import { render, waitFor } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import MathText from "./MathText";

describe("MathText", () => {
  it("يحوّل $...$ إلى معادلة مصوّرة بدون $ ظاهرة", async () => {
    const { container } = render(<MathText>{"قيمة $x^2 + 1$ هنا"}</MathText>);
    await waitFor(() => expect(container.querySelector(".katex")).not.toBeNull());
    expect(container).not.toHaveTextContent("$");
    expect(container).toHaveTextContent("قيمة");
  });

  it("المعادلة المنفصلة تحتاج $$ على أسطر مستقلة، وبسطر واحد تُعرض داخل السطر", async () => {
    const fenced = render(<MathText>{"$$\n\\frac{a}{b}\n$$"}</MathText>);
    await waitFor(() => expect(fenced.container.querySelector(".katex-display")).not.toBeNull());

    const oneLine = render(<MathText>{"$$\\frac{a}{b}$$"}</MathText>);
    await waitFor(() => expect(oneLine.container.querySelector(".katex")).not.toBeNull());
    expect(oneLine.container.querySelector(".katex-display")).toBeNull();
  });

  it("وضع inline لا يلفّ النص بفقرة <p>", async () => {
    const block = render(<MathText>{"نص قصير"}</MathText>);
    await waitFor(() => expect(block.container.querySelector("p")).not.toBeNull());

    const inline = render(<MathText inline>{"نص قصير"}</MathText>);
    await waitFor(() => expect(inline.container.querySelector(".math-text")).not.toHaveAttribute("aria-busy"));
    expect(inline.container.querySelector("p")).toBeNull();
    expect(inline.container.firstChild.tagName).toBe("SPAN");
  });

  it("الكود يبقى كودًا ولا يُعامل كرياضيات", async () => {
    const { container } = render(<MathText inline>{"الدالة `range(1, 5)` تنتج أرقامًا"}</MathText>);
    await waitFor(() => expect(container.querySelector("code")).toHaveTextContent("range(1, 5)"));
    expect(container.querySelector(".katex")).toBeNull();
  });

  it("معادلة غير صالحة لا تكسر الصفحة (تظهر بالأحمر)", async () => {
    const { container } = render(<MathText>{"$\\frac{a$"}</MathText>);
    await waitFor(() => expect(container.querySelector(".math-text")).not.toHaveAttribute("aria-busy"));
  });

  it("الجداول وعلامات الجداول GFM تُعرض", async () => {
    const { container } = render(<MathText>{"| الدالة | مشتقتها |\n|---|---|\n| $x^2$ | $2x$ |"}</MathText>);
    await waitFor(() => expect(container.querySelector("table")).not.toBeNull());
    expect(container.querySelectorAll(".katex")).toHaveLength(2);
  });

  it("يقبل قيمة غير نصية بدون أخطاء", async () => {
    const empty = render(<MathText>{undefined}</MathText>);
    const number = render(<MathText>{12}</MathText>);
    await waitFor(() => expect(empty.container.querySelector(".math-text")).not.toHaveAttribute("aria-busy"));
    expect(number.container).toHaveTextContent("12");
  });
});
