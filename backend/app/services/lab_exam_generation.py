from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.core.config import Settings
from app.schemas.api import LabExamPaperOut
from app.services.ai_generation import AiGenerationError, call_chat_completion, parse_json_content


def load_static_lab_exam(settings: Settings) -> dict[str, Any]:
    path = settings.lab_exam_dir / "static-paper.json"
    if not path.is_file():
        raise AiGenerationError("实验模拟卷材料不存在")
    data = json.loads(path.read_text(encoding="utf-8"))
    LabExamPaperOut.model_validate(data)
    return data


def load_lab_format_reference(settings: Settings) -> str:
    path = settings.lab_exam_dir / "format-reference.txt"
    if path.is_file():
        return path.read_text(encoding="utf-8")
    return "实验考试格式：选择题10分、汇编与机器语言分析20分、CPU设计60分、拓展题10分。"


def generate_lab_exam_paper(settings: Settings) -> dict[str, Any]:
    if not settings.ai_api_key:
        raise AiGenerationError("AI_API_KEY is not configured")
    static_paper = load_static_lab_exam(settings)
    format_reference = load_lab_format_reference(settings)
    prompt = build_lab_exam_prompt(format_reference, static_paper)
    # 生成整张试卷需要大量输出（23+ 题 + Verilog 代码 + FSM + 解析），给 300s
    response_payload = call_chat_completion(prompt, settings, timeout_seconds=300.0)
    content = (
        response_payload.get("choices", [{}])[0]
        .get("message", {})
        .get("content", "")
    )
    parsed = parse_json_content(content)
    paper = parsed.get("paper", parsed)
    if not isinstance(paper, dict):
        raise AiGenerationError("AI response must contain a paper object")
    normalized = normalize_lab_exam_paper(paper)
    LabExamPaperOut.model_validate(normalized)
    return normalized


def build_lab_exam_prompt(format_reference: str, static_paper: dict[str, Any]) -> str:
    sample_questions = static_paper.get("questions", [])[:6]
    sample = {
        "sections": static_paper.get("sections", []),
        "questions": sample_questions,
    }
    return f"""
你是《计算机组成原理》实验考试命题老师。请生成一份“计组实验模拟考试”试卷，并附带答案。

必须严格参考下面的实验考试格式：
{format_reference}

还要参考下面已有模拟卷的 JSON 风格、题型分布和难度，但不要逐字照抄题目：
{json.dumps(sample, ensure_ascii=False)}

只返回 JSON，不要 Markdown，不要解释额外文本。格式必须为：
{{
  "paper": {{
    "id": "lab-ai-自定义短ID",
    "title": "计组实验模拟考试（AI 生成）",
    "subtitle": "基于 RISC-V 指令集与实验模型机",
    "duration_minutes": 90,
    "total_score": 100,
    "generated": true,
    "sections": [
      {{"id": "choice", "title": "一、选择题", "score": 10, "description": "每题 1 分。"}},
      {{"id": "assembly", "title": "二、汇编程序、机器语言的分析、设计题", "score": 20}},
      {{"id": "cpu", "title": "三、CPU 设计题", "score": 60}},
      {{"id": "extension", "title": "四、拓展题", "score": 10}}
    ],
    "questions": [
      {{
        "id": "choice-1",
        "section_id": "choice",
        "number": "1",
        "title": "短标题",
        "score": 1,
        "stem": "题干",
        "answer_type": "single_choice",
        "options": [{{"key": "A", "text": "选项A"}}, {{"key": "B", "text": "选项B"}}, {{"key": "C", "text": "选项C"}}, {{"key": "D", "text": "选项D"}}],
        "answer": "A",
        "explanation": "解析"
      }},
      {{
        "id": "assembly-1",
        "section_id": "assembly",
        "number": "1",
        "title": "短标题",
        "score": 8,
        "stem": "题干",
        "answer_type": "text",
        "reference_answer": "参考答案",
        "explanation": "解析"
      }}
    ]
  }}
}}

严格要求：
- 总分必须为 100，考试时间 90 分钟。
- 必须包含 choice/assembly/cpu/extension 四个 section。
- choice 必须正好 10 道单选题，每题 1 分，每题 A/B/C/D 四个选项且答案唯一。
- assembly 必须包含 3 道题，总分 20，覆盖机器编码分析、汇编程序功能分析、C 到 RV32I 汇编设计。
- cpu 必须包含 6 道题，总分 60，围绕 3 条 RISC-V 指令设计多周期模型机，包含流程、FSM、控制信号、Verilog、机器码、正确性判断。
- extension 至少给 4 道拓展题，每题 5 分，说明考生任选 2 题。
- 每道题必须有 answer 或 reference_answer，并给出 explanation。
- 内容必须基于 RISC-V RV32I、实验模型机、多周期 CPU、控制信号、机器指令编码，不要出超纲题。
- Verilog 题答案要给出可读的参考代码或关键组合逻辑。
""".strip()


