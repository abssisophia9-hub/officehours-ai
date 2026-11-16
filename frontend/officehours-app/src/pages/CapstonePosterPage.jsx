import { useEffect, useMemo, useState } from "react";
import "./capstone-poster.css";

const BASE = import.meta.env.BASE_URL || "/";

/** Verified from package.json + requirements.txt */
const STACK = [
  "React",
  "Vite",
  "Tailwind CSS v4",
  "FastAPI",
  "SQLAlchemy",
  "SQLite / PostgreSQL",
  "sentence-transformers",
  "MiniLM-L6-v2",
  "scikit-learn",
  "PyJWT",
  "Canvas LTI 1.3",
  "Gemini (optional)",
];

/** Verified from AppShell SECTION_NAV + App.jsx routes + README roles table */
const ROLES = {
  student: [
    { route: "/student", label: "Study Agent", file: "StudentAgentPage.jsx" },
    { route: "/student/ask", label: "Ask for help", file: "StudentWorkspace.jsx" },
    { route: "/student/asks", label: "My asks", file: "StudentAsksPage.jsx" },
    { route: "/student/revision", label: "Pedagogy Agent", file: "StudentRevisionPage.jsx" },
    { route: "/student/room", label: "Rooms", file: "StuckRoomPage.jsx" },
    { route: "/student/notes", label: "Classmate Notes", file: "StudentNotesPage.jsx" },
  ],
  ta: [
    { route: "/ta/home", label: "Dashboard", file: "TaDashboardPage.jsx" },
    { route: "/ta", label: "Live Queue (Help Coach)", file: "TaWorkspace.jsx" },
    { route: "/ta/past", label: "Past asks", file: "TaPastAsksPage.jsx" },
  ],
  professor: [
    { route: "/professor", label: "Material / KB gate", file: "MaterialPage.jsx" },
    { route: "/professor/asks", label: "Your desk", file: "AsksPage.jsx" },
    { route: "/professor/insights", label: "Insights", file: "InsightsPage.jsx" },
    { route: "/professor/team", label: "Team", file: "TeamPage.jsx" },
  ],
};

/** Verified main.py include_router + route prefixes */
const ROUTERS = [
  "/auth",
  "/courses",
  "/requests",
  "/ta",
  "/knowledge",
  "/agent/ask",
  "/analytics/*",
  "/canvas",
  "/lti",
  "/help-room",
  "/peer-notes",
  "/revision",
  "/study-conversations",
  "/ws",
];

/** Verified backend/app/models/*.py */
const MODELS = [
  "Request",
  "User / Course / CourseMembership",
  "KnowledgeEntry",
  "HelpRoom / PeerNotes",
  "RevisionPlan",
  "TaRoster",
  "Action / Notification",
];

/**
 * Benchmarks only from in-repo JSON artifacts / tests.
 * Sources: reports/final_report/*, docs/eval_results/with_check_*, test_no_ta_routing.py
 */
const BENCHMARKS = [
  {
    id: "clf",
    metric: "Ask Triage Analyzer CV (macro F1)",
    value: "84.55%",
    bar: 84.55,
    note: "classifier_evaluation.json · n=156 · 5-fold · acc 84.62%",
  },
  {
    id: "match",
    metric: "Matcher holdout accuracy",
    value: "87.5%",
    bar: 87.5,
    note: "matcher_evaluation.json · 28/32 · silver labels",
  },
  {
    id: "gold",
    metric: "Gold-label Analyzer accuracy",
    value: "75.0%",
    bar: 75,
    note: "gold_label_evaluation.json · 60/80 · macro F1 0.66",
  },
  {
    id: "style",
    metric: "Learning-style CV accuracy",
    value: "92.5%",
    bar: 92.5,
    note: "learning_style_evaluation.json · n=40",
  },
  {
    id: "gate",
    metric: "Study Agent unapproved_only / other_course",
    value: "10/10 · 10/10",
    bar: 100,
    note: "with_check_gemini…json · cited_unapproved=0",
  },
  {
    id: "check",
    metric: "Study Agent gated suite (overall)",
    value: "74/75",
    bar: 98.7,
    note: "answer-check · 1 injection spurious_answer",
  },
  {
    id: "lat",
    metric: "Ask Triage latency p50",
    value: "62.57 ms",
    bar: 70,
    note: "ask_triage_latency.json · n=5 · lexical · TestClient",
  },
  {
    id: "nota",
    metric: "0-TA → professor routing",
    value: "PASS",
    bar: 100,
    note: "test_no_ta_routing.py · assignee_role=professor",
  },
];

