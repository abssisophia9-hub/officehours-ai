import { NavLink, Outlet, useLocation, useNavigate } from "react-router";
import { useAuth } from "../auth/AuthContext.jsx";

const ICONS = {
  dashboard: (
    <svg className="bh-nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
      <rect x="3" y="3" width="7.5" height="7.5" rx="1.5" />
      <rect x="13.5" y="3" width="7.5" height="7.5" rx="1.5" />
      <rect x="3" y="13.5" width="7.5" height="7.5" rx="1.5" />
      <rect x="13.5" y="13.5" width="7.5" height="7.5" rx="1.5" />
    </svg>
  ),
  courses: (
    <svg className="bh-nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
      <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20" />
      <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z" />
    </svg>
  ),
  ask: (
    <svg className="bh-nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
      <path d="M21 11.5a8.38 8.38 0 0 1-8.5 8.5 8.5 8.5 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 8.5-8.5 8.38 8.38 0 0 1 8.5 8.5z" />
    </svg>
  ),
  agent: (
    <svg className="bh-nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
      <rect x="4" y="7" width="16" height="12" rx="2" />
      <path d="M12 7V4M8 12h.01M16 12h.01M9 16h6" />
    </svg>
  ),
  notes: (
    <svg className="bh-nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
      <path d="M4 4h12v16H4z" />
      <path d="M16 8h4v12H8" />
      <path d="M7 9h6M7 13h6M7 17h4" />
    </svg>
  ),
  queue: (
    <svg className="bh-nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
      <path d="M8 6h13M8 12h13M8 18h13M3 6h.01M3 12h.01M3 18h.01" />
    </svg>
  ),
  clusters: (
    <svg className="bh-nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
      <circle cx="6" cy="6" r="3" />
      <circle cx="18" cy="8" r="3" />
      <circle cx="12" cy="18" r="3" />
      <path d="M8.7 7.5l6.6 0M7.5 8.7l3 6.5M16 10.5l-2.5 5" />
    </svg>
  ),
  knowledge: (
    <svg className="bh-nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
      <path d="M9 11l3 3 8-8" />
      <path d="M20 12v6a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h9" />
    </svg>
  ),
  canvas: (
    <svg className="bh-nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
      <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4M7 10l5 5 5-5M12 15V3" />
    </svg>
  ),
  requests: (
    <svg className="bh-nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
      <path d="M14 2v6h6M16 13H8M16 17H8M10 9H8" />
    </svg>
  ),
};

const SECTION_NAV = {
  student: [
    { id: "ask", label: "Ask for Help", icon: "ask" },
    { id: "agent", label: "Study Agent", icon: "agent" },
    { id: "peer-notes", label: "Classmate Notes", icon: "notes" },
  ],
  ta: [
    { id: "queue", label: "Live Queue", icon: "queue" },
  ],
  professor: [
    { id: "clusters", label: "Repeated Topics", icon: "clusters" },
    { id: "knowledge", label: "Knowledge Review", icon: "knowledge" },
    { id: "materials", label: "Canvas Materials", icon: "canvas" },
    { id: "requests", label: "Requests", icon: "requests" },
  ],
};

export default function AppShell() {
  const { user, activeCourse, setActiveCourse, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const role = activeCourse?.role;
  const roleHome =
    role === "professor" ? "/professor" : role === "ta" ? "/ta" : "/student";
  const sections = SECTION_NAV[role] || [];
  const initials = (user.display_name || "?")
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0].toUpperCase())
    .join("");

  function scrollToSection(id) {
    if (location.pathname !== roleHome) {
      navigate(roleHome);
      setTimeout(() => {
        document.getElementById(id)?.scrollIntoView({ behavior: "smooth", block: "start" });
      }, 150);
    } else {
      document.getElementById(id)?.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  }

  return (
    <div className="bh-frame">
      <aside className="bh-sidebar">
        <div className="bh-logo">
          OfficeHours AI
          <small>Al Akhawayn University</small>
        </div>

        <nav className="bh-nav">
          <NavLink
            to={roleHome}
            end
            className={({ isActive }) => `bh-nav-item${isActive ? " active" : ""}`}
          >
            {ICONS.dashboard}
            Dashboard
          </NavLink>
          {sections.map((section) => (
            <button
              key={section.id}
              type="button"
              className="bh-nav-item"
              onClick={() => scrollToSection(section.id)}
            >
              {ICONS[section.icon]}
              {section.label}
            </button>
          ))}
          <NavLink
            to="/"
            end
            className={({ isActive }) => `bh-nav-item${isActive ? " active" : ""}`}
          >
            {ICONS.courses}
            My Courses
          </NavLink>

          <p className="bh-nav-label">Course</p>
          <select
            className="bh-course-select"
            value={activeCourse?.id || ""}
            onChange={(event) => {
              const next = user.courses.find(
                (course) => String(course.id) === event.target.value,
              );
              setActiveCourse(next || null);
              if (next) {
                navigate(
                  next.role === "professor"
                    ? "/professor"
                    : next.role === "ta"
                      ? "/ta"
                      : "/student",
                );
              }
            }}
          >
            {user.courses.map((course) => (
              <option key={course.id} value={course.id}>
                {course.code} ({course.role})
              </option>
            ))}
          </select>
        </nav>

        <div className="bh-user">
          <div className="bh-avatar">{initials}</div>
          <div>
            <p className="bh-user-name">{user.display_name}</p>
            <p className="bh-user-role">
              {activeCourse ? `${activeCourse.role} · ${activeCourse.code}` : "No course"}
            </p>
          </div>
        </div>
        <button
          type="button"
          className="bh-logout"
          onClick={async () => {
            await logout();
            navigate("/login");
          }}
        >
          Log out
        </button>
      </aside>

      <main className="bh-main">
        <Outlet />
      </main>
    </div>
  );
}
