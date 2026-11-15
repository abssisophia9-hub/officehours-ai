"""Bounded public search + link checks for the Revision Agent.

Article path: Wikipedia OpenSearch (official, free, no key) then DuckDuckGo
Instant Answer fill, filtered to a trusted-host allowlist. Video path:
YouTube Data API v3 ``search.list`` (+ ``videos.list`` for duration) when
``YOUTUBE_API_KEY`` is set — **one search per topic**, cached and shared
across students/preferences. Preference is applied later by ranking, not by
extra YouTube searches. No HTML scraping of Google or YouTube pages.
"""

from __future__ import annotations

import json
import logging
import os
import re
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse
from zoneinfo import ZoneInfo

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

# Article / combined short cache (in-process). YouTube topic pool uses a
# longer persisted TTL — see youtube_cache_ttl_seconds().
_DEFAULT_CACHE_TTL = 1800
# 6h: covers a campus afternoon of shared weak-topic plans without re-hitting
# search.list; well under YouTube's 30-day Non-Authorized Data storage cap.
_DEFAULT_YOUTUBE_CACHE_TTL = 21600
_DEFAULT_FAILURE_TTL = 60
# Official defaults (developers.google.com/youtube/v3/determine_quota_cost):
# search.list has its own 100-calls/day bucket (1 unit/call there);
# videos.list costs 1 unit from the 10_000 other-units pool.
_DEFAULT_SEARCH_LIST_DAILY = 100
_DEFAULT_OTHER_UNITS_DAILY = 10_000
_QUOTA_HEADROOM_SEARCH = 5
_QUOTA_HEADROOM_OTHER = 100

_PACIFIC = ZoneInfo("America/Los_Angeles")
_CACHE_PATH = Path(
    os.getenv(
        "OFFICEHOURS_RESOURCES_CACHE_PATH",
        str(Path(__file__).resolve().parents[2] / "data" / "resources_cache.json"),
    )
)

_lock = threading.RLock()
# In-process article/combined cache: key → (expires_monotonic, hits)
_cache: dict[str, tuple[float, list[dict[str, Any]]]] = {}
# Singleflight waiters for identical in-flight YouTube topic fetches.
_inflight: dict[str, threading.Event] = {}
# Process-local counters for tests / measurement (never log key values).
_counters: dict[str, int] = {
    "search_list": 0,
    "videos_list": 0,
    "search_list_blocked_quota": 0,
    "cache_hits_youtube": 0,
    "cache_misses_youtube": 0,
}
# Persisted day counters loaded lazily.
_quota_day: str | None = None
_quota_search_list: int = 0
_quota_other_units: int = 0
_persist_loaded = False


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


def youtube_cache_ttl_seconds() -> int:
    raw = os.getenv(
        "OFFICEHOURS_YOUTUBE_CACHE_TTL_SECONDS",
        str(_DEFAULT_YOUTUBE_CACHE_TTL),
    )
    try:
        return max(0, int(raw))
    except (TypeError, ValueError):
        return _DEFAULT_YOUTUBE_CACHE_TTL


def failure_cache_ttl_seconds() -> int:
    raw = os.getenv(
        "OFFICEHOURS_RESOURCES_FAILURE_CACHE_TTL_SECONDS",
        str(_DEFAULT_FAILURE_TTL),
    )
    try:
        return max(0, int(raw))
    except (TypeError, ValueError):
        return _DEFAULT_FAILURE_TTL


def search_list_daily_limit() -> int:
    raw = os.getenv(
        "OFFICEHOURS_YOUTUBE_SEARCH_DAILY_LIMIT",
        str(_DEFAULT_SEARCH_LIST_DAILY),
    )
    try:
        return max(0, int(raw))
    except (TypeError, ValueError):
        return _DEFAULT_SEARCH_LIST_DAILY


def other_units_daily_limit() -> int:
    raw = os.getenv(
        "OFFICEHOURS_YOUTUBE_OTHER_UNITS_DAILY_LIMIT",
        str(_DEFAULT_OTHER_UNITS_DAILY),
    )
    try:
        return max(0, int(raw))
    except (TypeError, ValueError):
        return _DEFAULT_OTHER_UNITS_DAILY


