"""Build a learner dossier from how the student asks, what they ask, and style."""

from __future__ import annotations

from collections import Counter

from sqlalchemy.orm import Session

from app.ai.learning_style import LEARNING_STYLES, infer_learning_style
from app.ai.summarizer import extract_keywords
from app.models.request import Request
from app.models.strategist import AskSampleOut, LearnerDossierOut

STYLE_LABELS = {
    "visual_structural": "visual / structural — diagrams, animations, maps",
    "step_by_step": "step-by-step — ordered procedures and traces",
    "example_driven": "example-driven — worked problems and concrete cases",
    "conceptual": "conceptual — intuition and why, not just how",
    "unknown": "not enough asks yet to lock a style",
}


def build_learner_dossier(
    db: Session,
    *,
    user_id: int,
    course_id: int,
) -> LearnerDossierOut:
    rows = (
        db.query(Request)
        .filter(
            Request.created_by_user_id == user_id,
            Request.course_id == course_id,
        )
        .order_by(Request.created_at.desc())
        .limit(40)
        .all()
    )
    style_counts: Counter[str] = Counter()
    help_modes: Counter[str] = Counter()
    samples: list[AskSampleOut] = []
    texts: list[str] = []
    tag_bag: list[str] = []

    for row in rows:
        raw_style = (row.learning_style or "").strip().lower()
        if raw_style not in LEARNING_STYLES or raw_style == "unknown":
            inferred = infer_learning_style(row.text or "")
            raw_style = str(inferred.get("learning_style") or "unknown")
        if raw_style and raw_style != "unknown":
            style_counts[raw_style] += 1
        help_modes[(row.help_mode or "message")] += 1
        tags = _split_tags(row.triage_tags)
        tag_bag.extend(tags)
        texts.append(row.text or "")
        if len(samples) < 5 and (row.text or "").strip():
            samples.append(
                AskSampleOut(
                    text=(row.text or "").strip()[:240],
                    learning_style=raw_style or None,
                    category=row.triage_category or row.category,
                    tags=tags[:6],
                )
            )

    dominant = "unknown"
    if style_counts:
        dominant = style_counts.most_common(1)[0][0]

    keywords = extract_keywords(texts, max_keywords=6) if texts else []
    struggles = _unique([*keywords, *tag_bag])[:8]
    how = _how_they_ask(dominant, help_modes, texts)

    return LearnerDossierOut(
        dominant_style=dominant,
        style_counts=dict(style_counts),
        struggles=struggles,
        how_they_ask=how,
        ask_count=len(rows),
        help_modes=dict(help_modes),
        ask_samples=samples,
    )


def _split_tags(raw: str | None) -> list[str]:
    if not raw:
        return []
    return [part.strip() for part in raw.replace(";", ",").split(",") if part.strip()]


def _unique(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        key = item.strip().lower()
        if not key or key in seen:
            continue
        seen.add(key)
        out.append(item.strip())
    return out


def _how_they_ask(style: str, help_modes: Counter[str], texts: list[str]) -> str:
    style_bit = STYLE_LABELS.get(style, STYLE_LABELS["unknown"])
    mode = help_modes.most_common(1)[0][0] if help_modes else "message"
    mode_bit = {
        "message": "prefers a written reply",
        "face_to_face": "asks to meet in person",
        "online_meeting": "asks for a remote call",
    }.get(mode, "files tickets as messages")
    if not texts:
        return f"{style_bit}. No asks in this course yet — {mode_bit}."
    return f"{style_bit}. From {len(texts)} ask(s): {mode_bit}."
