import { useMemo, useState } from "react";
import { Link } from "react-router";

/**
 * Feedback prototype — NOT the live student workspace.
 * Keeps the current Dashboard look (stats + Ask + Study Agent).
 * Encapsulates Rooms / Classmate Notes / Revision Strategist in the sidebar.
 */

const NAV = [
  { id: "dashboard", label: "Dashboard", icon: "dashboard" },
  { id: "asks", label: "My asks", icon: "ask", badge: 2 },
  { id: "agent", label: "Study Agent", icon: "agent" },
  { id: "revision", label: "Revision Strategist", icon: "insights" },
  { id: "rooms", label: "Rooms", icon: "stuck" },
  { id: "notes", label: "Classmate Notes", icon: "notes" },
];

const ICONS = {
  dashboard: (
    <svg className="bh-nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
      <rect x="3" y="3" width="7.5" height="7.5" rx="1.5" />
      <rect x="13.5" y="3" width="7.5" height="7.5" rx="1.5" />
      <rect x="3" y="13.5" width="7.5" height="7.5" rx="1.5" />
      <rect x="13.5" y="13.5" width="7.5" height="7.5" rx="1.5" />
    </svg>
  ),
  ask: (
    <svg className="bh-nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
      <path d="M21 11.5a8.38 8.38 0 0 1-8.5 8.5 8.5 8.5 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 8.5-8.5 8.38 8.38 0 0 1 8.5 8.5z" />
    </svg>
  ),
  agent: (
    <svg className="bh-nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
      <rect x="4" y="7" width="16" height="12" rx="2" />
      <path d="M12 7V4M8 12h.01M16 12h.01M9 16h6" />
    </svg>
  ),
  notes: (
    <svg className="bh-nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
      <path d="M4 4h12v16H4z" />
      <path d="M16 8h4v12H8" />
      <path d="M7 9h6M7 13h6M7 17h4" />
    </svg>
  ),
  stuck: (
    <svg className="bh-nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
      <path d="M21 11.5a8.38 8.38 0 0 1-8.5 8.5 8.5 8.5 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 8.5-8.5 8.38 8.38 0 0 1 8.5 8.5z" />
      <path d="M8.5 12.5h7M12 9v7" />
    </svg>
  ),
  insights: (
    <svg className="bh-nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
      <path d="M4 19h16M7 16V9M12 16V5M17 16v-4" />
    </svg>
  ),
  courses: (
    <svg className="bh-nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
      <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20" />
      <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z" />
    </svg>
  ),
  clock: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" className="h-4 w-4">
      <circle cx="12" cy="12" r="9" />
      <path d="M12 7v5l3 3" />
    </svg>
  ),
  check: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" className="h-4 w-4">
      <circle cx="12" cy="12" r="9" />
      <path d="M8.5 12.5l2.5 2.5 5-5.5" />
    </svg>
  ),
};

const ASKS = [
  {
    id: "1842",
    title: "Red-black delete — why black-height breaks after transplant?",
    mode: "Quiet ask",
    status: "answered",
    stages: [
      { label: "Queued", done: true, detail: "Ask Triage → Alice Chen" },
      { label: "Claimed", done: true, detail: "Alice took your ask" },
      { label: "In progress", done: true, detail: "Help Coach draft used · 8 min" },
      { label: "Answered", done: true, detail: "Reply posted" },
    ],
    reply:
      "After transplant, if the deleted node was black, black-height drops by one. Fix with rotations + recolor from the replacement upward — same cases as CLRS delete-fixup.",
  },
  {
    id: "1831",
    title: "Hashing: chain vs open addressing for the project?",
    mode: "Identify me",
    status: "claimed",
    stages: [
      { label: "Queued", done: true, detail: "In TA desk" },
      { label: "Claimed", done: true, detail: "Sam Ortiz · face-to-face" },
      { label: "In progress", done: false, detail: "Waiting on meeting" },
      { label: "Answered", done: false, detail: "—" },
    ],
    meeting: "Thu 16:30 · Building 7 · Room 204",
    reply: null,
  },
  {
    id: "1820",
    title: "Do we need amortized analysis on the midterm?",
    mode: "Quiet ask",
    status: "queued",
    stages: [
      { label: "Queued", done: true, detail: "Waiting for a free TA" },
      { label: "Claimed", done: false, detail: "—" },
      { label: "In progress", done: false, detail: "—" },
      { label: "Answered", done: false, detail: "—" },
    ],
    reply: null,
  },
];

