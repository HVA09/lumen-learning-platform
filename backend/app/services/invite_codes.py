"""
توليد رمز دعوة للفصل — نص قصير يشاركه المعلّم مع طلابه للانضمام.

الأبجدية تستبعد الحروف/الأرقام المتشابهة بصريًا (0/O, 1/I/L) عشان الطالب يقدر
يكتبه من السبورة أو لقطة شاشة بدون لبس.
"""
import random
import secrets

CODE_ALPHABET = "23456789ABCDEFGHJKMNPQRSTUVWXYZ"
CODE_LENGTH = 8


def generate_invite_code(rng: random.Random | None = None) -> str:
    chooser = rng.choice if rng is not None else secrets.choice
    return "".join(chooser(CODE_ALPHABET) for _ in range(CODE_LENGTH))


def normalize_invite_code(raw: str) -> str:
    """يوحّد شكل الرمز اللي يدخله الطالب: أحرف كبيرة، بدون مسافات أو شرطات فاصلة"""
    return raw.strip().upper().replace("-", "").replace(" ", "")
