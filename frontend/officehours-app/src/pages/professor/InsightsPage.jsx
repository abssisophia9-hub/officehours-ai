import { useCallback, useEffect, useMemo, useState } from "react";
import { Link } from "react-router";
import { api } from "../../api/client.js";
import { useAuth } from "../../auth/AuthContext.jsx";

const RANGES = [
  { id: "7d", label: "7 days" },
  { id: "30d", label: "30 days" },
  { id: "term", label: "Term" },
];

/** Ask Triage taxonomy keys (Request.category), not syllabus chapters. */
const TRIAGE_CATEGORIES = new Set([
  "conceptual_question",
  "exam_logistics",
  "retake_request",
  "accessibility_accommodation",
  "grading_dispute",
  "emotional_stress",
  "project_submission",
  "office_hours_access",
  "academic_integrity",
  "uncategorized",
]);

const TOPIC_PREVIEW = 6;

function trendMark(trend) {
  if (trend === "up") return "↑";
  if (trend === "down") return "↓";
  return "→";
}

function topicLabel(name) {
  return String(name || "topic").replaceAll("_", " ");
}

function isTriageCategory(name) {
  return TRIAGE_CATEGORIES.has(String(name || "").trim().toLowerCase());
}

/** Local calendar label from ISO day (YYYY-MM-DD) → "Nov 9". */
function formatDayLabel(isoDay) {
  const raw = String(isoDay || "");
  const parts = raw.split("-").map((part) => Number(part));
  if (parts.length !== 3 || parts.some((n) => !Number.isFinite(n))) return raw;
  const [year, month, day] = parts;
  const date = new Date(year, month - 1, day);
  return date.toLocaleDateString(undefined, { month: "short", day: "numeric" });
}

/** Human age for overdue rows: 1770m → 29h ago, 3720m → 2.6d ago. */
function humanAge(minutes) {
  const m = Math.max(0, Math.round(Number(minutes) || 0));
  if (m < 60) return `${m}m ago`;
  if (m < 48 * 60) return `${Math.floor(m / 60)}h ago`;
  const days = Math.floor((m / (60 * 24)) * 10) / 10;
  return `${days}d ago`;
}

function buildCallout(missingMaterial, overdueAsks) {
  if (!missingMaterial.length && !overdueAsks.length) return null;
  const top = missingMaterial[0];
  const parts = [];
  if (top) {
    parts.push(
      `Students are heavily stuck on '${topicLabel(top.topic)}' (${top.count} asks with no approved material)`,
    );
  }
  if (overdueAsks.length) {
    parts.push(
      `${overdueAsks.length} ask${overdueAsks.length === 1 ? " is" : "s are"} overdue`,
    );
  }
  if (!parts.length) return null;
  if (parts.length === 1) return `${parts[0]}.`;
  return `${parts[0]} and ${parts[1]}.`;
}

