const API_BASE = import.meta.env.VITE_API_BASE || "http://127.0.0.1:8000";

export async function fetchRequestStatus(requestCode) {
  const normalizedCode = String(requestCode).trim().replace(/^#/, "");
  const response = await fetch(`${API_BASE}/requests/${normalizedCode}/status`);

  if (response.status === 404) {
    throw new Error("We couldn't find that request code. Double-check the number from your confirmation screen.");
  }

  if (!response.ok) {
    throw new Error(`Status lookup failed with status ${response.status}`);
  }

  return response.json();
}
