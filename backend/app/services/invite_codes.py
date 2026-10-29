"""
توليد رمز دعوة للفصل — نص قصير يشاركه المعلّم مع طلابه للانضمام.

الأبجدية تستبعد الحروف/الأرقام المتشابهة بصريًا (0/O, 1/I/L) عشان الطالب يقدر
يكتبه من السبورة أو لقطة شاشة بدون لبس.
"""
import random

CODE_ALPHABET = "23456789ABCDEFGHJKMNPQRSTUVWXYZ"
CODE_LENGTH = 6


def generate_invite_code(rng: random.Random | None = None) -> str:
    rng = rng or random.Random()
    return "".join(rng.choice(CODE_ALPHABET) for _ in range(CODE_LENGTH))


def normalize_invite_code(raw: str) -> str:
    """يوحّد شكل الرمز اللي يدخله الطالب: أحرف كبيرة، بدون مسافات أو شرطات فاصلة"""
    return raw.strip().upper().replace("-", "").replace(" ", "")
