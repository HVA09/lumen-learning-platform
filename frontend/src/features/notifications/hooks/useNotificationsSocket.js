import { useEffect } from "react";
import { buildNotificationsWebSocketUrl } from "../api/notificationsApi";

function parseNotificationMessage(data) {
  if (typeof data !== "string") return null;

  try {
    const notification = JSON.parse(data);
    if (
      !notification ||
      typeof notification !== "object" ||
      Array.isArray(notification) ||
      typeof notification.title !== "string" ||
      notification.title.trim() === ""
    ) {
      return null;
    }
    return notification;
  } catch {
    return null;
  }
}

export default function useNotificationsSocket({ enabled, onNotification }) {
  useEffect(() => {
    if (!enabled || typeof onNotification !== "function") return undefined;

    let socket;
    try {
      socket = new WebSocket(buildNotificationsWebSocketUrl());
    } catch {
      // A temporarily unavailable or invalid socket must not break the app shell.
      return undefined;
    }

    socket.onmessage = (event) => {
      const notification = parseNotificationMessage(event.data);
      if (notification) onNotification(notification);
    };

    return () => {
      socket.onmessage = null;
      socket.close();
    };
  }, [enabled, onNotification]);
}
