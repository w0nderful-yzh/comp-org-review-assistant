from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = ROOT.parent
sys.path.append(str(ROOT))

from sqlalchemy import select

from app.core.database import SessionLocal
from app.models.entities import Question


TYPE_MAP = {
    "单选题": "single_choice",
    "多选题": "multiple_choice",
    "判断题": "true_false",
    "填空题": "fill_blank",
    "简答题": "short_answer",
    "计算题": "calculation",
}
SUPPORTED_TYPES = set(TYPE_MAP)
CHAPTER_RE = re.compile(r"第(\d+)章")
TOP_RE = re.compile(r"^(\d+)\.\s*\(([^)]+)\)\s*(.*)$")
SUB_RE = re.compile(r"^\((\d+)\)\s*\(([^)]+)\)\s*(.*)$")
OPTION_RE = re.compile(r"^([A-H])\.\s*(.*)$")
ANSWER_RE = re.compile(r"^正确答案[:：]\s*(.*)$")
SECTION_SUMMARY_RE = re.compile(r"^[一二三四五六七八九十]+[.．]\s*.+（\d+")


@dataclass
class ParsedQuestion:
    chapter_id: int
    question_type: str
    difficulty: str
    stem: str
    options: list[dict[str, str]]
    answer: Any
    rubric: list[str]
    explanation: str | None
    source_assignment: str
    source_context: str


def clean_text(value: str) -> str:
    value = value.replace("\u00a0", " ")
    value = re.sub(r"[ \t]+", " ", value)
    value = re.sub(r"\n{3,}", "\n\n", value)
    return value.strip()


def nonempty(lines: list[str]) -> list[str]:
    return [clean_text(line) for line in lines if clean_text(line)]


def compact_lines(lines: list[str]) -> str:
    return clean_text("\n".join(nonempty(lines)))


def assignment_title(lines: list[str], path: Path) -> str:
    for line in lines[:12]:
        if line.startswith("source_title:"):
            return clean_text(line.split(":", 1)[1])
    return path.stem


def chapter_id_from_path(path: Path) -> int | None:
    match = CHAPTER_RE.search(path.name)
    return int(match.group(1)) if match else None


def question_kind(meta: str) -> str:
    return clean_text(meta.split(",", 1)[0].split("，", 1)[0])


def split_blocks(lines: list[str], pattern: re.Pattern[str]) -> list[tuple[str, str, list[str]]]:
    blocks: list[tuple[str, str, list[str]]] = []
    current_number: str | None = None
    current_meta: str | None = None
    current_lines: list[str] = []

    for line in lines:
        match = pattern.match(line)
        if match:
            if current_number and current_meta is not None:
                blocks.append((current_number, current_meta, current_lines))
            current_number, current_meta = match.group(1), match.group(2)
            current_lines = [match.group(3)] if match.group(3).strip() else []
        elif current_number:
            current_lines.append(line)

    if current_number and current_meta is not None:
        blocks.append((current_number, current_meta, current_lines))
    return blocks


def find_answer_index(lines: list[str]) -> int | None:
    for index, line in enumerate(lines):
        if ANSWER_RE.match(line):
            return index
    return None


def parse_options_and_stem(lines: list[str]) -> tuple[str, list[dict[str, str]]]:
    stem_lines: list[str] = []
    options: list[dict[str, str]] = []
    active_key: str | None = None
    active_text: list[str] = []

    def flush_option() -> None:
        nonlocal active_key, active_text
        if active_key:
            options.append({"key": active_key, "text": compact_lines(active_text)})
        active_key = None
        active_text = []

    for line in lines:
        stripped = clean_text(line)
        match = OPTION_RE.match(stripped)
        if match:
            flush_option()
            active_key = match.group(1)
            active_text = [match.group(2)] if match.group(2).strip() else []
            continue
        if active_key:
            active_text.append(line)
        else:
            stem_lines.append(line)

    flush_option()
    return compact_lines(stem_lines), options


def split_answer_and_explanation(answer_line_tail: str, lines_after_answer: list[str]) -> tuple[list[str], str | None]:
    answer_lines: list[str] = [answer_line_tail] if answer_line_tail.strip() else []
    explanation_lines: list[str] = []
    in_explanation = False

    for line in lines_after_answer:
        stripped = clean_text(line)
        if not stripped:
            continue
        if SECTION_SUMMARY_RE.match(stripped):
            break
        if stripped.startswith(":") or stripped.startswith("："):
            in_explanation = True
            explanation_lines.append(stripped[1:].strip())
            continue
        if stripped.startswith("答案解析"):
            in_explanation = True
            explanation_lines.append(stripped.split("：", 1)[-1].strip() if "：" in stripped else "")
            continue
        if in_explanation:
            explanation_lines.append(stripped)
        else:
            answer_lines.append(stripped)

    explanation = compact_lines(explanation_lines) if explanation_lines else None
    return answer_lines, explanation


