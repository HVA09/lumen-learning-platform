import { useEffect, useState } from "react";

export default function LTICallbackPage() {
  const [error, setError] = useState(false);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const accessToken = params.get("access_token");
    const refreshToken = params.get("refresh_token");

    if (accessToken && refreshToken) {
      localStorage.setItem("access_token", accessToken);
      localStorage.setItem("refresh_token", refreshToken);
      window.location.href = "/";
    } else {
      setError(true);
    }
  }, []);

  return (
    <div className="flex h-full items-center justify-center bg-slate-50 p-4">
      <div className="w-full max-w-sm rounded-3xl border border-slate-200 bg-white p-6 text-center shadow-sm">
        {error ? (
          <>
            <h1 className="mb-2 text-lg font-semibold text-red-700">تعذّر تسجيل الدخول</h1>
            <p className="text-sm text-slate-500">لم تصل بيانات الدخول من منصة التعليم.</p>
          </>
        ) : (
          <p className="text-sm text-slate-500">جاري تسجيل دخولك...</p>
        )}
      </div>
    </div>
  );
}
