import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import ErrorBoundary from "./ErrorBoundary";

function BrokenChild({ error }) {
  throw error;
}

const originalOnlineDescriptor = Object.getOwnPropertyDescriptor(
  window.navigator,
  "onLine"
);

afterEach(() => {
  cleanup();
  if (originalOnlineDescriptor) {
    Object.defineProperty(window.navigator, "onLine", originalOnlineDescriptor);
  } else {
    delete window.navigator.onLine;
  }
  vi.restoreAllMocks();
});

describe("ErrorBoundary", () => {
  it("explains a failed lazy chunk and enables retry when the connection returns", () => {
    Object.defineProperty(window.navigator, "onLine", {
      configurable: true,
      value: false,
    });
    vi.spyOn(console, "error").mockImplementation(() => {});

    render(
      <ErrorBoundary>
        <BrokenChild error={new TypeError("Failed to fetch dynamically imported module")} />
      </ErrorBoundary>
    );

    expect(
      screen.getByRole("heading", { name: "تعذّر تحميل جزء من التطبيق" })
    ).toBeInTheDocument();

    const retryButton = screen.getByRole("button", {
      name: "بانتظار عودة الاتصال",
    });
    expect(retryButton).toBeDisabled();
    expect(screen.getByRole("status")).toHaveTextContent("الاتصال غير متاح حاليًا");

    Object.defineProperty(window.navigator, "onLine", {
      configurable: true,
      value: true,
    });
    fireEvent(window, new Event("online"));

    expect(retryButton).toBeEnabled();
    expect(screen.getByRole("status")).toHaveTextContent("الاتصال متاح الآن");
    expect(retryButton).toHaveTextContent("إعادة المحاولة");
  });

  it("keeps a generic message for errors unrelated to lazy loading", () => {
    vi.spyOn(console, "error").mockImplementation(() => {});

    render(
      <ErrorBoundary>
        <BrokenChild error={new Error("Unexpected rendering failure")} />
      </ErrorBoundary>
    );

    expect(screen.getByRole("heading", { name: "حدث خطأ غير متوقع" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "تحديث الصفحة" })).toBeEnabled();
  });
});