def answer_letters(text: str) -> list[str]:
    return re.findall(r"[A-H]", text.upper())


def parse_fill_blanks(answer_lines: list[str]) -> list[dict[str, Any]]:
    text = "\n".join(answer_lines)
    matches = list(re.finditer(r"\((\d+)\)\s*([\s\S]*?)(?=\n?\(\d+\)|$)", text))
    if not matches:
        values = [part.strip() for part in re.split(r"[;；\n]+", text) if part.strip()]
        return [
            {
                "index": index + 1,
                "answer": value.split("；")[0].split(";")[0].strip(),
                "acceptable_answers": [item.strip() for item in re.split(r"[;；]", value) if item.strip()][1:],
            }
            for index, value in enumerate(values)
        ]

    blanks: list[dict[str, Any]] = []
    for match in matches:
        raw_value = clean_text(match.group(2))
        answers = [item.strip() for item in re.split(r"[;；]", raw_value) if item.strip()]
        if not answers:
            continue
        blanks.append({"index": int(match.group(1)), "answer": answers[0], "acceptable_answers": answers[1:]})
    return blanks


def parse_answer(question_type: str, answer_lines: list[str]) -> Any:
    answer_text = compact_lines(answer_lines)
    if question_type == "single_choice":
        letters = answer_letters(answer_text)
        return {"answer": letters[0] if letters else answer_text}
    if question_type == "multiple_choice":
        return {"answer": answer_letters(answer_text)}
    if question_type == "true_false":
        normalized = answer_text.upper()
        if "对" in answer_text or "TRUE" in normalized:
            return {"answer": "TRUE"}
        if "错" in answer_text or "FALSE" in normalized:
            return {"answer": "FALSE"}
        return {"answer": answer_text}
    if question_type in {"fill_blank", "cloze"}:
        return {"blanks": parse_fill_blanks(answer_lines)}
    return {"reference_answer": answer_text}


def parse_question(
    *,
    chapter_id: int,
    number: str,
    meta: str,
    lines: list[str],
    source_assignment: str,
    source_context: str,
    parent_context: str | None = None,
) -> ParsedQuestion | None:
    kind = question_kind(meta)
    if kind not in SUPPORTED_TYPES:
        return None
    answer_index = find_answer_index(lines)
    if answer_index is None:
        return None

    answer_match = ANSWER_RE.match(lines[answer_index])
    if not answer_match:
        return None

    body_lines = lines[:answer_index]
    answer_lines, explanation = split_answer_and_explanation(answer_match.group(1), lines[answer_index + 1 :])
    question_type = TYPE_MAP[kind]
    if question_type in {"single_choice", "multiple_choice", "true_false"}:
        stem, options = parse_options_and_stem(body_lines)
    else:
        stem, options = compact_lines(body_lines), []
    if parent_context:
        stem = clean_text(f"阅读材料：\n{parent_context}\n\n问题：\n{stem}")
    if not stem:
        return None

    return ParsedQuestion(
        chapter_id=chapter_id,
        question_type=question_type,
        difficulty="medium",
        stem=stem,
        options=options,
        answer=parse_answer(question_type, answer_lines),
        rubric=[],
        explanation=explanation,
        source_assignment=source_assignment,
        source_context=source_context,
    )


def parse_reading_block(
    *,
    chapter_id: int,
    number: str,
    lines: list[str],
    source_assignment: str,
    path: Path,
) -> list[ParsedQuestion]:
    subblocks = split_blocks(lines, SUB_RE)
    if not subblocks:
        return []
    first_sub_match_index = next(
        (index for index, line in enumerate(lines) if SUB_RE.match(line)),
        len(lines),
    )
    parent_context = compact_lines(lines[:first_sub_match_index])
    parsed: list[ParsedQuestion] = []
    for sub_number, meta, sub_lines in subblocks:
        item = parse_question(
            chapter_id=chapter_id,
            number=f"{number}.{sub_number}",
            meta=meta,
            lines=sub_lines,
            source_assignment=source_assignment,
            source_context=f"{path.as_posix()}#{number}.{sub_number}",
            parent_context=parent_context,
        )
        if item:
            parsed.append(item)
    return parsed


