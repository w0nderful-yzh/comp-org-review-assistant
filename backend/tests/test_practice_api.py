from __future__ import annotations

from types import SimpleNamespace
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import delete, select

from app.api.deps import get_current_user
from app.core.database import SessionLocal
from app.main import app
from app.models.entities import AnswerRecord, Chapter, PracticeSession, Question, QuestionFeedback, WrongQuestion


_current_test_user_id = "pytest-default"


def set_test_user(user_id: str) -> None:
    global _current_test_user_id
    _current_test_user_id = user_id


def current_test_user() -> SimpleNamespace:
    return SimpleNamespace(id=_current_test_user_id)


app.dependency_overrides[get_current_user] = current_test_user
client = TestClient(app)


def cleanup_test_data(chapter_id: int, user_id: str) -> None:
    set_test_user(user_id)
    with SessionLocal() as db:
        session_ids = list(
            db.scalars(select(PracticeSession.id).where(PracticeSession.user_id == user_id)).all()
        )
        if session_ids:
            db.execute(delete(AnswerRecord).where(AnswerRecord.session_id.in_(session_ids)))
            db.execute(delete(PracticeSession).where(PracticeSession.id.in_(session_ids)))
        question_ids = list(db.scalars(select(Question.id).where(Question.chapter_id == chapter_id)).all())
        if question_ids:
            db.execute(delete(QuestionFeedback).where(QuestionFeedback.question_id.in_(question_ids)))
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


def seed_source_question(chapter_id: int, source_context: str, source_assignment: str | None, is_ai_generated: bool) -> int:
    with SessionLocal() as db:
        if not db.get(Chapter, chapter_id):
            db.add(
                Chapter(
                    id=chapter_id,
                    title="来源标记测试",
                    description="pytest temporary source chapter",
                    order_index=chapter_id,
                    source_file=f"pytest-source-{chapter_id}.md",
                )
            )
        question = Question(
            chapter_id=chapter_id,
            knowledge_point_id=None,
            parent_question_id=None,
            type="single_choice",
            difficulty="medium",
            stem=f"pytest 来源题 {chapter_id}",
            options_json=[{"key": "A", "text": "正确"}],
            answer_json={"answer": "A"},
            rubric_json=[],
            explanation=None,
            source_context=source_context,
            source_assignment=source_assignment,
            is_ai_generated=is_ai_generated,
            is_reviewed=True,
            ai_status="verified" if is_ai_generated else None,
        )
        db.add(question)
        db.commit()
        db.refresh(question)
        return question.id


def seed_reading_group(chapter_id: int) -> tuple[int, int, int]:
    with SessionLocal() as db:
        if not db.get(Chapter, chapter_id):
            db.add(
                Chapter(
                    id=chapter_id,
                    title="阅读理解测试",
                    description="pytest temporary reading chapter",
                    order_index=chapter_id,
                    source_file=f"pytest-reading-{chapter_id}.md",
                )
            )
        parent = Question(
            chapter_id=chapter_id,
            knowledge_point_id=None,
            parent_question_id=None,
            type="question_group",
            difficulty="medium",
            stem="阅读材料：某计算机主频为 2GHz，CPI 为 2。",
            options_json=[],
            answer_json={},
            rubric_json=[],
            explanation=None,
            source_context=f"pytest-reading-{chapter_id}#parent",
            source_assignment="pytest阅读理解",
            is_ai_generated=False,
            is_reviewed=True,
        )
        db.add(parent)
        db.flush()
        first = Question(
            chapter_id=chapter_id,
            knowledge_point_id=None,
            parent_question_id=parent.id,
            type="single_choice",
            difficulty="medium",
            stem="时钟周期是多少？",
            options_json=[{"key": "A", "text": "0.5ns"}, {"key": "B", "text": "1ns"}],
            answer_json={"answer": "A"},
            rubric_json=[],
            explanation="2GHz 对应 0.5ns。",
            source_context=f"pytest-reading-{chapter_id}#1",
            source_assignment="pytest阅读理解",
            is_ai_generated=False,
            is_reviewed=True,
        )
        second = Question(
            chapter_id=chapter_id,
            knowledge_point_id=None,
            parent_question_id=parent.id,
            type="calculation",
            difficulty="medium",
            stem="执行 100 条指令需要多少 ns？",
            options_json=[],
            answer_json={"reference_answer": "100 ns"},
            rubric_json={"tolerance": 0.01},
            explanation="100 条 × CPI 2 × 0.5ns = 100ns。",
            source_context=f"pytest-reading-{chapter_id}#2",
            source_assignment="pytest阅读理解",
            is_ai_generated=False,
            is_reviewed=True,
        )
        db.add_all([first, second])
        db.commit()
        db.refresh(parent)
        db.refresh(first)
        db.refresh(second)
        return parent.id, first.id, second.id


