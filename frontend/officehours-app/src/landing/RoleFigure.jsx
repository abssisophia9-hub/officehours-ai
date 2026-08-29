const ROLE_COPY = [
  {
    id: "student",
    label: "Student",
    kicker: "01 · Student",
    tools: "Quiet ask · Rooms",
    title: "You do not perform in front of the room.",
    lead: "Private path to staff, or a named room for classmates. The product starts with the stuck student.",
    body: (
      <>
        <p>
          <strong>Quiet ask</strong> goes to staff without putting your name on a
          public board — the private path when the question is sensitive, or you
          just are not ready to be seen.
        </p>
        <p>
          <strong>Identify me</strong> when you want a meeting.{" "}
          <strong>Rooms</strong> are named on purpose: classmates help classmates,
          and that help can show up on the Hilbert board. Staff do not lurk there.
        </p>
      </>
    ),
  },
  {
    id: "ta",
    label: "TA",
    kicker: "02 · Teaching assistant",
    tools: "Queue · Help Coach",
    title: "A queue, not a pile.",
    lead: "Ask Triage routes the card. You claim it. Repeated concepts can become one group meeting.",
    body: (
      <>
        <p>
          <strong>Ask Triage</strong> classifies the ask as it comes in. You claim
          it, then <strong>Help Coach</strong> sits with you — similar opens,
          Socratic steps, a draft you still have to own.
        </p>
        <p>
          When the same concept clusters, one shared group meeting can replace
          twenty 1:1s. Same login if you are a student in another course.
        </p>
      </>
    ),
  },
  {
    id: "professor",
    label: "Professor",
    kicker: "03 · Professor",
    tools: "Insights · KB gate",
    title: "You stay the gate.",
    lead: "Review insights from asks + Rooms. Stamp a FAQ before the Study Agent may repeat it.",
    body: (
      <>
        <p>
          Clusters and <strong>review insights</strong> show what the week
          actually confused people — Quiet asks plus Rooms chapters, not a vanity
          dashboard.
        </p>
        <p>
          Approve a FAQ and the Study Agent may say it next time. Sync Canvas
          modules and those names become Rooms chapters. Nothing enters the
          student knowledge base until you say so.
        </p>
      </>
    ),
  },
];

export const ROLES = ROLE_COPY;

function StudentObjects() {
  return (
    <>
      <span className="oh-obj oh-obj-ask">
        <span className="oh-obj-pin" />
        <span className="oh-obj-line" />
        <span className="oh-obj-line short" />
        <span className="oh-obj-tag">Quiet</span>
      </span>
      <span className="oh-obj oh-obj-rooms">
        <span className="oh-obj-minihead" />
        <span className="oh-obj-minihead oh-obj-minihead-2" />
        <span className="oh-obj-tag">Rooms</span>
      </span>
    </>
  );
}

function TaObjects() {
  return (
    <>
      <span className="oh-obj oh-obj-queue">
        <span className="oh-obj-slip n1">1</span>
        <span className="oh-obj-slip n2">2</span>
        <span className="oh-obj-slip n3">3</span>
      </span>
      <span className="oh-obj oh-obj-coach">
        Coach
      </span>
    </>
  );
}

function ProfessorObjects() {
  return (
    <>
      <span className="oh-obj oh-obj-bars">
        <span className="oh-obj-bar-set">
          <span />
          <span />
          <span />
        </span>
        <span className="oh-obj-tag">Insights</span>
      </span>
      <span className="oh-obj oh-obj-stamp">
        <span className="oh-obj-check" />
        <span className="oh-obj-tag">KB</span>
      </span>
    </>
  );
}

export default function RoleFigure({
  role,
  active = false,
  size = "lg",
  onClick,
  showTools = true,
}) {
  const data = typeof role === "string" ? ROLES.find((item) => item.id === role) : role;
  if (!data) return null;

  return (
    <button
      type="button"
      className={`oh-fig oh-fig-${data.id} oh-fig-${size} ${active ? "is-on" : ""}`}
      onClick={onClick}
      aria-pressed={active}
      aria-label={`${data.label}. ${data.tools}`}
    >
      <span className="oh-fig-art" aria-hidden="true">
        <span className="oh-fig-floor" />
        {data.id === "student" ? <StudentObjects /> : null}
        {data.id === "ta" ? <TaObjects /> : null}
        {data.id === "professor" ? <ProfessorObjects /> : null}
        <span className="oh-fig-person">
          <span className="oh-fig-head" />
          <span className="oh-fig-torso" />
          <span className="oh-fig-arm oh-fig-arm-l" />
          <span className="oh-fig-arm oh-fig-arm-r" />
        </span>
      </span>
      <span className="oh-fig-meta">
        <span className="oh-fig-name">{data.label}</span>
        {showTools ? <span className="oh-fig-tools">{data.tools}</span> : null}
      </span>
    </button>
  );
}
