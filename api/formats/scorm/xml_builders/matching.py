import copy
import xml.etree.cElementTree as ET

from ..xmlcdata import CDATA


class MatchingBuilder:
    def generate_matching(self, it, question_ident, question):
        self.itemetadata(it, "Matching", question)
        self.itemproc_extension(it)
        matching = question.get_matching()
        question_ident_choice = question_ident + "_C"
        question_ident_answer = question_ident + "_A"

        it_pre = ET.SubElement(it, "presentation")
        it_pre_flow = ET.SubElement(it_pre, "flow")

        if question.hint:
            self.generate_hint(it, question.hint)

        it_res = ET.SubElement(it, "resprocessing")
        it_res_out = ET.SubElement(it_res, "outcomes")
        ET.SubElement(it_res_out, "decvar", {"vartype": "Integer", "defaultval": "0", "varname": "D2L_Correct", "minvalue": "0", "maxvalue": "100"})
        ET.SubElement(it_res_out, "decvar", {"vartype": "Integer", "defaultval": "0", "varname": "D2L_Incorrect", "minvalue": "0", "maxvalue": "100"})
        ET.SubElement(it_res_out, "decvar", {"vartype": "Decimal", "defaultval": "0", "varname": "que_score", "minvalue": "0", "maxvalue": "100"})

        it_pre_flow_mat = ET.SubElement(it_pre_flow, "material")
        it_pre_flow_mat_text = ET.SubElement(it_pre_flow_mat, "mattext", {"texttype": "text/html"})
        question_text = question.text
        it_pre_flow_mat_text.append(CDATA(question_text))

        it_pre_flow_res = ET.SubElement(it_pre_flow, "response_extension")
        it_pre_flow_res_grading_type = ET.SubElement(it_pre_flow_res, "d2l_2p0:grading_type")
        it_pre_flow_res_grading_type.text = "2"

        it_pre_flow_res_grp_ren = ET.Element("render_choice", {"shuffle": "yes"})
        it_pre_flow_res_grp_ren_flow = ET.SubElement(it_pre_flow_res_grp_ren, "flow_label", {"class": "Block"})

        it_temp = ET.Element("temp")
        matching_answers = matching.get_unique_matching_answers()

        ma_index = 1
        for matching_answer_text in matching_answers:
            matching_answer_index = question_ident_answer + str(ma_index)
            it_grp_ren_flow_lab = ET.SubElement(it_pre_flow_res_grp_ren_flow, "response_label", {"ident": matching_answer_index})
            it_grp_ren_flow_lab_flow = ET.SubElement(it_grp_ren_flow_lab, "flow_mat")
            it_grp_ren_flow_lab_flow_mat = ET.SubElement(it_grp_ren_flow_lab_flow, "material")
            it_grp_ren_flow_lab_flow_mat_text = ET.SubElement(it_grp_ren_flow_lab_flow_mat, "mattext", {"texttype": "text/html"})
            it_grp_ren_flow_lab_flow_mat_text.append(CDATA(matching_answer_text))

            it_respcondition = ET.SubElement(it_temp, "respcondition")
            it_respcondition_conditionvar = ET.SubElement(it_respcondition, "conditionvar")
            it_respcondition_varequal = ET.SubElement(it_respcondition_conditionvar, "varequal")
            it_respcondition_varequal.text = matching_answer_index
            it_respcondition_setvar = ET.SubElement(it_respcondition, "setvar", {"action": "Add"})
            it_respcondition_setvar.text = "1"

            ma_index += 1

        mc_index = 1
        for matching_choice in matching.get_matching_choices():
            matching_choice_index = question_ident_choice + str(mc_index)

            it_pre_flow_res_grp = ET.SubElement(it_pre_flow, "response_grp", {"respident": matching_choice_index, "rcardinality": "Single"})
            it_pre_flow_res_grp_mat = ET.SubElement(it_pre_flow_res_grp, "material")
            it_pre_flow_res_grp_mattext = ET.SubElement(it_pre_flow_res_grp_mat, "mattext", {"texttype": "text/html"})
            it_pre_flow_res_grp_mattext.append(CDATA(matching_choice.choice_text))
            it_pre_flow_res_grp.append(it_pre_flow_res_grp_ren)

            for respcondition in it_temp:
                conditionvar = respcondition.find("conditionvar")
                varequal = conditionvar.find("varequal")
                varequal.set("respident", matching_choice_index)
                setvar = respcondition.find("setvar")
                answer_mattext = it_pre_flow.find(
                    "response_grp[@respident='" + matching_choice_index + "'].//response_label[@ident='" + varequal.text + "'].//mattext"
                )
                is_correct = matching_choice.has_matching_answer(answer_mattext[0].text)
                if is_correct is True:
                    setvar.set("varname", "D2L_Correct")
                else:
                    setvar.set("varname", "D2L_Incorrect")
                it_res.append(copy.deepcopy(respcondition))
            mc_index += 1

        match matching.grading_type:
            case 0:
                it_respcondition = ET.SubElement(it_res, "respcondition")
                it_respcondition_var = ET.SubElement(it_respcondition, "conditionvar")
                ET.SubElement(it_respcondition_var, "other")
                it_resp_setvar = ET.SubElement(it_respcondition, "setvar", {"varname": "que_score", "action": "Set"})
                it_resp_setvar.text = "D2L_Correct"
            case 1:
                it_respcondition = ET.SubElement(it_res, "respcondition")
                it_respcondition_var = ET.SubElement(it_respcondition, "conditionvar")
                it_respcondition_var_vargte = ET.SubElement(it_respcondition_var, "vargte", {"respident": "D2L_Incorrect"})
                it_respcondition_var_vargte.text = "0"
                it_resp_setvar = ET.SubElement(it_respcondition, "setvar", {"varname": "que_score", "action": "Set"})
                it_resp_setvar.text = "0"

                it_respcondition2 = copy.deepcopy(it_respcondition)
                it_resp_setvar2 = it_respcondition2.find("setvar")
                it_resp_setvar2.text = "1"
                it_res.append(it_respcondition2)
            case 2:
                it_respcondition = ET.SubElement(it_res, "respcondition")
                it_respcondition_var = ET.SubElement(it_respcondition, "conditionvar")
                it_respcondition_var_vargte = ET.SubElement(it_respcondition_var, "vargte", {"respident": "D2L_Incorrect"})
                it_respcondition_var_vargte.text = "D2L_Correct"
                it_resp_setvar = ET.SubElement(it_respcondition, "setvar", {"varname": "que_score", "action": "Set"})
                it_resp_setvar.text = "0"

                it_respcondition2 = ET.SubElement(it_res, "respcondition")
                it_respcondition_var2 = ET.SubElement(it_respcondition2, "conditionvar")
                ET.SubElement(it_respcondition_var2, "varlt", {"respident": "D2L_Incorrect"})
                it_resp_setvar2 = ET.SubElement(it_respcondition2, "setvar", {"varname": "que_score", "action": "Set"})
                it_resp_setvar2.text = "D2L_Correct"
                it_resp_setvar3 = ET.SubElement(it_respcondition2, "setvar", {"varname": "que_score", "action": "Subtract"})
                it_resp_setvar3.text = "D2L_Incorrect"

        if question.feedback:
            self.generate_feedback(it, question_ident, question.feedback)
