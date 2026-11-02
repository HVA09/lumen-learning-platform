"""
منطق الاختبارات — دوال بحتة (بدون قاعدة بيانات أو FastAPI) عشان تكون سهلة الاختبار.

المبدأ الأساسي: الطالب يرسل إجاباته فقط، والسيرفر هو اللي يصحّح ويحسب الدرجة والإتقان.
ما فيه أي مسار يقبل درجة أو نسبة إتقان جاهزة من المتصفح.
"""
import math
import random
import re
from datetime import datetime, timedelta
from typing import Any

PRACTICE_QUESTION_COUNT = 5
GATEWAY_QUESTION_COUNT = 10
GATEWAY_PASS_PERCENTAGE = 80.0
ATTEMPT_RESUME_HOURS = 2  # محاولة غير مسلَّمة أحدث من هذي المدة تُعاد بدل ما نولّد أسئلة جديدة
GATEWAY_RETRY_COOLDOWN_MINUTES = 5  # مهلة بين محاولتين فاشلتين لاختبار البوابة (تشجّع على مراجعة الدرس)
MASTERY_NEW_SCORE_WEIGHT = 0.5  # وزن آخر محاولة بالمتوسط المتحرك للإتقان

QUESTION_KINDS = ("mcq", "true_false", "numeric", "short_text")
QUIZ_MODES = ("practice", "gateway")
TRUE_FALSE_CHOICES = ["صحيح", "خطأ"]

# تشكيل + تطويل — نشيلها قبل مقارنة الإجابات النصية العربية
_DIACRITICS = re.compile("[\u0610-\u061a\u064b-\u065f\u0670\u06d6-\u06ed\u0640]")
_ARABIC_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹", "01234567890123456789")
_LETTER_MAP = str.maketrans({"أ": "ا", "إ": "ا", "آ": "ا", "ٱ": "ا", "ى": "ي", "ة": "ه"})
_EDGE_PUNCTUATION = " .,;:!?؟،؛\"'`"


def normalize_text(value: Any) -> str:
    """يوحّد شكل النص العربي/الإنجليزي للمقارنة: حروف صغيرة، أرقام غربية، بدون تشكيل،
    وأشكال الألف والياء والتاء المربوطة موحّدة، وبدون علامات ترقيم بأطراف النص"""
    text = str(value).strip().lower().translate(_ARABIC_DIGITS)
    text = _DIACRITICS.sub("", text).translate(_LETTER_MAP)
    text = re.sub(r"\s+", " ", text)
    return text.strip(_EDGE_PUNCTUATION)


def _squash(text: str) -> str:
    """يشيل كل المسافات — عشان range(1, 11) و range(1,11) يُعتبرون نفس الإجابة"""
    return re.sub(r"\s+", "", text)


def parse_number(value: Any) -> float | None:
    """يحوّل إدخال الطالب لرقم: يقبل أرقامًا عربية، فاصلة عشرية عربية أو نقطة/فاصلة،
    علامة سالب يونيكود، وكسر بسيط مثل 1/2. يرجّع None لو ما قدر."""
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        number = float(value)
    elif isinstance(value, str):
        text = value.strip().translate(_ARABIC_DIGITS)
        text = text.replace("\u2212", "-").replace("٫", ".").replace("٬", "")
        text = text.replace(",", ".").replace(" ", "")
        if not text:
            return None
        try:
            if "/" in text:
                numerator, denominator = text.split("/", 1)
                number = float(numerator) / float(denominator)
            else:
                number = float(text)
        except (ValueError, ZeroDivisionError):
            return None
    else:
        return None
    if math.isnan(number) or math.isinf(number):
        return None
    return number


def _as_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float) and value.is_integer():
        return int(value)
    if isinstance(value, str) and value.strip().lstrip("-").isdigit():
        return int(value.strip())
    return None