def clear_resource_cache() -> None:
    """Clear in-process + persisted resource caches and reset day counters in memory."""
    global _quota_day, _quota_search_list, _quota_other_units, _persist_loaded
    with _lock:
        _cache.clear()
        _inflight.clear()
        _quota_day = _pacific_day()
        _quota_search_list = 0
        _quota_other_units = 0
        _persist_loaded = True
        _write_persist_unlocked({"entries": {}, "quota": _quota_snapshot_unlocked()})


def youtube_unit_counters() -> dict[str, int]:
    """Instrument counters (search.list / videos.list calls). No secrets."""
    with _lock:
        return dict(_counters)


def reset_youtube_unit_counters() -> None:
    with _lock:
        for key in _counters:
            _counters[key] = 0


def youtube_quota_usage() -> dict[str, Any]:
    _ensure_persist_loaded()
    with _lock:
        return {
            "day_pt": _quota_day,
            "search_list": _quota_search_list,
            "other_units": _quota_other_units,
            "search_list_limit": search_list_daily_limit(),
            "other_units_limit": other_units_daily_limit(),
        }


def _pacific_day() -> str:
    return datetime.now(_PACIFIC).date().isoformat()


def _ensure_persist_loaded() -> None:
    global _persist_loaded, _quota_day, _quota_search_list, _quota_other_units
    with _lock:
        if _persist_loaded:
            _roll_quota_day_unlocked()
            return
        data = _read_persist_unlocked()
        quota = data.get("quota") if isinstance(data.get("quota"), dict) else {}
        _quota_day = str(quota.get("day_pt") or _pacific_day())
        _quota_search_list = int(quota.get("search_list") or 0)
        _quota_other_units = int(quota.get("other_units") or 0)
        _persist_loaded = True
        _roll_quota_day_unlocked()


def _roll_quota_day_unlocked() -> None:
    global _quota_day, _quota_search_list, _quota_other_units
    today = _pacific_day()
    if _quota_day != today:
        _quota_day = today
        _quota_search_list = 0
        _quota_other_units = 0


def _quota_snapshot_unlocked() -> dict[str, Any]:
    return {
        "day_pt": _quota_day or _pacific_day(),
        "search_list": _quota_search_list,
        "other_units": _quota_other_units,
    }


def _read_persist_unlocked() -> dict[str, Any]:
    try:
        if not _CACHE_PATH.is_file():
            return {"entries": {}, "quota": {}}
        raw = json.loads(_CACHE_PATH.read_text(encoding="utf-8"))
        if isinstance(raw, dict):
            return raw
    except (OSError, ValueError, TypeError):
        logger.info("resources cache read failed")
    return {"entries": {}, "quota": {}}


def _write_persist_unlocked(data: dict[str, Any]) -> None:
    try:
        _CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
        tmp = _CACHE_PATH.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, ensure_ascii=True), encoding="utf-8")
        tmp.replace(_CACHE_PATH)
    except OSError:
        logger.info("resources cache write failed")


def _persist_put_entry(key: str, *, hits: list[dict[str, Any]], ttl: int, ok: bool) -> None:
    if ttl <= 0:
        return
    _ensure_persist_loaded()
    with _lock:
        data = _read_persist_unlocked()
        entries = data.get("entries") if isinstance(data.get("entries"), dict) else {}
        expires = time.time() + ttl
        entries[key] = {
            "expires": expires,
            "ok": ok,
            "hits": [dict(h) for h in hits],
        }
        # Drop expired entries opportunistically.
        now = time.time()
        entries = {
            k: v
            for k, v in entries.items()
            if isinstance(v, dict) and float(v.get("expires") or 0) > now
        }
        data["entries"] = entries
        data["quota"] = _quota_snapshot_unlocked()
        _write_persist_unlocked(data)


def _persist_get_entry(key: str) -> tuple[bool, list[dict[str, Any]]] | None:
    """Return (ok, hits) or None if missing/expired."""
    _ensure_persist_loaded()
    with _lock:
        data = _read_persist_unlocked()
        entries = data.get("entries") if isinstance(data.get("entries"), dict) else {}
        row = entries.get(key)
        if not isinstance(row, dict):
            return None
        expires = float(row.get("expires") or 0)
        if time.time() > expires:
            return None
        hits = row.get("hits") if isinstance(row.get("hits"), list) else []
        return bool(row.get("ok", True)), [dict(h) for h in hits if isinstance(h, dict)]


