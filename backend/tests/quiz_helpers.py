"""
مساعدات مشتركة لاختبارات الاختبارات والتحفيز والتقارير: تسجيل مستخدمين بأدوار مختلفة،
البحث عن موضوع بالـ slug، وإجراء اختبار كامل عبر الـ API (الإجابات الصحيحة تُقرأ من قاعدة البيانات مباشرة).
"""
from app.models.question import Question
from app.models.user import User, UserRole


def register_and_login(client, email, password="StrongPass123"):
    client.post("/auth/register", json={"email": email, "password": password})
    response = client.post("/auth/login", json={"email": email, "password": password})
    return response.cookies.get("lumen_access")


def auth(token):
    return {"Authorization": f"Bearer {token}"}


def make_student(client, email="student@example.com"):
    """يسجّل طالبًا عاديًا؛ التسجيل العام لا يمنح أدوارًا إدارية."""
    return register_and_login(client, email)


def set_role(db_session, email, role):
    user = db_session.query(User).filter(User.email == email).first()
    user.role = role
    db_session.commit()


def make_teacher(client, db_session, email="teacher@example.com"):
    token = make_student(client, email)
    set_role(db_session, email, UserRole.teacher)
    return token


def topic_id_by_slug(client, slug):
    for subject in client.get("/curriculum/subjects").json():
        for topic in subject["topics"]:
            if topic["slug"] == slug:
                return topic["id"]
    raise AssertionError(f"topic {slug} not seeded")


def correct_answer_payload(question: Question):
    """الإجابة الصحيحة بالشكل اللي يرسله الطالب (نقرأها من قاعدة البيانات مو من الـ API)"""
    if question.kind == "short_text":
        return question.correct_answer[0]
    return question.correct_answer


def take_quiz(client, db_session, token, topic_id, mode="practice", correct=True):
    """يبدأ اختبارًا ويسلّمه: كل الأجوبة صحيحة (correct=True) أو بدون أي إجابة (correct=False)"""
    started = client.post(
        f"/quiz/topics/{topic_id}/start", json={"mode": mode}, headers=auth(token)
    )
    assert started.status_code == 200, started.text
    attempt = started.json()
    answers = []
    if correct:
        for question in attempt["questions"]:
            row = db_session.get(Question, question["id"])
            answers.append(
                {"question_id": question["id"], "answer": correct_answer_payload(row)}
            )
    submitted = client.post(
        f"/quiz/attempts/{attempt['attempt_id']}/submit",
        json={"answers": answers},
        headers=auth(token),
    )
    assert submitted.status_code == 200, submitted.text
    return submitted.json()
