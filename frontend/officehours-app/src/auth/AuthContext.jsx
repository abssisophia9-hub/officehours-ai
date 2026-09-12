import { createContext, useContext, useEffect, useMemo, useState } from "react";
import { api } from "../api/client.js";

const AuthContext = createContext(null);
const TOKEN_KEY = "officehours_auth_token";
const COURSE_KEY = "officehours_active_course";

export function AuthProvider({ children }) {
  const [token, setToken] = useState(() => localStorage.getItem(TOKEN_KEY) || "");
  const [user, setUser] = useState(null);
  const [activeCourse, setActiveCourseState] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;
    async function boot() {
      if (!token) {
        setLoading(false);
        return;
      }
      try {
        const me = await api("/auth/me", { token });
        if (cancelled) return;
        setUser(me);
        const saved = localStorage.getItem(COURSE_KEY);
        const restored =
          me.courses.find((course) => String(course.id) === saved) ||
          me.courses[0] ||
          null;
        setActiveCourseState(restored);
      } catch {
        localStorage.removeItem(TOKEN_KEY);
        setToken("");
        setUser(null);
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    boot();
    return () => {
      cancelled = true;
    };
  }, [token]);

  async function login(email, password) {
    setError("");
    const result = await api("/auth/login", {
      method: "POST",
      body: { email, password },
    });
    // Clear previous role/course — land on My Courses so demos can pick
    // Student / TA / Professor seats intentionally (do not auto-enter a course).
    localStorage.removeItem(COURSE_KEY);
    setActiveCourseState(null);
    localStorage.setItem(TOKEN_KEY, result.token);
    setToken(result.token);
    setUser(result.user);
    return result.user;
  }

  async function logout() {
    try {
      if (token) await api("/auth/logout", { method: "POST", token });
    } catch {
      // ignore network logout failures
    }
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(COURSE_KEY);
    setToken("");
    setUser(null);
    setActiveCourseState(null);
  }

  function setActiveCourse(course) {
    setActiveCourseState(course);
    if (course) localStorage.setItem(COURSE_KEY, String(course.id));
  }

  // Adopt a session minted by a Canvas launch (no password login).
  async function adoptSession(newToken, activeCourseId) {
    localStorage.setItem(TOKEN_KEY, newToken);
    if (activeCourseId) {
      localStorage.setItem(COURSE_KEY, String(activeCourseId));
    } else {
      localStorage.removeItem(COURSE_KEY);
    }
    const me = await api("/auth/me", { token: newToken });
    setToken(newToken);
    setUser(me);
    const active =
      me.courses.find((course) => course.id === activeCourseId) ||
      me.courses[0] ||
      null;
    setActiveCourseState(active);
    if (active) localStorage.setItem(COURSE_KEY, String(active.id));
    return { user: me, activeCourse: active };
  }

  const value = useMemo(
    () => ({
      token,
      user,
      activeCourse,
      loading,
      error,
      setError,
      login,
      logout,
      setActiveCourse,
      adoptSession,
    }),
    [token, user, activeCourse, loading, error],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside AuthProvider");
  return ctx;
}