def create_session(chapter_id: int, user_id: str) -> int:
    set_test_user(user_id)
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
    set_test_user(user_id)
    response = client.post(
        f"/api/practice-sessions/{session_id}/submit",
        json={"user_id": user_id, "answers": [{"question_id": question_id, "user_answer": answer}]},
    )
    assert response.status_code == 200
    return response.json()


def seed_answer_record(question_id: int, user_id: str, is_correct: bool) -> None:
    with SessionLocal() as db:
        session = PracticeSession(user_id=user_id, mode="chapter", chapter_id=None, question_count=1, score=1 if is_correct else 0)
        db.add(session)
        db.flush()
        db.add(
            AnswerRecord(
                session_id=session.id,
                question_id=question_id,
                user_answer="A" if is_correct else "B",
                is_correct=is_correct,
                score=1 if is_correct else 0,
                feedback="pytest",
            )
        )
        db.commit()


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


def test_practice_history_and_review_flow() -> None:
    chapter_id = 907
    user_id = f"pytest-{uuid4()}"
    cleanup_test_data(chapter_id, user_id)

    try:
        question_id = seed_test_question(chapter_id)
        session_id = create_session(chapter_id, user_id)
        submit_answer(session_id, question_id, user_id, "A")

        history_response = client.get(f"/api/practice-sessions?user_id={user_id}")
        assert history_response.status_code == 200
        history = history_response.json()
        assert history[0]["id"] == session_id
        assert history[0]["question_count"] == 1
        assert history[0]["score"] == 1.0

        review_response = client.get(f"/api/practice-sessions/{session_id}/review?user_id={user_id}")
        assert review_response.status_code == 200
        review = review_response.json()
        assert review["id"] == session_id
        assert review["questions"][0]["id"] == question_id
        assert review["results"][0]["user_answer"] == "A"
        assert review["results"][0]["correct_answer"] == "A"
    finally:
        cleanup_test_data(chapter_id, user_id)


def test_submit_rejects_other_user_and_repeat_submit() -> None:
    chapter_id = 911
    owner_id = f"pytest-{uuid4()}"
    other_id = f"pytest-{uuid4()}"
    cleanup_test_data(chapter_id, owner_id)
    cleanup_test_data(chapter_id, other_id)

    try:
        question_id = seed_test_question(chapter_id)
        session_id = create_session(chapter_id, owner_id)

        set_test_user(other_id)
        forbidden_response = client.post(
            f"/api/practice-sessions/{session_id}/submit",
            json={"answers": [{"question_id": question_id, "user_answer": "A"}]},
        )
        assert forbidden_response.status_code == 404

        submit_answer(session_id, question_id, owner_id, "A")

        repeat_response = client.post(
            f"/api/practice-sessions/{session_id}/submit",
            json={"answers": [{"question_id": question_id, "user_answer": "A"}]},
        )
        assert repeat_response.status_code == 400
    finally:
        cleanup_test_data(chapter_id, owner_id)
        cleanup_test_data(chapter_id, other_id)


def test_unsubmitted_practice_review_hides_answers_and_stats_ignore_it() -> None:
    chapter_id = 909
    user_id = f"pytest-{uuid4()}"
    cleanup_test_data(chapter_id, user_id)

    try:
        question_id = seed_test_question(chapter_id)
        session_id = create_session(chapter_id, user_id)

        review_response = client.get(f"/api/practice-sessions/{session_id}/review?user_id={user_id}")
        assert review_response.status_code == 200
        review = review_response.json()
        assert review["submitted_at"] is None
        assert review["questions"][0]["id"] == question_id
        assert review["results"][0]["is_correct"] is None
        assert review["results"][0]["correct_answer"] is None
        assert review["results"][0]["explanation"] is None

        overview_response = client.get(f"/api/statistics/overview?user_id={user_id}")
        assert overview_response.status_code == 200
        overview = overview_response.json()
        assert overview["total_sessions"] == 1
        assert overview["total_answers"] == 0
        assert overview["wrong_question_count"] == 0
    finally:
        cleanup_test_data(chapter_id, user_id)


