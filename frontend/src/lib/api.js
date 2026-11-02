import axios from "axios";

const baseURL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

const api = axios.create({
  baseURL,
  headers: {
    "Content-Type": "application/json",
  },
  timeout: 30000,
  withCredentials: true,
});

let csrfToken = null;
let csrfBootstrapPromise = null;
let authSessionActive = false;
let sessionRefreshPromise = null;

export function setCsrfToken(token) {
  csrfToken = token || null;
}

export function setAuthSessionActive(active) {
  authSessionActive = Boolean(active);
}

async function ensureCsrfToken() {
  if (csrfToken) return csrfToken;
  if (!csrfBootstrapPromise) {
    csrfBootstrapPromise = axios
      .get(`${baseURL}/auth/csrf`, {
        timeout: 30000,
        withCredentials: true,
      })
      .then(({ data }) => {
        setCsrfToken(data.csrf_token);
        return csrfToken;
      })
      .catch((error) => {
        csrfBootstrapPromise = null;
        throw error;
      });
  }
  return csrfBootstrapPromise;
}

api.interceptors.request.use(async (config) => {
  config.withCredentials = true;
  const method = (config.method || "get").toLowerCase();
  if (!["get", "head", "options"].includes(method)) {
    const token = await ensureCsrfToken();
    config.headers = config.headers || {};
    config.headers["X-CSRF-Token"] = token;
  }
  return config;
});

async function refreshBrowserSession() {
  if (!sessionRefreshPromise) {
    sessionRefreshPromise = (async () => {
      const token = await ensureCsrfToken();
      const { data } = await axios.post(
        `${baseURL}/auth/refresh`,
        {},
        {
          timeout: 30000,
          withCredentials: true,
          headers: { "X-CSRF-Token": token },
        }
      );
      setCsrfToken(data.csrf_token);
    })().finally(() => {
      sessionRefreshPromise = null;
    });
  }
  return sessionRefreshPromise;
}

api.interceptors.response.use(
  (response) => {
    if (response.data?.csrf_token) {
      setCsrfToken(response.data.csrf_token);
    }
    return response;
  },
  async (error) => {
    const requestUrl = error.config?.url || "";
    const isPublicAuthRequest =
      requestUrl.includes("/auth/login") ||
      requestUrl.includes("/auth/csrf") ||
      requestUrl.includes("/auth/refresh") ||
      requestUrl.includes("/auth/logout") ||
      requestUrl.includes("/auth/password-reset/");

    if (
      error.response?.status === 401 &&
      authSessionActive &&
      !isPublicAuthRequest &&
      error.config &&
      !error.config.__sessionRetry
    ) {
      error.config.__sessionRetry = true;
      try {
        await refreshBrowserSession();
        return api(error.config);
      } catch {
        authSessionActive = false;
        window.dispatchEvent(new Event("auth:unauthorized"));
      }
    }
    return Promise.reject(error);
  }
);

export default api;
