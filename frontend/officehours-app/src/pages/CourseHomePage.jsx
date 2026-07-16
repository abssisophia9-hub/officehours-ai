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

const ROLE_BLOB = {
  student: "clay-blob-mint",
  ta: "clay-blob-sky",
  professor: "clay-blob-butter",
};

const ROLE_FIGURE = {
  student: "/figures/student.png",
  ta: "/figures/ta.png",
  professor: "/figures/professor.png",
};

export default function CourseHomePage() {
  const { user, setActiveCourse } = useAuth();
  const navigate = useNavigate();

  return (
    <section>
      <div className="mb-8 grid items-center gap-6 lg:grid-cols-[1fr_280px]">
        <div>
          <p className="glass-chip mb-4">Your courses</p>
          <h1 className="font-display text-4xl font-bold sm:text-5xl">
            Welcome, {user.display_name.split(" ")[0]}
          </h1>
          <p className="mt-3 max-w-2xl text-lg font-semibold text-aui-deep/75">
            Choose a course workspace. Your role can differ by course — for
            example a student in CS 330 and a TA elsewhere.
          </p>
        </div>
        <img
          src="/figures/student.png"
          alt=""
          className="clay-hero-figure mx-auto max-h-56 w-auto lg:mx-0 lg:justify-self-end"
        />
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
            <div className="flex items-start justify-between gap-3">
              <p
                className={`clay-blob ${ROLE_BLOB[course.role] || "clay-blob-mint"} px-3 py-1 text-xs font-extrabold uppercase`}
              >
                {course.role}
              </p>
              <img
                src={ROLE_FIGURE[course.role] || "/figures/student.png"}
                alt=""
                className="h-16 w-16 rounded-2xl object-cover"
              />
            </div>
            <h2 className="font-display mt-3 text-3xl font-bold">{course.code}</h2>
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
