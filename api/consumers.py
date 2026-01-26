import json
from channels.generic.websocket import JsonWebsocketConsumer
from django.core.files.base import ContentFile
import base64
from os.path import normpath
from .models import QuestionLibrary
import logging
newlogger = logging.getLogger(__name__)
from .logging.logging_adapter import FilenameLoggingAdapter
# from .logging.contextfilter import QuestionlibraryFilenameFilter
# logger.addFilter(QuestionlibraryFilenameFilter())
from .pipelines.response_payload import build_response_payload, build_status_payload
from .pipelines.ws_pipeline import Process

from .formats.docx.extract_images import ImageExtractError
from .formats.docx.formatter import FormatterError
from .formats.docx.sectioner import SectionerError
from .formats.docx.splitter import SplitterError
from .formats.docx.endanswers import EndAnswerError
from .formats.docx.parser import ParserError


# class FilenameLoggingAdapter(logging.LoggerAdapter):
#     """
#     This example adapter expects the passed in dict-like object to have a
#     'connid' key, whose value in brackets is prepended to the log message.
#     """
#     def process(self, msg, kwargs):
#         return f"[{self.extra['filename']}] {msg}", kwargs

class TextConsumer(JsonWebsocketConsumer):

    def connect(self):
        newlogger.info("New connection started")
        sessionid = None
        # print(self.scope['url_route']['kwargs']['session_id'])
        # self.sessionid = self.scope['url_route']['kwargs']['session_id']
        # self.channel_layer.group_add(self.sessionid, self.channel_name)
        self.accept()

    def disconnect(self, close_code):
        self.close()
        newlogger.info("Closing Connection")
        # self.channel_layer.group_discard(self.sessionid, self.channel_name)

    def receive_json(self, content, **kwargs):
        
###########################################
        # Save the file
###########################################
        try:
            newlogger.info("Process Start")
            format, fixeddata = content.get('file').split(';base64,')
            received_file = ContentFile(base64.b64decode(fixeddata),
                                        name=content.get('filename'))

            new_questionlibrary = QuestionLibrary.objects.create()

            new_questionlibrary.temp_file = received_file
            # new_questionlibrary.session_id = self.sessionid
            new_questionlibrary.main_title = content.get('filename').split(".")[0]
            new_questionlibrary.randomize_answer = content.get('randomize_answer')
            media_folder = content.get('media_folder')
            if media_folder != None:
                media_folder = normpath(media_folder).lstrip('/')
                new_questionlibrary.media_folder = media_folder
            enumeration = content.get('enumeration')
            if enumeration and enumeration > 0 and enumeration < 7:
                new_questionlibrary.enumeration = enumeration

            new_questionlibrary.user_ip = content.get('user_ip')
            new_questionlibrary.save()
            process = Process(new_questionlibrary)
            logger = FilenameLoggingAdapter(newlogger, {
                'filename': new_questionlibrary.temp_file.name,
                'user_ip': new_questionlibrary.user_ip
                })
            logger.info("File Saved")
        except Exception as e:
            logger.error("Not a valid .docx File: {e}")
            error_payload = build_status_payload(
                "Error",
                "Not a valid .docx File",
                "",
                process=None,
                questionlibrary=None,
            )
            self.send(text_data=json.dumps(error_payload))
            # close connection
            close_payload = build_status_payload("Close", "", "", process=None, questionlibrary=None)
            self.send(text_data=json.dumps(close_payload))
            return
        
###########################################
        # create_pandocstring
###########################################

        try:
            # process.questionlibrary.create_pandocstring()
            process.run_pandoc()
            logger.info("Pandoc DONE")
        except Exception as e:
            logger.error(str(e))
            error_payload = build_status_payload(
                "Error",
                "File unreadable",
                "",
                process=process,
                questionlibrary=process.questionlibrary,
            )
            self.send(text_data=json.dumps(error_payload))
            # close connection
            close_payload = build_status_payload(
                "Close",
                "",
                "",
                process=process,
                questionlibrary=process.questionlibrary,
            )
            self.send(text_data=json.dumps(close_payload))
            # return
        # except Exception as e:
        #     self.send(text_data=json.dumps(process.sendformat("Close", "", "")))
        #     logger.error(str(e))
        #     return
        else:
            self.send(text_data=json.dumps(process.sendformat("Busy", "The file is valid", "")))

###########################################
        # Extract Images
###########################################

        try:
            process.extract_images()
            logger.info("Done extracting Images")
        except ImageExtractError as e:
            self.send(text_data=json.dumps(process.sendformat("Warn", "Images extraction failed", "")))
        else:
            logger.info(f'{str(process.images_extracted)} Images Extracted')
            self.send(text_data=json.dumps(process.sendformat("Busy", "Image found: " + str(process.images_extracted), "")))