def parse_file(path: Path) -> tuple[list[ParsedQuestion], dict[str, int]]:
    lines = path.read_text(encoding="utf-8").splitlines()
    chapter_id = chapter_id_from_path(path)
    if not chapter_id:
        return [], {"skipped_files": 1}

    source_assignment = assignment_title(lines, path)
    stats: dict[str, int] = {"blocks": 0, "parsed": 0, "skipped": 0}
    parsed: list[ParsedQuestion] = []

    for number, meta, block_lines in split_blocks(lines, TOP_RE):
        stats["blocks"] += 1
        kind = question_kind(meta)
        if kind == "阅读理解":
            items = parse_reading_block(
                chapter_id=chapter_id,
                number=number,
                lines=block_lines,
                source_assignment=source_assignment,
                path=path,
            )
        else:
            item = parse_question(
                chapter_id=chapter_id,
                number=number,
                meta=meta,
                lines=block_lines,
                source_assignment=source_assignment,
                source_context=f"{path.as_posix()}#{number}",
            )
            items = [item] if item else []
        if items:
            parsed.extend(items)
            stats["parsed"] += len(items)
        else:
            stats["skipped"] += 1

    return parsed, stats


def sync_question(row: Question, item: ParsedQuestion, reviewed: bool) -> None:
    row.chapter_id = item.chapter_id
    row.type = item.question_type
    row.difficulty = item.difficulty
    row.stem = item.stem
    row.options_json = item.options
    row.answer_json = item.answer
    row.rubric_json = item.rubric
    row.explanation = item.explanation
    row.source_context = item.source_context
    row.source_assignment = item.source_assignment
    row.is_ai_generated = False
    row.is_reviewed = reviewed


def import_questions(questions: list[ParsedQuestion], reviewed: bool) -> tuple[int, int, int]:
    inserted = 0
    updated = 0
    skipped = 0
    with SessionLocal() as db:
        for item in questions:
            existing = db.scalar(
                select(Question).where(Question.source_context == item.source_context)
            )
            if not existing:
                existing = db.scalar(
                    select(Question).where(
                        Question.source_assignment == item.source_assignment,
                        Question.stem == item.stem,
                    )
                )
            if existing:
                sync_question(existing, item, reviewed)
                updated += 1
                continue

            equivalent = db.scalar(
                select(Question.id).where(
                    Question.source_assignment == item.source_assignment,
                    Question.stem == item.stem,
                )
            )
            if equivalent:
                skipped += 1
                continue
            db.add(
                Question(
                    chapter_id=item.chapter_id,
                    knowledge_point_id=None,
                    parent_question_id=None,
                    type=item.question_type,
                    difficulty=item.difficulty,
                    stem=item.stem,
                    options_json=item.options,
                    answer_json=item.answer,
                    rubric_json=item.rubric,
                    explanation=item.explanation,
                    source_context=item.source_context,
                    source_assignment=item.source_assignment,
                    is_ai_generated=False,
                    is_reviewed=reviewed,
                )
            )
            inserted += 1
        db.commit()
    return inserted, updated, skipped


def main() -> None:
    parser = argparse.ArgumentParser(description="Import cleaned homework examples into the question bank.")
    parser.add_argument(
        "--raw-dir",
        default=str(REPO_ROOT / "materials/homework-examples/raw"),
        help="Directory containing cleaned homework .txt files.",
    )
    parser.add_argument("--dry-run", action="store_true", help="Parse and print counts without writing to the database.")
    parser.add_argument("--draft", action="store_true", help="Import questions as unreviewed drafts.")
    args = parser.parse_args()

    raw_dir = Path(args.raw_dir)
    all_questions: list[ParsedQuestion] = []
    totals: dict[str, int] = {"files": 0, "blocks": 0, "parsed": 0, "skipped": 0}

    for path in sorted(raw_dir.glob("*.txt")):
        questions, stats = parse_file(path)
        all_questions.extend(questions)
        totals["files"] += 1
        for key in ("blocks", "parsed", "skipped"):
            totals[key] += stats.get(key, 0)
        print(f"{path.name}: parsed={len(questions)} blocks={stats.get('blocks', 0)} skipped={stats.get('skipped', 0)}")

    print(
        "TOTAL: "
        f"files={totals['files']} blocks={totals['blocks']} parsed={totals['parsed']} skipped={totals['skipped']}"
    )

    if args.dry_run:
        return

    inserted, updated, duplicate_skipped = import_questions(all_questions, reviewed=not args.draft)
    state = "draft" if args.draft else "reviewed"
    print(f"Imported {inserted} {state} questions; updated {updated}; skipped {duplicate_skipped} duplicates.")


if __name__ == "__main__":
    main()
