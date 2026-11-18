import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("../lib/classesApi", () => ({ listClasses: vi.fn() }));
vi.mock("../lib/gamificationApi", () => ({
  getLeaderboard: vi.fn(),
  getMyAchievements: vi.fn(),
  getMyStats: vi.fn(),
}));

import { listClasses } from "../lib/classesApi";
import { getLeaderboard, getMyAchievements, getMyStats } from "../lib/gamificationApi";
import LeaderboardPanel from "./LeaderboardPanel";

const platformBoard = [
  { user_id: 9, display_name: "نورة", score: 80, rank: 1, is_me: false },
  { user_id: 5, display_name: "أنا", score: 30, rank: 2, is_me: true },
];
const classBoard = [{ user_id: 5, display_name: "أنا", score: 30, rank: 1, is_me: true }];

beforeEach(() => {
  vi.clearAllMocks();
  listClasses.mockResolvedValue([]);
  getMyAchievements.mockResolvedValue([]);
  getMyStats.mockResolvedValue({ score: 30, rank: 2, streak_days: 4, studied_today: true });
  getLeaderboard.mockResolvedValue(platformBoard);

});

describe("LeaderboardPanel", () => {
  it("يعرض اللوحة العامة للمدير فقط", async () => {
    render(<LeaderboardPanel onClose={vi.fn()} isTeacher isAdmin />);
    expect(await screen.findByText(/🥇 نورة/)).toBeInTheDocument();
    expect(screen.getByText(/🥈 أنا \(أنت\)/)).toBeInTheDocument();
    expect(getLeaderboard).toHaveBeenCalledWith(null);
  });

  it("لا يعرض المعلم خيار اللوحة العامة ويبدأ بفصله", async () => {
    listClasses.mockResolvedValue([{ id: 7, name: "فصلي" }]);
    getLeaderboard.mockResolvedValue(classBoard);
    render(<LeaderboardPanel onClose={vi.fn()} isTeacher />);
    expect(await screen.findByText(/🥇 أنا \(أنت\)/)).toBeInTheDocument();
    expect(screen.getByRole("combobox", { name: "اختر الفصل" })).toHaveValue("7");
    expect(screen.queryByRole("option", { name: "كل المنصة" })).not.toBeInTheDocument();
    expect(getLeaderboard).toHaveBeenCalledWith("7");
  });

  it("لا يستدعي لوحة المتصدرين للطالب ويعرض إحصاءاته الشخصية فقط", async () => {
    render(<LeaderboardPanel onClose={vi.fn()} isTeacher={false} />);
    expect(await screen.findByText("تقدّمي الشخصي")).toBeInTheDocument();
    expect(screen.getByText("30")).toBeInTheDocument();
    expect(screen.getByText(/4 🔥/)).toBeInTheDocument();
    expect(screen.getByText("أنجزت نشاطاً دراسياً اليوم")).toBeInTheDocument();
    expect(screen.queryByText("لوحة المتصدرين")).not.toBeInTheDocument();
    expect(screen.queryByText("نورة")).not.toBeInTheDocument();
    expect(getLeaderboard).not.toHaveBeenCalled();
    expect(getMyStats).toHaveBeenCalledTimes(1);
  });

  it("يعرض رسالة واضحة للمعلم الذي لا يملك فصولاً", async () => {
    render(<LeaderboardPanel onClose={vi.fn()} isTeacher />);
    expect(await screen.findByText("لا توجد فصول مرتبطة بحسابك لعرض لوحاتها")).toBeInTheDocument();
    expect(getLeaderboard).not.toHaveBeenCalled();
  });

  it("اختيار فصل يطلب ترتيب ذلك الفصل فقط", async () => {
    listClasses.mockResolvedValue([{ id: 7, name: "فصلي" }, { id: 8, name: "فصل آخر" }]);
    getLeaderboard.mockResolvedValue(classBoard);
    const user = userEvent.setup();
    render(<LeaderboardPanel onClose={vi.fn()} isTeacher />);
    await screen.findByText(/🥇 أنا/);

    await user.selectOptions(await screen.findByRole("combobox", { name: "اختر الفصل" }), "8");
    await waitFor(() => expect(getLeaderboard).toHaveBeenLastCalledWith("8"));
  });

  it("خطأ السيرفر يظهر بدل قائمة فارغة صامتة", async () => {
    getLeaderboard.mockRejectedValue({ response: { data: { detail: "لوحة متصدرين هذا الفصل متاحة لمعلّمه أو المدير فقط" } } });
    render(<LeaderboardPanel onClose={vi.fn()} isTeacher isAdmin />);
    expect(await screen.findByText("لوحة متصدرين هذا الفصل متاحة لمعلّمه أو المدير فقط")).toBeInTheDocument();
  });

  it("تبويب الإنجازات يميّز المفتوح من المقفل", async () => {
    getMyAchievements.mockResolvedValue([
      { key: "a", title_ar: "بداية المعرفة", description_ar: "أنهيت أول درس", unlocked_at: "2026-09-29T00:00:00Z" },
      { key: "b", title_ar: "علامة كاملة", description_ar: "100% في اختبار", unlocked_at: null },
    ]);
    const user = userEvent.setup();
    render(<LeaderboardPanel onClose={vi.fn()} isTeacher isAdmin />);
    await user.click(await screen.findByRole("button", { name: "إنجازاتي" }));
    expect(await screen.findByText(/🏆 بداية المعرفة/)).toBeInTheDocument();
    expect(screen.getByText(/🔒 علامة كاملة/)).toBeInTheDocument();
  });

  it("keeps achievements visible when the student's stats request fails", async () => {
    getMyStats.mockRejectedValue(new Error("stats unavailable"));
    getMyAchievements.mockResolvedValue([
      { key: "a", title_ar: "إنجاز محفوظ", description_ar: "تم إنجازه", unlocked_at: "2026-11-18T00:00:00Z" },
    ]);
    render(<LeaderboardPanel onClose={vi.fn()} isTeacher={false} />);

    expect(await screen.findAllByText("تعذر تحميل تقدمك الشخصي")).toHaveLength(2);
    expect(await screen.findByText(/🏆 إنجاز محفوظ/)).toBeInTheDocument();
  });

  it("shows a loading state while the teacher's class list is pending", async () => {
    let resolveClasses;
    listClasses.mockReturnValue(new Promise((resolve) => { resolveClasses = resolve; }));
    render(<LeaderboardPanel onClose={vi.fn()} isTeacher />);

    expect(screen.queryByText("لا توجد فصول مرتبطة بحسابك لعرض لوحاتها")).not.toBeInTheDocument();
    expect(screen.getByText("...")).toBeInTheDocument();

    resolveClasses([{ id: 7, name: "فصلي" }]);
    expect(await screen.findByRole("combobox", { name: "اختر الفصل" })).toHaveValue("7");
  });

  it("fetches the admin global leaderboard only once when classes load", async () => {
    listClasses.mockResolvedValue([{ id: 7, name: "فصل إداري" }]);
    render(<LeaderboardPanel onClose={vi.fn()} isTeacher isAdmin />);

    expect(await screen.findByText(/🥇 نورة/)).toBeInTheDocument();
    await waitFor(() => expect(listClasses).toHaveBeenCalledTimes(1));
    expect(getLeaderboard).toHaveBeenCalledTimes(1);
    expect(getLeaderboard).toHaveBeenCalledWith(null);
  });

});
