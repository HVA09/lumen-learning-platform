import { useEffect, useState } from "react";
import {
  createClass,
  deleteClass,
  getClassDetail,
  joinClass,
  listClasses,
  regenerateInviteCode,
  removeStudentFromClass,
  renameClass,
} from "../lib/classesApi";

function extractError(err, fallback) {
  const detail = err.response?.data?.detail;
  return typeof detail === "string" ? detail : fallback;
}

function InviteCode({ code }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(code);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      // المتصفح رفض النسخ (مثلاً بدون HTTPS) — الرمز ظاهر ويقدر ينسخه يدويًا
    }
  };

  return (
    <button
      onClick={handleCopy}
      title="اضغط للنسخ"
      className="rounded-lg border border-dashed border-slate-300 bg-slate-50 px-3 py-1.5 font-mono text-base tracking-widest text-slate-900 hover:bg-slate-100"
      dir="ltr"
    >
      {code} <span className="text-xs tracking-normal text-slate-400">{copied ? "✓ نُسخ" : "نسخ"}</span>
    </button>
  );
}

function ClassRoster({ classId, onBack, onChanged }) {
  const [detail, setDetail] = useState(null);
  const [name, setName] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const refresh = () =>
    getClassDetail(classId)
      .then((data) => {
        setDetail(data);
        setName(data.name);
      })
      .catch((err) => setError(extractError(err, "تعذر تحميل الفصل")));

  useEffect(() => {
    refresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [classId]);

  const run = async (action, fallback) => {
    setBusy(true);
    setError("");
    try {
      await action();
      await refresh();
      onChanged();
    } catch (err) {
      setError(extractError(err, fallback));
    } finally {
      setBusy(false);
    }
  };

  if (!detail) return <p className="text-sm text-slate-400">{error || "..."}</p>;

  return (
    <div>
      <button onClick={onBack} className="mb-3 text-sm text-slate-500 hover:text-slate-700">
        ← رجوع للفصول
      </button>
      {error && <p className="mb-2 text-sm text-red-600">{error}</p>}

      <div className="mb-3 flex gap-2">
        <input
          value={name}
          onChange={(e) => setName(e.target.value)}
          className="flex-1 rounded-xl border border-slate-200 p-2 text-sm"
        />
        <button
          onClick={() => run(() => renameClass(classId, name.trim()), "تعذر إعادة التسمية")}
          disabled={busy || !name.trim() || name.trim() === detail.name}
          className="rounded-xl border border-slate-200 px-3 py-2 text-sm hover:bg-slate-50 disabled:opacity-50"
        >
          حفظ الاسم
        </button>
      </div>

      <div className="mb-4 rounded-2xl border border-slate-200 p-3">
        <p className="mb-2 text-xs text-slate-500">رمز الانضمام — شاركه مع طلابك</p>
        <div className="flex flex-wrap items-center gap-2">
          <InviteCode code={detail.invite_code} />
          <button
            onClick={() => {
              if (window.confirm("الرمز القديم سيتوقف عن العمل. متأكد؟")) {
                run(() => regenerateInviteCode(classId), "تعذر تجديد الرمز");
              }
            }}
            disabled={busy}
            className="rounded-lg border border-slate-200 px-2 py-1 text-xs text-slate-600 hover:bg-slate-50 disabled:opacity-50"
          >
            تجديد الرمز
          </button>
        </div>
      </div>

      <p className="mb-2 text-sm font-medium text-slate-900">الطلاب ({detail.students.length})</p>
      {detail.students.length === 0 ? (
        <p className="text-sm text-slate-400">ما انضمّ أحد بعد — شارك الرمز أعلاه</p>
      ) : (
        <div className="space-y-2">
          {detail.students.map((student) => (
            <div
              key={student.user_id}
              className="flex items-center justify-between gap-2 rounded-xl border border-slate-200 px-3 py-2 text-sm"
            >
              <div className="min-w-0">
                <p className="truncate text-slate-900">{student.display_name}</p>
                <p className="truncate text-xs text-slate-400">{student.email}</p>
              </div>
              <div className="flex shrink-0 items-center gap-2">
                <span
                  className={`rounded-full px-2 py-0.5 text-xs ${
                    student.average_mastery >= 70
                      ? "bg-emerald-50 text-emerald-700"
                      : student.average_mastery >= 40
                      ? "bg-amber-50 text-amber-700"
                      : "bg-red-50 text-red-600"
                  }`}
                  title="متوسط الإتقان"
                >
                  {Math.round(student.average_mastery)}%
                </span>
                <button
                  onClick={() => {
                    if (window.confirm(`إزالة ${student.display_name} من الفصل؟`)) {
                      run(() => removeStudentFromClass(classId, student.user_id), "تعذر إزالة الطالب");
                    }
                  }}
                  disabled={busy}
                  className="rounded-lg border border-red-200 px-2 py-1 text-xs text-red-600 hover:bg-red-50 disabled:opacity-50"
                >
                  إزالة
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      <button
        onClick={async () => {
          if (!window.confirm("حذف الفصل يحذف واجباته وتسليماتها أيضًا. متأكد؟")) return;
          setBusy(true);
          setError("");
          try {
            await deleteClass(classId);
            onChanged();
            onBack();
          } catch (err) {
            setError(extractError(err, "تعذر حذف الفصل"));
            setBusy(false);
          }
        }}
        disabled={busy}
        className="mt-5 w-full rounded-xl border border-red-200 px-3 py-2 text-sm text-red-600 hover:bg-red-50 disabled:opacity-50"
      >
        حذف الفصل
      </button>
    </div>
  );
}

export default function ClassesPanel({ onClose, isTeacher }) {
  const [classes, setClasses] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedId, setSelectedId] = useState(null);
  const [newName, setNewName] = useState("");
  const [code, setCode] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  const refresh = () =>
    listClasses()
      .then(setClasses)
      .catch(() => setError("تعذر تحميل الفصول"))
      .finally(() => setLoading(false));

  useEffect(() => {
    refresh();
  }, []);

  const handleCreate = async () => {
    setBusy(true);
    setError("");
    try {
      await createClass(newName.trim());
      setNewName("");
      await refresh();
    } catch (err) {
      setError(extractError(err, "تعذر إنشاء الفصل"));
    } finally {
      setBusy(false);
    }
  };

  const handleJoin = async () => {
    setBusy(true);
    setError("");
    setNotice("");
    try {
      const joined = await joinClass(code);
      setCode("");
      setNotice(`انضممت إلى فصل «${joined.name}»`);
      await refresh();
    } catch (err) {
      setError(extractError(err, "تعذر الانضمام"));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center overflow-y-auto bg-black/30 p-4">
      <div className="my-8 w-full max-w-md rounded-3xl border border-slate-200 bg-white p-6 shadow-lg">
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-lg font-semibold text-slate-900">الفصول</h2>
          <button
            onClick={onClose}
            className="rounded-lg px-2 py-1 text-slate-400 hover:bg-slate-100 focus:outline-none focus:ring-2 focus:ring-slate-400"
          >
            ✕
          </button>
        </div>

        {selectedId ? (
          <ClassRoster
            classId={selectedId}
            onBack={() => setSelectedId(null)}
            onChanged={refresh}
          />
        ) : (
          <>
            {error && <p className="mb-2 text-sm text-red-600">{error}</p>}
            {notice && <p className="mb-2 text-sm text-emerald-700">{notice}</p>}

            {isTeacher ? (
              <div className="mb-4 flex gap-2">
                <input
                  value={newName}
                  onChange={(e) => setNewName(e.target.value)}
                  placeholder="اسم الفصل الجديد (مثلاً: رياضيات — الصف العاشر)"
                  className="flex-1 rounded-xl border border-slate-200 p-2 text-sm"
                />
                <button
                  onClick={handleCreate}
                  disabled={busy || !newName.trim()}
                  className="rounded-xl bg-slate-900 px-3 py-2 text-sm text-white hover:bg-slate-800 disabled:opacity-50"
                >
                  إنشاء
                </button>
              </div>
            ) : (
              <div className="mb-4 flex gap-2">
                <input
                  value={code}
                  onChange={(e) => setCode(e.target.value)}
                  placeholder="رمز الانضمام من معلّمك"
                  maxLength={12}
                  dir="ltr"
                  className="flex-1 rounded-xl border border-slate-200 p-2 text-sm uppercase tracking-widest"
                />
                <button
                  onClick={handleJoin}
                  disabled={busy || !code.trim()}
                  className="rounded-xl bg-slate-900 px-3 py-2 text-sm text-white hover:bg-slate-800 disabled:opacity-50"
                >
                  انضمام
                </button>
              </div>
            )}

            {loading ? (
              <p className="text-sm text-slate-400">...</p>
            ) : classes.length === 0 ? (
              <p className="text-sm text-slate-400">
                {isTeacher ? "ما أنشأت فصولًا بعد" : "ما انضممت لأي فصل بعد — اطلب الرمز من معلّمك"}
              </p>
            ) : (
              <div className="space-y-2">
                {classes.map((c) => (
                  <div
                    key={c.id}
                    className="flex items-center justify-between gap-2 rounded-2xl border border-slate-200 p-3"
                  >
                    <div className="min-w-0">
                      <p className="truncate font-medium text-slate-900">{c.name}</p>
                      <p className="text-xs text-slate-400">{c.student_count} طالب</p>
                    </div>
                    {isTeacher ? (
                      <div className="flex shrink-0 items-center gap-2">
                        <InviteCode code={c.invite_code} />
                        <button
                          onClick={() => setSelectedId(c.id)}
                          className="rounded-lg border border-slate-200 px-3 py-1.5 text-xs hover:bg-slate-50"
                        >
                          إدارة
                        </button>
                      </div>
                    ) : null}
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
