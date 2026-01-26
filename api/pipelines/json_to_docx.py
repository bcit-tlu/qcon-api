import base64
import glob
import os
import re
import uuid
import subprocess
import logging
from os import path

from django.conf import settings
from django.core.files import File
from django.http import FileResponse

from api.serializers import QuestionLibraryPackageSerializer
from api.formats.scorm.scorm_formatter import ScormFormatter

logger = logging.getLogger(__name__)

class JsonToDocxError(Exception):
    def __init__(self, errors):
        super().__init__("JSON to DOCX validation failed")
        self.errors = errors


def build_docx_from_json(json_data, logger_instance=None):
    """
    High-level function to convert JSON to DOCX file.
    Returns a FileResponse and QuestionLibrary instance.
    """
    log = logger_instance or logger
    
    payload = json_data.get("data", json_data)
    ql_serializer = QuestionLibraryPackageSerializer(data=payload)
    if not ql_serializer.is_valid():
        raise JsonToDocxError(ql_serializer.errors)

    ql_instance = ql_serializer.save()
    ql_instance.filter_main_title()
    ql_instance.folder_path = settings.MEDIA_ROOT + str(ql_instance.id)
    ql_instance.image_path = ql_instance.folder_path + settings.MEDIA_URL
    ql_instance.create_directory()
    ql_instance.save()

    formatter = ScormFormatter()
    markdown_text = formatter.format_to_markdown(ql_instance)

    image_counter = 0
    base64_pattern = r'<img\s+([^>]*?)src=["\'](data:image/([^;]+);base64,([^"\']+))["\']([^>]*?)>'

    def replace_base64_with_file(match):
        nonlocal image_counter
        before_src = match.group(1)
        image_type = match.group(3)
        base64_data = match.group(4)
        after_src = match.group(5)

        try:
            image_data = base64.b64decode(base64_data)
            ext_map = {
                "png": "png",
                "jpeg": "jpg",
                "jpg": "jpg",
                "gif": "gif",
                "svg+xml": "svg",
                "webp": "webp",
            }
            ext = ext_map.get(image_type.lower(), "png")
            image_filename = f"image_{image_counter}_{uuid.uuid4().hex[:8]}.{ext}"
            image_path = path.join(ql_instance.folder_path, image_filename)

            with open(image_path, "wb") as img_file:
                img_file.write(image_data)

            image_counter += 1
            log.info(
                f"Extracted base64 image to file: {image_filename} ({len(image_data)} bytes)"
            )

            alt_match = re.search(r'alt=["\']([^"\']*)["\']', before_src + after_src)
            alt_text = alt_match.group(1) if alt_match else "image"
            markdown_image = f"![{alt_text}]({image_filename})"
            log.debug(f"Replacing base64 img tag with markdown: {markdown_image}")
            return markdown_image
        except Exception as e:
            log.error(f"Error extracting base64 image: {str(e)}")
            return match.group(0)

    markdown_text = re.sub(base64_pattern, replace_base64_with_file, markdown_text)
    log.info(f"Extracted {image_counter} base64 images to files")

    if ql_instance.main_title:
        filename = ql_instance.main_title.strip()
        filename = re.sub(r'[<>:"/\\|?*]', "", filename)
        filename = re.sub(r"\s+", "_", filename)
        filename = filename[:100]
        if not filename:
            filename = ql_instance.filtered_main_title
    else:
        filename = ql_instance.filtered_main_title

    docx_filename = f"{filename}.docx"
    docx_path = path.join(ql_instance.folder_path, docx_filename)

    current_file_dir = os.path.dirname(os.path.abspath(__file__))
    base_dir = os.path.dirname(os.path.dirname(current_file_dir))
    mdblockquote_path = os.path.abspath(
        os.path.join(base_dir, "pandoc", "pandoc-filters", "mdblockquote.lua")
    )
    emptypara_path = os.path.abspath(
        os.path.join(base_dir, "pandoc", "pandoc-filters", "emptypara.lua")
    )
    log.debug(
        f"Lua filter paths: mdblockquote={mdblockquote_path}, emptypara={emptypara_path}"
    )

    temp_md_path = path.join(ql_instance.folder_path, "temp_markdown.md")
    with open(temp_md_path, "w", encoding="utf-8") as f:
        f.write(markdown_text)

    file_refs = re.findall(r'!\[.*?\]\((image_\d+_[^)]+)\)', markdown_text)
    log.info(f"Found {len(file_refs)} image file references in markdown")
    image_files = glob.glob(path.join(ql_instance.folder_path, "image_*.*"))
    image_info = []
    total_image_size = 0
    for img_file in image_files:
        if path.exists(img_file):
            img_size = path.getsize(img_file)
            total_image_size += img_size
            img_size_mb = img_size / (1024 * 1024)
            image_info.append(
                f"{path.basename(img_file)} ({img_size_mb:.2f} MB, {img_size} bytes)"
            )
    if len(image_files) > 0:
        log.info(f"Found {len(image_files)} image files in folder:")
        for info in image_info:
            log.info(f"  - {info}")
        log.info(
            f"Total image size: {total_image_size / (1024 * 1024):.2f} MB ({total_image_size} bytes)"
        )
    log.info(f"Markdown file created at: {temp_md_path}")

    original_cwd = os.getcwd()
    try:
        os.chdir(ql_instance.folder_path)
        temp_md_rel_path = "temp_markdown.md"
        docx_output_name = os.path.basename(docx_path)
        log.info(
            f"Converting markdown with image file references to DOCX (working dir: {os.getcwd()})"
        )
        existing_images = glob.glob("image_*.*")
        log.info(f"Images in working directory before Pandoc: {existing_images}")
        with open(temp_md_rel_path, "r", encoding="utf-8") as f:
            md_content = f.read()
            image_refs_in_md = re.findall(r'!\[.*?\]\((image_\d+_[^)]+)\)', md_content)
            log.info(f"Image references found in markdown file: {image_refs_in_md}")
        pandoc_cmd = [
            "pandoc",
            temp_md_rel_path,
            "-f",
            "markdown_github+fancy_lists+emoji+hard_line_breaks+all_symbols_escapable+escaped_line_breaks+pipe_tables+startnum+tex_math_dollars",
            "-t",
            "docx+empty_paragraphs",
            "-o",
            docx_output_name,
            "--no-highlight",
            "--preserve-tabs",
            "--wrap=preserve",
            "--indent=false",
            "--mathml",
            "--ascii",
            "--lua-filter=" + mdblockquote_path,
            "--lua-filter=" + emptypara_path,
        ]
        log.info(f"Running pandoc command: {' '.join(pandoc_cmd)}")
        result = subprocess.run(
            pandoc_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        if result.returncode != 0:
            log.error(f"Pandoc failed (exit {result.returncode}): {result.stderr}")
            raise Exception(f"Pandoc failed: {result.stderr}")
        if result.stderr:
            log.warning(f"Pandoc warnings: {result.stderr}")
        log.info("Pandoc markdown to DOCX conversion completed")
    finally:
        os.chdir(original_cwd)

    try:
        if path.exists(temp_md_path):
            from os import remove

            remove(temp_md_path)

        image_files = (
            glob.glob(path.join(ql_instance.folder_path, "image_*.png"))
            + glob.glob(path.join(ql_instance.folder_path, "image_*.jpg"))
            + glob.glob(path.join(ql_instance.folder_path, "image_*.jpeg"))
            + glob.glob(path.join(ql_instance.folder_path, "image_*.gif"))
            + glob.glob(path.join(ql_instance.folder_path, "image_*.svg"))
            + glob.glob(path.join(ql_instance.folder_path, "image_*.webp"))
        )
        for img_file in image_files:
            try:
                if path.exists(img_file):
                    os.remove(img_file)
            except Exception as e:
                log.warning(
                    f"Could not remove temporary image file {img_file}: {str(e)}"
                )
    except Exception:
        pass

    with open(docx_path, "rb") as f:
        ql_instance.temp_file.save(docx_filename, File(f), save=True)

    file_response = FileResponse(ql_instance.temp_file)
    file_response["Content-Disposition"] = f'attachment; filename="{docx_filename}"'

    docx_size_bytes = path.getsize(docx_path)
    docx_size_mb = docx_size_bytes / (1024 * 1024)
    log.info(
        f"[{ql_instance.id}] JSON to DOCX conversion completed - DOCX size: {docx_size_mb:.2f} MB ({docx_size_bytes} bytes)"
    )

    return file_response, ql_instance


def json_to_docx(json_data, logger_instance=None):
    """
    High-level function to convert JSON to DOCX file.
    Returns a FileResponse and QuestionLibrary instance.
    """
    log = logger_instance or logger
    log.info("JSON to DOCX conversion started")
    file_response, ql_instance = build_docx_from_json(json_data, log)
    log.info(f"[{ql_instance.id}] JSON to DOCX conversion completed")
    return file_response, ql_instance
