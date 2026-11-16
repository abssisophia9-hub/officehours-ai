import { useEffect, useMemo, useState } from "react";
import {
  SiReact,
  SiVite,
  SiTailwindcss,
  SiFastapi,
  SiSqlalchemy,
  SiPostgresql,
  SiSqlite,
  SiHuggingface,
  SiScikitlearn,
  SiGooglegemini,
  SiInstructure,
  SiYoutube,
} from "react-icons/si";
import "./capstone-poster.css";

const BASE = import.meta.env.BASE_URL || "/";

const STACK = [
  { label: "React", Icon: SiReact, color: "#61DAFB" },
  { label: "Vite", Icon: SiVite, color: "#646CFF" },
  { label: "Tailwind CSS", Icon: SiTailwindcss, color: "#06B6D4" },
  { label: "FastAPI", Icon: SiFastapi, color: "#009688" },
  { label: "SQLAlchemy", Icon: SiSqlalchemy, color: "#D71F00" },
  { label: "PostgreSQL", Icon: SiPostgresql, color: "#4169E1" },
  { label: "SQLite", Icon: SiSqlite, color: "#003B57" },
  { label: "Hugging Face / MiniLM", Icon: SiHuggingface, color: "#FFD21E" },
  { label: "scikit-learn", Icon: SiScikitlearn, color: "#F7931E" },
  { label: "Google Gemini", Icon: SiGooglegemini, color: "#8E75B2" },
  { label: "Canvas LMS", Icon: SiInstructure, color: "#E72429" },
  { label: "YouTube", Icon: SiYoutube, color: "#FF0000" },
];

const ROLES = {
  student: [
    "Study Agent",
    "Ask for help",
    "My asks",
    "Pedagogy Agent",
    "Rooms",
    "Classmate Notes",
  ],
  ta: ["Dashboard", "Live Queue + Help Coach", "Past asks"],
  professor: ["Material / KB gate", "Your desk", "Insights", "Team"],
};

const WORKFLOW = [
  {
    title: "Accountability State Tracking",
    body: "Asks move through open → claimed → in progress with reply accountability.",
  },
  {
    title: "0-TA Course Auto-Routing",
    body: "When a course has no TA membership, escalation routes to the professor.",
  },
  {
    title: "Real-Time TA Pedagogical Coaching",
    body: "Help Coach suggests Socratic teaching moves while the TA drafts a reply.",
  },
  {
    title: "Faculty Struggle Telemetry",
    body: "Professor Insights surfaces recurring confusion topics and overdue asks.",
  },
];

const PIPELINES = [
  {
    title: "Hybrid ML Ask Triage & Escalation Router",
    body: "MiniLM embeddings + local scikit-learn classifiers for category, urgency, tags, and 0-TA professor fallback.",
  },
  {
    title: "Approval-Gated Study Agent",
    body: "Course-scoped retrieval strictly limited to faculty-approved materials, plus citation entailment check when enabled.",
  },
  {
    title: "Real-Time TA Help Coach",
    body: "Context-aware Socratic scaffolding and teaching-approach suggestions without leaking final answers.",
  },
  {
    title: "Adaptive Pedagogy Agent",
    body: "Canvas grade-gap ingestion + learning-style curation via trusted educational sources and YouTube Data API.",
  },
];

const KPIS = [
  { value: "100%", label: "Unapproved Source Refusal", note: "10/10 + 10/10 gated" },
  { value: "98.7%", label: "Gated Study Check", note: "74/75 answer-check" },
  { value: "84.6%", label: "Ask Triage 5-Fold CV F1", note: "n=156 local ML" },
  { value: "62.6 ms", label: "Local ML Triage Latency p50", note: "TestClient · lexical" },
];

const ACCURACY = [
  { label: "Learning-Style CV", value: 92.5 },
  { label: "Matcher Holdout", value: 87.5 },
  { label: "Ask Triage CV F1", value: 84.6 },
  { label: "Gold-Label Analyzer", value: 75.0 },
];

const TOPICS = [
  { label: "Conceptual Questions", n: 37 },
  { label: "Exam Logistics", n: 23 },
  { label: "Project Submission", n: 18 },
  { label: "Grading Dispute", n: 14 },
  { label: "Retake Request", n: 14 },
];

