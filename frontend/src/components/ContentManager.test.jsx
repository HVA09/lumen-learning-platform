import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const curriculumApi = vi.hoisted(() => ({
  getSubjects: vi.fn(),
}));

const contentApi = vi.hoisted(() => ({
  createLesson: vi.fn(),
  createQuestion: vi.fn(),
  deleteLesson: vi.fn(),
  deleteQuestion: vi.fn(),
  getTopicAnalytics: vi.fn(),
  listTopicLessonsForTeacher: vi.fn(),
  listTopicQuestions: vi.fn(),
  updateLesson: vi.fn(),
  updateQuestion: vi.fn(),
}));

vi.mock("../lib/curriculumApi", () => curriculumApi);
vi.mock("../lib/contentApi", () => contentApi);
vi.mock("./MathText", () => ({
  default: ({ children }) => children,
}));

import ContentManager from "./ContentManager";

const subjects = [
  {
    id: 1,
    name_ar: "الرياضيات",
    topics: [
      { id: 10, name_ar: "التفاضل" },
      { id: 20, name_ar: "التكامل" },
    ],
  },
];

const lesson = {
  id: 21,
  title_ar: "الدرس الأول",
  body_md: "شرح أولي",
  estimated_minutes: 5,
  order_index: 1,
  is_published: true,
};

const question = {
  id: 31,
  kind: "mcq",
  prompt_ar: "ما قيمة ٢ + ٢؟",
  choices: ["٣", "٤"],
  correct_answer: 1,
  tolerance: null,
  explanation_ar: null,
  difficulty: 1,
  is_active: true,
};

beforeEach(() => {
  vi.clearAllMocks();
  curriculumApi.getSubjects.mockResolvedValue(subjects);
  contentApi.createLesson.mockResolvedValue({ id: 22 });
  contentApi.createQuestion.mockResolvedValue({ id: 32 });
  contentApi.deleteLesson.mockResolvedValue(undefined);
  contentApi.deleteQuestion.mockResolvedValue(undefined);
  contentApi.getTopicAnalytics.mockResolvedValue([]);
  contentApi.listTopicLessonsForTeacher.mockResolvedValue([]);
  contentApi.listTopicQuestions.mockResolvedValue([]);
  contentApi.updateLesson.mockResolvedValue({ ...lesson, title_ar: "درس محدث" });
  contentApi.updateQuestion.mockResolvedValue({ ...question, prompt_ar: "سؤال محدث" });
});

afterEach(() => {
  vi.restoreAllMocks();
});

