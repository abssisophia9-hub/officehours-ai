import { useNavigate } from "react-router";
import { useAuth } from "../auth/AuthContext.jsx";
import { useUnstaffedCourses } from "../hooks/useUnstaffedCourses.js";

const ROLE_PATH = {
  student: "/student",
  ta: "/ta",
  professor: "/professor",
};

const ROLE_COPY = {
  student: "Ask quietly, check status, use Stuck Room with classmates, and the approved study agent.",
  ta: "Work the live queue and prepare teaching drafts for curation.",
  professor: "Approve course material, then see asks, insights, and your team.",
};

const ROLE_PILL = {
  student: "role-pill-student",
  ta: "role-pill-ta",
  professor: "role-pill-professor",
};

export default function CourseHomePage() {
  const { user, token, setActiveCourse } = useAuth();
  const unstaffed = useUnstaffedCourses(user.courses, token);
  const navigate = useNavigate();

  return (
    <section className="fade-up">
      <h1 className="bh-page-title">My Courses</h1>
      <p className="bh-page-subtitle">
        Choose a course workspace, {user.display_name.split(" ")[0]} — one role
        per course. TAs are staff on sections they already took.
      </p>

      <div className="mt-6 grid gap-4 md:grid-cols-2">
        {user.courses.map((course) => (
          <button
            key={`${course.id}-${course.role}`}
            type="button"
            className="glass-panel p-6 text-left"
            onClick={() => {
              setActiveCourse(course);
              navigate(ROLE_PATH[course.role] || "/");
            }}
          >
            <p className="course-card-tags">
              <span className={`role-pill ${ROLE_PILL[course.role] || "role-pill-student"}`}>
                {course.role}
              </span>
              {unstaffed.has(course.id) ? (
                <span className="course-nostaff">No staff</span>
              ) : null}
            </p>
            <h2 className="font-display mt-4 text-3xl font-semibold">
              {course.code}
            </h2>
            <p className="mt-1 font-medium text-aui-deep/80">{course.title}</p>
            <p className="mt-1 text-sm font-medium text-aui-deep/50">
              {course.term}
            </p>
            <p className="mt-4 text-sm font-medium text-aui-deep/65">
              {ROLE_COPY[course.role]}
            </p>
          </button>
        ))}
      </div>
    </section>
  );
}
