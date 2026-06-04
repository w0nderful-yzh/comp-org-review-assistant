from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    app_name: str = "CompOrg Review Assistant"
    database_url: str = (
        "postgresql+psycopg://comp_org:comp_org_dev_password"
        "@localhost:5432/comp_org_review"
    )
    cors_origins: list[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]
    ai_api_key: str | None = None
    ai_base_url: str = "https://api.openai.com/v1"
    ai_model: str = "gpt-4.1-mini"
    ai_request_timeout: float = 45.0
    ai_enabled: bool = True
    courseware_pdf_dir: Path = _ROOT / "materials" / "courseware-pdfs"
    exam_paper_dir: Path = _ROOT / "materials" / "exam-papers"

    # JWT 认证配置
    secret_key: str = "change-me-in-production"
    token_algorithm: str = "HS256"
    token_expire_minutes: int = 1440  # 24 小时

    model_config = SettingsConfigDict(
        env_file=str(_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
