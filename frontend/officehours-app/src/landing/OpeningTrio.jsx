import { useEffect, useState } from "react";
import { Link } from "react-router";
import RoleFigure, { ROLES } from "./RoleFigure.jsx";

const STEPS = [
  { n: "01", id: "student", title: "Student asks", note: "Quiet ask, Identify me, or a named Room." },
  { n: "02", id: "ta", title: "TA claims it", note: "Ask Triage routes a queue, not a pile." },
  { n: "03", id: "professor", title: "Professor keeps the gate", note: "Insights first. Stamp before the Study Agent speaks." },
  { n: "04", id: "join", title: "Sign in as yourself", note: "One AUI email. Role is per course." },
];

const TOOLS = [
  {
    href: "#student",
    title: "Quiet ask",
    kicker: "01 · Student",
    action: "Meet the student →",
    body: "Go to staff without putting your name on a board. Identify me only when you want a meeting.",
  },
  {
    href: "#student",
    title: "Rooms",
    kicker: "01 · Classmates",
    action: "See how Rooms work →",
    body: "Named classmate help. Staff stay out. What helps can surface later on the Hilbert board.",
  },
  {
    href: "#professor",
    title: "KB gate",
    kicker: "03 · Professor",
    action: "Meet the professor →",
    body: "Review insights, then stamp a FAQ. The Study Agent does not speak until you do.",
  },
];

