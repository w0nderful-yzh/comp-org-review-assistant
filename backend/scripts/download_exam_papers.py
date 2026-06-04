from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import quote
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[2]
MANIFEST_PATH = ROOT / "materials" / "exam-papers" / "exam-papers.json"
PDF_DIR = ROOT / "materials" / "exam-papers" / "pdf"


def download_file(url: str, target: Path) -> None:
    req = Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urlopen(req, timeout=60) as response:
        target.write_bytes(response.read())


def main() -> None:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    source_url = manifest["source"]["url"]
    raw_base = source_url.replace(
        "https://github.com/HDU-Course/HDU-FinalExamPaper/tree/main/",
        "https://raw.githubusercontent.com/HDU-Course/HDU-FinalExamPaper/main/",
    )
    PDF_DIR.mkdir(parents=True, exist_ok=True)

    for paper in manifest["papers"]:
        for key in ("paper_pdf", "answer_pdf"):
            filename = paper[key]
            target = PDF_DIR / filename
            if target.exists() and target.stat().st_size > 0:
                print(f"exists {target}")
                continue
            url = f"{raw_base}/{quote(filename)}"
            print(f"download {url}")
            download_file(url, target)


if __name__ == "__main__":
    main()
