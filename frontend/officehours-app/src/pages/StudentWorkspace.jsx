import { useEffect, useState } from "react";
import { Link, Navigate, useLocation, useNavigate } from "react-router";
import { api } from "../api/client.js";
import { useAuth } from "../auth/AuthContext.jsx";

const HELP_TYPES = [
  { value: "message", label: "Message" },
  { value: "face_to_face", label: "Face-to-face" },
  { value: "online_meeting", label: "Online" },
];

function composeAskText({ question, topic, code, tried }) {
  const blocks = [question.trim()];
  if (topic.trim()) blocks.push(`Which topic or week?\n${topic.trim()}`);
  if (code.trim()) blocks.push(`Paste code or an error\n${code.trim()}`);
  if (tried.trim()) blocks.push(`What have you tried?\n${tried.trim()}`);
  return blocks.join("\n\n");
}

export default function StudentWorkspace() {
  const { token, user, activeCourse } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [text, setText] = useState("");
  const [topic, setTopic] = useState("");
  const [codeSnippet, setCodeSnippet] = useState("");
  const [tried, setTried] = useState("");
  const [chapters, setChapters] = useState([]);
  const [anonymous, setAnonymous] = useState(true);
  const [helpMode, setHelpMode] = useState("message");
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [buddyStatus, setBuddyStatus] = useState(null);
  const [buddyBusy, setBuddyBusy] = useState(false);
  const [routing, setRouting] = useState(null);

  useEffect(() => {
    const question = location.state?.question;
    if (typeof question !== "string" || !question.trim()) return;
    setText(question);
    setAnonymous(true);
    window.setTimeout(() => {
      const box = document.getElementById("ask-box");
      box?.focus();
      box?.setSelectionRange(box.value.length, box.value.length);
    }, 40);
  }, [location.key, location.state]);

  useEffect(() => {
    if (!activeCourse || !token) return undefined;
    let cancelled = false;
    setRouting(null);
    setChapters([]);
    setTopic("");
    api(`/requests/routing?course_id=${activeCourse.id}`, { token })
      .then((data) => {
        if (!cancelled) setRouting(data || null);
      })
      .catch(() => {
        if (!cancelled) setRouting({ destination: "unknown", line: "" });
      });
    api(`/help-room/community/?course_id=${activeCourse.id}`, { token })
      .then((data) => {
        if (cancelled) return;
        const labels = (data?.chapters || [])
          .map((item) => String(item?.label || "").trim())
          .filter(Boolean);
        setChapters(labels);
      })
      .catch(() => {
        if (!cancelled) setChapters([]);
      });
    return () => {
      cancelled = true;
    };
  }, [activeCourse, token]);

  if (!activeCourse) return <Navigate to="/" replace />;
  if (activeCourse.role !== "student") {
    return (
      <Navigate
        to={`/${activeCourse.role === "professor" ? "professor" : "ta"}`}
        replace
      />
    );
  }

  const noStaff = routing?.destination === "none";
  const canSend = routing?.destination === "ta" || routing?.destination === "professor";
  const visibleName = user.display_name || "your name";
  const identityLine = anonymous
    ? "Staff see your question, not your name or ID."
    : user.student_id
      ? `Staff will see: ${visibleName} (ID ${user.student_id})`
      : `Staff will see: ${visibleName}`;

  async function submitQuestion(event) {
    event.preventDefault();
    if (!text.trim() || !canSend) return;
    setBusy(true);
    setError("");
    try {
      if (!anonymous && !user.student_id && !user.display_name) {
        setError("Identified asks need your name or student ID on the account.");
        setBusy(false);
        return;
      }
      const created = await api("/requests/", {
        method: "POST",
        token,
        body: {
          text: composeAskText({ question: text, topic, code: codeSnippet, tried }),
          anonymous,
          student_id: anonymous ? null : user.student_id,
          student_name: anonymous ? null : user.display_name,
          course: activeCourse.code,
          course_id: activeCourse.id,
          code_snippet: codeSnippet.trim() || null,
          help_mode: helpMode,
        },
      });
      setResult(created);
      setBuddyStatus(null);
      setText("");
      setTopic("");
      setCodeSnippet("");
      setTried("");
      if (created?.id) {
        try {
          const status = await api(`/requests/${created.id}/study-buddy`, { token });
          setBuddyStatus(status);
        } catch {
          setBuddyStatus(null);
        }
        window.setTimeout(() => {
          navigate(`/student/asks?focus=${created.id}`);
        }, 700);
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  async function optInStudyBuddy() {
    if (!result?.id) return;
    setBuddyBusy(true);
    try {
      const status = await api(`/requests/${result.id}/study-buddy`, {
        method: "POST",
        token,
        body: { request_id: result.id },
      });
      setBuddyStatus(status);
    } catch (err) {
      setError(err.message);
    } finally {
      setBuddyBusy(false);
    }
  }

  const courseLine = [activeCourse.code, activeCourse.title]
    .filter(Boolean)
    .join(" · ");

  return (
    <div className="sd fade-up">
      <h1 className="sa-course">{courseLine}</h1>
      <section id="ask" className="sd-ask sa-help">
        {noStaff ? (
          <div className="sd-nostaff" role="status">
            <p>
              This course has no TA or professor assigned, so asks can&apos;t be sent.
              Try the Study Agent.
            </p>
            <Link to="/student" className="sd-cta">
              Study Agent
            </Link>
          </div>
        ) : !canSend ? (
          <p className="sd-form-hint">
            {routing?.destination === "unknown"
              ? "Couldn't check who receives asks. Refresh and try again."
              : "Checking who receives asks…"}
          </p>
        ) : (
          <>
            {routing?.line ? <p className="sd-route">{routing.line}</p> : null}
            <form onSubmit={submitQuestion}>
              <label className="sd-check">
                <input
                  type="checkbox"
                  checked={anonymous}
                  onChange={(event) => setAnonymous(event.target.checked)}
                />
                Hide my name
              </label>
              <p className="sd-check-note">{identityLine}</p>

              <div className="sd-segment" role="radiogroup" aria-label="Help type">
                {HELP_TYPES.map((option) => (
                  <button
                    key={option.value}
                    type="button"
                    role="radio"
                    aria-checked={helpMode === option.value}
                    className={helpMode === option.value ? "is-on" : ""}
                    onClick={() => setHelpMode(option.value)}
                  >
                    {option.label}
                  </button>
                ))}
              </div>

              <textarea
                id="ask-box"
                className="field-glass mt-3 w-full px-4 py-3"
                placeholder="Describe what you're stuck on."
                value={text}
                onChange={(event) => setText(event.target.value)}
                required={canSend}
                disabled={!canSend}
              />

              <details className="sd-details">
                <summary>Add details (optional)</summary>
                <label htmlFor="ask-topic">Which topic or week?</label>
                {chapters.length ? (
                  <select
                    id="ask-topic"
                    className="field-glass mt-1 w-full px-3"
                    value={topic}
                    onChange={(event) => setTopic(event.target.value)}
                  >
                    <option value="">Select a topic or week</option>
                    {chapters.map((label) => (
                      <option key={label} value={label}>
                        {label}
                      </option>
                    ))}
                  </select>
                ) : (
                  <input
                    id="ask-topic"
                    className="field-glass mt-1 w-full px-3"
                    value={topic}
                    onChange={(event) => setTopic(event.target.value)}
                    placeholder="For example, week 4 or hashing"
                  />
                )}
                <label htmlFor="ask-code">Paste code or an error</label>
                <textarea
                  id="ask-code"
                  className="field-glass mt-1 min-h-20 w-full px-4 py-3 font-mono text-xs"
                  value={codeSnippet}
                  onChange={(event) => setCodeSnippet(event.target.value)}
                />
                <label htmlFor="ask-tried">What have you tried?</label>
                <textarea
                  id="ask-tried"
                  className="field-glass mt-1 min-h-16 w-full px-4 py-3"
                  value={tried}
                  onChange={(event) => setTried(event.target.value)}
                />
              </details>

              {error ? (
                <p className="mt-3 text-sm text-[var(--theme-red-fg)]">{error}</p>
              ) : null}
              <button
                type="submit"
                disabled={busy || !text.trim()}
                className="sd-cta mt-4"
              >
                {busy ? "Sending…" : anonymous ? "Send anonymously" : "Send"}
              </button>
            </form>
          </>
        )}

        {result ? (
          <div className="soft-stat mt-5 ml-2 text-sm">
            <p className="font-semibold text-[var(--theme-title)]">
              {result.anonymous ? "Sent anonymously" : "Sent"} · request{" "}
              <span className="bh-pill bh-pill-green">#{result.id}</span>
            </p>
            <p className="mt-1 text-xs text-[var(--theme-text-muted)]">
              Help mode:{" "}
              {result.help_mode === "face_to_face"
                ? "face-to-face"
                : result.help_mode === "online_meeting"
                  ? "online"
                  : "message"}
            </p>
            {result.assigned_ta ? (
              <p className="mt-1 text-xs text-[var(--theme-text-muted)]">
                Assigned to: {result.assigned_ta}
                {result.assignee_role === "professor" ? " (professor)" : ""}
              </p>
            ) : null}
            {result.sensitive ? (
              <p className="mt-2 rounded-lg bg-[var(--theme-amber-bg)] p-2.5 text-xs text-[var(--theme-amber-fg)]">
                This looks private. Staff will follow up one to one.
              </p>
            ) : null}
            {result.solidarity_message ? (
              <p className="mt-2 rounded-lg bg-[var(--theme-surface-soft)] p-2.5 text-xs">
                {result.solidarity_message}
              </p>
            ) : null}
            {buddyStatus?.eligible && !buddyStatus.opted_in ? (
              <div className="mt-3 rounded-lg border border-[var(--theme-emerald-border)] bg-[var(--theme-emerald-bg)] p-3 text-xs text-[var(--theme-emerald-fg)]">
                <p>{buddyStatus.study_buddy_message}</p>
                <button
                  type="button"
                  disabled={buddyBusy}
                  className="sd-cta mt-2 px-3 py-1.5 text-xs"
                  onClick={optInStudyBuddy}
                >
                  {buddyBusy ? "Saving…" : "Study with others on this question"}
                </button>
              </div>
            ) : null}
            {buddyStatus?.opted_in ? (
              <p className="mt-3 rounded-lg bg-[var(--theme-emerald-bg)] p-2.5 text-xs text-[var(--theme-emerald-fg)]">
                {buddyStatus.study_buddy_message}
              </p>
            ) : null}
          </div>
        ) : null}
      </section>
    </div>
  );
}
