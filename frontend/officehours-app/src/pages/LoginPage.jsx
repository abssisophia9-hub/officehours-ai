import { useState } from "react";
import { Navigate, useNavigate } from "react-router-dom";
import { useAuth } from "../auth/AuthContext.jsx";

// AUI emails are Initial.Lastname@aui.ma — role comes from course membership, not email.
const DEMO_ACCOUNTS = [
  {
    email: "s.elidrissi@aui.ma",
    role: "Student",
    note: "7 courses · CSC 2302…",
  },
  {
    email: "a.chen@aui.ma",
    role: "TA",
    note: "CSC 2302",
  },
  {
    email: "a.benali@aui.ma",
    role: "Professor",
    note: "CSC 2302 · 3323 · 3374",
  },
];

export default function LoginPage() {
  const { user, login, loading } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState("s.elidrissi@aui.ma");
  const [password, setPassword] = useState("aui-demo");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  if (!loading && user) {
    const first = user.courses[0];
    const path =
      first?.role === "professor"
        ? "/professor"
        : first?.role === "ta"
          ? "/ta"
          : first
            ? "/student"
            : "/";
    return <Navigate to={path} replace />;
  }

  async function handleSubmit(event) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      const nextUser = await login(email.trim(), password);
      const first = nextUser.courses[0];
      if (!first) {
        navigate("/");
        return;
      }
      navigate(
        first.role === "professor"
          ? "/professor"
          : first.role === "ta"
            ? "/ta"
            : "/student",
      );
    } catch (err) {
      setError(err.message || "Login failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="aui-shell flex min-h-screen items-center justify-center px-5 py-10">
      <div className="fade-up grid w-full max-w-5xl items-stretch gap-6 lg:grid-cols-[1.1fr_0.9fr]">
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
            Sign in with your AUI email (Initial.Lastname@aui.ma). Your role in
            each course comes from membership — not from the email itself.
          </p>

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

          <p className="mt-4 text-center text-sm font-medium text-aui-deep/60">
            Coming from your LMS?{" "}
            <a href="/canvas-demo" className="font-semibold text-aui-forest underline">
              Open from Canvas (one-click demo)
            </a>
          </p>
        </form>

        <aside className="glass-panel glass-panel-deep p-8">
          <p className="text-xs font-semibold uppercase tracking-[0.14em] text-emerald-50/85">
            Demo accounts
          </p>
          <h2 className="font-display mt-2 text-3xl font-semibold">
            Password: aui-demo
          </h2>
          <p className="mt-2 text-sm font-medium text-emerald-50/80">
            Same email shape for every role. Tap to fill the form.
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
      </div>
    </div>
  );
}
