const API_BASE = import.meta.env.VITE_API_BASE || "http://127.0.0.1:8000";

/**
 * Ask the student-facing KB agent (approved knowledge only).
 *
 * @param {string} question
 * @returns {Promise<object>} AgentAskResponse
 */
export async function askKbAgent(question) {
  const response = await fetch(`${API_BASE}/agent/ask`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question, top_k: 3 }),
  });

  if (!response.ok) {
    throw new Error(`KB agent request failed: ${response.status}`);
  }

  return response.json();
}
