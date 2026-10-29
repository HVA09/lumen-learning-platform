import { useEffect, useState } from "react";
import { getLearningPath } from "../lib/curriculumApi";
import { getMyStats } from "../lib/gamificationApi";

const STATUS_LABELS = {
  locked: "مقفل",
  available: "متاح",
  in_progress: "قيد الدراسة",
  mastered: "مُتقَن",
};

const STATUS_STYLES = {
  locked: "border-slate-200 bg-slate-50 opacity-60",
  available: "border-slate-200 bg-white hover:bg-slate-50",
  in_progress: "border-amber-200 bg-amber-50 hover:bg-amber-100",
  mastered: "border-emerald-200 bg-emerald-50 hover:bg-emerald-100",
};

function TopicCard({ topic, isRecommended, onSelect }) {
  const locked = topic.status === "locked";
  return (
    <button
      onClick={() => !locked && onSelect(topic.id)}
      disabled={locked}
      className={`w-full rounded-2xl border p-4 text-start transition ${STATUS_STYLES[topic.status]} ${
        locked ? "cursor-not-allowed" : ""
      } ${isRecommended ? "ring-2 ring-slate-900" : ""}`}
    >
      <div className="flex items-start justify-between gap-2">
        <div>
          <p className="font-medium text-slate-900">
            {locked ? "🔒 " : topic.status === "mastered" ? "✅ " : ""}
            {topic.name_ar}
          </p>
          {isRecommended && (
            <span className="mt-1 inline-block rounded-full bg-slate-900 px-2 py-0.5 text-[10px] text-white">
              التالي المقترح
            </span>
          )}
        </div>
        <span className="shrink-0 text-xs text-slate-500">{STATUS_LABELS[topic.status]}</span>
      </div>

      {locked ? (
        <p className="mt-2 text-xs text-slate-400">
          يحتاج اجتياز بوابة «{topic.prerequisite_name_ar}» أولًا
        </p>
      ) : (
        <>
          <div className="mt-3 h-1.5 w-full overflow-hidden rounded-full bg-slate-100">
            <div
              className="h-full rounded-full bg-slate-900"
              style={{ width: `${topic.mastery_percentage}%` }}
            />
          </div>
          <div className="mt-1.5 flex items-center justify-between text-xs text-slate-400">
            <span>{Math.round(topic.mastery_percentage)}% إتقان</span>
            <span>
              {topic.lessons_completed}/{topic.lessons_total} دروس
            </span>
          </div>
        </>
      )}
    </button>
  );
}

export default function LearningPath({ onSelectTopic }) {
  const [path, setPath] = useState(null);
  const [stats, setStats] = useState(null);
  const [error, setError] = useState("");

  const refresh = () => {
    Promise.all([getLearningPath(), getMyStats()])
      .then(([pathData, statsData]) => {
        setPath(pathData);
        setStats(statsData);
      })
      .catch(() => setError("تعذر تحميل مسار التعلّم"));
  };

  useEffect(refresh, []);

  if (error) {
    return (
      <div className="flex h-full items-center justify-center text-sm text-red-600">{error}</div>
    );
  }
  if (!path) {
    return <div className="flex h-full items-center justify-center text-sm text-slate-400">...</div>;
  }

  return (
    <div className="flex-1 space-y-6 overflow-y-auto p-4">
      <div className="rounded-3xl border border-slate-200 bg-white p-5">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <p className="text-sm text-slate-500">إتقانك الإجمالي</p>
            <p className="text-2xl font-semibold text-slate-900">{path.overall_mastery}%</p>
          </div>
          <div>
            <p className="text-sm text-slate-500">مواضيع مُتقَنة</p>
            <p className="text-2xl font-semibold text-slate-900">
              {path.topics_mastered}/{path.topics_total}
            </p>
          </div>
          {stats && (
            <div>
              <p className="text-sm text-slate-500">أيام متتالية</p>
              <p className="text-2xl font-semibold text-slate-900">
                🔥 {stats.streak_days}
                {!stats.studied_today && stats.streak_days > 0 && (
                  <span className="ms-1 text-xs font-normal text-amber-600">— ادرس اليوم!</span>
                )}
              </p>
            </div>
          )}
        </div>
      </div>

      {path.subjects.map((subject) => (
        <div key={subject.id}>
          <h3 className="mb-3 text-sm font-semibold text-slate-500">{subject.name_ar}</h3>
          <div className="grid gap-3 sm:grid-cols-2">
            {subject.topics.map((topic) => (
              <TopicCard
                key={topic.id}
                topic={topic}
                isRecommended={topic.id === path.recommended_topic_id}
                onSelect={onSelectTopic}
              />
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}
