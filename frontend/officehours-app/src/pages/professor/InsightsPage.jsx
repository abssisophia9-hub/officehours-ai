import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router";
import { api } from "../../api/client.js";
import { useAuth } from "../../auth/AuthContext.jsx";

const RANGES = [
  { id: "7d", label: "7 days" },
  { id: "30d", label: "30 days" },
  { id: "term", label: "Term" },
];

function trendMark(trend) {
  if (trend === "up") return "↑";
  if (trend === "down") return "↓";
  return "→";
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
  const topics = monitor?.topics || [];
  const maxTopic = Math.max(1, ...topics.map((t) => Number(t.count) || 0));

  return (
    <div className="pf-page pf-monitor">
      <header className="pf-head pf-desk-head">
        <div>
          <p className="pf-kicker">Early warning</p>
          <h1>Insights</h1>
          <p className="pf-line pf-monitor-lead">
            Stuck topics, trend vs prior range, waits that need you — act from
            here.
          </p>
        </div>
      </header>

      {/* apple-design: Purpose; Simplicity — not minimalism; Feedback; Familiarity; Craft; Response — kill latency; Reduced motion & accessibility; Typography — optical sizing, tracking, leading (8). */}
      <p className="pf-monitor-a11y">
        Applied: Purpose; Simplicity — not minimalism; Feedback; Familiarity;
        Craft; Response — kill latency; Reduced motion &amp; accessibility;
        Typography — optical sizing, tracking, leading (8).
      </p>

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
          <span>Topic</span>
          <select
            value={topic}
            onChange={(event) => setTopic(event.target.value)}
            aria-label="Filter by topic"
          >
            <option value="">All topics</option>
            {(monitor?.topic_options || []).map((name) => (
              <option key={name} value={name}>
                {name.replaceAll("_", " ")}
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
          <section className="pf-monitor-kpis" aria-label="Key measures">
            {(monitor.kpis || []).map((kpi) => (
              <article key={kpi.key} className="pf-monitor-kpi">
                <p className="pf-monitor-kpi-label">{kpi.label}</p>
                <p className="pf-monitor-kpi-value">{kpi.value}</p>
                {kpi.delta_label ? (
                  <p className="pf-monitor-kpi-delta">{kpi.delta_label}</p>
                ) : null}
                {kpi.missing ? (
                  <p className="pf-monitor-missing">{kpi.missing}</p>
                ) : null}
              </article>
            ))}
          </section>

          <section className="pf-block" aria-label="Asks per day">
            <h2>Asks per day</h2>
            {!monitor.enough_for_trend ? (
              <p className="pf-line">
                {monitor.message || "Not enough asks yet for a trend"}. Showing
                counts for this range.
              </p>
            ) : (
              <p className="pf-line">{monitor.message}</p>
            )}
            <div className="pf-monitor-chart" role="img" aria-label="Asks per day chart">
              <div className="pf-monitor-chart-plot">
                {days.map((point) => {
                  const count = Number(point.count) || 0;
                  const height = Math.max(count > 0 ? 8 : 0, Math.round((count / maxDay) * 100));
                  return (
                    <div key={point.day} className="pf-monitor-bar-col">
                      <span className="pf-monitor-bar-count">{count}</span>
                      <span
                        className="pf-monitor-bar"
                        style={{ height: `${height}%` }}
                        title={`${point.day}: ${count}`}
                      />
                      <span className="pf-monitor-bar-day">
                        {point.day.slice(5)}
                      </span>
                    </div>
                  );
                })}
              </div>
              <p className="pf-monitor-axis">Day (UTC) · solid count only</p>
            </div>
          </section>

          <section className="pf-block" aria-label="Topics">
            <h2>Topics</h2>
            {topics.length === 0 ? (
              <p className="pf-line">No asks in this range yet.</p>
            ) : (
              <ul className="pf-monitor-topics">
                {topics.map((bar) => {
                  const width = Math.max(
                    6,
                    Math.round((Number(bar.count) / maxTopic) * 100),
                  );
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
                          <strong>{bar.topic.replaceAll("_", " ")}</strong>
                          <span>
                            {bar.count} · {bar.pct}% · {trendMark(bar.trend)}
                          </span>
                        </span>
                        <span className="pf-monitor-topic-track" aria-hidden="true">
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
            )}
            {selectedTopic ? (
              <div className="pf-monitor-ask-list" aria-live="polite">
                <h3>Asks · {selectedTopic.replaceAll("_", " ")}</h3>
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
          </section>

          <section className="pf-block" aria-label="Needs you">
            <h2>Needs you</h2>
            {(monitor.needs_you || []).length === 0 ? (
              <p className="pf-line">
                Nothing urgent in this range. Keep watching the topic bars.
              </p>
            ) : (
              <ul className="pf-ask-list">
                {monitor.needs_you.map((item, index) => (
                  <li key={`${item.kind}-${item.request_id || item.topic || index}`}>
                    <p className="pf-ask-title">{item.title}</p>
                    <p className="pf-line">{item.detail}</p>
                    {item.action_href && item.action_label ? (
                      <Link className="btn-primary pf-btn" to={item.action_href}>
                        {item.action_label}
                      </Link>
                    ) : null}
                  </li>
                ))}
              </ul>
            )}
          </section>

          {(monitor.missing_fields || []).length > 0 ? (
            <p className="pf-monitor-missing-block">
              Missing data: {monitor.missing_fields.join("; ")}.
            </p>
          ) : null}
        </>
      ) : null}
    </div>
  );
}
