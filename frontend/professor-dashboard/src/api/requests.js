const API_BASE = import.meta.env.VITE_API_BASE || "http://127.0.0.1:8000";

/**
 * Fetch student requests for dashboard triage.
 *
 * @returns {Promise<Array<object>>} list of RequestOut objects from the backend
 */
export async function fetchRequests() {
  const response = await fetch(`${API_BASE}/requests/`);

  if (!response.ok) {
    throw new Error(`Failed to load requests: ${response.status}`);
  }

  return response.json();
}
