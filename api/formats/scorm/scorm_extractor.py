from api.models import (
    QuestionLibrary,
    Section,
    Question,
    MultipleChoice,
    MultipleChoiceAnswer,
    TrueFalse,
    Fib,
    MultipleSelect,
    MultipleSelectAnswer,
    Matching,
    MatchingChoice,
    MatchingAnswer,
    Ordering,
    WrittenResponse,
)

from .scorm_unzipper import extract_scorm_zip
from .scorm_parser import ScormParser


class ScormExtractor:
    """
    Import SCORM XML data into Django models.
    """

    def __init__(self, scorm_zip_path, extract_to_path=None):
        self.scorm_zip_path = scorm_zip_path
        self.extracted_path = extract_scorm_zip(scorm_zip_path, extract_to_path)
        self.parser = ScormParser(self.extracted_path)

    def parse_manifest(self):
        return self.parser.parse_manifest()

    def parse_questiondb(self):
        return self.parser.parse_questiondb()

    def populate_django_models(self, question_library=None):
        """
        Populate Django models from parsed SCORM XML data.

        Args:
            question_library: Optional existing QuestionLibrary instance to use.
                            If None, a new one will be created.

        Returns:
            QuestionLibrary: The QuestionLibrary instance with all sections and questions
        """
        question_library_data = self.parse_questiondb()

        main_title = ""
        if question_library_data["sections"]:
            main_title = question_library_data["sections"][0].get("title", "")

        if question_library is None:
            question_library = QuestionLibrary.objects.create(
                main_title=main_title,
                shuffle=False,
            )
        else:
            question_library.main_title = main_title
            question_library.save()

        section_order = 1
        question_index = 1
        for section_data in question_library_data["sections"]:
            has_nested_sections = len(section_data.get("sections", [])) > 0
            has_direct_questions = len(section_data.get("questions", [])) > 0
            has_text = section_data.get("text", "").strip() != ""
            should_set_main_text = (
                has_text
                # and section_data.get("is_text_displayed", False)
                and not question_library.main_text
            )
            if should_set_main_text:
                question_library.main_text = section_data.get("text", "")
                question_library.save(update_fields=["main_text"])

            if has_direct_questions or has_text:
                section = Section.objects.create(
                    question_library=question_library,
                    is_main_content=True,
                    order=section_order,
                    title=section_data.get("title", ""),
                    is_title_displayed=section_data.get("is_title_displayed", True),
                    text=section_data.get("text", ""),
                    is_text_displayed=section_data.get("is_text_displayed", False),
                    shuffle=section_data.get("shuffle", False),
                )

                for question_data in section_data.get("questions", []):
                    self._create_question_model(section, question_data, question_index)
                    question_index += 1

                for nested_section_data in section_data.get("sections", []):
                    nested_section = Section.objects.create(
                        question_library=question_library,
                        is_main_content=False,
                        order=section_order + 1,
                        title=nested_section_data.get("title", ""),
                        is_title_displayed=nested_section_data.get("is_title_displayed", True),
                        text=nested_section_data.get("text", ""),
                        is_text_displayed=nested_section_data.get("is_text_displayed", False),
                        shuffle=nested_section_data.get("shuffle", False),
                    )

                    for question_data in nested_section_data.get("questions", []):
                        self._create_question_model(nested_section, question_data, question_index)
                        question_index += 1

                    section_order += 1

                section_order += 1
            elif has_nested_sections:
                for nested_section_data in section_data.get("sections", []):
                    nested_section = Section.objects.create(
                        question_library=question_library,
                        is_main_content=False,
                        order=section_order,
                        title=nested_section_data.get("title", ""),
                        is_title_displayed=nested_section_data.get("is_title_displayed", True),
                        text=nested_section_data.get("text", ""),
                        is_text_displayed=nested_section_data.get("is_text_displayed", False),
                        shuffle=section_data.get("shuffle", False),
                    )

                    for question_data in nested_section_data.get("questions", []):
                        self._create_question_model(nested_section, question_data, question_index)
                        question_index += 1

                    section_order += 1

        return question_library

    def _create_question_model(self, section, question_data, index):
        question = Question.objects.create(
            section=section,
            index=index,
            title=question_data.get("title", ""),
            questiontype=question_data.get("question_type_code", ""),
            text=question_data.get("text", ""),
            points=question_data.get("points", 1.0),
            hint=question_data.get("hint"),
            feedback=question_data.get("feedback"),
        )

        question_type_code = question_data.get("question_type_code", "")
        specific_data = question_data.get("question_specific_data", {})

        if question_type_code == "MC":
            self._create_multiple_choice_model(question, specific_data)
        elif question_type_code == "TF":
            self._create_true_false_model(question, specific_data)
        elif question_type_code == "FIB":
            self._create_fib_model(question, specific_data)
        elif question_type_code == "MS":
            self._create_multiple_select_model(question, specific_data)
        elif question_type_code == "MAT":
            self._create_matching_model(question, specific_data)
        elif question_type_code == "ORD":
            self._create_ordering_model(question, specific_data)
        elif question_type_code == "WR":
            self._create_written_response_model(question, specific_data)

        return question

    def _create_multiple_choice_model(self, question, mc_data):
        mc = MultipleChoice.objects.create(
            question=question,
            randomize=mc_data.get("randomize", False),
            enumeration=mc_data.get("enumeration", 4),
        )

        for answer_data in mc_data.get("answers", []):
            MultipleChoiceAnswer.objects.create(
                multiple_choice=mc,
                order=answer_data.get("order", 1),
                answer=answer_data.get("answer", ""),
                answer_feedback=answer_data.get("answer_feedback"),
                weight=answer_data.get("weight", 0.0),
            )

    def _create_true_false_model(self, question, tf_data):
        TrueFalse.objects.create(
            question=question,
            true_weight=tf_data.get("true_weight", 0.0),
            true_feedback=tf_data.get("true_feedback"),
            false_weight=tf_data.get("false_weight", 0.0),
            false_feedback=tf_data.get("false_feedback"),
            enumeration=tf_data.get("enumeration", 4),
        )

    def _create_fib_model(self, question, fib_data):
        for fib_item in fib_data.get("fibs", []):
            Fib.objects.create(
                question=question,
                type=fib_item.get("type", "fibquestion"),
                text=fib_item.get("text", ""),
                order=fib_item.get("order", 1),
                size=fib_item.get("size"),
            )

    def _create_multiple_select_model(self, question, ms_data):
        ms = MultipleSelect.objects.create(
            question=question,
            randomize=ms_data.get("randomize", False),
            enumeration=ms_data.get("enumeration", 4),
            style=ms_data.get("style", 2),
            grading_type=ms_data.get("grading_type", 2),
        )

        for answer_data in ms_data.get("answers", []):
            MultipleSelectAnswer.objects.create(
                multiple_select=ms,
                order=answer_data.get("order", 1),
                answer=answer_data.get("answer", ""),
                answer_feedback=answer_data.get("answer_feedback"),
                is_correct=answer_data.get("is_correct", False),
            )

    def _create_matching_model(self, question, mat_data):
        matching = Matching.objects.create(
            question=question,
            grading_type=mat_data.get("grading_type", 0),
        )

        for choice_data in mat_data.get("choices", []):
            matching_choice = MatchingChoice.objects.create(
                matching=matching,
                choice_text=choice_data.get("choice_text", ""),
            )

            for answer_data in choice_data.get("matching_answers", []):
                MatchingAnswer.objects.create(
                    matching_choice=matching_choice,
                    answer_text=answer_data.get("answer_text", ""),
                )

    def _create_ordering_model(self, question, ord_data):
        for item_data in ord_data.get("items", []):
            Ordering.objects.create(
                question=question,
                text=item_data.get("text", ""),
                order=item_data.get("order", 1),
                ord_feedback=item_data.get("ord_feedback"),
            )

    def _create_written_response_model(self, question, wr_data):
        WrittenResponse.objects.create(
            question=question,
            enable_student_editor=wr_data.get("enable_student_editor", False),
            initial_text=wr_data.get("initial_text"),
            answer_key=wr_data.get("answer_key", ""),
            enable_attachments=wr_data.get("enable_attachments", False),
        )
