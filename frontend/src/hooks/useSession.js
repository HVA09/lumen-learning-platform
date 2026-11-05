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
  const authenticatedRef = useRef(false);
  const logoutRequestedRef = useRef(false);

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
    logoutRequestedRef.current = false;
    authenticatedRef.current = true;
    setAuthSessionActive(true);
    setAuthenticated(true);
    void refreshCurrentUser();
  }, [refreshCurrentUser]);

  const logout = useCallback(() => {
    logoutRequestedRef.current = true;
    authenticatedRef.current = false;
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
    let bootstrapRetryRequested = false;

    const bootstrapSession = async () => {
      if (!mounted || logoutRequestedRef.current) return;
      if (bootstrapInFlight) {
        bootstrapRetryRequested = true;
        return;
      }

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

        if (!mounted || logoutRequestedRef.current) return;
        authenticatedRef.current = true;
        setCurrentUser(user);
        setAuthSessionActive(true);
        setAuthenticated(true);
      } catch {
        // A temporary network failure must not be treated as an expired session.
        if (mounted && !authenticatedRef.current && !logoutRequestedRef.current) {
          setAuthSessionActive(false);
          setAuthenticated(false);
          setCurrentUser(null);
        }
      } finally {
        bootstrapInFlight = false;
        if (mounted) {
          setAuthReady(true);
          if (bootstrapRetryRequested) {
            bootstrapRetryRequested = false;
            if (!logoutRequestedRef.current) {
              if (!authenticatedRef.current) {
                void bootstrapSession();
              }
            }
          }
        } else {
          bootstrapRetryRequested = false;
        }
      }
    };

    const handleOnline = () => {
      if (!mounted || logoutRequestedRef.current) return;
      if (bootstrapInFlight) {
        bootstrapRetryRequested = true;
        return;
      }
      if (!authenticatedRef.current) {
        void bootstrapSession();
      }
    };

    window.addEventListener("online", handleOnline);
    void bootstrapSession();

    return () => {
      mounted = false;
      bootstrapRetryRequested = false;
      window.removeEventListener("online", handleOnline);
    };
  }, [refreshCurrentUser]);

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