def _as_bool(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        text = value.strip().lower()
        if text in ("true", "1", "صحيح"):
            return True
        if text in ("false", "0", "خطأ", "خطا"):
            return False
    return None


def coerce_int(value: Any) -> int | None:
    """يحوّل إجابة الطالب لرقم صحيح إن أمكن (يقبل "2" و 2.0) — وإلا None"""
    return _as_int(value)


def coerce_bool(value: Any) -> bool | None:
    """يحوّل إجابة صح/خطأ (true/false/"صحيح"/"خطأ"/1/0) لقيمة منطقية — وإلا None"""
    return _as_bool(value)


def grade_answer(kind: str, correct_answer: Any, given: Any, tolerance: float | None = None) -> bool:
    """يصحّح إجابة وحدة. أي إدخال غير مفهوم يُعتبر خطأ (ما نرمي استثناء بسبب إدخال الطالب)"""
    if given is None:
        return False

    if kind == "mcq":
        index = _as_int(given)
        return index is not None and index == correct_answer

    if kind == "true_false":
        value = _as_bool(given)
        return value is not None and value == correct_answer

    if kind == "numeric":
        number = parse_number(given)
        expected = parse_number(correct_answer)
        if number is None or expected is None:
            return False
        return abs(number - expected) <= (tolerance or 0.0) + 1e-9

    if kind == "short_text":
        if not isinstance(given, str):
            return False
        candidate = _squash(normalize_text(given))
        if not candidate:
            return False
        accepted = correct_answer if isinstance(correct_answer, list) else [correct_answer]
        return any(candidate == _squash(normalize_text(item)) for item in accepted)

    return False


def _format_number(value: Any) -> str:
    number = parse_number(value)
    if number is None:
        return str(value)
    if number.is_integer() and abs(number) < 1e15:
        return str(int(number))
    return str(round(number, 6))


def describe_correct_answer(
    kind: str, correct_answer: Any, choices: list | None = None, tolerance: float | None = None
) -> str:
    """نص يعرض الإجابة الصحيحة للطالب بعد التسليم"""
    if kind == "mcq":
        index = _as_int(correct_answer)
        if index is not None and choices and 0 <= index < len(choices):
            return str(choices[index])
        return str(correct_answer)
    if kind == "true_false":
        return TRUE_FALSE_CHOICES[0] if correct_answer else TRUE_FALSE_CHOICES[1]
    if kind == "numeric":
        text = _format_number(correct_answer)
        if tolerance:
            text += f" (± {_format_number(tolerance)})"
        return text
    if kind == "short_text":
        accepted = correct_answer if isinstance(correct_answer, list) else [correct_answer]
        return " أو ".join(str(item) for item in accepted[:2])
    return str(correct_answer)


def public_choices(kind: str, choices: list | None) -> list[str] | None:
    """الخيارات اللي تنعرض للطالب — صح/خطأ له خيارات ثابتة، والرقمي/النصي بدون خيارات"""
    if kind == "true_false":
        return list(TRUE_FALSE_CHOICES)
    if kind == "mcq" and choices:
        return [str(c) for c in choices]
    return None


def validate_question_definition(
    kind: str, choices: list | None, correct_answer: Any, tolerance: float | None
) -> list[str]:
    """يتحقق من تعريف سؤال جديد (من المعلّم) — يرجّع قائمة أخطاء بالعربي (فاضية = صالح)"""
    errors: list[str] = []
    if kind not in QUESTION_KINDS:
        return [f"نوع السؤال غير مدعوم: {kind}"]

    if kind == "mcq":
        if not isinstance(choices, list) or not 2 <= len(choices) <= 6:
            errors.append("سؤال الاختيار من متعدد يحتاج من 2 إلى 6 خيارات")
        elif any(not isinstance(c, str) or not c.strip() for c in choices):
            errors.append("كل خيار لازم يكون نصًا غير فاضي")
        index = _as_int(correct_answer)
        if isinstance(correct_answer, bool) or index is None:
            errors.append("الإجابة الصحيحة لازم تكون رقم الخيار (يبدأ من 0)")
        elif isinstance(choices, list) and not 0 <= index < len(choices):
            errors.append("رقم الإجابة الصحيحة خارج نطاق الخيارات")
    elif kind == "true_false":
        if not isinstance(correct_answer, bool):
            errors.append("الإجابة الصحيحة لسؤال صح/خطأ لازم تكون true أو false")
    elif kind == "numeric":
        if parse_number(correct_answer) is None or isinstance(correct_answer, bool):
            errors.append("الإجابة الصحيحة لازم تكون رقمًا")
        if tolerance is not None and (not isinstance(tolerance, (int, float)) or tolerance < 0):
            errors.append("هامش الخطأ المقبول لازم يكون رقمًا لا يقل عن صفر")
    elif kind == "short_text":
        if (
            not isinstance(correct_answer, list)
            or not 1 <= len(correct_answer) <= 10
            or any(not isinstance(a, str) or not a.strip() for a in correct_answer)
        ):
            errors.append("الإجابة النصية تحتاج قائمة من 1 إلى 10 إجابات مقبولة (نصوص غير فاضية)")
    return errors


def question_count_for_mode(mode: str) -> int:
    return GATEWAY_QUESTION_COUNT if mode == "gateway" else PRACTICE_QUESTION_COUNT


def select_question_ids(
    available_ids: list[int], count: int, rng: random.Random | None = None
) -> list[int]:
    """يختار أسئلة عشوائية بدون تكرار — لو البنك أصغر من المطلوب يرجّع كل الأسئلة بترتيب عشوائي"""
    rng = rng or random.Random()
    ids = list(available_ids)
    if count >= len(ids):
        rng.shuffle(ids)
        return ids
    return rng.sample(ids, count)


def compute_score_percentage(correct_flags: list[bool]) -> float:
    if not correct_flags:
        return 0.0
    return round(100.0 * sum(1 for c in correct_flags if c) / len(correct_flags), 1)


def is_gateway_pass(score_percentage: float) -> bool:
    return score_percentage >= GATEWAY_PASS_PERCENTAGE


def update_mastery(
    previous_mastery: float, attempts_before: int, score: float, passed_gateway: bool = False
) -> float:
    """الإتقان = متوسط متحرك لدرجات المحاولات (أحدث محاولة وزنها 50%)، وأول محاولة تحدّده مباشرة.
    اجتياز اختبار البوابة يرفع الإتقان على الأقل لدرجة الاختبار — عشان ما يظهر 'متقن' بنسبة منخفضة."""
    if attempts_before <= 0:
        mastery = score
    else:
        mastery = previous_mastery * (1 - MASTERY_NEW_SCORE_WEIGHT) + score * MASTERY_NEW_SCORE_WEIGHT
    if passed_gateway:
        mastery = max(mastery, score)
    return round(min(100.0, max(0.0, mastery)), 1)


def _as_aware(value: datetime, reference: datetime) -> datetime:
    """لو التاريخ بدون منطقة زمنية نفترضه بنفس منطقة المرجع (قواعد بيانات معيّنة ترجّعه كذا)"""
    return value.replace(tzinfo=reference.tzinfo) if value.tzinfo is None else value


def can_resume_attempt(created_at: datetime, now: datetime) -> bool:
    """هل المحاولة غير المسلَّمة لسه ضمن نافذة الاستئناف؟"""
    return now - _as_aware(created_at, now) < timedelta(hours=ATTEMPT_RESUME_HOURS)


def gateway_cooldown_remaining_minutes(last_failed_submitted_at: datetime | None, now: datetime) -> int:
    """كم دقيقة تبقّت قبل ما يقدر الطالب يعيد اختبار البوابة بعد محاولة فاشلة (0 = يقدر الحين)"""
    if last_failed_submitted_at is None:
        return 0
    elapsed = now - _as_aware(last_failed_submitted_at, now)
    remaining = timedelta(minutes=GATEWAY_RETRY_COOLDOWN_MINUTES) - elapsed
    if remaining <= timedelta(0):
        return 0
    return math.ceil(remaining.total_seconds() / 60)


def normalize_correct_answer(kind: str, correct_answer: Any) -> Any:
    """يوحّد شكل الإجابة الصحيحة قبل حفظها (بعد ما نتأكد إنها صالحة بـ validate_question_definition)"""
    if kind == "mcq":
        return _as_int(correct_answer)
    if kind == "true_false":
        return bool(correct_answer)
    if kind == "numeric":
        return parse_number(correct_answer)
    if kind == "short_text":
        return [str(a).strip() for a in correct_answer]
    return correct_answer
