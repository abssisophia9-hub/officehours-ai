"""Unit tests for custom Matcher / Synthesizer models (no Claude)."""

import os
from pathlib import Path

os.environ["OFFICEHOURS_CLUSTERING_BACKEND"] = "lexical"
os.environ["OFFICEHOURS_ALLOW_EXTERNAL_LLM"] = "false"

from app.ai.matcher_model import match_with_model, save_matcher, train_matcher
from app.ai.ml_classifier import _load_embedder
from app.ai.synthesizer_model import (
    draft_kb_with_model,
    load_synthesizer,
    save_synthesizer,
    synthesize_with_model,
    train_synthesizer_ranker,
)


ROSTER = [
    {
        "id": 1,
        "name": "Alice Chen",
        "expertise_tags": ["trees", "red-black", "conceptual_question"],
        "queue_depth": 1,
        "is_available": True,
    },
    {
        "id": 2,
        "name": "Bob Martinez",
        "expertise_tags": ["recursion", "dp"],
        "queue_depth": 2,
        "is_available": True,
    },
]


def test_train_and_match_custom_matcher(tmp_path, monkeypatch):
    texts = [
        "Red-black tree rotation after delete fixup is broken.",
        "How do rotations restore the black-height invariant?",
        "I need help tracing a recursive fibonacci call stack.",
        "Explain memoization vs plain recursion on knapsack.",
        "Why does my BST delete not rebalance like red-black?",
        "Dynamic programming recurrence for coin change.",
    ]
    labels = [
        "Alice Chen",
        "Alice Chen",
        "Bob Martinez",
        "Bob Martinez",
        "Alice Chen",
        "Bob Martinez",
    ]
    categories = [
        "conceptual_question",
        "conceptual_question",
        "conceptual_question",
        "conceptual_question",
        "conceptual_question",
        "conceptual_question",
    ]
    model_path = tmp_path / "matcher_classifier.joblib"
    bundle = train_matcher(texts, labels, categories=categories)
    save_matcher(bundle, model_path)
    monkeypatch.setenv("OFFICEHOURS_MATCHER_MODEL", str(model_path))
    from app.ai.matcher_model import load_matcher

    load_matcher.cache_clear()
    _load_embedder.cache_clear()

    result = match_with_model(
        question_text="My red-black delete fixup rotation never terminates.",
        analyzer={
            "ml_category": "conceptual_question",
            "category": "Red-Black Tree Deletion",
            "tags": ["trees", "red-black"],
            "estimated_minutes": 15,
        },
        roster=ROSTER,
        model_path=str(model_path),
    )
    assert result["assigned_ta"] == "Alice Chen"
    assert result["backend"] == "custom_matcher"
    assert "claude" not in result["backend"]


def test_synthesizer_uses_teaching_bank_without_claude(tmp_path, monkeypatch):
    bank = Path(__file__).resolve().parents[2] / "data" / "synthesizer_teaching_bank.csv"
    if not bank.exists():
        return
    texts = [
        "example driven recursion tracing",
        "step by step binary search",
        "visual tree rotation diagram",
        "conceptual invariant explanation",
    ]
    styles = [
        "example_driven",
        "step_by_step",
        "visual_structural",
        "conceptual",
    ]
    model_path = tmp_path / "synthesizer_ranker.joblib"
    save_synthesizer(train_synthesizer_ranker(texts, styles), model_path)
    monkeypatch.setenv("OFFICEHOURS_SYNTHESIZER_MODEL", str(model_path))
    monkeypatch.setenv("OFFICEHOURS_TEACHING_BANK", str(bank))
    load_synthesizer.cache_clear()
    _load_embedder.cache_clear()
    from app.ai.synthesizer_model import _bank_embeddings

    _bank_embeddings.cache_clear()

    result = synthesize_with_model(
        question_text="Can you show an example of recursion tracing on a small input?",
        analyzer={
            "ml_category": "conceptual_question",
            "category": "Recursion",
            "tags": ["recursion"],
            "urgency": "medium",
        },
        similar_questions=[],
        learning_style="example_driven",
        model_path=str(model_path),
    )
    assert result["student_hint"]
    assert result["teaching_approach"]
    assert "claude" not in result["backend"]
    assert "custom_synthesizer" in result["backend"]

    draft = draft_kb_with_model(
        question_text="Please walk through binary search steps.",
        category="conceptual_question",
        tags=["search"],
        learning_style="step_by_step",
    )
    assert "claude" not in draft["drafter_backend"]
    assert draft["answer_draft"]
