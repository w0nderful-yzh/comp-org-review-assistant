from __future__ import annotations

import pytest

from app.models.entities import Chapter
from app.schemas.api import AiQuestionDraftCreate
from app.services.ai_generation import AiGenerationError, extract_questions, normalize_question


def chapter() -> Chapter:
    return Chapter(id=1, title="概论", description=None, order_index=1, source_file="pytest")


def payload() -> AiQuestionDraftCreate:
    return AiQuestionDraftCreate(chapter_id=1, question_types=["multiple_choice"], difficulty="medium", count=1)


def test_extract_questions_accepts_plain_json_content() -> None:
    response = {
        "choices": [
            {
                "message": {
                    "content": '{"questions":[{"type":"true_false","stem":"CPU 只能执行机器指令。","answer":"TRUE"}]}'
                }
            }
        ]
    }

    assert extract_questions(response)[0]["type"] == "true_false"


def test_normalize_multiple_choice_accepts_comma_separated_answer() -> None:
    draft = normalize_question(
        {
            "type": "multiple_choice",
            "stem": "下列哪些会影响 CPU 执行时间？",
            "options": [
                {"key": "A", "text": "指令条数"},
                {"key": "B", "text": "CPI"},
                {"key": "C", "text": "主频"},
            ],
            "answer": "A, B",
            "explanation": "CPU 时间与指令条数、CPI、时钟周期有关。",
        },
        payload(),
        chapter(),
        [],
    )

    assert draft.answer_json == {"answer": ["A", "B"]}
    assert draft.options_json[0]["key"] == "A"


def test_normalize_fill_blank_handles_empty_acceptable_answers() -> None:
    draft = normalize_question(
        {
            "type": "fill_blank",
            "stem": "CPU 时间 = 指令条数 × （ ） × 时钟周期。",
            "blanks": [{"index": 1, "answer": "CPI", "acceptable_answers": None}],
        },
        AiQuestionDraftCreate(chapter_id=1, question_types=["fill_blank"], difficulty="medium", count=1),
        chapter(),
        [],
    )

    assert draft.answer_json == {"blanks": [{"index": 1, "answer": "CPI", "acceptable_answers": []}]}


def test_normalize_choice_rejects_answer_not_in_options() -> None:
    with pytest.raises(AiGenerationError):
        normalize_question(
            {
                "type": "single_choice",
                "stem": "下列哪项是正确的？",
                "options": [{"key": "A", "text": "正确"}, {"key": "B", "text": "错误"}],
                "answer": "C",
            },
            AiQuestionDraftCreate(chapter_id=1, question_types=["single_choice"], difficulty="medium", count=1),
            chapter(),
            [],
        )
