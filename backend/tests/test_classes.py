"""
اختبارات الفصول الدراسية: إنشاء، انضمام برمز دعوة، إدارة القائمة، وتحديد نطاق الواجبات ولوحة المتصدرين
"""
from tests.quiz_helpers import (
    auth,
    make_admin,
    make_student,
    make_teacher,
    take_quiz,
    topic_id_by_slug,
)


def _create_class(client, teacher_token, name="الرياضيات — الصف العاشر"):
    response = client.post("/classes", json={"name": name}, headers=auth(teacher_token))
    assert response.status_code == 201, response.text
    return response.json()


def _join(client, student_token, code):
    return client.post("/classes/join", json={"invite_code": code}, headers=auth(student_token))


def _create_assignment(client, teacher_token, **overrides):
    payload = {"title": "واجب", "description": "حل التمارين", **overrides}
    response = client.post("/assignments", json=payload, headers=auth(teacher_token))
    assert response.status_code == 201, response.text
    return response.json()


# ---------- إنشاء الفصل ----------

def test_classes_require_authentication(client):
    assert client.get("/classes").status_code == 401
    assert client.post("/classes", json={"name": "س"}).status_code == 401
    assert client.post("/classes/join", json={"invite_code": "ABC234"}).status_code == 401


def test_student_cannot_create_class(client):
    student = make_student(client, "noclass@example.com")
    assert client.post("/classes", json={"name": "س"}, headers=auth(student)).status_code == 403


def test_teacher_creates_class_with_invite_code(client, db_session):
    teacher = make_teacher(client, db_session)
    created = _create_class(client, teacher)
    assert created["name"] == "الرياضيات — الصف العاشر"
    assert len(created["invite_code"]) == 6
    assert created["student_count"] == 0
    assert created["is_archived"] is False


def test_class_name_is_required(client, db_session):
    teacher = make_teacher(client, db_session)
    assert client.post("/classes", json={"name": ""}, headers=auth(teacher)).status_code == 422


# ---------- الانضمام ----------

def test_student_joins_with_code_case_insensitive_and_idempotent(client, db_session):
    teacher = make_teacher(client, db_session)
    student = make_student(client, "joiner@example.com")
    created = _create_class(client, teacher)

    messy_code = f"  {created['invite_code'].lower()[:3]}-{created['invite_code'][3:]} "
    joined = _join(client, student, messy_code)
    assert joined.status_code == 200
    assert joined.json()["id"] == created["id"]
    assert joined.json()["student_count"] == 1

    again = _join(client, student, created["invite_code"])
    assert again.status_code == 200
    assert again.json()["student_count"] == 1  # ما يتكرر التسجيل


def test_join_with_wrong_code_404(client):
    student = make_student(client, "wrongcode@example.com")
    assert _join(client, student, "ZZZZZZ").status_code == 404


# ---------- القوائم والتفاصيل ----------

def test_list_classes_is_scoped_by_role(client, db_session):
    teacher_a = make_teacher(client, db_session, "teacher-a@example.com")
    teacher_b = make_teacher(client, db_session, "teacher-b@example.com")
    student = make_student(client, "lister@example.com")
    other_student = make_student(client, "otherlister@example.com")
    admin = make_admin(client, db_session, "first-admin@example.com")

    class_a = _create_class(client, teacher_a, "فصل أ")
    class_b = _create_class(client, teacher_b, "فصل ب")
    _join(client, student, class_a["invite_code"])

    assert [c["id"] for c in client.get("/classes", headers=auth(teacher_a)).json()] == [class_a["id"]]
    assert [c["id"] for c in client.get("/classes", headers=auth(teacher_b)).json()] == [class_b["id"]]
    assert [c["id"] for c in client.get("/classes", headers=auth(student)).json()] == [class_a["id"]]
    assert client.get("/classes", headers=auth(other_student)).json() == []
    assert {c["id"] for c in client.get("/classes", headers=auth(admin)).json()} == {class_a["id"], class_b["id"]}


def test_class_detail_shows_roster_with_average_mastery(client, db_session):
    teacher = make_teacher(client, db_session)
    student = make_student(client, "rostered@example.com")
    created = _create_class(client, teacher)
    _join(client, student, created["invite_code"])
    take_quiz(client, db_session, student, topic_id_by_slug(client, "linear-equations"), mode="practice", correct=True)

    detail = client.get(f"/classes/{created['id']}", headers=auth(teacher))
    assert detail.status_code == 200
    body = detail.json()
    assert body["student_count"] == 1
    assert body["students"][0]["email"] == "rostered@example.com"
    assert body["students"][0]["average_mastery"] == 100.0


