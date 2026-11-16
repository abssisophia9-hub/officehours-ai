import { useCallback, useEffect, useRef, useState } from "react";
import { Navigate } from "react-router";
import {
  Bold,
  Check,
  ChevronLeft,
  ChevronRight,
  Clock,
  Code2,
  Italic,
  PanelLeft,
  PanelRight,
  Send,
  Sparkles,
  Undo2,
} from "lucide-react";
import { api } from "../api/client.js";
import { pageItems, pageMeta } from "../api/page.js";
import { useAuth } from "../auth/AuthContext.jsx";

function fmtWait(minutes) {
  if (minutes == null || Number.isNaN(Number(minutes))) return "—";
  const min = Math.max(0, Math.round(Number(minutes)));
  if (min < 1) return "<1m";
  if (min < 60) return `${min}m`;
  return `${Math.floor(min / 60)}h ${min % 60}m`;
}

function fmtTime(value) {
  if (!value) return "";
  const date = value instanceof Date ? value : new Date(value);
  if (Number.isNaN(date.getTime())) return "";
  return date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

function previewLine(text, max = 72) {
  const clean = String(text || "")
    .replace(/\s+/g, " ")
    .trim();
  if (clean.length <= max) return clean;
  return `${clean.slice(0, max - 1)}…`;
}

function workLabel(status) {
  const value = status || "open";
  if (value === "in_progress") return "helping";
  if (value === "claimed") return "claimed";
  if (value === "helped") return "resolved";
  return "open";
}

function workClass(status) {
  const value = workLabel(status);
  return {
    open: "tar-pill tar-pill-open",
    claimed: "tar-pill tar-pill-claimed",
    helping: "tar-pill tar-pill-helping",
    resolved: "tar-pill tar-pill-resolved",
  }[value];
}

function studentLabel(req) {
  if (!req) return "Student";
  if (req.anonymous) return "Anonymous";
  return req.student_name || req.student_id || "Identified";
}

function strategyBullets(coach, notes) {
  const fromApproach = String(coach?.teaching_approach || notes || "")
    .split(/\n+/)
    .map((line) => line.replace(/^[-•*\d.)\s]+/, "").trim())
    .filter(Boolean);
  if (fromApproach.length) return fromApproach.slice(0, 6);
  return [
    "Ask for a concrete drawing or example before naming a textbook case.",
    "Separate the broken invariant from the fixup steps.",
    "Stop once the student can state the next move — do not hand the full solution.",
  ];
}

function socraticPrompt(coach, steps) {
  if (Array.isArray(steps) && steps.length) return steps[0];
  if (Array.isArray(coach?.socratic_steps) && coach.socratic_steps.length) {
    return coach.socratic_steps[0];
  }
  if (coach?.student_hint) return coach.student_hint;
  return "What is the smallest concrete example that fails, and which single property is broken after the change?";
}

