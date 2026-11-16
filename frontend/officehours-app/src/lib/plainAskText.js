/** Strip internal demo/test suffixes from ask text shown to users. */
export function plainAskText(text) {
  return String(text || "")
    .replace(/\s*\((?:past-asks|polish\s*redo|demo|test)[^)]*seed[^)]*\)\s*/gi, " ")
    .replace(/\s{2,}/g, " ")
    .trim();
}
