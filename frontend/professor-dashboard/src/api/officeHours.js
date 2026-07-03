const API_BASE = import.meta.env.VITE_API_BASE || "http://127.0.0.1:8000";

export async function fetchOfficeHours() {
  const response = await fetch(`${API_BASE}/office-hours/`);

  if (!response.ok) {
    throw new Error(`Office hours fetch failed with status ${response.status}`);
  }

  return response.json();
}

export async function createOfficeHoursWindow(window) {
  const response = await fetch(`${API_BASE}/office-hours/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(window),
  });

  if (!response.ok) {
    throw new Error(`Office hours create failed with status ${response.status}`);
  }

  return response.json();
}

export async function deleteOfficeHoursWindow(windowId) {
  const response = await fetch(`${API_BASE}/office-hours/${windowId}`, {
    method: "DELETE",
  });

  if (!response.ok) {
    throw new Error(`Office hours delete failed with status ${response.status}`);
  }
}
