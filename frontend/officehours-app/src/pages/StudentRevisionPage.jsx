import { useEffect, useMemo, useState } from "react";
import { Navigate, useNavigate } from "react-router";
import { api } from "../api/client.js";
import { useAuth } from "../auth/AuthContext.jsx";

const CSC_SEED = [
  { topic: "Trees & red-black", weight: 35, score: 62, source: "Demo sample · Quiz 4", assignment_kind: "text" },
  { topic: "Hashing", weight: 25, score: 78, source: "Demo sample · Assignment 3", assignment_kind: "text" },
  { topic: "Heaps", weight: 20, score: 88, source: "Demo sample · Quiz 3", assignment_kind: "text" },
  { topic: "Amortized analysis", weight: 20, score: 71, source: "Demo sample · practice", assignment_kind: "text" },
];

const GENERIC_SEED = [
  { topic: "Core concepts", weight: 30, score: 68, source: "Demo sample · Quiz", assignment_kind: "text" },
  { topic: "Problem sets", weight: 30, score: 74, source: "Demo sample · Assignment", assignment_kind: "text" },
  { topic: "Midterm topics", weight: 25, score: 71, source: "Demo sample · Midterm prep", assignment_kind: "text" },
  { topic: "Project / labs", weight: 15, score: 80, source: "Demo sample · Lab", assignment_kind: "project" },
];

const HORIZON_OPTIONS = [
  { id: "3", days: 3, label: "3 days" },
  { id: "10", days: 10, label: "10 days" },
  { id: "21", days: 21, label: "21 days" },
  { id: "exam", days: null, label: "Exam date" },
];

function daysUntilExam(isoDate) {
  if (!isoDate) return null;
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const exam = new Date(`${isoDate}T00:00:00`);
  if (Number.isNaN(exam.getTime())) return null;
  const diff = Math.round((exam.getTime() - today.getTime()) / 86400000);
  return Math.max(1, Math.min(60, diff));
}

const PREFERENCE_OPTIONS = [
  { id: "step_by_step", label: "Step-by-step" },
  { id: "example_driven", label: "Examples" },
  { id: "visual_structural", label: "Visual" },
  { id: "conceptual", label: "Conceptual" },
  { id: "unknown", label: "No preference" },
];

function storageKey(courseId) {
  return `officehours_revision_${courseId}`;
}

function prefsKey(courseId) {
  return `officehours_revision_prefs_${courseId}`;
}

