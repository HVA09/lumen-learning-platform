import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("../lib/reportsApi", () => ({
  getMyProgress: vi.fn(),
  sendMyReport: vi.fn(),
}));

import { getMyProgress } from "../lib/reportsApi";
import ProgressPanel from "./ProgressPanel";

beforeEach(() => {
  vi.clearAllMocks();
});

describe("ProgressPanel", () => {
  it("يعرض رسالة وإعادة المحاولة عند فشل تحميل التقرير", async () => {
    getMyProgress
      .mockRejectedValueOnce(new Error("network unavailable"))
      .mockResolvedValueOnce({
        average_mastery: 50,
        gateway_quizzes_passed: 1,
        lessons_completed: 2,
        quizzes_taken: 3,
        average_quiz_score: 70,
        streak_days: 2,
        achievements_unlocked: 1,
        assignments_submitted: 1,
        cards_due_now: 0,
        weak_topics: [],
      });

    const user = userEvent.setup();
    render(<ProgressPanel onClose={vi.fn()} />);

    expect(await screen.findByText(/تعذر تحميل تقرير التقدم/)).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "إعادة المحاولة" }));
    expect(await screen.findByText("50%")).toBeInTheDocument();
  });
});