function renderThreadText(text) {
  const blocks = [];
  const parts = String(text || "").split(/```([\s\S]*?)```/);
  parts.forEach((part, i) => {
    if (i % 2 === 1) {
      blocks.push(
        <pre key={`pre-${i}`} className="tar-code-block">
          {part.replace(/^\w*\n/, "")}
        </pre>,
      );
      return;
    }
    const lines = part.split("\n");
    lines.forEach((line, li) => {
      const bits = [];
      const re = /(\*\*[^*]+\*\*|\*[^*]+\*|`[^`]+`)/g;
      let last = 0;
      let match;
      while ((match = re.exec(line)) !== null) {
        if (match.index > last) bits.push(line.slice(last, match.index));
        const tok = match[0];
        if (tok.startsWith("**")) {
          bits.push(<strong key={`${i}-${li}-${match.index}`}>{tok.slice(2, -2)}</strong>);
        } else if (tok.startsWith("*")) {
          bits.push(<em key={`${i}-${li}-${match.index}`}>{tok.slice(1, -1)}</em>);
        } else {
          bits.push(<code key={`${i}-${li}-${match.index}`}>{tok.slice(1, -1)}</code>);
        }
        last = match.index + tok.length;
      }
      if (last < line.length) bits.push(line.slice(last));
      blocks.push(
        <p key={`p-${i}-${li}`} className={li > 0 || i > 0 ? "mt-2" : undefined}>
          {bits.length ? bits : "\u00A0"}
        </p>,
      );
    });
  });
  return blocks;
}

function ToolBtn({ children, onClick, title }) {
  return (
    <button type="button" title={title} onClick={onClick} className="tar-tool">
      {children}
    </button>
  );
}

export default function TaWorkspace() {
  const { token, user, activeCourse } = useAuth();
  const [queue, setQueue] = useState([]);
  const [queuePage, setQueuePage] = useState({ has_more: false, total: 0 });
  const [selectedId, setSelectedId] = useState(null);
  const [draft, setDraft] = useState("");
  const [notes, setNotes] = useState("");
  const [hint, setHint] = useState("");
  const [socraticSteps, setSocraticSteps] = useState([]);
  const [coachBusy, setCoachBusy] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [toast, setToast] = useState("");
  const [queueOpen, setQueueOpen] = useState(true);
  const [coachOpen, setCoachOpen] = useState(true);
  const [localThread, setLocalThread] = useState({});
  const composerRef = useRef(null);
  const threadRef = useRef(null);

  const loadQueue = useCallback(async () => {
    try {
      const params = new URLSearchParams({
        course_id: String(activeCourse.id),
        assignment: "all",
        limit: "50",
        offset: "0",
      });
      const data = await api(`/ta/queue/?${params.toString()}`, { token });
      const items = pageItems(data);
      setQueue(items);
      setQueuePage(pageMeta(data));
      setError("");
      return items;
    } catch (err) {
      setError(err.message);
      return null;
    }
  }, [token, activeCourse]);

  useEffect(() => {
    loadQueue();
    const id = setInterval(() => {
      loadQueue();
    }, 8000);
    return () => clearInterval(id);
  }, [loadQueue]);

  useEffect(() => {
    if (!toast) return undefined;
    const id = setTimeout(() => setToast(""), 2400);
    return () => clearTimeout(id);
  }, [toast]);

  useEffect(() => {
    if (!queue.length) {
      if (selectedId != null) setSelectedId(null);
      return;
    }
    if (selectedId != null && queue.some((item) => item.request.id === selectedId)) {
      return;
    }
    const first = queue[0];
    setSelectedId(first.request.id);
    const existing = first.help_coach;
    setNotes(existing?.teaching_approach || first.knowledge_entry?.answer_draft || "");
    setHint(
      existing?.student_hint ||
        first.knowledge_entry?.student_hint ||
        first.request.student_hint ||
        "",
    );
    setSocraticSteps(existing?.socratic_steps || []);
    setDraft("");
    if (existing) return;
    let cancelled = false;
    setCoachBusy(true);
    api(`/ta/coach/?request_id=${first.request.id}`, { token })
      .then((packet) => {
        if (cancelled) return;
        setNotes(packet.teaching_approach || first.knowledge_entry?.answer_draft || "");
        setHint(
          packet.student_hint ||
            first.knowledge_entry?.student_hint ||
            first.request.student_hint ||
            "",
        );
        setSocraticSteps(packet.socratic_steps || []);
        setQueue((prev) =>
          prev.map((row) =>
            row.request.id === first.request.id ? { ...row, help_coach: packet } : row,
          ),
        );
      })
      .catch((err) => {
        if (!cancelled) setError(err.message);
      })
      .finally(() => {
        if (!cancelled) setCoachBusy(false);
      });
    return () => {
      cancelled = true;
    };
  }, [queue, selectedId, token]);

  useEffect(() => {
    setDraft("");
  }, [selectedId]);

  useEffect(() => {
    if (threadRef.current) {
      threadRef.current.scrollTop = threadRef.current.scrollHeight;
    }
  }, [selectedId, localThread, queue]);

  if (!activeCourse) return <Navigate to="/" replace />;
  if (activeCourse.role !== "ta") {
    return (
      <Navigate
        to={activeCourse.role === "professor" ? "/professor" : "/student"}
        replace
      />
    );
  }

  const selected =
    queue.find((item) => item.request.id === selectedId) || queue[0] || null;
  const req = selected?.request || null;
  const activeId = req?.id ?? null;
  const liveCount = queuePage.total || queue.length;
  const coach = selected?.help_coach || null;
  const bullets = strategyBullets(coach, notes);
  const prompt = socraticPrompt(coach, socraticSteps);
  const isHelped = (req?.work_status || "open") === "helped";
  const iClaimed =
    !!req &&
    (req.claimed_by_user_id === user.id || req.claimed_by === user.display_name);
  const isClaimed =
    !!req &&
    (["claimed", "in_progress"].includes(req.work_status || "") || iClaimed);

  const threadMessages = (() => {
    if (!req) return [];
    const base = [
      {
        id: `ask-${req.id}`,
        role: "student",
        author: studentLabel(req),
        at: req.created_at || null,
        text: req.text,
      },
    ];
    if (req.ta_reply) {
      base.push({
        id: `reply-${req.id}`,
        role: "ta",
        author: req.claimed_by || user.display_name,
        at: req.ta_replied_at || null,
        text: req.ta_reply,
      });
    }
    const extras = localThread[req.id] || [];
    const seen = new Set(base.map((m) => m.text));
    for (const msg of extras) {
      if (!seen.has(msg.text)) {
        base.push(msg);
        seen.add(msg.text);
      }
    }
    return base;
  })();

  async function selectItem(item) {
    setSelectedId(item.request.id);
    setError("");
    const existing = item.help_coach;
    setNotes(existing?.teaching_approach || item.knowledge_entry?.answer_draft || "");
    setHint(
      existing?.student_hint ||
        item.knowledge_entry?.student_hint ||
        item.request.student_hint ||
        "",
    );
    setSocraticSteps(existing?.socratic_steps || []);
    // Composer stays empty — never dump coaching into the reply box.
    setDraft("");
    if (existing) return;
    setCoachBusy(true);
    try {
      const packet = await api(`/ta/coach/?request_id=${item.request.id}`, { token });
      setNotes(packet.teaching_approach || item.knowledge_entry?.answer_draft || "");
      setHint(
        packet.student_hint ||
          item.knowledge_entry?.student_hint ||
          item.request.student_hint ||
          "",
      );
      setSocraticSteps(packet.socratic_steps || []);
      setQueue((prev) =>
        prev.map((row) =>
          row.request.id === item.request.id ? { ...row, help_coach: packet } : row,
        ),
      );
    } catch (err) {
      setError(err.message);
    } finally {
      setCoachBusy(false);
    }
  }

  function patchRequest(nextRequest) {
    setQueue((prev) =>
      prev.map((item) =>
        item.request.id === nextRequest.id
          ? { ...item, request: nextRequest }
          : item,
      ),
    );
  }

  async function claimAsk() {
    if (!req || isHelped || busy) return;
    setBusy(true);
    setError("");
    try {
      const result = await api("/ta/claim/", {
        method: "POST",
        token,
        body: { request_id: req.id },
      });
      if (result.request) patchRequest(result.request);
      setToast(result.message || `Claimed ask #${req.id}`);
      await loadQueue();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  async function releaseAsk() {
    if (!req || isHelped || busy) return;
    setBusy(true);
    setError("");
    try {
      const result = await api("/ta/work-status/", {
        method: "POST",
        token,
        body: { request_id: req.id, status: "open" },
      });
      if (result.request) patchRequest(result.request);
      setToast(result.message || `Released ask #${req.id}`);
      await loadQueue();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  function teachingNotesForResolve() {
    const fromNotes = notes.trim();
    if (fromNotes.length >= 3) return fromNotes;
    const fromCoach = String(coach?.teaching_approach || "").trim();
    if (fromCoach.length >= 3) return fromCoach;
    const joined = bullets.join(" ").trim();
    if (joined.length >= 3) return joined.slice(0, 8000);
    return `Resolved ask #${req.id} — ${activeCourse.code}`;
  }

  async function advanceAfterResolve(fromId, items) {
    const list = items || queue;
    const nextOpen = list.find(
      (item) => item.request.id !== fromId && (item.request.work_status || "open") === "open",
    );
    const nextAny = list.find(
      (item) =>
        item.request.id !== fromId && (item.request.work_status || "open") !== "helped",
    );
    const next = nextOpen || nextAny;
    if (next) {
      await selectItem(next);
    } else {
      setSelectedId(null);
      setDraft("");
      setNotes("");
      setHint("");
      setSocraticSteps([]);
    }
  }

  async function resolveAsk({ withReply = false } = {}) {
    if (!req || isHelped || busy) return;
    const text = draft.trim();
    if (withReply && text && text.length < 3) {
      setError("Reply needs at least 3 characters, or clear the box and mark resolved.");
      return;
    }
    setBusy(true);
    setError("");
    const fromId = req.id;
    try {
      if (withReply && text) {
        const replied = await api("/ta/reply/", {
          method: "POST",
          token,
          body: {
            request_id: fromId,
            reply: text,
            update_student_hint: true,
          },
        });
        if (replied.request) patchRequest(replied.request);
        setLocalThread((prev) => ({
          ...prev,
          [fromId]: [
            ...(prev[fromId] || []),
            {
              id: `local-${fromId}-${Date.now()}`,
              role: "ta",
              author: user.display_name,
              at: new Date().toISOString(),
              text,
            },
          ],
        }));
      }

      const result = await api("/ta/resolve/", {
        method: "POST",
        token,
        body: {
          request_id: fromId,
          teaching_notes: teachingNotesForResolve(),
          student_hint: hint || text || null,
          resolution_status: "resolved",
        },
      });
      setToast(
        withReply && text
          ? `Resolved #${fromId} · advanced`
          : result.message || `Resolved #${fromId}`,
      );
      setDraft("");
      const items = await loadQueue();
      await advanceAfterResolve(fromId, items || []);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  async function sendKeepOpen() {
    if (!req || isHelped || busy) return;
    const text = draft.trim();
    if (text.length < 3) {
      setError("Write at least 3 characters before sending a reply.");
      return;
    }
    setBusy(true);
    setError("");
    try {
      const result = await api("/ta/reply/", {
        method: "POST",
        token,
        body: {
          request_id: req.id,
          reply: text,
          update_student_hint: true,
        },
      });
      if (result.request) patchRequest(result.request);
      setLocalThread((prev) => ({
        ...prev,
        [req.id]: [
          ...(prev[req.id] || []),
          {
            id: `local-${req.id}-${Date.now()}`,
            role: "ta",
            author: user.display_name,
            at: new Date().toISOString(),
            text,
          },
        ],
      }));
      setDraft("");
      setToast("Reply sent · ask kept open");
      await loadQueue();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  function insertCoach() {
    if (!req || isHelped) return;
    setDraft((current) => (current.trim() ? `${current.trim()}\n\n${prompt}` : prompt));
    composerRef.current?.focus();
    setToast("Inserted Socratic prompt into reply");
  }

  function wrapSelection(before, after = before) {
    const el = composerRef.current;
    if (!el) {
      setDraft((d) => `${d}${before}${after}`);
      return;
    }
    const start = el.selectionStart ?? draft.length;
    const end = el.selectionEnd ?? draft.length;
    const selectedText = draft.slice(start, end) || "text";
    const next = draft.slice(0, start) + before + selectedText + after + draft.slice(end);
    setDraft(next);
    requestAnimationFrame(() => {
      el.focus();
      el.setSelectionRange(start + before.length, start + before.length + selectedText.length);
    });
  }

  function onComposerKeyDown(event) {
    if ((event.metaKey || event.ctrlKey) && event.key === "Enter") {
      event.preventDefault();
      resolveAsk({ withReply: true });
    }
  }

  return (
    <div className="tar-desk">
      {/* Zone 2 · Mini-queue */}
      <section
        className={`tar-queue ${queueOpen ? "tar-queue-open" : "tar-queue-collapsed"}`}
        aria-label="Mini queue"
      >
        <div className="tar-pane-head">
          {queueOpen ? (
            <>
              <div className="px-1">
                <div className="tar-pane-title">Queue</div>
                <div className="tar-pane-sub font-mono">
                  {liveCount} open · {activeCourse.code}
                </div>
              </div>
              <button
                type="button"
                className="tar-icon-btn"
                onClick={() => setQueueOpen(false)}
                title="Collapse queue"
                aria-label="Collapse queue"
              >
                <ChevronLeft size={16} />
              </button>
            </>
          ) : (
            <button
              type="button"
              className="tar-icon-btn mx-auto"
              onClick={() => setQueueOpen(true)}
              title="Expand queue"
              aria-label="Expand queue"
            >
              <ChevronRight size={16} />
            </button>
          )}
        </div>
        {queueOpen ? (
          <div className="tar-scroll flex-1">
            {queue.length === 0 ? (
              <p className="tar-empty">No open asks.</p>
            ) : (
              queue.map((item) => {
                const request = item.request;
                const selectedRow = request.id === activeId;
                const mine =
                  request.claimed_by_user_id === user.id ||
                  request.claimed_by === user.display_name;
                const status = request.work_status || "open";
                return (
                  <button
                    key={request.id}
                    type="button"
                    onClick={() => selectItem(item)}
                    className={`tar-queue-row ${selectedRow ? "tar-queue-row-on" : ""}`}
                  >
                    <div className="flex items-center justify-between gap-2">
                      <span className="font-mono text-[11px] text-[var(--tar-mute)]">
                        #{request.id}
                      </span>
                      <span className="inline-flex items-center gap-1.5">
                        <span
                          className={`tar-dot ${
                            status === "open" && !mine ? "tar-dot-open" : "tar-dot-claimed"
                          }`}
                          title={
                            status === "open" && !mine
                              ? "Unclaimed"
                              : mine
                                ? "Claimed by You"
                                : `Claimed by ${request.claimed_by || "TA"}`
                          }
                        />
                        <span className={workClass(status)}>{workLabel(status)}</span>
                      </span>
                    </div>
                    <div className="mt-1 truncate text-[13px] font-medium text-[var(--tar-ink)]">
                      {studentLabel(request)}
                    </div>
                    <div className="tar-queue-preview">{previewLine(request.text)}</div>
                    <div className="mt-1.5 flex items-center gap-2 font-mono text-[11px] text-[var(--tar-mute)]">
                      <span className="inline-flex items-center gap-1">
                        <Clock size={11} />
                        {fmtWait(request.estimated_wait_minutes)}
                      </span>
                      <span>·</span>
                      <span>
                        {status === "open" && !mine
                          ? "Unclaimed"
                          : mine
                            ? "Claimed by You"
                            : request.claimed_by || "Claimed"}
                      </span>
                    </div>
                  </button>
                );
              })
            )}
          </div>
        ) : null}
      </section>

      {/* Zone 3 · Center workspace */}
      <main className="tar-center">
        {req ? (
          <>
            <header className="tar-center-head">
              <div className="min-w-0">
                <div className="flex flex-wrap items-center gap-2">
                  <h1 className="tar-ask-title">
                    Ask <span className="font-mono text-[18px]">#{req.id}</span>
                  </h1>
                  <span className={workClass(req.work_status)}>{workLabel(req.work_status)}</span>
                  {(req.triage_category || req.category) && (
                    <span className="tar-topic">{req.triage_category || req.category}</span>
                  )}
                </div>
                <div className="mt-0.5 text-[12px] text-[var(--tar-mute)]">
                  {studentLabel(req)}
                  {req.student_id && !req.anonymous ? (
                    <>
                      {" "}
                      · <span className="font-mono">{req.student_id}</span>
                    </>
                  ) : null}{" "}
                  · waited{" "}
                  <span className="font-mono">{fmtWait(req.estimated_wait_minutes)}</span>
                  {req.claimed_by ? (
                    <>
                      {" "}
                      · claimed by <span className="text-[var(--tar-ink)]">{req.claimed_by}</span>
                    </>
                  ) : null}
                </div>
              </div>

              <div className="flex shrink-0 items-center gap-2">
                {!queueOpen ? (
                  <button
                    type="button"
                    className="tar-ghost-icon"
                    onClick={() => setQueueOpen(true)}
                    title="Show queue"
                  >
                    <PanelLeft size={15} />
                  </button>
                ) : null}
                {!coachOpen ? (
                  <button
                    type="button"
                    className="tar-ghost-icon"
                    onClick={() => setCoachOpen(true)}
                    title="Show Help Coach"
                  >
                    <PanelRight size={15} />
                  </button>
                ) : null}

                {isHelped ? (
                  <span className="px-2 text-[12px] text-[var(--tar-mute)]">Resolved</span>
                ) : !isClaimed ? (
                  <button
                    type="button"
                    disabled={busy}
                    onClick={claimAsk}
                    className="tar-btn-primary"
                  >
                    Claim Ask
                  </button>
                ) : (
                  <>
                    <button
                      type="button"
                      disabled={busy}
                      onClick={() => resolveAsk({ withReply: false })}
                      className="tar-btn-primary"
                    >
                      <Check size={14} />
                      Mark Resolved &amp; Next
                    </button>
                    <button
                      type="button"
                      disabled={busy}
                      onClick={releaseAsk}
                      className="tar-btn-subtle"
                      title="Release claim"
                    >
                      <Undo2 size={14} />
                      Release
                    </button>
                  </>
                )}
              </div>
            </header>

            <div ref={threadRef} className="tar-thread tar-scroll">
              <div className="tar-thread-inner">
                {threadMessages.map((message) => (
                  <div
                    key={message.id}
                    className={`tar-msg ${message.role === "ta" ? "tar-msg-ta" : "tar-msg-student"}`}
                  >
                    <div className="mb-1.5 flex items-baseline justify-between gap-2">
                      <div className="text-[12.5px] font-semibold text-[var(--tar-ink)]">
                        {message.author}
                        <span className="ml-1.5 font-normal text-[var(--tar-mute)]">
                          {message.role === "ta" ? "TA" : "Student"}
                        </span>
                      </div>
                      {message.at ? (
                        <time className="font-mono text-[11px] text-[var(--tar-mute)]">
                          {fmtTime(message.at)}
                        </time>
                      ) : null}
                    </div>
                    <div className="tar-prose">{renderThreadText(message.text)}</div>
                  </div>
                ))}
              </div>
            </div>

            <div className="tar-composer">
              <div className="tar-composer-inner">
                <div className="mb-2 flex items-center gap-0.5">
                  <ToolBtn title="Bold" onClick={() => wrapSelection("**")}>
                    <Bold size={14} />
                  </ToolBtn>
                  <ToolBtn title="Italic" onClick={() => wrapSelection("*")}>
                    <Italic size={14} />
                  </ToolBtn>
                  <ToolBtn title="Inline code" onClick={() => wrapSelection("`")}>
                    <Code2 size={14} />
                  </ToolBtn>
                  <ToolBtn
                    title="Code block"
                    onClick={() => wrapSelection("```\n", "\n```")}
                  >
                    <span className="px-0.5 font-mono text-[10px] font-semibold">{"{ }"}</span>
                  </ToolBtn>
                  <span className="ml-auto font-mono text-[11px] text-[var(--tar-mute)]">
                    ⌘/Ctrl+Enter · Send &amp; Resolve
                  </span>
                </div>

                <textarea
                  ref={composerRef}
                  value={draft}
                  onChange={(event) => setDraft(event.target.value)}
                  onKeyDown={onComposerKeyDown}
                  disabled={isHelped || busy}
                  placeholder={
                    isHelped
                      ? "Ask resolved — select another from the queue"
                      : "Write a reply to the student…"
                  }
                  rows={4}
                  className="tar-textarea"
                />

                <div className="mt-2.5 flex items-center justify-end gap-2">
                  <button
                    type="button"
                    disabled={isHelped || busy || !draft.trim()}
                    onClick={sendKeepOpen}
                    className="tar-btn-secondary"
                  >
                    Send Reply · Keep Open
                  </button>
                  <button
                    type="button"
                    disabled={isHelped || busy}
                    onClick={() => resolveAsk({ withReply: true })}
                    className="tar-btn-primary"
                  >
                    <Send size={14} />
                    Send &amp; Resolve
                  </button>
                </div>
              </div>
            </div>
          </>
        ) : (
          <div className="flex flex-1 items-center justify-center text-[var(--tar-mute)]">
            No asks in queue.
          </div>
        )}
      </main>

      {/* Zone 4 · Help Coach */}
      <aside
        className={`tar-coach ${coachOpen ? "tar-coach-open" : "tar-coach-collapsed"}`}
        aria-label="Help Coach"
      >
        <div className="tar-pane-head">
          {coachOpen ? (
            <>
              <button
                type="button"
                className="tar-icon-btn"
                onClick={() => setCoachOpen(false)}
                title="Collapse Help Coach"
                aria-label="Collapse Help Coach"
              >
                <ChevronRight size={16} />
              </button>
              <div className="flex-1 px-1">
                <div className="tar-pane-title flex items-center gap-1.5">
                  <Sparkles size={13} className="text-[var(--tar-forest-mid)]" />
                  Help Coach
                </div>
                <div className="tar-pane-sub">Private · not sent to student</div>
              </div>
            </>
          ) : (
            <button
              type="button"
              className="tar-icon-btn mx-auto"
              onClick={() => setCoachOpen(true)}
              title="Expand Help Coach"
              aria-label="Expand Help Coach"
            >
              <ChevronLeft size={16} />
            </button>
          )}
        </div>

        {coachOpen ? (
          <div className="tar-scroll flex-1 space-y-4 px-3 py-3">
            {!req ? (
              <p className="tar-empty">Select an ask to load coaching.</p>
            ) : (
              <>
                <section>
                  <h2 className="tar-section-label">TA Strategy</h2>
                  {coachBusy ? (
                    <p className="mt-2 text-[12.5px] text-[var(--tar-mute)]">Loading coach…</p>
                  ) : (
                    <ul className="mt-2 space-y-2">
                      {bullets.map((line) => (
                        <li
                          key={line}
                          className="flex gap-2 text-[12.5px] leading-snug text-[var(--tar-ink)]"
                        >
                          <span className="mt-1.5 h-1 w-1 shrink-0 rounded-full bg-[var(--tar-forest-mid)]" />
                          <span>{line}</span>
                        </li>
                      ))}
                    </ul>
                  )}
                </section>

                <section className="rounded-md border border-[var(--tar-line)] bg-[var(--tar-canvas)] p-3">
                  <h2 className="tar-section-label">Socratic Prompt</h2>
                  <p className="mt-2 text-[12.5px] leading-relaxed text-[var(--tar-ink)]">
                    {prompt}
                  </p>
                  <button
                    type="button"
                    disabled={isHelped || !req}
                    onClick={insertCoach}
                    className="tar-btn-insert mt-3"
                  >
                    Insert into Reply
                  </button>
                </section>

                <p className="px-0.5 text-[11px] leading-snug text-[var(--tar-mute)]">
                  Coaching stays on this pane. The composer starts empty so you choose what
                  the student sees.
                </p>
              </>
            )}
          </div>
        ) : null}
      </aside>

      {error ? (
        <div className="tar-flash tar-flash-error" role="alert">
          {error}
        </div>
      ) : null}
      {toast ? <div className="tar-flash">{toast}</div> : null}
    </div>
  );
}
