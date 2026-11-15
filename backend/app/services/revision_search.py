"""Bounded public search + link checks for the Revision Agent.

Article path: Wikipedia OpenSearch (official, free, no key) then DuckDuckGo
Instant Answer fill, filtered to a trusted-host allowlist. Video path:
YouTube Data API v3 ``search.list`` (+ ``videos.list`` for duration) when
``YOUTUBE_API_KEY`` is set. No HTML scraping of Google or YouTube pages.
"""

from __future__ import annotations

import logging
import os
import re
import time
from typing import Any
from urllib.parse import urlparse

import httpx

logger = logging.getLogger("officehours.revision_search")

USER_AGENT = (
    "OfficeHoursAI/0.2 (campus FYP revision; "
    "https://github.com/abssisophia9-hub/officehours-ai)"
)
TIMEOUT = 5.0
SEARCH_TIMEOUT = 8.0

# Soft preference: Wikipedia, Khan, MIT OCW, and university hosts only.
TRUSTED_ARTICLE_SUFFIXES = (
    "wikipedia.org",
    "khanacademy.org",
    "ocw.mit.edu",
    ".edu",
    ".ac.uk",
    ".ac.ma",
)

CLICKBAIT_RE = re.compile(
    r"(must watch|shocking|you won'?t believe|click here|gone wrong|"
    r"top\s*\d+\s*secrets|\bOMG\b|\bEPIC\b|!!!)",
    re.I,
)
SHORTS_RE = re.compile(r"#shorts|\bshorts\b|/shorts/", re.I)

# In-process cache: topic+preference (+query) → hits. Default TTL 30 minutes.
_DEFAULT_CACHE_TTL = 1800
_cache: dict[str, tuple[float, list[dict[str, Any]]]] = {}


def _web_enabled() -> bool:
    return os.getenv("OFFICEHOURS_REVISION_WEB", "true").strip().lower() not in {
        "0",
        "false",
        "no",
        "off",
    }


def cache_ttl_seconds() -> int:
    raw = os.getenv("OFFICEHOURS_RESOURCES_CACHE_TTL_SECONDS", str(_DEFAULT_CACHE_TTL))
    try:
        return max(0, int(raw))
    except (TypeError, ValueError):
        return _DEFAULT_CACHE_TTL


def clear_resource_cache() -> None:
    _cache.clear()


def _cache_get(key: str) -> list[dict[str, Any]] | None:
    ttl = cache_ttl_seconds()
    if ttl <= 0:
        return None
    row = _cache.get(key)
    if not row:
        return None
    expires, hits = row
    if time.monotonic() > expires:
        _cache.pop(key, None)
        return None
    return [dict(h) for h in hits]


def _cache_set(key: str, hits: list[dict[str, Any]]) -> None:
    ttl = cache_ttl_seconds()
    if ttl <= 0:
        return
    _cache[key] = (time.monotonic() + ttl, [dict(h) for h in hits])


def _client(*, timeout: float = TIMEOUT) -> httpx.Client:
    return httpx.Client(
        timeout=timeout,
        headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
        follow_redirects=True,
    )


def youtube_key_configured() -> bool:
    return bool((os.getenv("YOUTUBE_API_KEY") or "").strip())


def is_trusted_article_url(url: str) -> bool:
    try:
        host = (urlparse(url).hostname or "").lower()
    except ValueError:
        return False
    if not host:
        return False
    for suffix in TRUSTED_ARTICLE_SUFFIXES:
        if suffix.startswith("."):
            if host.endswith(suffix) or host == suffix[1:]:
                return True
        elif host == suffix or host.endswith("." + suffix):
            return True
    return False


def looks_like_clickbait(title: str) -> bool:
    text = (title or "").strip()
    if not text:
        return True
    if CLICKBAIT_RE.search(text):
        return True
    letters = [c for c in text if c.isalpha()]
    if len(letters) >= 12:
        upper = sum(1 for c in letters if c.isupper())
        if upper / len(letters) >= 0.7:
            return True
    return False


