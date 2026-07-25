import { useNavigate } from "react-router-dom";

/**
 * Stand-in for a real Canvas course page. In production the button below is
 * an LTI tool placement inside Canvas; clicking it launches OfficeHours AI
 * with the user's Canvas identity, course, and enrollment role.
 */
const CANVAS_COURSES = [
  {
    canvas_course_id: "2101",
    code: "CS 210",
    title: "Operating Systems",
    modules: ["Module 1 — Processes", "Module 2 — Scheduling"],
    note: "Brand-new course: first click provisions everything.",
    users: [
      {
        label: "Student — Omar Tazi",
        email: "o.tazi@aui.ma",
        display_name: "Omar Tazi",
        canvas_role: "StudentEnrollment",
        student_id: "118220",
      },
      {
        label: "Professor — Leila Mansouri",
        email: "l.mansouri@aui.ma",
        display_name: "Prof. Leila Mansouri",
        canvas_role: "TeacherEnrollment",
      },
    ],
  },
  {
    canvas_course_id: "4001",
    code: "CS 400",
    title: "Data Structures",
    modules: ["Module 4 — Hashing", "Module 5 — Trees"],
    note: "Existing course: launch joins it and reuses the agent.",
    users: [
      {
        label: "Student — Sara El Idrissi",
        email: "s.elidrissi@aui.ma",
        display_name: "Sara El Idrissi",
        canvas_role: "StudentEnrollment",
        student_id: "117400",
      },
    ],
  },
];

export default function CanvasSimulatorPage() {
  const navigate = useNavigate();

  function launch(course, person) {
    const params = new URLSearchParams({
      canvas_course_id: course.canvas_course_id,
      email: person.email,
      display_name: person.display_name,
      canvas_role: person.canvas_role,
    });
    if (person.student_id) params.set("student_id", person.student_id);
    navigate(`/launch?${params.toString()}`);
  }

  return (
    <div className="min-h-screen bg-[#f2f4f4] font-sans text-[#2d3b45]">
      {/* Canvas-style chrome */}
      <header className="bg-[#394b58] px-6 py-3 text-white">
        <p className="text-sm font-semibold tracking-wide">
          Canvas LMS · Al Akhawayn University{" "}
          <span className="ml-2 rounded bg-white/15 px-2 py-0.5 text-xs">
            simulator
          </span>
        </p>
      </header>

      <main className="mx-auto max-w-3xl px-6 py-8">
        <p className="text-sm text-[#2d3b45]/70">
          This page stands in for Canvas. Each course below has the
          <strong> OfficeHours AI</strong> tool installed — pick who is
          clicking it.
        </p>

        {CANVAS_COURSES.map((course) => (
          <section
            key={course.canvas_course_id}
            className="mt-6 rounded border border-[#c7cdd1] bg-white"
          >
            <div className="border-b border-[#c7cdd1] px-5 py-4">
              <h2 className="text-xl font-bold text-[#0374b5]">
                {course.code} — {course.title}
              </h2>
              <p className="mt-1 text-xs text-[#2d3b45]/60">{course.note}</p>
            </div>

            <div className="px-5 py-4">
              <h3 className="text-xs font-bold uppercase tracking-wide text-[#2d3b45]/60">
                Modules
              </h3>
              <ul className="mt-2 space-y-1">
                {course.modules.map((moduleName) => (
                  <li
                    key={moduleName}
                    className="rounded border border-[#e8eaec] bg-[#f7f8f9] px-3 py-2 text-sm"
                  >
                    {moduleName}
                  </li>
                ))}
              </ul>

              <h3 className="mt-5 text-xs font-bold uppercase tracking-wide text-[#2d3b45]/60">
                Course tools
              </h3>
              <div className="mt-2 rounded border border-[#e8eaec] px-3 py-3">
                <p className="text-sm font-semibold">OfficeHours AI</p>
                <p className="mt-0.5 text-xs text-[#2d3b45]/60">
                  Opens your course workspace and the course study agent.
                </p>
                <div className="mt-3 flex flex-wrap gap-2">
                  {course.users.map((person) => (
                    <button
                      key={person.email}
                      type="button"
                      className="rounded bg-[#0374b5] px-4 py-2 text-sm font-semibold text-white transition hover:bg-[#02669e]"
                      onClick={() => launch(course, person)}
                    >
                      Open as {person.label}
                    </button>
                  ))}
                </div>
              </div>
            </div>
          </section>
        ))}
      </main>
    </div>
  );
}
