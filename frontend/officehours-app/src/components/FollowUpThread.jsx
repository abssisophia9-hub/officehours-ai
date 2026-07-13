import { useState } from "react";
import { api } from "../api/client.js";

function formatStamp(value) {
  if (!value) return "";
  try {
    return new Date(value).toLocaleString();
  } catch {
    return String(value);
  }
}

export default function FollowUpThread({
  requestId,
  followups = [],
  token,
  authorRole,
  authorName,
  onUpdated,
  allowReply = true,
}) {
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function submit(event) {
    event.preventDefault();
    if (!message.trim()) return;
    setBusy(true);
    setError("");
    try {
      await api(`/requests/${requestId}/followups`, {
        method: "POST",
        token,
        body: {
          message: message.trim(),
          author_role: authorRole,
          author_name: authorName,
        },
      });
      setMessage("");
      if (onUpdated) await onUpdated();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="space-y-3">
      <h3 className="font-display text-lg font-bold">Follow-ups</h3>
      {followups.length === 0 ? (
        <p className="text-sm text-aui-deep/60">No follow-up messages yet.</p>
      ) : (
        <ul className="space-y-2">
          {followups.map((item) => (
            <li
              key={item.id}
              className="rounded-2xl border border-white/50 bg-white/50 px-3 py-2 text-sm"
            >
              <p className="text-xs font-bold uppercase tracking-wide text-aui-deep/55">
                {item.author_role} · {item.author_name}
                {item.created_at ? ` · ${formatStamp(item.created_at)}` : ""}
              </p>
              <p className="mt-1 whitespace-pre-wrap text-aui-deep/90">{item.message}</p>
            </li>
          ))}
        </ul>
      )}

      {allowReply ? (
        <form onSubmit={submit} className="space-y-2">
          <textarea
            className="field-glass min-h-20 w-full px-3 py-2 text-sm"
            placeholder="Add a follow-up…"
            value={message}
            onChange={(event) => setMessage(event.target.value)}
            required
            minLength={2}
          />
          {error ? <p className="text-sm text-red-700">{error}</p> : null}
          <button type="submit" disabled={busy} className="btn-ghost px-4 py-2 text-sm">
            {busy ? "Sending…" : "Send follow-up"}
          </button>
        </form>
      ) : null}
    </div>
  );
}
