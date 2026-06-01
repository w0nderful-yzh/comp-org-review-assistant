from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any

import httpx

from app.core.config import Settings
from app.models.entities import Chapter, KnowledgeChunk
from app.schemas.api import AiQuestionDraftCreate


SUPPORTED_GENERATION_TYPES = {
    "single_choice",
    "multiple_choice",
    "true_false",
    "fill_blank",
    "short_answer",
    "calculation",
}


@dataclass(frozen=True)
class GeneratedQuestionDraft:
    chapter_id: int
    type: str
    difficulty: str
    stem: str
    options_json: Any
    answer_json: Any
    rubric_json: Any
    explanation: str | None
    source_context: str


class AiGenerationError(RuntimeError):
    pass


def generate_question_drafts(
    payload: AiQuestionDraftCreate,
    chapter: Chapter,
    chunks: list[KnowledgeChunk],
    settings: Settings,
) -> list[GeneratedQuestionDraft]:
    if not settings.ai_api_key:
        raise AiGenerationError("AI_API_KEY is not configured")

    requested_types = [item for item in payload.question_types if item in SUPPORTED_GENERATION_TYPES]
    if not requested_types:
        raise AiGenerationError("No supported question types selected")

    prompt = build_generation_prompt(payload, chapter, chunks, requested_types)
    response_payload = call_chat_completion(prompt, settings)
    raw_questions = extract_questions(response_payload)
    drafts = [
        normalize_question(raw, payload, chapter, chunks)
        for raw in raw_questions[: payload.count]
    ]
    if not drafts:
        raise AiGenerationError("The AI response did not contain valid questions")
    return drafts


def build_generation_prompt(
    payload: AiQuestionDraftCreate,
    chapter: Chapter,
    chunks: list[KnowledgeChunk],
    requested_types: list[str],
) -> str:
    context = "\n\n".join(
        f"[{chunk.chunk_id}] {chunk.title or '知识块'}\n{chunk.content[:900]}"
        for chunk in chunks[:8]
    )
    focus = payload.focus.strip() if payload.focus else "本章核心概念、易错点和计算方法"
    return f"""
你是《计算机组成原理》课程助教。请只根据给定知识块生成复习题，不要引入知识块之外的内容。

章节：第 {chapter.order_index} 章《{chapter.title}》
关注点：{focus}
题型范围：{", ".join(requested_types)}
难度：{payload.difficulty}
数量：{payload.count}

知识块：
{context}

只返回 JSON，不要 Markdown，不要解释额外文本。格式必须为：
{{
  "questions": [
    {{
      "type": "single_choice | multiple_choice | true_false | fill_blank | short_answer | calculation",
      "difficulty": "easy | medium | hard",
      "knowledge_points": ["相关知识点"],
      "stem": "题干",
      "options": [{{"key": "A", "text": "选项内容"}}],
      "answer": "A 或 [\\"A\\", \\"C\\"] 或 TRUE/FALSE",
      "blanks": [{{"index": 1, "answer": "标准答案", "acceptable_answers": ["可接受答案"]}}],
      "reference_answer": "简答/计算题参考答案",
      "rubric": ["评分点1", "评分点2"],
      "explanation": "解析，说明答案为什么正确"
    }}
  ]
}}

严格规则：
- 只根据给定知识块生成，不要编造知识块中没有的概念。
- 答案必须唯一，不能有争议。
- 解析必须说明答案为什么正确，选择题需解释其他选项为什么不合适。
- 不要生成超纲题、偏题、纯记忆刁钻题。
- 单选/多选必须提供 options，答案只能使用选项 key。
- 判断题 answer 只能是 TRUE 或 FALSE。
- 填空题使用 blanks，不要使用 options。
- 简答题和计算题使用 reference_answer 和 rubric。
- 不要照抄整段知识块，题目要能检验理解。
""".strip()


