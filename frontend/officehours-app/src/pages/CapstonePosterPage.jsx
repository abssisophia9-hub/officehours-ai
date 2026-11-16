import { useEffect, useMemo, useState } from "react";
import "./capstone-poster.css";

const BASE = import.meta.env.BASE_URL || "/";

/**
 * MIT-style research exhibition poster (landscape 1920×1080).
 * Composition: 20-second pitch · dominant architecture figure · sparse claims · measured results.
 * Numbers/modules only from reports/final_report/* and docs/eval_results / midreport evidence.
 */

const NODES = [
  {
    id: "canvas",
    x: 36,
    y: 78,
    w: 188,
    h: 96,
    title: "Canvas LTI",
    sub: "Course roster · material",
  },
  {
    id: "spa",
    x: 268,
    y: 78,
    w: 188,
    h: 96,
    title: "React SPA",
    sub: "Role per course",
  },
  {
    id: "api",
    x: 500,
    y: 28,
    w: 230,
    h: 196,
    title: "FastAPI modules",
    sub: "Ask · Study · Coach · Pedagogy · Rooms",
    tall: true,
  },
  {
    id: "gateway",
    x: 774,
    y: 28,
    w: 220,
    h: 196,
    title: "Model gateway",
    sub: "MiniLM + sklearn · gated Gemini",
    tall: true,
  },
  {
    id: "db",
    x: 1038,
    y: 78,
    w: 168,
    h: 96,
    title: "SQLAlchemy",
    sub: "SQLite / Postgres",
  },
];

const EDGES = [
  [36 + 188, 126, 268, 126],
  [268 + 188, 126, 500, 126],
  [500 + 230, 126, 774, 126],
  [774 + 220, 126, 1038, 126],
];

const LAYERS = [
  {
    id: "triage",
    short: "Ask Triage",
    claim: "Local Ask Triage routes asks without an LLM",
    detail:
      "Analyzer → Matcher → Synthesizer on MiniLM embeddings + logistic regression (joblib). Default path is local — not a prompted chat.",
  },
  {
    id: "study",
    short: "Study gate",
    claim: "Only professor-stamped material may be quoted",
    detail:
      "Study Agent retrieves approved KB for the caller’s course. Optional Gemini entailment check only when demo + LLM flags allow.",
  },
  {
    id: "coach",
    short: "Help Coach",
    claim: "Help Coach assists the TA — never answers as truth",
    detail:
      "Retrieval over a curated teaching bank + approved KB. Queue: open → claimed → in progress; 0-TA courses route to the professor.",
  },
  {
    id: "peer",
    short: "Peer path",
    claim: "Pedagogy, Rooms, and Notes recover beside staff help",
    detail:
      "Pedagogy builds focus plans from practice scores. Rooms and Classmate Notes keep peer pathways without inventing syllabus.",
  },
];

const RESULTS = [
  {
    value: "100%",
    label: "Unapproved / other-course refusal",
    note: "10/10 + 10/10 · with_check Gemini",
  },
  {
    value: "74/75",
    label: "Study answer-check harness",
    note: "98.7% · gated check suite",
  },
  {
    value: "84.6%",
    label: "Ask Triage macro F1",
    note: "5-fold CV · n=156",
  },
  {
    value: "62.6 ms",
    label: "Triage latency p50",
    note: "ask_triage_latency.json",
  },
];

const PROBLEM = [
  "Office-hours load spikes; TAs need triage before the desk.",
  "Unstamped notes must not become course truth.",
  "Peer help and staff help both need accountability.",
];

const METHOD = [
  "Ask Triage: local MiniLM + sklearn at intake.",
  "Professor Material gate before Study Agent answers.",
  "Help Coach retrieval (not LLM); 0-TA → professor.",
  "Pedagogy Agent · Rooms · Classmate Notes · Insights.",
];

const IMPACT = [
  "Students get stamped answers or a clear refusal.",
  "TAs open a classified queue with coaching scripts.",
  "Professors control the KB and see struggle Insights.",
];