###########################################
        # Convert to txt for fixing numbering
###########################################

        # try:
        #     process.convert_txt()
        #     logger.info("convert txt DONE")
        # except Exception as e:
        #     logger.error(e)

###########################################
        # Fix Numbering (broken lists)
###########################################

        # try:
        #     process.fix_numbering()
        #     logger.info("numbering fix DONE")
        # except Exception as e:
        #     logger.error(e)
        #     self.send(
        #         text_data=json.dumps(process.sendformat("Error", str(e), "")))
        #     # close connection
        #     # self.send(text_data=json.dumps(process.sendformat("Close", "", "")))
        #     return

##########################################
        # run_formatter
##########################################
        logger.debug("Formatting ...")
        try:
            process.run_formatter()
            logger.info("Formatter DONE")
        except FormatterError as e:
            logger.error("FormatterError: " + str(e))
            error_payload = build_status_payload(
                "Error",
                "No contents found in the body of the file",
                "",
                process=process,
                questionlibrary=process.questionlibrary,
            )
            self.send(text_data=json.dumps(error_payload))
            # close connection
            close_payload = build_status_payload(
                "Close",
                "",
                "",
                process=process,
                questionlibrary=process.questionlibrary,
            )
            self.send(text_data=json.dumps(close_payload))
            return
        else:
            self.send(text_data=json.dumps(process.sendformat("Busy", "Content Body detected", "")))

##########################################
        # run_sectioner
##########################################
        logger.debug("Sectioning ...")
        try:
            process.run_sectioner()
            logger.info("Sectioner DONE")
        except SectionerError as e:
            logger.error("SectionerError: " + str(e))
            error_payload = build_status_payload(
                "Error",
                "Sections can not be identified",
                "",
                process=process,
                questionlibrary=process.questionlibrary,
            )
            self.send(text_data=json.dumps(error_payload))
            # close connection
            close_payload = build_status_payload(
                "Close",
                "",
                "",
                process=process,
                questionlibrary=process.questionlibrary,
            )
            self.send(text_data=json.dumps(close_payload))
            return
        else:
            self.send(text_data=json.dumps(process.sendformat("Busy", "Section found: " + str(process.subsection_count), "")))

##########################################
        # run_splitter
##########################################
        logger.debug("Splitting Questions ...")
        try:
            process.run_splitter()
            logger.info("Splitter DONE")
        except Exception as e:
            logger.error("SplitterError: " + str(e))
            error_payload = build_status_payload(
                "Error",
                "Splitter failed",
                "",
                process=process,
                questionlibrary=process.questionlibrary,
            )
            self.send(text_data=json.dumps(error_payload))
            # close connection
            close_payload = build_status_payload(
                "Close",
                "",
                "",
                process=process,
                questionlibrary=process.questionlibrary,
            )
            self.send(text_data=json.dumps(close_payload))
            return
        else:
            self.send(text_data=json.dumps(process.sendformat("Busy", "Question found: " + str(process.questions_expected), "")))
###########################################
        # Grab end answers
###########################################
        logger.debug("Checking Endanswer ...")
        try:
            process.get_endanswers()
            logger.info("Check Endanswer DONE")
        except EndAnswerError as e:
            logger.error("EndAnswerError: " + str(e))
            self.send(text_data=json.dumps(process.sendformat("Busy", "Endanswers not found", "")))
        else:
            if process.endanswers_count > 0:
                self.send(text_data=json.dumps(process.sendformat("Busy", "End answers found", "")))

###########################################
        # run_parser
###########################################
        logger.debug("Starting Parser ...")
        try:
            process.run_parser()
            logger.info("Parser DONE")
        except Exception as e:
            logger.error("ParserError: " + str(e))
            error_payload = build_status_payload(
                "Error",
                "Parser failed",
                "",
                process=process,
                questionlibrary=process.questionlibrary,
            )
            self.send(text_data=json.dumps(error_payload))
                # close connection
            close_payload = build_status_payload(
                "Close",
                "",
                "",
                process=process,
                questionlibrary=process.questionlibrary,
            )
            self.send(text_data=json.dumps(close_payload))
        else:
            self.send(text_data=json.dumps(process.sendformat("Busy", "Parser complete", "")))

        # serialize and send response
###########################################
        logger.info("Process End")

        json_data = build_response_payload(process.questionlibrary, preview=True)
        done_payload = build_status_payload(
            "Done",
            "",
            json_data,
            process=process,
            questionlibrary=process.questionlibrary,
        )
        self.send(text_data=json.dumps(done_payload))

######################### Close Connection
        self.send(text_data=json.dumps(process.sendformat("Close", "", "")))
        self.close()
        
