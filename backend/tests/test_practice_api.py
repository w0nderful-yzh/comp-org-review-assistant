from __future__ import annotations

from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import delete, select

from app.core.database import SessionLocal
from app.main import app
from app.models.entities import AnswerRecord, Chapter, PracticeSession, Question, WrongQuestion


client = TestClient(app)


def cleanup_test_data(chapter_id: int, user_id: str) -> None:
    with SessionLocal() as db:
        session_ids = list(
            db.scalars(select(PracticeSession.id).where(PracticeSession.user_id == user_id)).all()
        )
        if session_ids:
            db.execute(delete(AnswerRecord).where(AnswerRecord.session_id.in_(session_ids)))
            db.execute(delete(PracticeSession).where(PracticeSession.id.in_(session_ids)))
        question_ids = list(db.scalars(select(Question.id).where(Question.chapter_id == chapter_id)).all())
        if question_ids:
            db.execute(delete(WrongQuestion).where(WrongQuestion.question_id.in_(question_ids)))
            db.execute(delete(Question).where(Question.id.in_(question_ids)))
        db.execute(delete(Chapter).where(Chapter.id == chapter_id))
        db.commit()


def seed_test_question(chapter_id: int) -> int:
    with SessionLocal() as db:
        db.add(
            Chapter(
                id=chapter_id,
                title="测试章节",
                description="pytest temporary chapter",
                order_index=chapter_id,
                source_file=f"pytest-{chapter_id}.md",
            )
        )
        question = Question(
            chapter_id=chapter_id,
            knowledge_point_id=None,
            parent_question_id=None,
            type="single_choice",
            difficulty="easy",
            stem=f"pytest 临时题 {chapter_id}",
            options_json=[
                {"key": "A", "text": "正确"},
                {"key": "B", "text": "错误"},
            ],
            answer_json={"answer": "A"},
            rubric_json=[],
            explanation="选择 A。",
            source_context=f"pytest#{chapter_id}",
            source_assignment="pytest",
            is_ai_generated=False,
            is_reviewed=True,
        )
        db.add(question)
        db.commit()
        db.refresh(question)
        return question.id


def create_session(chapter_id: int, user_id: str) -> int:
    response = client.post(
        "/api/practice-sessions",
        json={
            "mode": "chapter",
            "chapter_id": chapter_id,
            "question_count": 1,
            "question_types": ["single_choice"],
            "user_id": user_id,
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["question_count"] == 1
    return body["id"]


def submit_answer(session_id: int, question_id: int, user_id: str, answer: str) -> dict:
    response = client.post(
        f"/api/practice-sessions/{session_id}/submit",
        json={"user_id": user_id, "answers": [{"question_id": question_id, "user_answer": answer}]},
    )
    assert response.status_code == 200
    return response.json()


def test_wrong_question_count_and_mastered_flow() -> None:
    chapter_id = 900
    user_id = f"pytest-{uuid4()}"
    cleanup_test_data(chapter_id, user_id)

    try:
        question_id = seed_test_question(chapter_id)

        first_session_id = create_session(chapter_id, user_id)
        first_result = submit_answer(first_session_id, question_id, user_id, "B")
        assert first_result["results"][0]["is_correct"] is False

        second_session_id = create_session(chapter_id, user_id)
        second_result = submit_answer(second_session_id, question_id, user_id, "B")
        assert second_result["results"][0]["is_correct"] is False

        wrong_response = client.get(f"/api/wrong-questions?user_id={user_id}")
        assert wrong_response.status_code == 200
        wrong_items = wrong_response.json()
        assert len(wrong_items) == 1
        assert wrong_items[0]["question"]["id"] == question_id
        assert wrong_items[0]["wrong_count"] == 2
        assert wrong_items[0]["mastered"] is False

        mastered_response = client.post(f"/api/wrong-questions/{question_id}/mastered?user_id={user_id}")
        assert mastered_response.status_code == 200
        assert mastered_response.json() == {"mastered": True}

        active_wrong_response = client.get(f"/api/wrong-questions?user_id={user_id}")
        assert active_wrong_response.status_code == 200
        assert active_wrong_response.json() == []
    finally:
        cleanup_test_data(chapter_id, user_id)
