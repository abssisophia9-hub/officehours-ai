import { useEffect, useRef, useState } from "react";

function websocketUrl(token, courseId) {
  const apiBase = import.meta.env.VITE_API_BASE || "http://127.0.0.1:8000";
  const url = new URL(apiBase);
  url.protocol = url.protocol === "https:" ? "wss:" : "ws:";
  url.pathname = "/ws";
  url.search = `token=${encodeURIComponent(token)}&course_id=${encodeURIComponent(courseId)}`;
  return url.toString();
}

/** Course-scoped live events. No-op without token + courseId (legacy shell). */
export function useOfficeHoursSocket(onEvent, { token, courseId } = {}) {
  const [live, setLive] = useState(false);
  const handlerRef = useRef(onEvent);
  handlerRef.current = onEvent;

  useEffect(() => {
    if (!token || !courseId) {
      setLive(false);
      return undefined;
    }
    let closed = false;
    let socket;
    let retryTimer;

    function connect() {
      socket = new WebSocket(websocketUrl(token, courseId));

      socket.onopen = () => {
        if (!closed) setLive(true);
      };

      socket.onmessage = (message) => {
        try {
          const event = JSON.parse(message.data);
          if (event.type === "error") {
            socket.close();
            return;
          }
          handlerRef.current?.(event);
        } catch {
          // ignore malformed frames
        }
      };

      socket.onclose = () => {
        setLive(false);
        if (!closed) retryTimer = window.setTimeout(connect, 2000);
      };

      socket.onerror = () => {
        socket.close();
      };
    }

    connect();
    return () => {
      closed = true;
      window.clearTimeout(retryTimer);
      if (socket) socket.close();
    };
  }, [token, courseId]);

  return { live };
}
