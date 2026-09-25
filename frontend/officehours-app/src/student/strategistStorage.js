const GRADES_KEY = (courseId) => `officehours_revision_${courseId}`;
const PLAN_KEY = (courseId) => `officehours_strategist_plan_${courseId}`;

export function loadRevision(courseId) {
  try {
    const raw = localStorage.getItem(GRADES_KEY(courseId));
    if (!raw) return null;
    const parsed = JSON.parse(raw);
    if (!Array.isArray(parsed?.grades) || !parsed.grades.length) return null;
    return {
      grades: parsed.grades,
      loggedScore: parsed.loggedScore ?? null,
      loggedTopic: parsed.loggedTopic ?? null,
      goal: parsed.goal ?? "",
    };
  } catch {
    return null;
  }
}

export function saveRevision(courseId, payload) {
  localStorage.setItem(GRADES_KEY(courseId), JSON.stringify(payload));
}

export function loadStrategistPlan(courseId) {
  try {
    const raw = localStorage.getItem(PLAN_KEY(courseId));
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

export function saveStrategistPlan(courseId, plan) {
  if (!plan) return;
  localStorage.setItem(PLAN_KEY(courseId), JSON.stringify(plan));
}
