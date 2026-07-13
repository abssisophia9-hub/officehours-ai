import os

os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["OFFICEHOURS_CLUSTERING_BACKEND"] = "lexical"
os.environ["OFFICEHOURS_ANALYZER_BACKEND"] = "ml"
os.environ["OFFICEHOURS_ALLOW_EXTERNAL_LLM"] = "false"

from pathlib import Path

from app.ai.analyzer_agent import analyze_with_classifier
from app.ai.ml_classifier import load_classifier, save_classifier, train_classifier, _load_embedder
from scripts.train_classifier import load_labeled_rows


def test_analyzer_uses_ml_classifier_by_default(tmp_path, monkeypatch):
    rows = load_labeled_rows()
    model_path = tmp_path / "request_classifier.joblib"
    save_classifier(
        train_classifier([row["text"] for row in rows], [row["category"] for row in rows]),
        model_path,
    )
    load_classifier.cache_clear()
    _load_embedder.cache_clear()
    monkeypatch.setenv("OFFICEHOURS_CLASSIFIER_MODEL", str(model_path))
    monkeypatch.setenv("OFFICEHOURS_ANALYZER_BACKEND", "ml")

    result = analyze_with_classifier(
        question_text=(
            "I'm getting infinite recursion in my red-black tree delete fixup. "
            "Rotation isn't balancing properly."
        ),
        code_snippet="def delete_fixup(self, node): ...",
        course="CS 400",
    )

    assert result["backend"] == "ml_classifier"
    assert result["ml_category"] in {
        "conceptual_question",
        "project_submission",
        "uncategorized",
    }
    assert result["category"] == "Red-Black Tree Deletion"
    assert "trees" in result["tags"] or "red-black" in result["tags"]
    assert result["difficulty"] in {"EASY", "MEDIUM", "HARD"}
    assert result["estimated_minutes"] >= 8
    assert result["confidence"] >= 0.0


def test_analyzer_rules_backend(monkeypatch):
    monkeypatch.setenv("OFFICEHOURS_ANALYZER_BACKEND", "rules")
    result = analyze_with_classifier(
        question_text="Where is the final exam room posted?",
    )
    assert result["backend"] == "rules"
    assert result["ml_category"] == "exam_logistics"


def test_existing_model_file_is_loadable():
    model_path = Path(__file__).resolve().parents[1] / "models" / "request_classifier.joblib"
    if not model_path.exists():
        return
    load_classifier.cache_clear()
    bundle = load_classifier(str(model_path))
    assert "classifier" in bundle
    assert "embedding_model" in bundle
