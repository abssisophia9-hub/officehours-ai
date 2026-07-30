import { useEffect, useId, useRef, useState } from "react";
import { useNavigate } from "react-router";
import { api } from "../api/client.js";
import { useAuth } from "../auth/AuthContext.jsx";

const MENU_ICONS = {
  tour: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" aria-hidden>
      <path d="M3 6.5 9 4l6 2.5L21 4v15.5L15 22l-6-2.5L3 22V6.5z" />
      <path d="M9 4v15.5M15 6.5V22" />
    </svg>
  ),
  bug: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" aria-hidden>
      <path d="M8 9a4 4 0 0 1 8 0v6a4 4 0 0 1-8 0V9z" />
      <path d="M12 3v2M7 7 5 5M17 7l2-2M5 12h2M17 12h2M7 17l-2 2M17 17l2 2" />
    </svg>
  ),
  logout: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" aria-hidden>
      <path d="M10 4H6a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h4" />
      <path d="M15 8l4 4-4 4M9 12h10" />
    </svg>
  ),
  chevron: (
    <svg className="bh-account-chevron" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden>
      <path d="M7 14l5-5 5 5" />
      <path d="M7 10l5 5 5-5" />
    </svg>
  ),
};

const TOURS = {
  student: [
    {
      title: "Ask for Help",
      body: "Quiet ask hides your name. Identify me shares it. Pick a TA or the professor when that choice is available, then choose message, face-to-face, or online.",
      sectionId: "ask",
    },
    {
      title: "Course Study Agent",
      body: "Answers only from professor-approved FAQs and Canvas materials for this course. If nothing matches, ask a human — don't keep guessing.",
      sectionId: "agent",
    },
    {
      title: "Classmate notes",
      body: "Share study notes with classmates: say what they cover, upload, then like, comment, or download. Peer notes do not train the study agent.",
      sectionId: "peer-notes",
    },
  ],
  ta: [
    {
      title: "Live Queue",
      body: "Work course asks assigned to you or where you are backup. Draft teaching notes, then send them toward professor curation.",
      sectionId: "queue",
    },
  ],
  professor: [
    {
      title: "Repeated Topics",
      body: "See clustered student struggle themes for this course and decide what to turn into FAQs or agenda items.",
      sectionId: "clusters",
    },
    {
      title: "Knowledge Review",
      body: "Approve or edit drafts so the study agent only answers from materials you trust.",
      sectionId: "knowledge",
    },
    {
      title: "Canvas Materials",
      body: "Sync or upload course materials into the course knowledge base for student study.",
      sectionId: "materials",
    },
  ],
};

function Modal({ title, onClose, children, wide }) {
  return (
    <div className="bh-modal-backdrop" role="presentation" onClick={onClose}>
      <div
        className={`bh-modal${wide ? " bh-modal-wide" : ""}`}
        role="dialog"
        aria-modal="true"
        aria-label={title}
        onClick={(event) => event.stopPropagation()}
      >
        <div className="bh-modal-head">
          <h2>{title}</h2>
          <button type="button" className="bh-modal-close" onClick={onClose} aria-label="Close">
            ×
          </button>
        </div>
        {children}
      </div>
    </div>
  );
}