export default function OpeningTrio({ variant = "live" }) {
  const [pinned, setPinned] = useState(null);
  const [fromScroll, setFromScroll] = useState("student");
  const currentId = pinned || fromScroll;

  useEffect(() => {
    const nodes = [...document.querySelectorAll("[data-oh-role]")];
    if (!nodes.length) return undefined;
    const io = new IntersectionObserver(
      (entries) => {
        const on = entries
          .filter((entry) => entry.isIntersecting)
          .sort((a, b) => b.intersectionRatio - a.intersectionRatio)[0];
        if (!on) return;
        const id = on.target.getAttribute("data-oh-role");
        setFromScroll(id);
        setPinned((currentPinned) =>
          currentPinned && currentPinned !== id ? null : currentPinned,
        );
      },
      { threshold: [0.35, 0.55, 0.75], rootMargin: "-18% 0px -35% 0px" },
    );
    nodes.forEach((node) => io.observe(node));
    return () => io.disconnect();
  }, []);

  function selectRole(id) {
    setPinned(id);
    setFromScroll(id);
    document.getElementById(id)?.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  return (
    <div className={`oh-open-story oh-open-story-${variant}`}>
      <main className="oh-open-hero" id="hero">
        <div className="oh-open-copy">
          <p className="oh-open-kicker">Al Akhawayn University · Campus product</p>
          <h1 className="font-display">
            Get unstuck without the office-hours{" "}
            <span className="oh-open-mark">lottery.</span>
          </h1>
          <div className="oh-open-body">
            <p>
              <span className="oh-open-drop">F</span>
              inals week, the same question is asked twenty times. Students who
              will not raise a hand wait. TAs drown in a <em>pile</em>, not a
              queue. Professors miss the pattern until the exam already happened.
            </p>
            <p>
              OfficeHours turns that into a path you can read before you sign in:{" "}
              <mark>Quiet ask</mark>, a <mark>TA queue</mark>, and a professor{" "}
              <em>gate</em>. Click a person. Scroll the rest.
            </p>
          </div>
        </div>

        <div className="oh-open-picture" aria-label="Student, TA, and professor">
          {ROLES.map((role) => (
            <RoleFigure
              key={role.id}
              role={role}
              size="lg"
              active={currentId === role.id}
              onClick={() => selectRole(role.id)}
            />
          ))}
        </div>
      </main>

      <section className="oh-open-about" id="about">
        <div className="oh-open-about-copy">
          <p className="oh-open-kicker">About OfficeHours</p>
          <h2 className="font-display">A path, not a pile.</h2>
          <p>
            This is not a chatbot demo and not a jobs board. It is the office-hours
            loop for AUI: a stuck student, a TA with a real queue, a professor who
            decides what the class is allowed to learn next.
          </p>
          <p>
            One login. Role is <mark>per course</mark>. A TA on campus is also a
            student. Canvas memberships switch the workspace. Staff do not lurk in{" "}
            <em>Rooms</em>.
          </p>
        </div>
        <blockquote className="oh-open-mission">
          <p>
            A stuck student asks. A TA claims the card. A professor keeps the gate
            on what is <span>meaningful</span> enough to teach again.
          </p>
          <small>Every FAQ still needs a human stamp before the Study Agent may repeat it.</small>
          <footer>
            <span>2026</span>
            <span>AUI</span>
            <span>1 login</span>
          </footer>
        </blockquote>
      </section>

      <section className="oh-open-path" id="path">
        <div className="oh-open-path-head">
          <div>
            <p className="oh-open-kicker oh-open-kicker-on-dark">The path</p>
            <h2>
              From stuck to stamped — <span>clear.</span>
            </h2>
          </div>
          <p className="oh-open-path-aside">4 STEPS · AUI CAMPUS</p>
        </div>
        <ol className="oh-open-steps">
          {STEPS.map((step, index) => (
            <li key={step.n}>
              <a href={`#${step.id}`}>
                <span className={`oh-open-step-n ${index === 3 ? "is-last" : ""}`}>{step.n}</span>
                <strong>{step.title}</strong>
                <span>{step.note}</span>
              </a>
            </li>
          ))}
        </ol>
      </section>

      <section className="oh-open-tools" id="tools">
        <h2 className="font-display">What you can do before you log in.</h2>
        <ul>
          {TOOLS.map((tool) => (
            <li key={tool.title}>
              <a href={tool.href} className="oh-open-tool">
                <strong>{tool.title}</strong>
                <span className="oh-open-tool-kicker">{tool.kicker}</span>
                <span className="oh-open-tool-meta">{tool.meta}</span>
                <p>{tool.body}</p>
                <span className="oh-open-tool-go">{tool.action}</span>
              </a>
            </li>
          ))}
        </ul>
      </section>

      <div id="roles" className="oh-open-roles">
        <div className="oh-open-legend" role="navigation" aria-label="Roles">
          {ROLES.map((role) => (
            <button
              key={role.id}
              type="button"
              className={`oh-open-role-tab ${currentId === role.id ? "is-on" : ""}`}
              onClick={() => selectRole(role.id)}
            >
              {role.label}
            </button>
          ))}
        </div>

        {ROLES.map((role) => (
          <section
            key={role.id}
            id={role.id}
            data-oh-role={role.id}
            className={`oh-open-chapter ${currentId === role.id ? "is-on" : ""}`}
          >
            <article className="oh-open-card">
              <p className="oh-open-kicker">{role.kicker}</p>
              <h2 className="font-display">{role.title}</h2>
              <p className="oh-open-lead">{role.lead}</p>
              <div className="oh-open-chapter-body">{role.body}</div>
            </article>
            <RoleFigure
              role={role}
              size="xl"
              active
              onClick={() => selectRole(role.id)}
            />
          </section>
        ))}
      </div>

      <section className="oh-open-lime" id="join">
        <div>
          <p className="oh-open-kicker">The product · one login</p>
          <h2>Help is already on campus.</h2>
          <p className="oh-open-lime-quote">
            Stop choosing between waiting in the hallway and never asking —
            a quiet path, or a named room.
          </p>
        </div>
        <div className="oh-open-lime-panel">
          <p>AUI email. Role is per course. A TA can also be a student.</p>
          <Link className="oh-open-signin oh-open-signin-on-lime" to="/login">
            Sign in
          </Link>
        </div>
      </section>

      <footer className="oh-open-end">
        <div>
          <p className="oh-open-end-brand">OfficeHours</p>
          <p>The campus office-hours product for Al Akhawayn University. Quiet ask, Rooms, a TA queue, a professor gate.</p>
          <small>Al Akhawayn University · Ifrane, Morocco</small>
        </div>
        <div>
          <p className="oh-open-kicker oh-open-kicker-on-dark">By the numbers</p>
          <p className="oh-open-stat">1<span>login</span></p>
          <p className="oh-open-stat">3<span>roles per course</span></p>
          <p className="oh-open-stat">∞<span>until you stamp it</span></p>
        </div>
        <div>
          <p className="oh-open-kicker oh-open-kicker-on-dark">Navigate</p>
          <a href="#hero">Home</a>
          <a href="#about">About</a>
          <a href="#path">Path</a>
          <Link to="/login">Sign in</Link>
        </div>
      </footer>
    </div>
  );
}
