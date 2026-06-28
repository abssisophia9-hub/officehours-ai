import {
  formatDateTime,
  getCategoryLabel,
  getClusterLabel,
  getRecommendedAction,
} from "../utils/requests.js";

export default function RequestTable({ requests, activeFilter = "all" }) {
  const isFiltered = activeFilter !== "all";

  return (
    <section className="rounded-3xl border border-slate-200 bg-white shadow-sm">
      <div className="flex flex-col gap-2 border-b border-slate-200 p-6 md:flex-row md:items-end md:justify-between">
        <div>
          <p className="text-sm font-semibold uppercase tracking-wide text-indigo-600">
            Live queue
          </p>
          <h2 className="text-2xl font-black text-slate-950">
            Student requests
          </h2>
        </div>
        <p className="text-sm text-slate-500">
          {isFiltered
            ? "Focused by recommendation lane"
            : "Showing newest backend snapshot from "}
          {!isFiltered && <code>/requests/</code>}
        </p>
      </div>

      {requests.length === 0 ? (
        <div className="p-10 text-center">
          <p className="text-lg font-semibold text-slate-700">
            No student requests yet.
          </p>
          <p className="mt-2 text-sm text-slate-500">
            Submit a test request from the kiosk to populate this dashboard.
          </p>
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-slate-200 text-left text-sm">
            <thead className="bg-slate-50 text-xs uppercase tracking-wide text-slate-500">
              <tr>
                <th className="px-6 py-4 font-bold">Request</th>
                <th className="px-6 py-4 font-bold">Student</th>
                <th className="px-6 py-4 font-bold">Category</th>
                <th className="px-6 py-4 font-bold">Cluster</th>
                <th className="px-6 py-4 font-bold">Recommended action</th>
                <th className="px-6 py-4 font-bold">Submitted</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {requests.map((request) => (
                <tr key={request.id} className="align-top hover:bg-slate-50">
                  <td className="max-w-md px-6 py-5">
                    <p className="text-xs font-bold uppercase text-slate-400">
                      #{request.id}
                    </p>
                    <p className="mt-1 font-medium leading-6 text-slate-900">
                      {request.text}
                    </p>
                  </td>
                  <td className="px-6 py-5 text-slate-600">
                    {request.anonymous
                      ? "Anonymous"
                      : request.student_id || "Identified"}
                  </td>
                  <td className="px-6 py-5">
                    <Badge tone="indigo">{getCategoryLabel(request)}</Badge>
                  </td>
                  <td className="px-6 py-5">
                    <Badge tone="emerald">{getClusterLabel(request)}</Badge>
                  </td>
                  <td className="px-6 py-5 text-slate-700">
                    {getRecommendedAction(request)}
                  </td>
                  <td className="whitespace-nowrap px-6 py-5 text-slate-500">
                    {formatDateTime(request.created_at)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}

function Badge({ children, tone }) {
  const toneClasses = {
    emerald: "bg-emerald-50 text-emerald-700 ring-emerald-200",
    indigo: "bg-indigo-50 text-indigo-700 ring-indigo-200",
  };

  return (
    <span
      className={`inline-flex rounded-full px-3 py-1 text-xs font-bold ring-1 ${toneClasses[tone]}`}
    >
      {children}
    </span>
  );
}
