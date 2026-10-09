import { useEffect, useMemo, useState } from "react";
import { Navigate } from "react-router";
import { useAuth } from "../auth/AuthContext.jsx";

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

function storageKey(courseId) {
  return `officehours_revision_${courseId}`;
}

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

function loadRevision(courseId, courseCode) {
  try {
    const raw = localStorage.getItem(storageKey(courseId));
    if (raw) {
      const parsed = JSON.parse(raw);
      if (Array.isArray(parsed?.grades) && parsed.grades.length) {
        return {
          grades: parsed.grades,
          loggedScore: parsed.loggedScore ?? null,
          loggedTopic: parsed.loggedTopic ?? null,
        };
      }
    }
  } catch {
    // seed fresh
  }
  return {
    grades: seedGrades(courseCode),
    loggedScore: null,
    loggedTopic: null,
  };
}

function saveRevision(courseId, payload) {
  localStorage.setItem(storageKey(courseId), JSON.stringify(payload));
}

function weekPlan(focusTopic) {
  const short = (focusTopic || "Focus").split("&")[0].trim();
  return [
    ["Mon", `${short} · foundations`, "2.5h"],
    ["Tue", `${short} · practice`, "2h"],
    ["Wed", `${short} · check-in`, "2.5h"],
    ["Thu", "Second priority", "2h"],
    ["Fri", "Keep / project", "1.5h"],
    ["Sat", "Light review", "1h"],
    ["Sun", "Rest", "—"],
  ];
}

function resourcesFor(topic) {
  const t = String(topic || "").toLowerCase();
  if (t.includes("tree") || t.includes("red-black")) {
    return [
      { label: "Start here", text: "3Blue1Brown — red-black intuition" },
      { label: "Course", text: "Stamped slides — Week 5" },
      { label: "If stuck", text: "PatrickJMT — step-by-step" },
    ];
  }
  if (t.includes("hash")) {
    return [
      { label: "Start here", text: "Course stamped FAQ — chaining vs open addressing" },
      { label: "Course", text: "Week 6 slides · load factor" },
      { label: "If stuck", text: "Quiet ask a TA with your collision case" },
    ];
  }
  if (t.includes("heap")) {
    return [
      { label: "Start here", text: "Heapify walkthrough (course notes)" },
      { label: "Course", text: "Stamped slides — priority queues" },
      { label: "If stuck", text: "Work 3 textbook problems, then Quiet ask" },
    ];
  }
  return [
    { label: "Start here", text: "Syllabus outline for this topic" },
    { label: "Course", text: "Latest stamped materials in Study Agent" },
    { label: "If stuck", text: "Quiet ask with one concrete example" },
  ];
}

