from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel, Field


QuestionType = Literal[
    "single_choice",
    "multiple_choice",
    "true_false",
    "fill_blank",
    "short_answer",
    "calculation",
    "question_group",
    "cloze",
    "matching",
]


class ChapterOut(BaseModel):
    id: int
    title: str
    description: str | None
    order_index: int
    source_file: str
    question_count: int = 0


class QuestionOut(BaseModel):
    id: int
    chapter_id: int
    type: str
    difficulty: str
    stem: str
    options: Any
    explanation: str | None = None


class QuestionReviewOut(QuestionOut):
    answer: Any


class PracticeCreate(BaseModel):
    mode: Literal["chapter", "final_review", "wrong_questions"] = "chapter"
    chapter_id: int | None = None
    question_count: int = Field(default=5, ge=1, le=30)
    question_types: list[QuestionType] | None = None
    user_id: str = "demo"


class PracticeOut(BaseModel):
    id: int
    mode: str
    chapter_id: int | None
    question_count: int
    score: Decimal | None
    started_at: datetime
    submitted_at: datetime | None
    questions: list[QuestionOut]


class SubmittedAnswer(BaseModel):
    question_id: int
    user_answer: Any


class PracticeSubmit(BaseModel):
    user_id: str = "demo"
    answers: list[SubmittedAnswer]


class AnswerResult(BaseModel):
    question_id: int
    is_correct: bool
    score: float
    feedback: str
    correct_answer: Any
    explanation: str | None


class PracticeResult(BaseModel):
    session_id: int
    score: float
    total: int
    results: list[AnswerResult]


class WrongQuestionOut(BaseModel):
    id: int
    question: QuestionReviewOut
    wrong_count: int
    mastered: bool
    last_wrong_at: datetime


class StatisticsOverview(BaseModel):
    total_sessions: int
    total_answers: int
    correct_rate: float
    wrong_question_count: int


class ChapterStatistics(BaseModel):
    chapter_id: int
    chapter_title: str
    answered: int
    correct_rate: float
