from os import path, makedirs
from zipfile import ZipFile
from django.conf import settings


def extract_scorm_zip(scorm_zip_path, extract_to_path=None):
    """
    Extract a SCORM ZIP file and return the extraction path.

    Args:
        scorm_zip_path: Path to the SCORM ZIP file
        extract_to_path: Optional path to extract ZIP contents

    Returns:
        str: Path where the ZIP was extracted
    """
    if not path.exists(scorm_zip_path):
        raise FileNotFoundError(f"SCORM ZIP file not found: {scorm_zip_path}")

    if extract_to_path is None:
        zip_basename = path.splitext(path.basename(scorm_zip_path))[0]
        extract_to_path = path.join(settings.MEDIA_ROOT, f"scorm_extract_{zip_basename}")

    if not path.exists(extract_to_path):
        makedirs(extract_to_path)

    with ZipFile(scorm_zip_path, "r") as zip_ref:
        zip_ref.extractall(extract_to_path)

    return extract_to_path
