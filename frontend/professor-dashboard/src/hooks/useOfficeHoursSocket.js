import { useEffect, useRef, useState } from "react";

function websocketUrl() {
  const apiBase = import.meta.env.VITE_API_BASE || "http://127.0.0.1:8000";
  const url = new URL(apiBase);
  url.protocol = url.protocol === "https:" ? "wss:" : "ws:";
  url.pathname = "/ws";
  url.search = "";
  return url.toString();
}

/**
 * Subscribe to OfficeHours AI live events.
 * @param {(event: {type: string, payload: object}) => void} onEvent
 */
export function useOfficeHoursSocket(onEvent) {
  const [live, setLive] = useState(false);
  const handlerRef = useRef(onEvent);
  handlerRef.current = onEvent;

  useEffect(() => {
    let closed = false;
    let socket;
    let retryTimer;

    function connect() {
      socket = new WebSocket(websocketUrl());

      socket.onopen = () => {
        if (!closed) {
          setLive(true);
        }
      };

      socket.onmessage = (message) => {
        try {
          const event = JSON.parse(message.data);
          handlerRef.current?.(event);
        } catch {
          // ignore malformed frames
        }
      };

      socket.onclose = () => {
        setLive(false);
        if (!closed) {
          retryTimer = window.setTimeout(connect, 2000);
        }
      };

      socket.onerror = () => {
        socket.close();
      };
    }

    connect();

    return () => {
      closed = true;
      window.clearTimeout(retryTimer);
      if (socket) {
        socket.close();
      }
    };
  }, []);

  return { live };
}
