import { useCallback, useEffect, useMemo, useState } from "react";
import { getAssignments } from "../lib/assignmentsApi";
import {
  createLtiAssignmentLink,
  listDiscoveredResourceLinks,
  listLtiAssignmentLinks,
  listLtiGradeEvents,
  listLtiPlatforms,
  registerLtiPlatform,
  retryLtiGradeEvent,
} from "../lib/ltiApi";

const EMPTY_PLATFORM = {
  name: "",
  issuer: "",
  client_id: "",
  deployment_id: "",
  auth_login_url: "",
  auth_token_url: "",
  jwks_url: "",
};

const STATUS_LABELS = {
  pending: "بانتظار الإرسال",
  sent: "تم الإرسال",
  dead: "توقفت المحاولات",
  superseded: "استُبدل بتقييم أحدث",
};

function errorMessage(error, fallback) {
  return error.response?.data?.detail || fallback;
}

function formatDate(value) {
  if (!value) return "—";
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? "—" : date.toLocaleString("ar");
}

function StatusPill({ children, tone = "neutral" }) {
  const styles = {
    success: "bg-emerald-50 text-emerald-700",
    warning: "bg-amber-50 text-amber-700",
    danger: "bg-red-50 text-red-700",
    neutral: "bg-slate-100 text-slate-600",
  };
  return (
    <span className={`inline-flex rounded-full px-2 py-1 text-xs ${styles[tone] || styles.neutral}`}>
      {children}
    </span>
  );
}

function PlatformRegistrationForm({ onRegistered }) {
  const [form, setForm] = useState(EMPTY_PLATFORM);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  const update = (field) => (event) => {
    setForm((current) => ({ ...current, [field]: event.target.value }));
  };

  const submit = async (event) => {
    event.preventDefault();
    setError("");
    setNotice("");
    setSaving(true);
    try {
      const created = await registerLtiPlatform({
        ...form,
        name: form.name.trim(),
        issuer: form.issuer.trim(),
        client_id: form.client_id.trim(),
        deployment_id: form.deployment_id.trim(),
        auth_login_url: form.auth_login_url.trim(),
        auth_token_url: form.auth_token_url.trim(),
        jwks_url: form.jwks_url.trim(),
      });
      setForm(EMPTY_PLATFORM);
      setNotice(`تم تسجيل المنصة بنجاح (المعرّف: ${created.id})`);
      await onRegistered();
    } catch (requestError) {
      setError(errorMessage(requestError, "تعذر تسجيل المنصة. تحقق من القيم وعناوين HTTPS."));
    } finally {
      setSaving(false);
    }
  };

  const fields = [
    ["name", "اسم المنصة", "text"],
    ["issuer", "Issuer", "url"],
    ["client_id", "Client ID", "text"],
    ["deployment_id", "Deployment ID", "text"],
    ["auth_login_url", "OIDC Authorization URL", "url"],
    ["auth_token_url", "OAuth Token URL", "url"],
    ["jwks_url", "Platform JWKS URL", "url"],
  ];

  return (
    <form onSubmit={submit} className="space-y-3 rounded-2xl border border-slate-200 bg-slate-50 p-3">
      <div>
        <h4 className="text-sm font-semibold text-slate-900">تسجيل منصة تعليم جديدة</h4>
        <p className="mt-1 text-xs leading-5 text-slate-500">
          أدخل القيم الرسمية التي يعرضها Moodle أو Canvas. لا تضع المفتاح الخاص أو أي رمز وصول هنا.
        </p>
      </div>
      <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
        {fields.map(([name, label, type]) => (
          <label key={name} className="block space-y-1 text-xs text-slate-600">
            <span>{label}</span>
            <input
              aria-label={label}
              name={name}
              type={type}
              value={form[name]}
              onChange={update(name)}
              required
              maxLength={name === "issuer" ? 500 : name.endsWith("_url") ? 500 : 255}
              autoComplete="off"
              className="w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm text-slate-900 outline-none focus:border-slate-400 focus:ring-2 focus:ring-slate-200"
            />
          </label>
        ))}
      </div>
      {error && <p role="alert" className="text-xs text-red-600">{error}</p>}
      {notice && <p role="status" className="text-xs text-emerald-700">{notice}</p>}
      <button
        type="submit"
        disabled={saving}
        className="rounded-lg bg-slate-900 px-4 py-2 text-xs font-medium text-white hover:bg-slate-800 disabled:opacity-50"
      >
        {saving ? "جارٍ التسجيل..." : "تسجيل المنصة"}
      </button>
    </form>
  );
}

