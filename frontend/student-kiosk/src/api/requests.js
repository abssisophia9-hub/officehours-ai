const API_BASE = import.meta.env.VITE_API_BASE || "http://127.0.0.1:8000";

/**
 * Submit a student request to the backend.
 *
 * @param {{ text: string, anonymous: boolean, studentId?: string }} input
 * @returns {Promise<object>} the created request (RequestOut shape)
 */
export async function submitRequest({ text, anonymous, studentId }) {
  const body = {
    text: text.trim(),
    anonymous,
  };

  if (!anonymous && studentId) {
    body.student_id = studentId.trim();
  }

  const response = await fetch(`${API_BASE}/requests/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });

  if (!response.ok) {
    throw new Error(`Request failed with status ${response.status}`);
  }

  return response.json();
}
