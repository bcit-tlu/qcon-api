import copy
import re
import socket

from django.conf import settings

from api.serializers import JsonResponseSerializer, count_errors
from api.formats.docx.process_helper import html_to_plain, trim_text


def build_response_payload(questionlibrary, preview=False):
    count_errors(questionlibrary)
    serializer = JsonResponseSerializer(questionlibrary)
    json_data = serializer.data
    json_data["total_question_errors"] = str(questionlibrary.total_question_errors or 0)
    json_data["total_document_errors"] = str(questionlibrary.total_document_errors or 0)

    questionlibrary.json_data = json_data
    questionlibrary.save(update_fields=["json_data"])

    if preview:
        return _apply_preview_transform(copy.deepcopy(json_data), questionlibrary)

    return json_data


def build_status_payload(status, statustext, data="", process=None, questionlibrary=None):
    if process:
        payload = process.sendformat(status, statustext, data)
    else:
        payload = {
            "hostname": socket.gethostname(),
            "version": settings.APP_VERSION,
            "status": status,
            "statustext": statustext,
            "images_count": "0",
            "section_count": "0",
            "questions_count": "0",
            "endanswer_count": "0",
            "question_info_count": "0",
            "question_warning_count": "0",
            "question_error_count": "0",
            "data": data,
        }

    if questionlibrary:
        total_question_errors = getattr(questionlibrary, "total_question_errors", 0) or 0
        total_document_errors = getattr(questionlibrary, "total_document_errors", 0) or 0
        payload["total_question_errors"] = str(total_question_errors)
        payload["total_document_errors"] = str(total_document_errors)

    return payload


def _apply_preview_transform(json_data, questionlibrary):
    def replace_placeholders(text):
        if not text:
            return text

        pattern = r"&lt;&lt;&lt;&lt;(\d+)&gt;&gt;&gt;&gt;"

        def replace_match(match):
            image_id = match.group(1)
            try:
                image = questionlibrary.get_image(int(image_id))
                return image.image or match.group(0)
            except Exception:
                return match.group(0)

        return re.sub(pattern, replace_match, text)

    def build_title_from_text(text):
        if not text:
            return None

        has_table = re.search(r"<table(.|\n)+?</table>", text)
        has_img = re.search(r"<img\s+[^>]+>", text)

        title_text = text.replace("\n", " ")
        title_text = re.sub(r"<img\s+(.)+?\s+\/>", "[IMG]", title_text)
        title_text = re.sub(r"<table(.|\n)+?</table>", "[TABLE]", title_text)
        title_text = re.sub(r"&lt;&lt;&lt;&lt;\d+&gt;&gt;&gt;&gt;", "[IMG]", title_text)

        title_text = html_to_plain(title_text)
        title_text = trim_text(title_text)

        prefix = ""
        if has_table:
            prefix = "[TABLE]" + prefix
        if has_img:
            prefix = "[IMG]" + prefix

        if prefix:
            prefix = prefix + " "
            title_text = re.sub(r"\s*\[IMG\]", "", title_text).strip()
            title_text = re.sub(r"\s*\[TABLE\]", "", title_text).strip()

        title_text = prefix + title_text
        return title_text[:127]

    for section in json_data.get("sections", []):
        section["text"] = replace_placeholders(section.get("text"))

        for question in section.get("questions", []):
            question["text"] = replace_placeholders(question.get("text"))

            if not question.get("title"):
                question["title"] = build_title_from_text(question.get("text"))

            for mc in question.get("multiple_choice") or []:
                for answer in mc.get("multiple_choice_answers") or []:
                    answer["answer"] = replace_placeholders(answer.get("answer"))
                    answer["answer_feedback"] = replace_placeholders(answer.get("answer_feedback"))

            for tf in question.get("true_false") or []:
                tf["true_feedback"] = replace_placeholders(tf.get("true_feedback"))
                tf["false_feedback"] = replace_placeholders(tf.get("false_feedback"))

            for fib in question.get("fib") or []:
                fib["text"] = replace_placeholders(fib.get("text"))

            for ms in question.get("multiple_select") or []:
                for answer in ms.get("multiple_select_answers") or []:
                    answer["answer"] = replace_placeholders(answer.get("answer"))
                    answer["answer_feedback"] = replace_placeholders(answer.get("answer_feedback"))

            for ordering in question.get("ordering") or []:
                ordering["text"] = replace_placeholders(ordering.get("text"))
                ordering["ord_feedback"] = replace_placeholders(ordering.get("ord_feedback"))

            for matching in question.get("matching") or []:
                for choice in matching.get("matching_choices") or []:
                    choice["choice_text"] = replace_placeholders(choice.get("choice_text"))
                    for answer in choice.get("matching_answers") or []:
                        answer["answer_text"] = replace_placeholders(answer.get("answer_text"))

            for wr in question.get("written_response") or []:
                wr["initial_text"] = replace_placeholders(wr.get("initial_text"))
                wr["answer_key"] = replace_placeholders(wr.get("answer_key"))

    return json_data
