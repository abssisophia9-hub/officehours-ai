import { useEffect, useMemo, useState } from "react";
import "./capstone-poster.css";

const STACK = [
  "React",
  "Vite",
  "FastAPI",
  "SQLAlchemy",
  "SQLite/PostgreSQL",
  "MiniLM",
  "scikit-learn",
  "Gemini",
  "Canvas LTI/API",
  "YouTube Data API",
];

const ARCH_NODES = [
  {
    id: "canvas",
    label: "Canvas LMS Sync",
    sub: "Materials · Grades · LTI 1.3",
    x: 28,
    y: 18,
    w: 168,
    h: 58,
    accent: "canvas",
  },
  {
    id: "client",
    label: "Multi-Role Client",
    sub: "Student · TA · Professor",
    x: 230,
    y: 18,
    w: 168,
    h: 58,
    accent: "ink",
  },
  {
    id: "api",
    label: "FastAPI Orchestrator",
    sub: "CallerContext · routers",
    x: 432,
    y: 18,
    w: 176,
    h: 58,
    accent: "emerald",
  },
  {
    id: "rag",
    label: "Professor-Gated RAG",
    sub: "Approved chunks only",
    x: 28,
    y: 108,
    w: 168,
    h: 58,
    accent: "emerald",
  },
  {
    id: "sla",
    label: "Escalation & SLA",
    sub: "State machine · timers",
    x: 214,
    y: 108,
    w: 168,
    h: 58,
    accent: "brass",
  },
  {
    id: "coach",
    label: "TA Pedagogical Coach",
    sub: "Help Coach mid-reply",
    x: 400,
    y: 108,
    w: 176,
    h: 58,
    accent: "brass",
  },
  {
    id: "planner",
    label: "Study Planner",
    sub: "Grades · style · scrape",
    x: 594,
    y: 108,
    w: 156,
    h: 58,
    accent: "canvas",
  },
  {
    id: "db",
    label: "DB & Analytics",
    sub: "Support · Knowledge · Identity",
    x: 300,
    y: 198,
    w: 190,
    h: 52,
    accent: "ink",
  },
];

const NODE_DETAILS = {
  canvas: {
    title: "Canvas LMS Sync",
    inputs: "LTI 1.3 launch · NRPS roster · Files API · Grades API",
    logic:
      "Syncs approved course materials and grade gaps into Knowledge / Pedagogy paths. Session course_id comes from secure launch context, never from the model.",
    guardrails:
      "Read-only roster sync · course-scoped material · demo vs live Canvas via OFFICEHOURS_DEMO",
  },
  client: {
    title: "Multi-Role Client",
    inputs: "Session cookie · active course membership · role per course",
    logic:
      "One React SPA (officehours-app): student pathways, TA desk with Help Coach, professor Material / Insights / Team. No business logic in the browser beyond presentation.",
    guardrails: "Role gates on routes · Quiet ask privacy · staff ≠ student of same course",
  },
  api: {
    title: "FastAPI Orchestrator",
    inputs: "HTTPS/JSON · WebSocket /ws · CallerContext(user, course, role, course_has_ta)",
    logic:
      "Registers auth, knowledge, requests, live, revision, and help-room routers. Modules call each other through service interfaces—not foreign table scans.",
    guardrails: "Rate limits · validation · course_id from session only",
  },
  rag: {
    title: "Professor-Gated Study Agent (RAG)",
    inputs: "Student question · approved KB chunks · MiniLM / lexical retrieval",
    logic:
      "Retrieves only professor-stamped material for the caller’s course, then optional Gemini answer-check. Misses share one refusal sentence—no invented syllabus.",
    guardrails:
      "0% unapproved / other-course citation in gated eval (10/10 + 10/10) · answer-check 74/75 overall",
  },
  sla: {
    title: "Escalation & SLA State Machine",
    inputs: "Ask Triage matcher · course TA roster · estimated_wait_minutes",
    logic:
      "Tracks open → claimed → in_progress → answered with live wait timers on the TA desk. If the course has 0 TAs, assign_professor_when_no_ta routes to the professor.",
    guardrails: "test_no_ta_routing PASS · no inventing demo TAs on real courses",
  },
  coach: {
    title: "AI TA Pedagogical Coach (Help Coach)",
    inputs: "Open ask text · similar open asks · approved KB neighbors · ask kind",
    logic:
      "While the TA drafts a reply, Help Coach suggests structured teaching moves (Socratic steps, clarify vs bank_rag) without auto-dumping into the reply box.",
    guardrails: "Insert into Reply is explicit · local coaching path · mid-session only",
  },
  planner: {
    title: "Adaptive Web-Scraping Study Planner",
    inputs: "Canvas grades · preference (visual / step-by-step / examples) · custom duration",
    logic:
      "Pedagogy Agent ranks weak topics, searches YouTube/web with caps, and returns a timed plan. Scores never leak back to the client payload.",
    guardrails: "Token/search caps · link_ok checks · PEDAGOGY_GEMINI_API_KEY split · no score echo",
  },
  db: {
    title: "Relational DB & Analytics",
    inputs: "SQLAlchemy models · identity / knowledge / support schemas",
    logic:
      "SQLite for local FYP; PostgreSQL for campus. Professor Insights aggregates ask volume, recurring confusion topics, and overdue SLA rows.",
    guardrails: "Module table isolation · create_all on boot · DEMO seed accounts optional",
  },
};

