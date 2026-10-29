"""
بنك الأسئلة: كل سؤال يتبع موضوعًا، والإجابة الصحيحة تُحفظ بالسيرفر فقط ولا تُرسل للطالب
إلا بعد تسليم المحاولة (راجع app/services/quiz_logic.py للتصحيح).

أنواع الأسئلة (kind) وشكل correct_answer:
- mcq         : اختيار من متعدد — رقم الخيار الصحيح (يبدأ من 0)، والخيارات بـ choices
- true_false  : صح/خطأ — قيمة منطقية
- numeric     : إجابة رقمية — الرقم الصحيح، و tolerance هامش الخطأ المقبول
- short_text  : إجابة نصية قصيرة — قائمة إجابات مقبولة (تُقارن بعد تطبيع الحروف العربية)
"""
from datetime import datetime
from typing import Any

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.database import Base


class Question(Base):
    __tablename__ = "questions"

    id: Mapped[int] = mapped_column(primary_key=True)
    topic_id: Mapped[int] = mapped_column(
        ForeignKey("topics.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # مفتاح ثابت للأسئلة المزروعة مع النظام (يخلّي إعادة الزرع آمنة بدون تكرار) — فاضي لأسئلة المعلّمين
    key: Mapped[str | None] = mapped_column(String(60), unique=True, nullable=True)
    kind: Mapped[str] = mapped_column(String(20), nullable=False)
    prompt_ar: Mapped[str] = mapped_column(Text, nullable=False)
    choices: Mapped[list | None] = mapped_column(JSON, nullable=True)
    correct_answer: Mapped[Any] = mapped_column(JSON, nullable=False)
    tolerance: Mapped[float | None] = mapped_column(Float, nullable=True)
    explanation_ar: Mapped[str | None] = mapped_column(Text, nullable=True)
    difficulty: Mapped[int] = mapped_column(Integer, default=1, nullable=False)  # 1 سهل .. 3 صعب
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_by_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
