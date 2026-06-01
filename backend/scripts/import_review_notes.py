from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path

from docx import Document
from sqlalchemy import delete, select

ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = ROOT.parent
sys.path.append(str(ROOT))

from app.core.database import SessionLocal
from app.models.entities import KnowledgeChunk, KnowledgePoint


CHAPTER_RE = re.compile(r"chapter-(\d+)-")
MAX_CHUNK_CHARS = 1200
CHUNK_OVERLAP_CHARS = 160


@dataclass
class Section:
    chapter_id: int
    title: str
    content: str
    source_file: str
    order_index: int


def clean_text(value: str) -> str:
    value = value.replace("\u00a0", " ")
    value = re.sub(r"[ \t]+", " ", value)
    value = re.sub(r"\n{3,}", "\n\n", value)
    return value.strip()


def chapter_id_from_path(path: Path) -> int | None:
    match = CHAPTER_RE.search(path.name)
    return int(match.group(1)) if match else None


def relative_source(path: Path) -> str:
    return path.relative_to(REPO_ROOT).as_posix()


def is_heading(style_name: str) -> bool:
    return style_name in {"Heading 1", "Heading 2"}


def parse_docx(path: Path) -> list[Section]:
    chapter_id = chapter_id_from_path(path)
    if not chapter_id:
        return []

    doc = Document(path)
    sections: list[Section] = []
    current_title: str | None = None
    current_lines: list[str] = []
    source_file = relative_source(path)

    def flush() -> None:
        nonlocal current_title, current_lines
        if not current_title:
            current_lines = []
            return
        content = clean_text("\n".join(current_lines))
        if content:
            sections.append(
                Section(
                    chapter_id=chapter_id,
                    title=clean_text(current_title),
                    content=content,
                    source_file=source_file,
                    order_index=len(sections) + 1,
                )
            )
        current_lines = []

    for paragraph in doc.paragraphs:
        text = clean_text(paragraph.text)
        if not text:
            continue
        style_name = paragraph.style.name
        if is_heading(style_name):
            flush()
            current_title = text
            continue
        if current_title:
            current_lines.append(text)

    flush()
    return sections


def split_content(content: str) -> list[str]:
    if len(content) <= MAX_CHUNK_CHARS:
        return [content]

    chunks: list[str] = []
    start = 0
    while start < len(content):
        end = min(start + MAX_CHUNK_CHARS, len(content))
        if end < len(content):
            split_at = max(content.rfind("\n", start, end), content.rfind("。", start, end))
            if split_at > start + 300:
                end = split_at + 1
        chunks.append(clean_text(content[start:end]))
        if end >= len(content):
            break
        start = max(end - CHUNK_OVERLAP_CHARS, 0)
    return [chunk for chunk in chunks if chunk]


def summary_for(section: Section) -> str:
    first_line = section.content.splitlines()[0] if section.content else ""
    return clean_text(first_line[:260])


def import_sections(sections: list[Section]) -> tuple[int, int, int]:
    point_count = 0
    chunk_count = 0
    source_files = sorted({section.source_file for section in sections})

    with SessionLocal() as db:
        if source_files:
            db.execute(delete(KnowledgeChunk).where(KnowledgeChunk.source_file.in_(source_files)))

        for section in sections:
            point = db.scalar(
                select(KnowledgePoint).where(
                    KnowledgePoint.chapter_id == section.chapter_id,
                    KnowledgePoint.name == section.title,
                )
            )
            if point:
                point.summary = summary_for(section)
                point.difficulty = "medium"
            else:
                point = KnowledgePoint(
                    chapter_id=section.chapter_id,
                    name=section.title,
                    summary=summary_for(section),
                    difficulty="medium",
                )
                db.add(point)
                point_count += 1

            for chunk_index, chunk in enumerate(split_content(section.content), start=1):
                db.add(
                    KnowledgeChunk(
                        chapter_id=section.chapter_id,
                        chunk_id=f"ch{section.chapter_id:02d}-s{section.order_index:03d}-{chunk_index:02d}",
                        title=section.title,
                        content=chunk,
                        source_file=section.source_file,
                        source_page=None,
                    )
                )
                chunk_count += 1

        db.commit()

    return len(source_files), point_count, chunk_count


def main() -> None:
    parser = argparse.ArgumentParser(description="Parse prepared review-note docx files into RAG knowledge chunks.")
    parser.add_argument(
        "--notes-dir",
        default=str(REPO_ROOT / "materials/review-notes"),
        help="Directory containing chapter review-note .docx files.",
    )
    parser.add_argument("--dry-run", action="store_true", help="Parse and print counts without writing to the database.")
    args = parser.parse_args()

    all_sections: list[Section] = []
    for path in sorted(Path(args.notes_dir).glob("*.docx")):
        sections = parse_docx(path)
        all_sections.extend(sections)
        print(f"{path.name}: sections={len(sections)} chunks={sum(len(split_content(section.content)) for section in sections)}")

    print(f"TOTAL: files={len(list(Path(args.notes_dir).glob('*.docx')))} sections={len(all_sections)}")

    if args.dry_run:
        return

    source_count, inserted_points, chunk_count = import_sections(all_sections)
    print(f"Imported {chunk_count} chunks from {source_count} files; inserted {inserted_points} knowledge points.")


if __name__ == "__main__":
    main()
