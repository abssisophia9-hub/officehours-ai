"""One professor call approves every chunk from an upload.

auto_approve stays available only while OFFICEHOURS_DEMO is on, which is
how the existing suite and the local FYP helper run.
"""

import os

os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["OFFICEHOURS_CLUSTERING_BACKEND"] = "lexical"
os.environ["OFFICEHOURS_DEMO"] = "true"

from fastapi.testclient import TestClient

from app.database.session import Base, engine
from app.main import app
from tests.helpers import alice_auth, student_auth
from tests.test_material_uploads import _multipage_pdf, _professor

client = TestClient(app)


def setup_function():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def _upload_two_pages(headers, course_id, *, auto_approve: str = "false"):
    pdf = _multipage_pdf(
        [
            "Zephyr valves open when the copper kettle reaches a rolling boil.",
            "Lantern buffers store spare wicks for the night lab.",
        ]
    )
    return client.post(
        "/knowledge/materials/upload",
        headers=headers,
        data={
            "course_id": str(course_id),
            "title": "Demo lab notes",
            "auto_approve": auto_approve,
        },
        files={"file": ("lab-notes.pdf", pdf, "application/pdf")},
    )


def test_one_call_approves_every_chunk_of_an_upload():
    headers, course_id = _professor()
    uploaded = _upload_two_pages(headers, course_id)
    assert uploaded.status_code == 201, uploaded.text
    body = uploaded.json()
    assert body["chunks_created"] == 2
    upload_id = body["upload_id"]
    assert upload_id

    for entry_id in body["entry_ids"]:
        entry = client.get(f"/knowledge/{entry_id}", headers=headers).json()
        assert entry["status"] == "pending_review"

    student_headers, _ = student_auth(client, "CSC 2302")
    blocked = client.post(
        "/agent/ask",
        headers=student_headers,
        json={
            "question": "What do lantern buffers store for the night lab?",
            "course_id": course_id,
        },
    ).json()
    assert blocked["should_seek_help"] is True

    approved = client.post(
        f"/knowledge/uploads/{upload_id}/approve",
        headers=headers,
    )
    assert approved.status_code == 200, approved.text
    assert approved.json() == {
        "upload_id": upload_id,
        "course_id": course_id,
        "approved_count": 2,
    }
    for entry_id in body["entry_ids"]:
        entry = client.get(f"/knowledge/{entry_id}", headers=headers).json()
        assert entry["status"] == "approved"

    answer = client.post(
        "/agent/ask",
        headers=student_headers,
        json={
            "question": "What do lantern buffers store for the night lab?",
            "course_id": course_id,
        },
    ).json()
    assert answer["matched_count"] >= 1
    assert answer["answer"].startswith("Lantern buffers store spare wicks for the night lab.")
    assert "based on lab-notes.pdf, p.2 approved by the professor" in answer["answer"]


def test_student_and_ta_cannot_approve_an_upload():
    headers, course_id = _professor()
    upload_id = _upload_two_pages(headers, course_id).json()["upload_id"]
    student_headers, _ = student_auth(client, "CSC 2302")
    ta_headers, _ = alice_auth(client, "CSC 2302")
    assert (
        client.post(
            f"/knowledge/uploads/{upload_id}/approve",
            headers=student_headers,
        ).status_code
        == 403
    )
    assert (
        client.post(
            f"/knowledge/uploads/{upload_id}/approve",
            headers=ta_headers,
        ).status_code
        == 403
    )
    missing = client.post(
        "/knowledge/uploads/does-not-exist/approve",
        headers=headers,
    )
    assert missing.status_code == 404


def test_auto_approve_rejected_when_demo_mode_is_off(monkeypatch):
    headers, course_id = _professor()
    monkeypatch.setenv("OFFICEHOURS_DEMO", "false")
    uploaded = _upload_two_pages(headers, course_id, auto_approve="true")
    assert uploaded.status_code == 400
    assert "OFFICEHOURS_DEMO" in uploaded.json()["detail"]
    listed = client.get(
        f"/knowledge/?course_id={course_id}",
        headers=headers,
    ).json()
    assert listed == []

    pasted = client.post(
        "/knowledge/materials",
        headers=headers,
        json={
            "title": "Week 4 Hashing",
            "content": "Hash tables map keys to buckets with separate chaining.",
            "course_id": course_id,
            "source": "slides",
            "auto_approve": True,
        },
    )
    assert pasted.status_code == 400
    assert client.get(f"/knowledge/?course_id={course_id}", headers=headers).json() == []
