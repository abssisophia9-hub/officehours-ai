import { useEffect, useRef, useState } from "react";
import { Navigate, useNavigate } from "react-router";
import { api } from "../api/client.js";
import { useAuth } from "../auth/AuthContext.jsx";

const NOT_FOUND =
  "No professor-approved material answers this.";

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
        <p className="sa-quote">
          {quote || "This source has no stored passage."}
        </p>
      ) : null}
    </div>
  );
}

export default function StudentAgentPage() {
  const { token, activeCourse } = useAuth();
  const navigate = useNavigate();
  const [draft, setDraft] = useState("");
  const [messages, setMessages] = useState([]);
  const [busy, setBusy] = useState(false);
  const boxRef = useRef(null);
  const endRef = useRef(null);

  useEffect(() => {
    setMessages([]);
    setDraft("");
    if (boxRef.current) boxRef.current.style.height = "auto";
  }, [activeCourse?.id]);

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

  async function send(event) {
    event?.preventDefault();
    const question = draft.trim();
    if (!question || busy) return;
    setDraft("");
    if (boxRef.current) boxRef.current.style.height = "auto";
    setMessages((prev) => [
      ...prev,
      { id: `q-${Date.now()}`, role: "student", text: question },
    ]);
    setBusy(true);
    try {
      const answer = await api("/agent/ask", {
        method: "POST",
        token,
        body: { question, course_id: activeCourse.id },
      });
      const notFound = Boolean(
        answer.should_seek_help || answer.matched_count === 0,
      );
      setMessages((prev) => [
        ...prev,
        {
          id: `a-${Date.now()}`,
          role: "agent",
          text: notFound ? NOT_FOUND : answer.answer || "",
          sources: notFound ? [] : answer.sources || [],
          notFound,
          question,
        },
      ]);
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        {
          id: `e-${Date.now()}`,
          role: "agent",
          error: true,
          text:
            err?.message ||
            "The study agent didn't respond. Check your connection and try again.",
        },
      ]);
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

  const courseLine = [activeCourse.code, activeCourse.title]
    .filter(Boolean)
    .join(" · ");

  return (
    <div className="sa-page fade-up">
      <h1 className="sa-course">{courseLine}</h1>

      <div className="sa-thread" aria-live="polite">
        {messages.length === 0 && !busy ? (
          <p className="sa-empty">Ask a question about this course.</p>
        ) : null}
        {messages.map((message) =>
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
              {message.notFound ? (
                <button
                  type="button"
                  className="sa-staff"
                  onClick={() =>
                    navigate("/student/ask", {
                      state: { question: message.question },
                    })
                  }
                >
                  Ask staff
                </button>
              ) : null}
            </article>
          ),
        )}
        {busy ? (
          <p className="sa-bubble sa-bubble-agent sa-bubble-pending">Looking…</p>
        ) : null}
        <div ref={endRef} />
      </div>

      <form className="sa-composer" onSubmit={send}>
        <p className="sa-trust">
          Answers only come from material your professor approved.
        </p>
        <textarea
          ref={boxRef}
          className="sa-input"
          rows={2}
          value={draft}
          placeholder="Ask about this course"
          aria-label="Question for the study agent"
          disabled={busy}
          onChange={(event) => {
            setDraft(event.target.value);
            grow(event.target);
          }}
          onKeyDown={onKeyDown}
        />
        <button
          type="submit"
          className="sa-send"
          disabled={busy || !draft.trim()}
        >
          {busy ? "Looking…" : "Send"}
        </button>
      </form>
    </div>
  );
}
