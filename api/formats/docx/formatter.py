from ast import Not
import os
import xml.etree.ElementTree as ET
import subprocess
import re
# from .process_helper import trim_text
from api.tasks import trim_text

import logging
newlogger = logging.getLogger(__name__)
from api.logging.logging_adapter import FilenameLoggingAdapter

def run_formatter(questionlibrary):
    logger = FilenameLoggingAdapter(newlogger, {'filename': os.path.basename(questionlibrary.temp_file.name)})
    root = None

    try:
        os.chdir('/antlr_build/formatter')
        result = subprocess.run('java -cp formatter.jar:* formatter',
                                shell=True,
                                input=questionlibrary.pandoc_output.encode("utf-8"),
                                capture_output=True)
        os.chdir('/code')
        root = ET.fromstring(result.stdout.decode("utf-8"))
    except:
        raise FormatterError("Internal error while converting file")
    
    logger.debug("starting formatter extraction")

# ==================================== SECTION INFO

    maincontenttitle = root.find('maincontent_title')
    logger.debug("checking maincontent title")
    if maincontenttitle is not None:
        raw_main = (maincontenttitle.text or "").strip()
        if raw_main:
            # Use the first H1 line as the title; remaining lines become root-level text
            main_lines = raw_main.splitlines()
            title_index = None
            for idx, line in enumerate(main_lines):
                if line.lstrip().startswith('#'):
                    title_index = idx
                    break

            if title_index is not None:
                main_title = main_lines[title_index].strip()
                main_title = (trim_text(main_title)).lstrip('# ').strip()
                main_text_lines = main_lines[title_index + 1:]
            else:
                # Fallback: treat the first line as title if no H1 is found
                main_title = (trim_text(main_lines[0])).lstrip('# ').strip()
                main_text_lines = main_lines[1:]

            main_text = "\n".join(main_text_lines).strip()

            if main_title:
                questionlibrary.main_title = main_title
            if main_text:
                # Preserve raw markdown for root-level text
                questionlibrary.main_text = main_text
            questionlibrary.save()

# ==================================== BODY

    body = root.find('body')
    if body is not None:
        questionlibrary.formatter_output = body.text.rstrip() + "\n"
        questionlibrary.save()
    else:
        raise FormatterError("document body not found")

# ==================================== END ANSWERS

    end_answers = root.find('end_answers')
    logger.debug("checking for endanswers block")
    if end_answers is not None:
        logger.debug("endanswers block found")
        questionlibrary.end_answers_raw = end_answers.text
        questionlibrary.save()
    else:
        logger.info("No endanswers block found")

class FormatterError(Exception):
    def __init__(self, reason, message="Formatter Error"):
        self.reason = reason
        self.message = message
    def __str__(self):
        return f'{self.message} -> {self.reason}'
