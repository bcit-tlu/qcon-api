import logging
from api.pipelines.ws_pipeline import Process, run_pipeline
from api.pipelines.response_payload import build_response_payload

logger = logging.getLogger(__name__)


class DocxToJsonError(Exception):
    def __init__(self, message, process=None):
        super().__init__(message)
        self.process = process


def build_docx_to_json(questionlibrary):
    """
    Run the DOCX pipeline and return the QuestionLibrary instance.
    """
    pipeline = Process(questionlibrary)
    try:
        run_pipeline(pipeline)
    except Exception as exc:
        raise DocxToJsonError(str(exc), process=pipeline)
    return pipeline.questionlibrary


def docx_to_json(questionlibrary, logger_instance=None):
    """
    High-level function to convert DOCX to JSON.
    Returns the JSON payload and QuestionLibrary instance.
    """
    log = logger_instance or logger
    log.info(f"[{questionlibrary.id}] DOCX to JSON conversion started")
    ql_instance = build_docx_to_json(questionlibrary)
    json_data = build_response_payload(ql_instance)
    log.info(f"[{ql_instance.id}] DOCX to JSON conversion completed")
    return json_data, ql_instance
