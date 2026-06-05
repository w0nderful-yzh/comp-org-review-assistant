from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any, Optional

from sqlalchemy import BigInteger, Boolean, DateTime, Enum, ForeignKey, Integer, Numeric, SmallInteger, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.core.database import Base

class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    student_id: Mapped[str] = mapped_column(Text, unique=True)
    password_hash: Mapped[str] = mapped_column(Text)
    nickname: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


QuestionTypeEnum = Enum(
    "single_choice",
    "multiple_choice",
    "true_false",
    "fill_blank",
    "short_answer",
    "calculation",
    "question_group",
    "cloze",
    "matching",
    name="question_type",
    create_type=False,
)
QuestionDifficultyEnum = Enum("easy", "medium", "hard", name="question_difficulty", create_type=False)
PracticeModeEnum = Enum("chapter", "final_review", "wrong_questions", name="practice_mode", create_type=False)


class Chapter(Base):
    __tablename__ = "chapters"

    id: Mapped[int] = mapped_column(SmallInteger, primary_key=True)
    title: Mapped[str] = mapped_column(Text)
    description: Mapped[Optional[str]] = mapped_column(Text)
    order_index: Mapped[int] = mapped_column(SmallInteger)
    source_file: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    questions: Mapped[list["Question"]] = relationship(back_populates="chapter")


class KnowledgePoint(Base):
    __tablename__ = "knowledge_points"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    chapter_id: Mapped[int] = mapped_column(ForeignKey("chapters.id"))
    name: Mapped[str] = mapped_column(Text)
    summary: Mapped[Optional[str]] = mapped_column(Text)
    difficulty: Mapped[str] = mapped_column(QuestionDifficultyEnum)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Question(Base):
    __tablename__ = "questions"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    chapter_id: Mapped[int] = mapped_column(ForeignKey("chapters.id"))
    knowledge_point_id: Mapped[Optional[int]] = mapped_column(ForeignKey("knowledge_points.id"))
    parent_question_id: Mapped[Optional[int]] = mapped_column(ForeignKey("questions.id"))
    type: Mapped[str] = mapped_column(QuestionTypeEnum)
    difficulty: Mapped[str] = mapped_column(QuestionDifficultyEnum)
    stem: Mapped[str] = mapped_column(Text)
    options_json: Mapped[Any] = mapped_column(JSONB)
    answer_json: Mapped[Any] = mapped_column(JSONB)
    rubric_json: Mapped[Any] = mapped_column(JSONB)
    explanation: Mapped[Optional[str]] = mapped_column(Text)
    source_context: Mapped[Optional[str]] = mapped_column(Text)
    source_assignment: Mapped[Optional[str]] = mapped_column(Text)
    is_ai_generated: Mapped[bool] = mapped_column(Boolean)
    is_reviewed: Mapped[bool] = mapped_column(Boolean)
    archived: Mapped[bool] = mapped_column(Boolean, default=False)
    ai_status: Mapped[Optional[str]] = mapped_column(Text)  # temporary/candidate/community_approved/verified/flagged/archived
    quality_score: Mapped[int] = mapped_column(Integer, default=0)
    attempt_count: Mapped[int] = mapped_column(Integer, default=0)
    helpful_count: Mapped[int] = mapped_column(Integer, default=0)
    not_helpful_count: Mapped[int] = mapped_column(Integer, default=0)
    error_count: Mapped[int] = mapped_column(Integer, default=0)
    flag_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    chapter: Mapped[Chapter] = relationship(back_populates="questions")


class PracticeSession(Base):
    __tablename__ = "practice_sessions"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    user_id: Mapped[Optional[str]] = mapped_column(Text)
    mode: Mapped[str] = mapped_column(PracticeModeEnum)
    chapter_id: Mapped[Optional[int]] = mapped_column(ForeignKey("chapters.id"))
    question_count: Mapped[int] = mapped_column(Integer)
    score: Mapped[Optional[Decimal]] = mapped_column(Numeric(6, 2))
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    submitted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    answers: Mapped[list["AnswerRecord"]] = relationship(back_populates="session")


class AnswerRecord(Base):
    __tablename__ = "answer_records"
    __table_args__ = (UniqueConstraint("session_id", "question_id"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("practice_sessions.id"))
    question_id: Mapped[int] = mapped_column(ForeignKey("questions.id"))
    user_answer: Mapped[Any] = mapped_column(JSONB)
    is_correct: Mapped[Optional[bool]] = mapped_column(Boolean)
    score: Mapped[Optional[Decimal]] = mapped_column(Numeric(6, 2))
    feedback: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    session: Mapped[PracticeSession] = relationship(back_populates="answers")
    question: Mapped[Question] = relationship()


class WrongQuestion(Base):
    __tablename__ = "wrong_questions"
    __table_args__ = (UniqueConstraint("user_id", "question_id"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    user_id: Mapped[str] = mapped_column(Text)
    question_id: Mapped[int] = mapped_column(ForeignKey("questions.id"))
    wrong_count: Mapped[int] = mapped_column(Integer)
    last_wrong_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    mastered: Mapped[bool] = mapped_column(Boolean)

    question: Mapped[Question] = relationship()


class KnowledgeChunk(Base):
    __tablename__ = "knowledge_chunks"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    chapter_id: Mapped[int] = mapped_column(ForeignKey("chapters.id"))
    chunk_id: Mapped[str] = mapped_column(Text)
    title: Mapped[Optional[str]] = mapped_column(Text)
    content: Mapped[str] = mapped_column(Text)
    source_file: Mapped[str] = mapped_column(Text)
    source_page: Mapped[Optional[int]] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    chapter: Mapped[Chapter] = relationship()


class QuestionFeedback(Base):
    __tablename__ = "question_feedback"
    __table_args__ = (UniqueConstraint("user_id", "question_id"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    user_id: Mapped[str] = mapped_column(Text)
    question_id: Mapped[int] = mapped_column(ForeignKey("questions.id", ondelete="CASCADE"))
    is_helpful: Mapped[bool] = mapped_column(Boolean)
    feedback_type: Mapped[Optional[str]] = mapped_column(Text)  # helpful/not_helpful/flag
    reason: Mapped[Optional[str]] = mapped_column(Text)  # flag reasons
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class LabExamGeneration(Base):
    __tablename__ = "lab_exam_generations"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    user_id: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(Text, default="pending")
    paper_json: Mapped[Optional[Any]] = mapped_column(JSONB)
    answer_json: Mapped[Optional[Any]] = mapped_column(JSONB)
    error_message: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
