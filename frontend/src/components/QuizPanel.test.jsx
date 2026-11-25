import React from "react";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("../lib/quizApi", () => ({
  startQuiz: vi.fn(),
  saveDraftAnswers: vi.fn(),
  submitQuiz: vi.fn(),
}));

import { saveDraftAnswers, startQuiz, submitQuiz } from "../lib/quizApi";
import QuizPanel from "./QuizPanel";

const attempt = {
  attempt_id: 3,
  topic_id: 1,
  mode: "practice",
  pass_percentage: null,
  resumed: false,
  saved_answers: {},
  questions: [{ id: 1, kind: "mcq", prompt_ar: "ما مشتقة $x^2$؟", choices: ["$x$", "$2x$"], difficulty: 1 }],
};

beforeEach(() => {
  vi.clearAllMocks();
  startQuiz.mockResolvedValue(attempt);
  saveDraftAnswers.mockResolvedValue({ answer_count: 1 });
  submitQuiz.mockResolvedValue({ score_percentage: 100, correct_count: 1, total: 1, mode: "practice", results: [] });
});

describe("QuizPanel", () => {
  it("يطلب بدء الاختبار مرة واحدة فقط حتى تحت StrictMode (يعيد تشغيل الـ effects بالتطوير)", async () => {
    render(
      <React.StrictMode>
        <QuizPanel topicId={1} mode="practice" onClose={vi.fn()} onFinished={vi.fn()} />
      </React.StrictMode>
    );
    await screen.findByText(/سلّم الإجابات/);
    expect(startQuiz).toHaveBeenCalledTimes(1);
  });

  it("يعيد عرض الإجابة المحفوظة عند استئناف المحاولة", async () => {
    startQuiz.mockResolvedValueOnce({ ...attempt, resumed: true, saved_answers: { "1": 1 } });
    render(<QuizPanel topicId={1} mode="practice" onClose={vi.fn()} onFinished={vi.fn()} />);
    const radios = await screen.findAllByRole("radio");
    expect(radios[1]).toBeChecked();
    expect(saveDraftAnswers).not.toHaveBeenCalled();
  });

  it("يحفظ التغييرات تلقائيًا بعد مهلة قصيرة", async () => {
    render(<QuizPanel topicId={1} mode="practice" onClose={vi.fn()} onFinished={vi.fn()} />);
    fireEvent.click((await screen.findAllByRole("radio"))[1]);

    await waitFor(() => expect(saveDraftAnswers).toHaveBeenCalledTimes(1), { timeout: 2000 });
    expect(saveDraftAnswers).toHaveBeenCalledWith(3, [
      { question_id: 1, answer: 1 },
    ]);
    expect(await screen.findByText("تم حفظ الإجابات")).toBeInTheDocument();
  });

  it("خيارات الاختيار من متعدد تُعرض كمعادلات مصوّرة", async () => {
    render(<QuizPanel topicId={1} mode="practice" onClose={vi.fn()} onFinished={vi.fn()} />);
    const radios = await screen.findAllByRole("radio");
    expect(radios).toHaveLength(2);
    await waitFor(() => expect(radios[1].closest("label").querySelector(".katex")).not.toBeNull());
    expect(radios[1].closest("label")).not.toHaveTextContent("$");
  });

  it("يعرض عنوان الاختبار بحسب الوضع، ورسالة الخطأ لو فشل البدء", async () => {
    startQuiz.mockRejectedValue({ response: { data: { detail: "لا توجد أسئلة لهذا الموضوع بعد" } } });
    render(<QuizPanel topicId={1} mode="gateway" onClose={vi.fn()} onFinished={vi.fn()} />);
    expect(screen.getByText("اختبار البوابة")).toBeInTheDocument();
    expect(await screen.findByText("لا توجد أسئلة لهذا الموضوع بعد")).toBeInTheDocument();
  });
});
