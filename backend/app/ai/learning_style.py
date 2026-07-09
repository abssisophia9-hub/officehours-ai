"""
Infer how a student prefers to understand a topic from their question text.

Backends:
- rules (default): keyword/cue heuristics
- ml: embedding + logistic regression trained on labeled learning-style data
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass

LEARNING_STYLES = (
    "example_driven",
    "step_by_step",
    "visual_structural",
    "conceptual",
    "unknown",
)

STYLE_CUES: dict[str, tuple[str, ...]] = {
    "example_driven": (
        "example",
        "examples",
        "for instance",
        "sample",
        "walk through",
        "show me",
        "concrete",
        "worked",
        "like when",
    ),
    "step_by_step": (
        "step by step",
        "step-by-step",
        "steps",
        "procedure",
        "how do i",
        "how to",
        "walk me through",
        "order",
        "first",
        "then",
        "algorithm",
        "trace",
    ),
    "visual_structural": (
        "diagram",
        "picture",
        "draw",
        "tree",
        "graph",
        "visualize",
        "visual",
        "structure",
        "pointer",
        "rotation",
        "layout",
        "map",
    ),
    "conceptual": (
        "why",
        "intuition",
        "concept",
        "understand",
        "meaning",
        "prove",
        "invariant",
        "theory",
        "difference between",
        "explain the idea",
        "fundamentally",
    ),
}


@dataclass(frozen=True)
class LearningStyleResult:
    learning_style: str
    confidence: float
    matched_cues: list[str]
    backend: str


def infer_learning_style(text: str) -> dict[str, object]:
    backend = os.getenv("OFFICEHOURS_LEARNING_STYLE_BACKEND", "rules").strip().lower()
    if backend == "ml":
        from app.ai.ml_learning_style import classify_learning_style_ml

        return classify_learning_style_ml(text)

    return infer_learning_style_rules(text)


def infer_learning_style_rules(text: str) -> dict[str, object]:
    normalized = re.sub(r"\s+", " ", text.strip().lower())
    if not normalized:
        return _to_dict(
            LearningStyleResult(
                learning_style="unknown",
                confidence=0.0,
                matched_cues=[],
                backend="rules",
            )
        )

    scores: dict[str, list[str]] = {}
    for style, cues in STYLE_CUES.items():
        matched = [cue for cue in cues if cue in normalized]
        if matched:
            scores[style] = matched

    if not scores:
        # Conceptual questions without explicit cues still lean conceptual.
        if any(token in normalized for token in ("confused", "don't get", "do not get", "stuck")):
            return _to_dict(
                LearningStyleResult(
                    learning_style="conceptual",
                    confidence=0.45,
                    matched_cues=["confused/stuck"],
                    backend="rules",
                )
            )
        return _to_dict(
            LearningStyleResult(
                learning_style="unknown",
                confidence=0.25,
                matched_cues=[],
                backend="rules",
            )
        )

    best_style = max(scores, key=lambda style: (len(scores[style]), style))
    matched = scores[best_style]
    confidence = min(0.95, round(0.5 + 0.12 * len(matched), 2))
    return _to_dict(
        LearningStyleResult(
            learning_style=best_style,
            confidence=confidence,
            matched_cues=matched,
            backend="rules",
        )
    )


def _to_dict(result: LearningStyleResult) -> dict[str, object]:
    return {
        "learning_style": result.learning_style,
        "learning_style_confidence": result.confidence,
        "learning_style_cues": result.matched_cues,
        "learning_style_backend": result.backend,
    }
