"""Study Agent conversations stay with the student after a refresh."""

import os

os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["OFFICEHOURS_CLUSTERING_BACKEND"] = "lexical"
os.environ["OFFICEHOURS_DEMO"] = "true"

from fastapi.testclient import TestClient

from app.database.session import Base, SessionLocal, engine
from app.main import app
from app.models.agent_metrics import KbAskEvent
from app.models.knowledge import AgentAskResponse
from app.models.study_conversation import StudyMessage
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


def test_academic_support_turn_runs_agent_and_persists_both_messages(monkeypatch):
    sara, course_id = student_auth(client, "CSC 2302")
    created = client.post(
        "/study-conversations",
        headers=sara,
        json={"course_id": course_id},
    )
    conversation_id = created.json()["id"]
    captured = {}

    def fake_answer(db, question, **kwargs):
        captured["question"] = question
        captured["course_id"] = kwargs["course_id"]
        captured["user_id"] = kwargs["user_id"]
        captured.setdefault("histories", []).append(kwargs["session_history"])
        return AgentAskResponse(
            answer="A bounded answer.",
            confidence=0.9,
            matched_count=1,
            sources=[],
            should_seek_help=False,
        )

    monkeypatch.setattr(
        "app.routes.academic_support.answer_from_knowledge_base",
        fake_answer,
    )
    response = client.post(
        f"/academic-support/conversations/{conversation_id}/turns",
        headers=sara,
        json={"question": "How does the queue wrap?"},
    )
    assert response.status_code == 201, response.text
    assert response.json()["message"]["text"] == "A bounded answer."
    assert captured["course_id"] == course_id
    assert captured["histories"][0] == []

    second = client.post(
        f"/academic-support/conversations/{conversation_id}/turns",
        headers=sara,
        json={"question": "And when is it full?"},
    )
    assert second.status_code == 201
    assert captured["histories"][1] == [
        {"role": "student", "text": "How does the queue wrap?"},
        {"role": "agent", "text": "A bounded answer."},
    ]

    youssef, _ = login(client, "y.amrani@aui.ma")
    hidden = client.post(
        f"/academic-support/conversations/{conversation_id}/turns",
        headers=youssef,
        json={"question": "Can I use this chat?"},
    )
    assert hidden.status_code == 404

    db = SessionLocal()
    try:
        messages = (
            db.query(StudyMessage)
            .filter(StudyMessage.conversation_id == conversation_id)
            .order_by(StudyMessage.id)
            .all()
        )
        assert [(row.role, row.text) for row in messages] == [
            ("student", "How does the queue wrap?"),
            ("agent", "A bounded answer."),
            ("student", "And when is it full?"),
            ("agent", "A bounded answer."),
        ]
        assert db.query(KbAskEvent).filter(KbAskEvent.course_id == course_id).count() == 2
    finally:
        db.close()
