import re
from bs4 import BeautifulSoup


class ScormFormatter:
    """
    Format question library models into markdown and DOCX.
    """

    def _html_to_markdown(self, html_text):
        """
        Convert HTML text with base64 images to markdown format.
        Preserves ALL <img> tags as HTML. Converts MathML to TeX when possible.
        """
        if not html_text:
            return ""

        img_pattern = r"<img\s+[^>]*?>"

        html_images = {}
        image_counter = 0

        def preserve_img_tag(match):
            nonlocal image_counter
            full_img_tag = match.group(0)
            placeholder = f"__HTML_IMAGE_{image_counter}__"
            html_images[placeholder] = full_img_tag
            image_counter += 1
            return placeholder

        math_blocks = {}
        math_counter = 0
        math_pattern = r"<math[\s\S]*?</math>"

        def preserve_math(match):
            nonlocal math_counter
            full_math = match.group(0)
            placeholder = f"__MATH_BLOCK_{math_counter}__"
            tex_match = re.search(
                r'<annotation[^>]*encoding=["\']application/x-tex["\'][^>]*>(.*?)</annotation>',
                full_math,
                flags=re.IGNORECASE | re.DOTALL,
            )
            tex = tex_match.group(1) if tex_match else None
            math_blocks[placeholder] = {"tex": tex, "raw": full_math}
            math_counter += 1
            return placeholder

        result = re.sub(img_pattern, preserve_img_tag, html_text)
        result = re.sub(math_pattern, preserve_math, result, flags=re.IGNORECASE)

        result = re.sub(r"</p>", "\n", result, flags=re.IGNORECASE)
        result = re.sub(r"<p[^>]*>", "\n", result, flags=re.IGNORECASE)

        try:
            soup = BeautifulSoup(result, "html.parser")
            for br in soup.find_all("br"):
                br.replace_with("[[[BR]]]")
            text = soup.get_text(separator=" ", strip=False)
            text = text.replace("[[[BR]]]", "\n")
        except Exception:
            text = re.sub(r"<(?!/?__HTML_IMAGE_)[^>]+>", "", result)

        for placeholder, math_info in math_blocks.items():
            replacement = None
            if math_info.get("tex"):
                tex = math_info["tex"].strip()
                replacement = f"$$ {tex} $$"
            else:
                replacement = math_info.get("raw", "")
            text = text.replace(placeholder, replacement)
        for placeholder, html_img in html_images.items():
            text = text.replace(placeholder, html_img)

        text = text.replace("\r", "")
        text = re.sub(r"\n{3,}", "\n\n", text)
        normalized_lines = []
        for line in text.split("\n"):
            stripped = line.strip()
            if stripped == "":
                normalized_lines.append("")
                continue
            if (
                re.search(r"<img[^>]*>", stripped, flags=re.IGNORECASE)
                or re.search(r"<math", stripped, flags=re.IGNORECASE)
                or "$$" in stripped
            ):
                normalized_lines.append(stripped)
            else:
                normalized_lines.append(" ".join(stripped.split()))
        text = "\n".join(normalized_lines).strip()

        return text

    def _strip_block_tags(self, html_text):
        """
        Remove block-level HTML tags while preserving inline styling tags.
        """
        if not html_text:
            return ""

        try:
            soup = BeautifulSoup(html_text, "html.parser")

            block_tags = ["p", "div", "br", "h1", "h2", "h3", "h4", "h5", "h6", "li", "ul", "ol"]
            for tag_name in block_tags:
                for tag in soup.find_all(tag_name):
                    tag.unwrap()

            result = str(soup)
            result = re.sub(r">\s+<", "><", result)
            result = re.sub(r"\s+", " ", result)
            result = result.strip()
            return result
        except Exception:
            cleaned = re.sub(r">\s+<", "><", html_text)
            cleaned = re.sub(r"\s+", " ", cleaned).strip()
            return cleaned

    def format_to_markdown(self, question_library):
        """
        Format parsed questions from Django models into markdown/text format.
        """
        lines = []

        if question_library.main_title:
            main_title = question_library.main_title
            try:
                soup = BeautifulSoup(main_title, "html.parser")
                main_title = soup.get_text(separator=" ", strip=True)
            except Exception:
                main_title = re.sub(r"\s+", " ", main_title).strip()
            lines.append(f"# {main_title}")
            lines.append("")

        if getattr(question_library, "main_text", None):
            main_text = self._html_to_markdown(question_library.main_text)
            lines.append(main_text)
            lines.append("")

        sections = question_library.get_sections()
        for section in sections:
            if not section.is_main_content:
                if section.title and section.is_title_displayed:
                    section_title_display = section.title
                    try:
                        soup = BeautifulSoup(section_title_display, "html.parser")
                        section_title_display = soup.get_text(separator=" ", strip=True)
                    except Exception:
                        section_title_display = re.sub(r"\s+", " ", section_title_display).strip()
                    lines.append("")
                    lines.append("<br>")
                    lines.append("#section")
                    lines.append(f"## {section_title_display}")

            should_display_text = False
            if section.is_main_content:
                should_display_text = section.text and section.is_text_displayed
            else:
                should_display_text = bool(section.text)

            if should_display_text:
                section_text = self._html_to_markdown(section.text)
                lines.append(section_text)

            questions = section.get_questions()
            for idx, question in enumerate(questions):
                question_markdown = self._format_question_to_markdown(question)
                lines.append(question_markdown)

                if not section.is_main_content and idx == len(questions) - 1:
                    lines.append("")
                    lines.append("<br>")
                    lines.append("/section")

            if not section.is_main_content and len(questions) == 0:
                lines.append("")
                lines.append("<br>")
                lines.append("/section")

        result = "\n".join(lines)
        if result and not result.endswith("\n"):
            result += "\n"
        return result

    def _format_question_to_markdown(self, question):
        """
        Format a single question to markdown format matching raw_content format.
        """
        lines = []

        if question.questiontype:
            lines.append("")
            lines.append("<br>")
            lines.append(f"Type: {question.questiontype}")
        if question.title:
            lines.append(f"Title: {question.title}")
        if question.points:
            normalized_points = str(float(question.points)).rstrip("0").rstrip(".")
            lines.append(f"Points: {normalized_points}")

        randomize_value = None
        if question.questiontype == "MC":
            mc = question.get_multiple_choice()
            if mc and mc.randomize is not None:
                randomize_value = mc.randomize
        elif question.questiontype == "MS":
            ms = question.get_multiple_select()
            if ms and ms.randomize is not None:
                randomize_value = ms.randomize
        if randomize_value is True:
            lines.append("Randomize: yes")

        if question.text and question.questiontype != "FIB":
            question_text = self._html_to_markdown(question.text)
            plain_text = re.sub(r"!\[.*?\]\([^)]+\)", "", question_text)
            plain_text = re.sub(r"<[^>]+>", "", plain_text)
            plain_text = re.sub(r"\s+", " ", plain_text).strip()

            question_number = None
            if question.index is not None:
                question_number = question.index
            elif question.number_provided is not None:
                question_number = question.number_provided

            if question_number is not None:
                lines.append(f"{question_number}. {question_text}")
            else:
                lines.append(question_text)

        question_type = question.questiontype
        if question_type == "MC":
            answer_text = self._format_multiple_choice_markdown(question)
            if answer_text:
                lines.append(answer_text)
        elif question_type == "TF":
            answer_text = self._format_true_false_markdown(question)
            if answer_text:
                lines.append(answer_text)
        elif question_type == "FIB":
            answer_text = self._format_fib_markdown(question)
            if answer_text:
                question_number = None
                if question.index is not None:
                    question_number = question.index
                elif question.number_provided is not None:
                    question_number = question.number_provided

                if question_number is not None:
                    lines.append(f"{question_number}. {answer_text}")
                else:
                    lines.append(answer_text)
        elif question_type == "MS":
            answer_text = self._format_multi_select_markdown(question)
            if answer_text:
                lines.append(answer_text)
        elif question_type == "MAT":
            answer_text = self._format_matching_markdown(question)
            if answer_text:
                lines.append(answer_text)
        elif question_type == "ORD":
            answer_text = self._format_ordering_markdown(question)
            if answer_text:
                lines.append(answer_text)
        elif question_type == "WR":
            answer_text = self._format_written_response_markdown(question)
            if answer_text:
                lines.append(answer_text)

        if question.hint:
            hint_text = self._html_to_markdown(question.hint)
            lines.append(f"@Hint: {hint_text}")

        if question.feedback:
            feedback_text = self._html_to_markdown(question.feedback)
            lines.append(f"@Feedback: {feedback_text}")

        return "\n\n".join(lines)

    def _format_multiple_choice_markdown(self, question):
        lines = []
        mc = question.get_multiple_choice()
        if mc:
            answers = mc.get_multiple_choice_answers()
            for idx, answer in enumerate(answers, start=1):
                letter = chr(96 + idx)
                marker = "*" if answer.weight and answer.weight > 0 else ""
                answer_text = self._html_to_markdown(answer.answer)
                lines.append(f"    {letter}. {marker}{answer_text}")
                if answer.answer_feedback:
                    feedback_text = self._html_to_markdown(answer.answer_feedback)
                    lines.append(f"    @Feedback: {feedback_text}")
        return "\n".join(lines)

    def _format_true_false_markdown(self, question):
        lines = []
        tf = question.get_true_false()
        if tf:
            true_marker = "*" if tf.true_weight and tf.true_weight > 0 else ""
            false_marker = "*" if tf.false_weight and tf.false_weight > 0 else ""
            lines.append(f"    a. {true_marker}True")
            if tf.true_feedback:
                feedback_text = self._html_to_markdown(tf.true_feedback)
                lines.append(f"    @Feedback: {feedback_text}")
            lines.append(f"    b. {false_marker}False")
            if tf.false_feedback:
                feedback_text = self._html_to_markdown(tf.false_feedback)
                lines.append(f"    @Feedback: {feedback_text}")
        return "\n".join(lines)

    def _format_fib_markdown(self, question):
        lines = []
        fibs = question.get_fibs()
        current_text = ""
        for fib in fibs:
            if fib.type == "fibquestion":
                if fib.text:
                    cleaned_text = self._html_to_markdown(fib.text)
                    current_text += cleaned_text
            elif fib.type == "fibanswer":
                if fib.text:
                    current_text += f" [{fib.text}]"
                else:
                    current_text += " [ ]"
        if current_text:
            lines.append(current_text)
        return "\n".join(lines)

    def _format_multi_select_markdown(self, question):
        lines = []
        ms = question.get_multiple_select()
        if ms:
            answers = ms.get_multiple_select_answers()
            for idx, answer in enumerate(answers, start=1):
                letter = chr(96 + idx)
                marker = "*" if answer.is_correct else ""
                answer_text = self._html_to_markdown(answer.answer)
                lines.append(f"    {letter}. {marker}{answer_text}")
                if answer.answer_feedback:
                    feedback_text = self._html_to_markdown(answer.answer_feedback)
                    lines.append(f"    @Feedback: {feedback_text}")
        return "\n".join(lines)

    def _format_matching_markdown(self, question):
        lines = []
        matching = question.get_matching()
        if matching:
            choices = matching.get_matching_choices()
            for idx, choice in enumerate(choices, start=1):
                letter = chr(96 + idx)
                choice_text = self._html_to_markdown(choice.choice_text)

                answers = choice.matching_answers.all()
                if answers:
                    answer = answers[0]
                    answer_text = self._html_to_markdown(answer.answer_text)
                    lines.append(f"    {letter}. {choice_text} = {answer_text}")
                else:
                    lines.append(f"    {letter}. {choice_text} =")
        return "\n".join(lines)

    def _format_ordering_markdown(self, question):
        lines = []
        orderings = question.get_orderings()
        for idx, ordering in enumerate(orderings, start=1):
            letter = chr(96 + idx)
            ordering_text = self._html_to_markdown(ordering.text)
            lines.append(f"    {letter}. {ordering_text}")
            if ordering.ord_feedback:
                feedback_text = self._html_to_markdown(ordering.ord_feedback)
                lines.append(f"    @Feedback: {feedback_text}")
        return "\n".join(lines)

    def _format_written_response_markdown(self, question):
        lines = []
        wr = question.get_written_response()
        if wr and wr.answer_key:
            lines.append("")
            answer_text = self._html_to_markdown(wr.answer_key)
            lines.append("Correct Answer:")
            lines.append(f"{answer_text}")
        return "\n\n".join(lines)

    def convert_markdown_to_docx(self, markdown_text, output_path):
        """
        Convert markdown text to DOCX file using pandoc.
        """
        import pypandoc
        import tempfile
        import os

        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False, encoding="utf-8") as temp_md:
            temp_md.write(markdown_text)
            temp_md_path = temp_md.name

        try:
            pypandoc.convert_file(
                temp_md_path,
                format="markdown_github+fancy_lists+emoji+hard_line_breaks+all_symbols_escapable+escaped_line_breaks+pipe_tables+startnum+tex_math_dollars",
                to="docx+empty_paragraphs",
                outputfile=output_path,
                extra_args=[
                    "--no-highlight",
                    "--preserve-tabs",
                    "--wrap=preserve",
                    "--indent=false",
                    "--mathml",
                    "--ascii",
                ],
            )
        finally:
            if os.path.exists(temp_md_path):
                os.unlink(temp_md_path)

        return output_path
