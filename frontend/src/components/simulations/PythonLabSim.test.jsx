import { act, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import PythonLabSim from "./PythonLabSim";

const CHANNEL = "lumen-python-sandbox";

function sendSandboxMessage(frame, message, origin = "null", source = frame.contentWindow) {
  act(() => {
    window.dispatchEvent(
      new MessageEvent("message", {
        data: { channel: CHANNEL, ...message },
        origin,
        source,
      })
    );
  });
}

function renderReadySandbox() {
  render(<PythonLabSim />);
  const frame = screen.getByTitle("بيئة تنفيذ Python معزولة");
  const postMessage = vi.spyOn(frame.contentWindow, "postMessage").mockImplementation(() => {});
  sendSandboxMessage(frame, { type: "ready" });
  return { frame, postMessage };
}

function lastRunMessage(postMessage) {
  const call = postMessage.mock.calls.find(([message]) => message?.type === "run");
  expect(call).toBeDefined();
  return call[0];
}

afterEach(() => {
  vi.useRealTimers();
  vi.restoreAllMocks();
});

describe("isolated Python lab", () => {
  it("uses an opaque-origin iframe without same-origin or extra permissions", () => {
    render(<PythonLabSim />);
    const frame = screen.getByTitle("بيئة تنفيذ Python معزولة");

    expect(frame).toHaveAttribute("sandbox", "allow-scripts");
    expect(frame).toHaveAttribute("referrerpolicy", "origin");
    expect(frame).not.toHaveAttribute("allow");
    expect(frame).toHaveAttribute("aria-hidden", "true");
  });

  it("sends learner code only to the sandbox and renders its result", async () => {
    const user = userEvent.setup();
    const { frame, postMessage } = renderReadySandbox();

    await user.click(screen.getByRole("button", { name: /شغّل الكود/ }));
    const request = lastRunMessage(postMessage);

    expect(request.channel).toBe(CHANNEL);
    expect(request.code).toContain("print(total)");
    expect(postMessage.mock.calls.at(-1)[1]).toBe("*");

    sendSandboxMessage(frame, {
      type: "status",
      requestId: request.requestId,
      status: "running",
    });
    sendSandboxMessage(frame, {
      type: "complete",
      requestId: request.requestId,
      output: "55",
    });

    expect(screen.getByText("55")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "تحقّق من التحدي" }));
    expect(screen.getByText("صحيح! 55 = 1+2+...+10")).toBeInTheDocument();
  });

  it("ignores messages from a non-opaque origin", async () => {
    const user = userEvent.setup();
    const { frame, postMessage } = renderReadySandbox();
    await user.click(screen.getByRole("button", { name: /شغّل الكود/ }));
    const request = lastRunMessage(postMessage);

    sendSandboxMessage(
      frame,
      { type: "complete", requestId: request.requestId, output: "forged" },
      "https://attacker.example"
    );

    expect(screen.getByRole("button", { name: "إيقاف التنفيذ" })).toBeInTheDocument();
    expect(screen.queryByText("forged")).not.toBeInTheDocument();

    sendSandboxMessage(frame, {
      type: "complete",
      requestId: request.requestId,
      output: "55",
    });
    expect(screen.getByText("55")).toBeInTheDocument();
  });

  it("ignores sandbox messages from a different browsing context", async () => {
    const user = userEvent.setup();
    const { frame, postMessage } = renderReadySandbox();
    await user.click(screen.getByRole("button", { name: /شغّل الكود/ }));
    const request = lastRunMessage(postMessage);

    sendSandboxMessage(
      frame,
      { type: "complete", requestId: request.requestId, output: "forged" },
      "null",
      window
    );

    expect(screen.getByRole("button", { name: "إيقاف التنفيذ" })).toBeInTheDocument();
    expect(screen.queryByText("forged")).not.toBeInTheDocument();
  });

  it("shows runtime loading errors without exposing internal objects", async () => {
    const user = userEvent.setup();
    const { frame, postMessage } = renderReadySandbox();
    await user.click(screen.getByRole("button", { name: /شغّل الكود/ }));
    const request = lastRunMessage(postMessage);

    sendSandboxMessage(frame, {
      type: "error",
      requestId: request.requestId,
      error: "runtime unavailable",
    });

    expect(screen.getByText("خطأ بتشغيل الكود: runtime unavailable")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /شغّل الكود/ })).toBeEnabled();
  });

  it("cancels execution by replacing the sandbox browsing context", async () => {
    const user = userEvent.setup();
    const { frame, postMessage } = renderReadySandbox();
    const originalSrc = frame.getAttribute("src");

    await user.click(screen.getByRole("button", { name: /شغّل الكود/ }));
    expect(lastRunMessage(postMessage)).toBeDefined();

    await user.click(screen.getByRole("button", { name: "إيقاف التنفيذ" }));

    expect(screen.getByText("تم إيقاف التنفيذ وإعادة ضبط بيئة Python.")).toBeInTheDocument();
    expect(frame.getAttribute("src")).not.toBe(originalSrc);
    expect(screen.getByRole("button", { name: /شغّل الكود/ })).toBeEnabled();
  });

  it("terminates a long-running execution after the hard timeout", async () => {
    vi.useFakeTimers();
    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
    const { frame, postMessage } = renderReadySandbox();

    await user.click(screen.getByRole("button", { name: /شغّل الكود/ }));
    const request = lastRunMessage(postMessage);
    sendSandboxMessage(frame, {
      type: "status",
      requestId: request.requestId,
      status: "running",
    });

    act(() => {
      vi.advanceTimersByTime(8_001);
    });

    expect(
      screen.getByText(/انتهت مهلة التنفيذ/)
    ).toBeInTheDocument();
    expect(frame.getAttribute("src")).toContain("reset=");
    expect(screen.getByRole("button", { name: /شغّل الكود/ })).toBeEnabled();
  });
});
