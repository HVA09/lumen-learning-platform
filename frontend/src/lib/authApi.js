import api, { setAuthSessionActive, setCsrfToken } from "./api";

export async function registerUser(email, password) {
  const { data } = await api.post("/auth/register", { email, password });
  return data;
}

export async function loginUser(email, password, totpCode = null) {
  const { data } = await api.post("/auth/login", {
    email,
    password,
    totp_code: totpCode,
  });
  if (data.authenticated) {
    setCsrfToken(data.csrf_token);
    setAuthSessionActive(true);
  }
  return data;
}

export async function logoutUser() {
  const { data } = await api.post("/auth/logout");
  setCsrfToken(data.csrf_token);
  setAuthSessionActive(false);
  return data;
}

export async function refreshSession() {
  const { data } = await api.post("/auth/refresh");
  setCsrfToken(data.csrf_token);
  setAuthSessionActive(true);
  return data;
}

export async function exchangeLtiCode(code) {
  const { data } = await api.post("/lti/exchange-code", { code });
  if (data.authenticated) {
    setCsrfToken(data.csrf_token);
    setAuthSessionActive(true);
  }
  return data;
}

export async function requestPasswordReset(email) {
  const { data } = await api.post("/auth/password-reset/request", { email });
  return data;
}

export async function confirmPasswordReset(token, newPassword) {
  const { data } = await api.post("/auth/password-reset/confirm", {
    token,
    new_password: newPassword,
  });
  return data;
}

export async function confirmEmailVerification(token) {
  const { data } = await api.post("/auth/verify-email/confirm", { token });
  return data;
}

export async function requestEmailVerification() {
  const { data } = await api.post("/auth/verify-email/request");
  return data;
}

export async function setupTwoFactor() {
  const { data } = await api.post("/auth/2fa/setup");
  return data;
}

export async function enableTwoFactor(totpCode) {
  const { data } = await api.post("/auth/2fa/enable", { totp_code: totpCode });
  return data;
}

export async function disableTwoFactor(totpCode) {
  const { data } = await api.post("/auth/2fa/disable", { totp_code: totpCode });
  return data;
}
