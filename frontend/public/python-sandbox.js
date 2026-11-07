/* Isolated Pyodide runtime. This document is embedded with sandbox="allow-scripts"
 * and therefore receives an opaque origin. Do not add allow-same-origin.
 */
const CHANNEL = "lumen-python-sandbox";
const PYODIDE_VERSION = "0.26.4";
const PYODIDE_ROOT = `https://cdn.jsdelivr.net/pyodide/v${PYODIDE_VERSION}/full/`;
const MAX_CODE_LENGTH = 20_000;
const MAX_OUTPUT_LENGTH = 20_000;

let pyodidePromise = null;
let activeRequestId = null;

const parentOrigin = (() => {
  try {
    return document.referrer ? new URL(document.referrer).origin : null;
  } catch {
    return null;
  }
})();

function sendToParent(message) {
  if (!parentOrigin || window.parent === window) return;
  window.parent.postMessage({ channel: CHANNEL, ...message }, parentOrigin);
}

function loadPyodideScript() {
  if (typeof window.loadPyodide === "function") return Promise.resolve();

  return new Promise((resolve, reject) => {
    const script = document.createElement("script");
    script.src = `${PYODIDE_ROOT}pyodide.js`;
    script.crossOrigin = "anonymous";
    script.onload = resolve;
    script.onerror = () => reject(new Error("تعذر تحميل بيئة Python من مصدرها"));
    document.head.appendChild(script);
  });
}

async function getPyodide() {
  if (!pyodidePromise) {
    pyodidePromise = (async () => {
      await loadPyodideScript();
      return window.loadPyodide({ indexURL: PYODIDE_ROOT });
    })().catch((error) => {
      pyodidePromise = null;
      throw error;
    });
  }

  return pyodidePromise;
}

const CAPTURE_OUTPUT_SCRIPT = `
import io
import sys

class _LumenLimitedOutput(io.StringIO):
    def __init__(self, limit):
        super().__init__()
        self.limit = limit
        self.truncated = False

    def write(self, value):
        remaining = max(0, self.limit - self.tell())
        if remaining:
            super().write(value[:remaining])
        if len(value) > remaining:
            self.truncated = True
        return len(value)

_lumen_output = _LumenLimitedOutput(20000)
_lumen_previous_stdout = sys.stdout
sys.stdout = _lumen_output
try:
    _lumen_namespace = {"__name__": "__main__"}
    exec(compile(__lumen_student_code, "<student>", "exec"), _lumen_namespace, _lumen_namespace)
except BaseException as _lumen_error:
    print(f"خطأ: {_lumen_error}")
finally:
    sys.stdout = _lumen_previous_stdout

_lumen_result = _lumen_output.getvalue()
if _lumen_output.truncated:
    _lumen_result += "\\n... تم اقتطاع الإخراج لأنه تجاوز الحد المسموح"
_lumen_result
`;

async function runPython(requestId, code) {
  if (activeRequestId !== null) return;
  activeRequestId = requestId;

  try {
    sendToParent({ type: "status", requestId, status: "loading" });
    const pyodide = await getPyodide();
    if (activeRequestId !== requestId) return;

    sendToParent({ type: "status", requestId, status: "running" });
    pyodide.globals.set("__lumen_student_code", code);

    let captured;
    try {
      captured = await pyodide.runPythonAsync(CAPTURE_OUTPUT_SCRIPT);
    } finally {
      pyodide.globals.delete("__lumen_student_code");
    }

    if (activeRequestId !== requestId) return;
    const rawOutput =
      typeof captured === "string"
        ? captured
        : typeof captured?.toJs === "function"
          ? captured.toJs()
          : String(captured ?? "");
    if (typeof captured?.destroy === "function") captured.destroy();

    sendToParent({
      type: "complete",
      requestId,
      output: String(rawOutput).slice(0, MAX_OUTPUT_LENGTH),
    });
  } catch (error) {
    if (activeRequestId === requestId) {
      sendToParent({
        type: "error",
        requestId,
        error: String(error?.message || error || "تعذر تشغيل كود Python").slice(0, 1000),
      });
    }
  } finally {
    if (activeRequestId === requestId) activeRequestId = null;
  }
}

window.addEventListener("message", (event) => {
  if (
    !parentOrigin ||
    event.source !== window.parent ||
    event.origin !== parentOrigin
  ) {
    return;
  }

  const message = event.data;
  if (
    !message ||
    typeof message !== "object" ||
    message.channel !== CHANNEL ||
    message.type !== "run" ||
    typeof message.requestId !== "string" ||
    message.requestId.length > 100 ||
    typeof message.code !== "string" ||
    message.code.length > MAX_CODE_LENGTH
  ) {
    return;
  }

  void runPython(message.requestId, message.code);
});

sendToParent({ type: "ready" });
