import { lazy, Suspense } from "react";

const MathTextRenderer = lazy(() => import("./MathTextRenderer"));

function MathTextFallback({ inline = false, className = "" }) {
  const Wrapper = inline ? "span" : "div";
  return (
    <Wrapper className={`math-text ${className}`.trim()} aria-busy="true">
      <span aria-hidden="true">…</span>
    </Wrapper>
  );
}

/**
 * حمّل محرك Markdown وKaTeX فقط عندما يظهر محتوى يحتاج إلى العرض.
 * يبقى هذا الغلاف خفيفًا حتى مع استيراده من لوحات محمّلة عند الطلب.
 */
export default function MathText(props) {
  return (
    <Suspense fallback={<MathTextFallback inline={props.inline} className={props.className} />}>
      <MathTextRenderer {...props} />
    </Suspense>
  );
}