function planKey(courseId) {
  return `officehours_revision_plan_${courseId}`;
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

function weaknessFromScore(score) {
  if (score < 70) return "high";
  if (score < 80) return "med";
  return "low";
}

const WEAKNESS_LABEL = {
  high: "needs work",
  med: "getting there",
  low: "on track",
};

function planModeLabel(plan) {
  if (!plan) return "";
  if (plan.mode_label && !/planning mode|rule-based|llm_|fallback|gate:/i.test(plan.mode_label)) {
    return plan.mode_label;
  }
  if (plan.mode === "agent") return "Plan built with the Pedagogy Agent";
  return "Plan built from your scores and preference";
}

function publicPlanNotes(notes) {
  const blocked =
    /llm_|fallback|gate:|budget:|quota|rule-based|invalid model|api key|gemini|orchestrat/i;
  // Resources box already shows the empty-state sentence — don't repeat it under notes.
  const emptyResources =
    /^we couldn't find resources right now\. try again later\.?$/i;
  return (notes || [])
    .map((note) => String(note || "").trim())
    .filter((note) => note && !blocked.test(note) && !emptyResources.test(note));
}

function scrubCanvasLabel(source) {
  const text = String(source || "").trim();
  if (!text) return "Demo sample";
  if (/^canvas\b/i.test(text)) {
    return text.replace(/^canvas\b/i, "Demo sample");
  }
  return text;
}

function loadRevision(courseId, courseCode) {
  try {
    const raw = localStorage.getItem(storageKey(courseId));
    if (raw) {
      const parsed = JSON.parse(raw);
      if (Array.isArray(parsed?.grades) && parsed.grades.length) {
        return {
          grades: parsed.grades.map((row) => ({
            ...row,
            source: scrubCanvasLabel(row.source),
          })),
        };
      }
    }
  } catch {
    // start from demo samples
  }
  return {
    grades: seedGrades(courseCode),
  };
}

function saveRevision(courseId, payload) {
  localStorage.setItem(
    storageKey(courseId),
    JSON.stringify({ grades: payload.grades || [] }),
  );
}

function horizonKey(courseId) {
  return `officehours_revision_horizon_${courseId}`;
}

function examKey(courseId) {
  return `officehours_revision_exam_${courseId}`;
}

function loadHorizonState(courseId) {
  try {
    const raw = localStorage.getItem(horizonKey(courseId));
    if (raw === "exam") {
      const examDate = localStorage.getItem(examKey(courseId)) || "";
      const days = daysUntilExam(examDate) || 14;
      return { mode: "exam", examDate, days };
    }
    const days = Number(raw);
    if (HORIZON_OPTIONS.some((opt) => opt.days === days)) {
      return { mode: String(days), examDate: "", days };
    }
  } catch {
    // default
  }
  return { mode: "10", examDate: "", days: 10 };
}

function saveHorizonState(courseId, mode, examDate) {
  localStorage.setItem(horizonKey(courseId), mode);
  if (mode === "exam") {
    localStorage.setItem(examKey(courseId), examDate || "");
  } else {
    localStorage.removeItem(examKey(courseId));
  }
}

function loadPreference(courseId) {
  try {
    const raw = localStorage.getItem(prefsKey(courseId));
    if (raw && PREFERENCE_OPTIONS.some((opt) => opt.id === raw)) return raw;
  } catch {
    // default
  }
  return "step_by_step";
}

function savePreference(courseId, value) {
  localStorage.setItem(prefsKey(courseId), value);
}

function loadPlan(courseId) {
  try {
    const raw = localStorage.getItem(planKey(courseId));
    if (raw) return JSON.parse(raw);
  } catch {
    // none
  }
  return null;
}

function savePlan(courseId, plan) {
  if (!plan) {
    localStorage.removeItem(planKey(courseId));
    return;
  }
  localStorage.setItem(planKey(courseId), JSON.stringify(plan));
}

function planDeadlines(grades, horizonDays) {
  const horizon = Math.max(1, Math.min(60, Number(horizonDays) || 10));
  const ranked = [...grades].sort((a, b) => gap(b) - gap(a));
  const weak = ranked.filter((row) => row.score < 85);
  const focus = (weak.length ? weak : ranked).slice(0, 3);
  return focus.map((row, index) => {
    const due = Math.round(((index + 1) / focus.length) * horizon);
    return {
      topic: row.topic,
      due_in_days: Math.max(1, Math.min(horizon, due)),
      label: index === 0 ? "Primary focus" : index === 1 ? "Second focus" : "Follow-up",
    };
  });
}

export default function StudentRevisionPage() {
  const { activeCourse, token } = useAuth();
  const navigate = useNavigate();
  const [grades, setGrades] = useState([]);
  const [editingGrade, setEditingGrade] = useState(null);
  const [gradeDraft, setGradeDraft] = useState("");
  const [preference, setPreference] = useState("step_by_step");
  const [horizonMode, setHorizonMode] = useState("10");
  const [examDate, setExamDate] = useState("");
  const [horizonDays, setHorizonDays] = useState(10);
  const [plan, setPlan] = useState(null);
  const [busy, setBusy] = useState(false);
  const [askBusy, setAskBusy] = useState(false);
  const [error, setError] = useState("");
  const [toast, setToast] = useState("");

  useEffect(() => {
    if (!activeCourse) return;
    const data = loadRevision(activeCourse.id, activeCourse.code);
    setGrades(data.grades);
    setPreference(loadPreference(activeCourse.id));
    const horizon = loadHorizonState(activeCourse.id);
    setHorizonMode(horizon.mode);
    setExamDate(horizon.examDate);
    setHorizonDays(horizon.days);
    setPlan(loadPlan(activeCourse.id));
    setError("");
  }, [activeCourse]);

  const ranked = useMemo(() => [...grades].sort((a, b) => gap(b) - gap(a)), [grades]);
  const focus = ranked[0] || {
    topic: "Revision plan",
    score: 0,
    weight: 0,
    source: "Local plan",
  };

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

  function persist(nextGrades) {
    setGrades(nextGrades);
    saveRevision(activeCourse.id, { grades: nextGrades });
  }

  function onPreference(value) {
    setPreference(value);
    savePreference(activeCourse.id, value);
  }

  function onHorizonMode(value) {
    if (value === "exam") {
      const days = daysUntilExam(examDate) || 14;
      setHorizonMode("exam");
      setHorizonDays(days);
      saveHorizonState(activeCourse.id, "exam", examDate);
      return;
    }
    const days = Number(value);
    setHorizonMode(String(days));
    setHorizonDays(days);
    saveHorizonState(activeCourse.id, String(days), "");
  }

  function onExamDate(value) {
    setExamDate(value);
    const days = daysUntilExam(value) || 14;
    setHorizonMode("exam");
    setHorizonDays(days);
    saveHorizonState(activeCourse.id, "exam", value);
  }

  function saveGrade(topic) {
    const n = Number(gradeDraft);
    if (Number.isNaN(n) || n < 0 || n > 100) return;
    const next = grades.map((row) =>
      row.topic === topic
        ? {
            ...row,
            score: n,
            source: "Adjusted by you",
          }
        : row,
    );
    persist(next);
    setEditingGrade(null);
    flash("Score updated · rebuild the plan when you are ready");
  }

  async function buildPlan() {
    setBusy(true);
    setError("");
    try {
      const body = {
        course_id: activeCourse.id,
        preference,
        available_minutes_today: 120,
        deadlines: planDeadlines(grades, horizonDays),
        grades: grades
          .filter((row) => (row.assignment_kind || "text") === "text")
          .map((row) => ({
            topic: row.topic,
            weakness: weaknessFromScore(row.score),
            assignment_kind: "text",
          })),
      };
      const result = await api("/revision/plan", {
        method: "POST",
        token,
        body,
      });
      setPlan(result);
      savePlan(activeCourse.id, result);
      flash(planModeLabel(result) || "Plan ready");
    } catch (err) {
      setError(err.message || "Could not build plan.");
    } finally {
      setBusy(false);
    }
  }

  async function askTa() {
    if (!plan?.ask_draft) return;
    setAskBusy(true);
    setError("");
    try {
      const created = await api("/requests/", {
        method: "POST",
        token,
        body: {
          text: plan.ask_draft,
          anonymous: true,
          course: activeCourse.code,
          course_id: activeCourse.id,
          help_mode: "message",
          learning_style: preference === "unknown" ? null : preference,
        },
      });
      flash("Quiet ask sent");
      if (created?.id) {
        window.setTimeout(() => navigate(`/student/asks?focus=${created.id}`), 500);
      }
    } catch (err) {
      setError(err.message || "Could not send Quiet ask.");
    } finally {
      setAskBusy(false);
    }
  }

  const courseLine = [activeCourse.code, activeCourse.title].filter(Boolean).join(" · ");
  const slots = plan?.time_slots || [];
  const resources = plan?.resources || [];
  const visibleNotes = publicPlanNotes(plan?.notes);
  const planWindowDays = slots.reduce(
    (max, slot) => Math.max(max, Number(slot.day_offset) || 0),
    0,
  );

  return (
    <div className="fade-up pa-page">
      <h1 className="sa-course">{courseLine}</h1>
      <h2 className="bh-page-title">Pedagogy Agent</h2>
      <p className="bh-page-subtitle">
        A short focus plan from your practice scores, how you learn, and
        checked public links. Adjust any score that looks wrong before you build.
      </p>

      {toast ? (
        <div className="mb-3 rounded-xl border border-aui-forest/30 bg-[#eef8f1] px-4 py-2.5 text-sm font-medium text-aui-ink">
          {toast}
        </div>
      ) : null}

      {error ? (
        <div className="mb-3 rounded-xl border border-red-200 bg-red-50 px-4 py-2.5 text-sm text-red-900">
          {error}
        </div>
      ) : null}

      <div className="grid gap-5 lg:grid-cols-2">
        <section className="bh-card">
          <div className="bh-card-title">
            <h2>Practice scores</h2>
          </div>
          <p className="bh-card-note">
            These are demo practice scores for a typical quiz and assignment mix —
            not live Canvas grades. Use Fix this grade to set your own score before
            you build; only the priority level (needs work / getting there / on track)
            is sent when the plan is built.
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
                      {row.source} · {row.weight}% of exam ·{" "}
                      {WEAKNESS_LABEL[weaknessFromScore(row.score)]}
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
            Priority: <strong>{focus.topic}</strong> — highest exam weight among
            topics below 85%.
          </p>
        </section>

        <section className="bh-card">
          <div className="bh-card-title">
            <h2>Build plan</h2>
          </div>
          <p className="bh-card-note">
            Tell us how you learn so resources and the focus schedule match your style.
          </p>

          <label className="mt-3 block text-sm font-semibold text-aui-ink" htmlFor="rev-pref">
            How you learn
          </label>
          <select
            id="rev-pref"
            className="field-glass mt-1 w-full px-3 py-2 text-sm"
            value={preference}
            onChange={(event) => onPreference(event.target.value)}
          >
            {PREFERENCE_OPTIONS.map((opt) => (
              <option key={opt.id} value={opt.id}>
                {opt.label}
              </option>
            ))}
          </select>

          <label className="mt-3 block text-sm font-semibold text-aui-ink" htmlFor="rev-horizon">
            How many days until you need this plan
          </label>
          <select
            id="rev-horizon"
            className="field-glass mt-1 w-full px-3 py-2 text-sm"
            value={horizonMode}
            onChange={(event) => onHorizonMode(event.target.value)}
          >
            {HORIZON_OPTIONS.map((opt) => (
              <option key={opt.id} value={opt.id === "exam" ? "exam" : String(opt.days)}>
                {opt.label}
              </option>
            ))}
          </select>
          {horizonMode === "exam" ? (
            <label className="mt-2 block text-sm text-aui-ink" htmlFor="rev-exam-date">
              Exam date
              <input
                id="rev-exam-date"
                type="date"
                className="field-glass mt-1 w-full px-3 py-2 text-sm"
                value={examDate}
                onChange={(event) => onExamDate(event.target.value)}
              />
            </label>
          ) : null}
          <p className="mt-1 text-xs text-aui-deep/70">
            Choose the window before you build. The schedule fits inside these{" "}
            <strong>{horizonDays}</strong> day{horizonDays === 1 ? "" : "s"}
            {horizonMode === "exam" && examDate ? ` (until ${examDate})` : ""}.
          </p>

          <div className="mt-4 flex flex-wrap items-center gap-2">
            <button
              type="button"
              className="btn-primary px-4 py-2 text-sm"
              onClick={buildPlan}
              disabled={busy}
            >
              {busy ? "Building…" : "Build plan"}
            </button>
            {plan?.ask_draft ? (
              <button
                type="button"
                className="rounded-lg border border-aui-forest/30 bg-white px-4 py-2 text-sm font-semibold text-aui-forest"
                onClick={askTa}
                disabled={askBusy}
              >
                {askBusy ? "Sending…" : "Ask TA"}
              </button>
            ) : null}
          </div>

          {plan ? (
            <p className="mt-3 text-sm font-medium text-aui-ink">
              {planModeLabel(plan)}
            </p>
          ) : null}

          {slots.length ? (
            <>
              <p className="mt-4 text-xs text-aui-deep/70">
                Focus window: next{" "}
                <strong>
                  {Math.max(horizonDays, 1)} day
                  {horizonDays === 1 ? "" : "s"}
                </strong>
                {horizonMode === "exam" && examDate
                  ? ` until your exam on ${examDate}`
                  : " — the length you chose above"}
                {planWindowDays > 0 && planWindowDays !== horizonDays
                  ? ` (through day ${planWindowDays})`
                  : ""}
                . Days count from today.
              </p>
              <ol className="mt-2 space-y-2 text-sm">
                {slots.map((slot) => (
                  <li
                    key={`${slot.day_offset}-${slot.label}-${slot.topic}`}
                    className="rounded-lg border border-[#d7e0d9] bg-white px-3 py-2"
                  >
                    <strong>
                      Day {slot.day_offset} · {slot.minutes} min · {slot.label}
                    </strong>
                    <span className="mt-0.5 block text-xs text-aui-deep/70">
                      {slot.topic} — {slot.focus}
                    </span>
                  </li>
                ))}
              </ol>
            </>
          ) : (
            <p className="mt-4 text-sm text-aui-deep/70">
              Build a plan to see a short focus schedule for your weakest topics.
            </p>
          )}

          <div className="mt-4 rounded-lg border border-aui-forest/20 bg-[#f3faf5] p-3 text-xs">
            <p className="font-semibold text-aui-ink">Resources</p>
            {resources.filter((item) => item.url).length ? (
              <ol className="mt-2 list-decimal space-y-2 pl-4 text-aui-deep/85">
                {resources
                  .filter((item) => item.url)
                  .map((item) => (
                    <li key={`${item.source}-${item.title}-${item.url}`}>
                      <a
                        className="font-semibold text-aui-forest underline"
                        href={item.url}
                        target="_blank"
                        rel="noreferrer"
                      >
                        {item.title}
                      </a>
                      <span className="mt-0.5 block">
                        {item.source}
                        {item.why ? `. ${item.why}` : ""}
                      </span>
                    </li>
                  ))}
              </ol>
            ) : (
              <p className="mt-2 text-aui-deep/70">
                We couldn't find resources right now. Try again later.
              </p>
            )}
          </div>

          {visibleNotes.length ? (
            <ul className="mt-3 space-y-1 text-xs text-aui-deep/75">
              {visibleNotes.map((note) => (
                <li key={note}>{note}</li>
              ))}
            </ul>
          ) : null}
        </section>
      </div>
    </div>
  );
}
