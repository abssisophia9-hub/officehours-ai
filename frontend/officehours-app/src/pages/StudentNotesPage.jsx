import { Navigate } from "react-router";
import { useAuth } from "../auth/AuthContext.jsx";
import PeerNotesFeed from "../components/PeerNotesFeed.jsx";

export default function StudentNotesPage() {
  const { token, activeCourse } = useAuth();

  if (!activeCourse) return <Navigate to="/" replace />;
  if (activeCourse.role !== "student") {
    return (
      <Navigate
        to={`/${activeCourse.role === "professor" ? "professor" : "ta"}`}
        replace
      />
    );
  }

  const courseLine = [activeCourse.code, activeCourse.title].filter(Boolean).join(" · ");

  return (
    <div className="fade-up">
      <h1 className="sa-course">{courseLine}</h1>
      <h2 className="bh-page-title">Classmate Notes</h2>
      <p className="bh-page-subtitle">
        Share and browse study notes with classmates · {activeCourse.code} — not
        on the Dashboard.
      </p>
      <PeerNotesFeed
        token={token}
        courseId={activeCourse.id}
        courseCode={activeCourse.code}
      />
    </div>
  );
}
