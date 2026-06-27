"""
Request classification logic.

This starts with a deterministic rule-based classifier so the API can classify
requests without loading heavyweight ML models at runtime. The public
``classify`` function can later be backed by embeddings or a trained model
without changing route/service callers.
"""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class ClassificationResult:
    category: str
    urgency: str
    confidence: float
    matched_keywords: list[str]


CATEGORY_KEYWORDS: dict[str, tuple[str, ...]] = {
    "emotional_stress": (
        "overwhelmed",
        "panic",
        "panicking",
        "scared",
        "afraid",
        "cannot focus",
        "can't focus",
        "not slept",
        "fail the class",
        "feel stuck",
        "stuck",
        "study plan",
        "six hours",
        "stressed",
        "stress",
    ),
    "retake_request": (
        "makeup",
        "make-up",
        "retake",
        "exam conflict",
        "conflicts with",
        "religious observance",
        "medical documentation",
        "sick",
    ),
    "accessibility_accommodation": (
        "accommodation",
        "extra time",
        "disability",
        "accessibility",
    ),
    "grading_dispute": (
        "grade",
        "score",
        "points",
        "rubric",
        "appeal",
        "late penalty",
        "recheck",
        "partial credit",
    ),
    "academic_integrity": (
        "academic integrity",
        "similarity report",
        "plagiarism",
        "honor code",
    ),
    "project_submission": (
        "project",
        "autograder",
        "hidden tests",
        "demo",
        "report",
        "screenshots",
        "submitted the wrong file",
        "presentation",
        "team member",
    ),
    "office_hours_access": (
        "office hours",
        "office hour",
        "slots filled",
        "extended",
        "register",
    ),
    "exam_logistics": (
        "final exam",
        "exam room",
        "cumulative",
        "midterm",
        "do we need to memorize",
        "memorize",
        "reference table",
        "closed book",
        "notes page",
        "coding by hand",
        "multiple choice",
        "start",
        "grace period",
        "recorded",
        "practice final",
    ),
    "conceptual_question": (
        "explain",
        "explanation",
        "understand",
        "confused",
        "recursion",
        "binary search",
        "dynamic programming",
        "bfs",
        "dfs",
        "dijkstra",
        "graph",
        "sorting",
        "runtime",
        "sql",
        "joins",
        "derivative",
        "integration",
        "hypothesis",
        "confidence interval",
        "cache",
        "memory hierarchy",
        "prove",
        "algorithm",
    ),
}

CATEGORY_PRIORITY = (
    "emotional_stress",
    "accessibility_accommodation",
    "retake_request",
    "academic_integrity",
    "grading_dispute",
    "project_submission",
    "office_hours_access",
    "exam_logistics",
    "conceptual_question",
)

HIGH_URGENCY_CATEGORIES = {
    "accessibility_accommodation",
    "retake_request",
    "academic_integrity",
}

HIGH_URGENCY_KEYWORDS = (
    "today",
    "tomorrow",
    "emergency",
    "deadline",
    "urgent",
    "cannot",
    "can't",
    "missed",
)


def classify(text: str) -> dict[str, object]:
    """
    Classify request text into an initial category with confidence metadata.
    """
    normalized_text = _normalize(text)
    if not normalized_text:
        result = ClassificationResult(
            category="uncategorized",
            urgency="low",
            confidence=0.0,
            matched_keywords=[],
        )
        return _to_dict(result)

    matches_by_category = {
        category: _matched_keywords(normalized_text, keywords)
        for category, keywords in CATEGORY_KEYWORDS.items()
    }
    category = _best_category(matches_by_category)
    matched_keywords = matches_by_category.get(category, [])

    if category == "uncategorized":
        result = ClassificationResult(
            category=category,
            urgency="low",
            confidence=0.2,
            matched_keywords=[],
        )
        return _to_dict(result)

    result = ClassificationResult(
        category=category,
        urgency=_infer_urgency(category, normalized_text),
        confidence=_confidence(len(matched_keywords)),
        matched_keywords=matched_keywords,
    )
    return _to_dict(result)


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip().lower())


def _matched_keywords(text: str, keywords: tuple[str, ...]) -> list[str]:
    return [keyword for keyword in keywords if keyword in text]


def _best_category(matches_by_category: dict[str, list[str]]) -> str:
    best_score = 0
    best_category = "uncategorized"

    for category in CATEGORY_PRIORITY:
        score = len(matches_by_category.get(category, []))
        if score > best_score:
            best_score = score
            best_category = category

    return best_category


def _infer_urgency(category: str, text: str) -> str:
    if category == "emotional_stress":
        return "urgent" if any(word in text for word in ("panic", "fail", "not slept")) else "high"

    if category in HIGH_URGENCY_CATEGORIES:
        return "high"

    if any(keyword in text for keyword in HIGH_URGENCY_KEYWORDS):
        return "medium"

    return "medium" if category in {"conceptual_question", "project_submission"} else "low"


def _confidence(match_count: int) -> float:
    return min(0.95, round(0.55 + (0.1 * match_count), 2))


def _to_dict(result: ClassificationResult) -> dict[str, object]:
    return {
        "category": result.category,
        "urgency": result.urgency,
        "confidence": result.confidence,
        "matched_keywords": result.matched_keywords,
    }
