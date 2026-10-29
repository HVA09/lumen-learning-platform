import { useRef, useState } from "react";

const G = 9.8; // م/ث² — تسارع الجاذبية
const TARGET_RANGE = 20; // م — هدف: أصب هذي المسافة تقريبًا

function computeTrajectory(v0, angleDeg) {
  const angle = (angleDeg * Math.PI) / 180;
  const vx = v0 * Math.cos(angle);
  const vy = v0 * Math.sin(angle);
  const flightTime = (2 * vy) / G;
  const range = vx * flightTime;
  return { vx, vy, flightTime, range };
}

export default function ProjectileSim() {
  const canvasRef = useRef(null);
  const [v0, setV0] = useState(15);
  const [angle, setAngle] = useState(45);
  const [result, setResult] = useState(null);
  const [animating, setAnimating] = useState(false);

  const { flightTime, range } = computeTrajectory(v0, angle);

  const drawStatic = () => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    const w = canvas.width;
    const h = canvas.height;
    const scale = 6; // بكسل لكل متر
    const groundY = h - 20;

    ctx.clearRect(0, 0, w, h);
    ctx.strokeStyle = "#cbd5e1";
    ctx.beginPath();
    ctx.moveTo(0, groundY);
    ctx.lineTo(w, groundY);
    ctx.stroke();

    // علامة الهدف
    ctx.fillStyle = "#059669";
    ctx.fillRect(10 + TARGET_RANGE * scale - 3, groundY - 15, 6, 15);

    return { ctx, groundY, scale };
  };

  const launch = () => {
    const setup = drawStatic();
    if (!setup) return;
    const { ctx, groundY, scale } = setup;
    const { vx, vy } = computeTrajectory(v0, angle);

    setAnimating(true);
    let t = 0;
    const step = () => {
      t += 0.03;
      const x = vx * t;
      const y = vy * t - 0.5 * G * t * t;
      if (y < 0 || t > flightTime + 0.1) {
        setAnimating(false);
        return;
      }
      drawStatic();
      ctx.fillStyle = "#0f172a";
      ctx.beginPath();
      ctx.arc(10 + x * scale, groundY - y * scale, 5, 0, Math.PI * 2);
      ctx.fill();
      requestAnimationFrame(step);
    };
    requestAnimationFrame(step);
  };

  const checkChallenge = () => {
    setResult(Math.abs(range - TARGET_RANGE) < 1.5);
  };

  return (
    <div>
      <p className="mb-2 text-sm text-slate-600">
        اضبط السرعة والزاوية عشان توصل للهدف الأخضر (مسافة {TARGET_RANGE} م تقريبًا)
      </p>
      <canvas ref={canvasRef} width={320} height={220} className="mx-auto rounded-xl bg-white" />
      <div className="mt-3 space-y-2">
        <label className="block text-sm">
          السرعة الابتدائية: {v0} م/ث
          <input
            type="range" min="5" max="30" value={v0}
            onChange={(e) => setV0(Number(e.target.value))}
            className="w-full"
          />
        </label>
        <label className="block text-sm">
          الزاوية: {angle}°
          <input
            type="range" min="10" max="80" value={angle}
            onChange={(e) => setAngle(Number(e.target.value))}
            className="w-full"
          />
        </label>
      </div>
      <p className="mt-2 text-xs text-slate-400">
        المدى المتوقع: {range.toFixed(1)} م — زمن الطيران: {flightTime.toFixed(1)} ث
      </p>
      <div className="mt-3 grid grid-cols-2 gap-2">
        <button
          onClick={launch}
          disabled={animating}
          className="rounded-xl border border-slate-200 px-4 py-2 text-sm hover:bg-slate-50 disabled:opacity-50"
        >
          أطلق
        </button>
        <button
          onClick={checkChallenge}
          className="rounded-xl bg-slate-900 px-4 py-2 text-sm text-white hover:bg-slate-800"
        >
          تحقّق
        </button>
      </div>
      {result !== null && (
        <p className={`mt-2 text-center text-sm ${result ? "text-emerald-600" : "text-red-600"}`}>
          {result ? "أصبت الهدف! 🎯" : `قريب — مداك الحالي ${range.toFixed(1)} م`}
        </p>
      )}
    </div>
  );
}
