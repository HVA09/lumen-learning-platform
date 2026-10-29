import { useEffect, useState } from "react";
import { listClasses } from "../lib/classesApi";
import { getLeaderboard, getMyAchievements } from "../lib/gamificationApi";

const RANK_MEDALS = { 1: "🥇", 2: "🥈", 3: "🥉" };

export default function LeaderboardPanel({ onClose }) {
  const [tab, setTab] = useState("leaderboard");
  const [classes, setClasses] = useState([]);
  const [scope, setScope] = useState(""); // "" = كل المنصة، وإلا رقم الفصل
  const [leaderboard, setLeaderboard] = useState([]);
  const [achievements, setAchievements] = useState([]);
  const [loadingBoard, setLoadingBoard] = useState(true);
  const [loadingOther, setLoadingOther] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    Promise.all([listClasses(), getMyAchievements()])
      .then(([classesData, achievementsData]) => {
        setClasses(classesData);
        setAchievements(achievementsData);
      })
      .catch(() => setError("تعذر تحميل البيانات"))
      .finally(() => setLoadingOther(false));
  }, []);

  useEffect(() => {
    setLoadingBoard(true);
    setError("");
    getLeaderboard(scope || null)
      .then(setLeaderboard)
      .catch((err) => {
        setLeaderboard([]);
        setError(err.response?.data?.detail || "تعذر تحميل لوحة المتصدرين");
      })
      .finally(() => setLoadingBoard(false));
  }, [scope]);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center overflow-y-auto bg-black/30 p-4">
      <div className="my-8 w-full max-w-md rounded-3xl border border-slate-200 bg-white p-6 shadow-lg">
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-lg font-semibold text-slate-900">التحفيز</h2>
          <button
            onClick={onClose}
            className="rounded-lg px-2 py-1 text-slate-400 hover:bg-slate-100 focus:outline-none focus:ring-2 focus:ring-slate-400"
          >
            ✕
          </button>
        </div>

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

        {error && <p className="mb-3 text-sm text-red-600">{error}</p>}

        {tab === "leaderboard" ? (
          <>
            {classes.length > 0 && (
              <select
                value={scope}
                onChange={(e) => setScope(e.target.value)}
                className="mb-3 w-full rounded-xl border border-slate-200 bg-white p-2 text-sm"
              >
                <option value="">كل المنصة</option>
                {classes.map((c) => (
                  <option key={c.id} value={c.id}>
                    فصل: {c.name}
                  </option>
                ))}
              </select>
            )}
            {loadingBoard ? (
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
        ) : loadingOther ? (
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
