import { useEffect, useRef, useState } from "react";
import { Link, useNavigate } from "react-router";
import { useAuth } from "../auth/AuthContext.jsx";

/**
 * Landing spot for Microsoft sign-in: the backend callback redirects here with
 * the app session token in the URL hash (never sent to any server).
 */
export default function SsoCompletePage() {
  const { adoptSession } = useAuth();
  const navigate = useNavigate();
  const [error, setError] = useState("");
  const ran = useRef(false);

  useEffect(() => {
    if (ran.current) return;
    ran.current = true;
    const params = new URLSearchParams(window.location.hash.slice(1));
    const token = params.get("token");
    const courseId = params.get("course");
    // Drop the token from the address bar immediately.
    window.history.replaceState(null, "", "/sso");
    if (!token) {
      setError("No sign-in token found. Please try signing in again.");
      return;
    }
    adoptSession(token, courseId ? Number(courseId) : undefined)
      .then(({ activeCourse }) => {
        navigate(
          activeCourse?.role === "professor"
            ? "/professor"
            : activeCourse?.role === "ta"
              ? "/ta"
              : activeCourse
                ? "/student"
                : "/courses",
          { replace: true },
        );
      })
      .catch(() => setError("Could not finish the Microsoft sign-in. Please try again."));
  }, [adoptSession, navigate]);

  return (
    <div className="aui-shell flex min-h-screen items-center justify-center px-5">
      <div className="glass-panel max-w-md p-8 text-center">
        {error ? (
          <>
            <h1 className="font-display text-2xl font-semibold text-aui-ink">Sign-in failed</h1>
            <p className="mt-3 text-sm font-medium text-aui-deep/70">{error}</p>
            <Link to="/login" className="btn-primary mt-6 inline-block px-5 py-3 text-sm">
              Back to sign in
            </Link>
          </>
        ) : (
          <>
            <h1 className="font-display text-2xl font-semibold text-aui-ink">Signing you in…</h1>
            <p className="mt-3 text-sm font-medium text-aui-deep/70">
              Finishing your campus sign-in.
            </p>
          </>
        )}
      </div>
    </div>
  );
}
