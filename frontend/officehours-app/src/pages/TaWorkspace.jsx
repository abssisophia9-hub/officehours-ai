import { useCallback, useEffect, useState } from "react";
import { Navigate } from "react-router";
import { api } from "../api/client.js";
import { useAuth } from "../auth/AuthContext.jsx";

const ICONS = {
  queue: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
      <path d="M8 6h13M8 12h13M8 18h13M3 6h.01M3 12h.01M3 18h.01" />
    </svg>
  ),
  check: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
      <circle cx="12" cy="12" r="9" />
      <path d="M8.5 12.5l2.5 2.5 5-5.5" />
    </svg>
  ),
  flame: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
      <path d="M12 2s5 4.5 5 10a5 5 0 0 1-10 0c0-2 1-3.8 2-5 0 2 1 3 2 3 0-3 1-6.5 1-8z" />
    </svg>
  ),
  clock: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
      <circle cx="12" cy="12" r="9" />
      <path d="M12 7v5l3 3" />
    </svg>
  ),
};

export default function TaWorkspace() {
  const { token, user, activeCourse } = useAuth();
  const [queue, setQueue] = useState([]);
  const [selectedId, setSelectedId] = useState(null);
  const [notes, setNotes] = useState("");
  const [hint, setHint] = useState("");
  const [error, setError] = useState("");
  const [toast, setToast] = useState("");
  const [resolvedCount, setResolvedCount] = useState(0);
  const [assignmentFilter, setAssignmentFilter] = useState("mine");

  const loadQueue = useCallback(async () => {
    try {
      const params = new URLSearchParams({
        course_id: String(activeCourse.id),
        assignment: assignmentFilter,
        ta_name: user.display_name,
      });
      const data = await api(`/ta/queue/?${params.toString()}`, { token });
      setQueue(data);
    } catch (err) {
      setError(err.message);
    }
  }, [token, activeCourse, assignmentFilter, user.display_name]);

  useEffect(() => {
    loadQueue();
    const id = setInterval(loadQueue, 8000);
    return () => clearInterval(id);
  }, [loadQueue]);

  if (!activeCourse) return <Navigate to="/" replace />;
  if (activeCourse.role !== "ta") {
    return (
      <Navigate
        to={activeCourse.role === "professor" ? "/professor" : "/student"}
        replace
      />
    );
  }

  const selected = queue.find((item) => item.request.id === selectedId) || null;
  const urgentCount = queue.filter((item) =>
    ["high", "urgent"].includes((item.request.urgency || "").toLowerCase()),
  ).length;
  const waits = queue
    .map((item) => item.request.estimated_wait_minutes)
    .filter((value) => typeof value === "number");
  const avgWait = waits.length
    ? Math.round(waits.reduce((total, value) => total + value, 0) / waits.length)
    : null;

  async function resolve(status) {
    if (!selected) return;
    setError("");
    try {
      const result = await api("/ta/resolve/", {
        method: "POST",
        token,
        body: {
          request_id: selected.request.id,
          ta_name: user.display_name,
          teaching_notes: notes,
          student_hint: hint || null,
          resolution_status: status,
        },
      });
      setToast(result.message || "Saved for professor review");
      setResolvedCount((count) => count + 1);
      setSelectedId(null);
      setNotes("");
      setHint("");
      await loadQueue();
    } catch (err) {
      setError(err.message);
    }
  }

  return (
    <div className="fade-up">
      <h1 className="bh-page-title">TA Dashboard</h1>
      <p className="bh-page-subtitle">
        Work the live queue and prepare teaching drafts for professor curation ·{" "}
        {activeCourse.code} — {activeCourse.title}
      </p>

      <div className="bh-stats">
        <article className="bh-stat-card">
          <div className="bh-stat-head">Open Queue {ICONS.queue}</div>
          <p className="bh-stat-value">{queue.length}</p>
          <p className="bh-stat-note">Requests waiting in {activeCourse.code}</p>
        </article>
        <article className="bh-stat-card">
          <div className="bh-stat-head">Urgent {ICONS.flame}</div>
          <p className="bh-stat-value">{urgentCount}</p>
          <p className="bh-stat-note">High-urgency asks to take first</p>
        </article>
        <article className="bh-stat-card">
          <div className="bh-stat-head">Avg Wait {ICONS.clock}</div>
          <p className="bh-stat-value">{avgWait === null ? "—" : `${avgWait}m`}</p>
          <p className="bh-stat-note">Oracle wait estimate</p>
        </article>
        <article className="bh-stat-card">
          <div className="bh-stat-head">Resolved {ICONS.check}</div>
          <p className="bh-stat-value">{resolvedCount}</p>
          <p className="bh-stat-note">Sent to curation this session</p>
        </article>
      </div>

      <section id="queue" className="bh-card scroll-mt-6">
        <div className="bh-card-title">
          <h2>Live Queue</h2>
          <span className="bh-pill bh-pill-green live-pulse">live</span>
        </div>
        <div className="mt-3 flex flex-wrap gap-2">
          {[
            ["mine", "Assigned to me"],
            ["backup", "I'm backup"],
            ["unassigned", "Unassigned"],
            ["all", "All course asks"],
          ].map(([value, label]) => (
            <button
              key={value}
              type="button"
              className={`btn-ghost px-3 py-1.5 text-xs ${
                assignmentFilter === value ? "ring-2 ring-aui-deep/30" : ""
              }`}
              onClick={() => setAssignmentFilter(value)}
            >
              {label}
            </button>
          ))}
        </div>
        <p className="bh-card-note mt-2">
          Dual-TA courses: primary and backup are set by the Matcher using this
          course&apos;s TA roster and queue depth.
        </p>
        {error ? <p className="mt-2 text-sm text-red-700">{error}</p> : null}
        {toast ? <p className="mt-2 text-sm text-emerald-700">{toast}</p> : null}

        {queue.length === 0 ? (
          <p className="bh-card-note mt-4">No open requests for this course.</p>
        ) : (
          <table className="bh-table">
            <thead>
              <tr>
                <th>#</th>
                <th>Question</th>
                <th>From</th>
                <th>Ask</th>
                <th>Help</th>
                <th>Category</th>
                <th>Urgency</th>
                <th>Wait</th>
                <th>Primary</th>
                <th>Backup</th>
              </tr>
            </thead>
            <tbody>
              {queue.map((item) => {
                const request = item.request;
                const urgency = (request.urgency || "n/a").toLowerCase();
                const helpMode = request.help_mode || "message";
                const preferred = request.preferred_helper || "either";
                return (
                  <tr
                    key={request.id}
                    className={`bh-row-click${selectedId === request.id ? " bh-row-active" : ""}`}
                    onClick={() => {
                      setSelectedId(request.id);
                      setNotes(item.knowledge_entry?.answer_draft || "");
                      setHint(item.knowledge_entry?.student_hint || "");
                    }}
                  >
                    <td className="font-semibold">#{request.id}</td>
                    <td className="max-w-[22rem]">
                      <span className="line-clamp-2">{request.text}</span>
                    </td>
                    <td>
                      {request.anonymous
                        ? "Anonymous"
                        : request.student_name || request.student_id || "Identified"}
                    </td>
                    <td>
                      <span
                        className={`bh-pill ${
                          preferred === "professor"
                            ? "bh-pill-amber"
                            : preferred === "ta"
                              ? "bh-pill-green"
                              : "bh-pill-gray"
                        }`}
                      >
                        {preferred === "professor"
                          ? "professor"
                          : preferred === "ta"
                            ? "TA"
                            : "either"}
                      </span>
                    </td>
                    <td>
                      <span
                        className={`bh-pill ${
                          helpMode === "face_to_face"
                            ? "bh-pill-amber"
                            : helpMode === "online_meeting"
                              ? "bh-pill-blue"
                              : "bh-pill-gray"
                        }`}
                      >
                        {helpMode === "face_to_face"
                          ? "in person"
                          : helpMode === "online_meeting"
                            ? "online"
                            : "message"}
                      </span>
                    </td>
                    <td>{request.oracle_category || request.category || "n/a"}</td>
                    <td>
                      <span
                        className={`bh-pill ${
                          ["high", "urgent"].includes(urgency)
                            ? "bh-pill-red"
                            : urgency === "medium"
                              ? "bh-pill-amber"
                              : "bh-pill-gray"
                        }`}
                      >
                        {urgency}
                      </span>
                    </td>
                    <td>
                      {request.estimated_wait_minutes != null
                        ? `~${request.estimated_wait_minutes}m`
                        : "—"}
                    </td>
                    <td>{request.assigned_ta || "Unassigned"}</td>
                    <td>{request.alternative_ta || "—"}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </section>

      {selected ? (
        <section className="bh-card">
          <div className="bh-card-title">
            <h2>Teaching Draft · #{selected.request.id}</h2>
            <span className="bh-pill bh-pill-blue">
              {selected.request.oracle_category || "uncategorized"}
            </span>
          </div>
          <p className="bh-card-note">{selected.request.text}</p>
          <div className="mt-2 flex flex-wrap gap-2 text-xs">
            <span className="bh-pill bh-pill-gray">
              {selected.request.anonymous
                ? "Anonymous"
                : selected.request.student_name ||
                  selected.request.student_id ||
                  "Identified"}
            </span>
            <span
              className={`bh-pill ${
                selected.request.preferred_helper === "professor"
                  ? "bh-pill-amber"
                  : selected.request.preferred_helper === "ta"
                    ? "bh-pill-green"
                    : "bh-pill-gray"
              }`}
            >
              {selected.request.preferred_helper === "professor"
                ? "Asked for professor"
                : selected.request.preferred_helper === "ta"
                  ? "Asked for a TA"
                  : "Either TA or professor"}
            </span>
            <span
              className={`bh-pill ${
                selected.request.help_mode === "face_to_face"
                  ? "bh-pill-amber"
                  : selected.request.help_mode === "online_meeting"
                    ? "bh-pill-blue"
                    : "bh-pill-gray"
              }`}
            >
              {selected.request.help_mode === "face_to_face"
                ? "Wants face-to-face"
                : selected.request.help_mode === "online_meeting"
                  ? "Wants online meeting"
                  : "Message / async"}
            </span>
          </div>
          {selected.request.recommended_action ? (
            <p className="mt-2 rounded-lg bg-amber-50 px-3 py-2 text-xs text-amber-950">
              <strong>Suggested action:</strong> {selected.request.recommended_action}
            </p>
          ) : null}
          {selected.request.code_snippet ? (
            <pre className="soft-stat mt-3 overflow-x-auto font-mono text-xs">
              {selected.request.code_snippet}
            </pre>
          ) : null}

          <label className="mt-4 block text-xs font-semibold uppercase tracking-wide text-aui-deep/60">
            Teaching draft
            <textarea
              className="field-glass mt-1.5 min-h-40 w-full px-3 py-2.5 text-sm"
              value={notes}
              onChange={(event) => setNotes(event.target.value)}
            />
          </label>
          <label className="mt-3 block text-xs font-semibold uppercase tracking-wide text-aui-deep/60">
            Student hint
            <textarea
              className="field-glass mt-1.5 min-h-20 w-full px-3 py-2.5 text-sm"
              value={hint}
              onChange={(event) => setHint(event.target.value)}
              placeholder="Student hint"
            />
          </label>
          <div className="mt-4 flex flex-wrap gap-2">
            <button
              type="button"
              className="btn-primary px-4 py-2 text-sm"
              onClick={() => resolve("resolved")}
            >
              Mark resolved → professor curation
            </button>
            <button
              type="button"
              className="btn-ghost px-4 py-2 text-sm"
              onClick={() => resolve("needs_professor")}
            >
              Needs professor
            </button>
          </div>
        </section>
      ) : (
        <section className="bh-card">
          <p className="bh-card-note">
            Select a request in the queue to edit its teaching draft.
          </p>
        </section>
      )}
    </div>
  );
}
