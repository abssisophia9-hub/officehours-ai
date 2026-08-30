import { useCallback, useEffect, useState } from "react";
import { Link, Navigate } from "react-router";
import { api } from "../api/client.js";
import { pageItems } from "../api/page.js";
import { useAuth } from "../auth/AuthContext.jsx";
import HelpRoomFeed from "../components/HelpRoomFeed.jsx";
import PeerNotesFeed from "../components/PeerNotesFeed.jsx";

const ICONS = {
  doc: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
      <path d="M14 2v6h6" />
    </svg>
  ),
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
  book: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
      <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20" />
      <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z" />
    </svg>
  ),
};

export default function StudentWorkspace() {
  const { token, user, activeCourse } = useAuth();
  const [text, setText] = useState("");
  const [codeSnippet, setCodeSnippet] = useState("");
  const [anonymous, setAnonymous] = useState(true);
  const [helpMode, setHelpMode] = useState("message");
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [agentQ, setAgentQ] = useState("");
  const [agentA, setAgentA] = useState("");
  const [agentSeekHelp, setAgentSeekHelp] = useState(false);
  const [agentSources, setAgentSources] = useState([]);
  const [myAsks, setMyAsks] = useState([]);
  const [stats, setStats] = useState({
    open: 0,
    anonymous: 0,
    approved: 0,
    hitShort: "—",
    hitLabel: "No agent asks in this course yet",
  });
  const [buddyStatus, setBuddyStatus] = useState(null);
  const [buddyBusy, setBuddyBusy] = useState(false);
  const [statusCode, setStatusCode] = useState("");
  const [statusResult, setStatusResult] = useState(null);
  const [statusBusy, setStatusBusy] = useState(false);

  const loadStats = useCallback(async () => {
    if (!activeCourse) return;
    try {
      const [requests, approved, hitRate] = await Promise.all([
        api(`/requests/?course_id=${activeCourse.id}&limit=50`, { token }),
        api(`/knowledge/?status=approved&course_id=${activeCourse.id}&limit=50`, { token }),
        api(`/analytics/kb-hit-rate?course_id=${activeCourse.id}`, { token }),
      ]);
      const inCourse = pageItems(requests).filter(
        (item) => !item.course || item.course === activeCourse.code,
      );
      const asks = hitRate?.total_asks || 0;
      const hits = hitRate?.total_hits || 0;
      setMyAsks(inCourse);
      setStats({
        open: inCourse.length,
        anonymous: inCourse.filter((item) => item.anonymous).length,
        approved: pageItems(approved).length,
        hitShort: asks ? `${hits}/${asks}` : "—",
        hitLabel: asks
          ? `${hits} of ${asks} asks this course hit a stamp`
          : "No agent asks in this course yet",
      });
    } catch {
      // stats are decorative; workspace still works without them
    }
  }, [token, activeCourse]);

  useEffect(() => {
    loadStats();
  }, [loadStats]);

  if (!activeCourse) return <Navigate to="/" replace />;
  if (activeCourse.role !== "student") {
    return <Navigate to={`/${activeCourse.role === "professor" ? "professor" : "ta"}`} replace />;
  }

  async function submitQuestion(event) {
    event.preventDefault();
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
      setBuddyStatus(null);
      setStatusCode(created?.id ? String(created.id) : "");
      setStatusResult(null);
      setText("");
      setCodeSnippet("");
      await loadStats();
      if (created?.id) {
        try {
          const status = await api(`/requests/${created.id}/study-buddy`, { token });
          setBuddyStatus(status);
        } catch {
          setBuddyStatus(null);
        }
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
      await loadStats();
    } catch (err) {
      setAgentA(err.message);
      setAgentSeekHelp(true);
    }
  }

  return (
    <div className="fade-up">
      <h1 className="bh-page-title">Student Dashboard</h1>
      <p className="bh-page-subtitle">
        Ask staff quietly, unlock an “aha” with classmates, or study from
        professor-approved knowledge · {activeCourse.code} — {activeCourse.title}
      </p>

      <div className="bh-stats">
        <article className="bh-stat-card">
          <div className="bh-stat-head">My asks {ICONS.clock}</div>
          <p className="bh-stat-value">{stats.open}</p>
          <p className="bh-stat-note">Your asks in {activeCourse.code} — not the class queue</p>
        </article>
        <article className="bh-stat-card">
          <div className="bh-stat-head">My Quiet asks {ICONS.check}</div>
          <p className="bh-stat-value">{stats.anonymous}</p>
          <p className="bh-stat-note">Name hidden from staff — you can still open status</p>
        </article>
        <article className="bh-stat-card">
          <div className="bh-stat-head">Approved Knowledge {ICONS.book}</div>
          <p className="bh-stat-value">{stats.approved}</p>
          <p className="bh-stat-note">Stamped FAQs the study agent may quote</p>
        </article>
        <article className="bh-stat-card">
          <div className="bh-stat-head">Agent hit-rate {ICONS.doc}</div>
          <p className="bh-stat-value">{stats.hitShort}</p>
          <p className="bh-stat-note">{stats.hitLabel}</p>
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
          <form onSubmit={submitQuestion} className="mt-4">
            <div className="rounded-xl border border-aui-forest/25 bg-[#f3faf5] p-3 sm:p-4">
              <p className="text-sm font-semibold text-aui-ink">
                Who should staff see?
              </p>
              <p className="mt-1 text-xs text-aui-deep/70">
                Pick one — Quiet ask hides your name; Identify me shares it.
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

            <fieldset className="mt-4 space-y-2">
              <legend className="text-xs font-semibold uppercase tracking-wide text-aui-deep/60">
                How do you want help?
              </legend>
              {[
                {
                  value: "message",
                  title: "Message / async",
                  note: "Answer in the queue or FAQ — no live meeting required.",
                },
                {
                  value: "face_to_face",
                  title: "Face-to-face meeting",
                  note: "Request an in-person office-hours slot on campus.",
                },
                {
                  value: "online_meeting",
                  title: "Online meeting",
                  note: "Request a Zoom / Teams call with a TA or professor.",
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
              className="field-glass mt-3 min-h-32 px-4 py-3 text-sm"
              placeholder="Describe what you're stuck on…"
              value={text}
              onChange={(event) => setText(event.target.value)}
              required
            />
            <textarea
              className="field-glass mt-3 min-h-20 px-4 py-3 font-mono text-xs"
              placeholder="Optional code snippet"
              value={codeSnippet}
              onChange={(event) => setCodeSnippet(event.target.value)}
            />
            {error ? <p className="mt-3 text-sm text-red-700">{error}</p> : null}
            <button type="submit" disabled={busy} className="btn-primary mt-4 px-5 py-2.5 text-sm">
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
            <p className="text-sm font-semibold text-aui-ink">My asks</p>
            <p className="mt-1 text-xs text-aui-deep/70">
              Your submissions in this course. Quiet asks stay nameless to staff.
              A request code is only for a receipt you wrote down.
            </p>
            {myAsks.length ? (
              <ul className="mt-3 space-y-2">
                {myAsks.slice().reverse().map((ask) => (
                  <li key={ask.id}>
                    <button
                      type="button"
                      className="w-full rounded-lg border border-[#d7e0d9] bg-white px-3 py-2 text-left text-xs hover:border-aui-forest"
                      onClick={() => {
                        setStatusCode(String(ask.id));
                        setStatusResult(null);
                        setError("");
                        api(`/requests/${ask.id}/status`, { token })
                          .then(setStatusResult)
                          .catch((err) => setError(err.message));
                      }}
                    >
                      <span className="font-semibold text-aui-ink">#{ask.id}</span>
                      {" · "}
                      {ask.anonymous ? "Quiet ask" : "Identify me"}
                      {" · "}
                      {ask.work_status || "open"}
                      <span className="mt-1 block truncate text-aui-deep/80">
                        {ask.text}
                      </span>
                    </button>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="mt-2 text-xs text-aui-deep/60">No asks from this login yet.</p>
            )}
            <form onSubmit={checkRequestStatus} className="mt-3 flex flex-wrap gap-2">
              <input
                className="field-glass min-w-[8rem] flex-1 px-3 py-2 text-sm"
                value={statusCode}
                onChange={(event) => setStatusCode(event.target.value)}
                placeholder="Request code (receipt)"
                inputMode="numeric"
              />
              <button
                type="submit"
                disabled={statusBusy}
                className="btn-ghost px-4 py-2 text-sm"
              >
                {statusBusy ? "Checking…" : "Look up receipt"}
              </button>
            </form>
            {statusResult ? (
              <div className="mt-3 rounded-lg bg-white p-3 text-xs text-aui-deep">
                <p className="font-semibold text-aui-ink">
                  #{statusResult.request_code} · {statusResult.headline}
                </p>
                <p className="mt-1">{statusResult.message}</p>
                {statusResult.meeting_title ||
                statusResult.meeting_when ||
                statusResult.meeting_place ? (
                  <div className="mt-2 rounded-lg border border-emerald-200 bg-emerald-50 p-2.5 text-emerald-950">
                    <p className="font-semibold">Shared group meeting</p>
                    {statusResult.meeting_title ? (
                      <p className="mt-1">{statusResult.meeting_title}</p>
                    ) : null}
                    {statusResult.meeting_when ? (
                      <p className="mt-1">
                        <strong>When:</strong> {statusResult.meeting_when}
                      </p>
                    ) : null}
                    {statusResult.meeting_place ? (
                      <p className="mt-1">
                        <strong>Where:</strong> {statusResult.meeting_place}
                      </p>
                    ) : null}
                  </div>
                ) : null}
                {statusResult.ta_reply ? (
                  <p className="mt-2">
                    <strong>TA reply:</strong> {statusResult.ta_reply}
                  </p>
                ) : null}
              </div>
            ) : null}
          </div>
        </section>

        <section id="agent" className="bh-card scroll-mt-6">
          <div className="bh-card-title">
            <h2>Course Study Agent</h2>
          </div>
          <p className="bh-card-note">
            Answers only from professor-approved FAQs and Canvas course materials
            for {activeCourse.code}. If nothing matches, stop guessing — Quiet ask
            a TA instead.
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
                Don&apos;t keep spinning on the agent. Quiet ask a TA, or post the
                stuck point in Stuck Room — a classmate often has the missing
                perspective.
              </p>
              <div className="mt-3 flex flex-wrap gap-2">
                <a
                  href="#ask"
                  className="btn-primary inline-flex px-4 py-2 text-xs"
                  onClick={() => {
                    if (agentQ.trim()) setText(agentQ);
                  }}
                >
                  Go to Quiet ask
                </a>
                <Link to="/student/room" className="btn-ghost inline-flex px-4 py-2 text-xs">
                  Open Stuck Room
                </Link>
              </div>
            </div>
          ) : null}
        </section>
      </div>

      <HelpRoomFeed courseCode={activeCourse.code} />

      <PeerNotesFeed
        token={token}
        courseId={activeCourse.id}
        courseCode={activeCourse.code}
      />
    </div>
  );
}
