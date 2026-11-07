import { useEffect, useRef, useState } from "react";

const CHANNEL = "lumen-python-sandbox";
const PYTHON_SANDBOX_URL = `${import.meta.env.BASE_URL}python-sandbox.html`;
const MAX_CODE_LENGTH = 20_000;
const MAX_OUTPUT_LENGTH = 20_000;
const SANDBOX_BOOT_TIMEOUT_MS = 45_000;
const EXECUTION_TIMEOUT_MS = 8_000;

const DEFAULT_CODE = `# اطبع مجموع الأرقام من 1 إلى 10
total = 0
for i in range(1, 11):
    total += i
print(total)`;
const EXPECTED_OUTPUT = "55";

const STATUS_LABELS = {
  loading: "تحميل بيئة Python لأول مرة...",
  running: "تشغيل الكود...",
};

function messageText(value, fallback) {
  return typeof value === "string" && value.trim()
    ? value.slice(0, 1000)
    : fallback;
}

export default function PythonLabSim() {
  const [code, setCode] = useState(DEFAULT_CODE);
  const [output, setOutput] = useState("");
  const [status, setStatus] = useState("");
  const [running, setRunning] = useState(false);
  const [result, setResult] = useState(null);

  const frameRef = useRef(null);
  const sandboxReadyRef = useRef(false);
  const readyWaiterRef = useRef(null);
  const pendingRequestRef = useRef(null);
  const bootTimerRef = useRef(null);
  const executionTimerRef = useRef(null);
  const generationRef = useRef(0);
  const requestCounterRef = useRef(0);

  const clearTimers = () => {
    if (bootTimerRef.current !== null) {
      window.clearTimeout(bootTimerRef.current);
      bootTimerRef.current = null;
    }
    if (executionTimerRef.current !== null) {
      window.clearTimeout(executionTimerRef.current);
      executionTimerRef.current = null;
    }
  };

  const reloadSandbox = () => {
    sandboxReadyRef.current = false;
    const frame = frameRef.current;
    if (frame) {
      frame.src = `${PYTHON_SANDBOX_URL}?reset=${Date.now()}`;
    }
  };

  useEffect(() => {
    const handleSandboxMessage = (event) => {
      const frame = frameRef.current;
      if (
        !frame ||
        event.source !== frame.contentWindow ||
        event.origin !== "null"
      ) {
        return;
      }

      const message = event.data;
      if (
        !message ||
        typeof message !== "object" ||
        message.channel !== CHANNEL ||
        typeof message.type !== "string"
      ) {
        return;
      }

      if (message.type === "ready") {
        sandboxReadyRef.current = true;
        if (readyWaiterRef.current) {
          readyWaiterRef.current.resolve();
          readyWaiterRef.current = null;
        }
        return;
      }

      const pending = pendingRequestRef.current;
      if (!pending || message.requestId !== pending.id) return;

      if (message.type === "status") {
        if (message.status === "running") {
          if (bootTimerRef.current !== null) {
            window.clearTimeout(bootTimerRef.current);
            bootTimerRef.current = null;
          }
          if (executionTimerRef.current !== null) {
            window.clearTimeout(executionTimerRef.current);
          }
          executionTimerRef.current = window.setTimeout(() => {
            if (pendingRequestRef.current?.id !== pending.id) return;
            pendingRequestRef.current = null;
            clearTimers();
            generationRef.current += 1;
            setRunning(false);
            setStatus("");
            setOutput("انتهت مهلة التنفيذ. أوقفنا بيئة Python لحماية المنصة؛ يمكنك المحاولة بكود أقصر.");
            reloadSandbox();
          }, EXECUTION_TIMEOUT_MS);
        }
        setStatus(STATUS_LABELS[message.status] || "جارٍ تجهيز بيئة Python...");
        return;
      }

      if (message.type === "complete") {
        pendingRequestRef.current = null;
        clearTimers();
        setRunning(false);
        setStatus("");
        const value = typeof message.output === "string" ? message.output : "";
        setOutput(value.slice(0, MAX_OUTPUT_LENGTH) || "(لا يوجد إخراج — استخدم print() لعرض نتيجة)");
        return;
      }

      if (message.type === "error") {
        pendingRequestRef.current = null;
        clearTimers();
        setRunning(false);
        setStatus("");
        setOutput(`خطأ بتشغيل الكود: ${messageText(message.error, "تعذر تشغيل بيئة Python")}`);
      }
    };

    window.addEventListener("message", handleSandboxMessage);
    return () => {
      window.removeEventListener("message", handleSandboxMessage);
      generationRef.current += 1;
      pendingRequestRef.current = null;
      clearTimers();
      if (readyWaiterRef.current) {
        readyWaiterRef.current.reject(new Error("تم إغلاق المختبر"));
        readyWaiterRef.current = null;
      }
    };
  }, []);

  const waitForSandboxReady = () => {
    if (sandboxReadyRef.current) return Promise.resolve();

    return new Promise((resolve, reject) => {
      const timeout = window.setTimeout(() => {
        readyWaiterRef.current = null;
        reject(new Error("انتهت مهلة تحميل بيئة Python المعزولة"));
      }, SANDBOX_BOOT_TIMEOUT_MS);

      readyWaiterRef.current = {
        resolve: () => {
          window.clearTimeout(timeout);
          resolve();
        },
        reject: (error) => {
          window.clearTimeout(timeout);
          reject(error);
        },
      };
    });
  };

  const runCode = async () => {
    if (code.length > MAX_CODE_LENGTH) {
      setOutput("الكود أطول من الحد المسموح (20,000 حرف).");
      setResult(null);
      return;
    }

    const generation = generationRef.current + 1;
    generationRef.current = generation;
    setRunning(true);
    setResult(null);
    setOutput("");
    setStatus("جارٍ تجهيز بيئة Python المعزولة...");

    try {
      await waitForSandboxReady();
      if (generationRef.current !== generation) return;

      const frame = frameRef.current;
      if (!frame?.contentWindow) {
        throw new Error("تعذر الوصول إلى إطار Python المعزول");
      }

      const requestId = `python-${Date.now()}-${++requestCounterRef.current}`;
      pendingRequestRef.current = { id: requestId, generation };
      bootTimerRef.current = window.setTimeout(() => {
        if (pendingRequestRef.current?.id !== requestId) return;
        pendingRequestRef.current = null;
        clearTimers();
        generationRef.current += 1;
        setRunning(false);
        setStatus("");
        setOutput("تعذر تجهيز بيئة Python. تحقق من اتصال الإنترنت وحاول مرة أخرى.");
        reloadSandbox();
      }, SANDBOX_BOOT_TIMEOUT_MS);

      frame.contentWindow.postMessage(
        { channel: CHANNEL, type: "run", requestId, code },
        "*"
      );
    } catch (error) {
      if (generationRef.current !== generation) return;
      pendingRequestRef.current = null;
      clearTimers();
      setRunning(false);
      setStatus("");
      setOutput(`خطأ بتشغيل الكود: ${messageText(error?.message, "تعذر تحميل بيئة Python")}`);
      reloadSandbox();
    }
  };

  const cancelRun = () => {
    generationRef.current += 1;
    pendingRequestRef.current = null;
    clearTimers();
    if (readyWaiterRef.current) {
      readyWaiterRef.current.reject(new Error("تم إيقاف التنفيذ"));
      readyWaiterRef.current = null;
    }
    setRunning(false);
    setStatus("");
    setResult(null);
    setOutput("تم إيقاف التنفيذ وإعادة ضبط بيئة Python.");
    reloadSandbox();
  };

  const checkChallenge = () => {
    setResult(output.trim() === EXPECTED_OUTPUT);
  };

  return (
    <div>
      <p className="mb-2 text-sm text-slate-600">
        اكتب كود بايثون يطبع مجموع الأرقام من 1 إلى 10 (الجواب المتوقع: {EXPECTED_OUTPUT})
      </p>
      <textarea
        value={code}
        onChange={(event) => setCode(event.target.value)}
        rows={8}
        maxLength={MAX_CODE_LENGTH}
        dir="ltr"
        spellCheck={false}
        className="w-full rounded-xl border border-slate-200 bg-slate-900 p-3 font-mono text-sm text-slate-100 outline-none focus:ring-2 focus:ring-slate-400"
      />
      <button
        onClick={runCode}
        disabled={running}
        className="mt-3 w-full rounded-xl bg-slate-900 px-4 py-2 text-sm text-white hover:bg-slate-800 disabled:opacity-50"
      >
        {running ? status || "جاري التشغيل..." : "▶ شغّل الكود"}
      </button>

      {running && (
        <button
          onClick={cancelRun}
          className="mt-2 w-full rounded-xl border border-red-200 px-4 py-2 text-sm text-red-700 hover:bg-red-50"
        >
          إيقاف التنفيذ
        </button>
      )}

      {output && (
        <div className="mt-3 rounded-xl border border-slate-200 bg-slate-50 p-3">
          <p className="mb-1 text-xs font-medium text-slate-500">الإخراج:</p>
          <pre dir="ltr" className="whitespace-pre-wrap font-mono text-sm text-slate-800">
            {output}
          </pre>
        </div>
      )}

      {output && (
        <button
          onClick={checkChallenge}
          className="mt-3 w-full rounded-xl border border-slate-200 px-4 py-2 text-sm hover:bg-slate-50"
        >
          تحقّق من التحدي
        </button>
      )}
      {result !== null && (
        <p className={`mt-2 text-center text-sm ${result ? "text-emerald-600" : "text-red-600"}`}>
          {result ? "صحيح! 55 = 1+2+...+10" : `الإخراج الحالي "${output.trim()}" مو مطابق`}
        </p>
      )}

      <iframe
        ref={frameRef}
        title="بيئة تنفيذ Python معزولة"
        src={PYTHON_SANDBOX_URL}
        sandbox="allow-scripts"
        referrerPolicy="origin"
        aria-hidden="true"
        tabIndex={-1}
        className="pointer-events-none fixed left-0 top-0 h-px w-px border-0 opacity-0"
      />
    </div>
  );
}