def _quota_allows_search() -> bool:
    _ensure_persist_loaded()
    with _lock:
        _roll_quota_day_unlocked()
        search_cap = max(0, search_list_daily_limit() - _QUOTA_HEADROOM_SEARCH)
        other_cap = max(0, other_units_daily_limit() - _QUOTA_HEADROOM_OTHER)
        return _quota_search_list < search_cap and _quota_other_units < other_cap


def _record_quota(search_list: int = 0, other_units: int = 0) -> None:
    global _quota_search_list, _quota_other_units
    _ensure_persist_loaded()
    with _lock:
        _roll_quota_day_unlocked()
        _quota_search_list += max(0, search_list)
        _quota_other_units += max(0, other_units)
        _counters["search_list"] += max(0, search_list)
        _counters["videos_list"] += max(0, other_units)
        data = _read_persist_unlocked()
        data["quota"] = _quota_snapshot_unlocked()
        if "entries" not in data or not isinstance(data["entries"], dict):
            data["entries"] = {}
        _write_persist_unlocked(data)


def _cache_get(key: str) -> list[dict[str, Any]] | None:
    ttl = cache_ttl_seconds()
    if ttl <= 0:
        return None
    with _lock:
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
    with _lock:
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


def _normalize_topic(topic: str | None) -> str:
    return re.sub(r"\s+", " ", (topic or "").strip().lower())


def topic_youtube_query(topic: str) -> str:
    """Neutral topic query — preference is applied later by ranking, not here."""
    t = (topic or "").strip() or "course revision"
    return f"{t} data structures tutorial"[:200]


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
    """Direct YouTube Data API v3 search (no topic cache). Prefer youtube_topic_pool."""
    q = (query or "").strip()
    key = (os.getenv("YOUTUBE_API_KEY") or "").strip()
    if not q or not key or not _web_enabled():
        return []
    if not _quota_allows_search():
        with _lock:
            _counters["search_list_blocked_quota"] += 1
        logger.info("youtube search skipped near daily quota")
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
            _record_quota(search_list=1)
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


def youtube_topic_pool(topic: str, *, max_results: int = 6) -> list[dict[str, Any]]:
    """One YouTube search per topic; shared by all students/preferences.

    Cached (long TTL, disk), singleflight for identical simultaneous requests,
    failures cached briefly, and blocked near the daily quota.
    """
    if not _web_enabled() or not youtube_key_configured():
        return []
    norm = _normalize_topic(topic) or "course revision"
    cache_key = f"yt|{norm}"
    ttl = youtube_cache_ttl_seconds()

    cached = _persist_get_entry(cache_key)
    if cached is not None:
        ok, hits = cached
        with _lock:
            _counters["cache_hits_youtube"] += 1
        return [] if not ok else hits[:max_results]

    # Singleflight: one live call for identical simultaneous topic keys.
    waiter: threading.Event | None = None
    leader = False
    with _lock:
        existing = _inflight.get(cache_key)
        if existing is not None:
            waiter = existing
        else:
            waiter = threading.Event()
            _inflight[cache_key] = waiter
            leader = True

    if not leader:
        assert waiter is not None
        waiter.wait(timeout=SEARCH_TIMEOUT + 5)
        cached = _persist_get_entry(cache_key)
        if cached is not None:
            ok, hits = cached
            with _lock:
                _counters["cache_hits_youtube"] += 1
            return [] if not ok else hits[:max_results]
        return []

    with _lock:
        _counters["cache_misses_youtube"] += 1

    try:
        if not _quota_allows_search():
            with _lock:
                _counters["search_list_blocked_quota"] += 1
            _persist_put_entry(
                cache_key,
                hits=[],
                ttl=failure_cache_ttl_seconds(),
                ok=False,
            )
            return []

        query = topic_youtube_query(topic)
        try:
            hits, ok = _youtube_topic_pool_fetch(query, max_results=max_results)
        except Exception:
            logger.info("youtube topic pool failed")
            hits, ok = [], False

        if ok:
            store_ttl = ttl if ttl > 0 else _DEFAULT_YOUTUBE_CACHE_TTL
            _persist_put_entry(cache_key, hits=hits, ttl=store_ttl, ok=True)
        else:
            _persist_put_entry(
                cache_key,
                hits=[],
                ttl=failure_cache_ttl_seconds(),
                ok=False,
            )
        return hits[:max_results] if ok else []
    finally:
        with _lock:
            event = _inflight.pop(cache_key, None)
            if event is not None:
                event.set()


