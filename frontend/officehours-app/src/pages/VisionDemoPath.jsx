import { useEffect, useRef, useState } from "react";
import VisionChrome, { Person, VisionCopy } from "../landing/VisionChrome.jsx";

const BEATS = [
  {
    id: "student",
    kicker: "01 · Student",
    title: "The question starts here.",
    body: "Quiet ask if you need privacy. Identify me for a meeting. Rooms if a classmate can help.",
  },
  {
    id: "ta",
    kicker: "02 · TA",
    title: "The same card enters a queue.",
    body: "Ask Triage classifies it. You claim it. Help Coach sits with you — not twenty 1:1s of the same thing.",
  },
  {
    id: "professor",
    kicker: "03 · Professor",
    title: "Then it meets the gate.",
    body: "Clusters and review insights. Approve a FAQ and the Study Agent may say it next time — only after you stamp it.",
  },
];

export default function VisionDemoPath() {
  const stage = useRef(null);
  const [progress, setProgress] = useState(0);
  const [pinned, setPinned] = useState(null);

  useEffect(() => {
    const onScroll = () => {
      const el = stage.current;
      if (!el) return;
      const rect = el.getBoundingClientRect();
      const span = el.offsetHeight - window.innerHeight;
      const gone = -rect.top;
      setProgress(span > 0 ? Math.min(1, Math.max(0, gone / span)) : 0);
    };
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    window.addEventListener("resize", onScroll);
    return () => {
      window.removeEventListener("scroll", onScroll);
      window.removeEventListener("resize", onScroll);
    };
  }, []);

  const beatIndex = progress < 0.33 ? 0 : progress < 0.66 ? 1 : 2;
  const beat = BEATS[pinned ? BEATS.findIndex((b) => b.id === pinned) : beatIndex];
  const t = progress;

  return (
    <VisionChrome kicker="Option 2 · One question travels — scroll the path · click a person">
      <div className="vd-path-hero">
        <VisionCopy option="2" title="One ask. Three people. Same card.">
          <p>
            <span className="vd-drop">S</span>
            croll and the question moves. Click a person to pin that beat. Sign
            in stays up top — the story is optional.
          </p>
        </VisionCopy>
      </div>

      <div className="vd-path-stage" ref={stage}>
        <div className="vd-path-sticky">
          <svg className="vd-path-line" viewBox="0 0 100 40" preserveAspectRatio="none" aria-hidden="true">
            <path d="M 8 30 C 28 8, 42 8, 50 22 C 58 36, 72 34, 92 12" />
          </svg>
          <div className="vd-path-stations">
            <Person
              kind="student"
              label="Student"
              active={beat.id === "student"}
              onClick={() => setPinned(pinned === "student" ? null : "student")}
            />
            <Person
              kind="ta"
              label="TA"
              active={beat.id === "ta"}
              onClick={() => setPinned(pinned === "ta" ? null : "ta")}
            />
            <Person
              kind="professor"
              label="Professor"
              active={beat.id === "professor"}
              onClick={() => setPinned(pinned === "professor" ? null : "professor")}
            />
          </div>
          <div
            className="vd-qcard"
            style={{
              left: `calc(8% + ${t * 72}%)`,
              top: `calc(${t < 0.5 ? 62 - t * 50 : 37 + (t - 0.5) * 10}%)`,
            }}
          >
            <span>Ask</span>
            Why does my recursion never stop?
          </div>
          <article className="vd-card vd-path-read">
            <p className="vd-kicker">{beat.kicker}</p>
            <h2 className="font-display">{beat.title}</h2>
            <p>{beat.body}</p>
          </article>
        </div>
      </div>
    </VisionChrome>
  );
}
