import { useEffect, useState } from "react";
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import {
  getAdminStats,
  getDailyAnalytics,
  downloadAnalyticsCsv,
  listAllUsers,
  updateUser,
  deleteUser,
  listAuditLogs,
} from "../lib/adminApi";
import LTIManagementTab from "./LTIManagementTab";

const TABS = [
  { id: "stats", label: "الإحصائيات" },
  { id: "users", label: "المستخدمون" },
  { id: "logs", label: "السجل" },
  { id: "lti", label: "تكامل LMS" },
];

const ROLE_LABELS = { user: "طالب", teacher: "معلّم", admin: "admin" };

function formatSize(bytes) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function StatsTab() {
  const [stats, setStats] = useState(null);
  const [daily, setDaily] = useState([]);
  const [error, setError] = useState("");
  const [exporting, setExporting] = useState(false);

  useEffect(() => {
    Promise.all([getAdminStats(), getDailyAnalytics(30)])
      .then(([statsData, dailyData]) => {
        setStats(statsData);
        setDaily(dailyData.map((p) => ({ ...p, dateLabel: p.date.slice(5) })));
      })
      .catch(() => setError("تعذر تحميل الإحصائيات"));
  }, []);

  const handleExport = async () => {
    setExporting(true);
    try {
      await downloadAnalyticsCsv(30);
    } catch {
      setError("تعذر تصدير الملف");
    } finally {
      setExporting(false);
    }
  };

  if (error) return <p className="text-sm text-red-600">{error}</p>;
  if (!stats) return <p className="text-sm text-slate-400">...</p>;

  const cards = [
    ["الطلاب", stats.total_students],
    ["المعلّمون", stats.total_teachers],
    ["الدروس", stats.total_lessons],
    ["الأسئلة", stats.total_questions],
    ["محاولات اختبار", stats.total_quiz_attempts],
    ["الواجبات", stats.total_assignments],
    ["التسليمات", stats.total_submissions],
    ["مساحة التخزين", formatSize(stats.storage_used_bytes)],
  ];

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
        {cards.map(([label, value]) => (
          <div key={label} className="rounded-2xl border border-slate-200 p-4 text-center">
            <p className="text-2xl font-semibold text-slate-900">{value}</p>
            <p className="mt-1 text-xs text-slate-500">{label}</p>
          </div>
        ))}
      </div>

      <div className="flex items-center justify-between">
        <p className="text-sm font-medium text-slate-900">آخر 30 يوم</p>
        <button
          onClick={handleExport}
          disabled={exporting}
          className="rounded-lg border border-slate-200 px-3 py-1.5 text-xs hover:bg-slate-50 disabled:opacity-50"
        >
          {exporting ? "..." : "تصدير CSV"}
        </button>
      </div>

      <div>
        <p className="mb-2 text-xs text-slate-500">مستخدمون جدد ومحاولات اختبار</p>
        <ResponsiveContainer width="100%" height={180}>
          <LineChart data={daily}>
            <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
            <XAxis dataKey="dateLabel" tick={{ fontSize: 10 }} />
            <YAxis tick={{ fontSize: 10 }} allowDecimals={false} />
            <Tooltip />
            <Line type="monotone" dataKey="new_users" name="مستخدمون" stroke="#0f172a" dot={false} />
            <Line
              type="monotone"
              dataKey="quiz_attempts"
              name="محاولات اختبار"
              stroke="#64748b"
              dot={false}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>

      <div>
        <p className="mb-2 text-xs text-slate-500">متوسط درجة الاختبارات وتسليمات الواجبات</p>
        <ResponsiveContainer width="100%" height={180}>
          <LineChart data={daily}>
            <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
            <XAxis dataKey="dateLabel" tick={{ fontSize: 10 }} />
            <YAxis tick={{ fontSize: 10 }} allowDecimals={false} />
            <Tooltip />
            <Line
              type="monotone"
              dataKey="average_quiz_score"
              name="متوسط الدرجة %"
              stroke="#0f172a"
              dot={false}
            />
            <Line
              type="monotone"
              dataKey="assignment_submissions"
              name="تسليمات واجبات"
              stroke="#64748b"
              dot={false}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

function UsersTab({ currentUserId }) {
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const refresh = () => {
    setLoading(true);
    listAllUsers()
      .then(setUsers)
      .catch(() => setError("تعذر تحميل المستخدمين"))
      .finally(() => setLoading(false));
  };

  useEffect(refresh, []);

  const changeRole = async (user, role) => {
    if (role === user.role) return;
    try {
      await updateUser(user.id, { role });
      refresh();
    } catch (err) {
      setError(err.response?.data?.detail || "تعذر تحديث المستخدم");
    }
  };

  const toggleActive = async (user) => {
    try {
      await updateUser(user.id, { is_active: !user.is_active });
      refresh();
    } catch (err) {
      setError(err.response?.data?.detail || "تعذر تحديث المستخدم");
    }
  };

  const handleDelete = async (user) => {
    if (!window.confirm(`حذف المستخدم ${user.email}؟`)) return;
    try {
      await deleteUser(user.id);
      refresh();
    } catch (err) {
      setError(err.response?.data?.detail || "تعذر حذف المستخدم");
    }
  };

  if (loading) return <p className="text-sm text-slate-400">...</p>;

  return (
    <div className="space-y-2">
      {error && <p className="text-sm text-red-600">{error}</p>}
      {users.map((user) => (
        <div
          key={user.id}
          className="flex flex-wrap items-center justify-between gap-2 rounded-xl border border-slate-200 px-3 py-2 text-sm"
        >
          <div className="min-w-0">
            <p className="truncate text-slate-900">{user.email}</p>
            <p className="text-xs text-slate-400">
              {user.is_active ? "مفعّل" : "معطّل"} ·{" "}
              {user.is_email_verified ? "بريد مؤكَّد" : "بريد غير مؤكَّد"}
            </p>
          </div>
          <div className="flex shrink-0 items-center gap-1">
            <select
              value={user.role}
              onChange={(e) => changeRole(user, e.target.value)}
              disabled={user.id === currentUserId}
              className="rounded-lg border border-slate-200 px-2 py-1 text-xs disabled:opacity-50"
            >
              {Object.entries(ROLE_LABELS).map(([value, label]) => (
                <option key={value} value={value}>
                  {label}
                </option>
              ))}
            </select>
            <button
              onClick={() => toggleActive(user)}
              disabled={user.id === currentUserId}
              className="rounded-lg border border-slate-200 px-2 py-1 text-xs hover:bg-slate-50 disabled:opacity-50"
            >
              {user.is_active ? "تعطيل" : "تفعيل"}
            </button>
            {user.id !== currentUserId && (
              <button
                onClick={() => handleDelete(user)}
                className="rounded-lg border border-red-200 px-2 py-1 text-xs text-red-600 hover:bg-red-50"
              >
                حذف
              </button>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}

function LogsTab() {
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    listAuditLogs()
      .then(setLogs)
      .catch(() => setError("تعذر تحميل السجل"))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <p className="text-sm text-slate-400">...</p>;
  if (error) return <p className="text-sm text-red-600">{error}</p>;
  if (logs.length === 0) return <p className="text-sm text-slate-400">لا توجد أحداث بعد</p>;

  return (
    <div className="space-y-1.5">
      {logs.map((log) => (
        <div key={log.id} className="rounded-xl border border-slate-200 px-3 py-2 text-sm">
          <div className="flex items-center justify-between gap-2">
            <span className="rounded-full bg-slate-100 px-2 py-0.5 text-xs text-slate-600">
              {log.event_type}
            </span>
            <span className="shrink-0 text-xs text-slate-400">
              {new Date(log.created_at).toLocaleString()}
            </span>
          </div>
          <p className="mt-1 text-slate-700">{log.description}</p>
        </div>
      ))}
    </div>
  );
}

export default function AdminDashboard({ currentUserId, onClose }) {
  const [tab, setTab] = useState("stats");

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 p-4">
      <div className="flex h-[85vh] w-full max-w-5xl flex-col rounded-3xl border border-slate-200 bg-white shadow-lg">
        <div className="flex items-center justify-between border-b border-slate-200 p-4">
          <h2 className="text-lg font-semibold text-slate-900">لوحة الإدارة</h2>
          <button
            onClick={onClose}
            className="rounded-lg px-2 py-1 text-slate-400 hover:bg-slate-100 focus:outline-none focus:ring-2 focus:ring-slate-400"
          >
            ✕
          </button>
        </div>

        <div className="flex gap-1 overflow-x-auto border-b border-slate-200 px-4 pt-2">
          {TABS.map((t) => (
            <button
              key={t.id}
              onClick={() => setTab(t.id)}
              className={`rounded-t-xl px-3 py-2 text-sm ${
                tab === t.id
                  ? "border-b-2 border-slate-900 font-medium text-slate-900"
                  : "text-slate-500 hover:text-slate-700"
              }`}
            >
              {t.label}
            </button>
          ))}
        </div>

        <div className="flex-1 overflow-y-auto p-4">
          {tab === "stats" && <StatsTab />}
          {tab === "users" && <UsersTab currentUserId={currentUserId} />}
          {tab === "logs" && <LogsTab />}
          {tab === "lti" && <LTIManagementTab />}
        </div>
      </div>
    </div>
  );
}