const REFS = [
  "IMS Global Learning Tools Interoperability (LTI) 1.3",
  "Reimers & Gurevych, Sentence-BERT, EMNLP 2019",
  "Lewis et al., Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks, NeurIPS 2020",
  "Pedregosa et al., Scikit-learn: Machine Learning in Python, JMLR 2011",
];

function ModularMonolithSvg({ className }) {
  return (
    <svg
      className={className}
      viewBox="0 0 980 520"
      role="img"
      aria-label="OfficeHours AI modular monolith architecture"
    >
      <rect width="980" height="520" fill="#FFFFFF" />
      <text x="20" y="28" className="mm-title">
        OfficeHours AI — modular monolith architecture
      </text>
      <text x="20" y="48" className="mm-sub">
        One FastAPI deployable · modules call interfaces only · Pedagogy Agent in Academic Support
      </text>

      {/* Canvas external */}
      <rect x="12" y="160" width="118" height="170" rx="8" className="mm-ext" />
      <text x="22" y="186" className="mm-h">Canvas LMS</text>
      <text x="22" y="210" className="mm-p">LTI 1.3 Launch</text>
      <text x="22" y="228" className="mm-p">Roster Sync</text>
      <text x="22" y="246" className="mm-p">(NRPS)</text>
      <text x="22" y="264" className="mm-p">Grade Sync</text>

      {/* SPA */}
      <rect x="160" y="70" width="660" height="52" rx="8" className="mm-spa" />
      <text x="176" y="92" className="mm-h">React SPA (Browser)</text>
      <text x="176" y="110" className="mm-p">
        Student · TA · Professor views · no business logic · HTTPS/JSON + session cookie
      </text>

      {/* Backend shell */}
      <rect x="160" y="140" width="660" height="300" rx="10" className="mm-back" />
      <text x="176" y="162" className="mm-h">BACKEND — Modular Monolith · FastAPI (Python)</text>

      {/* API edge */}
      <rect x="176" y="174" width="628" height="42" rx="6" className="mm-edge" />
      <text x="190" y="192" className="mm-h">API Edge — FastAPI Routers &amp; Middleware</text>
      <text x="190" y="208" className="mm-p">
        CallerContext (user, course, role, course_has_ta) · rate limiting · validation
      </text>

      {/* Identity */}
      <rect x="176" y="230" width="196" height="148" rx="6" className="mm-id" />
      <text x="188" y="252" className="mm-h">Identity &amp; Courses</text>
      <text x="188" y="274" className="mm-p">LTI 1.3 Auth</text>
      <text x="188" y="292" className="mm-p">Roster Sync</text>
      <text x="188" y="310" className="mm-p">Role &amp; Course Membership</text>
      <text x="188" y="336" className="mm-iface">INTERFACE</text>
      <text x="188" y="354" className="mm-p">resolve_caller · sync_roster</text>

      {/* Knowledge */}
      <rect x="386" y="230" width="196" height="148" rx="6" className="mm-know" />
      <text x="398" y="252" className="mm-h">Knowledge</text>
      <text x="398" y="274" className="mm-p">PDF Upload</text>
      <text x="398" y="292" className="mm-p">Professor Approval Gate</text>
      <text x="398" y="310" className="mm-p">Chunking &amp; Embeddings</text>
      <text x="398" y="328" className="mm-p">Approved-Only Filter</text>
      <text x="398" y="354" className="mm-iface">retrieve · submit/approve</text>

      {/* Academic Support */}
      <rect x="596" y="230" width="208" height="148" rx="6" className="mm-sup" />
      <text x="608" y="250" className="mm-h">Academic Support</text>
      <text x="608" y="270" className="mm-p">Study Agent Chat</text>
      <text x="608" y="286" className="mm-p">Help Requests · 0-TA Escalation</text>
      <text x="608" y="302" className="mm-p">TA Live Queue · Help Coach</text>
      <text x="608" y="318" className="mm-p">Peer Rooms &amp; Notes</text>
      <rect x="608" y="326" width="180" height="42" rx="4" className="mm-ped" />
      <text x="616" y="344" className="mm-h">Pedagogy Agent</text>
      <text x="616" y="360" className="mm-p">Grade-gap · learning-style plan</text>

      {/* Persistence */}
      <rect x="176" y="390" width="628" height="36" rx="6" className="mm-db" />
      <text x="190" y="412" className="mm-h">
        SQLAlchemy Persistence — SQLite / PostgreSQL · identity · knowledge · support schemas
      </text>

      {/* Model gateway */}
      <rect x="846" y="160" width="120" height="170" rx="8" className="mm-gw" />
      <text x="856" y="186" className="mm-h">Model Gateway</text>
      <text x="856" y="210" className="mm-p">MiniLM +</text>
      <text x="856" y="226" className="mm-p">scikit-learn</text>
      <text x="856" y="242" className="mm-p">local triage</text>
      <text x="856" y="266" className="mm-p">Gated Gemini</text>
      <text x="856" y="282" className="mm-p">adapter</text>
      <text x="856" y="306" className="mm-p">Egress guard</text>

      {/* arrows */}
      <path d="M130 245 H160" className="mm-arrow" />
      <path d="M820 245 H846" className="mm-arrow" />
      <path d="M490 122 V140" className="mm-arrow" />
      <path d="M372 304 H386" className="mm-dash" />
      <path d="M582 304 H596" className="mm-dash" />

      <text x="20" y="500" className="mm-foot">
        Modules never query another module’s tables · course_id from CallerContext session only
      </text>
    </svg>
  );
}

