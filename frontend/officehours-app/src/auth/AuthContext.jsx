import { createContext, useContext, useEffect, useMemo, useState } from "react";
import { api } from "../api/client.js";
import {
  clearLegacyCourseKey,
  coursePath,
  forgetCourse,
  landingCourse,
  rememberCourse,
} from "./courseLanding.js";

const AuthContext = createContext(null);
const TOKEN_KEY = "officehours_auth_token";

export { coursePath, landingCourse };

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
        clearLegacyCourseKey();
        const restored = landingCourse(me);
        setActiveCourseState(restored);
        if (restored) rememberCourse(me.id, restored);
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
    clearLegacyCourseKey();
    setActiveCourseState(null);
    localStorage.setItem(TOKEN_KEY, result.token);
    setToken(result.token);
    setUser(result.user);
    const next = landingCourse(result.user, { preferStaff: true });
    setActiveCourseState(next);
    if (next) rememberCourse(result.user.id, next);
    return result.user;
  }

  async function logout() {
    try {
      if (token) await api("/auth/logout", { method: "POST", token });
    } catch {
      // ignore network logout failures
    }
    forgetCourse(user?.id);
    localStorage.removeItem(TOKEN_KEY);
    setToken("");
    setUser(null);
    setActiveCourseState(null);
  }

  function setActiveCourse(course) {
    setActiveCourseState(course);
    if (course && user?.id) rememberCourse(user.id, course);
  }

  // Adopt a session minted by a Canvas launch (no password login).
  async function adoptSession(newToken, activeCourseId) {
    clearLegacyCourseKey();
    localStorage.setItem(TOKEN_KEY, newToken);
    const me = await api("/auth/me", { token: newToken });
    setToken(newToken);
    setUser(me);
    const explicit = activeCourseId
      ? me.courses.find(
          (course) => String(course.id) === String(activeCourseId),
        )
      : null;
    const active = explicit || landingCourse(me, { preferStaff: true });
    setActiveCourseState(active);
    if (active) rememberCourse(me.id, active);
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
