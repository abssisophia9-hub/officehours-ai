"""Professors can see each uploaded file and whether it is still waiting."""

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


def _upload(headers, course_id, name, pages):
    pdf = _multipage_pdf(pages)
    response = client.post(
        "/knowledge/materials/upload",
        headers=headers,
        data={"course_id": str(course_id), "auto_approve": "false"},
        files={"file": (name, pdf, "application/pdf")},
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_upload_list_groups_one_row_per_file_and_tracks_status():
    headers, course_id = _professor()
    empty = client.get(
        f"/knowledge/uploads?course_id={course_id}",
        headers=headers,
    )
    assert empty.status_code == 200
    assert empty.json() == []

    first = _upload(
        headers,
        course_id,
        "lab-notes.pdf",
        [
            "Zephyr valves open when the copper kettle reaches a rolling boil.",
            "Lantern buffers store spare wicks for the night lab.",
        ],
    )
    second = _upload(
        headers,
        course_id,
        "week-two.pdf",
        ["Hash tables map keys into buckets with separate chaining."],
    )

    listed = client.get(
        f"/knowledge/uploads?course_id={course_id}",
        headers=headers,
    )
    assert listed.status_code == 200, listed.text
    rows = listed.json()
    assert [row["filename"] for row in rows] == ["week-two.pdf", "lab-notes.pdf"]
    by_name = {row["filename"]: row for row in rows}
    notes = by_name["lab-notes.pdf"]
    assert notes["upload_id"] == first["upload_id"]
    assert notes["chunk_count"] == 2
    assert notes["pending_count"] == 2
    assert notes["status"] == "pending"
    assert notes["uploaded_at"]
    assert by_name["week-two.pdf"]["upload_id"] == second["upload_id"]
    assert by_name["week-two.pdf"]["chunk_count"] == 1

    patched = client.patch(
        f"/knowledge/{first['entry_ids'][0]}",
        headers=headers,
        json={"status": "approved"},
    )
    assert patched.status_code == 200
    mixed = client.get(
        f"/knowledge/uploads?course_id={course_id}",
        headers=headers,
    ).json()
    notes = next(row for row in mixed if row["filename"] == "lab-notes.pdf")
    assert notes["status"] == "partly_approved"
    assert notes["approved_count"] == 1
    assert notes["pending_count"] == 1

    approved = client.post(
        f"/knowledge/uploads/{first['upload_id']}/approve",
        headers=headers,
    )
    assert approved.status_code == 200
    assert approved.json()["approved_count"] == 2
    after = client.get(
        f"/knowledge/uploads?course_id={course_id}",
        headers=headers,
    ).json()
    notes = next(row for row in after if row["upload_id"] == first["upload_id"])
    assert notes["status"] == "approved"
    assert notes["approved_count"] == 2

    rejected = client.post(
        f"/knowledge/uploads/{second['upload_id']}/reject",
        headers=headers,
    )
    assert rejected.status_code == 200
    assert rejected.json()["rejected_count"] == 1
    final = client.get(
        f"/knowledge/uploads?course_id={course_id}",
        headers=headers,
    ).json()
    week = next(row for row in final if row["upload_id"] == second["upload_id"])
    assert week["status"] == "rejected"
    assert week["rejected_count"] == 1


def test_students_and_tas_cannot_list_or_reject_uploads():
    headers, course_id = _professor()
    uploaded = _upload(
        headers,
        course_id,
        "lab-notes.pdf",
        ["Lantern buffers store spare wicks for the night lab."],
    )
    student_headers, _ = student_auth(client, "CSC 2302")
    ta_headers, _ = alice_auth(client, "CSC 2302")
    assert (
        client.get(
            f"/knowledge/uploads?course_id={course_id}",
            headers=student_headers,
        ).status_code
        == 403
    )
    assert (
        client.get(
            f"/knowledge/uploads?course_id={course_id}",
            headers=ta_headers,
        ).status_code
        == 403
    )
    assert (
        client.post(
            f"/knowledge/uploads/{uploaded['upload_id']}/reject",
            headers=student_headers,
        ).status_code
        == 403
    )
    missing = client.post(
        "/knowledge/uploads/does-not-exist/reject",
        headers=headers,
    )
    assert missing.status_code == 404
