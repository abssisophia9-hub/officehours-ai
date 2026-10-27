import { useEffect, useRef, useState } from "react";
import { Navigate, useNavigate } from "react-router";
import { api } from "../api/client.js";
import { useAuth } from "../auth/AuthContext.jsx";

const NOT_FOUND = "No professor-approved material answers this.";
const GROUPS = ["Today", "Last 7 days", "Older"];

function sourceLabel(entry) {
  const file = String(entry?.source_filename || "").trim();
  const page = entry?.page_number;
  if (file && page != null && page !== "") return `${file} · p. ${page}`;
  if (file) return file;
  const title = String(entry?.question_text || "").trim();
  if (title) return title.length > 42 ? `${title.slice(0, 39)}…` : title;
  return "Course material";
}

function sourceQuote(entry) {
  return String(entry?.answer_draft || "").trim();
}

function dayGroup(iso) {
  const then = new Date(iso);
  if (Number.isNaN(then.getTime())) return "Older";
  const now = new Date();
  const startToday = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const startThen = new Date(then.getFullYear(), then.getMonth(), then.getDate());
  const days = Math.round((startToday - startThen) / 86400000);
  if (days <= 0) return "Today";
  if (days < 7) return "Last 7 days";
  return "Older";
}

function SourceChip({ hit }) {
  const [open, setOpen] = useState(false);
  const entry = hit?.entry || {};
  const quote = sourceQuote(entry);
  const label = sourceLabel(entry);
  return (
    <div className={`sa-source${open ? " sa-source-open" : ""}`}>
      <button
        type="button"
        className="sa-chip"
        aria-expanded={open}
        title={label}
        onClick={() => setOpen((value) => !value)}
      >
        {label}
      </button>
      {open ? (
        <p className="sa-quote">{quote || "This source has no stored passage."}</p>
      ) : null}
    </div>
  );
}

