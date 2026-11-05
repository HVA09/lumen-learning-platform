"""Real-browser smoke test for registration, sessions, and lesson progress."""

from __future__ import annotations

import math
import os
import re
import sys
import uuid
from pathlib import Path

from playwright.sync_api import Error, expect, sync_playwright


BASE_URL = os.environ.get("LUMEN_E2E_BASE_URL", "http://127.0.0.1:4173").rstrip("/")
API_URL = os.environ.get("LUMEN_E2E_API_URL", "http://127.0.0.1:8000").rstrip("/")
SCREENSHOT = Path(os.environ.get("RUNNER_TEMP", "/tmp")) / "lumen-browser-e2e-failure.png"


def _select_quiz_radio(card, index: int) -> None:
    """Select a quiz option through the browser's native input event."""
    radio = card.locator("input[type='radio']").nth(index)
    radio.evaluate(
        "(element) => { element.scrollIntoView({block: 'center', inline: 'nearest'}); element.click(); }"
    )
    assert radio.is_checked(), "The selected quiz option did not become checked"




def _register_browser_user(browser, email: str, password: str):
    """Register an isolated browser user through the real sign-up form."""
    context = browser.new_context(
        viewport={"width": 390, "height": 844},
        locale="ar",
    )
    page = context.new_page()
    try:
        response = page.goto(BASE_URL, wait_until="domcontentloaded")
        assert response is not None and response.ok, (
            f"Frontend did not load successfully: {response.status if response else 'no response'}"
        )
        expect(page.get_by_placeholder("البريد الإلكتروني")).to_be_visible(timeout=30_000)
        page.get_by_role("button", name="ليس لديك حساب؟ أنشئ واحدًا").click()
        page.get_by_placeholder("البريد الإلكتروني").fill(email)
        page.get_by_placeholder("كلمة المرور (8 أحرف على الأقل)").fill(password)
        page.get_by_role("button", name="إنشاء حساب").click()
        expect(page.get_by_text("إتقانك الإجمالي", exact=True)).to_be_visible(
            timeout=45_000
        )
        return context, page
    except Exception:
        context.close()
        raise


def _promote_e2e_user(email: str, role: str) -> None:
    """Assign a role only inside the disposable local lumen_e2e CI database."""
    from sqlalchemy.engine import make_url

    database_url = os.environ.get("DATABASE_URL", "")
    parsed_url = make_url(database_url) if database_url else None
    if (
        parsed_url is None
        or parsed_url.database != "lumen_e2e"
        or parsed_url.host not in {"localhost", "127.0.0.1"}
    ):
        raise RuntimeError(
            "Role fixtures may only modify the local PostgreSQL database named lumen_e2e"
        )

    backend_path = Path(__file__).resolve().parents[2] / "backend"
    if not backend_path.is_dir():
        raise RuntimeError(f"Backend package not found at {backend_path}")
    backend_path_text = str(backend_path)
    if backend_path_text not in sys.path:
        sys.path.insert(0, backend_path_text)

    from app.config import settings
    from app.database import SessionLocal, normalize_database_url
    from app.models.user import User, UserRole

    if normalize_database_url(settings.DATABASE_URL) != normalize_database_url(database_url):
        raise RuntimeError("The application database URL does not match the guarded E2E database")

    try:
        target_role = UserRole(role)
    except ValueError as exc:
        raise ValueError(f"Unsupported E2E role: {role}") from exc

    with SessionLocal() as session:
        user = session.query(User).filter(User.email == email).one_or_none()
        if user is None:
            raise AssertionError(f"Registered E2E user {email!r} was not found in the test database")
        user.role = target_role
        session.commit()


def _browser_access_token(context) -> str:
    cookie = next(
        (item for item in context.cookies() if item["name"] == "lumen_access"),
        None,
    )
    assert cookie is not None, "Expected the browser session access cookie"
    assert cookie["httpOnly"] is True, "The access cookie must remain HttpOnly"
    return cookie["value"]


