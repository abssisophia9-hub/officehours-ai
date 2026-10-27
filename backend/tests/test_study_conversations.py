"""Study Agent conversations stay with the student after a refresh."""

import os

os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["OFFICEHOURS_CLUSTERING_BACKEND"] = "lexical"
os.environ["OFFICEHOURS_DEMO"] = "true"

from fastapi.testclient import TestClient

from app.database.session import Base, engine
from app.main import app
from tests.helpers import login, professor_auth, student_auth

client = TestClient(app)


def setup_function():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def test_student_keeps_a_conversation_and_a_second_student_cannot_read_it():
    sara, course_id = student_auth(client, "CSC 2302")
    created = client.post(
        "/study-conversations",
        headers=sara,
        json={"course_id": course_id},
    )
    assert created.status_code == 201
    conversation_id = created.json()["id"]
    assert created.json()["title"] == "New chat"

    again = client.post(
        "/study-conversations",
        headers=sara,
        json={"course_id": course_id},
    )
    assert again.json()["id"] == conversation_id

    saved = client.post(
        f"/study-conversations/{conversation_id}/messages",
        headers=sara,
        json={"role": "student", "text": "How many mugs a circular queue holds?"},
    )
    assert saved.status_code == 201
    assert saved.json()["title"] == "How many mugs a circular queue holds?"

    answer = client.post(
        f"/study-conversations/{conversation_id}/messages",
        headers=sara,
        json={
            "role": "agent",
            "text": "At most eight mugs.\nbased on demo_kettle_notes.pdf, p.2 approved by the professor",
            "sources": [{"entry": {"source_filename": "demo_kettle_notes.pdf", "page_number": 2}}],
        },
    )
    assert answer.status_code == 201

    listed = client.get(f"/study-conversations?course_id={course_id}", headers=sara)
    assert listed.status_code == 200
    assert listed.json()[0]["title"] == "How many mugs a circular queue holds?"

    detail = client.get(f"/study-conversations/{conversation_id}", headers=sara)
    assert [row["role"] for row in detail.json()["messages"]] == ["student", "agent"]
    assert detail.json()["messages"][1]["sources"][0]["entry"]["page_number"] == 2

    fresh = client.post(
        "/study-conversations",
        headers=sara,
        json={"course_id": course_id},
    )
    attached = client.post(
        f"/study-conversations/{fresh.json()['id']}/messages",
        headers=sara,
        json={
            "role": "student",
            "text": "What does the sample print?\nAttached: greet.py",
        },
    )
    assert attached.status_code == 201
    assert attached.json()["title"] == "What does the sample print?"
    assert "Attached:" in attached.json()["message"]["text"]

    youssef, _youssef = login(client, "y.amrani@aui.ma")
    hidden = client.get(f"/study-conversations/{conversation_id}", headers=youssef)
    assert hidden.status_code == 404

    professor, _professor_course = professor_auth(client, "CSC 2302")
    blocked = client.post(
        "/study-conversations",
        headers=professor,
        json={"course_id": course_id},
    )
    assert blocked.status_code == 403
