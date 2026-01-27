import xml.etree.cElementTree as ET

from ..xmlcdata import CDATA


class TrueFalseBuilder:
    def generate_true_false(self, it, question_ident, question):
        self.itemetadata(it, "True/False", question)
        self.itemproc_extension(it)

        question_lid = question_ident + "_LID"
        question_ident_answer = question_ident + "_A"
        question_ident_feedback = question_ident + "_IF"

        it_pre = ET.SubElement(it, "presentation")
        it_pre_flow = ET.SubElement(it_pre, "flow")
        it_pre_flow_mat = ET.SubElement(it_pre_flow, "material")

        true_false = question.get_true_false()
        it_pre_flow_mat_text = ET.SubElement(it_pre_flow_mat, "mattext", {"texttype": "text/html"})
        question_text = question.text
        it_pre_flow_mat_text.append(CDATA(question_text))

        it_pre_flow_res = ET.SubElement(it_pre_flow, "response_extension")
        it_pre_flow_res_display_style = ET.SubElement(it_pre_flow_res, "d2l_2p0:display_style")
        it_pre_flow_res_display_style.text = "2"
        it_pre_flow_res_enumeration = ET.SubElement(it_pre_flow_res, "d2l_2p0:enumeration")
        it_pre_flow_res_enumeration.text = str(true_false.enumeration) if true_false.enumeration else "4"
        it_pre_flow_res_grading_type = ET.SubElement(it_pre_flow_res, "d2l_2p0:grading_type")
        it_pre_flow_res_grading_type.text = "0"

        it_pre_flow_lid = ET.SubElement(it_pre_flow, "response_lid", {"ident": question_lid, "rcardinality": "Single"})
        it_pre_flow_lid_render_choice = ET.SubElement(it_pre_flow_lid, "render_choice", {"shuffle": "no"})

        it_res = ET.SubElement(it, "resprocessing")

        if question.feedback:
            self.generate_feedback(it, question_ident, question.feedback)

        tf_index = 0
        answer_text = ["True", "False"]
        while tf_index < 2:
            flow = ET.SubElement(it_pre_flow_lid_render_choice, "flow_label", {"class": "Block"})
            response_label = ET.SubElement(flow, "response_label", {"ident": question_ident_answer + str(tf_index)})
            flow_mat = ET.SubElement(response_label, "flow_mat")
            material = ET.SubElement(flow_mat, "material")
            mattext = ET.SubElement(material, "mattext", {"texttype": "text/plain"})
            mattext.text = answer_text[tf_index]

            it_res_con = ET.SubElement(it_res, "respcondition", {"title": "Response Condition" + str(tf_index)})
            it_res_con_var = ET.SubElement(it_res_con, "conditionvar")
            it_res_con_var_equal = ET.SubElement(it_res_con_var, "varequal", {"respident": question_lid})
            it_res_con_var_equal.text = question_ident_answer + str(tf_index)
            it_res_set_var = ET.SubElement(it_res_con, "setvar", {"action": "Set"})

            if tf_index == 0:
                current_weight = true_false.true_weight
                current_feedback = true_false.true_feedback
            else:
                current_weight = true_false.false_weight
                current_feedback = true_false.false_feedback

            it_res_set_var.text = str(current_weight) if current_weight else "0.0000"
            ET.SubElement(
                it_res_con,
                "displayfeedback",
                {"feedbacktype": "Response", "linkrefid": question_ident_feedback + str(tf_index)},
            )

            if current_feedback:
                self.generate_feedback(it, question_ident_feedback + str(tf_index), current_feedback)
            tf_index += 1
