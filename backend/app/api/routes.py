from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_db
from app.models.entities import AnswerRecord, Chapter, KnowledgeChunk, KnowledgePoint, PracticeSession, Question, QuestionFeedback, WrongQuestion
from app.schemas.api import (
    AiQuestionDraftCreate,
    AiQuestionDraftOut,
    AiStatusOut,
    AnswerResult,
    ChapterOut,
    ChapterStatistics,
    KnowledgeChunkOut,
    KnowledgePointOut,
    KnowledgeSearchOut,
    PracticeCreate,
    PracticeOut,
    PracticeResult,
    PracticeSubmit,
    QuestionFeedbackCreate,
    QuestionFeedbackOut,
    QuestionOut,
    QuestionReviewOut,
    StatisticsOverview,
    WrongQuestionOut,
)
from app.services.ai_generation import AiGenerationError, generate_question_drafts
from app.services.grading import grade_answer, public_answer

UNHELPFUL_ARCHIVE_THRESHOLD = 3
DAILY_AI_LIMIT = 30

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


def question_out(question: Question, likes: int = 0, user_liked: bool = False) -> QuestionOut:
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
    )


def question_review_out(question: Question, likes: int = 0, user_liked: bool = False) -> QuestionReviewOut:
    base = question_out(question, likes, user_liked).model_dump()
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


def load_feedback_map(db: Session, question_ids: list[int], user_id: str = "demo") -> dict[int, dict]:
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


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/ai-status", response_model=AiStatusOut)
def ai_status(user_id: str = "demo", db: Session = Depends(get_db)) -> AiStatusOut:
    settings = get_settings()
    if not settings.ai_enabled or not settings.ai_api_key:
        return AiStatusOut(enabled=False, daily_remaining=0)
    used = get_daily_ai_count(db, user_id)
    return AiStatusOut(enabled=True, daily_remaining=max(0, DAILY_AI_LIMIT - used))