const BENCHMARKS = [
  {
    metric: "Unapproved-source refusal",
    value: "100%",
    note: "10/10 unapproved + 10/10 other-course",
  },
  {
    metric: "Study answer-check (gated)",
    value: "74/75",
    note: "98.7% · Gemini check suite",
  },
  {
    metric: "0-TA auto-fallback routing",
    value: "PASS",
    note: "test_no_ta_routing",
  },
  {
    metric: "Ask Triage macro F1",
    value: "84.6%",
    note: "5-fold CV · n=156",
  },
  {
    metric: "Ask Triage latency p50",
    value: "~30 ms",
    note: "warm local ML · Part 4 n=10",
  },
  {
    metric: "Grade-gap planner E2E",
    value: "PASS",
    note: "revision/plan + resource search",
  },
];

const TOPIC_BARS = [
  { topic: "Hash Tables", count: 18, color: "#006838" },
  { topic: "Recursion", count: 14, color: "#008EE2" },
  { topic: "Red-Black Trees", count: 11, color: "#C59B5F" },
  { topic: "Exam Logistics", count: 9, color: "#2D3B45" },
  { topic: "Project Submit", count: 7, color: "#5A8F72" },
];

const VOLUME = [
  { d: "Mon", v: 12 },
  { d: "Tue", v: 19 },
  { d: "Wed", v: 15 },
  { d: "Thu", v: 22 },
  { d: "Fri", v: 17 },
  { d: "Sat", v: 6 },
  { d: "Sun", v: 8 },
];