const GRADES = [
  { topic: "Trees & red-black", weight: 35, score: 62, source: "Canvas · Quiz 4" },
  { topic: "Hashing", weight: 25, score: 78, source: "Canvas · Assignment 3" },
  { topic: "Heaps", weight: 20, score: 88, source: "Canvas · Quiz 3" },
  { topic: "Amortized analysis", weight: 20, score: 71, source: "Canvas · practice" },
];

function gap(row) {
  return row.weight * Math.max(0, 85 - row.score);
}

export default function StudentVisionPrototype() {
  const [section, setSection] = useState("dashboard");
  const [activeAsk, setActiveAsk] = useState(ASKS[0].id);
  const [anonymous, setAnonymous] = useState(true);
  const [helpMode, setHelpMode] = useState("message");

  const ranked = useMemo(() => [...GRADES].sort((a, b) => gap(b) - gap(a)), []);
  const focus = ranked[0];
  const ask = ASKS.find((item) => item.id === activeAsk) || ASKS[0];

  return (
    <div className="bh-frame">
      <aside className="bh-sidebar">
        <div className="bh-logo">
          OfficeHours AI
          <small>Al Akhawayn University</small>
        </div>

        <p className="mx-3 mb-2 rounded-lg bg-amber-50 px-2 py-1.5 text-[10px] font-semibold uppercase tracking-wide text-amber-900">
          Prototype · not merged · feedback only
        </p>

        <nav className="bh-nav">
          {NAV.map((item) => (
            <button
              key={item.id}
              type="button"
              className={`bh-nav-item${section === item.id ? " active" : ""}`}
              onClick={() => setSection(item.id)}
            >
              {ICONS[item.icon]}
              <span className="flex flex-1 items-center justify-between gap-2">
                {item.label}
                {item.badge ? (
                  <span className="rounded-full bg-aui-forest px-1.5 py-0.5 text-[10px] font-bold text-white">
                    {item.badge}
                  </span>
                ) : null}
              </span>
            </button>
          ))}
          <Link to="/" className="bh-nav-item">
            {ICONS.courses}
            My Courses
          </Link>

          <p className="bh-nav-label">Course</p>
          <select className="bh-course-select" defaultValue="csc2302">
            <option value="csc2302">CSC 2302 (student)</option>
            <option value="csc3323">CSC 3323 (student)</option>
          </select>
        </nav>

        <div className="bh-user mt-auto">
          <div className="bh-avatar">SE</div>
          <div>
            <p className="bh-user-name">Sara El Idrissi</p>
            <p className="bh-user-role">Student · CSC 2302</p>
          </div>
        </div>
      </aside>

      <main className="bh-main">
        <div className="mb-4 flex flex-wrap items-center justify-between gap-2 rounded-xl border border-amber-200 bg-amber-50 px-4 py-2.5 text-xs text-amber-950">
          <span>
            Same dashboard look as today — Rooms, Notes, and Revision live in the
            sidebar only (not stacked on the Dashboard).
          </span>
          <Link to="/demo" className="font-semibold underline">
            Back to demos
          </Link>
        </div>

        {section === "dashboard" ? (
          <DashboardView
            anonymous={anonymous}
            setAnonymous={setAnonymous}
            helpMode={helpMode}
            setHelpMode={setHelpMode}
            focus={focus}
            onOpenAsks={() => setSection("asks")}
            onOpenRevision={() => setSection("revision")}
          />
        ) : null}
        {section === "asks" ? (
          <AsksView ask={ask} activeAsk={activeAsk} setActiveAsk={setActiveAsk} />
        ) : null}
        {section === "agent" ? <AgentView /> : null}
        {section === "revision" ? <RevisionView ranked={ranked} focus={focus} /> : null}
        {section === "rooms" ? <RoomsView /> : null}
        {section === "notes" ? <NotesView /> : null}
      </main>
    </div>
  );
}

