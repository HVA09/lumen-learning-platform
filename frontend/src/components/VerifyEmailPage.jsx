import { useEffect, useState } from "react";
import { confirmEmailVerification } from "../lib/authApi";

export default function VerifyEmailPage() {
  const [status, setStatus] = useState("loading"); // loading | success | error
  const [message, setMessage] = useState("");

  useEffect(() => {
    const token = new URLSearchParams(window.location.search).get("token");
    if (!token) {
      setStatus("error");
      setMessage("رابط التأكيد ناقص.");
      return;
    }
    confirmEmailVerification(token)
      .then((data) => {
        setStatus("success");
        setMessage(data.detail);
      })
      .catch((err) => {
        setStatus("error");
        setMessage(err.response?.data?.detail || "تعذر تأكيد البريد الإلكتروني.");
      });
  }, []);

  return (
    <div className="flex h-full items-center justify-center bg-slate-50 p-4">
      <div className="w-full max-w-sm rounded-3xl border border-slate-200 bg-white p-6 text-center shadow-sm">
        {status === "loading" && <p className="text-slate-500">جارٍ التأكيد...</p>}
        {status === "success" && (
          <>
            <h1 className="mb-2 text-lg font-semibold text-emerald-700">تم التأكيد ✓</h1>
            <p className="text-sm text-slate-500">{message}</p>
          </>
        )}
        {status === "error" && (
          <>
            <h1 className="mb-2 text-lg font-semibold text-red-700">تعذّر التأكيد</h1>
            <p className="text-sm text-slate-500">{message}</p>
          </>
        )}
        <a
          href="/"
          className="mt-4 inline-block rounded-xl bg-slate-900 px-4 py-2 text-sm text-white hover:bg-slate-800"
        >
          الرجوع للتطبيق
        </a>
      </div>
    </div>
  );
}
