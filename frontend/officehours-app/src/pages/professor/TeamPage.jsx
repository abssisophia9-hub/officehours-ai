import { useProfessorData } from "./ProfessorData.jsx";

export default function TeamPage() {
  const { taLoad, ready, error } = useProfessorData();
  const tas = taLoad?.tas || [];

  return (
    <div className="pf-page">
      <header className="pf-head">
        <h1>Team</h1>
      </header>
      {error ? (
        <p className="pf-error" role="alert">
          {error}
        </p>
      ) : null}
      {!ready ? <p className="pf-line">Loading team…</p> : null}
      {ready && !error && tas.length === 0 ? <p className="pf-line">No TAs. Asks come to you.</p> : null}
      {tas.length > 0 ? (
        <table className="bh-table pf-stack-table">
          <thead>
            <tr>
              <th>Name</th>
              <th>Main asks</th>
              <th>Backup asks</th>
              <th>Open asks</th>
            </tr>
          </thead>
          <tbody>
            {tas.map((ta) => (
              <tr key={ta.user_id}>
                <td data-label="Name">{ta.name}</td>
                <td data-label="Main asks">{ta.primary_assignments}</td>
                <td data-label="Backup asks">{ta.backup_assignments}</td>
                <td data-label="Open asks">{ta.queue_depth}</td>
              </tr>
            ))}
          </tbody>
        </table>
      ) : null}
    </div>
  );
}
