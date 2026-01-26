from django.conf import settings
from django.http import FileResponse
from api.serializers import QuestionLibraryPackageSerializer
import logging

logger = logging.getLogger(__name__)


class JsonToScormError(Exception):
    def __init__(self, errors):
        super().__init__("JSON to SCORM validation failed")
        self.errors = errors


def build_scorm_from_json(json_data):
    """
    Build SCORM ZIP from JSON data.
    Returns the QuestionLibrary instance with zip_file created.
    """
    payload = json_data.get("data", json_data)
    ql_serializer = QuestionLibraryPackageSerializer(data=payload)
    if not ql_serializer.is_valid():
        raise JsonToScormError(ql_serializer.errors)

    ql_instance = ql_serializer.save()
    ql_instance.filter_main_title()
    ql_instance.folder_path = settings.MEDIA_ROOT + str(ql_instance.id)
    ql_instance.image_path = ql_instance.folder_path + settings.MEDIA_URL
    ql_instance.create_directory()
    ql_instance.save()

    ql_instance.create_xml_files()
    missing_files = []
    if not ql_instance.imsmanifest_file:
        missing_files.append("imsmanifest_file")
    if not ql_instance.questiondb_file:
        missing_files.append("questiondb_file")
    if missing_files:
        detail = ql_instance.error or "XML generation failed."
        raise JsonToScormError({"xml_files": [detail], "missing_files": missing_files})

    ql_instance.zip_files()

    if not ql_instance.zip_file:
        detail = ql_instance.error or "Zip file was not created."
        raise JsonToScormError({"zip_file": [detail]})

    return ql_instance


def json_to_scorm(json_data, logger_instance=None):
    """
    High-level function to convert JSON to SCORM ZIP file.
    Returns a FileResponse and QuestionLibrary instance.
    """
    log = logger_instance or logger
    log.info("JSON to SCORM conversion started")
    ql_instance = build_scorm_from_json(json_data)
    
    file_name = f"{ql_instance.filtered_main_title}.zip"
    file_response = FileResponse(ql_instance.zip_file)
    file_response['Content-Disposition'] = f'attachment; filename="{file_name}"'
    
    log.info(f"[{ql_instance.id}] JSON to SCORM conversion completed")
    
    return file_response, ql_instance