describe("ContentManager", () => {
  it("loads subjects, selects the first topic, and lists its lessons", async () => {
    render(<ContentManager onClose={vi.fn()} />);

    expect(await screen.findByRole("combobox")).toHaveValue("10");
    expect(screen.getByRole("button", { name: "+ درس جديد" })).toBeInTheDocument();
    expect(contentApi.listTopicLessonsForTeacher).toHaveBeenCalledWith(10);
  });

  it("reloads the lesson list when the selected topic changes", async () => {
    const user = userEvent.setup();
    render(<ContentManager onClose={vi.fn()} />);
    const topicSelect = await screen.findByRole("combobox");

    await user.selectOptions(topicSelect, "20");
    await waitFor(() => {
      expect(contentApi.listTopicLessonsForTeacher).toHaveBeenCalledWith(20);
    });
  });

  it("creates a lesson with trimmed text and numeric fields", async () => {
    const user = userEvent.setup();
    render(<ContentManager onClose={vi.fn()} />);
    await screen.findByRole("combobox");
    await user.click(screen.getByRole("button", { name: "+ درس جديد" }));

    await user.type(screen.getByPlaceholderText("عنوان الدرس"), "  مقدمة في التفاضل  ");
    await user.type(
      screen.getByPlaceholderText(/محتوى الدرس/),
      "شرح قاعدة الاشتقاق"
    );
    const minutes = screen.getByLabelText("الدقائق التقديرية");
    await user.clear(minutes);
    await user.type(minutes, "12");
    const order = screen.getByLabelText("الترتيب");
    await user.clear(order);
    await user.type(order, "3");
    await user.click(screen.getByRole("checkbox", { name: "منشور (يظهر للطلاب)" }));

    await user.click(screen.getByRole("button", { name: "حفظ" }));

    expect(contentApi.createLesson).toHaveBeenCalledWith(10, {
      title_ar: "مقدمة في التفاضل",
      body_md: "شرح قاعدة الاشتقاق",
      estimated_minutes: 12,
      order_index: 3,
      is_published: false,
    });
  });

  it("edits an existing lesson using its identifier", async () => {
    contentApi.listTopicLessonsForTeacher
      .mockResolvedValueOnce([lesson])
      .mockResolvedValueOnce([{ ...lesson, title_ar: "درس محدث" }]);
    const user = userEvent.setup();
    render(<ContentManager onClose={vi.fn()} />);

    await user.click(await screen.findByRole("button", { name: "تعديل" }));
    const title = screen.getByPlaceholderText("عنوان الدرس");
    await user.clear(title);
    await user.type(title, "درس محدث");
    await user.click(screen.getByRole("button", { name: "حفظ" }));

    expect(contentApi.updateLesson).toHaveBeenCalledWith(
      lesson.id,
      expect.objectContaining({ title_ar: "درس محدث" })
    );
  });

  it("deletes a lesson only after confirmation", async () => {
    contentApi.listTopicLessonsForTeacher
      .mockResolvedValueOnce([lesson])
      .mockResolvedValueOnce([]);
    const confirm = vi.spyOn(window, "confirm").mockReturnValue(true);
    const user = userEvent.setup();
    render(<ContentManager onClose={vi.fn()} />);

    await screen.findByText("الدرس الأول");
    await user.click(screen.getByRole("button", { name: "حذف" }));

    expect(confirm).toHaveBeenCalledWith('حذف درس "الدرس الأول"؟');
    expect(contentApi.deleteLesson).toHaveBeenCalledWith(lesson.id);
    await waitFor(() => {
      expect(contentApi.listTopicLessonsForTeacher).toHaveBeenCalledTimes(2);
    });
  });

  it("creates an MCQ question with the selected answer index", async () => {
    const user = userEvent.setup();
    render(<ContentManager onClose={vi.fn()} />);
    await screen.findByRole("combobox");
    await user.click(screen.getByRole("button", { name: "الأسئلة" }));
    await user.click(await screen.findByRole("button", { name: "+ سؤال جديد" }));

    await user.type(
      screen.getByPlaceholderText(/نص السؤال/),
      "ما قيمة اثنين زائد اثنين؟"
    );
    await user.type(screen.getByPlaceholderText("خيار 1"), "٣");
    await user.type(screen.getByPlaceholderText("خيار 2"), "٤");
    await user.click(screen.getByRole("button", { name: "حفظ" }));

    expect(contentApi.createQuestion).toHaveBeenCalledWith(10, {
      kind: "mcq",
      prompt_ar: "ما قيمة اثنين زائد اثنين؟",
      choices: ["٣", "٤"],
      correct_answer: 0,
      tolerance: null,
      explanation_ar: null,
      difficulty: 1,
      is_active: true,
    });
  });

  it("maps numeric question answers and tolerance to the API payload", async () => {
    const user = userEvent.setup();
    render(<ContentManager onClose={vi.fn()} />);
    await screen.findByRole("combobox");
    await user.click(screen.getByRole("button", { name: "الأسئلة" }));
    await user.click(await screen.findByRole("button", { name: "+ سؤال جديد" }));

    await user.selectOptions(screen.getAllByRole("combobox")[1], "numeric");
    await user.type(
      screen.getByPlaceholderText(/نص السؤال/),
      "احسب قيمة التعبير"
    );
    await user.type(screen.getByPlaceholderText("الإجابة الصحيحة"), "4.5");
    await user.type(screen.getByPlaceholderText("هامش الخطأ (اختياري)"), "0.1");
    await user.click(screen.getByRole("button", { name: "حفظ" }));

    expect(contentApi.createQuestion).toHaveBeenCalledWith(10, {
      kind: "numeric",
      prompt_ar: "احسب قيمة التعبير",
      choices: null,
      correct_answer: "4.5",
      tolerance: 0.1,
      explanation_ar: null,
      difficulty: 1,
      is_active: true,
    });
  });

  it("displays question analytics and the review count", async () => {
    contentApi.getTopicAnalytics.mockResolvedValueOnce([
      {
        question_id: 31,
        prompt_ar: "ما قيمة ٢ + ٢؟",
        success_rate: 80,
        correct: 4,
        answered: 5,
        flag: "check_answer_key",
        flag_label_ar: "راجع مفتاح الإجابة",
        difficulty: 1,
        top_wrong_answer: "٣",
        top_wrong_count: 1,
      },
    ]);
    const user = userEvent.setup();
    render(<ContentManager onClose={vi.fn()} />);
    await screen.findByRole("combobox");
    await user.click(screen.getByRole("button", { name: "التحليلات" }));

    expect(await screen.findByText("إجابة مسجّلة")).toBeInTheDocument();
    expect(screen.getByText("سؤال يحتاج مراجعة")).toBeInTheDocument();
    expect(screen.getByText("راجع مفتاح الإجابة")).toBeInTheDocument();
    expect(contentApi.getTopicAnalytics).toHaveBeenCalledWith(10);
  });

  it("deletes a question only after confirmation", async () => {
    contentApi.listTopicQuestions
      .mockResolvedValueOnce([question])
      .mockResolvedValueOnce([]);
    const confirm = vi.spyOn(window, "confirm").mockReturnValue(true);
    const user = userEvent.setup();
    render(<ContentManager onClose={vi.fn()} />);
    await screen.findByRole("combobox");
    await user.click(screen.getByRole("button", { name: "الأسئلة" }));

    await screen.findByText(question.prompt_ar);
    await user.click(screen.getByRole("button", { name: "حذف" }));

    expect(confirm).toHaveBeenCalledWith("حذف هذا السؤال؟");
    expect(contentApi.deleteQuestion).toHaveBeenCalledWith(question.id);
    await waitFor(() => {
      expect(contentApi.listTopicQuestions).toHaveBeenCalledTimes(2);
    });
  });

  it("calls onClose when the content manager is closed", async () => {
    const onClose = vi.fn();
    const user = userEvent.setup();
    render(<ContentManager onClose={onClose} />);

    await user.click(screen.getByRole("button", { name: "✕" }));
    expect(onClose).toHaveBeenCalledTimes(1);
  });
});
