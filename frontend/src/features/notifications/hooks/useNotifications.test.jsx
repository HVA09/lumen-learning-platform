import { act, renderHook, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import useNotifications from "./useNotifications";
import {
  listNotifications,
  markAllNotificationsRead,
  markNotificationRead,
} from "../api/notificationsApi";

vi.mock("../api/notificationsApi", () => ({
  listNotifications: vi.fn(),
  markNotificationRead: vi.fn(),
  markAllNotificationsRead: vi.fn(),
}));

describe("useNotifications", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    listNotifications.mockResolvedValue([]);
    markNotificationRead.mockResolvedValue({});
    markAllNotificationsRead.mockResolvedValue({});
  });

  it("does not load notifications for an unauthenticated session", () => {
    renderHook(() => useNotifications({ enabled: false }));

    expect(listNotifications).not.toHaveBeenCalled();
  });

  it("loads the current user's notifications when enabled", async () => {
    const items = [
      { id: 1, title: "درس جديد", is_read: false },
      { id: 2, title: "تم تقييم الواجب", is_read: true },
    ];
    listNotifications.mockResolvedValue(items);

    const { result } = renderHook(() => useNotifications({ enabled: true }));

    await waitFor(() => expect(result.current.notifications).toEqual(items));
    expect(listNotifications).toHaveBeenCalledTimes(1);
  });

  it("clears notifications when the session becomes disabled", async () => {
    listNotifications.mockResolvedValue([{ id: 1, title: "تنبيه", is_read: false }]);
    const { result, rerender } = renderHook(
      ({ enabled }) => useNotifications({ enabled }),
      { initialProps: { enabled: true } }
    );

    await waitFor(() => expect(result.current.notifications).toHaveLength(1));

    rerender({ enabled: false });

    await waitFor(() => expect(result.current.notifications).toEqual([]));
  });

  it("prepends notifications received from the WebSocket", () => {
    listNotifications.mockReturnValue(new Promise(() => {}));
    const { result } = renderHook(() => useNotifications({ enabled: true }));
    const notification = { id: 3, title: "إنجاز جديد", is_read: false };

    act(() => {
      result.current.addNotification(notification);
    });

    expect(result.current.notifications).toEqual([notification]);
  });

  it("marks one notification as read after the API succeeds", async () => {
    const items = [
      { id: 1, title: "الأول", is_read: false },
      { id: 2, title: "الثاني", is_read: false },
    ];
    listNotifications.mockResolvedValue(items);
    const { result } = renderHook(() => useNotifications({ enabled: true }));
    await waitFor(() => expect(result.current.notifications).toEqual(items));

    await act(async () => {
      await result.current.markNotificationRead(1);
    });

    expect(markNotificationRead).toHaveBeenCalledWith(1);
    expect(result.current.notifications).toEqual([
      { ...items[0], is_read: true },
      items[1],
    ]);
  });

  it("marks every notification as read after the API succeeds", async () => {
    const items = [
      { id: 1, title: "الأول", is_read: false },
      { id: 2, title: "الثاني", is_read: false },
    ];
    listNotifications.mockResolvedValue(items);
    const { result } = renderHook(() => useNotifications({ enabled: true }));
    await waitFor(() => expect(result.current.notifications).toEqual(items));

    await act(async () => {
      await result.current.markAllNotificationsRead();
    });

    expect(markAllNotificationsRead).toHaveBeenCalledTimes(1);
    expect(result.current.notifications.every((item) => item.is_read)).toBe(true);
  });

  it("keeps read state unchanged when an API mutation fails", async () => {
    const items = [{ id: 1, title: "تنبيه", is_read: false }];
    listNotifications.mockResolvedValue(items);
    markNotificationRead.mockRejectedValue(new Error("request failed"));
    const { result } = renderHook(() => useNotifications({ enabled: true }));
    await waitFor(() => expect(result.current.notifications).toEqual(items));

    await act(async () => {
      await result.current.markNotificationRead(1);
    });

    expect(result.current.notifications).toEqual(items);
  });

  it("ignores a late list response after the hook is disabled", async () => {
    let resolveList;
    listNotifications.mockReturnValue(
      new Promise((resolve) => {
        resolveList = resolve;
      })
    );
    const { result, rerender } = renderHook(
      ({ enabled }) => useNotifications({ enabled }),
      { initialProps: { enabled: true } }
    );

    rerender({ enabled: false });
    await act(async () => {
      resolveList([{ id: 9, title: "قديمة", is_read: false }]);
    });

    expect(result.current.notifications).toEqual([]);
  });

  it("ignores a single-read result from a previous session", async () => {
    const previousItems = [{ id: 1, title: "الحساب السابق", is_read: false }];
    const currentItems = [{ id: 1, title: "الحساب الحالي", is_read: false }];
    listNotifications
      .mockResolvedValueOnce(previousItems)
      .mockResolvedValueOnce(currentItems);

    let resolveRead;
    markNotificationRead.mockReturnValue(
      new Promise((resolve) => {
        resolveRead = resolve;
      })
    );

    const { result, rerender } = renderHook(
      ({ enabled }) => useNotifications({ enabled }),
      { initialProps: { enabled: true } }
    );
    await waitFor(() => expect(result.current.notifications).toEqual(previousItems));

    let pendingRead;
    act(() => {
      pendingRead = result.current.markNotificationRead(1);
    });

    rerender({ enabled: false });
    await waitFor(() => expect(result.current.notifications).toEqual([]));
    rerender({ enabled: true });
    await waitFor(() => expect(result.current.notifications).toEqual(currentItems));

    await act(async () => {
      resolveRead({});
      await pendingRead;
    });

    expect(result.current.notifications).toEqual(currentItems);
  });

  it("ignores a mark-all result from a previous session", async () => {
    const previousItems = [{ id: 2, title: "إشعارات قديمة", is_read: false }];
    const currentItems = [{ id: 2, title: "إشعارات الحساب الجديد", is_read: false }];
    listNotifications
      .mockResolvedValueOnce(previousItems)
      .mockResolvedValueOnce(currentItems);

    let resolveReadAll;
    markAllNotificationsRead.mockReturnValue(
      new Promise((resolve) => {
        resolveReadAll = resolve;
      })
    );

    const { result, rerender } = renderHook(
      ({ enabled }) => useNotifications({ enabled }),
      { initialProps: { enabled: true } }
    );
    await waitFor(() => expect(result.current.notifications).toEqual(previousItems));

    let pendingReadAll;
    act(() => {
      pendingReadAll = result.current.markAllNotificationsRead();
    });

    rerender({ enabled: false });
    await waitFor(() => expect(result.current.notifications).toEqual([]));
    rerender({ enabled: true });
    await waitFor(() => expect(result.current.notifications).toEqual(currentItems));

    await act(async () => {
      resolveReadAll({});
      await pendingReadAll;
    });

    expect(result.current.notifications).toEqual(currentItems);
  });

  it("ignores incoming notifications while the session is disabled", () => {
    const { result } = renderHook(() => useNotifications({ enabled: false }));

    act(() => {
      result.current.addNotification({
        id: 3,
        title: "إشعار متأخر",
        is_read: false,
      });
    });

    expect(result.current.notifications).toEqual([]);
  });

});
