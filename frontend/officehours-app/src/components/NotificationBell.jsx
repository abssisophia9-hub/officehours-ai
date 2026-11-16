import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "../api/client.js";
import { useAuth } from "../auth/AuthContext.jsx";

export default function NotificationBell({ plain = false }) {
  const { token } = useAuth();
  const rootRef = useRef(null);
  const [open, setOpen] = useState(false);
  const [inbox, setInbox] = useState({ unread: 0, items: [], smtp_configured: false });

  const load = useCallback(async () => {
    if (!token) return;
    try {
      setInbox(await api("/notifications/", { token }));
    } catch {
      setInbox({ unread: 0, items: [], smtp_configured: false });
    }
  }, [token]);

  useEffect(() => {
    load();
    const timer = setInterval(load, 20000);
    return () => clearInterval(timer);
  }, [load]);

  useEffect(() => {
    if (!open) return undefined;
    function onDocClick(event) {
      if (!rootRef.current?.contains(event.target)) setOpen(false);
    }
    function onKey(event) {
      if (event.key === "Escape") setOpen(false);
    }
    document.addEventListener("mousedown", onDocClick);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onDocClick);
      document.removeEventListener("keydown", onKey);
    };
  }, [open]);

  async function markRead(id) {
    await api(`/notifications/${id}/read`, { method: "POST", token });
    await load();
  }

  return (
    <div className="relative" ref={rootRef}>
      <button
        type="button"
        className="bh-nav-item w-full"
        aria-expanded={open}
        aria-controls="bh-inbox-panel"
        onClick={() => setOpen((value) => !value)}
      >
        Inbox
        {inbox.unread ? (
          <span className="ml-auto rounded-full bg-white/20 px-2 text-xs">{inbox.unread}</span>
        ) : null}
      </button>
      {open ? (
        <div
          id="bh-inbox-panel"
          role="dialog"
          aria-label="Inbox"
          className={`absolute top-full left-0 z-20 mt-2 w-72 rounded-xl border border-aui-forest/20 bg-white p-3 text-xs text-aui-ink shadow-lg${plain ? " pf-inbox" : ""}`}
        >
          <div className="flex items-start justify-between gap-2">
            <p className="font-semibold">Notifications</p>
            <button
              type="button"
              className="rounded px-1.5 py-0.5 text-sm font-semibold text-aui-deep/70 hover:bg-aui-mist"
              aria-label="Close inbox"
              onClick={() => setOpen(false)}
            >
              ×
            </button>
          </div>
          <p className={plain ? "pf-inbox-note" : "mt-1 text-[11px] text-aui-deep/60"}>
            {plain
              ? "Notifications for this account."
              : inbox.smtp_configured
                ? "Also emailed when email alerts are enabled."
                : "In-app alerts for this account. Email alerts when enabled."}
          </p>
          <ul className="mt-2 max-h-56 space-y-2 overflow-auto">
            {(inbox.items || []).map((item) => (
              <li key={item.id} className="rounded-lg bg-[#f3faf5] p-2">
                <p className="font-semibold">{item.title}</p>
                <p className="mt-0.5 text-aui-deep/80">{item.body}</p>
                {!item.read_at ? (
                  <button
                    type="button"
                    className={plain ? "pf-inbox-read" : "mt-1 text-aui-forest underline"}
                    onClick={() => markRead(item.id)}
                  >
                    Mark read
                  </button>
                ) : null}
              </li>
            ))}
            {!inbox.items?.length ? (
              <li className="text-aui-deep/60">No notifications yet.</li>
            ) : null}
          </ul>
        </div>
      ) : null}
    </div>
  );
}
