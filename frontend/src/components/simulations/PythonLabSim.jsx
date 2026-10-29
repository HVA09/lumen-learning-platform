import { useRef, useState } from "react";

const PYODIDE_CDN = "https://cdn.jsdelivr.net/pyodide/v0.26.4/full/pyodide.js";
const DEFAULT_CODE = `# اطبع مجموع الأرقام من 1 إلى 10
total = 0
for i in range(1, 11):
    total += i
print(total)`;
const EXPECTED_OUTPUT = "55";

let pyodideInstance = null; // نحمّل Pyodide مرة وحدة فقط، حتى لو المكوّن يُعاد رسمه

async function loadPyodideOnce(onStatus) {
  if (pyodideInstance) return pyodideInstance;

  if (!window.loadPyodide) {
    onStatus("تحميل بيئة بايثون (أول مرة بس، تاخذ بضع ثوانٍ)...");
    await new Promise((resolve, reject) => {
      const script = document.createElement("script");
      script.src = PYODIDE_CDN;
      script.onload = resolve;
      script.onerror = () => reject(new Error("تعذر تحميل بيئة بايثون"));
      document.head.appendChild(script);
    });
  }

  onStatus("تجهيز المفسّر...");
  pyodideInstance = await window.loadPyodide();
  return pyodideInstance;
}

export default function PythonLabSim() {
  const [code, setCode] = useState(DEFAULT_CODE);
  const [output, setOutput] = useState("");
  const [status, setStatus] = useState("");
  const [running, setRunning] = useState(false);
  const [result, setResult] = useState(null);
  const editorRef = useRef(null);

  const runCode = async () => {
    setRunning(true);
    setResult(null);
    setOutput("");
    try {
      const pyodide = await loadPyodideOnce(setStatus);
      setStatus("تشغيل الكود...");

      // نلف كود الطالب بمصيدة stdout عشان نلتقط print() ونمسك أي استثناء
      // بدل ما يوقف كامل بيئة Pyodide لو صار خطأ
      const wrapped = `
import sys, io
_stdout = io.StringIO()
_old_stdout = sys.stdout
sys.stdout = _stdout
try:
${code
  .split("\n")
  .map((line) => "    " + line)
  .join("\n")}
except Exception as e:
    print(f"خطأ: {e}")
finally:
    sys.stdout = _old_stdout
_stdout.getvalue()
`;
      const captured = await pyodide.runPythonAsync(wrapped);
      setOutput(captured || "(لا يوجد إخراج — استخدم print() لعرض نتيجة)");
    } catch (err) {
      setOutput(`خطأ بتشغيل الكود: ${err.message}`);
    } finally {
      setStatus("");
      setRunning(false);
    }
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
        ref={editorRef}
        value={code}
        onChange={(e) => setCode(e.target.value)}
        rows={8}
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
    </div>
  );
}
