"""اختبارات تحليل الأسئلة (دوال بحتة)"""
from app.services.question_analytics import (
    FLAG_CHECK_KEY,
    FLAG_EASIER,
    FLAG_HARDER,
    FLAG_INSUFFICIENT,
    FLAG_OK,
    MIN_ANSWERS_FOR_ANALYSIS,
    classify_question,
    most_common_wrong_answer,
    sort_for_review,
    success_rate,
)


def test_success_rate():
    assert success_rate(0, 0) is None
    assert success_rate(4, 3) == 75.0
    assert success_rate(3, 1) == 33.3
    assert success_rate(10, 10) == 100.0


def test_too_few_answers_is_insufficient():
    assert classify_question(1, MIN_ANSWERS_FOR_ANALYSIS - 1, 0) == FLAG_INSUFFICIENT
    assert classify_question(2, 0, 0) == FLAG_INSUFFICIENT


def test_nobody_correct_suggests_checking_the_answer_key():
    assert classify_question(1, 10, 0) == FLAG_CHECK_KEY
    assert classify_question(3, 6, 0) == FLAG_CHECK_KEY


def test_easy_question_with_low_success_is_harder_than_declared():
    assert classify_question(1, 10, 4) == FLAG_HARDER  # 40% < 65%


def test_hard_question_with_high_success_is_easier_than_declared():
    assert classify_question(3, 10, 9) == FLAG_EASIER  # 90% > 75%


def test_question_within_expected_range_is_ok():
    assert classify_question(1, 10, 8) == FLAG_OK
    assert classify_question(2, 10, 6) == FLAG_OK
    assert classify_question(3, 10, 4) == FLAG_OK


def test_boundaries_are_inclusive_of_the_expected_range():
    assert classify_question(1, 20, 13) == FLAG_OK  # 65% بالضبط
    assert classify_question(3, 20, 15) == FLAG_OK  # 75% بالضبط


def test_unknown_difficulty_falls_back_to_medium_range():
    assert classify_question(9, 10, 6) == FLAG_OK


def test_most_common_wrong_answer():
    assert most_common_wrong_answer([]) is None
    assert most_common_wrong_answer([None, None]) is None
    assert most_common_wrong_answer([2, 1, 2, 3, 2]) == (2, 3)
    assert most_common_wrong_answer([True, True, False]) == (True, 2)


def test_most_common_wrong_answer_handles_list_values():
    assert most_common_wrong_answer([[1, 2], [1, 2], [3]]) == ((1, 2), 2)


def test_sort_puts_weakest_first_and_insufficient_data_last():
    rows = [
        {"question_id": 1, "success_rate": 90.0, "flag": FLAG_OK},
        {"question_id": 2, "success_rate": None, "flag": FLAG_INSUFFICIENT},
        {"question_id": 3, "success_rate": 20.0, "flag": FLAG_HARDER},
        {"question_id": 4, "success_rate": 60.0, "flag": FLAG_OK},
        {"question_id": 5, "success_rate": 50.0, "flag": FLAG_INSUFFICIENT},
    ]
    assert [r["question_id"] for r in sort_for_review(rows)] == [3, 4, 1, 2, 5]
