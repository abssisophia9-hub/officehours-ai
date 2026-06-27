import { getRecommendedAction } from "../utils/requests.js";

export default function SummaryCards({ requests }) {
  const needsReview = requests.filter(
    (request) => !request.recommended_action,
  ).length;
  const uniqueClusters = new Set(
    requests
      .map((request) => request.cluster_id)
      .filter((clusterId) => clusterId !== null && clusterId !== undefined),
  ).size;
  const groupSessionCount = requests.filter((request) =>
    getRecommendedAction(request).toLowerCase().includes("group"),
  ).length;

  const cards = [
    {
      label: "Total requests",
      value: requests.length,
      detail: "Questions submitted through the kiosk",
    },
    {
      label: "Need review",
      value: needsReview,
      detail: "No AI recommendation yet",
    },
    {
      label: "Active clusters",
      value: uniqueClusters,
      detail: "Grouped topics from AI clustering",
    },
    {
      label: "Group-session candidates",
      value: groupSessionCount,
      detail: "Recommended action mentions group help",
    },
  ];

  return (
    <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
      {cards.map((card) => (
        <article
          key={card.label}
          className="rounded-3xl border border-slate-200 bg-white p-5 shadow-sm"
        >
          <p className="text-sm font-medium text-slate-500">{card.label}</p>
          <p className="mt-3 text-4xl font-black tracking-tight text-slate-950">
            {card.value}
          </p>
          <p className="mt-2 text-sm text-slate-500">{card.detail}</p>
        </article>
      ))}
    </section>
  );
}
