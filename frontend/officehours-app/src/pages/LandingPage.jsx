import { useEffect, useState } from "react";
import { Link } from "react-router";
import OpeningStory from "../landing/OpeningTrio.jsx";

const TICKER = [
  "Quiet ask",
  "Identify me",
  "Rooms",
  "Ask Triage",
  "Help Coach",
  "Review insights",
  "KB gate",
  "Al Akhawayn University",
];

export default function LandingPage() {
  const [section, setSection] = useState("hero");

  useEffect(() => {
    const nodes = ["hero", "about", "path", "roles"].map((id) => document.getElementById(id)).filter(Boolean);
    if (!nodes.length) return undefined;
    const io = new IntersectionObserver(
      (entries) => {
        const on = entries
          .filter((entry) => entry.isIntersecting)
          .sort((a, b) => b.intersectionRatio - a.intersectionRatio)[0];
        if (on) setSection(on.id);
      },
      { threshold: 0.25, rootMargin: "-20% 0px -55% 0px" },
    );
    nodes.forEach((node) => io.observe(node));
    return () => io.disconnect();
  }, []);

  return (
    <div className="oh-open">
      <header className="oh-open-nav">
        <a className="oh-open-brand" href="#hero">
          <img src="/aui-logo.png" alt="Al Akhawayn University" />
          <span>
            OfficeHours
            <small>AUI campus product</small>
          </span>
        </a>
        <nav aria-label="Page">
          <a href="#about" className={section === "about" ? "is-on" : ""}>
            About
          </a>
          <a href="#path" className={section === "path" ? "is-on" : ""}>
            Path
          </a>
          <a href="#roles" className={section === "roles" ? "is-on" : ""}>
            Roles
          </a>
          <Link className="oh-open-nav-cta" to="/login">
            <span className="oh-open-door" aria-hidden="true" />
            Sign in
          </Link>
        </nav>
      </header>
      <p className="oh-open-ticker" aria-label="Product objects">
        <span className="oh-open-ticker-track">
          {[0, 1].map((copy) => (
            <span key={copy} className="oh-open-ticker-copy">
              {TICKER.map((item) => (
                <span key={`${copy}-${item}`}>{item}</span>
              ))}
            </span>
          ))}
        </span>
      </p>
      <OpeningStory variant="live" />
    </div>
  );
}