/** Support counts from classifier_evaluation.json — verified label distribution */
const TRIAGE_SUPPORT = [
  { label: "conceptual_question", n: 37 },
  { label: "exam_logistics", n: 23 },
  { label: "project_submission", n: 18 },
  { label: "emotional_stress", n: 14 },
  { label: "grading_dispute", n: 14 },
  { label: "retake_request", n: 14 },
  { label: "accessibility_accommodation", n: 10 },
  { label: "office_hours_access", n: 9 },
  { label: "uncategorized", n: 9 },
  { label: "academic_integrity", n: 8 },
];

const PIPELINES = [
  {
    title: "Ask Triage",
    module: "ask_triage_service.py",
    files: "analyzer_agent · matcher_model · synthesizer_model",
    logic:
      "On POST /requests/: Analyzer → category/urgency/tags → Matcher → primary/alt TA + wait → Synthesizer → student_hint / teaching approach (local joblib models).",
    gate: "Default local ML path — not a prompted chat. Legacy Claude helpers gated/optional only.",
  },
  {
    title: "Study Agent",
    module: "kb_agent_service.py · agent_policy.py",
    files: "POST /agent/ask · knowledge approve gate",
    logic:
      "Retrieves professor-approved KB chunks for the caller’s course_id, then optional Gemini/Claude entailment check when demo + LLM flags allow.",
    gate: "Only approved material; OFFICEHOURS_ALLOW_EXTERNAL_LLM=false by default.",
  },
  {
    title: "Help Coach",
    module: "help_coach_service.py",
    files: "POST /ta/assist/ · synthesizer_model · teaching bank",
    logic:
      "While TA helps: similar open asks, approved KB neighbors, Socratic steps, draft/rewrite suggestions from 68-row teaching bank + KB retrieval — no LLM.",
    gate: "Does not answer the student as course truth; Insert into Reply is explicit.",
  },
  {
    title: "Pedagogy Agent + Escalation",
    module: "revision_service.py · course_ta_service.py",
    files: "POST /revision/plan · revision_search.py · work_status",
    logic:
      "Focus plan from practice scores + preference; Resources via Wikipedia/trusted search + YouTube when keyed. Escalation: work_status open→claimed→in_progress; 0 TAs → assign_professor_when_no_ta.",
    gate: "No real grades/names in client payload; scores not echoed.",
  },
];

function DiagramPanel({ mode, onZoom }) {
  const src =
    mode === "arch"
      ? `${BASE}architecture-diagram.png`
      : `${BASE}github-repo-diagram.png`;
  const alt =
    mode === "arch"
      ? "OfficeHours Platform complete architecture diagram"
      : "OfficeHours AI verified repository structure diagram";
  return (
    <button type="button" className="cfc-diagram-frame" onClick={onZoom} aria-label="Click to zoom diagram">
      <img src={src} alt={alt} className="cfc-diagram-img" />
      <span className="cfc-zoom-chip">Click to zoom</span>
    </button>
  );
}

function ZoomModal({ mode, onClose }) {
  const src =
    mode === "arch"
      ? `${BASE}architecture-diagram.png`
      : `${BASE}github-repo-diagram.png`;
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
        <img src={src} alt="Zoomed diagram" />
      </div>
    </div>
  );
}