export default function CapstonePosterPage() {
  const [active, setActive] = useState("study");
  const [fit, setFit] = useState({ scale: 1, mx: 0, my: 0 });
  const layer = LAYERS.find((l) => l.id === active) || LAYERS[1];

  useEffect(() => {
    document.documentElement.setAttribute("data-theme", "light");
    document.body.classList.add("cfc-poster-lock");
    const relayout = () => {
      const scale = Math.min(window.innerWidth / 1920, window.innerHeight / 1080);
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
    <div className="mit-viewport">
      <article className="mit-stage" style={stageStyle} aria-label="OfficeHours AI research exhibition poster">
        <header className="mit-banner">
          <div className="mit-banner-left">
            <img src={`${BASE}aui-logo.png`} alt="" className="mit-logo" />
            <p className="mit-affiliation">
              Al Akhawayn University · School of Science &amp; Engineering · EGR 4402 Capstone
            </p>
          </div>
          <p className="mit-event">CFC Dean &amp; Employer Exhibition</p>
        </header>

        <div className="mit-titleblock">
          <h1 className="mit-title">OfficeHours AI</h1>
          <p className="mit-pitch">
            Faculty stamp the only answers the agent may quote — local Ask Triage, human escalation.
          </p>
        </div>

        <div className="mit-body">
          <section className="mit-figure" aria-label="System architecture figure">
            <div className="mit-figure-frame">
              <p className="mit-fig-label">Figure 1 · Modular-monolith helpdesk path</p>
              <svg
                className="mit-arch"
                viewBox="0 0 1240 270"
                role="img"
                aria-label="Canvas to SPA to FastAPI to model gateway to database"
              >
                <defs>
                  <filter id="mitSoft" x="-20%" y="-20%" width="140%" height="140%">
                    <feDropShadow dx="0" dy="3" stdDeviation="3" floodColor="#2d3b45" floodOpacity="0.12" />
                  </filter>
                  <linearGradient id="mitPlane" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#ffffff" />
                    <stop offset="100%" stopColor="#eef3ef" />
                  </linearGradient>
                </defs>

                {/* subtle depth floor */}
                <ellipse cx="620" cy="250" rx="540" ry="16" fill="rgba(0,104,56,0.08)" />

                {EDGES.map(([x1, y1, x2, y2], i) => (
                  <g key={i}>
                    <line
                      x1={x1}
                      y1={y1}
                      x2={x2}
                      y2={y2}
                      stroke="#008EE2"
                      strokeWidth="3"
                      strokeLinecap="round"
                    />
                    <polygon
                      points={`${x2},${y2} ${x2 - 10},${y2 - 5} ${x2 - 10},${y2 + 5}`}
                      fill="#008EE2"
                    />
                  </g>
                ))}

                {NODES.map((n) => (
                  <g key={n.id} filter="url(#mitSoft)" className="mit-node">
                    <rect
                      x={n.x}
                      y={n.y}
                      width={n.w}
                      height={n.h}
                      rx="6"
                      fill="url(#mitPlane)"
                      stroke={n.tall ? "#006838" : "#2d3b45"}
                      strokeWidth={n.tall ? 2.5 : 1.5}
                    />
                    {/* slight 3D edge */}
                    <path
                      d={`M${n.x + 6} ${n.y} L${n.x + 14} ${n.y - 8} L${n.x + n.w + 8} ${n.y - 8} L${n.x + n.w} ${n.y}`}
                      fill="rgba(0,104,56,0.12)"
                      stroke="none"
                    />
                    <text
                      x={n.x + n.w / 2}
                      y={n.y + (n.tall ? 72 : 42)}
                      textAnchor="middle"
                      className="mit-node-title"
                    >
                      {n.title}
                    </text>
                    <text
                      x={n.x + n.w / 2}
                      y={n.y + (n.tall ? 108 : 68)}
                      textAnchor="middle"
                      className="mit-node-sub"
                    >
                      {n.sub}
                    </text>
                  </g>
                ))}
              </svg>

              <div className="mit-layer-row" role="tablist" aria-label="Pipeline claims">
                {LAYERS.map((l) => (
                  <button
                    key={l.id}
                    type="button"
                    role="tab"
                    aria-selected={active === l.id}
                    className={`mit-layer-chip${active === l.id ? " is-active" : ""}`}
                    onClick={() => setActive(l.id)}
                  >
                    <span className="mit-layer-short">{l.short}</span>
                    <span className="mit-layer-claim">{l.claim}</span>
                  </button>
                ))}
              </div>

              <p className="mit-fig-caption" key={layer.id}>
                <strong>{layer.claim}.</strong> {layer.detail}
              </p>
            </div>
          </section>

          <aside className="mit-side">
            <section className="mit-col">
              <h2 className="mit-claim-h">Office hours lack a gated path from ask to answer</h2>
              <ul>
                {PROBLEM.map((line) => (
                  <li key={line}>{line}</li>
                ))}
              </ul>
            </section>

            <section className="mit-col">
              <h2 className="mit-claim-h">Gate locally, coach the TA, keep peers accountable</h2>
              <ul>
                {METHOD.map((line) => (
                  <li key={line}>{line}</li>
                ))}
              </ul>
            </section>

            <section className="mit-col">
              <h2 className="mit-claim-h">Stamped truth for students; load relief for staff</h2>
              <ul>
                {IMPACT.map((line) => (
                  <li key={line}>{line}</li>
                ))}
              </ul>
            </section>

            <section className="mit-results" aria-label="Measured results">
              <p className="mit-results-kicker">Results · verified FYP evidence</p>
              <div className="mit-results-grid">
                {RESULTS.map((r) => (
                  <div key={r.label} className="mit-result">
                    <strong className="mit-mono">{r.value}</strong>
                    <span>{r.label}</span>
                    <em>{r.note}</em>
                  </div>
                ))}
              </div>
              <p className="mit-pass">
                <span>PASS</span> 0-TA → professor routing · <span>PASS</span> grade-gap planner E2E
              </p>
            </section>
          </aside>
        </div>

        <footer className="mit-footer">
          <div className="mit-people">
            <p>
              <strong>Sophia Abssi</strong> · B.S. AI &amp; Robotization
            </p>
            <p>
              Supervisor <strong>Dr. Oumaima Hourrane</strong>
            </p>
          </div>
          <div className="mit-qr">
            <img
              src={`${BASE}poster-demo-qr.png`}
              alt="QR code to GitHub repository"
              className="mit-qr-img"
            />
            <div>
              <p className="mit-qr-title">Live prototype</p>
              <p className="mit-mono">github.com/abssisophia9-hub/officehours-ai</p>
            </div>
          </div>
        </footer>
      </article>
    </div>
  );
}
