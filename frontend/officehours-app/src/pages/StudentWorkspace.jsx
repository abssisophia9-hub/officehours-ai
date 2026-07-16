import { useState } from "react";
import { Navigate } from "react-router-dom";
import { api } from "../api/client.js";
import { useAuth } from "../auth/AuthContext.jsx";

export default function StudentWorkspace() {
  const { token, user, activeCourse } = useAuth();
  const [text, setText] = useState("");
  const [codeSnippet, setCodeSnippet] = useState("");
  const [anonymous, setAnonymous] = useState(true);
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [agentQ, setAgentQ] = useState("");
  const [agentA, setAgentA] = useState("");

  if (!activeCourse) return <Navigate to="/" replace />;
  if (activeCourse.role !== "student") {
    return <Navigate to={`/${activeCourse.role === "professor" ? "professor" : "ta"}`} replace />;
  }

  async function submitQuestion(event) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
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
        },
      });
      setResult(created);
      setText("");
      setCodeSnippet("");
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  async function askAgent(event) {
    event.preventDefault();
    setAgentA("");
    try {
      const answer = await api("/agent/ask", {
        method: "POST",
        token,
        body: { question: agentQ, course_id: activeCourse.id },
      });
      setAgentA(answer.answer || JSON.stringify(answer));
    } catch (err) {
      setAgentA(err.message);
    }
  }

  return (
    <div className="fade-up grid gap-6 lg:grid-cols-2">
      <form onSubmit={submitQuestion} className="glass-panel p-6">
        <p className="glass-chip mb-3">Student · {activeCourse.code}</p>
        <h1 className="font-display max-w-[16ch] text-3xl font-semibold sm:text-4xl">
          Ask for help
        </h1>
        <p className="mt-2 max-w-md font-medium text-aui-deep/70">
          Start quietly if you prefer. Anonymous asks never store your name or ID —
          staff only see the question and a request code.
        </p>
        <label className="clay-blob clay-blob-mint mt-5 flex w-full cursor-pointer items-start gap-3 px-4 py-3">
          <input
            type="checkbox"
            className="mt-1 h-4 w-4 accent-aui-forest"
            checked={anonymous}
            onChange={(event) => setAnonymous(event.target.checked)}
          />
          <span>
            <span className="block font-semibold text-aui-ink">Quiet ask (anonymous)</span>
            <span className="mt-1 block text-sm font-medium text-aui-deep/70">
              Keep your request code and check status later.
            </span>
          </span>
        </label>
        <textarea
          className="field-glass mt-4 min-h-36 px-4 py-3"
          placeholder="Describe what you're stuck on…"
          value={text}
          onChange={(event) => setText(event.target.value)}
          required
        />
        <textarea
          className="field-glass mt-3 min-h-24 px-4 py-3 font-mono text-sm"
          placeholder="Optional code snippet"
          value={codeSnippet}
          onChange={(event) => setCodeSnippet(event.target.value)}
        />
        {error ? <p className="mt-3 text-sm text-red-700">{error}</p> : null}
        <button type="submit" disabled={busy} className="btn-primary mt-4 px-5 py-3">
          {busy ? "Running Oracle…" : anonymous ? "Submit anonymously" : "Submit to office hours"}
        </button>
      </form>

      <div className="space-y-6">
        {result ? (
          <section className="glass-panel p-6">
            <p className="glass-chip">Request #{result.id}</p>
            <h2 className="font-display mt-3 text-2xl font-semibold">
              {result.anonymous ? "Submitted quietly" : "Submitted"}
            </h2>
            <p className="mt-2 text-sm text-aui-deep/75">{result.text}</p>
            {result.anonymous ? (
              <p className="mt-3 rounded-2xl bg-emerald-50/80 p-3 text-sm text-aui-deep/80">
                Your identity was not stored. Save request code <strong>#{result.id}</strong> to
                check status later.
              </p>
            ) : null}
            {result.sensitive ? (
              <p className="mt-3 rounded-2xl bg-amber-50/90 p-3 text-sm text-amber-950">
                This looks private/sensitive — it will be routed for confidential follow-up,
                not a public group review.
              </p>
            ) : null}
            {result.oracle ? (
              <div className="mt-4 grid gap-2">
                <div className="soft-stat text-sm font-medium">
                  <strong>Analyzer:</strong> {result.oracle.analyzer.category} ·{" "}
                  {result.oracle.analyzer.difficulty}
                </div>
                <div className="soft-stat text-sm font-medium">
                  <strong>Matcher:</strong> {result.oracle.matcher.assigned_ta} · wait ~
                  {result.oracle.matcher.estimated_wait_minutes} min
                </div>
                <div className="soft-stat text-sm font-medium">
                  <strong>Hint:</strong> {result.oracle.synthesizer.student_hint}
                </div>
              </div>
            ) : null}
          </section>
        ) : null}

        <form onSubmit={askAgent} className="glass-panel p-6">
          <h2 className="font-display text-2xl font-semibold">Approved KB agent</h2>
          <p className="mt-1 text-sm text-aui-deep/65">
            Answers only from professor-approved FAQs and course materials for this course.
          </p>
          <input
            className="field-glass mt-3 px-4 py-3"
            placeholder="Ask from approved answers / slides…"
            value={agentQ}
            onChange={(event) => setAgentQ(event.target.value)}
          />
          <button type="submit" className="btn-ghost mt-3 px-4 py-2 text-sm">
            Ask
          </button>
          {agentA ? (
            <p className="mt-4 whitespace-pre-wrap rounded-2xl bg-white/50 p-4 text-sm">
              {agentA}
            </p>
          ) : null}
        </form>
      </div>
    </div>
  );
}
