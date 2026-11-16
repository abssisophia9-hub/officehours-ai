import { Link } from "react-router";
import VisionChrome from "../landing/VisionChrome.jsx";

const CARDS = [
  {
    to: "/demo/board",
    n: "01",
    title: "The Ask Board",
    blurb: "One look: this is help, a queue, and a gate - not job postings. Click a slip.",
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
    blurb: "Now the live homepage. All three roles on screen at once. Scroll focuses; click a person.",
  },
  {
    to: "/demo/student-vision",
    n: "04",
    title: "Student IA + Pedagogy Agent",
    blurb:
      "Student Home, My asks tracking, Study Agent vs Pedagogy Agent (practice scores + syllabus).",
  },
];

export default function VisionDemoHub() {
  return (
    <VisionChrome>
      <main className="vd-hub">
        <p className="vd-kicker">Option 3 is the live homepage · 01 and 02 stay as experiments</p>
        <h1 className="font-display">Three people, one picture.</h1>
        <p className="vd-hub-lead">
          The opening is the trio: Student, TA, and Professor at once. The
          other two demos remain here if you want to compare. Sign in stays in
          the header.
        </p>
        <ul className="vd-hub-grid">
          {CARDS.map((card) => (
            <li key={card.to}>
              <Link to={card.to} className={`vd-hub-card${card.n === "03" ? " is-chosen" : ""}`}>
                <span className="vd-kicker">{card.n}</span>
                <strong>{card.title}</strong>
                <span>{card.blurb}</span>
              </Link>
            </li>
          ))}
        </ul>
        <p className="vd-hub-foot">
          Live opening is now Option 3 on the{" "}
          <Link to="/">homepage</Link>.
        </p>
      </main>
    </VisionChrome>
  );
}
