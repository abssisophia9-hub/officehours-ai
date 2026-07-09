const API_BASE = import.meta.env.VITE_API_BASE || "http://127.0.0.1:8000";

export async function fetchKnowledgeEntries(status) {
  const query = status ? `?status=${encodeURIComponent(status)}` : "";
  const response = await fetch(`${API_BASE}/knowledge/${query}`);

  if (!response.ok) {
    throw new Error(`Failed to load knowledge entries: ${response.status}`);
  }

  return response.json();
}

export async function updateKnowledgeEntry(entryId, payload) {
  const response = await fetch(`${API_BASE}/knowledge/${entryId}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    throw new Error(`Failed to update knowledge entry: ${response.status}`);
  }

  return response.json();
}

export async function fetchStruggleHeatmap() {
  const response = await fetch(`${API_BASE}/analytics/struggle-heatmap`);

  if (!response.ok) {
    throw new Error(`Failed to load struggle heatmap: ${response.status}`);
  }

  return response.json();
}

export async function fetchEscalations() {
  const response = await fetch(`${API_BASE}/analytics/escalations`);

  if (!response.ok) {
    throw new Error(`Failed to load escalations: ${response.status}`);
  }

  return response.json();
}
