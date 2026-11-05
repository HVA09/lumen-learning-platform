import { useEffect } from "react";
import { buildNotificationsWebSocketUrl } from "../api/notificationsApi";

const RECONNECT_BASE_DELAY_MS = 1_000;
const RECONNECT_MAX_DELAY_MS = 30_000;
const NON_RETRYABLE_CLOSE_CODES = new Set([1008, 4001]);

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

    let active = true;
    let socket = null;
    let reconnectTimer = null;
    let reconnectAttempts = 0;

    const scheduleReconnect = () => {
      if (!active || reconnectTimer !== null) return;

      const delay = Math.min(
        RECONNECT_BASE_DELAY_MS * 2 ** reconnectAttempts,
        RECONNECT_MAX_DELAY_MS
      );
      reconnectAttempts += 1;
      reconnectTimer = setTimeout(() => {
        reconnectTimer = null;
        connect();
      }, delay);
    };

    const connect = () => {
      if (!active) return;

      let connection;
      try {
        connection = new WebSocket(buildNotificationsWebSocketUrl());
      } catch {
        scheduleReconnect();
        return;
      }

      socket = connection;
      connection.onopen = () => {
        reconnectAttempts = 0;
      };
      connection.onmessage = (event) => {
        const notification = parseNotificationMessage(event.data);
        if (notification) onNotification(notification);
      };
      connection.onclose = (event) => {
        if (socket === connection) socket = null;
        connection.onopen = null;
        connection.onmessage = null;
        connection.onclose = null;
        if (NON_RETRYABLE_CLOSE_CODES.has(event.code)) return;
        scheduleReconnect();
      };
    };

    const handleOnline = () => {
      if (!active || reconnectTimer === null) return;
      clearTimeout(reconnectTimer);
      reconnectTimer = null;
      connect();
    };

    window.addEventListener("online", handleOnline);
    connect();

    return () => {
      active = false;
      window.removeEventListener("online", handleOnline);
      if (reconnectTimer !== null) {
        clearTimeout(reconnectTimer);
      }
      if (socket) {
        socket.onopen = null;
        socket.onmessage = null;
        socket.onclose = null;
        socket.close();
      }
    };
  }, [enabled, onNotification]);
}
