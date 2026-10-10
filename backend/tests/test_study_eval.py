"""Eval corpus, question file, four filter modes, and the score sweep."""

import json
import os
from pathlib import Path

os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["OFFICEHOURS_CLUSTERING_BACKEND"] = "lexical"
os.environ["OFFICEHOURS_DEMO"] = "true"

from fastapi.testclient import TestClient

from app.database.session import Base, SessionLocal, engine
from app.eval.study_harness import (
    ANSWER_THRESHOLD,
    MODE_ORDER,
    SWEEP_THRESHOLDS,
    assert_flags_not_on_ask_route,
    corpus_files,
    evaluate,
    format_baseline,
    format_summary,
    ingest_corpus,
    load_questions,
    separation,
    threshold_sweep,
    validate_questions,
)
from app.main import app
from app.models.knowledge import KnowledgeEntry
from app.services.kb_agent_service import WEAK_MATCH_CONFIDENCE

REPO = Path(__file__).resolve().parents[2]
QUESTIONS = REPO / "docs" / "eval_questions" / "study_agent_questions.json"
MANIFEST = REPO / "backend" / "demo_data" / "eval" / "manifest.json"
DEMO_ROOT = REPO / "backend" / "demo_data"
GUIDE = REPO / "docs" / "eval_questions" / "HOW_TO_WRITE_QUESTIONS.md"

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
    guide = GUIDE.read_text(encoding="utf-8")
    assert "human_written" in guide
    assert "agent_generated" in guide
    assert "without" not in guide or "Do not read" in guide
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


def test_runner_scores_four_modes_without_merging_authors():
    assert_flags_not_on_ask_route()
    assert WEAK_MATCH_CONFIDENCE == 0.42
    assert ANSWER_THRESHOLD == 0.42
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    files = corpus_files(manifest)
    ingested = ingest_corpus(client, manifest, DEMO_ROOT)
    questions = load_questions(QUESTIONS)
    db = SessionLocal()
    try:
        report = evaluate(db, ingested["course_a_id"], questions, files)
    finally:
        db.close()

    assert set(report["sections"]) == {"agent_generated", "human_written"}
    assert report["sections"]["human_written"]["n"] == 0
    generated = report["sections"]["agent_generated"]
    assert list(generated["modes"]) == list(MODE_ORDER)
    both_on = generated["modes"]["both_on"]
    approval_off = generated["modes"]["approval_off"]
    course_off = generated["modes"]["course_off"]
    both_off = generated["modes"]["both_off"]
    assert both_on["flags"] == {"approved_only": True, "course_scoped": True}
    assert approval_off["flags"] == {"approved_only": False, "course_scoped": True}
    assert course_off["flags"] == {"approved_only": True, "course_scoped": False}
    assert both_off["flags"] == {"approved_only": False, "course_scoped": False}

    for mode in generated["modes"].values():
        assert mode["counts"]["in_document"]["n"] == 20
        assert mode["counts"]["hard_negative"]["n"] == 20
        for count in mode["counts"].values():
            assert {"hidden_page_cited", "spurious_answer", "wrong_source", "correct"} <= set(count)
        assert [row["threshold"] for row in mode["threshold_sweep"]] == SWEEP_THRESHOLDS
        assert mode["threshold_sweep"][0]["threshold"] == 0.30
        assert mode["threshold_sweep"][-1]["threshold"] == 0.70

    for row in both_on["questions"]:
        assert row["hidden_page_cited"] is False
        assert row["cited_page_kind"] != "unapproved"
        assert row["cited_page_kind"] != "other_course"
        if row["retrieved"]:
            assert row["retrieved"]["file"] in files["approved_a"]
    for row in approval_off["questions"]:
        assert row["cited_page_kind"] != "other_course"
        if row["hidden_page_cited"]:
            assert row["retrieved"]["file"] in files["pending_a"]
    for row in course_off["questions"]:
        assert row["cited_page_kind"] != "unapproved"
        if row["hidden_page_cited"]:
            assert row["retrieved"]["file"] in files["approved_b"]

    summary = format_summary(report)
    assert "agent_generated: 75 questions" in summary
    assert "human_written: 0 questions" in summary
    assert "not merged with agent_generated" in summary
    assert "both_on" in summary and "approval_off" in summary
    assert "course_off" in summary and "both_off" in summary
    assert "hidden_page_cited" in summary
    assert "spurious_answer" in summary
    assert "wrong_source" in summary
    assert "leak" not in summary.lower()
    assert "%" not in summary

    baseline = {
        "backends": {"lexical": report},
    }
    side_by_side = format_baseline(baseline)
    assert "Threshold sweep" in side_by_side
    assert "0.42" in side_by_side
    assert "human_written: 0 questions" in side_by_side
    assert "leak" not in side_by_side.lower()


def test_threshold_sweep_uses_recorded_scores_only():
    details = [
        {
            "category": "in_document",
            "expected": "answer",
            "blended_score": 0.80,
            "blended_matches_expected": True,
            "blended_page_kind": "approved_course_a",
        },
        {
            "category": "in_document",
            "expected": "answer",
            "blended_score": 0.50,
            "blended_matches_expected": False,
            "blended_page_kind": "approved_course_a",
        },
        {
            "category": "hard_negative",
            "expected": "not_found",
            "blended_score": 0.90,
            "blended_matches_expected": False,
            "blended_page_kind": "approved_course_a",
        },
        {
            "category": "hard_negative",
            "expected": "not_found",
            "blended_score": 0.20,
            "blended_matches_expected": False,
            "blended_page_kind": "approved_course_a",
        },
    ]
    sweep = {row["threshold"]: row for row in threshold_sweep(details)}
    assert sweep[0.42]["in_document_correct_citation"] == 1
    assert sweep[0.42]["hard_negative_answered"] == 1
    assert sweep[0.42]["spurious_answer"] == 1
    assert sweep[0.60]["in_document_correct_citation"] == 1
    assert sweep[0.60]["hard_negative_answered"] == 1
    assert sweep[0.60]["spurious_answer"] == 1
    info = separation(details)
    assert info["separates"] is False
    assert info["min_in_document_correct_top_page"] == 0.80
    assert info["max_hard_negative"] == 0.90

    separated = separation(
        [
            {
                "category": "in_document",
                "blended_score": 0.70,
                "blended_matches_expected": True,
            },
            {
                "category": "hard_negative",
                "blended_score": 0.40,
                "blended_matches_expected": False,
            },
        ]
    )
    assert separated["separates"] is True
