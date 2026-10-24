"""Gemini generateContent for the study-agent answer check.

One urllib call. No SDK. The key is read from ``GEMINI_API_KEY`` or
``GOOGLE_API_KEY`` and is never logged. The default model is on the Gemini
API free tier (free input and output tokens until billing is turned on).
"""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from dataclasses import dataclass

DEFAULT_GEMINI_MODEL = "gemini-3.8-flash"
_GENERATE_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
)


def gemini_api_key() -> str:
    return (os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY") or "").strip()


def gemini_model() -> str:
    return os.getenv("GEMINI_MODEL", DEFAULT_GEMINI_MODEL).strip() or DEFAULT_GEMINI_MODEL


@dataclass
class GeminiCompletion:
    text: str
    model: str
    input_tokens: int
    output_tokens: int
    latency_ms: float


def complete_gemini(
    system: str,
    user: str,
    *,
    max_tokens: int = 400,
    temperature: float = 0,
    timeout: float = 10,
) -> GeminiCompletion:
    """One generateContent call. Raises RuntimeError when the key is missing."""
    api_key = gemini_api_key()
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY missing")

    model = gemini_model()
    payload = {
        "systemInstruction": {"parts": [{"text": system}]},
        "contents": [{"role": "user", "parts": [{"text": user}]}],
        "generationConfig": {
            "temperature": temperature,
            "maxOutputTokens": max_tokens,
            "responseMimeType": "application/json",
            "thinkingConfig": {"thinkingBudget": 0},
        },
    }
    request = urllib.request.Request(
        _GENERATE_URL.format(model=model),
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "content-type": "application/json",
            "x-goog-api-key": api_key,
        },
        method="POST",
    )
    started = time.perf_counter()
    with urllib.request.urlopen(request, timeout=timeout) as response:
        body = json.loads(response.read().decode("utf-8"))
    latency_ms = (time.perf_counter() - started) * 1000
    candidates = body.get("candidates") or []
    parts = ((candidates[0].get("content") or {}).get("parts") if candidates else None) or []
    texts = [
        part.get("text", "")
        for part in parts
        if isinstance(part, dict) and part.get("text") and not part.get("thought")
    ]
    usage = body.get("usageMetadata") or {}
    return GeminiCompletion(
        text="\n".join(texts).strip(),
        model=str(body.get("modelVersion") or model),
        input_tokens=int(usage.get("promptTokenCount") or 0),
        output_tokens=int(usage.get("candidatesTokenCount") or 0),
        latency_ms=latency_ms,
    )
