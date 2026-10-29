"""
خوارزمية التكرار المتباعد SM-2+ (مبنية على SuperMemo-2 الأصلية، مع خطوات تعلّم
قصيرة قبل التخرّج لجدول SM-2 الكامل — نفس أسلوب أنظمة مثل Anki).

التقييم على 3 مستويات بدل مقياس SM-2 الأصلي 0-5 (أبسط للواجهة):
- "again": فشل — يرجع لخطوات التعلّم من جديد وينقص معامل السهولة (EF)
- "good": نجح بصعوبة عادية — EF ثابت
- "easy": نجح بسهولة — يرفع EF ويكبّر الفاصل الزمني أكثر (مكافأة الحفظ السهل)

leech: بطاقة فشلت فيها كثير (LEECH_THRESHOLD مرة) رغم المراجعة المتكررة —
تُعلَّم عشان الطالب أو المعلّم ينتبه لها (يحتاج شرح مختلف، مو بس تكرار)
"""
from datetime import datetime, timedelta, timezone

from app.models.review_card import CardState, ReviewCard

LEECH_THRESHOLD = 8
GRADUATING_REPETITIONS = 3  # بعد كم مراجعة ناجحة متتالية تتخرّج البطاقة لجدول SM-2 الكامل
LEARNING_STEPS_DAYS = [1, 3]  # فواصل خطوات التعلّم قبل التخرّج (يوم واحد، ثم 3 أيام)

MIN_EASE_FACTOR = 1.3
MAX_EASE_FACTOR = 3.5
LAPSE_EASE_PENALTY = 0.2
EASY_EASE_BONUS = 0.15
EASY_INTERVAL_BONUS = 1.3
MAX_INTERVAL_DAYS = 365

Grade = str  # "again" | "good" | "easy"


def _next_review_interval(previous_days: int, ease_factor: float, easy: bool) -> int:
    """الفاصل الجديد دائمًا أكبر من السابق بيوم على الأقل (بدون هذا الشرط، التقريب
    يخلّي فاصل صغير مع EF منخفض يعلق على نفس القيمة) ولا يتجاوز سقف سنة"""
    factor = ease_factor * (EASY_INTERVAL_BONUS if easy else 1.0)
    return min(MAX_INTERVAL_DAYS, max(previous_days + 1, round(previous_days * factor)))


def review_card(card: ReviewCard, grade: Grade, now: datetime | None = None) -> ReviewCard:
    """يطبّق تقييم مراجعة وحدة على البطاقة ويحدّث حالتها SM-2+ بالكامل (in-place)"""
    now = now or datetime.now(timezone.utc)

    if grade == "again":
        card.lapses += 1
        card.repetitions = 0
        card.state = CardState.relearning if card.state == CardState.review else CardState.learning
        card.interval_days = LEARNING_STEPS_DAYS[0]
        card.ease_factor = max(MIN_EASE_FACTOR, card.ease_factor - LAPSE_EASE_PENALTY)
        if card.lapses >= LEECH_THRESHOLD:
            card.is_leech = True
    else:
        easy = grade == "easy"
        card.repetitions += 1

        if card.state in (CardState.new, CardState.learning, CardState.relearning):
            step_index = card.repetitions - 1
            if step_index < len(LEARNING_STEPS_DAYS):
                card.interval_days = LEARNING_STEPS_DAYS[step_index]
                card.state = CardState.learning
            else:
                card.state = CardState.review
                card.interval_days = _next_review_interval(card.interval_days, card.ease_factor, easy)
        else:  # already in review — نمو SM-2 الكامل
            card.interval_days = _next_review_interval(card.interval_days, card.ease_factor, easy)

        if card.repetitions >= GRADUATING_REPETITIONS:
            card.state = CardState.review

        if easy:
            card.ease_factor = min(MAX_EASE_FACTOR, card.ease_factor + EASY_EASE_BONUS)

    card.due_at = now + timedelta(days=card.interval_days)
    return card
