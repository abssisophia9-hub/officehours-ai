"""Staff-triggered evaluate + optional joblib retrain from gold labels."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy.orm import Session

from app.models.agent_metrics import AgentGoldLabel

REPO = Path(__file__).resolve().parents[3]
BACKEND = REPO / "backend"


def allow_retrain() -> bool:
    return os.getenv("OFFICEHOURS_ALLOW_RETRAIN", "").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def export_course_gold(db: Session, *, course_id: int | None) -> list[dict[str, str]]:
    query = db.query(AgentGoldLabel).order_by(AgentGoldLabel.id)
    if course_id is not None:
        query = query.filter(AgentGoldLabel.course_id == course_id)
    rows = query.all()
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


def run_retrain(
    db: Session, *, course_id: int | None, apply_models: bool
) -> dict:
    import importlib.util

    eval_path = BACKEND / "scripts" / "evaluate_gold_labels.py"
    spec = importlib.util.spec_from_file_location("evaluate_gold_labels", eval_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    evaluate = module.evaluate
    load_gold_csv = module.load_gold_csv

    gold_csv = REPO / "data" / "gold_labels" / "gold_labels.csv"
    rows = load_gold_csv(gold_csv)
    rows.extend(export_course_gold(db, course_id=course_id))
    deduped: list[dict[str, str]] = []
    seen: set[str] = set()
    for row in rows:
        key = (row.get("label_id") or "").strip() or (row.get("text") or "").strip()
        if not key or key in seen:
            continue
        seen.add(key)
        deduped.append(row)

    if not deduped:
        return {
            "n_labels": 0,
            "applied_models": False,
            "message": "No gold labels to evaluate.",
        }

    report = evaluate(deduped)
    report["applied_models"] = False
    report["evaluated_at"] = datetime.now(timezone.utc).isoformat()
    report["course_id"] = course_id
    report["message"] = (
        "Evaluated gold labels. Joblib files were not rewritten. "
        "Set OFFICEHOURS_ALLOW_RETRAIN=true and apply_models to retrain Analyzer."
    )

    if apply_models and allow_retrain():
        script = BACKEND / "scripts" / "train_classifier.py"
        result = subprocess.run(
            [sys.executable, str(script)],
            cwd=str(BACKEND),
            capture_output=True,
            text=True,
            timeout=180,
            check=False,
        )
        report["applied_models"] = result.returncode == 0
        report["train_exit"] = result.returncode
        report["message"] = (
            "Analyzer retrain finished."
            if result.returncode == 0
            else f"Retrain failed: {(result.stderr or result.stdout)[:400]}"
        )

    if not os.getenv("PYTEST_CURRENT_TEST"):
        out = REPO / "reports" / "final_report" / "gold_label_evaluation.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report
