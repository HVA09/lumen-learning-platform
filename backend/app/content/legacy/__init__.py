"""
لقطة المحتوى الأصلي (الإصدار 1، قبل رياضيات LaTeX) — مرجع يعتمد عليه updater.py لمعرفة
أي صف ما زال نصه الأصلي فيُرقّى، وأي صف عدّله معلّم فيُترك. ملف خفيف بلا اعتماديات
(لا SQLAlchemy) عشان تقدر الاختبارات البحتة تقرأه.
"""
import json
import pathlib

SEED_V1_PATH = pathlib.Path(__file__).parent / "seed_v1.json"


def load_seed_v1() -> dict:
    """{"lessons": {...}, "questions": {...}, "cards": {...}} بنفس شكل lessons_data/questions_data/cards_data"""
    return json.loads(SEED_V1_PATH.read_text(encoding="utf-8"))
