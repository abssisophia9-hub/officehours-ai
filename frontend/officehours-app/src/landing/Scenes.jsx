/**
 * Small CSS-drawn characters and scenes for the opening page.
 * Faceless-but-expressive: posture, marks, and props carry the emotion.
 */

function Mini({ tone = "student", mood = "up", slumped = false, anon = false, arm = false }) {
  const cls = [
    "oh-mini",
    `oh-mini-${tone}`,
    `oh-mood-${mood}`,
    slumped ? "is-slumped" : "",
    anon ? "is-anon" : "",
  ]
    .filter(Boolean)
    .join(" ");
  return (
    <span className={cls}>
      <span className="oh-mini-head">{anon ? <b>?</b> : <span className="oh-mini-face" />}</span>
      {arm ? <span className="oh-mini-arm" /> : null}
      <span className="oh-mini-body" />
    </span>
  );
}

function Bot() {
  return (
    <span className="oh-bot">
      <span className="oh-bot-antenna" />
      <span className="oh-bot-head">
        <span className="oh-bot-eye" />
        <span className="oh-bot-eye" />
      </span>
      <span className="oh-bot-body" />
    </span>
  );
}

/** 2 AM, alone: slumped student, storm scribble, laptop, question marks. */
export function SceneAlone() {
  return (
    <div className="oh-scene oh-scene-alone" aria-hidden="true">
      <svg className="oh-storm" viewBox="0 0 120 40">
        <path
          d="M6 30 Q18 6 30 22 T54 18 T78 24 T102 12"
          fill="none"
          stroke="#5d7268"
          strokeWidth="3"
          strokeLinecap="round"
        />
      </svg>
      <span className="oh-mark oh-mark-q1">?</span>
      <span className="oh-mark oh-mark-q2">?!</span>
      <Mini tone="student" mood="down" slumped />
      <span className="oh-laptop" />
    </div>
  );
}

/** Same student, upright, flanked by two classmates saying "me too". */
export function SceneTogether() {
  return (
    <div className="oh-scene oh-scene-together" aria-hidden="true">
      <span className="oh-bub oh-bub-left">me too</span>
      <span className="oh-bub oh-bub-right">try chaining</span>
      <span className="oh-spark oh-spark-1">✦</span>
      <span className="oh-spark oh-spark-2">✦</span>
      <Mini tone="peer" />
      <Mini tone="student" />
      <Mini tone="peer2" />
    </div>
  );
}

/** Anonymous (dashed silhouette, request code) or named (same student, name chip). */
export function SceneAnon() {
  return (
    <div className="oh-scene oh-scene-choice" aria-hidden="true">
      <span className="oh-mini-wrap">
        <Mini tone="student" anon />
        <span className="oh-chip">Request #204</span>
      </span>
      <span className="oh-vs">or</span>
      <span className="oh-mini-wrap">
        <Mini tone="student" />
        <span className="oh-chip oh-chip-lime">Sara · CSC 2302</span>
      </span>
    </div>
  );
}

/** A human TA and the course agent answering side by side. */
export function SceneDuo() {
  return (
    <div className="oh-scene oh-scene-choice" aria-hidden="true">
      <span className="oh-mini-wrap">
        <Mini tone="ta" />
        <span className="oh-chip">TA · your hint</span>
      </span>
      <span className="oh-vs">and</span>
      <span className="oh-mini-wrap">
        <Bot />
        <span className="oh-chip oh-chip-lime">Agent · stamped FAQ</span>
      </span>
    </div>
  );
}

/** Professor pointing the way along a dotted path to an open, lit doorway. */
export function SceneGuide() {
  return (
    <div className="oh-scene oh-scene-guide" aria-hidden="true">
      <span className="oh-mini-wrap">
        <Mini tone="professor" arm />
        <span className="oh-chip">points the way</span>
      </span>
      <span className="oh-dots">
        <i />
        <i />
        <i />
      </span>
      <span className="oh-mini-wrap">
        <span className="oh-arch" />
        <span className="oh-chip oh-chip-lime">door stays open</span>
      </span>
    </div>
  );
}
