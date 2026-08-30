/** Accept a raw list (tests / old clients) or a {items,total,has_more} page. */
export function pageItems(data) {
  if (Array.isArray(data)) return data;
  return data?.items || [];
}

export function pageMeta(data) {
  if (Array.isArray(data)) {
    return { total: data.length, has_more: false, limit: data.length, offset: 0 };
  }
  return {
    total: data?.total ?? 0,
    has_more: Boolean(data?.has_more),
    limit: data?.limit ?? 0,
    offset: data?.offset ?? 0,
  };
}
