"""
Claude-backed teaching-approach drafts, adapted to inferred learning style.

Set USE_MOCK_CLAUDE=true (default) for deterministic local/demo drafts without
an API key. Set USE_MOCK_CLAUDE=false and ANTHROPIC_API_KEY to call Claude.
"""

from __future__ import annotations

import json
import os
import re
from typing import Any

STYLE_TEACHING_GUIDANCE = {
    "example_driven": (
        "Lead with 1–2 concrete worked examples before naming the general rule. "
        "Ask the student to predict the next step in a third tiny example."
    ),
    "step_by_step": (
        "Number a short procedure. Keep each step one action. "
        "After the sequence, have the student restate the steps from memory."
    ),
    "visual_structural": (
        "Describe the structure spatially (nodes, edges, before/after states). "
        "Suggest a quick sketch or table that makes the invariant visible."
    ),
    "conceptual": (
        "Start from the why / invariant / definition. "
        "Only then attach one minimal example that proves the idea."
    ),
    "unknown": (
        "Offer a hybrid: one-sentence intuition, one tiny example, then a 3-step checklist."
    ),
}


def draft_with_claude(
    *,
    question_text: str,
    category: str | None,
    tags: list[str],
    learning_style: str | None,
    urgency: str | None = None,
) -> dict[str, Any]:
    style = (learning_style or "unknown").strip() or "unknown"
    if _use_mock():
        return _mock_draft(
            question_text=question_text,
            category=category,
            tags=tags,
            learning_style=style,
            urgency=urgency,
        )

    return _live_claude_draft(
        question_text=question_text,
        category=category,
        tags=tags,
        learning_style=style,
        urgency=urgency,
    )


def _use_mock() -> bool:
    flag = os.getenv("USE_MOCK_CLAUDE", "true").strip().lower()
    if flag in {"0", "false", "no"}:
        return not bool(os.getenv("ANTHROPIC_API_KEY", "").strip())
    return True


def _mock_draft(
    *,
    question_text: str,
    category: str | None,
    tags: list[str],
    learning_style: str,
    urgency: str | None,
) -> dict[str, Any]:
    topic = ", ".join(tags[:3]) if tags else (category or "this topic").replace("_", " ")
    guidance = STYLE_TEACHING_GUIDANCE.get(learning_style, STYLE_TEACHING_GUIDANCE["unknown"])
    urgency_note = f" Urgency signal: {urgency}." if urgency else ""

    if learning_style == "example_driven":
        approach = (
            f"Teaching approach for {topic} (example-driven):\n"
            f"1. Restate the stuck point in the student's words.{urgency_note}\n"
            "2. Work one tiny concrete example end-to-end.\n"
            "3. Change one input and ask what must change in the result.\n"
            "4. Name the general rule only after the examples land.\n"
            f"Original question: {question_text.strip()}"
        )
        hint = (
            f"Try inventing the smallest example of “{tags[0] if tags else topic}” "
            "that should obviously work — what happens in that case?"
        )
    elif learning_style == "step_by_step":
        approach = (
            f"Teaching approach for {topic} (step-by-step):\n"
            f"1. Write a 4-step checklist for the procedure.{urgency_note}\n"
            "2. Execute step 1–2 together on their case.\n"
            "3. Have them complete steps 3–4 aloud.\n"
            "4. Ask which step failed last time and why.\n"
            f"Original question: {question_text.strip()}"
        )
        hint = (
            "List the steps you think the algorithm/process should take, "
            "then mark the first step you are unsure about."
        )
    elif learning_style == "visual_structural":
        approach = (
            f"Teaching approach for {topic} (visual/structural):\n"
            f"1. Sketch the before/after structure (boxes, pointers, layers).{urgency_note}\n"
            "2. Mark the invariant that must hold after each transformation.\n"
            "3. Trace one failing case on the sketch.\n"
            "4. Correct the structure, then restate the invariant in one sentence.\n"
            f"Original question: {question_text.strip()}"
        )
        hint = (
            "Draw the structure before and after the operation — "
            "what relationship must stay true?"
        )
    elif learning_style == "conceptual":
        approach = (
            f"Teaching approach for {topic} (conceptual):\n"
            f"1. Ask what definition or invariant they believe applies.{urgency_note}\n"
            "2. Clarify the core idea in one sentence without jargon pile-up.\n"
            "3. Attach one minimal example that proves the idea.\n"
            "4. Ask them to explain the why back to you.\n"
            f"Original question: {question_text.strip()}"
        )
        hint = (
            "Before debugging details, write one sentence: what must remain true "
            "for this idea to work?"
        )
    else:
        approach = (
            f"Teaching approach for {topic} (hybrid):\n"
            f"1. One-sentence intuition.{urgency_note}\n"
            "2. One tiny example.\n"
            "3. Three-step checklist they can reuse.\n"
            "4. Confirm the takeaway in their own words.\n"
            f"Original question: {question_text.strip()}"
        )
        hint = (
            "Write what you already tried and the exact point where your understanding "
            "breaks — that helps the next helper jump in faster."
        )

    return {
        "answer_draft": approach,
        "student_hint": hint,
        "learning_style": learning_style,
        "style_guidance": guidance,
        "drafter_backend": "mock_claude",
    }


