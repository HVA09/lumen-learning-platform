import { useEffect, useState } from "react";
import {
  createAssignment,
  deleteAssignment,
  getAssignments,
  getMySubmission,
  gradeSubmission,
  listSubmissions,
  submitAssignment,
} from "../lib/assignmentsApi";
import { listClasses } from "../lib/classesApi";
import MathText from "./MathText";

const STATUS_LABELS = {
  submitted: "بانتظار تقييم المعلّم",
  graded: "تم التقييم",
};

function NewAssignmentForm({ onCancel, onCreated, classes }) {
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [rubricText, setRubricText] = useState("");
  const [dueAt, setDueAt] = useState("");
  const [classId, setClassId] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  const handleCreate = async () => {
    setError("");
    setSaving(true);
    try {
      const created = await createAssignment({
        title: title.trim(),
        description: description.trim(),
        rubric_criteria: rubricText.split("\n").map((s) => s.trim()).filter(Boolean),
        due_at: dueAt ? new Date(dueAt).toISOString() : null,
        class_section_id: classId ? Number(classId) : null,
      });
      onCreated(created);
    } catch (err) {
      setError(err.response?.data?.detail || "تعذر إنشاء الواجب");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="space-y-2 rounded-2xl border border-slate-300 bg-slate-50 p-3">
      {error && <p className="text-xs text-red-600">{error}</p>}
      <input
        value={title}
        onChange={(e) => setTitle(e.target.value)}
        placeholder="عنوان الواجب"
        className="w-full rounded-lg border border-slate-200 p-2 text-sm"
      />
      <textarea
        value={description}
        onChange={(e) => setDescription(e.target.value)}
        rows={3}
        placeholder="وصف الواجب والمطلوب من الطالب"
        className="w-full rounded-lg border border-slate-200 p-2 text-sm"
      />
      <textarea
        value={rubricText}
        onChange={(e) => setRubricText(e.target.value)}
        rows={2}
        placeholder="معايير التقييم (كل معيار بسطر، اختياري)"
        className="w-full rounded-lg border border-slate-200 p-2 text-sm"
      />
      <label className="flex items-center gap-2 text-xs text-slate-600">
        موجَّه إلى
        <select
          value={classId}
          onChange={(e) => setClassId(e.target.value)}
          className="flex-1 rounded-lg border border-slate-200 p-1.5 text-sm"
        >
          <option value="">كل الطلاب (عام)</option>
          {classes.map((c) => (
            <option key={c.id} value={c.id}>
              فصل: {c.name}
            </option>
          ))}
        </select>
      </label>
      <label className="flex items-center gap-2 text-xs text-slate-600">
        الموعد النهائي (اختياري)
        <input
          type="datetime-local"
          value={dueAt}
          onChange={(e) => setDueAt(e.target.value)}
          className="rounded-lg border border-slate-200 p-1.5 text-sm"
        />
      </label>
      <div className="flex gap-2">
        <button
          onClick={handleCreate}
          disabled={saving || !title.trim() || !description.trim()}
          className="rounded-lg bg-slate-900 px-3 py-1.5 text-xs text-white hover:bg-slate-800 disabled:opacity-50"
        >
          {saving ? "..." : "إنشاء الواجب"}
        </button>
        <button onClick={onCancel} className="rounded-lg border border-slate-200 px-3 py-1.5 text-xs">
          إلغاء
        </button>
      </div>
    </div>
  );
}

function GradeForm({ submission, onGraded }) {
  const [grade, setGrade] = useState(submission.grade_percentage ?? 80);
  const [feedback, setFeedback] = useState(submission.feedback ?? "");
  const [saving, setSaving] = useState(false);

  const handleGrade = async () => {
    setSaving(true);
    try {
      onGraded(await gradeSubmission(submission.assignment_id, submission.id, Number(grade), feedback.trim()));
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="mt-2 space-y-2 rounded-xl border border-slate-200 bg-white p-2">
      <div className="flex items-center gap-2">
        <input
          type="number"
          min={0}
          max={100}
          value={grade}
          onChange={(e) => setGrade(e.target.value)}
          className="w-20 rounded-lg border border-slate-200 p-1.5 text-sm"
        />
        <span className="text-xs text-slate-500">%</span>
      </div>
      <textarea
        value={feedback}
        onChange={(e) => setFeedback(e.target.value)}
        rows={2}
        placeholder="ملاحظات للطالب (اختياري)"
        className="w-full rounded-lg border border-slate-200 p-2 text-sm"
      />
      <button
        onClick={handleGrade}
        disabled={saving}
        className="rounded-lg bg-slate-900 px-3 py-1.5 text-xs text-white hover:bg-slate-800 disabled:opacity-50"
      >
        {saving ? "..." : submission.status === "graded" ? "تحديث التقييم" : "حفظ التقييم"}
      </button>
    </div>
  );
}

function TeacherSubmissions({ assignment, onBack }) {
  const [submissions, setSubmissions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [gradingId, setGradingId] = useState(null);

  const refresh = () => {
    setLoading(true);
    listSubmissions(assignment.id)
      .then(setSubmissions)
      .finally(() => setLoading(false));
  };

  useEffect(refresh, [assignment.id]);

  return (
    <div>
      <button onClick={onBack} className="mb-3 text-sm text-slate-500 hover:text-slate-700">
        ← رجوع
      </button>
      <h3 className="mb-3 font-semibold text-slate-900">{assignment.title} — التسليمات</h3>
      {loading ? (
        <p className="text-sm text-slate-400">...</p>
      ) : submissions.length === 0 ? (
        <p className="text-sm text-slate-400">ما فيه تسليمات بعد</p>
      ) : (
        <div className="space-y-2">
          {submissions.map((s) => (
            <div key={s.id} className="rounded-xl border border-slate-200 p-3 text-sm">
              <div className="flex items-center justify-between">
                <p className="font-medium text-slate-900">{s.student_name}</p>
                <span className="text-xs text-slate-400">
                  {s.status === "graded" ? `${Math.round(s.grade_percentage)}%` : STATUS_LABELS[s.status]}
                  {s.is_late && " · متأخر"}
                </span>
              </div>
              <p className="mt-1 whitespace-pre-line text-slate-600">{s.written_answer}</p>
              {gradingId === s.id ? (
                <GradeForm
                  submission={{ ...s, assignment_id: assignment.id }}
                  onGraded={(updated) => {
                    setSubmissions((prev) => prev.map((x) => (x.id === updated.id ? updated : x)));
                    setGradingId(null);
                  }}
                />
              ) : (
                <button
                  onClick={() => setGradingId(s.id)}
                  className="mt-2 rounded-lg border border-slate-200 px-3 py-1 text-xs hover:bg-slate-50"
                >
                  {s.status === "graded" ? "تعديل التقييم" : "قيّم الآن"}
                </button>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function TeacherReadOnlyAssignment({ assignment, onBack }) {
  return (
    <div>
      <button onClick={onBack} className="mb-3 text-sm text-slate-500 hover:text-slate-700">
        ← رجوع
      </button>
      <h3 className="mb-2 font-semibold text-slate-900">{assignment.title}</h3>
      <MathText className="mb-3 whitespace-pre-line text-sm text-slate-600">
        {assignment.description}
      </MathText>
      <p className="rounded-xl border border-slate-200 bg-slate-50 p-3 text-sm text-slate-600">
        هذا واجب عام أنشأه معلّم آخر. يمكنك الاطلاع على تفاصيله، لكن لا تملك صلاحية إدارة تسليماته أو تقييم الطلاب.
      </p>
    </div>
  );
}

function StudentAssignment({ assignment, onBack }) {
  const [submission, setSubmission] = useState(null);
  const [answer, setAnswer] = useState("");
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    getMySubmission(assignment.id)
      .then((data) => {
        setSubmission(data);
        if (data?.written_answer) setAnswer(data.written_answer);
      })
      .finally(() => setLoading(false));
  }, [assignment.id]);

  const handleSubmit = async () => {
    if (!answer.trim()) return;
    setSubmitting(true);
    try {
      setSubmission(await submitAssignment(assignment.id, answer.trim()));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div>
      <button onClick={onBack} className="mb-3 text-sm text-slate-500 hover:text-slate-700">
        ← رجوع
      </button>
      <h3 className="mb-1 font-semibold text-slate-900">{assignment.title}</h3>
      <MathText className="mb-3 whitespace-pre-line text-sm text-slate-600">{assignment.description}</MathText>
      {assignment.rubric_criteria?.length > 0 && (
        <ul className="mb-3 list-inside list-disc text-xs text-slate-500">
          {assignment.rubric_criteria.map((c) => (
            <li key={c}>
              <MathText inline>{c}</MathText>
            </li>
          ))}
        </ul>
      )}

      {loading ? (
        <p className="text-sm text-slate-400">...</p>
      ) : submission?.status === "graded" ? (
        <div className="rounded-2xl border border-emerald-200 bg-emerald-50 p-4">
          <p className="text-sm font-medium text-emerald-800">
            النتيجة: {Math.round(submission.grade_percentage)}%
          </p>
          {submission.feedback && <p className="mt-1 text-sm text-emerald-700">{submission.feedback}</p>}
        </div>
      ) : (
        <>
          {submission?.status === "submitted" && (
            <p className="mb-2 rounded-xl border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-700">
              {STATUS_LABELS.submitted}{submission.is_late && " · سُلِّم متأخرًا"}
            </p>
          )}
          <textarea
            value={answer}
            onChange={(e) => setAnswer(e.target.value)}
            rows={5}
            placeholder="اكتب إجابتك وشرحك هنا..."
            className="w-full rounded-xl border border-slate-200 bg-slate-50 p-3 text-sm outline-none focus:border-slate-400 focus:ring-2 focus:ring-slate-400"
          />
          <button
            onClick={handleSubmit}
            disabled={submitting || !answer.trim()}
            className="mt-3 w-full rounded-xl bg-slate-900 px-4 py-2 text-sm text-white hover:bg-slate-800 disabled:opacity-50"
          >
            {submitting ? "..." : submission ? "تحديث الإجابة" : "سلّم الإجابة"}
          </button>
        </>
      )}
    </div>
  );
}

export default function AssignmentsPanel({ onClose, isTeacher }) {
  const [assignments, setAssignments] = useState([]);
  const [selected, setSelected] = useState(null);
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [classes, setClasses] = useState([]);
  const classNames = Object.fromEntries(classes.map((c) => [c.id, c.name]));

  useEffect(() => {
    listClasses()
      .then(setClasses)
      .catch(() => {}); // فشل تحميل أسماء الفصول لا يمنع عرض الواجبات
  }, []);

  const refresh = () => {
    setLoading(true);
    getAssignments()
      .then(setAssignments)
      .finally(() => setLoading(false));
  };

  useEffect(refresh, []);

  const handleDelete = async (assignment) => {
    if (!window.confirm(`حذف واجب "${assignment.title}"؟`)) return;
    await deleteAssignment(assignment.id);
    refresh();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center overflow-y-auto bg-black/30 p-4">
      <div className="my-8 w-full max-w-lg rounded-3xl border border-slate-200 bg-white p-6 shadow-lg">
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-lg font-semibold text-slate-900">الواجبات</h2>
          <button
            onClick={onClose}
            className="rounded-lg px-2 py-1 text-slate-400 hover:bg-slate-100 focus:outline-none focus:ring-2 focus:ring-slate-400"
          >
            ✕
          </button>
        </div>

        {selected ? (
          isTeacher ? (
            selected.can_manage ? (
              <TeacherSubmissions assignment={selected} onBack={() => setSelected(null)} />
            ) : (
              <TeacherReadOnlyAssignment assignment={selected} onBack={() => setSelected(null)} />
            )
          ) : (
            <StudentAssignment assignment={selected} onBack={() => setSelected(null)} />
          )
        ) : (
          <>
            {isTeacher &&
              (creating ? (
                <div className="mb-3">
                  <NewAssignmentForm
                    classes={classes}
                    onCancel={() => setCreating(false)}
                    onCreated={() => {
                      setCreating(false);
                      refresh();
                    }}
                  />
                </div>
              ) : (
                <button
                  onClick={() => setCreating(true)}
                  className="mb-3 w-full rounded-xl border border-dashed border-slate-300 py-2 text-sm text-slate-500 hover:bg-slate-50"
                >
                  + واجب جديد
                </button>
              ))}

            {loading ? (
              <p className="text-sm text-slate-400">...</p>
            ) : assignments.length === 0 ? (
              <p className="text-sm text-slate-400">ما فيه واجبات حاليًا</p>
            ) : (
              <div className="space-y-2">
                {assignments.map((a) => (
                  <div key={a.id} className="rounded-2xl border border-slate-200 p-3">
                    <button onClick={() => setSelected(a)} className="w-full text-start">
                      <p className="font-medium text-slate-900">
                        {a.title}
                        {a.class_section_id && (
                          <span className="ms-2 rounded-full bg-slate-100 px-2 py-0.5 text-[10px] font-normal text-slate-500">
                            {classNames[a.class_section_id] || "فصل"}
                          </span>
                        )}
                      </p>
                      <div className="mt-1 flex flex-wrap items-center gap-x-3 text-xs text-slate-400">
                        {a.due_at && <span>الموعد النهائي: {new Date(a.due_at).toLocaleDateString()}</span>}
                        {isTeacher && a.can_manage ? (
                          <span>{a.submissions_count} تسليم · {a.pending_grading_count} بانتظار التقييم</span>
                        ) : (
                          a.my_status && (
                            <span>
                              {a.my_status === "graded"
                                ? `النتيجة: ${Math.round(a.my_grade_percentage)}%`
                                : STATUS_LABELS[a.my_status]}
                            </span>
                          )
                        )}
                      </div>
                    </button>
                    {isTeacher && a.can_manage && (
                      <button
                        onClick={() => handleDelete(a)}
                        className="mt-2 rounded-lg border border-red-200 px-2 py-1 text-xs text-red-600 hover:bg-red-50"
                      >
                        حذف الواجب
                      </button>
                    )}
                  </div>
                ))}
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
