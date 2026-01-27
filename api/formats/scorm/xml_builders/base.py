import xml.etree.cElementTree as ET
from xml.dom.minidom import parseString

from ..xmlcdata import CDATA


class BaseQuestionBuilder:
    def itemetadata(self, it, question_type, question):
        it_metadata = ET.SubElement(it, "itemmetadata")
        it_metadata_qtidata = ET.SubElement(it_metadata, "qtimetadata")
        it_computer_scored = ET.SubElement(it_metadata_qtidata, "qti_metadatafield")
        it_computer_scored_label = ET.SubElement(it_computer_scored, "fieldlabel")
        it_computer_scored_label.text = "qmd_computerscored"
        it_computer_scored_entry = ET.SubElement(it_computer_scored, "fieldentry")
        it_computer_scored_entry.text = "yes"
        it_question_type = ET.SubElement(it_metadata_qtidata, "qti_metadatafield")
        it_question_type_label = ET.SubElement(it_question_type, "fieldlabel")
        it_question_type_label.text = "qmd_questiontype"
        it_question_type_entry = ET.SubElement(it_question_type, "fieldentry")
        it_question_type_entry.text = question_type
        it_weighting = ET.SubElement(it_metadata_qtidata, "qti_metadatafield")
        it_weighting_label = ET.SubElement(it_weighting, "fieldlabel")
        it_weighting_label.text = "qmd_weighting"
        it_weighting_entry = ET.SubElement(it_weighting, "fieldentry")
        points = question.points if question.points is not None else 1
        it_weighting_entry.text = "{:.4f}".format(points)

    def itemproc_extension(self, it):
        it_proc = ET.SubElement(it, "itemproc_extension")
        it_proc_difficulty = ET.SubElement(it_proc, "d2l_2p0:difficulty")
        it_proc_difficulty.text = "1"
        it_proc_isbonus = ET.SubElement(it_proc, "d2l_2p0:isbonus")
        it_proc_isbonus.text = "no"
        it_proc_ismandatory = ET.SubElement(it_proc, "d2l_2p0:ismandatory")
        it_proc_ismandatory.text = "no"

    def generate_feedback(self, it, ident, feedback):
        it_fb = ET.SubElement(it, "itemfeedback", {"ident": ident})
        it_fb_mat = ET.SubElement(it_fb, "material")
        it_fb_mat_text = ET.SubElement(it_fb_mat, "mattext", {"texttype": "text/html"})
        it_fb_mat_text.append(CDATA(feedback))

    def generate_hint(self, it, hint):
        it_hint = ET.SubElement(it, "hint")
        it_hint_mat = ET.SubElement(it_hint, "hintmaterial")
        it_hint_mat_flow = ET.SubElement(it_hint_mat, "flow_mat")
        it_hint_mat_flow_mat = ET.SubElement(it_hint_mat_flow, "material")
        it_hint_mat_flow_text = ET.SubElement(
            it_hint_mat_flow_mat, "mattext", {"texttype": "text/html"}
        )
        it_hint_mat_flow_text.append(CDATA(hint))

    def xml_to_string(self, xml):
        rough_string = ET.tostring(xml, "utf-8")
        reparsed = parseString(rough_string)
        pretty_xml = reparsed.toprettyxml(indent="\t")
        return pretty_xml
