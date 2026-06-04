#!/usr/bin/env python3
"""Crop meaningful diagrams from exam page images and update structured JSONs.

Each year's exam pages are full-page scans. This script:
1. Crops specific diagram regions from the page images
2. Updates the structured JSON to reference only the cropped images
3. Only keeps source_images for questions that actually need diagrams
"""
from __future__ import annotations

import io
import json
import os
import struct
import zlib
from pathlib import Path

MATERIALS_DIR = Path("materials/exam-papers")
IMAGES_DIR = MATERIALS_DIR / "images"
STRUCTURED_DIR = MATERIALS_DIR / "structured"

# All images are 1024x724 (from PDF page scans)
IMG_W, IMG_H = 1024, 724

# ── PNG crop helper (no external dependencies) ────────────────────────────────

def read_png(path: str | Path) -> tuple[dict, bytes]:
    with open(path, "rb") as f:
        sig = f.read(8)
        chunks: dict = {}
        idat = b""
        while True:
            raw = f.read(8)
            if len(raw) < 8:
                break
            length = struct.unpack(">I", raw[:4])[0]
            ctype = raw[4:8]
            data = f.read(length)
            f.read(4)  # crc
            if ctype == b"IHDR":
                w, h, bd, ct = struct.unpack(">IIBB", data[:10])
                chunks["width"] = w
                chunks["height"] = h
                chunks["bit_depth"] = bd
                chunks["color_type"] = ct
            elif ctype == b"IDAT":
                idat += data
    return chunks, idat


def crop_png(src: str | Path, dst: str | Path, x: int, y: int, w: int, h: int) -> None:
    chunks, idat_raw = read_png(src)
    pw, ph = chunks["width"], chunks["height"]
    bd = chunks["bit_depth"]
    ct = chunks["color_type"]

    bpp_map = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}
    bpp = bpp_map.get(ct, 4)

    raw_data = zlib.decompress(idat_raw)
    stride = pw * bpp + 1  # +1 for filter byte

    # Extract and crop rows
    crop_rows: list[tuple[int, bytes]] = []
    for row_idx in range(y, min(y + h, ph)):
        start = row_idx * stride
        filter_byte = raw_data[start]
        row_data = raw_data[start + 1 : start + stride]
        crop_start = x * bpp
        crop_end = min((x + w) * bpp, len(row_data))
        crop_rows.append((filter_byte, row_data[crop_start:crop_end]))

    out = io.BytesIO()
    out.write(b"\x89PNG\r\n\x1a\n")

    def write_chunk(ctype: bytes, data: bytes) -> None:
        out.write(struct.pack(">I", len(data)))
        out.write(ctype)
        out.write(data)
        crc = zlib.crc32(ctype + data) & 0xFFFFFFFF
        out.write(struct.pack(">I", crc))

    write_chunk(b"IHDR", struct.pack(">IIBBBBB", w, len(crop_rows), bd, ct, 0, 0, 0))

    compressed = b""
    for fb, rd in crop_rows:
        compressed += bytes([fb]) + rd
    write_chunk(b"IDAT", zlib.compress(compressed, 9))
    write_chunk(b"IEND", b"")

    with open(dst, "wb") as f:
        f.write(out.getvalue())
    print(f"  cropped: {src} -> {dst} ({w}x{len(crop_rows)})")


# ── Per-year diagram definitions ──────────────────────────────────────────────
# Format: { "question_id": [ { "page": "X.png", "crop": (x, y, w, h), "label": "..." }, ... ] }

