const API_BASE = import.meta.env.VITE_API_BASE || "http://127.0.0.1:8000";

export async function fetchRecommendationDecisions() {
  const response = await fetch(`${API_BASE}/actions/recommendations/`);

  if (!response.ok) {
    throw new Error(`Failed to load decisions: ${response.status}`);
  }

  return response.json();
}

export async function saveRecommendationDecision({ card, status, professorNote }) {
  const response = await fetch(`${API_BASE}/actions/recommendations/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      card_id: card.id,
      action_kind: card.kind,
      action_title: card.action,
      status,
      cluster_id: firstClusterId(card),
      professor_note: professorNote || null,
      request_ids: card.requests.map((request) => request.id),
    }),
  });

  if (!response.ok) {
    throw new Error(`Decision save failed with status ${response.status}`);
  }

  return response.json();
}

export function getCalendarExportUrl(decisionId) {
  return `${API_BASE}/actions/recommendations/${decisionId}/calendar.ics`;
}

function firstClusterId(card) {
  const clusterId = card.requests.find(
    (request) => request.cluster_id !== null && request.cluster_id !== undefined,
  )?.cluster_id;

  return clusterId ?? null;
}
