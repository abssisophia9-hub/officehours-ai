import { useState } from "react";
import { useNavigate } from "react-router";

/**
 * Stand-in for Canvas LMS (we have no AUI Canvas credentials in dev).
 *
 * Models reality: you are signed in to Canvas as ONE person, you see the
 * courses you are enrolled in, and each course has ONE "Open OfficeHours AI"
 * tool button. Your role in the launch comes from your Canvas enrollment —
 * never from a choice on the page. The account switcher below stands in for
 * logging into Canvas as someone else.
 */
const PERSONAS = [
  {
    id: "omar",
    label: "Omar Tazi (student)",
    email: "o.tazi@aui.ma",
    display_name: "Omar Tazi",
    student_id: "118220",
    enrollments: [
      { canvas_course_id: "2101", canvas_role: "StudentEnrollment" },
    ],
  },
  {
    // TAs are also students: Karim TAs OS and takes Data Structures as a student.
    id: "karim",
    label: "Karim Bennis (TA + student)",
    email: "k.bennis@aui.ma",
    display_name: "Karim Bennis",
    student_id: "118310",
    enrollments: [
      { canvas_course_id: "2101", canvas_role: "TaEnrollment" },
      { canvas_course_id: "4001", canvas_role: "StudentEnrollment" },
    ],
  },
  {
    id: "leila",
    label: "Prof. Leila Mansouri (teacher)",
    email: "l.mansouri@aui.ma",
    display_name: "Prof. Leila Mansouri",
    enrollments: [
      { canvas_course_id: "2101", canvas_role: "TeacherEnrollment" },
    ],
  },
  {
    id: "sara",
    label: "Sara El Idrissi (student)",
    email: "s.elidrissi@aui.ma",
    display_name: "Sara El Idrissi",
    student_id: "117400",
    enrollments: [
      { canvas_course_id: "4001", canvas_role: "StudentEnrollment" },
      { canvas_course_id: "3301", canvas_role: "StudentEnrollment" },
      { canvas_course_id: "3374", canvas_role: "StudentEnrollment" },
    ],
  },
];

const COURSES = {
  2101: {
    code: "CSC 3351",
    title: "Operating Systems",
    modules: ["Module 1 — Processes", "Module 2 — Scheduling"],
  },
  4001: {
    code: "CSC 2302",
    title: "Data Structures",
    modules: ["Module 4 — Hashing", "Module 5 — Trees"],
  },
  3301: {
    code: "CSC 3323",
    title: "Analysis of Algorithms",
    modules: ["Module 2 — Divide & Conquer"],
  },
  3374: {
    code: "CSC 3374",
    title: "Adv. Distributed Programming Paradigms",
    modules: ["Module 1 — Message Passing"],
  },
};

const ROLE_LABEL = {
  StudentEnrollment: "Student",
  TaEnrollment: "TA",
  TeacherEnrollment: "Teacher",
};

export default function CanvasSimulatorPage() {
  const navigate = useNavigate();
  const [personaId, setPersonaId] = useState(PERSONAS[0].id);
  const persona = PERSONAS.find((item) => item.id === personaId);

  function launch(enrollment) {
    const params = new URLSearchParams({
      canvas_course_id: enrollment.canvas_course_id,
      email: persona.email,
      display_name: persona.display_name,
      canvas_role: enrollment.canvas_role,
    });
    if (persona.student_id) params.set("student_id", persona.student_id);
    navigate(`/launch?${params.toString()}`);
  }

  return (
    <div className="min-h-screen bg-[#f2f4f4] font-sans text-[#2d3b45]">
      {/* Canvas-style chrome */}
      <header className="flex items-center justify-between bg-[#394b58] px-6 py-3 text-white">
        <p className="text-sm font-semibold tracking-wide">
          Canvas LMS · Al Akhawayn University{" "}
          <span className="ml-2 rounded bg-white/15 px-2 py-0.5 text-xs">
            simulator
          </span>
        </p>
        <label className="flex items-center gap-2 text-xs font-medium text-white/80">
          Signed in as
          <select
            className="rounded border border-white/25 bg-[#2d3b45] px-2 py-1 text-sm font-semibold text-white"
            value={personaId}
            onChange={(event) => setPersonaId(event.target.value)}
          >
            {PERSONAS.map((item) => (
              <option key={item.id} value={item.id}>
                {item.label}
              </option>
            ))}
          </select>
        </label>
      </header>

      <main className="mx-auto max-w-3xl px-6 py-8">
        <h1 className="text-2xl font-bold">Dashboard</h1>
        <p className="mt-1 text-sm text-[#2d3b45]/70">
          In real Canvas you are already signed in — the switcher above stands
          in for that. You only see courses you are enrolled in. Role is per
          course (a TA can also be a student elsewhere).
        </p>

        {persona.enrollments.map((enrollment) => {
          const course = COURSES[enrollment.canvas_course_id];
          return (
            <section
              key={enrollment.canvas_course_id}
              className="mt-6 rounded border border-[#c7cdd1] bg-white"
            >
              <div className="border-b border-[#c7cdd1] px-5 py-4">
                <h2 className="text-xl font-bold text-[#0374b5]">
                  {course.code} — {course.title}
                </h2>
                <p className="mt-1 text-xs text-[#2d3b45]/60">
                  Enrolled as{" "}
                  <strong>{ROLE_LABEL[enrollment.canvas_role]}</strong>
                </p>
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
                <div className="mt-2 flex items-center justify-between rounded border border-[#e8eaec] px-3 py-3">
                  <div>
                    <p className="text-sm font-semibold">OfficeHours AI</p>
                    <p className="mt-0.5 text-xs text-[#2d3b45]/60">
                      Opens your course workspace and the course study agent.
                    </p>
                  </div>
                  <button
                    type="button"
                    className="rounded bg-[#0374b5] px-4 py-2 text-sm font-semibold text-white transition hover:bg-[#02669e]"
                    onClick={() => launch(enrollment)}
                  >
                    Open OfficeHours AI
                  </button>
                </div>
              </div>
            </section>
          );
        })}
      </main>
    </div>
  );
}