function RepoStructureSvg({ className }) {
  return (
    <svg className={className} viewBox="0 0 980 520" role="img" aria-label="Repository structure">
      <rect width="980" height="520" fill="#FFFFFF" />
      <text x="24" y="36" className="mm-title">
        OfficeHours AI — repository structure
      </text>
      {[
        {
          x: 24,
          title: "backend/",
          lines: [
            "FastAPI app + routers",
            "Ask Triage · Help Coach",
            "Study · Pedagogy services",
            "SQLAlchemy models",
            "Local MiniLM classifiers",
          ],
          fill: "#E8F5EE",
          stroke: "#006838",
        },
        {
          x: 340,
          title: "frontend/officehours-app/",
          lines: [
            "Unified React SPA",
            "Student · TA · Professor",
            "Vite + Tailwind CSS v4",
            "Course-scoped role shell",
            "Public /poster showcase",
          ],
          fill: "#EAF5FB",
          stroke: "#008EE2",
        },
        {
          x: 656,
          title: "docs/ · data/ · diagrams/",
          lines: [
            "Architecture & glossary",
            "Eval result JSON",
            "Teaching bank (68 rows)",
            "Platform diagrams",
            "FYP evidence tables",
          ],
          fill: "#F3F5F6",
          stroke: "#2D3B45",
        },
      ].map((col) => (
        <g key={col.title}>
          <rect x={col.x} y="64" width="300" height="400" rx="10" fill={col.fill} stroke={col.stroke} strokeWidth="2" />
          <rect x={col.x} y="64" width="300" height="48" rx="10" fill={col.stroke} />
          <rect x={col.x} y="88" width="300" height="24" fill={col.stroke} />
          <text x={col.x + 16} y="94" fill="#fff" fontFamily="IBM Plex Mono, monospace" fontSize="16" fontWeight="700">
            {col.title}
          </text>
          {col.lines.map((line, i) => (
            <text
              key={line}
              x={col.x + 18}
              y={150 + i * 42}
              fill="#2D3B45"
              fontFamily="Inter, sans-serif"
              fontSize="16"
            >
              {line}
            </text>
          ))}
        </g>
      ))}
    </svg>
  );
}

function AccuracyChart() {
  const max = 100;
  return (
    <div className="cfc-acc-chart" aria-label="Component accuracy comparison">
      {ACCURACY.map((row) => (
        <div key={row.label} className="cfc-acc-row">
          <span className="cfc-acc-label">{row.label}</span>
          <span className="cfc-acc-track">
            <span className="cfc-acc-fill" style={{ height: `${(row.value / max) * 100}%` }} />
          </span>
          <strong className="cfc-mono">{row.value}%</strong>
        </div>
      ))}
    </div>
  );
}

