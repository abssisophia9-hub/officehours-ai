"""
Custom-trained Matcher model (no external LLM).

Learns which TA should handle a question from silver/gold labels:
question embedding (+ optional category cue) → TA name.

At inference, ranks roster members with the classifier probabilities and
applies a small queue-depth penalty for wait-time estimation.
"""

from __future__ import annotations

import json
import os
from functools import lru_cache
from pathlib import Path
from typing import Any

import joblib
import numpy as np
from sklearn.linear_model import LogisticRegression

from app.ai.ml_classifier import encode_texts

MODEL_DIR = Path(__file__).resolve().parents[2] / "models"
DEFAULT_MODEL_PATH = MODEL_DIR / "matcher_classifier.joblib"
DEFAULT_EMBEDDING_MODEL = "all-MiniLM-L6-v2"


def build_matcher() -> LogisticRegression:
    return LogisticRegression(max_iter=4000, class_weight="balanced", C=2.5)


def train_matcher(
    texts: list[str],
    assigned_tas: list[str],
    *,
    categories: list[str] | None = None,
    model_name: str | None = None,
) -> dict[str, object]:
    embedding_model = model_name or os.getenv(
        "OFFICEHOURS_EMBEDDING_MODEL", DEFAULT_EMBEDDING_MODEL
    )
    enriched = [
        f"{text}\ncategory:{category}" if category else text
        for text, category in zip(texts, categories or [""] * len(texts))
    ]
    features = encode_texts(enriched, embedding_model)
    classifier = build_matcher()
    classifier.fit(features, assigned_tas)
    return {
        "embedding_model": embedding_model,
        "classifier": classifier,
        "labels": sorted(set(assigned_tas)),
        "strategy": "embedding-logreg-ta-matcher",
    }


def save_matcher(bundle: dict[str, object], path: Path = DEFAULT_MODEL_PATH) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(bundle, path)
    return path


@lru_cache(maxsize=1)
def load_matcher(path: str | None = None) -> dict[str, object]:
    model_path = Path(path or os.getenv("OFFICEHOURS_MATCHER_MODEL", DEFAULT_MODEL_PATH))
    if not model_path.exists():
        raise FileNotFoundError(
            f"Matcher model not found at {model_path}. "
            "Run backend/scripts/train_matcher.py first."
        )
    return joblib.load(model_path)


def match_with_model(
    *,
    question_text: str,
    analyzer: dict[str, Any],
    roster: list[dict[str, Any]],
    model_path: str | None = None,
) -> dict[str, Any]:
    if not roster:
        return {
            "assigned_ta": "Unassigned",
            "alternative_ta": None,
            "estimated_wait_minutes": int(analyzer.get("estimated_minutes") or 15),
            "rationale": "No TA roster configured.",
            "backend": "custom_matcher_unassigned",
        }

    try:
        bundle = load_matcher(model_path)
    except FileNotFoundError:
        return _heuristic_match(analyzer, roster)

    from app.ai.ml_classifier import _load_embedder

    category = str(analyzer.get("ml_category") or analyzer.get("category") or "")
    query = f"{question_text}\ncategory:{category}"
    embedder = _load_embedder(str(bundle["embedding_model"]))
    features = np.asarray(embedder.encode([query], show_progress_bar=False))
    classifier: LogisticRegression = bundle["classifier"]
    probabilities = classifier.predict_proba(features)[0]
    classes = list(classifier.classes_)

    roster_by_name = {row["name"]: row for row in roster}
    scored: list[tuple[float, dict[str, Any]]] = []
    for index, name in enumerate(classes):
        ta = roster_by_name.get(name)
        if ta is None or not ta.get("is_available", True):
            continue
        overlap = _tag_overlap(analyzer, ta)
        # Blend classifier score with expertise overlap so topic overlays
        # (hashing, scheduling, …) steer assignment when the model is flat.
        queue_penalty = 0.03 * float(ta.get("queue_depth") or 0)
        scored.append(
            (float(probabilities[index]) + 0.06 * overlap - queue_penalty, ta)
        )

    # Include roster TAs unseen in training with prior from tag overlap.
    for ta in roster:
        if ta["name"] in classes:
            continue
        overlap = _tag_overlap(analyzer, ta)
        scored.append((0.05 * overlap - 0.03 * float(ta.get("queue_depth") or 0), ta))

    if not scored:
        return _heuristic_match(analyzer, roster)

    scored.sort(key=lambda item: item[0], reverse=True)
    primary = scored[0][1]
    alternative = scored[1][1] if len(scored) > 1 else None
    wait = max(
        int(analyzer.get("estimated_minutes") or 15),
        int(analyzer.get("estimated_minutes") or 15) * max(int(primary.get("queue_depth") or 0), 1),
    )
    overlap_note = _tag_overlap(analyzer, primary)
    return {
        "assigned_ta": primary["name"],
        "alternative_ta": alternative["name"] if alternative else None,
        "estimated_wait_minutes": wait,
        "rationale": (
            f"Custom Matcher assigned {primary['name']} "
            f"(trained embedding classifier + expertise overlap {overlap_note} "
            f"+ queue penalty)."
        ),
        "backend": "custom_matcher",
        "confidence": round(float(scored[0][0]), 3),
    }


def _tag_overlap(analyzer: dict[str, Any], ta: dict[str, Any]) -> int:
    tags = {str(tag).lower() for tag in analyzer.get("tags") or []}
    category = str(analyzer.get("ml_category") or analyzer.get("category") or "").lower()
    expertise = {str(tag).lower() for tag in ta.get("expertise_tags") or []}
    return len(tags & expertise) + (1 if category in expertise else 0)


def _heuristic_match(analyzer: dict[str, Any], roster: list[dict[str, Any]]) -> dict[str, Any]:
    scored = []
    for ta in roster:
        score = _tag_overlap(analyzer, ta) * 10 - int(ta.get("queue_depth") or 0)
        scored.append((score, ta))
    scored.sort(key=lambda item: (-item[0], int(item[1].get("queue_depth") or 0)))
    primary = scored[0][1]
    alternative = scored[1][1] if len(scored) > 1 else None
    wait = max(
        int(analyzer.get("estimated_minutes") or 15),
        int(analyzer.get("estimated_minutes") or 15) * max(int(primary.get("queue_depth") or 0), 1),
    )
    return {
        "assigned_ta": primary["name"],
        "alternative_ta": alternative["name"] if alternative else None,
        "estimated_wait_minutes": wait,
        "rationale": "Matcher model missing; used expertise-overlap fallback. Train with scripts/train_matcher.py.",
        "backend": "custom_matcher_fallback",
    }
