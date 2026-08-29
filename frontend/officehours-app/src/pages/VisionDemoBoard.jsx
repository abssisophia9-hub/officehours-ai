import { useState } from "react";
import VisionChrome, { VisionCopy } from "../landing/VisionChrome.jsx";

const SLIPS = [
  {
    id: "quiet",
    cls: "quiet",
    pin: "lime",
    kicker: "Quiet ask",
    title: "No name on the board",
    body: "Staff see a request code. The private path when the question is sensitive.",
  },
  {
    id: "identify",
    cls: "identify",
    pin: "pine",
    kicker: "Identify me",
    title: "Sara · CSC 3323",
    body: "You want a meeting. Staff can find you.",
  },
  {
    id: "rooms",
    cls: "rooms",
    pin: "lime",
    kicker: "Rooms",
    title: "Heap vs stack — anyone?",
    body: "Named classmate help. Helpers can show on the Hilbert board.",
  },
  {
    id: "queue",
    cls: "queue",
    pin: "pine",
    kicker: "TA queue",
    title: "Now helping · Alice",
    body: "Ask Triage classified it. Claim → Help Coach → done. Not a pile.",
  },
  {
    id: "gate",
    cls: "gate",
    pin: "lime",
    kicker: "Professor gate",
    title: "Approve for Study Agent",
    body: "Nothing enters the student KB until you stamp it.",
  },
];

export default function VisionDemoBoard() {
  const [open, setOpen] = useState("quiet");
  const active = SLIPS.find((s) => s.id === open) || SLIPS[0];

  return (
    <VisionChrome kicker="Option 1 · The Ask Board — click a slip · scroll for the path">
      <main className="vd-split">
        <VisionCopy option="1" title="Pins and lines, not job postings.">
          <p>
            <span className="vd-drop">A</span>
            UI students do not need another jobs board. They need to see{" "}
            <mark>Quiet ask</mark>, a <mark>TA queue</mark>, and a{" "}
            <em>professor gate</em> in one glance.
          </p>
          <p className="vd-active-read">
            <strong>{active.kicker}:</strong> {active.body}
          </p>
        </VisionCopy>

        <div className="vd-board" aria-label="Office-hours ask board">
          <svg className="vd-board-lines" viewBox="0 0 420 460" aria-hidden="true">
            <path d="M90 90 C 140 140, 180 160, 250 210" />
            <path d="M250 210 C 280 250, 200 300, 120 340" />
            <path d="M120 340 C 200 360, 280 300, 330 390" />
          </svg>
          {SLIPS.map((slip) => (
            <button
              key={slip.id}
              type="button"
              className={`vd-slip vd-slip-${slip.cls} ${open === slip.id ? "is-on" : ""}`}
              onClick={() => setOpen(slip.id)}
            >
              <span className={`vd-pin vd-pin-${slip.pin}`} />
              <span className="vd-slip-kicker">{slip.kicker}</span>
              <span className="vd-slip-title">{slip.title}</span>
            </button>
          ))}
        </div>
      </main>
    </VisionChrome>
  );
}
