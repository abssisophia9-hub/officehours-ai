#!/usr/bin/env python3
"""Train the custom Matcher classifier (no external LLM).

Silver labels: data/matcher_training.csv
  columns: text, category, assigned_ta, alternative_ta, source

Usage (from backend/):
  venv/bin/python scripts/train_matcher.py
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

from sklearn.metrics import accuracy_score, f1_score

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.ai.matcher_model import (  # noqa: E402
    DEFAULT_MODEL_PATH,
    load_matcher,
    save_matcher,
    train_matcher,
)
from app.ai.ml_classifier import _load_embedder, encode_texts  # noqa: E402


def load_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def load_matcher_rows(data_path: Path) -> list[dict[str, str]]:
    """Load matcher CSV plus CSC and multi-department supplements beside it."""
    rows = load_csv(data_path)
    for name in ("matcher_training_csc.csv", "matcher_training_multidept.csv"):
        extra = data_path.parent / name
        if extra.exists() and extra != data_path:
            rows.extend(load_csv(extra))
    deduped: list[dict[str, str]] = []
    seen: set[str] = set()
    for row in rows:
        key = row.get("text", "").strip()
        if not key or key in seen:
            continue
        seen.add(key)
        deduped.append(row)
    return deduped


def main() -> int:
    parser = argparse.ArgumentParser(description="Train OfficeHours Matcher model")
    parser.add_argument(
        "--data",
        type=Path,
        default=ROOT.parent / "data" / "matcher_training.csv",
    )
    parser.add_argument("--out", type=Path, default=DEFAULT_MODEL_PATH)
    parser.add_argument("--holdout", type=float, default=0.2)
    args = parser.parse_args()

    rows = load_matcher_rows(args.data)
    if len(rows) < 8:
        raise SystemExit(f"Need at least 8 labeled examples, found {len(rows)}")

    by_label: dict[str, list[dict[str, str]]] = {}
    for row in rows:
        by_label.setdefault(row["assigned_ta"].strip(), []).append(row)

    train_rows: list[dict[str, str]] = []
    test_rows: list[dict[str, str]] = []
    for items in by_label.values():
        n_test = max(1, int(round(len(items) * args.holdout))) if len(items) >= 5 else 0
        test_rows.extend(items[:n_test])
        train_rows.extend(items[n_test:])

    if not train_rows:
        train_rows = rows
        test_rows = []

    bundle = train_matcher(
        [row["text"].strip() for row in train_rows],
        [row["assigned_ta"].strip() for row in train_rows],
        categories=[row.get("category", "").strip() for row in train_rows],
    )
    path = save_matcher(bundle, args.out)
    load_matcher.cache_clear()
    _load_embedder.cache_clear()

    metrics: dict[str, object] = {"n": len(test_rows), "accuracy": None, "macro_f1": None}
    if test_rows:
        texts = [
            f"{row['text'].strip()}\ncategory:{row.get('category', '').strip()}"
            for row in test_rows
        ]
        features = encode_texts(texts, str(bundle["embedding_model"]))
        preds = list(bundle["classifier"].predict(features))
        labels = [row["assigned_ta"].strip() for row in test_rows]
        metrics = {
            "n": len(test_rows),
            "accuracy": round(float(accuracy_score(labels, preds)), 4),
            "macro_f1": round(
                float(f1_score(labels, preds, average="macro", zero_division=0)),
                4,
            ),
            "label_note": "silver_or_csc_or_multidept_supplement — not gold TA judgments",
        }

    report = {
        "model_path": str(path),
        "train_n": len(train_rows),
        "test_n": len(test_rows),
        "labels": sorted({row["assigned_ta"].strip() for row in rows}),
        "metrics": metrics,
    }
    report_dir = ROOT.parent / "reports" / "final_report"
    report_dir.mkdir(parents=True, exist_ok=True)
    report_path = report_dir / "matcher_evaluation.json"
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    print(f"Wrote {report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
