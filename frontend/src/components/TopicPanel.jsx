import { useEffect, useState } from "react";
import { completeLesson, getTopic, getTopicLessons, getTopicMastery } from "../lib/curriculumApi";
import { getQuizHistory } from "../lib/quizApi";
import LabPanel from "./LabPanel";
import MathText from "./MathText";
import QuizPanel from "./QuizPanel";

function LessonReader({ lesson, onBack, onCompleted }) {
  const [completing, setCompleting] = useState(false);

  const handleComplete = async () => {
    setCompleting(true);
    try {
      const result = await completeLesson(lesson.id);
      onCompleted(lesson.id, result.new_achievements);
    } finally {
      setCompleting(false);
    }
  };

  return (
    <div>
      <button onClick={onBack} className="mb-3 text-sm text-slate-500 hover:text-slate-700">
        ← رجوع للدروس
      </button>
      <h3 className="mb-3 text-lg font-semibold text-slate-900">{lesson.title_ar}</h3>
      <MathText className="lesson-content">{lesson.body_md}</MathText>
      {lesson.completed ? (
        <p className="mt-4 rounded-xl border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-700">
          ✓ أنهيت هذا الدرس
        </p>
      ) : (
        <button
          onClick={handleComplete}
          disabled={completing}
          className="mt-4 w-full rounded-xl bg-slate-900 px-4 py-2 text-sm text-white hover:bg-slate-800 disabled:opacity-50"
        >
          {completing ? "..." : "أنهيت هذا الدرس"}
        </button>
      )}
    </div>
  );
}

