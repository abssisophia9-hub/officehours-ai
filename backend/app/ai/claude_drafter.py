"""
KB / teaching draft helper.

FYP runtime uses the custom-trained Synthesizer (RAG + style ranker).
``draft_with_claude`` is retained as a compatibility alias and no longer
calls Anthropic or USE_MOCK_CLAUDE templates.
"""

from __future__ import annotations

from typing import Any

# Kept for docs / optional style hints in analytics UIs.
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
    """Compatibility alias → custom Synthesizer draft (no Claude / no mocks)."""
    from app.ai.synthesizer_model import draft_kb_with_model

    return draft_kb_with_model(
        question_text=question_text,
        category=category,
        tags=tags,
        learning_style=learning_style,
        urgency=urgency,
    )
