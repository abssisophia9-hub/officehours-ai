import { useNavigate } from "react-router-dom";
import { useAuth } from "../auth/AuthContext.jsx";

const ROLE_PATH = {
  student: "/student",
  ta: "/ta",
  professor: "/professor",
};

const ROLE_COPY = {
  student: "Ask quietly, check status, and use the approved KB agent.",
  ta: "Work the live queue and prepare teaching drafts for curation.",
  professor: "Triage repeats, draft FAQs, and approve knowledge for students.",
};

const ROLE_PILL = {
  student: "role-pill-student",
  ta: "role-pill-ta",
  professor: "role-pill-professor",
};

export default function CourseHomePage() {
  const { user, setActiveCourse } = useAuth();
  const navigate = useNavigate();

  return (
    <section className="fade-up">
      <div className="mb-8 max-w-2xl">
        <p className="glass-chip mb-4">Your courses</p>
        <h1 className="font-display text-4xl font-semibold sm:text-5xl">
          Welcome, {user.display_name.split(" ")[0]}
        </h1>
        <p className="mt-3 text-base font-medium text-aui-deep/70">
          Choose a course workspace. Your role can differ by course — for
          example a student in CS 330 and a TA elsewhere.
        </p>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
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
            <p
              className={`role-pill ${ROLE_PILL[course.role] || "role-pill-student"}`}
            >
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
