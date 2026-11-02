"""
اختبارات مسار التعلّم والـ streak (دوال بحتة)
"""
from datetime import date, timedelta

from app.services.learning_path import (
    STATUS_AVAILABLE,
    STATUS_IN_PROGRESS,
    STATUS_LOCKED,
    STATUS_MASTERED,
    build_learning_path,
    compute_topic_status,
    pick_recommended_topic,
)
from app.services.streak_logic import compute_streak


def _subjects():
    return [
        {
            "id": 1, "slug": "math", "name_ar": "الرياضيات", "name_en": "Math",
            "topics": [
                {"id": 1, "slug": "a", "name_ar": "أ", "name_en": "A", "prerequisite_topic_id": None},
                {"id": 2, "slug": "b", "name_ar": "ب", "name_en": "B", "prerequisite_topic_id": 1},
            ],
        },
        {
            "id": 2, "slug": "physics", "name_ar": "الفيزياء", "name_en": "Physics",
            "topics": [
                {"id": 3, "slug": "c", "name_ar": "ج", "name_en": "C", "prerequisite_topic_id": None},
            ],
        },
    ]


def _statuses(path):
    return {t["id"]: t["status"] for s in path["subjects"] for t in s["topics"]}


def test_topic_status_rules():
    assert compute_topic_status(gateway_passed=True, prerequisite_met=False, has_activity=False) == STATUS_MASTERED
    assert compute_topic_status(gateway_passed=False, prerequisite_met=False, has_activity=True) == STATUS_LOCKED
    assert compute_topic_status(gateway_passed=False, prerequisite_met=True, has_activity=True) == STATUS_IN_PROGRESS
    assert compute_topic_status(gateway_passed=False, prerequisite_met=True, has_activity=False) == STATUS_AVAILABLE


def test_new_student_sees_locked_dependent_topic_and_first_topic_recommended():
    path = build_learning_path(_subjects(), {}, {}, {}, {})
    assert _statuses(path) == {1: STATUS_AVAILABLE, 2: STATUS_LOCKED, 3: STATUS_AVAILABLE}
    assert path["recommended_topic_id"] == 1
    assert path["topics_total"] == 3
    assert path["topics_mastered"] == 0
    assert path["overall_mastery"] == 0.0


def test_passing_prerequisite_gateway_unlocks_dependent_topic():
    mastery = {1: {"mastery_percentage": 90.0, "gateway_quiz_passed": True, "attempts_count": 2}}
    path = build_learning_path(_subjects(), mastery, {}, {}, {})
    assert _statuses(path) == {1: STATUS_MASTERED, 2: STATUS_AVAILABLE, 3: STATUS_AVAILABLE}
    assert path["topics_mastered"] == 1
    assert path["recommended_topic_id"] == 2


def test_high_mastery_without_gateway_does_not_unlock_dependent_topic():
    mastery = {1: {"mastery_percentage": 99.0, "gateway_quiz_passed": False, "attempts_count": 4}}
    path = build_learning_path(_subjects(), mastery, {}, {}, {})
    assert _statuses(path)[2] == STATUS_LOCKED
    assert _statuses(path)[1] == STATUS_IN_PROGRESS


def test_recommendation_prefers_weakest_in_progress_topic():
    mastery = {
        1: {"mastery_percentage": 70.0, "gateway_quiz_passed": False, "attempts_count": 3},
        3: {"mastery_percentage": 35.0, "gateway_quiz_passed": False, "attempts_count": 1},
    }
    path = build_learning_path(_subjects(), mastery, {}, {}, {})
    assert path["recommended_topic_id"] == 3


def test_reading_a_lesson_counts_as_progress():
    path = build_learning_path(_subjects(), {}, {1: 2}, {1: 1}, {})
    assert _statuses(path)[1] == STATUS_IN_PROGRESS
    topic = path["subjects"][0]["topics"][0]
    assert topic["lessons_total"] == 2 and topic["lessons_completed"] == 1


def test_everything_mastered_has_no_recommendation():
    mastery = {i: {"mastery_percentage": 95.0, "gateway_quiz_passed": True, "attempts_count": 1} for i in (1, 2, 3)}
    path = build_learning_path(_subjects(), mastery, {}, {}, {})
    assert path["recommended_topic_id"] is None
    assert path["topics_mastered"] == 3


def test_dangling_prerequisite_does_not_lock_forever():
    subjects = _subjects()
    subjects[0]["topics"][1]["prerequisite_topic_id"] = 999  # موضوع غير موجود بالمسار
    path = build_learning_path(subjects, {}, {}, {}, {})
    assert _statuses(path)[2] == STATUS_AVAILABLE


def test_pick_recommended_topic_empty_list():
    assert pick_recommended_topic([]) is None


def test_streak_counts_consecutive_days_ending_today():
    today = date(2026, 9, 20)
    days = {today, today - timedelta(days=1), today - timedelta(days=2)}
    assert compute_streak(days, today) == 3


def test_streak_survives_until_end_of_today_if_studied_yesterday():
    today = date(2026, 9, 20)
    assert compute_streak({today - timedelta(days=1), today - timedelta(days=2)}, today) == 2


def test_streak_breaks_after_a_missed_day():
    today = date(2026, 9, 20)
    assert compute_streak({today - timedelta(days=2), today - timedelta(days=3)}, today) == 0
    assert compute_streak(set(), today) == 0


def test_streak_stops_at_gap():
    today = date(2026, 9, 20)
    days = {today, today - timedelta(days=1), today - timedelta(days=3)}
    assert compute_streak(days, today) == 2
