import { useMemo, useState } from "react";
import { Link } from "react-router";

/** Advanced UX prototype — feedback only. Live student workspace unchanged. */

const NAV = [
  { id: "dashboard", label: "Dashboard", icon: "dashboard" },
  { id: "asks", label: "My asks", icon: "ask" },
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

const SEED_ASKS = [
  {
    id: "1842",
    title: "Red-black delete — why black-height breaks after transplant?",
    mode: "Quiet ask",
    status: "answered",
    unread: true,
    stages: [
      { label: "Queued", done: true, detail: "Ask Triage → Alice Chen" },
      { label: "Claimed", done: true, detail: "Alice took your ask" },
      { label: "In progress", done: true, detail: "Help Coach draft · 8 min" },
      { label: "Answered", done: true, detail: "Reply posted · 12 min ago" },
    ],
    reply:
      "After transplant, if the deleted node was black, black-height drops by one. Fix with rotations + recolor from the replacement upward — same cases as CLRS delete-fixup.",
  },
  {
    id: "1831",
    title: "Hashing: chain vs open addressing for the project?",
    mode: "Identify me",
    status: "claimed",
    unread: false,
    meeting: "Thu 16:30 · Building 7 · Room 204",
    stages: [
      { label: "Queued", done: true, detail: "In TA desk" },
      { label: "Claimed", done: true, detail: "Sam Ortiz · face-to-face" },
      { label: "In progress", done: false, detail: "Waiting on meeting" },
      { label: "Answered", done: false, detail: "—" },
    ],
    reply: null,
  },
  {
    id: "1820",
    title: "Do we need amortized analysis on the midterm?",
    mode: "Quiet ask",
    status: "queued",
    unread: false,
    stages: [
      { label: "Queued", done: true, detail: "Waiting for a free TA" },
      { label: "Claimed", done: false, detail: "—" },
      { label: "In progress", done: false, detail: "—" },
      { label: "Answered", done: false, detail: "—" },
    ],
    reply: null,
  },
];

const SEED_GRADES = [
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
  const [asks, setAsks] = useState(SEED_ASKS);
  const [activeAsk, setActiveAsk] = useState(SEED_ASKS[0].id);
  const [anonymous, setAnonymous] = useState(true);
  const [helpMode, setHelpMode] = useState("message");
  const [askText, setAskText] = useState("");
  const [askCode, setAskCode] = useState("");
  const [showHelpModes, setShowHelpModes] = useState(false);
  const [justSubmitted, setJustSubmitted] = useState(null);
  const [agentQ, setAgentQ] = useState("");
  const [agentState, setAgentState] = useState("idle");
  const [grades, setGrades] = useState(SEED_GRADES);
  const [editingGrade, setEditingGrade] = useState(null);
  const [gradeDraft, setGradeDraft] = useState("");
  const [todayScore, setTodayScore] = useState("75");
  const [loggedScore, setLoggedScore] = useState(null);
  const [toast, setToast] = useState("");

  const ranked = useMemo(() => [...grades].sort((a, b) => gap(b) - gap(a)), [grades]);
  const focus = ranked[0];
  const ask = asks.find((item) => item.id === activeAsk) || asks[0];
  const unreadReplies = asks.filter((item) => item.unread && item.status === "answered").length;
  const openCount = asks.filter((item) => item.status !== "answered").length;
  const quietCount = asks.filter((item) => item.mode === "Quiet ask").length;

  function flash(message) {
    setToast(message);
    window.setTimeout(() => setToast(""), 3000);
  }

  function openAsk(id) {
    setSection("asks");
    if (id) {
      setActiveAsk(id);
      setAsks((prev) => prev.map((item) => (item.id === id ? { ...item, unread: false } : item)));
    }
  }

  function submitAsk() {
    if (!askText.trim()) return;
    const id = String(1900 + asks.length);
    const created = {
      id,
      title: askText.trim().slice(0, 90),
      mode: anonymous ? "Quiet ask" : "Identify me",
      status: "queued",
      unread: false,
      optimistic: true,
      stages: [
        { label: "Queued", done: true, detail: "Just now · Ask Triage routing" },
        { label: "Claimed", done: false, detail: "—" },
        { label: "In progress", done: false, detail: "—" },
        { label: "Answered", done: false, detail: "—" },
      ],
      reply: null,
    };
    setAsks((prev) => [created, ...prev]);
    setJustSubmitted({ id, anonymous });
    setAskText("");
    setAskCode("");
    setShowHelpModes(false);
    flash(anonymous ? "Submitted quietly · tracking opened" : "Submitted · tracking opened");
    openAsk(id);
  }

  function runAgent(event) {
    event.preventDefault();
    const q = agentQ.trim().toLowerCase();
    if (!q) return;
    if (q.includes("exam") || q.includes("when is") || q.includes("grade")) {
      setAgentState("miss");
    } else {
      setAgentState("hit");
    }
  }

  function turnAgentIntoAsk() {
    setAskText(agentQ.trim() || "I need help with something the Study Agent could not answer.");
    setAnonymous(true);
    setShowHelpModes(true);
    setSection("dashboard");
    setAgentState("idle");
    flash("Prefilling Quiet ask from Study Agent");
    window.setTimeout(() => document.getElementById("proto-ask-box")?.focus(), 80);
  }

  function saveGrade(topic) {
    const n = Number(gradeDraft);
    if (Number.isNaN(n) || n < 0 || n > 100) return;
    setGrades((prev) =>
      prev.map((row) =>
        row.topic === topic
          ? { ...row, score: n, source: `${row.source.split(" · ")[0]} · adjusted by you` }
          : row,
      ),
    );
    setEditingGrade(null);
    flash("Grade updated · plan will recalculate");
  }

  function logToday() {
    const n = Number(todayScore);
    if (Number.isNaN(n) || n < 0 || n > 100) return;
    setLoggedScore(n);
    setGrades((prev) =>
      prev.map((row) =>
        row.topic === focus.topic ? { ...row, score: n, source: "You · today's check-in" } : row,
      ),
    );
    flash(
      n >= 75
        ? "Logged 75%+ · next week Trees can drop to 2 days"
        : n >= 65
          ? "Logged · keep 3 Trees days next week"
          : "Logged · next week will escalate Trees",
    );
  }

  return (
    <div className="bh-frame">
      <aside className="bh-sidebar">
        <div className="bh-logo">
          OfficeHours AI
          <small>Al Akhawayn University</small>
        </div>
        <p className="mx-3 mb-2 rounded-lg bg-amber-50 px-2 py-1.5 text-[10px] font-semibold uppercase tracking-wide text-amber-900">
          Advanced UX prototype · not merged
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
                {item.id === "asks" && unreadReplies > 0 ? (
                  <span className="rounded-full bg-rose-600 px-1.5 py-0.5 text-[10px] font-bold text-white">
                    {unreadReplies}
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
            Same dashboard + advanced UX: next-action strip, optimistic asks, Quiet
            ask trust, agent→ask handoff, grade override, today-first revision.
          </span>
          <Link to="/demo" className="font-semibold underline">
            Back to demos
          </Link>
        </div>

        {toast ? (
          <div className="mb-3 rounded-xl border border-aui-forest/30 bg-[#eef8f1] px-4 py-2.5 text-sm font-medium text-aui-ink">
            {toast}
          </div>
        ) : null}

        {section === "dashboard" ? (
          <div className="fade-up">
            <h1 className="bh-page-title">Student Dashboard</h1>
            <p className="bh-page-subtitle">
              Ask staff quietly, study from professor-approved knowledge · CSC 2302
              — Data Structures
            </p>

            <div className="mb-4 flex flex-wrap items-center gap-3 rounded-xl border border-aui-forest/25 bg-[#f3faf5] px-4 py-3 text-sm">
              <span className="font-semibold text-aui-ink">Now</span>
              {unreadReplies > 0 ? (
                <button
                  type="button"
                  className="rounded-full bg-rose-600 px-3 py-1 text-xs font-bold text-white"
                  onClick={() => openAsk("1842")}
                >
                  {unreadReplies} reply waiting — open
                </button>
              ) : (
                <span className="text-xs text-aui-deep/70">{openCount} open asks</span>
              )}
              <span className="text-aui-deep/30">·</span>
              <button
                type="button"
                className="text-xs font-semibold text-aui-forest underline"
                onClick={() => setSection("revision")}
              >
                Today: {focus.topic} ({focus.score}% · {focus.weight}% exam)
              </button>
            </div>

            <div className="bh-stats">
              <article className="bh-stat-card">
                <div className="bh-stat-head">My asks {ICONS.clock}</div>
                <p className="bh-stat-value">{asks.length}</p>
                <p className="bh-stat-note">Your asks in CSC 2302 — not the class queue</p>
              </article>
              <article className="bh-stat-card">
                <div className="bh-stat-head">My Quiet asks {ICONS.check}</div>
                <p className="bh-stat-value">{quietCount}</p>
                <p className="bh-stat-note">Name hidden — you still track status</p>
              </article>
              <article className="bh-stat-card">
                <div className="bh-stat-head">Needs reply</div>
                <p className="bh-stat-value">{unreadReplies}</p>
                <p className="bh-stat-note">
                  <button type="button" className="font-semibold text-aui-forest underline" onClick={() => openAsk()}>
                    Open My asks
                  </button>
                </p>
              </article>
              <article className="bh-stat-card">
                <div className="bh-stat-head">Today&apos;s focus</div>
                <p className="bh-stat-value text-lg leading-snug">
                  {focus.topic.split("&")[0].trim()}
                </p>
                <p className="bh-stat-note">
                  Canvas {focus.score}% · {focus.weight}% exam ·{" "}
                  <button type="button" className="font-semibold text-aui-forest underline" onClick={() => setSection("revision")}>
                    Revision plan
                  </button>
                </p>
              </article>
            </div>

            <div className="grid gap-0 lg:grid-cols-2 lg:gap-5">
              <section className="bh-card">
                <div className="bh-card-title">
                  <h2>Ask for Help</h2>
                </div>
                <p className="bh-card-note">
                  Choose whether staff see your name. Meeting options appear once
                  you start typing.
                </p>

                {justSubmitted ? (
                  <div className="mt-3 rounded-lg border border-emerald-200 bg-emerald-50 p-3 text-xs text-emerald-950">
                    {justSubmitted.anonymous ? (
                      <p>
                        <strong>Quiet ask trust:</strong> Staff cannot see your name
                        or student ID. Track #{justSubmitted.id} in My asks.
                      </p>
                    ) : (
                      <p>Submitted as you · track #{justSubmitted.id} in My asks.</p>
                    )}
                  </div>
                ) : null}

                <div className="mt-4 rounded-xl border border-aui-forest/25 bg-[#f3faf5] p-3 sm:p-4">
                  <p className="text-sm font-semibold text-aui-ink">Who should staff see?</p>
                  <div className="mt-3 grid gap-2 sm:grid-cols-2">
                    {[
                      { value: true, title: "Quiet ask", note: "Anonymous — no name or student ID stored." },
                      { value: false, title: "Identify me", note: "Share Sara El Idrissi · ID 117400." },
                    ].map((opt) => (
                      <label
                        key={String(opt.value)}
                        className={`flex cursor-pointer items-start gap-3 rounded-xl border px-3 py-3 ${
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
                          <span className="mt-0.5 block text-xs text-aui-deep/70">{opt.note}</span>
                        </span>
                      </label>
                    ))}
                  </div>
                </div>

                <textarea
                  id="proto-ask-box"
                  className="field-glass mt-3 min-h-28 px-4 py-3 text-sm"
                  placeholder="Describe what you're stuck on…"
                  value={askText}
                  onChange={(event) => {
                    setAskText(event.target.value);
                    if (event.target.value.trim()) setShowHelpModes(true);
                  }}
                />

                {showHelpModes ? (
                  <>
                    <fieldset className="mt-3 space-y-2">
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
                            <span className="mt-0.5 block text-xs text-aui-deep/70">{option.note}</span>
                          </span>
                        </label>
                      ))}
                    </fieldset>
                    <textarea
                      className="field-glass mt-3 min-h-20 px-4 py-3 font-mono text-xs"
                      placeholder="Optional code snippet"
                      value={askCode}
                      onChange={(event) => setAskCode(event.target.value)}
                    />
                  </>
                ) : (
                  <p className="mt-2 text-xs text-aui-deep/55">
                    Start typing to choose message / face-to-face / online.
                  </p>
                )}

                <button
                  type="button"
                  className="btn-primary mt-4 px-5 py-2.5 text-sm disabled:opacity-50"
                  disabled={!askText.trim()}
                  onClick={submitAsk}
                >
                  {anonymous ? "Submit anonymously" : "Submit as me"}
                </button>

                <div className="mt-5 rounded-xl border border-[#e3e8e4] bg-[#fafcfa] p-3">
                  <div className="flex items-center justify-between gap-2">
                    <p className="text-sm font-semibold text-aui-ink">My asks</p>
                    <button type="button" className="text-xs font-semibold text-aui-forest underline" onClick={() => openAsk()}>
                      Full status →
                    </button>
                  </div>
                  <ul className="mt-3 space-y-2">
                    {asks.slice(0, 2).map((item) => (
                      <li key={item.id}>
                        <button
                          type="button"
                          className="w-full rounded-lg border border-[#d7e0d9] bg-white px-3 py-2 text-left text-xs hover:border-aui-forest"
                          onClick={() => openAsk(item.id)}
                        >
                          <span className="font-semibold text-aui-ink">#{item.id}</span>
                          {" · "}
                          {item.mode}
                          {" · "}
                          {item.status}
                          {item.unread ? (
                            <span className="ml-1 rounded-full bg-rose-600 px-1.5 py-0.5 text-[10px] font-bold text-white">
                              new reply
                            </span>
                          ) : null}
                          {item.optimistic ? (
                            <span className="ml-1 text-[10px] font-semibold text-aui-forest">just now</span>
                          ) : null}
                          <span className="mt-1 block truncate text-aui-deep/80">{item.title}</span>
                        </button>
                      </li>
                    ))}
                  </ul>
                </div>
              </section>

              <section className="bh-card">
                <div className="bh-card-title">
                  <h2>Course Study Agent</h2>
                </div>
                <p className="bh-card-note">
                  Quick ask from stamped materials. Full refuse → Quiet ask handoff
                  is in the Study Agent sidebar section.
                </p>
                <input
                  className="field-glass mt-4 px-4 py-3 text-sm"
                  placeholder="Ask from approved answers / slides…"
                  value={agentQ}
                  onChange={(event) => setAgentQ(event.target.value)}
                />
                <div className="mt-3 flex flex-wrap gap-2">
                  <button
                    type="button"
                    className="btn-ghost px-4 py-2 text-sm"
                    onClick={() => {
                      setSection("agent");
                      if (agentQ.trim()) setAgentState("idle");
                    }}
                  >
                    Open Study Agent →
                  </button>
                </div>
                <p className="soft-stat mt-4 text-sm text-aui-deep/70">
                  Rooms and Classmate Notes stay in the sidebar — not under this
                  dashboard.
                </p>
              </section>
            </div>
          </div>
        ) : null}

        {section === "asks" ? (
          <div className="fade-up">
            <h1 className="bh-page-title">My asks</h1>
            <p className="bh-page-subtitle">
              Status and replies live here. New replies badge the sidebar — no
              receipt-code hunting.
            </p>
            <div className="grid gap-5 lg:grid-cols-[minmax(240px,0.9fr)_minmax(0,1.2fr)]">
              <section className="bh-card">
                <div className="bh-card-title">
                  <h2>This course</h2>
                </div>
                <ul className="mt-3 space-y-2">
                  {asks.map((item) => (
                    <li key={item.id}>
                      <button
                        type="button"
                        className={`w-full rounded-lg border px-3 py-2 text-left text-xs ${
                          activeAsk === item.id
                            ? "border-aui-forest bg-[#f3faf5]"
                            : "border-[#d7e0d9] bg-white hover:border-aui-forest"
                        }`}
                        onClick={() => openAsk(item.id)}
                      >
                        <span className="font-semibold text-aui-ink">#{item.id}</span>
                        {" · "}
                        {item.mode}
                        {" · "}
                        {item.status}
                        {item.unread ? (
                          <span className="ml-1 rounded-full bg-rose-600 px-1.5 py-0.5 text-[10px] font-bold text-white">
                            new
                          </span>
                        ) : null}
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
                {ask.mode === "Quiet ask" ? (
                  <p className="mt-2 rounded-lg bg-[#f3faf5] px-3 py-2 text-xs text-aui-deep/80">
                    Quiet ask: staff do not see your name. You still own this thread.
                  </p>
                ) : null}
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
                  <p className="mt-4 text-xs text-aui-deep/60">
                    No reply yet — status above is the source of truth.
                  </p>
                )}
              </section>
            </div>
          </div>
        ) : null}

        {section === "agent" ? (
          <div className="fade-up">
            <h1 className="bh-page-title">Study Agent</h1>
            <p className="bh-page-subtitle">
              Stamped materials only. If it refuses, one tap turns the question into
              a Quiet ask.
            </p>
            <section className="bh-card max-w-3xl">
              <div className="bh-card-title">
                <h2>Course Study Agent</h2>
              </div>
              <p className="bh-card-note">
                Try a course topic for a hit. Try “When is the exam?” for refuse →
                Quiet ask.
              </p>
              <form onSubmit={runAgent} className="mt-4">
                <input
                  className="field-glass px-4 py-3 text-sm"
                  placeholder="Ask from approved answers / slides…"
                  value={agentQ}
                  onChange={(event) => setAgentQ(event.target.value)}
                />
                <button type="submit" className="btn-ghost mt-3 px-4 py-2 text-sm">
                  Ask agent
                </button>
              </form>
              {agentState === "hit" ? (
                <div className="soft-stat mt-4 text-sm">
                  <p className="text-xs font-semibold text-aui-forest">From stamped FAQ · Benali</p>
                  <p className="mt-1">
                    Use open addressing when load factor stays moderate. Prefer
                    chaining when deletions are frequent. Source: Week 6 stamped notes.
                  </p>
                </div>
              ) : null}
              {agentState === "miss" ? (
                <div className="mt-4 rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-950">
                  <p className="font-semibold">No approved answer yet — seek help.</p>
                  <p className="mt-1 text-xs leading-5">
                    Don&apos;t keep spinning on the agent. Turn this into a Quiet ask.
                  </p>
                  <button type="button" className="btn-primary mt-3 px-4 py-2 text-xs" onClick={turnAgentIntoAsk}>
                    Turn this into a Quiet ask
                  </button>
                </div>
              ) : null}
            </section>
          </div>
        ) : null}

        {section === "revision" ? (
          <div className="fade-up">
            <h1 className="bh-page-title">Revision Strategist</h1>
            <p className="bh-page-subtitle">
              Canvas grades + syllabus weights → clear priority. Firm, not harsh —
              and you can correct a wrong grade.
            </p>
            <div className="grid gap-5 lg:grid-cols-2">
              <section className="bh-card">
                <div className="bh-card-title">
                  <h2>From Canvas + syllabus</h2>
                </div>
                <p className="bh-card-note">Each row shows its source. Fix if Canvas is wrong.</p>
                <ul className="mt-4 space-y-2">
                  {ranked.map((row) => (
                    <li key={row.topic} className="rounded-lg border border-[#d7e0d9] bg-white px-3 py-2 text-sm">
                      <div className="flex items-start justify-between gap-3">
                        <div>
                          <p className="font-semibold text-aui-ink">{row.topic}</p>
                          <p className="text-xs text-aui-deep/70">
                            {row.source} · {row.weight}% of exam
                          </p>
                        </div>
                        <span className={`text-lg font-bold ${row.score < 70 ? "text-amber-800" : "text-aui-forest"}`}>
                          {row.score}%
                        </span>
                      </div>
                      {editingGrade === row.topic ? (
                        <div className="mt-2 flex flex-wrap items-center gap-2">
                          <input
                            className="field-glass w-24 px-2 py-1 text-xs"
                            type="number"
                            min="0"
                            max="100"
                            value={gradeDraft}
                            onChange={(event) => setGradeDraft(event.target.value)}
                          />
                          <button type="button" className="btn-primary px-3 py-1 text-xs" onClick={() => saveGrade(row.topic)}>
                            Save
                          </button>
                          <button type="button" className="text-xs underline" onClick={() => setEditingGrade(null)}>
                            Cancel
                          </button>
                        </div>
                      ) : (
                        <button
                          type="button"
                          className="mt-1 text-[11px] font-semibold text-aui-forest underline"
                          onClick={() => {
                            setEditingGrade(row.topic);
                            setGradeDraft(String(row.score));
                          }}
                        >
                          Fix this grade
                        </button>
                      )}
                    </li>
                  ))}
                </ul>
                <p className="soft-stat mt-4 text-sm">
                  Priority: <strong>{focus.topic}</strong> — lowest score among high
                  exam weight.
                </p>
              </section>

              <section className="bh-card">
                <div className="bh-card-title">
                  <h2>Today&apos;s plan</h2>
                </div>
                <p className="bh-card-note">
                  Why: {focus.source} shows {focus.score}%, and it is {focus.weight}%
                  of the final. 18 days left — close the biggest gap first.
                </p>
                <p className="mt-3 text-sm font-semibold text-aui-ink">2 h 15 min · finish by 22:30</p>
                <ol className="mt-3 space-y-2 text-sm">
                  <li className="rounded-lg border border-[#d7e0d9] bg-white px-3 py-2">
                    <strong>Block 1 · 45 min · Start here</strong>
                    <span className="mt-0.5 block text-xs text-aui-deep/70">CLRS delete-fixup + Week 5 stamped slides</span>
                  </li>
                  <li className="rounded-lg border border-[#d7e0d9] bg-white px-3 py-2">
                    <strong>Block 2 · 60 min · Practice</strong>
                    <span className="mt-0.5 block text-xs text-aui-deep/70">Textbook 13.3 problems 1–6</span>
                  </li>
                  <li className="rounded-lg border border-[#d7e0d9] bg-white px-3 py-2">
                    <strong>Block 3 · 30 min · Check</strong>
                    <span className="mt-0.5 block text-xs text-aui-deep/70">Self quiz · target 75%+</span>
                  </li>
                </ol>
                <div className="mt-4 rounded-lg border border-aui-forest/20 bg-[#f3faf5] p-3 text-xs">
                  <p className="font-semibold text-aui-ink">Resources (3 max)</p>
                  <ol className="mt-2 list-decimal space-y-1 pl-4 text-aui-deep/85">
                    <li><strong>Start here:</strong> 3Blue1Brown — red-black intuition</li>
                    <li><strong>Course:</strong> Stamped slides — Week 5</li>
                    <li><strong>If stuck:</strong> PatrickJMT — step-by-step</li>
                  </ol>
                </div>
                <div className="mt-4 rounded-lg border border-[#d7e0d9] bg-white p-3">
                  <p className="text-sm font-semibold text-aui-ink">Log today&apos;s check-in</p>
                  <p className="mt-1 text-xs text-aui-deep/70">After Block 3, log your score — next week recalculates.</p>
                  <div className="mt-2 flex flex-wrap items-center gap-2">
                    <input
                      className="field-glass w-24 px-2 py-1.5 text-sm"
                      type="number"
                      min="0"
                      max="100"
                      value={todayScore}
                      onChange={(event) => setTodayScore(event.target.value)}
                    />
                    <button type="button" className="btn-primary px-3 py-1.5 text-xs" onClick={logToday}>
                      Log score
                    </button>
                  </div>
                  {loggedScore != null ? (
                    <p className="mt-2 text-xs font-medium text-aui-forest">
                      Saved {loggedScore}% for {focus.topic}.
                    </p>
                  ) : null}
                </div>
              </section>
            </div>

            <section className="bh-card mt-5">
              <div className="bh-card-title">
                <h2>This week</h2>
              </div>
              <p className="bh-card-note">Secondary to Today — glance only.</p>
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
            </section>
          </div>
        ) : null}

        {section === "rooms" ? (
          <div className="fade-up">
            <h1 className="bh-page-title">Rooms</h1>
            <p className="bh-page-subtitle">Classmates only — not on the Dashboard.</p>
            <section className="bh-card max-w-3xl">
              <div className="bh-card-title">
                <h2>r/CSC2302</h2>
              </div>
              <div className="mt-4 rounded-xl border border-dashed border-[#c5d0c8] bg-[#fafcfa] px-4 py-8 text-center">
                <p className="text-sm font-semibold text-aui-ink">No stuck threads yet</p>
                <p className="mt-1 text-xs text-aui-deep/70">
                  Be the first — classmates often unblock what a stamped FAQ cannot.
                </p>
                <button type="button" className="btn-primary mt-4 px-5 py-2.5 text-sm">
                  Start a stuck thread
                </button>
              </div>
            </section>
          </div>
        ) : null}

        {section === "notes" ? (
          <div className="fade-up">
            <h1 className="bh-page-title">Classmate Notes</h1>
            <p className="bh-page-subtitle">Share and browse here — removed from Dashboard.</p>
            <section className="bh-card max-w-3xl">
              <div className="bh-card-title">
                <h2>Share with classmates</h2>
              </div>
              <div className="mt-4 rounded-xl border border-dashed border-[#c5d0c8] bg-[#fafcfa] px-4 py-8 text-center">
                <p className="text-sm font-semibold text-aui-ink">No classmate notes yet</p>
                <p className="mt-1 text-xs text-aui-deep/70">PDF, DOCX, or images · optional hide my name.</p>
                <button type="button" className="btn-primary mt-4 px-5 py-2.5 text-sm">
                  Share the first note
                </button>
              </div>
            </section>
          </div>
        ) : null}

        <div className="mt-6 rounded-xl border border-dashed border-[#c5d0c8] bg-white/70 px-4 py-3 text-xs text-aui-deep/70 lg:hidden">
          On phone: Dashboard · Asks · Agent · More as bottom tabs — same encapsulation.
        </div>
      </main>
    </div>
  );
}
