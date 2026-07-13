const API_BASE = import.meta.env.VITE_API_BASE || "http://127.0.0.1:8000";

/**
 * Submit a student request to the backend.
 *
 * @returns {Promise<object>} the created request (RequestOut + oracle)
 */
export async function submitRequest({
  text,
  anonymous,
  studentId,
  studentName,
  course,
  codeSnippet,
}) {
  const body = {
    text: text.trim(),
    anonymous,
  };

  if (!anonymous && studentId) {
    body.student_id = studentId.trim();
  }
  if (studentName?.trim()) {
    body.student_name = studentName.trim();
  }
  if (course?.trim()) {
    body.course = course.trim();
  }
  if (codeSnippet?.trim()) {
    body.code_snippet = codeSnippet.trim();
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

/**
 * Add a follow-up message to an existing request.
 */
export async function addFollowUp(requestId, { message, authorRole, authorName }) {
  const response = await fetch(`${API_BASE}/requests/${requestId}/followups`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      message: message.trim(),
      author_role: authorRole,
      author_name: authorName,
    }),
  });

  if (!response.ok) {
    throw new Error(`Follow-up failed with status ${response.status}`);
  }

  return response.json();
}

/**
 * Fetch a request including follow-ups.
 */
export async function getRequest(requestId) {
  const response = await fetch(`${API_BASE}/requests/${requestId}`);
  if (!response.ok) {
    throw new Error(`Request lookup failed with status ${response.status}`);
  }
  return response.json();
}
