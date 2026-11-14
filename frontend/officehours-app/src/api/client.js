const API_BASE = import.meta.env.VITE_API_BASE || "http://127.0.0.1:8000";

const GENERIC_REQUEST_ERROR = "Something went wrong. Please try again.";
const GENERIC_UPLOAD_ERROR = "Upload failed. Please try again.";

function userFacingError(detail, fallback) {
  if (typeof detail === "string") {
    const trimmed = detail.trim();
    // Short plain messages from the API are safe to show; skip JSON/HTML dumps.
    if (
      trimmed &&
      trimmed.length <= 160 &&
      !trimmed.startsWith("{") &&
      !trimmed.startsWith("[") &&
      !trimmed.startsWith("<")
    ) {
      return trimmed;
    }
  }
  return fallback;
}

export async function api(path, { method = "GET", token, body } = {}) {
  const headers = { Accept: "application/json" };
  if (body !== undefined) {
    headers["Content-Type"] = "application/json";
  }
  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }
  const response = await fetch(`${API_BASE}${path}`, {
    method,
    headers,
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });
  const text = await response.text();
  let data = null;
  try {
    data = text ? JSON.parse(text) : null;
  } catch {
    data = { detail: text };
  }
  if (!response.ok) {
    const detail = data?.detail;
    if (typeof console !== "undefined" && console.warn) {
      console.warn("API error", response.status, path, detail ?? text);
    }
    throw new Error(userFacingError(detail, GENERIC_REQUEST_ERROR));
  }
  return data;
}

export async function apiUpload(path, { token, formData }) {
  const headers = { Accept: "application/json" };
  if (token) headers.Authorization = `Bearer ${token}`;
  const response = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers,
    body: formData,
  });
  const text = await response.text();
  let data = null;
  try {
    data = text ? JSON.parse(text) : null;
  } catch {
    data = { detail: text };
  }
  if (!response.ok) {
    const detail = data?.detail;
    if (typeof console !== "undefined" && console.warn) {
      console.warn("Upload error", response.status, path, detail ?? text);
    }
    throw new Error(userFacingError(detail, GENERIC_UPLOAD_ERROR));
  }
  return data;
}

export { API_BASE };
