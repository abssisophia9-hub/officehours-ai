import os

os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["OFFICEHOURS_CLUSTERING_BACKEND"] = "lexical"
os.environ["USE_MOCK_CLAUDE"] = "true"
os.environ["OFFICEHOURS_LEARNING_STYLE_BACKEND"] = "rules"

from app.ai.learning_style import infer_learning_style_rules
from app.ai.claude_drafter import draft_with_claude
from app.ai.ml_learning_style import train_learning_style_classifier
from pathlib import Path
import csv


def test_infer_example_driven_style():
    result = infer_learning_style_rules(
        "Can you show me an example of recursion on a small array?"
    )
    assert result["learning_style"] == "example_driven"
    assert result["learning_style_confidence"] > 0.5


def test_infer_step_by_step_style():
    result = infer_learning_style_rules(
        "Please walk me through the steps of merge sort."
    )
    assert result["learning_style"] == "step_by_step"


def test_infer_visual_style():
    result = infer_learning_style_rules(
        "Can you draw the tree structure after deletion?"
    )
    assert result["learning_style"] == "visual_structural"


def test_mock_claude_adapts_to_learning_style():
    draft = draft_with_claude(
        question_text="I need a diagram of pointer updates after rotation.",
        category="conceptual_question",
        tags=["rotation", "pointers"],
        learning_style="visual_structural",
        urgency="medium",
    )
    assert draft["drafter_backend"] == "mock_claude"
    assert "visual" in draft["answer_draft"].lower() or "sketch" in draft["answer_draft"].lower()
    assert draft["student_hint"]


def test_train_learning_style_classifier_on_csv(tmp_path: Path):
    data_path = Path(__file__).resolve().parents[2] / "data" / "labeled_learning_styles.csv"
    texts = []
    labels = []
    with data_path.open(newline="") as handle:
        for row in csv.DictReader(handle):
            texts.append(row["text"])
            labels.append(row["learning_style"])

    model_path = tmp_path / "learning_style_classifier.joblib"
    metrics = train_learning_style_classifier(texts, labels, model_path=model_path)
    assert model_path.exists()
    assert metrics["n_examples"] == len(texts)
    assert metrics["cv_accuracy_mean"] >= 0.7