export default function StudentRevisionPage() {
  const { activeCourse } = useAuth();
  const [grades, setGrades] = useState([]);
  const [editingGrade, setEditingGrade] = useState(null);
  const [gradeDraft, setGradeDraft] = useState("");
  const [todayScore, setTodayScore] = useState("75");
  const [loggedScore, setLoggedScore] = useState(null);
  const [loggedTopic, setLoggedTopic] = useState(null);
  const [toast, setToast] = useState("");

  useEffect(() => {
    if (!activeCourse) return;
    const data = loadRevision(activeCourse.id, activeCourse.code);
    setGrades(data.grades);
    setLoggedScore(data.loggedScore);
    setLoggedTopic(data.loggedTopic);
  }, [activeCourse]);

  const ranked = useMemo(() => [...grades].sort((a, b) => gap(b) - gap(a)), [grades]);
  const focus = ranked[0] || {
    topic: "Revision plan",
    score: 0,
    weight: 0,
    source: "Local plan",
  };
  const resources = useMemo(() => resourcesFor(focus.topic), [focus.topic]);
  const week = useMemo(() => weekPlan(focus.topic), [focus.topic]);

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

  function persist(nextGrades, nextLogged = loggedScore, nextTopic = loggedTopic) {
    setGrades(nextGrades);
    setLoggedScore(nextLogged);
    setLoggedTopic(nextTopic);
    saveRevision(activeCourse.id, {
      grades: nextGrades,
      loggedScore: nextLogged,
      loggedTopic: nextTopic,
    });
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
    flash("Grade updated · plan recalculated");
  }

  function logToday() {
    const n = Number(todayScore);
    if (Number.isNaN(n) || n < 0 || n > 100) return;
    const next = grades.map((row) =>
      row.topic === focus.topic
        ? { ...row, score: n, source: "You · today's check-in" }
        : row,
    );
    persist(next, n, focus.topic);
    const short = focus.topic.split("&")[0].trim();
    flash(
      n >= 75
        ? `Logged ${n}% · next week can ease ${short}`
        : n >= 65
          ? `Logged ${n}% · keep three solid days on ${short}`
          : `Logged ${n}% · next week escalates ${short}`,
    );
  }

  return (
    <div className="fade-up">
      <h1 className="bh-page-title">Revision Strategist</h1>
      <p className="bh-page-subtitle">
        Local grade plan for {activeCourse.code} until Canvas grades land in the
        API. Firm priorities — you can correct a wrong score.
      </p>

      {toast ? (
        <div className="mb-3 rounded-xl border border-aui-forest/30 bg-[#eef8f1] px-4 py-2.5 text-sm font-medium text-aui-ink">
          {toast}
        </div>
      ) : null}

      <p className="mb-4 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-950">
        Grades are seeded locally (not live Canvas yet). Edits stay on this device
        under key{" "}
        <code className="font-mono">officehours_revision_{activeCourse.id}</code>.
      </p>

      <div className="grid gap-5 lg:grid-cols-2">
        <section className="bh-card">
          <div className="bh-card-title">
            <h2>From Canvas + syllabus</h2>
          </div>
          <p className="bh-card-note">Each row shows its source. Fix if a score is wrong.</p>
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
            Priority: <strong>{focus.topic}</strong> — weight × gap to 85% is largest.
          </p>
        </section>

        <section className="bh-card">
          <div className="bh-card-title">
            <h2>Today&apos;s plan</h2>
          </div>
          <p className="bh-card-note">
            Why: {focus.source} shows {focus.score}%, and it is {focus.weight}% of
            the exam weight. Close the biggest gap first — steady beats harsh.
          </p>
          <p className="mt-3 text-sm font-semibold text-aui-ink">
            2 h 15 min · finish by 22:30
          </p>
          <ol className="mt-3 space-y-2 text-sm">
            <li className="rounded-lg border border-[#d7e0d9] bg-white px-3 py-2">
              <strong>Block 1 · 45 min · Start here</strong>
              <span className="mt-0.5 block text-xs text-aui-deep/70">
                Core notes for {focus.topic.split("&")[0].trim()}
              </span>
            </li>
            <li className="rounded-lg border border-[#d7e0d9] bg-white px-3 py-2">
              <strong>Block 2 · 60 min · Practice</strong>
              <span className="mt-0.5 block text-xs text-aui-deep/70">
                Worked problems until one clean pass
              </span>
            </li>
            <li className="rounded-lg border border-[#d7e0d9] bg-white px-3 py-2">
              <strong>Block 3 · 30 min · Check</strong>
              <span className="mt-0.5 block text-xs text-aui-deep/70">
                Self quiz · target 75%+
              </span>
            </li>
          </ol>

          <div className="mt-4 rounded-lg border border-aui-forest/20 bg-[#f3faf5] p-3 text-xs">
            <p className="font-semibold text-aui-ink">Resources (3 max)</p>
            <ol className="mt-2 list-decimal space-y-1 pl-4 text-aui-deep/85">
              {resources.map((item) => (
                <li key={item.label}>
                  <strong>{item.label}:</strong> {item.text}
                </li>
              ))}
            </ol>
          </div>

          <div className="mt-4 rounded-lg border border-[#d7e0d9] bg-white p-3">
            <p className="text-sm font-semibold text-aui-ink">Log today&apos;s check-in</p>
            <p className="mt-1 text-xs text-aui-deep/70">
              After Block 3, log your score — next week&apos;s glance recalculates.
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
      </div>

      <section className="bh-card mt-5">
        <div className="bh-card-title">
          <h2>This week</h2>
        </div>
        <p className="bh-card-note">Secondary to Today — glance only.</p>
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
      </section>
    </div>
  );
}
