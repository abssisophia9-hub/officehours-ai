import { useNavigate } from "react-router-dom";
import { useAuth } from "../auth/AuthContext.jsx";

const ROLE_PATH = {
  student: "/student",
  ta: "/ta",
  professor: "/professor",
};

const ROLE_COPY = {
  student: "Ask quietly, check status, and poke the approved KB agent.",
  ta: "Squish through the live queue and prep teaching drafts.",
  professor: "Command-center triage, FAQ drafts, and slide → KB magic.",
};

const ROLE_BLOB = {
  student: "clay-blob-mint",
  ta: "clay-blob-sky",
  professor: "clay-blob-butter",
};

export default function CourseHomePage() {
  const { user, setActiveCourse } = useAuth();
  const navigate = useNavigate();

  return (
    <section>
      <p className="glass-chip mb-4">Your soft campus map</p>
      <h1 className="font-display text-4xl font-bold sm:text-5xl">
        Hey {user.display_name.split(" ")[0]}
      </h1>
      <p className="mt-3 max-w-2xl text-lg font-semibold text-aui-deep/75">
        Tap a clay tile to enter a course. Your role can change by course — student
        here, TA there, no drama.
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
            <p className={`clay-blob ${ROLE_BLOB[course.role] || "clay-blob-mint"} px-3 py-1 text-xs font-extrabold uppercase`}>
              {course.role}
            </p>
            <h2 className="font-display mt-4 text-3xl font-bold">{course.code}</h2>
            <p className="mt-1 font-semibold text-aui-deep/80">{course.title}</p>
            <p className="mt-1 text-sm font-bold text-aui-deep/55">{course.term}</p>
            <p className="mt-4 text-sm font-semibold text-aui-deep/70">
              {ROLE_COPY[course.role]}
            </p>
          </button>
        ))}
      </div>
    </section>
  );
}
