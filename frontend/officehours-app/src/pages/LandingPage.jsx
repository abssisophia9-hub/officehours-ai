import { Link } from "react-router";
import OpeningTrio from "../landing/OpeningTrio.jsx";

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
        <nav aria-label="Roles">
          <a href="#student">Student</a>
          <a href="#ta">TA</a>
          <a href="#professor">Professor</a>
          <Link className="oh-open-nav-cta" to="/login">
            Sign in
          </Link>
        </nav>
      </header>
      <OpeningTrio variant="live" />
    </div>
  );
}
