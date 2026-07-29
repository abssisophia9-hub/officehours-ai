#!/usr/bin/env python3
"""Evaluate Analyzer + Matcher against human gold labels.

Loads ``data/gold_labels/gold_labels.csv`` (and optionally DB rows) and reports
accuracy / macro-F1. Gold labels are the quality bar — silver training metrics
are not a substitute.

Usage (from ``backend/``):

    OFFICEHOURS_CLUSTERING_BACKEND=lexical \\
      venv/bin/python scripts/evaluate_gold_labels.py

    # Include labels submitted via POST /analytics/gold-labels
    OFFICEHOURS_CLUSTERING_BACKEND=lexical \\
      venv/bin/python scripts/evaluate_gold_labels.py --include-db
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

os.environ.setdefault("OFFICEHOURS_CLUSTERING_BACKEND", "lexical")

from sklearn.metrics import accuracy_score, f1_score  # noqa: E402

from app.ai.analyzer_agent import analyze_with_classifier  # noqa: E402
from app.ai.claude_client import match_ta  # noqa: E402
from app.models.ta_roster import DEFAULT_TA_ROSTER  # noqa: E402


DEFAULT_GOLD_CSV = REPO / "data" / "gold_labels" / "gold_labels.csv"
REPORT_PATH = REPO / "reports" / "final_report" / "gold_label_evaluation.json"


def load_gold_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def load_gold_from_db() -> list[dict[str, str]]:
    from app.database.session import SessionLocal
    from app.models.agent_metrics import AgentGoldLabel

    db = SessionLocal()
    try:
        rows = db.query(AgentGoldLabel).order_by(AgentGoldLabel.id).all()
        return [
            {
                "label_id": row.label_id or f"DB{row.id}",
                "text": row.text,
                "gold_category": row.gold_category,
                "gold_assigned_ta": row.gold_assigned_ta or "",
                "gold_hint_useful": str(row.gold_hint_useful or ""),
                "department": row.department or "",
                "course_code": row.course_code or "",
                "labeled_by": row.labeled_by or "",
                "label_source": row.label_source,
            }
            for row in rows
        ]
    finally:
        db.close()


def _safe_macro_f1(y_true: list[str], y_pred: list[str]) -> float | None:
    if not y_true:
        return None
    return round(f1_score(y_true, y_pred, average="macro", zero_division=0), 4)


def evaluate(rows: list[dict[str, str]]) -> dict[str, object]:
    if not rows:
        raise SystemExit("No gold labels found.")

    roster = [{**row, "is_available": True} for row in DEFAULT_TA_ROSTER]
    gold_categories: list[str] = []
    pred_categories: list[str] = []
    gold_tas: list[str] = []
    pred_tas: list[str] = []
    by_dept: Counter[str] = Counter()
    category_errors: list[dict[str, str]] = []
    matcher_errors: list[dict[str, str]] = []

    for row in rows:
        text = (row.get("text") or "").strip()
        if not text:
            continue
        gold_cat = (row.get("gold_category") or "").strip()
        gold_ta = (row.get("gold_assigned_ta") or "").strip()
        dept = (row.get("department") or "UNK").strip() or "UNK"
        by_dept[dept] += 1

        analyzer = analyze_with_classifier(question_text=text)
        pred_cat = str(
            analyzer.get("ml_category") or analyzer.get("category") or ""
        ).strip()
        if gold_cat:
            gold_categories.append(gold_cat)
            pred_categories.append(pred_cat)
            if pred_cat != gold_cat:
                category_errors.append(
                    {
                        "label_id": row.get("label_id", ""),
                        "department": dept,
                        "gold": gold_cat,
                        "predicted": pred_cat,
                        "text": text[:160],
                    }
                )

        if gold_ta:
            matched = match_ta(analyzer, roster, question_text=text)
            pred_ta = str(matched.get("assigned_ta") or "").strip()
            gold_tas.append(gold_ta)
            pred_tas.append(pred_ta)
            if pred_ta != gold_ta:
                matcher_errors.append(
                    {
                        "label_id": row.get("label_id", ""),
                        "department": dept,
                        "gold": gold_ta,
                        "predicted": pred_ta,
                        "text": text[:160],
                    }
                )

    report = {
        "n_labels": len(rows),
        "by_department": dict(by_dept),
        "analyzer": {
            "n": len(gold_categories),
            "accuracy": (
                round(accuracy_score(gold_categories, pred_categories), 4)
                if gold_categories
                else None
            ),
            "macro_f1": _safe_macro_f1(gold_categories, pred_categories),
            "errors_sample": category_errors[:12],
        },
        "matcher": {
            "n": len(gold_tas),
            "accuracy": (
                round(accuracy_score(gold_tas, pred_tas), 4) if gold_tas else None
            ),
            "macro_f1": _safe_macro_f1(gold_tas, pred_tas),
            "errors_sample": matcher_errors[:12],
            "label_note": "Compared against human gold_assigned_ta — not silver holdout",
        },
        "source": "data/gold_labels/gold_labels.csv (+ optional DB)",
        "note": (
            "Seed gold is illustrative. Replace with real TA judgments before "
            "claiming production agent quality."
        ),
    }
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate agents on gold labels")
    parser.add_argument("--gold", type=Path, default=DEFAULT_GOLD_CSV)
    parser.add_argument("--include-db", action="store_true")
    parser.add_argument("--out", type=Path, default=REPORT_PATH)
    args = parser.parse_args()

    rows = load_gold_csv(args.gold)
    if args.include_db:
        rows.extend(load_gold_from_db())

    # De-dupe by label_id then text
    deduped: list[dict[str, str]] = []
    seen: set[str] = set()
    for row in rows:
        key = (row.get("label_id") or "").strip() or (row.get("text") or "").strip()
        if not key or key in seen:
            continue
        seen.add(key)
        deduped.append(row)

    report = evaluate(deduped)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    print(f"\nWrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
