import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("../lib/srsApi", () => ({
  addDeck: vi.fn(),
  getDecks: vi.fn(),
  getDueCards: vi.fn(),
  submitReview: vi.fn(),
}));

import { getDecks, getDueCards, submitReview } from "../lib/srsApi";
import FlashcardReview from "./FlashcardReview";

beforeEach(() => {
  vi.clearAllMocks();
  getDecks.mockResolvedValue([]);
  getDueCards.mockResolvedValue([
    { id: 21, front_text: "السؤال الأول", back_text: "الإجابة الأولى" },
  ]);
});

describe("FlashcardReview", () => {
  it("لا ينتقل إلى البطاقة التالية عندما يفشل حفظ التقييم", async () => {
    submitReview.mockRejectedValue(new Error("network unavailable"));
    const user = userEvent.setup();
    render(<FlashcardReview onClose={vi.fn()} />);

    await user.click(await screen.findByRole("button", { name: /راجع البطاقات المستحقة الآن/ }));
    expect(await screen.findByText("السؤال الأول")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "اعرض الجواب" }));
    await user.click(screen.getByRole("button", { name: "ما عرفت" }));

    expect(await screen.findByRole("alert")).toHaveTextContent(/لم يُحفظ تقييم البطاقة/);
    expect(screen.getByText("الإجابة الأولى")).toBeInTheDocument();
    expect(submitReview).toHaveBeenCalledTimes(1);
  });
});
