import { useEffect, useRef, useState } from "react";

// f(x) = x^2  →  f'(x) = 2x
const TARGET_SLOPE = 4; // f'(x)=4  →  x=2

function f(x) {
  return x * x;
}
function fPrime(x) {
  return 2 * x;
}

function draw(canvas, x0) {
  const ctx = canvas.getContext("2d");
  const w = canvas.width;
  const h = canvas.height;
  const scale = 20;
  const cx = w / 2;
  const cy = h - 20;

  ctx.clearRect(0, 0, w, h);
  ctx.strokeStyle = "#cbd5e1";
  ctx.beginPath();
  ctx.moveTo(0, cy);
  ctx.lineTo(w, cy);
  ctx.moveTo(cx, 0);
  ctx.lineTo(cx, h);
  ctx.stroke();

  // منحنى f(x) = x^2
  ctx.strokeStyle = "#0f172a";
  ctx.lineWidth = 2;
  ctx.beginPath();
  for (let px = 0; px <= w; px++) {
    const x = (px - cx) / scale;
    const y = f(x);
    const py = cy - y * scale;
    if (px === 0) ctx.moveTo(px, py);
    else ctx.lineTo(px, py);
  }
  ctx.stroke();

  // نقطة المماس
  const y0 = f(x0);
  const slope = fPrime(x0);
  ctx.fillStyle = "#dc2626";
  ctx.beginPath();
  ctx.arc(cx + x0 * scale, cy - y0 * scale, 5, 0, Math.PI * 2);
  ctx.fill();

  // خط المماس
  ctx.strokeStyle = "#dc2626";
  ctx.lineWidth = 1.5;
  ctx.beginPath();
  const dx = 3;
  ctx.moveTo(cx + (x0 - dx) * scale, cy - (y0 - slope * dx) * scale);
  ctx.lineTo(cx + (x0 + dx) * scale, cy - (y0 + slope * dx) * scale);
  ctx.stroke();
}

export default function DerivativeSim() {
  const canvasRef = useRef(null);
  const [x0, setX0] = useState(0);
  const [result, setResult] = useState(null);

  useEffect(() => {
    if (canvasRef.current) draw(canvasRef.current, x0);
  }, [x0]);

  const slope = fPrime(x0);

  const checkChallenge = () => {
    setResult(Math.abs(slope - TARGET_SLOPE) < 0.3);
  };

  return (
    <div>
      <p className="mb-2 text-sm text-slate-600">
        الدالة f(x) = x² — حرّك النقطة الحمراء لين ميل المماس (المشتقة) يساوي 4
      </p>
      <canvas ref={canvasRef} width={320} height={280} className="mx-auto rounded-xl bg-white" />
      <label className="mt-3 block text-sm">
        الموضع x: {x0.toFixed(1)} — الميل الحالي f&apos;(x) = {slope.toFixed(1)}
        <input
          type="range" min="-4" max="4" step="0.1" value={x0}
          onChange={(e) => setX0(Number(e.target.value))}
          className="w-full"
        />
      </label>
      <button
        onClick={checkChallenge}
        className="mt-3 w-full rounded-xl bg-slate-900 px-4 py-2 text-sm text-white hover:bg-slate-800"
      >
        تحقّق
      </button>
      {result !== null && (
        <p className={`mt-2 text-center text-sm ${result ? "text-emerald-600" : "text-red-600"}`}>
          {result ? "صحيح! عند x=2، الميل = 2×2 = 4" : "قريب، جرّب تحرّك النقطة أكثر"}
        </p>
      )}
    </div>
  );
}
