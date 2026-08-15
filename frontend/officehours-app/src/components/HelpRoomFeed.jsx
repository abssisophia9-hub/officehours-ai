import { Link } from "react-router";

export default function HelpRoomFeed({ courseCode }) {
  const name = `r/${String(courseCode || "course").replace(/\s+/g, "")}`;
  return (
    <section id="stuck-room" className="sr-teaser scroll-mt-6">
      <div className="sr-teaser-banner" />
      <div className="sr-teaser-body">
        <p className="sr-kicker">Stuck Room · classmates only</p>
        <h2>{name}</h2>
        <p>
          A course community — not a comment box. Post what you are stuck on, upvote
          “same here,” nest comments, and rank classmates who actually unlocked it.
        </p>
        <Link to="/student/room" className="btn-primary mt-4 inline-flex px-5 py-2.5 text-sm">
          Enter {name}
        </Link>
      </div>
    </section>
  );
}
