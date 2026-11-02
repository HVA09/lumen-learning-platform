"""
اختبارات منطق الاختبارات (دوال بحتة): تصحيح الإجابات، التحقق من تعريف الأسئلة، الاختيار العشوائي، والإتقان
"""
import random
from datetime import datetime, timedelta, timezone

from app.services.quiz_logic import (
    GATEWAY_PASS_PERCENTAGE,
    can_resume_attempt,
    compute_score_percentage,
    describe_correct_answer,
    gateway_cooldown_remaining_minutes,
    grade_answer,
    is_gateway_pass,
    normalize_correct_answer,
    normalize_text,
    parse_number,
    public_choices,
    question_count_for_mode,
    select_question_ids,
    update_mastery,
    validate_question_definition,
)


def test_mcq_grading_uses_option_index():
    assert grade_answer("mcq", 2, 2) is True
    assert grade_answer("mcq", 2, "2") is True
    assert grade_answer("mcq", 2, 1) is False
    assert grade_answer("mcq", 1, True) is False  # True ما يُعتبر رقم الخيار 1
    assert grade_answer("mcq", 0, None) is False


def test_true_false_grading():
    assert grade_answer("true_false", True, True) is True
    assert grade_answer("true_false", False, False) is True
    assert grade_answer("true_false", True, False) is False
    assert grade_answer("true_false", True, "صحيح") is True
    assert grade_answer("true_false", True, "غير مفهوم") is False


def test_numeric_grading_with_tolerance_and_arabic_digits():
    assert grade_answer("numeric", 4, "4") is True
    assert grade_answer("numeric", 4, "٤") is True
    assert grade_answer("numeric", 2.5, "2,5") is True
    assert grade_answer("numeric", 2.5, "٢٫٥") is True
    assert grade_answer("numeric", 0.5, "1/2") is True
    assert grade_answer("numeric", -3, "\u22123") is True
    assert grade_answer("numeric", 20.4, 20.0, tolerance=0.5) is True
    assert grade_answer("numeric", 20.4, 19.0, tolerance=0.5) is False
    assert grade_answer("numeric", 4, "أربعة") is False
    assert grade_answer("numeric", 4, "nan") is False
    assert grade_answer("numeric", 4, True) is False


def test_short_text_ignores_diacritics_alef_forms_and_spacing():
    accepted = ["أوم", "قانون أوم"]
    assert grade_answer("short_text", accepted, "اوم") is True
    assert grade_answer("short_text", accepted, "  أُوم. ") is True
    assert grade_answer("short_text", accepted, "قانون  اوم") is True
    assert grade_answer("short_text", accepted, "فولت") is False
    assert grade_answer("short_text", accepted, "") is False
    assert grade_answer("short_text", ["range(1, 11)"], "range(1,11)") is True
    assert grade_answer("short_text", ["for"], "FOR") is True


def test_unknown_kind_is_wrong_instead_of_crashing():
    assert grade_answer("essay", "x", "x") is False


def test_normalize_text_unifies_arabic_variants():
    assert normalize_text("مُدَرِّسة") == normalize_text("مدرسه")
    assert normalize_text("إِلى") == normalize_text("الي")
    assert normalize_text("ـــمعادلة") == normalize_text("معادلة")


def test_parse_number_rejects_garbage():
    assert parse_number("") is None
    assert parse_number("1/0") is None
    assert parse_number("abc") is None
    assert parse_number(None) is None
    assert parse_number("inf") is None
    assert parse_number(" 3.5 ") == 3.5


def test_describe_correct_answer():
    assert describe_correct_answer("mcq", 1, ["أ", "ب", "ج"]) == "ب"
    assert describe_correct_answer("true_false", True) == "صحيح"
    assert describe_correct_answer("true_false", False) == "خطأ"
    assert describe_correct_answer("numeric", 20.0, tolerance=1.5) == "20 (± 1.5)"
    assert describe_correct_answer("numeric", 2.5) == "2.5"
    assert describe_correct_answer("short_text", ["أوم", "قانون أوم", "ثالث"]) == "أوم أو قانون أوم"


def test_public_choices_never_expose_answers():
    assert public_choices("true_false", None) == ["صحيح", "خطأ"]
    assert public_choices("mcq", ["أ", "ب"]) == ["أ", "ب"]
    assert public_choices("numeric", None) is None
    assert public_choices("short_text", None) is None