def looks_like_short(title: str, url: str = "", duration_seconds: int | None = None) -> bool:
    if duration_seconds is not None and duration_seconds < 60:
        return True
    blob = f"{title} {url}"
    return bool(SHORTS_RE.search(blob))


def article_search(query: str, *, max_results: int = 4) -> list[dict[str, Any]]:
    """Wikipedia first, DuckDuckGo fill on trusted hosts only."""
    q = (query or "").strip()
    if not q or not _web_enabled():
        return []
    hits = _wikipedia_opensearch(q, max_results=max_results)
    if len(hits) < max_results:
        extra = _duckduckgo_related(q, max_results=max_results - len(hits))
        seen = {h["url"] for h in hits}
        for row in extra:
            if row["url"] not in seen and is_trusted_article_url(row["url"]):
                hits.append(row)
                seen.add(row["url"])
    return [h for h in hits if is_trusted_article_url(h["url"])][:max_results]


def youtube_search(query: str, *, max_results: int = 4) -> list[dict[str, Any]]:
    """YouTube Data API v3 search. Empty when key missing, web off, or quota."""
    q = (query or "").strip()
    key = (os.getenv("YOUTUBE_API_KEY") or "").strip()
    if not q or not key or not _web_enabled():
        return []

    params = {
        "part": "snippet",
        "q": q,
        "type": "video",
        "safeSearch": "strict",
        "maxResults": max(1, min(max_results * 2, 10)),
        "videoEmbeddable": "true",
        "relevanceLanguage": "en",
        "key": key,
    }
    try:
        with _client(timeout=SEARCH_TIMEOUT) as client:
            response = client.get(
                "https://www.googleapis.com/youtube/v3/search",
                params=params,
            )
            if response.status_code in {403, 429}:
                logger.info("youtube search unavailable status=%s", response.status_code)
                return []
            response.raise_for_status()
            payload = response.json()
    except (httpx.HTTPError, ValueError, TypeError):
        logger.info("youtube search failed")
        return []

    items = payload.get("items") if isinstance(payload, dict) else None
    if not isinstance(items, list):
        return []

    raw: list[dict[str, Any]] = []
    video_ids: list[str] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        vid = ((item.get("id") or {}) if isinstance(item.get("id"), dict) else {}).get(
            "videoId"
        )
        snippet = item.get("snippet") if isinstance(item.get("snippet"), dict) else {}
        if not vid or not snippet:
            continue
        title = str(snippet.get("title") or "").strip()
        channel = str(snippet.get("channelTitle") or "").strip()
        description = str(snippet.get("description") or "").strip()
        url = f"https://www.youtube.com/watch?v={vid}"
        if looks_like_short(title, url) or looks_like_clickbait(title):
            continue
        video_ids.append(str(vid))
        raw.append(
            {
                "kind": "video",
                "title": title[:160] or f"Video {vid}",
                "url": url,
                "snippet": description[:280],
                "query": query,
                "provider": "youtube",
                "channel": channel[:120],
                "video_id": str(vid),
            }
        )

    durations = _youtube_durations(video_ids, key=key)
    hits: list[dict[str, Any]] = []
    for row in raw:
        seconds = durations.get(str(row.get("video_id") or ""))
        if looks_like_short(row["title"], row["url"], seconds):
            continue
        if seconds is not None:
            row["duration_seconds"] = seconds
        hits.append(row)
        if len(hits) >= max_results:
            break
    return hits


