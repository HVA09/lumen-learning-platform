import { Component } from "react";

function isChunkLoadError(error) {
  const message = error instanceof Error ? error.message : String(error ?? "");
  return /failed to fetch dynamically imported module|importing a module script failed|failed to load module script|loading chunk .+ failed/i.test(
    message
  );
}

export default class ErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = {
      hasError: false,
      isChunkLoadError: false,
      isOnline: typeof navigator === "undefined" || navigator.onLine !== false,
    };
    this.handleOnline = () => this.setState({ isOnline: true });
    this.handleOffline = () => this.setState({ isOnline: false });
  }

  static getDerivedStateFromError(error) {
    return {
      hasError: true,
      isChunkLoadError: isChunkLoadError(error),
    };
  }

  componentDidMount() {
    window.addEventListener("online", this.handleOnline);
    window.addEventListener("offline", this.handleOffline);
  }

  componentWillUnmount() {
    window.removeEventListener("online", this.handleOnline);
    window.removeEventListener("offline", this.handleOffline);
  }

  componentDidCatch(error, info) {
    console.error("خطأ غير متوقع بالواجهة:", error, info);
  }

  render() {
    if (this.state.hasError) {
      const { isChunkLoadError, isOnline } = this.state;

      return (
        <div
          role="alert"
          className="flex h-full flex-col items-center justify-center gap-3 bg-slate-50 p-6 text-center"
        >
          <h2 className="text-lg font-semibold text-slate-900">
            {isChunkLoadError ? "تعذّر تحميل جزء من التطبيق" : "حدث خطأ غير متوقع"}
          </h2>
          <p className="max-w-sm text-sm text-slate-500">
            {isChunkLoadError
              ? "قد يكون الاتصال ضعيفًا أو أن نسخة الصفحة قديمة. تحقق من الاتصال ثم أعد المحاولة."
              : "حدثت مشكلة أثناء عرض الصفحة. حاول تحديث الصفحة."}
          </p>
          {isChunkLoadError && (
            <p role="status" className="text-sm text-slate-500">
              {isOnline
                ? "الاتصال متاح الآن. يمكنك إعادة تحميل الصفحة."
                : "الاتصال غير متاح حاليًا. ستتمكن من إعادة المحاولة عند عودته."}
            </p>
          )}
          <button
            type="button"
            disabled={isChunkLoadError && !isOnline}
            onClick={() => window.location.reload()}
            className="rounded-xl bg-slate-900 px-4 py-2 text-sm text-white hover:bg-slate-800 focus:outline-none focus:ring-2 focus:ring-slate-400 focus:ring-offset-1 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {isChunkLoadError
              ? isOnline
                ? "إعادة المحاولة"
                : "بانتظار عودة الاتصال"
              : "تحديث الصفحة"}
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}