export default function StudentAgentPage() {
  const { token, activeCourse } = useAuth();
  const navigate = useNavigate();
  const courseId = activeCourse?.id;
  const [draft, setDraft] = useState("");
  const [threads, setThreads] = useState([]);
  const [activeId, setActiveId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(true);
  const boxRef = useRef(null);
  const endRef = useRef(null);
  const activeIdRef = useRef(activeId);
  activeIdRef.current = activeId;

  useEffect(() => {
    if (!token || !courseId || activeCourse?.role !== "student") return undefined;
    let cancelled = false;
    setLoading(true);
    setDraft("");
    (async () => {
      try {
        let list = await api(`/study-conversations?course_id=${courseId}`, { token });
        if (!list.length) {
          const created = await api("/study-conversations", {
            method: "POST",
            token,
            body: { course_id: courseId },
          });
          list = [created];
        }
        if (cancelled) return;
        setThreads(list);
        setActiveId(list[0].id);
        const detail = await api(`/study-conversations/${list[0].id}`, { token });
        if (!cancelled) setMessages(detail.messages || []);
      } catch (err) {
        if (!cancelled) {
          setThreads([]);
          setActiveId(null);
          setMessages([
            {
              id: "load-error",
              role: "agent",
              error: true,
              text: err?.message || "Could not load your conversations.",
            },
          ]);
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [token, courseId, activeCourse?.role]);

  useEffect(() => {
    endRef.current?.scrollIntoView({ block: "nearest" });
  }, [messages, busy]);

  if (!activeCourse) return <Navigate to="/" replace />;
  if (activeCourse.role !== "student") {
    return (
      <Navigate
        to={`/${activeCourse.role === "professor" ? "professor" : "ta"}`}
        replace
      />
    );
  }

  function grow(element) {
    if (!element) return;
    element.style.height = "auto";
    element.style.height = `${Math.min(element.scrollHeight, 280)}px`;
  }

  async function openThread(id) {
    if (id === activeIdRef.current || busy) return;
    setActiveId(id);
    setMessages([]);
    setLoading(true);
    try {
      const detail = await api(`/study-conversations/${id}`, { token });
      setMessages(detail.messages || []);
    } catch (err) {
      setMessages([
        {
          id: "open-error",
          role: "agent",
          error: true,
          text: err?.message || "Could not open that conversation.",
        },
      ]);
    } finally {
      setLoading(false);
      boxRef.current?.focus();
    }
  }

  async function openNew() {
    if (busy) return;
    const empty = threads.find((thread) => thread.title === "New chat");
    if (empty) {
      await openThread(empty.id);
      return;
    }
    const created = await api("/study-conversations", {
      method: "POST",
      token,
      body: { course_id: courseId },
    });
    setThreads((prev) => [created, ...prev.filter((thread) => thread.id !== created.id)]);
    setActiveId(created.id);
    setMessages([]);
    setDraft("");
    boxRef.current?.focus();
  }

  async function saveMessage(conversationId, body) {
    const saved = await api(`/study-conversations/${conversationId}/messages`, {
      method: "POST",
      token,
      body,
    });
    setThreads((prev) => {
      const next = prev.map((thread) =>
        thread.id === conversationId
          ? { ...thread, title: saved.title, updated_at: saved.updated_at }
          : thread,
      );
      next.sort((a, b) => new Date(b.updated_at) - new Date(a.updated_at));
      return next;
    });
    return saved.message;
  }

  async function send(event) {
    event?.preventDefault();
    const question = draft.trim();
    if (!question || busy || !activeId) return;
    const conversationId = activeId;
    setDraft("");
    if (boxRef.current) boxRef.current.style.height = "auto";
    setMessages((prev) => [...prev, { id: `q-${Date.now()}`, role: "student", text: question }]);
    setBusy(true);
    try {
      await saveMessage(conversationId, { role: "student", text: question });
      const answer = await api("/agent/ask", {
        method: "POST",
        token,
        body: { question, course_id: activeCourse.id },
      });
      const notFound = Boolean(answer.should_seek_help || answer.matched_count === 0);
      const agentBody = {
        role: "agent",
        text: notFound ? NOT_FOUND : answer.answer || "",
        sources: notFound ? [] : answer.sources || [],
        not_found: notFound,
        error: false,
      };
      const stored = await saveMessage(conversationId, agentBody);
      if (activeIdRef.current === conversationId) {
        setMessages((prev) => [...prev, stored]);
      }
    } catch (err) {
      const agentBody = {
        role: "agent",
        text: err?.message || "The study agent didn't respond. Check your connection and try again.",
        error: true,
        not_found: false,
      };
      try {
        const stored = await saveMessage(conversationId, agentBody);
        if (activeIdRef.current === conversationId) {
          setMessages((prev) => [...prev, stored]);
        }
      } catch {
        if (activeIdRef.current === conversationId) {
          setMessages((prev) => [...prev, { id: `e-${Date.now()}`, ...agentBody }]);
        }
      }
    } finally {
      setBusy(false);
      boxRef.current?.focus();
    }
  }

  function onKeyDown(event) {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      send();
    }
  }

  const courseLine = [activeCourse.code, activeCourse.title].filter(Boolean).join(" · ");
  const grouped = GROUPS.map((label) => ({
    label,
    rows: threads.filter((thread) => dayGroup(thread.updated_at) === label),
  })).filter((group) => group.rows.length);

  return (
    <div className="sa-desk">
      <aside className="sa-history" aria-label="Your conversations">
        <button type="button" className="sa-new-chat" onClick={openNew} disabled={busy}>
          + New chat
        </button>
        {grouped.map((group) => (
          <div key={group.label}>
            <div className="sa-history-group">{group.label}</div>
            {group.rows.map((thread) => (
              <button
                key={thread.id}
                type="button"
                className={`sa-history-item${thread.id === activeId ? " active" : ""}`}
                onClick={() => openThread(thread.id)}
              >
                {thread.title}
              </button>
            ))}
          </div>
        ))}
      </aside>

      <div className="sa-page">
        <h1 className="sa-course">{courseLine}</h1>
        <div className="sa-thread" aria-live="polite">
          {loading && messages.length === 0 ? (
            <p className="sa-empty">Loading this conversation.</p>
          ) : null}
          {!loading && messages.length === 0 && !busy ? (
            <p className="sa-empty">Ask a question about this course.</p>
          ) : null}
          {messages.map((message, index) =>
            message.role === "student" ? (
              <p key={message.id} className="sa-bubble sa-bubble-student">
                {message.text}
              </p>
            ) : (
              <article
                key={message.id}
                className={`sa-bubble sa-bubble-agent${message.error ? " sa-bubble-error" : ""}`}
              >
                <p className="sa-answer">{message.text}</p>
                {message.sources?.length ? (
                  <div className="sa-sources">
                    {message.sources.map((hit, index) => (
                      <SourceChip
                        key={hit.entry?.id ?? `${message.id}-${index}`}
                        hit={hit}
                      />
                    ))}
                  </div>
                ) : null}
                {message.not_found || message.notFound ? (
                  <button
                    type="button"
                    className="sa-staff"
                    onClick={() => {
                      const question = [...messages.slice(0, index)]
                        .reverse()
                        .find((item) => item.role === "student")?.text;
                      navigate("/student/ask", { state: { question } });
                    }}
                  >
                    Ask staff
                  </button>
                ) : null}
              </article>
            ),
          )}
          {busy ? <p className="sa-bubble sa-bubble-agent sa-bubble-pending">Looking…</p> : null}
          <div ref={endRef} />
        </div>

        <form className="sa-composer" onSubmit={send}>
          <p className="sa-trust">Answers only come from material your professor approved.</p>
          <textarea
            ref={boxRef}
            className="sa-input"
            rows={2}
            value={draft}
            placeholder="Ask about this course"
            aria-label="Question for the study agent"
            disabled={busy || loading}
            onChange={(event) => {
              setDraft(event.target.value);
              grow(event.target);
            }}
            onKeyDown={onKeyDown}
          />
          <button type="submit" className="sa-send" disabled={busy || loading || !draft.trim()}>
            {busy ? "Looking…" : "Send"}
          </button>
        </form>
      </div>
    </div>
  );
}
