import { useState } from "react";
import { Link } from "react-router";
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
  const { requests, commandCenter, noTa, ready, error } = useProfessorData();
  const [showRecent, setShowRecent] = useState(false);

  const assigned = assignedToProfessor(requests);
  const escalations = commandCenter?.escalations || [];
  const recent = requests.slice(0, 12);

  return (
    <div className="pf-page">
      <header className="pf-head pf-head-stack">
        <div>
          <p className="pf-kicker">Teaching desk</p>
          <h1>Your desk</h1>
          <p className="pf-line">
            Assigned and urgent asks first. Patterns across the class live on{" "}
            <Link to="/professor/insights">Insights</Link>; file approvals live on{" "}
            <Link to="/professor">Material</Link>.
          </p>
        </div>
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
        <button
          type="button"
          className="pf-quiet"
          aria-expanded={showRecent}
          onClick={() => setShowRecent((open) => !open)}
        >
          {showRecent ? "Hide recent asks" : "Show recent asks"}
        </button>
        {showRecent ? (
          <>
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
          </>
        ) : null}
      </section>
    </div>
  );
}
