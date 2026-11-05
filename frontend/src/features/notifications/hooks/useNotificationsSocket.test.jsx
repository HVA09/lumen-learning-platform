import { act, renderHook } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import useNotificationsSocket from "./useNotificationsSocket";

function installWebSocketMock() {
  const instances = [];

  class MockWebSocket {
    constructor(url) {
      this.url = url;
      this.onopen = null;
      this.onmessage = null;
      this.onclose = null;
      this.close = vi.fn();
      instances.push(this);
    }
  }

  vi.stubGlobal("WebSocket", MockWebSocket);
  return instances;
}

describe("useNotificationsSocket", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
    vi.useRealTimers();
  });

  it("does not connect while notifications are disabled", () => {
    const instances = installWebSocketMock();

    renderHook(() =>
      useNotificationsSocket({ enabled: false, onNotification: vi.fn() })
    );

    expect(instances).toHaveLength(0);
  });

  it("forwards a valid notification object", () => {
    const instances = installWebSocketMock();
    const onNotification = vi.fn();
    renderHook(() => useNotificationsSocket({ enabled: true, onNotification }));

    const notification = {
      id: 7,
      title: "تم إكمال الدرس",
      is_read: false,
    };

    act(() => {
      instances[0].onmessage({ data: JSON.stringify(notification) });
    });

    expect(onNotification).toHaveBeenCalledTimes(1);
    expect(onNotification).toHaveBeenCalledWith(notification);
  });

  it("ignores malformed JSON and invalid notification shapes", () => {
    const instances = installWebSocketMock();
    const onNotification = vi.fn();
    renderHook(() => useNotificationsSocket({ enabled: true, onNotification }));

    act(() => {
      instances[0].onmessage({ data: "not-json" });
      instances[0].onmessage({ data: JSON.stringify(null) });
      instances[0].onmessage({ data: JSON.stringify(["not", "an", "object"]) });
      instances[0].onmessage({ data: JSON.stringify({ id: 8 }) });
      instances[0].onmessage({ data: JSON.stringify({ title: "   " }) });
      instances[0].onmessage({ data: 12 });
    });

    expect(onNotification).not.toHaveBeenCalled();
  });

  it("reconnects after a transient close using capped exponential backoff", () => {
    vi.useFakeTimers();
    const instances = installWebSocketMock();
    renderHook(() =>
      useNotificationsSocket({ enabled: true, onNotification: vi.fn() })
    );

    act(() => {
      instances[0].onclose({ code: 1006 });
      vi.advanceTimersByTime(1_000);
    });
    expect(instances).toHaveLength(2);

    act(() => {
      instances[1].onclose({ code: 1006 });
      vi.advanceTimersByTime(1_999);
    });
    expect(instances).toHaveLength(2);

    act(() => {
      vi.advanceTimersByTime(1);
    });
    expect(instances).toHaveLength(3);
  });

  it("resets the reconnect delay after the socket opens", () => {
    vi.useFakeTimers();
    const instances = installWebSocketMock();
    renderHook(() =>
      useNotificationsSocket({ enabled: true, onNotification: vi.fn() })
    );

    act(() => {
      instances[0].onclose({ code: 1006 });
      vi.advanceTimersByTime(1_000);
    });
    expect(instances).toHaveLength(2);

    act(() => {
      instances[1].onopen();
      instances[1].onclose({ code: 1006 });
      vi.advanceTimersByTime(1_000);
    });
    expect(instances).toHaveLength(3);
  });

  it.each([1008, 4001])(
    "does not retry terminal close code %i",
    (code) => {
      vi.useFakeTimers();
      const instances = installWebSocketMock();
      renderHook(() =>
        useNotificationsSocket({ enabled: true, onNotification: vi.fn() })
      );

      act(() => {
        instances[0].onclose({ code });
        vi.advanceTimersByTime(60_000);
      });

      expect(instances).toHaveLength(1);
    }
  );

  it("cancels a pending reconnect on unmount", () => {
    vi.useFakeTimers();
    const instances = installWebSocketMock();
    const { unmount } = renderHook(() =>
      useNotificationsSocket({ enabled: true, onNotification: vi.fn() })
    );
    const socket = instances[0];

    act(() => {
      socket.onclose({ code: 1006 });
    });
    unmount();

    act(() => {
      vi.advanceTimersByTime(60_000);
    });

    expect(instances).toHaveLength(1);
    expect(socket.close).not.toHaveBeenCalled();
  });

  it("closes the socket and detaches its message handler on unmount", () => {
    const instances = installWebSocketMock();
    const { unmount } = renderHook(() =>
      useNotificationsSocket({ enabled: true, onNotification: vi.fn() })
    );
    const socket = instances[0];

    unmount();

    expect(socket.onmessage).toBeNull();
    expect(socket.close).toHaveBeenCalledTimes(1);
  });
});
