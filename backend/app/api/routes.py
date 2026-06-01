from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.entities import AnswerRecord, Chapter, KnowledgeChunk, KnowledgePoint, PracticeSession, Question, WrongQuestion
from app.schemas.api import (
    AnswerResult,
    ChapterOut,
    ChapterStatistics,
    KnowledgeChunkOut,
    KnowledgePointOut,
    KnowledgeSearchOut,
    QuestionAdminListOut,
    QuestionAdminOut,
    QuestionUpdate,
    PracticeCreate,
    PracticeOut,
    PracticeResult,
    PracticeSubmit,
    QuestionOut,
    QuestionReviewOut,
    StatisticsOverview,
    WrongQuestionOut,
)
from app.services.grading import grade_answer, public_answer

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
    labels = {
        "ai": "AI生成",
        "homework": "作业原题",
        "sample": "样例题",
        "manual": "人工维护",
    }
    return labels[question_source_type(question)]


def source_type_conditions(source_type: str):
    homework_condition = or_(
        Question.source_context.ilike("%homework-examples%"),
        Question.source_assignment.ilike("%作业%"),
    )
    sample_condition = Question.source_context.ilike("%phase-1 sample seed%")
    if source_type == "ai":
        return Question.is_ai_generated.is_(True)
    if source_type == "homework":
        return and_(Question.is_ai_generated.is_(False), homework_condition)
    if source_type == "sample":
        return and_(Question.is_ai_generated.is_(False), sample_condition)
    if source_type == "manual":
        return and_(
            Question.is_ai_generated.is_(False),
            or_(Question.source_context.is_(None), ~Question.source_context.ilike("%phase-1 sample seed%")),
            or_(Question.source_context.is_(None), ~Question.source_context.ilike("%homework-examples%")),
            or_(Question.source_assignment.is_(None), ~Question.source_assignment.ilike("%作业%")),
        )
    return None


def question_out(question: Question) -> QuestionOut:
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
    )


def question_review_out(question: Question) -> QuestionReviewOut:
    base = question_out(question).model_dump()
    return QuestionReviewOut(**base, answer=public_answer(question.answer_json))


