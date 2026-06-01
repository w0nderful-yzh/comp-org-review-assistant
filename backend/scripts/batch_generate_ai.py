"""Batch generate AI questions for chapters with thin coverage.

Usage:
    python scripts/batch_generate_ai.py              # generate for all chapters with < 10 questions
    python scripts/batch_generate_ai.py --chapter 8  # generate for a specific chapter
    python scripts/batch_generate_ai.py --count 10   # generate 10 questions per chapter
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))

from sqlalchemy import func, select

from app.core.config import get_settings
from app.core.database import SessionLocal
from app.models.entities import Chapter, KnowledgeChunk, Question
from app.schemas.api import AiQuestionDraftCreate
from app.services.ai_generation import AiGenerationError, generate_question_drafts

QUESTION_TYPES_PER_CHAPTER = [
    ["single_choice", "multiple_choice", "true_false"],
    ["fill_blank", "short_answer", "calculation"],
]


def get_chapter_question_count(db, chapter_id: int) -> int:
    return db.scalar(
        select(func.count(Question.id)).where(
            Question.chapter_id == chapter_id,
            Question.archived.is_(False),
        )
    ) or 0


def generate_for_chapter(db, chapter: Chapter, count: int, settings) -> int:
    chunks = db.scalars(
        select(KnowledgeChunk)
        .where(KnowledgeChunk.chapter_id == chapter.id)
        .order_by(KnowledgeChunk.chunk_id)
        .limit(12)
    ).all()
    if not chunks:
        print(f"  跳过第{chapter.order_index}章 - 没有知识块")
        return 0

    total_created = 0
    for types in QUESTION_TYPES_PER_CHAPTER:
        payload = AiQuestionDraftCreate(
            chapter_id=chapter.id,
            question_types=types,
            difficulty="medium",
            count=count,
        )
        try:
            drafts = generate_question_drafts(payload, chapter, chunks, settings)
            for draft in drafts:
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
                )
                db.add(question)
            db.flush()
            total_created += len(drafts)
            print(f"  生成 {len(drafts)} 道 ({', '.join(types)})")
        except AiGenerationError as exc:
            print(f"  生成失败 ({', '.join(types)}): {exc}")

        time.sleep(1)

    db.commit()
    return total_created


def main():
    parser = argparse.ArgumentParser(description="Batch generate AI questions")
    parser.add_argument("--chapter", type=int, help="Specific chapter ID to generate for")
    parser.add_argument("--count", type=int, default=5, help="Questions per batch (default: 5)")
    parser.add_argument("--min-threshold", type=int, default=10, help="Min questions before generating (default: 10)")
    args = parser.parse_args()

    settings = get_settings()
    if not settings.ai_api_key:
        print("错误: AI_API_KEY 未配置")
        sys.exit(1)

    with SessionLocal() as db:
        if args.chapter:
            chapter = db.get(Chapter, args.chapter)
            if not chapter:
                print(f"错误: 第{args.chapter}章不存在")
                sys.exit(1)
            chapters = [chapter]
        else:
            chapters = db.scalars(select(Chapter).order_by(Chapter.order_index)).all()

        total = 0
        for chapter in chapters:
            current = get_chapter_question_count(db, chapter.id)
            if not args.chapter and current >= args.min_threshold:
                print(f"第{chapter.order_index}章《{chapter.title}》已有 {current} 道，跳过")
                continue

            print(f"第{chapter.order_index}章《{chapter.title}》当前 {current} 道，开始生成...")
            created = generate_for_chapter(db, chapter, args.count, settings)
            total += created
            print(f"  完成，新增 {created} 道")

        print(f"\n总计生成 {total} 道 AI 题目")


if __name__ == "__main__":
    main()
