export default function BillingSuccessPage() {
  return (
    <div className="flex h-full items-center justify-center bg-slate-50 p-4">
      <div className="w-full max-w-sm rounded-3xl border border-slate-200 bg-white p-6 text-center shadow-sm">
        <h1 className="mb-2 text-lg font-semibold text-emerald-700">تم الدفع بنجاح ✓</h1>
        <p className="text-sm text-slate-500">
          يستغرق تفعيل الاشتراك بضع ثوانٍ. ارجع للتطبيق وتحقق من حالة اشتراكك من لوحة "الاشتراك".
        </p>
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
