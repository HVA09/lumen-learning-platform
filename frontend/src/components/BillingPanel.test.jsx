import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";

vi.mock("../lib/billingApi", () => ({
  cancelSubscription: vi.fn(),
  createCheckout: vi.fn(),
  getBillingStatus: vi.fn(),
  getMySubscription: vi.fn(),
  getPlans: vi.fn(),
}));

import { getBillingStatus, getMySubscription, getPlans } from "../lib/billingApi";
import BillingPanel from "./BillingPanel";

const plans = [
  { id: 1, name: "Free", price_cents: 0, currency: "usd", interval: "month" },
  { id: 2, name: "Pro", price_cents: 1000, currency: "usd", interval: "month" },
];

beforeEach(() => {
  vi.clearAllMocks();
  getPlans.mockResolvedValue(plans);
  getMySubscription.mockResolvedValue(null);
});

describe("BillingPanel", () => {
  it("يعرض الخطة المجانية ويخفي الدفع عندما يكون غير مفعّل", async () => {
    getBillingStatus.mockResolvedValue({ online_payments_enabled: false });

    render(<BillingPanel onClose={vi.fn()} />);

    expect(await screen.findByRole("status")).toHaveTextContent(
      "يمكنك استخدام الخطة المجانية دون بطاقة أو حساب دفع"
    );
    expect(screen.getByText("Free")).toBeInTheDocument();
    expect(screen.getByText("غير متاح حالياً")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "اشترك" })).not.toBeInTheDocument();
  });

  it("يعرض زر الاشتراك فقط عندما يكون الدفع مفعّلاً", async () => {
    getBillingStatus.mockResolvedValue({ online_payments_enabled: true });

    render(<BillingPanel onClose={vi.fn()} />);

    expect(await screen.findByRole("button", { name: "اشترك" })).toBeInTheDocument();
    expect(screen.queryByText("غير متاح حالياً")).not.toBeInTheDocument();
  });
});
