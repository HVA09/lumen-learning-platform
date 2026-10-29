import { useEffect, useRef, useState } from "react";
import api from "../lib/api";

export default function LTICallbackPage() {
  const [error, setError] = useState(false);
  const started = useRef(false);

  useEffect(() => {
    if (started.current) return;
    started.current = true;

    const params = new URLSearchParams(window.location.search);
    const code = params.get("code");

    // امسح الرمز من شريط العنوان فور قراءته؛ لا نحتفظ برموز الدخول في URL.
    window.history.replaceState({}, document.title, window.location.pathname);

    if (!code) {
      setError(true);
      return;
    }

    api
      .post("/lti/exchange-code", { code })
      .then(({ data }) => {
        localStorage.setItem("access_token", data.access_token);
        localStorage.setItem("refresh_token", data.refresh_token);
        window.location.replace("/");
      })
      .catch(() => setError(true));
  }, []);

  return (
    <div className="flex h-full items-center justify-center bg-slate-50 p-4">
      <div className="w-full max-w-sm rounded-3xl border border-slate-200 bg-white p-6 text-center shadow-sm">
        {error ? (
          <>
            <h1 className="mb-2 text-lg font-semibold text-red-700">تعذّر تسجيل الدخول</h1>
            <p className="text-sm text-slate-500">
              رمز تسجيل الدخول غير صالح أو منتهي. ابدأ تسجيل الدخول عبر منصة التعليم مرة أخرى.
            </p>
          </>
        ) : (
          <p className="text-sm text-slate-500">جاري تسجيل دخولك...</p>
        )}
      </div>
    </div>
  );
}
