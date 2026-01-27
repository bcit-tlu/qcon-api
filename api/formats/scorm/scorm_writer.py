import datetime
import random
import time
import xml.etree.cElementTree as ET
from uuid import UUID
from xml.dom.minidom import parseString

from .scorm_question_builder import ScormQuestionBuilder
from .xmlcdata import CDATA


class ScormWriter(ScormQuestionBuilder):
    def __init__(self, question_library):
        ident = datetime.datetime.now().strftime("%Y%m%d%H%M%S%f")
        questionLibraryIdent = "QLIB_" + ident
        root_el = ET.Element(
            "questestinterop",
            {"xmlns:d2l_2p0": "http://desire2learn.com/xsd/d2lcp_v2p0"},
        )
        objectbank_el = ET.SubElement(
            root_el,
            "objectbank",
            {"ident": questionLibraryIdent, "xmlns:d2l_2p0": "http://desire2learn.com/xsd/d2lcp_v2p0"},
        )

        base_ident = "SECT_" + str(datetime.datetime.now().strftime("%Y%m%d%H%M%S")) + str(
            int(UUID(int=0x12345678123456781234567812345678))
        )
        base_section_el = ET.SubElement(
            objectbank_el,
            "section",
            {"ident": base_ident, "title": self._safe_attr(question_library.main_title)},
        )
        if question_library.shuffle is True:
            self.create_section_shuffle(base_section_el)

        self.create_presentation_material(base_section_el, question_library.main_text)

        sec_proc = ET.SubElement(base_section_el, "sectionproc_extension")
        sec_proc_dis_name = ET.SubElement(sec_proc, "d2l_2p0:display_section_name")
        sec_proc_dis_name.text = "yes"
        sec_proc_dis_line = ET.SubElement(sec_proc, "d2l_2p0:display_section_line")
        sec_proc_dis_line.text = "no"
        sec_proc_dis_sec = ET.SubElement(sec_proc, "d2l_2p0:type_display_section")
        sec_proc_dis_sec.text = "0"

        section_objs = question_library.get_sections()
        for section_obj in section_objs:
            if section_obj.is_main_content is True:
                root_question_objs = section_obj.get_questions()
                self.create_questions(base_section_el, root_question_objs)
            else:
                current_section_el = self.create_section(base_section_el, section_obj)
                question_objs = section_obj.get_questions()
                self.create_questions(current_section_el, question_objs)
        self.questiondb_string = self.xml_to_string(root_el)

    def _safe_attr(self, value):
        return "" if value is None else str(value)

    def create_section(self, parent_el, section_obj):
        sectionIdent = "SECT_" + str(datetime.datetime.now().strftime("%Y%m%d%H%M%S")) + str(
            int(UUID(int=0x12345678123456781234567812345678))
        )
        section_el = ET.SubElement(
            parent_el,
            "section",
            {"ident": sectionIdent, "title": self._safe_attr(section_obj.title)},
        )
        if section_obj.shuffle is True:
            self.create_section_shuffle(section_el)

        self.create_presentation_material(section_el, section_obj.text)
        self.create_sectionproc_extension(section_el, section_obj)

        return section_el

    def create_section_shuffle(self, section_el):
        sel_ord = ET.SubElement(section_el, "selection_ordering")
        sel_ord_ord = ET.SubElement(sel_ord, "order", {"order_type": "Random"})

    def create_presentation_material(self, section_el, section_text):
        sec_pres_mat = ET.SubElement(section_el, "presentation_material")
        sec_pres_mat_flo = ET.SubElement(sec_pres_mat, "flow_mat")
        sec_pres_mat_flo_flo = ET.SubElement(sec_pres_mat_flo, "flow_mat")
        sec_pres_mat_flo_flo_mat = ET.SubElement(sec_pres_mat_flo_flo, "material")
        sec_pres_mat_flo_flo_mat_text = ET.SubElement(sec_pres_mat_flo_flo_mat, "mattext", {"texttype": "text/html"})
        if section_text:
            sec_pres_mat_flo_flo_mat_text.append(CDATA(section_text))

    def create_sectionproc_extension(self, section_el, section_obj):
        sec_proc = ET.SubElement(section_el, "sectionproc_extension")
        sec_proc_dis_name = ET.SubElement(sec_proc, "d2l_2p0:display_section_name")
        sec_proc_dis_name.text = "yes" if section_obj.is_title_displayed in (None, True) else "no"
        sec_proc_dis_line = ET.SubElement(sec_proc, "d2l_2p0:display_section_line")
        sec_proc_dis_line.text = "no"
        sec_proc_dis_sec = ET.SubElement(sec_proc, "d2l_2p0:type_display_section")
        if section_obj.is_text_displayed is None:
            sec_proc_dis_sec.text = "0"
        else:
            sec_proc_dis_sec.text = "1" if section_obj.is_text_displayed else "0"

    def create_questions(self, section_el, question_objs):
        for question in question_objs:
            time_ns = str(time.process_time_ns())
            random_int = str(random.randint(1000000, 9999999))
            ident = time_ns + random_int
            question_ident = "QUES_" + ident
            item_el = ET.Element(
                "item",
                {
                    "ident": "OBJ_" + ident,
                    "label": question_ident,
                    "d2l_2p0:page": "1",
                    "title": self._safe_attr(question.title),
                },
            )
            question_type = question.questiontype
            match question_type:
                case "MC":
                    self.generate_multiple_choice(item_el, question_ident, question)
                case "TF":
                    self.generate_true_false(item_el, question_ident, question)
                case "FIB" | "FMB":
                    self.generate_fill_in_the_blanks(item_el, question_ident, question)
                case "MS" | "MR":
                    self.generate_multi_select(item_el, question_ident, question)
                case "MAT" | "MT":
                    self.generate_matching(item_el, question_ident, question)
                case "ORD":
                    self.generate_ordering(item_el, question_ident, question)
                case "WR" | "E":
                    self.generate_written_response(item_el, question_ident, question)

            section_el.append(item_el)

    def xml_to_string(self, xml):
        rough_string = ET.tostring(xml, "utf-8")
        reparsed = parseString(rough_string)
        pretty_xml = reparsed.toprettyxml(indent="\t")
        return pretty_xml
