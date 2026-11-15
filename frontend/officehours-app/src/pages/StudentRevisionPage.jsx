import { useEffect, useMemo, useState } from "react";
import { ExternalLink } from "lucide-react";
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
  { topic: "Main ideas from class", weight: 30, score: 68, source: "Demo sample · Quiz", assignment_kind: "text" },
  { topic: "Homework problems", weight: 30, score: 74, source: "Demo sample · Assignment", assignment_kind: "text" },
  { topic: "Exam review topics", weight: 25, score: 71, source: "Demo sample · Midterm prep", assignment_kind: "text" },
  { topic: "Labs and project work", weight: 15, score: 80, source: "Demo sample · Lab", assignment_kind: "project" },
];

/** Plan duration bounds (days). Custom values clamp to this range. */
export const PLAN_DURATION_MIN = 1;
export const PLAN_DURATION_MAX = 60;
export const PLAN_DURATION_DEFAULT = 7;

const DURATION_PRESETS = [
  { id: "3", days: 3, label: "3 days" },
  { id: "7", days: 7, label: "1 week" },
  { id: "14", days: 14, label: "2 weeks" },
  { id: "30", days: 30, label: "1 month" },
];

function clampPlanDays(value) {
  const n = Math.round(Number(value));
  if (!Number.isFinite(n)) return PLAN_DURATION_DEFAULT;
  return Math.max(PLAN_DURATION_MIN, Math.min(PLAN_DURATION_MAX, n));
}

