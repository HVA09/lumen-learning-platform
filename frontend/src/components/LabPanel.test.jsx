import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

vi.mock("./simulations/LinearFunctionSim", () => ({
  default: () => <div data-testid="linear-function-simulation" />,
}));
vi.mock("./simulations/DerivativeSim", () => ({
  default: () => <div data-testid="derivative-simulation" />,
}));
vi.mock("./simulations/ProjectileSim", () => ({
  default: () => <div data-testid="projectile-simulation" />,
}));
vi.mock("./simulations/CircuitSim", () => ({
  default: () => <div data-testid="circuit-simulation" />,
}));
vi.mock("./simulations/PythonLabSim", () => ({
  default: () => <div data-testid="python-lab-simulation" />,
}));

import LabPanel from "./LabPanel";

describe("LabPanel", () => {
  it.each([
    ["linear-function", "linear-function-simulation"],
    ["derivative", "derivative-simulation"],
    ["projectile", "projectile-simulation"],
    ["circuits-dc", "circuit-simulation"],
    ["python-lab", "python-lab-simulation"],
  ])("loads the correct lazy simulation for type %s", async (simulationType, testId) => {
    render(
      <LabPanel
        simulationType={simulationType}
        topicName="موضوع تجريبي"
        onClose={vi.fn()}
      />
    );

    expect(await screen.findByTestId(testId)).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "المختبر — موضوع تجريبي" })).toBeInTheDocument();
  });

  it("shows a fallback message for an unsupported simulation type", () => {
    render(
      <LabPanel
        simulationType="unknown-simulation"
        topicName="موضوع آخر"
        onClose={vi.fn()}
      />
    );

    expect(screen.getByText("ما فيه محاكاة لهذا الموضوع بعد")).toBeInTheDocument();
    expect(screen.queryByTestId(/-simulation$/)).not.toBeInTheDocument();
  });

  it("shows the default laboratory heading when no topic name is supplied", () => {
    render(<LabPanel simulationType="unknown-simulation" onClose={vi.fn()} />);

    expect(screen.getByRole("heading", { name: "المختبر" })).toBeInTheDocument();
  });

  it("closes the laboratory when the close button is selected", async () => {
    const onClose = vi.fn();
    const user = userEvent.setup();

    render(
      <LabPanel
        simulationType="linear-function"
        topicName="المعادلات الخطية"
        onClose={onClose}
      />
    );

    await screen.findByTestId("linear-function-simulation");
    await user.click(screen.getByRole("button", { name: "✕" }));

    expect(onClose).toHaveBeenCalledTimes(1);
  });
});
