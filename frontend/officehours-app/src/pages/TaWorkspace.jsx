import { useCallback, useEffect, useState } from "react";
import { Navigate } from "react-router";
import { api } from "../api/client.js";
import { useAuth } from "../auth/AuthContext.jsx";

function workPill(status) {
  const value = status || "open";
  if (value === "in_progress") return { label: "helping now", className: "bh-pill-amber" };
  if (value === "claimed") return { label: "claimed", className: "bh-pill-blue" };
  if (value === "helped") return { label: "helped", className: "bh-pill-green" };
  return { label: "open", className: "bh-pill-gray" };
}

function helpModeLabel(mode) {
  if (mode === "face_to_face") return "in person";
  if (mode === "online_meeting") return "online";
  return "message";
}

const FILTERS = [
  ["mine", "Mine"],
  ["backup", "Backup"],
  ["in_progress", "Helping"],
  ["unassigned", "Unassigned"],
  ["all", "All"],
];

const DETAIL_TABS = [
  ["help", "Help"],
  ["reply", "Reply"],
  ["curation", "Curation"],
];

export default function TaWorkspace() {
  const { token, user, activeCourse } = useAuth();
  const [queue, setQueue] = useState([]);
  const [loadInfo, setLoadInfo] = useState(null);
  const [selectedId, setSelectedId] = useState(null);
  const [detailTab, setDetailTab] = useState("help");
  const [notes, setNotes] = useState("");
  const [hint, setHint] = useState("");
  const [reply, setReply] = useState("");
  const [socraticSteps, setSocraticSteps] = useState([]);
  const [showSocratic, setShowSocratic] = useState(false);
  const [showKb, setShowKb] = useState(false);
  const [coachBusy, setCoachBusy] = useState(false);
  const [error, setError] = useState("");
  const [toast, setToast] = useState("");
  const [resolvedCount, setResolvedCount] = useState(0);
  const [helpedCount, setHelpedCount] = useState(0);
  const [assignmentFilter, setAssignmentFilter] = useState("mine");
  const [busy, setBusy] = useState(false);

  const loadQueue = useCallback(async () => {
    try {
      const params = new URLSearchParams({
        course_id: String(activeCourse.id),
        assignment: assignmentFilter,
      });
      const data = await api(`/ta/queue/?${params.toString()}`, { token });
      setQueue(data);
      setError("");
    } catch (err) {
      setError(err.message);
    }
  }, [token, activeCourse, assignmentFilter]);

  const loadPartnerLoad = useCallback(async () => {
    try {
      const data = await api(`/ta/load/?course_id=${activeCourse.id}`, { token });
      setLoadInfo(data);
    } catch {
      setLoadInfo(null);
    }
  }, [token, activeCourse]);

  useEffect(() => {
    loadQueue();
    loadPartnerLoad();
    const id = setInterval(() => {
      loadQueue();
      loadPartnerLoad();
    }, 8000);
    return () => clearInterval(id);
  }, [loadQueue, loadPartnerLoad]);

  useEffect(() => {
    if (!toast) return undefined;
    const id = setTimeout(() => setToast(""), 4000);
    return () => clearTimeout(id);
  }, [toast]);

  useEffect(() => {
    if (selectedId && !queue.some((item) => item.request.id === selectedId)) {
      setSelectedId(null);
    }
  }, [queue, selectedId]);

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
  const inProgressCount = queue.filter(
    (item) => item.request.work_status === "in_progress",
  ).length;

  function selectItem(item) {
    setSelectedId(item.request.id);
    setDetailTab("help");
    setShowSocratic(false);
    setShowKb(false);
    const coach = item.help_coach;
    setNotes(
      coach?.teaching_approach || item.knowledge_entry?.answer_draft || "",
    );
    setHint(
      coach?.student_hint ||
        item.knowledge_entry?.student_hint ||
        item.request.student_hint ||
        "",
    );
    setReply(item.request.ta_reply || "");
    setSocraticSteps(coach?.socratic_steps || []);
    setError("");
  }

  async function runHelpCoach(mode) {
    if (!selected) return;
    setCoachBusy(true);
    setError("");
    try {
      const result = await api("/ta/assist/", {
        method: "POST",
        token,
        body: {
          request_id: selected.request.id,
          mode,
          current_reply: reply || null,
        },
      });
      setToast(result.message || "Help Coach updated");
      if (result.draft_reply) {
        setReply(result.draft_reply);
        setDetailTab("reply");
      }
      if (result.teaching_approach) setNotes(result.teaching_approach);
      if (result.student_hint) setHint(result.student_hint);
      if (Array.isArray(result.socratic_steps)) {
        setSocraticSteps(result.socratic_steps);
        if (mode === "socratic") setShowSocratic(true);
      }
      if (result.help_coach) {
        setQueue((prev) =>
          prev.map((item) =>
            item.request.id === selected.request.id
              ? { ...item, help_coach: result.help_coach }
              : item,
          ),
        );
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setCoachBusy(false);
    }
  }

  async function runAction(path, body, { helpedBump = false } = {}) {
    setBusy(true);
    setError("");
    try {
      const result = await api(path, { method: "POST", token, body });
      setToast(result.message || "Updated");
      if (helpedBump) setHelpedCount((count) => count + 1);
      if (result.request) {
        setQueue((prev) =>
          prev.map((item) =>
            item.request.id === result.request.id
              ? { ...item, request: result.request }
              : item,
          ),
        );
      }
      await loadQueue();
      await loadPartnerLoad();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  async function resolve(status) {
    if (!selected) return;
    if (notes.trim().length < 3) {
      setError("Add a short teaching draft (3+ characters) before sending to curation.");
      setDetailTab("curation");
      return;
    }
    setBusy(true);
    setError("");
    try {
      const result = await api("/ta/resolve/", {
        method: "POST",
        token,
        body: {
          request_id: selected.request.id,
          teaching_notes: notes,
          student_hint: hint || null,
          resolution_status: status,
        },
      });
      setToast(result.message || "Saved for professor review");
      setResolvedCount((count) => count + 1);
      setHelpedCount((count) => count + 1);
      setSelectedId(null);
      setNotes("");
      setHint("");
      setReply("");
      await loadQueue();
      await loadPartnerLoad();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  const req = selected?.request;
  const coach = selected?.help_coach;
  const work = workPill(req?.work_status);
  const iAmPrimary = req?.assigned_ta === user.display_name;
  const iAmBackup = req?.alternative_ta === user.display_name;
  const iClaimed = req?.claimed_by === user.display_name;
  const myLoad = (loadInfo?.tas || []).find((ta) => ta.name === user.display_name);
  const partnerLoad = (loadInfo?.tas || []).find((ta) => ta.name !== user.display_name);

  return (
    <div className="fade-up ta-shell">
      <header className="ta-top">
        <div>
          <h1 className="bh-page-title">TA Dashboard</h1>
          <p className="bh-page-subtitle">
            {activeCourse.code} — {activeCourse.title}
          </p>
        </div>
        <div className="ta-top-metrics">
          <div>
            <strong>{queue.length}</strong>
            <span>open</span>
          </div>
          <div>
            <strong>{inProgressCount}</strong>
            <span>helping</span>
          </div>
          <div>
            <strong>{urgentCount}</strong>
            <span>urgent</span>
          </div>
          <div>
            <strong>{helpedCount}</strong>
            <span>helped</span>
          </div>
          <div>
            <strong>{resolvedCount}</strong>
            <span>curated</span>
          </div>
        </div>
      </header>

      {(myLoad || partnerLoad) && (
        <p className="ta-load-line">
          Load
          {myLoad ? (
            <>
              {" · "}
              <strong>you {myLoad.queue_depth ?? "—"}</strong>
            </>
          ) : null}
          {partnerLoad ? (
            <>
              {" · "}
              {partnerLoad.name} {partnerLoad.queue_depth ?? "—"}
            </>
          ) : null}
        </p>
      )}

      <div className={`ta-layout${selected ? " ta-layout-split" : ""}`}>
        <section id="queue" className="bh-card ta-queue-panel scroll-mt-6">
          <div className="bh-card-title">
            <h2>Queue</h2>
            <span className="bh-pill bh-pill-green live-pulse">live</span>
          </div>

          <div className="ta-filters">
            {FILTERS.map(([value, label]) => (
              <button
                key={value}
                type="button"
                className={`ta-filter${assignmentFilter === value ? " is-active" : ""}`}
                onClick={() => setAssignmentFilter(value)}
              >
                {label}
              </button>
            ))}
          </div>

          {error ? <p className="mt-2 text-sm text-red-700">{error}</p> : null}
          {toast ? <p className="mt-2 text-sm text-emerald-700">{toast}</p> : null}

          {queue.length === 0 ? (
            <p className="bh-card-note mt-4">No open requests for this filter.</p>
          ) : (
            <ul className="ta-queue-list">
              {queue.map((item) => {
                const request = item.request;
                const urgency = (request.urgency || "n/a").toLowerCase();
                const status = workPill(request.work_status);
                const similarN = item.help_coach?.similar_open_count || 0;
                const active = selectedId === request.id;
                return (
                  <li key={request.id}>
                    <button
                      type="button"
                      className={`ta-queue-item${active ? " is-active" : ""}`}
                      onClick={() => selectItem(item)}
                    >
                      <div className="ta-queue-item-top">
                        <span className="ta-queue-id">#{request.id}</span>
                        <span className={`bh-pill ${status.className}`}>{status.label}</span>
                        {similarN > 0 ? (
                          <span
                            className={`bh-pill ${
                              similarN >= 2 ? "bh-pill-amber" : "bh-pill-blue"
                            }`}
                          >
                            {similarN} similar
                          </span>
                        ) : null}
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
                      </div>
                      <p className="ta-queue-text">{request.text}</p>
                      <p className="ta-queue-meta">
                        {request.anonymous
                          ? "Anonymous"
                          : request.student_name || request.student_id || "Identified"}
                        {" · "}
                        {helpModeLabel(request.help_mode)}
                        {" · "}
                        {request.oracle_category || request.category || "topic"}
                        {" · "}
                        {request.assigned_ta || "Unassigned"}
                        {request.alternative_ta ? ` / ${request.alternative_ta}` : ""}
                      </p>
                    </button>
                  </li>
                );
              })}
            </ul>
          )}
        </section>

        {selected && req ? (
          <section className="bh-card ta-detail-panel">
            <div className="ta-detail-head">
              <div>
                <div className="ta-detail-kicker">
                  <span className={`bh-pill ${work.className}`}>{work.label}</span>
                  <span className="bh-pill bh-pill-gray">
                    {helpModeLabel(req.help_mode)}
                  </span>
                  {req.sensitive ? (
                    <span className="bh-pill bh-pill-amber">sensitive</span>
                  ) : null}
                </div>
                <h2 className="ta-detail-title">Ask #{req.id}</h2>
                <p className="ta-detail-question">{req.text}</p>
                <p className="ta-detail-meta">
                  {[
                    req.anonymous
                      ? "Anonymous"
                      : req.student_name || req.student_id || "Identified",
                    req.oracle_category || req.category,
                    req.oracle_difficulty,
                    req.oracle_estimated_minutes != null
                      ? `~${req.oracle_estimated_minutes} min`
                      : null,
                    selected.learning_style || req.learning_style,
                    req.assigned_ta ? `→ ${req.assigned_ta}` : null,
                  ]
                    .filter(Boolean)
                    .join(" · ")}
                </p>
              </div>
              <div className="ta-detail-actions">
                <button
                  type="button"
                  disabled={busy || (req.claimed_by && !iClaimed && req.work_status !== "open")}
                  className="btn-primary px-3 py-2 text-sm"
                  onClick={() => runAction("/ta/claim/", { request_id: req.id })}
                >
                  Claim
                </button>
                <button
                  type="button"
                  disabled={busy}
                  className="btn-ghost px-3 py-2 text-sm"
                  onClick={() =>
                    runAction("/ta/work-status/", {
                      request_id: req.id,
                      status: "in_progress",
                    })
                  }
                >
                  Start
                </button>
                <button
                  type="button"
                  disabled={busy}
                  className="btn-ghost px-3 py-2 text-sm"
                  onClick={() =>
                    runAction(
                      "/ta/work-status/",
                      { request_id: req.id, status: "helped" },
                      { helpedBump: true },
                    )
                  }
                >
                  Done
                </button>
                {iAmBackup ? (
                  <button
                    type="button"
                    disabled={busy}
                    className="btn-ghost px-3 py-2 text-sm"
                    onClick={() => runAction("/ta/take-backup/", { request_id: req.id })}
                  >
                    Take primary
                  </button>
                ) : null}
                {!iAmPrimary &&
                !iAmBackup &&
                (!req.assigned_ta || req.assigned_ta === "Unassigned") ? (
                  <button
                    type="button"
                    disabled={busy}
                    className="btn-ghost px-3 py-2 text-sm"
                    onClick={() => runAction("/ta/take-backup/", { request_id: req.id })}
                  >
                    Take ownership
                  </button>
                ) : null}
              </div>
            </div>

            {req.code_snippet ? (
              <pre className="ta-code">{req.code_snippet}</pre>
            ) : null}

            <div className="ta-tabs" role="tablist">
              {DETAIL_TABS.map(([id, label]) => (
                <button
                  key={id}
                  type="button"
                  role="tab"
                  aria-selected={detailTab === id}
                  className={`ta-tab${detailTab === id ? " is-active" : ""}`}
                  onClick={() => setDetailTab(id)}
                >
                  {label}
                  {id === "help" && coach?.similar_open_count
                    ? ` (${coach.similar_open_count})`
                    : ""}
                </button>
              ))}
            </div>

            {detailTab === "help" ? (
              <div className="ta-tab-panel">
                <div className="ta-coach-toolbar">
                  <p className="ta-section-label">Help Coach</p>
                  <div className="ta-coach-buttons">
                    <button
                      type="button"
                      disabled={busy || coachBusy}
                      className="btn-primary px-3 py-1.5 text-xs"
                      onClick={() => runHelpCoach("draft_reply")}
                    >
                      {coachBusy ? "Working…" : "Draft reply"}
                    </button>
                    <button
                      type="button"
                      disabled={busy || coachBusy}
                      className="btn-ghost px-3 py-1.5 text-xs"
                      onClick={() => runHelpCoach("socratic")}
                    >
                      Socratic steps
                    </button>
                    <button
                      type="button"
                      disabled={busy || coachBusy}
                      className="btn-ghost px-3 py-1.5 text-xs"
                      onClick={() => runHelpCoach("refresh_teaching")}
                    >
                      Refresh script
                    </button>
                  </div>
                </div>

                {coach?.group_help_suggested || coach?.similar_open_count ? (
                  <div className="ta-soft-block">
                    <p className="ta-section-label">
                      Similar open asks
                      {coach.group_help_suggested ? " · consider group help" : ""}
                    </p>
                    <ul className="ta-link-list">
                      {(coach.similar_open || []).map((peer) => (
                        <li key={peer.id}>
                          <button
                            type="button"
                            onClick={() => {
                              const peerItem = queue.find(
                                (item) => item.request.id === peer.id,
                              );
                              if (peerItem) selectItem(peerItem);
                            }}
                          >
                            #{peer.id}
                          </button>
                          <span>{(peer.text || "").slice(0, 100)}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                ) : null}

                <div className="ta-soft-block">
                  <button
                    type="button"
                    className="ta-disclosure"
                    onClick={() => setShowSocratic((value) => !value)}
                  >
                    Socratic steps ({socraticSteps.length || 0})
                    <span>{showSocratic ? "Hide" : "Show"}</span>
                  </button>
                  {showSocratic && socraticSteps.length ? (
                    <ol className="ta-steps">
                      {socraticSteps.map((step) => (
                        <li key={step}>{step}</li>
                      ))}
                    </ol>
                  ) : null}
                </div>

                {coach?.similar_kb?.length ? (
                  <div className="ta-soft-block">
                    <button
                      type="button"
                      className="ta-disclosure"
                      onClick={() => setShowKb((value) => !value)}
                    >
                      Approved KB ({coach.similar_kb.length})
                      <span>{showKb ? "Hide" : "Show"}</span>
                    </button>
                    {showKb ? (
                      <ul className="ta-kb-list">
                        {coach.similar_kb.map((hit) => (
                          <li key={`${hit.id}-${hit.question_text}`}>
                            <p>
                              #{hit.id}
                              {hit.similarity != null
                                ? ` · ${Math.round(Number(hit.similarity) * 100)}%`
                                : ""}
                            </p>
                            <p>{(hit.question_text || "").slice(0, 120)}</p>
                          </li>
                        ))}
                      </ul>
                    ) : null}
                  </div>
                ) : null}

                {coach?.kb_insight || req.oracle?.synthesizer?.kb_insight ? (
                  <p className="ta-footnote">
                    {coach?.kb_insight || req.oracle?.synthesizer?.kb_insight}
                  </p>
                ) : null}
              </div>
            ) : null}

            {detailTab === "reply" ? (
              <div className="ta-tab-panel">
                {(req.help_mode === "message" || !req.help_mode) ? (
                  <>
                    <div className="ta-coach-toolbar">
                      <p className="ta-section-label">Message the student</p>
                      <div className="ta-coach-buttons">
                        <button
                          type="button"
                          disabled={busy || coachBusy}
                          className="btn-ghost px-3 py-1.5 text-xs"
                          onClick={() => runHelpCoach("draft_reply")}
                        >
                          Draft
                        </button>
                        <button
                          type="button"
                          disabled={busy || coachBusy || reply.trim().length < 3}
                          className="btn-ghost px-3 py-1.5 text-xs"
                          onClick={() => runHelpCoach("rewrite_reply")}
                        >
                          Rewrite
                        </button>
                      </div>
                    </div>
                    <textarea
                      className="field-glass mt-2 min-h-36 w-full px-3 py-2.5 text-sm"
                      value={reply}
                      onChange={(event) => setReply(event.target.value)}
                      placeholder="Short reply the student can read on request status…"
                    />
                    <button
                      type="button"
                      disabled={busy || reply.trim().length < 3}
                      className="btn-primary mt-3 px-4 py-2 text-sm"
                      onClick={() =>
                        runAction("/ta/reply/", {
                          request_id: req.id,
                          reply: reply.trim(),
                          update_student_hint: true,
                        })
                      }
                    >
                      Send reply
                    </button>
                    {req.ta_reply ? (
                      <p className="ta-footnote mt-3">
                        Last sent: {req.ta_reply}
                      </p>
                    ) : null}
                  </>
                ) : (
                  <p className="bh-card-note">
                    This student asked for {helpModeLabel(req.help_mode)}. Use Help
                    for coaching notes; reply is for message-mode asks.
                  </p>
                )}
              </div>
            ) : null}

            {detailTab === "curation" ? (
              <div className="ta-tab-panel">
                <p className="ta-section-label">Teaching draft for professor review</p>
                <textarea
                  className="field-glass mt-2 min-h-40 w-full px-3 py-2.5 text-sm"
                  value={notes}
                  onChange={(event) => setNotes(event.target.value)}
                  placeholder="How you taught this — becomes a pending KB draft"
                />
                <p className="ta-section-label mt-4">Student hint</p>
                <textarea
                  className="field-glass mt-2 min-h-20 w-full px-3 py-2.5 text-sm"
                  value={hint}
                  onChange={(event) => setHint(event.target.value)}
                  placeholder="Non-spoiler nudge for the student"
                />
                <div className="mt-4 flex flex-wrap gap-2">
                  <button
                    type="button"
                    disabled={busy}
                    className="btn-primary px-4 py-2 text-sm"
                    onClick={() => resolve("resolved")}
                  >
                    Send to curation
                  </button>
                  <button
                    type="button"
                    disabled={busy}
                    className="btn-ghost px-4 py-2 text-sm"
                    onClick={() => resolve("needs_professor")}
                  >
                    Needs professor
                  </button>
                </div>
              </div>
            ) : null}
          </section>
        ) : (
          <section className="bh-card ta-detail-panel ta-detail-empty">
            <p className="bh-card-note">
              Select an ask from the queue to help with Help Coach, reply, or send
              a teaching draft.
            </p>
          </section>
        )}
      </div>
    </div>
  );
}
