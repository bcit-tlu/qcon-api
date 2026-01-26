from .xml_builders import (
    BaseQuestionBuilder,
    MultipleChoiceBuilder,
    TrueFalseBuilder,
    FillInTheBlanksBuilder,
    MultiSelectBuilder,
    MatchingBuilder,
    OrderingBuilder,
    WrittenResponseBuilder,
)


class ScormQuestionBuilder(
    BaseQuestionBuilder,
    MultipleChoiceBuilder,
    TrueFalseBuilder,
    FillInTheBlanksBuilder,
    MultiSelectBuilder,
    MatchingBuilder,
    OrderingBuilder,
    WrittenResponseBuilder,
):
    pass
