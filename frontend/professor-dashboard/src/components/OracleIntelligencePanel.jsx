import { useEffect, useState } from "react";

const API_BASE = import.meta.env.VITE_API_BASE || "http://127.0.0.1:8000";

export default function OracleIntelligencePanel() {
  const [metrics, setMetrics] = useState(null);
  const [lifetime, setLifetime] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;

    async function load() {
      try {
        const [metricsRes, lifetimeRes] = await Promise.all([
          fetch(`${API_BASE}/analytics/oracle-metrics`),
          fetch(`${API_BASE}/analytics/lifetime-confusion`),
        ]);
        if (!metricsRes.ok || !lifetimeRes.ok) {
          throw new Error("Oracle analytics unavailable");
        }
        const metricsJson = await metricsRes.json();
        const lifetimeJson = await lifetimeRes.json();
        if (!cancelled) {
          setMetrics(metricsJson);
          setLifetime(lifetimeJson);
          setError("");
        }
      } catch (loadError) {
        if (!cancelled) {
          setError(loadError.message);
        }
      }
    }

    load();
    return () => {
      cancelled = true;
    };
  }, []);

  if (error) {
    return (
      <section className="rounded-3xl border border-amber-200 bg-amber-50 p-5 text-amber-900">
        <p className="font-bold">Oracle metrics unavailable</p>
        <p className="mt-1 text-sm">{error}</p>
      </section>
    );
  }

  if (!metrics) {
    return (
      <section className="rounded-3xl border border-slate-200 bg-white p-6 text-slate-500 shadow-sm">
        Loading Oracle intelligence…
      </section>
    );
  }

  return (
    <section className="glass-panel p-6">
      <div className="flex flex-col gap-2 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <p className="text-sm font-bold uppercase tracking-[0.2em] text-aui-forest">
            Office Hours Oracle
          </p>
          <h2 className="mt-1 text-2xl font-black tracking-tight text-slate-950">
            Multi-agent intelligence
          </h2>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-600">
            Analyzer → Matcher → Synthesizer coordinate each submission. You
            remain the gate: approve curated answers before the student KB /
            lifetime confusion agent can use them.
          </p>
        </div>
      </div>

      <div className="mt-6 grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <MetricCard label="Time saved" value={`${metrics.time_saved_minutes} min`} />
        <MetricCard label="KB growth" value={metrics.kb_growth} />
        <MetricCard label="Approved answers" value={metrics.kb_approved} />
        <MetricCard label="Oracle runs" value={metrics.oracle_runs} />
      </div>

      <div className="mt-6 grid gap-6 xl:grid-cols-2">
        <div className="rounded-3xl bg-slate-950 p-5 text-white">
          <p className="text-sm font-bold uppercase tracking-wide text-emerald-100">
            Agent flow
          </p>
          <div className="mt-4 grid gap-3 sm:grid-cols-3">
            {["Analyzer", "Matcher", "Synthesizer"].map((name, index) => (
              <div
                key={name}
                className="rounded-2xl bg-white/10 p-4 text-center"
              >
                <p className="text-xs uppercase tracking-wide text-white/60">
                  Agent {index + 1}
                </p>
                <p className="mt-1 text-lg font-black">{name}</p>
              </div>
            ))}
          </div>
          <ul className="mt-4 space-y-2 text-sm text-slate-200">
            {(metrics.recent_agent_traces || []).slice(0, 4).map((trace) => (
              <li
                key={trace.request_id}
                className="rounded-xl bg-white/5 px-3 py-2"
              >
                #{trace.request_id} · {trace.oracle_category || "topic"} ·{" "}
                {trace.assigned_ta || "unassigned"} · {trace.elapsed_ms ?? "?"}ms
              </li>
            ))}
            {(metrics.recent_agent_traces || []).length === 0 ? (
              <li className="text-slate-400">No Oracle traces yet.</li>
            ) : null}
          </ul>
        </div>

        <div className="rounded-3xl border border-emerald-100 bg-emerald-50 p-5">
          <p className="text-sm font-bold uppercase tracking-wide text-emerald-700">
            Lifetime confusion agent
          </p>
          <p className="mt-2 text-sm leading-6 text-emerald-950">
            {lifetime?.message ||
              "Hotspots from professor-approved knowledge."}
          </p>
          <ul className="mt-4 space-y-3">
            {(lifetime?.topics || []).slice(0, 5).map((topic) => (
              <li
                key={topic.topic}
                className="rounded-2xl bg-white/80 px-4 py-3 shadow-sm"
              >
                <div className="flex items-center justify-between gap-3">
                  <p className="font-bold text-slate-900">{topic.topic}</p>
                  <span className="text-xs font-bold text-emerald-700">
                    {topic.approved_count} approved
                  </span>
                </div>
                <p className="mt-1 text-xs text-slate-500">
                  {(topic.top_tags || []).join(", ") || "no tags"}
                </p>
              </li>
            ))}
            {(lifetime?.topics || []).length === 0 ? (
              <li className="text-sm text-emerald-900">
                Approve curated KB entries to train the lifetime confusion map.
              </li>
            ) : null}
          </ul>
        </div>
      </div>
    </section>
  );
}

function MetricCard({ label, value }) {
  return (
    <div className="rounded-3xl border border-slate-200 bg-slate-50 p-5">
      <p className="text-xs font-bold uppercase tracking-wide text-slate-500">
        {label}
      </p>
      <p className="mt-2 text-3xl font-black text-slate-950">{value}</p>
    </div>
  );
}