export default function TopicPanel({ topicId, onClose, isTeacher, onManageContent, onAchievements }) {
  const [topic, setTopic] = useState(null);
  const [lessons, setLessons] = useState([]);
  const [mastery, setMastery] = useState(null);
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [selectedLesson, setSelectedLesson] = useState(null);
  const [showLab, setShowLab] = useState(false);
  const [quizMode, setQuizMode] = useState(null); // "practice" | "gateway" | null

  const refresh = () => {
    setLoading(true);
    Promise.all([
      getTopic(topicId),
      getTopicLessons(topicId),
      getTopicMastery(topicId),
      getQuizHistory(topicId),
    ])
      .then(([topicData, lessonsData, masteryData, historyData]) => {
        setTopic(topicData);
        setLessons(lessonsData);
        setMastery(masteryData);
        setHistory(historyData);
      })
      .catch(() => setError("تعذر تحميل الموضوع"))
      .finally(() => setLoading(false));
  };

  useEffect(refresh, [topicId]);

  const handleLessonCompleted = (lessonId, newAchievements) => {
    setLessons((prev) => prev.map((l) => (l.id === lessonId ? { ...l, completed: true } : l)));
    setSelectedLesson((prev) => (prev ? { ...prev, completed: true } : prev));
    if (newAchievements?.length) onAchievements?.(newAchievements);
  };

  // يُستدعى فور وصول نتيجة التسليم: نحدّث الإتقان والسجل خلف النافذة، لكن لا نغلقها —
  // الطالب يقرأ درجته وشرح كل سؤال، ثم يغلقها بزر "إغلاق" (QuizPanel.onClose)
  const handleQuizFinished = (result) => {
    setMastery({
      topic_id: topicId,
      mastery_percentage: result.mastery_percentage,
      gateway_quiz_passed: result.gateway_quiz_passed,
      attempts_count: (mastery?.attempts_count ?? 0) + 1,
      last_practiced_at: new Date().toISOString(),
    });
    getQuizHistory(topicId).then(setHistory).catch(() => {});
    if (result.new_achievements?.length) onAchievements?.(result.new_achievements);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center overflow-y-auto bg-black/30 p-4">
      <div className="my-8 w-full max-w-lg rounded-3xl border border-slate-200 bg-white p-6 shadow-lg">
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-lg font-semibold text-slate-900">{topic?.name_ar || "..."}</h2>
          <button
            onClick={onClose}
            className="rounded-lg px-2 py-1 text-slate-400 hover:bg-slate-100 focus:outline-none focus:ring-2 focus:ring-slate-400"
          >
            ✕
          </button>
        </div>

        {loading ? (
          <p className="text-sm text-slate-400">...</p>
        ) : error ? (
          <p className="text-sm text-red-600">{error}</p>
        ) : selectedLesson ? (
          <LessonReader
            lesson={selectedLesson}
            onBack={() => setSelectedLesson(null)}
            onCompleted={handleLessonCompleted}
          />
        ) : (
          <>
            {topic.learning_outcomes_ar?.length > 0 && (
              <ul className="mb-4 list-inside list-disc space-y-1 text-sm text-slate-600">
                {topic.learning_outcomes_ar.map((outcome) => (
                  <li key={outcome}>{outcome}</li>
                ))}
              </ul>
            )}

            <div className="mb-4 rounded-2xl border border-slate-200 p-3">
              <div className="flex items-center justify-between text-sm">
                <span className="text-slate-600">الإتقان</span>
                <span className="font-medium text-slate-900">
                  {Math.round(mastery.mastery_percentage)}%
                  {mastery.gateway_quiz_passed && " ✅"}
                </span>
              </div>
              <div className="mt-2 h-1.5 w-full overflow-hidden rounded-full bg-slate-100">
                <div
                  className="h-full rounded-full bg-slate-900"
                  style={{ width: `${mastery.mastery_percentage}%` }}
                />
              </div>
            </div>

            <p className="mb-2 text-sm font-medium text-slate-900">الدروس</p>
            <div className="mb-4 space-y-2">
              {lessons.length === 0 && <p className="text-sm text-slate-400">لا توجد دروس بعد</p>}
              {lessons.map((lesson) => (
                <button
                  key={lesson.id}
                  onClick={() => setSelectedLesson(lesson)}
                  className="flex w-full items-center justify-between rounded-xl border border-slate-200 px-3 py-2 text-start text-sm hover:bg-slate-50"
                >
                  <span className="text-slate-900">
                    {lesson.completed ? "✓ " : ""}
                    {lesson.title_ar}
                  </span>
                  <span className="shrink-0 text-xs text-slate-400">{lesson.estimated_minutes} د</span>
                </button>
              ))}
            </div>

            <div className="grid grid-cols-2 gap-2">
              <button
                onClick={() => setQuizMode("practice")}
                className="rounded-xl border border-slate-200 px-3 py-2 text-sm hover:bg-slate-50"
              >
                📝 اختبار تدريبي
              </button>
              <button
                onClick={() => setQuizMode("gateway")}
                className="rounded-xl border border-slate-900 bg-slate-900 px-3 py-2 text-sm text-white hover:bg-slate-800"
              >
                🚪 اختبار البوابة
              </button>
            </div>

            {topic.simulation_type && (
              <button
                onClick={() => setShowLab(true)}
                className="mt-2 w-full rounded-xl border border-slate-200 px-3 py-2 text-sm hover:bg-slate-50"
              >
                🧪 افتح المختبر
              </button>
            )}

            {isTeacher && (
              <button
                onClick={() => onManageContent(topicId)}
                className="mt-2 w-full rounded-xl border border-slate-200 px-3 py-2 text-sm text-slate-600 hover:bg-slate-50"
              >
                ⚙️ إدارة دروس وأسئلة هذا الموضوع
              </button>
            )}

            {history.length > 0 && (
              <div className="mt-4">
                <p className="mb-2 text-xs font-medium text-slate-500">آخر المحاولات</p>
                <div className="space-y-1">
                  {history.map((h) => (
                    <div
                      key={h.id}
                      className="flex items-center justify-between rounded-lg border border-slate-100 px-2 py-1 text-xs text-slate-500"
                    >
                      <span>{h.mode === "gateway" ? "بوابة" : "تدريب"}</span>
                      <span>{Math.round(h.score_percentage ?? 0)}%</span>
                      <span>{h.submitted_at ? new Date(h.submitted_at).toLocaleDateString() : ""}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </>
        )}
      </div>

      {showLab && (
        <LabPanel
          simulationType={topic.simulation_type}
          topicName={topic.name_ar}
          onClose={() => setShowLab(false)}
        />
      )}

      {quizMode && (
        <QuizPanel
          topicId={topicId}
          mode={quizMode}
          onClose={() => setQuizMode(null)}
          onFinished={handleQuizFinished}
        />
      )}
    </div>
  );
}
