import { useCallback, useEffect, useMemo, useState } from "react";
import { Link, Navigate, useLocation, useNavigate } from "react-router";
import { api } from "../api/client.js";
import { pageItems } from "../api/page.js";
import { useAuth } from "../auth/AuthContext.jsx";
import { loadStrategistPlan } from "../student/strategistStorage.js";

function needsReply(ask) {
  if (ask?.ta_reply) return true;
  const status = String(ask?.work_status || "").toLowerCase();
  return status === "helped" || status === "done" || status === "answered";
}

const ONBOARD_STORAGE_KEY = "officehours_student_onboarded";

const ASK_GUIDE =
  "Write one concrete question below. Quiet ask hides your name; Ask Triage matches you to staff.";

function readOnboarded() {
  try {
    return localStorage.getItem(ONBOARD_STORAGE_KEY) === "1";
  } catch {
    return false;
  }
}

function writeOnboarded() {
  try {
    localStorage.setItem(ONBOARD_STORAGE_KEY, "1");
  } catch {
    // ignore
  }
}

function readTodayFocus(courseId, courseCode) {
  const plan = loadStrategistPlan(courseId);
  if (plan?.focus?.topic) {
    return {
      topic: plan.focus.topic,
      score: plan.focus.score,
      weight: plan.focus.weight,
      source: plan.focus.source,
      today: Array.isArray(plan.today) ? plan.today : [],
      summary: plan.today_summary || "",
    };
  }
  const code = String(courseCode || "").toUpperCase();
  if (code.startsWith("CSC") || code.includes("DATA")) {
    return { topic: "Trees & red-black", score: 62, weight: 35, today: [] };
  }
  return { topic: "Core concepts", score: null, weight: null, today: [] };
}

