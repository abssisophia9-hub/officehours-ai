import csv
from pathlib import Path

from app.ai.classifier import classify, classify_rules
from app.ai.ml_classifier import classify_ml, load_classifier, save_classifier, train_classifier, _load_embedder
from scripts.train_classifier import evaluate_classifier, load_labeled_rows


def test_rule_classifier_matches_original_labeled_dataset():
    dataset_path = Path(__file__).parents[2] / "data" / "labeled_requests.csv"

    with dataset_path.open(newline="") as dataset_file:
        rows = list(csv.DictReader(dataset_file))

    mismatches = [
        (row["request_id"], row["category"], classify_rules(row["text"])["category"])
        for row in rows
        if classify_rules(row["text"])["category"] != row["category"]
    ]

    assert len(rows) == 40
    assert mismatches == []


def test_evaluate_classifier_meets_accuracy_target():
    rows = load_labeled_rows()

    metrics = evaluate_classifier(rows)

    assert metrics["dataset_size"] == 120
    assert metrics["accuracy"] >= 0.8
    assert metrics["macro_f1"] >= 0.75


def test_ml_classifier_trains_and_predicts():
    rows = load_labeled_rows()
    bundle = train_classifier(
        [row["text"] for row in rows],
        [row["category"] for row in rows],
    )

    embedder_model = bundle["embedding_model"]
    from app.ai.ml_classifier import _load_embedder
    import numpy as np

    features = np.asarray(
        _load_embedder(str(embedder_model)).encode(
            ["Can someone explain recursion versus iteration on the final?"],
            show_progress_bar=False,
        )
    )
    prediction = bundle["classifier"].predict(features)[0]

    assert prediction == "conceptual_question"


def test_classify_ml_backend_shape(tmp_path, monkeypatch):
    rows = load_labeled_rows()
    model_path = tmp_path / "request_classifier.joblib"

    save_classifier(
        train_classifier([row["text"] for row in rows], [row["category"] for row in rows]),
        model_path,
    )
    load_classifier.cache_clear()
    _load_embedder.cache_clear()
    monkeypatch.setenv("OFFICEHOURS_CLASSIFIER_MODEL", str(model_path))

    result = classify_ml("Where is the final exam room posted?")

    assert result["category"] == "exam_logistics"
    assert result["classifier_backend"] == "ml"
    assert result["confidence"] > 0.0


def test_classify_respects_ml_backend_env(tmp_path, monkeypatch):
    rows = load_labeled_rows()
    model_path = tmp_path / "request_classifier.joblib"

    save_classifier(
        train_classifier([row["text"] for row in rows], [row["category"] for row in rows]),
        model_path,
    )
    load_classifier.cache_clear()
    _load_embedder.cache_clear()
    monkeypatch.setenv("OFFICEHOURS_CLASSIFIER_BACKEND", "ml")
    monkeypatch.setenv("OFFICEHOURS_CLASSIFIER_MODEL", str(model_path))

    result = classify("I need a makeup exam because of a scheduling conflict.")

    assert result["category"] == "retake_request"
    assert result["classifier_backend"] == "ml"
