const ID_PARAM_NAMES = ["student_id", "studentId", "id"];

export function parseStudentIdFromScan(rawValue) {
  const value = rawValue.trim();
  if (!value) {
    return "";
  }

  const fromUrl = parseUrlPayload(value);
  if (fromUrl) {
    return normalizeStudentId(fromUrl);
  }

  const prefixedMatch = value.match(/(?:student(?:_id)?|id)\s*[:=]\s*([a-z0-9-]+)/i);
  if (prefixedMatch) {
    return normalizeStudentId(prefixedMatch[1]);
  }

  return normalizeStudentId(value);
}

function parseUrlPayload(value) {
  try {
    const parsedUrl = new URL(value);
    for (const paramName of ID_PARAM_NAMES) {
      const paramValue = parsedUrl.searchParams.get(paramName);
      if (paramValue) {
        return paramValue;
      }
    }
  } catch {
    return "";
  }

  return "";
}

function normalizeStudentId(value) {
  return value.trim().replace(/\s+/g, "");
}
