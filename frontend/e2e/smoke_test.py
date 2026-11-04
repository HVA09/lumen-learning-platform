"""Real-browser smoke test for registration, sessions, and lesson progress."""

from __future__ import annotations

import os
import re
import sys
import uuid
from pathlib import Path

from playwright.sync_api import Error, expect, sync_playwright


BASE_URL = os.environ.get("LUMEN_E2E_BASE_URL", "http://127.0.0.1:4173").rstrip("/")
API_URL = os.environ.get("LUMEN_E2E_API_URL", "http://127.0.0.1:8000").rstrip("/")
SCREENSHOT = Path(os.environ.get("RUNNER_TEMP", "/tmp")) / "lumen-browser-e2e-failure.png"


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
                    name=re.compile(re.escape(topic_name)),
                ).click()

            lesson_list_response = lesson_list_info.value
            assert lesson_list_response.status == 200, (
                f"Lesson list returned HTTP {lesson_list_response.status}"
            )
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

            page.get_by_role(
                "button",
                name="← رجوع للدروس",
                exact=True,
            ).click()
            page.get_by_role("button", name="✕", exact=True).click()

            # The learning path must reflect one completed lesson out of two.
            expect(page.get_by_text("1/2 دروس", exact=True)).to_be_visible(
                timeout=30_000
            )

            # Reload the app, restore the HttpOnly session, and re-fetch lesson state.
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
                    name=re.compile(re.escape(topic_name)),
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
            page.get_by_role("button", name="✕", exact=True).click()

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
            logout_response.finished()
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
                "Browser E2E passed: registration, HttpOnly session, lesson "
                "completion, persisted progress after reload, and logout."
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
