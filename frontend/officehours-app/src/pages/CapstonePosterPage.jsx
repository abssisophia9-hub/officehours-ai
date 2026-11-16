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

/**
 * Exhibition redesign — recruiter-scannable “helpdesk engine”.
 * Metrics/modules verified from reports/final_report/*, docs/eval_results,
 * course_ta_service (0-TA), README agents table, AppShell roles.
 */

const STACK = [
  { label: "React", Icon: SiReact, color: "#61DAFB" },
  { label: "Vite", Icon: SiVite, color: "#646CFF" },
  { label: "Tailwind", Icon: SiTailwindcss, color: "#06B6D4" },
  { label: "FastAPI", Icon: SiFastapi, color: "#009688" },
  { label: "SQLAlchemy", Icon: SiSqlalchemy, color: "#D71F00" },
  { label: "Postgres", Icon: SiPostgresql, color: "#4169E1" },
  { label: "SQLite", Icon: SiSqlite, color: "#003B57" },
  { label: "MiniLM", Icon: SiHuggingface, color: "#FFD21E" },
  { label: "sklearn", Icon: SiScikitlearn, color: "#F7931E" },
  { label: "Gemini", Icon: SiGooglegemini, color: "#8E75B2" },
  { label: "Canvas", Icon: SiInstructure, color: "#E72429" },
  { label: "YouTube", Icon: SiYoutube, color: "#FF0000" },
];

/** Interactive architecture planes — names match README / services */
const PLANES = [
  {
    id: "triage",
    tag: "01 · Intake",
    title: "Ask Triage",
    claim: "Local MiniLM + scikit-learn — not a prompted chat.",
    detail:
      "On ask submit: Analyzer → Matcher → Synthesizer (category, urgency, tags, TA match, teaching hint). Default path is trained local models.",
    accent: "emerald",
  },
  {
    id: "study",
    tag: "02 · Gate",
    title: "Professor-Gated Study Agent",
    claim: "Only stamped course material reaches the student answer.",
    detail:
      "Retrieval over professor-approved KB for the caller’s course. Optional Gemini entailment check only when demo + LLM flags allow. Unapproved/other-course refusal measured 10/10 + 10/10.",
    accent: "canvas",
  },
  {
    id: "coach",
    tag: "03 · Desk",
    title: "Help Coach + Live Queue",
    claim: "Coaches the TA — does not answer as course truth.",
    detail:
      "Mid-session assist from teaching-bank + approved KB retrieval (no LLM). Queue tracks open → claimed → in progress; 0-TA courses auto-route to the professor.",
    accent: "brass",
  },
  {
    id: "pedagogy",
    tag: "04 · Recover",
    title: "Pedagogy Agent · Rooms · Notes",
    claim: "Grade-gap plans + peer pathways beside staff help.",
    detail:
      "Pedagogy builds focus plans from practice scores + learning style (Resources via trusted search / YouTube when keyed). Rooms and Classmate Notes give peer collaboration without inventing syllabus.",
    accent: "ink",
  },
];

const KPIS = [
  {
    value: "100%",
    label: "Unapproved refusal",
    note: "with_check gated · 10/10 + 10/10",
  },
  {
    value: "74/75",
    label: "Study answer-check",
    note: "98.7% · Gemini check suite",
  },
  {
    value: "84.6%",
    label: "Triage macro F1",
    note: "5-fold CV · n=156",
  },
  {
    value: "62.6ms",
    label: "Triage latency p50",
    note: "ask_triage_latency.json",
  },
];

const PASSES = ["0-TA → professor routing", "Grade-gap planner E2E"];

const ROLES = [
  {
    role: "Student",
    lines: ["Study Agent", "Ask + My asks", "Pedagogy Agent", "Rooms · Notes"],
  },
  {
    role: "TA",
    lines: ["Live Queue", "Help Coach", "Past asks"],
  },
  {
    role: "Professor",
    lines: ["Material gate", "Insights", "Team · Desk"],
  },
];

const EXTRA = [
  { label: "Matcher holdout", value: "87.5%" },
  { label: "Gold analyzer", value: "75.0%" },
  { label: "Learning-style CV", value: "92.5%" },
];

