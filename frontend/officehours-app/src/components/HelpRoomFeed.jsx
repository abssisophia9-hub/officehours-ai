import { Link } from "react-router";

export default function HelpRoomFeed({ courseCode }) {
  const name = `r/${String(courseCode || "course").replace(/\s+/g, "")}`;
  return (
    <section id="stuck-room" className="sr-teaser scroll-mt-6">
      <div className="sr-teaser-banner" />
      <div className="sr-teaser-body">
        <p className="sr-kicker">AUI Rooms · classmates only</p>
        <h2>{name}</h2>
        <p>
          Stack Overflow for this course: Problem / Discussion / Article rooms,
          chapter fields, Express Interest, and a Hilbert-weighted classmate
          leaderboard.
        </p>
        <Link to="/student/room" className="btn-primary mt-4 inline-flex px-5 py-2.5 text-sm">
          Enter {name}
        </Link>
      </div>
    </section>
  );
}
