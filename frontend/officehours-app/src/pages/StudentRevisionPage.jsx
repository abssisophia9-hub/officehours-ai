import { useCallback, useEffect, useMemo, useState } from "react";
import { Navigate } from "react-router";
import { api } from "../api/client.js";
import { useAuth } from "../auth/AuthContext.jsx";
import {
  loadRevision,
  loadStrategistPlan,
  saveRevision,
  saveStrategistPlan,
} from "../student/strategistStorage.js";

const CSC_SEED = [
  { topic: "Trees & red-black", weight: 35, score: 62, source: "Canvas · Quiz 4" },
  { topic: "Hashing", weight: 25, score: 78, source: "Canvas · Assignment 3" },
  { topic: "Heaps", weight: 20, score: 88, source: "Canvas · Quiz 3" },
  { topic: "Amortized analysis", weight: 20, score: 71, source: "Canvas · practice" },
];

const GENERIC_SEED = [
  { topic: "Core concepts", weight: 30, score: 68, source: "Canvas · Quiz" },
  { topic: "Problem sets", weight: 30, score: 74, source: "Canvas · Assignment" },
  { topic: "Midterm topics", weight: 25, score: 71, source: "Canvas · Midterm prep" },
  { topic: "Project / labs", weight: 15, score: 80, source: "Canvas · Lab" },
];

function isCscLike(code) {
  const c = String(code || "").toUpperCase();
  return c.startsWith("CSC") || c.includes("DATA") || c.includes("ALGOR");
}

function seedGrades(courseCode) {
  return (isCscLike(courseCode) ? CSC_SEED : GENERIC_SEED).map((row) => ({ ...row }));
}

function gap(row) {
  return row.weight * Math.max(0, 85 - row.score);
}

function styleLabel(style) {
  return String(style || "unknown").replaceAll("_", " ");
}

