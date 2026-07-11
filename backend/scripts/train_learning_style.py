"""
Train the learning-style classifier on labeled CSV data.

Run from `backend/`:
    OFFICEHOURS_CLUSTERING_BACKEND=lexical python3 scripts/train_learning_style.py
"""

from __future__ import annotations

import csv
import json
import os
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]
BACKEND_DIR = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT_DIR / "data" / "labeled_learning_styles.csv"
REPORT_PATH = ROOT_DIR / "reports" / "final_report" / "learning_style_evaluation.json"

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

os.environ.setdefault("OFFICEHOURS_CLUSTERING_BACKEND", "lexical")

from app.ai.ml_learning_style import train_learning_style_classifier


def load_rows(path: Path = DATA_PATH) -> tuple[list[str], list[str]]:
    texts: list[str] = []
    labels: list[str] = []
    with path.open(newline="") as handle:
        for row in csv.DictReader(handle):
            texts.append(row["text"].strip())
            labels.append(row["learning_style"].strip())
    return texts, labels


def main() -> None:
    texts, labels = load_rows()
    metrics = train_learning_style_classifier(texts, labels)
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(metrics, indent=2) + "\n")
    print(json.dumps(metrics, indent=2))
    print(f"Wrote {REPORT_PATH}")


if __name__ == "__main__":
    main()
