import { lazy, Suspense } from "react";

const SIM_COMPONENTS = {
  "linear-function": lazy(() => import("./simulations/LinearFunctionSim")),
  derivative: lazy(() => import("./simulations/DerivativeSim")),
  projectile: lazy(() => import("./simulations/ProjectileSim")),
  "circuits-dc": lazy(() => import("./simulations/CircuitSim")),
  "python-lab": lazy(() => import("./simulations/PythonLabSim")),
};

export default function LabPanel({ simulationType, topicName, onClose }) {
  const SimComponent = SIM_COMPONENTS[simulationType];

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center overflow-y-auto bg-black/30 p-4">
      <div className="my-8 w-full max-w-md rounded-3xl border border-slate-200 bg-white p-6 shadow-lg">
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-lg font-semibold text-slate-900">
            المختبر{topicName ? ` — ${topicName}` : ""}
          </h2>
          <button
            onClick={onClose}
            className="rounded-lg px-2 py-1 text-slate-400 hover:bg-slate-100 focus:outline-none focus:ring-2 focus:ring-slate-400"
          >
            ✕
          </button>
        </div>

        {SimComponent ? (
          <Suspense fallback={<p className="text-sm text-slate-400">جاري تحميل المحاكاة...</p>}>
            <SimComponent />
          </Suspense>
        ) : (
          <p className="text-sm text-slate-400">ما فيه محاكاة لهذا الموضوع بعد</p>
        )}
      </div>
    </div>
  );
}
