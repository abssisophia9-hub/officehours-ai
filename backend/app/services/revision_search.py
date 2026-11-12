"""Bounded public search + link checks for the Revision Agent.

Wikipedia OpenSearch and DuckDuckGo Instant Answer via httpx only.
No new dependencies. Never scrapes full pages.
"""

from __future__ import annotations

import os
from typing import Any

import httpx

USER_AGENT = (
    "OfficeHoursAI/0.2 (campus FYP revision; "
    "https://github.com/abssisophia9-hub/officehours-ai)"
)
TIMEOUT = 5.0
SEARCH_TIMEOUT = 8.0


def _web_enabled() -> bool:
    return os.getenv("OFFICEHOURS_REVISION_WEB", "true").strip().lower() not in {
        "0",
        "false",
        "no",
        "off",
    }


def _client(*, timeout: float = TIMEOUT) -> httpx.Client:
    return httpx.Client(
        timeout=timeout,
        headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
        follow_redirects=True,
    )


def article_search(query: str, *, max_results: int = 4) -> list[dict[str, Any]]:
    """Wikipedia first, DuckDuckGo fill. Empty when web disabled or offline."""
    q = (query or "").strip()
    if not q or not _web_enabled():
        return []
    hits = _wikipedia_opensearch(q, max_results=max_results)
    if len(hits) < max_results:
        extra = _duckduckgo_related(q, max_results=max_results - len(hits))
        seen = {h["url"] for h in hits}
        for row in extra:
            if row["url"] not in seen:
                hits.append(row)
                seen.add(row["url"])
    return hits[:max_results]


def link_ok(url: str, *, timeout: float = TIMEOUT) -> bool:
    """HEAD then GET. Accept 2xx/3xx only. Fail closed on errors."""
    target = (url or "").strip()
    if not target.startswith("http://") and not target.startswith("https://"):
        return False
    try:
        with _client(timeout=timeout) as client:
            head = client.head(target)
            if 200 <= head.status_code < 400:
                return True
            if head.status_code in {405, 403, 501}:
                get = client.get(target)
                return 200 <= get.status_code < 400
            return False
    except (httpx.HTTPError, ValueError, TypeError):
        return False


def _wikipedia_opensearch(query: str, *, max_results: int) -> list[dict[str, Any]]:
    url = "https://en.wikipedia.org/w/api.php"
    params = {
        "action": "opensearch",
        "search": query,
        "limit": max(1, min(max_results, 8)),
        "namespace": 0,
        "format": "json",
    }
    try:
        with _client(timeout=SEARCH_TIMEOUT) as client:
            response = client.get(url, params=params)
            response.raise_for_status()
            payload = response.json()
    except (httpx.HTTPError, ValueError, TypeError):
        return []
    if not isinstance(payload, list) or len(payload) < 4:
        return []
    titles = payload[1] if isinstance(payload[1], list) else []
    snippets = payload[2] if isinstance(payload[2], list) else []
    urls = payload[3] if isinstance(payload[3], list) else []
    hits: list[dict[str, Any]] = []
    for title, snippet, link in zip(titles, snippets, urls):
        if not link:
            continue
        hits.append(
            {
                "kind": "article",
                "title": str(title),
                "url": str(link),
                "snippet": str(snippet or "")[:280],
                "query": query,
                "provider": "wikipedia",
            }
        )
    return hits


def _duckduckgo_related(query: str, *, max_results: int) -> list[dict[str, Any]]:
    url = "https://api.duckduckgo.com/"
    params = {
        "q": query,
        "format": "json",
        "no_html": 1,
        "skip_disambig": 1,
    }
    try:
        with _client(timeout=SEARCH_TIMEOUT) as client:
            response = client.get(url, params=params)
            response.raise_for_status()
            payload = response.json()
    except (httpx.HTTPError, ValueError, TypeError):
        return []
    hits: list[dict[str, Any]] = []
    topics = payload.get("RelatedTopics") or []
    for item in topics:
        if not isinstance(item, dict):
            continue
        if "Topics" in item:
            continue
        first = str(item.get("FirstURL") or "")
        text = str(item.get("Text") or "")
        if not first.startswith("http"):
            continue
        hits.append(
            {
                "kind": "article",
                "title": text.split(" - ", 1)[0][:160] or first,
                "url": first,
                "snippet": text[:280],
                "query": query,
                "provider": "duckduckgo",
            }
        )
        if len(hits) >= max_results:
            break
    return hits
