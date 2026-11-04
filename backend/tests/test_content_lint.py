"""
فحص جودة المحتوى التعليمي الجاهز (دوال بحتة، بدون قاعدة بيانات): يمنع أخطاء الكتابة الشائعة
قبل ما تصل للطلاب — علامات $ غير متوازنة، خيارات مكررة، مفاتيح مكررة، وتغيّر معنى الأسئلة
بين إصدارات المحتوى.
"""
import re

from app.content.cards_data import CARDS
from app.content.legacy import load_seed_v1
from app.content.lessons_data import LESSONS
from app.content.questions_data import QUESTIONS
from app.modules.assessments.domain.quiz_logic import grade_answer, validate_question_definition


def _legacy():
    return load_seed_v1()


def _all_strings():
    for topic, lessons in LESSONS.items():
        for lesson in lessons:
            yield f"lesson:{lesson['slug']}", lesson["body_md"]
    for questions in QUESTIONS.values():
        for q in questions:
            yield f"{q['key']}:prompt", q["prompt_ar"]
            if q["explanation_ar"]:
                yield f"{q['key']}:explanation", q["explanation_ar"]
            for i, choice in enumerate(q["choices"] or []):
                yield f"{q['key']}:choice{i}", choice
    for cards in CARDS.values():
        for card in cards:
            yield f"{card['key']}:front", card["front_text"]
            yield f"{card['key']}:back", card["back_text"]


def _strip_code(text: str) -> str:
    """الشيفرة (أسوار ``` وbackticks) قد تحوي $ عادية — لا تُحسب ضمن توازن علامات الرياضيات"""
    text = re.sub(r"```.*?```", "", text, flags=re.S)
    return re.sub(r"`[^`]*`", "", text)


def test_math_delimiters_are_balanced_everywhere():
    for where, text in _all_strings():
        cleaned = _strip_code(text).replace("$$", "")
        assert cleaned.count("$") % 2 == 0, f"علامة $ يتيمة في {where}: {text[:60]!r}"


def test_no_space_padding_inside_inline_math():
    """remark-math لا يعتبر $ x $ رياضيات — لازم لا مسافة بعد الفتح ولا قبل الإغلاق"""
    for where, text in _all_strings():
        cleaned = re.sub(r"\$\$.*?\$\$", "", _strip_code(text), flags=re.S)
        for match in re.finditer(r"\$([^$\n]+)\$", cleaned):
            inner = match.group(1)
            assert inner == inner.strip(), f"مسافة زائدة داخل الرياضيات في {where}: ${inner}$"


def test_display_equations_use_fenced_blocks_not_a_single_line():
    """$$x$$ على سطر واحد يُحلَّل كرياضيات داخل السطر (نص عادي)، فلا تظهر معادلة منفصلة مركزية.
    المعادلة المنفصلة تحتاج $$ على سطر مستقل قبلها وبعدها."""
    for where, text in _all_strings():
        match = re.search(r"^\$\$.+\$\$[ \t]*$", _strip_code(text), flags=re.M)
        assert match is None, f"معادلة $$ بسطر واحد في {where}: {match.group(0)[:60]!r} — اكتبها على ثلاثة أسطر"


def test_math_topics_do_not_use_backticks_for_formulas():
    for topic in ("linear-equations", "derivatives-intro", "projectile-motion", "dc-circuits"):
        for q in QUESTIONS[topic]:
            for text in [q["prompt_ar"], q["explanation_ar"] or ""] + list(q["choices"] or []):
                assert "`" not in text, f"{q['key']} ما زال يستخدم backticks لصيغة رياضية: {text!r}"


def test_question_keys_are_unique_and_prefixed_by_topic():
    keys = [q["key"] for qs in QUESTIONS.values() for q in qs]
    assert len(keys) == len(set(keys))
    card_keys = [c["key"] for cs in CARDS.values() for c in cs]
    assert len(card_keys) == len(set(card_keys))


def test_mcq_choices_are_unique_and_answer_in_range():
    for qs in QUESTIONS.values():
        for q in qs:
            if q["kind"] == "mcq":
                assert len(set(q["choices"])) == len(q["choices"]), f"خيارات مكررة في {q['key']}"
                assert 0 <= q["correct_answer"] < len(q["choices"])


def test_every_question_is_valid_and_its_stored_answer_is_graded_correct():
    for qs in QUESTIONS.values():
        for q in qs:
            assert validate_question_definition(q["kind"], q["choices"], q["correct_answer"], q["tolerance"]) == []
            given = q["correct_answer"][0] if q["kind"] == "short_text" else q["correct_answer"]
            assert grade_answer(q["kind"], q["correct_answer"], given, q["tolerance"]), q["key"]


def test_card_fronts_are_unique_within_a_topic():
    for topic, cards in CARDS.items():
        fronts = [c["front_text"] for c in cards]
        assert len(fronts) == len(set(fronts)), topic


def test_every_topic_has_lessons_questions_and_cards():
    assert set(LESSONS) == set(QUESTIONS) == set(CARDS)
    for topic in LESSONS:
        assert len(LESSONS[topic]) >= 2 and len(QUESTIONS[topic]) >= 10 and len(CARDS[topic]) >= 5


# ---------- عدم تغيّر معنى المحتوى بين الإصدارات (يحمي سجل إجابات الطلاب) ----------

def test_legacy_snapshot_is_a_subset_of_current_content():
    """المحتوى يكبر بإضافة جديد لكن لا يُحذف شيء من الأصلي — حذفه يكسر سجل إجابات الطلاب وتحليل الأسئلة"""
    legacy = _legacy()
    assert {q["key"] for qs in legacy["questions"].values() for q in qs} <= {q["key"] for qs in QUESTIONS.values() for q in qs}
    assert {c["key"] for cs in legacy["cards"].values() for c in cs} <= {c["key"] for cs in CARDS.values() for c in cs}
    assert {lesson["slug"] for lessons in legacy["lessons"].values() for lesson in lessons} <= {lesson["slug"] for lessons in LESSONS.values() for lesson in lessons}


def test_question_meaning_never_changed_between_versions():
    legacy = {q["key"]: q for qs in _legacy()["questions"].values() for q in qs}
    for qs in QUESTIONS.values():
        for q in qs:
            old = legacy.get(q["key"])
            if old is None:
                continue  # سؤال أُضيف بعد الإصدار الأول
            for field in ("kind", "correct_answer", "tolerance", "difficulty"):
                assert old[field] == q[field], f"{q['key']}.{field} تغيّر بين الإصدارين"
            assert len(old["choices"] or []) == len(q["choices"] or []), q["key"]
