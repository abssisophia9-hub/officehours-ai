import { useEffect, useState } from "react";
import { Link } from "react-router";
import RoleFigure, { ROLES } from "./RoleFigure.jsx";

export default function OpeningTrio({ variant = "live" }) {
  const [pinned, setPinned] = useState(null);
  const [fromScroll, setFromScroll] = useState("student");
  const currentId = pinned || fromScroll;
  const current = ROLES.find((role) => role.id === currentId) || ROLES[0];

  useEffect(() => {
    const nodes = [...document.querySelectorAll("[data-oh-role]")];
    if (!nodes.length) return undefined;
    const io = new IntersectionObserver(
      (entries) => {
        const on = entries
          .filter((entry) => entry.isIntersecting)
          .sort((a, b) => b.intersectionRatio - a.intersectionRatio)[0];
        if (on) setFromScroll(on.target.getAttribute("data-oh-role"));
      },
      { threshold: [0.35, 0.55, 0.75], rootMargin: "-18% 0px -35% 0px" },
    );
    nodes.forEach((node) => io.observe(node));
    return () => io.disconnect();
  }, []);

  function selectRole(id) {
    setPinned((currentPinned) => (currentPinned === id ? null : id));
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
          <p className="oh-open-sub">You see the whole product before you scroll.</p>
          <div className="oh-open-body">
            <p>
              <span className="oh-open-drop">T</span>
              hree stylized people, three objects. A stuck student, a TA with a
              queue, a professor who keeps the gate. Click a person to pin that
              role. Scroll to go deeper. Sign in stays in the header.
            </p>
          </div>
          <p className="oh-open-now">
            Looking at <strong>{current.label}</strong>
            {pinned ? " · pinned" : " · from scroll"}
            <span> · {current.tools}</span>
          </p>
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

      <div className="oh-open-legend" role="navigation" aria-label="Roles">
        {ROLES.map((role) => (
          <RoleFigure
            key={role.id}
            role={role}
            size="sm"
            showTools={false}
            active={currentId === role.id}
            onClick={() => selectRole(role.id)}
          />
        ))}
        <p className="oh-open-legend-hint">
          {pinned ? `Pinned · ${current.label}` : `Scroll · ${current.label}`}
        </p>
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
            active={currentId === role.id}
            onClick={() => selectRole(role.id)}
          />
        </section>
      ))}

      <section id="join" className="oh-open-chapter oh-open-join">
        <article className="oh-open-card">
          <p className="oh-open-kicker">The product · one login</p>
          <h2 className="font-display">Role is per course. Sign in as yourself.</h2>
          <p className="oh-open-lead">
            A TA on campus is also a student. One AUI email, memberships from
            Canvas, a workspace that switches when the course does.
          </p>
          <p className="oh-open-cta-row">
            <Link className="oh-open-signin" to="/login">
              Sign in
            </Link>
            <a className="oh-open-ghost" href="#hero">
              Back to the three people
            </a>
          </p>
        </article>
      </section>

      {variant === "live" ? (
        <p className="oh-open-foot">
          Other opening experiments stay at <Link to="/demo">/demo</Link>.
        </p>
      ) : null}
    </div>
  );
}
