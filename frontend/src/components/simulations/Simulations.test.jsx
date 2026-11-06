import { act, fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import LinearFunctionSim from "./LinearFunctionSim";
import DerivativeSim from "./DerivativeSim";
import ProjectileSim from "./ProjectileSim";
import CircuitSim from "./CircuitSim";
import PythonLabSim from "./PythonLabSim";

function createCanvasContext() {
  return {
    clearRect: vi.fn(),
    beginPath: vi.fn(),
    moveTo: vi.fn(),
    lineTo: vi.fn(),
    stroke: vi.fn(),
    arc: vi.fn(),
    fill: vi.fn(),
    fillRect: vi.fn(),
    strokeRect: vi.fn(),
    fillText: vi.fn(),
  };
}

let canvasContexts = [];
const runPythonAsyncMock = vi.fn();

beforeEach(() => {
  canvasContexts = [];
  runPythonAsyncMock.mockReset().mockResolvedValue("55");
  window.loadPyodide = vi.fn().mockResolvedValue({
    runPythonAsync: runPythonAsyncMock,
  });
  vi.spyOn(HTMLCanvasElement.prototype, "getContext").mockImplementation(() => {
    const context = createCanvasContext();
    canvasContexts.push(context);
    return context;
  });
});

afterEach(() => {
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
  delete window.loadPyodide;
});

describe("interactive simulation calculations", () => {
  it("accepts the target line through both points when m=2 and b=1", async () => {
    const user = userEvent.setup();
    render(<LinearFunctionSim />);

    const [slope, intercept] = screen.getAllByRole("slider");
    fireEvent.change(slope, { target: { value: "2" } });
    fireEvent.change(intercept, { target: { value: "1" } });

    await user.click(screen.getByRole("button", { name: "تحقّق" }));

    expect(await screen.findByText("صحيح! المعادلة: y = 2x + 1")).toBeInTheDocument();
  });

  it("shows feedback when the selected line does not pass through both targets", async () => {
    const user = userEvent.setup();
    render(<LinearFunctionSim />);
    await user.click(screen.getByRole("button", { name: "تحقّق" }));
    expect(await screen.findByText("قريب، جرّب تعدّل القيم أكثر")).toBeInTheDocument();
  });

  it("accepts the derivative challenge when x=2 and f'(x)=4", async () => {
    const user = userEvent.setup();
    render(<DerivativeSim />);

    fireEvent.change(screen.getByRole("slider"), { target: { value: "2" } });
    expect(screen.getByRole("slider")).toHaveValue("2");

    await user.click(screen.getByRole("button", { name: "تحقّق" }));

    expect(await screen.findByText("صحيح! عند x=2، الميل = 2×2 = 4")).toBeInTheDocument();
  });

  it("shows feedback when the selected derivative slope is not the target", async () => {
    const user = userEvent.setup();
    render(<DerivativeSim />);
    await user.click(screen.getByRole("button", { name: "تحقّق" }));
    expect(await screen.findByText("قريب، جرّب تحرّك النقطة أكثر")).toBeInTheDocument();
  });

  it("reaches the 20 metre projectile target at 14 m/s and 45 degrees", async () => {
    const user = userEvent.setup();
    render(<ProjectileSim />);

    const [speed, angle] = screen.getAllByRole("slider");
    fireEvent.change(speed, { target: { value: "14" } });
    fireEvent.change(angle, { target: { value: "45" } });

    expect(screen.getByText(/المدى المتوقع: 20\.0 م/)).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "تحقّق" }));

    expect(await screen.findByText("أصبت الهدف! 🎯")).toBeInTheDocument();
  });

  it("shows feedback when the projectile range misses the target", async () => {
    const user = userEvent.setup();
    render(<ProjectileSim />);
    await user.click(screen.getByRole("button", { name: "تحقّق" }));
    expect(await screen.findByText(/قريب — مداك الحالي/)).toBeInTheDocument();
  });

  it("animates a launched projectile until it reaches the ground", async () => {
    const user = userEvent.setup();
    const frames = [];
    vi.stubGlobal("requestAnimationFrame", vi.fn((callback) => {
      frames.push(callback);
      return frames.length;
    }));
    render(<ProjectileSim />);

    const launchButton = screen.getByRole("button", { name: "أطلق" });
    await user.click(launchButton);
    expect(launchButton).toBeDisabled();
    expect(frames).toHaveLength(1);

    await act(async () => {
      let frameCount = 0;
      while (frames.length > 0 && frameCount < 150) {
        const nextFrame = frames.shift();
        nextFrame(0);
        frameCount += 1;
      }
    });

    expect(frames).toHaveLength(0);
    expect(launchButton).toBeEnabled();
    expect(canvasContexts.some((context) => context.fill.mock.calls.length > 0)).toBe(true);
  });

  it("computes the equivalent resistance and current for a parallel circuit", async () => {
    const user = userEvent.setup();
    render(<CircuitSim />);

    await user.click(screen.getByRole("button", { name: "توازي" }));
    const [r1, r2] = screen.getAllByRole("slider");
    fireEvent.change(r1, { target: { value: "12" } });
    fireEvent.change(r2, { target: { value: "12" } });

    expect(screen.getByText(/المقاومة المكافئة: 6\.0 أوم/)).toBeInTheDocument();
    expect(screen.getByText(/التيار الكلي: 2\.00 أمبير/)).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "تحقّق" }));
    expect(await screen.findByText("صحيح! طبّقت قانون أوم بنجاح")).toBeInTheDocument();
  });

  it("shows feedback when the circuit current is not the target", async () => {
    const user = userEvent.setup();
    render(<CircuitSim />);
    await user.click(screen.getByRole("button", { name: "تحقّق" }));
    expect(await screen.findByText(/التيار حاليًا 1\.20 أمبير/)).toBeInTheDocument();
  });

  it("computes the total current for a series circuit", async () => {
    const user = userEvent.setup();
    render(<CircuitSim />);

    const [r1, r2] = screen.getAllByRole("slider");
    fireEvent.change(r1, { target: { value: "2" } });
    fireEvent.change(r2, { target: { value: "4" } });

    expect(screen.getByText(/المقاومة المكافئة: 6\.0 أوم/)).toBeInTheDocument();
    expect(screen.getByText(/التيار الكلي: 2\.00 أمبير/)).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "تحقّق" }));
    expect(await screen.findByText("صحيح! طبّقت قانون أوم بنجاح")).toBeInTheDocument();
  });

  it("shows a useful error when the Pyodide runtime cannot be loaded", async () => {
    const user = userEvent.setup();
    const loadPyodide = vi.fn().mockRejectedValue(new Error("runtime unavailable"));
    window.loadPyodide = loadPyodide;

    render(<PythonLabSim />);
    await user.click(screen.getByRole("button", { name: /شغّل الكود/ }));

    expect(await screen.findByText("خطأ بتشغيل الكود: runtime unavailable")).toBeInTheDocument();
    expect(loadPyodide).toHaveBeenCalledTimes(1);
    expect(screen.getByRole("button", { name: /شغّل الكود/ })).toBeEnabled();
  });

  it("runs the Python exercise through a mocked Pyodide runtime", async () => {
    const user = userEvent.setup();
    const loadPyodide = window.loadPyodide;

    render(<PythonLabSim />);

    await user.click(screen.getByRole("button", { name: /شغّل الكود/ }));

    expect(await screen.findByText("55")).toBeInTheDocument();
    expect(loadPyodide).toHaveBeenCalledTimes(1);
    expect(runPythonAsyncMock).toHaveBeenCalledTimes(1);

    await user.click(screen.getByRole("button", { name: "تحقّق من التحدي" }));
    expect(await screen.findByText("صحيح! 55 = 1+2+...+10")).toBeInTheDocument();
  });

  it("rejects a Python challenge when the output does not match the expected answer", async () => {
    const user = userEvent.setup();
    runPythonAsyncMock.mockReset().mockResolvedValue("54");

    render(<PythonLabSim />);
    await user.click(screen.getByRole("button", { name: /شغّل الكود/ }));
    expect(await screen.findByText("54")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "تحقّق من التحدي" }));
    expect(await screen.findByText('الإخراج الحالي "54" مو مطابق')).toBeInTheDocument();
  });

  it("shows a Python execution error when the runtime rejects the code", async () => {
    const user = userEvent.setup();
    runPythonAsyncMock.mockReset().mockRejectedValue(new Error("execution interrupted"));

    render(<PythonLabSim />);
    await user.click(screen.getByRole("button", { name: /شغّل الكود/ }));
    expect(await screen.findByText("خطأ بتشغيل الكود: execution interrupted")).toBeInTheDocument();
  });

});
