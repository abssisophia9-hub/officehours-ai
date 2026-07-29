"""Per-course KB hit-rate + human gold labels + multi-department coverage."""

import os

os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["OFFICEHOURS_CLUSTERING_BACKEND"] = "lexical"
os.environ["OFFICEHOURS_ALLOW_EXTERNAL_LLM"] = "false"

from pathlib import Path

from fastapi.testclient import TestClient

from app.database.session import Base, engine
from app.main import app
from app.services.demo_accounts import DEMO_PASSWORD

ROOT = Path(__file__).resolve().parents[2]
client = TestClient(app)


def setup_function():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def _login_professor():
    return client.post(
        "/auth/login",
        json={"email": "a.benali@aui.ma", "password": DEMO_PASSWORD},
    ).json()["token"]


def test_kb_hit_rate_is_tracked_per_course():
    token = _login_professor()
    courses = client.get(
        "/courses/mine", headers={"Authorization": f"Bearer {token}"}
    ).json()
    course_id = courses[0]["id"]

    miss = client.post(
        "/agent/ask",
        json={
            "question": "What is the yoga blockchain midterm policy for this course?",
            "course_id": course_id,
        },
    ).json()
    assert miss["should_seek_help"] is True

    ingest = client.post(
        "/knowledge/materials",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "course_id": course_id,
            "title": "RB trees",
            "content": (
                "Red-black deletion fixup restores black-height with recolor "
                "and rotations after deleting a black leaf. Students should "
                "draw the smallest broken tree before applying fixup cases."
            ),
            "auto_approve": True,
        },
    )
    assert ingest.status_code in {200, 201}, ingest.text

    client.post(
        "/agent/ask",
        json={
            "question": "How does red-black deletion fixup restore black-height?",
            "course_id": course_id,
        },
    )

    report = client.get("/analytics/kb-hit-rate").json()
    assert report["total_asks"] >= 2
    course_row = next(
        row for row in report["by_course"] if row["course_id"] == course_id
    )
    assert course_row["asks"] >= 2
    assert "hit_rate" in course_row


def test_gold_label_api_roundtrip():
    created = client.post(
        "/analytics/gold-labels",
        json={
            "text": "How do I structure an induction proof base case vs inductive step?",
            "gold_category": "conceptual_question",
            "gold_assigned_ta": "Alice Chen",
            "gold_hint_useful": 1,
            "department": "MTH",
            "course_code": "MTH 1304",
            "labeled_by": "a.chen@aui.ma",
        },
    )
    assert created.status_code == 201
    body = created.json()
    assert body["gold_category"] == "conceptual_question"
    assert body["department"] == "MTH"

    listed = client.get("/analytics/gold-labels?department=MTH").json()
    assert any(row["id"] == body["id"] for row in listed)


def test_multidept_training_files_exist():
    data = ROOT / "data"
    assert (data / "labeled_requests_multidept.csv").exists()
    assert (data / "matcher_training_multidept.csv").exists()
    assert (data / "synthesizer_teaching_bank_multidept.csv").exists()
    assert (data / "gold_labels" / "gold_labels.csv").exists()
    text = (data / "labeled_requests_multidept.csv").read_text(encoding="utf-8")
    assert "MTH" in text and "COM" in text and "ECO" in text


def test_evaluate_gold_labels_script_runs():
    import sys

    sys.path.insert(0, str(ROOT / "backend"))
    from scripts.evaluate_gold_labels import evaluate, load_gold_csv

    rows = load_gold_csv(ROOT / "data" / "gold_labels" / "gold_labels.csv")
    assert len(rows) >= 10
    report = evaluate(rows)
    assert report["n_labels"] >= 10
    assert report["analyzer"]["n"] >= 10
    assert "by_department" in report
