const RELOAD_STORAGE_KEY = "lumen:vite-preload-error-reload-at";
const RELOAD_COOLDOWN_MS = 60_000;

export function recoverFromVitePreloadError(event, browserWindow) {
  if (browserWindow.navigator?.onLine === false) {
    // Leave the error unhandled so React ErrorBoundary can show an offline message.
    return false;
  }

  try {
    const now = Date.now();
    const lastReloadAt = Number(
      browserWindow.sessionStorage.getItem(RELOAD_STORAGE_KEY)
    ) || 0;

    // Prevent a bad or unavailable chunk from causing an automatic reload loop.
    if (now - lastReloadAt < RELOAD_COOLDOWN_MS) {
      return false;
    }

    browserWindow.sessionStorage.setItem(RELOAD_STORAGE_KEY, String(now));
  } catch {
    // If session storage is unavailable, let the error reach the visible boundary.
    return false;
  }

  event.preventDefault();
  browserWindow.location.reload();
  return true;
}

export function registerVitePreloadRecovery(browserWindow = window) {
  browserWindow.addEventListener("vite:preloadError", (event) => {
    recoverFromVitePreloadError(event, browserWindow);
  });
}