export default function AccountMenu({ onScrollToSection }) {
  const { user, activeCourse, token, logout } = useAuth();
  const navigate = useNavigate();
  const menuId = useId();
  const rootRef = useRef(null);
  const [open, setOpen] = useState(false);
  const [tourOpen, setTourOpen] = useState(false);
  const [tourStep, setTourStep] = useState(0);
  const [bugOpen, setBugOpen] = useState(false);
  const [bugTitle, setBugTitle] = useState("");
  const [bugBody, setBugBody] = useState("");
  const [bugBusy, setBugBusy] = useState(false);
  const [bugDone, setBugDone] = useState(false);
  const [bugError, setBugError] = useState("");

  const role = activeCourse?.role || "student";
  const tourSteps = TOURS[role] || TOURS.student;
  const initials = (user.display_name || "?")
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0].toUpperCase())
    .join("");

  useEffect(() => {
    if (!open) return undefined;
    function onDocClick(event) {
      if (!rootRef.current?.contains(event.target)) setOpen(false);
    }
    function onKey(event) {
      if (event.key === "Escape") setOpen(false);
    }
    document.addEventListener("mousedown", onDocClick);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onDocClick);
      document.removeEventListener("keydown", onKey);
    };
  }, [open]);

  function startTour() {
    setOpen(false);
    setTourStep(0);
    setTourOpen(true);
    const first = tourSteps[0];
    if (first?.sectionId) onScrollToSection?.(first.sectionId);
  }

  function nextTour() {
    const next = tourStep + 1;
    if (next >= tourSteps.length) {
      setTourOpen(false);
      return;
    }
    setTourStep(next);
    const step = tourSteps[next];
    if (step?.sectionId) onScrollToSection?.(step.sectionId);
  }

  async function submitBug(event) {
    event.preventDefault();
    setBugBusy(true);
    setBugError("");
    try {
      await api("/feedback/bugs", {
        method: "POST",
        token,
        body: {
          title: bugTitle.trim(),
          body: bugBody.trim(),
          course_id: activeCourse?.id ?? null,
          course_code: activeCourse?.code ?? null,
          role,
          page_path: window.location.pathname,
        },
      });
      setBugDone(true);
      setBugTitle("");
      setBugBody("");
    } catch (err) {
      setBugError(err.message);
    } finally {
      setBugBusy(false);
    }
  }

  async function handleLogout() {
    setOpen(false);
    await logout();
    navigate("/login");
  }

  return (
    <>
      <div className="bh-account" ref={rootRef}>
        {open ? (
          <div className="bh-account-menu" id={menuId} role="menu">
            <button type="button" className="bh-account-item" role="menuitem" onClick={startTour}>
              <span className="bh-account-item-icon">{MENU_ICONS.tour}</span>
              Tour
            </button>
            <button
              type="button"
              className="bh-account-item"
              role="menuitem"
              onClick={() => {
                setOpen(false);
                setBugDone(false);
                setBugError("");
                setBugOpen(true);
              }}
            >
              <span className="bh-account-item-icon">{MENU_ICONS.bug}</span>
              Report Bug/Issue
            </button>
            <button
              type="button"
              className="bh-account-item bh-account-item-danger"
              role="menuitem"
              onClick={handleLogout}
            >
              <span className="bh-account-item-icon">{MENU_ICONS.logout}</span>
              Log out
            </button>
          </div>
        ) : null}

        <button
          type="button"
          className={`bh-account-trigger${open ? " open" : ""}`}
          aria-haspopup="menu"
          aria-expanded={open}
          aria-controls={open ? menuId : undefined}
          onClick={() => setOpen((value) => !value)}
        >
          <div className="bh-avatar" aria-hidden>
            {initials}
          </div>
          <div className="bh-account-copy">
            <p className="bh-user-name">{user.display_name}</p>
            <p className="bh-user-role">
              {activeCourse
                ? `${activeCourse.role} · ${activeCourse.code}`
                : "No course"}
            </p>
          </div>
          {MENU_ICONS.chevron}
        </button>
      </div>

      {tourOpen ? (
        <Modal title="Quick tour" onClose={() => setTourOpen(false)} wide>
          <p className="bh-modal-kicker">
            {role} workspace
            {activeCourse ? ` · ${activeCourse.code}` : ""}
          </p>
          <h3 className="bh-modal-step-title">
            {tourStep + 1}. {tourSteps[tourStep]?.title}
          </h3>
          <p className="bh-modal-body">{tourSteps[tourStep]?.body}</p>
          <div className="bh-modal-actions">
            <button type="button" className="btn-ghost px-4 py-2 text-sm" onClick={() => setTourOpen(false)}>
              Close
            </button>
            <button type="button" className="btn-primary px-4 py-2 text-sm" onClick={nextTour}>
              {tourStep + 1 >= tourSteps.length ? "Done" : "Next"}
            </button>
          </div>
        </Modal>
      ) : null}

      {bugOpen ? (
        <Modal
          title="Report Bug/Issue"
          onClose={() => {
            setBugOpen(false);
            setBugDone(false);
          }}
        >
          {bugDone ? (
            <>
              <p className="bh-modal-body">
                Thanks — your report was saved for the course team. Keep teaching
                (or studying); we&apos;ll use this to harden OfficeHours AI.
              </p>
              <div className="bh-modal-actions">
                <button
                  type="button"
                  className="btn-primary px-4 py-2 text-sm"
                  onClick={() => {
                    setBugOpen(false);
                    setBugDone(false);
                  }}
                >
                  Done
                </button>
              </div>
            </>
          ) : (
            <form onSubmit={submitBug} className="space-y-3">
              <p className="bh-modal-body">
                Tell us what broke or felt wrong. Include the page and what you
                expected.
              </p>
              <input
                className="field-glass w-full px-3 py-2.5 text-sm"
                placeholder="Short title"
                value={bugTitle}
                onChange={(event) => setBugTitle(event.target.value)}
                required
              />
              <textarea
                className="field-glass min-h-28 w-full px-3 py-2.5 text-sm"
                placeholder="What happened?"
                value={bugBody}
                onChange={(event) => setBugBody(event.target.value)}
                required
              />
              {bugError ? <p className="text-sm text-red-700">{bugError}</p> : null}
              <div className="bh-modal-actions">
                <button
                  type="button"
                  className="btn-ghost px-4 py-2 text-sm"
                  onClick={() => setBugOpen(false)}
                >
                  Cancel
                </button>
                <button type="submit" disabled={bugBusy} className="btn-primary px-4 py-2 text-sm">
                  {bugBusy ? "Sending…" : "Submit report"}
                </button>
              </div>
            </form>
          )}
        </Modal>
      ) : null}
    </>
  );
}
