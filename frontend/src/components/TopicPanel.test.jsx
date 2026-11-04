import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("../lib/curriculumApi", () => ({
  getTopic: vi.fn(),
  getTopicLessons: vi.fn(),
  getTopicMastery: vi.fn(),
  completeLesson: vi.fn(),
}));
vi.mock("../lib/quizApi", () => ({
  startQuiz: vi.fn(),
  submitQuiz: vi.fn(),
  getQuizHistory: vi.fn(),
}));
// المختبر يحمّل محاكاة ثقيلة — غير مهم لهذه الاختبارات
vi.mock("./LabPanel", () => ({ default: () => null }));

import { completeLesson, getTopic, getTopicLessons, getTopicMastery } from "../lib/curriculumApi";
import { getQuizHistory, startQuiz, submitQuiz } from "../lib/quizApi";
import TopicPanel from "./TopicPanel";

const topic = {
  id: 1,
  name_ar: "المعادلات الخطية",
  learning_outcomes_ar: ["يحل معادلة خطية بمتغيّر واحد"],
  simulation_type: null,
};
const lessons = [
  {
    id: 11,
    topic_id: 1,
    slug: "solving",
    title_ar: "كيف نحلّ المعادلة؟",
    body_md: "## عنوان\n\nالمعادلة $2x + 3 = 7$ نحلّها هكذا.",
    estimated_minutes: 6,
    order_index: 1,
    completed: false,
  },
];
const attempt = {
  attempt_id: 10,
  topic_id: 1,
  mode: "practice",
  pass_percentage: null,
  resumed: false,
  questions: [
    { id: 1, kind: "true_false", prompt_ar: "المعادلة $x^2 + 1 = 5$ خطية.", choices: ["صحيح", "خطأ"], difficulty: 1 },
    { id: 2, kind: "numeric", prompt_ar: "حلّ $3x = 21$. ما قيمة $x$؟", choices: null, difficulty: 1 },
  ],
};
const quizResult = {
  attempt_id: 10,
  topic_id: 1,
  mode: "practice",
  score_percentage: 50,
  correct_count: 1,
  total: 2,
  passed: null,
  mastery_percentage: 50,
  gateway_quiz_passed: false,
  new_achievements: [{ key: "first_quiz", title_ar: "أول اختبار" }],
  results: [
    { question_id: 1, kind: "true_false", prompt_ar: "المعادلة $x^2 + 1 = 5$ خطية.", choices: ["صحيح", "خطأ"], correct: true, given_answer: false, correct_answer_text: "خطأ", explanation_ar: "المجهول مرفوع للأس 2." },
    { question_id: 2, kind: "numeric", prompt_ar: "حلّ $3x = 21$. ما قيمة $x$؟", choices: null, correct: false, given_answer: "5", correct_answer_text: "7", explanation_ar: "نقسم على 3 فيكون $x = 7$." },
  ],
};

function renderPanel(overrides = {}) {
  const props = { topicId: 1, onClose: vi.fn(), isTeacher: false, onManageContent: vi.fn(), onAchievements: vi.fn(), ...overrides };
  render(<TopicPanel {...props} />);
  return props;
}

beforeEach(() => {
  vi.clearAllMocks();
  getTopic.mockResolvedValue(topic);
  getTopicLessons.mockResolvedValue(lessons);
  getTopicMastery.mockResolvedValue({ topic_id: 1, mastery_percentage: 0, gateway_quiz_passed: false, attempts_count: 0, last_practiced_at: null });
  getQuizHistory.mockResolvedValue([]);
  startQuiz.mockResolvedValue(attempt);
  submitQuiz.mockResolvedValue(quizResult);
});

describe("TopicPanel — الدروس", () => {
  it("يعرض الدروس والمخرجات، وفتح الدرس يصوّر المعادلات بدون $ ظاهرة", async () => {
    const user = userEvent.setup();
    renderPanel();
    expect(await screen.findByText("يحل معادلة خطية بمتغيّر واحد")).toBeInTheDocument();

    await user.click(await screen.findByText("كيف نحلّ المعادلة؟"));
    const body = await screen.findByText(/نحلّها هكذا/);
    expect(body.closest(".lesson-content")).not.toBeNull();
    await waitFor(() => expect(body.closest(".lesson-content").querySelector(".katex")).not.toBeNull());
    expect(body.closest(".lesson-content")).not.toHaveTextContent("$");
  });

  it("إنهاء الدرس ينادي completeLesson ويبلّغ عن الإنجازات الجديدة", async () => {
    completeLesson.mockResolvedValue({ lesson_id: 11, completed: true, new_achievements: [{ key: "first_lesson", title_ar: "بداية المعرفة" }] });
    const user = userEvent.setup();
    const { onAchievements } = renderPanel();

    await user.click(await screen.findByText("كيف نحلّ المعادلة؟"));
    await user.click(await screen.findByRole("button", { name: "أنهيت هذا الدرس" }));

    expect(completeLesson).toHaveBeenCalledWith(11);
    expect(onAchievements).toHaveBeenCalledWith([{ key: "first_lesson", title_ar: "بداية المعرفة" }]);
    expect(await screen.findByText("✓ أنهيت هذا الدرس")).toBeInTheDocument();
  });
});