function ArchDiagram({ activeId, onSelect }) {
  // Orthogonal pipeline: Canvas → Client → API → four cores → DB
  const paths = [
    "M 196 47 H 230",
    "M 398 47 H 432",
    "M 520 76 V 92 H 112 V 108",
    "M 520 92 H 298 V 108",
    "M 520 92 H 488 V 108",
    "M 520 92 H 672 V 108",
    "M 112 166 V 184 H 395 V 198",
    "M 298 166 V 184 H 395",
    "M 488 166 V 184 H 395",
    "M 672 166 V 184 H 490",
  ];

  return (
    <svg
      className="cfc-arch-svg"
      viewBox="0 0 780 270"
      role="group"
      aria-label="End-to-end system architecture"
    >
      {paths.map((d, i) => (
        <path key={i} d={d} className="cfc-arch-edge" />
      ))}
      {ARCH_NODES.map((node) => {
        const active = activeId === node.id;
        return (
          <g
            key={node.id}
            className={`cfc-arch-node cfc-arch-node--${node.accent}${active ? " is-active" : ""}`}
            transform={`translate(${node.x} ${node.y})`}
          >
            <rect
              width={node.w}
              height={node.h}
              rx="6"
              ry="6"
              role="button"
              tabIndex={0}
              aria-pressed={active}
              aria-label={node.label}
              onClick={(e) => {
                e.stopPropagation();
                onSelect(node.id);
              }}
              onKeyDown={(e) => {
                if (e.key === "Enter" || e.key === " ") {
                  e.preventDefault();
                  onSelect(node.id);
                }
              }}
              style={{ cursor: "pointer" }}
            />
            <text className="cfc-arch-label" x={10} y={24} pointerEvents="none">
              {node.label}
            </text>
            <text className="cfc-arch-sub" x={10} y={42} pointerEvents="none">
              {node.sub}
            </text>
          </g>
        );
      })}
    </svg>
  );
}

