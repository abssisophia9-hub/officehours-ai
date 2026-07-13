import { useCallback, useEffect, useState } from "react";
import { Navigate } from "react-router-dom";
import { api } from "../api/client.js";
import { useAuth } from "../auth/AuthContext.jsx";

export default function TaWorkspace() {
  const { token, user, activeCourse } = useAuth();
  const [queue, setQueue] = useState([]);
  const [selectedId, setSelectedId] = useState(null);
  const [notes, setNotes] = useState("");
  const [hint, setHint] = useState("");
  const [error, setError] = useState("");
  const [toast, setToast] = useState("");

  const loadQueue = useCallback(async () => {
    try {
      const data = await api("/ta/queue/", { token });
      const filtered = data.filter((item) => {
        const course = item.request.course;
        return !course || course === activeCourse.code;
      });
      setQueue(filtered);
    } catch (err) {
      setError(err.message);
    }
  }, [token, activeCourse]);

  useEffect(() => {
    loadQueue();
    const id = setInterval(loadQueue, 8000);
    return () => clearInterval(id);
  }, [loadQueue]);

  if (!activeCourse) return <Navigate to="/" replace />;
  if (activeCourse.role !== "ta") {
    return (
      <Navigate
        to={activeCourse.role === "professor" ? "/professor" : "/student"}
        replace
      />
    );
  }

  const selected = queue.find((item) => item.request.id === selectedId) || null;

  async function resolve(status) {
    if (!selected) return;
    setError("");
    try {
      const result = await api("/ta/resolve/", {
        method: "POST",
        token,
        body: {
          request_id: selected.request.id,
          ta_name: user.display_name,
          teaching_notes: notes,
          student_hint: hint || null,
          resolution_status: status,
        },
      });
      setToast(result.message || "Saved for professor review");
      setSelectedId(null);
      setNotes("");
      setHint("");
      await loadQueue();
    } catch (err) {
      setError(err.message);
    }
  }

  return (
    <div className="grid gap-6 lg:grid-cols-[320px_minmax(0,1fr)]">
      <section className="glass-panel p-4">
        <p className="glass-chip mb-3">TA · {activeCourse.code}</p>
        <h1 className="font-display text-2xl font-bold">Open queue</h1>
        {error ? <p className="mt-2 text-sm text-red-700">{error}</p> : null}
        {toast ? <p className="mt-2 text-sm text-emerald-700">{toast}</p> : null}
        <ul className="mt-4 space-y-2">
          {queue.map((item) => (
            <li key={item.request.id}>
              <button
                type="button"
                className={`w-full rounded-2xl border px-3 py-3 text-left ${
                  selectedId === item.request.id
                    ? "border-aui-forest bg-aui-mist/80"
                    : "border-white/50 bg-white/40"
                }`}
                onClick={() => {
                  setSelectedId(item.request.id);
                  setNotes(item.knowledge_entry?.answer_draft || "");
                  setHint(item.knowledge_entry?.student_hint || "");
                }}
              >
                <p className="text-xs font-bold text-aui-deep/60">#{item.request.id}</p>
                <p className="line-clamp-3 text-sm font-medium">{item.request.text}</p>
              </button>
            </li>
          ))}
          {queue.length === 0 ? (
            <p className="rounded-2xl bg-white/40 px-3 py-6 text-center text-sm text-aui-deep/60">
              No open requests for this course.
            </p>
          ) : null}
        </ul>
      </section>

      <section className="glass-panel p-6">
        {!selected ? (
          <p className="text-aui-deep/70">Select a request to edit the teaching draft.</p>
        ) : (
          <div className="space-y-4">
            <h2 className="font-display text-2xl font-bold">{selected.request.text}</h2>
            <textarea
              className="field-glass min-h-48 w-full px-3 py-2 text-sm"
              value={notes}
              onChange={(event) => setNotes(event.target.value)}
            />
            <textarea
              className="field-glass min-h-24 w-full px-3 py-2 text-sm"
              value={hint}
              onChange={(event) => setHint(event.target.value)}
              placeholder="Student hint"
            />
            <div className="flex flex-wrap gap-2">
              <button type="button" className="btn-primary px-4 py-2 text-sm" onClick={() => resolve("resolved")}>
                Mark resolved → professor curation
              </button>
              <button type="button" className="btn-ghost px-4 py-2 text-sm" onClick={() => resolve("needs_professor")}>
                Needs professor
              </button>
            </div>
          </div>
        )}
      </section>
    </div>
  );
}
