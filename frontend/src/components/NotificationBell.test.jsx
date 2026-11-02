import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi } from "vitest";
import NotificationBell from "./NotificationBell";

const sampleNotifications = [
  { id: 1, title: "أهلًا بك", body: "تم إنشاء حسابك", is_read: false },
  { id: 2, title: "تم تفعيل اشتراكك", body: "خطتك الآن Pro", is_read: true },
];

describe("NotificationBell", () => {
  it("يعرض عدد الإشعارات غير المقروءة", () => {
    render(
      <NotificationBell
        notifications={sampleNotifications}
        onMarkRead={vi.fn()}
        onMarkAllRead={vi.fn()}
      />
    );
    expect(screen.getByText("1")).toBeInTheDocument();
  });

  it("ما يعرض شارة لو كل الإشعارات مقروءة", () => {
    const allRead = sampleNotifications.map((n) => ({ ...n, is_read: true }));
    render(<NotificationBell notifications={allRead} onMarkRead={vi.fn()} onMarkAllRead={vi.fn()} />);
    expect(screen.queryByText("0")).not.toBeInTheDocument();
  });

  it("يفتح القائمة ويعرض الإشعارات عند الضغط على الجرس", async () => {
    const user = userEvent.setup();
    render(
      <NotificationBell
        notifications={sampleNotifications}
        onMarkRead={vi.fn()}
        onMarkAllRead={vi.fn()}
      />
    );
    await user.click(screen.getByText("🔔"));
    expect(screen.getByText("أهلًا بك")).toBeInTheDocument();
    expect(screen.getByText("تم تفعيل اشتراكك")).toBeInTheDocument();
  });

  it("الضغط على إشعار غير مقروء ينادي onMarkRead بمعرّفه", async () => {
    const onMarkRead = vi.fn();
    const user = userEvent.setup();
    render(
      <NotificationBell
        notifications={sampleNotifications}
        onMarkRead={onMarkRead}
        onMarkAllRead={vi.fn()}
      />
    );
    await user.click(screen.getByText("🔔"));
    await user.click(screen.getByText("أهلًا بك"));
    expect(onMarkRead).toHaveBeenCalledWith(1);
  });

  it("زر 'تعليم الكل كمقروء' ينادي onMarkAllRead", async () => {
    const onMarkAllRead = vi.fn();
    const user = userEvent.setup();
    render(
      <NotificationBell
        notifications={sampleNotifications}
        onMarkRead={vi.fn()}
        onMarkAllRead={onMarkAllRead}
      />
    );
    await user.click(screen.getByText("🔔"));
    await user.click(screen.getByText("تعليم الكل كمقروء"));
    expect(onMarkAllRead).toHaveBeenCalled();
  });

  it("يعرض رسالة عدم وجود إشعارات لما تكون القائمة فاضية", async () => {
    const user = userEvent.setup();
    render(<NotificationBell notifications={[]} onMarkRead={vi.fn()} onMarkAllRead={vi.fn()} />);
    await user.click(screen.getByText("🔔"));
    expect(screen.getByText("لا توجد إشعارات")).toBeInTheDocument();
  });
});
