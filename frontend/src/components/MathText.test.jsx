import { render } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import MathText from "./MathText";

describe("MathText", () => {
  it("يحوّل $...$ إلى معادلة مصوّرة بدون $ ظاهرة", () => {
    const { container } = render(<MathText>{"قيمة $x^2 + 1$ هنا"}</MathText>);
    expect(container.querySelector(".katex")).not.toBeNull();
    expect(container).not.toHaveTextContent("$");
    expect(container).toHaveTextContent("قيمة");
  });

  it("المعادلة المنفصلة تحتاج $$ على أسطر مستقلة، وبسطر واحد تُعرض داخل السطر", () => {
    const fenced = render(<MathText>{"$$\n\\frac{a}{b}\n$$"}</MathText>);
    expect(fenced.container.querySelector(".katex-display")).not.toBeNull();

    const oneLine = render(<MathText>{"$$\\frac{a}{b}$$"}</MathText>);
    expect(oneLine.container.querySelector(".katex")).not.toBeNull();
    expect(oneLine.container.querySelector(".katex-display")).toBeNull();
  });

  it("وضع inline لا يلفّ النص بفقرة <p>", () => {
    const block = render(<MathText>{"نص قصير"}</MathText>);
    expect(block.container.querySelector("p")).not.toBeNull();

    const inline = render(<MathText inline>{"نص قصير"}</MathText>);
    expect(inline.container.querySelector("p")).toBeNull();
    expect(inline.container.firstChild.tagName).toBe("SPAN");
  });

  it("الكود يبقى كودًا ولا يُعامل كرياضيات", () => {
    const { container } = render(<MathText inline>{"الدالة `range(1, 5)` تنتج أرقامًا"}</MathText>);
    expect(container.querySelector("code")).toHaveTextContent("range(1, 5)");
    expect(container.querySelector(".katex")).toBeNull();
  });

  it("معادلة غير صالحة لا تكسر الصفحة (تظهر بالأحمر)", () => {
    expect(() => render(<MathText>{"$\\frac{a$"}</MathText>)).not.toThrow();
  });

  it("الجداول وعلامات الجداول GFM تُعرض", () => {
    const { container } = render(<MathText>{"| الدالة | مشتقتها |\n|---|---|\n| $x^2$ | $2x$ |"}</MathText>);
    expect(container.querySelector("table")).not.toBeNull();
    expect(container.querySelectorAll(".katex")).toHaveLength(2);
  });

  it("يقبل قيمة غير نصية بدون أخطاء", () => {
    expect(() => render(<MathText>{undefined}</MathText>)).not.toThrow();
    expect(() => render(<MathText>{12}</MathText>)).not.toThrow();
  });
});