function DashboardView({
  anonymous,
  setAnonymous,
  helpMode,
  setHelpMode,
  focus,
  onOpenAsks,
  onOpenRevision,
}) {
  return (
    <div className="fade-up">
      <h1 className="bh-page-title">Student Dashboard</h1>
      <p className="bh-page-subtitle">
        Ask staff quietly, study from professor-approved knowledge · CSC 2302 —
        Data Structures
      </p>

      {/* Keep familiar stats — drop Approved Knowledge / hit-rate (not student jobs) */}
      <div className="bh-stats">
        <article className="bh-stat-card">
          <div className="bh-stat-head">My asks {ICONS.clock}</div>
          <p className="bh-stat-value">3</p>
          <p className="bh-stat-note">Your asks in CSC 2302 — not the class queue</p>
        </article>
        <article className="bh-stat-card">
          <div className="bh-stat-head">My Quiet asks {ICONS.check}</div>
          <p className="bh-stat-value">2</p>
          <p className="bh-stat-note">Name hidden from staff — you can still open status</p>
        </article>
        <article className="bh-stat-card">
          <div className="bh-stat-head">Needs reply</div>
          <p className="bh-stat-value">1</p>
          <p className="bh-stat-note">
            <button type="button" className="font-semibold text-aui-forest underline" onClick={onOpenAsks}>
              Open My asks
            </button>{" "}
            to read TA replies
          </p>
        </article>
        <article className="bh-stat-card">
          <div className="bh-stat-head">Today&apos;s focus</div>
          <p className="bh-stat-value text-lg leading-snug">{focus.topic.split(" ")[0]}</p>
          <p className="bh-stat-note">
            Canvas {focus.score}% · {focus.weight}% exam ·{" "}
            <button type="button" className="font-semibold text-aui-forest underline" onClick={onOpenRevision}>
              Revision plan
            </button>
          </p>
        </article>
      </div>

      <div className="grid gap-0 lg:grid-cols-2 lg:gap-5">
        <section id="ask" className="bh-card scroll-mt-6">
          <div className="bh-card-title">
            <h2>Ask for Help</h2>
          </div>
          <p className="bh-card-note">
            Choose whether staff see your name, and how you want to meet —
            message only, face-to-face, or online.
          </p>

          <div className="mt-4 rounded-xl border border-aui-forest/25 bg-[#f3faf5] p-3 sm:p-4">
            <p className="text-sm font-semibold text-aui-ink">Who should staff see?</p>
            <div className="mt-3 grid gap-2 sm:grid-cols-2">
              {[
                { value: true, title: "Quiet ask", note: "Anonymous — no name or student ID stored." },
                { value: false, title: "Identify me", note: "Share Sara El Idrissi · ID 117400." },
              ].map((opt) => (
                <label
                  key={String(opt.value)}
                  className={`flex cursor-pointer items-start gap-3 rounded-xl border px-3 py-3 transition ${
                    anonymous === opt.value
                      ? "border-aui-forest bg-white shadow-sm"
                      : "border-[#d7e0d9] bg-white/70"
                  }`}
                >
                  <input
                    type="radio"
                    className="mt-1 h-4 w-4 accent-aui-forest"
                    checked={anonymous === opt.value}
                    onChange={() => setAnonymous(opt.value)}
                  />
                  <span>
                    <span className="block text-sm font-semibold text-aui-ink">{opt.title}</span>
                    <span className="mt-0.5 block text-xs font-medium text-aui-deep/70">{opt.note}</span>
                  </span>
                </label>
              ))}
            </div>
          </div>

          <fieldset className="mt-4 space-y-2">
            <legend className="text-xs font-semibold uppercase tracking-wide text-aui-deep/60">
              How do you want help?
            </legend>
            {[
              { value: "message", title: "Message / async", note: "Answer in the queue — no live meeting." },
              { value: "face_to_face", title: "Face-to-face meeting", note: "In-person office-hours on campus." },
              { value: "online_meeting", title: "Online meeting", note: "Zoom / Teams with a TA or professor." },
            ].map((option) => (
              <label key={option.value} className="clay-blob flex w-full cursor-pointer items-start gap-3 px-4 py-3">
                <input
                  type="radio"
                  className="mt-1 h-4 w-4 accent-aui-forest"
                  checked={helpMode === option.value}
                  onChange={() => setHelpMode(option.value)}
                />
                <span>
                  <span className="block text-sm font-semibold text-aui-ink">{option.title}</span>
                  <span className="mt-0.5 block text-xs font-medium text-aui-deep/70">{option.note}</span>
                </span>
              </label>
            ))}
          </fieldset>

          <textarea
            className="field-glass mt-3 min-h-32 px-4 py-3 text-sm"
            placeholder="Describe what you're stuck on…"
            defaultValue=""
          />
          <textarea
            className="field-glass mt-3 min-h-20 px-4 py-3 font-mono text-xs"
            placeholder="Optional code snippet"
            defaultValue=""
          />
          <button type="button" className="btn-primary mt-4 px-5 py-2.5 text-sm">
            {anonymous ? "Submit anonymously" : "Submit as me"}
          </button>

          <div className="mt-5 rounded-xl border border-[#e3e8e4] bg-[#fafcfa] p-3">
            <div className="flex items-center justify-between gap-2">
              <p className="text-sm font-semibold text-aui-ink">My asks</p>
              <button type="button" className="text-xs font-semibold text-aui-forest underline" onClick={onOpenAsks}>
                Full status →
              </button>
            </div>
            <p className="mt-1 text-xs text-aui-deep/70">
              Latest in this course. Open My asks for queued → claimed → answered.
            </p>
            <ul className="mt-3 space-y-2">
              {ASKS.slice(0, 2).map((item) => (
                <li key={item.id}>
                  <button
                    type="button"
                    className="w-full rounded-lg border border-[#d7e0d9] bg-white px-3 py-2 text-left text-xs hover:border-aui-forest"
                    onClick={onOpenAsks}
                  >
                    <span className="font-semibold text-aui-ink">#{item.id}</span>
                    {" · "}
                    {item.mode}
                    {" · "}
                    <span className="bh-pill bh-pill-green">{item.status}</span>
                    <span className="mt-1 block truncate text-aui-deep/80">{item.title}</span>
                  </button>
                </li>
              ))}
            </ul>
          </div>
        </section>

        <section id="agent" className="bh-card scroll-mt-6">
          <div className="bh-card-title">
            <h2>Course Study Agent</h2>
          </div>
          <p className="bh-card-note">
            Answers only from professor-approved FAQs and Canvas course materials
            for CSC 2302. If nothing matches, stop guessing — Quiet ask a TA instead.
          </p>
          <form
            className="mt-4"
            onSubmit={(event) => {
              event.preventDefault();
            }}
          >
            <input
              className="field-glass px-4 py-3 text-sm"
              placeholder="Ask from approved answers / slides…"
              defaultValue=""
            />
            <button type="submit" className="btn-ghost mt-3 px-4 py-2 text-sm">
              Ask agent
            </button>
          </form>
          <p className="soft-stat mt-4 text-sm text-aui-deep/70">
            Tip: Rooms and Classmate Notes are in the sidebar — they no longer sit
            under this dashboard.
          </p>
        </section>
      </div>
    </div>
  );
}

