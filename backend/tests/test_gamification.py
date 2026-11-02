"""
اختبارات لوحة المتصدرين والإنجازات والإحصائيات الشخصية — كلها مبنية على بيانات يتحقق منها السيرفر
"""
from app.models.review_card import ReviewCard
from app.models.user import User
from tests.quiz_helpers import (
    auth,
    make_student,
    make_teacher,
    take_quiz,
    topic_id_by_slug,
)


def test_my_achievements_lists_all_definitions_locked_initially(client):
    token = make_student(client, "freshgamer@example.com")
    response = client.get("/gamification/my-achievements", headers=auth(token))
    assert response.status_code == 200
    achievements = response.json()
    assert len(achievements) >= 10
    assert all(a["unlocked_at"] is None for a in achievements)
    assert {"first_lesson", "first_quiz", "perfect_quiz", "gateway_first", "streak_3"} <= {
        a["key"] for a in achievements
    }


def test_passing_gateway_quiz_unlocks_gateway_achievement(client, db_session):
    token = make_student(client, "gatewaygamer@example.com")
    topic_id = topic_id_by_slug(client, "linear-equations")
    take_quiz(client, db_session, token, topic_id, mode="gateway", correct=True)

    achievements = client.get("/gamification/my-achievements", headers=auth(token)).json()
    by_key = {a["key"]: a for a in achievements}
    assert by_key["gateway_first"]["unlocked_at"] is not None
    assert by_key["first_quiz"]["unlocked_at"] is not None
    assert by_key["perfect_quiz"]["unlocked_at"] is not None
    assert by_key["gateway_five"]["unlocked_at"] is None


def test_failing_quiz_only_unlocks_first_quiz(client, db_session):
    token = make_student(client, "failer@example.com")
    topic_id = topic_id_by_slug(client, "linear-equations")
    take_quiz(client, db_session, token, topic_id, mode="practice", correct=False)

    by_key = {a["key"]: a for a in client.get("/gamification/my-achievements", headers=auth(token)).json()}
    assert by_key["first_quiz"]["unlocked_at"] is not None
    assert by_key["perfect_quiz"]["unlocked_at"] is None
    assert by_key["gateway_first"]["unlocked_at"] is None


def test_reviewing_a_card_unlocks_first_review_achievement(client):
    token = make_student(client, "reviewgamer@example.com")
    headers = auth(token)
    card = client.post("/srs/cards", json={"front_text": "س", "back_text": "ج"}, headers=headers).json()
    client.post(f"/srs/cards/{card['id']}/review", json={"grade": "good"}, headers=headers)

    achievements = client.get("/gamification/my-achievements", headers=headers).json()
    first_review = next(a for a in achievements if a["key"] == "first_review")
    assert first_review["unlocked_at"] is not None


def test_leaderboard_requires_authentication(client):
    assert client.get("/gamification/leaderboard").status_code == 401
    assert client.get("/gamification/my-stats").status_code == 401


def test_leaderboard_ranks_students_by_verified_score(client, db_session):
    top = make_student(client, "topscorer@example.com")
    mid = make_student(client, "midscorer@example.com")
    make_student(client, "zeroscorer@example.com")
    linear_id = topic_id_by_slug(client, "linear-equations")

    take_quiz(client, db_session, top, linear_id, mode="gateway", correct=True)  # بوابة 20 + إتقان 100% = 10
    take_quiz(client, db_session, mid, linear_id, mode="practice", correct=True)  # إتقان 100% = 10 فقط

    response = client.get("/gamification/leaderboard", headers=auth(top))
    assert response.status_code == 200
    entries = response.json()
    assert [e["score"] for e in entries] == [30, 10]  # الطالب بدون نقاط ما يظهر
    assert [e["rank"] for e in entries] == [1, 2]
    assert entries[0]["is_me"] is True
    assert entries[1]["is_me"] is False


def test_leaderboard_hides_emails_and_excludes_staff(client, db_session):
    student = make_student(client, "privatestudent@example.com")
    teacher = make_teacher(client, db_session, "leaderteacher@example.com")
    linear_id = topic_id_by_slug(client, "linear-equations")
    take_quiz(client, db_session, student, linear_id, mode="practice", correct=True)
    take_quiz(client, db_session, teacher, linear_id, mode="practice", correct=True)  # المعلّم ما يدخل اللوحة

    entries = client.get("/gamification/leaderboard", headers=auth(student)).json()
    assert len(entries) == 1
    assert "@" not in entries[0]["display_name"]
    assert "privatestudent" not in entries[0]["display_name"]

    user = db_session.query(User).filter(User.email == "privatestudent@example.com").first()
    user.full_name = "نورة"
    db_session.commit()
    entries = client.get("/gamification/leaderboard", headers=auth(student)).json()
    assert entries[0]["display_name"] == "نورة"


def test_card_points_are_capped_so_spamming_cards_does_not_win(client, db_session):
    token = make_student(client, "cardspammer@example.com")
    user = db_session.query(User).filter(User.email == "cardspammer@example.com").first()
    for i in range(40):
        db_session.add(ReviewCard(user_id=user.id, front_text=f"س{i}", back_text="ج", repetitions=1))
    db_session.commit()

    entries = client.get("/gamification/leaderboard", headers=auth(token)).json()
    assert entries[0]["score"] == 50  # سقف 25 بطاقة × نقطتين


def test_my_stats_tracks_score_streak_and_today(client, db_session):
    token = make_student(client, "statsuser@example.com")
    headers = auth(token)

    fresh = client.get("/gamification/my-stats", headers=headers).json()
    assert fresh == {"score": 0, "rank": None, "streak_days": 0, "studied_today": False}

    take_quiz(client, db_session, token, topic_id_by_slug(client, "linear-equations"), mode="gateway", correct=True)
    stats = client.get("/gamification/my-stats", headers=headers).json()
    assert stats["score"] == 30
    assert stats["rank"] == 1
    assert stats["streak_days"] == 1
    assert stats["studied_today"] is True


def test_staff_stats_show_score_without_rank(client, db_session):
    teacher = make_teacher(client, db_session, "statsteacher@example.com")
    take_quiz(client, db_session, teacher, topic_id_by_slug(client, "linear-equations"), mode="practice", correct=True)

    stats = client.get("/gamification/my-stats", headers=auth(teacher)).json()
    assert stats["rank"] is None
    assert stats["score"] == 10


def test_streak_achievement_after_three_consecutive_days(client, db_session):
    from datetime import datetime, timedelta, timezone

    from app.models.study_day import StudyDay

    token = make_student(client, "streaker@example.com")
    user = db_session.query(User).filter(User.email == "streaker@example.com").first()
    today = datetime.now(timezone.utc).date()  # السيرفر يحسب الأيام بتوقيت UTC
    for offset in (1, 2):
        db_session.add(StudyDay(user_id=user.id, day=today - timedelta(days=offset)))
    db_session.commit()

    # نشاط اليوم (إنهاء درس) يكمّل 3 أيام متتالية
    topic_id = topic_id_by_slug(client, "linear-equations")
    lessons = client.get(f"/curriculum/topics/{topic_id}/lessons", headers=auth(token)).json()
    response = client.post(f"/curriculum/lessons/{lessons[0]['id']}/complete", headers=auth(token))
    assert "streak_3" in {a["key"] for a in response.json()["new_achievements"]}
    assert client.get("/gamification/my-stats", headers=auth(token)).json()["streak_days"] == 3

