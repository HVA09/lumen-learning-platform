import { useEffect, useState } from "react";
import { listClasses } from "../lib/classesApi";
import { getLeaderboard, getMyAchievements, getMyStats } from "../lib/gamificationApi";

const RANK_MEDALS = { 1: "🥇", 2: "🥈", 3: "🥉" };

export default function LeaderboardPanel({ onClose, isTeacher = true, isAdmin = false }) {
  const [tab, setTab] = useState(isTeacher ? "leaderboard" : "achievements");
  const [classes, setClasses] = useState([]);
  const [scope, setScope] = useState("");
  const [leaderboard, setLeaderboard] = useState([]);
  const [achievements, setAchievements] = useState([]);
  const [myStats, setMyStats] = useState(null);
  const [loadingBoard, setLoadingBoard] = useState(true);
  const [loadingAchievements, setLoadingAchievements] = useState(true);
  const [loadingStats, setLoadingStats] = useState(true);
  const [loadingClasses, setLoadingClasses] = useState(isTeacher);
  const [classesLoadFailed, setClassesLoadFailed] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    getMyAchievements()
      .then(setAchievements)
      .catch(() => setError("تعذر تحميل الإنجازات"))
      .finally(() => setLoadingAchievements(false));

    if (isTeacher) {
      listClasses()
        .then(setClasses)
        .catch(() => {
          setClassesLoadFailed(true);
          setError("تعذر تحميل الفصول");
        })
        .finally(() => setLoadingClasses(false));
    } else {
      getMyStats()
        .then(setMyStats)
        .catch(() => undefined)
        .finally(() => setLoadingStats(false));
    }
  }, [isTeacher]);

  const selectedScope = isAdmin ? scope : (scope || (classes[0]?.id ? String(classes[0].id) : ""));

  useEffect(() => {
    if (!isTeacher) {
      setLoadingBoard(false);
      return;
    }

    // Teachers may only request a class they teach. Only admins can request
    // the global leaderboard.
    const classId = isAdmin ? (scope || null) : selectedScope;
    if (!isAdmin && !classId) {
      setLeaderboard([]);
      setLoadingBoard(false);
      return;
    }

    setLoadingBoard(true);
    setError("");
    getLeaderboard(classId)
      .then(setLeaderboard)
      .catch((err) => {
        setLeaderboard([]);
        setError(err.response?.data?.detail || "تعذر تحميل لوحة المتصدرين");
      })
      .finally(() => setLoadingBoard(false));
  }, [isTeacher, isAdmin, selectedScope]);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center overflow-y-auto bg-black/30 p-4">
      <div className="my-8 w-full max-w-md rounded-3xl border border-slate-200 bg-white p-6 shadow-lg">
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-lg font-semibold text-slate-900">{isTeacher ? "التحفيز" : "إنجازاتي وتقدّمي"}</h2>
          <button
            onClick={onClose}
            className="rounded-lg px-2 py-1 text-slate-400 hover:bg-slate-100 focus:outline-none focus:ring-2 focus:ring-slate-400"
          >
            ✕
          </button>
        </div>

        {isTeacher && (
          <div className="mb-4 flex gap-2">
            <button
              onClick={() => setTab("leaderboard")}
              className={`flex-1 rounded-xl border px-3 py-1.5 text-sm ${tab === "leaderboard" ? "border-slate-900 bg-slate-900 text-white" : "border-slate-200"}`}
            >
              لوحة المتصدرين
            </button>
            <button
              onClick={() => setTab("achievements")}
              className={`flex-1 rounded-xl border px-3 py-1.5 text-sm ${tab === "achievements" ? "border-slate-900 bg-slate-900 text-white" : "border-slate-200"}`}
            >
              إنجازاتي
            </button>
          </div>
        )}

        {error && <p className="mb-3 text-sm text-red-600">{error}</p>}

        {!isTeacher && (
          <section className="mb-4 rounded-2xl border border-slate-200 p-4" aria-label="إحصائياتي الشخصية">
            <h3 className="mb-3 text-sm font-semibold text-slate-900">تقدّمي الشخصي</h3>
            {loadingStats ? (
              <p className="text-sm text-slate-400">...</p>
            ) : myStats ? (
              <div className="grid grid-cols-2 gap-3 text-center">
                <div>
                  <p className="text-xl font-semibold text-slate-900">{myStats.score}</p>
                  <p className="text-xs text-slate-500">نقاطي</p>
                </div>
                <div>
                  <p className="text-xl font-semibold text-slate-900">{myStats.streak_days} 🔥</p>
                  <p className="text-xs text-slate-500">أيام الدراسة المتتالية</p>
                </div>
                <p className="col-span-2 text-xs text-slate-500">
                  {myStats.studied_today ? "أنجزت نشاطاً دراسياً اليوم" : "لم تسجل نشاطاً دراسياً اليوم بعد"}
                </p>
              </div>
            ) : (
              <p className="text-sm text-slate-400">تعذر تحميل تقدمك الشخصي</p>
            )}
          </section>
        )}

        {isTeacher && tab === "leaderboard" ? (
          <>
            {classes.length > 0 && (
              <select
                aria-label="اختر الفصل"
                value={selectedScope}
                onChange={(e) => setScope(e.target.value)}
                className="mb-3 w-full rounded-xl border border-slate-200 bg-white p-2 text-sm"
              >
                {isAdmin && <option value="">كل المنصة</option>}
                {classes.map((c) => (
                  <option key={c.id} value={c.id}>
                    فصل: {c.name}
                  </option>
                ))}
              </select>
            )}
            {!isAdmin && loadingClasses ? (
              <p className="text-sm text-slate-400">...</p>
            ) : !isAdmin && classesLoadFailed ? (
              <p role="alert" className="text-sm text-red-600">تعذر تحميل قائمة الفصول، حاول مرة أخرى</p>
            ) : !isAdmin && classes.length === 0 ? (
              <p className="text-sm text-slate-500">لا توجد فصول مرتبطة بحسابك لعرض لوحاتها</p>
            ) : loadingBoard ? (
              <p className="text-sm text-slate-400">...</p>
            ) : leaderboard.length === 0 ? (
              <p className="text-sm text-slate-400">لا توجد نقاط بعد — أنجز اختبارًا أو درسًا لتظهر هنا</p>
            ) : (
              <div className="space-y-2">
                {leaderboard.map((entry) => (
                  <div
                    key={entry.user_id}
                    className={`flex items-center justify-between rounded-xl border px-3 py-2 ${
                      entry.is_me ? "border-slate-900 bg-slate-50" : "border-slate-200"
                    }`}
                  >
                    <span className="text-sm text-slate-900">
                      {RANK_MEDALS[entry.rank] || `#${entry.rank}`} {entry.display_name}
                      {entry.is_me && " (أنت)"}
                    </span>
                    <span className="text-sm font-medium text-slate-600">{entry.score} نقطة</span>
                  </div>
                ))}
              </div>
            )}
          </>
        ) : loadingAchievements ? (
          <p className="text-sm text-slate-400">...</p>
        ) : (
          <div className="space-y-2">
            {achievements.map((a) => (
              <div
                key={a.key}
                className={`rounded-xl border p-3 ${
                  a.unlocked_at ? "border-emerald-200 bg-emerald-50" : "border-slate-200 opacity-50"
                }`}
              >
                <p className="text-sm font-medium text-slate-900">
                  {a.unlocked_at ? "🏆" : "🔒"} {a.title_ar}
                </p>
                <p className="text-xs text-slate-500">{a.description_ar}</p>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
