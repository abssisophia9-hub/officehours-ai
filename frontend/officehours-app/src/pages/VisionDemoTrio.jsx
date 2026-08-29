import { useEffect, useState } from "react";
import VisionChrome, { Person, VisionCopy } from "../landing/VisionChrome.jsx";

const ROLES = [
  {
    id: "student",
    kicker: "01 · Student",
    object: "Quiet ask · Rooms",
    title: "You do not perform in front of the room.",
    body: "Private path to staff, or a named room for classmates. The product starts with the stuck student.",
  },
  {
    id: "ta",
    kicker: "02 · TA",
    object: "Queue · Help Coach",
    title: "A queue, not a pile.",
    body: "Ask Triage routes the card. You claim it. Repeated concepts can become one group meeting.",
  },
  {
    id: "professor",
    kicker: "03 · Professor",
    object: "Insights · KB gate",
    title: "You stay the gate.",
    body: "Review insights from asks + Rooms. Stamp a FAQ before the Study Agent may repeat it.",
  },
];

export default function VisionDemoTrio() {
  const [pinned, setPinned] = useState(null);
  const [fromScroll, setFromScroll] = useState("student");

  useEffect(() => {
    const nodes = [...document.querySelectorAll("[data-vd-role]")];
    const io = new IntersectionObserver(
      (entries) => {
        const on = entries
          .filter((e) => e.isIntersecting)
          .sort((a, b) => b.intersectionRatio - a.intersectionRatio)[0];
        if (on) setFromScroll(on.target.getAttribute("data-vd-role"));
      },
      { threshold: 0.55 },
    );
    nodes.forEach((n) => io.observe(n));
    return () => io.disconnect();
  }, []);

  const currentId = pinned || fromScroll;

  return (
    <VisionChrome kicker="Option 3 · Three people, one picture — scroll to focus · click a person">
      <main className="vd-trio-hero">
        <VisionCopy option="3" title="You see the whole product before you scroll.">
          <p>
            <span className="vd-drop">T</span>
            hree stylized people, three objects. No campus walk. Click to pin a
            role. Scroll to go deeper. Sign in is always in the header.
          </p>
        </VisionCopy>
        <div className="vd-trio-stage">
          {ROLES.map((role) => (
            <div key={role.id} className={`vd-trio-slot ${currentId === role.id ? "is-on" : ""}`}>
              <Person
                kind={role.id}
                label={role.kicker.replace(/^\d+ · /, "")}
                size="lg"
                active={currentId === role.id}
                onClick={() => setPinned(pinned === role.id ? null : role.id)}
              />
              <p className="vd-trio-object">{role.object}</p>
            </div>
          ))}
        </div>
      </main>

      {ROLES.map((role) => (
        <section key={role.id} className="vd-chapter" data-vd-role={role.id} id={role.id}>
          <article className={`vd-card ${currentId === role.id ? "is-on" : ""}`}>
            <p className="vd-kicker">{role.kicker}</p>
            <h2 className="font-display">{role.title}</h2>
            <p>{role.body}</p>
          </article>
        </section>
      ))}
    </VisionChrome>
  );
}
