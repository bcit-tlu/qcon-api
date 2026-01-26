from bs4 import BeautifulSoup
from api.formats.docx.extract_images import extract_images
from api.formats.docx.formatter import run_formatter
from api.formats.docx.sectioner import run_sectioner
from api.formats.docx.splitter import Splitter
from api.formats.docx.endanswers import get_endanswers
from api.formats.docx.parser import run_parser
from api.formats.docx.convert_txt import convert_txt
from api.formats.docx.fix_numbering import fix_numbering
import socket
from api.tasks import run_pandoc_task
from django.conf import settings
import logging
from api.logging.logging_adapter import FilenameLoggingAdapter

from api.logging.ErrorTypes import *

logger = logging.getLogger(__name__)


class Process:
    def __init__(self, questionlibrary) -> None:
        self.questionlibrary = questionlibrary
        self.images_extracted = 0
        self.subsection_count = 0
        self.questions_expected = 0
        self.questions_processed = 0
        self.endanswers_count = 0
        self.question_info_count = 0
        self.question_warning_count = 0
        self.question_error_count = 0

    def run_pandoc(self):
        file_logger = FilenameLoggingAdapter(
            logger,
            {
                "filename": self.questionlibrary.temp_file.name,
                "user_ip": self.questionlibrary.user_ip,
            },
        )
        try:
            result = run_pandoc_task.apply_async(
                kwargs={"questionlibrary_id": self.questionlibrary.id},
                ignore_result=False,
            )
            pandoc_task_result = result.get()
            self.questionlibrary.pandoc_output = pandoc_task_result
        except Exception as e:
            raise Exception(str(e))

        if self.questionlibrary.pandoc_output is None:
            raise MarkDownConversionError("Pandoc output string is empty")

    def convert_txt(self):
        convert_txt(self.questionlibrary)

    def fix_numbering(self):
        fix_numbering(self.questionlibrary)

    def extract_images(self):
        self.images_extracted = extract_images(self.questionlibrary)

    def run_formatter(self):
        file_logger = FilenameLoggingAdapter(
            logger,
            {
                "filename": self.questionlibrary.temp_file.name,
                "user_ip": self.questionlibrary.user_ip,
            },
        )
        file_logger.debug("starting formatter antlr process")
        run_formatter(self.questionlibrary)

    # This is to split sections into separate objects
    def run_sectioner(self):
        file_logger = FilenameLoggingAdapter(
            logger,
            {
                "filename": self.questionlibrary.temp_file.name,
                "user_ip": self.questionlibrary.user_ip,
            },
        )
        file_logger.debug("starting sectioner antlr process")
        self.subsection_count = run_sectioner(self.questionlibrary)

    def run_splitter(self):
        file_logger = FilenameLoggingAdapter(
            logger,
            {
                "filename": self.questionlibrary.temp_file.name,
                "user_ip": self.questionlibrary.user_ip,
            },
        )
        file_logger.debug("starting splitter antlr process")
        splitter = Splitter(self.questionlibrary)
        self.questions_expected = splitter.run_splitter()

    def get_endanswers(self):
        self.endanswers_count = get_endanswers(self.questionlibrary)

    def run_parser(self):
        file_logger = FilenameLoggingAdapter(
            logger,
            {
                "filename": self.questionlibrary.temp_file.name,
                "user_ip": self.questionlibrary.user_ip,
            },
        )
        file_logger.debug("starting questionparser antlr process")
        run_parser(self.questionlibrary)

    def sendformat(self, status, statustext, data):
        return {
            "hostname": socket.gethostname(),
            "version": settings.APP_VERSION,
            "status": status,
            "statustext": statustext,
            "images_count": str(self.images_extracted),
            "section_count": str(self.subsection_count),
            "questions_count": str(self.questions_expected),
            "endanswer_count": str(self.endanswers_count),
            "question_info_count": str(self.question_info_count),
            "question_warning_count": str(self.question_warning_count),
            "question_error_count": str(self.question_error_count),
            "data": data,
        }


def run_pipeline(pipeline):
    pipeline.run_pandoc()
    pipeline.extract_images()
    pipeline.run_formatter()
    pipeline.run_sectioner()
    pipeline.run_splitter()
    pipeline.get_endanswers()
    pipeline.run_parser()
    return pipeline


def process(questionlibrary):
    pipeline = Process(questionlibrary)
    return run_pipeline(pipeline)
