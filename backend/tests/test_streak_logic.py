"""اختبارات قواعد حساب سلسلة أيام الدراسة المتتالية."""

from datetime import date, timedelta

from app.modules.learning_progress.domain.streak_logic import compute_streak


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