describe("TopicPanel — الاختبارات", () => {
  async function takeQuiz(user) {
    await user.click(await screen.findByText("📝 اختبار تدريبي"));
    await user.click(await screen.findByRole("radio", { name: "خطأ" }));
    await user.type(screen.getByPlaceholderText("اكتب رقمًا..."), "5");
    await user.click(screen.getByText(/سلّم الإجابات/));
  }

  it("نتيجة الاختبار تبقى ظاهرة بعد التسليم ولا تُغلق النافذة تلقائيًا", async () => {
    // انحدار: كان TopicPanel يغلق نافذة الاختبار فور وصول النتيجة فلا يرى الطالب درجته ولا الشرح
    const user = userEvent.setup();
    renderPanel();
    await takeQuiz(user);

    expect(await screen.findByText("1 من 2 صحيحة")).toBeInTheDocument();
    expect(screen.getByText("50%", { selector: "p" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "إغلاق" })).toBeInTheDocument();
    expect(screen.getByText(/نقسم على 3 فيكون/)).toBeInTheDocument();
    expect(submitQuiz).toHaveBeenCalledWith(10, [
      { question_id: 1, answer: false },
      { question_id: 2, answer: "5" },
    ]);
  });

  it("المعادلات في النتائج والشرح مصوّرة بدون $ ظاهرة", async () => {
    const user = userEvent.setup();
    renderPanel();
    await takeQuiz(user);
    const explanation = await screen.findByText(/نقسم على 3 فيكون/);
    await waitFor(() => expect(explanation.querySelector(".katex")).not.toBeNull());
    expect(explanation).not.toHaveTextContent("$");
  });

  it("الإغلاق يُظهر الإتقان المحدّث خلف النافذة ويبلّغ عن الإنجازات", async () => {
    const user = userEvent.setup();
    const { onAchievements } = renderPanel();
    await takeQuiz(user);
    await user.click(await screen.findByRole("button", { name: "إغلاق" }));

    expect(screen.queryByText("1 من 2 صحيحة")).not.toBeInTheDocument();
    expect(await screen.findByText("50%")).toBeInTheDocument();
    expect(onAchievements).toHaveBeenCalledWith([{ key: "first_quiz", title_ar: "أول اختبار" }]);
    expect(getQuizHistory).toHaveBeenCalledTimes(2); // عند الفتح وبعد التسليم
  });

  it("اختبار البوابة يبدأ بوضع gateway", async () => {
    const user = userEvent.setup();
    renderPanel();
    await user.click(await screen.findByText("🚪 اختبار البوابة"));
    expect(startQuiz).toHaveBeenCalledWith(1, "gateway");
  });

  it("رسالة السيرفر (مثل مهلة إعادة البوابة) تظهر كما هي", async () => {
    startQuiz.mockRejectedValue({ response: { data: { detail: "راجع الدرس أولًا ثم أعد اختبار البوابة بعد 4 دقيقة" } } });
    const user = userEvent.setup();
    renderPanel();
    await user.click(await screen.findByText("🚪 اختبار البوابة"));
    expect(await screen.findByText("راجع الدرس أولًا ثم أعد اختبار البوابة بعد 4 دقيقة")).toBeInTheDocument();
  });
});

describe("TopicPanel — صلاحيات المعلّم", () => {
  it("زر إدارة المحتوى يظهر للمعلّم فقط وينادي onManageContent", async () => {
    const user = userEvent.setup();
    const { onManageContent } = renderPanel({ isTeacher: true });
    await user.click(await screen.findByText("⚙️ إدارة دروس وأسئلة هذا الموضوع"));
    expect(onManageContent).toHaveBeenCalledWith(1);
  });

  it("الطالب لا يرى زر إدارة المحتوى", async () => {
    renderPanel({ isTeacher: false });
    await screen.findByText("📝 اختبار تدريبي");
    expect(screen.queryByText("⚙️ إدارة دروس وأسئلة هذا الموضوع")).not.toBeInTheDocument();
  });
});
