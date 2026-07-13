import { useState } from "react";
import { Navigate, useNavigate } from "react-router-dom";
import { useAuth } from "../auth/AuthContext.jsx";

const DEMO_ACCOUNTS = [
  { email: "student@aui.ma", role: "Student", note: "CS 400 + CS 330" },
  { email: "ta.alice@aui.ma", role: "TA", note: "CS 400" },
  { email: "professor@aui.ma", role: "Professor", note: "CS 400 + CS 330" },
];

export default function LoginPage() {
  const { user, login, loading } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState("student@aui.ma");
  const [password, setPassword] = useState("aui-demo");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  if (!loading && user) {
    return <Navigate to="/" replace />;
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
      <div className="grid w-full max-w-5xl gap-6 lg:grid-cols-[1.1fr_0.9fr]">
        <form onSubmit={handleSubmit} className="glass-panel p-8 sm:p-10">
          <img src="/aui-logo.png" alt="Al Akhawayn University" className="aui-logo mb-6" />
          <p className="glass-chip mb-4">Campus product login</p>
          <h1 className="font-display text-4xl font-bold text-aui-ink">
            OfficeHours AI
          </h1>
          <p className="mt-3 text-lg text-aui-deep/75">
            One packaged platform for students, TAs, and professors — with
            course-scoped workspaces.
          </p>

          <label className="mt-8 block text-sm font-semibold uppercase tracking-wide text-aui-deep/60">
            Email
            <input
              className="field-glass mt-2 px-4 py-3 text-base"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              autoComplete="username"
            />
          </label>
          <label className="mt-4 block text-sm font-semibold uppercase tracking-wide text-aui-deep/60">
            Password
            <input
              type="password"
              className="field-glass mt-2 px-4 py-3 text-base"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              autoComplete="current-password"
            />
          </label>

          {error ? (
            <p className="mt-4 rounded-xl border border-red-200 bg-red-50/80 px-4 py-3 text-sm text-red-700">
              {error}
            </p>
          ) : null}

          <button
            type="submit"
            disabled={busy}
            className="btn-primary mt-6 w-full px-5 py-4 text-lg disabled:opacity-60"
          >
            {busy ? "Signing in…" : "Sign in"}
          </button>
        </form>

        <aside className="glass-panel glass-panel-deep p-8 text-white">
          <p className="text-sm font-bold uppercase tracking-[0.18em] text-emerald-50/90">
            Supervisor demo accounts
          </p>
          <h2 className="font-display mt-2 text-3xl font-bold">Password: aui-demo</h2>
          <ul className="mt-6 space-y-4">
            {DEMO_ACCOUNTS.map((account) => (
              <li key={account.email}>
                <button
                  type="button"
                  className="w-full rounded-2xl bg-white/10 px-4 py-3 text-left backdrop-blur transition hover:bg-white/20"
                  onClick={() => {
                    setEmail(account.email);
                    setPassword("aui-demo");
                  }}
                >
                  <p className="font-bold">{account.role}</p>
                  <p className="text-sm text-emerald-50/90">{account.email}</p>
                  <p className="text-xs text-emerald-50/70">{account.note}</p>
                </button>
              </li>
            ))}
          </ul>
        </aside>
      </div>
    </div>
  );
}