def test_validate_question_definition_accepts_valid_questions():
    assert validate_question_definition("mcq", ["أ", "ب"], 1, None) == []
    assert validate_question_definition("true_false", None, False, None) == []
    assert validate_question_definition("numeric", None, 3.5, 0.1) == []
    assert validate_question_definition("short_text", None, ["for"], None) == []


def test_validate_question_definition_rejects_invalid_questions():
    assert validate_question_definition("essay", None, "x", None)
    assert validate_question_definition("mcq", ["فقط خيار"], 0, None)
    assert validate_question_definition("mcq", ["أ", "ب"], 5, None)
    assert validate_question_definition("mcq", ["أ", "ب"], True, None)
    assert validate_question_definition("mcq", ["أ", " "], 0, None)
    assert validate_question_definition("true_false", None, "نعم", None)
    assert validate_question_definition("numeric", None, "abc", None)
    assert validate_question_definition("numeric", None, 1, -0.5)
    assert validate_question_definition("short_text", None, [], None)
    assert validate_question_definition("short_text", None, "for", None)


def test_select_question_ids_is_unique_and_bounded():
    rng = random.Random(7)
    picked = select_question_ids(list(range(1, 21)), 5, rng)
    assert len(picked) == 5
    assert len(set(picked)) == 5
    assert set(picked) <= set(range(1, 21))


def test_select_question_ids_returns_all_when_bank_is_small():
    picked = select_question_ids([4, 8, 15], 10, random.Random(1))
    assert sorted(picked) == [4, 8, 15]
    assert select_question_ids([], 5) == []


def test_score_percentage():
    assert compute_score_percentage([True, True, False, False]) == 50.0
    assert compute_score_percentage([True, False, False]) == 33.3
    assert compute_score_percentage([]) == 0.0


def test_gateway_pass_threshold_is_inclusive():
    assert is_gateway_pass(GATEWAY_PASS_PERCENTAGE) is True
    assert is_gateway_pass(GATEWAY_PASS_PERCENTAGE - 0.1) is False


def test_first_attempt_sets_mastery_directly_then_moving_average():
    assert update_mastery(0.0, 0, 60.0) == 60.0
    assert update_mastery(60.0, 1, 100.0) == 80.0
    assert update_mastery(80.0, 2, 40.0) == 60.0


def test_passing_gateway_lifts_mastery_to_at_least_the_score():
    # متوسط متحرك عادي: 30*0.5 + 90*0.5 = 60 — لكن اجتياز البوابة يرفعه لـ 90
    assert update_mastery(30.0, 3, 90.0, passed_gateway=True) == 90.0


def test_mastery_stays_within_bounds():
    assert update_mastery(100.0, 5, 100.0) == 100.0
    assert update_mastery(0.0, 5, 0.0) == 0.0


def test_question_count_per_mode():
    assert question_count_for_mode("gateway") > question_count_for_mode("practice")


def test_resume_window():
    now = datetime.now(timezone.utc)
    assert can_resume_attempt(now - timedelta(minutes=30), now) is True
    assert can_resume_attempt(now - timedelta(hours=5), now) is False


def test_gateway_cooldown_counts_down_and_ends():
    now = datetime.now(timezone.utc)
    assert gateway_cooldown_remaining_minutes(None, now) == 0
    assert gateway_cooldown_remaining_minutes(now, now) == 5
    assert gateway_cooldown_remaining_minutes(now - timedelta(minutes=2, seconds=30), now) == 3
    assert gateway_cooldown_remaining_minutes(now - timedelta(minutes=5), now) == 0
    assert gateway_cooldown_remaining_minutes(now - timedelta(hours=3), now) == 0


def test_naive_datetimes_are_treated_as_same_timezone_as_now():
    now = datetime.now(timezone.utc)
    naive_recent = (now - timedelta(minutes=10)).replace(tzinfo=None)
    assert can_resume_attempt(naive_recent, now) is True
    assert gateway_cooldown_remaining_minutes(naive_recent, now) == 0


def test_normalize_correct_answer_unifies_stored_shapes():
    assert normalize_correct_answer("mcq", "2") == 2
    assert normalize_correct_answer("numeric", "3.14") == 3.14
    assert normalize_correct_answer("numeric", 5) == 5.0
    assert normalize_correct_answer("short_text", ["  أوم ", "قانون أوم"]) == ["أوم", "قانون أوم"]
    assert normalize_correct_answer("true_false", True) is True
