import { Link } from "react-router";
import VisionChrome from "../landing/VisionChrome.jsx";

const CARDS = [
  {
    to: "/demo/board",
    n: "01",
    title: "The Ask Board",
    blurb: "One look: this is help, a queue, and a gate — not job postings. Click a slip.",
  },
  {
    to: "/demo/path",
    n: "02",
    title: "One question travels",
    blurb: "Scroll and the same ask moves student → TA → professor. Click a person.",
  },
  {
    to: "/demo/trio",
    n: "03",
    title: "Three people, one picture",
    blurb: "All three roles on screen at once. Scroll focuses; click a person.",
  },
];

export default function VisionDemoHub() {
  return (
    <VisionChrome>
      <main className="vd-hub">
        <p className="vd-kicker">Pick a direction · same product, three openings</p>
        <h1 className="font-display">Which opening feels like OfficeHours?</h1>
        <p className="vd-hub-lead">
          BeHive makes jobs obvious with a corkboard. These demos try the same
          trick for office hours — no toy campus. Sign in stays in the header.
        </p>
        <ul className="vd-hub-grid">
          {CARDS.map((card) => (
            <li key={card.to}>
              <Link to={card.to} className="vd-hub-card">
                <span className="vd-kicker">{card.n}</span>
                <strong>{card.title}</strong>
                <span>{card.blurb}</span>
              </Link>
            </li>
          ))}
        </ul>
        <p className="vd-hub-foot">
          Live product landing is still the{" "}
          <Link to="/">current homepage</Link> until you choose.
        </p>
      </main>
    </VisionChrome>
  );
}
