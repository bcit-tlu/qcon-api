import os
import re
import base64
import html
import xml.etree.cElementTree as ET
from os import path
from bs4 import BeautifulSoup


class ScormParser:
    """
    Parse SCORM XML files (questiondb.xml, imsmanifest.xml) into dicts.
    """

    def __init__(self, extracted_path):
        self.extracted_path = extracted_path
        self.questiondb_xml = None
        self.imsmanifest_xml = None
        self._parse_xml_files()

    def _parse_xml_files(self):
        """Parse questiondb.xml and imsmanifest.xml from extracted files."""
        questiondb_path = path.join(self.extracted_path, "questiondb.xml")
        imsmanifest_path = path.join(self.extracted_path, "imsmanifest.xml")

        if not path.exists(questiondb_path):
            raise FileNotFoundError(f"questiondb.xml not found in SCORM package: {questiondb_path}")

        if not path.exists(imsmanifest_path):
            raise FileNotFoundError(f"imsmanifest.xml not found in SCORM package: {imsmanifest_path}")

        self.questiondb_xml = ET.parse(questiondb_path)
        self.imsmanifest_xml = ET.parse(imsmanifest_path)

    def parse_manifest(self):
        """
        Parse imsmanifest.xml and extract metadata.

        Returns:
            dict: Dictionary containing manifest metadata
        """
        root = self.imsmanifest_xml.getroot()

        manifest_data = {
            "identifier": root.get("identifier", ""),
            "resources": [],
        }

        resources_el = root.find("resources")
        if resources_el is not None:
            for resource_el in resources_el.findall("resource"):
                resource_data = {
                    "identifier": resource_el.get("identifier", ""),
                    "type": resource_el.get("type", ""),
                    "material_type": resource_el.get("{http://desire2learn.com/xsd/d2lcp_v2p0}material_type", ""),
                    "href": resource_el.get("href", ""),
                    "link_target": resource_el.get("{http://desire2learn.com/xsd/d2lcp_v2p0}link_target", ""),
                    "title": resource_el.get("title", ""),
                }
                manifest_data["resources"].append(resource_data)

        return manifest_data

    def parse_questiondb(self):
        """
        Parse questiondb.xml and extract question library structure.

        Returns:
            dict: Dictionary containing question library data structure
        """
        root = self.questiondb_xml.getroot()
        objectbank_el = root.find("objectbank")
        if objectbank_el is None:
            raise ValueError("objectbank element not found in questiondb.xml")

        question_library_data = {
            "ident": objectbank_el.get("ident", ""),
            "sections": [],
        }

        base_sections = objectbank_el.findall("section")
        for section_el in base_sections:
            section_data = self._parse_section(section_el)
            question_library_data["sections"].append(section_data)

        return question_library_data

    def _parse_section(self, section_el):
        """
        Parse a section element and extract section data.
        """
        section_data = {
            "ident": section_el.get("ident", ""),
            "title": section_el.get("title", ""),
            "shuffle": False,
            "is_title_displayed": True,
            "is_text_displayed": False,
            "text": "",
            "questions": [],
        }

        selection_ordering = section_el.find("selection_ordering")
        if selection_ordering is not None:
            order_el = selection_ordering.find("order")
            if order_el is not None and order_el.get("order_type") == "Random":
                section_data["shuffle"] = True

        presentation_material = section_el.find("presentation_material")
        if presentation_material is not None:
            text = self._extract_material_text(presentation_material)
            section_data["text"] = text

        sectionproc = section_el.find("sectionproc_extension")
        if sectionproc is not None:
            display_name = sectionproc.find("{http://desire2learn.com/xsd/d2lcp_v2p0}display_section_name")
            if display_name is not None:
                section_data["is_title_displayed"] = display_name.text.lower() == "yes"

            type_display = sectionproc.find("{http://desire2learn.com/xsd/d2lcp_v2p0}type_display_section")
            if type_display is not None:
                section_data["is_text_displayed"] = type_display.text == "1"

        nested_sections = section_el.findall("section")
        for nested_section_el in nested_sections:
            nested_section_data = self._parse_section(nested_section_el)
            section_data["sections"] = section_data.get("sections", [])
            section_data["sections"].append(nested_section_data)

        items = section_el.findall("item")
        for item_el in items:
            question_data = self._parse_question(item_el)
            section_data["questions"].append(question_data)

        return section_data

    def _parse_question(self, item_el):
        """
        Parse a question (item) element and extract question data.
        """
        question_data = {
            "ident": item_el.get("ident", ""),
            "label": item_el.get("label", ""),
            "title": item_el.get("title", ""),
            "question_type": None,
            "points": 1.0,
            "text": "",
            "hint": None,
            "feedback": None,
            "question_specific_data": {},
        }

        itemmetadata = item_el.find("itemmetadata")
        if itemmetadata is not None:
            qtidata = itemmetadata.find("qtimetadata")
            if qtidata is not None:
                for field in qtidata.findall("qti_metadatafield"):
                    fieldlabel = field.find("fieldlabel")
                    fieldentry = field.find("fieldentry")
                    if fieldlabel is not None and fieldentry is not None:
                        if fieldlabel.text == "qmd_questiontype":
                            question_data["question_type"] = fieldentry.text
                        elif fieldlabel.text == "qmd_weighting":
                            try:
                                question_data["points"] = float(fieldentry.text)
                            except (ValueError, TypeError):
                                pass

        presentation = item_el.find("presentation")
        if presentation is not None:
            question_text = self._extract_question_text(presentation)
            question_data["text"] = question_text

        hint_el = item_el.find("hint")
        if hint_el is not None:
            question_data["hint"] = self._extract_hint_text(hint_el)

        feedback_els = item_el.findall("itemfeedback")
        for feedback_el in feedback_els:
            if feedback_el.get("ident") == question_data["label"]:
                question_data["feedback"] = self._extract_feedback_text(feedback_el)

        question_type = question_data["question_type"]
        if question_type:
            if question_type == "Multiple Choice":
                question_data["question_specific_data"] = self._parse_multiple_choice(item_el, question_data["label"])
                question_data["question_type_code"] = "MC"
            elif question_type == "True/False":
                question_data["question_specific_data"] = self._parse_true_false(item_el, question_data["label"])
                question_data["question_type_code"] = "TF"
            elif question_type == "Fill in the Blanks":
                question_data["question_specific_data"] = self._parse_fill_in_the_blanks(item_el, question_data["label"])
                question_data["question_type_code"] = "FIB"
            elif question_type == "Multi-Select":
                question_data["question_specific_data"] = self._parse_multi_select(item_el, question_data["label"])
                question_data["question_type_code"] = "MS"
            elif question_type == "Matching":
                question_data["question_specific_data"] = self._parse_matching(item_el, question_data["label"])
                question_data["question_type_code"] = "MAT"
            elif question_type == "Ordering":
                question_data["question_specific_data"] = self._parse_ordering(item_el, question_data["label"])
                question_data["question_type_code"] = "ORD"
            elif question_type == "Long Answer":
                question_data["question_specific_data"] = self._parse_written_response(item_el, question_data["label"])
                question_data["question_type_code"] = "WR"

        return question_data

    def _extract_material_text(self, material_el):
        """
        Extract text content from material element, handling CDATA and images.
        """
        text_parts = []

        flow_mat = material_el.find("flow_mat")
        if flow_mat is not None:
            materials = flow_mat.findall(".//material")
            for material in materials:
                mattext = material.find("mattext")
                if mattext is not None:
                    raw_text = mattext.text if mattext.text else ""
                    if mattext.tail:
                        raw_text += mattext.tail
                    decoded_text = html.unescape(raw_text)
                    cleaned_text = self._clean_cdata(decoded_text)
                    cleaned_text = self._inline_scorm_images(cleaned_text)
                    text_parts.append(cleaned_text)

        return "".join(text_parts)

    def _extract_question_text(self, presentation_el):
        """
        Extract question text from presentation element.
        """
        text_parts = []

        flow = presentation_el.find("flow")
        if flow is not None:
            material = flow.find("material")
            if material is not None:
                mattext = material.find("mattext")
                if mattext is not None:
                    raw_text = mattext.text if mattext.text else ""
                    if mattext.tail:
                        raw_text += mattext.tail
                    decoded_text = html.unescape(raw_text)
                    cleaned_text = self._clean_cdata(decoded_text)
                    cleaned_text = self._inline_scorm_images(cleaned_text)
                    text_parts.append(cleaned_text)

        return "".join(text_parts)

    def _extract_hint_text(self, hint_el):
        """Extract text from hint element."""
        hintmaterial = hint_el.find("hintmaterial")
        if hintmaterial is not None:
            return self._extract_material_text(hintmaterial)
        return None

    def _extract_feedback_text(self, feedback_el):
        """
        Extract text from feedback element.
        """
        material = feedback_el.find("material")
        if material is not None:
            mattext = material.find("mattext")
            if mattext is not None:
                raw_text = mattext.text if mattext.text else ""
                decoded_text = html.unescape(raw_text)
                cleaned_text = self._clean_cdata(decoded_text)
                return self._inline_scorm_images(cleaned_text)
        return None

    def _clean_cdata(self, text):
        """
        Normalize whitespace from CDATA sections while preserving HTML tags.
        """
        if not text:
            return ""

        try:
            cleaned = re.sub(r"[ \t\n\r]+", " ", text)
            cleaned = re.sub(r">\s+<", "><", cleaned)
            cleaned = cleaned.strip()
            return cleaned
        except Exception:
            cleaned = re.sub(r"\s+", " ", text).strip()
            return cleaned

    def _inline_scorm_images(self, html_text):
        """
        Convert SCORM image file paths to base64 data URIs in HTML text.
        """
        if not html_text or not self.extracted_path:
            return html_text

        img_pattern = r'<img\s+([^>]*?)src=["\']([^"\']+)["\']([^>]*?)>'

        def replace_image(match):
            before_src = match.group(1)
            img_src = match.group(2)
            after_src = match.group(3)

            if img_src.startswith("data:") or "base64" in img_src:
                return match.group(0)

            if img_src.startswith("http://") or img_src.startswith("https://"):
                return match.group(0)

            try:
                img_path = img_src.lstrip("./")
                possible_paths = [
                    path.join(self.extracted_path, img_path),
                    path.join(self.extracted_path, "assessment-assets", path.basename(img_path)),
                ]

                image_file = None
                for possible_path in possible_paths:
                    if path.exists(possible_path) and path.isfile(possible_path):
                        image_file = possible_path
                        break

                if not image_file:
                    for root, dirs, files in os.walk(self.extracted_path):
                        if path.basename(img_path) in files:
                            image_file = path.join(root, path.basename(img_path))
                            break

                if image_file and path.exists(image_file):
                    with open(image_file, "rb") as f:
                        image_data = f.read()
                        base64_data = base64.b64encode(image_data).decode("utf-8")

                    ext = path.splitext(image_file)[1].lower()
                    mime_types = {
                        ".png": "image/png",
                        ".jpg": "image/jpeg",
                        ".jpeg": "image/jpeg",
                        ".gif": "image/gif",
                        ".svg": "image/svg+xml",
                        ".webp": "image/webp",
                    }
                    mime_type = mime_types.get(ext, "image/png")

                    base64_src = f"data:{mime_type};base64,{base64_data}"
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.info(
                        f"Converted SCORM image {path.basename(image_file)} to base64 ({len(base64_data)} chars)"
                    )
                    return f'<img {before_src}src="{base64_src}"{after_src}>'
                else:
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.warning(f"SCORM image not found: {img_src} (searched in {self.extracted_path})")
                    return match.group(0)
            except Exception:
                return match.group(0)

        result = re.sub(img_pattern, replace_image, html_text)
        return result

    def _parse_multiple_choice(self, item_el, question_ident):
        """
        Parse multiple choice question data.
        """
        mc_data = {
            "randomize": False,
            "enumeration": 4,
            "answers": [],
        }

        presentation = item_el.find("presentation")
        if presentation is None:
            return mc_data

        flow = presentation.find("flow")
        if flow is None:
            return mc_data

        response_ext = flow.find("response_extension")
        if response_ext is not None:
            enumeration_el = response_ext.find("{http://desire2learn.com/xsd/d2lcp_v2p0}enumeration")
            if enumeration_el is not None and enumeration_el.text:
                try:
                    mc_data["enumeration"] = int(enumeration_el.text)
                except (ValueError, TypeError):
                    pass

        response_lid = flow.find("response_lid")
        if response_lid is not None:
            render_choice = response_lid.find("render_choice")
            if render_choice is not None:
                mc_data["randomize"] = render_choice.get("shuffle", "no").lower() == "yes"

            question_lid = response_lid.get("ident", "")
            answer_index = 1
            for flow_label in response_lid.findall(".//flow_label"):
                response_label = flow_label.find("response_label")
                if response_label is not None:
                    answer_ident = response_label.get("ident", "")
                    mattext = response_label.find(".//mattext")
                    answer_text = ""
                    if mattext is not None:
                        raw_text = mattext.text if mattext.text else ""
                        decoded_text = html.unescape(raw_text)
                        answer_text = self._clean_cdata(decoded_text)

                    weight = 0.0
                    answer_feedback = None
                    resprocessing = item_el.find("resprocessing")
                    if resprocessing is not None:
                        for respcondition in resprocessing.findall("respcondition"):
                            conditionvar = respcondition.find("conditionvar")
                            if conditionvar is not None:
                                varequal = conditionvar.find("varequal")
                                if varequal is not None and varequal.get("respident") == question_lid:
                                    if varequal.text == answer_ident:
                                        setvar = respcondition.find("setvar")
                                        if setvar is not None:
                                            try:
                                                weight = float(setvar.text)
                                            except (ValueError, TypeError):
                                                pass

                                        displayfeedback = respcondition.find("displayfeedback")
                                        if displayfeedback is not None:
                                            feedback_ident = displayfeedback.get("linkrefid", "")
                                            feedback_el = item_el.find(
                                                f".//itemfeedback[@ident='{feedback_ident}']"
                                            )
                                            if feedback_el is not None:
                                                answer_feedback = self._extract_feedback_text(feedback_el)

                    mc_data["answers"].append(
                        {
                            "answer": answer_text,
                            "weight": weight,
                            "answer_feedback": answer_feedback,
                            "order": answer_index,
                        }
                    )
                    answer_index += 1

        return mc_data

    def _parse_true_false(self, item_el, question_ident):
        """
        Parse true/false question data.
        """
        tf_data = {
            "true_weight": 0.0,
            "true_feedback": None,
            "false_weight": 0.0,
            "false_feedback": None,
            "enumeration": 4,
        }

        presentation = item_el.find("presentation")
        if presentation is None:
            return tf_data

        flow = presentation.find("flow")
        if flow is None:
            return tf_data

        response_ext = flow.find("response_extension")
        if response_ext is not None:
            enumeration_el = response_ext.find("{http://desire2learn.com/xsd/d2lcp_v2p0}enumeration")
            if enumeration_el is not None and enumeration_el.text:
                try:
                    tf_data["enumeration"] = int(enumeration_el.text)
                except (ValueError, TypeError):
                    pass

        response_lid = flow.find("response_lid")
        if response_lid is not None:
            question_lid = response_lid.get("ident", "")

            render_choice = response_lid.find("render_choice")
            true_ident = None
            false_ident = None
            if render_choice is not None:
                response_labels = render_choice.findall(".//response_label")
                if len(response_labels) >= 1:
                    true_ident = response_labels[0].get("ident", "")
                if len(response_labels) >= 2:
                    false_ident = response_labels[1].get("ident", "")

            resprocessing = item_el.find("resprocessing")

            if resprocessing is not None:
                for respcondition in resprocessing.findall("respcondition"):
                    conditionvar = respcondition.find("conditionvar")
                    if conditionvar is not None:
                        varequal = conditionvar.find("varequal")
                        if varequal is not None and varequal.get("respident") == question_lid:
                            answer_ident = varequal.text

                            if true_ident and answer_ident == true_ident:
                                setvar = respcondition.find("setvar")
                                if setvar is not None:
                                    try:
                                        tf_data["true_weight"] = float(setvar.text)
                                    except (ValueError, TypeError):
                                        pass

                                displayfeedback = respcondition.find("displayfeedback")
                                if displayfeedback is not None:
                                    feedback_ident = displayfeedback.get("linkrefid", "")
                                    feedback_el = item_el.find(
                                        f".//itemfeedback[@ident='{feedback_ident}']"
                                    )
                                    if feedback_el is not None:
                                        tf_data["true_feedback"] = self._extract_feedback_text(feedback_el)

                            elif false_ident and answer_ident == false_ident:
                                setvar = respcondition.find("setvar")
                                if setvar is not None:
                                    try:
                                        tf_data["false_weight"] = float(setvar.text)
                                    except (ValueError, TypeError):
                                        pass

                                displayfeedback = respcondition.find("displayfeedback")
                                if displayfeedback is not None:
                                    feedback_ident = displayfeedback.get("linkrefid", "")
                                    feedback_el = item_el.find(
                                        f".//itemfeedback[@ident='{feedback_ident}']"
                                    )
                                    if feedback_el is not None:
                                        tf_data["false_feedback"] = self._extract_feedback_text(feedback_el)

        return tf_data

    def _parse_fill_in_the_blanks(self, item_el, question_ident):
        """
        Parse fill in the blanks question data.
        """
        fib_data = {"fibs": []}

        presentation = item_el.find("presentation")
        if presentation is None:
            return fib_data

        flow = presentation.find("flow")
        if flow is None:
            return fib_data

        idx = 1
        for child in flow:
            if child.tag == "material":
                mattext = child.find("mattext")
                text = ""
                if mattext is not None:
                    raw_text = mattext.text if mattext.text else ""
                    text = html.unescape(raw_text)

                fib_data["fibs"].append({"type": "fibquestion", "text": text, "order": idx})

            elif child.tag == "response_str":
                question_ans = question_ident + str(idx) + "_ANS"

                answers = []
                resprocessing = item_el.find("resprocessing")
                if resprocessing is not None:
                    for respcondition in resprocessing.findall("respcondition"):
                        conditionvar = respcondition.find("conditionvar")
                        if conditionvar is not None:
                            varequal = conditionvar.find("varequal")
                            if varequal is not None and varequal.get("respident") == question_ans:
                                answer_text = varequal.text if varequal.text else ""
                                if answer_text:
                                    answers.append(answer_text)

                fib_data["fibs"].append(
                    {
                        "type": "fibanswer",
                        "text": ",".join(answers) if answers else "",
                        "order": idx,
                        "size": 30,
                    }
                )
                idx += 1

        return fib_data

    def _parse_multi_select(self, item_el, question_ident):
        """
        Parse multi-select question data.
        """
        ms_data = {
            "randomize": False,
            "enumeration": 4,
            "style": 2,
            "grading_type": 2,
            "answers": [],
        }

        presentation = item_el.find("presentation")
        if presentation is None:
            return ms_data

        flow = presentation.find("flow")
        if flow is None:
            return ms_data

        response_ext = flow.find("response_extension")
        if response_ext is not None:
            enumeration_el = response_ext.find("{http://desire2learn.com/xsd/d2lcp_v2p0}enumeration")
            if enumeration_el is not None and enumeration_el.text:
                try:
                    ms_data["enumeration"] = int(enumeration_el.text)
                except (ValueError, TypeError):
                    pass

            grading_type_el = response_ext.find("{http://desire2learn.com/xsd/d2lcp_v2p0}grading_type")
            if grading_type_el is not None and grading_type_el.text:
                try:
                    ms_data["grading_type"] = int(grading_type_el.text)
                except (ValueError, TypeError):
                    pass

        response_lid = flow.find("response_lid")
        if response_lid is not None:
            question_lid = response_lid.get("ident", "")

            render_choice = response_lid.find("render_choice")
            if render_choice is not None:
                ms_data["randomize"] = render_choice.get("shuffle", "no").lower() == "yes"

            answer_index = 1
            for flow_label in response_lid.findall(".//flow_label"):
                response_label = flow_label.find("response_label")
                if response_label is not None:
                    answer_ident = response_label.get("ident", "")

                    mattext = response_label.find(".//mattext")
                    answer_text = ""
                    if mattext is not None:
                        raw_text = mattext.text if mattext.text else ""
                        decoded_text = html.unescape(raw_text)
                        answer_text = self._clean_cdata(decoded_text)

                    is_correct = False
                    answer_feedback = None
                    resprocessing = item_el.find("resprocessing")
                    if resprocessing is not None:
                        for respcondition in resprocessing.findall("respcondition"):
                            conditionvar = respcondition.find("conditionvar")
                            if conditionvar is not None:
                                varequal = conditionvar.find("varequal")
                                if varequal is not None and varequal.get("respident") == question_lid:
                                    if varequal.text == answer_ident:
                                        setvar = respcondition.find("setvar")
                                        if setvar is not None:
                                            if setvar.get("varname") == "D2L_Correct":
                                                is_correct = True

                                        displayfeedback = respcondition.find("displayfeedback")
                                        if displayfeedback is not None:
                                            feedback_ident = displayfeedback.get("linkrefid", "")
                                            feedback_el = item_el.find(
                                                f".//itemfeedback[@ident='{feedback_ident}']"
                                            )
                                            if feedback_el is not None:
                                                answer_feedback = self._extract_feedback_text(feedback_el)

                    ms_data["answers"].append(
                        {
                            "answer": answer_text,
                            "is_correct": is_correct,
                            "answer_feedback": answer_feedback,
                            "order": answer_index,
                        }
                    )
                    answer_index += 1

        return ms_data

    def _parse_matching(self, item_el, question_ident):
        """
        Parse matching question data.
        """
        mat_data = {
            "grading_type": 0,
            "choices": [],
        }

        presentation = item_el.find("presentation")
        if presentation is None:
            return mat_data

        flow = presentation.find("flow")
        if flow is None:
            return mat_data

        response_ext = flow.find("response_extension")
        if response_ext is not None:
            grading_type_el = response_ext.find("{http://desire2learn.com/xsd/d2lcp_v2p0}grading_type")
            if grading_type_el is not None and grading_type_el.text:
                try:
                    mat_data["grading_type"] = int(grading_type_el.text)
                except (ValueError, TypeError):
                    pass

        matching_answers = {}
        response_grps = flow.findall("response_grp")

        for response_grp in response_grps:
            render_choice = response_grp.find("render_choice")
            if render_choice is not None:
                for response_label in render_choice.findall(".//response_label"):
                    answer_ident = response_label.get("ident", "")
                    mattext = response_label.find(".//mattext")
                    if mattext is not None:
                        raw_text = mattext.text if mattext.text else ""
                        answer_text = self._clean_cdata(raw_text)
                        if answer_text and answer_ident not in matching_answers:
                            matching_answers[answer_ident] = answer_text

        for response_grp in response_grps:
            choice_ident = response_grp.get("respident", "")

            material = response_grp.find("material")
            choice_text = ""
            if material is not None:
                mattext = material.find("mattext")
                if mattext is not None:
                    raw_text = mattext.text if mattext.text else ""
                    decoded_text = html.unescape(raw_text)
                    choice_text = self._clean_cdata(decoded_text)

            correct_answer_ident = None
            resprocessing = item_el.find("resprocessing")
            if resprocessing is not None:
                for respcondition in resprocessing.findall("respcondition"):
                    conditionvar = respcondition.find("conditionvar")
                    if conditionvar is not None:
                        varequal = conditionvar.find("varequal")
                        if varequal is not None and varequal.get("respident") == choice_ident:
                            setvar = respcondition.find("setvar")
                            if setvar is not None and setvar.get("varname") == "D2L_Correct":
                                correct_answer_ident = varequal.text
                                break

            matching_answers_list = []
            if correct_answer_ident and correct_answer_ident in matching_answers:
                matching_answers_list.append({"answer_text": matching_answers[correct_answer_ident]})

            mat_data["choices"].append(
                {"choice_text": choice_text, "matching_answers": matching_answers_list}
            )

        return mat_data

    def _parse_ordering(self, item_el, question_ident):
        """
        Parse ordering question data.
        """
        ord_data = {"items": []}

        presentation = item_el.find("presentation")
        if presentation is None:
            return ord_data

        flow = presentation.find("flow")
        if flow is None:
            return ord_data

        response_grp = flow.find('response_grp[@rcardinality="Ordered"]')
        if response_grp is None:
            return ord_data

        render_choice = response_grp.find("render_choice")
        if render_choice is None:
            return ord_data

        order_index = 1
        for response_label in render_choice.findall(".//response_label"):
            ident_num = response_label.get("ident", "")

            mattext = response_label.find(".//mattext")
            text = ""
            if mattext is not None:
                raw_text = mattext.text if mattext.text else ""
                decoded_text = html.unescape(raw_text)
                text = self._clean_cdata(decoded_text)

            ord_feedback = None
            question_ident_feedback = question_ident + "_IF"
            feedback_ident = question_ident_feedback + str(order_index)
            feedback_el = item_el.find(f".//itemfeedback[@ident='{feedback_ident}']")
            if feedback_el is not None:
                ord_feedback = self._extract_feedback_text(feedback_el)

            ord_data["items"].append(
                {"text": text, "order": order_index, "ord_feedback": ord_feedback}
            )
            order_index += 1

        return ord_data

    def _parse_written_response(self, item_el, question_ident):
        """
        Parse written response question data.
        """
        wr_data = {
            "enable_student_editor": False,
            "initial_text": None,
            "answer_key": "",
            "enable_attachments": False,
        }

        presentation = item_el.find("presentation")
        if presentation is not None:
            flow = presentation.find("flow")
            if flow is not None:
                response_ext = flow.find("response_extension")
                if response_ext is not None:
                    editor_el = response_ext.find("{http://desire2learn.com/xsd/d2lcp_v2p0}has_htmleditor")
                    if editor_el is not None:
                        editor_text = editor_el.text if editor_el.text else ""
                        wr_data["enable_student_editor"] = editor_text.lower() == "yes"

        answer_key_el = item_el.find("answer_key")
        if answer_key_el is not None:
            answer_key_mat = answer_key_el.find("answer_key_material")
            if answer_key_mat is not None:
                mattext = answer_key_mat.find(".//mattext")
                if mattext is not None:
                    raw_text = mattext.text if mattext.text else ""
                    wr_data["answer_key"] = self._clean_cdata(raw_text)

        initial_text_el = item_el.find("initial_text")
        if initial_text_el is not None:
            initial_text_mat = initial_text_el.find("initial_text_material")
            if initial_text_mat is not None:
                mattext = initial_text_mat.find(".//mattext")
                if mattext is not None:
                    raw_text = mattext.text if mattext.text else ""
                    decoded_text = html.unescape(raw_text)
                    cleaned_text = self._clean_cdata(decoded_text)
                    wr_data["initial_text"] = cleaned_text if cleaned_text else None

        return wr_data
