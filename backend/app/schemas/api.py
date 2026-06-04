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
    blank_count: int = 0
    source_type: Literal["homework", "ai", "sample", "manual"] = "manual"
    source_label: str = "人工维护"
    explanation: str | None = None
    likes: int = 0
    user_liked: bool = False
    ai_status: str | None = None
    quality_score: int = 0
    children: list["QuestionOut"] = Field(default_factory=list)


class QuestionReviewOut(QuestionOut):
    answer: Any


SourceScope = Literal["original_only", "standard", "ai_new", "ai_pool"]


class PracticeCreate(BaseModel):
    mode: Literal["chapter", "final_review", "wrong_questions"] = "chapter"
    chapter_id: int | None = None
    question_count: int = Field(default=5, ge=1, le=30)
    question_types: list[QuestionType] | None = None
    source_scope: SourceScope = "standard"


class PracticeOut(BaseModel):
    id: int
    mode: str
    chapter_id: int | None
    question_count: int
    score: Decimal | None
    started_at: datetime
    submitted_at: datetime | None
    questions: list[QuestionOut]


class AllQuestionsCompletedOut(BaseModel):
    completed: bool = True
    message: str
    total_questions: int
    answered_questions: int
    suggestions: list[str]


class SubmittedAnswer(BaseModel):
    question_id: int
    user_answer: Any


class PracticeSubmit(BaseModel):
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


class PracticeHistoryItem(BaseModel):
    id: int
    mode: str
    chapter_id: int | None
    chapter_title: str | None
    question_count: int
    score: float | None
    started_at: datetime
    submitted_at: datetime | None


class AnswerReviewResult(BaseModel):
    question_id: int
    user_answer: Any
    is_correct: bool | None
    score: float | None
    feedback: str | None
    correct_answer: Any
    explanation: str | None


class PracticeReviewOut(BaseModel):
    id: int
    mode: str
    chapter_id: int | None
    chapter_title: str | None
    question_count: int
    score: float | None
    started_at: datetime
    submitted_at: datetime | None
    questions: list[QuestionReviewOut]
    results: list[AnswerReviewResult]


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
    total_questions: int
    correct_rate: float
    coverage: float  # 题目覆盖率
    mastered_rate: float  # 错题掌握率
    mastery_score: float  # 综合掌握度 (0-100)


class QuestionTypeStatistics(BaseModel):
    question_type: str
    answered: int
    correct_rate: float


class StudyRecommendation(BaseModel):
    chapter_id: int
    chapter_title: str
    answered: int
    correct_rate: float
    wrong_count: int
    reason: str
    action: str
    priority: float


class AiQuestionDraftCreate(BaseModel):
    chapter_id: int | None = None
    question_types: list[QuestionType] = Field(default_factory=list)
    difficulty: Literal["easy", "medium", "hard"] = "medium"
    count: int = Field(default=3, ge=1, le=5)
    focus: str | None = None


class AiQuestionDraftOut(BaseModel):
    created: int
    question_ids: list[int]


class KnowledgePointOut(BaseModel):
    id: int
    chapter_id: int
    name: str
    summary: str | None
    difficulty: str


class KnowledgeChunkOut(BaseModel):
    id: int
    chunk_id: str
    chapter_id: int
    title: str | None
    content: str
    source_file: str
    source_page: int | None


class KnowledgeSearchOut(BaseModel):
    items: list[KnowledgeChunkOut]
    total: int


class QuestionFeedbackCreate(BaseModel):
    feedback_type: Literal["helpful", "not_helpful", "flag"]
    reason: str | None = None  # flag reasons: answer_error, unclear_stem, ambiguous_options, out_of_scope, duplicate, unclear_explanation


class QuestionFeedbackOut(BaseModel):
    question_id: int
    likes: int
    unhelpful: int
    flags: int
    user_liked: bool
    ai_status: str | None = None
    quality_score: int = 0


class AiStatusOut(BaseModel):
    enabled: bool
    daily_remaining: int


class ExamSectionOut(BaseModel):
    id: str
    title: str
    score: int
    slots: list[str]


class ExamSubQuestionOut(BaseModel):
    id: str
    label: str
    prompt: str
    score: float | None = None
    answer_type: Literal["text", "single_choice"] = "text"
    options: list[dict[str, str]] = Field(default_factory=list)


class ExamSourceImageOut(BaseModel):
    label: str
    filename: str
    url: str


class ExamQuestionOut(BaseModel):
    id: str
    section_id: str
    number: str
    title: str
    score: float
    stem: str
    source_images: list[ExamSourceImageOut] = Field(default_factory=list)
    sub_questions: list[ExamSubQuestionOut] = Field(default_factory=list)


class ExamPaperOut(BaseModel):
    year: int
    title: str
    duration_minutes: int
    total_score: int
    paper_pdf: str
    answer_pdf: str
    sections: list[ExamSectionOut]
    source_url: str
    questions: list[ExamQuestionOut] = Field(default_factory=list)


# ========== 认证相关 Schema ==========


class UserRegister(BaseModel):
    student_id: str = Field(..., pattern=r"^\d{8}$", description="8位学号")
    password: str = Field(..., min_length=6, max_length=128)
    nickname: str | None = None


class UserLogin(BaseModel):
    student_id: str = Field(..., pattern=r"^\d{8}$", description="8位学号")
    password: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    id: int
    student_id: str
    nickname: str | None
    created_at: datetime