def call_chat_completion(prompt: str, settings: Settings) -> dict[str, Any]:
    url = f"{settings.ai_base_url.rstrip('/')}/chat/completions"
    body = {
        "model": settings.ai_model,
        "messages": [
            {"role": "system", "content": "你只输出可解析的 JSON。"},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.4,
        "response_format": {"type": "json_object"},
    }
    try:
        with httpx.Client(timeout=settings.ai_request_timeout) as client:
            response = client.post(
                url,
                headers={"Authorization": f"Bearer {settings.ai_api_key}"},
                json=body,
            )
            response.raise_for_status()
            return response.json()
    except httpx.HTTPError as exc:
        raise AiGenerationError(f"AI provider request failed: {exc}") from exc


def extract_questions(response_payload: dict[str, Any]) -> list[dict[str, Any]]:
    content = (
        response_payload.get("choices", [{}])[0]
        .get("message", {})
        .get("content", "")
    )
    if not isinstance(content, str) or not content.strip():
        raise AiGenerationError("AI provider returned an empty message")
    parsed = parse_json_content(content)
    questions = parsed.get("questions")
    if not isinstance(questions, list):
        raise AiGenerationError("AI response JSON must contain a questions list")
    return [item for item in questions if isinstance(item, dict)]


def parse_json_content(content: str) -> dict[str, Any]:
    cleaned = content.strip()
    fence = re.match(r"^```(?:json)?\s*(.*?)\s*```$", cleaned, flags=re.DOTALL)
    if fence:
        cleaned = fence.group(1).strip()
    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise AiGenerationError("AI response is not valid JSON") from exc
    if not isinstance(parsed, dict):
        raise AiGenerationError("AI response JSON must be an object")
    return parsed


def normalize_question(
    raw: dict[str, Any],
    payload: AiQuestionDraftCreate,
    chapter: Chapter,
    chunks: list[KnowledgeChunk],
) -> GeneratedQuestionDraft:
    question_type = str(raw.get("type") or payload.question_types[0]).strip()
    if question_type not in SUPPORTED_GENERATION_TYPES:
        raise AiGenerationError(f"Unsupported generated question type: {question_type}")
    difficulty = str(raw.get("difficulty") or payload.difficulty).strip()
    if difficulty not in {"easy", "medium", "hard"}:
        difficulty = payload.difficulty
    stem = str(raw.get("stem") or "").strip()
    if not stem:
        raise AiGenerationError("Generated question is missing stem")

    options = normalize_options(raw.get("options"))
    answer_json: Any
    rubric_json: Any = raw.get("rubric") if isinstance(raw.get("rubric"), list) else []

    if question_type == "single_choice":
        ensure_options(options)
        answer = normalize_choice_key(raw.get("answer"))
        ensure_answer_in_options(answer, options)
        answer_json = {"answer": answer}
    elif question_type == "multiple_choice":
        ensure_options(options)
        answers = [normalize_choice_key(item) for item in list_value(raw.get("answer"))]
        if not answers:
            raise AiGenerationError("Multiple choice question is missing answer")
        for answer in answers:
            ensure_answer_in_options(answer, options)
        answer_json = {"answer": sorted(set(answers))}
    elif question_type == "true_false":
        options = []
        answer_json = {"answer": normalize_true_false(raw.get("answer"))}
    elif question_type == "fill_blank":
        options = []
        blanks = normalize_blanks(raw.get("blanks"))
        if not blanks:
            raise AiGenerationError("Fill blank question is missing blanks")
        answer_json = {"blanks": blanks}
    else:
        options = []
        reference_answer = str(raw.get("reference_answer") or raw.get("answer") or "").strip()
        if not reference_answer:
            raise AiGenerationError("Generated written question is missing reference answer")
        answer_json = {"reference_answer": reference_answer}
        if not rubric_json:
            rubric_json = [reference_answer]

    source_chunks = ",".join(chunk.chunk_id for chunk in chunks[:8]) or "no-chunks"
    source_context = f"ai:model-draft;chunks={source_chunks}"
    explanation = str(raw.get("explanation") or "").strip() or None
    return GeneratedQuestionDraft(
        chapter_id=chapter.id,
        type=question_type,
        difficulty=difficulty,
        stem=stem,
        options_json=options,
        answer_json=answer_json,
        rubric_json=rubric_json,
        explanation=explanation,
        source_context=source_context,
    )


def normalize_options(value: Any) -> list[dict[str, str]]:
    if not isinstance(value, list):
        return []
    options = []
    for item in value:
        if not isinstance(item, dict):
            continue
        key = normalize_choice_key(item.get("key"))
        text = str(item.get("text") or "").strip()
        if key and text:
            options.append({"key": key, "text": text})
    return options


def normalize_choice_key(value: Any) -> str:
    return str(value or "").strip().upper()


def ensure_options(options: list[dict[str, str]]) -> None:
    if len(options) < 2:
        raise AiGenerationError("Choice question must contain at least two options")


def ensure_answer_in_options(answer: str, options: list[dict[str, str]]) -> None:
    if answer not in {option["key"] for option in options}:
        raise AiGenerationError("Choice answer must match one option key")


def list_value(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    if isinstance(value, str) and "," in value:
        return [item.strip() for item in value.split(",")]
    if value is None:
        return []
    return [value]


def normalize_true_false(value: Any) -> str:
    text = str(value or "").strip().upper()
    if text in {"TRUE", "T", "对", "正确", "YES"}:
        return "TRUE"
    if text in {"FALSE", "F", "错", "错误", "NO"}:
        return "FALSE"
    raise AiGenerationError("True/false answer must be TRUE or FALSE")


def normalize_blanks(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    blanks = []
    for index, item in enumerate(value, start=1):
        if not isinstance(item, dict):
            continue
        answer = str(item.get("answer") or "").strip()
        if not answer:
            continue
        acceptable_source = item.get("acceptable_answers") or []
        acceptable = [str(option).strip() for option in acceptable_source if str(option).strip()]
        blanks.append(
            {
                "index": int(item.get("index") or index),
                "answer": answer,
                "acceptable_answers": acceptable,
            }
        )
    return blanks
