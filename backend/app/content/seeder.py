"""
زرع المنهج والمحتوى التعليمي بقاعدة البيانات — idempotent: تشغيله أكثر من مرة آمن، لأنه
يضيف فقط اللي غير موجود (بمفتاح ثابت: slug أو key) ولا يعدّل أو يحذف أي شيء موجود
(فأي تعديل يسويه المعلّم على الدروس والأسئلة يبقى).

يشتغل على SQLAlchemy Core بتعريفات جداول خفيفة (بدل نماذج ORM) عشان يصلح للاستدعاء من migration
ومن الاختبارات ومن سكربت يدوي بنفس الطريقة: seed_all(connection)
"""
import sqlalchemy as sa

from app.content.cards_data import CARDS
from app.content.curriculum_data import PLANS, SUBJECTS, TOPICS
from app.content.lessons_data import LESSONS
from app.content.questions_data import QUESTIONS

_subjects = sa.table(
    "subjects",
    sa.column("id", sa.Integer), sa.column("slug", sa.String), sa.column("name_ar", sa.String),
    sa.column("name_en", sa.String), sa.column("order_index", sa.Integer),
    sa.column("is_active", sa.Boolean),
)
_topics = sa.table(
    "topics",
    sa.column("id", sa.Integer), sa.column("subject_id", sa.Integer), sa.column("slug", sa.String),
    sa.column("name_ar", sa.String), sa.column("name_en", sa.String),
    sa.column("learning_outcomes_ar", sa.JSON), sa.column("skill_tags", sa.JSON),
    sa.column("prerequisite_topic_id", sa.Integer), sa.column("simulation_type", sa.String),
    sa.column("order_index", sa.Integer),
)
_plans = sa.table(
    "plans",
    sa.column("id", sa.Integer), sa.column("name", sa.String), sa.column("price_cents", sa.Integer),
    sa.column("currency", sa.String), sa.column("interval", sa.String), sa.column("is_active", sa.Boolean),
)
_lessons = sa.table(
    "lessons",
    sa.column("id", sa.Integer), sa.column("topic_id", sa.Integer), sa.column("slug", sa.String),
    sa.column("title_ar", sa.String), sa.column("body_md", sa.Text),
    sa.column("estimated_minutes", sa.Integer), sa.column("order_index", sa.Integer),
    sa.column("is_published", sa.Boolean),
)
_questions = sa.table(
    "questions",
    sa.column("id", sa.Integer), sa.column("topic_id", sa.Integer), sa.column("key", sa.String),
    sa.column("kind", sa.String), sa.column("prompt_ar", sa.Text), sa.column("choices", sa.JSON),
    sa.column("correct_answer", sa.JSON), sa.column("tolerance", sa.Float),
    sa.column("explanation_ar", sa.Text), sa.column("difficulty", sa.Integer),
    sa.column("is_active", sa.Boolean),
)
_topic_cards = sa.table(
    "topic_cards",
    sa.column("id", sa.Integer), sa.column("topic_id", sa.Integer), sa.column("key", sa.String),
    sa.column("front_text", sa.Text), sa.column("back_text", sa.Text), sa.column("order_index", sa.Integer),
)


def sync_sequences(connection) -> None:
    """migrations القديمة زرعت المواد والمواضيع بأرقام (id) صريحة بدون ما تحرّك عدّاد PostgreSQL،
    فأي إضافة جديدة بدون id تصطدم برقم موجود. نرفع العدّاد لآخر رقم مستخدم (PostgreSQL فقط)."""
    if connection.dialect.name != "postgresql":
        return
    for table in ("subjects", "topics"):
        connection.execute(
            sa.text(
                f"SELECT setval(pg_get_serial_sequence('{table}', 'id'), "
                f"COALESCE((SELECT MAX(id) FROM {table}), 1), "
                f"(SELECT MAX(id) FROM {table}) IS NOT NULL)"
            )
        )


def seed_curriculum(connection) -> None:
    """المواد والمواضيع وخطط الاشتراك الافتراضية (إن ما كانت موجودة)"""
    sync_sequences(connection)

    subject_ids = {r.slug: r.id for r in connection.execute(sa.select(_subjects.c.slug, _subjects.c.id))}
    for subject in SUBJECTS:
        if subject["slug"] not in subject_ids:
            # is_active صريحة: جداول create_all (الاختبارات) ما فيها server_default مثل جداول migrations
            connection.execute(_subjects.insert().values(is_active=True, **subject))
    subject_ids = {r.slug: r.id for r in connection.execute(sa.select(_subjects.c.slug, _subjects.c.id))}

    topic_ids = {r.slug: r.id for r in connection.execute(sa.select(_topics.c.slug, _topics.c.id))}
    for topic in TOPICS:
        if topic["slug"] in topic_ids:
            continue
        values = {k: v for k, v in topic.items() if k not in ("subject_slug", "prerequisite_slug")}
        values["subject_id"] = subject_ids[topic["subject_slug"]]
        values["prerequisite_topic_id"] = topic_ids.get(topic["prerequisite_slug"])
        connection.execute(_topics.insert().values(**values))
        topic_ids = {r.slug: r.id for r in connection.execute(sa.select(_topics.c.slug, _topics.c.id))}

    existing_plans = {r.name for r in connection.execute(sa.select(_plans.c.name))}
    for plan in PLANS:
        if plan["name"] not in existing_plans:
            connection.execute(_plans.insert().values(**plan))


def seed_education_content(connection) -> None:
    """الدروس وبنك الأسئلة وبطاقات المراجعة الجاهزة — لكل موضوع موجود بقاعدة البيانات"""
    topic_ids = {r.slug: r.id for r in connection.execute(sa.select(_topics.c.slug, _topics.c.id))}

    for slug, lessons in LESSONS.items():
        topic_id = topic_ids.get(slug)
        if topic_id is None:
            continue
        existing = {
            r.slug
            for r in connection.execute(sa.select(_lessons.c.slug).where(_lessons.c.topic_id == topic_id))
        }
        for lesson in lessons:
            if lesson["slug"] not in existing:
                connection.execute(
                    _lessons.insert().values(topic_id=topic_id, is_published=True, **lesson)
                )

    existing_question_keys = {
        r.key
        for r in connection.execute(sa.select(_questions.c.key).where(_questions.c.key.is_not(None)))
    }
    for slug, questions in QUESTIONS.items():
        topic_id = topic_ids.get(slug)
        if topic_id is None:
            continue
        for question in questions:
            if question["key"] not in existing_question_keys:
                connection.execute(
                    _questions.insert().values(topic_id=topic_id, is_active=True, **question)
                )

    existing_card_keys = {
        r.key
        for r in connection.execute(sa.select(_topic_cards.c.key).where(_topic_cards.c.key.is_not(None)))
    }
    for slug, cards in CARDS.items():
        topic_id = topic_ids.get(slug)
        if topic_id is None:
            continue
        for order, card in enumerate(cards, start=1):
            if card["key"] not in existing_card_keys:
                connection.execute(
                    _topic_cards.insert().values(topic_id=topic_id, order_index=order, **card)
                )


def seed_all(connection) -> None:
    seed_curriculum(connection)
    seed_education_content(connection)
