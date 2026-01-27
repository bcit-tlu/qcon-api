import xml.etree.cElementTree as ET

from ..xmlcdata import CDATA


class MultipleChoiceBuilder:
    def generate_multiple_choice(self, it, question_ident, question):
        self.itemetadata(it, "Multiple Choice", question)
        self.itemproc_extension(it)
        question_lid = question_ident + "_LID"
        question_ident_answer = question_ident + "_A"
        question_ident_feedback = question_ident + "_IF"

        it_pre = ET.SubElement(it, "presentation")
        it_pre_flow = ET.SubElement(it_pre, "flow")
        it_pre_flow_mat = ET.SubElement(it_pre_flow, "material")

        multiple_choice = question.get_multiple_choice()
        it_pre_flow_mat_text = ET.SubElement(it_pre_flow_mat, "mattext", {"texttype": "text/html"})
        question_text = question.text
        it_pre_flow_mat_text.append(CDATA(question_text))

        it_pre_flow_res = ET.SubElement(it_pre_flow, "response_extension")
        it_pre_flow_res_display_style = ET.SubElement(it_pre_flow_res, "d2l_2p0:display_style")
        it_pre_flow_res_display_style.text = "2"
        it_pre_flow_res_enumeration = ET.SubElement(it_pre_flow_res, "d2l_2p0:enumeration")
        it_pre_flow_res_enumeration.text = str(multiple_choice.enumeration) if multiple_choice.enumeration else "4"
        it_pre_flow_res_grading_type = ET.SubElement(it_pre_flow_res, "d2l_2p0:grading_type")
        it_pre_flow_res_grading_type.text = "0"
        it_pre_flow_lid = ET.SubElement(it_pre_flow, "response_lid", {"ident": question_lid, "rcardinality": "Multiple"})
        it_pre_flow_lid_render_choice = ET.SubElement(
            it_pre_flow_lid, "render_choice", {"shuffle": ("yes" if multiple_choice.randomize else "no")}
        )

        if question.hint:
            self.generate_hint(it, question.hint)

        it_res = ET.SubElement(it, "resprocessing")

        if question.feedback:
            self.generate_feedback(it, question_ident, question.feedback)

        mc_answer_index = 1
        for mc_answer in multiple_choice.get_multiple_choice_answers():
            flow = ET.SubElement(it_pre_flow_lid_render_choice, "flow_label", {"class": "Block"})
            response_label = ET.SubElement(flow, "response_label", {"ident": question_ident_answer + str(mc_answer_index)})
            flow_mat = ET.SubElement(response_label, "flow_mat")
            material = ET.SubElement(flow_mat, "material")
            mattext = ET.SubElement(material, "mattext", {"texttype": "text/html"})
            mattext.append(CDATA(mc_answer.answer))

            it_res_con = ET.SubElement(it_res, "respcondition", {"title": "Response Condition" + str(mc_answer_index)})
            it_res_con_var = ET.SubElement(it_res_con, "conditionvar")
            it_res_con_var_equal = ET.SubElement(it_res_con_var, "varequal", {"respident": question_lid})
            it_res_con_var_equal.text = question_ident_answer + str(mc_answer_index)
            it_res_set_var = ET.SubElement(it_res_con, "setvar", {"action": "Set"})
            it_res_set_var.text = str(mc_answer.weight) if mc_answer.weight else "0.0000"
            ET.SubElement(
                it_res_con,
                "displayfeedback",
                {"feedbacktype": "Response", "linkrefid": question_ident_feedback + str(mc_answer_index)},
            )

            if mc_answer.answer_feedback:
                self.generate_feedback(it, question_ident_feedback + str(mc_answer_index), mc_answer.answer_feedback)
            mc_answer_index += 1
