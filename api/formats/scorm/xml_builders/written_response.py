import xml.etree.cElementTree as ET

from ..xmlcdata import CDATA


class WrittenResponseBuilder:
    def generate_written_response(self, it, question_ident, question):
        self.itemetadata(it, "Long Answer", question)
        self.itemproc_extension(it)

        question_ident_str = question_ident + "_STR"
        question_ident_la = question_ident + "_LA"

        it_pre = ET.SubElement(it, "presentation")
        it_pre_flow = ET.SubElement(it_pre, "flow")

        written_response = question.get_written_response()

        it_pre_flow_mat = ET.SubElement(it_pre_flow, "material")
        it_pre_flow_mat_text = ET.SubElement(it_pre_flow_mat, "mattext", {"texttype": "text/html"})
        question_text = question.text
        it_pre_flow_mat_text.append(CDATA(question_text))

        it_pre_flow_mat_res_ext = ET.SubElement(it_pre_flow, "response_extension")
        it_pre_flow_mat_res_ext_sign = ET.SubElement(it_pre_flow_mat_res_ext, "d2l_2p0:has_signed_comments")
        it_pre_flow_mat_res_ext_sign.append(CDATA("no"))
        it_pre_flow_mat_res_ext_editor = ET.SubElement(it_pre_flow_mat_res_ext, "d2l_2p0:has_htmleditor")
        it_pre_flow_mat_res_ext_editor.append(CDATA("no"))

        it_pre_flow_mat_res_str = ET.SubElement(
            it_pre_flow, "response_str", {"rcardinality": "Multiple", "ident": question_ident_str}
        )
        it_pre_flow_mat_res_str_render = ET.SubElement(
            it_pre_flow_mat_res_str, "render_fib", {"fibtype": "String", "prompt": "Box", "columns": "100", "rows": "15"}
        )
        it_pre_flow_mat_res_str_render_label = ET.SubElement(
            it_pre_flow_mat_res_str_render, "response_label", {"ident": question_ident_la}
        )
        it_pre_flow_mat_res_str_render_label_mat = ET.SubElement(it_pre_flow_mat_res_str_render_label, "material")
        ET.SubElement(it_pre_flow_mat_res_str_render_label_mat, "mattext", {"texttype": "text/html"})

        if question.hint:
            self.generate_hint(it, question.hint)
        if question.feedback:
            self.generate_feedback(it, question_ident, question.feedback)
        it_init_text = ET.SubElement(it, "initial_text")
        it_init_text_mat = ET.SubElement(it_init_text, "initial_text_material")
        it_init_text_mat_flow = ET.SubElement(it_init_text_mat, "flow_mat")
        it_init_text_mat_flow_mat = ET.SubElement(it_init_text_mat_flow, "material")
        ET.SubElement(it_init_text_mat_flow_mat, "mattext", {"texttype": "text/html"})
        it_ans = ET.SubElement(it, "answer_key")
        it_ans_mat = ET.SubElement(it_ans, "answer_key_material")
        it_ans_mat_flow = ET.SubElement(it_ans_mat, "flow_mat")
        it_ans_mat_flow_mat = ET.SubElement(it_ans_mat_flow, "material")
        it_ans_mat_flow_mat_text = ET.SubElement(it_ans_mat_flow_mat, "mattext", {"texttype": "text/html"})
        it_ans_mat_flow_mat_text.append(CDATA(written_response.answer_key))
