import { useState } from "react";
import { api } from "../../api/client.js";
import { useAuth } from "../../auth/AuthContext.jsx";
import { assignedToProfessor, useProfessorData } from "./ProfessorData.jsx";

function helpLabel(mode) {
  if (mode === "face_to_face") return "In person";
  if (mode === "online_meeting") return "Online";
  return "Message";
}

function personLabel(request) {
  if (request.anonymous) return "Anonymous";
  return request.student_name || request.student_id || "—";
}

export default function AsksPage() {
  const { token } = useAuth();
  const { requests, entries, commandCenter, noTa, ready, error, setError, reload } = useProfessorData();
  const [busyId, setBusyId] = useState("");
  const [approvedNotes, setApprovedNotes] = useState([]);

  const assigned = assignedToProfessor(requests);
  const escalations = commandCenter?.escalations || [];
  const drafts = entries.filter(
    (entry) => entry.status === "pending_review" && entry.entry_kind !== "course_material",
  );
  const recent = requests.slice(0, 12);

  async function approveDraft(entry) {
    setBusyId(String(entry.id));
    setError("");
    try {
      await api(`/knowledge/${entry.id}`, {
        method: "PATCH",
        token,
        body: { status: "approved" },
      });
      setApprovedNotes((prev) => [
        ...prev,
        {
          id: entry.id,
          text: entry.question_text,
        },
      ]);
      await reload();
    } catch (err) {
      setError(err.message || "Could not approve that answer.");
    } finally {
      setBusyId("");
    }
  }

  return (
    <div className="pf-page">
      <header className="pf-head">
        <h1>Asks</h1>
      </header>
      {error ? (
        <p className="pf-error" role="alert">
          {error}
        </p>
      ) : null}

      <section className="pf-block" aria-label="Assigned to you">
        <h2>Assigned to you</h2>
        {noTa ? <p className="pf-line">This course has no TA, so these asks come to you.</p> : null}
        {!ready ? <p className="pf-line">Loading asks…</p> : null}
        {ready && !error && assigned.length === 0 ? (
          <p className="pf-line">Nothing needs you right now.</p>
        ) : null}
        {assigned.length > 0 ? (
          <ul className="pf-ask-list">
            {assigned.map((request) => (
              <li key={request.id}>
                <p className="pf-ask-title">{request.text}</p>
                <p className="pf-meta">
                  {personLabel(request)}
                  {request.sensitive ? " · Sensitive" : ""}
                  {request.urgency ? ` · ${request.urgency}` : ""}
                </p>
              </li>
            ))}
          </ul>
        ) : null}
      </section>

      {escalations.length > 0 ? (
        <section className="pf-block" aria-label="Urgent and sensitive">
          <h2>Urgent and sensitive</h2>
          <ul className="pf-ask-list">
            {escalations.map((item) => (
              <li key={item.request_id}>
                <p className="pf-ask-title">{item.text}</p>
                <p className="pf-meta">
                  {item.sensitive ? "Sensitive" : "Urgent"}
                  {item.urgency ? ` · ${item.urgency}` : ""}
                  {item.reason ? ` · ${item.reason}` : ""}
                </p>
              </li>
            ))}
          </ul>
        </section>
      ) : null}

      <section className="pf-block" aria-label="Recent asks">
        <h2>Recent asks</h2>
        {ready && recent.length === 0 ? <p className="pf-line">No asks yet.</p> : null}
        {recent.length > 0 ? (
          <table className="bh-table pf-stack-table">
            <thead>
              <tr>
                <th>Question</th>
                <th>From</th>
                <th>Help</th>
                <th>Topic</th>
                <th>Flags</th>
              </tr>
            </thead>
            <tbody>
              {recent.map((request) => (
                <tr key={request.id}>
                  <td data-label="Question">{request.text}</td>
                  <td data-label="From">{personLabel(request)}</td>
                  <td data-label="Help">{helpLabel(request.help_mode)}</td>
                  <td data-label="Topic">{(request.category || "—").replaceAll("_", " ")}</td>
                  <td data-label="Flags">
                    {request.sensitive ? "Sensitive" : request.anonymous ? "Anonymous" : "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : null}
      </section>

      {drafts.length > 0 || approvedNotes.length > 0 ? (
        <section className="pf-block" aria-label="Suggested answers">
          <h2>Suggested answers</h2>
          <p className="pf-line">The study agent does not use these.</p>
          <ul className="pf-ask-list">
            {drafts.map((entry) => (
              <li key={entry.id}>
                <p className="pf-ask-title">{entry.question_text}</p>
                <p className="pf-chunk-text">{entry.answer_draft}</p>
                <button
                  type="button"
                  className="pf-approve"
                  disabled={busyId === String(entry.id)}
                  onClick={() => approveDraft(entry)}
                >
                  Approve
                </button>
              </li>
            ))}
            {approvedNotes
              .filter((item) => !drafts.some((entry) => entry.id === item.id))
              .map((item) => (
                <li key={`done-${item.id}`}>
                  <p className="pf-ask-title">{item.text}</p>
                  <p className="pf-note" role="status">
                    Approved. The study agent does not use these.
                  </p>
                </li>
              ))}
          </ul>
        </section>
      ) : null}
    </div>
  );
}
