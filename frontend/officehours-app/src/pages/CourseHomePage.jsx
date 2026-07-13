import { useNavigate } from "react-router-dom";
import { useAuth } from "../auth/AuthContext.jsx";

const ROLE_PATH = {
  student: "/student",
  ta: "/ta",
  professor: "/professor",
};

const ROLE_COPY = {
  student: "Ask questions, check status, and use the approved KB agent.",
  ta: "Work the live queue and prepare teaching drafts for curation.",
  professor: "Triage requests, approve knowledge, and manage office hours.",
};

export default function CourseHomePage() {
  const { user, setActiveCourse } = useAuth();
  const navigate = useNavigate();

  return (
    <section>
      <p className="glass-chip mb-4">Your courses</p>
      <h1 className="font-display text-4xl font-bold">Welcome, {user.display_name}</h1>
      <p className="mt-3 max-w-2xl text-lg text-aui-deep/75">
        Pick a course workspace. Your role can differ by course — for example a
        student in CS 330 and a TA elsewhere.
      </p>

      <div className="mt-8 grid gap-4 md:grid-cols-2">
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
            <p className="glass-chip">{course.role}</p>
            <h2 className="font-display mt-3 text-2xl font-bold">
              {course.code}
            </h2>
            <p className="mt-1 text-aui-deep/80">{course.title}</p>
            <p className="mt-1 text-sm text-aui-deep/60">{course.term}</p>
            <p className="mt-4 text-sm text-aui-deep/70">
              {ROLE_COPY[course.role]}
            </p>
          </button>
        ))}
      </div>
    </section>
  );
}
