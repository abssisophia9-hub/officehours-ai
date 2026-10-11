import { useCallback, useEffect, useRef, useState } from "react";
import { Navigate } from "react-router";
import { api, apiUpload } from "../api/client.js";
import { pageItems } from "../api/page.js";
import { useAuth } from "../auth/AuthContext.jsx";

const UPLOAD_BADGE = {
  pending: ["Pending", "bh-pill-amber"],
  approved: ["Approved", "bh-pill-green"],
  rejected: ["Rejected", "bh-pill-red"],
  partly_approved: ["Partly approved", "bh-pill-amber"],
};

function reviewGroups(entries) {
  const groups = new Map();
  for (const entry of entries) {
    const key = entry.upload_id || "drafts";
    if (!groups.has(key)) {
      groups.set(key, {
        key,
        uploadId: entry.upload_id || null,
        name: entry.source_filename || (entry.upload_id ? "Uploaded file" : "Other drafts"),
        entries: [],
      });
    }
    const group = groups.get(key);
    if (entry.source_filename) group.name = entry.source_filename;
    group.entries.push(entry);
  }
  for (const group of groups.values()) {
    group.entries.sort(
      (a, b) =>
        (a.page_number || 0) - (b.page_number || 0) ||
        (a.chunk_index || 0) - (b.chunk_index || 0),
    );
  }
  return [...groups.values()];
}

function formatUploadedAt(value) {
  if (!value) return "";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "";
  return date.toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    year: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

const ICONS = {
  doc: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
      <path d="M14 2v6h6" />
    </svg>
  ),
  clusters: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
      <circle cx="6" cy="6" r="3" />
      <circle cx="18" cy="8" r="3" />
      <circle cx="12" cy="18" r="3" />
    </svg>
  ),
  alert: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
      <path d="M10.3 3.9L1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0z" />
      <path d="M12 9v4M12 17h.01" />
    </svg>
  ),
  shield: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
      <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
    </svg>
  ),
};