export default function InsightsPage() {
  const { token, activeCourse } = useAuth();
  const [range, setRange] = useState("7d");
  const [topic, setTopic] = useState("");
  const [monitor, setMonitor] = useState(null);
  const [selectedTopic, setSelectedTopic] = useState(null);
  const [topicAsks, setTopicAsks] = useState([]);
  const [ready, setReady] = useState(false);
  const [error, setError] = useState("");
  const [loadingAsks, setLoadingAsks] = useState(false);
  const [showAllTopics, setShowAllTopics] = useState(false);

  const load = useCallback(async () => {
    if (!token || !activeCourse || activeCourse.role !== "professor") return;
    setReady(false);
    setError("");
    try {
      const q = new URLSearchParams({
        course_id: String(activeCourse.id),
        range,
      });
      if (topic) q.set("topic", topic);
      const body = await api(`/analytics/struggle-monitor?${q}`, { token });
      setMonitor(body);
      setSelectedTopic(null);
      setTopicAsks([]);
      setShowAllTopics(false);
    } catch (err) {
      setError(err.message || "Could not load Insights.");
      setMonitor(null);
    } finally {
      setReady(true);
    }
  }, [token, activeCourse, range, topic]);

  useEffect(() => {
    load();
  }, [load]);

  async function openTopic(bar) {
    if (!token || !activeCourse) return;
    setSelectedTopic(bar.topic);
    setLoadingAsks(true);
    setError("");
    try {
      const q = new URLSearchParams({
        course_id: String(activeCourse.id),
        range,
        topic: bar.topic,
      });
      const rows = await api(`/analytics/struggle-monitor/asks?${q}`, { token });
      setTopicAsks(Array.isArray(rows) ? rows : []);
    } catch (err) {
      setError(err.message || "Could not load asks for that topic.");
      setTopicAsks([]);
    } finally {
      setLoadingAsks(false);
    }
  }

  const days = monitor?.asks_per_day || [];
  const maxDay = Math.max(1, ...days.map((d) => Number(d.count) || 0));
  const allTopics = monitor?.topics || [];

  const courseTopics = useMemo(
    () => allTopics.filter((bar) => !isTriageCategory(bar.topic)),
    [allTopics],
  );
  const askCategories = useMemo(
    () => allTopics.filter((bar) => isTriageCategory(bar.topic)),
    [allTopics],
  );

  const topicBars = courseTopics;
  const maxTopic = Math.max(1, ...topicBars.map((t) => Number(t.count) || 0));
  const visibleTopics = showAllTopics
    ? topicBars
    : topicBars.slice(0, TOPIC_PREVIEW);
  const hiddenTopicCount = Math.max(0, topicBars.length - TOPIC_PREVIEW);

  const missingMaterial = useMemo(() => {
    const fromNeeds = (monitor?.needs_you || []).filter(
      (item) => item.kind === "add_material",
    );
    const mapped = fromNeeds.length
      ? fromNeeds.map((item) => ({
          topic: item.topic || item.title,
          count:
            item.ask_count ||
            Number((item.detail || "").match(/(\d+)/)?.[1]) ||
            0,
        }))
      : topicBars
          .filter((bar) => Number(bar.count) >= 3 && !bar.has_approved_material)
          .map((bar) => ({ topic: bar.topic, count: bar.count }));
    return mapped.filter((row) => !isTriageCategory(row.topic));
  }, [monitor, topicBars]);

  const missingAmongBars = useMemo(
    () => topicBars.filter((bar) => !bar.has_approved_material),
    [topicBars],
  );
  const majorityMissing =
    topicBars.length > 0 && missingAmongBars.length > topicBars.length / 2;
  const badgeTopics = useMemo(() => {
    const ranked = [...missingAmongBars].sort(
      (a, b) => Number(b.count) - Number(a.count),
    );
    return new Set(ranked.slice(0, 3).map((bar) => bar.topic));
  }, [missingAmongBars]);

  const overdueAsks = useMemo(() => {
    return (monitor?.needs_you || [])
      .filter((item) => item.kind === "overdue_ask" || item.kind === "urgent_ask")
      .filter(
        (item) =>
          (Number(item.age_minutes) || 0) >= 24 * 60 || item.kind === "overdue_ask",
      )
      .sort((a, b) => (Number(b.age_minutes) || 0) - (Number(a.age_minutes) || 0));
  }, [monitor]);

  const callout = useMemo(
    () => buildCallout(missingMaterial, overdueAsks),
    [missingMaterial, overdueAsks],
  );

  const displayKpis = useMemo(() => {
    const rows = monitor?.kpis || [];
    const topCourse = topicBars[0];
    if (!topCourse) return rows;
    return rows.map((kpi) => {
      if (kpi.key !== "top_topic") return kpi;
      if (!isTriageCategory(String(kpi.value || "").replaceAll(" ", "_"))) {
        return kpi;
      }
      return {
        ...kpi,
        value: topicLabel(topCourse.topic),
        delta_label: `${topCourse.count} asks in range`,
      };
    });
  }, [monitor, topicBars]);

  const waitingKpi = displayKpis.find((kpi) => kpi.key === "waiting");
  const waitingCount = Number(waitingKpi?.value) || 0;

  const courseTopicOptions = useMemo(() => {
    const opts = monitor?.topic_options || [];
    const course = opts.filter((name) => !isTriageCategory(name));
    return course.length ? course : opts;
  }, [monitor]);

  // apple-design: Purpose; Simplicity — not minimalism; Feedback; Familiarity;
  // Craft; Response — kill latency; Reduced motion & accessibility;
  // Typography — optical sizing, tracking, leading (8).

  return (
    <div className="pf-page pf-monitor pf-radar">
      <header className="pf-head pf-desk-head">
        <div>
          <p className="pf-kicker">Student Struggle Radar</p>
          <h1>Insights</h1>
          <p className="pf-line pf-monitor-lead">
            What students are stuck on, whether it is getting worse, and what
            needs you now.
          </p>
        </div>
      </header>

      <p className="pf-monitor-a11y">
        Applied: Purpose; Simplicity — not minimalism; Feedback; Familiarity;
        Craft; Response — kill latency; Reduced motion &amp; accessibility;
        Typography — optical sizing, tracking, leading (8).
      </p>

      <div className="pf-radar-shell">
        <div className="pf-monitor-controls" role="group" aria-label="Range and topic">
          <div className="pf-monitor-ranges" role="tablist" aria-label="Time range">
            {RANGES.map((item) => (
              <button
                key={item.id}
                type="button"
                role="tab"
                aria-selected={range === item.id}
                className={`pf-monitor-chip${range === item.id ? " is-on" : ""}`}
                onClick={() => setRange(item.id)}
              >
                {item.label}
              </button>
            ))}
          </div>
          <label className="pf-monitor-topic">
            <span>Course topic</span>
            <select
              value={topic}
              onChange={(event) => setTopic(event.target.value)}
              aria-label="Filter by course topic"
            >
              <option value="">All topics</option>
              {courseTopicOptions.map((name) => (
                <option key={name} value={name}>
                  {topicLabel(name)}
                </option>
              ))}
            </select>
          </label>
        </div>

        {error ? (
          <p className="pf-error" role="alert">
            {error}
          </p>
        ) : null}
        {!ready ? <p className="pf-line">Loading insights…</p> : null}

        {ready && monitor ? (
          <>
            {callout ? (
              <section className="pf-radar-callout" aria-label="Top struggle">
                <p className="pf-radar-callout-text">{callout}</p>
                <div className="pf-radar-callout-actions">
                  {missingMaterial.length ? (
                    <Link className="pf-radar-cta" to="/professor">
                      Add Material
                    </Link>
                  ) : null}
                  {overdueAsks.length ? (
                    <Link className="pf-radar-cta pf-radar-cta-ghost" to="/professor/asks">
                      Review on Desk
                    </Link>
                  ) : null}
                </div>
              </section>
            ) : null}

            <section className="pf-radar-kpis" aria-label="Key measures">
              {displayKpis.map((kpi) => {
                const warn =
                  kpi.key === "waiting" && waitingCount > 0 ? " is-warn" : "";
                return (
                  <article key={kpi.key} className={`pf-monitor-kpi pf-radar-kpi${warn}`}>
                    <p className="pf-monitor-kpi-label">{kpi.label}</p>
                    <p className="pf-monitor-kpi-value">{kpi.value}</p>
                    {kpi.delta_label ? (
                      <p className="pf-monitor-kpi-delta">{kpi.delta_label}</p>
                    ) : null}
                    {kpi.missing ? (
                      <p className="pf-monitor-missing">{kpi.missing}</p>
                    ) : null}
                  </article>
                );
              })}
            </section>

            <section className="pf-radar-bento" aria-label="Charts">
              <div className="pf-radar-col pf-radar-col-left">
                <div className="pf-radar-panel">
                  <div className="pf-radar-panel-head">
                    <h2>Asks per day</h2>
                    <p className="pf-radar-panel-note">
                      {!monitor.enough_for_trend
                        ? monitor.message || "Not enough asks yet for a trend"
                        : monitor.message}
                    </p>
                  </div>
                  <div
                    className="pf-monitor-chart"
                    role="img"
                    aria-label="Asks per day chart"
                  >
                    <div className="pf-monitor-chart-plot">
                      {days.map((point) => {
                        const count = Number(point.count) || 0;
                        const height = Math.max(
                          count > 0 ? 8 : 0,
                          Math.round((count / maxDay) * 100),
                        );
                        const dayLabel = formatDayLabel(point.day);
                        return (
                          <div key={point.day} className="pf-monitor-bar-col">
                            <span className="pf-monitor-bar-count">{count}</span>
                            <span
                              className="pf-monitor-bar"
                              style={{ height: `${height}%` }}
                              title={`${dayLabel}: ${count} asks`}
                            />
                            <span className="pf-monitor-bar-day">{dayLabel}</span>
                          </div>
                        );
                      })}
                    </div>
                    <p className="pf-monitor-axis">
                      Asks per day · local date · count
                    </p>
                  </div>
                </div>

                <section className="pf-radar-needs" aria-label="Needs you">
                  <div className="pf-radar-panel-head pf-radar-needs-head">
                    <h2>Needs you</h2>
                  </div>
                  {!missingMaterial.length && !overdueAsks.length ? (
                    <p className="pf-line">
                      Nothing urgent in this range. Keep watching the topic bars.
                    </p>
                  ) : (
                    <div className="pf-radar-needs-grid">
                      <div className="pf-radar-needs-col">
                        <h3>Missing material</h3>
                        {!missingMaterial.length ? (
                          <p className="pf-radar-needs-empty">No gaps in this range.</p>
                        ) : (
                          <ul className="pf-radar-mat-list">
                            {missingMaterial.map((row) => (
                              <li key={row.topic}>
                                <div>
                                  <strong>{topicLabel(row.topic)}</strong>
                                  <span>{row.count} asks</span>
                                </div>
                                <Link className="pf-radar-add" to="/professor">
                                  + Add
                                </Link>
                              </li>
                            ))}
                          </ul>
                        )}
                      </div>
                      <div className="pf-radar-needs-col">
                        <div className="pf-radar-overdue-head">
                          <h3>Overdue asks</h3>
                          {overdueAsks.length ? (
                            <Link className="pf-radar-desk-link" to="/professor/asks">
                              Open Your desk →
                            </Link>
                          ) : null}
                        </div>
                        {!overdueAsks.length ? (
                          <p className="pf-radar-needs-empty">No asks over 24h.</p>
                        ) : (
                          <ul className="pf-radar-overdue-list">
                            {overdueAsks.map((item) => (
                              <li
                                key={
                                  item.request_id || `${item.topic}-${item.detail}`
                                }
                              >
                                <p className="pf-radar-overdue-title">{item.title}</p>
                                <div className="pf-radar-overdue-meta">
                                  <time>{humanAge(item.age_minutes)}</time>
                                  {item.topic ? (
                                    <span className="pf-radar-topic-tag">
                                      {topicLabel(item.topic)}
                                    </span>
                                  ) : null}
                                </div>
                              </li>
                            ))}
                          </ul>
                        )}
                      </div>
                    </div>
                  )}
                </section>
              </div>

              <div className="pf-radar-col pf-radar-col-right">
                <div className="pf-radar-panel">
                  <div className="pf-radar-panel-head">
                    <h2>Course topics</h2>
                    <p className="pf-radar-panel-note">
                      Sorted by ask count. Click a row to list asks.
                      {askCategories.length
                        ? " Ask Triage categories are listed separately below."
                        : ""}
                    </p>
                  </div>

                  {majorityMissing ? (
                    <div className="pf-radar-mat-summary" role="status">
                      <p>
                        {missingAmongBars.length} of {topicBars.length} topics
                        have no approved material.
                      </p>
                      <Link className="pf-radar-cta" to="/professor">
                        Add material
                      </Link>
                    </div>
                  ) : null}

                  {topicBars.length === 0 ? (
                    <p className="pf-line">No asks in this range yet.</p>
                  ) : (
                    <>
                      <ul className="pf-monitor-topics">
                        {visibleTopics.map((bar) => {
                          const width = Math.max(
                            6,
                            Math.round((Number(bar.count) / maxTopic) * 100),
                          );
                          const showBadge =
                            !bar.has_approved_material &&
                            badgeTopics.has(bar.topic);
                          return (
                            <li key={bar.topic}>
                              <button
                                type="button"
                                className={`pf-monitor-topic-row${
                                  selectedTopic === bar.topic ? " is-on" : ""
                                }`}
                                onClick={() => openTopic(bar)}
                              >
                                <span className="pf-monitor-topic-head">
                                  <span className="pf-radar-topic-title">
                                    <strong>{topicLabel(bar.topic)}</strong>
                                    {showBadge ? (
                                      <span className="pf-radar-no-mat">
                                        No material
                                      </span>
                                    ) : null}
                                  </span>
                                  <span>
                                    {bar.count} · {bar.pct}% ·{" "}
                                    {trendMark(bar.trend)}
                                  </span>
                                </span>
                                <span
                                  className="pf-monitor-topic-track"
                                  aria-hidden="true"
                                >
                                  <span
                                    className="pf-monitor-topic-fill"
                                    style={{ width: `${width}%` }}
                                  />
                                </span>
                              </button>
                            </li>
                          );
                        })}
                      </ul>
                      {hiddenTopicCount > 0 ? (
                        <button
                          type="button"
                          className="pf-radar-show-all"
                          onClick={() => setShowAllTopics((on) => !on)}
                        >
                          {showAllTopics
                            ? "Show fewer"
                            : `Show all (${topicBars.length})`}
                        </button>
                      ) : null}
                    </>
                  )}

                  {askCategories.length ? (
                    <div className="pf-radar-ask-cats" aria-label="Ask categories">
                      <h3>Ask categories</h3>
                      <p className="pf-radar-panel-note">
                        Triage labels (not syllabus chapters). Not shown in the
                        course-topic bars.
                      </p>
                      <ul className="pf-radar-ask-cat-list">
                        {askCategories.map((bar) => (
                          <li key={bar.topic}>
                            <button
                              type="button"
                              className={`pf-radar-ask-cat${
                                selectedTopic === bar.topic ? " is-on" : ""
                              }`}
                              onClick={() => openTopic(bar)}
                            >
                              <span>{topicLabel(bar.topic)}</span>
                              <span>
                                {bar.count} · {bar.pct}%
                              </span>
                            </button>
                          </li>
                        ))}
                      </ul>
                    </div>
                  ) : null}

                  {selectedTopic ? (
                    <div className="pf-monitor-ask-list" aria-live="polite">
                      <h3>Asks · {topicLabel(selectedTopic)}</h3>
                      {loadingAsks ? <p className="pf-line">Loading asks…</p> : null}
                      {!loadingAsks && topicAsks.length === 0 ? (
                        <p className="pf-line">No asks for this topic in range.</p>
                      ) : null}
                      <ul>
                        {topicAsks.map((ask) => (
                          <li key={ask.request_id}>
                            <p className="pf-ask-title">{ask.text}</p>
                            <p className="pf-meta">
                              #{ask.request_id} · {ask.work_status}
                              {ask.anonymous ? " · anonymous" : ""}
                            </p>
                          </li>
                        ))}
                      </ul>
                    </div>
                  ) : null}
                </div>
              </div>
            </section>

            {(monitor.missing_fields || []).length > 0 ? (
              <p className="pf-monitor-missing-block">
                Missing data: {monitor.missing_fields.join("; ")}.
              </p>
            ) : null}
          </>
        ) : null}
      </div>
    </div>
  );
}
