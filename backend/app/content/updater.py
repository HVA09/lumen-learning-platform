"""
ترقية محتوى قاعدة بيانات موجودة من الإصدار 1 (نص عادي) إلى الإصدار 2 (رياضيات LaTeX).

القاعدة الأساسية: لا نكتب فوق أي شيء عدّله معلّم. كل حقل يُحدَّث فقط لو نصّه الحالي
يطابق حرفيًا نص الإصدار 1 الأصلي (المحفوظ في legacy/seed_v1.json). حقل تغيّر يدويًا
بعد الزرع يبقى كما هو.

- الدروس: تحديث body_md
- الأسئلة: تحديث نص السؤال والشرح والخيارات — كل حقل بشكل مستقل. ترتيب الخيارات وفهرس
  الإجابة الصحيحة لا يتغيران أبدًا (يتغير التنسيق فقط)، فسجل إجابات الطلاب يبقى صالحًا
- بطاقات المواضيع الجاهزة: تحديث النص، ثم نسخ الطلاب منها (نفس النص القديم بالضبط)
  حتى يبقى كشف "أضفت هذه المجموعة من قبل" صحيحًا ولا تتكرر البطاقات

آمن للتكرار (idempotent): بعد أول تشغيل ما يبقى شيء يطابق النص القديم.

يعمل بالاتجاهين: refresh_content_to_v2 للترقية، وrevert_content_to_v1 للتراجع (downgrade) —
نفس المنطق بعكس الطرفين: الحقل يتحوّل فقط لو نصّه الحالي يطابق نص الاتجاه المصدر.
"""
import json

import sqlalchemy as sa

from app.content.cards_data import CARDS
from app.content.legacy import load_seed_v1
from app.content.lessons_data import LESSONS
from app.content.questions_data import QUESTIONS

_topics = sa.table("topics", sa.column("id", sa.Integer), sa.column("slug", sa.String))
_lessons = sa.table(
    "lessons",
    sa.column("id", sa.Integer), sa.column("topic_id", sa.Integer),
    sa.column("slug", sa.String), sa.column("body_md", sa.Text),
)
_questions = sa.table(
    "questions",
    sa.column("id", sa.Integer), sa.column("key", sa.String), sa.column("prompt_ar", sa.Text),
    sa.column("choices", sa.JSON), sa.column("explanation_ar", sa.Text),
)
_topic_cards = sa.table(
    "topic_cards",
    sa.column("id", sa.Integer), sa.column("key", sa.String),
    sa.column("front_text", sa.Text), sa.column("back_text", sa.Text),
)
_review_cards = sa.table(
    "review_cards",
    sa.column("id", sa.Integer), sa.column("front_text", sa.Text), sa.column("back_text", sa.Text),
)


def _as_list(value):
    """بعض التعريفات ترجّع عمود JSON كنص — نوحّده لقائمة"""
    if isinstance(value, str):
        try:
            return json.loads(value)
        except ValueError:
            return value
    return value


def _migrate_lessons(connection, old: dict, new: dict) -> int:
    topic_ids = {r.slug: r.id for r in connection.execute(sa.select(_topics.c.slug, _topics.c.id))}
    updated = 0
    for topic_slug, lessons in new["lessons"].items():
        topic_id = topic_ids.get(topic_slug)
        if topic_id is None:
            continue
        old_by_slug = {lesson["slug"]: lesson for lesson in old["lessons"].get(topic_slug, [])}
        for lesson in lessons:
            old_lesson = old_by_slug.get(lesson["slug"])
            if old_lesson is None or old_lesson["body_md"] == lesson["body_md"]:
                continue
            result = connection.execute(
                _lessons.update()
                .where(
                    sa.and_(
                        _lessons.c.topic_id == topic_id,
                        _lessons.c.slug == lesson["slug"],
                        _lessons.c.body_md == old_lesson["body_md"],
                    )
                )
                .values(body_md=lesson["body_md"])
            )
            updated += result.rowcount
    return updated


