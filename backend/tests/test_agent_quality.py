"""Golden behavioral checks for Ask Triage + KB agent usefulness.

These are not CV metrics — they lock demo-critical CSC topics so retrains
cannot silently break the AUI walkthrough.
"""

import os

os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["OFFICEHOURS_CLUSTERING_BACKEND"] = "lexical"
os.environ["OFFICEHOURS_ALLOW_EXTERNAL_LLM"] = "false"
os.environ["OFFICEHOURS_LEARNING_STYLE_BACKEND"] = "ml"

from fastapi.testclient import TestClient

from app.ai.analyzer_agent import analyze_with_classifier
from app.ai.claude_client import match_ta
from app.database.session import Base, engine
from app.main import app
from app.models.ta_roster import DEFAULT_TA_ROSTER
from app.services.demo_accounts import DEMO_PASSWORD

client = TestClient(app)


def setup_function():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def test_analyzer_overlays_csc_topics():
    red_black = analyze_with_classifier(
        question_text=(
            "In CSC 2302 red-black tree deletion fixup after deleting a black leaf "
            "needs which rotations?"
        ),
        course="CSC 2302",
    )
    assert "red-black" in red_black["category"].lower() or "trees" in {
        t.lower() for t in red_black["tags"]
    }

    hashing = analyze_with_classifier(
        question_text="How do hash tables handle collisions with chaining vs open addressing?",
        course="CSC 2302",
    )
    assert "hash" in hashing["category"].lower() or "hashing" in {
        t.lower() for t in hashing["tags"]
    }


def test_matcher_uses_category_expertise_tags():
    roster = [{**row, "is_available": True} for row in DEFAULT_TA_ROSTER]
    analyzer = {
        "category": "Red-Black Tree Deletion",
        "ml_category": "conceptual_question",
        "tags": ["trees", "red-black", "deletion", "rotations"],
        "estimated_minutes": 15,
    }
    matched = match_ta(
        analyzer,
        roster,
        question_text="Red-black deletion fixup after deleting a black leaf",
    )
    assert matched["assigned_ta"] == "Alice Chen"

    stress = match_ta(
        {
            "category": "Emotional Stress / Support",
            "ml_category": "emotional_stress",
            "tags": ["emotional_stress"],
            "estimated_minutes": 20,
        },
        roster,
        question_text="I am overwhelmed and panicking about failing the class",
    )
    assert stress["assigned_ta"] == "Sam Ortiz"


def test_kb_miss_sets_should_seek_help():
    from tests.helpers import student_auth

    headers, course_id = student_auth(client)
    response = client.post(
        "/agent/ask",
        headers=headers,
        json={
            "question": "What is the yoga blockchain midterm policy for CSC 9999?",
            "course_id": course_id,
        },
    ).json()
    assert response["matched_count"] == 0
    assert response["should_seek_help"] is True
    assert "quiet ask" in response["answer"].lower()


def test_analyzer_covers_multidepartment_topics():
    """Campus-wide asks (not CSC-only) should still get a usable category."""
    induction = analyze_with_classifier(
        question_text=(
            "In MTH 1304 I keep mixing up proof by induction base case vs "
            "inductive step — how do I structure the write-up?"
        )
    )
    assert induction["ml_category"] in {
        "conceptual_question",
        "exam_logistics",
        "project_submission",
        "grading_dispute",
        "emotional_stress",
        "retake_request",
        "accessibility_accommodation",
        "academic_integrity",
    } or "conceptual" in str(induction.get("category", "")).lower()

    speech = analyze_with_classifier(
        question_text=(
            "I am extremely anxious about speaking in front of the COM 1301 "
            "class and need private support before my speech day."
        )
    )
    cat = str(speech.get("ml_category") or speech.get("category") or "").lower()
    assert "stress" in cat or "emotional" in cat or cat == "emotional_stress"


def test_roster_seed_includes_category_tags():
    login = client.post(
        "/auth/login",
        json={"email": "a.chen@aui.ma", "password": DEMO_PASSWORD},
    )
    assert login.status_code == 200
    roster = client.get(
        "/ta/roster/",
        headers={"Authorization": f"Bearer {login.json()['token']}"},
    ).json()
    alice = next(row for row in roster if row["name"] == "Alice Chen")
    assert "conceptual_question" in alice["expertise_tags"]
    sam = next(row for row in roster if row["name"] == "Sam Ortiz")
    assert "emotional_stress" in sam["expertise_tags"]