def test_delete_practice_history_item() -> None:
    chapter_id = 910
    user_id = f"pytest-{uuid4()}"
    cleanup_test_data(chapter_id, user_id)

    try:
        question_id = seed_test_question(chapter_id)
        session_id = create_session(chapter_id, user_id)
        submit_answer(session_id, question_id, user_id, "A")

        delete_response = client.delete(f"/api/practice-sessions/{session_id}?user_id={user_id}")
        assert delete_response.status_code == 200
        assert delete_response.json() == {"deleted": True}

        history_response = client.get(f"/api/practice-sessions?user_id={user_id}")
        assert history_response.status_code == 200
        assert history_response.json() == []

        review_response = client.get(f"/api/practice-sessions/{session_id}/review?user_id={user_id}")
        assert review_response.status_code == 404
    finally:
        cleanup_test_data(chapter_id, user_id)


def test_question_group_practice_submits_child_answers() -> None:
    chapter_id = 908
    user_id = f"pytest-{uuid4()}"
    cleanup_test_data(chapter_id, user_id)

    try:
        parent_id, first_id, second_id = seed_reading_group(chapter_id)
        response = client.post(
            "/api/practice-sessions",
            json={
                "mode": "chapter",
                "chapter_id": chapter_id,
                "question_count": 1,
                "question_types": ["question_group"],
                "source_scope": "original_only",
                "user_id": user_id,
            },
        )
        assert response.status_code == 200
        body = response.json()
        assert body["question_count"] == 1
        assert body["questions"][0]["id"] == parent_id
        assert body["questions"][0]["type"] == "question_group"
        assert [child["id"] for child in body["questions"][0]["children"]] == [first_id, second_id]

        result_response = client.post(
            f"/api/practice-sessions/{body['id']}/submit",
            json={
                "user_id": user_id,
                "answers": [
                    {"question_id": first_id, "user_answer": "A"},
                    {"question_id": second_id, "user_answer": "100ns"},
                ],
            },
        )
        assert result_response.status_code == 200
        result = result_response.json()
        assert result["total"] == 2
        assert result["score"] == 2
        assert {item["question_id"] for item in result["results"]} == {first_id, second_id}
    finally:
        cleanup_test_data(chapter_id, user_id)


def test_question_source_labels() -> None:
    homework_chapter_id = 901
    ai_chapter_id = 902
    user_id = f"pytest-{uuid4()}"
    cleanup_test_data(homework_chapter_id, user_id)
    cleanup_test_data(ai_chapter_id, user_id)

    try:
        homework_id = seed_source_question(
            homework_chapter_id,
            "materials/homework-examples/作业1.docx#1",
            "第1次作业",
            False,
        )
        ai_id = seed_source_question(
            ai_chapter_id,
            "knowledge_chunks:pytest",
            "AI题目生成",
            True,
        )

        practice_response = client.post(
            "/api/practice-sessions",
            json={"mode": "chapter", "chapter_id": homework_chapter_id, "question_count": 1, "user_id": user_id},
        )
        assert practice_response.status_code == 200
        question = practice_response.json()["questions"][0]
        assert question["source_type"] == "homework"
        assert question["source_label"] == "作业原题"

        ai_practice_response = client.post(
            "/api/practice-sessions",
            json={"mode": "chapter", "chapter_id": ai_chapter_id, "question_count": 1, "user_id": user_id},
        )
        assert ai_practice_response.status_code == 200
        ai_question = ai_practice_response.json()["questions"][0]
        assert ai_question["source_type"] == "ai"
        assert "AI" in ai_question["source_label"]
    finally:
        cleanup_test_data(homework_chapter_id, user_id)
        cleanup_test_data(ai_chapter_id, user_id)


