import { useCallback, useEffect, useState } from "react";
import { Navigate } from "react-router";
import { api } from "../api/client.js";
import { pageItems, pageMeta } from "../api/page.js";
import { useAuth } from "../auth/AuthContext.jsx";

function workPill(status) {
  const value = status || "open";
  if (value === "in_progress") return { label: "helping now", className: "bh-pill-amber" };
  if (value === "claimed") return { label: "claimed", className: "bh-pill-blue" };
  if (value === "helped") return { label: "helped", className: "bh-pill-green" };
  return { label: "open", className: "bh-pill-gray" };
}

export default function TaWorkspace() {
  const { token, user, activeCourse } = useAuth();
  const [queue, setQueue] = useState([]);
  const [loadInfo, setLoadInfo] = useState(null);
  const [selectedId, setSelectedId] = useState(null);
  const [notes, setNotes] = useState("");
  const [hint, setHint] = useState("");
  const [reply, setReply] = useState("");
  const [socraticSteps, setSocraticSteps] = useState([]);
  const [coachBusy, setCoachBusy] = useState(false);
  const [error, setError] = useState("");
  const [toast, setToast] = useState("");
  const [resolvedCount, setResolvedCount] = useState(0);
  const [helpedCount, setHelpedCount] = useState(0);
  const [assignmentFilter, setAssignmentFilter] = useState("desk");
  const [busy, setBusy] = useState(false);
  const [meetingOpen, setMeetingOpen] = useState(false);
  const [meetingTitle, setMeetingTitle] = useState("");
  const [meetingWhen, setMeetingWhen] = useState("");
  const [meetingPlace, setMeetingPlace] = useState("");
  const [goldCategory, setGoldCategory] = useState("conceptual_question");
  const [goldHintUseful, setGoldHintUseful] = useState("1");
  const [goldBusy, setGoldBusy] = useState(false);
  const [queuePage, setQueuePage] = useState({ has_more: false, total: 0 });

  const loadQueue = useCallback(async () => {
    try {
      const params = new URLSearchParams({
        course_id: String(activeCourse.id),
        assignment: assignmentFilter,
        limit: "50",
        offset: "0",
      });
      const data = await api(`/ta/queue/?${params.toString()}`, { token });
      setQueue(pageItems(data));
      setQueuePage(pageMeta(data));
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

  async function selectItem(item) {
    setSelectedId(item.request.id);
    const existing = item.help_coach;
    setNotes(
      existing?.teaching_approach || item.knowledge_entry?.answer_draft || "",
    );
    setHint(
      existing?.student_hint ||
        item.knowledge_entry?.student_hint ||
        item.request.student_hint ||
        "",
    );
    setReply(item.request.ta_reply || item.knowledge_entry?.student_hint || "");
    setSocraticSteps(existing?.socratic_steps || []);
    setMeetingOpen(false);
    setMeetingTitle(
      `Group review: ${item.request.triage_category || item.request.category || "topic"}`,
    );
    setMeetingWhen("");
    setMeetingPlace("");
    setError("");
    if (existing) return;
    setCoachBusy(true);
    try {
      const coach = await api(`/ta/coach/?request_id=${item.request.id}`, { token });
      setNotes(coach.teaching_approach || item.knowledge_entry?.answer_draft || "");
      setHint(
        coach.student_hint ||
          item.knowledge_entry?.student_hint ||
          item.request.student_hint ||
          "",
      );
      setSocraticSteps(coach.socratic_steps || []);
      setQueue((prev) =>
        prev.map((row) =>
          row.request.id === item.request.id ? { ...row, help_coach: coach } : row,
        ),
      );
    } catch (err) {
      setError(err.message);
    } finally {
      setCoachBusy(false);
    }
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
      if (result.draft_reply) setReply(result.draft_reply);
      if (result.teaching_approach) setNotes(result.teaching_approach);
      if (result.student_hint) setHint(result.student_hint);
      if (Array.isArray(result.socratic_steps)) {
        setSocraticSteps(result.socratic_steps);
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

  async function proposeGroupMeeting() {
    if (!selected || !req) return;
    const when = meetingWhen.trim();
    const place = meetingPlace.trim();
    if (!when || !place) {
      setError("Add a shared time and place/link for the group meeting.");
      setMeetingOpen(true);
      return;
    }
    const peerIds = (selected.help_coach?.similar_open || []).map((peer) => peer.id);
    const requestIds = Array.from(new Set([req.id, ...peerIds]));
    const title = (
      meetingTitle ||
      `Group review: ${req.triage_category || req.category || "topic"}`
    ).trim();
    setBusy(true);
    setError("");
    try {
      await api("/actions/recommendations/", {
        method: "POST",
        token,
        body: {
          card_id: `ta-group-${req.cluster_id || req.id}-${Date.now()}`,
          action_kind: "group_session",
          action_title: title,
          status: "approved",
          cluster_id: req.cluster_id || null,
          request_ids: requestIds,
          professor_note: "Proposed by TA from Help Coach similar asks.",
          meeting_title: title,
          meeting_when: when,
          meeting_place: place,
        },
      });
      setToast(
        `Group meeting set for ${requestIds.length} asks · ${when} · ${place}`,
      );
      setMeetingOpen(false);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
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
      setError("Add at least a short teaching draft (3+ characters) before resolving.");
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
  const tags = req?.triage_tags || [];
  const work = workPill(req?.work_status);
  const iAmPrimary = req?.assigned_ta === user.display_name;
  const iAmBackup = req?.alternative_ta === user.display_name;
  const iClaimed =
    req?.claimed_by_user_id === user.id || req?.claimed_by === user.display_name;

  return (
    <div className="taq">
      <header className="taq-head">
        <h1 className="taq-title">Queue</h1>
        <p className="taq-sub">
          {activeCourse.code} · {activeCourse.title}
          {loadInfo?.ta_count ? ` · ${loadInfo.ta_count} TAs` : ""}
          {helpedCount || resolvedCount
            ? ` · helped ${helpedCount} · curation ${resolvedCount}`
            : ""}
        </p>
      </header>

      <div className="taq-layout">
        <section id="queue" className="taq-queue scroll-mt-6">
          <div className="taq-filters">
            {[
              ["desk", "My desk"],
              ["mine", "Assigned / claimed by me"],
              ["backup", "I'm backup"],
              ["in_progress", "I'm helping now"],
              ["unassigned", "Unassigned"],
              ["all", "All open asks"],
            ].map(([value, label]) => (
              <button
                key={value}
                type="button"
                className={`taq-filter${assignmentFilter === value ? " taq-filter-on" : ""}`}
                onClick={() => setAssignmentFilter(value)}
              >
                {label}
              </button>
            ))}
          </div>

          {error ? <p className="taq-msg taq-msg-err">{error}</p> : null}
          {toast ? <p className="taq-msg taq-msg-ok">{toast}</p> : null}

          {queue.length === 0 ? (
            <p className="taq-empty">No open asks. New asks appear here.</p>
          ) : (
            <div className="taq-list" role="list">
              <div className="taq-list-head" aria-hidden="true">
                <span>Student</span>
                <span>Ask</span>
                <span>Course</span>
                <span>Wait</span>
                <span>Status</span>
              </div>
              {queue.map((item) => {
                const request = item.request;
                const status = workPill(request.work_status);
                const wait =
                  typeof request.estimated_wait_minutes === "number"
                    ? `${request.estimated_wait_minutes}m`
                    : "—";
                const from = request.anonymous
                  ? "Anonymous"
                  : request.student_name || request.student_id || "Identified";
                return (
                  <button
                    key={request.id}
                    type="button"
                    role="listitem"
                    className={`taq-row${selectedId === request.id ? " taq-row-on" : ""}`}
                    onClick={() => selectItem(item)}
                  >
                    <span className="taq-cell taq-cell-student">{from}</span>
                    <span className="taq-cell taq-cell-ask">
                      <span className="taq-ask-id">#{request.id}</span>{" "}
                      {request.text}
                    </span>
                    <span className="taq-cell taq-cell-course">{activeCourse.code}</span>
                    <span className="taq-cell taq-cell-wait">{wait}</span>
                    <span className="taq-cell taq-cell-status">
                      <span className={`bh-pill ${status.className}`}>{status.label}</span>
                    </span>
                  </button>
                );
              })}
            </div>
          )}
          {queuePage.has_more ? (
            <p className="taq-page-note">
              Showing {queue.length} of {queuePage.total}.
            </p>
          ) : null}
        </section>

        <aside className="taq-detail">
          {selected && req ? (
            <>
              <section className="taq-ask">
                <div className="taq-ask-top">
                  <h2 className="taq-ask-title">Ask #{req.id}</h2>
                  <span className={`bh-pill ${work.className}`}>{work.label}</span>
                </div>
                <p className="taq-ask-body">{req.text}</p>
                <p className="taq-meta">
                  {req.anonymous
                    ? "Quiet ask"
                    : req.student_name || req.student_id || "Identified"}
                  {" · "}
                  {req.help_mode === "face_to_face"
                    ? "Face-to-face"
                    : req.help_mode === "online_meeting"
                      ? "Online meeting"
                      : "Message"}
                  {" · "}
                  {req.triage_category || req.category || "n/a"}
                  {req.urgency ? ` · ${req.urgency}` : ""}
                  {req.claimed_by ? ` · claimed by ${req.claimed_by}` : ""}
                </p>
                {tags.length ? (
                  <p className="taq-meta">Tags: {tags.join(", ")}</p>
                ) : null}
                {req.triage?.matcher?.rationale || req.assigned_ta ? (
                  <p className="taq-meta">
                    Matcher:{" "}
                    {req.triage?.matcher?.rationale ||
                      `${req.assigned_ta || "Unassigned"}${
                        req.alternative_ta ? ` (backup ${req.alternative_ta})` : ""
                      }`}
                  </p>
                ) : null}
                {req.recommended_action ? (
                  <p className="taq-meta">
                    <strong>Suggested:</strong> {req.recommended_action}
                  </p>
                ) : null}
                {req.code_snippet ? (
                  <pre className="taq-code">{req.code_snippet}</pre>
                ) : null}
              </section>

              <section className="taq-actions">
                <div className="taq-action-row">
                  <button
                    type="button"
                    disabled={busy || (req.claimed_by && !iClaimed && req.work_status !== "open")}
                    className="btn-primary taq-btn"
                    onClick={() => runAction("/ta/claim/", { request_id: req.id })}
                  >
                    Claim ask
                  </button>
                  <button
                    type="button"
                    disabled={busy}
                    className="btn-ghost taq-btn"
                    onClick={() =>
                      runAction("/ta/work-status/", {
                        request_id: req.id,
                        status: "in_progress",
                      })
                    }
                  >
                    Start helping
                  </button>
                  <button
                    type="button"
                    disabled={busy}
                    className="btn-ghost taq-btn"
                    onClick={() =>
                      runAction(
                        "/ta/work-status/",
                        { request_id: req.id, status: "helped" },
                        { helpedBump: true },
                      )
                    }
                  >
                    Done helping
                  </button>
                  {iAmBackup || (!iAmPrimary && req.alternative_ta === user.display_name) ? (
                    <button
                      type="button"
                      disabled={busy}
                      className="btn-ghost taq-btn"
                      onClick={() => runAction("/ta/take-backup/", { request_id: req.id })}
                    >
                      Take as primary
                    </button>
                  ) : null}
                  {!iAmPrimary &&
                  !iAmBackup &&
                  (!req.assigned_ta || req.assigned_ta === "Unassigned") ? (
                    <button
                      type="button"
                      disabled={busy}
                      className="btn-ghost taq-btn"
                      onClick={() => runAction("/ta/take-backup/", { request_id: req.id })}
                    >
                      Take ownership
                    </button>
                  ) : null}
                </div>

                {(req.help_mode === "message" || !req.help_mode) && (
                  <div className="taq-block">
                    <label className="taq-label" htmlFor="taq-reply">
                      Reply to student
                    </label>
                    <textarea
                      id="taq-reply"
                      className="field-glass taq-field"
                      value={reply}
                      onChange={(event) => setReply(event.target.value)}
                      placeholder="Short reply the student can read"
                    />
                    <button
                      type="button"
                      disabled={busy || reply.trim().length < 3}
                      className="btn-primary taq-btn"
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
                      <p className="taq-meta">
                        <strong>Last reply:</strong> {req.ta_reply}
                      </p>
                    ) : null}
                  </div>
                )}

                <div className="taq-block">
                  <label className="taq-label" htmlFor="taq-notes">
                    Teaching draft (professor curation)
                  </label>
                  <textarea
                    id="taq-notes"
                    className="field-glass taq-field taq-field-lg"
                    value={notes}
                    onChange={(event) => setNotes(event.target.value)}
                  />
                  <label className="taq-label" htmlFor="taq-hint">
                    Student hint
                  </label>
                  <textarea
                    id="taq-hint"
                    className="field-glass taq-field"
                    value={hint}
                    onChange={(event) => setHint(event.target.value)}
                    placeholder="Student hint"
                  />
                  <div className="taq-action-row">
                    <button
                      type="button"
                      disabled={busy}
                      className="btn-primary taq-btn"
                      onClick={() => resolve("resolved")}
                    >
                      Mark resolved
                    </button>
                    <button
                      type="button"
                      disabled={busy}
                      className="btn-ghost taq-btn"
                      onClick={() => resolve("needs_professor")}
                    >
                      Needs professor
                    </button>
                  </div>
                </div>
              </section>

              {(() => {
                const coach = selected.help_coach;
                if (!coach) return null;
                return (
                  <section className="taq-coach">
                    <details className="taq-coach-details">
                      <summary className="taq-coach-summary">
                        Help Coach
                        {coach.group_help_suggested
                          ? ` · ${coach.similar_open_count} similar open`
                          : ""}
                        {coachBusy ? " · working…" : ""}
                      </summary>
                      <div className="taq-coach-body">
                        {coach.similar_open_count > 0 ? (
                          <div className="taq-block">
                            <p className="taq-label">Similar open asks</p>
                            <ul className="taq-plain-list">
                              {coach.similar_open.map((peer) => (
                                <li key={peer.id}>
                                  <button
                                    type="button"
                                    className="taq-link"
                                    onClick={() => {
                                      const peerItem = queue.find(
                                        (item) => item.request.id === peer.id,
                                      );
                                      if (peerItem) selectItem(peerItem);
                                    }}
                                  >
                                    #{peer.id}
                                  </button>
                                  {" · "}
                                  {(peer.text || "").slice(0, 90)}
                                  {(peer.text || "").length > 90 ? "…" : ""}
                                </li>
                              ))}
                            </ul>
                            <button
                              type="button"
                              className="btn-ghost taq-btn"
                              disabled={busy}
                              onClick={() => setMeetingOpen((value) => !value)}
                            >
                              {meetingOpen
                                ? "Hide group meeting form"
                                : "Propose one group meeting"}
                            </button>
                            {meetingOpen ? (
                              <div className="taq-block">
                                <input
                                  className="field-glass taq-input"
                                  value={meetingTitle}
                                  onChange={(event) => setMeetingTitle(event.target.value)}
                                  placeholder="Meeting title"
                                />
                                <div className="taq-split">
                                  <input
                                    className="field-glass taq-input"
                                    value={meetingWhen}
                                    onChange={(event) => setMeetingWhen(event.target.value)}
                                    placeholder="When · Thu 4:00–4:30 PM"
                                  />
                                  <input
                                    className="field-glass taq-input"
                                    value={meetingPlace}
                                    onChange={(event) => setMeetingPlace(event.target.value)}
                                    placeholder="Where / Zoom link"
                                  />
                                </div>
                                <button
                                  type="button"
                                  className="btn-primary taq-btn"
                                  disabled={busy}
                                  onClick={proposeGroupMeeting}
                                >
                                  Schedule shared meeting
                                </button>
                              </div>
                            ) : null}
                          </div>
                        ) : null}

                        {coach.similar_kb?.length ? (
                          <div className="taq-block">
                            <p className="taq-label">Approved KB neighbors</p>
                            <ul className="taq-plain-list">
                              {coach.similar_kb.map((hit) => (
                                <li key={`${hit.id}-${hit.question_text}`}>
                                  #{hit.id}
                                  {hit.similarity != null
                                    ? ` (${Math.round(Number(hit.similarity) * 100)}%)`
                                    : ""}
                                  {" — "}
                                  {(hit.question_text || "").slice(0, 110)}
                                </li>
                              ))}
                            </ul>
                          </div>
                        ) : null}

                        {socraticSteps.length ? (
                          <div className="taq-block">
                            <p className="taq-label">Socratic steps</p>
                            <ol className="taq-steps">
                              {socraticSteps.map((step) => (
                                <li key={step}>{step}</li>
                              ))}
                            </ol>
                          </div>
                        ) : null}

                        <div className="taq-action-row">
                          <button
                            type="button"
                            disabled={busy || coachBusy}
                            className="btn-ghost taq-btn"
                            onClick={() => runHelpCoach("draft_reply")}
                          >
                            {coachBusy ? "Working…" : "Draft student reply"}
                          </button>
                          <button
                            type="button"
                            disabled={busy || coachBusy}
                            className="btn-ghost taq-btn"
                            onClick={() => runHelpCoach("socratic")}
                          >
                            Socratic steps
                          </button>
                          <button
                            type="button"
                            disabled={busy || coachBusy}
                            className="btn-ghost taq-btn"
                            onClick={() => runHelpCoach("refresh_teaching")}
                          >
                            Refresh teaching script
                          </button>
                          <button
                            type="button"
                            disabled={busy || coachBusy || reply.trim().length < 3}
                            className="btn-ghost taq-btn"
                            onClick={() => runHelpCoach("rewrite_reply")}
                          >
                            Rewrite reply
                          </button>
                        </div>
                      </div>
                    </details>
                  </section>
                );
              })()}

              <section className="taq-gold">
                <details className="taq-coach-details">
                  <summary className="taq-coach-summary">Gold label</summary>
                  <div className="taq-coach-body taq-action-row">
                    <select
                      className="field-glass taq-input"
                      value={goldCategory}
                      onChange={(event) => setGoldCategory(event.target.value)}
                    >
                      {[
                        "conceptual_question",
                        "exam_logistics",
                        "retake_request",
                        "accessibility_accommodation",
                        "grading_dispute",
                        "emotional_stress",
                        "project_submission",
                        "office_hours_access",
                        "academic_integrity",
                        "uncategorized",
                      ].map((value) => (
                        <option key={value} value={value}>
                          {value.replaceAll("_", " ")}
                        </option>
                      ))}
                    </select>
                    <select
                      className="field-glass taq-input"
                      value={goldHintUseful}
                      onChange={(event) => setGoldHintUseful(event.target.value)}
                    >
                      <option value="1">Hint was useful</option>
                      <option value="0">Hint was not useful</option>
                    </select>
                    <button
                      type="button"
                      disabled={goldBusy}
                      className="btn-ghost taq-btn"
                      onClick={async () => {
                        setGoldBusy(true);
                        setError("");
                        try {
                          await api("/analytics/gold-labels", {
                            method: "POST",
                            token,
                            body: {
                              text: req.text,
                              gold_category: goldCategory,
                              gold_assigned_ta: req.assigned_ta || user.display_name,
                              gold_hint_useful: Number(goldHintUseful),
                              course_id: activeCourse.id,
                              course_code: activeCourse.code,
                              department: activeCourse.code.split(" ")[0],
                              labeled_by: user.email,
                              notes: `request #${req.id}`,
                            },
                          });
                          setToast(`Gold label saved for #${req.id}`);
                        } catch (err) {
                          setError(err.message);
                        } finally {
                          setGoldBusy(false);
                        }
                      }}
                    >
                      {goldBusy ? "Saving…" : "Save gold label"}
                    </button>
                  </div>
                </details>
              </section>
            </>
          ) : (
            <section className="taq-ask">
              <h2 className="taq-ask-title">Selected ask</h2>
              <p className="taq-empty">Select a row in the queue.</p>
            </section>
          )}
        </aside>
      </div>
    </div>
  );
}
