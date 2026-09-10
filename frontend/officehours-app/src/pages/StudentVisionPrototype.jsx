import { useMemo, useState } from "react";
import { Link } from "react-router";
import "./studentVisionPrototype.css";

const SECTIONS = [
  { id: "home", label: "Home" },
  { id: "asks", label: "My asks" },
  { id: "study", label: "Study Agent" },
  { id: "revision", label: "Revision Strategist" },
  { id: "rooms", label: "Rooms" },
];

const ASKS = [
  {
    id: "OH-1842",
    title: "Red-black delete — why black-height breaks after transplant?",
    mode: "Quiet ask",
    updated: "12 min ago",
    stage: "answered",
    stages: [
      { key: "queued", label: "Queued", done: true, detail: "Ask Triage routed to Alice Chen" },
      { key: "claimed", label: "Claimed", done: true, detail: "Alice took your ask" },
      { key: "working", label: "In progress", done: true, detail: "Help Coach draft used · 8 min" },
      { key: "answered", label: "Answered", done: true, detail: "Reply posted · meeting optional" },
    ],
    reply:
      "After transplant, if the deleted node was black, the black-height of that subtree drops by one. Fix with rotations + recolor from the replacement node upward — same cases as CLRS delete-fixup.",
  },
  {
    id: "OH-1831",
    title: "Hashing collision chain vs open addressing for our project?",
    mode: "Identify me",
    updated: "Yesterday",
    stage: "claimed",
    stages: [
      { key: "queued", label: "Queued", done: true, detail: "In TA desk" },
      { key: "claimed", label: "Claimed", done: true, detail: "Sam Ortiz claimed · face-to-face" },
      { key: "working", label: "In progress", done: false, detail: "Waiting on meeting slot" },
      { key: "answered", label: "Answered", done: false, detail: "—" },
    ],
    reply: null,
    meeting: "Thu 16:30 · Building 7 · Room 204",
  },
  {
    id: "OH-1820",
    title: "Do we need amortized analysis on the midterm?",
    mode: "Quiet ask",
    updated: "2 days ago",
    stage: "queued",
    stages: [
      { key: "queued", label: "Queued", done: true, detail: "Waiting for a free TA" },
      { key: "claimed", label: "Claimed", done: false, detail: "—" },
      { key: "working", label: "In progress", done: false, detail: "—" },
      { key: "answered", label: "Answered", done: false, detail: "—" },
    ],
    reply: null,
  },
];

const GRADES = [
  { topic: "Trees & red-black", weight: 35, score: 62, source: "Canvas · Quiz 4" },
  { topic: "Hashing", weight: 25, score: 78, source: "Canvas · Assignment 3" },
  { topic: "Heaps & priority queues", weight: 20, score: 88, source: "Canvas · Quiz 3" },
  { topic: "Amortized analysis", weight: 20, score: 71, source: "Canvas · Midterm practice" },
];

function gapPriority(row) {
  return row.weight * Math.max(0, 85 - row.score);
}

export default function StudentVisionPrototype() {
  const [section, setSection] = useState("home");
  const [activeAsk, setActiveAsk] = useState(ASKS[0].id);

  const ranked = useMemo(
    () => [...GRADES].sort((a, b) => gapPriority(b) - gapPriority(a)),
    [],
  );
  const focus = ranked[0];
  const ask = ASKS.find((item) => item.id === activeAsk) || ASKS[0];
  const openCount = ASKS.filter((item) => item.stage !== "answered").length;

  return (
    <div className="svp">
      <header className="svp-top">
        <div>
          <p className="svp-kicker">Prototype · not merged · feedback only</p>
          <h1>Student space — scannable IA</h1>
          <p className="svp-lead">
            One job per page. Home only shows what needs you. Asks are where
            answers and status live. Study Agent answers stamped material.
            Revision Strategist reads Canvas grades + syllabus weights and
            tells you what to prioritize — like a parent checking your grades.
          </p>
        </div>
        <Link className="svp-exit" to="/demo">
          Back to demos
        </Link>
      </header>

      <div className="svp-shell">
        <aside className="svp-nav" aria-label="Prototype sections">
          <p className="svp-course">CSC 2302 · Data Structures</p>
          <p className="svp-who">Sara El Idrissi · student</p>
          <nav>
            {SECTIONS.map((item) => (
              <button
                key={item.id}
                type="button"
                className={section === item.id ? "is-on" : undefined}
                onClick={() => setSection(item.id)}
              >
                {item.label}
                {item.id === "asks" && openCount ? (
                  <span className="svp-badge">{openCount}</span>
                ) : null}
              </button>
            ))}
          </nav>
          <p className="svp-aside-note">
            This nav is the product map. Nothing from Rooms or Revision should
            spill into Home except a one-line next action.
          </p>
        </aside>

        <main className="svp-main">
          {section === "home" ? (
            <HomePanel
              openCount={openCount}
              focus={focus}
              onOpenAsks={() => setSection("asks")}
              onOpenRevision={() => setSection("revision")}
              onOpenStudy={() => setSection("study")}
              onOpenRooms={() => setSection("rooms")}
            />
          ) : null}
          {section === "asks" ? (
            <AsksPanel ask={ask} activeAsk={activeAsk} setActiveAsk={setActiveAsk} />
          ) : null}
          {section === "study" ? <StudyPanel /> : null}
          {section === "revision" ? (
            <RevisionPanel ranked={ranked} focus={focus} />
          ) : null}
          {section === "rooms" ? <RoomsPanel /> : null}
        </main>
      </div>
    </div>
  );
}

