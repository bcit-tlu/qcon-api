import xml.etree.cElementTree as ET

from ..xmlcdata import CDATA


class OrderingBuilder:
    def generate_ordering(self, it, question_ident, question):
        self.itemetadata(it, "Ordering", question)
        self.itemproc_extension(it)

        question_o = question_ident + "_O"
        question_ident_feedback = question_ident + "_IF"

        it_pre = ET.SubElement(it, "presentation")
        it_pre_flow = ET.SubElement(it_pre, "flow")

        it_pre_flow_mat = ET.SubElement(it_pre_flow, "material")
        it_pre_flow_mat_text = ET.SubElement(it_pre_flow_mat, "mattext", {"texttype": "text/html"})
        question_text = question.text
        it_pre_flow_mat_text.append(CDATA(question_text))

        it_pre_flow_res_ext = ET.SubElement(it_pre_flow, "response_extension")
        it_pre_flow_res_ext_grading = ET.SubElement(it_pre_flow_res_ext, "d2l_2p0:grading_type")
        grading_type = 2
        it_pre_flow_res_ext_grading.append(CDATA(grading_type))

        it_pre_flow_res_grp = ET.SubElement(it_pre_flow, "response_grp", {"ident": question_o, "rcardinality": "Ordered"})
        it_pre_flow_res_grp_render = ET.SubElement(it_pre_flow_res_grp, "render_choice", {"shuffle": "yes"})
        it_pre_flow_res_grp_render_flow = ET.SubElement(it_pre_flow_res_grp_render, "flow_label", {"class": "Block"})

        if question.hint:
            self.generate_hint(it, question.hint)

        it_res = ET.SubElement(it, "resprocessing")
        it_out = ET.SubElement(it_res, "outcomes")
        ET.SubElement(it_out, "decvar", {"maxvalue": "100", "minvalue": "0", "varname": "D2L_Correct", "defaultval": "0", "vartype": "Integer"})
        ET.SubElement(it_out, "decvar", {"minvalue": "0", "varname": "D2L_Incorrect", "defaultval": "0", "vartype": "Integer"})
        ET.SubElement(it_out, "decvar", {"minvalue": "0", "varname": "que_score", "defaultval": "0", "vartype": "Integer"})

        it_res_con_other = ET.SubElement(it_res, "respcondition")
        it_res_con_other_var = ET.SubElement(it_res_con_other, "conditionvar")
        ET.SubElement(it_res_con_other_var, "other")
        it_res_con_other_setvar = ET.SubElement(it_res_con_other, "setvar", {"varname": "que_score", "action": "Set"})
        it_res_con_other_setvar.text = "D2L_Correct"

        if question.feedback:
            self.generate_feedback(it, question_ident, question.feedback)

        ord_index = 1
        for ord in question.get_orderings():
            ident_num = question_o + str(ord_index)
            it_pre_flow_res_grp_render_flow_res = ET.SubElement(
                it_pre_flow_res_grp_render_flow, "response_label", {"ident": ident_num}
            )
            it_pre_flow_res_grp_render_flow_res_flow = ET.SubElement(it_pre_flow_res_grp_render_flow_res, "flow_mat")
            it_pre_flow_res_grp_render_flow_res_flow_mat = ET.SubElement(
                it_pre_flow_res_grp_render_flow_res_flow, "material"
            )
            it_pre_flow_res_grp_render_flow_res_flow_mat_text = ET.SubElement(
                it_pre_flow_res_grp_render_flow_res_flow_mat, "mattext", {"texttype": "text/html"}
            )
            question_text = ord.text
            it_pre_flow_res_grp_render_flow_res_flow_mat_text.append(CDATA(question_text))

            it_res_con_correct = ET.SubElement(it_res, "respcondition", {"title": "Correct Condition"})
            it_res_con_correct_var = ET.SubElement(it_res_con_correct, "conditionvar")
            it_res_con_correct_var_equal = ET.SubElement(it_res_con_correct_var, "varequal", {"respident": ident_num})
            it_res_con_correct_var_equal.text = str(ord_index)
            it_res_con_correct_setvar = ET.SubElement(it_res_con_correct, "setvar", {"varname": "D2L_Correct", "action": "Add"})
            it_res_con_correct_setvar.text = str(1)

            it_res_con_incorrect = ET.SubElement(it_res, "respcondition", {"title": "Incorrect Condition"})
            it_res_con_incorrect_var = ET.SubElement(it_res_con_incorrect, "conditionvar")
            it_res_con_incorrect_var_not = ET.SubElement(it_res_con_incorrect_var, "not")
            it_res_con_incorrect_var_not_equal = ET.SubElement(
                it_res_con_incorrect_var_not, "varequal", {"respident": ident_num}
            )
            it_res_con_incorrect_var_not_equal.text = str(ord_index)
            it_res_con_incorrect_setvar = ET.SubElement(
                it_res_con_incorrect, "setvar", {"varname": "D2L_Incorrect", "action": "Add"}
            )
            it_res_con_incorrect_setvar.text = str(1)

            if ord.ord_feedback:
                self.generate_feedback(it, question_ident_feedback + str(ord_index), ord.ord_feedback)
            ord_index += 1
