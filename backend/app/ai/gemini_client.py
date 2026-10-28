"""Gemini REST client for the study-agent answer check.

Default model is ``gemini-3.5-flash-lite``. The Gemini API pricing page
(checked 2026-10-24) lists its standard input and output as free of charge,
and the structured-output guide includes this model. It is the current
Flash-Lite for high-volume short JSON, and its default thinking level is
minimal, so a 400-token cap stays on the answer. ``gemini-3.8-flash`` is
also free, but it is the large agent model and spends the free quota faster.
``gemini-2.5-flash`` is restricted for new projects.

The key is read only from ``GEMINI_API_KEY``. It is sent in the
``x-goog-api-key`` header, never placed in the URL, and never logged.
"""

from __future__ import annotations

import base64
import json
import logging
import os
import threading
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from urllib.parse import quote

logger = logging.getLogger("officehours.answer_check")

DEFAULT_GEMINI_MODEL = "gemini-3.5-flash-lite"


def gemini_model() -> str:
    return os.getenv("GEMINI_MODEL", DEFAULT_GEMINI_MODEL).strip() or DEFAULT_GEMINI_MODEL
GEMINI_ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
RATE_LIMIT_ATTEMPTS = 3
RATE_LIMIT_BACKOFF_SECONDS = (1.0, 2.0)

# Response contract shared with the Claude check. Nullable fields use the
# JSON Schema form the generateContent REST examples accept.
ANSWER_JSON_SCHEMA = {
    "type": "object",
    "properties": {
        "answerable": {"type": "boolean"},
        "supporting_chunk_id": {"type": "integer", "nullable": True},
        "answer": {"type": "string", "nullable": True},
        "quote": {"type": "string", "nullable": True},
    },
    "required": ["answerable", "supporting_chunk_id", "answer", "quote"],
}

_FREE_TIER_WARNING = (
    "Gemini free tier is selected (OFFICEHOURS_LLM_PROVIDER=gemini). "
    "Google may use prompts to improve its products. "
    "Only synthetic demo data may be sent. "
    "The check also requires OFFICEHOURS_GEMINI_FREE_TIER_ACK=true, "
    "OFFICEHOURS_ALLOW_EXTERNAL_LLM=true, and OFFICEHOURS_DEMO=true."
)

_request_times: list[float] = []
_throttle_lock = threading.Lock()
_free_tier_warned = False


class DailyQuotaError(Exception):
    """HTTP 429 that is a daily quota, not a short rate limit."""


class RateLimitExhausted(Exception):
    """429 or 503 persisted after the configured retries."""


@dataclass
class GeminiCompletion:
    text: str
    model: str
    input_tokens: int
    output_tokens: int
    latency_ms: float


def warn_gemini_free_tier() -> None:
    """Log once when the Gemini provider is selected. The key is not read."""
    global _free_tier_warned
    provider = os.getenv("OFFICEHOURS_LLM_PROVIDER", "").strip().lower()
    if provider != "gemini" or _free_tier_warned:
        return
    _free_tier_warned = True
    logger.warning("%s", _FREE_TIER_WARNING)


def reset_throttle() -> None:
    """Drop the in-process request window. Tests call this."""
    with _throttle_lock:
        _request_times.clear()


def _rpm() -> int:
    raw = os.getenv("OFFICEHOURS_LLM_RPM", "5").strip()
    try:
        value = int(raw)
    except ValueError:
        return 5
    return value if value > 0 else 5


def _throttle() -> None:
    """At most ``OFFICEHOURS_LLM_RPM`` requests per 60 seconds (default 5)."""
    rpm = _rpm()
    with _throttle_lock:
        now = time.monotonic()
        _request_times[:] = [stamp for stamp in _request_times if now - stamp < 60.0]
        if len(_request_times) >= rpm:
            wait = 60.0 - (now - _request_times[0])
            if wait > 0:
                time.sleep(wait)
            now = time.monotonic()
            _request_times[:] = [stamp for stamp in _request_times if now - stamp < 60.0]
        _request_times.append(time.monotonic())


def _is_daily_quota(body: str) -> bool:
    folded = body.lower()
    compact = folded.replace("_", "").replace(" ", "").replace("-", "")
    return "perday" in compact or "per day" in folded or "daily" in folded


def _error_body(exc: urllib.error.HTTPError) -> str:
    try:
        raw = exc.read()
    except Exception:
        return ""
    if isinstance(raw, bytes):
        return raw.decode("utf-8", errors="replace")
    return str(raw or "")


def _completion_from_body(raw: bytes, model: str, latency_ms: float) -> GeminiCompletion:
    body = json.loads(raw.decode("utf-8"))
    texts: list[str] = []
    candidates = body.get("candidates") or []
    if candidates:
        content = candidates[0].get("content") or {}
        for part in content.get("parts") or []:
            if part.get("thought"):
                continue
            text = part.get("text")
            if isinstance(text, str):
                texts.append(text)
    usage = body.get("usageMetadata") or {}
    return GeminiCompletion(
        text="\n".join(texts).strip(),
        model=str(body.get("modelVersion") or model),
        input_tokens=int(usage.get("promptTokenCount") or 0),
        output_tokens=int(usage.get("candidatesTokenCount") or 0),
        latency_ms=latency_ms,
    )


