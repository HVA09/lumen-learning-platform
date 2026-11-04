import { lazy, Suspense } from "react";

const MathTextRenderer = lazy(() => import("./MathTextRenderer"));

/**
 * غلاف خفيف يؤجل ReactMarkdown وKaTeX حتى يظهر محتوى يحتاج إلى تنسيق.
 * تظهر القيمة النصية مؤقتًا أثناء تحميل محرك العرض، مع الحفاظ على عنصر inline/block.
 */
export default function MathText({ children, inline = false, className = "" }) {
  const text = typeof children === "string" ? children : String(children ?? "");
  const Wrapper = inline ? "span" : "div";
  const classes = `math-text ${className}`.trim();

  return (
    <Suspense
      fallback={
        <Wrapper className={classes} aria-busy="true">
          {text}
        </Wrapper>
      }
    >
      <MathTextRenderer children={children} inline={inline} className={className} />
    </Suspense>
  );
}