def question_admin_out(question: Question) -> QuestionAdminOut:
    base = question_out(question).model_dump()
    return QuestionAdminOut(
        **base,
        answer_json=question.answer_json,
        rubric_json=question.rubric_json,
        is_ai_generated=question.is_ai_generated,
        is_reviewed=question.is_reviewed,
        source_assignment=question.source_assignment,
        source_context=question.source_context,
        created_at=question.created_at,
        updated_at=question.updated_at,
    )


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


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/chapters", response_model=list[ChapterOut])
def list_chapters(db: Session = Depends(get_db)) -> list[ChapterOut]:
    counts = dict(
        db.execute(
            select(Question.chapter_id, func.count(Question.id))
            .where(Question.is_reviewed.is_(True))
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
            Question.is_reviewed.is_(True),
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
    db: Session = Depends(get_db),
) -> list[QuestionReviewOut]:
    conditions = [Question.is_reviewed.is_(True)]
    if chapter_id:
        conditions.append(Question.chapter_id == chapter_id)
    if question_type:
        conditions.append(Question.type == question_type)
    questions = db.scalars(select(Question).where(*conditions).order_by(Question.id)).all()
    return [question_review_out(question) for question in questions]


@router.get("/admin/questions", response_model=QuestionAdminListOut)
def admin_list_questions(
    chapter_id: int | None = None,
    question_type: str | None = None,
    source_type: str | None = None,
    reviewed: bool | None = None,
    keyword: str | None = None,
    limit: int = 30,
    offset: int = 0,
    db: Session = Depends(get_db),
) -> QuestionAdminListOut:
    limit = min(max(limit, 1), 100)
    offset = max(offset, 0)
    conditions = []
    if chapter_id:
        conditions.append(Question.chapter_id == chapter_id)
    if question_type:
        conditions.append(Question.type == question_type)
    if source_type:
        source_condition = source_type_conditions(source_type)
        if source_condition is None:
            raise HTTPException(status_code=400, detail="Unsupported source_type")
        conditions.append(source_condition)
    if reviewed is not None:
        conditions.append(Question.is_reviewed.is_(reviewed))
    if keyword:
        conditions.append(Question.stem.ilike(f"%{keyword}%"))

    total = db.scalar(select(func.count(Question.id)).where(*conditions)) or 0
    questions = db.scalars(
        select(Question)
        .where(*conditions)
        .order_by(Question.updated_at.desc(), Question.id.desc())
        .limit(limit)
        .offset(offset)
    ).all()
    return QuestionAdminListOut(items=[question_admin_out(question) for question in questions], total=total)


@router.get("/admin/questions/{question_id}", response_model=QuestionAdminOut)
def admin_get_question(question_id: int, db: Session = Depends(get_db)) -> QuestionAdminOut:
    question = db.get(Question, question_id)
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")
    return question_admin_out(question)


@router.patch("/admin/questions/{question_id}", response_model=QuestionAdminOut)
def admin_update_question(
    question_id: int,
    payload: QuestionUpdate,
    db: Session = Depends(get_db),
) -> QuestionAdminOut:
    question = db.get(Question, question_id)
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")

    data = payload.model_dump(exclude_unset=True)
    for field, value in data.items():
        if field == "options_json" and value is None:
            value = []
        if field == "answer_json" and value is None:
            value = {}
        if field == "rubric_json" and value is None:
            value = []
        setattr(question, field, value)
    question.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(question)
    return question_admin_out(question)


@router.post("/practice-sessions", response_model=PracticeOut)
def create_practice_session(payload: PracticeCreate, db: Session = Depends(get_db)) -> PracticeOut:
    filters = [Question.is_reviewed.is_(True)]
    if payload.mode == "chapter":
        if not payload.chapter_id:
            raise HTTPException(status_code=400, detail="chapter_id is required for chapter practice")
        filters.append(Question.chapter_id == payload.chapter_id)
    if payload.question_types:
        filters.append(Question.type.in_(payload.question_types))
    if payload.mode == "wrong_questions":
        wrong_ids = select(WrongQuestion.question_id).where(
            WrongQuestion.user_id == payload.user_id,
            WrongQuestion.mastered.is_(False),
        )
        filters.append(Question.id.in_(wrong_ids))

    questions = db.scalars(
        select(Question)
        .where(and_(*filters))
        .order_by(func.random())
        .limit(payload.question_count)
    ).all()
    if not questions:
        raise HTTPException(status_code=404, detail="No reviewed questions available for this practice")

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

    return PracticeOut(
        id=session.id,
        mode=session.mode,
        chapter_id=session.chapter_id,
        question_count=session.question_count,
        score=session.score,
        started_at=session.started_at,
        submitted_at=session.submitted_at,
        questions=[question_out(question) for question in questions],
    )


@router.get("/practice-sessions/{session_id}", response_model=PracticeOut)
def get_practice_session(session_id: int, db: Session = Depends(get_db)) -> PracticeOut:
    session = db.get(PracticeSession, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Practice session not found")
    questions = [answer.question for answer in session.answers]
    return PracticeOut(
        id=session.id,
        mode=session.mode,
        chapter_id=session.chapter_id,
        question_count=session.question_count,
        score=session.score,
        started_at=session.started_at,
        submitted_at=session.submitted_at,
        questions=[question_out(question) for question in questions],
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

        if not is_correct:
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
    return [
        WrongQuestionOut(
            id=row.id,
            question=question_review_out(row.question),
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
    rows: list[ChapterStatistics] = []
    for chapter in chapters:
        answered = db.scalar(
            select(func.count(AnswerRecord.id))
            .join(PracticeSession)
            .join(Question, Question.id == AnswerRecord.question_id)
            .where(
                PracticeSession.user_id == user_id,
                Question.chapter_id == chapter.id,
                or_(AnswerRecord.is_correct.is_(True), AnswerRecord.is_correct.is_(False)),
            )
        ) or 0
        correct = db.scalar(
            select(func.count(AnswerRecord.id))
            .join(PracticeSession)
            .join(Question, Question.id == AnswerRecord.question_id)
            .where(
                PracticeSession.user_id == user_id,
                Question.chapter_id == chapter.id,
                AnswerRecord.is_correct.is_(True),
            )
        ) or 0
        rows.append(
            ChapterStatistics(
                chapter_id=chapter.id,
                chapter_title=chapter.title,
                answered=answered,
                correct_rate=round(correct / answered, 4) if answered else 0,
            )
        )
    return rows
