"""Study-agent retrieval flags stay on the service layer.

Filtered defaults hide pending rows and other courses. Plain mode
(approved_only=False, course_scoped=False) can see both. FAQ drafts from
student asks stay out of the study agent either way.
"""

import os

os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["OFFICEHOURS_CLUSTERING_BACKEND"] = "lexical"

from fastapi.testclient import TestClient

from app.database.session import Base, SessionLocal, engine
from app.main import app
from app.models.knowledge import KnowledgeEntry
from app.services.kb_agent_service import answer_from_knowledge_base
from app.services.knowledge_service import search_approved_entries
from tests.helpers import professor_auth, student_auth

client = TestClient(app)

ZEPHYR = (
    "Zephyr valves open when the copper kettle reaches a rolling boil."
)
ZEPHYR_QUESTION = "When do zephyr valves open on the copper kettle?"
LANTERN = "Lantern buffers store spare wicks for the night lab."
LANTERN_QUESTION = "What do lantern buffers store for the night lab?"


def setup_function():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def _add_entry(**kwargs) -> int:
    db = SessionLocal()
    try:
        entry = KnowledgeEntry(
            student_hint="Demo chunk.",
            category=kwargs.pop("category", "course_material"),
            tags="[]",
            **kwargs,
        )
        db.add(entry)
        db.commit()
        db.refresh(entry)
        return entry.id
    finally:
        db.close()


def test_plain_mode_sees_pending_row_filtered_mode_does_not():
    _, course_id = student_auth(client)
    _add_entry(
        question_text="Zephyr valves — part 1",
        answer_draft=ZEPHYR,
        status="pending_review",
        course_id=course_id,
        entry_kind="course_material",
        material_source="slides",
    )
    db = SessionLocal()
    try:
        filtered = answer_from_knowledge_base(db, ZEPHYR_QUESTION, course_id=course_id)
        plain = answer_from_knowledge_base(
            db,
            ZEPHYR_QUESTION,
            course_id=course_id,
            approved_only=False,
            course_scoped=True,
        )
    finally:
        db.close()
    assert filtered.matched_count == 0
    assert filtered.should_seek_help is True
    assert plain.matched_count >= 1
    assert plain.should_seek_help is False
    assert "zephyr" in plain.answer.lower()
    assert plain.used_approved_kb_only is False


def test_plain_mode_sees_other_course_row_filtered_mode_does_not():
    _, course_a = student_auth(client, "CSC 3374")
    _, course_b = professor_auth(client, "CSC 2302")
    assert course_a != course_b
    _add_entry(
        question_text="Lantern buffers — part 1",
        answer_draft=LANTERN,
        status="approved",
        course_id=course_b,
        entry_kind="course_material",
        material_source="notes",
    )
    db = SessionLocal()
    try:
        filtered = answer_from_knowledge_base(
            db, LANTERN_QUESTION, course_id=course_a
        )
        plain = answer_from_knowledge_base(
            db,
            LANTERN_QUESTION,
            course_id=course_a,
            approved_only=False,
            course_scoped=False,
        )
    finally:
        db.close()
    assert filtered.matched_count == 0
    assert filtered.should_seek_help is True
    assert plain.matched_count >= 1
    assert "lantern" in plain.answer.lower()


def test_study_agent_skips_faq_drafts_even_in_plain_mode():
    _, course_id = student_auth(client)
    _add_entry(
        question_text="FAQ: zephyr valves",
        answer_draft=ZEPHYR,
        status="approved",
        course_id=course_id,
        entry_kind=None,
        category="faq",
        material_source=None,
    )
    db = SessionLocal()
    try:
        agent = answer_from_knowledge_base(
            db,
            ZEPHYR_QUESTION,
            course_id=course_id,
            approved_only=False,
            course_scoped=False,
        )
        shared = search_approved_entries(
            db, ZEPHYR_QUESTION, course_id=course_id, course_material_only=False
        )
    finally:
        db.close()
    assert agent.matched_count == 0
    assert agent.should_seek_help is True
    assert shared
    assert "zephyr" in shared[0][0].answer_draft.lower()


def test_agent_route_does_not_accept_retrieval_flags():
    headers, course_id = student_auth(client)
    _add_entry(
        question_text="Zephyr valves — part 1",
        answer_draft=ZEPHYR,
        status="pending_review",
        course_id=course_id,
        entry_kind="course_material",
        material_source="slides",
    )
    response = client.post(
        "/agent/ask",
        headers=headers,
        json={
            "question": ZEPHYR_QUESTION,
            "course_id": course_id,
            "approved_only": False,
            "course_scoped": False,
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["matched_count"] == 0
    assert body["should_seek_help"] is True
    assert "approved_only" not in body
    assert "course_scoped" not in body
