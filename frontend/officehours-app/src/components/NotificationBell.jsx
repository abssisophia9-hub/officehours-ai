import { useCallback, useEffect, useState } from "react";
import { api } from "../api/client.js";
import { useAuth } from "../auth/AuthContext.jsx";

export default function NotificationBell({ plain = false }) {
  const { token } = useAuth();
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

  async function markRead(id) {
    await api(`/notifications/${id}/read`, { method: "POST", token });
    await load();
  }

  return (
    <div className="relative">
      <button
        type="button"
        className="bh-nav-item w-full"
        onClick={() => setOpen((value) => !value)}
      >
        Inbox
        {inbox.unread ? (
          <span className="ml-auto rounded-full bg-white/20 px-2 text-xs">{inbox.unread}</span>
        ) : null}
      </button>
      {open ? (
        <div className="absolute bottom-full left-0 z-20 mb-2 w-72 rounded-xl border border-aui-forest/20 bg-white p-3 text-xs text-aui-ink shadow-lg">
          <p className="font-semibold">Notifications</p>
          <p className="mt-1 text-[11px] text-aui-deep/60">
            {plain
              ? "Notifications for this account."
              : inbox.smtp_configured
                ? "Also emailed when SMTP is set."
                : "In-app + live socket. Set SMTP to also email."}
          </p>
          <ul className="mt-2 max-h-56 space-y-2 overflow-auto">
            {(inbox.items || []).map((item) => (
              <li key={item.id} className="rounded-lg bg-[#f3faf5] p-2">
                <p className="font-semibold">{item.title}</p>
                <p className="mt-0.5 text-aui-deep/80">{item.body}</p>
                {!item.read_at ? (
                  <button
                    type="button"
                    className="mt-1 text-aui-forest underline"
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
