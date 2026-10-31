import { useState } from "react";
import { useTranslation } from "react-i18next";
import { loginUser, registerUser, requestPasswordReset } from "../lib/authApi";

export default function AuthForm({ onAuthenticated }) {
  const { t } = useTranslation();
  const [mode, setMode] = useState("login"); // "login" | "register" | "forgot"
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [totpCode, setTotpCode] = useState("");
  const [needsTotp, setNeedsTotp] = useState(false);
  const [error, setError] = useState("");
  const [info, setInfo] = useState("");
  const [loading, setLoading] = useState(false);

  const switchMode = (nextMode) => {
    setMode(nextMode);
    setError("");
    setInfo("");
    setNeedsTotp(false);
    setTotpCode("");
  };

  const completeLogin = async () => {
    await loginUser(email, password, needsTotp ? totpCode : null);
    onAuthenticated();
  };

  const submit = async (e) => {
    e.preventDefault();
    setError("");
    setInfo("");
    setLoading(true);
    try {
      if (mode === "forgot") {
        const data = await requestPasswordReset(email);
        setInfo(data.detail);
        return;
      }
      if (mode === "register") {
        await registerUser(email, password);
      }
      await completeLogin();
    } catch (err) {
      if (err.response?.status === 428) {
        // الحساب مفعّل عليه 2FA — نطلب الرمز ونعرض حقل إدخاله
        setNeedsTotp(true);
        setError("");
        return;
      }
      const detail = err.response?.data?.detail;
      setError(detail || "حدث خطأ، تأكد من البيانات وحاول مرة أخرى.");
    } finally {
      setLoading(false);
    }
  };

  const titles = {
    login: needsTotp ? "أدخل رمز التحقق الثنائي" : "سجّل الدخول للمتابعة",
    register: "أنشئ حسابًا جديدًا",
    forgot: "استرجاع كلمة المرور",
  };

  return (
    <div className="flex h-full items-center justify-center bg-slate-50 p-4">
      <form
        onSubmit={submit}
        className="w-full max-w-sm rounded-3xl border border-slate-200 bg-white p-6 shadow-sm"
      >
        <h1 className="mb-1 text-xl font-semibold text-slate-900">{t("appName")}</h1>
        <p className="mb-5 text-sm text-slate-500">{titles[mode]}</p>

        {needsTotp ? (
          <input
            type="text"
            required
            autoFocus
            inputMode="numeric"
            maxLength={6}
            placeholder="رمز التحقق (6 أرقام)"
            value={totpCode}
            onChange={(e) => setTotpCode(e.target.value)}
            className="w-full rounded-xl border border-slate-200 bg-slate-50 px-4 py-2.5 text-center tracking-[0.5em] outline-none focus:border-slate-400 focus:ring-2 focus:ring-slate-400"
          />
        ) : (
          <div className="space-y-3">
            <input
              type="email"
              required
              placeholder="البريد الإلكتروني"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full rounded-xl border border-slate-200 bg-slate-50 px-4 py-2.5 outline-none focus:border-slate-400 focus:ring-2 focus:ring-slate-400"
            />
            {mode !== "forgot" && (
              <input
                type="password"
                required
                minLength={8}
                placeholder="كلمة المرور (8 أحرف على الأقل)"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full rounded-xl border border-slate-200 bg-slate-50 px-4 py-2.5 outline-none focus:border-slate-400 focus:ring-2 focus:ring-slate-400"
              />
            )}
          </div>
        )}

        {mode === "login" && !needsTotp && (
          <button
            type="button"
            onClick={() => switchMode("forgot")}
            className="mt-2 text-sm text-slate-500 hover:text-slate-700"
          >
            نسيت كلمة المرور؟
          </button>
        )}

        {error && (
          <div className="mt-3 rounded-xl border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
            {error}
          </div>
        )}
        {info && (
          <div className="mt-3 rounded-xl border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-700">
            {info}
          </div>
        )}

        <button
          type="submit"
          disabled={loading}
          className="mt-4 w-full rounded-xl bg-slate-900 px-4 py-2.5 text-white hover:bg-slate-800 disabled:opacity-50 focus:outline-none focus:ring-2 focus:ring-slate-400 focus:ring-offset-1"
        >
          {loading
            ? "..."
            : needsTotp
              ? "تأكيد"
              : mode === "login"
                ? "دخول"
                : mode === "register"
                  ? "إنشاء حساب"
                  : "أرسل رابط الاسترجاع"}
        </button>

        {needsTotp ? (
          <button
            type="button"
            onClick={() => switchMode("login")}
            className="mt-3 w-full text-center text-sm text-slate-500 hover:text-slate-700"
          >
            رجوع
          </button>
        ) : mode === "forgot" ? (
          <button
            type="button"
            onClick={() => switchMode("login")}
            className="mt-3 w-full text-center text-sm text-slate-500 hover:text-slate-700"
          >
            رجوع لتسجيل الدخول
          </button>
        ) : (
          <button
            type="button"
            onClick={() => switchMode(mode === "login" ? "register" : "login")}
            className="mt-3 w-full text-center text-sm text-slate-500 hover:text-slate-700"
          >
            {mode === "login" ? "ليس لديك حساب؟ أنشئ واحدًا" : "لديك حساب؟ سجّل الدخول"}
          </button>
        )}
      </form>
    </div>
  );
}
