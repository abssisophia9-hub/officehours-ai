import { useCallback, useEffect, useMemo, useState } from "react";
import { Link, Navigate } from "react-router";
import { api } from "../api/client.js";
import { pageItems } from "../api/page.js";
import { useAuth } from "../auth/AuthContext.jsx";
import { plainAskText } from "../lib/plainAskText.js";

function fmtAgo(iso) {
  if (!iso) return null;
  const t = new Date(iso).getTime();
  if (Number.isNaN(t)) return null;
  const mins = Math.max(0, Math.round((Date.now() - t) / 60000));
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins} min ago`;
  const h = Math.floor(mins / 60);
  if (h < 48) return h === 1 ? "1 hour ago" : `${h} hours ago`;
  const d = Math.floor(h / 24);
  return d === 1 ? "1 day ago" : `${d} days ago`;
}

function avgWaitLabel(items) {
  const waits = items
    .map((req) => Number(req.estimated_wait_minutes))
    .filter((n) => Number.isFinite(n) && n >= 0);
  if (!waits.length) return "—";
  const avg = Math.round(waits.reduce((a, b) => a + b, 0) / waits.length);
  if (avg < 1) return "<1 min";
  if (avg < 60) return `~${avg} min`;
  const h = Math.floor(avg / 60);
  const m = avg % 60;
  return m ? `~${h}h ${m}m` : `~${h}h`;
}

export default function TaDashboardPage() {
  const { token, user, activeCourse } = useAuth();
  const [load, setLoad] = useState(null);
  const [openRows, setOpenRows] = useState([]);
  const [helpedRows, setHelpedRows] = useState([]);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(true);

  const refresh = useCallback(async () => {
    if (!token || !activeCourse) return;
    setBusy(true);
    setError("");
    try {
      const courseId = activeCourse.id;
      const [loadData, openData, helpedData] = await Promise.all([
        api(`/ta/load/?course_id=${courseId}`, { token }),
        api(
          `/ta/queue/?course_id=${courseId}&assignment=all&include_helped=false&limit=40&offset=0`,
          { token },
        ),
        api(
          `/ta/queue/?course_id=${courseId}&assignment=all&include_helped=true&limit=40&offset=0`,
          { token },
        ),
      ]);
      setLoad(loadData);
      setOpenRows(
        pageItems(openData)
          .map((item) => item.request || item)
          .filter((req) => String(req.work_status || "") !== "helped"),
      );
      setHelpedRows(
        pageItems(helpedData)
          .map((item) => item.request || item)
          .filter((req) => String(req.work_status || "") === "helped")
          .slice(0, 5),
      );
    } catch (err) {
      setError(err.message || "Could not load dashboard.");
      setLoad(null);
      setOpenRows([]);
      setHelpedRows([]);
    } finally {
      setBusy(false);
    }
  }, [token, activeCourse]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const mine = useMemo(
    () =>
      openRows.filter(
        (req) =>
          String(req.claimed_by_user_id || "") === String(user?.id || "") ||
          String(req.assigned_ta_user_id || "") === String(user?.id || ""),
      ),
    [openRows, user?.id],
  );

  if (!activeCourse) return <Navigate to="/" replace />;
  if (activeCourse.role !== "ta" && activeCourse.role !== "professor") {
    return <Navigate to="/student" replace />;
  }

  // Prefer live queue rows over /ta/load aggregates — load may still count helped.
  const openCount = openRows.length;
  const unassigned =
    Number(load?.unassigned_open) >= 0 && openRows.length
      ? Math.min(Number(load.unassigned_open), openRows.length)
      : openRows.filter(
          (req) =>
            !(req.claimed_by || req.claimed_by_user_id) &&
            (!req.assigned_ta || req.assigned_ta === "Unassigned"),
        ).length;
  const wait = avgWaitLabel(openRows);

  return (
    <div className="fade-up td-dash">
      <header className="td-dash-head">
        <div>
          <p className="td-dash-kicker">{activeCourse.code}</p>
          <h1 className="bh-page-title">Dashboard</h1>
          <p className="bh-page-subtitle">
            Your desk for this course — open asks, what you claimed, and recent
            replies.
          </p>
        </div>
        <div className="td-dash-actions">
          <Link className="btn-primary px-4 py-2 text-sm" to="/ta">
            Open live queue
          </Link>
          <Link className="btn-ghost px-4 py-2 text-sm" to="/ta/past">
            Past asks
          </Link>
        </div>
      </header>

      {error ? <p className="mb-3 text-sm text-red-700">{error}</p> : null}

      <div className="td-dash-stats" aria-label="Queue summary">
        <article className="td-dash-stat">
          <p className="td-dash-stat-label">Open asks</p>
          <p className="td-dash-stat-value">{busy ? "…" : openCount}</p>
        </article>
        <article className="td-dash-stat">
          <p className="td-dash-stat-label">Waiting for a TA</p>
          <p className="td-dash-stat-value">{busy ? "…" : unassigned}</p>
        </article>
        <article className="td-dash-stat">
          <p className="td-dash-stat-label">On your plate</p>
          <p className="td-dash-stat-value">{busy ? "…" : mine.length}</p>
        </article>
        <article className="td-dash-stat">
          <p className="td-dash-stat-label">Typical wait</p>
          <p className="td-dash-stat-value td-dash-stat-value-sm">{busy ? "…" : wait}</p>
        </article>
      </div>

      <div className="td-dash-grid">
        <section className="bh-card td-dash-panel">
          <div className="bh-card-title">
            <h2>Needs attention</h2>
          </div>
          <p className="bh-card-note">Oldest open asks first. Claim them in the live queue.</p>
          {busy ? (
            <p className="mt-3 text-sm text-aui-deep/70">Loading…</p>
          ) : openRows.length === 0 ? (
            <p className="mt-3 text-sm text-aui-deep/70">Queue is clear for now.</p>
          ) : (
            <ul className="td-dash-list">
              {openRows.slice(0, 6).map((req) => (
                <li key={req.id}>
                  <p className="td-dash-ask">{plainAskText(req.text)}</p>
                  <p className="td-dash-meta">
                    #{req.id}
                    {req.urgency ? ` · ${req.urgency}` : ""}
                    {fmtAgo(req.created_at) ? ` · asked ${fmtAgo(req.created_at)}` : ""}
                  </p>
                </li>
              ))}
            </ul>
          )}
          <Link className="td-dash-link" to="/ta">
            Go to live queue
          </Link>
        </section>

        <section className="bh-card td-dash-panel">
          <div className="bh-card-title">
            <h2>Recently resolved</h2>
          </div>
          <p className="bh-card-note">Your latest helped asks with timing.</p>
          {busy ? (
            <p className="mt-3 text-sm text-aui-deep/70">Loading…</p>
          ) : helpedRows.length === 0 ? (
            <p className="mt-3 text-sm text-aui-deep/70">
              No resolved asks yet. After you reply and resolve, they land here and
              in Past asks.
            </p>
          ) : (
            <ul className="td-dash-list">
              {helpedRows.map((req) => (
                <li key={req.id}>
                  <p className="td-dash-ask">{plainAskText(req.text)}</p>
                  <p className="td-dash-meta">
                    #{req.id}
                    {fmtAgo(req.helped_at || req.ta_replied_at)
                      ? ` · resolved ${fmtAgo(req.helped_at || req.ta_replied_at)}`
                      : ""}
                  </p>
                </li>
              ))}
            </ul>
          )}
          <Link className="td-dash-link" to="/ta/past">
            Browse past asks
          </Link>
        </section>
      </div>
    </div>
  );
}