function ResourceLinkCard({ resource, platformName, assignments, onMapped }) {
  const [assignmentId, setAssignmentId] = useState(assignments[0] ? String(assignments[0].id) : "");
  const [scoreMaximum, setScoreMaximum] = useState("100");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!assignmentId && assignments[0]) setAssignmentId(String(assignments[0].id));
  }, [assignments, assignmentId]);

  const submit = async (event) => {
    event.preventDefault();
    setError("");
    if (!assignmentId || !(Number(scoreMaximum) > 0)) {
      setError("اختر واجبًا وأدخل درجة قصوى أكبر من صفر.");
      return;
    }
    setSaving(true);
    try {
      await createLtiAssignmentLink({
        platform_id: resource.platform_id,
        assignment_id: Number(assignmentId),
        resource_link_id: resource.resource_link_id,
        score_maximum: Number(scoreMaximum),
      });
      await onMapped();
    } catch (requestError) {
      setError(errorMessage(requestError, "تعذر ربط المورد بالواجب."));
    } finally {
      setSaving(false);
    }
  };

  return (
    <article className="rounded-xl border border-slate-200 p-3">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div className="min-w-0">
          <p className="break-all text-sm font-medium text-slate-900">{resource.resource_link_id}</p>
          <p className="mt-1 text-xs text-slate-500">
            {platformName || `منصة #${resource.platform_id}`} · Deployment: {resource.deployment_id}
          </p>
        </div>
        <StatusPill tone={resource.lineitem_ready ? "success" : "warning"}>
          {resource.lineitem_ready ? "جاهز لإرسال الدرجات" : "ينتظر صلاحية AGS"}
        </StatusPill>
      </div>
      <p className="mt-2 text-xs text-slate-500">
        آخر ظهور: {formatDate(resource.last_seen_at)}
        {" · "}
        {resource.score_scope_allowed ? "صلاحية score متاحة" : "صلاحية score غير متاحة"}
      </p>
      {resource.mapped_assignment_id ? (
        <p className="mt-2 text-xs font-medium text-emerald-700">
          مربوط مسبقًا بالواجب رقم {resource.mapped_assignment_id}
        </p>
      ) : (
        <form onSubmit={submit} className="mt-3 flex flex-wrap items-end gap-2">
          <label className="min-w-[180px] flex-1 space-y-1 text-xs text-slate-600">
            <span>واجب Lumen</span>
            <select
              aria-label={`الواجب للمورد ${resource.resource_link_id}`}
              value={assignmentId}
              onChange={(event) => setAssignmentId(event.target.value)}
              disabled={assignments.length === 0 || saving}
              className="w-full rounded-lg border border-slate-200 bg-white px-2 py-2 text-sm"
            >
              <option value="">اختر الواجب</option>
              {assignments.map((assignment) => (
                <option key={assignment.id} value={assignment.id}>
                  {assignment.title} (#{assignment.id})
                </option>
              ))}
            </select>
          </label>
          <label className="w-32 space-y-1 text-xs text-slate-600">
            <span>الدرجة القصوى</span>
            <input
              aria-label={`الدرجة القصوى للمورد ${resource.resource_link_id}`}
              type="number"
              min="0.01"
              max="1000000"
              step="any"
              value={scoreMaximum}
              onChange={(event) => setScoreMaximum(event.target.value)}
              disabled={saving}
              className="w-full rounded-lg border border-slate-200 bg-white px-2 py-2 text-sm"
            />
          </label>
          <button
            type="submit"
            disabled={saving || assignments.length === 0 || !assignmentId}
            className="rounded-lg bg-slate-900 px-3 py-2 text-xs text-white disabled:opacity-50"
          >
            {saving ? "جارٍ الربط..." : "ربط الواجب"}
          </button>
        </form>
      )}
      {error && <p role="alert" className="mt-2 text-xs text-red-600">{error}</p>}
    </article>
  );
}

