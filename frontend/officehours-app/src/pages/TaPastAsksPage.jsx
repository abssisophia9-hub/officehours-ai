import { useCallback, useEffect, useMemo, useState } from "react";
import { Navigate } from "react-router";
import { api } from "../api/client.js";
import { pageItems } from "../api/page.js";
import { useAuth } from "../auth/AuthContext.jsx";

function dayKey(iso) {
  if (!iso) return "";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "";
  return d.toISOString().slice(0, 10);
}

function fmtWhen(iso) {
  if (!iso) return "—";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "—";
  return d.toLocaleString();
}

function timeTaken(askedIso, answeredIso) {
  if (!askedIso || !answeredIso) return "—";
  const a = new Date(askedIso).getTime();
  const b = new Date(answeredIso).getTime();
  if (Number.isNaN(a) || Number.isNaN(b) || b < a) return "—";
  const mins = Math.round((b - a) / 60000);
  if (mins < 1) return "<1 min";
  if (mins < 60) return `${mins} min`;
  const h = Math.floor(mins / 60);
  const m = mins % 60;
  return m ? `${h}h ${m}m` : `${h}h`;
}

export default function TaPastAsksPage() {
  const { token, user, activeCourse } = useAuth();
  const [rows, setRows] = useState([]);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(true);
  const [courseFilter, setCourseFilter] = useState("active");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");

  const taCourses = useMemo(
    () => (user?.courses || []).filter((c) => c.role === "ta" || c.role === "professor"),
    [user],
  );

  const load = useCallback(async () => {
    if (!token || !activeCourse) return;
    setBusy(true);
    setError("");
    try {
      const courseId =
        courseFilter === "active"
          ? activeCourse.id
          : courseFilter === "all"
            ? null
            : Number(courseFilter);
      const params = new URLSearchParams({
        assignment: "all",
        include_helped: "true",
        limit: "100",
        offset: "0",
      });
      if (courseId) params.set("course_id", String(courseId));
      const data = await api(`/ta/queue/?${params.toString()}`, { token });
      const items = pageItems(data)
        .map((item) => item.request || item)
        .filter((req) => String(req.work_status || "") === "helped");
      setRows(items);
    } catch (err) {
      setError(err.message || "Could not load past asks.");
      setRows([]);
    } finally {
      setBusy(false);
    }
  }, [token, activeCourse, courseFilter]);

  useEffect(() => {
    load();
  }, [load]);

  if (!activeCourse) return <Navigate to="/" replace />;
  if (activeCourse.role !== "ta" && activeCourse.role !== "professor") {
    return <Navigate to="/student" replace />;
  }

  const filtered = rows.filter((req) => {
    const asked = dayKey(req.created_at);
    if (dateFrom && asked && asked < dateFrom) return false;
    if (dateTo && asked && asked > dateTo) return false;
    return true;
  });

  return (
    <div className="fade-up ta-past">
      <h1 className="bh-page-title">Past asks</h1>
      <p className="bh-page-subtitle">
        Resolved asks you can review — question, reply, course, and timing only.
      </p>

      <div className="bh-card ta-past-filters mb-4 flex flex-wrap items-end gap-3">
        <label className="ta-past-label">
          Course
          <select
            className="field-glass mt-1 block min-w-[12rem] px-3 py-2 text-sm"
            value={courseFilter}
            onChange={(event) => setCourseFilter(event.target.value)}
          >
            <option value="active">Current · {activeCourse.code}</option>
            <option value="all">All my staff courses</option>
            {taCourses.map((course) => (
              <option key={course.id} value={String(course.id)}>
                {course.code}
              </option>
            ))}
          </select>
        </label>
        <label className="ta-past-label">
          From
          <input
            type="date"
            className="field-glass mt-1 block px-3 py-2 text-sm"
            value={dateFrom}
            onChange={(event) => setDateFrom(event.target.value)}
          />
        </label>
        <label className="ta-past-label">
          To
          <input
            type="date"
            className="field-glass mt-1 block px-3 py-2 text-sm"
            value={dateTo}
            onChange={(event) => setDateTo(event.target.value)}
          />
        </label>
        <button type="button" className="btn-ghost px-3 py-2 text-sm" onClick={load} disabled={busy}>
          Refresh
        </button>
      </div>

      {error ? <p className="mb-3 text-sm text-red-700">{error}</p> : null}

      {busy ? (
        <p className="text-sm text-aui-deep/70">Loading…</p>
      ) : filtered.length === 0 ? (
        <p className="bh-card-note">No resolved asks in this course/date range.</p>
      ) : (
        <ul className="ta-past-list space-y-3">
          {filtered.map((req) => {
            const answeredAt = req.ta_replied_at || req.helped_at;
            return (
              <li key={req.id} className="bh-card ta-past-card text-sm">
                <p className="ta-past-title">
                  #{req.id} · {req.course || "Course"}
                </p>
                <p className="ta-past-question mt-2 whitespace-pre-wrap">{req.text}</p>
                <div className="ta-past-reply mt-3 rounded-lg p-3">
                  <p className="ta-past-reply-label">TA response</p>
                  <p className="ta-past-reply-body mt-1 whitespace-pre-wrap">
                    {req.ta_reply?.trim() || "— (no written reply on file)"}
                  </p>
                </div>
                <dl className="ta-past-meta mt-3 grid gap-1 sm:grid-cols-2">
                  <div>
                    <dt>Course</dt>
                    <dd>{req.course || "—"}</dd>
                  </div>
                  <div>
                    <dt>Time asked</dt>
                    <dd>{fmtWhen(req.created_at)}</dd>
                  </div>
                  <div>
                    <dt>Time answered</dt>
                    <dd>{fmtWhen(answeredAt)}</dd>
                  </div>
                  <div>
                    <dt>Time taken</dt>
                    <dd>{timeTaken(req.created_at, answeredAt)}</dd>
                  </div>
                </dl>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
