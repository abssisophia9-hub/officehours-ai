const API_BASE = import.meta.env.VITE_API_BASE || "http://127.0.0.1:8000";

export async function fetchTaQueue() {
  const response = await fetch(`${API_BASE}/ta/queue/`);
  if (!response.ok) {
    throw new Error(`Failed to load TA queue: ${response.status}`);
  }
  return response.json();
}

export async function resolveTaItem(payload) {
  const response = await fetch(`${API_BASE}/ta/resolve/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    throw new Error(`Failed to resolve request: ${response.status}`);
  }
  return response.json();
}
