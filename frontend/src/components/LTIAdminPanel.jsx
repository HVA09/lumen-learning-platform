import { useCallback, useEffect, useMemo, useState } from "react";
import { getAssignments } from "../lib/assignmentsApi";
import {
  createLtiAssignmentLink,
  createLtiPlatform,
  listLtiAssignmentLinks,
  listLtiGradeEvents,
  listLtiPlatforms,
  listLtiResourceLinks,
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
  dead: "متوقف — يحتاج مراجعة",
  superseded: "استُبدلت بدرجة أحدث",
};

function formatDate(value) {
  if (!value) return "—";
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? "—" : date.toLocaleString();
}

function Field({ label, value, onChange, type = "text", required = true, dir = "auto", maxLength, min, max, step }) {
  return (
    <label className="block min-w-0 space-y-1 text-xs text-slate-600">
      <span>{label}</span>
      <input
        type={type}
        value={value}
        onChange={(event) => onChange(event.target.value)}
        required={required}
        maxLength={maxLength}
        min={min}
        max={max}
        step={step}
        dir={dir}
        className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm text-slate-900 outline-none focus:border-slate-400 focus:ring-2 focus:ring-slate-100"
      />
    </label>
  );
}

export default function LTIAdminPanel() {
  const [platforms, setPlatforms] = useState([]);
  const [resources, setResources] = useState([]);
  const [assignmentLinks, setAssignmentLinks] = useState([]);
  const [events, setEvents] = useState([]);
  const [assignments, setAssignments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [platformForm, setPlatformForm] = useState(EMPTY_PLATFORM);
  const [creatingPlatform, setCreatingPlatform] = useState(false);
  const [resourceId, setResourceId] = useState("");
  const [assignmentId, setAssignmentId] = useState("");
  const [scoreMaximum, setScoreMaximum] = useState("100");
  const [creatingMapping, setCreatingMapping] = useState(false);
  const [retryingEventId, setRetryingEventId] = useState(null);

  const loadData = useCallback(async (isRefresh = false) => {
    if (isRefresh) setRefreshing(true);
    else setLoading(true);
    setError("");
    try {
      const [platformData, resourceData, linkData, eventData, assignmentData] = await Promise.all([
        listLtiPlatforms(),
        listLtiResourceLinks(),
        listLtiAssignmentLinks(),
        listLtiGradeEvents(),
        getAssignments(),
      ]);
      setPlatforms(platformData);
      setResources(resourceData);
      setAssignmentLinks(linkData);
      setEvents(eventData);
      setAssignments(assignmentData);
    } catch (requestError) {
      setError(requestError.response?.data?.detail || "تعذر تحميل بيانات تكامل LTI. حاول تحديث اللوحة.");
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const unmappedReadyResources = useMemo(
    () => resources.filter((resource) => resource.lineitem_ready && !resource.mapped_assignment_id),
    [resources]
  );

  const handlePlatformChange = (field, value) => {
    setPlatformForm((current) => ({ ...current, [field]: value }));
  };

  const handleCreatePlatform = async (event) => {
    event.preventDefault();
    setCreatingPlatform(true);
    setError("");
    setNotice("");
    try {
      await createLtiPlatform(platformForm);
      setPlatformForm(EMPTY_PLATFORM);
      setNotice("تم تسجيل منصة LTI. أجرِ إطلاقًا تجريبيًا من المنصة ليظهر رابط المورد هنا.");
      await loadData(true);
    } catch (requestError) {
      setError(requestError.response?.data?.detail || "تعذر تسجيل منصة LTI. راجع العناوين والبيانات.");
    } finally {
      setCreatingPlatform(false);
    }
  };

  const handleCreateMapping = async (event) => {
    event.preventDefault();
    const selectedResource = resources.find((resource) => String(resource.id) === resourceId);
    if (!selectedResource || !assignmentId) return;
    setCreatingMapping(true);
    setError("");
    setNotice("");
    try {
      await createLtiAssignmentLink({
        platform_id: selectedResource.platform_id,
        assignment_id: Number(assignmentId),
        resource_link_id: selectedResource.resource_link_id,
        score_maximum: Number(scoreMaximum),
      });
      setResourceId("");
      setAssignmentId("");
      setScoreMaximum("100");
      setNotice("تم ربط مورد المنصة بالواجب. ستُرسل الدرجات بعد تقييم تسليم الطالب.");
      await loadData(true);
    } catch (requestError) {
      setError(requestError.response?.data?.detail || "تعذر إنشاء الربط. حدّث البيانات وتحقق من عدم وجود ربط سابق.");
    } finally {
      setCreatingMapping(false);
    }
  };

  const handleRetry = async (eventId) => {
    setRetryingEventId(eventId);
    setError("");
    setNotice("");
    try {
      await retryLtiGradeEvent(eventId);
      setNotice("تم تفويض محاولة إعادة الإرسال مرة واحدة. سيعالجها العامل الخلفي عند تشغيله.");
      await loadData(true);
    } catch (requestError) {
      setError(requestError.response?.data?.detail || "تعذرت إعادة المحاولة. حدّث حالة الحدث أولًا.");
    } finally {
      setRetryingEventId(null);
    }
  };

  if (loading) return <p className="text-sm text-slate-500">جارٍ تحميل تكامل LTI...</p>;

  return (
    <div className="space-y-5" dir="rtl">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <h3 className="font-semibold text-slate-900">تكامل منصات التعليم (LTI 1.3 / AGS)</h3>
          <p className="mt-1 text-xs text-slate-500">تسجيل المنصات، ربط مواردها بالواجبات، ومتابعة إرسال الدرجات.</p>
        </div>
        <button
          type="button"
          onClick={() => loadData(true)}
          disabled={refreshing}
          className="rounded-lg border border-slate-200 px-3 py-2 text-xs text-slate-700 hover:bg-slate-50 disabled:opacity-50"
        >
          {refreshing ? "جارٍ التحديث..." : "تحديث البيانات"}
        </button>
      </div>

      {error && <p role="alert" className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700">{error}</p>}
      {notice && <p role="status" className="rounded-lg border border-emerald-200 bg-emerald-50 p-3 text-sm text-emerald-800">{notice}</p>}

      <section className="rounded-2xl border border-slate-200 p-3 sm:p-4">
        <h4 className="font-medium text-slate-900">تسجيل منصة جديدة</h4>
        <p className="mt-1 text-xs leading-5 text-slate-500">أدخل بيانات التسجيل التي توفرها منصة LMS. لا تضع مفاتيح خاصة أو رموز وصول في هذه الحقول.</p>
        <form onSubmit={handleCreatePlatform} className="mt-3 grid grid-cols-1 gap-3 sm:grid-cols-2">
          <Field label="اسم المنصة" value={platformForm.name} onChange={(value) => handlePlatformChange("name", value)} maxLength={255} />
          <Field label="Issuer URL" value={platformForm.issuer} onChange={(value) => handlePlatformChange("issuer", value)} type="url" dir="ltr" maxLength={500} />
          <Field label="Client ID" value={platformForm.client_id} onChange={(value) => handlePlatformChange("client_id", value)} dir="ltr" maxLength={255} />
          <Field label="Deployment ID" value={platformForm.deployment_id} onChange={(value) => handlePlatformChange("deployment_id", value)} dir="ltr" maxLength={255} />
          <Field label="OIDC Login URL" value={platformForm.auth_login_url} onChange={(value) => handlePlatformChange("auth_login_url", value)} type="url" dir="ltr" maxLength={500} />
          <Field label="OAuth Token URL" value={platformForm.auth_token_url} onChange={(value) => handlePlatformChange("auth_token_url", value)} type="url" dir="ltr" maxLength={500} />
          <div className="sm:col-span-2">
            <Field label="JWKS URL" value={platformForm.jwks_url} onChange={(value) => handlePlatformChange("jwks_url", value)} type="url" dir="ltr" maxLength={500} />
          </div>
          <button
            type="submit"
            disabled={creatingPlatform}
            className="rounded-lg bg-slate-900 px-4 py-2 text-sm text-white hover:bg-slate-800 disabled:opacity-50 sm:col-span-2"
          >
            {creatingPlatform ? "جارٍ التسجيل..." : "تسجيل المنصة"}
          </button>
        </form>
        {platforms.length > 0 && (
          <div className="mt-4 space-y-2 border-t border-slate-100 pt-3">
            <p className="text-xs font-medium text-slate-600">المنصات المسجلة ({platforms.length})</p>
            {platforms.map((platform) => (
              <div key={platform.id} className="flex flex-wrap items-center justify-between gap-2 rounded-lg bg-slate-50 px-3 py-2 text-sm">
                <span className="font-medium text-slate-800">{platform.name}</span>
                <span className="break-all text-xs text-slate-500" dir="ltr">{platform.issuer} · {platform.deployment_id}</span>
              </div>
            ))}
          </div>
        )}
      </section>

      <section className="rounded-2xl border border-slate-200 p-3 sm:p-4">
        <h4 className="font-medium text-slate-900">ربط مورد LMS بواجب</h4>
        <p className="mt-1 text-xs leading-5 text-slate-500">يظهر المورد بعد إطلاق موثّق من منصة مسجلة. لا يمكن ربط مورد لا يتيح صلاحية إرسال الدرجات.</p>
        {unmappedReadyResources.length === 0 ? (
          <p className="mt-3 rounded-lg bg-slate-50 p-3 text-xs text-slate-500">لا توجد موارد جاهزة وغير مربوطة حاليًا. نفّذ إطلاقًا من المنصة وتأكد من منح AGS score scope.</p>
        ) : assignments.length === 0 ? (
          <p className="mt-3 rounded-lg bg-slate-50 p-3 text-xs text-slate-500">أنشئ واجبًا أولًا حتى تتمكن من ربط مورد المنصة به.</p>
        ) : (
          <form onSubmit={handleCreateMapping} className="mt-3 space-y-3">
            <label className="block space-y-1 text-xs text-slate-600">
              <span>مورد المنصة</span>
              <select value={resourceId} onChange={(event) => setResourceId(event.target.value)} required className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm text-slate-900">
                <option value="">اختر موردًا مكتشفًا</option>
                {unmappedReadyResources.map((resource) => {
                  const platform = platforms.find((item) => item.id === resource.platform_id);
                  return <option key={resource.id} value={resource.id}>{platform?.name || `منصة ${resource.platform_id}`} · {resource.resource_link_id}</option>;
                })}
              </select>
            </label>
            <label className="block space-y-1 text-xs text-slate-600">
              <span>واجب Lumen</span>
              <select value={assignmentId} onChange={(event) => setAssignmentId(event.target.value)} required className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm text-slate-900">
                <option value="">اختر واجبًا</option>
                {assignments.map((assignment) => <option key={assignment.id} value={assignment.id}>{assignment.title}</option>)}
              </select>
            </label>
            <Field label="الدرجة القصوى في منصة LMS" type="number" value={scoreMaximum} onChange={setScoreMaximum} dir="ltr" min="0.01" max="1000000" step="0.01" />
            <button type="submit" disabled={creatingMapping || !resourceId || !assignmentId || !Number.isFinite(Number(scoreMaximum)) || Number(scoreMaximum) <= 0 || Number(scoreMaximum) > 1000000} className="w-full rounded-lg bg-slate-900 px-4 py-2 text-sm text-white hover:bg-slate-800 disabled:opacity-50">
              {creatingMapping ? "جارٍ إنشاء الربط..." : "حفظ الربط"}
            </button>
          </form>
        )}

        {assignmentLinks.length > 0 && (
          <div className="mt-4 space-y-2 border-t border-slate-100 pt-3">
            <p className="text-xs font-medium text-slate-600">الروابط النشطة ({assignmentLinks.length})</p>
            {assignmentLinks.map((link) => {
              const assignment = assignments.find((item) => item.id === link.assignment_id);
              const platform = platforms.find((item) => item.id === link.platform_id);
              return (
                <div key={link.id} className="rounded-lg bg-slate-50 px-3 py-2 text-xs">
                  <p className="font-medium text-slate-800">{assignment?.title || `واجب ${link.assignment_id}`}</p>
                  <p className="mt-1 break-all text-slate-500" dir="ltr">{platform?.name || `منصة ${link.platform_id}`} · {link.resource_link_id}</p>
                  <p className="mt-1 text-slate-500">الدرجة القصوى: {link.score_maximum} · {link.lineitem_ready ? "جاهز لإرسال الدرجات" : "غير جاهز لإرسال الدرجات"}</p>
                </div>
              );
            })}
          </div>
        )}
      </section>

      <section className="rounded-2xl border border-slate-200 p-3 sm:p-4">
        <h4 className="font-medium text-slate-900">سجل إرسال الدرجات</h4>
        <p className="mt-1 text-xs text-slate-500">يعرض الحالة التشغيلية فقط، ولا يعرض معرّفات الطلاب أو الدرجات أو روابط lineitem أو رموز OAuth.</p>
        {events.length === 0 ? (
          <p className="mt-3 rounded-lg bg-slate-50 p-3 text-xs text-slate-500">لا توجد أحداث درجات حتى الآن.</p>
        ) : (
          <div className="mt-3 space-y-2">
            {events.map((item) => (
              <div key={item.id} className="rounded-lg border border-slate-100 px-3 py-2 text-xs">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <span className="font-medium text-slate-800">حدث #{item.id} · {STATUS_LABELS[item.status] || item.status}</span>
                  <span className="text-slate-500">محاولات: {item.attempts}</span>
                </div>
                <p className="mt-1 text-slate-500">تاريخ الإنشاء: {formatDate(item.created_at)} · الإصدار: {item.grade_version}</p>
                {item.last_error && <p className="mt-1 text-red-600">آخر خطأ: {item.last_error}</p>}
                {item.status === "dead" && (
                  <button type="button" onClick={() => handleRetry(item.id)} disabled={retryingEventId === item.id} className="mt-2 rounded-lg border border-amber-300 px-3 py-1.5 text-xs text-amber-800 hover:bg-amber-50 disabled:opacity-50">
                    {retryingEventId === item.id ? "جارٍ التفويض..." : "تفويض إعادة محاولة واحدة"}
                  </button>
                )}
              </div>
            ))}
          </div>
        )}
      </section>

      <p className="text-xs leading-5 text-slate-500">ملاحظة تشغيلية: يلزم ضبط مفاتيح LTI الخاصة على الخادم وتشغيل Celery Worker وBeat. نجاح حفظ الربط لا يثبت اتصال Moodle أو Canvas؛ يجب اختبار كل منصة في بيئة Sandbox مستقلة قبل الاعتماد.</p>
    </div>
  );
}
