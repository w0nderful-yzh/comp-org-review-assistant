from __future__ import annotations

import json
import random
from datetime import datetime, timezone
from typing import Union
from urllib.parse import quote
from zoneinfo import ZoneInfo

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from fastapi.responses import FileResponse
from sqlalchemy import and_, delete, func, or_, select, text
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import get_settings
from app.core.database import SessionLocal, get_db
from app.core.limiter import limiter
from app.core.security import create_access_token, get_password_hash, verify_password
from app.models.entities import AnswerRecord, Chapter, KnowledgeChunk, KnowledgePoint, LabExamGeneration, PracticeSession, Question, QuestionFeedback, User, WrongQuestion
from app.schemas.api import (
    AiQuestionDraftCreate,
    AiQuestionDraftOut,
    AiStatusOut,
    AllQuestionsCompletedOut,
    AnswerReviewResult,
    AnswerResult,
    ChapterOut,
    ChapterStatistics,
    ExamPaperOut,
    KnowledgeChunkOut,
    KnowledgePointOut,
    KnowledgeSearchOut,
    LabExamDashboardOut,
    LabExamGenerationOut,
    LabExamPaperOut,
    PracticeCreate,
    PracticeHistoryItem,
    PracticeOut,
    PracticeResult,
    PracticeReviewOut,
    QuestionTypeStatistics,
    PracticeSubmit,
    QuestionFeedbackCreate,
    QuestionFeedbackOut,
    QuestionOut,
    QuestionReviewOut,
    StatisticsOverview,
    StudyRecommendation,
    TokenOut,
    UserLogin,
    UserOut,
    UserRegister,
    WrongQuestionOut,
)
from app.core.logging import get_logger
from app.services.ai_generation import AiGenerationError, generate_question_drafts
from app.services.grading import grade_answer, public_answer
from app.services.lab_exam_generation import generate_lab_exam_paper, load_static_lab_exam

logger = get_logger(__name__)

UNHELPFUL_ARCHIVE_THRESHOLD = 3
DAILY_AI_LIMIT = 50
DAILY_LAB_EXAM_LIMIT = 1
APP_TIMEZONE = ZoneInfo("Asia/Shanghai")

FLAG_SCORE_MAP = {
    "answer_error": (-5, 1),     # (quality_delta, error_count_delta)
    "ambiguous_options": (-3, 0),
    "out_of_scope": (-4, 0),
    "unclear_stem": (-2, 0),
    "unclear_explanation": (-2, 0),
    "duplicate": (-2, 0),
}

AI_STATUS_LABELS = {
    "temporary": "AI 临时补充题",
    "candidate": "AI 补充题 · 候选",
    "community_approved": "AI 补充题 · 已通过反馈",
    "verified": "AI 补充题 · 已确认",
    "flagged": "AI 补充题 · 待检查",
}

router = APIRouter(prefix="/api")


# ========== 认证路由 ==========


