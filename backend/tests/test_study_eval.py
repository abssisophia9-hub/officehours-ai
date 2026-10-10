"""Eval corpus, question file, and both retrieval modes. Lexical only."""

import json
import os
from pathlib import Path

os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["OFFICEHOURS_CLUSTERING_BACKEND"] = "lexical"
os.environ["OFFICEHOURS_DEMO"] = "true"

from fastapi.testclient import TestClient

from app.database.session import Base, SessionLocal, engine
from app.eval.study_harness import (
    assert_flags_not_on_ask_route,
    evaluate,
    format_summary,
    ingest_corpus,
    load_questions,
    validate_questions,
)
from app.main import app
from app.models.knowledge import KnowledgeEntry

REPO = Path(__file__).resolve().parents[2]
QUESTIONS = REPO / "docs" / "eval_questions" / "study_agent_questions.json"
MANIFEST = REPO / "backend" / "demo_data" / "eval" / "manifest.json"
DEMO_ROOT = REPO / "backend" / "demo_data"

client = TestClient(app)


def setup_function():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def test_question_file_meets_the_schema_and_keeps_authors_apart():
    payload = load_questions(QUESTIONS)
    assert payload["human_written"] == []
    assert all(row["author"] == "agent_generated" for row in payload["agent_generated"])
    counts = {}
    for row in payload["agent_generated"]:
        counts[row["category"]] = counts.get(row["category"], 0) + 1
    assert counts == {
        "in_document": 20,
        "hard_negative": 20,
        "unapproved_only": 10,
        "other_course_only": 10,
        "injection": 15,
    }
    broken = json.loads(QUESTIONS.read_text(encoding="utf-8"))
    broken["agent_generated"][0]["author"] = "human"
    try:
        validate_questions(broken)
    except ValueError as exc:
        assert "author" in str(exc)
    else:
        raise AssertionError("mixed author was accepted")


def test_corpus_ingests_approved_and_pending_on_two_courses():
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    ingested = ingest_corpus(client, manifest, DEMO_ROOT)
    assert ingested["course_a_id"] != ingested["course_b_id"]
    by_file = {row["file"]: row for row in ingested["uploads"]}
    assert by_file["csc2302_lecture_notes.pdf"]["chunks"] == 3
    assert by_file["csc2302_lecture_notes.pdf"]["approved"] is True
    assert by_file["csc2302_draft_exam_notice.pdf"]["approved"] is False
    assert by_file["csc3323_policy_sheet.pdf"]["approved"] is True
    assert by_file["demo_kettle_notes.pdf"]["chunks"] == 4

    db = SessionLocal()
    try:
        pending = (
            db.query(KnowledgeEntry)
            .filter(KnowledgeEntry.source_filename == "csc2302_pending_lab_extension.pdf")
            .all()
        )
        assert pending
        assert {row.status for row in pending} == {"pending_review"}
        assert {row.course_id for row in pending} == {ingested["course_a_id"]}
        assert "fig-harvest" in pending[0].answer_draft

        other = (
            db.query(KnowledgeEntry)
            .filter(KnowledgeEntry.source_filename == "csc3323_lecture_notes.pdf")
            .all()
        )
        assert other
        assert {row.status for row in other} == {"approved"}
        assert {row.course_id for row in other} == {ingested["course_b_id"]}
        assert any("cedar-split" in row.answer_draft for row in other)

        approved_a = (
            db.query(KnowledgeEntry)
            .filter(
                KnowledgeEntry.source_filename == "csc2302_policy_sheet.pdf",
                KnowledgeEntry.page_number == 2,
            )
            .one()
        )
        assert approved_a.status == "approved"
        assert approved_a.chunk_index == 2
        assert "cedar-stamp" in approved_a.answer_draft
    finally:
        db.close()


def test_runner_scores_filtered_and_plain_separately():
    assert_flags_not_on_ask_route()
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    ingested = ingest_corpus(client, manifest, DEMO_ROOT)
    questions = load_questions(QUESTIONS)
    db = SessionLocal()
    try:
        report = evaluate(db, ingested["course_a_id"], questions)
    finally:
        db.close()

    assert set(report["sections"]) == {"agent_generated", "human_written"}
    assert report["sections"]["human_written"]["n"] == 0
    generated = report["sections"]["agent_generated"]
    assert set(generated["modes"]) == {"filtered", "plain"}
    for mode in generated["modes"].values():
        assert mode["counts"]["in_document"]["n"] == 20
        assert mode["counts"]["hard_negative"]["n"] == 20
        assert mode["leaks"]["unapproved_only"]["n"] == 10
        assert mode["leaks"]["other_course_only"]["n"] == 10
        assert "under_0.35" in mode["score_distribution"]["in_document"]
        assert "at_or_above_0.42" in mode["score_distribution"]["hard_negative"]
    summary = format_summary(report)
    assert "agent_generated: 75 questions" in summary
    assert "human_written: 0 questions" in summary
    assert "filtered" in summary and "plain" in summary
    assert "%" not in summary
