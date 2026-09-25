"""Web tools the Strategist agent calls — structured search, not page scrapers.

YouTube: Data API v3 when ``YOUTUBE_API_KEY`` is set, else optional Invidious.
Articles: Wikipedia OpenSearch (no key). Optional DuckDuckGo related topics.
"""

from __future__ import annotations

import os
from typing import Any
import httpx

USER_AGENT = (
    "OfficeHoursAI/0.2 (campus FYP strategist; "
    "https://github.com/abssisophia9-hub/officehours-ai)"
)
TIMEOUT = 8.0


def _web_enabled() -> bool:
    return os.getenv("OFFICEHOURS_STRATEGIST_WEB", "true").strip().lower() not in {
        "0",
        "false",
        "no",
        "off",
    }


def _client() -> httpx.Client:
    return httpx.Client(
        timeout=TIMEOUT,
        headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
        follow_redirects=True,
    )


def youtube_search(query: str, *, max_results: int = 4) -> list[dict[str, Any]]:
    """Return structured YouTube hits. Empty list if no key / network / disabled."""
    q = (query or "").strip()
    if not q or not _web_enabled():
        return []
    key = (os.getenv("YOUTUBE_API_KEY") or "").strip()
    if key:
        return _youtube_data_api(q, key, max_results=max_results)
    invidious = (os.getenv("OFFICEHOURS_INVIDIOUS_URL") or "").strip().rstrip("/")
    if invidious:
        return _invidious_search(q, invidious, max_results=max_results)
    return []


def article_search(query: str, *, max_results: int = 4) -> list[dict[str, Any]]:
    """Return structured article hits from Wikipedia (+ optional DuckDuckGo)."""
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


def _youtube_data_api(query: str, key: str, *, max_results: int) -> list[dict[str, Any]]:
    url = "https://www.googleapis.com/youtube/v3/search"
    params = {
        "part": "snippet",
        "q": query,
        "type": "video",
        "maxResults": max(1, min(max_results, 8)),
        "safeSearch": "strict",
        "key": key,
    }
    try:
        with _client() as client:
            response = client.get(url, params=params)
            response.raise_for_status()
            payload = response.json()
    except (httpx.HTTPError, ValueError):
        return []
    hits: list[dict[str, Any]] = []
    for item in payload.get("items") or []:
        video_id = (item.get("id") or {}).get("videoId")
        snippet = item.get("snippet") or {}
        if not video_id:
            continue
        hits.append(
            {
                "kind": "youtube",
                "title": str(snippet.get("title") or "YouTube video"),
                "url": f"https://www.youtube.com/watch?v={video_id}",
                "snippet": str(snippet.get("description") or "")[:280],
                "query": query,
            }
        )
    return hits


def _invidious_search(query: str, base: str, *, max_results: int) -> list[dict[str, Any]]:
    url = f"{base}/api/v1/search"
    try:
        with _client() as client:
            response = client.get(url, params={"q": query, "type": "video"})
            response.raise_for_status()
            payload = response.json()
    except (httpx.HTTPError, ValueError, TypeError):
        return []
    hits: list[dict[str, Any]] = []
    if not isinstance(payload, list):
        return []
    for item in payload:
        if not isinstance(item, dict):
            continue
        video_id = item.get("videoId")
        if not video_id:
            continue
        hits.append(
            {
                "kind": "youtube",
                "title": str(item.get("title") or "YouTube video"),
                "url": f"https://www.youtube.com/watch?v={video_id}",
                "snippet": str(item.get("description") or "")[:280],
                "query": query,
            }
        )
        if len(hits) >= max_results:
            break
    return hits


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
        with _client() as client:
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
        with _client() as client:
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
            }
        )
        if len(hits) >= max_results:
            break
    return hits
