import { Link } from "react-router";
import { assignedToProfessor, useProfessorData } from "./ProfessorData.jsx";

const OPEN_WORK = new Set(["open", "claimed", "in_progress"]);

function helpLabel(mode) {
  if (mode === "face_to_face") return "In person";
  if (mode === "online_meeting") return "Online";
  return "Message";
}

function personLabel(request) {
  if (request.anonymous) return "Anonymous";
  return request.student_name || request.student_id || "-";
}

function topicLabel(request) {
  return (request.category || "uncategorized").replaceAll("_", " ");
}

function ageLabel(createdAt) {
  if (!createdAt) return "—";
  const then = new Date(createdAt).getTime();
  if (!Number.isFinite(then)) return "—";
  const mins = Math.max(0, Math.round((Date.now() - then) / 60000));
  if (mins < 60) return `${mins}m`;
  if (mins < 60 * 48) return `${Math.round(mins / 60)}h`;
  return `${Math.round(mins / (60 * 24))}d`;
}

function statusChip(request) {
  const work = String(request.work_status || "open").toLowerCase();
  if (work === "helped") return "Resolved";
  if (work === "in_progress") return "In progress";
  if (work === "claimed") return "Claimed";
  if (request.sensitive) return "Sensitive";
  if ((request.urgency || "").toLowerCase() === "urgent") return "Urgent";
  return "Waiting";
}

function AskTable({ rows, empty, action }) {
  if (!rows.length) {
    return <p className="pf-line">{empty}</p>;
  }
  return (
    <table className="bh-table pf-stack-table pf-desk-table">
      <thead>
        <tr>
          <th>Question</th>
          <th>Topic</th>
          <th>Age</th>
          <th>Status</th>
          <th>Action</th>
        </tr>
      </thead>
      <tbody>
        {rows.map((request) => (
          <tr key={request.id}>
            <td data-label="Question">
              <p className="pf-desk-q">{request.text}</p>
              <p className="pf-meta">
                {personLabel(request)} · {helpLabel(request.help_mode)}
              </p>
            </td>
            <td data-label="Topic">{topicLabel(request)}</td>
            <td data-label="Age">{ageLabel(request.created_at)}</td>
            <td data-label="Status">
              <span className="pf-desk-chip">{statusChip(request)}</span>
            </td>
            <td data-label="Action">{action(request)}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

export default function AsksPage() {
  const { requests, entries, commandCenter, noTa, ready, error } = useProfessorData();

  const assigned = assignedToProfessor(requests);
  const escalations = commandCenter?.escalations || [];
  const urgentIds = new Set(escalations.map((item) => item.request_id));
  const urgentRows = requests.filter(
    (item) => urgentIds.has(item.id) && OPEN_WORK.has(item.work_status || "open"),
  );
  const waitingApproval = (entries || []).filter(
    (entry) => entry.status === "pending_review",
  );

  // apple-design for this screen: Purpose; Agency; Simplicity — not minimalism;
  // Feedback; Familiarity; Wayfinding (6).

  return (
    <div className="pf-page pf-desk">
      <header className="pf-head pf-head-stack">
        <div>
          <p className="pf-kicker">Teaching desk</p>
          <h1>Your desk</h1>
          <p className="pf-line">
            Work queue for this course. Patterns stay on{" "}
            <Link to="/professor/insights">Insights</Link>; files on{" "}
            <Link to="/professor">Material</Link>.
          </p>
        </div>
      </header>
      {/* Applied: Purpose; Agency; Simplicity — not minimalism; Feedback; Familiarity; Wayfinding (6). */}

      <div className="pf-desk-counts" aria-label="Desk counts">
        <article>
          <strong>{assigned.length}</strong>
          <span>Assigned to you</span>
        </article>
        <article>
          <strong>{urgentRows.length}</strong>
          <span>Urgent</span>
        </article>
        <article>
          <strong>{waitingApproval.length}</strong>
          <span>Waiting for approval</span>
        </article>
      </div>

      {error ? (
        <p className="pf-error" role="alert">
          {error}
        </p>
      ) : null}

      <section className="pf-block" aria-label="Assigned to you">
        <h2>Assigned to you</h2>
        {noTa ? (
          <p className="pf-line">This course has no TA, so these asks come to you.</p>
        ) : null}
        {!ready ? <p className="pf-line">Loading asks…</p> : null}
        {ready ? (
          <AskTable
            rows={assigned}
            empty="Nothing assigned to you. Check Urgent or approve pending material."
            action={() => (
              <Link className="pf-desk-action" to="/professor/insights">
                See pattern
              </Link>
            )}
          />
        ) : null}
      </section>

      <section className="pf-block" aria-label="Urgent">
        <h2>Urgent</h2>
        <AskTable
          rows={urgentRows}
          empty="No open urgent or sensitive asks. Keep the queue moving from Insights."
          action={(request) =>
            request.sensitive ? (
              <span className="pf-meta">Keep private</span>
            ) : (
              <Link className="pf-desk-action" to="/professor/team">
                Check team
              </Link>
            )
          }
        />
      </section>

      <section className="pf-block" aria-label="Waiting for approval">
        <h2>Waiting for approval</h2>
        {waitingApproval.length === 0 ? (
          <p className="pf-line">
            No drafts waiting.{" "}
            <Link to="/professor">Open Material</Link> to approve uploads.
          </p>
        ) : (
          <table className="bh-table pf-stack-table pf-desk-table">
            <thead>
              <tr>
                <th>Question</th>
                <th>Topic</th>
                <th>Age</th>
                <th>Status</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {waitingApproval.slice(0, 20).map((entry) => (
                <tr key={entry.id}>
                  <td data-label="Question">
                    <p className="pf-desk-q">{entry.question_text}</p>
                  </td>
                  <td data-label="Topic">
                    {(entry.category || "—").replaceAll("_", " ")}
                  </td>
                  <td data-label="Age">{ageLabel(entry.created_at)}</td>
                  <td data-label="Status">
                    <span className="pf-desk-chip">Pending</span>
                  </td>
                  <td data-label="Action">
                    <Link className="btn-primary pf-btn" to="/professor">
                      Review on Material
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>
    </div>
  );
}
