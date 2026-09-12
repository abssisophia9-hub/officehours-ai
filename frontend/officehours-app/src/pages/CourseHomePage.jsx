import { useNavigate } from "react-router";
import { useAuth } from "../auth/AuthContext.jsx";

const ROLE_PATH = {
  student: "/student",
  ta: "/ta",
  professor: "/professor",
};

const ROLE_COPY = {
  student: "Ask quietly, check status, use Stuck Room with classmates, and the approved study agent.",
  ta: "Work the live queue and prepare teaching drafts for curation.",
  professor: "Triage repeats, see chapter review insights, draft FAQs, and approve knowledge.",
};

const ROLE_PILL = {
  student: "role-pill-student",
  ta: "role-pill-ta",
  professor: "role-pill-professor",
};

export default function CourseHomePage() {
  const { user, setActiveCourse, logout } = useAuth();
  const navigate = useNavigate();

  async function switchAccount() {
    await logout();
    window.location.assign("/login?switch=1");
  }

  return (
    <section className="fade-up">
      <h1 className="bh-page-title">My Courses</h1>
      <p className="bh-page-subtitle">
        Choose a course workspace, {user.display_name.split(" ")[0]} — one role
        per course. TAs are staff on sections they already took.
      </p>
      <div className="mt-3 flex flex-wrap items-center gap-3">
        <button
          type="button"
          className="btn-primary px-4 py-2 text-sm"
          onClick={switchAccount}
          data-testid="switch-account-courses"
        >
          Switch account (Student / TA / Professor)
        </button>
        <p className="text-sm font-medium text-aui-deep/55">
          Use this between roles when demoing for a supervisor.
        </p>
      </div>

      <div className="mt-6 grid gap-4 md:grid-cols-2">
        {user.courses.map((course) => (
          <button
            key={`${course.id}-${course.role}`}
            type="button"
            className="glass-panel p-6 text-left"
            data-testid={`course-card-${course.code}-${course.role}`}
            onClick={() => {
              setActiveCourse(course);
              navigate(ROLE_PATH[course.role] || "/");
            }}
          >
            <p className={`role-pill ${ROLE_PILL[course.role] || "role-pill-student"}`}>
              {course.role}
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