@router.get("/chapters", response_model=list[ChapterOut])
def list_chapters(db: Session = Depends(get_db)) -> list[ChapterOut]:
    counts = dict(
        db.execute(
            select(Question.chapter_id, func.count(Question.id))
            .where(Question.archived.is_(False))
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


@router.get("/questions", response_model=list[QuestionReviewOut])
def list_questions(
    chapter_id: int | None = None,
    question_type: str | None = None,
    user_id: str = "demo",
    db: Session = Depends(get_db),
) -> list[QuestionReviewOut]:
    conditions = [Question.archived.is_(False)]
    if chapter_id:
        conditions.append(Question.chapter_id == chapter_id)
    if question_type:
        conditions.append(Question.type == question_type)
    questions = db.scalars(select(Question).where(*conditions).order_by(Question.id)).all()
    feedback_map = load_feedback_map(db, [q.id for q in questions], user_id)
    return [question_review_out(q, **feedback_map.get(q.id, {"likes": 0, "user_liked": False})) for q in questions]


@router.post("/questions/{question_id}/feedback", response_model=QuestionFeedbackOut)
def submit_feedback(
    question_id: int,
    payload: QuestionFeedbackCreate,
    user_id: str = "demo",
    db: Session = Depends(get_db),
) -> QuestionFeedbackOut:
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
    user_id: str = "demo",
    db: Session = Depends(get_db),
) -> dict[str, bool]:
    existing = db.scalar(
        select(QuestionFeedback).where(
            QuestionFeedback.user_id == user_id,
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
    db: Session = Depends(get_db),
) -> AiQuestionDraftOut:
    settings = get_settings()
    if not settings.ai_enabled or not settings.ai_api_key:
        raise HTTPException(status_code=503, detail="AI service is not configured")

    used = get_daily_ai_count(db, payload.user_id)
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


@router.post("/practice-sessions", response_model=PracticeOut)
def create_practice_session(payload: PracticeCreate, db: Session = Depends(get_db)) -> PracticeOut:
    base_filter = [Question.archived.is_(False)]

    if payload.mode == "chapter":
        if not payload.chapter_id:
            raise HTTPException(status_code=400, detail="chapter_id is required for chapter practice")
        base_filter.append(Question.chapter_id == payload.chapter_id)
    if payload.question_types:
        base_filter.append(Question.type.in_(payload.question_types))

    if payload.source_scope == "original_only":
        filters = base_filter + [Question.is_ai_generated.is_(False)]
    elif payload.source_scope == "supplement":
        ai_filter = and_(
            Question.is_ai_generated.is_(True),
            Question.ai_status.in_(["temporary", "candidate", "community_approved", "verified"]),
        )
        filters = base_filter + [or_(Question.is_ai_generated.is_(False), ai_filter)]
    else:
        verified_ai = and_(
            Question.is_ai_generated.is_(True),
            Question.ai_status.in_(["verified", "community_approved"]),
        )
        filters = base_filter + [or_(Question.is_ai_generated.is_(False), verified_ai)]

    if payload.mode == "wrong_questions":
        wrong_ids = select(WrongQuestion.question_id).where(
            WrongQuestion.user_id == payload.user_id,
            WrongQuestion.mastered.is_(False),
        )
        filters.append(Question.id.in_(wrong_ids))

    if payload.source_scope == "standard" and payload.mode != "wrong_questions":
        ai_available = db.scalar(
            select(func.count()).where(and_(*filters, Question.is_ai_generated.is_(True)))
        ) or 0
        ai_count_needed = min(max(1, payload.question_count // 5), ai_available) if ai_available > 0 else 0
        original_count_needed = payload.question_count - ai_count_needed

        original_questions = db.scalars(
            select(Question)
            .where(and_(*filters, Question.is_ai_generated.is_(False)))
            .order_by(func.random())
            .limit(original_count_needed)
        ).all()

        # Fill remaining slots with original if not enough AI
        shortfall = original_count_needed - len(original_questions)
        ai_questions = []
        if ai_count_needed > 0:
            ai_questions = db.scalars(
                select(Question)
                .where(and_(*filters, Question.is_ai_generated.is_(True)))
                .order_by(func.random())
                .limit(ai_count_needed + shortfall)
            ).all()

        questions = list(original_questions) + list(ai_questions)
        if not questions:
            questions = db.scalars(
                select(Question).where(and_(*filters)).order_by(func.random()).limit(payload.question_count)
            ).all()
    else:
        questions = db.scalars(
            select(Question)
            .where(and_(*filters))
            .order_by(func.random())
            .limit(payload.question_count)
        ).all()

    if not questions:
        raise HTTPException(status_code=404, detail="No questions available for this practice")

    # Sort by type: 选择 → 判断 → 填空 → 其他
    TYPE_ORDER = {"single_choice": 0, "multiple_choice": 1, "true_false": 2, "fill_blank": 3, "cloze": 3}
    questions.sort(key=lambda q: TYPE_ORDER.get(q.type, 4))

    session = PracticeSession(
        user_id=payload.user_id,
        mode=payload.mode,
        chapter_id=payload.chapter_id if payload.mode == "chapter" else None,
        question_count=len(questions),
    )
    db.add(session)
    db.flush()
    for question in questions:
        db.add(AnswerRecord(session_id=session.id, question_id=question.id, user_answer={}))
    db.commit()
    db.refresh(session)

    feedback_map = load_feedback_map(db, [q.id for q in questions], payload.user_id)
    return PracticeOut(
        id=session.id,
        mode=session.mode,
        chapter_id=session.chapter_id,
        question_count=session.question_count,
        score=session.score,
        started_at=session.started_at,
        submitted_at=session.submitted_at,
        questions=[question_out(q, **feedback_map.get(q.id, {"likes": 0, "user_liked": False})) for q in questions],
    )


@router.get("/practice-sessions/{session_id}", response_model=PracticeOut)
def get_practice_session(session_id: int, user_id: str = "demo", db: Session = Depends(get_db)) -> PracticeOut:
    session = db.get(PracticeSession, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Practice session not found")
    questions = [answer.question for answer in session.answers]
    feedback_map = load_feedback_map(db, [q.id for q in questions], user_id)
    return PracticeOut(
        id=session.id,
        mode=session.mode,
        chapter_id=session.chapter_id,
        question_count=session.question_count,
        score=session.score,
        started_at=session.started_at,
        submitted_at=session.submitted_at,
        questions=[question_out(q, **feedback_map.get(q.id, {"likes": 0, "user_liked": False})) for q in questions],
    )


@router.post("/practice-sessions/{session_id}/submit", response_model=PracticeResult)
def submit_practice_session(
    session_id: int,
    payload: PracticeSubmit,
    db: Session = Depends(get_db),
) -> PracticeResult:
    session = db.get(PracticeSession, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Practice session not found")

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
                    WrongQuestion.user_id == payload.user_id,
                    WrongQuestion.question_id == question.id,
                )
            )
            if wrong:
                wrong.wrong_count += 1
                wrong.last_wrong_at = datetime.now(timezone.utc)
                wrong.mastered = False
            else:
                db.add(WrongQuestion(user_id=payload.user_id, question_id=question.id, wrong_count=1, mastered=False))

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
    user_id: str = "demo",
    mastered: bool | None = False,
    db: Session = Depends(get_db),
) -> list[WrongQuestionOut]:
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
    user_id: str = "demo",
    db: Session = Depends(get_db),
) -> dict[str, bool]:
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
def statistics_overview(user_id: str = "demo", db: Session = Depends(get_db)) -> StatisticsOverview:
    total_sessions = db.scalar(select(func.count(PracticeSession.id)).where(PracticeSession.user_id == user_id)) or 0
    total_answers = db.scalar(
        select(func.count(AnswerRecord.id)).join(PracticeSession).where(PracticeSession.user_id == user_id)
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
def chapter_statistics(user_id: str = "demo", db: Session = Depends(get_db)) -> list[ChapterStatistics]:
    chapters = db.scalars(select(Chapter).order_by(Chapter.order_index)).all()

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
        .group_by(Question.chapter_id)
    ).all()
    stats_map = {row.chapter_id: row for row in stats_rows}

    return [
        ChapterStatistics(
            chapter_id=chapter.id,
            chapter_title=chapter.title,
            answered=stats_map[chapter.id].answered if chapter.id in stats_map else 0,
            correct_rate=(
                round(stats_map[chapter.id].correct / stats_map[chapter.id].answered, 4)
                if chapter.id in stats_map and stats_map[chapter.id].answered
                else 0
            ),
        )
        for chapter in chapters
    ]