def run_smoke_test() -> None:
    email = f"browser-e2e-{uuid.uuid4().hex[:12]}@example.com"
    password = "BrowserE2E-Pass-2026"
    topic_name = "المعادلات الخطية"

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 390, "height": 844},
            locale="ar",
        )
        page = context.new_page()
        page_errors: list[str] = []
        page.on("pageerror", lambda error: page_errors.append(str(error)))

        try:
            response = page.goto(BASE_URL, wait_until="domcontentloaded")
            assert response is not None and response.ok, (
                f"Frontend did not load successfully: {response.status if response else 'no response'}"
            )

            email_input = page.get_by_placeholder("البريد الإلكتروني")
            expect(email_input).to_be_visible(timeout=30_000)

            page.get_by_role("button", name="ليس لديك حساب؟ أنشئ واحدًا").click()
            email_input.fill(email)
            page.get_by_placeholder("كلمة المرور (8 أحرف على الأقل)").fill(password)
            page.get_by_role("button", name="إنشاء حساب").click()

            # Registration must create a real API account, establish a cookie
            # session, and load the authenticated learning dashboard.
            expect(page.get_by_text("إتقانك الإجمالي", exact=True)).to_be_visible(
                timeout=45_000
            )
            expect(page.get_by_text("الرياضيات", exact=True)).to_be_visible(
                timeout=30_000
            )
            expect(page.get_by_text(topic_name, exact=True)).to_be_visible(
                timeout=30_000
            )

            cookies = {
                cookie["name"]: cookie
                for cookie in context.cookies(f"{API_URL}/auth/refresh")
            }
            for name in ("lumen_access", "lumen_refresh"):
                assert name in cookies, f"Expected browser session cookie {name!r}"
                assert cookies[name]["httpOnly"] is True, (
                    f"Session cookie {name!r} must be HttpOnly"
                )

            document_cookies = page.evaluate("document.cookie")
            assert "lumen_access" not in document_cookies
            assert "lumen_refresh" not in document_cookies
            assert page.evaluate("localStorage.getItem('access_token')") is None
            assert page.evaluate("localStorage.getItem('refresh_token')") is None

            # Open a real seeded topic and capture the lessons returned by the API.
            with page.expect_response(
                lambda response: response.request.method == "GET"
                and "/curriculum/topics/" in response.url
                and response.url.endswith("/lessons"),
                timeout=30_000,
            ) as lesson_list_info:
                page.get_by_role(
                    "button",
                    name=re.compile(rf"^{re.escape(topic_name)}\s"),
                ).click()

            lesson_list_response = lesson_list_info.value
            assert lesson_list_response.status == 200, (
                f"Lesson list returned HTTP {lesson_list_response.status}"
            )
            topic_match = re.search(r"/curriculum/topics/(\d+)/lessons$", lesson_list_response.url)
            assert topic_match, f"Could not determine topic id from {lesson_list_response.url}"
            topic_id = int(topic_match.group(1))
            lessons = lesson_list_response.json()
            assert lessons, "The seeded topic must contain at least one published lesson"
            first_lesson = lessons[0]
            lesson_id = first_lesson["id"]
            lesson_title = first_lesson["title_ar"]

            page.get_by_role(
                "button",
                name=re.compile(re.escape(lesson_title)),
            ).click()
            expect(
                page.get_by_role("heading", name=lesson_title, exact=True)
            ).to_be_visible(timeout=30_000)

            # Complete the lesson through the UI and require a successful API response.
            with page.expect_response(
                lambda response: response.request.method == "POST"
                and response.url.endswith(
                    f"/curriculum/lessons/{lesson_id}/complete"
                ),
                timeout=30_000,
            ) as completion_info:
                page.get_by_role(
                    "button",
                    name="أنهيت هذا الدرس",
                    exact=True,
                ).click()

            completion_response = completion_info.value
            assert completion_response.status == 200, (
                f"Lesson completion returned HTTP {completion_response.status}"
            )
            expect(
                page.get_by_text("✓ أنهيت هذا الدرس", exact=True)
            ).to_be_visible(timeout=30_000)

            # Reload directly from the lesson reader. This avoids relying on the
            # modal's internal scroll position at the narrow mobile viewport.
            # The dashboard must be rebuilt from persisted server-side progress.
            page.reload(wait_until="domcontentloaded")
            expect(page.get_by_text("إتقانك الإجمالي", exact=True)).to_be_visible(
                timeout=45_000
            )
            expect(page.get_by_text("1/2 دروس", exact=True)).to_be_visible(
                timeout=30_000
            )

            with page.expect_response(
                lambda response: response.request.method == "GET"
                and "/curriculum/topics/" in response.url
                and response.url.endswith("/lessons"),
                timeout=30_000,
            ) as refreshed_lessons_info:
                page.get_by_role(
                    "button",
                    name=re.compile(rf"^{re.escape(topic_name)}\s"),
                ).click()

            refreshed_lessons_response = refreshed_lessons_info.value
            assert refreshed_lessons_response.status == 200, (
                f"Reloaded lesson list returned HTTP {refreshed_lessons_response.status}"
            )
            refreshed_lessons = refreshed_lessons_response.json()
            persisted_lesson = next(
                (lesson for lesson in refreshed_lessons if lesson["id"] == lesson_id),
                None,
            )
            assert persisted_lesson is not None, "Completed lesson disappeared after reload"
            assert persisted_lesson["completed"] is True, (
                "Lesson completion was not restored from the server after reload"
            )

            page.get_by_role(
                "button",
                name=re.compile(re.escape(lesson_title)),
            ).click()
            expect(
                page.get_by_text("✓ أنهيت هذا الدرس", exact=True)
            ).to_be_visible(timeout=30_000)

            # A clean reload returns to the dashboard so the logout control is reachable.
            page.reload(wait_until="domcontentloaded")
            expect(page.get_by_text("إتقانك الإجمالي", exact=True)).to_be_visible(
                timeout=45_000
            )
            page.get_by_role(
                "button",
                name=re.compile(rf"^{re.escape(topic_name)}\s"),
            ).click()
            expect(
                page.get_by_role("heading", name=topic_name, exact=True)
            ).to_be_visible(timeout=30_000)

            # Exercise a real learner quiz through the browser. The initial attempt
            # must not expose answer keys; the server alone grades the submission.
            with page.expect_response(
                lambda response: response.request.method == "POST"
                and response.url.endswith(f"/quiz/topics/{topic_id}/start"),
                timeout=30_000,
            ) as quiz_start_info:
                page.get_by_role(
                    "button",
                    name=re.compile(r"اختبار تدريبي"),
                ).click()

            quiz_start_response = quiz_start_info.value
            assert quiz_start_response.status == 200, (
                f"Quiz start returned HTTP {quiz_start_response.status}"
            )
            quiz_attempt = quiz_start_response.json()
            quiz_questions = quiz_attempt.get("questions", [])
            assert quiz_attempt["topic_id"] == topic_id
            assert quiz_attempt["mode"] == "practice"
            assert quiz_questions, "The seeded topic must contain quiz questions"
            assert all(
                "correct_answer" not in question and "answer_key" not in question
                for question in quiz_questions
            ), "Quiz start must not expose correct answers to the learner"

            expect(
                page.get_by_role("heading", name="اختبار تدريبي", exact=True)
            ).to_be_visible(timeout=30_000)
            submit_label = f"سلّم الإجابات (0/{len(quiz_questions)})"
            with page.expect_response(
                lambda response: response.request.method == "POST"
                and response.url.endswith(
                    f"/quiz/attempts/{quiz_attempt['attempt_id']}/submit"
                ),
                timeout=30_000,
            ) as quiz_submit_info:
                page.get_by_role("button", name=submit_label, exact=True).click()

            quiz_submit_response = quiz_submit_info.value
            assert quiz_submit_response.status == 200, (
                f"Quiz submission returned HTTP {quiz_submit_response.status}"
            )
            quiz_result = quiz_submit_response.json()
            assert quiz_result["attempt_id"] == quiz_attempt["attempt_id"]
            assert quiz_result["mode"] == "practice"
            assert quiz_result["total"] == len(quiz_questions)
            assert quiz_result["correct_count"] == 0
            assert quiz_result["score_percentage"] == 0.0
            assert quiz_result["passed"] is None
            assert all(
                item["correct"] is False and item["correct_answer_text"]
                for item in quiz_result["results"]
            ), "The graded result must contain per-question feedback"

            expect(
                page.get_by_text(
                    f"0 من {len(quiz_questions)} صحيحة",
                    exact=True,
                )
            ).to_be_visible(timeout=30_000)
            page.get_by_role("button", name="إغلاق", exact=True).click()
            page.get_by_role("button", name="✕", exact=True).click()

            # Reload the app and fetch history again to prove the submitted attempt
            # was committed to the server, not just held in the component state.
            page.reload(wait_until="domcontentloaded")
            expect(page.get_by_text("إتقانك الإجمالي", exact=True)).to_be_visible(
                timeout=45_000
            )
            with page.expect_response(
                lambda response: response.request.method == "GET"
                and response.url.endswith(f"/quiz/topics/{topic_id}/history"),
                timeout=30_000,
            ) as quiz_history_info:
                page.get_by_role(
                    "button",
                    name=re.compile(rf"^{re.escape(topic_name)}\s"),
                ).click()

            quiz_history_response = quiz_history_info.value
            assert quiz_history_response.status == 200, (
                f"Quiz history returned HTTP {quiz_history_response.status}"
            )
            quiz_history = quiz_history_response.json()
            assert quiz_history, "The submitted quiz must appear in the attempt history"
            assert quiz_history[0]["id"] == quiz_attempt["attempt_id"]
            assert quiz_history[0]["mode"] == "practice"
            assert quiz_history[0]["score_percentage"] == 0.0
            assert quiz_history[0]["submitted_at"] is not None
            expect(page.get_by_text("آخر المحاولات", exact=True)).to_be_visible(
                timeout=30_000
            )
            page.get_by_role("button", name="✕", exact=True).click()

            # Students must not see teacher/admin controls, and direct API access
            # to teacher content or administration endpoints must remain forbidden.
            expect(page.get_by_role("button", name="الإدارة", exact=True)).to_have_count(0)
            expect(page.get_by_role("button", name="إدارة المحتوى", exact=True)).to_have_count(0)
            student_headers = {
                "Authorization": f"Bearer {_browser_access_token(context)}"
            }
            student_questions = page.request.get(
                f"{API_URL}/content/topics/{topic_id}/questions",
                headers=student_headers,
            )
            assert student_questions.status == 403, (
                f"Student content access returned HTTP {student_questions.status}"
            )
            student_admin = page.request.get(
                f"{API_URL}/admin/stats",
                headers=student_headers,
            )
            assert student_admin.status == 403, (
                f"Student admin access returned HTTP {student_admin.status}"
            )

            role_contexts = []
            try:
                teacher_a_email = f"browser-e2e-teacher-a-{uuid.uuid4().hex[:10]}@example.com"
                teacher_a_context, teacher_a_page = _register_browser_user(
                    browser, teacher_a_email, password
                )
                role_contexts.append(teacher_a_context)
                _promote_e2e_user(teacher_a_email, "teacher")
                teacher_a_page.reload(wait_until="domcontentloaded")
                expect(
                    teacher_a_page.get_by_text("إتقانك الإجمالي", exact=True)
                ).to_be_visible(timeout=45_000)
                expect(
                    teacher_a_page.get_by_role(
                        "button", name="إدارة المحتوى", exact=True
                    )
                ).to_be_visible()
                expect(
                    teacher_a_page.get_by_role(
                        "button", name="الإدارة", exact=True
                    )
                ).to_have_count(0)

                # The teacher content manager must be reachable from the real UI.
                teacher_a_page.get_by_role(
                    "button", name="إدارة المحتوى", exact=True
                ).click()
                expect(
                    teacher_a_page.get_by_role(
                        "heading", name="إدارة المحتوى", exact=True
                    )
                ).to_be_visible(timeout=30_000)
                expect(
                    teacher_a_page.get_by_role("button", name="الدروس", exact=True)
                ).to_be_visible()

                # Read answer keys only through the teacher-only content endpoint.
                # The learner browser still receives public quiz questions without keys.
                teacher_headers = {
                    "Authorization": f"Bearer {_browser_access_token(teacher_a_context)}"
                }
                teacher_a_page.locator("select").select_option(str(topic_id))
                teacher_question_response = teacher_a_page.request.get(
                    f"{API_URL}/content/topics/{topic_id}/questions",
                    headers=teacher_headers,
                )
                assert teacher_question_response.status == 200, (
                    f"Teacher question bank returned HTTP {teacher_question_response.status}"
                )
                teacher_questions_by_id = {
                    item["id"]: item for item in teacher_question_response.json()
                }

                # Exercise a real gateway quiz at the minimum passing score. Ten
                # questions and the threshold come from the server, not the browser.
                page.get_by_role(
                    "button",
                    name=re.compile(rf"^{re.escape(topic_name)}\s"),
                ).click()
                expect(
                    page.get_by_role("heading", name=topic_name, exact=True)
                ).to_be_visible(timeout=30_000)
                with page.expect_response(
                    lambda response: response.request.method == "POST"
                    and response.url.endswith(f"/quiz/topics/{topic_id}/start"),
                    timeout=30_000,
                ) as gateway_start_info:
                    page.get_by_role(
                        "button", name=re.compile(r"اختبار البوابة")
                    ).click()

                gateway_start_response = gateway_start_info.value
                assert gateway_start_response.status == 200, (
                    f"Gateway quiz start returned HTTP {gateway_start_response.status}"
                )
                gateway_attempt = gateway_start_response.json()
                gateway_questions = gateway_attempt.get("questions", [])
                assert gateway_attempt["mode"] == "gateway"
                assert len(gateway_questions) == 10
                assert gateway_attempt["pass_percentage"] is not None
                assert all(
                    "correct_answer" not in question and "answer_key" not in question
                    for question in gateway_questions
                ), "Gateway quiz must not expose correct answers to the learner"

                pass_percentage = float(gateway_attempt["pass_percentage"])
                target_correct_count = math.ceil(
                    pass_percentage * len(gateway_questions) / 100.0
                )
                expected_score = round(
                    100.0 * target_correct_count / len(gateway_questions), 1
                )
                assert expected_score >= pass_percentage
                assert (
                    expected_score - 100.0 / len(gateway_questions) < pass_percentage
                ), "The selected result must be the minimum passing score"

                quiz_heading = page.get_by_role(
                    "heading", name="اختبار البوابة", exact=True
                )
                expect(quiz_heading).to_be_visible(timeout=30_000)
                quiz_modal = quiz_heading.locator("xpath=../..")
                question_cards = quiz_modal.locator(
                    "div.rounded-2xl.border.border-slate-200.p-3"
                )
                expect(question_cards).to_have_count(len(gateway_questions), timeout=30_000)

                for index, question in enumerate(gateway_questions):
                    teacher_question = teacher_questions_by_id.get(question["id"])
                    assert teacher_question is not None, (
                        f"Teacher answer key is missing question {question['id']}"
                    )
                    answer_should_be_correct = index < target_correct_count
                    answer_key = teacher_question["correct_answer"]
                    card = question_cards.nth(index)
                    card.scroll_into_view_if_needed()

                    if question["kind"] == "mcq":
                        correct_index = int(answer_key)
                        choices = question["choices"]
                        assert choices and 0 <= correct_index < len(choices)
                        selected_index = correct_index
                        if not answer_should_be_correct:
                            selected_index = (correct_index + 1) % len(choices)
                        _select_quiz_radio(card, selected_index)
                    elif question["kind"] == "true_false":
                        selected_answer = bool(answer_key)
                        if not answer_should_be_correct:
                            selected_answer = not selected_answer
                        selected_index = 0 if selected_answer else 1
                        _select_quiz_radio(card, selected_index)
                    elif question["kind"] == "numeric":
                        numeric_answer = float(answer_key)
                        if not answer_should_be_correct:
                            numeric_answer += float(teacher_question.get("tolerance") or 0) + 1.0
                        card.get_by_placeholder("اكتب رقمًا...").fill(str(numeric_answer))
                    elif question["kind"] == "short_text":
                        accepted = answer_key if isinstance(answer_key, list) else [answer_key]
                        assert accepted
                        text_answer = str(accepted[0])
                        if not answer_should_be_correct:
                            text_answer = "إجابة اختبار غير صحيحة"
                        card.get_by_placeholder("اكتب إجابتك...").fill(text_answer)
                    else:
                        raise AssertionError(
                            f"Unsupported seeded question kind: {question['kind']}"
                        )

                submit_label = (
                    f"سلّم الإجابات ({len(gateway_questions)}/{len(gateway_questions)})"
                )
                with page.expect_response(
                    lambda response: response.request.method == "POST"
                    and response.url.endswith(
                        f"/quiz/attempts/{gateway_attempt['attempt_id']}/submit"
                    ),
                    timeout=30_000,
                ) as gateway_submit_info:
                    quiz_modal.get_by_role(
                        "button", name=submit_label, exact=True
                    ).click()

                gateway_submit_response = gateway_submit_info.value
                assert gateway_submit_response.status == 200, (
                    f"Gateway quiz submission returned HTTP {gateway_submit_response.status}"
                )
                gateway_result = gateway_submit_response.json()
                assert gateway_result["attempt_id"] == gateway_attempt["attempt_id"]
                assert gateway_result["mode"] == "gateway"
                assert gateway_result["total"] == len(gateway_questions) == 10
                assert gateway_result["correct_count"] == target_correct_count
                assert gateway_result["score_percentage"] == expected_score
                assert gateway_result["score_percentage"] >= pass_percentage
                assert gateway_result["passed"] is True
                assert gateway_result["gateway_quiz_passed"] is True
                expect(
                    quiz_modal.get_by_text("🎉 اجتزت اختبار البوابة!", exact=True)
                ).to_be_visible(timeout=30_000)
                page.get_by_role("button", name="إغلاق", exact=True).click()
                page.get_by_role("button", name="✕", exact=True).click()

                # Select the seeded lesson topic and create an unpublished draft
                # through the teacher content manager.
                teacher_a_page.locator("select").select_option(str(topic_id))
                draft_title = f"Browser E2E draft {uuid.uuid4().hex[:8]}"
                draft_body = "نص تجريبي لمسودة غير منشورة."
                with teacher_a_page.expect_response(
                    lambda response: response.request.method == "POST"
                    and response.url.endswith(
                        f"/content/topics/{topic_id}/lessons"
                    ),
                    timeout=30_000,
                ) as draft_create_info:
                    teacher_a_page.get_by_role(
                        "button", name="+ درس جديد", exact=True
                    ).click()
                    teacher_a_page.get_by_placeholder("عنوان الدرس").fill(draft_title)
                    teacher_a_page.get_by_placeholder(
                        re.compile(r"^محتوى الدرس \(Markdown\)")
                    ).fill(draft_body)
                    teacher_a_page.get_by_label(
                        "منشور (يظهر للطلاب)", exact=True
                    ).uncheck()
                    teacher_a_page.get_by_role(
                        "button", name="حفظ", exact=True
                    ).click()

                draft_create_response = draft_create_info.value
                assert draft_create_response.status == 201, (
                    f"Draft lesson creation returned HTTP {draft_create_response.status}"
                )
                draft_lesson = draft_create_response.json()
                draft_lesson_id = draft_lesson["id"]
                assert draft_lesson["is_published"] is False
                assert draft_lesson["title_ar"] == draft_title
                expect(
                    teacher_a_page.get_by_text(draft_title, exact=False)
                ).to_be_visible(timeout=30_000)

                student_draft_list = page.request.get(
                    f"{API_URL}/curriculum/topics/{topic_id}/lessons",
                    headers=student_headers,
                )
                assert student_draft_list.status == 200, (
                    f"Student lesson list returned HTTP {student_draft_list.status}"
                )
                assert all(
                    item["id"] != draft_lesson_id
                    for item in student_draft_list.json()
                ), "Unpublished lesson must remain hidden from students"

                teacher_draft_card = teacher_a_page.get_by_text(
                    draft_title, exact=False
                ).locator("xpath=../..")
                with teacher_a_page.expect_response(
                    lambda response: response.request.method == "PUT"
                    and response.url.endswith(
                        f"/content/lessons/{draft_lesson_id}"
                    ),
                    timeout=30_000,
                ) as draft_publish_info:
                    teacher_draft_card.get_by_role(
                        "button", name="تعديل", exact=True
                    ).click()
                    teacher_a_page.get_by_placeholder("عنوان الدرس").fill(
                        f"{draft_title} منشور"
                    )
                    teacher_a_page.get_by_placeholder(
                        re.compile(r"^محتوى الدرس \(Markdown\)")
                    ).fill(f"{draft_body}\n\nتم نشر هذا الدرس.")
                    teacher_a_page.get_by_label(
                        "منشور (يظهر للطلاب)", exact=True
                    ).check()
                    teacher_a_page.get_by_role(
                        "button", name="حفظ", exact=True
                    ).click()

                publish_response = draft_publish_info.value
                assert publish_response.status == 200, (
                    f"Lesson publication returned HTTP {publish_response.status}"
                )
                published_lesson = publish_response.json()
                published_title = f"{draft_title} منشور"
                assert published_lesson["id"] == draft_lesson_id
                assert published_lesson["is_published"] is True
                assert published_lesson["title_ar"] == published_title
                expect(
                    teacher_a_page.get_by_text(published_title, exact=False)
                ).to_be_visible(timeout=30_000)

                student_published_list = page.request.get(
                    f"{API_URL}/curriculum/topics/{topic_id}/lessons",
                    headers=student_headers,
                )
                assert student_published_list.status == 200
                assert any(
                    item["id"] == draft_lesson_id
                    and item["title_ar"] == published_title
                    for item in student_published_list.json()
                ), "Published lesson must become visible in the student curriculum"

                # Close Content Manager before continuing with class ownership checks.
                teacher_a_page.get_by_role(
                    "button", name="✕", exact=True
                ).click()

                # Create a class through the teacher UI, not a database fixture.
                teacher_a_class_name = f"E2E Teacher A {uuid.uuid4().hex[:6]}"
                with teacher_a_page.expect_response(
                    lambda response: response.request.method == "POST"
                    and response.url.endswith("/classes"),
                    timeout=30_000,
                ) as teacher_a_class_info:
                    teacher_a_page.get_by_role(
                        "button", name="الفصول", exact=True
                    ).click()
                    teacher_a_page.get_by_placeholder(
                        "اسم الفصل الجديد (مثلاً: رياضيات — الصف العاشر)"
                    ).fill(teacher_a_class_name)
                    teacher_a_page.get_by_role(
                        "button", name="إنشاء", exact=True
                    ).click()
                teacher_a_class_response = teacher_a_class_info.value
                assert teacher_a_class_response.status == 201, (
                    f"Teacher A class creation returned HTTP {teacher_a_class_response.status}"
                )
                teacher_a_class = teacher_a_class_response.json()
                teacher_a_class_id = teacher_a_class["id"]
                assert teacher_a_class.get("invite_code"), (
                    "Teacher A should receive the invite code for their own class"
                )
                expect(
                    teacher_a_page.get_by_text(teacher_a_class_name, exact=True)
                ).to_be_visible(timeout=30_000)
                teacher_a_page.get_by_role(
                    "button", name="✕", exact=True
                ).click()

                teacher_a_headers = {
                    "Authorization": f"Bearer {_browser_access_token(teacher_a_context)}"
                }
                teacher_a_questions = teacher_a_page.request.get(
                    f"{API_URL}/content/topics/{topic_id}/questions",
                    headers=teacher_a_headers,
                )
                assert teacher_a_questions.status == 200, (
                    f"Teacher content access returned HTTP {teacher_a_questions.status}"
                )
                teacher_questions = teacher_a_questions.json()
                assert teacher_questions and "correct_answer" in teacher_questions[0], (
                    "Teacher content access should return the authorized question answer key"
                )

                teacher_b_email = f"browser-e2e-teacher-b-{uuid.uuid4().hex[:10]}@example.com"
                teacher_b_context, teacher_b_page = _register_browser_user(
                    browser, teacher_b_email, password
                )
                role_contexts.append(teacher_b_context)
                _promote_e2e_user(teacher_b_email, "teacher")
                teacher_b_page.reload(wait_until="domcontentloaded")
                expect(
                    teacher_b_page.get_by_text("إتقانك الإجمالي", exact=True)
                ).to_be_visible(timeout=45_000)
                expect(
                    teacher_b_page.get_by_role(
                        "button", name="إدارة المحتوى", exact=True
                    )
                ).to_be_visible()
                expect(
                    teacher_b_page.get_by_role(
                        "button", name="الإدارة", exact=True
                    )
                ).to_have_count(0)

                teacher_b_class_name = f"E2E Teacher B {uuid.uuid4().hex[:6]}"
                with teacher_b_page.expect_response(
                    lambda response: response.request.method == "POST"
                    and response.url.endswith("/classes"),
                    timeout=30_000,
                ) as teacher_b_class_info:
                    teacher_b_page.get_by_role(
                        "button", name="الفصول", exact=True
                    ).click()
                    teacher_b_page.get_by_placeholder(
                        "اسم الفصل الجديد (مثلاً: رياضيات — الصف العاشر)"
                    ).fill(teacher_b_class_name)
                    teacher_b_page.get_by_role(
                        "button", name="إنشاء", exact=True
                    ).click()
                teacher_b_class_response = teacher_b_class_info.value
                assert teacher_b_class_response.status == 201, (
                    f"Teacher B class creation returned HTTP {teacher_b_class_response.status}"
                )
                teacher_b_class = teacher_b_class_response.json()
                teacher_b_class_id = teacher_b_class["id"]
                expect(
                    teacher_b_page.get_by_text(teacher_b_class_name, exact=True)
                ).to_be_visible(timeout=30_000)
                teacher_b_page.get_by_role(
                    "button", name="✕", exact=True
                ).click()

                teacher_b_headers = {
                    "Authorization": f"Bearer {_browser_access_token(teacher_b_context)}"
                }
                teacher_a_classes = teacher_a_page.request.get(
                    f"{API_URL}/classes", headers=teacher_a_headers
                )
                teacher_b_classes = teacher_b_page.request.get(
                    f"{API_URL}/classes", headers=teacher_b_headers
                )
                assert teacher_a_classes.status == 200
                assert [item["id"] for item in teacher_a_classes.json()] == [
                    teacher_a_class_id
                ], "Teacher A must only see their own class"
                assert teacher_b_classes.status == 200
                assert [item["id"] for item in teacher_b_classes.json()] == [
                    teacher_b_class_id
                ], "Teacher B must only see their own class"

                teacher_b_outside_class = teacher_b_page.request.get(
                    f"{API_URL}/classes/{teacher_a_class_id}",
                    headers=teacher_b_headers,
                )
                assert teacher_b_outside_class.status == 403, (
                    "Teacher B must not read Teacher A's class roster"
                )
                teacher_a_outside_class = teacher_a_page.request.get(
                    f"{API_URL}/classes/{teacher_b_class_id}",
                    headers=teacher_a_headers,
                )
                assert teacher_a_outside_class.status == 403, (
                    "Teacher A must not read Teacher B's class roster"
                )

                student_outside_class = page.request.get(
                    f"{API_URL}/classes/{teacher_a_class_id}",
                    headers=student_headers,
                )
                assert student_outside_class.status == 403, (
                    "A student must not read a teacher's class roster"
                )

                admin_email = f"browser-e2e-admin-{uuid.uuid4().hex[:10]}@example.com"
                admin_context, admin_page = _register_browser_user(
                    browser, admin_email, password
                )
                role_contexts.append(admin_context)
                _promote_e2e_user(admin_email, "admin")
                admin_page.reload(wait_until="domcontentloaded")
                expect(
                    admin_page.get_by_text("إتقانك الإجمالي", exact=True)
                ).to_be_visible(timeout=45_000)
                expect(
                    admin_page.get_by_role("button", name="الإدارة", exact=True)
                ).to_be_visible()
                expect(
                    admin_page.get_by_role(
                        "button", name="إدارة المحتوى", exact=True
                    )
                ).to_be_visible()

                admin_page.get_by_role(
                    "button", name="الإدارة", exact=True
                ).click()
                expect(
                    admin_page.get_by_role(
                        "heading", name="لوحة الإدارة", exact=True
                    )
                ).to_be_visible(timeout=30_000)
                admin_page.get_by_role(
                    "button", name="✕", exact=True
                ).click()

                admin_headers = {
                    "Authorization": f"Bearer {_browser_access_token(admin_context)}"
                }
                admin_stats = admin_page.request.get(
                    f"{API_URL}/admin/stats", headers=admin_headers
                )
                assert admin_stats.status == 200, (
                    f"Admin stats returned HTTP {admin_stats.status}"
                )
                admin_users = admin_page.request.get(
                    f"{API_URL}/admin/users", headers=admin_headers
                )
                assert admin_users.status == 200, (
                    f"Admin user list returned HTTP {admin_users.status}"
                )
                admin_classes = admin_page.request.get(
                    f"{API_URL}/classes", headers=admin_headers
                )
                assert admin_classes.status == 200
                admin_class_ids = {item["id"] for item in admin_classes.json()}
                assert {teacher_a_class_id, teacher_b_class_id}.issubset(admin_class_ids), (
                    "Admin must see both teachers' classes"
                )
                admin_class_detail = admin_page.request.get(
                    f"{API_URL}/classes/{teacher_a_class_id}",
                    headers=admin_headers,
                )
                assert admin_class_detail.status == 200, (
                    "Admin must be allowed to inspect a teacher's class roster"
                )
                admin_questions = admin_page.request.get(
                    f"{API_URL}/content/topics/{topic_id}/questions",
                    headers=admin_headers,
                )
                assert admin_questions.status == 200, (
                    "Admin must be allowed to read managed question content"
                )

            finally:
                for role_context in role_contexts:
                    role_context.close()

            # Logout is asynchronous in the UI: wait for the server to revoke the session.
            with page.expect_response(
                lambda response: response.url.endswith("/auth/logout")
                and response.request.method == "POST",
                timeout=30_000,
            ) as logout_response_info:
                page.get_by_role("button", name="خروج", exact=True).click()

            logout_response = logout_response_info.value
            assert logout_response.status == 200, (
                f"Logout endpoint returned HTTP {logout_response.status}"
            )
            expect(page.get_by_placeholder("البريد الإلكتروني")).to_be_visible(
                timeout=30_000
            )

            remaining_cookies = {
                cookie["name"]
                for cookie in context.cookies(f"{API_URL}/auth/refresh")
            }
            assert "lumen_access" not in remaining_cookies
            assert "lumen_refresh" not in remaining_cookies
            assert not page_errors, f"Unexpected browser errors: {page_errors}"

            print(
                "Browser E2E passed: registration, HttpOnly session, lesson progress, quiz submission, "
                "persisted lesson progress, server-graded quiz result at the gateway pass threshold, persisted quiz history, and logout."
            )
        except Exception:
            try:
                page.screenshot(path=str(SCREENSHOT), full_page=True)
                print(f"Failure screenshot saved to {SCREENSHOT}", file=sys.stderr)
            except Error:
                pass
            raise
        finally:
            context.close()
            browser.close()


if __name__ == "__main__":
    run_smoke_test()
