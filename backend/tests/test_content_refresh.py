"""
اختبار ترقية المحتوى (updater) على قاعدة بيانات حقيقية: تحويل المحتوى الأصلي v1 إلى v2
بدون المساس بتعديلات المعلّم، وأن التراجع يعيده كما كان.
"""
from app.content.legacy import load_seed_v1
from app.content.lessons_data import LESSONS
from app.content.updater import refresh_content_to_v2, revert_content_to_v1
from app.models.lesson import Lesson
from app.models.question import Question
from app.models.review_card import ReviewCard
from app.models.topic_card import TopicCard
from app.models.user import User


def _lesson(db, slug):
    return db.query(Lesson).filter(Lesson.slug == slug).first()


def _put_lesson_in_v1(db, topic_slug, index):
    old = load_seed_v1()["lessons"][topic_slug][index]
    lesson = _lesson(db, old["slug"])
    lesson.body_md = old["body_md"]
    return lesson, old


def _any_user_id(db):
    user = db.query(User).first()
    if user is None:
        user = User(email="refresh-test@example.com", hashed_password="x")
        db.add(user)
        db.flush()
    return user.id


def test_v1_lessons_are_upgraded_to_v2(db_session):
    lesson, old = _put_lesson_in_v1(db_session, "linear-equations", 0)
    db_session.flush()
    assert "$" not in lesson.body_md

    stats = refresh_content_to_v2(db_session.connection())
    db_session.expire_all()

    assert stats["lessons"] >= 1
    assert _lesson(db_session, old["slug"]).body_md == LESSONS["linear-equations"][0]["body_md"]


def test_lesson_edited_by_a_teacher_is_never_overwritten(db_session):
    _put_lesson_in_v1(db_session, "linear-equations", 0)
    edited = _lesson(db_session, "slope-and-intercept")
    edited.body_md = "نسخة عدّلها المعلّم"
    db_session.flush()

    refresh_content_to_v2(db_session.connection())
    db_session.expire_all()

    assert _lesson(db_session, "slope-and-intercept").body_md == "نسخة عدّلها المعلّم"
    assert _lesson(db_session, "solving-linear-equations").body_md == LESSONS["linear-equations"][0]["body_md"]


def test_question_fields_upgrade_independently_and_answers_never_change(db_session):
    old = next(q for q in load_seed_v1()["questions"]["derivatives-intro"] if q["key"] == "der-05")
    question = db_session.query(Question).filter(Question.key == "der-05").first()
    current_answer, current_choices = question.correct_answer, list(question.choices)
    question.prompt_ar = "صياغة المعلّم"                  # عدّلها المعلّم
    question.explanation_ar = old["explanation_ar"]         # ما زالت v1
    question.choices = old["choices"]                        # ما زالت v1
    db_session.flush()

    refresh_content_to_v2(db_session.connection())
    db_session.expire_all()
    question = db_session.query(Question).filter(Question.key == "der-05").first()

    assert question.prompt_ar == "صياغة المعلّم"
    assert question.explanation_ar != old["explanation_ar"] and "$" in question.explanation_ar
    assert question.choices == current_choices
    assert question.correct_answer == current_answer


def test_students_copies_of_starter_cards_follow_the_upgrade(db_session):
    old = next(c for c in load_seed_v1()["cards"]["derivatives-intro"] if c["key"] == "der-c5")
    starter = db_session.query(TopicCard).filter(TopicCard.key == "der-c5").first()
    starter.front_text, starter.back_text = old["front_text"], old["back_text"]
    user_id = _any_user_id(db_session)
    mine = ReviewCard(user_id=user_id, front_text=old["front_text"], back_text=old["back_text"], repetitions=4)
    mine_custom = ReviewCard(user_id=user_id, front_text="بطاقتي", back_text="جوابي")
    db_session.add_all([mine, mine_custom])
    db_session.flush()

    stats = refresh_content_to_v2(db_session.connection())
    db_session.expire_all()

    assert stats["starter_cards"] >= 1 and stats["student_cards"] >= 1
    starter = db_session.query(TopicCard).filter(TopicCard.key == "der-c5").first()
    assert "$" in starter.front_text
    refreshed = db_session.get(ReviewCard, mine.id)
    assert refreshed.front_text == starter.front_text and refreshed.repetitions == 4
    assert db_session.get(ReviewCard, mine_custom.id).front_text == "بطاقتي"


def test_refresh_is_idempotent_and_rollback_restores_v1(db_session):
    lesson, old = _put_lesson_in_v1(db_session, "dc-circuits", 0)
    db_session.flush()

    refresh_content_to_v2(db_session.connection())
    second = refresh_content_to_v2(db_session.connection())
    assert second == {"lessons": 0, "questions": 0, "starter_cards": 0, "student_cards": 0}

    revert_content_to_v1(db_session.connection())
    db_session.expire_all()
    assert _lesson(db_session, old["slug"]).body_md == old["body_md"]
