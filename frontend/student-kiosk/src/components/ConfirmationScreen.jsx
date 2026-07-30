export default function ConfirmationScreen({ result, onReset, onCheckStatus }) {
  const triage = result.triage || result.oracle;

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
        Ask Triage (Analyzer → Matcher → Synthesizer) finished in{" "}
        {triage?.elapsed_ms != null ? `~${triage.elapsed_ms}ms` : "under 2 seconds"}.
        Professor still approves what reaches the student KB agent.
      </p>

      <div className="mt-8 rounded-2xl border border-slate-100 bg-slate-50 p-6 text-left">
        <div className="flex items-center justify-between gap-3">
          <span className="text-sm font-semibold uppercase tracking-wide text-slate-400">
            Request
          </span>
          <span className="glass-chip">
            #{result.id}
          </span>
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

      {triage ? (
        <div className="mt-6 grid gap-4 lg:grid-cols-3">
          <AgentCard
            title="Analyzer"
            accent="bg-sky-500"
            lines={[
              `Category: ${triage.analyzer.category}`,
              `Difficulty: ${triage.analyzer.difficulty}`,
              `Est. time: ${triage.analyzer.estimated_minutes} min`,
              `Tags: ${(triage.analyzer.tags || []).join(", ")}`,
            ]}
          />
          <AgentCard
            title="Matcher"
            accent="bg-orange-500"
            lines={[
              `Assigned: ${triage.matcher.assigned_ta}`,
              `Wait: ~${triage.matcher.estimated_wait_minutes} min`,
              `Alternative: ${triage.matcher.alternative_ta || "n/a"}`,
              triage.matcher.rationale,
            ]}
          />
          <AgentCard
            title="Synthesizer"
            accent="bg-emerald-500"
            lines={[
              `Similar KB hits: ${triage.synthesizer.similar_count}`,
              `Hint: ${triage.synthesizer.student_hint}`,
              triage.synthesizer.kb_insight,
            ]}
          />
        </div>
      ) : null}

      {triage?.synthesizer?.student_hint ? (
        <div className="mt-6 rounded-2xl border border-amber-200 bg-amber-50 p-5 text-left">
          <p className="text-sm font-bold uppercase tracking-wide text-amber-700">
            While you wait
          </p>
          <p className="mt-2 text-base leading-7 text-amber-950">
            {triage.synthesizer.student_hint}
          </p>
        </div>
      ) : null}

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