def test_class_detail_is_restricted_to_owner_and_admin(client, db_session):
    teacher = make_teacher(client, db_session, "owner@example.com")
    other_teacher = make_teacher(client, db_session, "intruder-teacher@example.com")
    student = make_student(client, "member@example.com")
    admin = register_and_login(client, "first-admin@example.com")
    created = _create_class(client, teacher)
    _join(client, student, created["invite_code"])

    url = f"/classes/{created['id']}"
    assert client.get(url, headers=auth(student)).status_code == 403  # الطالب ما يشوف القائمة ولا إيميلات زملائه
    assert client.get(url, headers=auth(other_teacher)).status_code == 403
    assert client.get(url, headers=auth(teacher)).status_code == 200
    assert client.get(url, headers=auth(admin)).status_code == 200
    assert client.get("/classes/999999", headers=auth(teacher)).status_code == 404


# ---------- إدارة الفصل ----------

def test_teacher_can_rename_class(client, db_session):
    teacher = make_teacher(client, db_session)
    created = _create_class(client, teacher)
    renamed = client.patch(f"/classes/{created['id']}", json={"name": "اسم جديد"}, headers=auth(teacher))
    assert renamed.status_code == 200
    assert renamed.json()["name"] == "اسم جديد"


def test_regenerating_code_invalidates_the_old_one(client, db_session):
    teacher = make_teacher(client, db_session)
    student = make_student(client, "latecomer@example.com")
    created = _create_class(client, teacher)

    regenerated = client.post(f"/classes/{created['id']}/regenerate-code", headers=auth(teacher))
    assert regenerated.status_code == 200
    new_code = regenerated.json()["invite_code"]
    assert new_code != created["invite_code"]

    assert _join(client, student, created["invite_code"]).status_code == 404
    assert _join(client, student, new_code).status_code == 200


def test_only_owner_can_modify_class(client, db_session):
    teacher = make_teacher(client, db_session, "realowner@example.com")
    other_teacher = make_teacher(client, db_session, "fakeowner@example.com")
    student = make_student(client, "sneaky-class@example.com")
    created = _create_class(client, teacher)
    url = f"/classes/{created['id']}"

    assert client.patch(url, json={"name": "س"}, headers=auth(other_teacher)).status_code == 403
    assert client.post(f"{url}/regenerate-code", headers=auth(other_teacher)).status_code == 403
    assert client.delete(url, headers=auth(other_teacher)).status_code == 403
    assert client.patch(url, json={"name": "س"}, headers=auth(student)).status_code == 403


def test_teacher_removes_a_student(client, db_session):
    teacher = make_teacher(client, db_session)
    student = make_student(client, "removed@example.com")
    created = _create_class(client, teacher)
    _join(client, student, created["invite_code"])
    student_id = client.get(f"/classes/{created['id']}", headers=auth(teacher)).json()["students"][0]["user_id"]

    assert client.delete(f"/classes/{created['id']}/students/{student_id}", headers=auth(teacher)).status_code == 204
    assert client.get("/classes", headers=auth(student)).json() == []
    assert client.delete(f"/classes/{created['id']}/students/{student_id}", headers=auth(teacher)).status_code == 404


def test_deleting_class_removes_it_and_its_code(client, db_session):
    teacher = make_teacher(client, db_session)
    student = make_student(client, "afterdelete@example.com")
    created = _create_class(client, teacher)
    assert client.delete(f"/classes/{created['id']}", headers=auth(teacher)).status_code == 204
    assert client.get("/classes", headers=auth(teacher)).json() == []
    assert _join(client, student, created["invite_code"]).status_code == 404


# ---------- واجبات محصورة بفصل ----------

def test_class_assignment_is_visible_only_to_class_members(client, db_session):
    teacher = make_teacher(client, db_session)
    member = make_student(client, "member-a@example.com")
    outsider = make_student(client, "outsider-a@example.com")
    created = _create_class(client, teacher)
    _join(client, member, created["invite_code"])

    scoped = _create_assignment(client, teacher, title="واجب الفصل", class_section_id=created["id"])
    global_one = _create_assignment(client, teacher, title="واجب عام")
    assert scoped["class_section_id"] == created["id"]
    assert global_one["class_section_id"] is None

    member_ids = {a["id"] for a in client.get("/assignments", headers=auth(member)).json()}
    outsider_ids = {a["id"] for a in client.get("/assignments", headers=auth(outsider)).json()}
    assert member_ids == {scoped["id"], global_one["id"]}
    assert outsider_ids == {global_one["id"]}  # العام يبقى مرئيًا للكل


def test_outsider_cannot_read_or_submit_class_assignment(client, db_session):
    teacher = make_teacher(client, db_session)
    member = make_student(client, "member-b@example.com")
    outsider = make_student(client, "outsider-b@example.com")
    created = _create_class(client, teacher)
    _join(client, member, created["invite_code"])
    scoped = _create_assignment(client, teacher, class_section_id=created["id"])
    url = f"/assignments/{scoped['id']}"

    assert client.get(url, headers=auth(outsider)).status_code == 404
    assert client.get(f"{url}/my-submission", headers=auth(outsider)).status_code == 404
    blocked = client.post(f"{url}/submit", json={"written_answer": "إجابة"}, headers=auth(outsider))
    assert blocked.status_code == 403

    assert client.get(url, headers=auth(member)).status_code == 200
    allowed = client.post(f"{url}/submit", json={"written_answer": "إجابتي"}, headers=auth(member))
    assert allowed.status_code == 200


