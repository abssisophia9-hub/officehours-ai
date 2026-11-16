import { useEffect, useState } from "react";
import { Link, Navigate, useNavigate, useSearchParams } from "react-router";
import { API_BASE, api } from "../api/client.js";
import { coursePath, landingCourse, useAuth } from "../auth/AuthContext.jsx";
import ThemeToggle from "../components/ThemeToggle.jsx";

// AUI emails are Initial.Lastname@aui.ma - role comes from course membership, not email.
const DEMO_ACCOUNTS = [
  {
    email: "s.elidrissi@aui.ma",
    role: "Student",
    note: "8 courses · CSC 3390 has no TA",
  },
  {
    email: "a.chen@aui.ma",
    role: "TA (staff on 2302)",
    note: "Assigned to CSC 2302 - a course she already took",
  },
  {
    email: "a.benali@aui.ma",
    role: "Professor",
    note: "CSC 2302 · 3323 · 3374 · 3390 (no TA)",
  },
];

export default function LoginPage() {
  const { user, login, loading } = useAuth();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const [demo, setDemo] = useState(false);
  const [microsoft, setMicrosoft] = useState(false);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(() => searchParams.get("sso_error") || "");

  useEffect(() => {
    let cancelled = false;
    api("/auth/config")
      .then((config) => {
        if (cancelled) return;
        const on = Boolean(config?.demo);
        setDemo(on);
        setMicrosoft(Boolean(config?.microsoft));
        if (on) {
          setEmail((current) => current || "s.elidrissi@aui.ma");
          setPassword((current) => current || "aui-demo");
        }
      })
      .catch(() => {
        if (!cancelled) setDemo(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  if (!loading && user) {
    return <Navigate to={coursePath(landingCourse(user))} replace />;
  }

  async function handleSubmit(event) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      const nextUser = await login(email.trim(), password);
      navigate(coursePath(landingCourse(nextUser)));
    } catch (err) {
      setError(err.message || "Login failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="aui-shell flex min-h-screen flex-col px-5 py-6 sm:py-10">
      <div className="oh-land-login-bar">
        <Link to="/" className="oh-land-login-back">
          ← How it works
        </Link>
        <span className="oh-land-login-hint">AUI email · role per course</span>
        <ThemeToggle />
      </div>
      <div className="fade-up mx-auto grid w-full max-w-5xl flex-1 items-center gap-6 lg:grid-cols-[1.1fr_0.9fr]">
        <form onSubmit={handleSubmit} className="glass-panel p-8 sm:p-10">
          <img
            src="/aui-logo.png"
            alt="Al Akhawayn University"
            className="aui-logo mb-6"
          />
          <p className="glass-chip mb-4">Campus product login</p>
          <h1 className="font-display text-4xl font-semibold text-aui-ink sm:text-5xl">
            OfficeHours AI
          </h1>
          <p className="mt-3 max-w-md text-base font-medium text-aui-deep/70">
            Sign in with your AUI email (Initial.Lastname@aui.ma). Role is per
            course. A TA is staff on a course they already completed - not a
            student in that section.
          </p>

          {microsoft ? (
            <>
              <a
                href={`${API_BASE}/auth/microsoft/login`}
                className="ms-signin mt-8"
                data-testid="ms-signin"
              >
                <svg viewBox="0 0 21 21" aria-hidden="true" focusable="false">
                  <rect x="1" y="1" width="9" height="9" fill="#f25022" />
                  <rect x="11" y="1" width="9" height="9" fill="#7fba00" />
                  <rect x="1" y="11" width="9" height="9" fill="#00a4ef" />
                  <rect x="11" y="11" width="9" height="9" fill="#ffb900" />
                </svg>
                Sign in with your AUI Microsoft account
              </a>
              <p className="ms-signin-divider" aria-hidden="true">
                <span>or use a local account</span>
              </p>
            </>
          ) : null}

          <label className="mt-8 block text-xs font-semibold uppercase tracking-wide text-aui-deep/55">
            Email
            <input
              className="field-glass mt-2 px-4 py-3 text-base font-medium"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              autoComplete="username"
              placeholder="S.Abssi@aui.ma"
            />
          </label>
          <label className="mt-4 block text-xs font-semibold uppercase tracking-wide text-aui-deep/55">
            Password
            <input
              type="password"
              className="field-glass mt-2 px-4 py-3 text-base font-medium"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              autoComplete="current-password"
            />
          </label>

          {error ? (
            <p className="clay-blob clay-blob-coral mt-4 block w-full px-4 py-3 text-sm font-semibold text-aui-ink">
              {error}
            </p>
          ) : null}

          <button
            type="submit"
            disabled={busy}
            className="btn-primary mt-6 w-full px-5 py-3.5 text-base disabled:opacity-60"
          >
            {busy ? "Signing in…" : "Sign in"}
          </button>

          {demo ? (
            <p className="mt-4 text-center text-sm font-medium text-aui-deep/60">
              Coming from your LMS?{" "}
              <a href="/canvas-demo" className="font-semibold text-aui-forest underline">
                Open from Canvas (one-click demo)
              </a>
            </p>
          ) : (
            <p className="mt-4 text-center text-sm font-medium text-aui-deep/60">
              Sign in with the account linked from your Canvas course.
            </p>
          )}
        </form>

        {demo ? (
        <aside className="glass-panel glass-panel-deep p-8">
          <p className="text-xs font-semibold uppercase tracking-[0.14em] text-emerald-50/85">
            Demo accounts
          </p>
          <h2 className="font-display mt-2 text-3xl font-semibold">
            Password: aui-demo
          </h2>
          <p className="mt-2 text-sm font-medium text-emerald-50/80">
            Same email shape for every role. Tap to fill the form. Not used on a
            community deploy.
          </p>
          <ul className="mt-6 space-y-3">
            {DEMO_ACCOUNTS.map((account) => (
              <li key={account.email}>
                <button
                  type="button"
                  className="demo-account"
                  onClick={() => {
                    setEmail(account.email);
                    setPassword("aui-demo");
                  }}
                >
                  <span className="demo-dot" aria-hidden="true" />
                  <span>
                    <span className="block font-semibold">{account.role}</span>
                    <span className="block text-sm font-medium opacity-85">
                      {account.email}
                    </span>
                    <span className="block text-xs font-medium opacity-65">
                      {account.note}
                    </span>
                  </span>
                </button>
              </li>
            ))}
          </ul>
        </aside>
        ) : (
        <aside className="glass-panel glass-panel-deep p-8">
          <p className="text-xs font-semibold uppercase tracking-[0.14em] text-emerald-50/85">
            AUI community
          </p>
          <h2 className="font-display mt-2 text-3xl font-semibold">
            Your Canvas course
          </h2>
          <p className="mt-2 text-sm font-medium text-emerald-50/80">
            Courses, chapters, and classmates come from the linked Canvas
            course - not a hardcoded catalog. Ask your professor to open
            OfficeHours from Canvas and sync modules.
          </p>
        </aside>
        )}
      </div>
    </div>
  );
}
