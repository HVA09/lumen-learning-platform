"""Real-browser smoke test for the public registration and browser-session flow."""

from __future__ import annotations

import os
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
            expect(page.get_by_text("المعادلات الخطية", exact=True)).to_be_visible(
                timeout=30_000
            )

            cookies = {cookie["name"]: cookie for cookie in context.cookies(f"{API_URL}/auth/refresh")}
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

            # Reload proves the authenticated session is restored from cookies,
            # not from transient React state or browser localStorage.
            page.reload(wait_until="domcontentloaded")
            expect(page.get_by_text("إتقانك الإجمالي", exact=True)).to_be_visible(
                timeout=45_000
            )
            expect(page.get_by_text("المعادلات الخطية", exact=True)).to_be_visible(
                timeout=30_000
            )

            page.get_by_role("button", name="خروج", exact=True).click()
            expect(page.get_by_placeholder("البريد الإلكتروني")).to_be_visible(
                timeout=30_000
            )

            remaining_cookies = {
                cookie["name"] for cookie in context.cookies(f"{API_URL}/auth/refresh")
            }
            assert "lumen_access" not in remaining_cookies
            assert "lumen_refresh" not in remaining_cookies
            assert not page_errors, f"Unexpected browser errors: {page_errors}"

            print(
                "Browser E2E passed: registration, HttpOnly session cookies, "
                "learning dashboard, reload/session restoration, and logout."
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
