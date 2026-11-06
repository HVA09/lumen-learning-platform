import { act, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

const curriculumApi = vi.hoisted(() => ({
  getLearningPath: vi.fn(),
}));
const gamificationApi = vi.hoisted(() => ({
  getMyStats: vi.fn(),
}));

vi.mock("../lib/curriculumApi", () => curriculumApi);
vi.mock("../lib/gamificationApi", () => gamificationApi);

import LearningPath from "./LearningPath";

const pathFixture = {
  overall_mastery: 42.4,
  topics_mastered: 1,
  topics_total: 4,
  recommended_topic_id: 2,
  subjects: [
    {
      id: 10,
      name_ar: "أساسيات البرمجة",
      topics: [
        {
          id: 1,
          name_ar: "مقدمة البرمجة",
          status: "mastered",
          mastery_percentage: 100,
          lessons_completed: 5,
          lessons_total: 5,
        },
        {
          id: 2,
          name_ar: "المتغيرات",
          status: "available",
          mastery_percentage: 0,
          lessons_completed: 0,
          lessons_total: 3,
        },
        {
          id: 3,
          name_ar: "الشروط",
          status: "locked",
          prerequisite_name_ar: "المتغيرات",
          mastery_percentage: 0,
          lessons_completed: 0,
          lessons_total: 4,
        },
        {
          id: 4,
          name_ar: "الحلقات",
          status: "in_progress",
          mastery_percentage: 63.8,
          lessons_completed: 2,
          lessons_total: 4,
        },
      ],
    },
  ],
};

const statsFixture = {
  streak_days: 3,
  studied_today: false,
};

beforeEach(() => {
  vi.clearAllMocks();
  curriculumApi.getLearningPath.mockResolvedValue(pathFixture);
  gamificationApi.getMyStats.mockResolvedValue(statsFixture);
});

describe("LearningPath", () => {
  it("shows a loading state until the learning path is available", async () => {
    let resolvePath;
    curriculumApi.getLearningPath.mockReturnValue(
      new Promise((resolve) => {
        resolvePath = resolve;
      })
    );

    render(<LearningPath onSelectTopic={vi.fn()} />);

    expect(screen.getByText("...")).toBeInTheDocument();
    expect(curriculumApi.getLearningPath).toHaveBeenCalledTimes(1);
    expect(gamificationApi.getMyStats).toHaveBeenCalledTimes(1);

    await act(async () => {
      resolvePath(pathFixture);
    });

    expect(await screen.findByText("إتقانك الإجمالي")).toBeInTheDocument();
  });

  it("renders mastery totals, subjects, topic states, recommendations, and streak stats", async () => {
    render(<LearningPath onSelectTopic={vi.fn()} />);

    expect(await screen.findByText("إتقانك الإجمالي")).toBeInTheDocument();
    expect(screen.getByText("42.4%")).toBeInTheDocument();
    expect(screen.getByText("1/4")).toBeInTheDocument();
    expect(screen.getByText("أساسيات البرمجة")).toBeInTheDocument();

    expect(screen.getByText("مقدمة البرمجة")).toBeInTheDocument();
    expect(screen.getByText("✅ " + "مقدمة البرمجة")).toBeInTheDocument();
    expect(screen.getByText("المتغيرات")).toBeInTheDocument();
    expect(screen.getByText("التالي المقترح")).toBeInTheDocument();
    expect(screen.getByText("الشروط")).toBeInTheDocument();
    expect(screen.getByText("مقفل")).toBeInTheDocument();
    expect(screen.getByText("قيد الدراسة")).toBeInTheDocument();
    expect(screen.getByText("64% إتقان")).toBeInTheDocument();
    expect(screen.getByText("2/4 دروس")).toBeInTheDocument();

    expect(screen.getByText("أيام متتالية")).toBeInTheDocument();
    expect(screen.getByText("🔥 3")).toBeInTheDocument();
    expect(screen.getByText("— ادرس اليوم!")).toBeInTheDocument();
  });

  it("prevents selection of locked topics and selects an available topic", async () => {
    const onSelectTopic = vi.fn();
    const user = userEvent.setup();
    render(<LearningPath onSelectTopic={onSelectTopic} />);

    const lockedTopic = await screen.findByRole("button", { name: /الشروط/ });
    const availableTopic = screen.getByRole("button", { name: /المتغيرات/ });

    expect(lockedTopic).toBeDisabled();
    await user.click(lockedTopic);
    expect(onSelectTopic).not.toHaveBeenCalled();

    expect(availableTopic).toBeEnabled();
    await user.click(availableTopic);
    expect(onSelectTopic).toHaveBeenCalledTimes(1);
    expect(onSelectTopic).toHaveBeenCalledWith(2);
  });

  it("keeps the curriculum visible when optional streak statistics fail", async () => {
    gamificationApi.getMyStats.mockRejectedValueOnce(
      new Error("gamification service unavailable")
    );

    render(<LearningPath onSelectTopic={vi.fn()} />);

    expect(await screen.findByText("إتقانك الإجمالي")).toBeInTheDocument();
    expect(screen.getByText("أساسيات البرمجة")).toBeInTheDocument();
    expect(screen.queryByText("تعذر تحميل مسار التعلّم")).not.toBeInTheDocument();
    expect(screen.queryByText("أيام متتالية")).not.toBeInTheDocument();
  });

  it("shows an error when the required learning path request fails", async () => {
    curriculumApi.getLearningPath.mockRejectedValueOnce(
      new Error("curriculum service unavailable")
    );

    render(<LearningPath onSelectTopic={vi.fn()} />);

    expect(await screen.findByText("تعذر تحميل مسار التعلّم")).toBeInTheDocument();
    expect(screen.queryByText("أساسيات البرمجة")).not.toBeInTheDocument();
  });

  it.each([
    ["already studied today", 3, true],
    ["has no active streak", 0, false],
  ])("does not show the study reminder when the learner %s", async (_label, streakDays, studiedToday) => {
    gamificationApi.getMyStats.mockResolvedValueOnce({
      streak_days: streakDays,
      studied_today: studiedToday,
    });

    render(<LearningPath onSelectTopic={vi.fn()} />);

    expect(await screen.findByText("إتقانك الإجمالي")).toBeInTheDocument();
    expect(screen.queryByText("— ادرس اليوم!")).not.toBeInTheDocument();
  });

  it("does not update component state after unmount while requests are pending", async () => {
    let resolvePath;
    let resolveStats;
    curriculumApi.getLearningPath.mockReturnValue(
      new Promise((resolve) => {
        resolvePath = resolve;
      })
    );
    gamificationApi.getMyStats.mockReturnValue(
      new Promise((resolve) => {
        resolveStats = resolve;
      })
    );

    const { unmount } = render(<LearningPath onSelectTopic={vi.fn()} />);
    unmount();

    await act(async () => {
      resolvePath(pathFixture);
      resolveStats(statsFixture);
    });

    await waitFor(() => {
      expect(curriculumApi.getLearningPath).toHaveBeenCalledTimes(1);
      expect(gamificationApi.getMyStats).toHaveBeenCalledTimes(1);
    });
  });
});
