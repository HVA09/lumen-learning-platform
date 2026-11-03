import { act, renderHook } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import useNotificationsSocket from "./useNotificationsSocket";

function installWebSocketMock() {
  const instances = [];

  class MockWebSocket {
    constructor(url) {
      this.url = url;
      this.onmessage = null;
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