@router.post("/auth/register", response_model=TokenOut)
def register(payload: UserRegister, db: Session = Depends(get_db)) -> TokenOut:
    existing = db.scalar(select(User).where(User.student_id == payload.student_id))
    if existing:
        logger.warning(f"注册失败: 学号 {payload.student_id} 已存在")
        raise HTTPException(status_code=400, detail="该学号已注册")
    user = User(
        student_id=payload.student_id,
        password_hash=get_password_hash(payload.password),
        nickname=payload.nickname,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    token = create_access_token(data={"sub": str(user.id)})
    logger.info(f"用户注册成功: {payload.student_id}")
    return TokenOut(access_token=token)


@router.post("/auth/login", response_model=TokenOut)
def login(payload: UserLogin, db: Session = Depends(get_db)) -> TokenOut:
    user = db.scalar(select(User).where(User.student_id == payload.student_id))
    if not user or not verify_password(payload.password, user.password_hash):
        logger.warning(f"登录失败: 学号 {payload.student_id}")
        raise HTTPException(status_code=401, detail="学号或密码错误")
    token = create_access_token(data={"sub": str(user.id)})
    logger.info(f"用户登录成功: {payload.student_id}")
    return TokenOut(access_token=token)


@router.get("/auth/me", response_model=UserOut)
def get_me(current_user: User = Depends(get_current_user)) -> UserOut:
    return UserOut(
        id=current_user.id,
        student_id=current_user.student_id,
        nickname=current_user.nickname,
        created_at=current_user.created_at,
    )


def question_source_type(question: Question) -> str:
    if question.is_ai_generated:
        return "ai"
    context = (question.source_context or "").lower()
    assignment = question.source_assignment or ""
    if "homework-examples" in context or "作业" in assignment:
        return "homework"
    if "phase-1 sample seed" in context:
        return "sample"
    return "manual"


def question_source_label(question: Question) -> str:
    if question.is_ai_generated and question.ai_status:
        return AI_STATUS_LABELS.get(question.ai_status, "AI生成")
    labels = {
        "ai": "AI生成",
        "homework": "作业原题",
        "sample": "样例题",
        "manual": "人工维护",
    }
    return labels[question_source_type(question)]


def question_out(
    question: Question,
    likes: int = 0,
    user_liked: bool = False,
    children: list[QuestionOut] | None = None,
) -> QuestionOut:
    blank_count = 0
    if question.type in {"fill_blank", "cloze"} and isinstance(question.answer_json, dict):
        blank_count = len(question.answer_json.get("blanks", []))
    return QuestionOut(
        id=question.id,
        chapter_id=question.chapter_id,
        type=question.type,
        difficulty=question.difficulty,
        stem=question.stem,
        options=question.options_json,
        blank_count=blank_count,
        source_type=question_source_type(question),
        source_label=question_source_label(question),
        explanation=question.explanation,
        likes=likes,
        user_liked=user_liked,
        ai_status=question.ai_status,
        quality_score=question.quality_score,
        children=children or [],
    )


def question_review_out(
    question: Question,
    likes: int = 0,
    user_liked: bool = False,
    children: list[QuestionOut] | None = None,
) -> QuestionReviewOut:
    base = question_out(question, likes, user_liked, children).model_dump()
    return QuestionReviewOut(**base, answer=public_answer(question.answer_json))


def knowledge_point_out(point: KnowledgePoint) -> KnowledgePointOut:
    return KnowledgePointOut(
        id=point.id,
        chapter_id=point.chapter_id,
        name=point.name,
        summary=point.summary,
        difficulty=point.difficulty,
    )


def knowledge_chunk_out(chunk: KnowledgeChunk) -> KnowledgeChunkOut:
    return KnowledgeChunkOut(
        id=chunk.id,
        chunk_id=chunk.chunk_id,
        chapter_id=chunk.chapter_id,
        title=chunk.title,
        content=chunk.content,
        source_file=chunk.source_file,
        source_page=chunk.source_page,
    )


def load_exam_manifest() -> dict:
    manifest_path = get_settings().exam_paper_dir / "exam-papers.json"
    if not manifest_path.is_file():
        raise HTTPException(status_code=404, detail="Exam paper manifest not found")
    return json.loads(manifest_path.read_text(encoding="utf-8"))


def exam_paper_out(row: dict, source_url: str) -> ExamPaperOut:
    questions_path = get_settings().exam_paper_dir / "structured" / f"{row['year']}.json"
    questions = []
    if questions_path.is_file():
        structured = json.loads(questions_path.read_text(encoding="utf-8"))
        questions = [
            attach_exam_source_image_urls(row["year"], question)
            for question in structured.get("questions", [])
        ]
    return ExamPaperOut(
        year=row["year"],
        title=row["title"],
        duration_minutes=row["duration_minutes"],
        total_score=row["total_score"],
        paper_pdf=row["paper_pdf"],
        answer_pdf=row["answer_pdf"],
        sections=row["sections"],
        source_url=source_url,
        questions=questions,
    )


def attach_exam_source_image_urls(year: int, question: dict) -> dict:
    images_dir = get_settings().exam_paper_dir / "images" / str(year)
    source_images = []
    for index, image in enumerate(question.get("source_images", []), start=1):
        filename = str(image.get("filename", ""))
        if not filename or "/" in filename or "\\" in filename:
            continue
        image_path = images_dir / filename
        if not image_path.is_file():
            continue
        source_images.append({
            "label": image.get("label") or f"原卷图页 {index}",
            "filename": filename,
            "url": f"/api/exam-papers/{year}/images/{quote(filename)}",
        })
    return {**question, "source_images": source_images}


def get_exam_paper_row(year: int) -> tuple[dict, str]:
    manifest = load_exam_manifest()
    source_url = manifest.get("source", {}).get("url", "")
    for row in manifest.get("papers", []):
        if row.get("year") == year:
            return row, source_url
    raise HTTPException(status_code=404, detail="Exam paper not found")


def load_feedback_map(db: Session, question_ids: list[int], user_id: str) -> dict[int, dict]:
    if not question_ids:
        return {}
    counts = dict(
        db.execute(
            select(QuestionFeedback.question_id, func.count())
            .where(QuestionFeedback.question_id.in_(question_ids), QuestionFeedback.is_helpful.is_(True))
            .group_by(QuestionFeedback.question_id)
        ).all()
    )
    user_liked_ids = set(
        db.scalars(
            select(QuestionFeedback.question_id)
            .where(
                QuestionFeedback.question_id.in_(question_ids),
                QuestionFeedback.user_id == user_id,
                QuestionFeedback.is_helpful.is_(True),
            )
        ).all()
    )
    return {
        qid: {"likes": counts.get(qid, 0), "user_liked": qid in user_liked_ids}
        for qid in question_ids
    }


def check_ai_status_transition(question: Question) -> None:
    if not question.is_ai_generated or not question.ai_status:
        return

    if question.quality_score <= -5:
        question.ai_status = "archived"
        question.archived = True
        return

    if question.ai_status in ("temporary", "candidate") and question.error_count >= 2:
        question.ai_status = "flagged"
        return

    total = question.helpful_count + question.not_helpful_count
    if question.ai_status == "temporary":
        if question.attempt_count >= 5 and question.quality_score >= 6 and question.error_count == 0:
            question.ai_status = "candidate"
    elif question.ai_status == "candidate":
        if question.attempt_count >= 10 and total > 0 and question.helpful_count / total >= 0.7 and question.quality_score >= 10:
            question.ai_status = "community_approved"


def get_daily_ai_count(db: Session, user_id: str) -> int:
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    return db.scalar(
        select(func.count(Question.id))
        .where(
            Question.is_ai_generated.is_(True),
            Question.created_at >= today_start,
        )
    ) or 0


def select_adaptive_questions(db: Session, filters: list, question_count: int, user_id: str) -> list[Question]:
    candidates = db.scalars(select(Question).where(and_(*filters))).all()
    if not candidates:
        return []

    question_ids = [question.id for question in candidates]
    stats_rows = db.execute(
        select(
            AnswerRecord.question_id,
            func.count(AnswerRecord.id).label("answered"),
            func.count().filter(AnswerRecord.is_correct.is_(True)).label("correct"),
        )
        .join(PracticeSession, PracticeSession.id == AnswerRecord.session_id)
        .where(
            PracticeSession.user_id == user_id,
            AnswerRecord.question_id.in_(question_ids),
            AnswerRecord.is_correct.isnot(None),
        )
        .group_by(AnswerRecord.question_id)
    ).all()
    stats_map = {row.question_id: row for row in stats_rows}

    wrong_rows = db.execute(
        select(WrongQuestion.question_id, WrongQuestion.wrong_count)
        .where(
            WrongQuestion.user_id == user_id,
            WrongQuestion.mastered.is_(False),
            WrongQuestion.question_id.in_(question_ids),
        )
    ).all()
    wrong_map = {row.question_id: row.wrong_count for row in wrong_rows}

    def priority(question: Question) -> float:
        row = stats_map.get(question.id)
        answered = row.answered if row else 0
        correct = row.correct if row else 0
        if answered == 0:
            base = 100.0
        else:
            incorrect_rate = 1 - (correct / answered)
            base = incorrect_rate * 70 + max(0, 3 - answered) * 6
        base += min(wrong_map.get(question.id, 0), 5) * 18
        return base + random.random()

    return sorted(candidates, key=priority, reverse=True)[:question_count]


def practice_chapter_title(db: Session, session: PracticeSession) -> str | None:
    if session.chapter_id is None:
        return None
    chapter = db.get(Chapter, session.chapter_id)
    return chapter.title if chapter else None


def load_children_map(db: Session, questions: list[Question]) -> dict[int, list[Question]]:
    parent_ids = [question.id for question in questions if question.type == "question_group"]
    if not parent_ids:
        return {}
    children = db.scalars(
        select(Question)
        .where(
            Question.parent_question_id.in_(parent_ids),
            Question.archived.is_(False),
        )
        .order_by(Question.parent_question_id, Question.id)
    ).all()
    children_map: dict[int, list[Question]] = {parent_id: [] for parent_id in parent_ids}
    for child in children:
        if child.parent_question_id is not None:
            children_map.setdefault(child.parent_question_id, []).append(child)
    return children_map


def answerable_questions(db: Session, questions: list[Question]) -> list[Question]:
    children_map = load_children_map(db, questions)
    answerable: list[Question] = []
    for question in questions:
        if question.type == "question_group":
            answerable.extend(children_map.get(question.id, []))
        else:
            answerable.append(question)
    return answerable


def question_tree_out(
    db: Session,
    question: Question,
    feedback_map: dict[int, dict],
    review: bool = False,
) -> QuestionOut:
    children = load_children_map(db, [question]).get(question.id, [])
    child_out = [
        question_tree_out(db, child, feedback_map, review)
        for child in children
    ]
    feedback = feedback_map.get(question.id, {"likes": 0, "user_liked": False})
    if review:
        return question_review_out(question, **feedback, children=child_out)
    return question_out(question, **feedback, children=child_out)


def session_top_level_questions(db: Session, records: list[AnswerRecord]) -> list[Question]:
    questions: list[Question] = []
    seen: set[int] = set()
    for record in records:
        question = record.question
        if question.parent_question_id is not None:
            parent = db.get(Question, question.parent_question_id)
            if parent and parent.id not in seen:
                questions.append(parent)
                seen.add(parent.id)
            continue
        if question.id not in seen:
            questions.append(question)
            seen.add(question.id)
    return questions


def collect_question_tree_ids(db: Session, questions: list[Question]) -> list[int]:
    ids: list[int] = []
    children_map = load_children_map(db, questions)
    for question in questions:
        ids.append(question.id)
        ids.extend(child.id for child in children_map.get(question.id, []))
    return ids


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/ai-status", response_model=AiStatusOut)
def ai_status(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AiStatusOut:
    settings = get_settings()
    if not settings.ai_enabled or not settings.ai_api_key:
        return AiStatusOut(enabled=False, daily_remaining=0)
    used = get_daily_ai_count(db, str(current_user.id))
    return AiStatusOut(enabled=True, daily_remaining=max(0, DAILY_AI_LIMIT - used))


@router.get("/chapters", response_model=list[ChapterOut])
def list_chapters(db: Session = Depends(get_db)) -> list[ChapterOut]:
    counts = dict(
        db.execute(
            select(Question.chapter_id, func.count(Question.id))
            .where(
                Question.archived.is_(False),
                Question.parent_question_id.is_(None),
                Question.type != "short_answer",
            )
            .group_by(Question.chapter_id)
        ).all()
    )
    chapters = db.scalars(select(Chapter).order_by(Chapter.order_index)).all()
    return [
        ChapterOut(
            id=chapter.id,
            title=chapter.title,
            description=chapter.description,
            order_index=chapter.order_index,
            source_file=chapter.source_file,
            question_count=counts.get(chapter.id, 0),
        )
        for chapter in chapters
    ]


@router.get("/chapters/{chapter_id}", response_model=ChapterOut)
def get_chapter(chapter_id: int, db: Session = Depends(get_db)) -> ChapterOut:
    chapter = db.get(Chapter, chapter_id)
    if not chapter:
        raise HTTPException(status_code=404, detail="Chapter not found")
    count = db.scalar(
        select(func.count(Question.id)).where(
            Question.chapter_id == chapter_id,
            Question.archived.is_(False),
            Question.parent_question_id.is_(None),
            Question.type != "short_answer",
        )
    )
    return ChapterOut(
        id=chapter.id,
        title=chapter.title,
        description=chapter.description,
        order_index=chapter.order_index,
        source_file=chapter.source_file,
        question_count=count or 0,
    )


@router.get("/chapters/{chapter_id}/knowledge-points", response_model=list[KnowledgePointOut])
def list_knowledge_points(chapter_id: int, db: Session = Depends(get_db)) -> list[KnowledgePointOut]:
    chapter = db.get(Chapter, chapter_id)
    if not chapter:
        raise HTTPException(status_code=404, detail="Chapter not found")
    points = db.scalars(
        select(KnowledgePoint)
        .where(KnowledgePoint.chapter_id == chapter_id)
        .order_by(KnowledgePoint.id)
    ).all()
    return [knowledge_point_out(point) for point in points]


@router.get("/chapters/{chapter_id}/knowledge-chunks", response_model=list[KnowledgeChunkOut])
def list_knowledge_chunks(
    chapter_id: int,
    limit: int = 80,
    db: Session = Depends(get_db),
) -> list[KnowledgeChunkOut]:
    chapter = db.get(Chapter, chapter_id)
    if not chapter:
        raise HTTPException(status_code=404, detail="Chapter not found")
    limit = min(max(limit, 1), 200)
    chunks = db.scalars(
        select(KnowledgeChunk)
        .where(KnowledgeChunk.chapter_id == chapter_id)
        .order_by(KnowledgeChunk.chunk_id)
        .limit(limit)
    ).all()
    return [knowledge_chunk_out(chunk) for chunk in chunks]


@router.get("/knowledge/search", response_model=KnowledgeSearchOut)
def search_knowledge(
    q: str,
    chapter_id: int | None = None,
    limit: int = 8,
    db: Session = Depends(get_db),
) -> KnowledgeSearchOut:
    query = q.strip()
    if not query:
        return KnowledgeSearchOut(items=[], total=0)

    limit = min(max(limit, 1), 30)
    conditions = [
        or_(
            KnowledgeChunk.title.ilike(f"%{query}%"),
            KnowledgeChunk.content.ilike(f"%{query}%"),
        )
    ]
    if chapter_id:
        conditions.append(KnowledgeChunk.chapter_id == chapter_id)

    total = db.scalar(select(func.count(KnowledgeChunk.id)).where(*conditions)) or 0
    chunks = db.scalars(
        select(KnowledgeChunk)
        .where(*conditions)
        .order_by(KnowledgeChunk.chapter_id, KnowledgeChunk.chunk_id)
        .limit(limit)
    ).all()
    return KnowledgeSearchOut(items=[knowledge_chunk_out(chunk) for chunk in chunks], total=total)


@router.get("/exam-papers", response_model=list[ExamPaperOut])
def list_exam_papers() -> list[ExamPaperOut]:
    manifest = load_exam_manifest()
    source_url = manifest.get("source", {}).get("url", "")
    papers = sorted(manifest.get("papers", []), key=lambda item: item["year"], reverse=True)
    return [exam_paper_out(row, source_url) for row in papers]


@router.get("/exam-papers/{year}", response_model=ExamPaperOut)
def get_exam_paper(year: int) -> ExamPaperOut:
    row, source_url = get_exam_paper_row(year)
    return exam_paper_out(row, source_url)


@router.get("/exam-papers/{year}/{kind}-pdf")
def get_exam_paper_pdf(
    year: int,
    kind: str,
    download: bool = False,
    current_user: User = Depends(get_current_user),
) -> FileResponse:
    if kind not in {"paper", "answer"}:
        raise HTTPException(status_code=404, detail="Exam PDF not found")
    row, _ = get_exam_paper_row(year)
    filename = row["paper_pdf"] if kind == "paper" else row["answer_pdf"]
    pdf_path = get_settings().exam_paper_dir / "pdf" / filename
    if not pdf_path.is_file():
        raise HTTPException(status_code=404, detail="Exam PDF not found")
    return FileResponse(
        pdf_path,
        media_type="application/pdf",
        filename=filename,
        content_disposition_type="attachment" if download else "inline",
    )


@router.get("/exam-papers/{year}/images/{filename:path}")
def get_exam_paper_image(
    year: int,
    filename: str,
) -> FileResponse:
    get_exam_paper_row(year)
    if "/" in filename or "\\" in filename:
        raise HTTPException(status_code=404, detail="Exam image not found")
    image_path = get_settings().exam_paper_dir / "images" / str(year) / filename
    if not image_path.is_file():
        raise HTTPException(status_code=404, detail="Exam image not found")
    media_type = "image/jpeg" if image_path.suffix.lower() in {".jpg", ".jpeg"} else "image/png"
    return FileResponse(
        image_path,
        media_type=media_type,
        headers={"Cache-Control": "no-cache, must-revalidate"},
    )


def ensure_lab_exam_generation_table(db: Session) -> None:
    db.execute(text("""
        CREATE TABLE IF NOT EXISTS lab_exam_generations (
          id BIGSERIAL PRIMARY KEY,
          user_id TEXT NOT NULL,
          status TEXT NOT NULL DEFAULT 'pending',
          paper_json JSONB,
          answer_json JSONB,
          error_message TEXT,
          created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
          started_at TIMESTAMPTZ,
          completed_at TIMESTAMPTZ
        )
    """))
    db.execute(text("""
        CREATE INDEX IF NOT EXISTS idx_lab_exam_generations_user_created
        ON lab_exam_generations(user_id, created_at DESC)
    """))
    db.commit()


def lab_exam_today_start() -> datetime:
    now = datetime.now(APP_TIMEZONE)
    return now.replace(hour=0, minute=0, second=0, microsecond=0)


def lab_exam_generation_out(row: LabExamGeneration | None) -> LabExamGenerationOut | None:
    if row is None:
        return None
    paper = None
    if row.status == "completed" and row.paper_json:
        paper = LabExamPaperOut.model_validate(row.paper_json)
    return LabExamGenerationOut(
        id=row.id,
        status=row.status,
        created_at=row.created_at,
        started_at=row.started_at,
        completed_at=row.completed_at,
        error_message=row.error_message,
        paper=paper,
    )


def latest_lab_exam_generation(db: Session, user_id: str) -> LabExamGeneration | None:
    return db.scalar(
        select(LabExamGeneration)
        .where(LabExamGeneration.user_id == user_id)
        .order_by(LabExamGeneration.created_at.desc(), LabExamGeneration.id.desc())
        .limit(1)
    )


def today_lab_exam_generation(db: Session, user_id: str) -> LabExamGeneration | None:
    return db.scalar(
        select(LabExamGeneration)
        .where(
            LabExamGeneration.user_id == user_id,
            LabExamGeneration.created_at >= lab_exam_today_start(),
        )
        .order_by(LabExamGeneration.created_at.desc(), LabExamGeneration.id.desc())
        .limit(1)
    )


def run_lab_exam_generation(generation_id: int) -> None:
    settings = get_settings()
    with SessionLocal() as db:
        ensure_lab_exam_generation_table(db)
        row = db.get(LabExamGeneration, generation_id)
        if row is None:
            return
        row.status = "running"
        row.started_at = datetime.now(timezone.utc)
        db.commit()
        try:
            paper = generate_lab_exam_paper(settings)
            row.status = "completed"
            row.paper_json = paper
            row.answer_json = {
                "questions": [
                    {
                        "id": question.get("id"),
                        "answer": question.get("answer"),
                        "reference_answer": question.get("reference_answer"),
                        "explanation": question.get("explanation"),
                    }
                    for question in paper.get("questions", [])
                ]
            }
            row.completed_at = datetime.now(timezone.utc)
            row.error_message = None
        except Exception as exc:
            logger.exception("实验模拟卷生成失败: %s", exc)
            row.status = "failed"
            row.error_message = str(exc)
            row.completed_at = datetime.now(timezone.utc)
        db.commit()


@router.get("/lab-exams", response_model=LabExamDashboardOut)
def get_lab_exam_dashboard(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> LabExamDashboardOut:
    ensure_lab_exam_generation_table(db)
    settings = get_settings()
    user_id = str(current_user.id)
    today_row = today_lab_exam_generation(db, user_id)
    latest_row = today_row or latest_lab_exam_generation(db, user_id)
    return LabExamDashboardOut(
        static_paper=LabExamPaperOut.model_validate(load_static_lab_exam(settings)),
        latest_generation=lab_exam_generation_out(latest_row),
        daily_remaining=0 if today_row else DAILY_LAB_EXAM_LIMIT,
        ai_enabled=bool(settings.ai_enabled and settings.ai_api_key),
    )


@router.post("/lab-exams/generations", response_model=LabExamGenerationOut)
def create_lab_exam_generation(
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> LabExamGenerationOut:
    ensure_lab_exam_generation_table(db)
    settings = get_settings()
    if not settings.ai_enabled or not settings.ai_api_key:
        raise HTTPException(status_code=503, detail="AI service is not configured")

    user_id = str(current_user.id)
    existing = today_lab_exam_generation(db, user_id)
    if existing:
        return lab_exam_generation_out(existing)  # type: ignore[return-value]

    row = LabExamGeneration(user_id=user_id, status="pending")
    db.add(row)
    db.commit()
    db.refresh(row)
    background_tasks.add_task(run_lab_exam_generation, row.id)
    return lab_exam_generation_out(row)  # type: ignore[return-value]


@router.get("/lab-exams/generations/{generation_id}", response_model=LabExamGenerationOut)
def get_lab_exam_generation(
    generation_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> LabExamGenerationOut:
    ensure_lab_exam_generation_table(db)
    user_id = str(current_user.id)
    row = db.get(LabExamGeneration, generation_id)
    if not row or row.user_id != user_id:
        raise HTTPException(status_code=404, detail="Lab exam generation not found")
    return lab_exam_generation_out(row)  # type: ignore[return-value]


@router.get("/chapters/{chapter_id}/courseware-pdf")
def get_chapter_courseware_pdf(
    chapter_id: int,
    download: bool = False,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> FileResponse:
    chapter = db.get(Chapter, chapter_id)
    if chapter is None:
        raise HTTPException(status_code=404, detail="Chapter not found")
    pdf_dir = get_settings().courseware_pdf_dir
    pdf_path = pdf_dir / f"chapter-{chapter.order_index:02d}-courseware.pdf"
    if not pdf_path.is_file():
        raise HTTPException(status_code=404, detail="Courseware PDF not found")
    filename = f"第{chapter.order_index}章-{chapter.title}-课件.pdf"
    return FileResponse(
        pdf_path,
        media_type="application/pdf",
        filename=filename,
        content_disposition_type="attachment" if download else "inline",
    )


@router.get("/questions", response_model=list[QuestionReviewOut])
def list_questions(
    chapter_id: int | None = None,
    question_type: str | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[QuestionReviewOut]:
    conditions = [Question.archived.is_(False), Question.parent_question_id.is_(None)]
    if chapter_id:
        conditions.append(Question.chapter_id == chapter_id)
    if question_type:
        conditions.append(Question.type == question_type)
    questions = db.scalars(select(Question).where(*conditions).order_by(Question.id)).all()
    feedback_map = load_feedback_map(db, collect_question_tree_ids(db, questions), str(current_user.id))
    return [question_tree_out(db, q, feedback_map, review=True) for q in questions]


@router.post("/questions/{question_id}/feedback", response_model=QuestionFeedbackOut)
def submit_feedback(
    question_id: int,
    payload: QuestionFeedbackCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> QuestionFeedbackOut:
    user_id = str(current_user.id)
    question = db.get(Question, question_id)
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")

    is_helpful = payload.feedback_type == "helpful"

    existing = db.scalar(
        select(QuestionFeedback).where(
            QuestionFeedback.user_id == user_id,
            QuestionFeedback.question_id == question_id,
        )
    )
    if existing:
        existing.is_helpful = is_helpful
        existing.feedback_type = payload.feedback_type
        existing.reason = payload.reason
    else:
        db.add(QuestionFeedback(
            user_id=user_id,
            question_id=question_id,
            is_helpful=is_helpful,
            feedback_type=payload.feedback_type,
            reason=payload.reason,
        ))

    if question.is_ai_generated and question.ai_status:
        if payload.feedback_type == "helpful":
            question.helpful_count += 1
            question.quality_score += 2
        elif payload.feedback_type == "not_helpful":
            question.not_helpful_count += 1
            question.quality_score -= 1
        elif payload.feedback_type == "flag":
            question.flag_count += 1
            score_delta, error_delta = FLAG_SCORE_MAP.get(payload.reason or "", (-2, 0))
            question.quality_score += score_delta
            question.error_count += error_delta
            if payload.reason == "answer_error":
                question.error_count += 1
        check_ai_status_transition(question)
    elif not question.is_ai_generated:
        if payload.feedback_type != "helpful":
            unhelpful_count = db.scalar(
                select(func.count()).where(
                    QuestionFeedback.question_id == question_id,
                    QuestionFeedback.is_helpful.is_(False),
                )
            ) or 0
            if unhelpful_count >= UNHELPFUL_ARCHIVE_THRESHOLD:
                question.archived = True

    db.commit()

    likes = db.scalar(
        select(func.count()).where(QuestionFeedback.question_id == question_id, QuestionFeedback.is_helpful.is_(True))
    ) or 0
    unhelpful = db.scalar(
        select(func.count()).where(QuestionFeedback.question_id == question_id, QuestionFeedback.is_helpful.is_(False))
    ) or 0
    flags = db.scalar(
        select(func.count()).where(QuestionFeedback.question_id == question_id, QuestionFeedback.feedback_type == "flag")
    ) or 0
    return QuestionFeedbackOut(
        question_id=question_id,
        likes=likes,
        unhelpful=unhelpful,
        flags=flags,
        user_liked=is_helpful,
        ai_status=question.ai_status,
        quality_score=question.quality_score,
    )


@router.delete("/questions/{question_id}/feedback")
def delete_feedback(
    question_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, bool]:
    existing = db.scalar(
        select(QuestionFeedback).where(
            QuestionFeedback.user_id == str(current_user.id),
            QuestionFeedback.question_id == question_id,
        )
    )
    if not existing:
        raise HTTPException(status_code=404, detail="Feedback not found")
    db.delete(existing)
    db.commit()
    return {"deleted": True}


@router.post("/ai-question-drafts", response_model=AiQuestionDraftOut)
def create_ai_question_drafts(
    payload: AiQuestionDraftCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AiQuestionDraftOut:
    settings = get_settings()
    if not settings.ai_enabled or not settings.ai_api_key:
        raise HTTPException(status_code=503, detail="AI service is not configured")

    used = get_daily_ai_count(db, str(current_user.id))
    if used >= DAILY_AI_LIMIT:
        raise HTTPException(status_code=429, detail=f"Daily AI generation limit reached ({DAILY_AI_LIMIT}/day)")

    actual_count = min(payload.count, 5, DAILY_AI_LIMIT - used)

    # Auto-select chapter if not provided: pick the one with fewest questions
    chapter_id = payload.chapter_id
    if chapter_id is None:
        chapter_id = db.scalar(
            select(Chapter.id)
            .outerjoin(Question, Question.chapter_id == Chapter.id)
            .group_by(Chapter.id)
            .order_by(func.count(Question.id))
            .limit(1)
        )
        if chapter_id is None:
            raise HTTPException(status_code=404, detail="No chapters available")

    chapter = db.get(Chapter, chapter_id)
    if not chapter:
        raise HTTPException(status_code=404, detail="Chapter not found")

    chunks = db.scalars(
        select(KnowledgeChunk)
        .where(KnowledgeChunk.chapter_id == chapter_id)
        .order_by(KnowledgeChunk.chunk_id)
        .limit(12)
    ).all()
    if not chunks:
        raise HTTPException(status_code=404, detail="No knowledge chunks available for this chapter")

    try:
        drafts = generate_question_drafts(payload, chapter, chunks, settings)
    except AiGenerationError as exc:
        status_code = 503 if "AI_API_KEY" in str(exc) else 502
        raise HTTPException(status_code=status_code, detail=str(exc)) from exc

    existing_stems = set(
        db.scalars(
            select(Question.stem)
            .where(Question.chapter_id == chapter_id, Question.archived.is_(False))
        ).all()
    )

    question_ids: list[int] = []
    for draft in drafts[:actual_count]:
        if any(draft.stem in s or s in draft.stem for s in existing_stems if len(s) > 10):
            continue
        question = Question(
            chapter_id=draft.chapter_id,
            knowledge_point_id=None,
            parent_question_id=None,
            type=draft.type,
            difficulty=draft.difficulty,
            stem=draft.stem,
            options_json=draft.options_json,
            answer_json=draft.answer_json,
            rubric_json=draft.rubric_json,
            explanation=draft.explanation,
            source_context=draft.source_context,
            source_assignment="AI题目生成",
            is_ai_generated=True,
            is_reviewed=True,
            ai_status="temporary",
            quality_score=0,
        )
        db.add(question)
        db.flush()
        question_ids.append(question.id)
    db.commit()
    return AiQuestionDraftOut(created=len(question_ids), question_ids=question_ids)


@router.post("/practice-sessions", response_model=Union[PracticeOut, AllQuestionsCompletedOut])
def create_practice_session(
    payload: PracticeCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Union[PracticeOut, AllQuestionsCompletedOut]:
    user_id = str(current_user.id)
    base_filter = [
        Question.archived.is_(False),
        or_(Question.type != "short_answer", Question.parent_question_id.isnot(None)),
    ]
    if payload.mode != "wrong_questions":
        base_filter.append(Question.parent_question_id.is_(None))

    if payload.mode == "chapter":
        if not payload.chapter_id:
            raise HTTPException(status_code=400, detail="chapter_id is required for chapter practice")
        base_filter.append(Question.chapter_id == payload.chapter_id)
    if payload.question_types:
        base_filter.append(Question.type.in_(payload.question_types))

    if payload.source_scope == "original_only":
        filters = base_filter + [Question.is_ai_generated.is_(False)]
    elif payload.source_scope == "ai_new":
        # AI新题模式：只使用新生成的AI题
        pass
    elif payload.source_scope == "ai_pool":
        # 社区AI题库模式：只显示已公开的AI题（candidate/community_approved/verified）
        public_ai = and_(
            Question.is_ai_generated.is_(True),
            Question.ai_status.in_(["candidate", "community_approved", "verified"]),
        )
        filters = base_filter + [public_ai]
    else:
        verified_ai = and_(
            Question.is_ai_generated.is_(True),
            Question.ai_status.in_(["verified", "community_approved"]),
        )
        filters = base_filter + [or_(Question.is_ai_generated.is_(False), verified_ai)]

    if payload.mode == "wrong_questions":
        wrong_ids = select(WrongQuestion.question_id).where(
            WrongQuestion.user_id == user_id,
            WrongQuestion.mastered.is_(False),
        )
        filters.append(Question.id.in_(wrong_ids))

    # AI新题模式：只生成新的AI题
    if payload.source_scope == "ai_new" and payload.mode != "wrong_questions":
        questions = []
        settings = get_settings()
        if not settings.ai_enabled or not settings.ai_api_key:
            raise HTTPException(status_code=503, detail="AI service is not configured")

        # 检查每日限额
        used = get_daily_ai_count(db, user_id)
        if used >= DAILY_AI_LIMIT:
            raise HTTPException(status_code=429, detail=f"Daily AI generation limit reached ({DAILY_AI_LIMIT}/day)")

        actual_count = min(payload.question_count, DAILY_AI_LIMIT - used, 5)

        # 选择章节
        target_chapter_id = payload.chapter_id
        if target_chapter_id is None:
            target_chapter_id = db.scalar(
                select(Chapter.id)
                .outerjoin(Question, Question.chapter_id == Chapter.id)
                .group_by(Chapter.id)
                .order_by(func.count(Question.id))
                .limit(1)
            )

        if not target_chapter_id:
            raise HTTPException(status_code=404, detail="No chapters available")

        chapter = db.get(Chapter, target_chapter_id)
        if not chapter:
            raise HTTPException(status_code=404, detail="Chapter not found")

        chunks = db.scalars(
            select(KnowledgeChunk)
            .where(KnowledgeChunk.chapter_id == target_chapter_id)
            .order_by(KnowledgeChunk.chunk_id)
            .limit(12)
        ).all()

        if not chunks:
            raise HTTPException(status_code=404, detail="No knowledge chunks available for this chapter")

        draft_payload = AiQuestionDraftCreate(
            chapter_id=target_chapter_id,
            count=actual_count,
        )

        try:
            drafts = generate_question_drafts(draft_payload, chapter, chunks, settings)
            for draft in drafts[:actual_count]:
                question = Question(
                    chapter_id=draft.chapter_id,
                    knowledge_point_id=None,
                    parent_question_id=None,
                    type=draft.type,
                    difficulty=draft.difficulty,
                    stem=draft.stem,
                    options_json=draft.options_json,
                    answer_json=draft.answer_json,
                    rubric_json=draft.rubric_json,
                    explanation=draft.explanation,
                    source_context=draft.source_context,
                    source_assignment="AI新题练习",
                    is_ai_generated=True,
                    is_reviewed=True,
                    ai_status="temporary",
                    quality_score=0,
                )
                db.add(question)
                db.flush()
                questions.append(question)
        except AiGenerationError as exc:
            raise HTTPException(status_code=502, detail=str(exc))

        if not questions:
            raise HTTPException(status_code=404, detail="Failed to generate AI questions")

    elif payload.source_scope == "standard" and payload.mode != "wrong_questions":
        ai_available = db.scalar(
            select(func.count()).where(and_(*filters, Question.is_ai_generated.is_(True)))
        ) or 0
        ai_count_needed = min(max(1, payload.question_count // 5), ai_available) if ai_available > 0 else 0
        original_count_needed = payload.question_count - ai_count_needed

        original_questions = select_adaptive_questions(
            db,
            filters + [Question.is_ai_generated.is_(False)],
            original_count_needed,
            user_id,
        )

        # If original questions are scarce, let reviewed AI questions fill the gap.
        shortfall = original_count_needed - len(original_questions)
        ai_questions = []
        if ai_count_needed > 0:
            ai_questions = select_adaptive_questions(
                db,
                filters + [Question.is_ai_generated.is_(True)],
                ai_count_needed + shortfall,
                user_id,
            )

        questions = list(original_questions) + list(ai_questions)
        if not questions:
            questions = select_adaptive_questions(db, filters, payload.question_count, user_id)

        # 检查是否所有题目都已完成
        if not questions and payload.source_scope in ["original_only", "standard"]:
            total_available = db.scalar(
                select(func.count()).where(and_(*filters))
            ) or 0
            if total_available > 0:
                return AllQuestionsCompletedOut(
                    completed=True,
                    message="该章节/模式下的题目已全部完成！",
                    total_questions=total_available,
                    answered_questions=total_available,
                    suggestions=[
                        "错题复盘：回顾并重做错题",
                        "再刷一遍：重新练习所有题目",
                        "AI加练：生成新的AI题目进行练习",
                    ],
                )
    else:
        questions = select_adaptive_questions(db, filters, payload.question_count, user_id)

    if not questions:
        # 检查是否所有题目都已完成
        total_available = db.scalar(
            select(func.count()).where(and_(*filters))
        ) or 0
        if total_available > 0 and payload.source_scope in ["original_only", "standard"]:
            return AllQuestionsCompletedOut(
                completed=True,
                message="该章节/模式下的题目已全部完成！",
                total_questions=total_available,
                answered_questions=total_available,
                suggestions=[
                    "错题复盘：回顾并重做错题",
                    "再刷一遍：重新练习所有题目",
                    "AI加练：生成新的AI题目进行练习",
                ],
            )
        raise HTTPException(status_code=404, detail="No questions available for this practice")

    # Sort by type: 选择 → 判断 → 填空 → 其他
    TYPE_ORDER = {"single_choice": 0, "multiple_choice": 1, "true_false": 2, "fill_blank": 3, "cloze": 3}
    questions.sort(key=lambda q: TYPE_ORDER.get(q.type, 4))

    session = PracticeSession(
        user_id=user_id,
        mode=payload.mode,
        chapter_id=payload.chapter_id if payload.mode == "chapter" else None,
        question_count=len(questions),
    )
    db.add(session)
    db.flush()
    records_questions = answerable_questions(db, questions)
    for question in records_questions:
        db.add(AnswerRecord(session_id=session.id, question_id=question.id, user_answer={}))
    db.commit()
    db.refresh(session)

    feedback_map = load_feedback_map(db, collect_question_tree_ids(db, questions), user_id)
    return PracticeOut(
        id=session.id,
        mode=session.mode,
        chapter_id=session.chapter_id,
        question_count=session.question_count,
        score=session.score,
        started_at=session.started_at,
        submitted_at=session.submitted_at,
        questions=[question_tree_out(db, q, feedback_map) for q in questions],
    )


@router.get("/practice-sessions", response_model=list[PracticeHistoryItem])
def list_practice_sessions(
    current_user: User = Depends(get_current_user),
    limit: int = 20,
    db: Session = Depends(get_db),
) -> list[PracticeHistoryItem]:
    user_id = str(current_user.id)
    limit = min(max(limit, 1), 100)
    sessions = db.scalars(
        select(PracticeSession)
        .where(PracticeSession.user_id == user_id)
        .order_by(PracticeSession.started_at.desc(), PracticeSession.id.desc())
        .limit(limit)
    ).all()
    chapter_ids = {session.chapter_id for session in sessions if session.chapter_id is not None}
    chapter_rows = db.scalars(select(Chapter).where(Chapter.id.in_(chapter_ids))).all() if chapter_ids else []
    chapter_map = {chapter.id: chapter.title for chapter in chapter_rows}
    return [
        PracticeHistoryItem(
            id=session.id,
            mode=session.mode,
            chapter_id=session.chapter_id,
            chapter_title=chapter_map.get(session.chapter_id),
            question_count=session.question_count,
            score=float(session.score) if session.score is not None else None,
            started_at=session.started_at,
            submitted_at=session.submitted_at,
        )
        for session in sessions
    ]


@router.get("/practice-sessions/{session_id}/review", response_model=PracticeReviewOut)
def review_practice_session(
    session_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PracticeReviewOut:
    user_id = str(current_user.id)
    session = db.get(PracticeSession, session_id)
    if not session or session.user_id != user_id:
        raise HTTPException(status_code=404, detail="Practice session not found")

    records = db.scalars(
        select(AnswerRecord)
        .where(AnswerRecord.session_id == session_id)
        .order_by(AnswerRecord.id)
    ).all()
    questions = session_top_level_questions(db, records)
    feedback_map = load_feedback_map(db, collect_question_tree_ids(db, questions), user_id)
    submitted = session.submitted_at is not None
    return PracticeReviewOut(
        id=session.id,
        mode=session.mode,
        chapter_id=session.chapter_id,
        chapter_title=practice_chapter_title(db, session),
        question_count=session.question_count,
        score=float(session.score) if session.score is not None else None,
        started_at=session.started_at,
        submitted_at=session.submitted_at,
        questions=[question_tree_out(db, q, feedback_map, review=True) for q in questions],
        results=[
            AnswerReviewResult(
                question_id=record.question_id,
                user_answer=record.user_answer,
                is_correct=record.is_correct if submitted else None,
                score=float(record.score) if submitted and record.score is not None else None,
                feedback=record.feedback if submitted else None,
                correct_answer=public_answer(record.question.answer_json) if submitted else None,
                explanation=record.question.explanation if submitted else None,
            )
            for record in records
        ],
    )


@router.delete("/practice-sessions/{session_id}")
def delete_practice_session(
    session_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, bool]:
    user_id = str(current_user.id)
    session = db.get(PracticeSession, session_id)
    if not session or session.user_id != user_id:
        raise HTTPException(status_code=404, detail="Practice session not found")
    db.execute(delete(AnswerRecord).where(AnswerRecord.session_id == session_id))
    db.delete(session)
    db.commit()
    return {"deleted": True}


@router.get("/practice-sessions/{session_id}", response_model=PracticeOut)
def get_practice_session(
    session_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PracticeOut:
    user_id = str(current_user.id)
    session = db.get(PracticeSession, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Practice session not found")
    if session.user_id != user_id:
        raise HTTPException(status_code=404, detail="Practice session not found")
    if session.submitted_at is not None:
        raise HTTPException(status_code=400, detail="Practice session already submitted")
    records = db.scalars(
        select(AnswerRecord)
        .where(AnswerRecord.session_id == session_id)
        .order_by(AnswerRecord.id)
    ).all()
    questions = session_top_level_questions(db, records)
    feedback_map = load_feedback_map(db, collect_question_tree_ids(db, questions), user_id)
    return PracticeOut(
        id=session.id,
        mode=session.mode,
        chapter_id=session.chapter_id,
        question_count=session.question_count,
        score=session.score,
        started_at=session.started_at,
        submitted_at=session.submitted_at,
        questions=[question_tree_out(db, q, feedback_map) for q in questions],
    )


@router.post("/practice-sessions/{session_id}/submit", response_model=PracticeResult)
def submit_practice_session(
    session_id: int,
    payload: PracticeSubmit,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PracticeResult:
    user_id = str(current_user.id)
    session = db.get(PracticeSession, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Practice session not found")
    if session.user_id != user_id:
        raise HTTPException(status_code=404, detail="Practice session not found")
    if session.submitted_at is not None:
        raise HTTPException(status_code=400, detail="Practice session already submitted")

    answers_by_question = {answer.question_id: answer.user_answer for answer in payload.answers}
    records = db.scalars(select(AnswerRecord).where(AnswerRecord.session_id == session_id)).all()
    results: list[AnswerResult] = []

    total_score = 0.0
    for record in records:
        question = record.question
        user_answer = answers_by_question.get(question.id, {})
        is_correct, score, feedback = grade_answer(
            question.type,
            question.answer_json,
            user_answer,
            question.rubric_json,
        )
        record.user_answer = user_answer
        record.is_correct = is_correct
        record.score = score
        record.feedback = feedback
        total_score += score

        if question.is_ai_generated and question.ai_status:
            question.attempt_count += 1

        is_temporary_ai = question.is_ai_generated and question.ai_status == "temporary"

        if not is_correct and not is_temporary_ai:
            wrong = db.scalar(
                select(WrongQuestion).where(
                    WrongQuestion.user_id == user_id,
                    WrongQuestion.question_id == question.id,
                )
            )
            if wrong:
                wrong.wrong_count += 1
                wrong.last_wrong_at = datetime.now(timezone.utc)
                wrong.mastered = False
            else:
                db.add(WrongQuestion(user_id=user_id, question_id=question.id, wrong_count=1, mastered=False))

        results.append(
            AnswerResult(
                question_id=question.id,
                is_correct=is_correct,
                score=round(score, 2),
                feedback=feedback,
                correct_answer=public_answer(question.answer_json),
                explanation=question.explanation,
            )
        )

    session.score = round(total_score, 2)
    session.submitted_at = datetime.now(timezone.utc)
    db.commit()

    return PracticeResult(
        session_id=session.id,
        score=round(total_score, 2),
        total=len(records),
        results=results,
    )


@router.get("/wrong-questions", response_model=list[WrongQuestionOut])
def list_wrong_questions(
    mastered: bool | None = False,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[WrongQuestionOut]:
    user_id = str(current_user.id)
    conditions = [WrongQuestion.user_id == user_id]
    if mastered is not None:
        conditions.append(WrongQuestion.mastered.is_(mastered))
    rows = db.scalars(select(WrongQuestion).where(*conditions).order_by(WrongQuestion.last_wrong_at.desc())).all()
    feedback_map = load_feedback_map(db, [row.question_id for row in rows], user_id)
    return [
        WrongQuestionOut(
            id=row.id,
            question=question_review_out(row.question, **feedback_map.get(row.question_id, {"likes": 0, "user_liked": False})),
            wrong_count=row.wrong_count,
            mastered=row.mastered,
            last_wrong_at=row.last_wrong_at,
        )
        for row in rows
    ]


@router.post("/wrong-questions/{question_id}/mastered")
def mark_wrong_question_mastered(
    question_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, bool]:
    user_id = str(current_user.id)
    wrong = db.scalar(
        select(WrongQuestion).where(
            WrongQuestion.user_id == user_id,
            WrongQuestion.question_id == question_id,
        )
    )
    if not wrong:
        raise HTTPException(status_code=404, detail="Wrong question not found")
    wrong.mastered = True
    db.commit()
    return {"mastered": True}


@router.get("/statistics/overview", response_model=StatisticsOverview)
def statistics_overview(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> StatisticsOverview:
    user_id = str(current_user.id)
    total_sessions = db.scalar(select(func.count(PracticeSession.id)).where(PracticeSession.user_id == user_id)) or 0
    total_answers = db.scalar(
        select(func.count(AnswerRecord.id))
        .join(PracticeSession)
        .where(
            PracticeSession.user_id == user_id,
            AnswerRecord.is_correct.isnot(None),
        )
    ) or 0
    correct_answers = db.scalar(
        select(func.count(AnswerRecord.id))
        .join(PracticeSession)
        .where(PracticeSession.user_id == user_id, AnswerRecord.is_correct.is_(True))
    ) or 0
    wrong_count = db.scalar(
        select(func.count(WrongQuestion.id)).where(
            WrongQuestion.user_id == user_id,
            WrongQuestion.mastered.is_(False),
        )
    ) or 0
    return StatisticsOverview(
        total_sessions=total_sessions,
        total_answers=total_answers,
        correct_rate=round(correct_answers / total_answers, 4) if total_answers else 0,
        wrong_question_count=wrong_count,
    )


@router.get("/statistics/chapters", response_model=list[ChapterStatistics])
def chapter_statistics(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[ChapterStatistics]:
    user_id = str(current_user.id)
    chapters = db.scalars(select(Chapter).order_by(Chapter.order_index)).all()

    # 1. 统计每章的答题数据
    stats_rows = db.execute(
        select(
            Question.chapter_id,
            func.count(AnswerRecord.id).label("answered"),
            func.count()
            .filter(AnswerRecord.is_correct.is_(True))
            .label("correct"),
        )
        .join(AnswerRecord, AnswerRecord.question_id == Question.id)
        .join(PracticeSession, PracticeSession.id == AnswerRecord.session_id)
        .where(PracticeSession.user_id == user_id)
        .where(AnswerRecord.is_correct.isnot(None))
        .where(or_(Question.type != "short_answer", Question.parent_question_id.isnot(None)))
        .group_by(Question.chapter_id)
    ).all()
    stats_map = {row.chapter_id: row for row in stats_rows}

    # 2. 统计每章的题目总数（排除短答题）
    total_rows = db.execute(
        select(
            Question.chapter_id,
            func.count(Question.id).label("total"),
        )
        .where(
            Question.archived.is_(False),
            Question.parent_question_id.is_(None),
            Question.type != "short_answer",
        )
        .group_by(Question.chapter_id)
    ).all()
    total_map = {row.chapter_id: row.total for row in total_rows}

    # 3. 统计每章的错题掌握情况
    wrong_rows = db.execute(
        select(
            Question.chapter_id,
            func.count(WrongQuestion.id).label("total_wrong"),
            func.count()
            .filter(WrongQuestion.mastered.is_(True))
            .label("mastered"),
        )
        .join(Question, Question.id == WrongQuestion.question_id)
        .where(WrongQuestion.user_id == user_id)
        .group_by(Question.chapter_id)
    ).all()
    wrong_map = {row.chapter_id: row for row in wrong_rows}

    # 4. 计算综合掌握度
    results = []
    for chapter in chapters:
        stats = stats_map.get(chapter.id)
        total_questions = total_map.get(chapter.id, 0)
        wrong_stats = wrong_map.get(chapter.id)

        answered = stats.answered if stats else 0
        correct = stats.correct if stats else 0
        correct_rate = round(correct / answered, 4) if answered else 0

        # 题目覆盖率：已答题目数 / 总题目数
        coverage = round(answered / total_questions, 4) if total_questions else 0

        # 错题掌握率：已掌握错题数 / 总错题数
        total_wrong = wrong_stats.total_wrong if wrong_stats else 0
        mastered = wrong_stats.mastered if wrong_stats else 0
        mastered_rate = round(mastered / total_wrong, 4) if total_wrong else 1.0  # 无错题视为完全掌握

        # 综合掌握度计算 (0-100分)
        # 权重：正确率 50% + 覆盖率 30% + 错题掌握 20%
        if answered == 0:
            mastery_score = 0
        else:
            # 正确率得分 (0-50分)
            correct_score = correct_rate * 50

            # 覆盖率得分 (0-30分)
            coverage_score = min(coverage, 1.0) * 30

            # 错题掌握得分 (0-20分)
            mastery_score_base = mastered_rate * 20

            mastery_score = round(correct_score + coverage_score + mastery_score_base, 1)

        results.append(
            ChapterStatistics(
                chapter_id=chapter.id,
                chapter_title=chapter.title,
                answered=answered,
                total_questions=total_questions,
                correct_rate=correct_rate,
                coverage=coverage,
                mastered_rate=mastered_rate,
                mastery_score=mastery_score,
            )
        )

    return results


@router.get("/statistics/question-types", response_model=list[QuestionTypeStatistics])
def question_type_statistics(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[QuestionTypeStatistics]:
    user_id = str(current_user.id)
    rows = db.execute(
        select(
            Question.type.label("question_type"),
            func.count(AnswerRecord.id).label("answered"),
            func.count().filter(AnswerRecord.is_correct.is_(True)).label("correct"),
        )
        .join(AnswerRecord, AnswerRecord.question_id == Question.id)
        .join(PracticeSession, PracticeSession.id == AnswerRecord.session_id)
        .where(PracticeSession.user_id == user_id)
        .where(AnswerRecord.is_correct.isnot(None))
        .where(or_(Question.type != "short_answer", Question.parent_question_id.isnot(None)))
        .group_by(Question.type)
        .order_by(Question.type)
    ).all()
    return [
        QuestionTypeStatistics(
            question_type=row.question_type,
            answered=row.answered,
            correct_rate=round(row.correct / row.answered, 4) if row.answered else 0,
        )
        for row in rows
    ]


@router.get("/statistics/recommendations", response_model=list[StudyRecommendation])
def study_recommendations(
    limit: int = 4,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[StudyRecommendation]:
    user_id = str(current_user.id)
    limit = min(max(limit, 1), 9)
    chapters = db.scalars(select(Chapter).order_by(Chapter.order_index)).all()
    stats_rows = db.execute(
        select(
            Question.chapter_id,
            func.count(AnswerRecord.id).label("answered"),
            func.count().filter(AnswerRecord.is_correct.is_(True)).label("correct"),
        )
        .join(AnswerRecord, AnswerRecord.question_id == Question.id)
        .join(PracticeSession, PracticeSession.id == AnswerRecord.session_id)
        .where(PracticeSession.user_id == user_id)
        .where(AnswerRecord.is_correct.isnot(None))
        .where(or_(Question.type != "short_answer", Question.parent_question_id.isnot(None)))
        .group_by(Question.chapter_id)
    ).all()
    stats_map = {row.chapter_id: row for row in stats_rows}
    wrong_rows = db.execute(
        select(Question.chapter_id, func.sum(WrongQuestion.wrong_count).label("wrong_count"))
        .join(Question, Question.id == WrongQuestion.question_id)
        .where(WrongQuestion.user_id == user_id, WrongQuestion.mastered.is_(False))
        .group_by(Question.chapter_id)
    ).all()
    wrong_map = {row.chapter_id: int(row.wrong_count or 0) for row in wrong_rows}

    recommendations: list[StudyRecommendation] = []
    for chapter in chapters:
        row = stats_map.get(chapter.id)
        answered = row.answered if row else 0
        correct = row.correct if row else 0
        correct_rate = round(correct / answered, 4) if answered else 0
        wrong_count = wrong_map.get(chapter.id, 0)

        if answered == 0:
            reason = "还没有练习记录"
            action = "先做 5 道基础混合题建立基线"
            priority = 100.0
        elif wrong_count > 0:
            reason = f"还有 {wrong_count} 次错题记录"
            action = "优先错题重练，再做同章专项补充"
            priority = 80 + min(wrong_count, 10) * 2 - correct_rate * 10
        elif correct_rate < 0.7:
            reason = f"章节正确率 {round(correct_rate * 100)}%"
            action = "回看知识库后做一组标准练习"
            priority = 70 - correct_rate * 30
        elif answered < 10:
            reason = f"只做过 {answered} 道题"
            action = "补一组标准练习，让统计更可靠"
            priority = 45 - answered
        else:
            continue

        recommendations.append(
            StudyRecommendation(
                chapter_id=chapter.id,
                chapter_title=chapter.title,
                answered=answered,
                correct_rate=correct_rate,
                wrong_count=wrong_count,
                reason=reason,
                action=action,
                priority=round(priority, 2),
            )
        )

    return sorted(recommendations, key=lambda item: item.priority, reverse=True)[:limit]
