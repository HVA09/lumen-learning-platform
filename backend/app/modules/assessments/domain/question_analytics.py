"""
تحليل الأسئلة (Item Analysis) — دوال بحتة بدون قاعدة بيانات.

الفكرة: نسبة نجاح الطلاب الفعلية بكل سؤال تكشف للمعلّم أسئلة تحتاج مراجعة:
- سؤال لا أحد جاوب عليه صح غالبًا مفتاح إجابته خاطئ أو صياغته ملتبسة
- سؤال مصنّف "سهل" ونسبة نجاحه منخفضة، أو العكس، يعني تصنيف صعوبته غير دقيق
"""
from collections import Counter
from typing import Any

MIN_ANSWERS_FOR_ANALYSIS = 5

# المدى المتوقع لنسبة النجاح (%) حسب الصعوبة اللي حدّدها المعلّم (1 سهل .. 3 صعب)
EXPECTED_SUCCESS_RANGE = {
    1: (65.0, 100.0),
    2: (40.0, 90.0),
    3: (15.0, 75.0),
}

FLAG_INSUFFICIENT = "insufficient_data"
FLAG_OK = "ok"
FLAG_CHECK_KEY = "check_answer_key"
FLAG_HARDER = "harder_than_declared"
FLAG_EASIER = "easier_than_declared"

FLAG_LABELS_AR = {
    FLAG_INSUFFICIENT: "بيانات غير كافية",
    FLAG_OK: "سليم",
    FLAG_CHECK_KEY: "لا أحد أجاب صح — راجع مفتاح الإجابة أو الصياغة",
    FLAG_HARDER: "أصعب من المصنّف — راجع الصياغة أو ارفع الصعوبة",
    FLAG_EASIER: "أسهل من المصنّف — خفّض الصعوبة أو صعّب السؤال",
}


def success_rate(answered: int, correct: int) -> float | None:
    """نسبة النجاح المئوية، أو None لو ما أحد جاوب"""
    if answered <= 0:
        return None
    return round(100.0 * correct / answered, 1)


def classify_question(declared_difficulty: int, answered: int, correct: int) -> str:
    """يحدّد حالة السؤال بحسب أداء الطلاب الفعلي مقابل صعوبته المصنّفة"""
    if answered < MIN_ANSWERS_FOR_ANALYSIS:
        return FLAG_INSUFFICIENT
    rate = success_rate(answered, correct)
    if rate == 0.0:
        return FLAG_CHECK_KEY
    low, high = EXPECTED_SUCCESS_RANGE.get(declared_difficulty, EXPECTED_SUCCESS_RANGE[2])
    if rate < low:
        return FLAG_HARDER
    if rate > high:
        return FLAG_EASIER
    return FLAG_OK


def most_common_wrong_answer(given_answers: list[Any]) -> tuple[Any, int] | None:
    """أكثر إجابة خاطئة تكرارًا (القيمة، عدد المرات) — يكشف "مشتّت" جذّاب في سؤال الاختيار من متعدد.
    الإجابات الفارغة (None) تُتجاهل لأنها تعني ترك السؤال وليست اختيارًا"""
    counts = Counter(_hashable(a) for a in given_answers if a is not None)
    if not counts:
        return None
    value, count = counts.most_common(1)[0]
    return value, count


def _hashable(value: Any) -> Any:
    return tuple(value) if isinstance(value, list) else value


def sort_for_review(rows: list[dict]) -> list[dict]:
    """الأسئلة اللي تحتاج مراجعة أولًا: أدنى نسبة نجاح، ثم الأسئلة بلا بيانات كافية بالنهاية"""
    with_data = [r for r in rows if r["flag"] != FLAG_INSUFFICIENT]
    without_data = [r for r in rows if r["flag"] == FLAG_INSUFFICIENT]
    with_data.sort(key=lambda r: (r["success_rate"] if r["success_rate"] is not None else 101.0, r["question_id"]))
    without_data.sort(key=lambda r: r["question_id"])
    return with_data + without_data


# Public API maintained by the legacy compatibility facade.
__all__ = (
    "EXPECTED_SUCCESS_RANGE",
    "FLAG_CHECK_KEY",
    "FLAG_EASIER",
    "FLAG_HARDER",
    "FLAG_INSUFFICIENT",
    "FLAG_LABELS_AR",
    "FLAG_OK",
    "MIN_ANSWERS_FOR_ANALYSIS",
    "classify_question",
    "most_common_wrong_answer",
    "sort_for_review",
    "success_rate",
)
