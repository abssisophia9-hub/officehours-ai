import { useEffect, useRef, useState } from "react";
import { Link } from "react-router";
import RoleFigure, { ROLES } from "./RoleFigure.jsx";

const COURSES = [
  {
    code: "CSC 2302",
    title: "Data Structures",
    modules: [
      {
        name: "Hashing",
        room: "Hash collisions on insert — anyone?",
        agent: "A hash table maps a key to a bucket. Collisions are normal; we chain or probe. Approved FAQ + Canvas Module 4.",
      },
      {
        name: "Trees",
        room: "BST vs heap — which one for Dijkstra?",
        agent: "A BST orders by key. A heap is a priority queue. The course agent only says this because the professor stamped it.",
      },
    ],
  },
  {
    code: "CSC 3323",
    title: "Analysis of Algorithms",
    modules: [
      {
        name: "Divide & Conquer",
        room: "Merge sort recurrence — how to unwind it?",
        agent: "T(n) = 2T(n/2) + Θ(n) solves to Θ(n log n). Pulled from the approved FAQ for this course only.",
      },
    ],
  },
];

export default function OpeningTrio({ variant = "live" }) {
  const [pinned, setPinned] = useState(null);
  const [fromScroll, setFromScroll] = useState("student");
  const [courseIdx, setCourseIdx] = useState(0);
  const [moduleIdx, setModuleIdx] = useState(0);
  const [quiet, setQuiet] = useState(true);
  const [stamped, setStamped] = useState(false);
  const ignoreObserver = useRef(false);
  const currentId = pinned || fromScroll;
  const course = COURSES[courseIdx];
  const module = course.modules[moduleIdx];

  useEffect(() => {
    const nodes = [...document.querySelectorAll("[data-oh-role]")];
    if (!nodes.length) return undefined;
    const io = new IntersectionObserver(
      (entries) => {
        if (ignoreObserver.current) return;
        const on = entries
          .filter((entry) => entry.isIntersecting)
          .sort((a, b) => b.intersectionRatio - a.intersectionRatio)[0];
        if (!on) return;
        setFromScroll(on.target.getAttribute("data-oh-role"));
        setPinned(null);
      },
      { threshold: [0.4, 0.7], rootMargin: "-20% 0px -40% 0px" },
    );
    nodes.forEach((node) => io.observe(node));
    return () => io.disconnect();
  }, []);

  function selectRole(id) {
    ignoreObserver.current = true;
    setPinned(id);
    setFromScroll(id);
    document.getElementById(id)?.scrollIntoView({ behavior: "smooth", block: "start" });
    window.setTimeout(() => {
      ignoreObserver.current = false;
    }, 900);
  }

  function pickCourse(index) {
    setCourseIdx(index);
    setModuleIdx(0);
    setStamped(false);
  }

  return (
    <div className={`oh-open-story oh-open-story-${variant}`}>
      <main className="oh-open-hero" id="hero">
        <div className="oh-open-copy">
          <p className="oh-open-kicker">Al Akhawayn University · Linked to Canvas</p>
          <h1 className="font-display">
            Each course has its own agent.{" "}
            <span className="oh-open-mark">Staff stay the humans.</span>
          </h1>
          <div className="oh-open-body">
            <p>
              <span className="oh-open-drop">O</span>
              fficeHours opens from Canvas. Modules become Rooms chapters. A{" "}
              <mark>Course Study Agent</mark> answers only what that course’s
              professor stamped — never another syllabus, never classmate notes.
            </p>
            <p>
              The three people are the product: a stuck student, a TA with{" "}
              <mark>Ask Triage</mark> and Help Coach, a professor who keeps the{" "}
              <em>KB gate</em>. Click a person. Scroll the rest.
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

      <section className="oh-open-stitch" id="canvas">
        <div className="oh-open-stitch-copy">
          <p className="oh-open-kicker">Canvas LMS · one course at a time</p>
          <h2 className="font-display">The course you opened is the world the agent sees.</h2>
          <p>
            Launch from Canvas or sign in with your AUI email. Memberships decide
            your role. Syncing a module does two things at once: it names a Rooms
            chapter, and it feeds the Study Agent — still behind the professor stamp.
          </p>
          <div className="oh-open-course-switch" role="tablist" aria-label="Demo courses">
            {COURSES.map((item, index) => (
              <button
                key={item.code}
                type="button"
                role="tab"
                aria-selected={courseIdx === index}
                className={courseIdx === index ? "is-on" : ""}
                onClick={() => pickCourse(index)}
              >
                {item.code}
                <small>{item.title}</small>
              </button>
            ))}
          </div>
        </div>

        <div className="oh-open-loom">
          <div className="oh-open-lms">
            <p className="oh-open-loom-label">From Canvas</p>
            <p className="oh-open-loom-course">{course.code}</p>
            <ul>
              {course.modules.map((item, index) => (
                <li key={item.name}>
                  <button
                    type="button"
                    className={moduleIdx === index ? "is-on" : ""}
                    onClick={() => {
                      setModuleIdx(index);
                      setStamped(false);
                    }}
                  >
                    {item.name}
                  </button>
                </li>
              ))}
            </ul>
          </div>
          <p className="oh-open-loom-split" aria-hidden="true">
            becomes
          </p>
          <div className="oh-open-loom-out">
            <article>
              <p className="oh-open-loom-label">Rooms chapter</p>
              <h3>{module.name}</h3>
              <p>{module.room}</p>
            </article>
            <article>
              <p className="oh-open-loom-label">Course Study Agent</p>
              <h3>{course.code} only</h3>
              <p>{stamped ? module.agent : "Waiting on the professor stamp. The agent does not guess."}</p>
            </article>
          </div>
        </div>
      </section>

      <section className="oh-open-desk" id="student" data-oh-role="student">
        <div className="oh-open-desk-head">
          <RoleFigure role="student" size="lg" active onClick={() => selectRole("student")} />
          <div>
            <p className="oh-open-kicker">01 · Student</p>
            <h2 className="font-display">You do not perform in front of the room.</h2>
            <p className="oh-open-lead">
              Quiet ask or Identify me. Rooms for classmates. A Study Agent that
              belongs to this course — not a campus-wide chatbot.
            </p>
          </div>
        </div>
        <div className="oh-open-desk-grid">
          <article className="oh-open-pane">
            <div className="oh-open-toggle">
              <button type="button" className={quiet ? "is-on" : ""} onClick={() => setQuiet(true)}>
                Quiet ask
              </button>
              <button type="button" className={quiet ? "" : "is-on"} onClick={() => setQuiet(false)}>
                Identify me
              </button>
            </div>
            <p className="oh-open-pane-kicker">{quiet ? "Staff see a request code" : "Sara · CSC 2302"}</p>
            <p>
              {quiet
                ? "No name on a public board. The private path when the question is sensitive, or you are not ready to be seen."
                : "You want a meeting — message, face-to-face, or online. Staff can find you."}
            </p>
          </article>
          <article className="oh-open-pane oh-open-pane-agent">
            <p className="oh-open-pane-kicker">Course Study Agent · {course.code}</p>
            <p className="oh-open-chat">“Why do hash collisions happen?”</p>
            <p className="oh-open-chat is-reply">
              {stamped
                ? module.agent
                : "I don’t have an approved answer in this course yet. Ask a TA, or open a Room."}
            </p>
            <p className="oh-open-fine">Classmate notes never train this agent.</p>
          </article>
          <article className="oh-open-pane">
            <p className="oh-open-pane-kicker">Rooms · Hilbert ŵ</p>
            <p>
              Named classmate help. Express Interest. Accept a solution. Quality
              over volume on the leaderboard. Staff do not lurk here.
            </p>
          </article>
        </div>
      </section>

      <section className="oh-open-desk" id="ta" data-oh-role="ta">
        <div className="oh-open-desk-head">
          <RoleFigure role="ta" size="lg" active onClick={() => selectRole("ta")} />
          <div>
            <p className="oh-open-kicker">02 · Teaching assistant</p>
            <h2 className="font-display">A queue, not a pile.</h2>
            <p className="oh-open-lead">
              Ask Triage runs Analyzer, Matcher, and Synthesizer on the way in.
              You claim the card. Help Coach sits with you — it never publishes
              to the Study Agent.
            </p>
          </div>
        </div>
        <div className="oh-open-desk-grid oh-open-desk-grid-2">
          <article className="oh-open-pane">
            <p className="oh-open-pane-kicker">Ask Triage</p>
            <ul className="oh-open-triage">
              <li>
                <strong>Analyzer</strong> Hashing · medium
              </li>
              <li>
                <strong>Matcher</strong> Alice primary · Karim backup
              </li>
              <li>
                <strong>Synthesizer</strong> Hint drafted — you still own the reply
              </li>
            </ul>
          </article>
          <article className="oh-open-pane">
            <p className="oh-open-pane-kicker">Help Coach · dual-TA load</p>
            <p>
              Similar open asks, Socratic steps, a draft you can rewrite. Same
              concept twice? Propose one group meeting. When you are done, send
              the teaching note to the professor’s gate.
            </p>
          </article>
        </div>
      </section>

      <section className="oh-open-desk" id="professor" data-oh-role="professor">
        <div className="oh-open-desk-head">
          <RoleFigure role="professor" size="lg" active onClick={() => selectRole("professor")} />
          <div>
            <p className="oh-open-kicker">03 · Professor</p>
            <h2 className="font-display">You stay the gate.</h2>
            <p className="oh-open-lead">
              Review insights mix Quiet asks and Rooms chapters. Sync Canvas
              materials. Nothing the student agent says is yours until you stamp it.
            </p>
          </div>
        </div>
        <div className="oh-open-desk-grid oh-open-desk-grid-2">
          <article className="oh-open-pane">
            <p className="oh-open-pane-kicker">Review insights · {module.name}</p>
            <p>
              The week confused people on {module.name.toLowerCase()}. Emphasize
              in review, or draft a FAQ for the next cohort.
            </p>
          </article>
          <article className="oh-open-pane">
            <p className="oh-open-pane-kicker">KB gate</p>
            <p>{stamped ? "Stamped. The Course Study Agent may say this next time." : "Pending. The agent stays quiet."}</p>
            <button type="button" className="oh-open-stamp-btn" onClick={() => setStamped((on) => !on)}>
              {stamped ? "Unstamp (demo)" : "Stamp for Study Agent"}
            </button>
          </article>
        </div>
      </section>

      <section className="oh-open-close" id="join">
        <div>
          <p className="oh-open-kicker">One login · role per course</p>
          <h2 className="font-display">Open from Canvas, or sign in as yourself.</h2>
          <p>
            A TA on campus is also a student. One AUI email. The workspace
            switches when the course does. The agent switches with it.
          </p>
        </div>
        <p className="oh-open-cta-row">
          <Link className="oh-open-signin" to="/login">
            Sign in
          </Link>
          <Link className="oh-open-ghost" to="/canvas-demo">
            See the Canvas launch
          </Link>
        </p>
      </section>
    </div>
  );
}
