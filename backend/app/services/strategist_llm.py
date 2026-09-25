"""Optional hosted-LLM planner for the Strategist agent.

When ``OFFICEHOURS_ALLOW_EXTERNAL_LLM`` is on and an API key is present, the
model reads the learner dossier as a natural-language goal and emits tool calls
(youtube_search / article_search). Campus Ask Triage / Study Agent stay local.
"""

from __future__ import annotations

import json
import os
import re
from typing import Any, Callable

import httpx

TOOL_SPEC = [
    {
        "name": "youtube_search",
        "description": (
            "Search YouTube for videos that match how this student learns. "
            "Pass a specific query (topic + style words such as diagram, "
            "step by step, worked example)."
        ),
        "input_schema": {
            "type": "object",
            "properties": {"query": {"type": "string"}},
            "required": ["query"],
        },
    },
    {
        "name": "article_search",
        "description": (
            "Search articles / encyclopedic pages for the same topic, "
            "tuned to the student's learning style."
        ),
        "input_schema": {
            "type": "object",
            "properties": {"query": {"type": "string"}},
            "required": ["query"],
        },
    },
]


def external_llm_allowed() -> bool:
    return os.getenv("OFFICEHOURS_ALLOW_EXTERNAL_LLM", "false").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def llm_available() -> bool:
    if not external_llm_allowed():
        return False
    return bool(
        (os.getenv("OPENAI_API_KEY") or "").strip()
        or (os.getenv("ANTHROPIC_API_KEY") or "").strip()
    )


def llm_model_name() -> str:
    if (os.getenv("OPENAI_API_KEY") or "").strip():
        return os.getenv("OFFICEHOURS_STRATEGIST_LLM_MODEL", "gpt-4o-mini")
    if (os.getenv("ANTHROPIC_API_KEY") or "").strip():
        return os.getenv("OFFICEHOURS_STRATEGIST_LLM_MODEL", "claude-sonnet-4-5")
    return "none"


def plan_tool_queries_with_llm(
    *,
    goal: str,
    dossier: dict[str, Any],
    focus_topic: str,
    execute: Callable[[str, str], list[dict[str, Any]]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], str]:
    """Run a short tool loop. Returns (resources, tool_calls, model_id)."""
    if (os.getenv("OPENAI_API_KEY") or "").strip():
        return _openai_loop(goal, dossier, focus_topic, execute)
    return _anthropic_loop(goal, dossier, focus_topic, execute)


def _system_prompt() -> str:
    return (
        "You are the OfficeHours Revision Strategist, an autonomous study agent. "
        "You receive a learner dossier built from how the student asks, what they "
        "ask, what they struggle with, and their inferred learning style. "
        "Your job is to call youtube_search and article_search with queries that "
        "match THAT student — not generic 'best video' lists. "
        "Do not invent URLs. Only keep results the tools return. "
        "Prefer 3–6 resources. After tools return, reply with JSON only: "
        '{"picks":[{"url":"...","why":"one sentence"}]}'
    )


def _user_payload(goal: str, dossier: dict[str, Any], focus_topic: str) -> str:
    return json.dumps(
        {
            "natural_language_goal": goal,
            "focus_topic": focus_topic,
            "dossier": dossier,
        },
        ensure_ascii=False,
    )


def _openai_loop(
    goal: str,
    dossier: dict[str, Any],
    focus_topic: str,
    execute: Callable[[str, str], list[dict[str, Any]]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], str]:
    model = os.getenv("OFFICEHOURS_STRATEGIST_LLM_MODEL", "gpt-4o-mini")
    tools = [
        {
            "type": "function",
            "function": {
                "name": spec["name"],
                "description": spec["description"],
                "parameters": spec["input_schema"],
            },
        }
        for spec in TOOL_SPEC
    ]
    messages: list[dict[str, Any]] = [
        {"role": "system", "content": _system_prompt()},
        {"role": "user", "content": _user_payload(goal, dossier, focus_topic)},
    ]
    collected: list[dict[str, Any]] = []
    calls: list[dict[str, Any]] = []
    headers = {
        "Authorization": f"Bearer {os.environ['OPENAI_API_KEY']}",
        "Content-Type": "application/json",
    }
    with httpx.Client(timeout=25.0) as client:
        for _ in range(3):
            response = client.post(
                "https://api.openai.com/v1/chat/completions",
                headers=headers,
                json={
                    "model": model,
                    "messages": messages,
                    "tools": tools,
                    "tool_choice": "auto",
                    "temperature": 0.2,
                },
            )
            response.raise_for_status()
            message = response.json()["choices"][0]["message"]
            messages.append(message)
            tool_calls = message.get("tool_calls") or []
            if not tool_calls:
                picks = _parse_picks(message.get("content") or "")
                return _apply_picks(collected, picks), calls, f"openai:{model}"
            for call in tool_calls:
                fn = call.get("function") or {}
                name = str(fn.get("name") or "")
                try:
                    args = json.loads(fn.get("arguments") or "{}")
                except json.JSONDecodeError:
                    args = {}
                query = str(args.get("query") or focus_topic)
                hits = execute(name, query)
                collected.extend(hits)
                calls.append({"tool": name, "query": query, "hit_count": len(hits)})
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": call.get("id"),
                        "content": json.dumps(hits[:6], ensure_ascii=False),
                    }
                )
    return collected, calls, f"openai:{model}"


