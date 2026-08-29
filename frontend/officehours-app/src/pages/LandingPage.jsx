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
          <a href="#about">About</a>
          <a href="#path">Path</a>
          <a href="#roles">Roles</a>
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
