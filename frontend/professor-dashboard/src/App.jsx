import { Suspense, lazy, useCallback, useEffect, useMemo, useState } from "react";
import { fetchRequests } from "./api/requests.js";
import EscalationFeed from "./components/EscalationFeed.jsx";
import KnowledgeCurationPanel from "./components/KnowledgeCurationPanel.jsx";
import OfficeHoursPanel from "./components/OfficeHoursPanel.jsx";
import OracleIntelligencePanel from "./components/OracleIntelligencePanel.jsx";
import RecommendationBoard from "./components/RecommendationBoard.jsx";
import RequestTable from "./components/RequestTable.jsx";
import StruggleHeatmap from "./components/StruggleHeatmap.jsx";
import SummaryCards from "./components/SummaryCards.jsx";
import { useOfficeHoursSocket } from "./hooks/useOfficeHoursSocket.js";
import {
  getRecommendationKind,
  getRecommendedAction,
} from "./utils/requests.js";

const RequestCharts = lazy(() => import("./components/RequestCharts.jsx"));

export default function App() {
  const [requests, setRequests] = useState([]);
  const [status, setStatus] = useState("loading");
  const [error, setError] = useState("");
  const [lastLoadedAt, setLastLoadedAt] = useState(null);
  const [selectedRecommendationKind, setSelectedRecommendationKind] =
    useState("all");
  const [refreshKey, setRefreshKey] = useState(0);

  const loadRequests = useCallback(async () => {
    setStatus("loading");
    setError("");

    try {
      const data = await fetchRequests();
      setRequests(data);
      setLastLoadedAt(new Date());
      setRefreshKey((value) => value + 1);
      setStatus("success");
    } catch (requestError) {
      setStatus("error");
      setError(requestError.message);
    }
  }, []);

  useEffect(() => {
    loadRequests();
  }, [loadRequests]);

  const { live } = useOfficeHoursSocket((event) => {
    if (
      event.type === "request.created" ||
      event.type === "knowledge.created" ||
      event.type === "knowledge.updated" ||
      event.type === "ta.resolved" ||
      event.type === "escalation"
    ) {
      loadRequests();
    }
  });

  const sortedRequests = useMemo(
    () =>
      [...requests].sort(
        (a, b) => new Date(b.created_at) - new Date(a.created_at),
      ),
    [requests],
  );
  const focusedRequests = useMemo(() => {
    if (selectedRecommendationKind === "all") {
      return sortedRequests;
    }

    return sortedRequests.filter(
      (request) =>
        getRecommendationKind(getRecommendedAction(request)) ===
        selectedRecommendationKind,
    );
  }, [selectedRecommendationKind, sortedRequests]);

  return (
    <div className="aui-shell min-h-full text-aui-ink">
      <header className="px-6 pt-6">
        <div className="mx-auto mb-3 h-1.5 max-w-7xl overflow-hidden rounded-full bg-gradient-to-r from-emerald-400 via-sky-400 to-orange-400 shadow-[0_0_24px_rgba(16,185,129,0.45)]" />
        <div className="glass-header mx-auto flex max-w-7xl flex-col gap-5 rounded-2xl px-6 py-5 lg:flex-row lg:items-center lg:justify-between">
          <div className="flex items-center gap-4">
            <img
              src="/aui-logo.png"
              alt="Al Akhawayn University"
              className="aui-logo"
            />
            <div>
              <p className="text-sm font-semibold uppercase tracking-[0.16em] text-aui-forest">
                OfficeHours AI · AUI
              </p>
              <h1 className="font-display text-3xl font-bold tracking-tight">
                Professor Dashboard
              </h1>
            </div>
          </div>

          <div className="flex flex-col items-start gap-2 sm:flex-row sm:items-center">
            <span
              className={`glass-chip ${live ? "" : "opacity-70"}`}
            >
              <span
                className={`h-2 w-2 rounded-full ${live ? "live-pulse bg-emerald-500" : "bg-slate-400"}`}
              />
              {live ? "Live" : "Reconnecting"}
            </span>
            {lastLoadedAt ? (
              <p className="text-sm text-aui-deep/65">
                Last refreshed {lastLoadedAt.toLocaleTimeString()}
              </p>
            ) : null}
            <button
              type="button"
              onClick={loadRequests}
              className="btn-primary px-5 py-2.5 text-sm"
            >
              Refresh requests
            </button>
          </div>
        </div>
      </header>

      <main className="mx-auto flex max-w-7xl flex-col gap-8 px-6 py-8">
        {status === "error" ? (
          <div className="glass-panel border-red-200/70 bg-red-50/70 p-5 text-red-800">
            <p className="font-bold">Could not load backend requests.</p>
            <p className="mt-1 text-sm">
              {error}. Make sure the FastAPI backend is running and
              `VITE_API_BASE` points to it.
            </p>
          </div>
        ) : null}

        {status === "loading" && requests.length === 0 ? (
          <div className="glass-panel p-8 text-center text-slate-500">
            Loading request queue...
          </div>
        ) : (
          <>
            <SummaryCards requests={sortedRequests} />
            <OracleIntelligencePanel key={`oracle-${refreshKey}`} />
            <div className="grid gap-8 xl:grid-cols-2">
              <StruggleHeatmap key={`heatmap-${refreshKey}`} />
              <EscalationFeed key={`escalations-${refreshKey}`} />
            </div>
            <KnowledgeCurationPanel key={`kb-${refreshKey}`} />
            <div className="grid gap-8 2xl:grid-cols-[minmax(0,1fr)_420px]">
              <div className="space-y-8">
                <RecommendationBoard
                  requests={sortedRequests}
                  selectedKind={selectedRecommendationKind}
                  onSelectedKindChange={setSelectedRecommendationKind}
                />
                <Suspense fallback={<ChartLoadingState />}>
                  <RequestCharts requests={focusedRequests} />
                </Suspense>
                <RequestTable
                  requests={focusedRequests}
                  activeFilter={selectedRecommendationKind}
                />
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
    <div className="glass-panel p-8 text-center text-slate-500">
      Loading charts...
    </div>
  );
}