def _anthropic_loop(
    goal: str,
    dossier: dict[str, Any],
    focus_topic: str,
    execute: Callable[[str, str], list[dict[str, Any]]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], str]:
    model = os.getenv("OFFICEHOURS_STRATEGIST_LLM_MODEL", "claude-sonnet-4-5")
    tools = [
        {
            "name": spec["name"],
            "description": spec["description"],
            "input_schema": spec["input_schema"],
        }
        for spec in TOOL_SPEC
    ]
    messages: list[dict[str, Any]] = [
        {"role": "user", "content": _user_payload(goal, dossier, focus_topic)}
    ]
    collected: list[dict[str, Any]] = []
    calls: list[dict[str, Any]] = []
    headers = {
        "x-api-key": os.environ["ANTHROPIC_API_KEY"],
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }
    with httpx.Client(timeout=25.0) as client:
        for _ in range(3):
            response = client.post(
                "https://api.anthropic.com/v1/messages",
                headers=headers,
                json={
                    "model": model,
                    "max_tokens": 800,
                    "system": _system_prompt(),
                    "tools": tools,
                    "messages": messages,
                },
            )
            response.raise_for_status()
            payload = response.json()
            blocks = payload.get("content") or []
            messages.append({"role": "assistant", "content": blocks})
            tool_uses = [b for b in blocks if isinstance(b, dict) and b.get("type") == "tool_use"]
            if not tool_uses:
                text = " ".join(
                    str(b.get("text") or "")
                    for b in blocks
                    if isinstance(b, dict) and b.get("type") == "text"
                )
                picks = _parse_picks(text)
                return _apply_picks(collected, picks), calls, f"anthropic:{model}"
            tool_results = []
            for block in tool_uses:
                name = str(block.get("name") or "")
                args = block.get("input") or {}
                query = str(args.get("query") or focus_topic)
                hits = execute(name, query)
                collected.extend(hits)
                calls.append({"tool": name, "query": query, "hit_count": len(hits)})
                tool_results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": block.get("id"),
                        "content": json.dumps(hits[:6], ensure_ascii=False),
                    }
                )
            messages.append({"role": "user", "content": tool_results})
    return collected, calls, f"anthropic:{model}"


def _parse_picks(text: str) -> list[dict[str, str]]:
    if not text:
        return []
    match = re.search(r"\{.*\}", text, flags=re.S)
    if not match:
        return []
    try:
        payload = json.loads(match.group(0))
    except json.JSONDecodeError:
        return []
    picks = payload.get("picks") if isinstance(payload, dict) else None
    if not isinstance(picks, list):
        return []
    out: list[dict[str, str]] = []
    for item in picks:
        if isinstance(item, dict) and item.get("url"):
            out.append(
                {"url": str(item["url"]), "why": str(item.get("why") or "")[:240]}
            )
    return out


def _apply_picks(
    collected: list[dict[str, Any]], picks: list[dict[str, str]]
) -> list[dict[str, Any]]:
    by_url = {str(hit.get("url")): hit for hit in collected if hit.get("url")}
    ordered: list[dict[str, Any]] = []
    for pick in picks:
        hit = by_url.get(pick["url"])
        if not hit:
            continue
        row = dict(hit)
        if pick.get("why"):
            row["why"] = pick["why"]
        ordered.append(row)
    if ordered:
        return ordered
    return collected