YEAR_DIAGRAMS: dict[int, dict[str, list[dict]]] = {
    2017: {
        # Page 4: CPU architecture diagram (top-left area, with 程序计数器, 指令寄存器)
        # Page 6: Small CPU structure diagram (top-right corner)
        "model-1": [
            {"page": "4.png", "crop": (50, 60, 380, 310), "label": "CPU 结构图"},
        ],
        "model-2": [
            {"page": "4.png", "crop": (50, 60, 380, 310), "label": "CPU 结构图"},
        ],
    },
    2018: {
        # Page 5: CPU architecture diagram + flow diagram (left side)
        # Page 6: MIPS 系统 CPU 数据通路图 (center area)
        "model-1": [
            {"page": "5.png", "crop": (40, 30, 440, 350), "label": "CPU 数据通路图"},
        ],
        "model-2": [
            {"page": "6.png", "crop": (130, 140, 440, 310), "label": "MIPS CPU 数据通路图"},
        ],
    },
    2019: {
        # Page 4: Small CPU/memory architecture diagram (top-left)
        "model-1": [
            {"page": "4.png", "crop": (60, 50, 400, 290), "label": "CPU 结构图"},
        ],
        "model-2": [
            {"page": "4.png", "crop": (60, 50, 400, 290), "label": "CPU 结构图"},
        ],
    },
    2020: {
        # Page 4: MIPS 单周期 CPU 数据通路 (left side) + flow diagrams (right side)
        "model-1": [
            {"page": "4.png", "crop": (30, 40, 470, 350), "label": "MIPS 单周期 CPU 数据通路"},
        ],
        "model-2": [
            {"page": "4.png", "crop": (30, 40, 470, 350), "label": "MIPS 单周期 CPU 数据通路"},
        ],
    },
    2021: {
        # Pages 5-6: MIPS CPU datapath diagram (图 3) - center-left area
        "model-1": [
            {"page": "5.png", "crop": (40, 50, 450, 330), "label": "MIPS CPU 数据通路图"},
        ],
        "model-2": [
            {"page": "5.png", "crop": (40, 50, 450, 330), "label": "MIPS CPU 数据通路图"},
        ],
    },
    2022: {
        # Page 7: ARM CPU structure diagram (top-left, 图 4) + microprogram flow (top-center, 图 3)
        # Page 8: RISC-V model machine structure diagram (left side, 图 4)
        "model-arm": [
            {"page": "7.png", "crop": (30, 30, 480, 280), "label": "ARM CPU 结构图"},
            {"page": "7.png", "crop": (500, 30, 480, 280), "label": "微程序流程图"},
        ],
        "model-riscv": [
            {"page": "8.png", "crop": (20, 20, 500, 290), "label": "RISC-V 模型机结构图"},
        ],
    },
    2023: {
        # Already handled manually
    },
}


def process_year(year: int) -> None:
    """Process a single year: crop images and update JSON."""
    if year == 2023:
        print(f"  {year}: already processed, skipping")
        return

    diagrams = YEAR_DIAGRAMS.get(year)
    if not diagrams:
        print(f"  {year}: no diagrams defined, clearing source_images for all questions")
        # Just clear source_images from the JSON
        json_path = STRUCTURED_DIR / f"{year}.json"
        if not json_path.is_file():
            print(f"  {year}: no structured JSON found, skipping")
            return
        data = json.loads(json_path.read_text(encoding="utf-8"))
        for q in data.get("questions", []):
            q["source_images"] = []
        json_path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return

    year_img_dir = IMAGES_DIR / str(year)
    if not year_img_dir.is_dir():
        print(f"  {year}: no images directory found, skipping")
        return

    json_path = STRUCTURED_DIR / f"{year}.json"
    if not json_path.is_file():
        print(f"  {year}: no structured JSON found, skipping")
        return

    print(f"  {year}: processing {len(diagrams)} questions with diagrams")
    data = json.loads(json_path.read_text(encoding="utf-8"))

    # Collect all crops needed for this year
    crops_made: set[tuple[str, tuple[int, int, int, int]]] = set()

    # Build a mapping from question id to diagram info
    question_diagrams: dict[str, list[dict]] = {}
    for q in data.get("questions", []):
        qid = q["id"]
        if qid in diagrams:
            question_diagrams[qid] = diagrams[qid]
            q["source_images"] = [
                {"filename": f"{year}_{d['page'].replace('.png', '')}_{d['crop'][0]}_{d['crop'][1]}.png", "label": d["label"]}
                for d in diagrams[qid]
            ]
        else:
            q["source_images"] = []

    # Create cropped images
    for qid, diagram_list in question_diagrams.items():
        for d in diagram_list:
            page_file = year_img_dir / d["page"]
            crop_key = (d["page"], d["crop"])
            if crop_key in crops_made:
                continue
            crops_made.add(crop_key)

            x, y, w, h = d["crop"]
            out_name = f"{year}_{d['page'].replace('.png', '')}_{x}_{y}.png"
            out_path = year_img_dir / out_name
            if not out_path.is_file():
                crop_png(page_file, out_path, x, y, w, h)
            else:
                print(f"  already exists: {out_path}")

    # Write updated JSON
    json_path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"  {year}: JSON updated")


def main() -> None:
    print("Cropping exam diagrams and updating structured JSONs...")
    for year in sorted(YEAR_DIAGRAMS.keys()):
        print(f"\nProcessing {year}...")
        process_year(year)
    print("\nDone!")


if __name__ == "__main__":
    main()
