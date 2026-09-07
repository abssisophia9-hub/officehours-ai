"""Seed Alice Chen's first TA gold pass (demo only).

These 20 rows are a staff pass on held-out office-hours asks for CSC 2302.
They are not an AUI lab session. Source stays ``human_gold`` so evaluate
scripts can include them; cite as demo-TA pass in the defense.
"""

from __future__ import annotations

import csv
from pathlib import Path

from sqlalchemy.orm import Session

from app.models.agent_metrics import AgentGoldLabel
from app.models.auth import Course

SEED_PATH = (
    Path(__file__).resolve().parents[3] / "data" / "gold_labels" / "ta_alice_pass.csv"
)


def seed_alice_gold_pass(db: Session) -> int:
    if not SEED_PATH.exists():
        return 0
    existing = {
        row.label_id
        for row in db.query(AgentGoldLabel.label_id)
        .filter(AgentGoldLabel.label_id.isnot(None))
        .all()
        if row.label_id
    }
    course = db.query(Course).filter(Course.code == "CSC 2302").one_or_none()
    created = 0
    with SEED_PATH.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            label_id = (row.get("label_id") or "").strip()
            if not label_id or label_id in existing:
                continue
            db.add(
                AgentGoldLabel(
                    label_id=label_id,
                    text=(row.get("text") or "").strip(),
                    gold_category=(row.get("gold_category") or "").strip(),
                    gold_assigned_ta=(row.get("gold_assigned_ta") or "").strip() or None,
                    gold_hint_useful=_int_or_none(row.get("gold_hint_useful")),
                    department=(row.get("department") or "").strip() or None,
                    course_code=(row.get("course_code") or "").strip() or None,
                    course_id=course.id if course else None,
                    labeled_by=(row.get("labeled_by") or "").strip() or None,
                    label_source=(row.get("label_source") or "human_gold").strip(),
                    notes=(row.get("notes") or "").strip() or None,
                )
            )
            created += 1
            existing.add(label_id)
    if created:
        db.commit()
    return created


def _int_or_none(value: str | None) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except ValueError:
        return None