function ZoomModal({ mode, onClose }) {
  useEffect(() => {
    const onKey = (e) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);
  return (
    <div className="cfc-zoom" role="dialog" aria-modal="true" onClick={onClose}>
      <div className="cfc-zoom-inner" onClick={(e) => e.stopPropagation()}>
        <button type="button" className="cfc-zoom-close" onClick={onClose}>
          Close
        </button>
        {mode === "arch" ? (
          <ModularMonolithSvg className="cfc-zoom-svg" />
        ) : (
          <RepoStructureSvg className="cfc-zoom-svg" />
        )}
      </div>
    </div>
  );
}

export default function CapstonePosterPage() {
  const [diagramMode, setDiagramMode] = useState("arch");
  const [zoom, setZoom] = useState(false);
  const [fit, setFit] = useState({ scale: 1, mx: 0, my: 0 });
  const maxTopic = Math.max(...TOPICS.map((t) => t.n));

  useEffect(() => {
    document.documentElement.setAttribute("data-theme", "light");
    document.body.classList.add("cfc-poster-lock");
    const relayout = () => {
      const sx = window.innerWidth / 1080;
      const sy = window.innerHeight / 1920;
      const scale = Math.min(sx, sy);
      setFit({
        scale,
        mx: Math.max(0, (window.innerWidth - 1080 * scale) / 2),
        my: Math.max(0, (window.innerHeight - 1920 * scale) / 2),
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
      width: 1080,
      height: 1920,
      marginLeft: fit.mx,
      marginTop: fit.my,
    }),
    [fit],
  );

  return (
    <div className="cfc-poster-viewport">
      <article className="cfc-poster cfc-poster--portrait" style={stageStyle}>
        <div className="cfc-lattice" aria-hidden="true" />

        <header className="cfc-header">
          <div className="cfc-header-top">
            <img src={`${BASE}aui-logo.png`} alt="Al Akhawayn University" className="cfc-logo" />
            <div className="cfc-header-copy min-w-0">
              <p className="cfc-kicker">EGR 4402 Capstone Design · Al Akhawayn University</p>
              <h1>OfficeHours AI</h1>
              <p className="cfc-sub">
                Multi-pathway campus helpdesk with faculty-gated AI, human escalation
                accountability, peer Rooms, and adaptive study planning.
              </p>
            </div>
            <div className="cfc-meta min-w-0">
              <div className="cfc-meta-name">Sophia Abssi</div>
              <div>B.S. AI &amp; Robotization</div>
              <div>
                Supervisor: <strong>Dr. Oumaima Hourrane</strong>
              </div>
              <div>School of Science &amp; Engineering</div>
            </div>
          </div>
          <div className="cfc-stack" aria-label="Technology stack">
            {STACK.map(({ label, Icon, color }) => (
              <span key={label} className="cfc-logo-badge">
                <Icon aria-hidden="true" style={{ color }} />
                <span>{label}</span>
              </span>
            ))}
          </div>
        </header>

        <section className="cfc-card cfc-card--s1 min-w-0">
          <h2 className="cfc-bar cfc-bar--emerald">
            <span>1</span> Problem Statement &amp; Motivation
          </h2>
          <div className="cfc-card-body cfc-s1">
            <p className="cfc-s1-para">
              Struggling students do not all seek help the same way—some feel intimidated asking
              publicly, some need instant syllabus-accurate answers without the risk of AI
              hallucinations, some learn best by collaborating with peers, and others simply need a
              structured plan tailored to how they learn. Yet traditional academic tools force every
              student through the same rigid channel, leaving unanswered questions without
              accountability, leaving courses without TAs unserved, leaving TAs without guidance on
              how to coach rather than just give away answers, and leaving professors blind to where
              their students are silently falling behind.
            </p>
            <div className="cfc-workflow">
              {WORKFLOW.map((item) => (
                <div key={item.title} className="cfc-workflow-item">
                  <strong>{item.title}</strong>
                  <span>{item.body}</span>
                </div>
              ))}
            </div>
          </div>
        </section>

        <section className="cfc-card cfc-card--s2 min-w-0">
          <h2 className="cfc-bar cfc-bar--slate">
            <span>2</span> Multi-Role Functional Architecture
          </h2>
          <div className="cfc-card-body cfc-role-grid">
            {Object.entries(ROLES).map(([role, items]) => (
              <div key={role} className="cfc-role-col">
                <h3>{role[0].toUpperCase() + role.slice(1)}</h3>
                <ul>
                  {items.map((label) => (
                    <li key={label}>{label}</li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </section>

        <section className="cfc-card cfc-card--arch min-w-0">
          <h2 className="cfc-bar cfc-bar--emerald">
            <span>3</span> System Architecture &amp; Repository Structure
            <div className="cfc-tabs" role="tablist">
              <button
                type="button"
                role="tab"
                aria-selected={diagramMode === "arch"}
                className={diagramMode === "arch" ? "is-on" : ""}
                onClick={() => setDiagramMode("arch")}
              >
                System Architecture
              </button>
              <button
                type="button"
                role="tab"
                aria-selected={diagramMode === "repo"}
                className={diagramMode === "repo" ? "is-on" : ""}
                onClick={() => setDiagramMode("repo")}
              >
                Repository Structure
              </button>
            </div>
          </h2>
          <div className="cfc-card-body cfc-arch-body">
            <button
              type="button"
              className="cfc-diagram-frame"
              onClick={() => setZoom(true)}
              aria-label="Click to zoom diagram"
            >
              {diagramMode === "arch" ? (
                <ModularMonolithSvg className="cfc-diagram-svg" />
              ) : (
                <RepoStructureSvg className="cfc-diagram-svg" />
              )}
              <span className="cfc-zoom-chip">Click to zoom</span>
            </button>
          </div>
        </section>

        <section className="cfc-card cfc-card--s4 min-w-0">
          <h2 className="cfc-bar cfc-bar--slate">
            <span>4</span> Core Algorithmic &amp; AI Pipelines
          </h2>
          <div className="cfc-card-body cfc-pipe-grid">
            {PIPELINES.map((p, i) => (
              <article key={p.title} className="cfc-pipe min-w-0">
                <div className="cfc-pipe-idx cfc-mono">{String(i + 1).padStart(2, "0")}</div>
                <h3>{p.title}</h3>
                <p>{p.body}</p>
              </article>
            ))}
          </div>
        </section>

        <div className="cfc-row cfc-row--s56">
          <section className="cfc-card min-w-0">
            <h2 className="cfc-bar cfc-bar--emerald">
              <span>5</span> Experimental Evaluation &amp; Benchmarks
            </h2>
            <div className="cfc-card-body cfc-eval">
              <div className="cfc-kpi-grid">
                {KPIS.map((k) => (
                  <div key={k.label} className="cfc-kpi">
                    <strong className="cfc-mono">{k.value}</strong>
                    <span>{k.label}</span>
                    <em>{k.note}</em>
                  </div>
                ))}
              </div>
              <div className="cfc-eval-lower">
                <AccuracyChart />
                <div className="cfc-pass-col">
                  <div className="cfc-pass">
                    <span className="cfc-pass-badge">PASS</span>
                    <strong>0-TA Escalation Routing</strong>
                  </div>
                  <div className="cfc-pass">
                    <span className="cfc-pass-badge">PASS</span>
                    <strong>Grade-Gap Planner E2E</strong>
                  </div>
                </div>
              </div>
            </div>
          </section>

          <section className="cfc-card min-w-0">
            <h2 className="cfc-bar cfc-bar--slate">
              <span>6</span> Struggle Telemetry &amp; Live Prototype
            </h2>
            <div className="cfc-card-body cfc-tele">
              <div className="cfc-tele-chart min-w-0">
                <h3>Top confusion topics (CV support)</h3>
                <ul className="cfc-mini-bars">
                  {TOPICS.map((t) => (
                    <li key={t.label}>
                      <span>{t.label}</span>
                      <span className="cfc-bar-track">
                        <span
                          className="cfc-bar-fill"
                          style={{ width: `${(t.n / maxTopic) * 100}%` }}
                        />
                      </span>
                      <strong className="cfc-mono">{t.n}</strong>
                    </li>
                  ))}
                </ul>
              </div>
              <div className="cfc-qr-panel min-w-0">
                <img
                  src={`${BASE}poster-demo-qr.png`}
                  alt="QR code linking to the OfficeHours AI GitHub repository"
                  className="cfc-qr"
                />
                <p className="cfc-qr-title">Live Prototype</p>
                <p className="cfc-mono cfc-qr-url">github.com/abssisophia9-hub/officehours-ai</p>
              </div>
            </div>
          </section>
        </div>

        <section className="cfc-refs min-w-0">
          <h2>
            <span>7</span> References
          </h2>
          <ol>
            {REFS.map((ref) => (
              <li key={ref}>{ref}</li>
            ))}
          </ol>
        </section>

        <footer className="cfc-footer">
          Al Akhawayn University · School of Science &amp; Engineering · EGR 4402 Capstone Design ·
          Casablanca Finance City Showcase
        </footer>
      </article>

      {zoom ? <ZoomModal mode={diagramMode} onClose={() => setZoom(false)} /> : null}
    </div>
  );
}
