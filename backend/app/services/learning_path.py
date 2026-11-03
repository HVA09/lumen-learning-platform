from app.modules.learning_progress.domain.topic_progress import (
    STATUS_AVAILABLE,
    STATUS_IN_PROGRESS,
    STATUS_LOCKED,
    STATUS_MASTERED,
    compute_topic_status,
    pick_recommended_topic,
)

"""
مسار التعلّم — دوال بحتة (بدون قاعدة بيانات): تحسب حالة كل موضوع للطالب
(مقفل / متاح / قيد الدراسة / متقن) وتقترح الموضوع التالي.

قاعدة الفتح: الموضوع اللي له متطلّب سابق يُقفل لين يجتاز الطالب اختبار بوابة الموضوع السابق.
الطالب يقدر يقرأ دروس أي موضوع، لكن الاختبارات تحتاج فتح الموضوع (راجع routers/quiz.py).
"""

def build_learning_path(
    subjects: list[dict],
    mastery: dict[int, dict],
    lessons_total: dict[int, int],
    lessons_done: dict[int, int],
    questions_count: dict[int, int],
) -> dict:
    """يبني مسار الطالب الكامل.

    subjects: [{id, slug, name_ar, name_en, topics: [{id, slug, name_ar, name_en,
                learning_outcomes_ar, simulation_type, prerequisite_topic_id}]}]
    mastery:  {topic_id: {mastery_percentage, gateway_quiz_passed, attempts_count}}
    """
    topic_names = {t["id"]: t["name_ar"] for s in subjects for t in s["topics"]}

    flat: list[dict] = []
    out_subjects: list[dict] = []
    for subject in subjects:
        out_topics = []
        for topic in subject["topics"]:
            row = mastery.get(topic["id"], {})
            passed = bool(row.get("gateway_quiz_passed", False))
            percentage = float(row.get("mastery_percentage", 0.0))
            attempts = int(row.get("attempts_count", 0))
            done = lessons_done.get(topic["id"], 0)

            prerequisite_id = topic.get("prerequisite_topic_id")
            prerequisite_met = (
                prerequisite_id is None
                or prerequisite_id not in topic_names  # متطلّب محذوف/غير منشور — ما نقفل بسببه
                or bool(mastery.get(prerequisite_id, {}).get("gateway_quiz_passed", False))
            )

            item = {
                "id": topic["id"],
                "slug": topic["slug"],
                "name_ar": topic["name_ar"],
                "name_en": topic["name_en"],
                "learning_outcomes_ar": topic.get("learning_outcomes_ar") or [],
                "simulation_type": topic.get("simulation_type"),
                "prerequisite_topic_id": prerequisite_id,
                "prerequisite_name_ar": topic_names.get(prerequisite_id),
                "status": compute_topic_status(
                    gateway_passed=passed,
                    prerequisite_met=prerequisite_met,
                    has_activity=attempts > 0 or done > 0,
                ),
                "mastery_percentage": round(percentage, 1),
                "gateway_quiz_passed": passed,
                "lessons_total": lessons_total.get(topic["id"], 0),
                "lessons_completed": done,
                "questions_count": questions_count.get(topic["id"], 0),
            }
            out_topics.append(item)
            flat.append(item)
        out_subjects.append(
            {
                "id": subject["id"],
                "slug": subject["slug"],
                "name_ar": subject["name_ar"],
                "name_en": subject["name_en"],
                "topics": out_topics,
            }
        )

    mastered = sum(1 for t in flat if t["status"] == STATUS_MASTERED)
    overall = round(sum(t["mastery_percentage"] for t in flat) / len(flat), 1) if flat else 0.0
    return {
        "subjects": out_subjects,
        "recommended_topic_id": pick_recommended_topic(flat),
        "topics_total": len(flat),
        "topics_mastered": mastered,
        "overall_mastery": overall,
    }

__all__ = (
    "STATUS_LOCKED",
    "STATUS_AVAILABLE",
    "STATUS_IN_PROGRESS",
    "STATUS_MASTERED",
    "build_learning_path",
    "compute_topic_status",
    "pick_recommended_topic",
)
