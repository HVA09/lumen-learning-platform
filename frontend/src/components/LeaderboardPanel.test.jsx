import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("../lib/classesApi", () => ({ listClasses: vi.fn() }));
vi.mock("../lib/gamificationApi", () => ({ getLeaderboard: vi.fn(), getMyAchievements: vi.fn() }));

import { listClasses } from "../lib/classesApi";
import { getLeaderboard, getMyAchievements } from "../lib/gamificationApi";
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
  getLeaderboard.mockResolvedValue(platformBoard);
});

describe("LeaderboardPanel", () => {
  it("يعرض ترتيب المنصة وميداليات الثلاثة الأوائل ويميّز المستخدم", async () => {
    render(<LeaderboardPanel onClose={vi.fn()} />);
    expect(await screen.findByText(/🥇 نورة/)).toBeInTheDocument();
    expect(screen.getByText(/🥈 أنا \(أنت\)/)).toBeInTheDocument();
    expect(getLeaderboard).toHaveBeenCalledWith(null);
  });

  it("بدون فصول لا تظهر قائمة اختيار النطاق", async () => {
    render(<LeaderboardPanel onClose={vi.fn()} />);
    await screen.findByText(/نورة/);
    expect(screen.queryByRole("combobox")).not.toBeInTheDocument();
  });

  it("اختيار فصل يطلب ترتيب ذلك الفصل فقط", async () => {
    listClasses.mockResolvedValue([{ id: 7, name: "فصلي" }]);
    const user = userEvent.setup();
    render(<LeaderboardPanel onClose={vi.fn()} />);
    await screen.findByText(/نورة/);

    getLeaderboard.mockResolvedValue(classBoard);
    await user.selectOptions(await screen.findByRole("combobox"), "7");

    await waitFor(() => expect(getLeaderboard).toHaveBeenLastCalledWith("7"));
    await waitFor(() => expect(screen.queryByText(/نورة/)).not.toBeInTheDocument());
    expect(screen.getByText(/🥇 أنا \(أنت\)/)).toBeInTheDocument();
  });

  it("خطأ السيرفر (مثل 403) يظهر بدل قائمة فارغة صامتة", async () => {
    getLeaderboard.mockRejectedValue({ response: { data: { detail: "لوحة متصدرين هذا الفصل لطلابه فقط" } } });
    render(<LeaderboardPanel onClose={vi.fn()} />);
    expect(await screen.findByText("لوحة متصدرين هذا الفصل لطلابه فقط")).toBeInTheDocument();
  });

  it("تبويب الإنجازات يميّز المفتوح من المقفل", async () => {
    getMyAchievements.mockResolvedValue([
      { key: "a", title_ar: "بداية المعرفة", description_ar: "أنهيت أول درس", unlocked_at: "2026-09-29T00:00:00Z" },
      { key: "b", title_ar: "علامة كاملة", description_ar: "100% في اختبار", unlocked_at: null },
    ]);
    const user = userEvent.setup();
    render(<LeaderboardPanel onClose={vi.fn()} />);
    await user.click(await screen.findByRole("button", { name: "إنجازاتي" }));
    expect(await screen.findByText(/🏆 بداية المعرفة/)).toBeInTheDocument();
    expect(screen.getByText(/🔒 علامة كاملة/)).toBeInTheDocument();
  });
});
