import { useEffect, useRef, useState } from "react";

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || "http://localhost:8000").replace(/\/$/, "");

export default function LTICallbackPage() {
  const [error, setError] = useState(false);
  const started = useRef(false);

  useEffect(() => {
    if (started.current) return;
    started.current = true;

    // Use a URL fragment rather than query parameters so the code is not sent
    // to the frontend web server in the initial HTTP request.
    const params = new URLSearchParams(window.location.hash.slice(1));
    const code = params.get("code");

    // Remove the short-lived credential from the visible URL/history immediately.
    window.history.replaceState({}, document.title, window.location.pathname);

    if (!code) {
      setError(true);
      return;
    }

    const exchangeCode = async () => {
      try {
        const response = await fetch(`${API_BASE_URL}/lti/exchange`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ code }),
          cache: "no-store",
          credentials: "omit",
        });
        if (!response.ok) throw new Error("LTI code exchange failed");

        const tokens = await response.json();
        if (!tokens.access_token || !tokens.refresh_token) {
          throw new Error("LTI exchange response was incomplete");
        }

        localStorage.setItem("access_token", tokens.access_token);
        localStorage.setItem("refresh_token", tokens.refresh_token);
        window.location.replace("/");
      } catch {
        setError(true);
      }
    };

    exchangeCode();
  }, []);

  return (
    <div className="flex h-full items-center justify-center bg-slate-50 p-4">
      <div className="w-full max-w-sm rounded-3xl border border-slate-200 bg-white p-6 text-center shadow-sm">
        {error ? (
          <>
            <h1 className="mb-2 text-lg font-semibold text-red-700">تعذّر تسجيل الدخول</h1>
            <p className="text-sm text-slate-500">رمز الدخول غير صالح أو انتهت صلاحيته. ابدأ تسجيل الدخول من منصة التعليم مرة أخرى.</p>
          </>
        ) : (
          <p className="text-sm text-slate-500">جاري تسجيل دخولك...</p>
        )}
      </div>
    </div>
  );
}
