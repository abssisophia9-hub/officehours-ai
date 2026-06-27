export function formatDateTime(value) {
  if (!value) {
    return "Unknown time";
  }

  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

export function getCategoryLabel(request) {
  return request.category || "Uncategorized";
}

export function getClusterLabel(request) {
  return request.cluster_id === null || request.cluster_id === undefined
    ? "Unclustered"
    : `Cluster ${request.cluster_id}`;
}

export function getRecommendedAction(request) {
  return request.recommended_action || "Review manually";
}

export function summarizeBy(items, getKey) {
  const totals = new Map();

  for (const item of items) {
    const key = getKey(item);
    totals.set(key, (totals.get(key) || 0) + 1);
  }

  return Array.from(totals, ([name, value]) => ({ name, value })).sort(
    (a, b) => b.value - a.value || a.name.localeCompare(b.name),
  );
}
