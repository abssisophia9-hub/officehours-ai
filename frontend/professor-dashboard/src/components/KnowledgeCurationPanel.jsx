import { useEffect, useMemo, useState } from "react";
import {
  fetchKnowledgeEntries,
  updateKnowledgeEntry,
} from "../api/knowledge.js";

const FILTERS = [
  { id: "pending_review", label: "Pending review" },
  { id: "approved", label: "Approved" },
  { id: "rejected", label: "Rejected" },
  { id: "all", label: "All" },
];

export default function KnowledgeCurationPanel() {
  const [entries, setEntries] = useState([]);
  const [filter, setFilter] = useState("pending_review");
  const [status, setStatus] = useState("loading");
  const [error, setError] = useState("");
  const [drafts, setDrafts] = useState({});
  const [savingId, setSavingId] = useState(null);

  async function loadEntries() {
    setStatus("loading");
    setError("");
    try {
      const data = await fetchKnowledgeEntries(
        filter === "all" ? undefined : filter,
      );
      setEntries(data);
      setDrafts(
        Object.fromEntries(
          data.map((entry) => [
            entry.id,
            {
              answer_draft: entry.answer_draft,
              student_hint: entry.student_hint,
              professor_note: entry.professor_note || "",
            },
          ]),
        ),
      );
      setStatus("success");
    } catch (loadError) {
      setStatus("error");
      setError(loadError.message);
    }
  }

  useEffect(() => {
    loadEntries();
  }, [filter]);

  const counts = useMemo(() => {
    const pending = entries.filter((e) => e.status === "pending_review").length;
    return { pending, total: entries.length };
  }, [entries]);

  async function saveEntry(entryId, nextStatus) {
    setSavingId(entryId);
    setError("");
    try {
      const draft = drafts[entryId] || {};
      await updateKnowledgeEntry(entryId, {
        status: nextStatus,
        answer_draft: draft.answer_draft,
        student_hint: draft.student_hint,
        professor_note: draft.professor_note,
      });
      await loadEntries();
    } catch (saveError) {
      setError(saveError.message);
    } finally {
      setSavingId(null);
    }
  }

  function updateDraft(entryId, field, value) {
    setDrafts((current) => ({
      ...current,
      [entryId]: {
        ...current[entryId],
        [field]: value,
      },
    }));
  }

  return (
    <section className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
      <div className="mb-5 flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="text-sm font-semibold uppercase tracking-wide text-amber-700">
            Knowledge base
          </p>
          <h2 className="text-xl font-bold text-slate-950">
            Curation queue
          </h2>
          <p className="mt-1 text-sm text-slate-500">
            Every student question seeds a draft. Only approved entries power
            the student KB agent.
          </p>
        </div>
        <p className="text-sm font-semibold text-slate-600">
          {filter === "pending_review"
            ? `${counts.pending} awaiting review`
            : `${counts.total} shown`}
        </p>
      </div>

      <div className="mb-5 flex flex-wrap gap-2">
        {FILTERS.map((item) => (
          <button
            key={item.id}
            type="button"
            onClick={() => setFilter(item.id)}
            className={`rounded-full px-4 py-2 text-sm font-bold ${
              filter === item.id
                ? "bg-slate-950 text-white"
                : "bg-slate-100 text-slate-700 hover:bg-slate-200"
            }`}
          >
            {item.label}
          </button>
        ))}
      </div>

      {error ? (
        <p className="mb-4 rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {error}
        </p>
      ) : null}

      {status === "loading" && entries.length === 0 ? (
        <p className="text-sm text-slate-500">Loading knowledge drafts...</p>
      ) : null}

      {entries.length === 0 && status === "success" ? (
        <p className="rounded-2xl bg-slate-50 px-4 py-6 text-center text-sm text-slate-500">
          No knowledge entries in this filter yet.
        </p>
      ) : (
        <div className="space-y-4">
          {entries.map((entry) => {
            const draft = drafts[entry.id] || {};
            return (
              <article
                key={entry.id}
                className="rounded-2xl border border-slate-200 bg-slate-50/80 p-4"
              >
                <div className="mb-3 flex flex-wrap items-center gap-2">
                  <span className="rounded-full bg-white px-3 py-1 text-xs font-bold uppercase tracking-wide text-slate-600 ring-1 ring-slate-200">
                    {entry.status.replace("_", " ")}
                  </span>
                  {entry.category ? (
                    <span className="rounded-full bg-indigo-50 px-3 py-1 text-xs font-bold text-indigo-700">
                      {entry.category}
                    </span>
                  ) : null}
                  {entry.difficulty ? (
                    <span className="rounded-full bg-amber-50 px-3 py-1 text-xs font-bold text-amber-800">
                      {entry.difficulty}
                    </span>
                  ) : null}
                  <span className="text-xs text-slate-400">
                    Request #{entry.source_request_id}
                  </span>
                </div>

                <p className="text-sm font-semibold text-slate-900">
                  {entry.question_text}
                </p>

                <label className="mt-3 block text-xs font-bold uppercase tracking-wide text-slate-500">
                  Teaching approach (TA / professor)
                  <textarea
                    value={draft.answer_draft || ""}
                    onChange={(event) =>
                      updateDraft(entry.id, "answer_draft", event.target.value)
                    }
                    rows={4}
                    className="mt-1 w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm text-slate-800"
                  />
                </label>

                <label className="mt-3 block text-xs font-bold uppercase tracking-wide text-slate-500">
                  Student hint (non-spoiler)
                  <textarea
                    value={draft.student_hint || ""}
                    onChange={(event) =>
                      updateDraft(entry.id, "student_hint", event.target.value)
                    }
                    rows={2}
                    className="mt-1 w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm text-slate-800"
                  />
                </label>

                <label className="mt-3 block text-xs font-bold uppercase tracking-wide text-slate-500">
                  Professor note
                  <input
                    type="text"
                    value={draft.professor_note || ""}
                    onChange={(event) =>
                      updateDraft(
                        entry.id,
                        "professor_note",
                        event.target.value,
                      )
                    }
                    className="mt-1 w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm text-slate-800"
                    placeholder="Optional curation note"
                  />
                </label>

                <div className="mt-4 flex flex-wrap gap-2">
                  <button
                    type="button"
                    disabled={savingId === entry.id}
                    onClick={() => saveEntry(entry.id, "approved")}
                    className="rounded-full bg-emerald-600 px-4 py-2 text-sm font-bold text-white hover:bg-emerald-700 disabled:opacity-60"
                  >
                    Approve for student agent
                  </button>
                  <button
                    type="button"
                    disabled={savingId === entry.id}
                    onClick={() => saveEntry(entry.id, "pending_review")}
                    className="rounded-full bg-slate-900 px-4 py-2 text-sm font-bold text-white hover:bg-slate-800 disabled:opacity-60"
                  >
                    Save edits
                  </button>
                  <button
                    type="button"
                    disabled={savingId === entry.id}
                    onClick={() => saveEntry(entry.id, "rejected")}
                    className="rounded-full border border-red-200 bg-white px-4 py-2 text-sm font-bold text-red-700 hover:bg-red-50 disabled:opacity-60"
                  >
                    Reject
                  </button>
                </div>
              </article>
            );
          })}
        </div>
      )}
    </section>
  );
}