export default function CapstonePosterPage() {
  const [active, setActive] = useState("study");
  const [fit, setFit] = useState({ scale: 1, mx: 0, my: 0 });
  const plane = PLANES.find((p) => p.id === active) || PLANES[1];

  useEffect(() => {
    document.documentElement.setAttribute("data-theme", "light");
    document.body.classList.add("cfc-poster-lock");
    const relayout = () => {
      const scale = Math.min(window.innerWidth / 1080, window.innerHeight / 1920);
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
    <div className="expo-viewport">
      <article className="expo-stage" style={stageStyle} aria-label="OfficeHours AI exhibition poster">
        <div className="expo-atmosphere" aria-hidden="true">
          <div className="expo-glow expo-glow--a" />
          <div className="expo-glow expo-glow--b" />
          <div className="expo-grid" />
          <div className="expo-signal" />
        </div>

        {/* HERO — 10-second recruiter read */}
        <header className="expo-hero">
          <div className="expo-hero-meta">
            <img src={`${BASE}aui-logo.png`} alt="" className="expo-logo" />
            <div>
              <p className="expo-kicker">AUI · EGR 4402 Capstone · CFC Exhibition</p>
              <p className="expo-people">
                Sophia Abssi · B.S. AI &amp; Robotization · Supervisor Dr. Oumaima Hourrane
              </p>
            </div>
          </div>
          <h1 className="expo-brand">OfficeHours AI</h1>
          <p className="expo-claim">
            Faculty stamp the only answers the agent may quote.
            <span> Local triage. Human accountability. Peer Rooms.</span>
          </p>
          <p className="expo-thesis">
            One login, role per course — Ask Triage at intake, Help Coach on the TA desk,
            professor-gated Study Agent, Pedagogy Agent for grade-gap recovery, and Canvas LTI when
            live.
          </p>
          <div className="expo-stack">
            {STACK.map(({ label, Icon, color }) => (
              <span key={label} className="expo-badge">
                <Icon aria-hidden style={{ color }} />
                {label}
              </span>
            ))}
          </div>
        </header>

        {/* 3D ENGINE SPINE */}
        <section className="expo-engine" aria-label="Interactive system architecture">
          <div className="expo-engine-copy">
            <p className="expo-section-label">Core engine</p>
            <h2>Four layers. One modular monolith.</h2>
            <p>
              FastAPI backend · React SPA · SQLAlchemy (SQLite / Postgres) · Canvas LTI 1.3 · Model
              gateway with egress guard for gated Gemini.
            </p>
            <div className={`expo-detail expo-detail--${plane.accent}`} key={plane.id}>
              <p className="expo-detail-tag">{plane.tag}</p>
              <h3>{plane.title}</h3>
              <p className="expo-detail-claim">{plane.claim}</p>
              <p>{plane.detail}</p>
            </div>
          </div>

          <div className="expo-scene" aria-hidden={false}>
            <div className="expo-scene-floor" />
            <div className="expo-rig">
              {PLANES.map((p, i) => (
                <button
                  key={p.id}
                  type="button"
                  className={`expo-plane expo-plane--${p.accent}${active === p.id ? " is-active" : ""}`}
                  style={{ "--i": i }}
                  onClick={() => setActive(p.id)}
                  aria-pressed={active === p.id}
                >
                  <span className="expo-plane-tag">{p.tag}</span>
                  <span className="expo-plane-title">{p.title}</span>
                  <span className="expo-plane-hint">{p.claim}</span>
                </button>
              ))}
            </div>
            <p className="expo-scene-hint">Tap a layer · CSS 3D hierarchy</p>
          </div>
        </section>

        {/* PROOF */}
        <section className="expo-proof" aria-label="Measured evidence">
          <p className="expo-section-label">Measured evidence</p>
          <div className="expo-kpis">
            {KPIS.map((k) => (
              <div key={k.label} className="expo-kpi">
                <strong className="expo-mono">{k.value}</strong>
                <span>{k.label}</span>
                <em>{k.note}</em>
              </div>
            ))}
          </div>
          <div className="expo-proof-row">
            <div className="expo-passes">
              {PASSES.map((p) => (
                <span key={p} className="expo-pass">
                  <em>PASS</em> {p}
                </span>
              ))}
            </div>
            <div className="expo-extra">
              {EXTRA.map((e) => (
                <span key={e.label}>
                  <strong className="expo-mono">{e.value}</strong> {e.label}
                </span>
              ))}
            </div>
          </div>
        </section>

        {/* ROLES + QR */}
        <section className="expo-impact">
          <div className="expo-roles">
            {ROLES.map((r) => (
              <div key={r.role} className="expo-role">
                <h3>{r.role}</h3>
                <ul>
                  {r.lines.map((line) => (
                    <li key={line}>{line}</li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
          <div className="expo-qr">
            <img
              src={`${BASE}poster-demo-qr.png`}
              alt="QR code to GitHub repository"
              className="expo-qr-img"
            />
            <div>
              <p className="expo-qr-title">Prototype</p>
              <p className="expo-mono expo-qr-url">github.com/abssisophia9-hub/officehours-ai</p>
            </div>
          </div>
        </section>

        <footer className="expo-footer">
          Al Akhawayn University · School of Science &amp; Engineering · EGR 4402 · Casablanca
          Finance City Showcase
        </footer>
      </article>
    </div>
  );
}
