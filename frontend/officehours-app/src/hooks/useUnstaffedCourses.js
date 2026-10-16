import { useEffect, useState } from "react";
import { api } from "../api/client.js";

/** Course ids whose routing destination is neither a TA nor a professor. */
export function useUnstaffedCourses(courses, token) {
  const [ids, setIds] = useState(() => new Set());
  const signature = (courses || []).map((course) => course.id).join(",");

  useEffect(() => {
    if (!token || !courses?.length) {
      setIds(new Set());
      return undefined;
    }
    let cancelled = false;
    Promise.all(
      courses.map((course) =>
        api(`/requests/routing?course_id=${course.id}`, { token })
          .then((data) => (data?.destination === "none" ? course.id : null))
          .catch(() => null),
      ),
    ).then((flags) => {
      if (!cancelled) setIds(new Set(flags.filter((id) => id != null)));
    });
    return () => {
      cancelled = true;
    };
  }, [token, signature]);

  return ids;
}