function HomePanel({ openCount, focus, onOpenAsks, onOpenRevision, onOpenStudy, onOpenRooms }) {
  return (
    <section className="svp-panel">
      <header className="svp-panel-head">
        <h2>Home</h2>
        <p>Only what needs you right now. Everything else lives in its own section.</p>
      </header>

      <div className="svp-stack">
        <article className="svp-card svp-card-priority">
          <p className="svp-card-kicker">Needs you</p>
          <h3>{openCount} open asks</h3>
          <p>
            One has a TA reply. One is claimed for a face-to-face. One is still
            waiting in the queue.
          </p>
          <button type="button" className="svp-btn" onClick={onOpenAsks}>
            Open My asks
          </button>
        </article>

        <article className="svp-card">
          <p className="svp-card-kicker">Today from Revision Strategist</p>
          <h3>{focus.topic}</h3>
          <p>
            Canvas shows <strong>{focus.score}%</strong> on a topic worth{" "}
            <strong>{focus.weight}%</strong> of the exam. That is your priority
            today — not because you like it, because the grades say so.
          </p>
          <button type="button" className="svp-btn svp-btn-ghost" onClick={onOpenRevision}>
            See weekly plan
          </button>
        </article>

        <div className="svp-link-row">
          <button type="button" className="svp-link-card" onClick={onOpenStudy}>
            <span>Study Agent</span>
            <small>Ask from professor-stamped materials only</small>
          </button>
          <button type="button" className="svp-link-card" onClick={onOpenRooms}>
            <span>Rooms</span>
            <small>Classmates · not staff · not on this home page</small>
          </button>
        </div>
      </div>
    </section>
  );
}

function AsksPanel({ ask, activeAsk, setActiveAsk }) {
  return (
    <section className="svp-panel">
      <header className="svp-panel-head">
        <h2>My asks</h2>
        <p>
          This is where answers land and where you track: queued → claimed → in
          progress → answered. Not buried under the ask form.
        </p>
      </header>

      <div className="svp-asks">
        <ul className="svp-ask-list">
          {ASKS.map((item) => (
            <li key={item.id}>
              <button
                type="button"
                className={activeAsk === item.id ? "is-on" : undefined}
                onClick={() => setActiveAsk(item.id)}
              >
                <span className="svp-ask-id">{item.id}</span>
                <strong>{item.title}</strong>
                <em>
                  {item.mode} · {item.updated} · {item.stage}
                </em>
              </button>
            </li>
          ))}
        </ul>

        <article className="svp-ask-detail">
          <p className="svp-card-kicker">{ask.id}</p>
          <h3>{ask.title}</h3>
          <ol className="svp-timeline">
            {ask.stages.map((stage) => (
              <li key={stage.key} className={stage.done ? "is-done" : undefined}>
                <span>{stage.label}</span>
                <small>{stage.detail}</small>
              </li>
            ))}
          </ol>
          {ask.meeting ? (
            <div className="svp-reply-box">
              <p className="svp-card-kicker">Meeting</p>
              <p>{ask.meeting}</p>
            </div>
          ) : null}
          {ask.reply ? (
            <div className="svp-reply-box is-answer">
              <p className="svp-card-kicker">TA reply</p>
              <p>{ask.reply}</p>
            </div>
          ) : (
            <p className="svp-muted">No staff reply yet — status above is the source of truth.</p>
          )}
          <button type="button" className="svp-btn svp-btn-ghost">
            New Quiet ask
          </button>
        </article>
      </div>
    </section>
  );
}

