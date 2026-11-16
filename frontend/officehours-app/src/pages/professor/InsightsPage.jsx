import { useEffect, useState } from "react";
import { api } from "../../api/client.js";
import { useAuth } from "../../auth/AuthContext.jsx";
import { useProfessorData } from "./ProfessorData.jsx";

function meetingSeed() {
  return { title: "", when: "", place: "", open: false };
}

export default function InsightsPage() {
  const { token, activeCourse } = useAuth();
  const {
    commandCenter,
    reviewInsights,
    setReviewInsights,
    hitRate,
    goldCount,
    ready,
    error,
    setError,
    reload,
  } = useProfessorData();
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [meetingDrafts, setMeetingDrafts] = useState({});
  const [insightFilter, setInsightFilter] = useState("all");
  const [openInsight, setOpenInsight] = useState(null);
  const [cohortNotes, setCohortNotes] = useState({});
  const [qualityOpen, setQualityOpen] = useState(false);
  const [retrainBusy, setRetrainBusy] = useState(false);
  const [checkedLabels, setCheckedLabels] = useState(null);

  useEffect(() => {
    setMeetingDrafts({});
    setInsightFilter("all");
    setOpenInsight(null);
    setCohortNotes({});
    setQualityOpen(false);
    setCheckedLabels(null);
    setMessage("");
  }, [activeCourse?.id]);

  useEffect(() => {
    setCohortNotes((prev) => {
      const next = { ...prev };
      for (const topic of reviewInsights?.topics || []) {
        if (next[topic.topic_key] === undefined) {
          next[topic.topic_key] = topic.next_cohort_note || "";
        }
      }
      return next;
    });
  }, [reviewInsights]);

  function meetingDraft(clusterId) {
    return meetingDrafts[clusterId] || meetingSeed();
  }

  function patchMeetingDraft(clusterId, patch) {
    setMeetingDrafts((prev) => ({
      ...prev,
      [clusterId]: { ...(prev[clusterId] || meetingSeed()), ...patch },
    }));
  }

  const clusters = commandCenter?.clusters || [];
  const topics = reviewInsights?.topics || [];
  const visibleTopics = topics.filter((topic) => {
    if (insightFilter === "all") return true;
    if (insightFilter === "chapter" || insightFilter === "ask_category") {
      return topic.bucket === insightFilter;
    }
    return topic.review_status === insightFilter;
  });
  const asks = hitRate?.total_asks || 0;
  const answered = hitRate?.total_hits || 0;

  async function draftFaq(cluster) {
    setBusy(true);
    setError("");
    try {
      await api("/knowledge/from-cluster", {
        method: "POST",
        token,
        body: {
          cluster_id: cluster.cluster_id,
          course_id: activeCourse.id,
          course: activeCourse.code,
        },
      });
      setMessage("Suggested answer saved. The study agent does not use these.");
      await reload();
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
          ? `Marked ${topic.label} covered.`
          : reviewStatus === "emphasize"
            ? `Will emphasize ${topic.label} in review.`
            : `Watching ${topic.label}.`,
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
      setMessage(`Saved a note for ${topic.label}.`);
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
      await api("/knowledge/from-insight", {
        method: "POST",
        token,
        body: { course_id: activeCourse.id, topic_key: topic.topic_key },
      });
      setMessage("Suggested answer saved. The study agent does not use these.");
      await reload();
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
      setError("Add a shared time and place before scheduling.");
      patchMeetingDraft(cluster.cluster_id, { open: true });
      return;
    }
    setBusy(true);
    setError("");
    try {
      await api("/actions/recommendations/", {
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
      setMessage(`Group meeting set for ${cluster.request_ids.length} asks. ${when}. ${place}.`);
      patchMeetingDraft(cluster.cluster_id, { open: false });
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  async function evaluateGold() {
    setRetrainBusy(true);
    setError("");
    try {
      const report = await api(
        `/analytics/retrain?course_id=${activeCourse.id}&apply_models=false`,
        { method: "POST", token },
      );
      setCheckedLabels(report.n_labels || 0);
      setMessage(
        report.n_labels
          ? `Checked ${report.n_labels} labeled answers.`
          : "No labeled answers to check yet.",
      );
    } catch (err) {
      setError(err.message);
    } finally {
      setRetrainBusy(false);
    }
  }

  return (
    <div className="pf-page">
      <header className="pf-head">
        <h1>Insights</h1>
      </header>
      {error ? (
        <p className="pf-error" role="alert">
          {error}
        </p>
      ) : null}
      {message ? (
        <p className="pf-note" role="status">
          {message}
        </p>
      ) : null}

      <section className="pf-block" aria-label="Repeated topics">
        <h2>Repeated topics</h2>
        {!ready ? <p className="pf-line">Loading insights…</p> : null}
        {ready && clusters.length === 0 ? <p className="pf-line">No repeated topics yet.</p> : null}
        {clusters.length > 0 ? (
          <ul className="pf-ask-list">
            {clusters.map((cluster) => (
              <li key={cluster.cluster_id}>
                <p className="pf-meta">
                  {cluster.request_count} asks · {cluster.suggested_action.replaceAll("_", " ")}
                </p>
                <h3 className="pf-topic">{cluster.title}</h3>
                <p className="pf-line">{cluster.suggestion_reason}</p>
                {cluster.sensitive_count > 0 ? (
                  <p className="pf-line">
                    {cluster.sensitive_count} sensitive. Keep these private.
                  </p>
                ) : null}
                <div className="pf-actions">
                  {cluster.suggested_action === "group_session" ? (
                    <button
                      type="button"
                      className="btn-ghost pf-btn"
                      disabled={busy}
                      onClick={() =>
                        patchMeetingDraft(cluster.cluster_id, {
                          open: !meetingDraft(cluster.cluster_id).open,
                          title:
                            meetingDraft(cluster.cluster_id).title ||
                            `Group review: ${cluster.title}`,
                        })
                      }
                    >
                      {meetingDraft(cluster.cluster_id).open ? "Hide meeting form" : "Set a group meeting"}
                    </button>
                  ) : null}
                  <button
                    type="button"
                    className="btn-ghost pf-btn"
                    disabled={busy}
                    onClick={() => draftFaq(cluster)}
                  >
                    Draft a suggested answer
                  </button>
                </div>
                {meetingDraft(cluster.cluster_id).open ? (
                  <div className="pf-panel">
                    <p>Shared meeting for {cluster.request_count} asks. Every student on this topic sees the same time and place.</p>
                    <label className="pf-label">
                      Title
                      <input
                        className="field-glass"
                        value={meetingDraft(cluster.cluster_id).title}
                        onChange={(event) =>
                          patchMeetingDraft(cluster.cluster_id, { title: event.target.value })
                        }
                      />
                    </label>
                    <label className="pf-label">
                      When
                      <input
                        className="field-glass"
                        value={meetingDraft(cluster.cluster_id).when}
                        onChange={(event) =>
                          patchMeetingDraft(cluster.cluster_id, { when: event.target.value })
                        }
                        placeholder="Thu 4:00–4:30 PM"
                      />
                    </label>
                    <label className="pf-label">
                      Where
                      <input
                        className="field-glass"
                        value={meetingDraft(cluster.cluster_id).place}
                        onChange={(event) =>
                          patchMeetingDraft(cluster.cluster_id, { place: event.target.value })
                        }
                        placeholder="Building 8, room 204, or a meeting link"
                      />
                    </label>
                    <button
                      type="button"
                      className="btn-ghost pf-btn"
                      disabled={busy}
                      onClick={() => approveGroupReview(cluster)}
                    >
                      Schedule for these asks
                    </button>
                  </div>
                ) : null}
                <ul className="pf-plain-list">
                  {cluster.sample_texts.map((sample) => (
                    <li key={sample}>{sample}</li>
                  ))}
                </ul>
              </li>
            ))}
          </ul>
        ) : null}
      </section>

      <section className="pf-block" aria-label="Chapter and topic review">
        <h2>Chapter and topic review</h2>
        {ready && topics.length === 0 ? <p className="pf-line">No chapter notes yet.</p> : null}
        {topics.length > 0 ? (
          <>
            <div className="pf-filters">
              {[
                { id: "all", label: "All" },
                { id: "chapter", label: "Chapters" },
                { id: "ask_category", label: "Ask topics" },
                { id: "emphasize", label: "Emphasize" },
                { id: "covered", label: "Covered" },
              ].map((option) => (
                <button
                  key={option.id}
                  type="button"
                  className={`btn-ghost pf-btn${insightFilter === option.id ? " pf-filter-on" : ""}`}
                  aria-pressed={insightFilter === option.id}
                  onClick={() => setInsightFilter(option.id)}
                >
                  {option.label}
                </button>
              ))}
            </div>
            {visibleTopics.length === 0 ? <p className="pf-line">Nothing in this filter.</p> : null}
            <ul className="pf-ask-list">
              {visibleTopics.map((topic) => (
                <li key={topic.topic_key}>
                  <p className="pf-meta">
                    {topic.bucket === "chapter" ? "Chapter" : "Ask topic"} · {topic.office_hours_count}{" "}
                    asks · {topic.stuck_post_count} room posts
                  </p>
                  <h3 className="pf-topic">{topic.label}</h3>
                  <p className="pf-line">{topic.review_hint}</p>
                  {topic.review_status === "covered" ? (
                    <p className="pf-line">Covered</p>
                  ) : topic.review_status === "emphasize" || topic.emphasize ? (
                    <p className="pf-line">Emphasize</p>
                  ) : null}
                  <div className="pf-actions">
                    <button
                      type="button"
                      className="btn-ghost pf-btn"
                      onClick={() =>
                        setOpenInsight(openInsight === topic.topic_key ? null : topic.topic_key)
                      }
                    >
                      {openInsight === topic.topic_key ? "Hide questions" : "Show questions"}
                    </button>
                    <button
                      type="button"
                      className="btn-ghost pf-btn"
                      disabled={busy}
                      onClick={() => setInsightStatus(topic, "emphasize")}
                    >
                      Emphasize in review
                    </button>
                    <button
                      type="button"
                      className="btn-ghost pf-btn"
                      disabled={busy}
                      onClick={() => setInsightStatus(topic, "covered")}
                    >
                      Mark covered
                    </button>
                    <button
                      type="button"
                      className="btn-ghost pf-btn"
                      disabled={busy}
                      onClick={() => draftInsightFaq(topic)}
                    >
                      Draft a suggested answer
                    </button>
                  </div>
                  {openInsight === topic.topic_key ? (
                    <div className="pf-panel">
                      <ul className="pf-plain-list">
                        {(topic.questions || []).length === 0 ? <li>No stored questions for this topic.</li> : null}
                        {(topic.questions || []).map((question, index) => (
                          <li key={`${question.source}-${question.request_id || question.stuck_post_id || index}`}>
                            {question.source === "stuck_room" ? "Room. " : "Ask. "}
                            {question.text}
                          </li>
                        ))}
                      </ul>
                      <label className="pf-label">
                        Note for the next group
                        <textarea
                          className="field-glass"
                          rows={3}
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
                        className="btn-ghost pf-btn"
                        disabled={busy}
                        onClick={() => saveCohortNote(topic)}
                      >
                        Save note
                      </button>
                    </div>
                  ) : (
                    <ul className="pf-plain-list">
                      {(topic.sample_questions || []).map((sample) => (
                        <li key={sample}>{sample}</li>
                      ))}
                    </ul>
                  )}
                </li>
              ))}
            </ul>
          </>
        ) : null}
      </section>

      <section className="pf-block" aria-label="Answer quality check">
        <button
          type="button"
          className="pf-quiet"
          aria-expanded={qualityOpen}
          onClick={() => setQualityOpen((open) => !open)}
        >
          Answer quality check
        </button>
        {qualityOpen ? (
          <div className="pf-panel">
            <p className="pf-line">
              {asks > 0
                ? `Answered ${answered} of ${asks} questions.`
                : "No student questions yet."}{" "}
              {goldCount === 1
                ? "1 labeled answer for checking."
                : `${goldCount} labeled answers for checking.`}
            </p>
            {checkedLabels != null ? (
              <p className="pf-line">
                {checkedLabels === 1
                  ? "Checked 1 labeled answer."
                  : `Checked ${checkedLabels} labeled answers.`}
              </p>
            ) : null}
            <button type="button" className="btn-ghost pf-btn" disabled={retrainBusy} onClick={evaluateGold}>
              {retrainBusy ? "Checking…" : "Run quality check"}
            </button>
          </div>
        ) : null}
      </section>
    </div>
  );
}