def _youtube_topic_pool_fetch(
    query: str, *, max_results: int
) -> tuple[list[dict[str, Any]], bool]:
    """Run search; return (hits, ok). ok=False on quota HTTP / transport errors."""
    key = (os.getenv("YOUTUBE_API_KEY") or "").strip()
    if not query or not key:
        return [], False
    if not _quota_allows_search():
        with _lock:
            _counters["search_list_blocked_quota"] += 1
        return [], False

    params = {
        "part": "snippet",
        "q": query,
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
            _record_quota(search_list=1)
            if response.status_code in {403, 429}:
                logger.info("youtube search unavailable status=%s", response.status_code)
                return [], False
            response.raise_for_status()
            payload = response.json()
    except (httpx.HTTPError, ValueError, TypeError):
        logger.info("youtube search failed")
        return [], False

    items = payload.get("items") if isinstance(payload, dict) else None
    if not isinstance(items, list):
        return [], True

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
    return hits, True


def resource_search(
    query: str,
    *,
    max_results: int = 6,
    preference: str | None = None,
    topic: str | None = None,
) -> list[dict[str, Any]]:
    """Mixed YouTube (topic pool) + trusted articles (query).

    Preference is intentionally not part of the YouTube cache key — ranking
    applies learning preference over the shared topic pool afterwards.
    """
    q = (query or "").strip()
    if not q or not _web_enabled():
        return []

    # Article hits still keyed by query (+ optional preference label) so
    # preference-shaped article phrasing can differ; YouTube does not.
    article_key = "|".join(
        [
            "articles",
            (preference or "").strip().lower(),
            q.lower(),
        ]
    )
    cached_articles = _cache_get(article_key)

    hits: list[dict[str, Any]] = []
    seen: set[str] = set()

    video_budget = max(1, max_results // 2) if youtube_key_configured() else 0
    article_budget = max_results - video_budget if video_budget else max_results

    if video_budget:
        pool_topic = (topic or "").strip() or q
        for row in youtube_topic_pool(pool_topic, max_results=max(video_budget, max_results)):
            url = str(row.get("url") or "")
            if url and url not in seen:
                hits.append(row)
                seen.add(url)
            if len(hits) >= video_budget:
                break

    if cached_articles is not None:
        article_hits = cached_articles
    else:
        article_hits = article_search(q, max_results=max(article_budget, 2))
        _cache_set(article_key, article_hits)

    for row in article_hits:
        url = str(row.get("url") or "")
        if url and url not in seen:
            hits.append(row)
            seen.add(url)

    # Top-up from the same topic pool if articles were thin (no second search.list).
    if len(hits) < max_results and youtube_key_configured():
        pool_topic = (topic or "").strip() or q
        for row in youtube_topic_pool(pool_topic, max_results=max_results):
            url = str(row.get("url") or "")
            if url and url not in seen:
                hits.append(row)
                seen.add(url)
            if len(hits) >= max_results:
                break

    return hits[:max_results]


def link_ok(url: str, *, timeout: float = TIMEOUT) -> bool:
    """HEAD then GET. Accept 2xx/3xx only. Fail closed on errors.

    YouTube watch URLs skip HTTP (and do not call videos.list): search already
    returned them with a valid-looking video id. Duration filtering uses
    videos.list inside youtube search, not link_ok.
    """
    target = (url or "").strip()
    if not target.startswith("http://") and not target.startswith("https://"):
        return False
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
    if not _quota_allows_search():
        # videos.list is cheap but still counts; skip near the other-units cap.
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
            _record_quota(other_units=1)
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
