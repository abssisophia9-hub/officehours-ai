import { useEffect, useState } from "react";
import { Navigate, useLocation, useNavigate } from "react-router";
import { api } from "../api/client.js";
import { useAuth } from "../auth/AuthContext.jsx";

export default function StudentWorkspace() {
  const { token, user, activeCourse } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [text, setText] = useState("");
  const [codeSnippet, setCodeSnippet] = useState("");
  const [anonymous, setAnonymous] = useState(true);
  const [helpMode, setHelpMode] = useState("message");
  const [showHelpModes, setShowHelpModes] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [buddyStatus, setBuddyStatus] = useState(null);
  const [buddyBusy, setBuddyBusy] = useState(false);
  const [routingLine, setRoutingLine] = useState("");

  useEffect(() => {
    const question = location.state?.question;
    if (typeof question !== "string" || !question.trim()) return;
    setText(question);
    setAnonymous(true);
    setShowHelpModes(true);
    window.setTimeout(() => {
      const box = document.getElementById("ask-box");
      box?.focus();
      box?.setSelectionRange(box.value.length, box.value.length);
    }, 40);
  }, [location.key, location.state]);

  useEffect(() => {
    if (!activeCourse || !token) return;
    let cancelled = false;
    api(`/requests/routing?course_id=${activeCourse.id}`, { token })
      .then((data) => {
        if (!cancelled) setRoutingLine(data?.line || "");
      })
      .catch(() => {
        if (!cancelled) setRoutingLine("");
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

  async function submitQuestion(event) {
    event.preventDefault();
    if (!text.trim()) return;
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
          text,
          anonymous,
          student_id: anonymous ? null : user.student_id,
          student_name: anonymous ? null : user.display_name,
          course: activeCourse.code,
          course_id: activeCourse.id,
          code_snippet: codeSnippet || null,
          help_mode: helpMode,
        },
      });
      setResult(created);
      setBuddyStatus(null);
      setText("");
      setCodeSnippet("");
      setShowHelpModes(false);
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
        <div className="sd-ask-head">
          <div>
            <h2>Ask for help</h2>
            <p className="sd-ask-copy">
              Send this question to a TA or your professor. You can hide your name.
            </p>
            {routingLine ? <p className="sd-ask-copy">{routingLine}</p> : null}
          </div>
        </div>

        <div className="sd-identity">
          <p className="sd-identity-label">Who should staff see?</p>
          <div className="sd-identity-grid">
            <label
              className={`sd-choice sd-choice-quiet ${anonymous ? "sd-choice-on" : ""}`}
            >
              <input
                type="radio"
                name="identity"
                className="mt-1 h-4 w-4 accent-[var(--theme-forest)]"
                checked={anonymous}
                onChange={() => setAnonymous(true)}
              />
              <span>
                <strong>Hide my name</strong>
                <span>Staff see the question, not your name or ID.</span>
              </span>
            </label>
            <label className={`sd-choice ${!anonymous ? "sd-choice-on" : ""}`}>
              <input
                type="radio"
                name="identity"
                className="mt-1 h-4 w-4 accent-[var(--theme-forest)]"
                checked={!anonymous}
                onChange={() => setAnonymous(false)}
              />
              <span>
                <strong>Use my name</strong>
                <span>
                  Share <strong>{user.display_name || "your name"}</strong>
                  {user.student_id ? (
                    <>
                      {" "}
                      · ID <strong>{user.student_id}</strong>
                    </>
                  ) : null}
                  .
                </span>
              </span>
            </label>
          </div>
        </div>

        <form onSubmit={submitQuestion} className="mt-4">
          <textarea
            id="ask-box"
            className="field-glass mt-1 w-full px-4 py-3"
            placeholder="Describe what you're stuck on."
            value={text}
            onChange={(event) => {
              setText(event.target.value);
              if (event.target.value.trim()) setShowHelpModes(true);
            }}
            required
          />

          {showHelpModes ? (
            <>
              <fieldset className="mt-3 space-y-2">
                <legend className="sd-identity-label">How do you want help?</legend>
                {[
                  {
                    value: "message",
                    title: "Message",
                    note: "A written reply. No meeting.",
                  },
                  {
                    value: "face_to_face",
                    title: "Face-to-face meeting",
                    note: "In person on campus.",
                  },
                  {
                    value: "online_meeting",
                    title: "Online meeting",
                    note: "A video call.",
                  },
                ].map((option) => (
                  <label
                    key={option.value}
                    className={`sd-choice ${helpMode === option.value ? "sd-choice-on" : ""}`}
                  >
                    <input
                      type="radio"
                      name="help_mode"
                      className="mt-1 h-4 w-4 accent-[var(--theme-forest)]"
                      checked={helpMode === option.value}
                      onChange={() => setHelpMode(option.value)}
                    />
                    <span>
                      <strong>{option.title}</strong>
                      <span>{option.note}</span>
                    </span>
                  </label>
                ))}
              </fieldset>
              <textarea
                className="field-glass mt-3 min-h-20 w-full px-4 py-3 font-mono text-xs"
                placeholder="Optional code snippet"
                value={codeSnippet}
                onChange={(event) => setCodeSnippet(event.target.value)}
              />
            </>
          ) : (
            <p className="sd-form-hint">
              Start typing to choose message, face-to-face, or online.
            </p>
          )}

          {error ? (
            <p className="mt-3 text-sm text-[var(--theme-red-fg)]">{error}</p>
          ) : null}
          <button
            type="submit"
            disabled={busy || !text.trim()}
            className="sd-cta mt-4"
          >
            {busy ? "Sending…" : anonymous ? "Send without my name" : "Send with my name"}
          </button>
        </form>

        {result ? (
          <div className="soft-stat mt-5 ml-2 text-sm">
            <p className="font-semibold text-[var(--theme-title)]">
              {result.anonymous ? "Sent without your name" : "Sent with your name"} ·
              request <span className="bh-pill bh-pill-green">#{result.id}</span>
            </p>
            <p className="mt-1 text-xs text-[var(--theme-text-muted)]">
              Help mode:{" "}
              {result.help_mode === "face_to_face"
                ? "face-to-face meeting"
                : result.help_mode === "online_meeting"
                  ? "online meeting"
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
