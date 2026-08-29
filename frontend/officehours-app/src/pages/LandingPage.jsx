import { Link } from "react-router";
import OpeningStory from "../landing/OpeningTrio.jsx";

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
          <a href="#rooms">Rooms</a>
          <a href="#student">Student</a>
          <a href="#ta">TA</a>
          <a href="#professor">Professor</a>
          <Link className="oh-open-nav-cta" to="/login">
            <span className="oh-open-door" aria-hidden="true" />
            Sign in
          </Link>
        </nav>
      </header>
      <OpeningStory variant="live" />
    </div>
  );
}
