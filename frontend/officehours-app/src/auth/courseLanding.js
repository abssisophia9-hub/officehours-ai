const MAP_KEY = "officehours_active_course_by_user";
const LEGACY_KEY = "officehours_active_course";

function readMap() {
  try {
    const parsed = JSON.parse(localStorage.getItem(MAP_KEY) || "{}");
    return parsed && typeof parsed === "object" ? parsed : {};
  } catch {
    return {};
  }
}

function writeMap(map) {
  localStorage.setItem(MAP_KEY, JSON.stringify(map));
}

export function clearLegacyCourseKey() {
  localStorage.removeItem(LEGACY_KEY);
}

export function rememberCourse(userId, course) {
  if (!userId || !course?.id) return;
  const map = readMap();
  const key = String(userId);
  const prev = map[key] && typeof map[key] === "object" ? map[key] : {};
  const entry = { ...prev, courseId: String(course.id) };
  if (course.role === "professor" || course.role === "ta") {
    entry.staffCourseId = String(course.id);
  } else {
    entry.studentCourseId = String(course.id);
  }
  map[key] = entry;
  writeMap(map);
  clearLegacyCourseKey();
}

export function forgetCourse(userId) {
  clearLegacyCourseKey();
  if (!userId) {
    localStorage.removeItem(MAP_KEY);
    return;
  }
  const map = readMap();
  delete map[String(userId)];
  writeMap(map);
}

function isStaff(course) {
  return course?.role === "professor" || course?.role === "ta";
}

function courseById(courses, id) {
  if (id == null || id === "") return null;
  return courses.find((course) => String(course.id) === String(id)) || null;
}

/**
 * Where this person should open.
 * Login passes preferStaff so a TA or professor does not land in a student course.
 * A reload restores the course they last selected.
 */
export function landingCourse(user, { preferStaff = false } = {}) {
  const courses = user?.courses || [];
  if (!courses.length) return null;
  const saved = readMap()[String(user.id)] || {};
  const staff = courses.filter(isStaff);
  if (preferStaff && staff.length) {
    return courseById(courses, saved.staffCourseId) || staff[0];
  }
  return (
    courseById(courses, saved.courseId) ||
    (staff.length ? courseById(courses, saved.staffCourseId) || staff[0] : null) ||
    courseById(courses, saved.studentCourseId) ||
    courses[0]
  );
}

export function coursePath(course) {
  if (!course) return "/";
  if (course.role === "professor") return "/professor";
  if (course.role === "ta") return "/ta";
  return "/student";
}
