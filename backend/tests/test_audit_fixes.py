"""Regression locks for the five audit upgrades."""

import os

os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["OFFICEHOURS_CLUSTERING_BACKEND"] = "lexical"
os.environ["OFFICEHOURS_ALLOW_EXTERNAL_LLM"] = "false"

from fastapi.testclient import TestClient

from app.database.session import Base, engine
from app.main import app
from app.services.canvas_service import _extract_live_canvas_file
from app.services.material_extract import extract_material_text
from tests.helpers import alice_auth, professor_auth, student_auth
from tests.test_material_uploads import _minimal_pdf

client = TestClient(app)


def setup_function():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def test_materials_default_to_pending_review():
    headers, course_id = professor_auth(client)
    response = client.post(
        "/knowledge/materials",
        headers=headers,
        json={
            "title": "Week 2 stacks",
            "content": "A stack is LIFO. Push adds to the top. Pop removes from the top.",
            "course_id": course_id,
            "course": "CSC 2302",
            "source": "slides",
        },
    )
    assert response.status_code == 201
    entry_id = response.json()["entry_ids"][0]
    entry = client.get(f"/knowledge/{entry_id}", headers=headers).json()
    assert entry["status"] == "pending_review"

    student, sid = student_auth(client, "CSC 2302")
    miss = client.post(
        "/agent/ask",
        headers=student,
        json={"question": "What is a stack LIFO?", "course_id": sid},
    ).json()
    assert miss["should_seek_help"] is True


def test_alice_gold_pass_seeds_twenty_labels():
    headers, course_id = alice_auth(client)
    rows = client.get(
        f"/analytics/gold-labels?course_id={course_id}",
        headers=headers,
    ).json()
    assert len(rows) >= 20
    assert all(row["labeled_by"] == "a.chen@aui.ma" for row in rows)
    assert {row["label_source"] for row in rows} == {"human_gold"}


def test_ta_can_submit_gold_label():
    headers, course_id = alice_auth(client)
    created = client.post(
        "/analytics/gold-labels",
        headers=headers,
        json={
            "text": "Why does my queue using two stacks reverse the order?",
            "gold_category": "conceptual_question",
            "course_id": course_id,
            "course_code": "CSC 2302",
            "department": "CSC",
            "gold_hint_useful": 0,
        },
    )
    assert created.status_code == 201
    assert created.json()["labeled_by"] == "a.chen@aui.ma"


def test_live_canvas_extracts_pdf_bytes():
    pdf = _minimal_pdf("Open addressing stores colliding keys in the next free slot.")
    captured = {}

    def fake_bytes(url, headers):
        captured["url"] = url
        return pdf

    import app.services.canvas_service as canvas_service

    original = canvas_service._canvas_get_bytes
    canvas_service._canvas_get_bytes = fake_bytes
    try:
        text = _extract_live_canvas_file(
            "week4.pdf",
            "https://canvas.example/files/1/download",
            {},
        )
    finally:
        canvas_service._canvas_get_bytes = original
    assert text
    assert "open addressing" in text.lower()
    assert captured["url"].endswith("/download")


def test_pdf_extractor_still_works_for_manual_upload():
    pdf = _minimal_pdf("Memoization caches each subproblem once.")
    text, source = extract_material_text("notes.pdf", pdf)
    assert source == "slides"
    assert "memoization" in text.lower()
