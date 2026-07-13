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
