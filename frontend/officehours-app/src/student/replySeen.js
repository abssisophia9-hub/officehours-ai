const EVENT = "officehours-asks-seen";

function storageKey(userId) {
  return `officehours_seen_replies:${userId}`;
}

export function seenReplyIds(userId) {
  if (!userId) return new Set();
  try {
    const raw = JSON.parse(localStorage.getItem(storageKey(userId)) || "[]");
    return new Set(Array.isArray(raw) ? raw.map(String) : []);
  } catch {
    return new Set();
  }
}

export function markReplySeen(userId, requestId) {
  if (!userId || requestId == null) return;
  const ids = seenReplyIds(userId);
  const next = String(requestId);
  if (ids.has(next)) return;
  ids.add(next);
  localStorage.setItem(storageKey(userId), JSON.stringify([...ids]));
  window.dispatchEvent(new Event(EVENT));
}

export function subscribeReplySeen(listener) {
  window.addEventListener(EVENT, listener);
  return () => window.removeEventListener(EVENT, listener);
}

export function askHasReply(ask) {
  return Boolean(String(ask?.ta_reply || "").trim());
}