def resource_search(
    query: str,
    *,
    max_results: int = 6,
    preference: str | None = None,
    topic: str | None = None,
) -> list[dict[str, Any]]:
    """Mixed YouTube + trusted articles. Cached per topic+preference+query."""
    q = (query or "").strip()
    if not q or not _web_enabled():
        return []

    cache_key = "|".join(
        [
            (topic or "").strip().lower(),
            (preference or "").strip().lower(),
            q.lower(),
        ]
    )
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached[:max_results]

    # Prefer a mix: half video slots, half articles (when YouTube key present).
    video_budget = max(1, max_results // 2) if youtube_key_configured() else 0
    article_budget = max_results - video_budget if video_budget else max_results

    hits: list[dict[str, Any]] = []
    seen: set[str] = set()

    if video_budget:
        for row in youtube_search(q, max_results=video_budget):
            url = str(row.get("url") or "")
            if url and url not in seen:
                hits.append(row)
                seen.add(url)

    for row in article_search(q, max_results=max(article_budget, 2)):
        url = str(row.get("url") or "")
        if url and url not in seen:
            hits.append(row)
            seen.add(url)

    # If articles thin and YouTube still has room, top up videos.
    if len(hits) < max_results and youtube_key_configured():
        for row in youtube_search(q, max_results=max_results):
            url = str(row.get("url") or "")
            if url and url not in seen:
                hits.append(row)
                seen.add(url)
            if len(hits) >= max_results:
                break

    out = hits[:max_results]
    _cache_set(cache_key, out)
    return out


def link_ok(url: str, *, timeout: float = TIMEOUT) -> bool:
    """HEAD then GET. Accept 2xx/3xx only. Fail closed on errors."""
    target = (url or "").strip()
    if not target.startswith("http://") and not target.startswith("https://"):
        return False
    # YouTube watch pages often return odd HEAD codes; treat known watch URLs
    # as ok when the video id looks valid (search already returned them).
    if "youtube.com/watch" in target or "youtu.be/" in target:
        if re.search(r"(?:v=|/|youtu\.be/)([A-Za-z0-9_-]{6,})", target):
            return True
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


def _parse_iso8601_duration(value: str) -> int | None:
    """Parse YouTube contentDetails.duration (PT#H#M#S) to seconds."""
    text = (value or "").strip().upper()
    if not text.startswith("PT"):
        return None
    match = re.fullmatch(
        r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?",
        text,
    )
    if not match:
        return None
    hours = int(match.group(1) or 0)
    minutes = int(match.group(2) or 0)
    seconds = int(match.group(3) or 0)
    return hours * 3600 + minutes * 60 + seconds


def _youtube_durations(video_ids: list[str], *, key: str) -> dict[str, int]:
    ids = [vid for vid in video_ids if vid]
    if not ids or not key:
        return {}
    params = {
        "part": "contentDetails",
        "id": ",".join(ids[:10]),
        "key": key,
    }
    try:
        with _client(timeout=SEARCH_TIMEOUT) as client:
            response = client.get(
                "https://www.googleapis.com/youtube/v3/videos",
                params=params,
            )
            if response.status_code in {403, 429}:
                return {}
            response.raise_for_status()
            payload = response.json()
    except (httpx.HTTPError, ValueError, TypeError):
        return {}
    out: dict[str, int] = {}
    for item in payload.get("items") or []:
        if not isinstance(item, dict):
            continue
        vid = str(item.get("id") or "")
        details = item.get("contentDetails") if isinstance(item.get("contentDetails"), dict) else {}
        seconds = _parse_iso8601_duration(str(details.get("duration") or ""))
        if vid and seconds is not None:
            out[vid] = seconds
    return out


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
        if not link or not is_trusted_article_url(str(link)):
            continue
        if looks_like_clickbait(str(title)):
            continue
        hits.append(
            {
                "kind": "article",
                "title": str(title),
                "url": str(link),
                "snippet": str(snippet or "")[:280],
                "query": query,
                "provider": "wikipedia",
                "channel": "Wikipedia",
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
        if not first.startswith("http") or not is_trusted_article_url(first):
            continue
        title = text.split(" - ", 1)[0][:160] or first
        if looks_like_clickbait(title):
            continue
        hits.append(
            {
                "kind": "article",
                "title": title,
                "url": first,
                "snippet": text[:280],
                "query": query,
                "provider": "duckduckgo",
                "channel": urlparse(first).hostname or "web",
            }
        )
        if len(hits) >= max_results:
            break
    return hits
