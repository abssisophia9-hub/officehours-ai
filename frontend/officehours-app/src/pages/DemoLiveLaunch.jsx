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

// Coalesce StrictMode double-mount only — expire so revisiting a seat re-logins.
const inflight = new Map();

function launchSeatOnce(seat, { login, logout, setActiveCourse }) {
  if (!inflight.has(seat)) {
    const pending = (async () => {
      const target = SEATS[seat];
      if (!target) throw new Error("Unknown demo seat.");

      const config = await api("/auth/config");
      if (!config?.demo) {
        throw new Error("Demo live links are off (OFFICEHOURS_DEMO=false).");
      }

      await logout();
      const user = await login(target.email, DEMO_PASSWORD);
      const course =
        user.courses.find(
          (item) => item.code === target.code && item.role === target.role,
        ) ||
        user.courses.find((item) => item.role === target.role) ||
        null;
      if (!course) {
        throw new Error(`No ${target.role} seat found for ${target.email}.`);
      }
      setActiveCourse(course);
      return { path: target.path, label: target.label, code: course.code, who: target.who };
    })();
    inflight.set(seat, pending);
    pending.finally(() => {
      setTimeout(() => inflight.delete(seat), 1500);
    });
  }
  return inflight.get(seat);
}

export default function DemoLiveLaunch() {
  const { seat } = useParams();
  const navigate = useNavigate();
  const { login, logout, setActiveCourse } = useAuth();
  const [error, setError] = useState("");
  const [status, setStatus] = useState("Opening demo seat…");

  const target = SEATS[seat];

  useEffect(() => {
    let cancelled = false;

    if (!target) {
      setError("Unknown demo seat. Use /demo/live/student, /ta, or /professor.");
      return undefined;
    }

    setStatus(`Signing in as ${target.who}…`);
    launchSeatOnce(seat, { login, logout, setActiveCourse })
      .then((result) => {
        if (cancelled) return;
        setStatus(`Opening ${result.label} · ${result.code}…`);
        navigate(result.path, { replace: true });
      })
      .catch((err) => {
        if (!cancelled) setError(err.message || "Demo launch failed");
      });

    return () => {
      cancelled = true;
    };
    // Only re-run when the seat changes — auth helpers are stable enough via inflight.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [seat]);

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
