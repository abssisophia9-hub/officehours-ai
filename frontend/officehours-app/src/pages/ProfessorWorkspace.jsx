import { useCallback, useEffect, useState } from "react";
import { Navigate } from "react-router-dom";
import { api } from "../api/client.js";
import { useAuth } from "../auth/AuthContext.jsx";

export default function ProfessorWorkspace() {
  const { token, activeCourse } = useAuth();
  const [requests, setRequests] = useState([]);
  const [entries, setEntries] = useState([]);
  const [commandCenter, setCommandCenter] = useState(null);
  const [materialTitle, setMaterialTitle] = useState("");
  const [materialContent, setMaterialContent] = useState("");
  const [canvasInfo, setCanvasInfo] = useState(null);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    try {
      const [req, kb, clusters, canvas] = await Promise.all([
        api("/requests/", { token }),
        api(`/knowledge/?status=pending_review&course_id=${activeCourse.id}`, { token }),
        api(
          `/analytics/clusters?course_id=${activeCourse.id}&course=${encodeURIComponent(activeCourse.code)}`,
          { token },
        ),
        api(`/knowledge/canvas/status?course_id=${activeCourse.id}`, { token }),
      ]);
      setRequests(
        req.filter((item) => !item.course || item.course === activeCourse.code),
      );
      setEntries(
        kb.filter((item) => {
          if (item.course_id && item.course_id !== activeCourse.id) return false;
          const linked = req.find((r) => r.id === item.source_request_id);
          return !linked?.course || linked.course === activeCourse.code;
        }),
      );
      setCommandCenter(clusters);
      setCanvasInfo(canvas);
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

  async function draftFaq(cluster) {
    setBusy(true);
    setError("");
    try {
      const entry = await api("/knowledge/from-cluster", {
        method: "POST",
        token,
        body: {
          cluster_id: cluster.cluster_id,
          course_id: activeCourse.id,
          course: activeCourse.code,
        },
      });
      setMessage(`FAQ draft #${entry.id} created for cluster ${cluster.cluster_id}`);
      await load();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  async function approveGroupReview(cluster) {
    setBusy(true);
    setError("");
    try {
      const decision = await api("/actions/recommendations/", {
        method: "POST",
        token,
        body: {
          card_id: `group-cluster-${cluster.cluster_id}`,
          action_kind: "group_session",
          action_title: `Group review: ${cluster.title}`,
          status: "approved",
          cluster_id: cluster.cluster_id,
          request_ids: cluster.request_ids,
          professor_note: cluster.suggestion_reason,
        },
      });
      setMessage(
        decision.action_plan?.title
          ? `Scheduled plan: ${decision.action_plan.title}`
          : "Group review recommendation saved",
      );
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  async function ingestMaterials(event) {
    event.preventDefault();
    setBusy(true);
    setError("");
    setMessage("");
    try {
      const result = await api("/knowledge/materials", {
        method: "POST",
        token,
        body: {
          title: materialTitle,
          content: materialContent,
          course_id: activeCourse.id,
          course: activeCourse.code,
          source: "slides",
          auto_approve: true,
        },
      });
      setMessage(result.message);
      setMaterialTitle("");
      setMaterialContent("");
      await load();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  async function syncCanvas() {
    setBusy(true);
    setError("");
    setMessage("");
    try {
      const result = await api("/knowledge/canvas/sync", {
        method: "POST",
        token,
        body: {
          course_id: activeCourse.id,
          auto_approve: true,
        },
      });
      setMessage(result.message);
      await load();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  const sensitiveCount = requests.filter((item) => item.sensitive).length;
  const anonCount = requests.filter((item) => item.anonymous).length;

  return (
    <div className="fade-up space-y-6">
      <section className="glass-panel p-6">
        <p className="glass-chip mb-3">Professor · {activeCourse.code}</p>
        <h1 className="font-display max-w-[18ch] text-3xl font-semibold sm:text-4xl">
          Office-hours command center
        </h1>
        <p className="mt-2 max-w-2xl font-medium text-aui-deep/70">
          Group repeats, draft FAQs, flag sensitive cases, and ground the KB agent
          in your course materials.
        </p>
        {error ? (
          <p className="clay-blob clay-blob-coral mt-3 block w-full px-4 py-2 text-sm font-semibold">
            {error}
          </p>
        ) : null}
        {message ? (
          <p className="clay-blob clay-blob-mint mt-3 block w-full px-4 py-2 text-sm font-semibold">
            {message}
          </p>
        ) : null}
        <div className="mt-6 grid gap-3 sm:grid-cols-4">
          <article className="soft-stat">
            <p className="text-sm font-medium text-aui-deep/60">Requests</p>
            <p className="font-display text-3xl font-semibold">{requests.length}</p>
          </article>
          <article className="soft-stat">
            <p className="text-sm font-medium text-aui-deep/60">Topic clusters</p>
            <p className="font-display text-3xl font-semibold">
              {commandCenter?.clusters?.length || 0}
            </p>
          </article>
          <article className="soft-stat">
            <p className="text-sm font-medium text-aui-deep/60">Sensitive flags</p>
            <p className="font-display text-3xl font-semibold">{sensitiveCount}</p>
          </article>
          <article className="soft-stat">
            <p className="text-sm font-medium text-aui-deep/60">Anonymous asks</p>
            <p className="font-display text-3xl font-semibold">{anonCount}</p>
          </article>
        </div>
      </section>

      <section className="glass-panel p-6">
        <h2 className="font-display text-2xl font-semibold">Repeated topics</h2>
        <p className="mt-1 text-sm text-aui-deep/65">
          {commandCenter?.message ||
            "Similar questions are clustered so you can FAQ or group-review once."}
        </p>
        <ul className="mt-4 space-y-3">
          {(commandCenter?.clusters || []).map((cluster) => (
            <li
              key={cluster.cluster_id}
              className="rounded-2xl border border-white/60 bg-white/45 px-4 py-4"
            >
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <p className="text-xs font-bold uppercase tracking-wide text-aui-deep/55">
                    Cluster {cluster.cluster_id} · {cluster.request_count} asks ·{" "}
                    {cluster.suggested_action.replaceAll("_", " ")}
                  </p>
                  <h3 className="font-display mt-1 text-xl font-semibold">{cluster.title}</h3>
                  <p className="mt-1 text-sm text-aui-deep/75">{cluster.suggestion_reason}</p>
                  {cluster.sensitive_count > 0 ? (
                    <p className="mt-2 text-sm font-semibold text-red-700">
                      {cluster.sensitive_count} sensitive — keep private
                    </p>
                  ) : null}
                </div>
                <div className="flex flex-wrap gap-2">
                  {cluster.suggested_action === "group_session" ? (
                    <button
                      type="button"
                      disabled={busy}
                      className="btn-primary px-4 py-2 text-sm"
                      onClick={() => approveGroupReview(cluster)}
                    >
                      Plan group review
                    </button>
                  ) : null}
                  <button
                    type="button"
                    disabled={busy}
                    className="btn-ghost px-4 py-2 text-sm"
                    onClick={() => draftFaq(cluster)}
                  >
                    Draft FAQ for KB
                  </button>
                </div>
              </div>
              <ul className="mt-3 space-y-1 text-sm text-aui-deep/80">
                {cluster.sample_texts.map((text) => (
                  <li key={text} className="line-clamp-2">
                    • {text}
                  </li>
                ))}
              </ul>
            </li>
          ))}
          {(commandCenter?.clusters || []).length === 0 ? (
            <p className="text-sm text-aui-deep/60">
              No clustered repeats yet for this course.
            </p>
          ) : null}
        </ul>
      </section>

      <section className="glass-panel p-6">
        <h2 className="font-display text-2xl font-semibold">Urgent & sensitive</h2>
        <ul className="mt-4 space-y-2">
          {(commandCenter?.escalations || []).map((item) => (
            <li
              key={item.request_id}
              className={`rounded-2xl px-4 py-3 text-sm ${
                item.sensitive ? "bg-red-50/90" : "bg-orange-50/80"
              }`}
            >
              <p className="font-bold">
                #{item.request_id}
                {item.sensitive ? " · private" : ""} · {item.urgency || "n/a"}
              </p>
              <p className="mt-1 text-aui-deep/80">{item.text}</p>
              <p className="mt-1 text-xs text-aui-deep/60">{item.reason}</p>
            </li>
          ))}
          {(commandCenter?.escalations || []).length === 0 ? (
            <p className="text-sm text-aui-deep/60">No escalations right now.</p>
          ) : null}
        </ul>
      </section>

      <section className="glass-panel p-6">
        <h2 className="font-display text-2xl font-semibold">
          Canvas LMS → course KB
        </h2>
        <p className="mt-1 text-sm text-aui-deep/65">
          Sync pulls slide/pages from this course&apos;s Canvas link into the same
          approved KB the student agent searches. Live mode uses{" "}
          <code className="text-xs">CANVAS_BASE_URL</code> +{" "}
          <code className="text-xs">CANVAS_ACCESS_TOKEN</code>; otherwise the local
          AUI Canvas mirror is used for demos.
        </p>
        <div className="soft-stat mt-4 text-sm font-medium">
          <p>
            Mode: <strong>{canvasInfo?.mode || "…"}</strong>
            {canvasInfo?.canvas_course_id
              ? ` · Canvas course ${canvasInfo.canvas_course_id}`
              : ""}
          </p>
          <p className="mt-1 text-aui-deep/65">{canvasInfo?.message}</p>
          {(canvasInfo?.available_files || []).length > 0 ? (
            <ul className="mt-2 list-disc space-y-1 pl-5 text-aui-deep/75">
              {canvasInfo.available_files.map((file) => (
                <li key={file.external_id}>{file.title}</li>
              ))}
            </ul>
          ) : null}
        </div>
        <button
          type="button"
          disabled={busy}
          className="btn-primary mt-4 px-5 py-3 text-sm"
          onClick={syncCanvas}
        >
          {busy ? "Syncing…" : "Sync Canvas materials into KB"}
        </button>

        <h3 className="font-display mt-8 text-xl font-semibold">
          Or paste slides / notes
        </h3>
        <p className="mt-1 text-sm text-aui-deep/65">
          Manual ingest for the same course-scoped KB (useful when a file is not
          in Canvas yet).
        </p>
        <form onSubmit={ingestMaterials} className="mt-4 space-y-3">
          <input
            className="field-glass w-full px-4 py-3"
            placeholder="Material title (e.g. Week 4 — Hashing slides)"
            value={materialTitle}
            onChange={(event) => setMaterialTitle(event.target.value)}
            required
          />
          <textarea
            className="field-glass min-h-40 w-full px-4 py-3 text-sm"
            placeholder="Paste slide text / notes…"
            value={materialContent}
            onChange={(event) => setMaterialContent(event.target.value)}
            required
            minLength={20}
          />
          <button type="submit" disabled={busy} className="btn-ghost px-5 py-3 text-sm">
            {busy ? "Ingesting…" : "Add pasted material to course KB"}
          </button>
        </form>
      </section>

      <section className="glass-panel p-6">
        <h2 className="font-display text-2xl font-semibold">Pending knowledge curation</h2>
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
        <h2 className="font-display text-2xl font-semibold">Recent requests</h2>
        <ul className="mt-4 space-y-2">
          {requests.slice(0, 12).map((request) => (
            <li key={request.id} className="rounded-2xl bg-white/45 px-4 py-3 text-sm">
              <span className="font-bold">#{request.id}</span> ·{" "}
              {request.anonymous ? "Anonymous" : request.assigned_ta || "Unassigned"} ·{" "}
              {request.category || "n/a"}
              {request.sensitive ? " · sensitive" : ""}
              <p className="mt-1 text-aui-deep/80">{request.text}</p>
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}
