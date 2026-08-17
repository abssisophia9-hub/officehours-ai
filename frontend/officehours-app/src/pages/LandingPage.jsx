import { lazy, Suspense, useEffect, useRef, useState } from "react";
import { Link } from "react-router";
import { chapterFromProgress } from "../landing/helpPath.js";
import { hasWebGL } from "../landing/webgl.js";

const CampusCanvas = lazy(() => import("../landing/CampusCanvas.jsx"));

const CHAPTERS = [
  {
    id: "hero",
    kicker: "Al Akhawayn University · Final Year Project",
    title: (
      <>
        Get unstuck without the office-hours{" "}
        <span className="oh-land-mark">lottery.</span>
      </>
    ),
    body: (
      <>
        <p>
          <span className="oh-land-drop">F</span>
          inals week at AUI, the same question is asked twenty times. Students
          who will not raise a hand wait. TAs drown in a pile, not a queue.
          Professors miss the pattern until the exam already happened.
        </p>
        <p>
          OfficeHours AI turns that chaos into a path: a student asks, a TA
          helps, a professor keeps the gate on what the class learns next.
        </p>
      </>
    ),
  },
  {
    id: "student",
    kicker: "01 · Student",
    title: "You do not have to perform in front of the room.",
    body: (
      <>
        <p>
          <strong>Quiet ask</strong> goes to staff without putting your name on
          a public board — the private path when the question is sensitive, or
          you just are not ready to be seen.
        </p>
        <p>
          <strong>Identify me</strong> when you want a meeting.{" "}
          <strong>Rooms</strong> are named on purpose: classmates help
          classmates, and that help can show up on the Hilbert board. Staff do
          not lurk there.
        </p>
      </>
    ),
  },
  {
    id: "ta",
    kicker: "02 · Teaching assistant",
    title: "The path from a stuck student is a queue, not a pile.",
    body: (
      <>
        <p>
          <strong>Ask Triage</strong> classifies the ask as it comes in.
          You claim it, then <strong>Help Coach</strong> sits with you —
          similar opens, Socratic steps, a draft you still have to own.
        </p>
        <p>
          When the same concept clusters, one shared group meeting can replace
          twenty 1:1s. Same login if you are a student in another course.
        </p>
      </>
    ),
  },
  {
    id: "professor",
    kicker: "03 · Professor",
    title: "You stay the gate for what the class learns.",
    body: (
      <>
        <p>
          Clusters and <strong>review insights</strong> show what the week
          actually confused people — Quiet asks plus Rooms chapters, not a
          vanity dashboard.
        </p>
        <p>
          Approve a FAQ and the Study Agent may say it next time. Sync Canvas
          modules and those names become Rooms chapters. Nothing enters the
          student knowledge base until you say so.
        </p>
      </>
    ),
  },
  {
    id: "join",
    kicker: "The product · one login",
    title: "Role is per course. Sign in as yourself.",
    body: (
      <>
        <p>
          A TA on campus is also a student. One AUI email, memberships from
          Canvas, a workspace that switches when the course does. This is a
          senior capstone for a real office-hours problem — not a chatbot demo.
        </p>
        <p className="oh-land-cta-row">
          <Link className="btn-primary oh-land-signin" to="/login">
            Sign in
          </Link>
          <a className="btn-ghost oh-land-ghost" href="#student">
            Walk the path again
          </a>
        </p>
      </>
    ),
  },
];

function useStoryScroll(progressRef) {
  const [progress, setProgress] = useState(0);

  useEffect(() => {
    let ticking = false;
    const measure = () => {
      const max = document.documentElement.scrollHeight - window.innerHeight;
      const next = max > 0 ? window.scrollY / max : 0;
      progressRef.current = next;
      setProgress(next);
      ticking = false;
    };
    const onScroll = () => {
      if (ticking) return;
      ticking = true;
      requestAnimationFrame(measure);
    };
    measure();
    window.addEventListener("scroll", onScroll, { passive: true });
    window.addEventListener("resize", onScroll);
    return () => {
      window.removeEventListener("scroll", onScroll);
      window.removeEventListener("resize", onScroll);
    };
  }, [progressRef]);

  return progress;
}

export default function LandingPage() {
  const progressRef = useRef(0);
  const [webgl, setWebgl] = useState(true);
  const [reducedMotion, setReducedMotion] = useState(false);
  const progress = useStoryScroll(progressRef);
  const chapter = chapterFromProgress(progress);

  useEffect(() => {
    setWebgl(hasWebGL());
    const media = window.matchMedia("(prefers-reduced-motion: reduce)");
    const sync = () => setReducedMotion(media.matches);
    sync();
    media.addEventListener("change", sync);
    return () => media.removeEventListener("change", sync);
  }, []);

  return (
    <div className={`oh-land ${webgl ? "" : "oh-land-no3d"}`}>
      {webgl ? (
        <Suspense fallback={<div className="oh-land-canvas-fallback" />}>
          <CampusCanvas progressRef={progressRef} reducedMotion={reducedMotion} />
        </Suspense>
      ) : (
        <div className="oh-land-canvas-fallback" />
      )}

      <header className="oh-land-nav">
        <a className="oh-land-brand" href="#hero">
          <img src="/aui-logo.png" alt="Al Akhawayn University" />
          <span>
            OfficeHours
            <small>AUI campus product</small>
          </span>
        </a>
        <nav aria-label="Story">
          <a href="#student" className={chapter === "student" ? "is-on" : ""}>
            Student
          </a>
          <a href="#ta" className={chapter === "ta" ? "is-on" : ""}>
            TA
          </a>
          <a href="#professor" className={chapter === "professor" ? "is-on" : ""}>
            Professor
          </a>
          <Link className="oh-land-nav-cta" to="/login">
            Sign in
          </Link>
        </nav>
      </header>

      <ol className="oh-land-rail" aria-label="Path progress">
        {[
          ["hero", "Start"],
          ["student", "Student"],
          ["ta", "TA"],
          ["professor", "Professor"],
          ["join", "Sign in"],
        ].map(([id, label]) => (
          <li key={id} className={chapter === id ? "is-on" : ""}>
            <a href={`#${id}`}>{label}</a>
          </li>
        ))}
      </ol>

      <main className="oh-land-story">
        {CHAPTERS.map((item) => (
          <section
            key={item.id}
            id={item.id}
            className={`oh-land-chapter ${chapter === item.id ? "is-on" : ""}`}
          >
            <article className="oh-land-card">
              <p className="oh-land-kicker">{item.kicker}</p>
              <h1 className="font-display">{item.title}</h1>
              <div className="oh-land-copy">{item.body}</div>
            </article>
          </section>
        ))}
      </main>
    </div>
  );
}
