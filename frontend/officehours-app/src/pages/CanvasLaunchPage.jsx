import { useEffect, useRef, useState } from "react";
import { useNavigate, useSearchParams } from "react-router";
import { api } from "../api/client.js";
import { useAuth } from "../auth/AuthContext.jsx";

const STEPS = [
  "Verifying your Canvas identity…",
  "Connecting the course tenant…",
  "Reading course modules…",
  "Ingesting professor slides into the knowledge base…",
  "Spawning the course agent…",
];

// One launch per query string, shared across StrictMode double-mounts so the
// backend sees a single click per Canvas button press.
const launchCache = new Map();

function launchOnce(searchParams) {
  const key = searchParams.toString();
  if (!launchCache.has(key)) {
    launchCache.set(
      key,
      api("/canvas/launch", {
        method: "POST",
        body: {
          canvas_course_id: searchParams.get("canvas_course_id"),
          email: searchParams.get("email"),
          display_name: searchParams.get("display_name"),
          canvas_role: searchParams.get("canvas_role"),
          student_id: searchParams.get("student_id") || null,
        },
      }).catch((err) => {
        launchCache.delete(key);
        throw err;
      }),
    );
  }
  return launchCache.get(key);
}

export default function CanvasLaunchPage() {
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const { adoptSession } = useAuth();
  const [stepIndex, setStepIndex] = useState(0);
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");
  const startedRef = useRef(false);

  useEffect(() => {
    if (startedRef.current) return;
    startedRef.current = true;
    const mountedAt = Date.now();

    const ticker = setInterval(
      () => setStepIndex((index) => Math.min(index + 1, STEPS.length - 1)),
      550,
    );

    async function run() {
      try {
        const launch = await launchOnce(params);
        setResult(launch);
        await adoptSession(launch.token, launch.course_id);
        clearInterval(ticker);
        setStepIndex(STEPS.length - 1);
        // Keep the provisioning summary on screen long enough to read.
        const elapsed = Date.now() - mountedAt;
        const dwell = Math.max(3400 - elapsed, 0) + 1600;
        setTimeout(() => {
          navigate(
            launch.role === "professor"
              ? "/professor"
              : launch.role === "ta"
                ? "/ta"
                : "/student",
            { replace: true },
          );
        }, dwell);
      } catch (err) {
        clearInterval(ticker);
        setError(err.message || "Canvas launch failed");
      }
    }
    run();
    return () => clearInterval(ticker);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div className="aui-shell flex min-h-screen items-center justify-center px-5">
      <div className="glass-panel fade-up w-full max-w-lg p-8 text-center">
        <img
          src="/aui-logo.png"
          alt="Al Akhawayn University"
          className="aui-logo mx-auto mb-5"
        />
        <p className="glass-chip">Canvas launch</p>
        <h1 className="font-display mt-3 text-3xl font-semibold">
          Opening your course workspace
        </h1>

        {error ? (
          <p className="clay-blob clay-blob-coral mt-6 block w-full px-4 py-3 text-sm font-semibold">
            {error}
          </p>
        ) : (
          <ul className="mt-6 space-y-2 text-left">
            {STEPS.map((label, index) => (
              <li
                key={label}
                className={`flex items-center gap-3 rounded-xl px-4 py-2.5 text-sm font-medium transition ${
                  index < stepIndex || result
                    ? "bg-aui-mist text-aui-deep"
                    : index === stepIndex
                      ? "bg-white text-aui-ink shadow-sm"
                      : "text-aui-deep/40"
                }`}
              >
                <span aria-hidden="true">
                  {index < stepIndex || result ? "✓" : index === stepIndex ? "•" : "○"}
                </span>
                {label}
              </li>
            ))}
          </ul>
        )}

        {result ? (
          <div className="soft-stat mt-6 text-left text-sm font-medium">
            <p className="font-semibold text-aui-ink">{result.message}</p>
            <p className="mt-1 text-aui-deep/70">
              {result.course_code} · signed in as {result.display_name} (
              {result.role})
              {result.provisioned_course ? " · new course provisioned" : ""}
              {result.provisioned_user ? " · new account created" : ""}
            </p>
            <p className="mt-1 text-aui-deep/70">
              Course agent: {result.agent_ready ? "ready" : "pending"} ·{" "}
              {result.kb_chunks} KB chunk(s)
              {result.sync ? ` · ${result.sync.files_seen} Canvas file(s)` : ""}
            </p>
          </div>
        ) : null}
      </div>
    </div>
  );
}
