from __future__ import annotations

from typing import Any


def public_answer(answer_json: Any) -> Any:
    if isinstance(answer_json, dict) and "answer" in answer_json:
        return answer_json["answer"]
    if isinstance(answer_json, dict) and "blanks" in answer_json:
        return answer_json["blanks"]
    if isinstance(answer_json, dict) and "reference_answer" in answer_json:
        return answer_json["reference_answer"]
    return answer_json


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
            if actual and any(actual == str(item).strip() for item in accepted):
                matched += 1
        total = max(len(blanks), 1)
        score = matched / total
        return score == 1.0, score, f"填空匹配 {matched}/{total}"

    if question_type == "short_answer":
        text = str(user_answer or "").strip()
        rubric_items = rubric if isinstance(rubric, list) else []
        matched = sum(1 for item in rubric_items if str(item).strip() and str(item).strip() in text)
        if rubric_items:
            score = matched / len(rubric_items)
            return score >= 0.6, score, f"关键词/评分点命中 {matched}/{len(rubric_items)}"
        return bool(text), 1.0 if text else 0.0, "已提交简答，可对照参考答案自查"

    expected = str(correct_answer).strip()
    actual = str(user_answer).strip()
    is_correct = expected == actual
    return is_correct, 1.0 if is_correct else 0.0, "答案正确" if is_correct else "请对照解析复盘"
