import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { useAuth } from "../auth/AuthContext.jsx";

export default function AppShell() {
  const { user, activeCourse, setActiveCourse, logout } = useAuth();
  const navigate = useNavigate();

  const role = activeCourse?.role;
  const roleHome =
    role === "professor" ? "/professor" : role === "ta" ? "/ta" : "/student";

  return (
    <div className="aui-shell min-h-screen text-aui-ink">
      <header className="px-5 pt-5 sm:px-8">
        <div className="clay-stripe mb-3" />
        <div className="glass-header flex flex-col gap-4 px-5 py-4 lg:flex-row lg:items-center lg:justify-between">
          <div className="flex items-center gap-4">
            <img src="/aui-logo.png" alt="Al Akhawayn University" className="aui-logo clay-wiggle" />
            <div>
              <p className="font-display text-2xl font-bold leading-tight text-aui-ink sm:text-3xl">
                OfficeHours AI
              </p>
              <p className="text-sm font-semibold text-aui-deep/70">
                {user.display_name} ·{" "}
                {activeCourse
                  ? `${activeCourse.code} (${activeCourse.role})`
                  : "Pick a course"}
              </p>
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <label className="text-xs font-extrabold uppercase tracking-wide text-aui-deep/60">
              Course
              <select
                className="field-glass ml-2 px-3 py-2 text-sm font-bold"
                value={activeCourse?.id || ""}
                onChange={(event) => {
                  const next = user.courses.find(
                    (course) => String(course.id) === event.target.value,
                  );
                  setActiveCourse(next || null);
                  if (next) {
                    const path =
                      next.role === "professor"
                        ? "/professor"
                        : next.role === "ta"
                          ? "/ta"
                          : "/student";
                    navigate(path);
                  }
                }}
              >
                {user.courses.map((course) => (
                  <option key={course.id} value={course.id}>
                    {course.code} — {course.title} ({course.role})
                  </option>
                ))}
              </select>
            </label>
            <NavLink to="/" className="btn-ghost px-4 py-2 text-sm">
              Courses
            </NavLink>
            {role ? (
              <NavLink to={roleHome} className="btn-ghost px-4 py-2 text-sm">
                Workspace
              </NavLink>
            ) : null}
            <button
              type="button"
              className="btn-primary px-4 py-2 text-sm"
              onClick={async () => {
                await logout();
                navigate("/login");
              }}
            >
              Log out
            </button>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-6xl px-5 py-8 sm:px-8">
        <Outlet />
      </main>

      <footer className="px-5 pb-8 text-center text-sm font-semibold text-aui-deep/55 sm:px-8">
        Soft clay UI · AUI campus product · Ask quietly, get help faster
      </footer>
    </div>
  );
}
