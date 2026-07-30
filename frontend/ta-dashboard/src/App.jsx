import { useCallback, useEffect, useState } from "react";
import { fetchTaQueue, resolveTaItem } from "./api/ta.js";
import { useOfficeHoursSocket } from "./hooks/useOfficeHoursSocket.js";

export default function App() {
  const [queue, setQueue] = useState([]);
  const [status, setStatus] = useState("loading");
  const [error, setError] = useState("");
  const [taName, setTaName] = useState("Alice Chen");
  const [selectedId, setSelectedId] = useState(null);
  const [notes, setNotes] = useState("");
  const [hint, setHint] = useState("");
  const [saving, setSaving] = useState(false);
  const [toast, setToast] = useState("");

  const loadQueue = useCallback(async () => {
    setError("");
    try {
      const data = await fetchTaQueue();
      setQueue(data);
      setStatus("success");
      if (selectedId && !data.some((item) => item.request.id === selectedId)) {
        setSelectedId(null);
        setNotes("");
        setHint("");
      }
    } catch (loadError) {
      setStatus("error");
      setError(loadError.message);
    }
  }, [selectedId]);

  useEffect(() => {
    loadQueue();
  }, [loadQueue]);

  const { live } = useOfficeHoursSocket((event) => {
    if (
      event.type === "request.created" ||
      event.type === "knowledge.created" ||
      event.type === "knowledge.updated" ||
      event.type === "ta.resolved"
    ) {
      loadQueue();
    }
  });

  const selected = queue.find((item) => item.request.id === selectedId) || null;

  function selectItem(item) {
    setSelectedId(item.request.id);
    setNotes(item.knowledge_entry?.answer_draft || "");
    setHint(item.knowledge_entry?.student_hint || "");
    setToast("");
  }

  async function handleResolve(resolutionStatus) {
    if (!selected) {
      return;
    }
    setSaving(true);
    setError("");
    try {
      const result = await resolveTaItem({
        request_id: selected.request.id,
        ta_name: taName || "TA",
        teaching_notes: notes,
        student_hint: hint || null,
        resolution_status: resolutionStatus,
      });
      setToast(result.message);
      await loadQueue();
      setSelectedId(null);
      setNotes("");
      setHint("");
    } catch (resolveError) {
      setError(resolveError.message);
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="aui-shell min-h-full text-aui-ink">
      <header className="px-6 pt-6">
        <div className="mx-auto mb-3 h-1.5 max-w-6xl overflow-hidden rounded-full bg-gradient-to-r from-emerald-400 via-sky-400 to-orange-400 shadow-[0_0_24px_rgba(16,185,129,0.45)]" />
        <div className="glass-header mx-auto flex max-w-6xl flex-col gap-4 rounded-2xl px-6 py-5 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex items-center gap-4">
            <img
              src="/aui-logo.png"
              alt="Al Akhawayn University"
              className="aui-logo"
            />
            <div>
              <p className="text-sm font-semibold uppercase tracking-[0.16em] text-aui-forest">
                OfficeHours AI · AUI
              </p>
              <h1 className="font-display text-3xl font-bold tracking-tight">
                TA Dashboard
              </h1>
            </div>
          </div>
          <div className="flex flex-wrap items-center gap-3">
            <span className={`glass-chip ${live ? "" : "opacity-70"}`}>
              <span
                className={`h-2 w-2 rounded-full ${live ? "live-pulse bg-emerald-500" : "bg-slate-400"}`}
              />
              {live ? "Live" : "Reconnecting"}
            </span>
            <label className="text-sm font-semibold text-aui-deep/75">
              TA name
              <input
                value={taName}
                onChange={(event) => setTaName(event.target.value)}
                className="field-glass ml-2 px-3 py-1.5 text-sm"
              />
            </label>
          </div>
        </div>
      </header>

      <main className="mx-auto grid max-w-6xl gap-6 px-6 py-8 lg:grid-cols-[340px_minmax(0,1fr)]">
        {error ? (
          <div className="lg:col-span-2 rounded-3xl border border-red-200 bg-red-50 p-4 text-sm text-red-700">
            {error}
          </div>
        ) : null}
        {toast ? (
          <div className="lg:col-span-2 rounded-3xl border border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-800">
            {toast}
          </div>
        ) : null}

        <section className="glass-panel p-4">
          <h2 className="mb-3 font-display text-lg font-bold">Open queue</h2>
          {status === "loading" && queue.length === 0 ? (
            <p className="text-sm text-slate-500">Loading...</p>
          ) : null}
          {queue.length === 0 && status === "success" ? (
            <p className="rounded-2xl bg-slate-50 px-3 py-6 text-center text-sm text-slate-500">
              No open requests. New student questions appear live.
            </p>
          ) : (
            <ul className="space-y-2">
              {queue.map((item) => (
                <li key={item.request.id}>
                  <button
                    type="button"
                    onClick={() => selectItem(item)}
                    className={`w-full rounded-2xl border px-3 py-3 text-left transition ${
                      selectedId === item.request.id
                        ? "border-aui-forest bg-aui-mist/80"
                        : "border-white/50 bg-white/35 hover:border-aui-forest/35"
                    }`}
                  >
                    <div className="mb-1 flex flex-wrap gap-2">
                      <span className="text-xs font-bold text-slate-500">
                        #{item.request.id}
                      </span>
                      {item.request.assigned_ta ? (
                        <span className="rounded-full bg-emerald-50 px-2 py-0.5 text-xs font-bold text-[var(--aui-forest-deep)] ring-1 ring-emerald-100">
                          {item.request.assigned_ta}
                        </span>
                      ) : null}
                      {item.learning_style ? (
                        <span className="rounded-full glass-chip !px-2 !py-0.5">
                          {item.learning_style.replaceAll("_", " ")}
                        </span>
                      ) : null}
                      {item.urgency ? (
                        <span className="rounded-full bg-white px-2 py-0.5 text-xs font-bold uppercase text-rose-700 ring-1 ring-rose-100">
                          {item.urgency}
                        </span>
                      ) : null}
                    </div>
                    <p className="line-clamp-3 text-sm font-medium text-slate-900">
                      {item.request.text}
                    </p>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </section>

        <section className="glass-panel p-6">
          {!selected ? (
            <p className="text-sm text-aui-deep/70">
              Select a request to review the AI teaching draft, adapt it to the
              student&apos;s learning style, then mark resolved. Resolutions go
              to the professor curation queue as <strong>pending review</strong>
              — they do not publish to the student KB agent until approved.
            </p>
          ) : (
            <div className="space-y-4">
              <div>
                <p className="text-sm font-semibold uppercase tracking-wide text-aui-forest">
                  Request #{selected.request.id}
                </p>
                <h2 className="font-display mt-1 text-xl font-bold text-aui-ink">
                  {selected.request.text}
                </h2>
                <p className="mt-2 text-sm text-slate-500">
                  {selected.request.student_name
                    ? `${selected.request.student_name} · `
                    : ""}
                  {selected.request.course || "Course TBD"} · Category:{" "}
                  {selected.request.oracle_category ||
                    selected.request.category ||
                    "n/a"}{" "}
                  · Style:{" "}
                  {(selected.learning_style || "unknown").replaceAll("_", " ")}
                </p>
              </div>

              <div className="grid gap-3 rounded-2xl border border-slate-200 bg-slate-50 p-4 md:grid-cols-3">
                <div>
                  <p className="text-xs font-bold uppercase tracking-wide text-sky-700">
                    Analyzer
                  </p>
                  <p className="mt-1 text-sm font-semibold text-slate-900">
                    {selected.request.oracle_difficulty || "MEDIUM"} ·{" "}
                    {selected.request.oracle_estimated_minutes || "?"} min
                  </p>
                  <p className="mt-1 text-xs text-slate-600">
                    {(selected.request.oracle_tags || []).join(", ") ||
                      "No tags"}
                  </p>
                </div>
                <div>
                  <p className="text-xs font-bold uppercase tracking-wide text-aui-forest">
                    Matcher
                  </p>
                  <p className="mt-1 text-sm font-semibold text-slate-900">
                    {selected.request.assigned_ta || "Unassigned"}
                  </p>
                  <p className="mt-1 text-xs text-slate-600">
                    Wait ~{selected.request.estimated_wait_minutes || "?"} min
                    {selected.request.alternative_ta
                      ? ` · Alt: ${selected.request.alternative_ta}`
                      : ""}
                  </p>
                </div>
                <div>
                  <p className="text-xs font-bold uppercase tracking-wide text-emerald-700">
                    Synthesizer
                  </p>
                  <p className="mt-1 text-sm text-slate-700">
                    {selected.request.triage?.synthesizer?.kb_insight ||
                      selected.request.oracle?.synthesizer?.kb_insight ||
                      selected.knowledge_entry?.drafter_backend ||
                      "Teaching draft ready"}
                  </p>
                </div>
              </div>

              {selected.request.code_snippet ? (
                <pre className="overflow-x-auto rounded-2xl bg-slate-950 p-4 text-xs text-emerald-100">
                  {selected.request.code_snippet}
                </pre>
              ) : null}

              <label className="block text-xs font-bold uppercase tracking-wide text-slate-500">
                Teaching approach (editable)
                <textarea
                  value={notes}
                  onChange={(event) => setNotes(event.target.value)}
                  rows={8}
                  className="field-glass mt-1 w-full px-3 py-2 text-sm"
                />
              </label>

              <label className="block text-xs font-bold uppercase tracking-wide text-aui-deep/60">
                Student hint (non-spoiler)
                <textarea
                  value={hint}
                  onChange={(event) => setHint(event.target.value)}
                  rows={3}
                  className="field-glass mt-1 w-full px-3 py-2 text-sm"
                />
              </label>

              <div className="flex flex-wrap gap-2">
                <button
                  type="button"
                  disabled={saving || notes.trim().length < 3}
                  onClick={() => handleResolve("resolved")}
                  className="btn-primary px-5 py-2.5 text-sm disabled:opacity-60"
                >
                  Mark resolved → curation queue
                </button>
                <button
                  type="button"
                  disabled={saving || notes.trim().length < 3}
                  onClick={() => handleResolve("needs_professor")}
                  className="btn-ghost px-5 py-2.5 text-sm disabled:opacity-60"
                >
                  Needs professor
                </button>
              </div>
            </div>
          )}
        </section>
      </main>
    </div>
  );
}
