import { useCallback, useEffect, useState } from "react";
import { Navigate } from "react-router";
import { api } from "../api/client.js";
import { pageItems, pageMeta } from "../api/page.js";
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

  if (!activeCourse) return <Navigate to="/courses" replace />;
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
  const inProgressCount = queue.filter(
    (item) => item.request.work_status === "in_progress",
  ).length;

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
      `Group review: ${item.request.oracle_category || item.request.category || "topic"}`,
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
      `Group review: ${req.oracle_category || req.category || "topic"}`
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
  const tags = req?.oracle_tags || [];
  const work = workPill(req?.work_status);
  const iAmPrimary = req?.assigned_ta === user.display_name;
  const iAmBackup = req?.alternative_ta === user.display_name;
  const iClaimed =
    req?.claimed_by_user_id === user.id || req?.claimed_by === user.display_name;

  return (
    <div className="fade-up">
      <h1 className="bh-page-title">TA Dashboard</h1>
      <p className="bh-page-subtitle">
        Claim asks, help with Help Coach, reply async, then send drafts for
        professor curation · {activeCourse.code} — {activeCourse.title}
      </p>

      <div className="bh-stats">
        <article className="bh-stat-card">
          <div className="bh-stat-head">Open Queue {ICONS.queue}</div>
          <p className="bh-stat-value">{queue.length}</p>
          <p className="bh-stat-note">Visible with current filter</p>
        </article>
        <article className="bh-stat-card">
          <div className="bh-stat-head">Helping now {ICONS.flame}</div>
          <p className="bh-stat-value">{inProgressCount}</p>
          <p className="bh-stat-note">In-progress in this filter</p>
        </article>
        <article className="bh-stat-card">
          <div className="bh-stat-head">Urgent {ICONS.flame}</div>
          <p className="bh-stat-value">{urgentCount}</p>
          <p className="bh-stat-note">High-urgency asks to take first</p>
        </article>
        <article className="bh-stat-card">
          <div className="bh-stat-head">Avg Wait {ICONS.clock}</div>
          <p className="bh-stat-value">{avgWait === null ? "—" : `${avgWait}m`}</p>
          <p className="bh-stat-note">Matcher wait estimate</p>
        </article>
        <article className="bh-stat-card">
          <div className="bh-stat-head">Helped {ICONS.check}</div>
          <p className="bh-stat-value">{helpedCount}</p>
          <p className="bh-stat-note">Done helping this session</p>
        </article>
        <article className="bh-stat-card">
          <div className="bh-stat-head">To curation {ICONS.check}</div>
          <p className="bh-stat-value">{resolvedCount}</p>
          <p className="bh-stat-note">Sent to professor review</p>
        </article>
      </div>

      {loadInfo ? (
        <section className="bh-card mb-5">
          <div className="bh-card-title">
            <h2>TA load (you + partner)</h2>
          </div>
          <p className="bh-card-note">
            Dual-TA Matcher depth for {activeCourse.code}
            {loadInfo.ta_count ? ` · ${loadInfo.ta_count} TAs` : ""}.
          </p>
          <div className="mt-3 flex flex-wrap gap-2">
            {(loadInfo.tas || []).map((ta) => (
              <span
                key={ta.name}
                className={`bh-pill ${
                  ta.name === user.display_name ? "bh-pill-green" : "bh-pill-gray"
                }`}
              >
                {ta.name}
                {ta.name === user.display_name ? " (you)" : ""} · depth{" "}
                {ta.queue_depth ?? "—"}
                {Array.isArray(ta.expertise_tags) && ta.expertise_tags.length
                  ? ` · ${ta.expertise_tags.slice(0, 2).join(", ")}`
                  : ""}
              </span>
            ))}
          </div>
        </section>
      ) : null}

      <section id="queue" className="bh-card scroll-mt-6">
        <div className="bh-card-title">
          <h2>Live Queue</h2>
          <span className="bh-pill bh-pill-green live-pulse">live</span>
        </div>
        <div className="mt-3 flex flex-wrap gap-2">
          {[
            ["desk", "My desk (assigned, backup, open)"],
            ["mine", "Assigned / claimed by me"],
            ["backup", "I'm backup"],
            ["in_progress", "I'm helping now"],
            ["unassigned", "Unassigned"],
            ["all", "All open asks"],
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
        {error ? <p className="mt-2 text-sm text-red-700">{error}</p> : null}
        {toast ? <p className="mt-2 text-sm text-emerald-700">{toast}</p> : null}

        {queue.length === 0 ? (
          <p className="bh-card-note mt-4">No open requests for this filter.</p>
        ) : (
          <table className="bh-table">
            <thead>
              <tr>
                <th>#</th>
                <th>Question</th>
                <th>From</th>
                <th>Status</th>
                <th>Help</th>
                <th>Category</th>
                <th>Similar</th>
                <th>Urgency</th>
                <th>Primary</th>
                <th>Backup</th>
              </tr>
            </thead>
            <tbody>
              {queue.map((item) => {
                const request = item.request;
                const urgency = (request.urgency || "n/a").toLowerCase();
                const helpMode = request.help_mode || "message";
                const status = workPill(request.work_status);
                const similarN =
                  item.similar_open_count || item.help_coach?.similar_open_count || 0;
                return (
                  <tr
                    key={request.id}
                    className={`bh-row-click${selectedId === request.id ? " bh-row-active" : ""}`}
                    onClick={() => selectItem(item)}
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
                      <span className={`bh-pill ${status.className}`}>{status.label}</span>
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
                      {similarN > 0 ? (
                        <span
                          className={`bh-pill ${
                            similarN >= 2 ? "bh-pill-amber" : "bh-pill-blue"
                          }`}
                          title="Similar open asks — consider group help"
                        >
                          {similarN} similar
                        </span>
                      ) : (
                        <span className="text-aui-deep/45">—</span>
                      )}
                    </td>
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
                    <td>{request.assigned_ta || "Unassigned"}</td>
                    <td>{request.alternative_ta || "—"}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
        {queuePage.has_more ? (
          <p className="mt-2 text-xs text-aui-deep/70">
            Showing {queue.length} of {queuePage.total}. Refine the desk filter
            or raise the page size — this is a paged queue.
          </p>
        ) : null}
      </section>

      {selected && req ? (
        <section className="bh-card">
          <div className="bh-card-title">
            <h2>Ask · #{req.id}</h2>
            <span className={`bh-pill ${work.className}`}>{work.label}</span>
          </div>
          <p className="bh-card-note">{req.text}</p>

          <div className="mt-3 rounded-xl border border-aui-forest/20 bg-[#f3faf5] p-3 text-xs text-aui-deep">
            <p className="font-semibold text-aui-ink">Ask Triage</p>
            <p className="mt-0.5 text-[11px] text-aui-deep/60">
              Analyzer → Matcher → Synthesizer for this ask (local models)
            </p>
            <ul className="mt-2 space-y-1">
              <li>
                <strong>Category:</strong> {req.oracle_category || req.category || "n/a"}
                {" · "}
                <strong>Difficulty:</strong> {req.oracle_difficulty || "n/a"}
                {" · "}
                <strong>Est.:</strong>{" "}
                {req.oracle_estimated_minutes != null
                  ? `${req.oracle_estimated_minutes} min`
                  : "n/a"}
              </li>
              {selected.learning_style &&
              selected.learning_style !== "unknown" &&
              req.learning_style &&
              req.learning_style !== "unknown" ? (
                <li>
                  <strong>Learning style:</strong>{" "}
                  {selected.learning_style || req.learning_style}
                  {" · "}
                  <strong>Urgency:</strong> {req.urgency || "n/a"}
                </li>
              ) : (
                <li>
                  <strong>Urgency:</strong> {req.urgency || "n/a"}
                </li>
              )}
              <li>
                <strong>Tags:</strong> {tags.length ? tags.join(", ") : "none"}
              </li>
              <li>
                <strong>Sensitive:</strong> {req.sensitive ? "yes — keep private" : "no"}
              </li>
              {req.oracle?.matcher?.rationale ? (
                <li>
                  <strong>Matcher:</strong> {req.oracle.matcher.rationale}
                </li>
              ) : (
                <li>
                  <strong>Matcher:</strong> {req.assigned_ta || "Unassigned"}
                  {req.alternative_ta ? ` (backup ${req.alternative_ta})` : ""}
                </li>
              )}
              {(selected.help_coach?.kb_insight ||
                req.oracle?.synthesizer?.kb_insight) ? (
                <li>
                  <strong>KB insight:</strong>{" "}
                  {selected.help_coach?.kb_insight ||
                    req.oracle?.synthesizer?.kb_insight}
                </li>
              ) : null}
            </ul>
          </div>

          {(() => {
            const coach = selected.help_coach;
            if (!coach) return null;
            return (
              <div className="mt-3 rounded-xl border border-[#c5d9cc] bg-white p-3 text-xs text-aui-deep">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div>
                    <p className="font-semibold text-aui-ink">Help Coach</p>
                    <p className="mt-0.5 text-[11px] text-aui-deep/65">
                      Live co-pilot while you help ·{" "}
                      {coach.coach_summary || "ready"}
                    </p>
                  </div>
                  {coach.group_help_suggested ? (
                    <span className="bh-pill bh-pill-amber">
                      Group help · {coach.similar_open_count} similar open
                    </span>
                  ) : null}
                </div>

                {coach.similar_open_count > 0 ? (
                  <div className="mt-3">
                    <p className="font-semibold text-aui-ink">Similar open asks</p>
                    <ul className="mt-1 space-y-1">
                      {coach.similar_open.map((peer) => (
                        <li key={peer.id} className="rounded-lg bg-[#f3faf5] px-2 py-1.5">
                          <button
                            type="button"
                            className="text-left text-aui-forest underline-offset-2 hover:underline"
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
                          <span className="text-aui-deep/80">
                            {(peer.text || "").slice(0, 90)}
                            {(peer.text || "").length > 90 ? "…" : ""}
                          </span>
                        </li>
                      ))}
                    </ul>
                    <button
                      type="button"
                      className="btn-ghost mt-2 px-3 py-1.5 text-xs"
                      disabled={busy}
                      onClick={() => setMeetingOpen((value) => !value)}
                    >
                      {meetingOpen ? "Hide group meeting form" : "Propose one group meeting"}
                    </button>
                    {meetingOpen ? (
                      <div className="mt-2 rounded-lg border border-[#d7e0d9] bg-white p-2.5">
                        <p className="text-[11px] text-aui-deep/70">
                          Schedules the same time/place on status for this ask and{" "}
                          {coach.similar_open_count} similar open ask
                          {coach.similar_open_count === 1 ? "" : "s"}.
                        </p>
                        <input
                          className="field-glass mt-2 w-full px-2.5 py-1.5 text-xs"
                          value={meetingTitle}
                          onChange={(event) => setMeetingTitle(event.target.value)}
                          placeholder="Meeting title"
                        />
                        <div className="mt-1.5 grid gap-1.5 sm:grid-cols-2">
                          <input
                            className="field-glass w-full px-2.5 py-1.5 text-xs"
                            value={meetingWhen}
                            onChange={(event) => setMeetingWhen(event.target.value)}
                            placeholder="When · Thu 4:00–4:30 PM"
                          />
                          <input
                            className="field-glass w-full px-2.5 py-1.5 text-xs"
                            value={meetingPlace}
                            onChange={(event) => setMeetingPlace(event.target.value)}
                            placeholder="Where / Zoom link"
                          />
                        </div>
                        <button
                          type="button"
                          className="btn-primary mt-2 px-3 py-1.5 text-xs"
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
                  <div className="mt-3">
                    <p className="font-semibold text-aui-ink">Approved KB neighbors</p>
                    <ul className="mt-1 space-y-1.5">
                      {coach.similar_kb.map((hit) => (
                        <li
                          key={`${hit.id}-${hit.question_text}`}
                          className="rounded-lg border border-[#e4ece6] px-2 py-1.5"
                        >
                          <p className="font-medium text-aui-ink">
                            #{hit.id}{" "}
                            {hit.similarity != null
                              ? `(${Math.round(Number(hit.similarity) * 100)}%)`
                              : ""}
                          </p>
                          <p className="text-aui-deep/80">
                            {(hit.question_text || "").slice(0, 110)}
                          </p>
                          {hit.answer_preview ? (
                            <p className="mt-1 text-aui-deep/70">
                              {hit.answer_preview.slice(0, 160)}
                              {hit.answer_preview.length > 160 ? "…" : ""}
                            </p>
                          ) : null}
                        </li>
                      ))}
                    </ul>
                  </div>
                ) : null}

                {socraticSteps.length ? (
                  <div className="mt-3">
                    <p className="font-semibold text-aui-ink">Socratic steps</p>
                    <ol className="mt-1 list-decimal space-y-1 pl-4">
                      {socraticSteps.map((step) => (
                        <li key={step}>{step}</li>
                      ))}
                    </ol>
                  </div>
                ) : null}

                <div className="mt-3 flex flex-wrap gap-2">
                  <button
                    type="button"
                    disabled={busy || coachBusy}
                    className="btn-primary px-3 py-1.5 text-xs"
                    onClick={() => runHelpCoach("draft_reply")}
                  >
                    {coachBusy ? "Coaching…" : "Draft student reply"}
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
                    Refresh teaching script
                  </button>
                  <button
                    type="button"
                    disabled={busy || coachBusy || reply.trim().length < 3}
                    className="btn-ghost px-3 py-1.5 text-xs"
                    onClick={() => runHelpCoach("rewrite_reply")}
                  >
                    Rewrite reply
                  </button>
                </div>
              </div>
            );
          })()}

          <div className="mt-2 flex flex-wrap gap-2 text-xs">
            <span className="bh-pill bh-pill-gray">
              {req.anonymous
                ? "Anonymous"
                : req.student_name || req.student_id || "Identified"}
            </span>
            <span
              className={`bh-pill ${
                req.help_mode === "face_to_face"
                  ? "bh-pill-amber"
                  : req.help_mode === "online_meeting"
                    ? "bh-pill-blue"
                    : "bh-pill-gray"
              }`}
            >
              {req.help_mode === "face_to_face"
                ? "Wants face-to-face"
                : req.help_mode === "online_meeting"
                  ? "Wants online meeting"
                  : "Message / async"}
            </span>
            {req.claimed_by ? (
              <span className="bh-pill bh-pill-blue">Claimed by {req.claimed_by}</span>
            ) : null}
          </div>

          {req.recommended_action ? (
            <p className="mt-2 rounded-lg bg-amber-50 px-3 py-2 text-xs text-amber-950">
              <strong>Suggested action:</strong> {req.recommended_action}
            </p>
          ) : null}
          {req.code_snippet ? (
            <pre className="soft-stat mt-3 overflow-x-auto font-mono text-xs">
              {req.code_snippet}
            </pre>
          ) : null}

          <div className="mt-4 flex flex-wrap gap-2">
            <button
              type="button"
              disabled={busy || (req.claimed_by && !iClaimed && req.work_status !== "open")}
              className="btn-primary px-4 py-2 text-sm"
              onClick={() => runAction("/ta/claim/", { request_id: req.id })}
            >
              Claim
            </button>
            <button
              type="button"
              disabled={busy}
              className="btn-ghost px-4 py-2 text-sm"
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
              className="btn-ghost px-4 py-2 text-sm"
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
                className="btn-ghost px-4 py-2 text-sm"
                onClick={() => runAction("/ta/take-backup/", { request_id: req.id })}
              >
                Take as primary (backup handoff)
              </button>
            ) : null}
            {!iAmPrimary && !iAmBackup && (!req.assigned_ta || req.assigned_ta === "Unassigned") ? (
              <button
                type="button"
                disabled={busy}
                className="btn-ghost px-4 py-2 text-sm"
                onClick={() => runAction("/ta/take-backup/", { request_id: req.id })}
              >
                Take ownership
              </button>
            ) : null}
          </div>

          {(req.help_mode === "message" || !req.help_mode) && (
            <div className="mt-4 rounded-xl border border-[#d7e0d9] p-3">
              <p className="text-sm font-semibold text-aui-ink">Reply to student</p>
              <p className="mt-1 text-xs text-aui-deep/70">
                Publishes on their request status immediately (does not wait for
                professor KB approval). Use Help Coach to draft, then edit.
              </p>
              <textarea
                className="field-glass mt-2 min-h-24 w-full px-3 py-2.5 text-sm"
                value={reply}
                onChange={(event) => setReply(event.target.value)}
                placeholder="Write a short reply the student can read…"
              />
              <button
                type="button"
                disabled={busy || reply.trim().length < 3}
                className="btn-primary mt-2 px-4 py-2 text-sm"
                onClick={() =>
                  runAction("/ta/reply/", {
                    request_id: req.id,
                    reply: reply.trim(),
                    update_student_hint: true,
                  })
                }
              >
                Send reply to student
              </button>
              {req.ta_reply ? (
                <p className="mt-2 text-xs text-aui-deep">
                  <strong>Last reply:</strong> {req.ta_reply}
                </p>
              ) : null}
            </div>
          )}

          <label className="mt-4 block text-xs font-semibold uppercase tracking-wide text-aui-deep/60">
            Teaching draft (for professor curation)
            <textarea
              className="field-glass mt-1.5 min-h-40 w-full px-3 py-2.5 text-sm"
              value={notes}
              onChange={(event) => setNotes(event.target.value)}
            />
          </label>
          <label className="mt-3 block text-xs font-semibold uppercase tracking-wide text-aui-deep/60">
            Student hint (KB draft)
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
              disabled={busy}
              className="btn-primary px-4 py-2 text-sm"
              onClick={() => resolve("resolved")}
            >
              Done + send to professor curation
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

          <div className="mt-5 rounded-xl border border-[#d7e0d9] p-3">
            <p className="text-sm font-semibold text-aui-ink">Gold label this ask</p>
            <p className="mt-1 text-xs text-aui-deep/70">
              Staff judgment for evaluation — category + whether the Synthesizer
              hint helped. This does not retrain the live student agent. Protocol:
              one 45-minute TA lab, ≥40 asks, not a satisfaction survey.
            </p>
            <div className="mt-2 flex flex-wrap gap-2">
              <select
                className="field-glass px-3 py-2 text-xs"
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
                className="field-glass px-3 py-2 text-xs"
                value={goldHintUseful}
                onChange={(event) => setGoldHintUseful(event.target.value)}
              >
                <option value="1">Hint was useful</option>
                <option value="0">Hint was not useful</option>
              </select>
              <button
                type="button"
                disabled={goldBusy}
                className="btn-ghost px-3 py-2 text-xs"
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
          </div>
        </section>
      ) : (
        <section className="bh-card">
          <p className="bh-card-note">
            Select a request to claim it, help the student, reply, and prepare a
            teaching draft.
          </p>
        </section>
      )}
    </div>
  );
}
