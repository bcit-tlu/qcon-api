from os import path
import logging

from api.serializers import QuestionLibraryPackageSerializer, count_errors
from api.formats.scorm.scorm_extractor import ScormExtractor

logger = logging.getLogger(__name__)


class ScormToJsonError(Exception):
    def __init__(self, message):
        super().__init__(message)


def build_scorm_to_json(instance):
    """
    Run the SCORM extractor and return JSON data + QuestionLibrary instance.
    """
    scorm_zip_path = instance.temp_file.path
    xml_reader = ScormExtractor(
        scorm_zip_path,
        extract_to_path=path.join(instance.folder_path, "scorm_extract"),
    )

    question_library = xml_reader.populate_django_models(instance)
    ql_serializer = QuestionLibraryPackageSerializer(question_library)
    json_data = ql_serializer.data

    count_errors(question_library)
    json_data["total_question_errors"] = str(question_library.total_question_errors or 0)
    json_data["total_document_errors"] = str(question_library.total_document_errors or 0)

    instance.json_data = json_data
    instance.save()

    return json_data, question_library


def scorm_to_json(instance, logger_instance=None):
    """
    High-level function to convert SCORM ZIP to JSON.
    Returns the JSON data and QuestionLibrary instance.
    """
    log = logger_instance or logger
    log.info(f"[{instance.id}] SCORM to JSON conversion started")
    
    json_data, question_library = build_scorm_to_json(instance)
    log.info(f"[{instance.id}] SCORM to JSON conversion completed")
    
    return json_data, question_library
