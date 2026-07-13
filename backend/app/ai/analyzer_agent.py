"""
Oracle Analyzer agent backed by a fine-tuned small classifier.

Default path:
  sentence-transformer embeddings + logistic regression (``ml_classifier``)

Optional overlays:
  - keyword/topic labels for richer Oracle display names
  - TF-IDF tags, difficulty / ETA heuristics

FYP path uses custom-trained models only (no prompted Claude / mocks).
"""

from __future__ import annotations

import os
from typing import Any

from app.ai.ml_classifier import classify_ml, load_classifier
from app.ai.summarizer import extract_keywords

# Map trained taxonomy labels → Oracle UI labels.
CATEGORY_DISPLAY = {
    "conceptual_question": "Conceptual Question",
    "exam_logistics": "Exam Logistics",
    "retake_request": "Retake / Makeup Request",
    "accessibility_accommodation": "Accessibility Accommodation",
    "grading_dispute": "Grading Dispute",
    "emotional_stress": "Emotional Stress / Support",
    "project_submission": "Project Submission",
    "office_hours_access": "Office Hours Access",
    "academic_integrity": "Academic Integrity",
    "uncategorized": "General CS",
}

DIFFICULTY_BY_URGENCY = {
    "urgent": "HARD",
    "high": "HARD",
    "medium": "MEDIUM",
    "low": "EASY",
}

ETA_BY_CATEGORY = {
    "conceptual_question": 15,
    "exam_logistics": 8,
    "retake_request": 12,
    "accessibility_accommodation": 15,
    "grading_dispute": 20,
    "emotional_stress": 20,
    "project_submission": 18,
    "office_hours_access": 10,
    "academic_integrity": 25,
    "uncategorized": 15,
}

# Optional topic overlays for demo-friendly Analyzer titles (does not replace ML label).
TOPIC_OVERLAYS: list[tuple[tuple[str, ...], str, list[str]]] = [
    (
        ("red-black", "red black", "rb tree", "delete_fixup", "rotation"),
        "Red-Black Tree Deletion",
        ["trees", "red-black", "deletion", "rotations"],
    ),
    (
        ("binary search", "sorted array"),
        "Binary Search",
        ["search", "arrays", "invariants"],
    ),
    (
        ("recursion", "base case"),
        "Recursion",
        ["recursion", "base-case", "call-stack"],
    ),
    (
        ("dynamic programming", "memoization", " dp "),
        "Dynamic Programming",
        ["dp", "memoization", "subproblems"],
    ),
]


def analyze_with_classifier(
    *,
    question_text: str,
    code_snippet: str | None = None,
    course: str | None = None,
) -> dict[str, Any]:
    """
    Run the Analyzer agent.

    Backend selection (``OFFICEHOURS_ANALYZER_BACKEND``):
      - ``ml`` (default): fine-tuned embedding + logistic regression classifier
      - ``rules``: keyword rules only
      - ``claude``: blocked unless ``OFFICEHOURS_ALLOW_EXTERNAL_LLM=true``
    """
    backend = os.getenv("OFFICEHOURS_ANALYZER_BACKEND", "ml").strip().lower()
    combined = _combine(question_text, code_snippet)

    if backend == "claude":
        allow = os.getenv("OFFICEHOURS_ALLOW_EXTERNAL_LLM", "false").strip().lower()
        if allow not in {"1", "true", "yes", "on"}:
            raise RuntimeError(
                "Claude Analyzer is disabled for FYP (custom models required). "
                "Use OFFICEHOURS_ANALYZER_BACKEND=ml."
            )
        from app.ai import claude_client_legacy as legacy

        return legacy.analyze_question_llm(
            question_text=question_text,
            code_snippet=code_snippet,
            course=course,
        )

    if backend == "rules":
        from app.ai.classifier import classify_rules

        ml_like = classify_rules(combined)
        return _to_analyzer_payload(
            ml_like,
            question_text=question_text,
            code_snippet=code_snippet,
            course=course,
            backend="rules",
        )

    # Default: fine-tuned small classifier, with rules fallback if model missing.
    try:
        load_classifier()
        prediction = classify_ml(combined)
        return _to_analyzer_payload(
            prediction,
            question_text=question_text,
            code_snippet=code_snippet,
            course=course,
            backend="ml_classifier",
        )
    except FileNotFoundError:
        from app.ai.classifier import classify_rules

        prediction = classify_rules(combined)
        payload = _to_analyzer_payload(
            prediction,
            question_text=question_text,
            code_snippet=code_snippet,
            course=course,
            backend="rules_fallback",
        )
        payload["rationale"] = (
            "ML Analyzer model missing; fell back to rules. "
            "Train with `python scripts/train_classifier.py`."
        )
        return payload


def _to_analyzer_payload(
    prediction: dict[str, Any],
    *,
    question_text: str,
    code_snippet: str | None,
    course: str | None,
    backend: str,
) -> dict[str, Any]:
    category = str(prediction.get("category") or "uncategorized")
    urgency = str(prediction.get("urgency") or "medium").lower()
    confidence = float(prediction.get("confidence") or 0.0)
    combined = _combine(question_text, code_snippet)

    topic_label, topic_tags = _topic_overlay(combined)
    display_category = topic_label or CATEGORY_DISPLAY.get(
        category, category.replace("_", " ").title()
    )

    tags = list(prediction.get("matched_keywords") or [])
    tags.extend(topic_tags)
    tags.extend(extract_keywords([combined], max_keywords=4))
    if course:
        tags.append(course.lower().replace(" ", "-"))
    tags = list(dict.fromkeys([tag for tag in tags if tag]))[:8]

    estimated = ETA_BY_CATEGORY.get(category, 15)
    if urgency in {"high", "urgent"}:
        estimated = max(estimated, 15)

    return {
        "category": display_category,
        "ml_category": category,
        "difficulty": DIFFICULTY_BY_URGENCY.get(urgency, "MEDIUM"),
        "estimated_minutes": estimated,
        "tags": tags,
        "urgency": urgency,
        "confidence": round(confidence, 3),
        "rationale": (
            f"Fine-tuned Analyzer predicted `{category}` "
            f"(confidence {confidence:.2f})"
            + (f"; topic overlay `{topic_label}`" if topic_label else "")
            + "."
        ),
        "backend": backend,
    }


def _topic_overlay(text: str) -> tuple[str | None, list[str]]:
    lowered = f" {text.lower()} "
    for needles, label, tags in TOPIC_OVERLAYS:
        if any(needle in lowered for needle in needles):
            return label, list(tags)
    return None, []


def _combine(question_text: str, code_snippet: str | None) -> str:
    parts = [question_text.strip()]
    if code_snippet and code_snippet.strip():
        parts.append(code_snippet.strip())
    return "\n\n".join(parts)
