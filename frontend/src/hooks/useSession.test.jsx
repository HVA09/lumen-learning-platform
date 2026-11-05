import { StrictMode } from "react";
import { act, renderHook, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import useSession from "./useSession";
import { setAuthSessionActive } from "../lib/api";
import { logoutUser, refreshSession } from "../lib/authApi";
import { getCurrentUser } from "../lib/usersApi";

vi.mock("../lib/api", () => ({
  setAuthSessionActive: vi.fn(),
}));

vi.mock("../lib/authApi", () => ({
  logoutUser: vi.fn(),
  refreshSession: vi.fn(),
}));

vi.mock("../lib/usersApi", () => ({
  getCurrentUser: vi.fn(),
}));

describe("useSession", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
    logoutUser.mockResolvedValue({});
    refreshSession.mockResolvedValue({});
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("restores an existing session and loads the current user", async () => {
    const user = { id: 12, role: "student" };
    getCurrentUser.mockResolvedValue(user);

    const { result } = renderHook(() => useSession());

    await waitFor(() => expect(result.current.authReady).toBe(true));

    expect(result.current.authenticated).toBe(true);
    expect(result.current.currentUser).toEqual(user);
    expect(setAuthSessionActive).toHaveBeenCalledWith(true);
    expect(refreshSession).not.toHaveBeenCalled();
    expect(getCurrentUser).toHaveBeenCalledTimes(1);
  });

  it("restores the session when mounted under React StrictMode", async () => {
    const user = { id: 19, role: "student" };
    getCurrentUser.mockResolvedValue(user);
    const wrapper = ({ children }) => <StrictMode>{children}</StrictMode>;

    const { result } = renderHook(() => useSession(), { wrapper });

    await waitFor(() => {
      expect(result.current.authReady).toBe(true);
      expect(result.current.authenticated).toBe(true);
    });
    expect(result.current.currentUser).toEqual(user);
  });

  it("refreshes an expired session once and retries the user request", async () => {
    const user = { id: 13, role: "teacher" };
    getCurrentUser
      .mockRejectedValueOnce({ response: { status: 401 } })
      .mockResolvedValueOnce(user);

    const { result } = renderHook(() => useSession());

    await waitFor(() => expect(result.current.authReady).toBe(true));

    expect(refreshSession).toHaveBeenCalledTimes(1);
    expect(getCurrentUser).toHaveBeenCalledTimes(2);
    expect(result.current.authenticated).toBe(true);
    expect(result.current.currentUser).toEqual(user);
    expect(setAuthSessionActive).toHaveBeenCalledWith(true);
  });

  it("does not attempt refresh for non-authentication bootstrap errors", async () => {
    getCurrentUser.mockRejectedValue(new Error("network unavailable"));

    const { result } = renderHook(() => useSession());

    await waitFor(() => expect(result.current.authReady).toBe(true));

    expect(result.current.authenticated).toBe(false);
    expect(result.current.currentUser).toBeNull();
    expect(refreshSession).not.toHaveBeenCalled();
    expect(setAuthSessionActive).toHaveBeenCalledWith(false);
  });

  it("retries session bootstrap when the browser reports that the network is back", async () => {
    const user = { id: 17, role: "student" };
    getCurrentUser
      .mockRejectedValueOnce(new Error("network unavailable"))
      .mockResolvedValueOnce(user);

    const { result } = renderHook(() => useSession());

    await waitFor(() => expect(result.current.authReady).toBe(true));
    expect(result.current.authenticated).toBe(false);

    act(() => {
      window.dispatchEvent(new Event("online"));
    });

    await waitFor(() => {
      expect(result.current.authenticated).toBe(true);
      expect(result.current.currentUser).toEqual(user);
    });
    expect(getCurrentUser).toHaveBeenCalledTimes(2);
    expect(setAuthSessionActive).toHaveBeenLastCalledWith(true);
  });

  it("retries once when connectivity returns while session bootstrap is still in flight", async () => {
    const user = { id: 20, role: "student" };
    let rejectInitialRequest;
    const initialRequest = new Promise((resolve, reject) => {
      rejectInitialRequest = reject;
    });
    getCurrentUser
      .mockReturnValueOnce(initialRequest)
      .mockResolvedValueOnce(user);

    const { result } = renderHook(() => useSession());
    await waitFor(() => expect(getCurrentUser).toHaveBeenCalledTimes(1));

    act(() => {
      window.dispatchEvent(new Event("online"));
    });

    await act(async () => {
      rejectInitialRequest(new Error("network unavailable"));
      await waitFor(() => {
        expect(result.current.authenticated).toBe(true);
        expect(result.current.currentUser).toEqual(user);
      });
    });

    expect(getCurrentUser).toHaveBeenCalledTimes(2);
    expect(setAuthSessionActive).toHaveBeenLastCalledWith(true);
  });

  it("does not restart bootstrap when an authenticated session reconnects", async () => {
    const user = { id: 18, role: "teacher" };
    getCurrentUser.mockResolvedValue(user);

    const { result } = renderHook(() => useSession());
    await waitFor(() => expect(result.current.authenticated).toBe(true));

    act(() => {
      window.dispatchEvent(new Event("online"));
    });

    expect(getCurrentUser).toHaveBeenCalledTimes(1);
    expect(result.current.authenticated).toBe(true);
    expect(result.current.currentUser).toEqual(user);
  });

  it("marks a successful login and reloads the current user", async () => {
    const user = { id: 14, role: "admin" };
    getCurrentUser
      .mockRejectedValueOnce({ response: { status: 401 } })
      .mockResolvedValueOnce(user);

    const { result } = renderHook(() => useSession());
    await waitFor(() => expect(result.current.authReady).toBe(true));

    getCurrentUser.mockResolvedValueOnce(user);
    act(() => {
      result.current.markAuthenticated();
    });

    await waitFor(() => expect(result.current.currentUser).toEqual(user));
    expect(result.current.authenticated).toBe(true);
    expect(setAuthSessionActive).toHaveBeenLastCalledWith(true);
  });

  it("logs out locally immediately and attempts to revoke the server session", async () => {
    getCurrentUser.mockResolvedValue({ id: 15, role: "student" });
    const { result } = renderHook(() => useSession());
    await waitFor(() => expect(result.current.authenticated).toBe(true));

    logoutUser.mockRejectedValueOnce(new Error("server unavailable"));
    act(() => {
      result.current.logout();
    });

    expect(result.current.authenticated).toBe(false);
    expect(result.current.currentUser).toBeNull();
    expect(setAuthSessionActive).toHaveBeenLastCalledWith(false);
    expect(logoutUser).toHaveBeenCalledTimes(1);

    act(() => {
      window.dispatchEvent(new Event("online"));
    });
    expect(getCurrentUser).toHaveBeenCalledTimes(1);
  });

  it("handles unauthorized events and notifies the app shell", async () => {
    getCurrentUser.mockResolvedValue({ id: 16, role: "student" });
    const onSessionExpired = vi.fn();
    const { result } = renderHook(() => useSession({ onSessionExpired }));
    await waitFor(() => expect(result.current.authenticated).toBe(true));

    act(() => {
      window.dispatchEvent(new Event("auth:unauthorized"));
    });

    expect(result.current.authenticated).toBe(false);
    expect(result.current.currentUser).toBeNull();
    expect(onSessionExpired).toHaveBeenCalledTimes(1);
    expect(logoutUser).toHaveBeenCalledTimes(1);
  });

  it("removes the unauthorized listener when the hook unmounts", async () => {
    getCurrentUser.mockRejectedValue(new Error("not signed in"));
    const removeSpy = vi.spyOn(window, "removeEventListener");
    const { unmount } = renderHook(() => useSession());
    await waitFor(() => expect(setAuthSessionActive).toHaveBeenCalledWith(false));

    unmount();

    expect(removeSpy).toHaveBeenCalledWith("auth:unauthorized", expect.any(Function));
    expect(removeSpy).toHaveBeenCalledWith("online", expect.any(Function));
  });
});
