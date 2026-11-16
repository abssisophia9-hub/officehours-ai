import { useCallback, useEffect, useMemo, useState } from "react";
import { Link, Navigate, useSearchParams } from "react-router";
import { api } from "../api/client.js";
import { pageItems } from "../api/page.js";
import { useAuth } from "../auth/AuthContext.jsx";
import { askHasReply, markReplySeen } from "../student/replySeen.js";

function workStatusLabel(workStatus) {
  const work = String(workStatus || "open").toLowerCase();
  if (work === "claimed") return "Claimed";
  if (work === "in_progress") return "In progress";
  if (work === "helped" || work === "done" || work === "answered") return "Resolved";
  return "Waiting";
}

function workStageLabels(workStatus, statusPayload) {
  const work = String(workStatus || statusPayload?.work_status || "open").toLowerCase();
  const claimed = Boolean(statusPayload?.claimed_by || work === "claimed" || work === "in_progress" || work === "helped");
  const inProgress = work === "in_progress" || work === "helped" || Boolean(statusPayload?.ta_reply);
  const answered = Boolean(
    String(statusPayload?.ta_reply || "").trim() ||
      statusPayload?.status === "ta_replied",
  );

  const who =
    statusPayload?.claimed_by ||
    statusPayload?.assigned_ta ||
    null;
  const professor = statusPayload?.assignee_role === "professor";
  const assignedLine = statusPayload?.assigned_ta
    ? `Assigned to ${statusPayload.assigned_ta}${professor ? " (professor)" : ""}`
    : null;

  return [
    {
      label: "Queued",
      done: true,
      detail: assignedLine
        ? statusPayload?.estimated_wait_minutes != null
          ? `${assignedLine} · wait ~${statusPayload.estimated_wait_minutes} min`
          : assignedLine
        : statusPayload?.headline === "Waiting in queue"
          ? "Waiting for a free TA"
          : "Ask Triage routed your ask",
    },
    {
      label: "Claimed",
      done: claimed,
      detail: claimed
        ? who
          ? `${who} took your ask`
          : "A TA claimed your ask"
        : "-",
    },
    {
      label: "In progress",
      done: inProgress,
      detail: inProgress
        ? statusPayload?.headline || "Help in progress"
        : "-",
    },
    {
      label: "Answered",
      done: answered,
      detail: answered
        ? "Reply posted"
        : work === "helped"
          ? "Closed - check below for any note"
          : "-",
    },
  ];
}

