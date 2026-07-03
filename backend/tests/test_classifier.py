import csv
from pathlib import Path

from app.ai.classifier import classify, classify_rules
from app.services.classification_service import classify_and_recommend


def test_classify_conceptual_question():
    result = classify(
        "I am confused about recursion and binary search loop boundaries."
    )

    assert result["category"] == "conceptual_question"
    assert result["urgency"] == "medium"
    assert result["confidence"] > 0.5
    assert "recursion" in result["matched_keywords"]


def test_classify_emotional_stress_as_urgent():
    result = classify("I am panicking and scared I will fail the class.")

    assert result["category"] == "emotional_stress"
    assert result["urgency"] == "urgent"


def test_classify_and_recommend_exam_logistics():
    result = classify_and_recommend(
        "Is the final exam cumulative, and can we bring a notes page?"
    )

    assert result["category"] == "exam_logistics"
    assert result["recommended_action"] == "Post or update a final-exam FAQ response"


def test_classify_and_recommend_grading_dispute():
    result = classify_and_recommend(
        "My project score is missing points and I want the rubric reviewed."
    )

    assert result["category"] == "grading_dispute"
    assert result["recommended_action"] == "Route to grading review workflow"


def test_rule_classifier_matches_synthetic_labeled_dataset():
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
