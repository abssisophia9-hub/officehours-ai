import { useCallback, useEffect, useState } from "react";
import { Navigate } from "react-router-dom";
import { api } from "../api/client.js";
import { useAuth } from "../auth/AuthContext.jsx";
import FollowUpThread from "../components/FollowUpThread.jsx";

export default function ProfessorWorkspace() {
  const { token, user, activeCourse } = useAuth();
  const [requests, setRequests] = useState([]);
  const [entries, setEntries] = useState([]);
  const [selectedId, setSelectedId] = useState(null);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  const load = useCallback(async () => {
    try {
      const [req, kb] = await Promise.all([
        api("/requests/", { token }),
        api("/knowledge/?status=pending_review", { token }),
      ]);
      setRequests(
        req.filter((item) => !item.course || item.course === activeCourse.code),
      );
      setEntries(
        kb.filter((item) => {
          const linked = req.find((r) => r.id === item.source_request_id);
          return !linked?.course || linked.course === activeCourse.code;
        }),
      );
    } catch (err) {
      setError(err.message);
    }
  }, [token, activeCourse]);

  useEffect(() => {
    load();
  }, [load]);

  if (!activeCourse) return <Navigate to="/" replace />;
  if (activeCourse.role !== "professor") {
    return (
      <Navigate to={activeCourse.role === "ta" ? "/ta" : "/student"} replace />
    );
  }

  async function approve(entryId) {
    setMessage("");
    try {
      await api(`/knowledge/${entryId}`, {
        method: "PATCH",
        token,
        body: { status: "approved" },
      });
      setMessage(`Approved knowledge entry #${entryId}`);
      await load();
    } catch (err) {
      setError(err.message);
    }
  }

  return (
    <div className="space-y-6">
      <section className="glass-panel p-6">
        <p className="glass-chip mb-3">Professor · {activeCourse.code}</p>
        <h1 className="font-display text-3xl font-bold">{activeCourse.title}</h1>
        <p className="mt-2 text-aui-deep/70">
          Course-scoped triage and knowledge curation. Approve drafts before
          students can retrieve them.
        </p>
        {error ? <p className="mt-3 text-sm text-red-700">{error}</p> : null}
        {message ? <p className="mt-3 text-sm text-emerald-700">{message}</p> : null}
        <div className="mt-6 grid gap-4 sm:grid-cols-3">
          <article className="rounded-2xl bg-emerald-50/80 p-4">
            <p className="text-sm text-aui-deep/70">Requests</p>
            <p className="font-display text-3xl font-bold">{requests.length}</p>
          </article>
          <article className="rounded-2xl bg-sky-50/80 p-4">
            <p className="text-sm text-aui-deep/70">Pending KB</p>
            <p className="font-display text-3xl font-bold">{entries.length}</p>
          </article>
          <article className="rounded-2xl bg-orange-50/80 p-4">
            <p className="text-sm text-aui-deep/70">Assigned TAs</p>
            <p className="font-display text-3xl font-bold">
              {new Set(requests.map((r) => r.assigned_ta).filter(Boolean)).size}
            </p>
          </article>
        </div>
      </section>

      <section className="glass-panel p-6">
        <h2 className="font-display text-2xl font-bold">Pending knowledge curation</h2>
        <ul className="mt-4 space-y-3">
          {entries.map((entry) => (
            <li
              key={entry.id}
              className="rounded-2xl border border-white/60 bg-white/45 px-4 py-3"
            >
              <p className="text-sm font-bold text-aui-deep/60">#{entry.id}</p>
              <p className="mt-1 font-medium">{entry.question_text}</p>
              <p className="mt-2 line-clamp-3 text-sm text-aui-deep/75">
                {entry.answer_draft}
              </p>
              <button
                type="button"
                className="btn-primary mt-3 px-4 py-2 text-sm"
                onClick={() => approve(entry.id)}
              >
                Approve for student KB
              </button>
            </li>
          ))}
          {entries.length === 0 ? (
            <p className="text-sm text-aui-deep/60">No pending drafts for this course.</p>
          ) : null}
        </ul>
      </section>

      <section className="glass-panel p-6">
        <h2 className="font-display text-2xl font-bold">Recent requests</h2>
        <ul className="mt-4 space-y-2">
          {requests.slice(0, 12).map((request) => (
            <li key={request.id}>
              <button
                type="button"
                className={`w-full rounded-2xl px-4 py-3 text-left text-sm ${
                  selectedId === request.id
                    ? "bg-aui-mist/80 ring-1 ring-aui-forest/30"
                    : "bg-white/45"
                }`}
                onClick={() => setSelectedId(request.id)}
              >
                <span className="font-bold">#{request.id}</span> ·{" "}
                {request.assigned_ta || "Unassigned"} · {request.category || "n/a"}
                {(request.followups || []).length > 0 ? (
                  <span className="ml-2 text-xs font-bold text-aui-forest">
                    · {(request.followups || []).length} follow-up
                    {(request.followups || []).length === 1 ? "" : "s"}
                  </span>
                ) : null}
                <p className="mt-1 text-aui-deep/80">{request.text}</p>
              </button>
            </li>
          ))}
        </ul>
        {selectedId ? (
          <div className="mt-5 border-t border-white/50 pt-5">
            <FollowUpThread
              requestId={selectedId}
              followups={
                requests.find((item) => item.id === selectedId)?.followups || []
              }
              token={token}
              authorRole="professor"
              authorName={user.display_name}
              onUpdated={load}
            />
          </div>
        ) : null}
      </section>
    </div>
  );
}