function Section({ title, count, children }) {
  return (
    <section className="space-y-3">
      <div className="flex items-center justify-between gap-2">
        <h3 className="font-semibold text-slate-900">{title}</h3>
        <span className="text-xs text-slate-400">{count}</span>
      </div>
      {children}
    </section>
  );
}

export default function LTIManagementTab() {
  const [platforms, setPlatforms] = useState([]);
  const [resources, setResources] = useState([]);
  const [mappings, setMappings] = useState([]);
  const [events, setEvents] = useState([]);
  const [assignments, setAssignments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState("");
  const [retryingId, setRetryingId] = useState(null);

  const load = useCallback(async (quiet = false) => {
    if (quiet) setRefreshing(true);
    else setLoading(true);
    setError("");
    try {
      const [platformRows, resourceRows, mappingRows, eventRows, assignmentRows] = await Promise.all([
        listLtiPlatforms(),
        listDiscoveredResourceLinks(),
        listLtiAssignmentLinks(),
        listLtiGradeEvents(),
        getAssignments(),
      ]);
      setPlatforms(platformRows);
      setResources(resourceRows);
      setMappings(mappingRows);
      setEvents(eventRows);
      setAssignments(assignmentRows);
    } catch (requestError) {
      setError(errorMessage(requestError, "تعذر تحميل بيانات تكامل منصات التعليم."));
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const platformNames = useMemo(
    () => Object.fromEntries(platforms.map((platform) => [platform.id, platform.name])),
    [platforms]
  );
  const assignmentNames = useMemo(
    () => Object.fromEntries(assignments.map((assignment) => [assignment.id, assignment.title])),
    [assignments]
  );

  const handleRetry = async (eventId) => {
    setRetryingId(eventId);
    setError("");
    try {
      await retryLtiGradeEvent(eventId);
      await load(true);
    } catch (requestError) {
      setError(errorMessage(requestError, "تعذرت إعادة جدولة حدث الدرجات."));
    } finally {
      setRetryingId(null);
    }
  };

  if (loading) return <p className="text-sm text-slate-400">جارٍ تحميل تكامل LMS...</p>;

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <h3 className="font-semibold text-slate-900">إدارة تكامل Moodle وCanvas</h3>
          <p className="mt-1 text-xs text-slate-500">
            تسجيل المنصات، اكتشاف مواردها، ربط الواجبات ومتابعة إرسال الدرجات.
          </p>
        </div>
        <button
          type="button"
          onClick={() => load(true)}
          disabled={refreshing}
          className="rounded-lg border border-slate-200 px-3 py-2 text-xs hover:bg-slate-50 disabled:opacity-50"
        >
          {refreshing ? "جارٍ التحديث..." : "تحديث البيانات"}
        </button>
      </div>

      {error && <p role="alert" className="rounded-lg bg-red-50 p-3 text-sm text-red-700">{error}</p>}

      <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
        {[
          ["المنصات", platforms.length],
          ["الموارد المكتشفة", resources.length],
          ["الروابط المربوطة", mappings.length],
          ["أحداث الدرجات", events.length],
        ].map(([label, value]) => (
          <div key={label} className="rounded-xl border border-slate-200 p-3">
            <p className="text-xl font-semibold text-slate-900">{value}</p>
            <p className="text-xs text-slate-500">{label}</p>
          </div>
        ))}
      </div>

      <PlatformRegistrationForm onRegistered={() => load(true)} />

      <Section title="المنصات المسجلة" count={platforms.length}>
        {platforms.length === 0 ? (
          <p className="rounded-xl border border-dashed border-slate-200 p-4 text-sm text-slate-400">
            لم تسجل أي منصة بعد.
          </p>
        ) : (
          <div className="grid gap-2 sm:grid-cols-2">
            {platforms.map((platform) => (
              <article key={platform.id} className="rounded-xl border border-slate-200 p-3">
                <p className="font-medium text-slate-900">{platform.name}</p>
                <p className="mt-1 break-all text-xs text-slate-500">{platform.issuer}</p>
                <p className="mt-1 text-xs text-slate-400">
                  Platform #{platform.id} · Client ID: {platform.client_id}
                </p>
              </article>
            ))}
          </div>
        )}
      </Section>

      <Section title="روابط LMS المكتشفة" count={resources.length}>
        {resources.length === 0 ? (
          <p className="rounded-xl border border-dashed border-slate-200 p-4 text-sm leading-6 text-slate-400">
            لا توجد روابط مكتشفة بعد. بعد تسجيل المنصة وفتح نشاط Lumen من داخل Moodle أو Canvas بحساب تجريبي، سيظهر المورد هنا.
          </p>
        ) : (
          <div className="space-y-2">
            {resources.map((resource) => (
              <ResourceLinkCard
                key={resource.id}
                resource={resource}
                platformName={platformNames[resource.platform_id]}
                assignments={assignments}
                onMapped={() => load(true)}
              />
            ))}
          </div>
        )}
      </Section>

      <Section title="روابط الواجبات الحالية" count={mappings.length}>
        {mappings.length === 0 ? (
          <p className="text-sm text-slate-400">لم يتم ربط واجبات بمنصات خارجية بعد.</p>
        ) : (
          <div className="space-y-2">
            {mappings.map((mapping) => (
              <article key={mapping.id} className="rounded-xl border border-slate-200 p-3 text-sm">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <p className="font-medium text-slate-900">
                    {assignmentNames[mapping.assignment_id] || `واجب #${mapping.assignment_id}`}
                  </p>
                  <StatusPill tone={mapping.lineitem_ready ? "success" : "warning"}>
                    {mapping.lineitem_ready ? "جاهز" : "غير جاهز"}
                  </StatusPill>
                </div>
                <p className="mt-1 break-all text-xs text-slate-500">{mapping.resource_link_id}</p>
                <p className="mt-1 text-xs text-slate-400">
                  {platformNames[mapping.platform_id] || `منصة #${mapping.platform_id}`} · الدرجة القصوى: {mapping.score_maximum}
                </p>
              </article>
            ))}
          </div>
        )}
      </Section>

      <Section title="سجل إرسال الدرجات" count={events.length}>
        {events.length === 0 ? (
          <p className="text-sm text-slate-400">لا توجد أحداث إرسال بعد. تنشأ الأحداث بعد تقييم تسليم طالب مربوط بـ LTI.</p>
        ) : (
          <div className="space-y-2">
            {events.map((item) => (
              <article key={item.id} className="rounded-xl border border-slate-200 p-3 text-sm">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <p className="font-medium text-slate-900">
                    حدث #{item.id} · التسليم #{item.submission_id} · النسخة {item.grade_version}
                  </p>
                  <StatusPill
                    tone={item.status === "sent" ? "success" : item.status === "dead" ? "danger" : item.status === "superseded" ? "neutral" : "warning"}
                  >
                    {STATUS_LABELS[item.status] || item.status}
                  </StatusPill>
                </div>
                <p className="mt-1 text-xs text-slate-500">
                  المحاولات: {item.attempts} · الإنشاء: {formatDate(item.created_at)}
                  · وقت الدرجة: {formatDate(item.score_timestamp)}
                  {item.delivered_at ? ` · الإرسال: ${formatDate(item.delivered_at)}` : ""}
                </p>
                {item.last_error && <p className="mt-2 text-xs text-red-600">{item.last_error}</p>}
                {item.status === "dead" && (
                  <button
                    type="button"
                    onClick={() => handleRetry(item.id)}
                    disabled={retryingId === item.id}
                    className="mt-2 rounded-lg border border-red-200 px-3 py-1.5 text-xs text-red-700 hover:bg-red-50 disabled:opacity-50"
                  >
                    {retryingId === item.id ? "جارٍ إعادة الجدولة..." : "إعادة المحاولة"}
                  </button>
                )}
              </article>
            ))}
          </div>
        )}
      </Section>

      <p className="text-xs leading-5 text-slate-400">
        تعرض هذه الشاشة بيانات الحالة فقط. لا تعرض عناوين lineitem أو رموز OAuth أو مفاتيح التوقيع الخاصة.
      </p>
    </div>
  );
}