def test_practice_source_scope_can_exclude_or_include_ai_questions() -> None:
    chapter_id = 903
    user_id = f"pytest-{uuid4()}"
    cleanup_test_data(chapter_id, user_id)

    try:
        original_id = seed_source_question(
            chapter_id,
            "materials/homework-examples/作业-source-scope.txt#1",
            "pytest作业",
            False,
        )
        ai_id = seed_source_question(
            chapter_id,
            "ai:model-draft;chunks=pytest",
            "AI题目生成",
            True,
        )

        original_response = client.post(
            "/api/practice-sessions",
            json={
                "mode": "chapter",
                "chapter_id": chapter_id,
                "question_count": 2,
                "source_scope": "original_only",
                "user_id": user_id,
            },
        )
        assert original_response.status_code == 200
        original_questions = original_response.json()["questions"]
        assert [question["id"] for question in original_questions] == [original_id]
        assert all(question["source_type"] != "ai" for question in original_questions)

        standard_response = client.post(
            "/api/practice-sessions",
            json={
                "mode": "chapter",
                "chapter_id": chapter_id,
                "question_count": 2,
                "source_scope": "standard",
                "user_id": user_id,
            },
        )
        assert standard_response.status_code == 200
        mixed_ids = {question["id"] for question in standard_response.json()["questions"]}
        assert mixed_ids == {original_id, ai_id}
    finally:
        cleanup_test_data(chapter_id, user_id)


def test_question_feedback_like_and_unhelpful() -> None:
    chapter_id = 904
    user_id = f"pytest-{uuid4()}"
    cleanup_test_data(chapter_id, user_id)

    try:
        question_id = seed_test_question(chapter_id)

        like_response = client.post(
            f"/api/questions/{question_id}/feedback?user_id={user_id}",
            json={"feedback_type": "helpful"},
        )
        assert like_response.status_code == 200
        assert like_response.json()["likes"] == 1
        assert like_response.json()["user_liked"] is True

        practice_response = client.post(
            "/api/practice-sessions",
            json={"mode": "chapter", "chapter_id": chapter_id, "question_count": 1, "user_id": user_id},
        )
        assert practice_response.status_code == 200
        q = practice_response.json()["questions"][0]
        assert q["likes"] == 1
        assert q["user_liked"] is True

        unlike_response = client.delete(f"/api/questions/{question_id}/feedback?user_id={user_id}")
        assert unlike_response.status_code == 200

        unhelpful_response = client.post(
            f"/api/questions/{question_id}/feedback?user_id={user_id}",
            json={"feedback_type": "not_helpful"},
        )
        assert unhelpful_response.status_code == 200
        assert unhelpful_response.json()["likes"] == 0
        assert unhelpful_response.json()["unhelpful"] == 1
    finally:
        cleanup_test_data(chapter_id, user_id)


def test_adaptive_practice_prefers_unanswered_questions() -> None:
    chapter_id = 905
    user_id = f"pytest-{uuid4()}"
    cleanup_test_data(chapter_id, user_id)

    try:
        answered_id = seed_source_question(
            chapter_id,
            "materials/homework-examples/adaptive-answered.txt#1",
            "pytest作业",
            False,
        )
        unanswered_id = seed_source_question(
            chapter_id,
            "materials/homework-examples/adaptive-unanswered.txt#2",
            "pytest作业",
            False,
        )
        seed_answer_record(answered_id, user_id, True)

        response = client.post(
            "/api/practice-sessions",
            json={
                "mode": "chapter",
                "chapter_id": chapter_id,
                "question_count": 1,
                "source_scope": "original_only",
                "user_id": user_id,
            },
        )

        assert response.status_code == 200
        assert response.json()["questions"][0]["id"] == unanswered_id
    finally:
        cleanup_test_data(chapter_id, user_id)


def test_statistics_recommendations_and_question_type_stats() -> None:
    chapter_id = 906
    user_id = f"pytest-{uuid4()}"
    cleanup_test_data(chapter_id, user_id)

    try:
        question_id = seed_source_question(
            chapter_id,
            "materials/homework-examples/stats.txt#1",
            "pytest作业",
            False,
        )
        seed_answer_record(question_id, user_id, False)

        type_response = client.get(f"/api/statistics/question-types?user_id={user_id}")
        assert type_response.status_code == 200
        type_items = type_response.json()
        assert type_items[0]["question_type"] == "single_choice"
        assert type_items[0]["answered"] == 1
        assert type_items[0]["correct_rate"] == 0

        recommendation_response = client.get(f"/api/statistics/recommendations?user_id={user_id}")
        assert recommendation_response.status_code == 200
        recommendations = recommendation_response.json()
        assert recommendations
        assert {"reason", "action", "priority"}.issubset(recommendations[0])
    finally:
        cleanup_test_data(chapter_id, user_id)
