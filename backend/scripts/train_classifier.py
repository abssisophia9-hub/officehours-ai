"""
Train and evaluate the Analyzer's fine-tuned small classifier.

Uses labeled CSV fixtures (and optionally professor-approved exports).
Matcher and Synthesizer have separate training scripts.

Run from `backend/`:
    python3 scripts/train_classifier.py
"""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
)
from sklearn.model_selection import StratifiedKFold, cross_val_predict

ROOT_DIR = Path(__file__).resolve().parents[2]
BACKEND_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT_DIR / "data"
REPORT_DIR = ROOT_DIR / "reports" / "final_report"
MODEL_PATH = BACKEND_DIR / "models" / "request_classifier.joblib"

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.ai.ml_classifier import build_classifier, encode_texts, save_classifier, train_classifier  # noqa: E402


def load_labeled_rows(data_dir: Path = DATA_DIR) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for filename in (
        "labeled_requests.csv",
        "labeled_requests_extended.csv",
        "labeled_requests_extra.csv",
    ):
        path = data_dir / filename
        if not path.exists():
            continue
        with path.open(newline="") as handle:
            rows.extend(list(csv.DictReader(handle)))
    return rows


def evaluate_classifier(rows: list[dict[str, str]]) -> dict[str, object]:
    texts = [row["text"] for row in rows]
    categories = [row["category"] for row in rows]
    labels = sorted(set(categories))
    min_class_count = min(categories.count(label) for label in labels)
    n_splits = min(5, min_class_count)
    if n_splits < 2:
        raise ValueError("Need at least two examples per class for cross-validation.")

    features = encode_texts(texts)
    classifier = build_classifier()
    cv = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=42)
    predictions = cross_val_predict(classifier, features, categories, cv=cv)

    report = classification_report(
        categories,
        predictions,
        labels=labels,
        output_dict=True,
        zero_division=0,
    )

    return {
        "dataset_size": len(rows),
        "labels": labels,
        "cv_folds": n_splits,
        "accuracy": round(accuracy_score(categories, predictions), 4),
        "macro_f1": round(f1_score(categories, predictions, average="macro"), 4),
        "weighted_f1": round(f1_score(categories, predictions, average="weighted"), 4),
        "classification_report": report,
        "confusion_matrix": {
            "labels": labels,
            "matrix": confusion_matrix(categories, predictions, labels=labels).tolist(),
        },
        "source_files": [
            "data/labeled_requests.csv",
            "data/labeled_requests_extended.csv",
            "data/labeled_requests_extra.csv",
        ],
        "feature_backend": "sentence-transformer-embeddings + logistic regression",
    }


def main() -> None:
    rows = load_labeled_rows()
    metrics = evaluate_classifier(rows)

    bundle = train_classifier([row["text"] for row in rows], [row["category"] for row in rows])
    save_classifier(bundle, MODEL_PATH)

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    metrics_path = REPORT_DIR / "classifier_evaluation.json"
    metrics_path.write_text(json.dumps(metrics, indent=2), encoding="utf-8")

    markdown_path = REPORT_DIR / "classifier_evaluation.md"
    markdown_path.write_text(_render_markdown(metrics), encoding="utf-8")

    print(json.dumps(metrics, indent=2))
    print(f"\nSaved model to {MODEL_PATH}")
    print(f"Saved metrics to {metrics_path}")


def _render_markdown(metrics: dict[str, object]) -> str:
    lines = [
        "# Classifier Evaluation Summary",
        "",
        f"- Dataset size: {metrics['dataset_size']}",
        f"- Cross-validation folds: {metrics['cv_folds']}",
        f"- Feature backend: {metrics['feature_backend']}",
        f"- Accuracy: **{metrics['accuracy']}**",
        f"- Macro F1: **{metrics['macro_f1']}**",
        f"- Weighted F1: **{metrics['weighted_f1']}**",
        "",
        "## Source files",
        "",
    ]
    for source in metrics["source_files"]:
        lines.append(f"- `{source}`")
    lines.append("")
    return "\n".join(lines)


if __name__ == "__main__":
    main()