function StudyPanel() {
  return (
    <section className="svp-panel">
      <header className="svp-panel-head">
        <h2>Study Agent</h2>
        <p>
          One job: answer from professor-stamped knowledge for this course. If
          it is not stamped, it refuses. This is not the planner.
        </p>
      </header>
      <article className="svp-card">
        <label className="svp-label" htmlFor="study-q">
          Ask from approved materials
        </label>
        <textarea
          id="study-q"
          className="svp-input"
          rows={3}
          defaultValue="When do we use open addressing instead of chaining?"
        />
        <button type="button" className="svp-btn">
          Ask Study Agent
        </button>
        <div className="svp-reply-box is-answer">
          <p className="svp-card-kicker">From stamped FAQ · Benali</p>
          <p>
            Use open addressing when load factor stays moderate and you want
            cache-friendly probes. Prefer chaining when deletions are frequent
            or keys cluster. Source: Week 6 stamped notes.
          </p>
        </div>
      </article>
    </section>
  );
}

function RevisionPanel({ ranked, focus }) {
  return (
    <section className="svp-panel">
      <header className="svp-panel-head">
        <h2>Revision Strategist</h2>
        <p>
          Reads Canvas grades + syllabus exam weights. Builds a clear plan —
          what to prioritize, for how long, with which resources. Parent logic:
          grades decide the calendar.
        </p>
      </header>

      <div className="svp-rev-grid">
        <article className="svp-card">
          <p className="svp-card-kicker">From Canvas + syllabus</p>
          <h3>Current performance</h3>
          <ul className="svp-grade-list">
            {ranked.map((row) => (
              <li key={row.topic}>
                <div>
                  <strong>{row.topic}</strong>
                  <small>
                    {row.source} · {row.weight}% of exam
                  </small>
                </div>
                <span className={row.score < 70 ? "is-low" : undefined}>{row.score}%</span>
              </li>
            ))}
          </ul>
          <p className="svp-focus-line">
            Focus: <strong>{focus.topic}</strong> — lowest score among high exam
            weight. That is the priority.
          </p>
        </article>

        <article className="svp-card svp-card-priority">
          <p className="svp-card-kicker">Today&apos;s focus</p>
          <h3>Red-black delete-fixup cases</h3>
          <p className="svp-why">
            Why: Canvas Quiz 4 = 62%. Trees are 35% of the final. 18 days left.
            No negotiation — this is the gap.
          </p>
          <p className="svp-time">
            <strong>2 h 15 min</strong> · start now · finish by 22:30
          </p>
          <ol className="svp-blocks">
            <li>
              <strong>Block 1 · 45 min · Concept</strong>
              <span>CLRS delete-fixup walkthrough + Benali Week 5 stamped slides</span>
            </li>
            <li>
              <strong>Block 2 · 60 min · Practice</strong>
              <span>Textbook 13.3 problems 1–6 · if stuck, rewatch cases 1–2 only</span>
            </li>
            <li>
              <strong>Block 3 · 30 min · Check</strong>
              <span>Self quiz target 75%+ · log score back here</span>
            </li>
          </ol>
          <div className="svp-resources">
            <p className="svp-card-kicker">Resources ranked for you</p>
            <ol>
              <li>3Blue1Brown — Red-black intuition (start here)</li>
              <li>Course stamped slides — Week 5 delete cases</li>
              <li>PatrickJMT — step-by-step when stuck</li>
            </ol>
          </div>
        </article>

        <article className="svp-card svp-span">
          <p className="svp-card-kicker">Weekly plan · Sep 16–22</p>
          <div className="svp-week">
            {[
              ["Mon", "Trees · delete-fixup", "2.5h"],
              ["Tue", "Trees · insert + practice", "2h"],
              ["Wed", "Trees · cumulative quiz", "2.5h"],
              ["Thu", "Hashing · maintain 78%", "2h"],
              ["Fri", "Hashing · project collisions", "1.5h"],
              ["Sat", "Heaps · light keep-sharp", "1h"],
              ["Sun", "Rest or light review", "—"],
            ].map(([day, topic, dur]) => (
              <div key={day} className="svp-day">
                <strong>{day}</strong>
                <span>{topic}</span>
                <em>{dur}</em>
              </div>
            ))}
          </div>
          <p className="svp-muted">
            Next Sunday: if Trees ≥ 75%, drop to 2 days. If 65–74%, keep 3. If
            it falls, escalate to 4–5 days and pause maintenance topics. Grades
            decide the calendar.
          </p>
        </article>
      </div>
    </section>
  );
}

function RoomsPanel() {
  return (
    <section className="svp-panel">
      <header className="svp-panel-head">
        <h2>Rooms</h2>
        <p>
          Classmates only. Encapsulated here — not pasted onto Home, Ask, or
          Study Agent.
        </p>
      </header>
      <article className="svp-card">
        <h3>r/CSC2302</h3>
        <p>
          Post a stuck thread, browse article rooms, climb the Hilbert board.
          Staff do not sit in the room; professors see chapter aggregates later.
        </p>
        <button type="button" className="svp-btn">
          Enter room
        </button>
      </article>
    </section>
  );
}