def complete_gemini(
    system: str,
    user: str,
    *,
    max_tokens: int = 400,
    temperature: float = 0,
    timeout: float = 10,
) -> GeminiCompletion:
    """One generateContent call. 429/503 are retried inside this function.

    A daily quota is not retried. Exhausted retries raise
    ``RateLimitExhausted``, which is not a ``URLError``, so the outer gate
    does not retry them again. Timeouts and other transport errors propagate.
    """
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY missing")

    model = gemini_model()
    url = GEMINI_ENDPOINT.format(model=quote(model, safe=""))
    payload = {
        "systemInstruction": {"parts": [{"text": system}]},
        "contents": [{"role": "user", "parts": [{"text": user}]}],
        "generationConfig": {
            "temperature": temperature,
            "maxOutputTokens": max_tokens,
            # generateContent REST examples set mimeType to APPLICATION_JSON.
            "responseFormat": {
                "text": {
                    "mimeType": "APPLICATION_JSON",
                    "schema": ANSWER_JSON_SCHEMA,
                }
            },
        },
    }
    data = json.dumps(payload).encode("utf-8")
    headers = {
        "content-type": "application/json",
        "x-goog-api-key": api_key,
    }

    for attempt in range(1, RATE_LIMIT_ATTEMPTS + 1):
        _throttle()
        request = urllib.request.Request(url, data=data, headers=headers, method="POST")
        started = time.perf_counter()
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                raw = response.read()
        except urllib.error.HTTPError as exc:
            status = getattr(exc, "code", None)
            body = _error_body(exc)
            if status == 429 and _is_daily_quota(body):
                logger.warning("answer_check daily_quota provider=gemini")
                raise DailyQuotaError("daily_quota") from None
            if status in {429, 503} and attempt < RATE_LIMIT_ATTEMPTS:
                logger.warning(
                    "answer_check retry status=%s attempt=%s provider=gemini",
                    status,
                    attempt,
                )
                time.sleep(RATE_LIMIT_BACKOFF_SECONDS[attempt - 1])
                continue
            if status in {429, 503}:
                logger.warning(
                    "answer_check rate_limit_exhausted provider=gemini attempts=%s",
                    RATE_LIMIT_ATTEMPTS,
                )
                raise RateLimitExhausted("rate_limit_exhausted") from None
            raise
        latency_ms = (time.perf_counter() - started) * 1000
        return _completion_from_body(raw, model, latency_ms)

    logger.warning(
        "answer_check rate_limit_exhausted provider=gemini attempts=%s",
        RATE_LIMIT_ATTEMPTS,
    )
    raise RateLimitExhausted("rate_limit_exhausted")


def _image_request_bodies(system: str, data: bytes, mime: str) -> list[bytes]:
    """Two documented image shapes. The second is used only after a 400.

    The picture comes first. The instruction sits in the text part, because a
    system instruction beside an image is what this read was sending when
    Gemini rejected the screenshot.
    """
    encoded = base64.b64encode(data).decode("ascii")
    instruction = f"{system.strip()}\n\nTranscribe the visible text."

    def image_then_text(image_part: dict[str, object]) -> dict[str, object]:
        return {"contents": [{"parts": [image_part, {"text": instruction}]}]}

    shapes = (
        image_then_text({"inline_data": {"mime_type": mime, "data": encoded}}),
        image_then_text({"inlineData": {"mimeType": mime, "data": encoded}}),
    )
    return [json.dumps(shape).encode("utf-8") for shape in shapes]


def _post_image_body(
    url: str,
    body: bytes,
    headers: dict[str, str],
    model: str,
) -> GeminiCompletion:
    """Post one image body. A short rate limit is retried. A timeout is retried once."""
    for attempt in range(1, RATE_LIMIT_ATTEMPTS + 1):
        _throttle()
        request = urllib.request.Request(url, data=body, headers=headers, method="POST")
        started = time.perf_counter()
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                raw = response.read()
        except urllib.error.HTTPError as exc:
            status = getattr(exc, "code", None)
            error_body = _error_body(exc)
            if status == 429 and _is_daily_quota(error_body):
                logger.warning("study_file transcribe daily_quota provider=gemini")
                raise DailyQuotaError("daily_quota") from None
            if status in {429, 503} and attempt < RATE_LIMIT_ATTEMPTS:
                logger.warning(
                    "study_file transcribe retry status=%s attempt=%s provider=gemini",
                    status,
                    attempt,
                )
                time.sleep(RATE_LIMIT_BACKOFF_SECONDS[attempt - 1])
                continue
            reason = " ".join(error_body.split())[:160]
            logger.warning(
                "study_file transcribe status=%s provider=gemini reason=%s",
                status,
                reason,
            )
            raise
        except (TimeoutError, urllib.error.URLError):
            logger.warning(
                "study_file transcribe timeout attempt=%s provider=gemini",
                attempt,
            )
            if attempt < 2:
                continue
            raise
        latency_ms = (time.perf_counter() - started) * 1000
        return _completion_from_body(raw, model, latency_ms)
    raise RateLimitExhausted("rate_limit_exhausted")


def transcribe_image(data: bytes, mime: str, *, system: str) -> GeminiCompletion:
    """One vision call that returns visible text. The key stays in the header.

    The image is not written into the URL or the log. This call does not use
    the answer-check JSON schema. A screenshot is slower than a text check, so
    the limit is 30 seconds and a dropped connection or a short rate limit is
    retried. A 400 tries the other documented image field names once.
    """
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY missing")
    model = gemini_model()
    url = GEMINI_ENDPOINT.format(model=quote(model, safe=""))
    headers = {
        "content-type": "application/json",
        "x-goog-api-key": api_key,
    }
    bodies = _image_request_bodies(system, data, mime)
    for index, body in enumerate(bodies):
        if api_key.encode("utf-8") in body or "key=" in url:
            raise RuntimeError("refusing to send the API key in the image request")
        try:
            return _post_image_body(url, body, headers, model)
        except urllib.error.HTTPError as exc:
            if getattr(exc, "code", None) == 400 and index + 1 < len(bodies):
                logger.warning("study_file transcribe retry_shape provider=gemini")
                continue
            raise
    raise RuntimeError("screenshot read was not sent")