def normalize_lab_exam_paper(raw: dict[str, Any]) -> dict[str, Any]:
    paper = {
        "id": str(raw.get("id") or "lab-ai-generated").strip(),
        "title": str(raw.get("title") or "计组实验模拟考试（AI 生成）").strip(),
        "subtitle": str(raw.get("subtitle") or "基于 RISC-V 指令集与实验模型机").strip(),
        "duration_minutes": int(raw.get("duration_minutes") or 90),
        "total_score": int(raw.get("total_score") or 100),
        "source_file": raw.get("source_file"),
        "format_reference": raw.get("format_reference"),
        "generated": True,
        "sections": normalize_sections(raw.get("sections")),
        "questions": normalize_questions(raw.get("questions")),
    }
    if not paper["questions"]:
        raise AiGenerationError("AI generated paper has no questions")
    return paper


def normalize_sections(value: Any) -> list[dict[str, Any]]:
    fallback = [
        {"id": "choice", "title": "一、选择题", "score": 10, "description": "每题 1 分。"},
        {"id": "assembly", "title": "二、汇编程序、机器语言的分析、设计题", "score": 20, "description": None},
        {"id": "cpu", "title": "三、CPU 设计题", "score": 60, "description": None},
        {"id": "extension", "title": "四、拓展题", "score": 10, "description": "任选 2 题，每题 5 分。"},
    ]
    if not isinstance(value, list):
        return fallback
    sections = []
    for item in value:
        if not isinstance(item, dict):
            continue
        section_id = str(item.get("id") or "").strip()
        title = str(item.get("title") or "").strip()
        if section_id and title:
            sections.append({
                "id": section_id,
                "title": title,
                "score": int(item.get("score") or 0),
                "description": item.get("description"),
            })
    return sections or fallback


def normalize_questions(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    questions = []
    for index, item in enumerate(value, start=1):
        if not isinstance(item, dict):
            continue
        answer_type = str(item.get("answer_type") or "text").strip()
        if answer_type not in {"single_choice", "text"}:
            answer_type = "text"
        question = {
            "id": str(item.get("id") or f"q-{index}").strip(),
            "section_id": str(item.get("section_id") or "cpu").strip(),
            "number": str(item.get("number") or index).strip(),
            "title": str(item.get("title") or "实验模拟题").strip(),
            "score": float(item.get("score") or 0),
            "stem": str(item.get("stem") or "").strip(),
            "answer_type": answer_type,
            "options": normalize_options(item.get("options")) if answer_type == "single_choice" else [],
            "answer": str(item.get("answer") or "").strip() or None,
            "reference_answer": str(item.get("reference_answer") or "").strip() or None,
            "explanation": str(item.get("explanation") or "").strip() or None,
        }
        if not question["stem"]:
            continue
        if answer_type == "single_choice" and (len(question["options"]) != 4 or not question["answer"]):
            continue
        if answer_type == "text" and not question["reference_answer"]:
            continue
        questions.append(question)
    return questions


def normalize_options(value: Any) -> list[dict[str, str]]:
    if not isinstance(value, list):
        return []
    options = []
    for item in value:
        if not isinstance(item, dict):
            continue
        key = str(item.get("key") or "").strip().upper()
        text = str(item.get("text") or "").strip()
        if key and text:
            options.append({"key": key, "text": text})
    return options
