import { useEffect, useRef, useState } from "react";
import { Link } from "react-router";
import RoleFigure, { ROLES } from "./RoleFigure.jsx";
import { SceneAlone, SceneTogether, SceneAnon, SceneDuo, SceneGuide } from "./Scenes.jsx";
import { usePublicConfig } from "../config/PublicConfig.jsx";

const COURSES = [
  {
    code: "CSC 2302",
    title: "Data Structures",
    modules: [
      {
        name: "Hashing",
        ask: "Why do hash collisions happen?",
        room: "Hash collisions on insert — anyone?",
        agent: "A hash table maps a key to a bucket. Collisions are normal; we chain or probe. Approved FAQ + Canvas Module 4.",
      },
      {
        name: "Trees",
        ask: "BST vs heap — which one for Dijkstra?",
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
        ask: "How do I unwind the merge-sort recurrence?",
        room: "Merge sort recurrence — how to unwind it?",
        agent: "T(n) = 2T(n/2) + Θ(n) solves to Θ(n log n). Pulled from the approved FAQ for this course only.",
      },
    ],
  },
];

function Cut({ n, label }) {
  return (
    <div className="oh-cut" aria-hidden="true">
      <strong>{n}</strong>
      <span>{label}</span>
    </div>
  );
}

export default function OpeningTrio({ variant = "live" }) {
  const [pinned, setPinned] = useState(null);
  const [fromScroll, setFromScroll] = useState("student");
  const [courseIdx, setCourseIdx] = useState(0);
  const [moduleIdx, setModuleIdx] = useState(0);
  const [quiet, setQuiet] = useState(true);
  const [stamped, setStamped] = useState(false);
  const [votes, setVotes] = useState(7);
  const [stance, setStance] = useState("none");
  const { demo } = usePublicConfig();
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

  function voteUp() {
    if (stance === "ignore") return;
    setVotes((n) => n + 1);
  }

  return (
    <div className={`oh-open-story oh-open-story-${variant}`}>
      <main className="oh-open-hero oh-block-cream" id="hero">
        <div className="oh-open-copy">
          <p className="oh-open-kicker">Al Akhawayn University · a campus room</p>
          <h1 className="font-display">
            Choose how you get help.{" "}
            <span className="oh-open-mark">Choose how you give it.</span>
          </h1>
          <div className="oh-open-body">
            <p>
              <span className="oh-open-drop">T</span>
              he barrier was never the question. It was being alone with it.
              OfficeHours is classmates, TAs, and professors deciding, every
              time: <mark>human or agent</mark>, <mark>quiet or named</mark>,{" "}
              <mark>help or ignore</mark>.
            </p>
            <p>
              <em>Study Rooms</em> first — peer help rated Stack Overflow-style
              in Hilbert ŵ. The course agent is one door. The community is the
              building. Scroll the chapters.
            </p>
          </div>
        </div>
        <div className="oh-journey" aria-label="From alone with the problem to sharing it">
          <figure className="oh-panel is-dim">
            <SceneAlone />
            <figcaption>
              <strong>2:13 AM — alone with it</strong>
              <span>Same bug for three hours. Closed door. Nobody awake to ask.</span>
            </figcaption>
          </figure>
          <span className="oh-journey-arrow" aria-hidden="true">
            →
          </span>
          <figure className="oh-panel is-lit">
            <SceneTogether />
            <figcaption>
              <strong>2:31 AM — shared</strong>
              <span>She opened a Room. Two classmates were stuck on it too.</span>
            </figcaption>
          </figure>
        </div>
      </main>

      <Cut n="01" label="Choice at every level" />

      <section className="oh-open-choice oh-block-white" id="choice">
        <div className="oh-open-choice-copy">
          <p className="oh-open-kicker">No default path</p>
          <h2 className="font-display">You pick the door. Every time.</h2>
          <p>
            Mutual support only works if walking past is allowed. Collective
            learning only works if the room is optional. The product removes
            the performance — not the decision.
          </p>
        </div>
        <ul className="oh-choice-grid">
          <li>
            <SceneAnon />
            <h3>Quiet or named</h3>
            <p>
              Ask staff as a request code — no name on any board. Or put your
              name on it so help can find you. Same person, her call.
            </p>
          </li>
          <li>
            <SceneDuo />
            <h3>Human and AI, side by side</h3>
            <p>
              A TA drafts your hint while the course agent answers what the
              professor already stamped. Both doors stay open at once.
            </p>
          </li>
          <li>
            <SceneGuide />
            <h3>Staff guide. They don’t gatekeep.</h3>
            <p>
              A professor points review at the real stuck points and stamps
              what’s true. The doorway to classmates never closes.
            </p>
          </li>
        </ul>
      </section>

      <Cut n="02" label="Study Rooms · Hilbert ŵ" />

      <section className="oh-open-rooms oh-block-lime" id="rooms">
        <div className="oh-open-rooms-copy">
          <p className="oh-open-kicker">Peer rating, Stack Overflow-style</p>
          <h2 className="font-display">Classmates help classmates. Quality over volume.</h2>
          <p>
            A Room is named on purpose. You vote. You Express Interest, or you
            keep scrolling. Accept a solution only when it unlocked the stuck
            point. Staff do not lurk here.
          </p>
        </div>

        <div className="oh-open-room-stage">
          <article className={`oh-open-thread${stance === "ignore" ? " is-passed" : ""}`}>
            <button type="button" className="oh-open-vote" onClick={voteUp} disabled={stance === "ignore"}>
              <span aria-hidden="true">▲</span>
              <strong>{votes}</strong>
              <small>ŵ</small>
            </button>
            <div>
              <p className="oh-open-pane-kicker">{course.code} · {module.name}</p>
              <h3>{module.room}</h3>
              <p>
                {stance === "help"
                  ? "You expressed interest. Your name is on this thread — help can find you."
                  : stance === "ignore"
                    ? "You kept walking. The room stays open for someone else."
                    : "Share the stuck point, not the write-up. Help is named. Walking past is allowed."}
              </p>
              <div className="oh-open-thread-actions">
                <button
                  type="button"
                  className={stance === "help" ? "is-on" : ""}
                  onClick={() => setStance(stance === "help" ? "none" : "help")}
                >
                  {stance === "help" ? "Interested" : "Express Interest"}
                </button>
                <button
                  type="button"
                  className={stance === "ignore" ? "is-on" : ""}
                  onClick={() => setStance(stance === "ignore" ? "none" : "ignore")}
                >
                  {stance === "ignore" ? "Passed" : "Ignore"}
                </button>
              </div>
            </div>
          </article>
          <aside className="oh-open-hilbert">
            <p className="oh-open-pane-kicker">Hilbert board</p>
            <ol>
              <li>
                <span>Karim</span>
                <strong>12 ŵ</strong>
              </li>
              <li>
                <span>Sara</span>
                <strong>8 ŵ</strong>
              </li>
              <li>
                <span>Youssef</span>
                <strong>5 ŵ</strong>
              </li>
            </ol>
            <p className="oh-open-fine">Accepted solutions count. Noise does not.</p>
          </aside>
        </div>
      </section>

      <Cut n="03" label="Three seats, one room" />

      <section className="oh-open-trio-sec oh-block-cream" id="people">
        <div>
          <p className="oh-open-kicker">Student · TA · Professor</p>
          <h2 className="font-display">The same person can sit in two seats.</h2>
          <p>
            A TA on campus is also a student in another course. One login, a
            role per course. Click a person to jump to their chapter.
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
      </section>

      <section className="oh-open-desk oh-block-white" id="student" data-oh-role="student">
        <div className="oh-open-desk-head">
          <RoleFigure role="student" size="lg" active onClick={() => selectRole("student")} />
          <div>
            <p className="oh-open-kicker">01 · Student</p>
            <h2 className="font-display">Get help without performing it.</h2>
            <p className="oh-open-lead">
              Quiet ask if the question is sensitive. Identify me for a meeting.
              Rooms if a classmate can unlock it. The agent only if this course
              stamped an answer.
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
          <article className="oh-open-pane">
            <p className="oh-open-pane-kicker">Or a Room</p>
            <p>
              Named classmate help. Vote. Express Interest. Accept a solution.
              You can also ignore the thread and keep your night.
            </p>
          </article>
          <article className="oh-open-pane oh-open-pane-agent">
            <p className="oh-open-pane-kicker">Or the course agent · {course.code}</p>
            <p className="oh-open-chat">“{module.ask}”</p>
            <p className="oh-open-chat is-reply">
              {stamped
                ? module.agent
                : "I don’t have an approved answer in this course yet. Ask a classmate, or a TA."}
            </p>
            <p className="oh-open-fine">One door. Not the building.</p>
          </article>
        </div>
      </section>

      <section className="oh-open-desk oh-block-cream" id="ta" data-oh-role="ta">
        <div className="oh-open-desk-head">
          <RoleFigure role="ta" size="lg" active onClick={() => selectRole("ta")} />
          <div>
            <p className="oh-open-kicker">02 · Teaching assistant</p>
            <h2 className="font-display">Give help without drowning in the pile.</h2>
            <p className="oh-open-lead">
              Students already chose a door. You choose how to answer: claim
              the card, draft with Help Coach, or turn a cluster into one group
              meeting.
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

      <section className="oh-open-desk oh-block-white" id="professor" data-oh-role="professor">
        <div className="oh-open-desk-head">
          <RoleFigure role="professor" size="lg" active onClick={() => selectRole("professor")} />
          <div>
            <p className="oh-open-kicker">03 · Professor</p>
            <h2 className="font-display">A guide with a stamp.</h2>
            <p className="oh-open-lead">
              Review insights show where the class is actually stuck. You point
              the review there and stamp what the course agent may repeat. The
              community never waits on you to help each other.
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
            <p className="oh-open-pane-kicker">The stamp</p>
            <p>{stamped ? "Stamped. The Course Study Agent may say this next time." : "Pending. The agent stays quiet. Rooms stay open."}</p>
            <button type="button" className="oh-open-stamp-btn" onClick={() => setStamped((on) => !on)}>
              {stamped ? "Unstamp (demo)" : "Stamp for Study Agent"}
            </button>
          </article>
        </div>
      </section>

      <Cut n="04" label="Canvas names the chapters" />

      <section className="oh-open-stitch oh-block-cream" id="canvas">
        <div className="oh-open-stitch-copy">
          <p className="oh-open-kicker">Canvas LMS · the course you share</p>
          <h2 className="font-display">The course names the room. People fill it.</h2>
          <p>
            Launch from Canvas or sign in with your AUI email. A synced module
            becomes a Rooms chapter. The Course Study Agent only speaks what
            this professor stamped — never another syllabus, never classmate notes.
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

      <Cut n="05" label="Walk in" />

      <section className="oh-open-close" id="join">
        <div>
          <p className="oh-open-kicker">One login · role per course</p>
          <h2 className="font-display">The room is already open. Walk in.</h2>
          <p>
            Shared stress. Collective learning. Mutual support. Sign in as
            yourself — a TA on campus is also a student. One AUI email. The
            workspace switches when the course does.
          </p>
        </div>
        <p className="oh-open-cta-row">
          <Link className="oh-open-signin" to="/login">
            Sign in
          </Link>
          {demo ? (
            <Link className="oh-open-ghost" to="/canvas-demo">
              Or open from Canvas
            </Link>
          ) : (
            <span className="oh-open-ghost">Or open OfficeHours from your Canvas course</span>
          )}
        </p>
      </section>
    </div>
  );
}