def test_teacher_cannot_assign_to_someone_elses_class(client, db_session):
    teacher = make_teacher(client, db_session, "class-owner@example.com")
    other_teacher = make_teacher(client, db_session, "class-thief@example.com")
    created = _create_class(client, teacher)

    stolen = client.post(
        "/assignments",
        json={"title": "و", "description": "وصف", "class_section_id": created["id"]},
        headers=auth(other_teacher),
    )
    assert stolen.status_code == 403
    missing = client.post(
        "/assignments",
        json={"title": "و", "description": "وصف", "class_section_id": 999999},
        headers=auth(other_teacher),
    )
    assert missing.status_code == 404


def test_other_teachers_do_not_see_class_assignments_they_do_not_own(client, db_session):
    teacher = make_teacher(client, db_session, "author@example.com")
    other_teacher = make_teacher(client, db_session, "bystander@example.com")
    created = _create_class(client, teacher)
    scoped = _create_assignment(client, teacher, class_section_id=created["id"])

    assert scoped["id"] not in {a["id"] for a in client.get("/assignments", headers=auth(other_teacher)).json()}
    assert scoped["id"] in {a["id"] for a in client.get("/assignments", headers=auth(teacher)).json()}


def test_removed_student_loses_access_to_class_assignment(client, db_session):
    teacher = make_teacher(client, db_session)
    student = make_student(client, "expelled@example.com")
    created = _create_class(client, teacher)
    _join(client, student, created["invite_code"])
    scoped = _create_assignment(client, teacher, class_section_id=created["id"])
    student_id = client.get(f"/classes/{created['id']}", headers=auth(teacher)).json()["students"][0]["user_id"]

    assert client.get(f"/assignments/{scoped['id']}", headers=auth(student)).status_code == 200
    client.delete(f"/classes/{created['id']}/students/{student_id}", headers=auth(teacher))
    assert client.get(f"/assignments/{scoped['id']}", headers=auth(student)).status_code == 404


def test_deleting_class_removes_its_assignments(client, db_session):
    teacher = make_teacher(client, db_session)
    created = _create_class(client, teacher)
    scoped = _create_assignment(client, teacher, class_section_id=created["id"])

    client.delete(f"/classes/{created['id']}", headers=auth(teacher))
    assert client.get(f"/assignments/{scoped['id']}", headers=auth(teacher)).status_code == 404


# ---------- لوحة متصدرين الفصل ----------

def test_class_leaderboard_ranks_only_members(client, db_session):
    teacher = make_teacher(client, db_session)
    member = make_student(client, "lb-member@example.com")
    outsider = make_student(client, "lb-outsider@example.com")
    created = _create_class(client, teacher)
    _join(client, member, created["invite_code"])
    linear_id = topic_id_by_slug(client, "linear-equations")
    take_quiz(client, db_session, member, linear_id, mode="practice", correct=True)
    take_quiz(client, db_session, outsider, linear_id, mode="gateway", correct=True)  # نقاط أعلى لكن خارج الفصل

    global_board = client.get("/gamification/leaderboard", headers=auth(member)).json()
    assert len(global_board) == 2
    class_board = client.get(f"/gamification/leaderboard?class_id={created['id']}", headers=auth(member))
    assert class_board.status_code == 200
    assert len(class_board.json()) == 1
    assert class_board.json()[0]["is_me"] is True
    assert class_board.json()[0]["rank"] == 1


def test_class_leaderboard_access_control(client, db_session):
    teacher = make_teacher(client, db_session)
    member = make_student(client, "lb2-member@example.com")
    outsider = make_student(client, "lb2-outsider@example.com")
    admin = register_and_login(client, "first-admin@example.com")
    created = _create_class(client, teacher)
    _join(client, member, created["invite_code"])
    url = f"/gamification/leaderboard?class_id={created['id']}"

    assert client.get(url, headers=auth(outsider)).status_code == 403
    assert client.get(url, headers=auth(member)).status_code == 200
    assert client.get(url, headers=auth(teacher)).status_code == 200
    assert client.get(url, headers=auth(admin)).status_code == 200
    assert client.get("/gamification/leaderboard?class_id=999999", headers=auth(member)).status_code == 404


def test_empty_class_leaderboard_is_empty(client, db_session):
    teacher = make_teacher(client, db_session)
    created = _create_class(client, teacher)
    response = client.get(f"/gamification/leaderboard?class_id={created['id']}", headers=auth(teacher))
    assert response.status_code == 200
    assert response.json() == []
