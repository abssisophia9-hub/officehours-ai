import { useEffect, useState } from "react";
import { NavLink, Outlet, useLocation, useNavigate } from "react-router";
import AccountMenu from "../components/AccountMenu.jsx";
import NotificationBell from "../components/NotificationBell.jsx";
import ThemeToggle from "../components/ThemeToggle.jsx";
import { useAuth } from "../auth/AuthContext.jsx";
import { api } from "../api/client.js";
import { pageItems } from "../api/page.js";
import { ProfessorProvider, useProfessorData } from "../pages/professor/ProfessorData.jsx";
import { askHasReply, seenReplyIds, subscribeReplySeen } from "../student/replySeen.js";

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
  stuck: (
    <svg className="bh-nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
      <path d="M21 11.5a8.38 8.38 0 0 1-8.5 8.5 8.5 8.5 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 8.5-8.5 8.38 8.38 0 0 1 8.5 8.5z" />
      <path d="M8.5 12.5h7M12 9v7" />
    </svg>
  ),
  insights: (
    <svg className="bh-nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
      <path d="M4 19h16M7 16V9M12 16V5M17 16v-4" />
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
    {
      group: "Get help",
      items: [
        {
          id: "ask",
          label: "Ask for help",
          icon: "ask",
          to: "/student/ask",
          hint: "Message a TA or your professor",
        },
        {
          id: "asks",
          label: "My asks",
          icon: "requests",
          to: "/student/asks",
          hint: "Replies to your questions",
        },
      ],
    },
    {
      group: "Study",
      items: [
        {
          id: "revision",
          label: "Revision Strategist",
          icon: "insights",
          to: "/student/revision",
          hint: "Today-first exam plan",
        },
      ],
    },
    {
      group: "Community",
      items: [
        {
          id: "stuck-room",
          label: "Rooms",
          icon: "stuck",
          to: "/student/room",
          hint: "Peer help threads",
        },
        {
          id: "peer-notes",
          label: "Classmate Notes",
          icon: "notes",
          to: "/student/notes",
          hint: "Shared course notes",
        },
      ],
    },
  ],
  ta: [
    {
      group: "Desk",
      items: [
        {
          id: "dashboard",
          label: "Dashboard",
          icon: "dashboard",
          to: "/",
        },
        {
          id: "queue",
          label: "Live Queue",
          icon: "queue",
          to: "/ta",
          hint: "Claim, help, reply to students",
        },
        {
          id: "courses",
          label: "My Courses",
          icon: "courses",
          to: "/",
        },
        {
          id: "inbox",
          label: "Inbox",
          icon: "requests",
        },
      ],
    },
  ],
  professor: [
    {
      group: "Teaching",
      items: [
        {
          id: "clusters",
          label: "Repeated Topics",
          icon: "clusters",
          hint: "What to emphasize next",
        },
        {
          id: "review-insights",
          label: "Review Insights",
          icon: "insights",
          hint: "Chapter-end teaching notes",
        },
      ],
    },
    {
      group: "Study Agent",
      items: [
        {
          id: "knowledge",
          label: "Knowledge Review",
          icon: "knowledge",
          hint: "Stamp answers students can trust",
        },
        {
          id: "materials",
          label: "Canvas Materials",
          icon: "canvas",
          hint: "Ground the agent in your slides",
        },
      ],
    },
    {
      group: "Asks",
      items: [
        {
          id: "requests",
          label: "Requests",
          icon: "requests",
          hint: "All course asks",
        },
      ],
    },
  ],
};

function flattenSections(sections) {
  if (!sections.length) return [];
  if (sections[0]?.items) {
    return sections.flatMap((group) => group.items);
  }
  return sections;
}

function NavItemContent({ section }) {
  return (
    <>
      {ICONS[section.icon]}
      <span className="bh-nav-item-stack">
        <strong>{section.label}</strong>
        {section.hint ? <span className="bh-nav-hint">{section.hint}</span> : null}
      </span>
      {section.badge ? <span className="bh-nav-badge">{section.badge}</span> : null}
    </>
  );
}

function useStudentReplyCount(token, userId, course, pathname) {
  const [count, setCount] = useState(0);
  const courseId = course?.role === "student" ? course.id : null;

  useEffect(() => {
    if (!token || !userId || !courseId) {
      setCount(0);
      return undefined;
    }
    let cancelled = false;
    function load() {
      api(`/requests/?course_id=${courseId}&limit=50`, { token })
        .then((data) => {
          if (cancelled) return;
          const seen = seenReplyIds(userId);
          const next = pageItems(data).filter(
            (item) => askHasReply(item) && !seen.has(String(item.id)),
          ).length;
          setCount(next);
        })
        .catch(() => {
          if (!cancelled) setCount(0);
        });
    }
    load();
    const unsubscribe = subscribeReplySeen(() => {
      if (!cancelled) load();
    });
    return () => {
      cancelled = true;
      unsubscribe();
    };
  }, [token, userId, courseId, pathname]);

  return count;
}

