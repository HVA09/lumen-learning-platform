/* Isolated Pyodide runtime.
 * This document is embedded with sandbox="allow-scripts" (opaque origin only).
 * Pyodide itself runs in a dedicated worker so an infinite loop can be terminated
 * without blocking the iframe bridge or the authenticated application.
 */
const CHANNEL = "lumen-python-sandbox";
const PYODIDE_VERSION = "0.26.4";
const PYODIDE_ROOT = `https://cdn.jsdelivr.net/pyodide/v${PYODIDE_VERSION}/full/`;
const MAX_CODE_LENGTH = 20_000;
const MAX_OUTPUT_LENGTH = 20_000;

let worker = null;
let workerObjectUrl = null;
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

function buildWorkerSource() {
  return [
    `const PYODIDE_ROOT = ${JSON.stringify(PYODIDE_ROOT)};`,
    `const MAX_OUTPUT_LENGTH = ${MAX_OUTPUT_LENGTH};`,
    `const CAPTURE_OUTPUT_SCRIPT = ${JSON.stringify(CAPTURE_OUTPUT_SCRIPT)};`,
    "importScripts(PYODIDE_ROOT + 'pyodide.js');",
    "const pyodideReadyPromise = loadPyodide({ indexURL: PYODIDE_ROOT });",
    "let workerBusy = false;",
    "self.onmessage = async (event) => {",
    "  const message = event.data || {};",
    "  const requestId = message.requestId;",
    "  const code = message.code;",
    "  if (workerBusy || typeof requestId !== 'string' || typeof code !== 'string' || code.length > 20000) return;",
    "  workerBusy = true;",
    "  self.postMessage({ type: 'status', requestId, status: 'loading' });",
    "  try {",
    "    const pyodide = await pyodideReadyPromise;",
    "    self.postMessage({ type: 'status', requestId, status: 'running' });",
    "    pyodide.globals.set('__lumen_student_code', code);",
    "    let captured;",
    "    try { captured = await pyodide.runPythonAsync(CAPTURE_OUTPUT_SCRIPT); }",
    "    finally { pyodide.globals.delete('__lumen_student_code'); }",
    "    const rawOutput = typeof captured === 'string' ? captured : (typeof captured?.toJs === 'function' ? captured.toJs() : String(captured ?? ''));",
    "    if (typeof captured?.destroy === 'function') captured.destroy();",
    "    self.postMessage({ type: 'complete', requestId, output: String(rawOutput).slice(0, MAX_OUTPUT_LENGTH) });",
    "  } catch (error) {",
    "    self.postMessage({ type: 'error', requestId, error: String(error?.message || error || 'تعذر تشغيل كود Python').slice(0, 1000) });",
    "  } finally {",
    "    workerBusy = false;",
    "  }",
    "};",
    "self.postMessage({ type: 'worker-ready' });",
  ].join("\n");
}

function destroyWorker() {
  if (worker) {
    worker.terminate();
    worker = null;
  }
  if (workerObjectUrl) {
    URL.revokeObjectURL(workerObjectUrl);
    workerObjectUrl = null;
  }
  activeRequestId = null;
}

function getWorker() {
  if (worker) return worker;

  const blob = new Blob([buildWorkerSource()], { type: "text/javascript" });
  workerObjectUrl = URL.createObjectURL(blob);
  try {
    worker = new Worker(workerObjectUrl);
  } catch (error) {
    URL.revokeObjectURL(workerObjectUrl);
    workerObjectUrl = null;
    throw error;
  }

  worker.addEventListener("message", (event) => {
    const message = event.data;
    if (!message || typeof message !== "object") return;

    if (message.type === "worker-ready") {
      if (workerObjectUrl) {
        URL.revokeObjectURL(workerObjectUrl);
        workerObjectUrl = null;
      }
      return;
    }

    if (typeof message.requestId !== "string" || message.requestId !== activeRequestId) return;
    if (message.type === "status") {
      if (!["loading", "running"].includes(message.status)) return;
      sendToParent({ type: "status", requestId: activeRequestId, status: message.status });
      return;
    }
    if (message.type === "complete") {
      activeRequestId = null;
      sendToParent({
        type: "complete",
        requestId: message.requestId,
        output: typeof message.output === "string"
          ? message.output.slice(0, MAX_OUTPUT_LENGTH)
          : "",
      });
      return;
    }
    if (message.type === "error") {
      activeRequestId = null;
      sendToParent({
        type: "error",
        requestId: message.requestId,
        error: String(message.error || "تعذر تشغيل Python").slice(0, 1000),
      });
    }
  });

  worker.addEventListener("error", (event) => {
    const requestId = activeRequestId;
    destroyWorker();
    if (requestId) {
      sendToParent({
        type: "error",
        requestId,
        error: String(event.message || "تعذر تشغيل عامل Python المعزول").slice(0, 1000),
      });
    }
  });

  worker.addEventListener("messageerror", () => {
    const requestId = activeRequestId;
    destroyWorker();
    if (requestId) {
      sendToParent({
        type: "error",
        requestId,
        error: "تعذر استقبال نتيجة عامل Python المعزول",
      });
    }
  });

  return worker;
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
    message.code.length > MAX_CODE_LENGTH ||
    activeRequestId !== null
  ) {
    return;
  }

  activeRequestId = message.requestId;
  try {
    sendToParent({ type: "status", requestId: activeRequestId, status: "loading" });
    getWorker().postMessage({ requestId: activeRequestId, code: message.code });
  } catch (error) {
    const requestId = activeRequestId;
    destroyWorker();
    sendToParent({
      type: "error",
      requestId,
      error: String(error?.message || error || "تعذر بدء عامل Python المعزول").slice(0, 1000),
    });
  }
});

sendToParent({ type: "ready" });
