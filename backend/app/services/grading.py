from __future__ import annotations

import re
import string
from typing import Any


def public_answer(answer_json: Any) -> Any:
    if isinstance(answer_json, dict) and "answer" in answer_json:
        return answer_json["answer"]
    if isinstance(answer_json, dict) and "blanks" in answer_json:
        return answer_json["blanks"]
    if isinstance(answer_json, dict) and "reference_answer" in answer_json:
        return answer_json["reference_answer"]
    return answer_json


def normalize_text(value: Any) -> str:
    text = str(value or "").strip().lower()
    text = re.sub(r"\s+", "", text)
    return text.strip(string.punctuation + "，。；：、（）()[]【】")


def text_matches(actual: Any, expected: Any) -> bool:
    return normalize_text(actual) == normalize_text(expected)


def extract_numbers(value: Any) -> list[float]:
    text = str(value or "")
    matches = re.findall(r"[-+]?(?:\d+\.\d+|\d+|\.\d+)(?:[eE][-+]?\d+)?", text)
    return [float(item) for item in matches]


def numeric_tolerance(expected: float, rubric: Any) -> float:
    if isinstance(rubric, dict):
        raw = rubric.get("tolerance")
        if raw is not None:
            try:
                return float(raw)
            except (TypeError, ValueError):
                pass
    return max(1e-6, abs(expected) * 0.005)


def calculation_score(correct_answer: Any, user_answer: Any, rubric: Any) -> tuple[bool, float, str]:
    expected_numbers = extract_numbers(correct_answer)
    actual_numbers = extract_numbers(user_answer)
    if expected_numbers and actual_numbers:
        matched = 0
        remaining = actual_numbers[:]
        for expected in expected_numbers:
            tolerance = numeric_tolerance(expected, rubric)
            match_index = next(
                (idx for idx, actual in enumerate(remaining) if abs(actual - expected) <= tolerance),
                None,
            )
            if match_index is not None:
                matched += 1
                remaining.pop(match_index)
        score = matched / max(len(expected_numbers), 1)
        return score == 1.0, score, f"计算结果匹配 {matched}/{len(expected_numbers)}"

    is_correct = text_matches(user_answer, correct_answer)
    return is_correct, 1.0 if is_correct else 0.0, "答案正确" if is_correct else "请对照解析复盘"


def grade_answer(question_type: str, answer_json: Any, user_answer: Any, rubric: Any) -> tuple[bool, float, str]:
    correct_answer = public_answer(answer_json)

    if question_type == "multiple_choice":
        expected = {str(item).strip().upper() for item in correct_answer}
        actual = {str(item).strip().upper() for item in (user_answer or [])}
        is_correct = expected == actual
        return is_correct, 1.0 if is_correct else 0.0, "答案完全正确" if is_correct else "多选题需要与标准答案完全一致"

    if question_type in {"single_choice", "true_false"}:
        expected = str(correct_answer).strip().upper()
        actual = str(user_answer).strip().upper()
        is_correct = expected == actual
        return is_correct, 1.0 if is_correct else 0.0, "答案正确" if is_correct else "答案不正确"

    if question_type in {"fill_blank", "cloze"}:
        blanks = correct_answer if isinstance(correct_answer, list) else []
        actual_items = user_answer if isinstance(user_answer, list) else [user_answer]
        matched = 0
        for idx, blank in enumerate(blanks):
            actual = str(actual_items[idx]).strip() if idx < len(actual_items) else ""
            accepted = [blank.get("answer", ""), *blank.get("acceptable_answers", [])]
            if actual and any(text_matches(actual, item) for item in accepted):
                matched += 1
        total = max(len(blanks), 1)
        score = matched / total
        return score == 1.0, score, f"填空匹配 {matched}/{total}"

    if question_type == "short_answer":
        text = str(user_answer or "").strip()
        rubric_items = rubric if isinstance(rubric, list) else []
        normalized_text = normalize_text(text)
        matched = sum(1 for item in rubric_items if normalize_text(item) and normalize_text(item) in normalized_text)
        if rubric_items:
            score = matched / len(rubric_items)
            return score >= 0.6, score, f"关键词/评分点命中 {matched}/{len(rubric_items)}"
        return bool(text), 1.0 if text else 0.0, "已提交简答，可对照参考答案自查"

    if question_type == "calculation":
        return calculation_score(correct_answer, user_answer, rubric)

    is_correct = text_matches(user_answer, correct_answer)
    return is_correct, 1.0 if is_correct else 0.0, "答案正确" if is_correct else "请对照解析复盘"
