import { useEffect, useState } from "react";
import { getSubjects } from "../lib/curriculumApi";
import {
  createLesson,
  createQuestion,
  deleteLesson,
  deleteQuestion,
  getTopicAnalytics,
  listTopicLessonsForTeacher,
  listTopicQuestions,
  updateLesson,
  updateQuestion,
} from "../lib/contentApi";
import MathText from "./MathText";

const KIND_LABELS = {
  mcq: "اختيار من متعدد",
  true_false: "صح / خطأ",
  numeric: "رقمية",
  short_text: "نصية قصيرة",
};

function extractError(err, fallback) {
  const detail = err.response?.data?.detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) return detail.map((d) => d.msg).join("؛ ");
  return fallback;
}

// ---------------- الدروس ----------------

function LessonForm({ initial, onCancel, onSaved, topicId }) {
  const [titleAr, setTitleAr] = useState(initial?.title_ar || "");
  const [bodyMd, setBodyMd] = useState(initial?.body_md || "");
  const [estimatedMinutes, setEstimatedMinutes] = useState(initial?.estimated_minutes ?? 5);
  const [orderIndex, setOrderIndex] = useState(initial?.order_index ?? 0);
  const [isPublished, setIsPublished] = useState(initial?.is_published ?? true);
  const [showPreview, setShowPreview] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  const handleSave = async () => {
    setError("");
    setSaving(true);
    const payload = {
      title_ar: titleAr.trim(),
      body_md: bodyMd,
      estimated_minutes: Number(estimatedMinutes),
      order_index: Number(orderIndex),
      is_published: isPublished,
    };
    try {
      const saved = initial
        ? await updateLesson(initial.id, payload)
        : await createLesson(topicId, payload);
      onSaved(saved);
    } catch (err) {
      setError(extractError(err, "تعذر حفظ الدرس"));
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="space-y-2 rounded-2xl border border-slate-300 bg-slate-50 p-3">
      {error && <p className="text-xs text-red-600">{error}</p>}
      <input
        value={titleAr}
        onChange={(e) => setTitleAr(e.target.value)}
        placeholder="عنوان الدرس"
        className="w-full rounded-lg border border-slate-200 p-2 text-sm outline-none focus:border-slate-400"
      />
      <textarea
        value={bodyMd}
        onChange={(e) => setBodyMd(e.target.value)}
        rows={8}
        placeholder="محتوى الدرس (Markdown) — الرياضيات بين $...$ والمعادلة المنفصلة بـ $$ على أسطر مستقلة"
        className="w-full rounded-lg border border-slate-200 p-2 font-mono text-xs outline-none focus:border-slate-400"
      />
      <button
        type="button"
        onClick={() => setShowPreview((v) => !v)}
        className="text-xs text-slate-500 hover:text-slate-700"
      >
        {showPreview ? "إخفاء المعاينة" : "👁 معاينة كما يراها الطالب"}
      </button>
      {showPreview && (
        <div className="max-h-72 overflow-y-auto rounded-xl border border-slate-200 bg-white p-3">
          {bodyMd.trim() ? (
            <MathText className="lesson-content">{bodyMd}</MathText>
          ) : (
            <p className="text-xs text-slate-400">اكتب محتوى الدرس لتظهر المعاينة</p>
          )}
        </div>
      )}
      <div className="flex flex-wrap items-center gap-3">
        <label className="flex items-center gap-1.5 text-xs text-slate-600">
          الدقائق التقديرية
          <input
            type="number"
            min={1}
            value={estimatedMinutes}
            onChange={(e) => setEstimatedMinutes(e.target.value)}
            className="w-16 rounded-lg border border-slate-200 p-1.5 text-sm"
          />
        </label>
        <label className="flex items-center gap-1.5 text-xs text-slate-600">
          الترتيب
          <input
            type="number"
            min={0}
            value={orderIndex}
            onChange={(e) => setOrderIndex(e.target.value)}
            className="w-16 rounded-lg border border-slate-200 p-1.5 text-sm"
          />
        </label>
        <label className="flex items-center gap-1.5 text-xs text-slate-600">
          <input
            type="checkbox"
            checked={isPublished}
            onChange={(e) => setIsPublished(e.target.checked)}
          />
          منشور (يظهر للطلاب)
        </label>
      </div>
      <div className="flex gap-2">
        <button
          onClick={handleSave}
          disabled={saving || !titleAr.trim() || !bodyMd.trim()}
          className="rounded-lg bg-slate-900 px-3 py-1.5 text-xs text-white hover:bg-slate-800 disabled:opacity-50"
        >
          {saving ? "..." : "حفظ"}
        </button>
        <button onClick={onCancel} className="rounded-lg border border-slate-200 px-3 py-1.5 text-xs">
          إلغاء
        </button>
      </div>
    </div>
  );
}

function LessonsTab({ topicId }) {
  const [lessons, setLessons] = useState([]);
  const [loading, setLoading] = useState(true);
  const [editing, setEditing] = useState(null); // lesson object | "new" | null
  const [error, setError] = useState("");

  const refresh = () => {
    setLoading(true);
    listTopicLessonsForTeacher(topicId)
      .then(setLessons)
      .catch(() => setError("تعذر تحميل الدروس"))
      .finally(() => setLoading(false));
  };

  useEffect(refresh, [topicId]);

  const handleDelete = async (lesson) => {
    if (!window.confirm(`حذف درس "${lesson.title_ar}"؟`)) return;
    try {
      await deleteLesson(lesson.id);
      refresh();
    } catch {
      setError("تعذر حذف الدرس");
    }
  };

  if (loading) return <p className="text-sm text-slate-400">...</p>;

  return (
    <div className="space-y-2">
      {error && <p className="text-xs text-red-600">{error}</p>}
      {editing === "new" ? (
        <LessonForm
          topicId={topicId}
          onCancel={() => setEditing(null)}
          onSaved={() => {
            setEditing(null);
            refresh();
          }}
        />
      ) : (
        <button
          onClick={() => setEditing("new")}
          className="w-full rounded-xl border border-dashed border-slate-300 py-2 text-sm text-slate-500 hover:bg-slate-50"
        >
          + درس جديد
        </button>
      )}

      {lessons.map((lesson) =>
        editing?.id === lesson.id ? (
          <LessonForm
            key={lesson.id}
            initial={lesson}
            topicId={topicId}
            onCancel={() => setEditing(null)}
            onSaved={() => {
              setEditing(null);
              refresh();
            }}
          />
        ) : (
          <div key={lesson.id} className="rounded-xl border border-slate-200 p-3 text-sm">
            <div className="flex items-center justify-between gap-2">
              <p className="font-medium text-slate-900">
                {!lesson.is_published && "🔸 "}
                {lesson.title_ar}
              </p>
              <div className="flex shrink-0 gap-1">
                <button
                  onClick={() => setEditing(lesson)}
                  className="rounded-lg border border-slate-200 px-2 py-1 text-xs hover:bg-slate-50"
                >
                  تعديل
                </button>
                <button
                  onClick={() => handleDelete(lesson)}
                  className="rounded-lg border border-red-200 px-2 py-1 text-xs text-red-600 hover:bg-red-50"
                >
                  حذف
                </button>
              </div>
            </div>
            <p className="mt-1 text-xs text-slate-400">
              {lesson.estimated_minutes} دقيقة · ترتيب {lesson.order_index}
              {!lesson.is_published && " · غير منشور"}
            </p>
          </div>
        )
      )}
    </div>
  );
}

// ---------------- الأسئلة ----------------

function QuestionForm({ initial, onCancel, onSaved, topicId }) {
  const [kind, setKind] = useState(initial?.kind || "mcq");
  const [promptAr, setPromptAr] = useState(initial?.prompt_ar || "");
  const [choices, setChoices] = useState(initial?.choices?.length ? initial.choices : ["", ""]);
  const [correctIndex, setCorrectIndex] = useState(initial?.kind === "mcq" ? initial.correct_answer : 0);
  const [correctBool, setCorrectBool] = useState(initial?.kind === "true_false" ? initial.correct_answer : true);
  const [correctNumeric, setCorrectNumeric] = useState(
    initial?.kind === "numeric" ? String(initial.correct_answer) : ""
  );
  const [tolerance, setTolerance] = useState(initial?.tolerance != null ? String(initial.tolerance) : "");
  const [correctTextList, setCorrectTextList] = useState(
    initial?.kind === "short_text" ? initial.correct_answer.join("\n") : ""
  );
  const [explanationAr, setExplanationAr] = useState(initial?.explanation_ar || "");
  const [difficulty, setDifficulty] = useState(initial?.difficulty ?? 1);
  const [isActive, setIsActive] = useState(initial?.is_active ?? true);
  const [showPreview, setShowPreview] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  const updateChoice = (i, value) => setChoices((prev) => prev.map((c, idx) => (idx === i ? value : c)));
  const addChoice = () => setChoices((prev) => (prev.length < 6 ? [...prev, ""] : prev));
  const removeChoice = (i) =>
    setChoices((prev) => (prev.length > 2 ? prev.filter((_, idx) => idx !== i) : prev));

  const handleSave = async () => {
    setError("");
    let correctAnswer;
    if (kind === "mcq") correctAnswer = correctIndex;
    else if (kind === "true_false") correctAnswer = correctBool;
    else if (kind === "numeric") correctAnswer = correctNumeric;
    else correctAnswer = correctTextList.split("\n").map((s) => s.trim()).filter(Boolean);

    const payload = {
      kind,
      prompt_ar: promptAr.trim(),
      choices: kind === "mcq" ? choices.map((c) => c.trim()) : null,
      correct_answer: correctAnswer,
      tolerance: kind === "numeric" && tolerance !== "" ? Number(tolerance) : null,
      explanation_ar: explanationAr.trim() || null,
      difficulty: Number(difficulty),
      is_active: isActive,
    };
    setSaving(true);
    try {
      const saved = initial
        ? await updateQuestion(initial.id, payload)
        : await createQuestion(topicId, payload);
      onSaved(saved);
    } catch (err) {
      setError(extractError(err, "تعذر حفظ السؤال"));
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="space-y-2 rounded-2xl border border-slate-300 bg-slate-50 p-3">
      {error && <p className="text-xs text-red-600">{error}</p>}
      <select
        value={kind}
        onChange={(e) => setKind(e.target.value)}
        className="w-full rounded-lg border border-slate-200 p-2 text-sm"
      >
        {Object.entries(KIND_LABELS).map(([value, label]) => (
          <option key={value} value={value}>
            {label}
          </option>
        ))}
      </select>
      <textarea
        value={promptAr}
        onChange={(e) => setPromptAr(e.target.value)}
        rows={2}
        placeholder="نص السؤال — الرياضيات بين $...$ (مثال: $x^2 + 1 = 5$)"
        className="w-full rounded-lg border border-slate-200 p-2 text-sm outline-none focus:border-slate-400"
      />

      {kind === "mcq" && (
        <div className="space-y-1.5">
          {choices.map((choice, i) => (
            <div key={i} className="flex items-center gap-2">
              <input
                type="radio"
                checked={correctIndex === i}
                onChange={() => setCorrectIndex(i)}
                className="accent-slate-900"
              />
              <input
                value={choice}
                onChange={(e) => updateChoice(i, e.target.value)}
                placeholder={`خيار ${i + 1}`}
                className="flex-1 rounded-lg border border-slate-200 p-1.5 text-sm"
              />
              {choices.length > 2 && (
                <button onClick={() => removeChoice(i)} className="text-xs text-red-500">
                  ✕
                </button>
              )}
            </div>
          ))}
          {choices.length < 6 && (
            <button onClick={addChoice} className="text-xs text-slate-500 hover:text-slate-700">
              + إضافة خيار
            </button>
          )}
          <p className="text-xs text-slate-400">حدّد الدائرة بجانب الخيار الصحيح</p>
        </div>
      )}

      {kind === "true_false" && (
        <div className="flex gap-3">
          <label className="flex items-center gap-1.5 text-sm">
            <input type="radio" checked={correctBool === true} onChange={() => setCorrectBool(true)} />
            صحيح
          </label>
          <label className="flex items-center gap-1.5 text-sm">
            <input type="radio" checked={correctBool === false} onChange={() => setCorrectBool(false)} />
            خطأ
          </label>
        </div>
      )}

      {kind === "numeric" && (
        <div className="flex gap-2">
          <input
            value={correctNumeric}
            onChange={(e) => setCorrectNumeric(e.target.value)}
            placeholder="الإجابة الصحيحة"
            className="flex-1 rounded-lg border border-slate-200 p-2 text-sm"
          />
          <input
            value={tolerance}
            onChange={(e) => setTolerance(e.target.value)}
            placeholder="هامش الخطأ (اختياري)"
            className="w-36 rounded-lg border border-slate-200 p-2 text-sm"
          />
        </div>
      )}

      {kind === "short_text" && (
        <textarea
          value={correctTextList}
          onChange={(e) => setCorrectTextList(e.target.value)}
          rows={2}
          placeholder="إجابة مقبولة في كل سطر"
          className="w-full rounded-lg border border-slate-200 p-2 text-sm"
        />
      )}

      <textarea
        value={explanationAr}
        onChange={(e) => setExplanationAr(e.target.value)}
        rows={2}
        placeholder="شرح الإجابة (اختياري، يظهر بعد التسليم)"
        className="w-full rounded-lg border border-slate-200 p-2 text-sm"
      />

      <button
        type="button"
        onClick={() => setShowPreview((v) => !v)}
        className="text-xs text-slate-500 hover:text-slate-700"
      >
        {showPreview ? "إخفاء المعاينة" : "👁 معاينة السؤال"}
      </button>
      {showPreview && (
        <div className="space-y-1.5 rounded-xl border border-slate-200 bg-white p-3 text-sm">
          <p className="font-medium text-slate-900">
            <MathText inline>{promptAr || "(نص السؤال)"}</MathText>
          </p>
          {kind === "mcq" &&
            choices.map((choice, i) => (
              <p
                key={i}
                className={`rounded-lg border px-2 py-1 ${
                  correctIndex === i ? "border-emerald-300 bg-emerald-50" : "border-slate-200"
                }`}
              >
                <MathText inline>{choice || `(خيار ${i + 1})`}</MathText>
              </p>
            ))}
          {explanationAr && (
            <p className="text-xs text-slate-500">
              الشرح: <MathText inline>{explanationAr}</MathText>
            </p>
          )}
        </div>
      )}

      <div className="flex flex-wrap items-center gap-3">
        <label className="flex items-center gap-1.5 text-xs text-slate-600">
          الصعوبة
          <select
            value={difficulty}
            onChange={(e) => setDifficulty(e.target.value)}
            className="rounded-lg border border-slate-200 p-1 text-sm"
          >
            <option value={1}>سهل</option>
            <option value={2}>متوسط</option>
            <option value={3}>صعب</option>
          </select>
        </label>
        <label className="flex items-center gap-1.5 text-xs text-slate-600">
          <input type="checkbox" checked={isActive} onChange={(e) => setIsActive(e.target.checked)} />
          نشط (يظهر بالاختبارات)
        </label>
      </div>

      <div className="flex gap-2">
        <button
          onClick={handleSave}
          disabled={saving || !promptAr.trim()}
          className="rounded-lg bg-slate-900 px-3 py-1.5 text-xs text-white hover:bg-slate-800 disabled:opacity-50"
        >
          {saving ? "..." : "حفظ"}
        </button>
        <button onClick={onCancel} className="rounded-lg border border-slate-200 px-3 py-1.5 text-xs">
          إلغاء
        </button>
      </div>
    </div>
  );
}

function QuestionsTab({ topicId }) {
  const [questions, setQuestions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [editing, setEditing] = useState(null);
  const [error, setError] = useState("");

  const refresh = () => {
    setLoading(true);
    listTopicQuestions(topicId)
      .then(setQuestions)
      .catch(() => setError("تعذر تحميل الأسئلة"))
      .finally(() => setLoading(false));
  };

  useEffect(refresh, [topicId]);

  const handleDelete = async (question) => {
    if (!window.confirm("حذف هذا السؤال؟")) return;
    try {
      await deleteQuestion(question.id);
      refresh();
    } catch {
      setError("تعذر حذف السؤال");
    }
  };

  if (loading) return <p className="text-sm text-slate-400">...</p>;

  return (
    <div className="space-y-2">
      {error && <p className="text-xs text-red-600">{error}</p>}
      {editing === "new" ? (
        <QuestionForm
          topicId={topicId}
          onCancel={() => setEditing(null)}
          onSaved={() => {
            setEditing(null);
            refresh();
          }}
        />
      ) : (
        <button
          onClick={() => setEditing("new")}
          className="w-full rounded-xl border border-dashed border-slate-300 py-2 text-sm text-slate-500 hover:bg-slate-50"
        >
          + سؤال جديد
        </button>
      )}

      {questions.map((question) =>
        editing?.id === question.id ? (
          <QuestionForm
            key={question.id}
            initial={question}
            topicId={topicId}
            onCancel={() => setEditing(null)}
            onSaved={() => {
              setEditing(null);
              refresh();
            }}
          />
        ) : (
          <div key={question.id} className="rounded-xl border border-slate-200 p-3 text-sm">
            <div className="flex items-start justify-between gap-2">
              <p className="text-slate-900">
                {!question.is_active && "🔸 "}
                <MathText inline>{question.prompt_ar}</MathText>
              </p>
              <div className="flex shrink-0 gap-1">
                <button
                  onClick={() => setEditing(question)}
                  className="rounded-lg border border-slate-200 px-2 py-1 text-xs hover:bg-slate-50"
                >
                  تعديل
                </button>
                <button
                  onClick={() => handleDelete(question)}
                  className="rounded-lg border border-red-200 px-2 py-1 text-xs text-red-600 hover:bg-red-50"
                >
                  حذف
                </button>
              </div>
            </div>
            <p className="mt-1 text-xs text-slate-400">
              {KIND_LABELS[question.kind]} · صعوبة {question.difficulty}
              {!question.is_active && " · غير نشط"}
            </p>
          </div>
        )
      )}
    </div>
  );
}

// ---------------- تحليلات الأسئلة ----------------

const FLAG_STYLES = {
  check_answer_key: "border-red-200 bg-red-50 text-red-700",
  harder_than_declared: "border-amber-200 bg-amber-50 text-amber-700",
  easier_than_declared: "border-sky-200 bg-sky-50 text-sky-700",
  ok: "border-emerald-200 bg-emerald-50 text-emerald-700",
  insufficient_data: "border-slate-200 bg-slate-50 text-slate-500",
};

function successBarColor(rate) {
  if (rate === null) return "bg-slate-200";
  if (rate >= 70) return "bg-emerald-500";
  if (rate >= 40) return "bg-amber-500";
  return "bg-red-500";
}

function AnalyticsTab({ topicId }) {
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    setLoading(true);
    setError("");
    getTopicAnalytics(topicId)
      .then(setRows)
      .catch(() => setError("تعذر تحميل التحليلات"))
      .finally(() => setLoading(false));
  }, [topicId]);

  if (loading) return <p className="text-sm text-slate-400">...</p>;
  if (error) return <p className="text-sm text-red-600">{error}</p>;

  const totalAnswers = rows.reduce((sum, r) => sum + r.answered, 0);
  const needReview = rows.filter((r) =>
    ["check_answer_key", "harder_than_declared", "easier_than_declared"].includes(r.flag)
  ).length;

  return (
    <div className="space-y-2">
      <div className="grid grid-cols-2 gap-2">
        <div className="rounded-xl border border-slate-200 p-3 text-center">
          <p className="text-xl font-semibold text-slate-900">{totalAnswers}</p>
          <p className="text-xs text-slate-500">إجابة مسجّلة</p>
        </div>
        <div className="rounded-xl border border-slate-200 p-3 text-center">
          <p className={`text-xl font-semibold ${needReview ? "text-amber-600" : "text-slate-900"}`}>
            {needReview}
          </p>
          <p className="text-xs text-slate-500">سؤال يحتاج مراجعة</p>
        </div>
      </div>
      <p className="text-xs text-slate-400">
        الأسئلة الأضعف أداءً أولًا. التحليل يحتاج 5 إجابات على الأقل لكل سؤال.
      </p>

      {rows.map((row) => (
        <div key={row.question_id} className="rounded-xl border border-slate-200 p-3 text-sm">
          <p className="text-slate-900">
            <MathText inline>{row.prompt_ar}</MathText>
          </p>

          <div className="mt-2 flex items-center gap-2">
            <div className="h-2 flex-1 overflow-hidden rounded-full bg-slate-100">
              <div
                className={`h-full rounded-full ${successBarColor(row.success_rate)}`}
                style={{ width: `${row.success_rate ?? 0}%` }}
              />
            </div>
            <span className="w-24 shrink-0 text-end text-xs text-slate-500">
              {row.success_rate === null ? "لا إجابات" : `${row.success_rate}% (${row.correct}/${row.answered})`}
            </span>
          </div>

          <div className="mt-2 flex flex-wrap items-center gap-2">
            <span className={`rounded-full border px-2 py-0.5 text-[11px] ${FLAG_STYLES[row.flag]}`}>
              {row.flag_label_ar}
            </span>
            <span className="text-[11px] text-slate-400">صعوبة {row.difficulty}</span>
          </div>

          {row.top_wrong_answer && (
            <p className="mt-2 text-xs text-slate-500">
              أكثر إجابة خاطئة ({row.top_wrong_count}×): <MathText inline>{row.top_wrong_answer}</MathText>
            </p>
          )}
        </div>
      ))}
    </div>
  );
}

// ---------------- اللوحة الرئيسية ----------------

export default function ContentManager({ onClose, initialTopicId }) {
  const [subjects, setSubjects] = useState([]);
  const [topicId, setTopicId] = useState(initialTopicId || null);
  const [tab, setTab] = useState("lessons");
  const [loadingSubjects, setLoadingSubjects] = useState(true);

  useEffect(() => {
    getSubjects()
      .then((data) => {
        setSubjects(data);
        if (!topicId && data[0]?.topics[0]) setTopicId(data[0].topics[0].id);
      })
      .finally(() => setLoadingSubjects(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 p-4">
      <div className="flex h-[85vh] w-full max-w-xl flex-col rounded-3xl border border-slate-200 bg-white shadow-lg">
        <div className="flex items-center justify-between border-b border-slate-200 p-4">
          <h2 className="text-lg font-semibold text-slate-900">إدارة المحتوى</h2>
          <button
            onClick={onClose}
            className="rounded-lg px-2 py-1 text-slate-400 hover:bg-slate-100 focus:outline-none focus:ring-2 focus:ring-slate-400"
          >
            ✕
          </button>
        </div>

        <div className="border-b border-slate-200 p-4 pb-3">
          {loadingSubjects ? (
            <p className="text-sm text-slate-400">...</p>
          ) : (
            <select
              value={topicId || ""}
              onChange={(e) => setTopicId(Number(e.target.value))}
              className="w-full rounded-xl border border-slate-200 p-2 text-sm"
            >
              {subjects.map((subject) => (
                <optgroup key={subject.id} label={subject.name_ar}>
                  {subject.topics.map((topic) => (
                    <option key={topic.id} value={topic.id}>
                      {topic.name_ar}
                    </option>
                  ))}
                </optgroup>
              ))}
            </select>
          )}

          <div className="mt-3 flex gap-2">
            {[
              ["lessons", "الدروس"],
              ["questions", "الأسئلة"],
              ["analytics", "التحليلات"],
            ].map(([id, label]) => (
              <button
                key={id}
                onClick={() => setTab(id)}
                className={`flex-1 rounded-xl border px-3 py-1.5 text-sm ${
                  tab === id ? "border-slate-900 bg-slate-900 text-white" : "border-slate-200"
                }`}
              >
                {label}
              </button>
            ))}
          </div>
        </div>

        <div className="flex-1 overflow-y-auto p-4">
          {topicId && tab === "lessons" && <LessonsTab topicId={topicId} />}
          {topicId && tab === "questions" && <QuestionsTab topicId={topicId} />}
          {topicId && tab === "analytics" && <AnalyticsTab topicId={topicId} />}
        </div>
      </div>
    </div>
  );
}
