import { afterEach, describe, expect, it, vi } from "vitest";
import { recoverFromVitePreloadError } from "./vitePreloadRecovery";

function createBrowserWindow({ online = true, lastReloadAt = null } = {}) {
  const values = new Map();
  if (lastReloadAt !== null) {
    values.set("lumen:vite-preload-error-reload-at", String(lastReloadAt));
  }

  return {
    navigator: { onLine: online },
    sessionStorage: {
      getItem: vi.fn((key) => values.get(key) ?? null),
      setItem: vi.fn((key, value) => values.set(key, value)),
    },
    location: { reload: vi.fn() },
  };
}

function createPreloadErrorEvent() {
  return { preventDefault: vi.fn() };
}

afterEach(() => {
  vi.restoreAllMocks();
});

describe("Vite dynamic import recovery", () => {
  it("reloads once when the browser is online", () => {
    vi.spyOn(Date, "now").mockReturnValue(120_000);
    const browserWindow = createBrowserWindow();
    const event = createPreloadErrorEvent();

    const recovered = recoverFromVitePreloadError(event, browserWindow);

    expect(recovered).toBe(true);
    expect(event.preventDefault).toHaveBeenCalledOnce();
    expect(browserWindow.location.reload).toHaveBeenCalledOnce();
    expect(browserWindow.sessionStorage.setItem).toHaveBeenCalledWith(
      "lumen:vite-preload-error-reload-at",
      "120000"
    );
  });

  it("leaves the error for ErrorBoundary while the browser is offline", () => {
    vi.spyOn(Date, "now").mockReturnValue(120_000);
    const browserWindow = createBrowserWindow({ online: false });
    const event = createPreloadErrorEvent();

    const recovered = recoverFromVitePreloadError(event, browserWindow);

    expect(recovered).toBe(false);
    expect(event.preventDefault).not.toHaveBeenCalled();
    expect(browserWindow.location.reload).not.toHaveBeenCalled();
    expect(browserWindow.sessionStorage.setItem).not.toHaveBeenCalled();
  });

  it("does not repeat automatic reloads during the cooldown window", () => {
    vi.spyOn(Date, "now").mockReturnValue(120_000);
    const browserWindow = createBrowserWindow({ lastReloadAt: 90_000 });
    const event = createPreloadErrorEvent();

    const recovered = recoverFromVitePreloadError(event, browserWindow);

    expect(recovered).toBe(false);
    expect(event.preventDefault).not.toHaveBeenCalled();
    expect(browserWindow.location.reload).not.toHaveBeenCalled();
  });

  it("leaves the error visible when session storage is unavailable", () => {
    vi.spyOn(Date, "now").mockReturnValue(120_000);
    const browserWindow = createBrowserWindow();
    browserWindow.sessionStorage.getItem.mockImplementation(() => {
      throw new Error("Storage disabled");
    });
    const event = createPreloadErrorEvent();

    const recovered = recoverFromVitePreloadError(event, browserWindow);

    expect(recovered).toBe(false);
    expect(event.preventDefault).not.toHaveBeenCalled();
    expect(browserWindow.location.reload).not.toHaveBeenCalled();
  });
});