export default function StudentRevisionPage() {
  const { token, activeCourse } = useAuth();
  const [grades, setGrades] = useState([]);
  const [editingGrade, setEditingGrade] = useState(null);
  const [gradeDraft, setGradeDraft] = useState("");
  const [todayScore, setTodayScore] = useState("75");
  const [loggedScore, setLoggedScore] = useState(null);
  const [loggedTopic, setLoggedTopic] = useState(null);
  const [goal, setGoal] = useState("");
  const [toast, setToast] = useState("");
  const [plan, setPlan] = useState(null);
  const [planError, setPlanError] = useState("");
  const [planBusy, setPlanBusy] = useState(false);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    if (!activeCourse) return;
    const data = loadRevision(activeCourse.id);
    setGrades(data?.grades?.length ? data.grades : seedGrades(activeCourse.code));
    setLoggedScore(data?.loggedScore ?? null);
    setLoggedTopic(data?.loggedTopic ?? null);
    setGoal(data?.goal ?? "");
    setPlan(loadStrategistPlan(activeCourse.id));
    setReady(true);
  }, [activeCourse]);

  const ranked = useMemo(() => [...grades].sort((a, b) => gap(b) - gap(a)), [grades]);
  const localFocus = ranked[0] || {
    topic: "Revision plan",
    score: 0,
    weight: 0,
    source: "Local plan",
  };
  const focus = plan?.focus?.topic ? plan.focus : localFocus;
  const today = plan?.today || [];
  const week = plan?.week?.length ? plan.week : [];
  const resources = plan?.resources || [];

  const persist = useCallback(
    (nextGrades, extras = {}) => {
      const nextLogged = extras.loggedScore ?? loggedScore;
      const nextTopic = extras.loggedTopic ?? loggedTopic;
      const nextGoal = extras.goal ?? goal;
      setGrades(nextGrades);
      setLoggedScore(nextLogged);
      setLoggedTopic(nextTopic);
      setGoal(nextGoal);
      saveRevision(activeCourse.id, {
        grades: nextGrades,
        loggedScore: nextLogged,
        loggedTopic: nextTopic,
        goal: nextGoal,
      });
    },
    [activeCourse, goal, loggedScore, loggedTopic],
  );

  const runPlan = useCallback(
    async (nextGrades = grades, nextGoal = goal) => {
      if (!token || !activeCourse) return;
      setPlanBusy(true);
      setPlanError("");
      try {
        const body = await api("/strategist/plan", {
          method: "POST",
          token,
          body: {
            course_id: activeCourse.id,
            goal: nextGoal || undefined,
            grades: nextGrades.map((row) => ({
              topic: row.topic,
              score: row.score,
              weight: row.weight,
              source: row.source,
            })),
          },
        });
        setPlan(body);
        saveStrategistPlan(activeCourse.id, body);
      } catch (err) {
        setPlan(null);
        setPlanError(err.message || "Strategist could not build a plan.");
      } finally {
        setPlanBusy(false);
      }
    },
    [token, activeCourse, grades, goal],
  );

  useEffect(() => {
    if (!ready || !token || !activeCourse || !grades.length) return;
    if (loadStrategistPlan(activeCourse.id)) return;
    runPlan(grades, goal);
  }, [ready, token, activeCourse, grades, goal, runPlan]);

  if (!activeCourse) return <Navigate to="/" replace />;
  if (activeCourse.role !== "student") {
    return (
      <Navigate
        to={`/${activeCourse.role === "professor" ? "professor" : "ta"}`}
        replace
      />
    );
  }

  function flash(message) {
    setToast(message);
    window.setTimeout(() => setToast(""), 3200);
  }

  function saveGrade(topic) {
    const n = Number(gradeDraft);
    if (Number.isNaN(n) || n < 0 || n > 100) return;
    const next = grades.map((row) =>
      row.topic === topic
        ? {
            ...row,
            score: n,
            source: `${String(row.source || "Canvas").split(" · ")[0]} · adjusted by you`,
          }
        : row,
    );
    persist(next);
    setEditingGrade(null);
    flash("Grade updated · rebuild the plan when you are ready");
  }

  function logToday() {
    const n = Number(todayScore);
    if (Number.isNaN(n) || n < 0 || n > 100) return;
    const topic = focus.topic;
    const next = grades.map((row) =>
      row.topic === topic
        ? { ...row, score: n, source: "You · today's check-in" }
        : row,
    );
    persist(next, { loggedScore: n, loggedTopic: topic });
    const short = String(topic || "").split("&")[0].trim();
    flash(
      n >= 75
        ? `Logged ${n}% · next week can ease ${short}`
        : n >= 65
          ? `Logged ${n}% · keep three solid days on ${short}`
          : `Logged ${n}% · next week escalates ${short}`,
    );
  }

  function submitGoal(event) {
    event.preventDefault();
    persist(grades, { goal });
    runPlan(grades, goal);
  }

  return (
    <div className="fade-up rs-page">
      <h1 className="bh-page-title">Revision Strategist</h1>
      <p className="bh-page-subtitle">
        A planner agent for {activeCourse.code}: it reads how you ask and learn,
        then searches YouTube and articles. It does not invent links and it does
        not quote the syllabus.
      </p>

      {toast ? (
        <div className="mb-3 rounded-xl border border-aui-forest/30 bg-[#eef8f1] px-4 py-2.5 text-sm font-medium text-aui-ink">
          {toast}
        </div>
      ) : null}

      <form className="rs-goal bh-card" onSubmit={submitGoal}>
        <div className="bh-card-title">
          <h2>What should the planner hunt for?</h2>
        </div>
        <p className="bh-card-note">
          Optional. Leave blank and the agent writes a goal from your asks and
          the biggest grade gap.
        </p>
        <div className="rs-goal-row">
          <input
            className="field-glass rs-goal-input"
            value={goal}
            maxLength={500}
            placeholder="e.g. I need a diagram of red-black delete_fixup"
            onChange={(event) => setGoal(event.target.value)}
          />
          <button type="submit" className="btn-primary rs-goal-go" disabled={planBusy}>
            {planBusy ? "Planning…" : "Build my plan"}
          </button>
        </div>
        {plan ? (
          <p className="rs-meta">
            Planner: <strong>{plan.planner}</strong>
            {plan.model ? ` · ${plan.model}` : ""}
            {plan.focus?.topic ? ` · focus ${plan.focus.topic}` : ""}
          </p>
        ) : null}
      </form>

      {plan?.dossier ? (
        <section className="bh-card rs-dossier">
          <div className="bh-card-title">
            <h2>Learner dossier</h2>
          </div>
          <p className="bh-card-note">{plan.dossier.how_they_ask}</p>
          <p className="rs-dossier-line">
            Style: <strong>{styleLabel(plan.dossier.dominant_style)}</strong>
            {plan.dossier.struggles?.length
              ? ` · struggling with ${plan.dossier.struggles.slice(0, 4).join(", ")}`
              : ""}
            {` · ${plan.dossier.ask_count} ask(s) in this course`}
          </p>
          {plan.goal ? (
            <p className="rs-dossier-goal">
              <strong>Agent goal:</strong> {plan.goal}
            </p>
          ) : null}
        </section>
      ) : null}

      <div className="grid gap-5 lg:grid-cols-2">
        <section className="bh-card">
          <div className="bh-card-title">
            <h2>Today&apos;s plan</h2>
          </div>
          <p className="bh-card-note">
            {plan?.today_summary ||
              (focus.source
                ? `Why: ${focus.source}${
                    focus.score != null ? ` shows ${focus.score}%` : ""
                  }${focus.weight != null ? ` · ${focus.weight}% of exam weight` : ""}.`
                : "Build a plan to get today's three blocks.")}
          </p>
          {planBusy && today.length === 0 ? (
            <p className="mt-3 text-sm text-aui-deep/70">
              Searching YouTube and articles from your dossier…
            </p>
          ) : today.length ? (
            <ol className="mt-3 space-y-2 text-sm">
              {today.map((block) => (
                <li
                  key={block.title}
                  className="rounded-lg border border-[#d7e0d9] bg-white px-3 py-2"
                >
                  <strong>
                    {block.title} · {block.minutes} min
                  </strong>
                  <span className="mt-0.5 block text-xs text-aui-deep/70">
                    {block.action}
                  </span>
                  {block.resource_url ? (
                    <a
                      className="mt-1 inline-block text-[11px] font-semibold text-aui-forest underline"
                      href={block.resource_url}
                      target="_blank"
                      rel="noreferrer"
                    >
                      {block.resource_title || block.resource_url}
                    </a>
                  ) : null}
                </li>
              ))}
            </ol>
          ) : (
            <p className="mt-3 text-sm text-aui-deep/70">
              No today blocks yet. Build a plan.
            </p>
          )}

          <div className="mt-4 rounded-lg border border-aui-forest/20 bg-[#f3faf5] p-3 text-xs">
            <p className="font-semibold text-aui-ink">Resources from the web tools</p>
            {planError ? (
              <p className="mt-2 text-amber-900">{planError}</p>
            ) : resources.length === 0 ? (
              <p className="mt-2 text-aui-deep/70">
                {plan?.notes?.[0] ||
                  "No structured hits yet. The agent will not invent a YouTube URL."}
              </p>
            ) : (
              <ol className="mt-2 list-decimal space-y-2 pl-4 text-aui-deep/85">
                {resources.map((item) => (
                  <li key={item.url}>
                    <span className="font-semibold uppercase tracking-wide">
                      {item.kind}
                    </span>
                    {": "}
                    <a
                      className="font-semibold text-aui-forest underline"
                      href={item.url}
                      target="_blank"
                      rel="noreferrer"
                    >
                      {item.title}
                    </a>
                    {item.why ? (
                      <span className="mt-0.5 block text-[11px] text-aui-deep/70">
                        {item.why}
                      </span>
                    ) : null}
                  </li>
                ))}
              </ol>
            )}
            {plan?.tool_calls?.length ? (
              <p className="mt-3 text-[11px] text-aui-deep/60">
                Tools:{" "}
                {plan.tool_calls
                  .map((call) => `${call.tool}(“${call.query}”)`)
                  .join(" · ")}
              </p>
            ) : null}
          </div>

          <div className="mt-4 rounded-lg border border-[#d7e0d9] bg-white p-3">
            <p className="text-sm font-semibold text-aui-ink">Log today&apos;s check-in</p>
            <p className="mt-1 text-xs text-aui-deep/70">
              After the last block, log your score — the next plan uses it.
            </p>
            <div className="mt-2 flex flex-wrap items-center gap-2">
              <input
                className="field-glass w-24 px-2 py-1.5 text-sm"
                type="number"
                min="0"
                max="100"
                value={todayScore}
                onChange={(event) => setTodayScore(event.target.value)}
              />
              <button
                type="button"
                className="btn-primary px-3 py-1.5 text-xs"
                onClick={logToday}
              >
                Log score
              </button>
            </div>
            {loggedScore != null ? (
              <p className="mt-2 text-xs font-medium text-aui-forest">
                Saved {loggedScore}% for {loggedTopic || focus.topic}.
              </p>
            ) : null}
          </div>
        </section>

        <section className="bh-card">
          <div className="bh-card-title">
            <h2>From Canvas + syllabus</h2>
          </div>
          <p className="bh-card-note">
            Grades stay on this device until a live Canvas grade token. The
            dossier still comes from your asks in {activeCourse.code}.
          </p>
          <ul className="mt-4 space-y-2">
            {ranked.map((row) => (
              <li
                key={row.topic}
                className="rounded-lg border border-[#d7e0d9] bg-white px-3 py-2 text-sm"
              >
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <p className="font-semibold text-aui-ink">{row.topic}</p>
                    <p className="text-xs text-aui-deep/70">
                      {row.source} · {row.weight}% of exam
                    </p>
                  </div>
                  <span
                    className={`text-lg font-bold ${
                      row.score < 70 ? "text-amber-800" : "text-aui-forest"
                    }`}
                  >
                    {row.score}%
                  </span>
                </div>
                {editingGrade === row.topic ? (
                  <div className="mt-2 flex flex-wrap items-center gap-2">
                    <input
                      className="field-glass w-24 px-2 py-1 text-xs"
                      type="number"
                      min="0"
                      max="100"
                      value={gradeDraft}
                      onChange={(event) => setGradeDraft(event.target.value)}
                    />
                    <button
                      type="button"
                      className="btn-primary px-3 py-1 text-xs"
                      onClick={() => saveGrade(row.topic)}
                    >
                      Save
                    </button>
                    <button
                      type="button"
                      className="text-xs underline"
                      onClick={() => setEditingGrade(null)}
                    >
                      Cancel
                    </button>
                  </div>
                ) : (
                  <button
                    type="button"
                    className="mt-1 text-[11px] font-semibold text-aui-forest underline"
                    onClick={() => {
                      setEditingGrade(row.topic);
                      setGradeDraft(String(row.score));
                    }}
                  >
                    Fix this grade
                  </button>
                )}
              </li>
            ))}
          </ul>
          <p className="soft-stat mt-4 text-sm">
            Priority: <strong>{focus.topic}</strong> — weight × gap to 85% is
            largest.
          </p>
        </section>
      </div>

      <section className="bh-card mt-5">
        <div className="bh-card-title">
          <h2>This week</h2>
        </div>
        <p className="bh-card-note">Secondary to Today — glance only.</p>
        {week.length ? (
          <div className="mt-3 grid gap-2 sm:grid-cols-7">
            {week.map(([day, topic, dur]) => (
              <div
                key={day}
                className="rounded-lg border border-[#d7e0d9] bg-white p-2 text-xs"
              >
                <p className="font-bold text-aui-forest">{day}</p>
                <p className="mt-1 text-aui-ink">{topic}</p>
                <p className="mt-2 text-aui-deep/60">{dur}</p>
              </div>
            ))}
          </div>
        ) : (
          <p className="mt-3 text-sm text-aui-deep/70">Week plan arrives with the agent.</p>
        )}
      </section>
    </div>
  );
}
