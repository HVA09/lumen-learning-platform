import { beforeEach, describe, expect, it, vi } from "vitest";

const mocks = vi.hoisted(() => ({
  api: { post: vi.fn() },
  setAuthSessionActive: vi.fn(),
  setCsrfToken: vi.fn(),
}));

vi.mock("./api", () => ({
  default: mocks.api,
  setAuthSessionActive: mocks.setAuthSessionActive,
  setCsrfToken: mocks.setCsrfToken,
}));

import {
  confirmEmailVerification,
  confirmPasswordReset,
  disableTwoFactor,
  enableTwoFactor,
  exchangeLtiCode,
  loginUser,
  logoutUser,
  refreshSession,
  registerUser,
  requestEmailVerification,
  requestPasswordReset,
  setupTwoFactor,
} from "./authApi";

const testPassword = "unit-test-password";
const replacementPassword = "replacement-value";

describe("auth API adapters", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mocks.api.post.mockResolvedValue({ data: { ok: true } });
  });

  it("registers with the supplied email and password", async () => {
    const data = { id: 7, email: "learner@example.com" };
    mocks.api.post.mockResolvedValueOnce({ data });

    await expect(registerUser("learner@example.com", testPassword)).resolves.toEqual(data);
    expect(mocks.api.post).toHaveBeenCalledWith("/auth/register", {
      email: "learner@example.com",
      password: testPassword,
    });
  });

  it("activates the browser session after an authenticated login", async () => {
    const data = { authenticated: true, csrf_token: "csrf-login" };
    mocks.api.post.mockResolvedValueOnce({ data });

    await expect(loginUser("learner@example.com", testPassword, "123456")).resolves.toEqual(data);
    expect(mocks.api.post).toHaveBeenCalledWith("/auth/login", {
      email: "learner@example.com",
      password: testPassword,
      totp_code: "123456",
    });
    expect(mocks.setCsrfToken).toHaveBeenCalledWith("csrf-login");
    expect(mocks.setAuthSessionActive).toHaveBeenCalledWith(true);
  });

  it("does not activate a session when login is not authenticated", async () => {
    mocks.api.post.mockResolvedValueOnce({
      data: { authenticated: false, requires_2fa: true },
    });

    await loginUser("learner@example.com", testPassword);
    expect(mocks.api.post).toHaveBeenCalledWith("/auth/login", {
      email: "learner@example.com",
      password: testPassword,
      totp_code: null,
    });
    expect(mocks.setCsrfToken).not.toHaveBeenCalled();
    expect(mocks.setAuthSessionActive).not.toHaveBeenCalled();
  });

  it("clears the browser session after logout", async () => {
    const data = { csrf_token: "csrf-logout" };
    mocks.api.post.mockResolvedValueOnce({ data });

    await expect(logoutUser()).resolves.toEqual(data);
    expect(mocks.api.post).toHaveBeenCalledWith("/auth/logout");
    expect(mocks.setCsrfToken).toHaveBeenCalledWith("csrf-logout");
    expect(mocks.setAuthSessionActive).toHaveBeenCalledWith(false);
  });

  it("activates the browser session after a successful refresh", async () => {
    const data = { csrf_token: "csrf-refresh" };
    mocks.api.post.mockResolvedValueOnce({ data });

    await expect(refreshSession()).resolves.toEqual(data);
    expect(mocks.api.post).toHaveBeenCalledWith("/auth/refresh");
    expect(mocks.setCsrfToken).toHaveBeenCalledWith("csrf-refresh");
    expect(mocks.setAuthSessionActive).toHaveBeenCalledWith(true);
  });

  it("activates the session after an authenticated LTI code exchange", async () => {
    const data = { authenticated: true, csrf_token: "csrf-lti" };
    mocks.api.post.mockResolvedValueOnce({ data });

    await expect(exchangeLtiCode("one-time-code")).resolves.toEqual(data);
    expect(mocks.api.post).toHaveBeenCalledWith("/lti/exchange-code", {
      code: "one-time-code",
    });
    expect(mocks.setCsrfToken).toHaveBeenCalledWith("csrf-lti");
    expect(mocks.setAuthSessionActive).toHaveBeenCalledWith(true);
  });

  it("maps password-reset, email-verification, and two-factor requests", async () => {
    await requestPasswordReset("learner@example.com");
    await confirmPasswordReset("reset-token", replacementPassword);
    await confirmEmailVerification("verification-token");
    await requestEmailVerification();
    await setupTwoFactor();
    await enableTwoFactor("123456");
    await disableTwoFactor("654321");

    expect(mocks.api.post.mock.calls).toEqual([
      ["/auth/password-reset/request", { email: "learner@example.com" }],
      ["/auth/password-reset/confirm", {
        token: "reset-token",
        new_password: replacementPassword,
      }],
      ["/auth/verify-email/confirm", { token: "verification-token" }],
      ["/auth/verify-email/request"],
      ["/auth/2fa/setup"],
      ["/auth/2fa/enable", { totp_code: "123456" }],
      ["/auth/2fa/disable", { totp_code: "654321" }],
    ]);
  });

  it("propagates request errors to the caller", async () => {
    const error = new Error("network unavailable");
    mocks.api.post.mockRejectedValueOnce(error);

    await expect(registerUser("learner@example.com", testPassword)).rejects.toBe(error);
  });
});