export default function StudentWorkspace() {
  const { token, user, activeCourse } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [text, setText] = useState("");
  const [codeSnippet, setCodeSnippet] = useState("");
  const [anonymous, setAnonymous] = useState(true);
  const [helpMode, setHelpMode] = useState("message");
  const [showHelpModes, setShowHelpModes] = useState(false);
  const [result, setResult] = useState(null);
  const [justSubmitted, setJustSubmitted] = useState(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [agentQ, setAgentQ] = useState("");
  const [agentA, setAgentA] = useState("");
  const [agentSeekHelp, setAgentSeekHelp] = useState(false);
  const [agentSources, setAgentSources] = useState([]);
  const [myAsks, setMyAsks] = useState([]);
  const [buddyStatus, setBuddyStatus] = useState(null);
  const [buddyBusy, setBuddyBusy] = useState(false);
  const [statusCode, setStatusCode] = useState("");
  const [statusResult, setStatusResult] = useState(null);
  const [statusBusy, setStatusBusy] = useState(false);
  const [todayFocus, setTodayFocus] = useState({ topic: "Revision plan" });
  const [roomCount, setRoomCount] = useState(null);
  const [showOnboard, setShowOnboard] = useState(() => !readOnboarded());
  const [showAskGuide, setShowAskGuide] = useState(false);

  const loadAsks = useCallback(async () => {
    if (!activeCourse) return;
    try {
      const requests = await api(
        `/requests/?course_id=${activeCourse.id}&limit=50`,
        { token },
      );
      const inCourse = pageItems(requests).filter(
        (item) => !item.course || item.course === activeCourse.code,
      );
      setMyAsks(inCourse);
    } catch {
      // list is decorative
    }
  }, [token, activeCourse]);

  const loadRooms = useCallback(async () => {
    if (!activeCourse) return;
    try {
      const posts = await api(`/help-room/?course_id=${activeCourse.id}&limit=20`, {
        token,
      });
      setRoomCount(pageItems(posts).length);
    } catch {
      setRoomCount(null);
    }
  }, [token, activeCourse]);

  useEffect(() => {
    loadAsks();
    loadRooms();
  }, [loadAsks, loadRooms]);

  useEffect(() => {
    if (!activeCourse) return;
    setTodayFocus(readTodayFocus(activeCourse.id, activeCourse.code));
  }, [activeCourse]);

  useEffect(() => {
    if (location.hash === "#agent" || location.hash === "#ask") {
      const id = location.hash.slice(1);
      window.setTimeout(() => {
        document.getElementById(id)?.scrollIntoView({ behavior: "smooth", block: "start" });
      }, 80);
    }
  }, [location.hash]);

  const replyWaiting = useMemo(
    () => myAsks.filter((ask) => needsReply(ask)),
    [myAsks],
  );
  const quietCount = useMemo(
    () => myAsks.filter((ask) => ask.anonymous).length,
    [myAsks],
  );
  const openCount = useMemo(
    () =>
      myAsks.filter((ask) => {
        const status = String(ask.work_status || "open").toLowerCase();
        return status !== "helped" && status !== "done" && status !== "answered";
      }).length,
    [myAsks],
  );

  if (!activeCourse) return <Navigate to="/" replace />;
  if (activeCourse.role !== "student") {
    return (
      <Navigate
        to={`/${activeCourse.role === "professor" ? "professor" : "ta"}`}
        replace
      />
    );
  }

  async function submitQuestion(event) {
    event.preventDefault();
    if (!text.trim()) return;
    setBusy(true);
    setError("");
    try {
      if (!anonymous && !user.student_id && !user.display_name) {
        setError("Identified asks need your name or student ID on the account.");
        setBusy(false);
        return;
      }
      const created = await api("/requests/", {
        method: "POST",
        token,
        body: {
          text,
          anonymous,
          student_id: anonymous ? null : user.student_id,
          student_name: anonymous ? null : user.display_name,
          course: activeCourse.code,
          course_id: activeCourse.id,
          code_snippet: codeSnippet || null,
          help_mode: helpMode,
        },
      });
      setResult(created);
      setJustSubmitted({
        id: created?.id,
        anonymous: Boolean(created?.anonymous ?? anonymous),
      });
      setBuddyStatus(null);
      setStatusCode(created?.id ? String(created.id) : "");
      setStatusResult(null);
      setText("");
      setCodeSnippet("");
      setShowHelpModes(false);
      await loadAsks();
      if (created?.id) {
        try {
          const status = await api(`/requests/${created.id}/study-buddy`, { token });
          setBuddyStatus(status);
        } catch {
          setBuddyStatus(null);
        }
        window.setTimeout(() => {
          navigate(`/student/asks?focus=${created.id}`);
        }, 700);
        return;
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  async function checkRequestStatus(event) {
    event.preventDefault();
    const code = statusCode.trim();
    if (!code) {
      setError("Enter your request code to check status.");
      return;
    }
    setStatusBusy(true);
    setError("");
    try {
      const status = await api(`/requests/${code}/status`, { token });
      setStatusResult(status);
    } catch (err) {
      setStatusResult(null);
      setError(err.message);
    } finally {
      setStatusBusy(false);
    }
  }

  async function optInStudyBuddy() {
    if (!result?.id) return;
    setBuddyBusy(true);
    try {
      const status = await api(`/requests/${result.id}/study-buddy`, {
        method: "POST",
        token,
        body: { request_id: result.id },
      });
      setBuddyStatus(status);
    } catch (err) {
      setError(err.message);
    } finally {
      setBuddyBusy(false);
    }
  }

  async function askAgent(event) {
    event.preventDefault();
    setAgentA("");
    setAgentSeekHelp(false);
    setAgentSources([]);
    try {
      const answer = await api("/agent/ask", {
        method: "POST",
        token,
        body: { question: agentQ, course_id: activeCourse.id },
      });
      const hint = answer.student_hint ? `\n\n${answer.student_hint}` : "";
      setAgentA(`${answer.answer || ""}${hint}`);
      setAgentSeekHelp(Boolean(answer.should_seek_help || answer.matched_count === 0));
      setAgentSources(
        (answer.sources || [])
          .map((hit) => (hit.entry?.question_text || "").trim())
          .filter(Boolean),
      );
    } catch (err) {
      setAgentA(err.message);
      setAgentSeekHelp(true);
    }
  }

  function turnIntoQuietAsk() {
    setAnonymous(true);
    if (agentQ.trim()) setText(agentQ);
    setShowHelpModes(true);
    setShowAskGuide(true);
    window.setTimeout(() => {
      document.getElementById("ask")?.scrollIntoView({ behavior: "smooth", block: "start" });
      document.getElementById("ask-box")?.focus();
    }, 50);
  }

  function dismissOnboard() {
    writeOnboarded();
    setShowOnboard(false);
  }

  function focusAsk() {
    dismissOnboard();
    setShowAskGuide(true);
    window.setTimeout(() => {
      document.getElementById("ask")?.scrollIntoView({ behavior: "smooth", block: "start" });
      document.getElementById("ask-box")?.focus();
    }, 60);
  }

  function focusAgent() {
    dismissOnboard();
    window.setTimeout(() => {
      document.getElementById("agent")?.scrollIntoView({ behavior: "smooth", block: "start" });
      document.querySelector("#agent input")?.focus();
    }, 60);
  }

  const focusLabel = todayFocus?.topic
    ? todayFocus.topic.split("&")[0].trim()
    : "Revision plan";
  const openCopy =
    openCount === 0
      ? "Queue is clear — a good moment to ask"
      : openCount === 1
        ? "1 ask still waiting on staff"
        : `${openCount} asks still waiting on staff`;

  return (
    <div className="sd fade-up">
      <header className="sd-hero">
        <p className="sd-kicker">
          AUI · {activeCourse.code} · {activeCourse.title}
        </p>
        <h1 className="sd-title">What do you need help with?</h1>
        <p className="sd-lead">
          <strong>Ask for help</strong> is the main action — Quiet asks hide your
          name and match you to a TA. Everything else is optional.
        </p>

        {showOnboard ? (
          <div className="sd-onboard" role="status">
            <div>
              <strong>New here? Start with Ask for help</strong>
              <p>
                Write your question in the form below. Study Agent and Revision
                Strategist stay in the sidebar when you need them later.
              </p>
            </div>
            <div className="sd-onboard-actions">
              <button type="button" className="sd-onboard-go" onClick={focusAsk}>
                Jump to Ask for help
              </button>
              <button
                type="button"
                className="sd-onboard-dismiss"
                onClick={dismissOnboard}
              >
                Dismiss
              </button>
            </div>
          </div>
        ) : null}

        <p className="sd-alt-tools">
          Not stuck right now?{" "}
          <button type="button" onClick={focusAgent}>
            Study Agent
          </button>{" "}
          answers from stamped FAQs &amp; slides ·{" "}
          <Link to="/student/revision">Revision Strategist</Link> searches
          YouTube and articles from how you ask and learn.
        </p>

        <div className="sd-pulse">
          {replyWaiting.length > 0 ? (
            <Link
              className="sd-chip sd-chip-hot"
              to={`/student/asks?focus=${replyWaiting[0].id}`}
            >
              {replyWaiting.length} reply waiting — open now
            </Link>
          ) : (
            <button type="button" className="sd-chip" onClick={focusAsk}>
              {openCopy}
            </button>
          )}
          <Link className="sd-chip sd-pulse-secondary" to="/student/revision">
            Today: {focusLabel}
            {todayFocus?.score != null ? ` · ${todayFocus.score}%` : ""}
          </Link>
          <Link className="sd-chip sd-pulse-secondary" to="/student/room">
            Rooms
            {roomCount != null ? ` · ${roomCount} open` : ""}
          </Link>
          <Link className="sd-chip sd-pulse-secondary" to="/student/notes">
            Classmate notes
          </Link>
        </div>
      </header>

      <div className="sd-layout">
        <section id="ask" className="sd-ask scroll-mt-6">
          <div className="sd-ask-head">
            <div>
              <h2>Ask for help</h2>
              <p className="sd-ask-copy">
                Use when you&apos;re stuck and need a TA or professor. Quiet asks
                hide your name; you still own the thread in My asks.
              </p>
            </div>
            <span className="sd-badge">Primary</span>
          </div>

          {showAskGuide ? (
            <p className="sd-ask-guide">
              <strong>Quick start:</strong> {ASK_GUIDE}
            </p>
          ) : null}

          {justSubmitted ? (
            <div className="mt-4 ml-2 rounded-xl border border-aui-forest/25 bg-[var(--theme-emerald-bg)] p-3 text-sm text-[var(--theme-emerald-fg)]">
              {justSubmitted.anonymous ? (
                <p>
                  <strong>Quiet ask trust:</strong> Staff cannot see your name.
                  Track #{justSubmitted.id} in My asks.
                </p>
              ) : (
                <p>
                  Submitted as you · track #{justSubmitted.id} in My asks.
                </p>
              )}
            </div>
          ) : null}

          <div className="sd-identity">
            <p className="sd-identity-label">Who should staff see?</p>
            <div className="sd-identity-grid">
              <label
                className={`sd-choice sd-choice-quiet ${anonymous ? "sd-choice-on" : ""}`}
              >
                <input
                  type="radio"
                  name="identity"
                  className="mt-1 h-4 w-4 accent-[var(--theme-forest)]"
                  checked={anonymous}
                  onChange={() => setAnonymous(true)}
                />
                <span>
                  <strong>Quiet ask</strong>
                  <span>Anonymous — no name or student ID stored.</span>
                  <span className="sd-choice-tag">Recommended when you hesitate</span>
                </span>
              </label>
              <label className={`sd-choice ${!anonymous ? "sd-choice-on" : ""}`}>
                <input
                  type="radio"
                  name="identity"
                  className="mt-1 h-4 w-4 accent-[var(--theme-forest)]"
                  checked={!anonymous}
                  onChange={() => setAnonymous(false)}
                />
                <span>
                  <strong>Identify me</strong>
                  <span>
                    Share <strong>{user.display_name || "your name"}</strong>
                    {user.student_id ? (
                      <>
                        {" "}
                        · ID <strong>{user.student_id}</strong>
                      </>
                    ) : null}
                    .
                  </span>
                </span>
              </label>
            </div>
          </div>

          <form onSubmit={submitQuestion} className="mt-4">
            <textarea
              id="ask-box"
              className="field-glass mt-1 w-full px-4 py-3"
              placeholder="Describe what you're stuck on — one concrete question beats a vague wall of text…"
              value={text}
              onChange={(event) => {
                setText(event.target.value);
                if (event.target.value.trim()) setShowHelpModes(true);
              }}
              required
            />

            {showHelpModes ? (
              <>
                <fieldset className="mt-3 space-y-2">
                  <legend className="sd-identity-label">How do you want help?</legend>
                  {[
                    {
                      value: "message",
                      title: "Message / async",
                      note: "Answer in the queue — no live meeting.",
                    },
                    {
                      value: "face_to_face",
                      title: "Face-to-face meeting",
                      note: "In-person office hours on campus.",
                    },
                    {
                      value: "online_meeting",
                      title: "Online meeting",
                      note: "Zoom / Teams with a TA or professor.",
                    },
                  ].map((option) => (
                    <label
                      key={option.value}
                      className={`sd-choice ${helpMode === option.value ? "sd-choice-on" : ""}`}
                    >
                      <input
                        type="radio"
                        name="help_mode"
                        className="mt-1 h-4 w-4 accent-[var(--theme-forest)]"
                        checked={helpMode === option.value}
                        onChange={() => setHelpMode(option.value)}
                      />
                      <span>
                        <strong>{option.title}</strong>
                        <span>{option.note}</span>
                      </span>
                    </label>
                  ))}
                </fieldset>
                <textarea
                  className="field-glass mt-3 min-h-20 w-full px-4 py-3 font-mono text-xs"
                  placeholder="Optional code snippet"
                  value={codeSnippet}
                  onChange={(event) => setCodeSnippet(event.target.value)}
                />
              </>
            ) : (
              <p className="sd-form-hint">
                Start typing to choose message / face-to-face / online.
              </p>
            )}

            {error ? (
              <p className="mt-3 text-sm text-[var(--theme-red-fg)]">{error}</p>
            ) : null}
            <button
              type="submit"
              disabled={busy || !text.trim()}
              className="sd-cta mt-4"
            >
              {busy
                ? "Running Ask Triage…"
                : anonymous
                  ? "Submit quietly — staff never see my name"
                  : "Submit as me"}
            </button>
          </form>

          {result ? (
            <div className="soft-stat mt-5 ml-2 text-sm">
              <p className="font-semibold text-[var(--theme-title)]">
                {result.anonymous ? "Submitted quietly" : "Submitted as you"} ·
                request <span className="bh-pill bh-pill-green">#{result.id}</span>
              </p>
              <p className="mt-1 text-xs text-[var(--theme-text-muted)]">
                Help mode:{" "}
                {result.help_mode === "face_to_face"
                  ? "face-to-face meeting"
                  : result.help_mode === "online_meeting"
                    ? "online meeting"
                    : "message / async"}
              </p>
              {result.sensitive ? (
                <p className="mt-2 rounded-lg bg-[var(--theme-amber-bg)] p-2.5 text-xs text-[var(--theme-amber-fg)]">
                  This looks private — it will be routed for confidential follow-up.
                </p>
              ) : null}
              {result.solidarity_message ? (
                <p className="mt-2 rounded-lg bg-[var(--theme-surface-soft)] p-2.5 text-xs">
                  {result.solidarity_message}
                </p>
              ) : null}
              {result.triage ? (
                <div className="mt-3 rounded-lg border border-[var(--theme-border)] bg-[var(--theme-surface)] p-2.5">
                  <p className="text-xs font-semibold text-[var(--theme-title)]">
                    Ask Triage
                  </p>
                  <ul className="mt-2 space-y-1.5 text-xs text-[var(--theme-text-muted)]">
                    <li>
                      <strong>Analyzer:</strong> {result.triage.analyzer.category} ·{" "}
                      {result.triage.analyzer.difficulty}
                    </li>
                    <li>
                      <strong>Matcher:</strong> {result.triage.matcher.assigned_ta}
                      {result.triage.matcher.alternative_ta
                        ? ` (backup: ${result.triage.matcher.alternative_ta})`
                        : ""}{" "}
                      · wait ~{result.triage.matcher.estimated_wait_minutes} min
                    </li>
                    <li>
                      <strong>Hint:</strong> {result.triage.synthesizer.student_hint}
                    </li>
                  </ul>
                </div>
              ) : null}
              {buddyStatus?.eligible && !buddyStatus.opted_in ? (
                <div className="mt-3 rounded-lg border border-[var(--theme-emerald-border)] bg-[var(--theme-emerald-bg)] p-3 text-xs text-[var(--theme-emerald-fg)]">
                  <p>{buddyStatus.study_buddy_message}</p>
                  <button
                    type="button"
                    disabled={buddyBusy}
                    className="sd-cta mt-2 px-3 py-1.5 text-xs"
                    onClick={optInStudyBuddy}
                  >
                    {buddyBusy ? "Saving…" : "Opt in to study-buddy group"}
                  </button>
                </div>
              ) : null}
              {buddyStatus?.opted_in ? (
                <p className="mt-3 rounded-lg bg-[var(--theme-emerald-bg)] p-2.5 text-xs text-[var(--theme-emerald-fg)]">
                  {buddyStatus.study_buddy_message}
                </p>
              ) : null}
            </div>
          ) : null}
        </section>

        <aside className="sd-rail">
          <section className="sd-panel sd-panel-focus">
            <p className="sd-panel-label">Today&apos;s focus</p>
            <h3>{focusLabel}</h3>
            <p>
              {todayFocus?.score != null ? (
                <>
                  Your plan prioritizes this because Canvas shows{" "}
                  <strong>{todayFocus.score}%</strong>
                  {todayFocus.weight != null
                    ? ` and it is ${todayFocus.weight}% of the exam`
                    : ""}
                  .
                </>
              ) : (
                <>Open your revision plan for a today-first study sequence.</>
              )}
            </p>
            <div className="sd-focus-blocks">
              {(todayFocus?.today?.length
                ? todayFocus.today
                : [
                    { title: "Start here", minutes: 45, action: "Open Revision Strategist" },
                    { title: "Practice", minutes: 60, action: "Worked problems" },
                    { title: "Check", minutes: 30, action: "Self-quiz · 75%+" },
                  ]
              ).map((block) => (
                <div className="sd-focus-block" key={block.title}>
                  <strong>{block.title}</strong>
                  <span>{block.minutes} min</span>
                </div>
              ))}
            </div>
            <Link className="sd-link" to="/student/revision">
              Open full Revision Strategist →
            </Link>
          </section>

          <section className="sd-panel">
            <p className="sd-panel-label">Your status in {activeCourse.code}</p>
            <div className="sd-metrics mt-3">
              <Link to="/student/asks" className="sd-metric">
                <strong>{myAsks.length}</strong>
                <span>My asks</span>
                <em>Yours only — not the class queue</em>
              </Link>
              <Link to="/student/asks" className="sd-metric">
                <strong>{quietCount}</strong>
                <span>Quiet</span>
                <em>Name hidden · still trackable</em>
              </Link>
              <Link
                to={
                  replyWaiting[0]
                    ? `/student/asks?focus=${replyWaiting[0].id}`
                    : "/student/asks"
                }
                className={`sd-metric ${replyWaiting.length ? "sd-metric-alert" : ""}`}
              >
                <strong>{replyWaiting.length}</strong>
                <span>Needs reply</span>
                <em>
                  {replyWaiting.length
                    ? "Staff answered — open it"
                    : "Nothing waiting"}
                </em>
              </Link>
            </div>
          </section>

          <section className="sd-panel">
            <div className="flex items-center justify-between gap-2">
              <p className="sd-panel-label">Recent asks</p>
              <Link className="sd-link mt-0" to="/student/asks">
                Full status →
              </Link>
            </div>
            {myAsks.length ? (
              <ul className="sd-ask-list">
                {myAsks
                  .slice()
                  .reverse()
                  .slice(0, 3)
                  .map((ask) => (
                    <li key={ask.id}>
                      <Link to={`/student/asks?focus=${ask.id}`}>
                        <span className="sd-ask-meta">
                          #{ask.id} · {ask.anonymous ? "Quiet" : "Named"} ·{" "}
                          {ask.work_status || "open"}
                          {needsReply(ask) ? " · reply ready" : ""}
                        </span>
                        <span className="sd-ask-text">{ask.text}</span>
                      </Link>
                    </li>
                  ))}
              </ul>
            ) : (
              <p className="mt-2 text-xs text-[var(--theme-text-subtle)]">
                No asks from this login yet — your first Quiet ask can start above.
              </p>
            )}
            <details className="mt-3">
              <summary className="cursor-pointer text-xs font-medium text-[var(--theme-text-subtle)]">
                Optional: look up a receipt code
              </summary>
              <form onSubmit={checkRequestStatus} className="mt-2 flex flex-wrap gap-2">
                <input
                  className="field-glass min-w-[8rem] flex-1 px-3 py-2 text-sm"
                  value={statusCode}
                  onChange={(event) => setStatusCode(event.target.value)}
                  placeholder="Request code"
                  inputMode="numeric"
                />
                <button
                  type="submit"
                  disabled={statusBusy}
                  className="btn-ghost px-4 py-2 text-sm"
                >
                  {statusBusy ? "Checking…" : "Look up"}
                </button>
              </form>
              {statusResult ? (
                <div className="mt-3 rounded-lg bg-[var(--theme-surface-muted)] p-3 text-xs">
                  <p className="font-semibold text-[var(--theme-title)]">
                    #{statusResult.request_code} · {statusResult.headline}
                  </p>
                  <p className="mt-1">{statusResult.message}</p>
                </div>
              ) : null}
            </details>
          </section>

          <section id="agent" className="sd-panel sd-panel-tool scroll-mt-6">
            <p className="sd-panel-label">Course Study Agent</p>
            <h3>Ask stamped materials</h3>
            <p>
              Secondary to Ask for help — use when you want answers from approved
              FAQs and slides for {activeCourse.code}. If nothing matches, turn it
              into a Quiet ask.
            </p>
            <form onSubmit={askAgent} className="mt-3">
              <input
                className="field-glass w-full px-4 py-3 text-sm"
                placeholder="Ask from approved answers / slides…"
                value={agentQ}
                onChange={(event) => setAgentQ(event.target.value)}
              />
              <button type="submit" className="btn-ghost mt-3 w-full px-4 py-2.5 text-sm">
                Ask agent
              </button>
            </form>
            {agentA ? (
              <p className="soft-stat mt-3 whitespace-pre-wrap text-sm">{agentA}</p>
            ) : null}
            {agentSources.length ? (
              <ul className="mt-2 space-y-1 text-xs text-[var(--theme-text-muted)]">
                {agentSources.map((title) => (
                  <li key={title}>Quoted from: {title}</li>
                ))}
              </ul>
            ) : null}
            {agentSeekHelp ? (
              <div className="mt-3 rounded-lg border border-[var(--theme-amber-border)] bg-[var(--theme-amber-bg)] p-3 text-sm text-[var(--theme-amber-fg)]">
                <p className="font-semibold">No approved answer yet — seek help.</p>
                <button
                  type="button"
                  className="sd-cta mt-3 px-4 py-2 text-xs"
                  onClick={turnIntoQuietAsk}
                >
                  Turn this into a Quiet ask
                </button>
              </div>
            ) : null}
          </section>

          <section className="sd-panel">
            <p className="sd-panel-label">Campus community</p>
            <h3>Study with classmates</h3>
            <div className="sd-community mt-3">
              <Link to="/student/room">
                Rooms
                <small>
                  {roomCount != null
                    ? `${roomCount} open thread${roomCount === 1 ? "" : "s"}`
                    : "Peer help threads"}
                </small>
              </Link>
              <Link to="/student/notes">
                Classmate notes
                <small>Shared course notes</small>
              </Link>
            </div>
          </section>
        </aside>
      </div>
    </div>
  );
}
