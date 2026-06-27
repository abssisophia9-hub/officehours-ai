import { Suspense, lazy, useEffect, useMemo, useState } from "react";
import { fetchRequests } from "./api/requests.js";
import OfficeHoursPanel from "./components/OfficeHoursPanel.jsx";
import RequestTable from "./components/RequestTable.jsx";
import SummaryCards from "./components/SummaryCards.jsx";

const RequestCharts = lazy(() => import("./components/RequestCharts.jsx"));

export default function App() {
  const [requests, setRequests] = useState([]);
  const [status, setStatus] = useState("loading");
  const [error, setError] = useState("");
  const [lastLoadedAt, setLastLoadedAt] = useState(null);

  async function loadRequests() {
    setStatus("loading");
    setError("");

    try {
      const data = await fetchRequests();
      setRequests(data);
      setLastLoadedAt(new Date());
      setStatus("success");
    } catch (requestError) {
      setStatus("error");
      setError(requestError.message);
    }
  }

  useEffect(() => {
    loadRequests();
  }, []);

  const sortedRequests = useMemo(
    () =>
      [...requests].sort(
        (a, b) => new Date(b.created_at) - new Date(a.created_at),
      ),
    [requests],
  );

  return (
    <div className="min-h-full bg-slate-100 text-slate-950">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-7xl flex-col gap-5 px-6 py-6 lg:flex-row lg:items-center lg:justify-between">
          <div className="flex items-center gap-4">
            <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-indigo-600 text-lg font-black text-white shadow-lg shadow-indigo-200">
              OH
            </div>
            <div>
              <p className="text-sm font-semibold uppercase tracking-wide text-indigo-600">
                OfficeHours AI
              </p>
              <h1 className="text-3xl font-black tracking-tight">
                Professor Dashboard
              </h1>
            </div>
          </div>

          <div className="flex flex-col items-start gap-2 sm:flex-row sm:items-center">
            {lastLoadedAt ? (
              <p className="text-sm text-slate-500">
                Last refreshed {lastLoadedAt.toLocaleTimeString()}
              </p>
            ) : null}
            <button
              type="button"
              onClick={loadRequests}
              className="rounded-full bg-slate-950 px-5 py-2.5 text-sm font-bold text-white shadow-sm hover:bg-slate-800"
            >
              Refresh requests
            </button>
          </div>
        </div>
      </header>

      <main className="mx-auto flex max-w-7xl flex-col gap-8 px-6 py-8">
        {status === "error" ? (
          <div className="rounded-3xl border border-red-200 bg-red-50 p-5 text-red-800">
            <p className="font-bold">Could not load backend requests.</p>
            <p className="mt-1 text-sm">
              {error}. Make sure the FastAPI backend is running and
              `VITE_API_BASE` points to it.
            </p>
          </div>
        ) : null}

        {status === "loading" && requests.length === 0 ? (
          <div className="rounded-3xl border border-slate-200 bg-white p-8 text-center text-slate-500">
            Loading request queue...
          </div>
        ) : (
          <>
            <SummaryCards requests={sortedRequests} />
            <div className="grid gap-8 2xl:grid-cols-[minmax(0,1fr)_420px]">
              <div className="space-y-8">
                <Suspense fallback={<ChartLoadingState />}>
                  <RequestCharts requests={sortedRequests} />
                </Suspense>
                <RequestTable requests={sortedRequests} />
              </div>
              <OfficeHoursPanel />
            </div>
          </>
        )}
      </main>
    </div>
  );
}

function ChartLoadingState() {
  return (
    <div className="rounded-3xl border border-slate-200 bg-white p-8 text-center text-slate-500 shadow-sm">
      Loading charts...
    </div>
  );
}
