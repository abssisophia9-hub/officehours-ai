import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { api } from "../../api/client.js";
import { pageItems } from "../../api/page.js";
import { useAuth } from "../../auth/AuthContext.jsx";

const ProfessorDataContext = createContext(null);

const OPEN_WORK = new Set(["open", "claimed", "in_progress"]);

export function waitingUploads(uploads) {
  return (uploads || []).filter(
    (item) => item.status === "pending" || item.status === "partly_approved",
  );
}

export function assignedToProfessor(requests) {
  return (requests || []).filter(
    (item) => item.assignee_role === "professor" && OPEN_WORK.has(item.work_status || "open"),
  );
}

export function useProfessorData() {
  const value = useContext(ProfessorDataContext);
  if (!value) {
    throw new Error("Professor pages must render inside the professor workspace.");
  }
  return value;
}

export function ProfessorProvider({ children }) {
  const { token, activeCourse } = useAuth();
  const [requests, setRequests] = useState([]);
  const [entries, setEntries] = useState([]);
  const [uploads, setUploads] = useState([]);
  const [commandCenter, setCommandCenter] = useState(null);
  const [reviewInsights, setReviewInsights] = useState(null);
  const [taLoad, setTaLoad] = useState(null);
  const [canvasInfo, setCanvasInfo] = useState(null);
  const [hitRate, setHitRate] = useState(null);
  const [goldCount, setGoldCount] = useState(0);
  const [error, setError] = useState("");
  const [ready, setReady] = useState(false);

  const load = useCallback(async () => {
    if (!token || !activeCourse || activeCourse.role !== "professor") return;
    const courseId = activeCourse.id;
    try {
      const [req, pending, approved, rejected, clusters, canvas, loadBody, insights, rate, gold, files] =
        await Promise.all([
          api(`/requests/?course_id=${courseId}&limit=50`, { token }),
          api(`/knowledge/?status=pending_review&course_id=${courseId}&limit=200`, { token }),
          api(`/knowledge/?status=approved&course_id=${courseId}&limit=200`, { token }),
          api(`/knowledge/?status=rejected&course_id=${courseId}&limit=200`, { token }),
          api(
            `/analytics/clusters?course_id=${courseId}&course=${encodeURIComponent(activeCourse.code)}`,
            { token },
          ),
          api(`/knowledge/canvas/status?course_id=${courseId}`, { token }),
          api(`/ta/load/?course_id=${courseId}`, { token }),
          api(`/analytics/review-insights?course_id=${courseId}`, { token }),
          api(`/analytics/kb-hit-rate?course_id=${courseId}`, { token }),
          api(`/analytics/gold-labels?course_id=${courseId}`, { token }),
          api(`/knowledge/uploads?course_id=${courseId}`, { token }),
        ]);
      const courseRequests = pageItems(req).filter(
        (item) => !item.course || item.course === activeCourse.code,
      );
      setRequests(courseRequests);
      setEntries(
        [...pageItems(pending), ...pageItems(approved), ...pageItems(rejected)].filter(
          (item) => !item.course_id || item.course_id === courseId,
        ),
      );
      setCommandCenter(clusters);
      setReviewInsights(insights);
      setCanvasInfo(canvas);
      setTaLoad(loadBody);
      setHitRate(rate);
      setGoldCount(Array.isArray(gold) ? gold.length : 0);
      setUploads(Array.isArray(files) ? files : []);
      setError("");
    } catch (err) {
      setError(err.message || "Could not load this course.");
    } finally {
      setReady(true);
    }
  }, [token, activeCourse]);

  useEffect(() => {
    setReady(false);
    setRequests([]);
    setEntries([]);
    setUploads([]);
    setCommandCenter(null);
    setReviewInsights(null);
    setTaLoad(null);
    setCanvasInfo(null);
    setHitRate(null);
    setGoldCount(0);
    load();
  }, [load]);

  const waitingFiles = waitingUploads(uploads).length;
  const assignedAsks = assignedToProfessor(requests).length;
  const noTa = ready && (taLoad?.tas || []).length === 0;

  const value = useMemo(
    () => ({
      requests,
      entries,
      uploads,
      commandCenter,
      reviewInsights,
      setReviewInsights,
      taLoad,
      canvasInfo,
      hitRate,
      goldCount,
      error,
      setError,
      ready,
      reload: load,
      waitingFiles,
      assignedAsks,
      noTa,
    }),
    [
      requests,
      entries,
      uploads,
      commandCenter,
      reviewInsights,
      taLoad,
      canvasInfo,
      hitRate,
      goldCount,
      error,
      ready,
      load,
      waitingFiles,
      assignedAsks,
      noTa,
    ],
  );

  return <ProfessorDataContext.Provider value={value}>{children}</ProfessorDataContext.Provider>;
}
