"""ترقية المحتوى التعليمي إلى الإصدار 2 (رياضيات LaTeX + شيفرة منسّقة)

الدروس والأسئلة وبطاقات المراجعة الجاهزة صارت تُكتب بصيغة $...$ (KaTeX) بدل نص عادي.
هذي الـ migration تحدّث فقط الصفوف اللي ما زال نصها مطابقًا للمحتوى الأصلي — أي درس أو
سؤال عدّله معلّم يدويًا يبقى كما هو (راجع app/content/updater.py). فهرس الإجابة الصحيحة
وترتيب الخيارات لا يتغيران، فسجل إجابات الطلاب وتحليل الأسئلة يبقيان صالحين.

Revision ID: 0017_latex_content
Revises: 0016_classes_and_analytics
Create Date: 2026-09-29

"""
from typing import Sequence, Union

from alembic import context, op

revision: str = "0017_latex_content"
down_revision: Union[str, None] = "0016_classes_and_analytics"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    if context.is_offline_mode():  # وضع --sql: لا توجد قاعدة بيانات لنقرأ منها
        return
    from app.content.updater import refresh_content_to_v2

    refresh_content_to_v2(op.get_bind())


def downgrade() -> None:
    if context.is_offline_mode():
        return
    from app.content.updater import revert_content_to_v1

    revert_content_to_v1(op.get_bind())
