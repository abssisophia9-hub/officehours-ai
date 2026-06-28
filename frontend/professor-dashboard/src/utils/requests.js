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

export function getRecommendationKind(action) {
  const normalizedAction = action.toLowerCase();

  if (normalizedAction.includes("group")) {
    return "group_session";
  }
  if (normalizedAction.includes("faq")) {
    return "faq";
  }
  if (normalizedAction.includes("one-to-one") || normalizedAction.includes("1:1")) {
    return "one_to_one";
  }
  if (normalizedAction.includes("ta") || normalizedAction.includes("project")) {
    return "ta_support";
  }
  if (
    normalizedAction.includes("admin") ||
    normalizedAction.includes("grading") ||
    normalizedAction.includes("accommodation") ||
    normalizedAction.includes("integrity")
  ) {
    return "admin_route";
  }

  return "manual_review";
}

export function buildRecommendationCards(requests) {
  const cardsByKey = new Map();

  for (const request of requests) {
    const action = getRecommendedAction(request);
    const kind = getRecommendationKind(action);
    const clusterKey =
      request.cluster_id === null || request.cluster_id === undefined
        ? "unclustered"
        : `cluster-${request.cluster_id}`;
    const key = `${kind}:${action}:${clusterKey}`;

    if (!cardsByKey.has(key)) {
      cardsByKey.set(key, {
        id: key,
        kind,
        action,
        clusterLabel: getClusterLabel(request),
        category: getCategoryLabel(request),
        requests: [],
      });
    }

    cardsByKey.get(key).requests.push(request);
  }

  return Array.from(cardsByKey.values())
    .map((card) => ({
      ...card,
      priority: recommendationPriority(card),
      newestAt: Math.max(
        ...card.requests.map((request) => new Date(request.created_at).getTime()),
      ),
    }))
    .sort((a, b) => b.priority - a.priority || b.newestAt - a.newestAt);
}

function recommendationPriority(card) {
  const kindScores = {
    one_to_one: 60,
    admin_route: 50,
    group_session: 40,
    ta_support: 30,
    faq: 20,
    manual_review: 10,
  };

  return (kindScores[card.kind] || 0) + card.requests.length;
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
