import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import remarkMath from "remark-math";
import rehypeKatex from "rehype-katex";

// ثوابت خارج المكوّن: نفس المراجع كل عرض بدل إنشاء مصفوفات جديدة
const REMARK_PLUGINS = [remarkGfm, remarkMath];
// throwOnError: false → معادلة خاطئة تظهر بالأحمر بدل ما تكسر الصفحة
const REHYPE_PLUGINS = [[rehypeKatex, { throwOnError: false, strict: "ignore" }]];
// الفقرة تصير <span> عشان النص القصير (سؤال، خيار) يبقى داخل السطر بدون هوامش فقرة
const INLINE_COMPONENTS = {
  // eslint-disable-next-line no-unused-vars
  p: ({ node, ...props }) => <span {...props} />,
};

/**
 * يعرض نصًا فيه Markdown + رياضيات LaTeX ($...$ داخل السطر، و$$ على أسطر مستقلة للمعادلة المنفصلة) + كود.
 * inline: للنصوص القصيرة (نص سؤال، خيار، شرح) — بدون فقرات وهوامش.
 */
export default function MathText({ children, inline = false, className = "" }) {
  const text = typeof children === "string" ? children : String(children ?? "");
  const Wrapper = inline ? "span" : "div";
  return (
    <Wrapper className={`math-text ${className}`.trim()}>
      <ReactMarkdown
        remarkPlugins={REMARK_PLUGINS}
        rehypePlugins={REHYPE_PLUGINS}
        components={inline ? INLINE_COMPONENTS : undefined}
      >
        {text}
      </ReactMarkdown>
    </Wrapper>
  );
}
