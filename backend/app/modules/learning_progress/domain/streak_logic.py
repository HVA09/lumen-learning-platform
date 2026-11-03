"""
حساب سلسلة أيام الدراسة المتتالية (streak) — قاعدة مجال نقية.
لا تعتمد على قاعدة البيانات أو HTTP أو نماذج ORM.
"""
from datetime import date, timedelta


def compute_streak(days: set[date], today: date) -> int:
    """عدد الأيام المتتالية المنتهية اليوم، أو أمس لو ما درس اليوم بعد
    (اليوم الحالي ما يكسر الـ streak إلا لو فات يوم كامل بدون دراسة)."""
    if today in days:
        cursor = today
    elif today - timedelta(days=1) in days:
        cursor = today - timedelta(days=1)
    else:
        return 0

    count = 0
    while cursor in days:
        count += 1
        cursor -= timedelta(days=1)
    return count


__all__ = ("compute_streak",)
