export default function ConfirmationScreen({ result, onReset, onCheckStatus }) {
  const oracle = result.oracle;

  return (
    <div className="w-full max-w-4xl animate-fade-in-up rounded-3xl bg-white p-8 shadow-2xl shadow-emerald-200/40 sm:p-10">
      <div className="mx-auto mb-6 flex h-20 w-20 animate-pop-in items-center justify-center rounded-full bg-emerald-100">
        <svg
          className="h-10 w-10 text-emerald-600"
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

      <h1 className="text-center text-3xl font-extrabold tracking-tight text-slate-900 sm:text-4xl">
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
          <span className="rounded-full bg-indigo-100 px-3 py-1 text-sm font-bold text-indigo-700">
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

      {oracle ? (
        <div className="mt-6 grid gap-4 lg:grid-cols-3">
          <AgentCard
            title="Analyzer"
            accent="bg-sky-600"
            lines={[
              `Category: ${oracle.analyzer.category}`,
              `Difficulty: ${oracle.analyzer.difficulty}`,
              `Est. time: ${oracle.analyzer.estimated_minutes} min`,
              `Tags: ${(oracle.analyzer.tags || []).join(", ")}`,
            ]}
          />
          <AgentCard
            title="Matcher"
            accent="bg-violet-600"
            lines={[
              `Assigned: ${oracle.matcher.assigned_ta}`,
              `Wait: ~${oracle.matcher.estimated_wait_minutes} min`,
              `Alternative: ${oracle.matcher.alternative_ta || "n/a"}`,
              oracle.matcher.rationale,
            ]}
          />
          <AgentCard
            title="Synthesizer"
            accent="bg-emerald-600"
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

      <div className="mt-6 grid gap-3 sm:grid-cols-2">
        <button
          type="button"
          onClick={onCheckStatus}
          className="rounded-2xl border-2 border-indigo-200 bg-indigo-50 px-6 py-5 text-lg font-bold text-indigo-800 transition hover:border-indigo-300 hover:bg-indigo-100 active:scale-[0.99]"
        >
          Check status now
        </button>
        <button
          type="button"
          onClick={onReset}
          className="rounded-2xl bg-slate-900 px-6 py-5 text-lg font-bold text-white shadow-lg transition hover:bg-slate-800 active:scale-[0.99]"
        >
          Submit another question
        </button>
      </div>
    </div>
  );
}

function AgentCard({ title, accent, lines }) {
  return (
    <article className="rounded-2xl border border-slate-200 bg-white p-5 text-left shadow-sm">
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