function useTaLiveCount(token, course) {
  const [count, setCount] = useState(0);
  const courseId = course?.role === "ta" ? course.id : null;

  useEffect(() => {
    if (!token || !courseId) {
      setCount(0);
      return undefined;
    }
    let cancelled = false;
    function load() {
      const params = new URLSearchParams({
        course_id: String(courseId),
        assignment: "all",
        limit: "1",
        offset: "0",
      });
      api(`/ta/queue/?${params.toString()}`, { token })
        .then((data) => {
          if (cancelled) return;
          const meta = pageMeta(data);
          const items = pageItems(data);
          setCount(meta.total || items.length || 0);
        })
        .catch(() => {
          if (!cancelled) setCount(0);
        });
    }
    load();
    const id = setInterval(load, 8000);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, [token, courseId]);

  return count;
}

export default function AppShell() {
  const { user, token, activeCourse, setActiveCourse } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const replyCount = useStudentReplyCount(token, user?.id, activeCourse, location.pathname);
  const taLiveCount = useTaLiveCount(token, activeCourse);

  const role = activeCourse?.role;
  const roleHome =
    role === "professor" ? "/professor" : role === "ta" ? "/ta" : "/student";
  const sections = SECTION_NAV[role] || [];
  const grouped = Boolean(sections[0]?.items);
  const flatSections = flattenSections(sections);

  const SECTION_ROUTES = {
    "peer-notes": "/student/notes",
    asks: "/student/asks",
    ask: "/student/ask",
    agent: "/student",
    revision: "/student/revision",
    "stuck-room": "/student/room",
  };

  function scrollToSection(id) {
    const routed = SECTION_ROUTES[id];
    if (routed) {
      navigate(routed);
      return;
    }
    const hashTarget = id === "agent" || id === "ask" ? id : null;
    if (location.pathname !== roleHome) {
      navigate(hashTarget ? `${roleHome}#${hashTarget}` : roleHome);
      setTimeout(() => {
        document.getElementById(id)?.scrollIntoView({ behavior: "smooth", block: "start" });
      }, 150);
    } else {
      if (hashTarget) {
        window.history.replaceState(null, "", `${roleHome}#${hashTarget}`);
      }
      document.getElementById(id)?.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  }

  function renderNavItem(section) {
    const badge =
      section.id === "queue" && role === "ta" && taLiveCount > 0
        ? taLiveCount
        : section.badge;
    const content = <NavItemContent section={{ ...section, badge }} />;
    if (section.to) {
      return (
        <NavLink
          key={section.id}
          to={section.to}
          end={section.to === "/ta" || section.to === "/"}
          className={({ isActive }) => {
            // Live Queue owns /ta. Dashboard is active on course home; My Courses stays inactive.
            let active = isActive;
            if (section.id === "queue") {
              active = location.pathname.startsWith("/ta");
            } else if (section.id === "dashboard") {
              active = location.pathname === "/";
            } else if (section.id === "courses") {
              active = false;
            }
            return `bh-nav-item${active ? " active" : ""}`;
          }}
        >
          {content}
        </NavLink>
      );
    }
    if (section.id === "inbox") {
      return (
        <button
          key={section.id}
          type="button"
          className="bh-nav-item"
          onClick={() => {
            const buttons = document.querySelectorAll(".bh-sidebar-footer button");
            for (const button of buttons) {
              if ((button.textContent || "").includes("Inbox")) {
                button.click();
                break;
              }
            }
          }}
        >
          {content}
        </button>
      );
    }
    return (
      <button
        key={section.id}
        type="button"
        className="bh-nav-item"
        onClick={() => scrollToSection(section.id)}
      >
        {content}
      </button>
    );
  }

  if (role === "professor") {
    return (
      <ProfessorProvider>
        <ProfessorFrame />
      </ProfessorProvider>
    );
  }

  return (
    <div
      className={`bh-frame${
        role === "student" ? " bh-frame-student" : role === "ta" ? " bh-frame-ta" : ""
      }`}
    >
      <aside className="bh-sidebar">
        <div className="bh-logo">
          OfficeHours AI
          <small>Al Akhawayn University</small>
        </div>

        <nav className="bh-nav" aria-label={role === "student" ? "Student" : "Workspace"}>
          {role === "student" ? (
            <>
              <NavLink
                to="/student"
                end
                className={({ isActive }) => `bh-nav-item${isActive ? " active" : ""}`}
              >
                {ICONS.agent}
                <span>Study Agent</span>
              </NavLink>
              <NavLink
                to="/student/revision"
                className={({ isActive }) => `bh-nav-item${isActive ? " active" : ""}`}
              >
                {ICONS.insights}
                <span>Revision Strategist</span>
              </NavLink>
              <NavLink
                to="/student/ask"
                className={({ isActive }) => `bh-nav-item${isActive ? " active" : ""}`}
              >
                {ICONS.ask}
                <span>Ask for help</span>
              </NavLink>
              <NavLink
                to="/student/asks"
                className={({ isActive }) => `bh-nav-item${isActive ? " active" : ""}`}
              >
                {ICONS.requests}
                <span>My asks</span>
                {replyCount > 0 ? (
                  <span className="bh-nav-badge">{replyCount}</span>
                ) : null}
              </NavLink>
              <div className="bh-nav-group">
                <p className="bh-nav-label">Classmates</p>
                <NavLink
                  to="/student/room"
                  className={({ isActive }) => `bh-nav-item${isActive ? " active" : ""}`}
                >
                  {ICONS.stuck}
                  <span>Rooms</span>
                </NavLink>
                <NavLink
                  to="/student/notes"
                  className={({ isActive }) => `bh-nav-item${isActive ? " active" : ""}`}
                >
                  {ICONS.notes}
                  <span>Classmate notes</span>
                </NavLink>
              </div>
            </>
          ) : role === "ta" ? (
            sections.map((group) => (
              <div key={group.group} className="bh-nav-group">
                <p className="bh-nav-label">{group.group}</p>
                {group.items.map((section) => renderNavItem(section))}
              </div>
            ))
          ) : (
            <>
              <NavLink
                to={roleHome}
                end
                className={({ isActive }) => `bh-nav-item${isActive ? " active" : ""}`}
              >
                {ICONS.dashboard}
                <span>Dashboard</span>
              </NavLink>
              {grouped
                ? sections.map((group) => (
                    <div key={group.group} className="bh-nav-group">
                      <p className="bh-nav-label">{group.group}</p>
                      {group.items.map((section) => renderNavItem(section))}
                    </div>
                  ))
                : flatSections.map((section) => renderNavItem(section))}
              <div className="bh-nav-group">
                <NavLink
                  to="/"
                  end
                  className={({ isActive }) => `bh-nav-item${isActive ? " active" : ""}`}
                >
                  {ICONS.courses}
                  My Courses
                </NavLink>
              </div>
            </>
          )}
        </nav>

        <div className="bh-sidebar-footer">
          <p className="bh-nav-label">Course</p>
          {role === "student" ? (
            <NavLink to="/" end className="bh-course-all">
              All courses
            </NavLink>
          ) : null}
          <select
            className="bh-course-select"
            aria-label="Course"
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
          <NotificationBell />
          <ThemeToggle className="theme-toggle-sidebar" />
          <AccountMenu onScrollToSection={scrollToSection} />
        </div>
      </aside>

      <main className="bh-main">
        <Outlet />
      </main>
    </div>
  );
}

const PROFESSOR_NAV = [
  { id: "material", label: "Material", to: "/professor", end: true, icon: "knowledge", badgeKey: "waitingFiles" },
  { id: "asks", label: "Asks", to: "/professor/asks", icon: "requests", badgeKey: "assignedAsks" },
  { id: "insights", label: "Insights", to: "/professor/insights", icon: "insights" },
  { id: "team", label: "Team", to: "/professor/team", icon: "queue" },
];

function ProfessorFrame() {
  const { user, activeCourse, setActiveCourse } = useAuth();
  const { waitingFiles, assignedAsks } = useProfessorData();
  const navigate = useNavigate();
  const counts = { waitingFiles, assignedAsks };

  return (
    <div className="bh-frame bh-frame-professor">
      <aside className="bh-sidebar">
        <div className="bh-logo">
          OfficeHours AI
          <small>Al Akhawayn University</small>
        </div>
        <nav className="bh-nav" aria-label="Professor">
          {PROFESSOR_NAV.map((item) => {
            const count = item.badgeKey ? counts[item.badgeKey] : 0;
            return (
              <NavLink
                key={item.id}
                to={item.to}
                end={item.end}
                className={({ isActive }) => `bh-nav-item${isActive ? " active" : ""}`}
              >
                {ICONS[item.icon]}
                <span>{item.label}</span>
                {count > 0 ? (
                  <span className="bh-nav-badge">{count}</span>
                ) : null}
              </NavLink>
            );
          })}
        </nav>
        <div className="bh-sidebar-footer">
          <p className="bh-nav-label">Course</p>
          <select
            className="bh-course-select"
            aria-label="Course"
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
          <NotificationBell plain />
          <ThemeToggle className="theme-toggle-sidebar" />
          <AccountMenu />
        </div>
      </aside>
      <main className="bh-main">
        <Outlet />
      </main>
    </div>
  );
}
