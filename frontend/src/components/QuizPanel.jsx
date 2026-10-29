import { useEffect, useRef, useState } from "react";
import { startQuiz, submitQuiz } from "../lib/quizApi";
import MathText from "./MathText";

function QuestionInput({ question, value, onChange }) {
  if (question.kind === "mcq" || question.kind === "true_false") {
    return (
      <div className="mt-2 space-y-1.5">
        {question.choices.map((choice, i) => {
          const optionValue = question.kind === "true_false" ? i === 0 : i;
          const checked = value === optionValue;
          return (
            <label
              key={choice}
              className={`flex cursor-pointer items-center gap-2 rounded-xl border px-3 py-2 text-sm ${
                checked ? "border-slate-900 bg-slate-50" : "border-slate-200 hover:bg-slate-50"
              }`}
            >
              <input
                type="radio"
                className="accent-slate-900"
                checked={checked}
                onChange={() => onChange(optionValue)}
              />
              <MathText inline>{choice}</MathText>
            </label>
          );
        })}
      </div>
    );
  }

  return (
    <input
      type={question.kind === "numeric" ? "text" : "text"}
      inputMode={question.kind === "numeric" ? "decimal" : "text"}
      value={value ?? ""}
      onChange={(e) => onChange(e.target.value)}
      placeholder={question.kind === "numeric" ? "اكتب رقمًا..." : "اكتب إجابتك..."}
      className="mt-2 w-full rounded-xl border border-slate-200 bg-slate-50 p-2.5 text-sm outline-none focus:border-slate-400 focus:ring-2 focus:ring-slate-400"
    />
  );
}

function ResultsView({ result, onClose }) {
  const isGateway = result.mode === "gateway";
  return (
    <div>
      <div
        className={`mb-4 rounded-2xl border p-4 text-center ${
          isGateway
            ? result.passed
              ? "border-emerald-200 bg-emerald-50"
              : "border-amber-200 bg-amber-50"
            : "border-slate-200 bg-slate-50"
        }`}
      >
        <p className="text-2xl font-semibold text-slate-900">{Math.round(result.score_percentage)}%</p>
        <p className="mt-1 text-sm text-slate-600">
          {result.correct_count} من {result.total} صحيحة
        </p>
        {isGateway && (
          <p className={`mt-2 text-sm font-medium ${result.passed ? "text-emerald-700" : "text-amber-700"}`}>
            {result.passed ? "🎉 اجتزت اختبار البوابة!" : "لم تجتز بعد — راجع الدرس وحاول مرة ثانية"}
          </p>
        )}
      </div>

      <div className="space-y-3">
        {result.results.map((r, i) => (
          <div
            key={r.question_id}
            className={`rounded-xl border p-3 text-sm ${
              r.correct ? "border-emerald-200 bg-emerald-50" : "border-red-200 bg-red-50"
            }`}
          >
            <p className="font-medium text-slate-900">
              {i + 1}. <MathText inline>{r.prompt_ar}</MathText>
            </p>
            <p className="mt-1 text-xs text-slate-600">
              {r.correct ? (
                "✓ صحيح"
              ) : (
                <>
                  ✗ الإجابة الصحيحة: <MathText inline>{r.correct_answer_text}</MathText>
                </>
              )}
            </p>
            {r.explanation_ar && (
              <p className="mt-1 text-xs text-slate-500">
                <MathText inline>{r.explanation_ar}</MathText>
              </p>
            )}
          </div>
        ))}
      </div>

      <button
        onClick={onClose}
        className="mt-4 w-full rounded-xl bg-slate-900 px-4 py-2 text-sm text-white hover:bg-slate-800"
      >
        إغلاق
      </button>
    </div>
  );
}

export default function QuizPanel({ topicId, mode, onClose, onFinished }) {
  const [attempt, setAttempt] = useState(null);
  const [answers, setAnswers] = useState({});
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");
  const startedRef = useRef(false);

  useEffect(() => {
    // StrictMode يشغّل الـ effect مرتين بالتطوير — بدون هذا الحارس ينشأ طلبان وتُنشأ محاولتان
    if (startedRef.current) return;
    startedRef.current = true;
    startQuiz(topicId, mode)
      .then(setAttempt)
      .catch((err) => setError(err.response?.data?.detail || "تعذر بدء الاختبار"))
      .finally(() => setLoading(false));
  }, [topicId, mode]);

  const handleSubmit = async () => {
    setSubmitting(true);
    try {
      const answersPayload = attempt.questions.map((q) => ({
        question_id: q.id,
        answer: answers[q.id] ?? null,
      }));
      const data = await submitQuiz(attempt.attempt_id, answersPayload);
      setResult(data);
      onFinished(data);
    } catch {
      setError("تعذر تسليم الاختبار");
    } finally {
      setSubmitting(false);
    }
  };

  // الإجابة الفارغة (كتب ثم مسح) ما تُحسب مُجابة
  const answeredCount = Object.values(answers).filter((v) => v !== "" && v !== null && v !== undefined).length;

  return (
    <div className="fixed inset-0 z-[60] flex items-center justify-center overflow-y-auto bg-black/40 p-4">
      <div className="my-8 w-full max-w-lg rounded-3xl border border-slate-200 bg-white p-6 shadow-lg">
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-lg font-semibold text-slate-900">
            {mode === "gateway" ? "اختبار البوابة" : "اختبار تدريبي"}
          </h2>
          <button
            onClick={onClose}
            className="rounded-lg px-2 py-1 text-slate-400 hover:bg-slate-100 focus:outline-none focus:ring-2 focus:ring-slate-400"
          >
            ✕
          </button>
        </div>

        {loading ? (
          <p className="text-sm text-slate-400">...</p>
        ) : error ? (
          <p className="text-sm text-red-600">{error}</p>
        ) : result ? (
          <ResultsView result={result} onClose={onClose} />
        ) : (
          <>
            {attempt.resumed && (
              <p className="mb-3 rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-xs text-slate-500">
                استكملت محاولة سابقة لم تُسلَّم
              </p>
            )}
            <div className="space-y-4">
              {attempt.questions.map((question, i) => (
                <div key={question.id} className="rounded-2xl border border-slate-200 p-3">
                  <p className="text-sm font-medium text-slate-900">
                    {i + 1}. <MathText inline>{question.prompt_ar}</MathText>
                  </p>
                  <QuestionInput
                    question={question}
                    value={answers[question.id]}
                    onChange={(v) => setAnswers((prev) => ({ ...prev, [question.id]: v }))}
                  />
                </div>
              ))}
            </div>

            <button
              onClick={handleSubmit}
              disabled={submitting}
              className="mt-4 w-full rounded-xl bg-slate-900 px-4 py-2 text-sm text-white hover:bg-slate-800 disabled:opacity-50"
            >
              {submitting
                ? "جاري التصحيح..."
                : `سلّم الإجابات (${answeredCount}/${attempt.questions.length})`}
            </button>
          </>
        )}
      </div>
    </div>
  );
}
