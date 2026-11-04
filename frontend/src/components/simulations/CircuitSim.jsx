import { useEffect, useRef, useState } from "react";

const VOLTAGE = 12; // فولت — ثابتة
const TARGET_CURRENT = 2; // أمبير — هدف: اضبط التيار الكلي ليساوي هذي القيمة تقريبًا

function drawCircuit(canvas, mode) {
  const ctx = canvas.getContext("2d");
  const w = canvas.width;
  const h = canvas.height;
  ctx.clearRect(0, 0, w, h);
  ctx.strokeStyle = "#0f172a";
  ctx.lineWidth = 2;
  ctx.font = "12px sans-serif";
  ctx.fillStyle = "#0f172a";

  // البطارية (يسار)
  ctx.strokeRect(20, 90, 20, 40);
  ctx.fillText("V", 25, 145);

  if (mode === "series") {
    ctx.beginPath();
    ctx.moveTo(40, 100);
    ctx.lineTo(120, 100);
    ctx.strokeRect(120, 85, 50, 30);
    ctx.fillText("R1", 135, 130);
    ctx.moveTo(170, 100);
    ctx.lineTo(220, 100);
    ctx.strokeRect(220, 85, 50, 30);
    ctx.fillText("R2", 235, 130);
    ctx.lineTo(280, 100);
    ctx.lineTo(280, 130);
    ctx.lineTo(20, 130);
    ctx.stroke();
  } else {
    // توازي: فرعان بين نفس العقدتين
    ctx.beginPath();
    ctx.moveTo(40, 100);
    ctx.lineTo(100, 100);
    ctx.moveTo(100, 60);
    ctx.lineTo(100, 140);
    ctx.moveTo(100, 70);
    ctx.lineTo(160, 70);
    ctx.strokeRect(160, 55, 50, 30);
    ctx.fillText("R1", 175, 100);
    ctx.moveTo(210, 70);
    ctx.lineTo(240, 70);
    ctx.moveTo(100, 130);
    ctx.lineTo(160, 130);
    ctx.strokeRect(160, 115, 50, 30);
    ctx.fillText("R2", 175, 160);
    ctx.moveTo(210, 130);
    ctx.lineTo(240, 130);
    ctx.moveTo(240, 70);
    ctx.lineTo(240, 130);
    ctx.moveTo(240, 100);
    ctx.lineTo(280, 100);
    ctx.lineTo(280, 130);
    ctx.lineTo(20, 130);
    ctx.stroke();
  }
}

function compute(mode, r1, r2) {
  if (mode === "series") {
    const rEq = r1 + r2;
    const current = VOLTAGE / rEq;
    return { rEq, totalCurrent: current, v1: current * r1, v2: current * r2 };
  }
  const rEq = (r1 * r2) / (r1 + r2);
  const i1 = VOLTAGE / r1;
  const i2 = VOLTAGE / r2;
  return { rEq, totalCurrent: i1 + i2, v1: VOLTAGE, v2: VOLTAGE };
}

export default function CircuitSim() {
  const canvasRef = useRef(null);
  const [mode, setMode] = useState("series");
  const [r1, setR1] = useState(4);
  const [r2, setR2] = useState(6);
  const [result, setResult] = useState(null);

  useEffect(() => {
    if (canvasRef.current) drawCircuit(canvasRef.current, mode);
  }, [mode, r1, r2]);

  const { rEq, totalCurrent } = compute(mode, r1, r2);

  const checkChallenge = () => {
    setResult(Math.abs(totalCurrent - TARGET_CURRENT) < 0.15);
  };

  return (
    <div>
      <p className="mb-2 text-sm text-slate-600">
        البطارية V = {VOLTAGE} فولت ثابتة — اضبط المقاومتين ونوع التوصيل عشان يصير
        التيار الكلي {TARGET_CURRENT} أمبير تقريبًا
      </p>
      <canvas ref={canvasRef} width={300} height={190} className="mx-auto rounded-xl bg-white" />
      <div className="mt-3 flex gap-2">
        <button
          onClick={() => setMode("series")}
          className={`flex-1 rounded-xl border px-3 py-1.5 text-sm ${mode === "series" ? "border-slate-900 bg-slate-900 text-white" : "border-slate-200"}`}
        >
          توالي
        </button>
        <button
          onClick={() => setMode("parallel")}
          className={`flex-1 rounded-xl border px-3 py-1.5 text-sm ${mode === "parallel" ? "border-slate-900 bg-slate-900 text-white" : "border-slate-200"}`}
        >
          توازي
        </button>
      </div>
      <div className="mt-3 space-y-2">
        <label className="block text-sm">
          R1: {r1} أوم
          <input type="range" min="1" max="20" value={r1} onChange={(e) => setR1(Number(e.target.value))} className="w-full" />
        </label>
        <label className="block text-sm">
          R2: {r2} أوم
          <input type="range" min="1" max="20" value={r2} onChange={(e) => setR2(Number(e.target.value))} className="w-full" />
        </label>
      </div>
      <p className="mt-2 text-xs text-slate-400">
        المقاومة المكافئة: {rEq.toFixed(1)} أوم — التيار الكلي: {totalCurrent.toFixed(2)} أمبير
      </p>
      <button
        onClick={checkChallenge}
        className="mt-3 w-full rounded-xl bg-slate-900 px-4 py-2 text-sm text-white hover:bg-slate-800"
      >
        تحقّق
      </button>
      {result !== null && (
        <p className={`mt-2 text-center text-sm ${result ? "text-emerald-600" : "text-red-600"}`}>
          {result ? "صحيح! طبّقت قانون أوم بنجاح" : `التيار حاليًا ${totalCurrent.toFixed(2)} أمبير`}
        </p>
      )}
    </div>
  );
}
