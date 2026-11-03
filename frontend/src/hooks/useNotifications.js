import { useCallback, useEffect, useRef, useState } from "react";
import {
  listNotifications,
  markAllNotificationsRead as markAllNotificationsReadRequest,
  markNotificationRead as markNotificationReadRequest,
} from "../lib/notificationsApi";

/**
 * Owns notification data and read-state mutations for the authenticated user.
 * WebSocket connection lifecycle remains in useNotificationsSocket.
 */
export default function useNotifications({ enabled }) {
  const [notifications, setNotifications] = useState([]);
  const sessionRef = useRef({ active: Boolean(enabled) });

  useEffect(() => {
    let active = true;
    const session = { active: Boolean(enabled) };
    sessionRef.current = session;

    if (!enabled) {
      setNotifications([]);
      return () => {
        active = false;
        session.active = false;
      };
    }

    listNotifications()
      .then((items) => {
        if (active) {
          setNotifications(Array.isArray(items) ? items : []);
        }
      })
      .catch(() => {
        // Loading notifications must not prevent the rest of the app from working.
      });

    return () => {
      active = false;
      session.active = false;
    };
  }, [enabled]);

  const addNotification = useCallback((notification) => {
    if (!sessionRef.current?.active) return;
    setNotifications((current) => [notification, ...current]);
  }, []);

  const markNotificationRead = useCallback(async (id) => {
    const session = sessionRef.current;
    try {
      await markNotificationReadRequest(id);
      if (!session?.active) return;
      setNotifications((current) =>
        current.map((item) => (item.id === id ? { ...item, is_read: true } : item))
      );
    } catch {
      // Keep the existing read state if the server request fails.
    }
  }, []);

  const markAllNotificationsRead = useCallback(async () => {
    const session = sessionRef.current;
    try {
      await markAllNotificationsReadRequest();
      if (!session?.active) return;
      setNotifications((current) => current.map((item) => ({ ...item, is_read: true })));
    } catch {
      // Keep the existing read state if the server request fails.
    }
  }, []);

  return {
    notifications,
    addNotification,
    markNotificationRead,
    markAllNotificationsRead,
  };
}