function AsksView({ ask, activeAsk, setActiveAsk }) {
  return (
    <div className="fade-up">
      <h1 className="bh-page-title">My asks</h1>
      <p className="bh-page-subtitle">
        Track status and read TA / professor replies here — queued → claimed → in
        progress → answered.
      </p>

      <div className="grid gap-5 lg:grid-cols-[minmax(240px,0.9fr)_minmax(0,1.2fr)]">
        <section className="bh-card">
          <div className="bh-card-title">
            <h2>This course</h2>
          </div>
          <ul className="mt-3 space-y-2">
            {ASKS.map((item) => (
              <li key={item.id}>
                <button
                  type="button"
                  className={`w-full rounded-lg border px-3 py-2 text-left text-xs ${
                    activeAsk === item.id
                      ? "border-aui-forest bg-[#f3faf5]"
                      : "border-[#d7e0d9] bg-white hover:border-aui-forest"
                  }`}
                  onClick={() => setActiveAsk(item.id)}
                >
                  <span className="font-semibold text-aui-ink">#{item.id}</span>
                  {" · "}
                  {item.mode}
                  {" · "}
                  {item.status}
                  <span className="mt-1 block truncate text-aui-deep/80">{item.title}</span>
                </button>
              </li>
            ))}
          </ul>
        </section>

        <section className="bh-card">
          <div className="bh-card-title">
            <h2>#{ask.id}</h2>
          </div>
          <p className="bh-card-note">{ask.title}</p>
          <ol className="mt-4 space-y-2">
            {ask.stages.map((stage) => (
              <li
                key={stage.label}
                className={`rounded-lg border px-3 py-2 text-xs ${
                  stage.done
                    ? "border-aui-forest/30 bg-[#f3faf5]"
                    : "border-[#e3e8e4] bg-[#fafcfa] text-aui-deep/60"
                }`}
              >
                <p className="font-semibold text-aui-ink">{stage.label}</p>
                <p className="mt-0.5">{stage.detail}</p>
              </li>
            ))}
          </ol>
          {ask.meeting ? (
            <div className="mt-4 rounded-lg border border-emerald-200 bg-emerald-50 p-3 text-xs text-emerald-950">
              <p className="font-semibold">Meeting</p>
              <p className="mt-1">{ask.meeting}</p>
            </div>
          ) : null}
          {ask.reply ? (
            <div className="soft-stat mt-4 text-sm">
              <p className="font-semibold text-aui-ink">TA reply</p>
              <p className="mt-1">{ask.reply}</p>
            </div>
          ) : (
            <p className="mt-4 text-xs text-aui-deep/60">No reply yet — status above is the source of truth.</p>
          )}
        </section>
      </div>
    </div>
  );
}

