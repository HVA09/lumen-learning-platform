import { render, waitFor } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import MathText from "./MathText";

async function waitForMathRenderer(container) {
  await waitFor(() => {
    const wrapper = container.querySelector(".math-text");
    expect(wrapper).not.toBeNull();
    expect(wrapper.getAttribute("aria-busy")).not.toBe("true");
  });
}

describe("MathText", () => {
  it("يحوّل $...$ إلى معادلة مصوّرة بدون $ ظاهرة", async () => {
    const { container } = render(<MathText>{"قيمة $x^2 + 1$ هنا"}</MathText>);
    await waitForMathRenderer(container);
    expect(container.querySelector(".katex")).not.toBeNull();
    expect(container).not.toHaveTextContent("$");
    expect(container).toHaveTextContent("قيمة");
  });

  it("المعادلة المنفصلة تحتاج $$ على أسطر مستقلة، وبسطر واحد تُعرض داخل السطر", async () => {
    const delimiter = String.fromCharCode(36, 36);
    const fenced = render(<MathText>{delimiter + "\n\\frac{a}{b}\n" + delimiter}</MathText>);
    await waitForMathRenderer(fenced.container);
    expect(fenced.container.querySelector(".katex-display")).not.toBeNull();

    const oneLine = render(<MathText>{delimiter + "\\frac{a}{b}" + delimiter}</MathText>);
    await waitForMathRenderer(oneLine.container);
    expect(oneLine.container.querySelector(".katex")).not.toBeNull();
    expect(oneLine.container.querySelector(".katex-display")).toBeNull();
  });

  it("وضع inline لا يلفّ النص بفقرة <p>", async () => {
    const block = render(<MathText>{"نص قصير"}</MathText>);
    await waitForMathRenderer(block.container);
    expect(block.container.querySelector("p")).not.toBeNull();

    const inline = render(<MathText inline>{"نص قصير"}</MathText>);
    await waitForMathRenderer(inline.container);
    expect(inline.container.querySelector("p")).toBeNull();
    expect(inline.container.firstChild.tagName).toBe("SPAN");
  });

  it("الكود يبقى كودًا ولا يُعامل كرياضيات", async () => {
    const { container } = render(<MathText inline>{"الدالة `range(1, 5)` تنتج أرقامًا"}</MathText>);
    await waitForMathRenderer(container);
    expect(container.querySelector("code")).toHaveTextContent("range(1, 5)");
    expect(container.querySelector(".katex")).toBeNull();
  });

  it("معادلة غير صالحة لا تكسر الصفحة (تظهر بالأحمر)", async () => {
    const { container } = render(<MathText>{"$\\frac{a$"}</MathText>);
    await waitForMathRenderer(container);
    expect(container.querySelector(".math-text")).not.toBeNull();
  });

  it("الجداول وعلامات الجداول GFM تُعرض", async () => {
    const { container } = render(<MathText>{"| الدالة | مشتقتها |\n|---|---|\n| $x^2$ | $2x$ |"}</MathText>);
    await waitForMathRenderer(container);
    expect(container.querySelector("table")).not.toBeNull();
    expect(container.querySelectorAll(".katex")).toHaveLength(2);
  });

  it("يقبل قيمة غير نصية بدون أخطاء", async () => {
    const empty = render(<MathText>{undefined}</MathText>);
    await waitForMathRenderer(empty.container);
    const number = render(<MathText>{12}</MathText>);
    await waitForMathRenderer(number.container);
    expect(number.container).toHaveTextContent("12");
  });
});