def _live_claude_draft(
    *,
    question_text: str,
    category: str | None,
    tags: list[str],
    learning_style: str,
    urgency: str | None,
) -> dict[str, Any]:
    try:
        import urllib.error
        import urllib.request
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError("urllib unavailable") from exc

    api_key = os.getenv("ANTHROPIC_API_KEY", "").strip()
    model = os.getenv("OFFICEHOURS_CLAUDE_MODEL", "claude-3-5-sonnet-20241022")
    guidance = STYLE_TEACHING_GUIDANCE.get(learning_style, STYLE_TEACHING_GUIDANCE["unknown"])
    prompt = {
        "model": model,
        "max_tokens": 700,
        "messages": [
            {
                "role": "user",
                "content": (
                    "You help TAs prepare office-hours teaching approaches.\n"
                    "Return strict JSON with keys answer_draft and student_hint.\n"
                    "answer_draft: numbered teaching roadmap for the TA (no full solution dump).\n"
                    "student_hint: one non-spoiler hint for the waiting student.\n"
                    f"Learning style to adapt to: {learning_style}. Guidance: {guidance}\n"
                    f"Category: {category}. Tags: {', '.join(tags)}. Urgency: {urgency}.\n"
                    f"Student question: {question_text}"
                ),
            }
        ],
    }
    request = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=json.dumps(prompt).encode("utf-8"),
        headers={
            "content-type": "application/json",
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
        fallback = _mock_draft(
            question_text=question_text,
            category=category,
            tags=tags,
            learning_style=learning_style,
            urgency=urgency,
        )
        fallback["drafter_backend"] = "mock_claude_fallback"
        return fallback

    text_blocks = [
        block.get("text", "")
        for block in payload.get("content", [])
        if isinstance(block, dict) and block.get("type") == "text"
    ]
    raw = "\n".join(text_blocks).strip()
    parsed = _parse_json_object(raw)
    if not parsed:
        fallback = _mock_draft(
            question_text=question_text,
            category=category,
            tags=tags,
            learning_style=learning_style,
            urgency=urgency,
        )
        fallback["drafter_backend"] = "mock_claude_fallback"
        return fallback

    return {
        "answer_draft": str(parsed.get("answer_draft") or "").strip()
        or _mock_draft(
            question_text=question_text,
            category=category,
            tags=tags,
            learning_style=learning_style,
            urgency=urgency,
        )["answer_draft"],
        "student_hint": str(parsed.get("student_hint") or "").strip()
        or _mock_draft(
            question_text=question_text,
            category=category,
            tags=tags,
            learning_style=learning_style,
            urgency=urgency,
        )["student_hint"],
        "learning_style": learning_style,
        "style_guidance": guidance,
        "drafter_backend": "claude",
    }


def _parse_json_object(raw: str) -> dict[str, Any] | None:
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        pass

    match = re.search(r"\{.*\}", raw, flags=re.DOTALL)
    if not match:
        return None
    try:
        parsed = json.loads(match.group(0))
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, dict) else None