function AgentView() {
  return (
    <div className="fade-up">
      <h1 className="bh-page-title">Study Agent</h1>
      <p className="bh-page-subtitle">
        Same Course Study Agent — only from professor-stamped materials for CSC 2302.
      </p>
      <section className="bh-card max-w-3xl">
        <div className="bh-card-title">
          <h2>Course Study Agent</h2>
        </div>
        <p className="bh-card-note">
          Answers only from professor-approved FAQs and Canvas course materials.
          If nothing matches, Quiet ask a TA.
        </p>
        <input
          className="field-glass mt-4 px-4 py-3 text-sm"
          placeholder="Ask from approved answers / slides…"
          defaultValue="When do we use open addressing instead of chaining?"
        />
        <button type="button" className="btn-ghost mt-3 px-4 py-2 text-sm">
          Ask agent
        </button>
        <p className="soft-stat mt-4 whitespace-pre-wrap text-sm">
          Use open addressing when load factor stays moderate and you want
          cache-friendly probes. Prefer chaining when deletions are frequent.
          Source: Week 6 stamped notes.
        </p>
      </section>
    </div>
  );
}

function RevisionView({ ranked, focus }) {
  return (
    <div className="fade-up">
      <h1 className="bh-page-title">Revision Strategist</h1>
      <p className="bh-page-subtitle">
        Reads Canvas grades + syllabus exam weights, then builds your plan —
        like a parent checking your grades and telling you what to prioritize.
      </p>

      <div className="grid gap-5 lg:grid-cols-2">
        <section className="bh-card">
          <div className="bh-card-title">
            <h2>From Canvas + syllabus</h2>
          </div>
          <p className="bh-card-note">Live performance vs exam weight.</p>
          <ul className="mt-4 space-y-2">
            {ranked.map((row) => (
              <li
                key={row.topic}
                className="flex items-center justify-between gap-3 rounded-lg border border-[#d7e0d9] bg-white px-3 py-2 text-sm"
              >
                <div>
                  <p className="font-semibold text-aui-ink">{row.topic}</p>
                  <p className="text-xs text-aui-deep/70">
                    {row.source} · {row.weight}% of exam
                  </p>
                </div>
                <span className={`text-lg font-bold ${row.score < 70 ? "text-amber-800" : "text-aui-forest"}`}>
                  {row.score}%
                </span>
              </li>
            ))}
          </ul>
          <p className="soft-stat mt-4 text-sm">
            Focus: <strong>{focus.topic}</strong> — lowest score among high exam
            weight.
          </p>
        </section>

        <section className="bh-card">
          <div className="bh-card-title">
            <h2>Today&apos;s plan</h2>
          </div>
          <p className="bh-card-note">
            Why: Canvas Quiz 4 = {focus.score}%. Trees are {focus.weight}% of the
            final. 18 days left.
          </p>
          <p className="mt-3 text-sm font-semibold text-aui-ink">
            2 h 15 min · finish by 22:30
          </p>
          <ol className="mt-3 space-y-2 text-sm">
            <li className="rounded-lg border border-[#d7e0d9] bg-white px-3 py-2">
              <strong>Block 1 · 45 min</strong> — CLRS delete-fixup + Week 5 slides
            </li>
            <li className="rounded-lg border border-[#d7e0d9] bg-white px-3 py-2">
              <strong>Block 2 · 60 min</strong> — Textbook 13.3 problems 1–6
            </li>
            <li className="rounded-lg border border-[#d7e0d9] bg-white px-3 py-2">
              <strong>Block 3 · 30 min</strong> — Self quiz target 75%+
            </li>
          </ol>
          <div className="mt-4 rounded-lg border border-aui-forest/20 bg-[#f3faf5] p-3 text-xs">
            <p className="font-semibold text-aui-ink">Resources ranked for you</p>
            <ol className="mt-2 list-decimal space-y-1 pl-4 text-aui-deep/85">
              <li>3Blue1Brown — red-black intuition</li>
              <li>Course stamped slides — Week 5</li>
              <li>PatrickJMT — step-by-step when stuck</li>
            </ol>
          </div>
        </section>
      </div>

      <section className="bh-card mt-5">
        <div className="bh-card-title">
          <h2>This week</h2>
        </div>
        <div className="mt-3 grid gap-2 sm:grid-cols-7">
          {[
            ["Mon", "Trees · fixup", "2.5h"],
            ["Tue", "Trees · insert", "2h"],
            ["Wed", "Trees · quiz", "2.5h"],
            ["Thu", "Hashing keep", "2h"],
            ["Fri", "Hashing project", "1.5h"],
            ["Sat", "Heaps light", "1h"],
            ["Sun", "Rest", "—"],
          ].map(([day, topic, dur]) => (
            <div key={day} className="rounded-lg border border-[#d7e0d9] bg-white p-2 text-xs">
              <p className="font-bold text-aui-forest">{day}</p>
              <p className="mt-1 text-aui-ink">{topic}</p>
              <p className="mt-2 text-aui-deep/60">{dur}</p>
            </div>
          ))}
        </div>
        <p className="bh-card-note mt-3">
          Next Sunday: if Trees ≥ 75%, drop to 2 days. If it falls, escalate and
          pause maintenance topics. Grades decide the calendar.
        </p>
      </section>
    </div>
  );
}

