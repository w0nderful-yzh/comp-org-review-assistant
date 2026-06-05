from __future__ import annotations

from contextlib import contextmanager
from types import SimpleNamespace
from collections.abc import Iterator

from fastapi.testclient import TestClient
from sqlalchemy import delete

from app.api import routes
from app.api.deps import get_current_user
from app.core.config import get_settings
from app.core.database import SessionLocal
from app.main import app
from app.models.entities import LabExamGeneration
from app.services.lab_exam_generation import load_static_lab_exam


TEST_USER_ID = "pytest-lab-exam"


def current_test_user() -> SimpleNamespace:
    return SimpleNamespace(id=TEST_USER_ID)


client = TestClient(app)


@contextmanager
def lab_user_override() -> Iterator[None]:
    previous = app.dependency_overrides.get(get_current_user)
    app.dependency_overrides[get_current_user] = current_test_user
    try:
        yield
    finally:
        if previous is None:
            app.dependency_overrides.pop(get_current_user, None)
        else:
            app.dependency_overrides[get_current_user] = previous


def cleanup_lab_generations() -> None:
    with SessionLocal() as db:
        routes.ensure_lab_exam_generation_table(db)
        db.execute(delete(LabExamGeneration).where(LabExamGeneration.user_id == TEST_USER_ID))
        db.commit()


def test_lab_exam_dashboard_returns_static_paper() -> None:
    cleanup_lab_generations()

    with lab_user_override():
        response = client.get("/api/lab-exams")

    assert response.status_code == 200
    body = response.json()
    assert body["static_paper"]["title"] == "计算机组成原理课程设计期末模拟卷"
    assert len(body["static_paper"]["questions"]) >= 20
    assert body["daily_remaining"] == 1


def test_lab_exam_generation_is_limited_to_once_per_day(monkeypatch) -> None:
    cleanup_lab_generations()
    settings = get_settings()
    original_api_key = settings.ai_api_key
    original_ai_enabled = settings.ai_enabled
    settings.ai_api_key = "pytest-key"
    settings.ai_enabled = True

    def fake_generate_lab_exam_paper(_settings):
        paper = load_static_lab_exam(_settings)
        paper["id"] = "pytest-generated-lab-exam"
        paper["generated"] = True
        return paper

    monkeypatch.setattr(routes, "generate_lab_exam_paper", fake_generate_lab_exam_paper)

    try:
        with lab_user_override():
            first = client.post("/api/lab-exams/generations")
            assert first.status_code == 200
            first_body = first.json()
            assert first_body["status"] in {"pending", "running", "completed"}

            routes.run_lab_exam_generation(first_body["id"])
            generated = client.get(f"/api/lab-exams/generations/{first_body['id']}")
            assert generated.status_code == 200
            generated_body = generated.json()
            assert generated_body["status"] == "completed"
            assert generated_body["paper"]["generated"] is True

            second = client.post("/api/lab-exams/generations")
            assert second.status_code == 200
            assert second.json()["id"] == first_body["id"]

            dashboard = client.get("/api/lab-exams")
            assert dashboard.status_code == 200
            assert dashboard.json()["daily_remaining"] == 0
    finally:
        settings.ai_api_key = original_api_key
        settings.ai_enabled = original_ai_enabled
        cleanup_lab_generations()
