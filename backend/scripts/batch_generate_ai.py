"""Batch generate AI questions to reach a target count per chapter.

Usage:
    python scripts/batch_generate_ai.py                  # fill all chapters to 50 questions
    python scripts/batch_generate_ai.py --target 30      # fill all chapters to 30 questions
    python scripts/batch_generate_ai.py --chapter 8      # fill chapter 8 to 50 questions
    python scripts/batch_generate_ai.py --chapter 8 --target 30
"""

from __future__ import annotations

import argparse
import random
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

ALL_TYPES = ["single_choice", "multiple_choice", "true_false", "fill_blank", "calculation"]
BATCH_SIZE = 5  # max per API call


def get_chapter_question_count(db, chapter_id: int) -> int:
    return db.scalar(
        select(func.count(Question.id)).where(
            Question.chapter_id == chapter_id,
            Question.archived.is_(False),
        )
    ) or 0


def pick_types_for_round(round_index: int) -> list[str]:
    """Pick 3 types per round, rotating through all types."""
    start = (round_index * 3) % len(ALL_TYPES)
    return ALL_TYPES[start:start + 3] if start + 3 <= len(ALL_TYPES) else ALL_TYPES[start:] + ALL_TYPES[:start + 3 - len(ALL_TYPES)]


def generate_for_chapter(db, chapter: Chapter, needed: int, settings) -> int:
    chunks = db.scalars(
        select(KnowledgeChunk)
        .where(KnowledgeChunk.chapter_id == chapter.id)
        .order_by(KnowledgeChunk.chunk_id)
        .limit(12)
    ).all()
    if not chunks:
        print(f"  跳过 - 没有知识块")
        return 0

    total_created = 0
    round_index = 0
    difficulties = ["easy", "medium", "medium", "hard"]  # weighted toward medium

    while total_created < needed:
        batch = min(BATCH_SIZE, needed - total_created)
        types = pick_types_for_round(round_index)
        difficulty = difficulties[round_index % len(difficulties)]

        payload = AiQuestionDraftCreate(
            chapter_id=chapter.id,
            question_types=types,
            difficulty=difficulty,
            count=batch,
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
                    ai_status="verified",
                    quality_score=0,
                )
                db.add(question)
            db.flush()
            total_created += len(drafts)
            print(f"  +{len(drafts)} 道 ({'/'.join(types)}, {difficulty})  累计 +{total_created}")
        except AiGenerationError as exc:
            print(f"  生成失败 ({'/'.join(types)}): {exc}")

        round_index += 1
        time.sleep(1)  # rate limit

    db.commit()
    return total_created


def main():
    parser = argparse.ArgumentParser(description="Batch generate AI questions to reach target count")
    parser.add_argument("--chapter", type=int, help="Specific chapter ID (default: all chapters)")
    parser.add_argument("--target", type=int, default=50, help="Target question count per chapter (default: 50)")
    args = parser.parse_args()

    settings = get_settings()
    if not settings.ai_api_key:
        print("错误: AI_API_KEY 未配置，请在 .env 中设置")
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

        grand_total = 0
        for chapter in chapters:
            current = get_chapter_question_count(db, chapter.id)
            needed = max(0, args.target - current)
            if needed == 0:
                print(f"第{chapter.order_index}章《{chapter.title}》已有 {current} 道 ✓")
                continue

            print(f"第{chapter.order_index}章《{chapter.title}》当前 {current} 道，需补充 {needed} 道...")
            created = generate_for_chapter(db, chapter, needed, settings)
            grand_total += created
            print(f"  完成，新增 {created} 道")

        print(f"\n{'='*40}")
        print(f"总计生成 {grand_total} 道 AI 题目")


if __name__ == "__main__":
    main()