function RoomsView() {
  return (
    <div className="fade-up">
      <h1 className="bh-page-title">Rooms</h1>
      <p className="bh-page-subtitle">
        Classmates only — encapsulated here, not on the Dashboard.
      </p>
      <section className="bh-card max-w-3xl">
        <div className="bh-card-title">
          <h2>r/CSC2302</h2>
        </div>
        <p className="bh-card-note">
          Stuck threads, article rooms, Hilbert board. Staff do not sit in the
          room.
        </p>
        <button type="button" className="btn-primary mt-4 px-5 py-2.5 text-sm">
          Enter room
        </button>
      </section>
    </div>
  );
}

function NotesView() {
  return (
    <div className="fade-up">
      <h1 className="bh-page-title">Classmate Notes</h1>
      <p className="bh-page-subtitle">
        Share and browse notes here — removed from the Dashboard stack.
      </p>
      <section className="bh-card max-w-3xl">
        <div className="bh-card-title">
          <h2>Share with classmates</h2>
        </div>
        <p className="bh-card-note">PDF, DOCX, or images · optional hide my name.</p>
        <input className="field-glass mt-3 px-4 py-3 text-sm" placeholder="Title" />
        <input className="field-glass mt-2 px-4 py-3 text-sm" placeholder="Topic (week, lecture…)" />
        <button type="button" className="btn-primary mt-4 px-5 py-2.5 text-sm">
          Share with classmates
        </button>
        <p className="mt-4 text-xs text-aui-deep/60">No classmate notes yet for CSC 2302.</p>
      </section>
    </div>
  );
}
