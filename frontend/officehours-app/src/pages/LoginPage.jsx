import { useState } from "react";
import { Navigate, useNavigate } from "react-router-dom";
import { useAuth } from "../auth/AuthContext.jsx";

const DEMO_ACCOUNTS = [
  { email: "student@aui.ma", role: "Student", note: "CS 400 + CS 330", blob: "clay-blob-mint" },
  { email: "ta.alice@aui.ma", role: "TA", note: "CS 400", blob: "clay-blob-sky" },
  { email: "professor@aui.ma", role: "Professor", note: "CS 400 + CS 330", blob: "clay-blob-butter" },
];

export default function LoginPage() {
  const { user, login, loading } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState("student@aui.ma");
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
      <div className="grid w-full max-w-5xl gap-6 lg:grid-cols-[1.1fr_0.9fr]">
        <form onSubmit={handleSubmit} className="glass-panel p-8 sm:p-10">
          <img
            src="/aui-logo.png"
            alt="Al Akhawayn University"
            className="aui-logo clay-wiggle mb-6"
          />
          <p className="glass-chip mb-4">Extra-squishy campus login</p>
          <h1 className="font-display text-4xl font-bold text-aui-ink sm:text-5xl">
            OfficeHours AI
          </h1>
          <p className="mt-3 text-lg font-semibold text-aui-deep/75">
            Poke the clay tiles, press the buttons, ask quietly — AUI office hours
            without the intimidation.
          </p>

          <label className="mt-8 block text-sm font-extrabold uppercase tracking-wide text-aui-deep/60">
            Email
            <input
              className="field-glass mt-2 px-4 py-3 text-base font-semibold"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              autoComplete="username"
            />
          </label>
          <label className="mt-4 block text-sm font-extrabold uppercase tracking-wide text-aui-deep/60">
            Password
            <input
              type="password"
              className="field-glass mt-2 px-4 py-3 text-base font-semibold"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              autoComplete="current-password"
            />
          </label>

          {error ? (
            <p className="clay-blob clay-blob-coral mt-4 px-4 py-3 text-sm font-bold text-aui-ink">
              {error}
            </p>
          ) : null}

          <button
            type="submit"
            disabled={busy}
            className="btn-primary mt-6 w-full px-5 py-4 text-lg disabled:opacity-60"
          >
            {busy ? "Squishing in…" : "Sign in"}
          </button>
        </form>

        <aside className="glass-panel glass-panel-deep p-8">
          <p className="text-sm font-extrabold uppercase tracking-[0.16em] text-emerald-50/90">
            Demo play accounts
          </p>
          <h2 className="font-display mt-2 text-3xl font-bold">Password: aui-demo</h2>
          <p className="mt-2 text-sm font-semibold text-emerald-50/85">
            Tap a role — we’ll fill the form for you.
          </p>
          <ul className="mt-6 space-y-3">
            {DEMO_ACCOUNTS.map((account) => (
              <li key={account.email}>
                <button
                  type="button"
                  className={`clay-blob ${account.blob} w-full px-4 py-3 text-left text-aui-ink transition hover:-translate-y-1`}
                  onClick={() => {
                    setEmail(account.email);
                    setPassword("aui-demo");
                  }}
                >
                  <p className="font-extrabold">{account.role}</p>
                  <p className="text-sm font-semibold opacity-80">{account.email}</p>
                  <p className="text-xs font-bold opacity-65">{account.note}</p>
                </button>
              </li>
            ))}
          </ul>
        </aside>
      </div>
    </div>
  );
}
