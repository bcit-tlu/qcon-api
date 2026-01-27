import xml.etree.cElementTree as ET

from ..xmlcdata import CDATA


class FillInTheBlanksBuilder:
    def generate_fill_in_the_blanks(self, it, question_ident, question):
        self.itemetadata(it, "Fill in the Blanks", question)
        self.itemproc_extension(it)

        it_pre = ET.SubElement(it, "presentation")
        it_pre_flow = ET.SubElement(it_pre, "flow")

        idx = 1
        for fib in question.get_fibs():
            question_str = question_ident + str(idx) + "_STR"
            question_ans = question_ident + str(idx) + "_ANS"
            if fib.type == "fibanswer":
                it_pre_flow_str = ET.SubElement(
                    it_pre_flow, "response_str", {"rcardinality": "Single", "ident": question_str}
                )
                it_pre_flow_str_render = ET.SubElement(
                    it_pre_flow_str,
                    "render_fib",
                    {"fibtype": "String", "prompt": "Box", "columns": "30", "rows": "1"},
                )
                ET.SubElement(it_pre_flow_str_render, "response_label", {"ident": question_ans})
                idx += 1
            elif fib.type == "fibquestion":
                it_pre_flow_mat = ET.SubElement(it_pre_flow, "material")
                it_pre_flow_mat_text = ET.SubElement(it_pre_flow_mat, "mattext", {"texttype": "text/html"})
                question_text = fib.text
                it_pre_flow_mat_text.append(CDATA(question_text))

        if question.hint:
            self.generate_hint(it, question.hint)

        it_res = ET.SubElement(it, "resprocessing")
        it_out = ET.SubElement(it_res, "outcomes")

        index = 1
        fib_answers_qs = list(question.get_fib_answers() or [])
        if not fib_answers_qs:
            return
        answer_weight = str(100.0 / len(fib_answers_qs))
        for fib_answers in fib_answers_qs:
            if not fib_answers.text:
                index += 1
                continue
            answers = [a.strip() for a in fib_answers.text.split(",") if a.strip()]
            question_ans = question_ident + str(index) + "_ANS"
            for answer in answers:
                it_res_con = ET.SubElement(it_res, "respcondition")
                it_res_con_var = ET.SubElement(it_res_con, "conditionvar")
                it_res_con_var_equal = ET.SubElement(
                    it_res_con_var, "varequal", {"case": "no", "respident": question_ans}
                )
                it_res_con_var_equal.text = answer
                it_res_set_var = ET.SubElement(it_res_con, "setvar", {"action": "Set"})
                it_res_set_var.text = answer_weight

            ET.SubElement(
                it_out,
                "decvar",
                {"varname": "Blank_" + str(index), "maxvalue": "100", "minvalue": "0", "vartype": "Integer"},
            )

            index += 1

        if question.feedback:
            self.generate_feedback(it, question_ident, question.feedback)
