import { useState } from "react";
import { addFollowUp, getRequest } from "../api/requests.js";

export default function ConfirmationScreen({
  result,
  onReset,
  onCheckStatus,
  onResultUpdate,
}) {
  const oracle = result.oracle;
  const [followUpText, setFollowUpText] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function sendFollowUp(event) {
    event.preventDefault();
    if (!followUpText.trim()) return;
    setBusy(true);
    setError("");
    try {
      await addFollowUp(result.id, {
        message: followUpText,
        authorRole: "student",
        authorName: result.student_name || result.student_id || "Student",
      });
      const fresh = await getRequest(result.id);
      onResultUpdate?.(fresh);
      setFollowUpText("");
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="glass-panel w-full max-w-4xl animate-fade-in-up p-8 sm:p-10">
      <div className="mx-auto mb-6 flex h-20 w-20 animate-pop-in items-center justify-center rounded-full bg-emerald-100/90 backdrop-blur">
        <svg
          className="h-10 w-10 text-aui-forest"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="3"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <path d="M20 6L9 17l-5-5" />
        </svg>
      </div>

      <h1 className="font-display text-center text-3xl font-bold tracking-tight text-aui-ink sm:text-4xl">
        Request submitted
      </h1>
      <p className="mt-2 text-center text-lg text-slate-500">
        Three Oracle agents coordinated in{" "}
        {oracle?.elapsed_ms != null ? `~${oracle.elapsed_ms}ms` : "under 2 seconds"}.
        Professor still approves what reaches the student KB agent.
      </p>

      <div className="mt-8 rounded-2xl border border-slate-100 bg-slate-50 p-6 text-left">
        <div className="flex items-center justify-between gap-3">
          <span className="text-sm font-semibold uppercase tracking-wide text-slate-400">
            Request
          </span>
          <span className="glass-chip">#{result.id}</span>
        </div>
        <p className="mt-3 text-lg leading-relaxed text-slate-800">
          “{result.text}”
        </p>
        <p className="mt-4 text-sm font-medium text-slate-500">
          {result.student_name ? `${result.student_name} · ` : ""}
          {result.course || "Course TBD"} ·{" "}
          {result.anonymous
            ? "Anonymous"
            : `ID ${result.student_id || "identified"}`}
        </p>
      </div>

      {oracle ? (
        <div className="mt-6 grid gap-4 lg:grid-cols-3">
          <AgentCard
            title="Analyzer"
            accent="bg-sky-500"
            lines={[
              `Category: ${oracle.analyzer.category}`,
              `Difficulty: ${oracle.analyzer.difficulty}`,
              `Est. time: ${oracle.analyzer.estimated_minutes} min`,
              `Tags: ${(oracle.analyzer.tags || []).join(", ")}`,
            ]}
          />
          <AgentCard
            title="Matcher"
            accent="bg-orange-500"
            lines={[
              `Assigned: ${oracle.matcher.assigned_ta}`,
              `Wait: ~${oracle.matcher.estimated_wait_minutes} min`,
              `Alternative: ${oracle.matcher.alternative_ta || "n/a"}`,
              oracle.matcher.rationale,
            ]}
          />
          <AgentCard
            title="Synthesizer"
            accent="bg-emerald-500"
            lines={[
              `Similar KB hits: ${oracle.synthesizer.similar_count}`,
              `Hint: ${oracle.synthesizer.student_hint}`,
              oracle.synthesizer.kb_insight,
            ]}
          />
        </div>
      ) : null}

      {oracle?.synthesizer?.student_hint ? (
        <div className="mt-6 rounded-2xl border border-amber-200 bg-amber-50 p-5 text-left">
          <p className="text-sm font-bold uppercase tracking-wide text-amber-700">
            While you wait
          </p>
          <p className="mt-2 text-base leading-7 text-amber-950">
            {oracle.synthesizer.student_hint}
          </p>
        </div>
      ) : null}

      <div className="mt-6 rounded-2xl border border-slate-100 bg-white/70 p-5 text-left">
        <p className="text-sm font-bold uppercase tracking-wide text-slate-500">
          Follow-ups
        </p>
        {(result.followups || []).length === 0 ? (
          <p className="mt-2 text-sm text-slate-500">
            Need to clarify something? Add a follow-up for your TA.
          </p>
        ) : (
          <ul className="mt-3 space-y-2">
            {(result.followups || []).map((item) => (
              <li
                key={item.id}
                className="rounded-xl bg-slate-50 px-3 py-2 text-sm text-slate-700"
              >
                <span className="font-semibold">{item.author_name}</span>: {item.message}
              </li>
            ))}
          </ul>
        )}
        <form onSubmit={sendFollowUp} className="mt-4 space-y-3">
          <textarea
            className="field-glass min-h-24 w-full px-4 py-3"
            placeholder="Add a follow-up message…"
            value={followUpText}
            onChange={(event) => setFollowUpText(event.target.value)}
            required
            minLength={2}
          />
          {error ? <p className="text-sm text-red-700">{error}</p> : null}
          <button type="submit" disabled={busy} className="btn-ghost px-4 py-2 text-sm">
            {busy ? "Sending…" : "Send follow-up"}
          </button>
        </form>
      </div>

      <div className="mt-6 grid gap-3 sm:grid-cols-2">
        <button
          type="button"
          onClick={onCheckStatus}
          className="btn-ghost rounded-2xl px-6 py-5 text-lg"
        >
          Check status now
        </button>
        <button
          type="button"
          onClick={onReset}
          className="btn-primary rounded-2xl px-6 py-5 text-lg"
        >
          Submit another question
        </button>
      </div>
    </div>
  );
}

function AgentCard({ title, accent, lines }) {
  return (
    <article className="glass-panel p-5 text-left">
      <div className="flex items-center gap-2">
        <span className={`h-2.5 w-2.5 rounded-full ${accent}`} />
        <h2 className="text-lg font-black text-slate-900">{title}</h2>
      </div>
      <ul className="mt-3 space-y-2 text-sm leading-6 text-slate-600">
        {lines.filter(Boolean).map((line) => (
          <li key={line}>{line}</li>
        ))}
      </ul>
    </article>
  );
}