export default function ProfessorWorkspace() {
  const { token, activeCourse } = useAuth();
  const [requests, setRequests] = useState([]);
  const [entries, setEntries] = useState([]);
  const [uploads, setUploads] = useState([]);
  const [commandCenter, setCommandCenter] = useState(null);
  const [reviewInsights, setReviewInsights] = useState(null);
  const [taLoad, setTaLoad] = useState(null);
  const [materialTitle, setMaterialTitle] = useState("");
  const [materialContent, setMaterialContent] = useState("");
  const [canvasInfo, setCanvasInfo] = useState(null);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);
  const [meetingDrafts, setMeetingDrafts] = useState({});
  const [insightFilter, setInsightFilter] = useState("all");
  const [openInsight, setOpenInsight] = useState(null);
  const [cohortNotes, setCohortNotes] = useState({});
  const [hitRate, setHitRate] = useState(null);
  const [goldCount, setGoldCount] = useState(0);
  const [retrainBusy, setRetrainBusy] = useState(false);
  const [retrainReport, setRetrainReport] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [uploadHint, setUploadHint] = useState("");
  const [uploadError, setUploadError] = useState("");
  const [uploadReceipts, setUploadReceipts] = useState([]);
  const [statusNote, setStatusNote] = useState("");
  const [focusUploadId, setFocusUploadId] = useState(null);
  const fileInputRef = useRef(null);

  function meetingDraft(clusterId) {
    return (
      meetingDrafts[clusterId] || {
        title: "",
        when: "",
        place: "",
        open: false,
      }
    );
  }

  function patchMeetingDraft(clusterId, patch) {
    setMeetingDrafts((prev) => ({
      ...prev,
      [clusterId]: {
        ...(prev[clusterId] || { title: "", when: "", place: "", open: false }),
        ...patch,
      },
    }));
  }

  const load = useCallback(async () => {
    try {
      const [req, kb, clusters, canvas, load, insights, rate, gold, files] = await Promise.all([
        api(`/requests/?course_id=${activeCourse.id}&limit=50`, { token }),
        api(`/knowledge/?status=pending_review&course_id=${activeCourse.id}&limit=200`, { token }),
        api(
          `/analytics/clusters?course_id=${activeCourse.id}&course=${encodeURIComponent(activeCourse.code)}`,
          { token },
        ),
        api(`/knowledge/canvas/status?course_id=${activeCourse.id}`, { token }),
        api(`/ta/load/?course_id=${activeCourse.id}`, { token }),
        api(`/analytics/review-insights?course_id=${activeCourse.id}`, { token }),
        api(`/analytics/kb-hit-rate?course_id=${activeCourse.id}`, { token }),
        api(`/analytics/gold-labels?course_id=${activeCourse.id}`, { token }),
        api(`/knowledge/uploads?course_id=${activeCourse.id}`, { token }),
      ]);
      setRequests(
        pageItems(req).filter((item) => !item.course || item.course === activeCourse.code),
      );
      setEntries(
        pageItems(kb).filter((item) => {
          if (item.course_id && item.course_id !== activeCourse.id) return false;
          const linked = pageItems(req).find((r) => r.id === item.source_request_id);
          return !linked?.course || linked.course === activeCourse.code;
        }),
      );
      setCommandCenter(clusters);
      setReviewInsights(insights);
      setCohortNotes((prev) => {
        const next = { ...prev };
        for (const topic of insights.topics || []) {
          if (next[topic.topic_key] === undefined) {
            next[topic.topic_key] = topic.next_cohort_note || "";
          }
        }
        return next;
      });
      setCanvasInfo(canvas);
      setTaLoad(load);
      setHitRate(rate);
      setGoldCount(Array.isArray(gold) ? gold.length : 0);
      setUploads(Array.isArray(files) ? files : []);
    } catch (err) {
      setError(err.message);
    }
  }, [token, activeCourse]);

  useEffect(() => {
    load();
  }, [load]);

  useEffect(() => {
    setUploadHint("");
    setUploadError("");
    setUploadReceipts([]);
    setStatusNote("");
    setFocusUploadId(null);
  }, [activeCourse?.id]);

  if (!activeCourse) return <Navigate to="/" replace />;
  if (activeCourse.role !== "professor") {
    return (
      <Navigate to={activeCourse.role === "ta" ? "/ta" : "/student"} replace />
    );
  }

  function showReview(uploadId) {
    setFocusUploadId(uploadId || null);
    window.setTimeout(() => {
      document.getElementById("knowledge")?.scrollIntoView({ behavior: "smooth", block: "start" });
    }, 30);
  }

  async function approve(entry) {
    setStatusNote("");
    setError("");
    const entryId = typeof entry === "object" ? entry.id : entry;
    const name =
      typeof entry === "object"
        ? entry.source_filename || "this draft"
        : "this draft";
    const page =
      typeof entry === "object" && entry.page_number != null
        ? `, page ${entry.page_number}`
        : "";
    try {
      await api(`/knowledge/${entryId}`, {
        method: "PATCH",
        token,
        body: { status: "approved" },
      });
      setStatusNote(`Approved a chunk from ${name}${page}. Students can see it now.`);
      await load();
    } catch (err) {
      setError(err.message);
    }
  }

  async function approveUpload(uploadId, name) {
    setStatusNote("");
    setError("");
    setUploadError("");
    try {
      const result = await api(`/knowledge/uploads/${uploadId}/approve`, {
        method: "POST",
        token,
      });
      setStatusNote(
        `Approved all ${result.approved_count} chunks from ${name}. Students can see them now.`,
      );
      setFocusUploadId(uploadId);
      await load();
    } catch (err) {
      setError(err.message);
    }
  }

  async function rejectUpload(upload) {
    setStatusNote("");
    setError("");
    setUploadError("");
    try {
      await api(`/knowledge/uploads/${upload.upload_id}/reject`, {
        method: "POST",
        token,
      });
      setStatusNote(`Rejected ${upload.filename}. Students can't see it.`);
      await load();
    } catch (err) {
      setUploadError(err.message || "Could not reject that file.");
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

  async function setInsightStatus(topic, reviewStatus) {
    setBusy(true);
    setError("");
    try {
      const updated = await api("/analytics/review-insights", {
        method: "PATCH",
        token,
        body: {
          course_id: activeCourse.id,
          topic_key: topic.topic_key,
          review_status: reviewStatus,
          next_cohort_note: cohortNotes[topic.topic_key] ?? topic.next_cohort_note ?? "",
        },
      });
      setReviewInsights(updated);
      setMessage(
        reviewStatus === "covered"
          ? `Marked ${topic.label} covered for this review`
          : reviewStatus === "emphasize"
            ? `Will emphasize ${topic.label} in review`
            : `Watching ${topic.label}`,
      );
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  async function saveCohortNote(topic) {
    setBusy(true);
    setError("");
    try {
      const updated = await api("/analytics/review-insights", {
        method: "PATCH",
        token,
        body: {
          course_id: activeCourse.id,
          topic_key: topic.topic_key,
          review_status: topic.review_status || "watch",
          next_cohort_note: (cohortNotes[topic.topic_key] || "").trim(),
        },
      });
      setReviewInsights(updated);
      setMessage(`Saved next-cohort note for ${topic.label}`);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  async function draftInsightFaq(topic) {
    setBusy(true);
    setError("");
    try {
      const entry = await api("/knowledge/from-insight", {
        method: "POST",
        token,
        body: {
          course_id: activeCourse.id,
          topic_key: topic.topic_key,
        },
      });
      setMessage(`FAQ draft #${entry.id} created from “${topic.label}” for the next cohort`);
      await load();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  async function approveGroupReview(cluster) {
    const draft = meetingDraft(cluster.cluster_id);
    const title = (draft.title || `Group review: ${cluster.title}`).trim();
    const when = (draft.when || "").trim();
    const place = (draft.place || "").trim();
    if (!when || !place) {
      setError("Add a shared time and place (or meeting link) before scheduling.");
      patchMeetingDraft(cluster.cluster_id, { open: true });
      return;
    }
    setBusy(true);
    setError("");
    try {
      const decision = await api("/actions/recommendations/", {
        method: "POST",
        token,
        body: {
          card_id: `group-cluster-${cluster.cluster_id}`,
          action_kind: "group_session",
          action_title: title,
          status: "approved",
          cluster_id: cluster.cluster_id,
          request_ids: cluster.request_ids,
          professor_note: cluster.suggestion_reason,
          meeting_title: title,
          meeting_when: when,
          meeting_place: place,
        },
      });
      setMessage(
        `Group meeting set for ${cluster.request_ids.length} asks · ${when} · ${place}`,
      );
      patchMeetingDraft(cluster.cluster_id, { open: false });
      void decision;
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
          auto_approve: false,
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

  async function uploadFiles(event) {
    event.preventDefault();
    const files = Array.from(fileInputRef.current?.files || []);
    if (files.length === 0) {
      setUploadHint("Choose a file first");
      setUploadError("");
      return;
    }
    setUploading(true);
    setUploadHint("");
    setUploadError("");
    setUploadReceipts([]);
    const receipts = [];
    try {
      for (const file of files) {
        const formData = new FormData();
        formData.append("course_id", String(activeCourse.id));
        formData.append("auto_approve", "false");
        formData.append("file", file);
        const result = await apiUpload("/knowledge/materials/upload", {
          token,
          formData,
        });
        receipts.push({
          filename: file.name,
          chunks: result.chunks_created,
          uploadId: result.upload_id,
        });
      }
      setUploadReceipts(receipts);
      if (fileInputRef.current) fileInputRef.current.value = "";
      await load();
    } catch (err) {
      setUploadReceipts(receipts);
      const reason = err?.message || "The upload failed. Try again.";
      setUploadError(
        receipts.length
          ? `${reason} The files above were uploaded.`
          : reason,
      );
      if (receipts.length) await load();
    } finally {
      setUploading(false);
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
          auto_approve: false,
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
    <div className="pd fade-up">
      <header className="pd-hero">
        <p className="pd-kicker">
          AUI · {activeCourse.code} · {activeCourse.title}
        </p>
        <h1 className="pd-title">What should you act on?</h1>
        <p className="pd-lead">
          <strong>Repeated Topics</strong> is the main action — see what students
          keep struggling with, then stamp FAQs so Study Agent stays trustworthy.
        </p>
        <p className="pd-alt">
          Knowledge Review and Canvas Materials ground the agent. Requests is the
          full ask list when you need detail.
        </p>
        <div className="pd-pulse">
          <span className="pd-chip">
            <strong>{requests.length}</strong> requests
          </span>
          <span className="pd-chip">
            <strong>{commandCenter?.clusters?.length || 0}</strong> topic clusters
          </span>
          {sensitiveCount > 0 ? (
            <span className="pd-chip pd-chip-hot">
              <strong>{sensitiveCount}</strong> sensitive
            </span>
          ) : (
            <span className="pd-chip">
              <strong>{anonCount}</strong> quiet asks
            </span>
          )}
          <span className="pd-chip">
            Agent hit-rate{" "}
            <strong>
              {hitRate && hitRate.total_asks
                ? `${Math.round((hitRate.overall_hit_rate || 0) * 100)}%`
                : "—"}
            </strong>
          </span>
        </div>
      </header>

      {error ? (
        <p className="clay-blob clay-blob-coral mb-4 block w-full px-4 py-2.5 text-sm font-semibold">
          {error}
        </p>
      ) : null}
      {message ? (
        <p className="clay-blob clay-blob-mint mb-4 block w-full px-4 py-2.5 text-sm font-semibold">
          {message}
        </p>
      ) : null}

      <section className="pd-panel mb-4">
        <p className="pd-panel-label">Agent quality</p>
        <h3>Gold labels &amp; hit-rate</h3>
        <p>
          {hitRate
            ? `${hitRate.total_hits || 0} hit · ${hitRate.total_misses || 0} refused · ${goldCount} TA gold labels`
            : "No student agent asks yet — stamp KB entries when repeats appear."}
        </p>
        <button
          type="button"
          className="btn-ghost mt-3 px-3 py-1.5 text-sm"
          disabled={retrainBusy}
          onClick={async () => {
            setRetrainBusy(true);
            try {
              const report = await api(
                `/analytics/retrain?course_id=${activeCourse.id}&apply_models=false`,
                { method: "POST", token },
              );
              setRetrainReport(report);
              setMessage(
                report.message ||
                  `Evaluated ${report.n_labels || 0} gold labels. Joblib not rewritten.`,
              );
            } catch (err) {
              setError(err.message);
            } finally {
              setRetrainBusy(false);
            }
          }}
        >
          {retrainBusy ? "Evaluating…" : "Evaluate gold now"}
        </button>
        {retrainReport?.analyzer?.accuracy != null ? (
          <p className="mt-2 text-sm text-[var(--theme-text-muted)]">
            Analyzer {Math.round(retrainReport.analyzer.accuracy * 100)}% on{" "}
            {retrainReport.n_labels} labels
          </p>
        ) : null}
      </section>

      <section id="ta-load" className="pd-panel mb-4 scroll-mt-6">
        <p className="pd-panel-label">Staffing</p>
        <h3>TA load (dual staffing)</h3>
        <p>
          {taLoad?.message ||
            "Typical AUI sections use up to two TAs. Matcher assigns primary + backup from this course."}
        </p>
        {(taLoad?.tas || []).length === 0 ? (
          <p className="td-empty">No TAs enrolled on this course yet.</p>
        ) : (
          <table className="bh-table mt-3">
            <thead>
              <tr>
                <th>TA</th>
                <th>Primary</th>
                <th>Backup</th>
                <th>Queue depth</th>
              </tr>
            </thead>
            <tbody>
              {taLoad.tas.map((ta) => (
                <tr key={ta.user_id}>
                  <td className="font-semibold">{ta.name}</td>
                  <td>{ta.primary_assignments}</td>
                  <td>{ta.backup_assignments}</td>
                  <td>{ta.queue_depth}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>

      <div className="pd-layout">
      <section id="clusters" className="pd-primary scroll-mt-6">
        <div className="pd-primary-head">
          <div>
            <h2>Repeated Topics</h2>
            <p className="pd-primary-copy">
              Use when the same struggle repeats — FAQ once, group-review, or keep
              sensitive cases private.
            </p>
          </div>
          <span className="pd-badge">Primary</span>
        </div>
        <p className="bh-card-note mt-3 pl-2">
          {commandCenter?.message ||
            "Similar questions are clustered so you can FAQ or group-review once."}
        </p>
        <ul className="mt-4 space-y-3">
          {(commandCenter?.clusters || []).map((cluster) => (
            <li
              key={cluster.cluster_id}
              className="rounded-xl border border-[#e3e8e4] bg-[#fafcfa] px-4 py-4"
            >
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <p className="text-xs font-semibold text-aui-deep/55">
                    Cluster {cluster.cluster_id} · {cluster.request_count} asks ·{" "}
                    {cluster.suggested_action.replaceAll("_", " ")}
                  </p>
                  <h3 className="font-display mt-1 text-lg font-semibold">
                    {cluster.title}
                  </h3>
                  <p className="mt-1 text-sm text-aui-deep/75">
                    {cluster.suggestion_reason}
                  </p>
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
                      onClick={() =>
                        patchMeetingDraft(cluster.cluster_id, {
                          open: !meetingDraft(cluster.cluster_id).open,
                          title:
                            meetingDraft(cluster.cluster_id).title ||
                            `Group review: ${cluster.title}`,
                        })
                      }
                    >
                      {meetingDraft(cluster.cluster_id).open
                        ? "Hide meeting form"
                        : "Propose group meeting"}
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
              {meetingDraft(cluster.cluster_id).open ? (
                <div className="mt-3 rounded-xl border border-aui-forest/20 bg-white p-3">
                  <p className="text-xs font-semibold text-aui-ink">
                    Shared meeting for {cluster.request_count} asks
                  </p>
                  <p className="mt-1 text-[11px] text-aui-deep/65">
                    Every student on this cluster will see the same time and place
                    on request status.
                  </p>
                  <label className="mt-2 block text-[11px] font-semibold uppercase tracking-wide text-aui-deep/55">
                    Title
                    <input
                      className="field-glass mt-1 w-full px-3 py-2 text-sm"
                      value={meetingDraft(cluster.cluster_id).title}
                      onChange={(event) =>
                        patchMeetingDraft(cluster.cluster_id, {
                          title: event.target.value,
                        })
                      }
                      placeholder={`Group review: ${cluster.title}`}
                    />
                  </label>
                  <div className="mt-2 grid gap-2 sm:grid-cols-2">
                    <label className="block text-[11px] font-semibold uppercase tracking-wide text-aui-deep/55">
                      When
                      <input
                        className="field-glass mt-1 w-full px-3 py-2 text-sm"
                        value={meetingDraft(cluster.cluster_id).when}
                        onChange={(event) =>
                          patchMeetingDraft(cluster.cluster_id, {
                            when: event.target.value,
                          })
                        }
                        placeholder="Thu 4:00–4:30 PM"
                      />
                    </label>
                    <label className="block text-[11px] font-semibold uppercase tracking-wide text-aui-deep/55">
                      Where / link
                      <input
                        className="field-glass mt-1 w-full px-3 py-2 text-sm"
                        value={meetingDraft(cluster.cluster_id).place}
                        onChange={(event) =>
                          patchMeetingDraft(cluster.cluster_id, {
                            place: event.target.value,
                          })
                        }
                        placeholder="Building 8 · Room 204 or Zoom link"
                      />
                    </label>
                  </div>
                  <button
                    type="button"
                    disabled={busy}
                    className="btn-primary mt-3 px-4 py-2 text-sm"
                    onClick={() => approveGroupReview(cluster)}
                  >
                    Schedule for all asks in cluster
                  </button>
                </div>
              ) : null}
              <ul className="mt-3 space-y-1 text-sm text-aui-deep/80">
                {cluster.sample_texts.map((sample) => (
                  <li key={sample} className="line-clamp-2">
                    • {sample}
                  </li>
                ))}
              </ul>
            </li>
          ))}
          {(commandCenter?.clusters || []).length === 0 ? (
            <p className="td-empty">No clustered repeats yet for this course.</p>
          ) : null}
        </ul>
      </section>

      <section id="review-insights" className="pd-secondary scroll-mt-6">
        <div className="bh-card-title">
          <h2>Chapter &amp; topic review insights</h2>
          <span className="bh-pill bh-pill-green">
            {(reviewInsights?.topics || []).filter(
              (topic) => topic.review_status === "emphasize" || topic.emphasize,
            ).length}{" "}
            to emphasize
          </span>
        </div>
        <p className="bh-card-note">
          {reviewInsights?.message ||
            "End-of-chapter board: Quiet ask questions plus Stuck Room chapters — what to review now and what to explain better for the next cohort."}
        </p>
        <p className="mt-2 text-xs text-aui-deep/65">
          Staff do not sit in Stuck Room. Mark a topic covered after review, or
          draft a FAQ so coming students get a tighter explanation.
        </p>
        <div className="mt-3 flex flex-wrap gap-2">
          {[
            { id: "all", label: "All" },
            { id: "chapter", label: "Stuck Room chapters" },
            { id: "ask_category", label: "Ask categories" },
            { id: "emphasize", label: "Emphasize" },
            { id: "covered", label: "Covered" },
          ].map((option) => (
            <button
              key={option.id}
              type="button"
              className={`btn-ghost px-3 py-1.5 text-xs ${
                insightFilter === option.id ? "border-aui-forest text-aui-forest" : ""
              }`}
              onClick={() => setInsightFilter(option.id)}
            >
              {option.label}
            </button>
          ))}
        </div>
        {(reviewInsights?.topics || []).length === 0 ? (
          <p className="mt-3 text-sm text-aui-deep/60">
            No signals yet for {activeCourse.code}. Once students Quiet ask or
            post in Stuck Room, topics land here.
          </p>
        ) : (
          <ul className="mt-4 space-y-3">
            {(reviewInsights.topics || [])
              .filter((topic) => {
                if (insightFilter === "all") return true;
                if (insightFilter === "chapter" || insightFilter === "ask_category") {
                  return topic.bucket === insightFilter;
                }
                return topic.review_status === insightFilter;
              })
              .map((topic) => (
                <li
                  key={topic.topic_key}
                  className="rounded-xl border border-[#e3e8e4] bg-[#fafcfa] px-4 py-4"
                >
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div>
                      <p className="text-xs font-semibold text-aui-deep/55">
                        {topic.bucket === "chapter"
                          ? "Stuck Room chapter"
                          : "Ask category"}{" "}
                        · {topic.office_hours_count} Quiet asks ·{" "}
                        {topic.stuck_post_count} stuck posts
                      </p>
                      <h3 className="font-display mt-1 text-lg font-semibold">
                        {topic.label}
                      </h3>
                      <p className="mt-1 text-sm text-aui-deep/75">{topic.review_hint}</p>
                      {topic.review_status === "covered" ? (
                        <span className="bh-pill bh-pill-green mt-2 inline-block">
                          covered
                        </span>
                      ) : topic.review_status === "emphasize" || topic.emphasize ? (
                        <span className="bh-pill bh-pill-amber mt-2 inline-block">
                          emphasize
                        </span>
                      ) : null}
                    </div>
                    <div className="flex flex-wrap gap-2">
                      <button
                        type="button"
                        className="btn-ghost px-3 py-1.5 text-xs"
                        onClick={() =>
                          setOpenInsight(
                            openInsight === topic.topic_key ? null : topic.topic_key,
                          )
                        }
                      >
                        {openInsight === topic.topic_key ? "Hide questions" : "Open question board"}
                      </button>
                      <button
                        type="button"
                        disabled={busy}
                        className="btn-ghost px-3 py-1.5 text-xs"
                        onClick={() => setInsightStatus(topic, "emphasize")}
                      >
                        Emphasize in review
                      </button>
                      <button
                        type="button"
                        disabled={busy}
                        className="btn-ghost px-3 py-1.5 text-xs"
                        onClick={() => setInsightStatus(topic, "covered")}
                      >
                        Mark covered
                      </button>
                      <button
                        type="button"
                        disabled={busy}
                        className="btn-primary px-3 py-1.5 text-xs"
                        onClick={() => draftInsightFaq(topic)}
                      >
                        Draft FAQ for next cohort
                      </button>
                    </div>
                  </div>
                  {openInsight === topic.topic_key ? (
                    <div className="mt-3 space-y-3 rounded-xl border border-aui-forest/20 bg-white p-3">
                      <p className="text-xs font-semibold uppercase tracking-wide text-aui-deep/55">
                        Asked questions
                      </p>
                      <ul className="space-y-1.5 text-sm text-aui-deep/85">
                        {(topic.questions || []).length === 0 ? (
                          <li>No stored questions for this topic.</li>
                        ) : (
                          (topic.questions || []).map((question, index) => (
                            <li key={`${question.source}-${question.request_id || question.stuck_post_id || index}`}>
                              <span className="bh-pill bh-pill-gray mr-1">
                                {question.source === "stuck_room" ? "Stuck Room" : "Quiet ask"}
                              </span>
                              {question.text}
                            </li>
                          ))
                        )}
                      </ul>
                      <label className="block text-[11px] font-semibold uppercase tracking-wide text-aui-deep/55">
                        Note for coming students / related chapters
                        <textarea
                          className="field-glass mt-1 min-h-16 w-full px-3 py-2 text-sm font-normal normal-case tracking-normal"
                          placeholder="What to explain differently next time…"
                          value={cohortNotes[topic.topic_key] ?? topic.next_cohort_note ?? ""}
                          onChange={(event) =>
                            setCohortNotes((prev) => ({
                              ...prev,
                              [topic.topic_key]: event.target.value,
                            }))
                          }
                        />
                      </label>
                      <button
                        type="button"
                        disabled={busy}
                        className="btn-ghost px-3 py-1.5 text-xs"
                        onClick={() => saveCohortNote(topic)}
                      >
                        Save note
                      </button>
                    </div>
                  ) : (
                    <ul className="mt-3 space-y-1 text-sm text-aui-deep/80">
                      {(topic.sample_questions || []).map((sample) => (
                        <li key={sample} className="line-clamp-2">
                          • {sample}
                        </li>
                      ))}
                    </ul>
                  )}
                </li>
              ))}
          </ul>
        )}
      </section>

      <section className="bh-card">
        <div className="bh-card-title">
          <h2>Urgent &amp; Sensitive</h2>
        </div>
        <ul className="mt-3 space-y-2">
          {(commandCenter?.escalations || []).map((item) => (
            <li
              key={item.request_id}
              className={`rounded-xl px-4 py-3 text-sm ${
                item.sensitive ? "bg-red-50" : "bg-orange-50"
              }`}
            >
              <p className="font-semibold">
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

      <section id="knowledge" className="pd-secondary scroll-mt-6">
        <div className="bh-card-title">
          <h2>Knowledge Review</h2>
          <span className="bh-pill bh-pill-amber">{entries.length} pending</span>
        </div>
        <p className="bh-card-note">
          Secondary to Repeated Topics — stamp drafts so Study Agent only answers
          from materials you trust. Nothing reaches students until you approve.
        </p>
        {statusNote ? (
          <p className="pd-upload-receipt mt-3">{statusNote}</p>
        ) : null}
        {entries.length === 0 ? (
          <p className="bh-card-note mt-3">No pending drafts for this course.</p>
        ) : (
          reviewGroups(entries)
            .sort((a, b) => {
              if (a.uploadId && a.uploadId === focusUploadId) return -1;
              if (b.uploadId && b.uploadId === focusUploadId) return 1;
              if (a.uploadId && !b.uploadId) return -1;
              if (!a.uploadId && b.uploadId) return 1;
              return a.name.localeCompare(b.name);
            })
            .map((group) => (
              <div
                key={group.key}
                className={`mt-4${group.uploadId === focusUploadId ? " pd-upload-focus" : ""}`}
              >
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <h3 className="font-display text-lg font-semibold">{group.name}</h3>
                  {group.uploadId ? (
                    <button
                      type="button"
                      className="btn-primary px-3.5 py-1.5 text-xs"
                      onClick={() => approveUpload(group.uploadId, group.name)}
                    >
                      Approve all {group.entries.length} chunks
                    </button>
                  ) : null}
                </div>
                <table className="bh-table">
                  <thead>
                    <tr>
                      <th>Page</th>
                      <th>Question</th>
                      <th>Draft</th>
                      <th></th>
                    </tr>
                  </thead>
                  <tbody>
                    {group.entries.map((entry) => (
                      <tr key={entry.id}>
                        <td className="whitespace-nowrap font-semibold">
                          {entry.page_number != null ? `p. ${entry.page_number}` : "—"}
                        </td>
                        <td className="max-w-[18rem]">
                          <span className="line-clamp-2 font-medium">
                            {entry.question_text}
                          </span>
                        </td>
                        <td className="max-w-[22rem]">
                          <span className="line-clamp-2 text-aui-deep/75">
                            {entry.answer_draft}
                          </span>
                        </td>
                        <td>
                          <button
                            type="button"
                            className="btn-ghost px-3.5 py-1.5 text-xs"
                            onClick={() => approve(entry)}
                          >
                            Approve
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ))
        )}
        {focusUploadId && !entries.some((entry) => entry.upload_id === focusUploadId) ? (
          <p className="bh-card-note mt-3">
            {uploads.find((item) => item.upload_id === focusUploadId)?.filename || "This file"}{" "}
            has nothing left to review.
          </p>
        ) : null}
      </section>

      <section id="materials" className="pd-secondary scroll-mt-6">
        <div className="bh-card-title">
          <h2>Canvas LMS → Course KB</h2>
          <span
            className={`bh-pill ${canvasInfo?.agent_ready ? "bh-pill-green" : "bh-pill-gray"}`}
          >
            agent {canvasInfo?.agent_ready ? "ready" : "pending"} ·{" "}
            {canvasInfo?.kb_chunks ?? 0} chunks
          </span>
        </div>
        <p className="bh-card-note">
          Sync pulls module slides/pages (including PDF/DOCX) into{" "}
          <strong>pending review</strong>. Stamp them below before the study
          agent can use them. Live mode uses{" "}
          <code className="text-xs">CANVAS_BASE_URL</code> +{" "}
          <code className="text-xs">CANVAS_ACCESS_TOKEN</code>; otherwise the
          local AUI mirror is used for demos.
        </p>
        <div className="soft-stat mt-4 text-sm">
          <p className="font-medium">
            Mode: <strong>{canvasInfo?.mode || "…"}</strong>
            {canvasInfo?.canvas_course_id
              ? ` · Canvas course ${canvasInfo.canvas_course_id}`
              : ""}
          </p>
          <p className="mt-1 text-aui-deep/65">{canvasInfo?.message}</p>
          {(canvasInfo?.available_files || []).length > 0 ? (
            <ul className="mt-2 list-disc space-y-1 pl-5 text-aui-deep/75">
              {canvasInfo.available_files.map((file) => (
                <li key={file.external_id}>
                  {file.module ? `${file.module} · ` : ""}
                  {file.title}
                </li>
              ))}
            </ul>
          ) : null}
        </div>
        <button
          type="button"
          disabled={busy}
          className="btn-primary mt-4 px-5 py-2.5 text-sm"
          onClick={syncCanvas}
        >
          {busy ? "Syncing…" : "Sync Canvas materials into KB"}
        </button>

        <h3 className="font-display mt-7 text-lg font-semibold">
          Upload files directly
        </h3>
        <p className="pd-upload-line">Students can't see this until you approve.</p>
        <p className="bh-card-note">
          PDF slides, DOCX/TXT/MD notes, or lecture-video transcripts
          (.vtt/.srt captions).
        </p>
        <form onSubmit={uploadFiles} className="mt-3 flex flex-wrap items-center gap-3">
          <input
            ref={fileInputRef}
            type="file"
            multiple
            accept=".pdf,.docx,.txt,.md,.vtt,.srt"
            className="field-glass max-w-md px-3 py-2 text-sm file:mr-3 file:rounded-md file:border-0 file:bg-aui-mist file:px-3 file:py-1.5 file:text-xs file:font-semibold file:text-aui-deep"
            onChange={() => {
              if (fileInputRef.current?.files?.length) setUploadHint("");
            }}
          />
          <button
            type="submit"
            disabled={uploading || busy}
            className="btn-primary px-5 py-2.5 text-sm"
          >
            {uploading ? "Uploading..." : "Upload to course KB"}
          </button>
        </form>
        {uploadHint ? <p className="pd-upload-error">{uploadHint}</p> : null}
        {uploadError ? <p className="pd-upload-error">{uploadError}</p> : null}
        {uploadReceipts.length > 0 ? (
          <div className="pd-upload-receipt">
            {uploadReceipts.map((receipt) => (
              <p key={receipt.uploadId || receipt.filename}>
                <strong>{receipt.filename}</strong>
                {" · "}
                {receipt.chunks} {receipt.chunks === 1 ? "chunk" : "chunks"}
                {" · Pending your approval"}
              </p>
            ))}
            <button
              type="button"
              className="btn-primary mt-2 px-3.5 py-1.5 text-xs"
              onClick={() => showReview(uploadReceipts[0]?.uploadId)}
            >
              Review these chunks
            </button>
          </div>
        ) : null}

        <h3 className="font-display mt-7 text-lg font-semibold">Uploaded files</h3>
        {statusNote ? <p className="pd-upload-receipt">{statusNote}</p> : null}
        {uploads.length === 0 ? (
          <p className="bh-card-note mt-2">No files uploaded for this course yet.</p>
        ) : (
          <table className="bh-table">
            <thead>
              <tr>
                <th>File</th>
                <th>Uploaded</th>
                <th>Chunks</th>
                <th>Status</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {uploads.map((upload) => {
                const [label, pill] = UPLOAD_BADGE[upload.status] || [
                  "Pending",
                  "bh-pill-amber",
                ];
                return (
                  <tr key={upload.upload_id}>
                    <td className="font-medium">{upload.filename}</td>
                    <td className="whitespace-nowrap">{formatUploadedAt(upload.uploaded_at)}</td>
                    <td>{upload.chunk_count}</td>
                    <td>
                      <span className={`bh-pill ${pill}`}>{label}</span>
                    </td>
                    <td>
                      <div className="flex flex-wrap gap-2">
                        {upload.status !== "approved" ? (
                          <button
                            type="button"
                            className="btn-primary px-3 py-1.5 text-xs"
                            onClick={() => approveUpload(upload.upload_id, upload.filename)}
                          >
                            Approve all
                          </button>
                        ) : null}
                        <button
                          type="button"
                          className="btn-ghost px-3 py-1.5 text-xs"
                          onClick={() => showReview(upload.upload_id)}
                        >
                          Review chunks
                        </button>
                        {upload.status !== "rejected" ? (
                          <button
                            type="button"
                            className="btn-ghost px-3 py-1.5 text-xs"
                            onClick={() => rejectUpload(upload)}
                          >
                            Reject
                          </button>
                        ) : null}
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}

        <h3 className="font-display mt-7 text-lg font-semibold">
          Or paste slides / notes
        </h3>
        <form onSubmit={ingestMaterials} className="mt-3 space-y-3">
          <input
            className="field-glass w-full px-4 py-2.5 text-sm"
            placeholder="Material title (e.g. Week 4 — Hashing slides)"
            value={materialTitle}
            onChange={(event) => setMaterialTitle(event.target.value)}
            required
          />
          <textarea
            className="field-glass min-h-32 w-full px-4 py-2.5 text-sm"
            placeholder="Paste slide text / notes…"
            value={materialContent}
            onChange={(event) => setMaterialContent(event.target.value)}
            required
            minLength={20}
          />
          <button type="submit" disabled={busy} className="btn-ghost px-5 py-2.5 text-sm">
            {busy ? "Ingesting…" : "Add pasted material to course KB"}
          </button>
        </form>
      </section>

      <section id="requests" className="pd-secondary scroll-mt-6">
        <div className="bh-card-title">
          <h2>Recent Requests</h2>
        </div>
        {requests.length === 0 ? (
          <p className="bh-card-note mt-3">No requests yet for this course.</p>
        ) : (
          <table className="bh-table">
            <thead>
              <tr>
                <th>#</th>
                <th>Question</th>
                <th>From</th>
                <th>Help</th>
                <th>Category</th>
                <th>Flags</th>
              </tr>
            </thead>
            <tbody>
              {requests.slice(0, 12).map((request) => (
                <tr key={request.id}>
                  <td className="font-semibold">#{request.id}</td>
                  <td className="max-w-[26rem]">
                    <span className="line-clamp-2">{request.text}</span>
                  </td>
                  <td>
                    {request.anonymous
                      ? "Anonymous"
                      : request.student_name || request.student_id || "—"}
                  </td>
                  <td>
                    {request.help_mode === "face_to_face"
                      ? "In person"
                      : request.help_mode === "online_meeting"
                        ? "Online"
                        : "Message"}
                  </td>
                  <td>{request.category || "n/a"}</td>
                  <td>
                    {request.sensitive ? (
                      <span className="bh-pill bh-pill-red">sensitive</span>
                    ) : request.anonymous ? (
                      <span className="bh-pill bh-pill-gray">anonymous</span>
                    ) : (
                      "—"
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>
      </div>
    </div>
  );
}