function durationModeForDays(days) {
  const clamped = clampPlanDays(days);
  if (DURATION_PRESETS.some((opt) => opt.days === clamped)) {
    return { mode: String(clamped), days: clamped };
  }
  return { mode: "custom", days: clamped };
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
  // Resources box already shows the empty-state sentence - don't repeat it under notes.
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

function durationKey(courseId) {
  return `officehours_revision_duration_${courseId}`;
}

function legacyHorizonKey(courseId) {
  return `officehours_revision_horizon_${courseId}`;
}

function loadDurationState(courseId) {
  try {
    const raw =
      localStorage.getItem(durationKey(courseId)) ??
      localStorage.getItem(legacyHorizonKey(courseId));
    if (raw && raw !== "exam" && raw !== "custom") {
      const days = Number(raw);
      if (Number.isFinite(days) && days >= PLAN_DURATION_MIN) {
        return durationModeForDays(days);
      }
    }
    if (raw === "custom") {
      const customRaw = localStorage.getItem(`${durationKey(courseId)}_custom`);
      const days = clampPlanDays(customRaw || PLAN_DURATION_DEFAULT);
      return { mode: "custom", days };
    }
  } catch {
    // default
  }
  return durationModeForDays(PLAN_DURATION_DEFAULT);
}

function saveDurationState(courseId, mode, days) {
  const clamped = clampPlanDays(days);
  if (mode === "custom") {
    localStorage.setItem(durationKey(courseId), "custom");
    localStorage.setItem(`${durationKey(courseId)}_custom`, String(clamped));
  } else {
    localStorage.setItem(durationKey(courseId), String(clamped));
    localStorage.removeItem(`${durationKey(courseId)}_custom`);
  }
  // Drop legacy "days until / exam" keys so old copy cannot resurface.
  localStorage.removeItem(legacyHorizonKey(courseId));
  localStorage.removeItem(`officehours_revision_exam_${courseId}`);
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

function planDeadlines(grades, planDays) {
  const horizon = clampPlanDays(planDays);
  const ranked = [...grades].sort((a, b) => gap(b) - gap(a));
  const weak = ranked.filter((row) => row.score < 85);
  const focus = (weak.length ? weak : ranked).slice(0, 3);
  // Primary (weakest) lands on the chosen plan end so length matches exactly.
  return focus.map((row, index) => {
    const due = Math.round(((focus.length - index) / focus.length) * horizon);
    return {
      topic: row.topic,
      due_in_days: Math.max(PLAN_DURATION_MIN, Math.min(horizon, due || horizon)),
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
  const [durationMode, setDurationMode] = useState(String(PLAN_DURATION_DEFAULT));
  const [planDays, setPlanDays] = useState(PLAN_DURATION_DEFAULT);
  const [customDaysDraft, setCustomDaysDraft] = useState(String(PLAN_DURATION_DEFAULT));
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
    const duration = loadDurationState(activeCourse.id);
    setDurationMode(duration.mode);
    setPlanDays(duration.days);
    setCustomDaysDraft(String(duration.days));
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

  function onDurationMode(value) {
    if (value === "custom") {
      const days = clampPlanDays(customDaysDraft || planDays);
      setDurationMode("custom");
      setPlanDays(days);
      setCustomDaysDraft(String(days));
      saveDurationState(activeCourse.id, "custom", days);
      return;
    }
    const days = clampPlanDays(value);
    setDurationMode(String(days));
    setPlanDays(days);
    setCustomDaysDraft(String(days));
    saveDurationState(activeCourse.id, String(days), days);
  }

  function onCustomDays(value) {
    setCustomDaysDraft(value);
    const parsed = Number(value);
    if (!Number.isFinite(parsed)) return;
    const days = clampPlanDays(parsed);
    setDurationMode("custom");
    setPlanDays(days);
    saveDurationState(activeCourse.id, "custom", days);
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
      // Read duration from the live control so the plan length always matches
      // the picker, even if a state update is still flushing.
      const selectEl = document.getElementById("rev-duration");
      const customEl = document.getElementById("rev-duration-custom");
      const selected = selectEl?.value || durationMode;
      const liveDays = clampPlanDays(
        selected === "custom"
          ? customEl?.value || customDaysDraft || planDays
          : selected || planDays,
      );
      if (liveDays !== planDays) setPlanDays(liveDays);
      const body = {
        course_id: activeCourse.id,
        preference,
        available_minutes_today: 120,
        deadlines: planDeadlines(grades, liveDays),
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
  const planWindowDays = Math.max(
    PLAN_DURATION_MIN,
    slots.reduce((max, slot) => Math.max(max, Number(slot.day_offset) || 0), 0),
  );
  const focusDays = clampPlanDays(planDays);

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
            These are demo practice scores for a typical quiz and assignment mix  - 
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
            Priority: <strong>{focus.topic}</strong> - highest exam weight among
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

          <label className="mt-3 block text-sm font-semibold text-aui-ink" htmlFor="rev-duration">
            How long should your plan be?
          </label>
          <select
            id="rev-duration"
            className="field-glass mt-1 w-full px-3 py-2 text-sm"
            value={durationMode}
            onChange={(event) => onDurationMode(event.target.value)}
          >
            {DURATION_PRESETS.map((opt) => (
              <option key={opt.id} value={String(opt.days)}>
                {opt.label}
              </option>
            ))}
            <option value="custom">Custom days</option>
          </select>
          {durationMode === "custom" ? (
            <label className="mt-2 block text-sm text-aui-ink" htmlFor="rev-duration-custom">
              Custom length (days)
              <input
                id="rev-duration-custom"
                type="number"
                min={PLAN_DURATION_MIN}
                max={PLAN_DURATION_MAX}
                className="field-glass mt-1 w-full px-3 py-2 text-sm"
                value={customDaysDraft}
                onChange={(event) => onCustomDays(event.target.value)}
              />
            </label>
          ) : null}
          <p className="mt-1 text-xs text-aui-deep/70">
            Your plan will fit inside this time.
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
                Focus window:{" "}
                <strong>
                  {focusDays} day
                  {focusDays === 1 ? "" : "s"}
                </strong>{" "}
                — Day 1 is today
                {planWindowDays > 0 && planWindowDays !== focusDays
                  ? ` (plan lists ${planWindowDays} days)`
                  : ""}
                . Self-check sits on the last day.
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
                      {slot.topic}: {slot.focus}
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
              <ol className="mt-2 list-decimal space-y-3 pl-4 text-aui-deep/85">
                {resources
                  .filter((item) => item.url)
                  .map((item) => (
                    <li key={`${item.source}-${item.title}-${item.url}`}>
                      <div className="flex flex-wrap items-baseline gap-x-2 gap-y-1">
                        <a
                          className="font-semibold text-aui-forest underline underline-offset-2"
                          href={item.url}
                          target="_blank"
                          rel="noopener noreferrer"
                        >
                          {item.title}
                        </a>
                        <a
                          className="inline-flex items-center gap-1 text-xs font-semibold text-aui-forest/90 underline underline-offset-2"
                          href={item.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          aria-label={`Open ${item.title}`}
                        >
                          Open
                          <ExternalLink className="size-3.5 shrink-0" aria-hidden="true" />
                        </a>
                      </div>
                      <span className="mt-0.5 block text-xs text-aui-deep/75">
                        {item.source}
                        {item.channel ? (
                          <span className="text-aui-deep/55"> · {item.channel}</span>
                        ) : null}
                      </span>
                      {item.why ? (
                        <span className="mt-0.5 block text-xs text-aui-deep/70">
                          {item.why}
                        </span>
                      ) : null}
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
