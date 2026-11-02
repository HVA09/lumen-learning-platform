import { useEffect, useRef, useState } from "react";

// تحدي: أوجد الخط اللي يمر بنقطتين محددتين
const TARGET_POINTS = [
  [2, 5],
  [-1, -1],
];
const TARGET_M = 2; // (5 - (-1)) / (2 - (-1))
const TARGET_B = 1; // 5 = 2*2 + b

function drawGraph(canvas, m, b) {
  const ctx = canvas.getContext("2d");
  const w = canvas.width;
  const h = canvas.height;
  const scale = 20; // بكسل لكل وحدة
  const cx = w / 2;
  const cy = h / 2;

  ctx.clearRect(0, 0, w, h);

  // المحاور
  ctx.strokeStyle = "#cbd5e1";
  ctx.lineWidth = 1;
  ctx.beginPath();
  ctx.moveTo(0, cy);
  ctx.lineTo(w, cy);
  ctx.moveTo(cx, 0);
  ctx.lineTo(cx, h);
  ctx.stroke();

  // النقاط الهدف
  ctx.fillStyle = "#059669";
  TARGET_POINTS.forEach(([x, y]) => {
    ctx.beginPath();
    ctx.arc(cx + x * scale, cy - y * scale, 5, 0, Math.PI * 2);
    ctx.fill();
  });

  // خط الطالب: y = m*x + b
  ctx.strokeStyle = "#0f172a";
  ctx.lineWidth = 2;
  ctx.beginPath();
  const x1 = -cx / scale;
  const x2 = cx / scale;
  ctx.moveTo(cx + x1 * scale, cy - (m * x1 + b) * scale);
  ctx.lineTo(cx + x2 * scale, cy - (m * x2 + b) * scale);
  ctx.stroke();
}

export default function LinearFunctionSim() {
  const canvasRef = useRef(null);
  const [m, setM] = useState(1);
  const [b, setB] = useState(0);
  const [result, setResult] = useState(null);

  useEffect(() => {
    if (canvasRef.current) drawGraph(canvasRef.current, m, b);
  }, [m, b]);

  const checkChallenge = () => {
    const correct = Math.abs(m - TARGET_M) < 0.15 && Math.abs(b - TARGET_B) < 0.15;
    setResult(correct);
  };

  return (
    <div>
      <p className="mb-2 text-sm text-slate-600">
        حرّك m وb لتجعل الخط يمر بالنقطتين الخضراوين — النقطتان: (2, 5) و(-1, -1)
      </p>
      <canvas ref={canvasRef} width={320} height={280} className="mx-auto rounded-xl bg-white" />
      <div className="mt-3 space-y-2">
        <label className="block text-sm">
          الميل (m): {m.toFixed(1)}
          <input
            type="range" min="-5" max="5" step="0.1" value={m}
            onChange={(e) => setM(Number(e.target.value))}
            className="w-full"
          />
        </label>
        <label className="block text-sm">
          نقطة التقاطع (b): {b.toFixed(1)}
          <input
            type="range" min="-10" max="10" step="0.1" value={b}
            onChange={(e) => setB(Number(e.target.value))}
            className="w-full"
          />
        </label>
      </div>
      <button
        onClick={checkChallenge}
        className="mt-3 w-full rounded-xl bg-slate-900 px-4 py-2 text-sm text-white hover:bg-slate-800"
      >
        تحقّق
      </button>
      {result !== null && (
        <p className={`mt-2 text-center text-sm ${result ? "text-emerald-600" : "text-red-600"}`}>
          {result ? "صحيح! المعادلة: y = 2x + 1" : "قريب، جرّب تعدّل القيم أكثر"}
        </p>
      )}
    </div>
  );
}
