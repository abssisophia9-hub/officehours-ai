import { useEffect, useMemo, useState } from "react";
import { fetchStruggleHeatmap } from "../api/knowledge.js";

export default function StruggleHeatmap() {
  const [data, setData] = useState({ cells: [], total_requests: 0 });
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;
    fetchStruggleHeatmap()
      .then((payload) => {
        if (!cancelled) {
          setData(payload);
        }
      })
      .catch((loadError) => {
        if (!cancelled) {
          setError(loadError.message);
        }
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const { categories, weeks, maxCount, lookup } = useMemo(() => {
    const categorySet = new Set();
    const weekSet = new Set();
    const map = new Map();
    let max = 0;

    for (const cell of data.cells || []) {
      categorySet.add(cell.category);
      weekSet.add(cell.week_start);
      map.set(`${cell.category}|${cell.week_start}`, cell.count);
      max = Math.max(max, cell.count);
    }

    return {
      categories: Array.from(categorySet).sort(),
      weeks: Array.from(weekSet).sort(),
      maxCount: max || 1,
      lookup: map,
    };
  }, [data]);

  function intensity(count) {
    if (!count) {
      return "bg-slate-100 text-slate-400";
    }
    const ratio = count / maxCount;
    if (ratio > 0.75) {
      return "bg-rose-600 text-white";
    }
    if (ratio > 0.5) {
      return "bg-orange-500 text-white";
    }
    if (ratio > 0.25) {
      return "bg-amber-300 text-amber-950";
    }
    return "bg-amber-100 text-amber-900";
  }

  return (
    <section className="glass-panel p-6">
      <div className="mb-5">
        <p className="text-sm font-semibold uppercase tracking-wide text-rose-600">
          Struggle heatmap
        </p>
        <h2 className="text-xl font-bold text-slate-950">
          Weekly topic pressure
        </h2>
        <p className="mt-1 text-sm text-slate-500">
          Aggregated from live requests — spikes signal lecture revisit
          candidates.
        </p>
      </div>

      {error ? (
        <p className="text-sm text-red-600">{error}</p>
      ) : null}

      {categories.length === 0 ? (
        <p className="rounded-2xl bg-slate-50 px-4 py-6 text-center text-sm text-slate-500">
          No request data yet for the heatmap.
        </p>
      ) : (
        <div className="overflow-x-auto">
          <table className="min-w-full border-separate border-spacing-1">
            <thead>
              <tr>
                <th className="px-2 py-1 text-left text-xs font-bold uppercase tracking-wide text-slate-400">
                  Topic
                </th>
                {weeks.map((week) => (
                  <th
                    key={week}
                    className="px-2 py-1 text-center text-xs font-bold text-slate-500"
                  >
                    {week.slice(5)}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {categories.map((category) => (
                <tr key={category}>
                  <td className="whitespace-nowrap px-2 py-1 text-sm font-semibold text-slate-700">
                    {category.replaceAll("_", " ")}
                  </td>
                  {weeks.map((week) => {
                    const count = lookup.get(`${category}|${week}`) || 0;
                    return (
                      <td key={`${category}-${week}`} className="px-1 py-1">
                        <div
                          className={`flex h-10 w-14 items-center justify-center rounded-lg text-sm font-bold ${intensity(count)}`}
                          title={`${category} · week of ${week}: ${count}`}
                        >
                          {count || "·"}
                        </div>
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
          <p className="mt-3 text-xs text-slate-400">
            {data.total_requests} total requests across {weeks.length} week
            {weeks.length === 1 ? "" : "s"}.
          </p>
        </div>
      )}
    </section>
  );
}
