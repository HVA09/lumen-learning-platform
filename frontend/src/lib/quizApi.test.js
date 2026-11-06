import { beforeEach, describe, expect, it, vi } from "vitest";

const api = vi.hoisted(() => ({
  get: vi.fn(),
  post: vi.fn(),
}));

vi.mock("./api", () => ({ default: api }));

import { getQuizHistory, startQuiz, submitQuiz } from "./quizApi";

describe("quiz API adapters", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("starts a practice quiz by default", async () => {
    const attempt = { id: 14, questions: [] };
    api.post.mockResolvedValueOnce({ data: attempt });

    await expect(startQuiz(8)).resolves.toEqual(attempt);
    expect(api.post).toHaveBeenCalledWith("/quiz/topics/8/start", { mode: "practice" });
  });

  it("passes a selected quiz mode to the start endpoint", async () => {
    api.post.mockResolvedValueOnce({ data: { id: 15 } });

    await startQuiz(9, "gateway");
    expect(api.post).toHaveBeenCalledWith("/quiz/topics/9/start", { mode: "gateway" });
  });

  it("submits answers for the selected attempt", async () => {
    const result = { score_percentage: 80, passed: true };
    const answers = [{ question_id: 2, selected_choice: "b" }];
    api.post.mockResolvedValueOnce({ data: result });

    await expect(submitQuiz(41, answers)).resolves.toEqual(result);
    expect(api.post).toHaveBeenCalledWith("/quiz/attempts/41/submit", { answers });
  });

  it("loads quiz history for a topic", async () => {
    const history = [{ id: 41, score_percentage: 80 }];
    api.get.mockResolvedValueOnce({ data: history });

    await expect(getQuizHistory(8)).resolves.toEqual(history);
    expect(api.get).toHaveBeenCalledWith("/quiz/topics/8/history");
  });
});
