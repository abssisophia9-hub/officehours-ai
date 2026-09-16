import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router";
import { api } from "../api/client.js";
import { useAuth } from "../auth/AuthContext.jsx";

/**
 * One-tap supervisor demo seats. Demo-mode only.
 * Same course (CSC 2302) across Student / TA / Professor so the walkthrough
 * stays on one section while the role changes.
 */
const SEATS = {
  student: {
    email: "s.elidrissi@aui.ma",
    role: "student",
    code: "CSC 2302",
    path: "/student",
    label: "Student",
    who: "Sara El Idrissi",
  },
  ta: {
    email: "a.chen@aui.ma",
    role: "ta",
    code: "CSC 2302",
    path: "/ta",
    label: "TA",
    who: "Alice Chen",
  },
  professor: {
    email: "a.benali@aui.ma",
    role: "professor",
    code: "CSC 2302",
    path: "/professor",
    label: "Professor",
    who: "Prof. Amine Benali",
  },
};

const DEMO_PASSWORD = "aui-demo";

export default function DemoLiveLaunch() {
  const { seat } = useParams();
  const navigate = useNavigate();
  const { login, logout, setActiveCourse } = useAuth();
  const [error, setError] = useState("");
  const [status, setStatus] = useState("Checking demo mode…");

  const target = SEATS[seat];

  useEffect(() => {
    let cancelled = false;

    async function run() {
      if (!target) {
        setError("Unknown demo seat. Use /demo/live/student, /ta, or /professor.");
        return;
      }

      try {
        const config = await api("/auth/config");
        if (cancelled) return;
        if (!config?.demo) {
          setError("Demo live links are off (OFFICEHOURS_DEMO=false).");
          return;
        }

        setStatus(`Signing in as ${target.who}…`);
        await logout();
        if (cancelled) return;

        const user = await login(target.email, DEMO_PASSWORD);
        if (cancelled) return;

        const course =
          user.courses.find(
            (item) => item.code === target.code && item.role === target.role,
          ) ||
          user.courses.find((item) => item.role === target.role) ||
          null;

        if (!course) {
          setError(`No ${target.role} seat found for ${target.email}.`);
          return;
        }

        setActiveCourse(course);
        setStatus(`Opening ${target.label} · ${course.code}…`);
        navigate(target.path, { replace: true });
      } catch (err) {
        if (!cancelled) setError(err.message || "Demo launch failed");
      }
    }

    run();
    return () => {
      cancelled = true;
    };
  }, [target, login, logout, setActiveCourse, navigate]);

  if (error) {
    return (
      <div className="aui-shell flex min-h-screen items-center justify-center px-5">
        <div className="glass-panel max-w-md p-8 text-aui-ink">
          <p className="glass-chip mb-3">Demo launch</p>
          <h1 className="font-display text-3xl font-semibold">Couldn’t open seat</h1>
          <p className="mt-3 text-sm font-medium text-aui-deep/70">{error}</p>
          <Link to="/login?switch=1" className="btn-primary mt-6 inline-flex px-5 py-2.5 text-sm">
            Back to login
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="aui-shell flex min-h-screen items-center justify-center px-5">
      <div className="glass-panel max-w-md p-8 text-aui-ink">
        <p className="glass-chip mb-3">Supervisor demo</p>
        <h1 className="font-display text-3xl font-semibold">
          {target ? `${target.label} · ${target.code}` : "Demo seat"}
        </h1>
        <p className="mt-3 text-sm font-medium text-aui-deep/70">{status}</p>
      </div>
    </div>
  );
}
