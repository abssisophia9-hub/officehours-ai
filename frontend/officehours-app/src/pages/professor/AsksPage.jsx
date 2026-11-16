import { useMemo, useState } from "react";
import { Link } from "react-router";
import { assignedToProfessor, useProfessorData } from "./ProfessorData.jsx";

const OPEN_WORK = new Set(["open", "claimed", "in_progress"]);

function personLabel(request) {
  if (request.anonymous) return "Anonymous";
  return request.student_name || request.student_id || "Anonymous";
}

function topicLabel(request) {
  return (request.category || "uncategorized").replaceAll("_", " ");
}

function ageLabel(createdAt) {
  if (!createdAt) return "—";
  const then = new Date(createdAt).getTime();
  if (!Number.isFinite(then)) return "—";
  const mins = Math.max(0, Math.round((Date.now() - then) / 60000));
  if (mins < 60) return `${mins}m ago`;
  if (mins < 60 * 48) return `${Math.round(mins / 60)}h ago`;
  return `${Math.round(mins / (60 * 24))}d ago`;
}

function previewText(request) {
  const text = (request.text || "").replace(/\s+/g, " ").trim();
  if (!text) return "No question text";
  return text.length > 110 ? `${text.slice(0, 109)}…` : text;
}

function laneFor(request, assignedIds, urgentIds) {
  if (assignedIds.has(request.id)) return "assigned";
  if (urgentIds.has(request.id)) return "urgent";
  return null;
}

export default function AsksPage() {
  const { requests, commandCenter, ready, error } = useProfessorData();
  const [filter, setFilter] = useState("all");

  const assigned = assignedToProfessor(requests);
  const escalations = commandCenter?.escalations || [];
  const urgentIds = useMemo(
    () => new Set(escalations.map((item) => item.request_id)),
    [escalations],
  );
  const assignedIds = useMemo(
    () => new Set(assigned.map((item) => item.id)),
    [assigned],
  );
  const urgentRows = useMemo(
    () =>
      (requests || []).filter(
        (item) =>
          urgentIds.has(item.id) && OPEN_WORK.has(item.work_status || "open"),
      ),
    [requests, urgentIds],
  );

  const feed = useMemo(() => {
    const open = (requests || []).filter((item) =>
      OPEN_WORK.has(item.work_status || "open"),
    );
    const ranked = open
      .map((item) => {
        const lane = laneFor(item, assignedIds, urgentIds);
        if (!lane) return null;
        return { item, lane };
      })
      .filter(Boolean)
      .sort((a, b) => {
        const aTime = new Date(a.item.created_at || 0).getTime();
        const bTime = new Date(b.item.created_at || 0).getTime();
        return bTime - aTime;
      });
    if (filter === "assigned") {
      return ranked.filter((row) => row.lane === "assigned");
    }
    if (filter === "urgent") {
      return ranked.filter((row) => row.lane === "urgent");
    }
    return ranked;
  }, [requests, assignedIds, urgentIds, filter]);

  function toggleFilter(next) {
    setFilter((prev) => (prev === next ? "all" : next));
  }

  // apple-design: Purpose; Agency; Simplicity — not minimalism; Feedback;
  // Familiarity; Response — kill latency (6).

  return (
    <div className="pf-page pf-desk pf-desk-feed">
      <header className="pf-head pf-desk-head">
        <div>
          <p className="pf-kicker">Teaching desk</p>
          <h1>Your desk</h1>
        </div>
      </header>

      <div className="pf-desk-shell">
        <div className="pf-desk-kpis" role="tablist" aria-label="Ask filters">
          <button
            type="button"
            role="tab"
            aria-selected={filter === "assigned"}
            className={`pf-desk-kpi${filter === "assigned" ? " is-on" : ""}`}
            onClick={() => toggleFilter("assigned")}
          >
            <strong>{assigned.length}</strong>
            <span>Assigned</span>
          </button>
          <button
            type="button"
            role="tab"
            aria-selected={filter === "urgent"}
            className={`pf-desk-kpi pf-desk-kpi-urgent${
              filter === "urgent" ? " is-on" : ""
            }`}
            onClick={() => toggleFilter("urgent")}
          >
            <strong>{urgentRows.length}</strong>
            <span>Urgent</span>
          </button>
        </div>

        {error ? (
          <p className="pf-error" role="alert">
            {error}
          </p>
        ) : null}

        <div className="pf-desk-feed-head">
          <h2>Student asks</h2>
          <div className="pf-desk-pills" role="group" aria-label="Feed filter">
            {[
              { id: "all", label: "All" },
              { id: "urgent", label: "Urgent" },
              { id: "assigned", label: "Assigned" },
            ].map((pill) => (
              <button
                key={pill.id}
                type="button"
                className={`pf-desk-pill${filter === pill.id ? " is-on" : ""}`}
                aria-pressed={filter === pill.id}
                onClick={() => setFilter(pill.id)}
              >
                {pill.label}
              </button>
            ))}
          </div>
        </div>

        <div className="pf-desk-list" aria-live="polite">
          {!ready ? <p className="pf-desk-empty">Loading asks…</p> : null}
          {ready && feed.length === 0 ? (
            <p className="pf-desk-empty">
              All caught up — no pending student asks
            </p>
          ) : null}
          {ready
            ? feed.map(({ item, lane }) => (
                <article key={item.id} className="pf-desk-row">
                  <div className="pf-desk-row-main">
                    <div className="pf-desk-row-tags">
                      <span
                        className={`pf-desk-status pf-desk-status-${lane}`}
                      >
                        {lane === "urgent" ? "Urgent" : "Assigned"}
                      </span>
                      <span className="pf-desk-topic">{topicLabel(item)}</span>
                    </div>
                    <p className="pf-desk-person">{personLabel(item)}</p>
                    <p className="pf-desk-preview">{previewText(item)}</p>
                  </div>
                  <div className="pf-desk-row-side">
                    <time className="pf-desk-age" dateTime={item.created_at}>
                      {ageLabel(item.created_at)}
                    </time>
                    <Link className="pf-desk-reply" to="/professor/team">
                      Reply
                    </Link>
                  </div>
                </article>
              ))
            : null}
        </div>
      </div>
    </div>
  );
}
