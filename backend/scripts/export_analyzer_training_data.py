"""
Export Analyzer training rows from labeled CSVs + professor-approved KB.

Run from `backend/`:
    python3 scripts/export_analyzer_training_data.py
"""

from __future__ import annotations

import csv
import json
import os
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]
BACKEND_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT_DIR / "data"
OUT_PATH = DATA_DIR / "analyzer_training_export.csv"

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

os.environ.setdefault("DATABASE_URL", "sqlite:///./officehours.db")
os.environ.setdefault("OFFICEHOURS_CLUSTERING_BACKEND", "lexical")

from app.database.session import SessionLocal  # noqa: E402
from app.models.knowledge import KnowledgeEntry  # noqa: E402
from scripts.train_classifier import load_labeled_rows  # noqa: E402


def export_rows() -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for row in load_labeled_rows(DATA_DIR):
        rows.append(
            {
                "text": row["text"],
                "category": row["category"],
                "source": row.get("label_source") or "labeled_csv",
            }
        )

    db = SessionLocal()
    try:
        approved = (
            db.query(KnowledgeEntry)
            .filter(KnowledgeEntry.status == "approved")
            .order_by(KnowledgeEntry.id)
            .all()
        )
        for entry in approved:
            if not entry.question_text or not entry.category:
                continue
            # Map Ask Triage display topics back to taxonomy when possible.
            category = _normalize_category(entry.category)
            rows.append(
                {
                    "text": entry.question_text,
                    "category": category,
                    "source": "professor_approved_kb",
                }
            )
    finally:
        db.close()

    return rows


def _normalize_category(raw: str) -> str:
    lowered = raw.strip().lower().replace(" ", "_").replace("-", "_")
    aliases = {
        "conceptual_question": "conceptual_question",
        "conceptual": "conceptual_question",
        "exam_logistics": "exam_logistics",
        "retake_request": "retake_request",
        "grading_dispute": "grading_dispute",
        "emotional_stress": "emotional_stress",
        "project_submission": "project_submission",
        "accessibility_accommodation": "accessibility_accommodation",
        "office_hours_access": "office_hours_access",
        "academic_integrity": "academic_integrity",
        "red_black_tree_deletion": "conceptual_question",
        "recursion": "conceptual_question",
        "binary_search": "conceptual_question",
        "dynamic_programming": "conceptual_question",
    }
    if lowered in aliases:
        return aliases[lowered]
    if "tree" in lowered or "recursion" in lowered or "search" in lowered:
        return "conceptual_question"
    return "uncategorized" if lowered not in {
        "conceptual_question",
        "exam_logistics",
        "retake_request",
        "accessibility_accommodation",
        "grading_dispute",
        "emotional_stress",
        "project_submission",
        "office_hours_access",
        "academic_integrity",
    } else lowered


def main() -> None:
    rows = export_rows()
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUT_PATH.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["text", "category", "source"])
        writer.writeheader()
        writer.writerows(rows)

    counts: dict[str, int] = {}
    for row in rows:
        counts[row["category"]] = counts.get(row["category"], 0) + 1

    print(
        json.dumps(
            {
                "exported_rows": len(rows),
                "output": str(OUT_PATH),
                "category_counts": counts,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
