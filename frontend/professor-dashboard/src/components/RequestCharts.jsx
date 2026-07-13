import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import {
  getCategoryLabel,
  getClusterLabel,
  summarizeBy,
} from "../utils/requests.js";

const COLORS = ["#4f46e5", "#059669", "#d97706", "#dc2626", "#7c3aed"];

export default function RequestCharts({ requests }) {
  const categoryData = summarizeBy(requests, getCategoryLabel);
  const clusterData = summarizeBy(requests, getClusterLabel).slice(0, 8);

  return (
    <section className="grid gap-6 xl:grid-cols-2">
      <article className="glass-panel p-6">
        <div className="mb-5">
          <p className="text-sm font-semibold uppercase tracking-wide text-aui-forest">
            Category mix
          </p>
          <h2 className="text-xl font-bold text-slate-950">
            Request categories
          </h2>
        </div>

        <div className="h-72">
          {categoryData.length > 0 ? (
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={categoryData}
                  dataKey="value"
                  nameKey="name"
                  outerRadius={96}
                  label
                >
                  {categoryData.map((entry, index) => (
                    <Cell
                      key={entry.name}
                      fill={COLORS[index % COLORS.length]}
                    />
                  ))}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          ) : (
            <EmptyChartMessage />
          )}
        </div>
      </article>

      <article className="glass-panel p-6">
        <div className="mb-5">
          <p className="text-sm font-semibold uppercase tracking-wide text-emerald-600">
            Clustering
          </p>
          <h2 className="text-xl font-bold text-slate-950">
            Requests by topic cluster
          </h2>
        </div>

        <div className="h-72">
          {clusterData.length > 0 ? (
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={clusterData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                <XAxis dataKey="name" tick={{ fontSize: 12 }} />
                <YAxis allowDecimals={false} />
                <Tooltip />
                <Bar dataKey="value" fill="#4f46e5" radius={[8, 8, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <EmptyChartMessage />
          )}
        </div>
      </article>
    </section>
  );
}

function EmptyChartMessage() {
  return (
    <div className="flex h-full items-center justify-center rounded-2xl bg-slate-50 text-sm text-slate-500">
      No request data yet.
    </div>
  );
}
