import { useCallback, useEffect, useRef, useState } from "react";
import { setAuthSessionActive } from "../lib/api";
import { logoutUser, refreshSession } from "../lib/authApi";
import { getCurrentUser } from "../lib/usersApi";

/**
 * Owns browser session bootstrap and the authenticated user's profile.
 * UI-specific cleanup and notifications are delegated to onSessionExpired.
 */
export default function useSession({ onSessionExpired } = {}) {
  const [authenticated, setAuthenticated] = useState(false);
  const [authReady, setAuthReady] = useState(false);
  const [currentUser, setCurrentUser] = useState(null);
  const sessionResolvedRef = useRef(false);

  const refreshCurrentUser = useCallback(async () => {
    try {
      const user = await getCurrentUser();
      setCurrentUser(user);
      return user;
    } catch {
      // A profile refresh failure must not silently mutate the session state.
      return null;
    }
  }, []);

  const markAuthenticated = useCallback(() => {
    sessionResolvedRef.current = true;
    setAuthSessionActive(true);
    setAuthenticated(true);
    void refreshCurrentUser();
  }, [refreshCurrentUser]);

  const logout = useCallback(() => {
    sessionResolvedRef.current = true;
    setAuthSessionActive(false);
    // Revoke the server session and clear HttpOnly cookies; UI logout is immediate.
    logoutUser().catch(() => {});
    setAuthenticated(false);
    setCurrentUser(null);
  }, []);

  useEffect(() => {
    // Remove legacy browser-stored JWTs during migration to HttpOnly cookies.
    localStorage.removeItem("access_token");
    localStorage.removeItem("refresh_token");
  }, []);

  useEffect(() => {
    let mounted = true;
    let bootstrapInFlight = false;

    const bootstrapSession = async () => {
      if (!mounted || bootstrapInFlight || sessionResolvedRef.current) return;

      bootstrapInFlight = true;
      try {
        let user;
        try {
          user = await getCurrentUser();
        } catch (error) {
          if (error.response?.status !== 401) throw error;
          await refreshSession();
          user = await getCurrentUser();
        }

        if (!mounted || sessionResolvedRef.current) return;
        sessionResolvedRef.current = true;
        setCurrentUser(user);
        setAuthSessionActive(true);
        setAuthenticated(true);
      } catch {
        if (mounted) setAuthSessionActive(false);
      } finally {
        bootstrapInFlight = false;
        if (mounted) setAuthReady(true);
      }
    };

    const handleOnline = () => {
      // A transient startup network failure must not require a manual page reload.
      if (!sessionResolvedRef.current) void bootstrapSession();
    };

    window.addEventListener("online", handleOnline);
    void bootstrapSession();

    return () => {
      mounted = false;
      window.removeEventListener("online", handleOnline);
    };
  }, []);

  useEffect(() => {
    const handleUnauthorized = () => {
      logout();
      onSessionExpired?.();
    };

    window.addEventListener("auth:unauthorized", handleUnauthorized);
    return () => window.removeEventListener("auth:unauthorized", handleUnauthorized);
  }, [logout, onSessionExpired]);

  return {
    authenticated,
    authReady,
    currentUser,
    markAuthenticated,
    logout,
    refreshCurrentUser,
  };
}
