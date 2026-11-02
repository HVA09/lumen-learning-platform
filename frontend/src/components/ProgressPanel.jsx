import { useEffect, useState } from "react";
import { getMyProgress, sendMyReport } from "../lib/reportsApi";

export default function ProgressPanel({ onClose }) {
  const [report, setReport] = useState(null);
  const [loading, setLoading] = useState(true);
  const [sending, setSending] = useState(false);
  const [sent, setSent] = useState(false);
  const [error, setError] = useState("");

  const loadReport = async () => {
    setLoading(true);
    setError("");
    try {
      setReport(await getMyProgress());
    } catch {
      setError("تعذر تحميل تقرير التقدم. تحقق من الاتصال وحاول مرة أخرى.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadReport();
  }, []);

  const handleSend = async () => {
    setSending(true);
    setError("");
    try {
      await sendMyReport();
      setSent(true);
    } catch {
      setError("تعذر إرسال التقرير. حاول مرة أخرى.");
    } finally {
      setSending(false);
    }
  };

  const stats = report
    ? [
        ["متوسط الإتقان", `${report.average_mastery}%`],
        ["بوابات مجتازة", report.gateway_quizzes_passed],
        ["دروس منجزة", report.lessons_completed],
        ["اختبارات مسلَّمة", report.quizzes_taken],
        ["متوسط درجة الاختبارات", `${report.average_quiz_score}%`],
        ["أيام دراسة متتالية", `🔥 ${report.streak_days}`],
        ["إنجازات مفتوحة", report.achievements_unlocked],
        ["واجبات مُسلَّمة", report.assignments_submitted],
        ["بطاقات مستحقة الآن", report.cards_due_now],
      ]
    : [];

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center overflow-y-auto bg-black/30 p-4">
      <div className="my-8 w-full max-w-md rounded-3xl border border-slate-200 bg-white p-6 shadow-lg">
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-lg font-semibold text-slate-900">تقدّمي</h2>
          <button
            onClick={onClose}
            className="rounded-lg px-2 py-1 text-slate-400 hover:bg-slate-100 focus:outline-none focus:ring-2 focus:ring-slate-400"
          >
            ✕
          </button>
        </div>

        {loading ? (
          <p className="text-sm text-slate-400">...</p>
        ) : error && !report ? (
          <div className="space-y-3">
            <p className="text-sm text-red-600">{error}</p>
            <button onClick={loadReport} className="w-full rounded-xl border border-slate-200 px-4 py-2 text-sm">
              إعادة المحاولة
            </button>
          </div>
        ) : report ? (
          <>
            {error && <p className="mb-3 text-sm text-red-600">{error}</p>}
            <div className="grid grid-cols-2 gap-3">
              {stats.map(([label, value]) => (
                <div key={label} className="rounded-2xl border border-slate-200 p-3 text-center">
                  <p className="text-xl font-semibold text-slate-900">{value}</p>
                  <p className="mt-1 text-xs text-slate-500">{label}</p>
                </div>
              ))}
            </div>

            {report.weak_topics.length > 0 && (
              <div className="mt-4 rounded-2xl border border-amber-200 bg-amber-50 p-3">
                <p className="text-sm text-amber-800">
                  مواضيع تحتاج تركيز أكثر: {report.weak_topics.join("، ")}
                </p>
              </div>
            )}

            <button
              onClick={handleSend}
              disabled={sending || sent}
              className="mt-4 w-full rounded-xl bg-slate-900 px-4 py-2 text-sm text-white hover:bg-slate-800 disabled:opacity-50"
            >
              {sent ? "تم الإرسال ✓" : sending ? "جاري الإرسال..." : "أرسل التقرير لبريدي"}
            </button>
          </>
        ) : null}
      </div>
    </div>
  );
}