def _migrate_questions(connection, old: dict, new: dict) -> int:
    old_by_key = {q["key"]: q for qs in old["questions"].values() for q in qs}
    new_by_key = {q["key"]: q for qs in new["questions"].values() for q in qs}
    rows = connection.execute(
        sa.select(
            _questions.c.id, _questions.c.key, _questions.c.prompt_ar,
            _questions.c.choices, _questions.c.explanation_ar,
        ).where(_questions.c.key.in_(list(new_by_key)))
    ).fetchall()

    updated = 0
    for row in rows:
        old_q, new_q = old_by_key.get(row.key), new_by_key.get(row.key)
        if old_q is None or new_q is None:
            continue
        changes = {}
        if row.prompt_ar == old_q["prompt_ar"] and new_q["prompt_ar"] != old_q["prompt_ar"]:
            changes["prompt_ar"] = new_q["prompt_ar"]
        if row.explanation_ar == old_q["explanation_ar"] and new_q["explanation_ar"] != old_q["explanation_ar"]:
            changes["explanation_ar"] = new_q["explanation_ar"]
        if (
            old_q["choices"] is not None
            and _as_list(row.choices) == old_q["choices"]
            and new_q["choices"] != old_q["choices"]
        ):
            assert len(new_q["choices"]) == len(old_q["choices"]), row.key  # الترتيب والعدد ثابتان
            changes["choices"] = new_q["choices"]
        if changes:
            connection.execute(_questions.update().where(_questions.c.id == row.id).values(**changes))
            updated += 1
    return updated


def _migrate_cards(connection, old: dict, new: dict) -> tuple[int, int]:
    old_by_key = {c["key"]: c for cs in old["cards"].values() for c in cs}
    starter_updated = student_updated = 0
    for cards in new["cards"].values():
        for card in cards:
            old_card = old_by_key.get(card["key"])
            if old_card is None or (old_card["front_text"], old_card["back_text"]) == (
                card["front_text"],
                card["back_text"],
            ):
                continue
            starter = connection.execute(
                _topic_cards.update()
                .where(
                    sa.and_(
                        _topic_cards.c.key == card["key"],
                        _topic_cards.c.front_text == old_card["front_text"],
                        _topic_cards.c.back_text == old_card["back_text"],
                    )
                )
                .values(front_text=card["front_text"], back_text=card["back_text"])
            )
            starter_updated += starter.rowcount
            copies = connection.execute(
                _review_cards.update()
                .where(
                    sa.and_(
                        _review_cards.c.front_text == old_card["front_text"],
                        _review_cards.c.back_text == old_card["back_text"],
                    )
                )
                .values(front_text=card["front_text"], back_text=card["back_text"])
            )
            student_updated += copies.rowcount
    return starter_updated, student_updated


def _current_content() -> dict:
    return {"lessons": LESSONS, "questions": QUESTIONS, "cards": CARDS}


def _migrate(connection, old: dict, new: dict) -> dict[str, int]:
    starter_cards, student_cards = _migrate_cards(connection, old, new)
    return {
        "lessons": _migrate_lessons(connection, old, new),
        "questions": _migrate_questions(connection, old, new),
        "starter_cards": starter_cards,
        "student_cards": student_cards,
    }


def refresh_content_to_v2(connection) -> dict[str, int]:
    """يرقّي المحتوى غير المعدَّل يدويًا من v1 إلى v2 ويرجّع عدد ما تغيّر بكل نوع"""
    return _migrate(connection, old=load_seed_v1(), new=_current_content())


def revert_content_to_v1(connection) -> dict[str, int]:
    """التراجع: يعيد المحتوى غير المعدَّل يدويًا من v2 إلى v1 (لمن يرجّع الواجهة لإصدار بلا KaTeX)"""
    return _migrate(connection, old=_current_content(), new=load_seed_v1())