export default function StudentAsksPage() {
  const { token, user, activeCourse } = useAuth();
  const [searchParams, setSearchParams] = useSearchParams();
  const focusParam = searchParams.get("focus");

  const [asks, setAsks] = useState([]);
  const [activeId, setActiveId] = useState(null);
  const [status, setStatus] = useState(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [listBusy, setListBusy] = useState(true);

  const loadAsks = useCallback(async () => {
    if (!activeCourse) return;
    setListBusy(true);
    try {
      const requests = await api(
        `/requests/?course_id=${activeCourse.id}&limit=50`,
        { token },
      );
      const inCourse = pageItems(requests)
        .filter((item) => !item.course || item.course === activeCourse.code)
        .slice()
        .reverse();
      setAsks(inCourse);
      setError("");
    } catch (err) {
      setError(err.message);
    } finally {
      setListBusy(false);
    }
  }, [token, activeCourse]);

  useEffect(() => {
    loadAsks();
  }, [loadAsks]);

  useEffect(() => {
    if (!asks.length) {
      setActiveId(null);
      return;
    }
    if (focusParam && asks.some((ask) => String(ask.id) === String(focusParam))) {
      setActiveId(Number(focusParam) || focusParam);
      return;
    }
    setActiveId((prev) => {
      if (prev && asks.some((ask) => ask.id === prev)) return prev;
      return asks[0].id;
    });
  }, [asks, focusParam]);

  useEffect(() => {
    if (!activeId) {
      setStatus(null);
      return;
    }
    let cancelled = false;
    setBusy(true);
    api(`/requests/${activeId}/status`, { token })
      .then((payload) => {
        if (!cancelled) {
          setStatus(payload);
          setError("");
        }
      })
      .catch((err) => {
        if (!cancelled) {
          setStatus(null);
          setError(err.message);
        }
      })
      .finally(() => {
        if (!cancelled) setBusy(false);
      });
    return () => {
      cancelled = true;
    };
  }, [activeId, token]);

  const selected = useMemo(
    () => asks.find((ask) => ask.id === activeId) || null,
    [asks, activeId],
  );

  const stages = useMemo(
    () => workStageLabels(selected?.work_status, status),
    [selected, status],
  );

  useEffect(() => {
    if (!user?.id || !selected || !askHasReply(selected)) return;
    markReplySeen(user.id, selected.id);
  }, [user?.id, selected]);

  if (!activeCourse) return <Navigate to="/" replace />;
  if (activeCourse.role !== "student") {
    return (
      <Navigate
        to={`/${activeCourse.role === "professor" ? "professor" : "ta"}`}
        replace
      />
    );
  }

  function selectAsk(id) {
    setActiveId(id);
    setSearchParams({ focus: String(id) });
  }

  const courseLine = [activeCourse.code, activeCourse.title].filter(Boolean).join(" · ");

  return (
    <div className="fade-up">
      <h1 className="sa-course">{courseLine}</h1>
      <h2 className="bh-page-title">My asks</h2>
      <p className="bh-page-subtitle">
        Status and replies live here - no receipt-code hunting.
      </p>

      {error ? <p className="mb-3 text-sm text-red-700">{error}</p> : null}

      <div className="grid gap-5 lg:grid-cols-[minmax(240px,0.9fr)_minmax(0,1.2fr)]">
        <section className="bh-card">
          <div className="bh-card-title">
            <h2>This course</h2>
          </div>
          {listBusy ? (
            <p className="mt-3 text-xs text-aui-deep/60">Loading your asks…</p>
          ) : asks.length === 0 ? (
            <div className="mt-4 rounded-xl border border-dashed border-[#c5d0c8] bg-[#fafcfa] px-4 py-8 text-center">
              <p className="text-sm font-semibold text-aui-ink">No asks yet</p>
              <p className="mt-1 text-xs text-aui-deep/70">
                Ask for help - Quiet or identified.
              </p>
              <Link to="/student/ask" className="btn-primary mt-4 inline-flex px-5 py-2.5 text-sm">
                Ask for help
              </Link>
            </div>
          ) : (
            <ul className="mt-3 space-y-2">
              {asks.map((ask) => {
                const hasReply = askHasReply(ask);
                return (
                  <li key={ask.id}>
                    <button
                      type="button"
                      className={`w-full rounded-lg border px-3 py-2 text-left text-xs ${
                        activeId === ask.id
                          ? "border-aui-forest bg-[#f3faf5]"
                          : "border-[#d7e0d9] bg-white hover:border-aui-forest"
                      }`}
                      onClick={() => selectAsk(ask.id)}
                    >
                      <span className="font-semibold text-aui-ink">#{ask.id}</span>
                      {" · "}
                      {ask.anonymous ? "Quiet ask" : "Identify me"}
                      {" · "}
                      {workStatusLabel(ask.work_status)}
                      {hasReply ? (
                        <span className="ml-1 rounded-full bg-rose-600 px-1.5 py-0.5 text-[10px] font-bold text-white">
                          reply
                        </span>
                      ) : null}
                      <span className="mt-1 block truncate text-aui-deep/80">
                        {ask.text}
                      </span>
                    </button>
                  </li>
                );
              })}
            </ul>
          )}
        </section>

        <section className="bh-card">
          {selected ? (
            <>
              <div className="bh-card-title">
                <h2>#{selected.id}</h2>
              </div>
              <p className="bh-card-note">{selected.text}</p>
              {selected.anonymous || status?.anonymous_submission ? (
                <p className="mt-2 rounded-lg bg-[#f3faf5] px-3 py-2 text-xs text-aui-deep/80">
                  Quiet ask: staff do not see your name. You still own this thread.
                </p>
              ) : null}

              {busy && !status ? (
                <p className="mt-4 text-xs text-aui-deep/60">Loading status…</p>
              ) : null}

              {status ? (
                <div className="mt-3 rounded-lg border border-aui-forest/20 bg-white px-3 py-2 text-xs">
                  <p className="font-semibold text-aui-ink">{status.headline}</p>
                  <p className="mt-1 text-aui-deep/80">{status.message}</p>
                  {status.assigned_ta ? (
                    <p className="mt-1 font-semibold text-aui-ink">
                      Assigned to: {status.assigned_ta}
                      {status.assignee_role === "professor" ? " (professor)" : ""}
                    </p>
                  ) : null}
                </div>
              ) : null}

              <ol className="mt-4 space-y-2">
                {stages.map((stage) => (
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

              {status?.meeting_title ||
              status?.meeting_when ||
              status?.meeting_place ? (
                <div className="mt-4 rounded-lg border border-emerald-200 bg-emerald-50 p-3 text-xs text-emerald-950">
                  <p className="font-semibold">Meeting</p>
                  {status.meeting_title ? (
                    <p className="mt-1">{status.meeting_title}</p>
                  ) : null}
                  {status.meeting_when ? (
                    <p className="mt-1">
                      <strong>When:</strong> {status.meeting_when}
                    </p>
                  ) : null}
                  {status.meeting_place ? (
                    <p className="mt-1">
                      <strong>Where:</strong> {status.meeting_place}
                    </p>
                  ) : null}
                </div>
              ) : null}

              {status?.ta_reply || selected.ta_reply ? (
                <div className="soft-stat mt-4 text-sm">
                  <p className="font-semibold text-aui-ink">TA reply</p>
                  <p className="mt-1 whitespace-pre-wrap">
                    {status?.ta_reply || selected.ta_reply}
                  </p>
                </div>
              ) : status?.student_hint || selected.student_hint ? (
                <div className="soft-stat mt-4 text-sm">
                  <p className="font-semibold text-aui-ink">Note from staff</p>
                  <p className="mt-1 whitespace-pre-wrap">
                    {status?.student_hint || selected.student_hint}
                  </p>
                </div>
              ) : String(selected.work_status || "").toLowerCase() === "helped" ? (
                <p className="mt-4 text-xs text-aui-deep/60">
                  This ask was closed without a written reply.
                </p>
              ) : (
                <p className="mt-4 text-xs text-aui-deep/60">
                  No reply yet - when a TA writes one, it appears here.
                </p>
              )}

              {status?.recommended_next_step ? (
                <p className="mt-3 text-xs text-aui-deep/75">
                  <strong>Next:</strong> {status.recommended_next_step}
                </p>
              ) : null}
            </>
          ) : (
            <div className="py-8 text-center text-sm text-aui-deep/60">
              Select an ask to see status.
            </div>
          )}
        </section>
      </div>
    </div>
  );
}
