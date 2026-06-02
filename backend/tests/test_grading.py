from app.services.grading import grade_answer


def test_multiple_choice_grading_is_order_insensitive_and_exact() -> None:
    answer = {"answer": ["A", "C"]}

    is_correct, score, _ = grade_answer("multiple_choice", answer, ["c", "a"], [])
    assert is_correct is True
    assert score == 1.0

    is_correct, score, _ = grade_answer("multiple_choice", answer, ["A", "B", "C"], [])
    assert is_correct is False
    assert score == 0.0


def test_fill_blank_accepts_alias_answers() -> None:
    answer = {
        "blanks": [
            {"index": 1, "answer": "补码", "acceptable_answers": ["二进制补码"]},
            {"index": 2, "answer": "Cache", "acceptable_answers": ["高速缓存"]},
        ]
    }

    is_correct, score, feedback = grade_answer("fill_blank", answer, ["二进制补码", "高速缓存"], [])

    assert is_correct is True
    assert score == 1.0
    assert feedback == "填空匹配 2/2"


def test_fill_blank_scores_partial_matches() -> None:
    answer = {
        "blanks": [
            {"index": 1, "answer": "CPU", "acceptable_answers": []},
            {"index": 2, "answer": "主存", "acceptable_answers": ["内存"]},
        ]
    }

    is_correct, score, feedback = grade_answer("fill_blank", answer, ["CPU", "外存"], [])

    assert is_correct is False
    assert score == 0.5
    assert feedback == "填空匹配 1/2"


def test_fill_blank_normalizes_spacing_case_and_punctuation() -> None:
    answer = {"blanks": [{"index": 1, "answer": "Cache", "acceptable_answers": ["高速缓存"]}]}

    is_correct, score, _ = grade_answer("fill_blank", answer, [" cache，"], [])

    assert is_correct is True
    assert score == 1.0


def test_calculation_accepts_numeric_tolerance() -> None:
    answer = {"reference_answer": "平均访问时间为 10.5 ns"}

    is_correct, score, feedback = grade_answer("calculation", answer, "10.51ns", {"tolerance": 0.02})

    assert is_correct is True
    assert score == 1.0
    assert feedback == "计算结果匹配 1/1"


def test_short_answer_matches_normalized_rubric_items() -> None:
    answer = {"reference_answer": "Cache 利用局部性原理提高访存速度。"}

    is_correct, score, feedback = grade_answer("short_answer", answer, "cache利用局部性原理，提高速度", ["Cache", "局部性原理", "访存速度"])

    assert is_correct is True
    assert round(score, 2) == 0.67
    assert feedback == "关键词/评分点命中 2/3"
