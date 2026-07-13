import { useEffect, useState } from "react";
import { fetchEscalations } from "../api/knowledge.js";
import { formatDateTime } from "../utils/requests.js";

export default function EscalationFeed() {
  const [items, setItems] = useState([]);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;
    fetchEscalations()
      .then((payload) => {
        if (!cancelled) {
          setItems(payload);
        }
      })
      .catch((loadError) => {
        if (!cancelled) {
          setError(loadError.message);
        }
      });
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <section className="glass-panel p-6">
      <div className="mb-5">
        <p className="text-sm font-semibold uppercase tracking-wide text-red-600">
          Escalations
        </p>
        <h2 className="text-xl font-bold text-slate-950">Live risk feed</h2>
        <p className="mt-1 text-sm text-slate-500">
          Auto-flagged for age, high urgency, or recurring conceptual gaps.
        </p>
      </div>

      {error ? <p className="text-sm text-red-600">{error}</p> : null}

      {items.length === 0 ? (
        <p className="rounded-2xl bg-slate-50 px-4 py-6 text-center text-sm text-slate-500">
          No escalations right now.
        </p>
      ) : (
        <ul className="space-y-3">
          {items.slice(0, 8).map((item) => (
            <li
              key={item.request_id}
              className="rounded-2xl border border-red-100 bg-red-50/60 p-4"
            >
              <div className="mb-2 flex flex-wrap items-center gap-2">
                <span className="rounded-full bg-white px-2.5 py-1 text-xs font-bold text-red-700 ring-1 ring-red-200">
                  #{item.request_id}
                </span>
                {item.urgency ? (
                  <span className="rounded-full bg-red-600 px-2.5 py-1 text-xs font-bold uppercase text-white">
                    {item.urgency}
                  </span>
                ) : null}
                <span className="text-xs text-slate-500">
                  {formatDateTime(item.created_at)} · {item.age_minutes} min
                </span>
              </div>
              <p className="text-sm font-medium text-slate-900">{item.text}</p>
              <p className="mt-2 text-xs font-semibold text-red-700">
                {item.reason}
              </p>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