function AnalyticsPanel() {
  const maxTopic = Math.max(...TOPIC_BARS.map((t) => t.count));
  const maxVol = Math.max(...VOLUME.map((v) => v.v));
  return (
    <div className="cfc-analytics">
      <div className="cfc-analytics-head">
        <span>Demo course · CSC 2302</span>
        <span className="cfc-mono">mean resolve 42m · SLA open 3</span>
      </div>
      <div className="cfc-analytics-grid">
        <div>
          <div className="cfc-mini-label">Recurring confusion topics</div>
          <ul className="cfc-bars">
            {TOPIC_BARS.map((row) => (
              <li key={row.topic}>
                <span className="cfc-bar-label">{row.topic}</span>
                <span className="cfc-bar-track">
                  <span
                    className="cfc-bar-fill"
                    style={{
                      width: `${(row.count / maxTopic) * 100}%`,
                      background: row.color,
                    }}
                  />
                </span>
                <span className="cfc-mono cfc-bar-n">{row.count}</span>
              </li>
            ))}
          </ul>
        </div>
        <div>
          <div className="cfc-mini-label">Ask volume (7d)</div>
          <div className="cfc-vol">
            {VOLUME.map((row) => (
              <div key={row.d} className="cfc-vol-col">
                <div
                  className="cfc-vol-bar"
                  style={{ height: `${(row.v / maxVol) * 100}%` }}
                  title={`${row.v} asks`}
                />
                <span>{row.d}</span>
              </div>
            ))}
          </div>
          <div className="cfc-sla-row">
            <div>
              <strong>99</strong>
              <span>asks / week</span>
            </div>
            <div>
              <strong>42m</strong>
              <span>mean resolve</span>
            </div>
            <div>
              <strong>3</strong>
              <span>overdue SLA</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default function CapstonePosterPage() {
  const [active, setActive] = useState("coach");
  const [fit, setFit] = useState({ scale: 1, mx: 0, my: 0 });
  const detail = NODE_DETAILS[active];

  useEffect(() => {
    document.documentElement.setAttribute("data-theme", "light");
    document.body.classList.add("cfc-poster-lock");
    const relayout = () => {
      const sx = window.innerWidth / 1920;
      const sy = window.innerHeight / 1080;
      const scale = Math.min(sx, sy);
      setFit({
        scale,
        mx: Math.max(0, (window.innerWidth - 1920 * scale) / 2),
        my: Math.max(0, (window.innerHeight - 1080 * scale) / 2),
      });
    };
    relayout();
    window.addEventListener("resize", relayout);
    return () => {
      document.body.classList.remove("cfc-poster-lock");
      window.removeEventListener("resize", relayout);
    };
  }, []);

  const stageStyle = useMemo(
    () => ({
      transform: `scale(${fit.scale})`,
      transformOrigin: "top left",
      width: 1920,
      height: 1080,
      marginLeft: fit.mx,
      marginTop: fit.my,
    }),
    [fit],
  );

  return (
    <div className="cfc-poster-viewport">
      <article className="cfc-poster" style={stageStyle} aria-label="OfficeHours AI Capstone Poster">
        <div className="cfc-lattice" aria-hidden="true" />

        <header className="cfc-header">
          <div className="cfc-brand-row">
            <img src={`${import.meta.env.BASE_URL}aui-logo.png`} alt="AUI" className="cfc-logo" />
            <div className="cfc-title-block">
              <p className="cfc-kicker">Digital Engineering Capstone · CFC Showcase</p>
              <h1>
                OfficeHours AI: Multi-Pathway Campus Helpdesk &amp; Pedagogical Intelligence
              </h1>
              <p className="cfc-thesis">
                Meeting every struggling student where they are comfortable—combining
                faculty-gated AI, human escalation accountability, peer collaboration, and
                adaptive study planning.
              </p>
            </div>
            <div className="cfc-meta">
              <div>Sophia Abssi</div>
              <div>B.S. AI &amp; Robotization</div>
              <div>
                Supervisor: <strong>Dr. Oumaima Hourrane</strong>
              </div>
              <div>Al Akhawayn University</div>
            </div>
          </div>
          <div className="cfc-stack" aria-label="Technology stack">
            {STACK.map((tag) => (
              <span key={tag} className="cfc-stack-tag">
                {tag}
              </span>
            ))}
          </div>
        </header>

        <div className="cfc-columns">
          {/* Column 1 */}
          <section className="cfc-col cfc-col--left">
            <div className="cfc-card">
              <h2>
                <span className="cfc-idx">01</span> Problem &amp; Motivation
              </h2>
              <div className="cfc-block">
                <h3>Diverse student help-seeking</h3>
                <p>
                  Students need different safe pathways—instant syllabus-accurate answers,
                  low-friction human escalation, peer debugging, or structured grade recovery.
                </p>
              </div>
              <div className="cfc-block">
                <h3>Staff visibility &amp; guidance</h3>
                <p>
                  TAs answer repeat questions without teaching guidance; professors lack
                  real-time insight into student struggle patterns.
                </p>
              </div>
            </div>

            <div className="cfc-card cfc-card--grow">
              <h2>
                <span className="cfc-idx">02</span> Multi-Role Functional Scope
              </h2>
              <div className="cfc-block">
                <h3>Student ecosystem — 4 pathways</h3>
                <ol className="cfc-pathways">
                  <li>
                    <em>01</em> Approved-Material Study Agent
                  </li>
                  <li>
                    <em>02</em> Direct TA/Professor escalation + live state
                  </li>
                  <li>
                    <em>03</em> Peer Notes &amp; Rooms Q&amp;A
                  </li>
                  <li>
                    <em>04</em> Canvas grade-gap Study Planner
                  </li>
                </ol>
              </div>
              <div className="cfc-block">
                <h3>TA workspace</h3>
                <p>
                  Live SLA queue with wait timers + real-time{" "}
                  <span className="cfc-hl-brass">AI Teaching Coach</span> (Help Coach).
                </p>
              </div>
              <div className="cfc-block">
                <h3>Professor command center</h3>
                <p>
                  Canvas material sync, content approval gate, and course-wide struggle
                  analytics.
                </p>
              </div>
            </div>
          </section>

          {/* Column 2 */}
          <section className="cfc-col cfc-col--mid">
            <div className="cfc-card">
              <h2>
                <span className="cfc-idx">03</span> End-to-End System Architecture
                <span className="cfc-hint">Click a node</span>
              </h2>
              <ArchDiagram activeId={active} onSelect={setActive} />
              <div className="cfc-detail" key={active}>
                <div className="cfc-detail-title">{detail.title}</div>
                <div className="cfc-detail-grid">
                  <div>
                    <span>Inputs</span>
                    <p>{detail.inputs}</p>
                  </div>
                  <div>
                    <span>Core logic</span>
                    <p>{detail.logic}</p>
                  </div>
                  <div>
                    <span>Guardrails</span>
                    <p>{detail.guardrails}</p>
                  </div>
                </div>
              </div>
            </div>

            <div className="cfc-card">
              <h2>
                <span className="cfc-idx">04</span> Core Algorithmic Modules
              </h2>
              <div className="cfc-modules">
                <button
                  type="button"
                  className={active === "rag" ? "is-on" : ""}
                  onClick={() => setActive("rag")}
                >
                  <strong>Professor-Gated Study Agent</strong>
                  <span>Retrieval strictly faculty-approved · 0% unapproved syllabus generation</span>
                </button>
                <button
                  type="button"
                  className={active === "sla" ? "is-on" : ""}
                  onClick={() => setActive("sla")}
                >
                  <strong>Escalation &amp; SLA State Machine</strong>
                  <span>
                    Auto-route to professor if 0 TAs ·{" "}
                    <span className="cfc-mono">Queued → Claimed → In Progress → Answered</span>
                  </span>
                </button>
                <button
                  type="button"
                  className={active === "coach" ? "is-on" : ""}
                  onClick={() => setActive("coach")}
                >
                  <strong>AI TA Pedagogical Coach</strong>
                  <span>Structured teaching approaches while the TA drafts a response</span>
                </button>
                <button
                  type="button"
                  className={active === "planner" ? "is-on" : ""}
                  onClick={() => setActive("planner")}
                >
                  <strong>Adaptive Web-Scraping Study Planner</strong>
                  <span>Grades + learning style + duration → curated timed plans</span>
                </button>
              </div>
            </div>
          </section>

          {/* Column 3 */}
          <section className="cfc-col cfc-col--right">
            <div className="cfc-card">
              <h2>
                <span className="cfc-idx">05</span> Experimental Evaluation
              </h2>
              <table className="cfc-table">
                <thead>
                  <tr>
                    <th>Benchmark</th>
                    <th>Result</th>
                  </tr>
                </thead>
                <tbody>
                  {BENCHMARKS.map((row) => (
                    <tr key={row.metric}>
                      <td>
                        <div>{row.metric}</div>
                        <small>{row.note}</small>
                      </td>
                      <td className="cfc-mono cfc-result">{row.value}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <div className="cfc-card">
              <h2>
                <span className="cfc-idx">06</span> Struggle &amp; SLA Analytics
              </h2>
              <AnalyticsPanel />
            </div>

            <div className="cfc-card cfc-qr-card">
              <h2>
                <span className="cfc-idx">07</span> Live Prototype &amp; Repository
              </h2>
              <div className="cfc-qr-row">
                <img
                  src={`${import.meta.env.BASE_URL}poster-demo-qr.png`}
                  alt="QR code to OfficeHours AI GitHub repository"
                  className="cfc-qr"
                />
                <div>
                  <p className="cfc-qr-lead">Scan for source + demo script</p>
                  <p className="cfc-mono cfc-qr-url">
                    github.com/abssisophia9-hub/officehours-ai
                  </p>
                  <p className="cfc-qr-note">
                    Local walkthrough: <span className="cfc-mono">./scripts/run_product.sh</span> →
                    :5180 · demo password <span className="cfc-mono">aui-demo</span>
                  </p>
                </div>
              </div>
            </div>
          </section>
        </div>

        <footer className="cfc-footer">
          <span>AUI × Canvas LMS × CFC architectural palette</span>
          <span className="cfc-mono">
            Emerald #006838 · Canvas Blue #008EE2 · Brass #C59B5F · Travertine #F9F7F3
          </span>
          <span>EGR 4402 Capstone Design · 16:9 interactive poster</span>
        </footer>
      </article>
    </div>
  );
}