export default function CapstonePosterPage() {
  const [diagramMode, setDiagramMode] = useState("arch");
  const [zoom, setZoom] = useState(false);
  const [fit, setFit] = useState({ scale: 1, mx: 0, my: 0 });
  const maxSupport = Math.max(...TRIAGE_SUPPORT.map((t) => t.n));

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

        {/* HEADER — 11% */}
        <header className="cfc-band cfc-band--header">
          <div className="cfc-header-inner">
            <img src={`${BASE}aui-logo.png`} alt="Al Akhawayn University" className="cfc-logo" />
            <div className="cfc-header-copy min-w-0">
              <p className="cfc-kicker">EGR 4402 Capstone Design · Al Akhawayn University</p>
              <h1>OfficeHours AI</h1>
              <p className="cfc-sub">
                One login for students, TAs, and professors (role per course): Ask Triage at intake,
                Help Coach while staffing, professor-gated Study Agent, Pedagogy Agent with web
                Resources, and peer Rooms — FastAPI + React campus helpdesk.
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
          <div className="cfc-stack">
            {STACK.map((t) => (
              <span key={t} className="cfc-chip">
                {t}
              </span>
            ))}
          </div>
        </header>

        {/* S1 + S2 — 18% */}
        <div className="cfc-row cfc-row--18">
          <section className="cfc-card cfc-card--fill min-w-0">
            <h2 className="cfc-bar cfc-bar--emerald">
              <span>1</span> Problem Statement &amp; Motivation
            </h2>
            <div className="cfc-card-body cfc-two-col">
              <div className="cfc-callout">
                <h3>Student help-seeking is not one channel</h3>
                <p>
                  Struggling students do not all seek help the same way—some feel intimidated asking
                  publicly, some need instant syllabus-accurate answers without AI hallucination
                  risk, some learn by collaborating with peers, and others need a structured plan
                  tailored to how they learn.
                </p>
              </div>
              <div className="cfc-callout">
                <h3>Staff workflow gaps this build targets</h3>
                <ul>
                  <li>
                    <strong>Accountability:</strong> asks need claim → help → reply state, not a
                    silent inbox.
                  </li>
                  <li>
                    <strong>0-TA courses:</strong> route to the professor when no TA membership
                    exists.
                  </li>
                  <li>
                    <strong>TA coaching:</strong> Help Coach guides teaching moves — not giving
                    away answers.
                  </li>
                  <li>
                    <strong>Professor visibility:</strong> Insights / struggle analytics expose
                    where students fall behind.
                  </li>
                </ul>
              </div>
            </div>
          </section>

          <section className="cfc-card cfc-card--fill min-w-0">
            <h2 className="cfc-bar cfc-bar--slate">
              <span>2</span> Multi-Role Functional Architecture
            </h2>
            <div className="cfc-card-body cfc-role-grid">
              {[
                ["Student", ROLES.student],
                ["TA", ROLES.ta],
                ["Professor", ROLES.professor],
              ].map(([title, items]) => (
                <div key={title} className="cfc-role-col">
                  <h3>{title}</h3>
                  <ul>
                    {items.map((r) => (
                      <li key={r.route}>
                        <span className="cfc-mono">{r.label}</span>
                        <em>{r.file}</em>
                      </li>
                    ))}
                  </ul>
                </div>
              ))}
            </div>
          </section>
        </div>

        {/* S3 — 29% hero */}
        <section className="cfc-card cfc-card--hero cfc-card--fill min-w-0">
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
          <div className="cfc-card-body cfc-hero-body">
            <DiagramPanel mode={diagramMode} onZoom={() => setZoom(true)} />
            <div className="cfc-strip-block">
              <div className="cfc-strip">
                <span className="cfc-strip-label">Routers</span>
                {ROUTERS.map((r) => (
                  <span key={r} className="cfc-chip cfc-chip--blue">
                    {r}
                  </span>
                ))}
              </div>
              <div className="cfc-strip">
                <span className="cfc-strip-label">Models</span>
                {MODELS.map((m) => (
                  <span key={m} className="cfc-chip cfc-chip--slate">
                    {m}
                  </span>
                ))}
              </div>
              <div className="cfc-strip">
                <span className="cfc-strip-label">Services</span>
                <span className="cfc-chip">ask_triage_service</span>
                <span className="cfc-chip">help_coach_service</span>
                <span className="cfc-chip">kb_agent_service</span>
                <span className="cfc-chip">revision_service</span>
                <span className="cfc-chip">course_ta_service</span>
                <span className="cfc-chip">analytics_service</span>
                <span className="cfc-chip">lti13 / canvas_service</span>
              </div>
            </div>
          </div>
        </section>

        {/* S4 — 20% */}
        <section className="cfc-card cfc-card--fill min-w-0">
          <h2 className="cfc-bar cfc-bar--slate">
            <span>4</span> Core Algorithmic &amp; AI Pipelines
          </h2>
          <div className="cfc-card-body cfc-pipe-grid">
            {PIPELINES.map((p) => (
              <article key={p.title} className="cfc-pipe min-w-0">
                <h3>{p.title}</h3>
                <p className="cfc-mono cfc-pipe-mod">{p.module}</p>
                <p className="cfc-pipe-files">{p.files}</p>
                <p>
                  <strong>Logic:</strong> {p.logic}
                </p>
                <p className="cfc-gate">
                  <strong>Gate:</strong> {p.gate}
                </p>
              </article>
            ))}
          </div>
        </section>

        {/* S5 + S6 — 19% */}
        <div className="cfc-row cfc-row--19">
          <section className="cfc-card cfc-card--fill min-w-0">
            <h2 className="cfc-bar cfc-bar--emerald">
              <span>5</span> Experimental Evaluation &amp; Benchmarks
            </h2>
            <div className="cfc-card-body cfc-bench">
              {BENCHMARKS.map((b) => (
                <div key={b.id} className="cfc-bench-row min-w-0">
                  <div className="cfc-bench-top">
                    <span>{b.metric}</span>
                    <strong className="cfc-mono">{b.value}</strong>
                  </div>
                  <div className="cfc-bar-track" aria-hidden="true">
                    <div className="cfc-bar-fill" style={{ width: `${Math.min(100, b.bar)}%` }} />
                  </div>
                  <div className="cfc-bench-note cfc-mono">{b.note}</div>
                </div>
              ))}
            </div>
          </section>

          <section className="cfc-card cfc-card--fill min-w-0">
            <h2 className="cfc-bar cfc-bar--slate">
              <span>6</span> System Telemetry &amp; Live Prototype
            </h2>
            <div className="cfc-card-body cfc-tele">
              <div className="cfc-tele-left min-w-0">
                <h3>Ask Triage label support (CV set)</h3>
                <p className="cfc-tele-src cfc-mono">classifier_evaluation.json · support counts</p>
                <ul className="cfc-mini-bars">
                  {TRIAGE_SUPPORT.slice(0, 7).map((t) => (
                    <li key={t.label}>
                      <span className="cfc-mono">{t.label.replaceAll("_", " ")}</span>
                      <span className="cfc-bar-track">
                        <span
                          className="cfc-bar-fill cfc-bar-fill--blue"
                          style={{ width: `${(t.n / maxSupport) * 100}%` }}
                        />
                      </span>
                      <strong className="cfc-mono">{t.n}</strong>
                    </li>
                  ))}
                </ul>
                <div className="cfc-api-chips">
                  <span className="cfc-chip cfc-chip--blue">/analytics/struggle-monitor</span>
                  <span className="cfc-chip cfc-chip--blue">/analytics/lifetime-confusion</span>
                  <span className="cfc-chip cfc-chip--brass">work_status · wait timers</span>
                </div>
              </div>
              <div className="cfc-qr-panel min-w-0">
                <img
                  src={`${BASE}poster-demo-qr.png`}
                  alt="QR code to GitHub repository abssisophia9-hub/officehours-ai"
                  className="cfc-qr"
                />
                <div className="cfc-qr-copy">
                  <p className="cfc-qr-title">Repository &amp; launch</p>
                  <p className="cfc-mono cfc-qr-url">github.com/abssisophia9-hub/officehours-ai</p>
                  <p className="cfc-qr-cmd cfc-mono">./scripts/run_product.sh</p>
                  <div className="cfc-qr-specs">
                    <span className="cfc-chip cfc-chip--slate">:5180 app</span>
                    <span className="cfc-chip cfc-chip--slate">:8000 API</span>
                    <span className="cfc-chip cfc-chip--brass">aui-demo</span>
                    <span className="cfc-chip cfc-chip--blue">/poster</span>
                  </div>
                  <p className="cfc-qr-note">
                    Demo accounts in README · OFFICEHOURS_DEMO=true via run_product.sh
                  </p>
                </div>
              </div>
            </div>
          </section>
        </div>

        <footer className="cfc-band cfc-band--footer">
          <span>Al Akhawayn University · Capstone Design EGR 4402</span>
          <span>OfficeHours AI · Canvas-linked multi-role campus helpdesk</span>
          <span>Supervisor: Dr. Oumaima Hourrane · Author: Sophia Abssi</span>
        </footer>
      </article>

      {zoom ? <ZoomModal mode={diagramMode} onClose={() => setZoom(false)} /> : null}
    </div>
  );
}
