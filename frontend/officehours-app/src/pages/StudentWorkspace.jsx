import { useCallback, useEffect, useMemo, useState } from "react";
import { Link, Navigate, useLocation, useNavigate } from "react-router";
import { api } from "../api/client.js";
import { pageItems } from "../api/page.js";
import { useAuth } from "../auth/AuthContext.jsx";

const ICONS = {
  clock: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
      <circle cx="12" cy="12" r="9" />
      <path d="M12 7v5l3 3" />
    </svg>
  ),
  check: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
      <circle cx="12" cy="12" r="9" />
      <path d="M8.5 12.5l2.5 2.5 5-5.5" />
    </svg>
  ),
};

function needsReply(ask) {
  if (ask?.ta_reply) return true;
  const status = String(ask?.work_status || "").toLowerCase();
  return status === "helped" || status === "done" || status === "answered";
}

function revisionStorageKey(courseId) {
  return `officehours_revision_${courseId}`;
}

function readTodayFocus(courseId, courseCode) {
  try {
    const raw = localStorage.getItem(revisionStorageKey(courseId));
    if (raw) {
      const parsed = JSON.parse(raw);
      const grades = Array.isArray(parsed?.grades) ? parsed.grades : [];
      if (grades.length) {
        const ranked = [...grades].sort(
          (a, b) =>
            b.weight * Math.max(0, 85 - b.score) - a.weight * Math.max(0, 85 - a.score),
        );
        return ranked[0];
      }
    }
  } catch {
    // fall through to default label
  }
  const code = String(courseCode || "").toUpperCase();
  if (code.startsWith("CSC") || code.includes("DATA")) {
    return { topic: "Trees & red-black", score: null, weight: null };
  }
  return { topic: "Revision plan", score: null, weight: null };
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
      // list is decorative; workspace still works
    }
  }, [token, activeCourse]);

  useEffect(() => {
    loadAsks();
  }, [loadAsks]);

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
    return <Navigate to={`/${activeCourse.role === "professor" ? "professor" : "ta"}`} replace />;
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
      setJustSubmitted({ id: created?.id, anonymous: Boolean(created?.anonymous ?? anonymous) });
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
        // Brief pause so Quiet ask trust banner can register before tracking page.
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
    window.setTimeout(() => {
      document.getElementById("ask")?.scrollIntoView({ behavior: "smooth", block: "start" });
      document.getElementById("ask-box")?.focus();
    }, 50);
  }

  const focusLabel = todayFocus?.topic
    ? todayFocus.topic.split("&")[0].trim()
    : "Revision plan";

  return (
    <div className="fade-up">
      <h1 className="bh-page-title">Student Dashboard</h1>
      <p className="bh-page-subtitle">
        Ask staff quietly, study from professor-approved knowledge ·{" "}
        {activeCourse.code} — {activeCourse.title}
      </p>

      <div className="mb-4 flex flex-wrap items-center gap-3 rounded-xl border border-aui-forest/25 bg-[#f3faf5] px-4 py-3 text-sm">
        <span className="font-semibold text-aui-ink">Now</span>
        {replyWaiting.length > 0 ? (
          <Link
            to={`/student/asks?focus=${replyWaiting[0].id}`}
            className="rounded-full bg-rose-600 px-3 py-1 text-xs font-bold text-white"
          >
            {replyWaiting.length} reply waiting — open
          </Link>
        ) : (
          <span className="text-xs text-aui-deep/70">{openCount} open asks</span>
        )}
        <span className="text-aui-deep/30">·</span>
        <Link
          to="/student/revision"
          className="text-xs font-semibold text-aui-forest underline"
        >
          Today: {focusLabel}
          {todayFocus?.score != null ? ` (${todayFocus.score}%` : ""}
          {todayFocus?.weight != null ? ` · ${todayFocus.weight}% exam)` : todayFocus?.score != null ? ")" : ""}
        </Link>
      </div>

      <div className="bh-stats">
        <article className="bh-stat-card">
          <div className="bh-stat-head">My asks {ICONS.clock}</div>
          <p className="bh-stat-value">{myAsks.length}</p>
          <p className="bh-stat-note">Your asks in {activeCourse.code} — not the class queue</p>
        </article>
        <article className="bh-stat-card">
          <div className="bh-stat-head">My Quiet asks {ICONS.check}</div>
          <p className="bh-stat-value">{quietCount}</p>
          <p className="bh-stat-note">Name hidden — you still track status</p>
        </article>
        <article className="bh-stat-card">
          <div className="bh-stat-head">Needs reply</div>
          <p className="bh-stat-value">{replyWaiting.length}</p>
          <p className="bh-stat-note">
            <Link to="/student/asks" className="font-semibold text-aui-forest underline">
              Open My asks
            </Link>
          </p>
        </article>
        <article className="bh-stat-card">
          <div className="bh-stat-head">Today&apos;s focus</div>
          <p className="bh-stat-value text-lg leading-snug">{focusLabel}</p>
          <p className="bh-stat-note">
            {todayFocus?.score != null ? (
              <>
                Canvas {todayFocus.score}%
                {todayFocus.weight != null ? ` · ${todayFocus.weight}% exam` : ""} ·{" "}
              </>
            ) : null}
            <Link to="/student/revision" className="font-semibold text-aui-forest underline">
              Revision plan
            </Link>
          </p>
        </article>
      </div>

      <div className="grid gap-0 lg:grid-cols-2 lg:gap-5">
        <section id="ask" className="bh-card scroll-mt-6">
          <div className="bh-card-title">
            <h2>Ask for Help</h2>
          </div>
          <p className="bh-card-note">
            Choose whether staff see your name. Meeting options appear once you
            start typing.
          </p>

          {justSubmitted ? (
            <div className="mt-3 rounded-lg border border-emerald-200 bg-emerald-50 p-3 text-xs text-emerald-950">
              {justSubmitted.anonymous ? (
                <p>
                  <strong>Quiet ask trust:</strong> Staff cannot see your name or
                  student ID. Track #{justSubmitted.id} in My asks.
                </p>
              ) : (
                <p>
                  Submitted as you · track #{justSubmitted.id} in My asks.
                </p>
              )}
            </div>
          ) : null}

          <form onSubmit={submitQuestion} className="mt-4">
            <div className="rounded-xl border border-aui-forest/25 bg-[#f3faf5] p-3 sm:p-4">
              <p className="text-sm font-semibold text-aui-ink">
                Who should staff see?
              </p>
              <div className="mt-3 grid gap-2 sm:grid-cols-2">
                <label
                  className={`flex cursor-pointer items-start gap-3 rounded-xl border px-3 py-3 transition ${
                    anonymous
                      ? "border-aui-forest bg-white shadow-sm"
                      : "border-[#d7e0d9] bg-white/70"
                  }`}
                >
                  <input
                    type="radio"
                    name="identity"
                    className="mt-1 h-4 w-4 accent-aui-forest"
                    checked={anonymous}
                    onChange={() => setAnonymous(true)}
                  />
                  <span>
                    <span className="block text-sm font-semibold text-aui-ink">
                      Quiet ask
                    </span>
                    <span className="mt-0.5 block text-xs font-medium text-aui-deep/70">
                      Anonymous — no name or student ID stored.
                    </span>
                  </span>
                </label>
                <label
                  className={`flex cursor-pointer items-start gap-3 rounded-xl border px-3 py-3 transition ${
                    !anonymous
                      ? "border-aui-forest bg-white shadow-sm"
                      : "border-[#d7e0d9] bg-white/70"
                  }`}
                >
                  <input
                    type="radio"
                    name="identity"
                    className="mt-1 h-4 w-4 accent-aui-forest"
                    checked={!anonymous}
                    onChange={() => setAnonymous(false)}
                  />
                  <span>
                    <span className="block text-sm font-semibold text-aui-ink">
                      Identify me
                    </span>
                    <span className="mt-0.5 block text-xs font-medium text-aui-deep/70">
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

            <textarea
              id="ask-box"
              className="field-glass mt-3 min-h-28 px-4 py-3 text-sm"
              placeholder="Describe what you're stuck on…"
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
                  <legend className="text-xs font-semibold uppercase tracking-wide text-aui-deep/60">
                    How do you want help?
                  </legend>
                  {[
                    {
                      value: "message",
                      title: "Message / async",
                      note: "Answer in the queue — no live meeting.",
                    },
                    {
                      value: "face_to_face",
                      title: "Face-to-face meeting",
                      note: "In-person office-hours on campus.",
                    },
                    {
                      value: "online_meeting",
                      title: "Online meeting",
                      note: "Zoom / Teams with a TA or professor.",
                    },
                  ].map((option) => (
                    <label
                      key={option.value}
                      className="clay-blob flex w-full cursor-pointer items-start gap-3 px-4 py-3"
                    >
                      <input
                        type="radio"
                        name="help_mode"
                        className="mt-1 h-4 w-4 accent-aui-forest"
                        checked={helpMode === option.value}
                        onChange={() => setHelpMode(option.value)}
                      />
                      <span>
                        <span className="block text-sm font-semibold text-aui-ink">
                          {option.title}
                        </span>
                        <span className="mt-0.5 block text-xs font-medium text-aui-deep/70">
                          {option.note}
                        </span>
                      </span>
                    </label>
                  ))}
                </fieldset>
                <textarea
                  className="field-glass mt-3 min-h-20 px-4 py-3 font-mono text-xs"
                  placeholder="Optional code snippet"
                  value={codeSnippet}
                  onChange={(event) => setCodeSnippet(event.target.value)}
                />
              </>
            ) : (
              <p className="mt-2 text-xs text-aui-deep/55">
                Start typing to choose message / face-to-face / online.
              </p>
            )}

            {error ? <p className="mt-3 text-sm text-red-700">{error}</p> : null}
            <button
              type="submit"
              disabled={busy || !text.trim()}
              className="btn-primary mt-4 px-5 py-2.5 text-sm disabled:opacity-50"
            >
              {busy
                ? "Running Ask Triage…"
                : anonymous
                  ? "Submit anonymously"
                  : "Submit as me"}
            </button>
          </form>

          {result ? (
            <div className="soft-stat mt-5 text-sm">
              <p className="font-semibold text-aui-ink">
                {result.anonymous ? "Submitted quietly" : "Submitted as you"} ·
                request <span className="bh-pill bh-pill-green">#{result.id}</span>
              </p>
              <p className="mt-1 text-xs text-aui-deep/75">
                Help mode:{" "}
                {result.help_mode === "face_to_face"
                  ? "face-to-face meeting"
                  : result.help_mode === "online_meeting"
                    ? "online meeting"
                    : "message / async"}
              </p>
              {result.sensitive ? (
                <p className="mt-2 rounded-lg bg-amber-50 p-2.5 text-xs text-amber-900">
                  This looks private — it will be routed for confidential follow-up.
                  Peer matching is disabled for sensitive asks.
                </p>
              ) : null}
              {result.solidarity_message ? (
                <p className="mt-2 rounded-lg bg-sky-50 p-2.5 text-xs text-sky-950">
                  {result.solidarity_message}
                </p>
              ) : null}
              {result.oracle ? (
                <div className="mt-3 rounded-lg border border-aui-forest/20 bg-white p-2.5">
                  <p className="text-xs font-semibold text-aui-ink">Ask Triage</p>
                  <p className="mt-0.5 text-[11px] text-aui-deep/60">
                    Analyzer → Matcher → Synthesizer (local models, this course)
                  </p>
                  <ul className="mt-2 space-y-1.5 text-xs text-aui-deep/85">
                    <li>
                      <strong>Analyzer:</strong> {result.oracle.analyzer.category} ·{" "}
                      {result.oracle.analyzer.difficulty}
                    </li>
                    <li>
                      <strong>Matcher:</strong> {result.oracle.matcher.assigned_ta}
                      {result.oracle.matcher.alternative_ta
                        ? ` (backup: ${result.oracle.matcher.alternative_ta})`
                        : ""}{" "}
                      · wait ~{result.oracle.matcher.estimated_wait_minutes} min
                    </li>
                    <li>
                      <strong>Synthesizer hint:</strong>{" "}
                      {result.oracle.synthesizer.student_hint}
                    </li>
                  </ul>
                </div>
              ) : null}
              {buddyStatus?.eligible && !buddyStatus.opted_in ? (
                <div className="mt-3 rounded-lg border border-emerald-200 bg-emerald-50 p-3 text-xs text-emerald-950">
                  <p>{buddyStatus.study_buddy_message}</p>
                  <button
                    type="button"
                    disabled={buddyBusy}
                    className="btn-primary mt-2 px-3 py-1.5 text-xs"
                    onClick={optInStudyBuddy}
                  >
                    {buddyBusy ? "Saving…" : "Opt in to study-buddy group"}
                  </button>
                </div>
              ) : null}
              {buddyStatus?.opted_in ? (
                <p className="mt-3 rounded-lg bg-emerald-50 p-2.5 text-xs text-emerald-950">
                  {buddyStatus.study_buddy_message}
                </p>
              ) : null}
            </div>
          ) : null}

          <div className="mt-5 rounded-xl border border-[#e3e8e4] bg-[#fafcfa] p-3">
            <div className="flex items-center justify-between gap-2">
              <p className="text-sm font-semibold text-aui-ink">My asks</p>
              <Link
                to="/student/asks"
                className="text-xs font-semibold text-aui-forest underline"
              >
                Full status →
              </Link>
            </div>
            {myAsks.length ? (
              <ul className="mt-3 space-y-2">
                {myAsks
                  .slice()
                  .reverse()
                  .slice(0, 3)
                  .map((ask) => (
                    <li key={ask.id}>
                      <Link
                        to={`/student/asks?focus=${ask.id}`}
                        className="block w-full rounded-lg border border-[#d7e0d9] bg-white px-3 py-2 text-left text-xs hover:border-aui-forest"
                      >
                        <span className="font-semibold text-aui-ink">#{ask.id}</span>
                        {" · "}
                        {ask.anonymous ? "Quiet ask" : "Identify me"}
                        {" · "}
                        {ask.work_status || "open"}
                        {needsReply(ask) ? (
                          <span className="ml-1 rounded-full bg-rose-600 px-1.5 py-0.5 text-[10px] font-bold text-white">
                            reply
                          </span>
                        ) : null}
                        <span className="mt-1 block truncate text-aui-deep/80">
                          {ask.text}
                        </span>
                      </Link>
                    </li>
                  ))}
              </ul>
            ) : (
              <p className="mt-2 text-xs text-aui-deep/60">No asks from this login yet.</p>
            )}
            <details className="mt-3">
              <summary className="cursor-pointer text-xs font-medium text-aui-deep/65">
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
                <div className="mt-3 rounded-lg bg-white p-3 text-xs text-aui-deep">
                  <p className="font-semibold text-aui-ink">
                    #{statusResult.request_code} · {statusResult.headline}
                  </p>
                  <p className="mt-1">{statusResult.message}</p>
                  {statusResult.ta_reply ? (
                    <p className="mt-2">
                      <strong>TA reply:</strong> {statusResult.ta_reply}
                    </p>
                  ) : null}
                </div>
              ) : null}
            </details>
          </div>
        </section>

        <section id="agent" className="bh-card scroll-mt-6">
          <div className="bh-card-title">
            <h2>Course Study Agent</h2>
          </div>
          <p className="bh-card-note">
            Answers only from professor-approved FAQs and Canvas course materials
            for {activeCourse.code}. If nothing matches, turn it into a Quiet ask.
          </p>
          <form onSubmit={askAgent} className="mt-4">
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
          {agentA ? (
            <p className="soft-stat mt-4 whitespace-pre-wrap text-sm">{agentA}</p>
          ) : null}
          {agentSources.length ? (
            <ul className="mt-3 space-y-1 text-xs text-aui-deep/80">
              {agentSources.map((title) => (
                <li key={title}>Quoted from: {title}</li>
              ))}
            </ul>
          ) : null}
          {agentSeekHelp ? (
            <div className="mt-4 rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-950">
              <p className="font-semibold">No approved answer yet — seek help.</p>
              <p className="mt-1 text-xs leading-5">
                Don&apos;t keep spinning on the agent. Turn this into a Quiet ask.
              </p>
              <button
                type="button"
                className="btn-primary mt-3 px-4 py-2 text-xs"
                onClick={turnIntoQuietAsk}
              >
                Turn this into a Quiet ask
              </button>
            </div>
          ) : null}
          <p className="soft-stat mt-4 text-sm text-aui-deep/70">
            Rooms and Classmate Notes stay in the sidebar — not under this
            dashboard.
          </p>
        </section>
      </div>
    </div>
  );
}
