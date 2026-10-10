"""Measure the study agent. Does not change retrieval or the 0.42 cutoff.

Filtered mode is the student path (approved rows, one course). Plain mode
passes approved_only=False and course_scoped=False into the service. Those
flags are not added to any HTTP route.
"""

from __future__ import annotations

import json
import statistics
from collections import defaultdict
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from app.ai.clustering import cosine_similarity, embed_text
from app.models.knowledge import AgentAskRequest, KnowledgeEntry
from app.services.kb_agent_service import answer_from_knowledge_base
from app.services.knowledge_service import (
    DEFAULT_SEARCH_THRESHOLD,
    _question_containment,
)

CATEGORIES = (
    "in_document",
    "hard_negative",
    "unapproved_only",
    "other_course_only",
    "injection",
)
MINIMUM_COUNTS = {
    "in_document": 20,
    "hard_negative": 20,
    "unapproved_only": 10,
    "other_course_only": 10,
    "injection": 15,
}
LEAK_CATEGORIES = ("unapproved_only", "other_course_only")
SCORE_CATEGORIES = ("in_document", "hard_negative")
MODES = {
    "filtered": {"approved_only": True, "course_scoped": True},
    "plain": {"approved_only": False, "course_scoped": False},
}
INCLUDE_THRESHOLD = DEFAULT_SEARCH_THRESHOLD
ANSWER_THRESHOLD = 0.42


def load_questions(path: Path) -> dict[str, list[dict[str, Any]]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    validate_questions(payload)
    return payload


def validate_questions(payload: dict[str, Any]) -> None:
    if not isinstance(payload, dict):
        raise ValueError("Question file must be an object with two sections.")
    for section, author in (
        ("agent_generated", "agent_generated"),
        ("human_written", "human"),
    ):
        if section not in payload:
            raise ValueError(f"Missing section {section}.")
        rows = payload[section]
        if not isinstance(rows, list):
            raise ValueError(f"{section} must be a list.")
        for row in rows:
            _validate_row(row, author=author, section=section)
    seen: set[str] = set()
    for section in ("agent_generated", "human_written"):
        for row in payload[section]:
            if row["id"] in seen:
                raise ValueError(f"Duplicate question id {row['id']}.")
            seen.add(row["id"])
    counts: dict[str, int] = defaultdict(int)
    for row in payload["agent_generated"]:
        counts[row["category"]] += 1
    for category, minimum in MINIMUM_COUNTS.items():
        if counts[category] < minimum:
            raise ValueError(
                f"agent_generated {category} has {counts[category]}/{minimum} questions."
            )


def _validate_row(row: dict[str, Any], *, author: str, section: str) -> None:
    required = ("id", "question", "category", "expected", "expected_source", "author")
    missing = [key for key in required if key not in row]
    if missing:
        raise ValueError(f"{section} row missing {missing}.")
    if row["author"] != author:
        raise ValueError(f"{row.get('id')} author must be {author}.")
    if row["category"] not in CATEGORIES:
        raise ValueError(f"{row['id']} has unknown category {row['category']}.")
    if row["expected"] not in {"answer", "not_found"}:
        raise ValueError(f"{row['id']} expected must be answer or not_found.")
    if not isinstance(row["question"], str) or len(row["question"].strip()) < 3:
        raise ValueError(f"{row['id']} question is too short.")
    source = row["expected_source"]
    if row["expected"] == "answer":
        if not isinstance(source, dict) or "file" not in source or "page" not in source:
            raise ValueError(f"{row['id']} answer items need expected_source file and page.")
    elif source is not None and (
        not isinstance(source, dict) or "file" not in source or "page" not in source
    ):
        raise ValueError(f"{row['id']} expected_source must be null or file plus page.")


def ingest_corpus(client, manifest: dict[str, Any], demo_root: Path) -> dict[str, Any]:
    """Upload the demo PDFs as the demo professor. Pending files stay pending."""
    from app.services.demo_accounts import DEMO_PASSWORD

    login = client.post(
        "/auth/login",
        json={"email": "a.benali@aui.ma", "password": DEMO_PASSWORD},
    )
    if login.status_code != 200:
        raise RuntimeError(login.text)
    body = login.json()
    headers = {"Authorization": f"Bearer {body['token']}"}
    courses = {course["code"]: course["id"] for course in body["user"]["courses"]}
    course_a = courses[manifest["course_a"]]
    course_b = courses[manifest["course_b"]]
    uploaded = []
    for course_id, names, approve in (
        (course_a, manifest["approved_a"], True),
        (course_a, manifest["pending_a"], False),
        (course_b, manifest["approved_b"], True),
    ):
        for name in names:
            path = demo_root / name
            if not path.is_file():
                raise FileNotFoundError(path)
            with path.open("rb") as handle:
                response = client.post(
                    "/knowledge/materials/upload",
                    headers=headers,
                    data={
                        "course_id": str(course_id),
                        "title": path.stem.replace("_", " "),
                    },
                    files={"file": (path.name, handle, "application/pdf")},
                )
            if response.status_code != 201:
                raise RuntimeError(f"{path.name}: {response.text}")
            payload = response.json()
            if approve:
                stamped = client.post(
                    f"/knowledge/uploads/{payload['upload_id']}/approve",
                    headers=headers,
                )
                if stamped.status_code != 200:
                    raise RuntimeError(stamped.text)
            uploaded.append(
                {
                    "file": path.name,
                    "course_id": course_id,
                    "chunks": payload["chunks_created"],
                    "upload_id": payload["upload_id"],
                    "approved": approve,
                }
            )
    return {
        "course_a_id": course_a,
        "course_b_id": course_b,
        "uploads": uploaded,
    }


def best_blended_score(
    db: Session,
    question: str,
    *,
    course_id: int,
    approved_only: bool,
    course_scoped: bool,
) -> tuple[float, str | None]:
    """Highest score the search function would compare with 0.42.

    Rows below the include cutoff are kept here so the distribution can show
    them. The cutoff inside search_approved_entries is not modified.
    Containment still replaces cosine only when cosine is under 0.35, matching
    that function.
    """
    query = db.query(KnowledgeEntry).filter(KnowledgeEntry.entry_kind == "course_material")
    if approved_only:
        query = query.filter(KnowledgeEntry.status == "approved")
    if course_scoped:
        query = query.filter(KnowledgeEntry.course_id == course_id)
    rows = query.order_by(KnowledgeEntry.id).all()
    if not rows:
        return 0.0, None
    query_embedding = embed_text(question)
    best_score = -1.0
    best_label = None
    for entry in rows:
        haystack = f"{entry.question_text}\n{entry.answer_draft}"
        similarity = cosine_similarity(query_embedding, embed_text(haystack))
        if similarity < INCLUDE_THRESHOLD:
            similarity = max(similarity, _question_containment(question, haystack))
        if similarity > best_score:
            best_score = similarity
            best_label = (
                f"{entry.source_filename}, p. {entry.page_number}, chunk {entry.chunk_index}"
            )
    if best_score < 0:
        return 0.0, None
    return round(best_score, 4), best_label


def evaluate(
    db: Session,
    course_id: int,
    questions: dict[str, list[dict[str, Any]]],
) -> dict[str, Any]:
    sections = {}
    for section_name in ("agent_generated", "human_written"):
        sections[section_name] = _evaluate_section(
            db, course_id, questions[section_name]
        )
    return {"sections": sections, "thresholds": {
        "include": INCLUDE_THRESHOLD,
        "answer": ANSWER_THRESHOLD,
    }}


def _evaluate_section(
    db: Session,
    course_id: int,
    rows: list[dict[str, Any]],
) -> dict[str, Any]:
    modes = {}
    for mode_name, flags in MODES.items():
        details = []
        for row in rows:
            response = answer_from_knowledge_base(
                db,
                row["question"],
                course_id=course_id,
                approved_only=flags["approved_only"],
                course_scoped=flags["course_scoped"],
            )
            blended, blended_source = best_blended_score(
                db,
                row["question"],
                course_id=course_id,
                approved_only=flags["approved_only"],
                course_scoped=flags["course_scoped"],
            )
            answered = (not response.should_seek_help) and response.matched_count >= 1
            retrieved = None
            if answered and response.sources:
                entry = response.sources[0].entry
                retrieved = {
                    "file": entry.source_filename,
                    "page": entry.page_number,
                    "chunk": entry.chunk_index,
                    "citation": (
                        f"{entry.source_filename}, p. {entry.page_number}, "
                        f"chunk {entry.chunk_index}"
                    ),
                    "similarity": response.sources[0].similarity,
                }
            expected_source = row["expected_source"]
            if row["expected"] == "not_found":
                correct = not answered
            else:
                correct = bool(
                    retrieved
                    and expected_source
                    and retrieved["file"] == expected_source["file"]
                    and retrieved["page"] == expected_source["page"]
                )
            leaked = row["category"] in LEAK_CATEGORIES and answered
            leaked_expected = bool(
                leaked
                and expected_source
                and retrieved
                and retrieved["file"] == expected_source["file"]
                and retrieved["page"] == expected_source["page"]
            )
            details.append(
                {
                    "id": row["id"],
                    "category": row["category"],
                    "question": row["question"],
                    "expected": row["expected"],
                    "expected_source": expected_source,
                    "author": row["author"],
                    "correct": correct,
                    "answered": answered,
                    "leaked": leaked,
                    "leaked_expected_source": leaked_expected,
                    "retrieved": retrieved,
                    "agent_confidence": response.confidence,
                    "blended_score": blended,
                    "blended_source": blended_source,
                }
            )
        modes[mode_name] = {
            "counts": _counts(details),
            "leaks": _leaks(details),
            "score_distribution": _distribution(details),
            "failures": [row for row in details if not row["correct"]],
            "questions": details,
        }
    return {"n": len(rows), "modes": modes}


def _counts(details: list[dict[str, Any]]) -> dict[str, dict[str, int]]:
    counts = {}
    for category in CATEGORIES:
        rows = [row for row in details if row["category"] == category]
        if not rows:
            continue
        counts[category] = {
            "correct": sum(1 for row in rows if row["correct"]),
            "n": len(rows),
        }
    return counts


def _leaks(details: list[dict[str, Any]]) -> dict[str, dict[str, int]]:
    leaks = {}
    for category in LEAK_CATEGORIES:
        rows = [row for row in details if row["category"] == category]
        if not rows:
            continue
        leaks[category] = {
            "leaked": sum(1 for row in rows if row["leaked"]),
            "leaked_expected_source": sum(1 for row in rows if row["leaked_expected_source"]),
            "n": len(rows),
        }
    return leaks


def _distribution(details: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    found = {}
    for category in SCORE_CATEGORIES:
        scores = [row["blended_score"] for row in details if row["category"] == category]
        if not scores:
            continue
        ordered = sorted(scores)
        found[category] = {
            "n": len(scores),
            "under_0.35": sum(1 for score in scores if score < INCLUDE_THRESHOLD),
            "from_0.35_below_0.42": sum(
                1 for score in scores if INCLUDE_THRESHOLD <= score < ANSWER_THRESHOLD
            ),
            "at_or_above_0.42": sum(1 for score in scores if score >= ANSWER_THRESHOLD),
            "min": round(ordered[0], 4),
            "median": round(statistics.median(ordered), 4),
            "max": round(ordered[-1], 4),
        }
    return found


def format_summary(report: dict[str, Any]) -> str:
    lines = [
        "Study-agent eval. Correct means the question file's contract:",
        "an in-document item must cite the named file and page; every other",
        "category must be not found. Plain mode is scored on that same contract,",
        "so a leak is not correct. Counts are not percentages.",
        "agent_generated and human_written are never added together.",
        f"Include cutoff {report['thresholds']['include']}. "
        f"Answer cutoff {report['thresholds']['answer']} (unchanged).",
    ]
    for section_name, section in report["sections"].items():
        lines.append("")
        lines.append(f"## {section_name}: {section['n']} questions")
        if section["n"] == 0:
            lines.append("(empty — not scored)")
            continue
        for mode_name, mode in section["modes"].items():
            lines.append("")
            lines.append(f"### {mode_name}")
            for category, count in mode["counts"].items():
                lines.append(
                    f"{category}: {count['correct']}/{count['n']} correct"
                )
            if mode["leaks"]:
                lines.append("Leaks (an answer was returned):")
                for category, leak in mode["leaks"].items():
                    lines.append(
                        f"  {category}: {leak['leaked']}/{leak['n']} leaked, "
                        f"{leak['leaked_expected_source']}/{leak['n']} cited the hidden page"
                    )
            if mode["score_distribution"]:
                lines.append(
                    "Blended score (cosine, or containment when cosine is under 0.35):"
                )
                for category, dist in mode["score_distribution"].items():
                    lines.append(
                        f"  {category} n={dist['n']} "
                        f"under 0.35: {dist['under_0.35']}/{dist['n']}, "
                        f"0.35 to below 0.42: {dist['from_0.35_below_0.42']}/{dist['n']}, "
                        f"0.42 or higher: {dist['at_or_above_0.42']}/{dist['n']}, "
                        f"min {dist['min']}, median {dist['median']}, max {dist['max']}"
                    )
            if mode["failures"]:
                lines.append(f"Failures: {len(mode['failures'])}")
                for failure in mode["failures"]:
                    retrieved = failure["retrieved"]["citation"] if failure["retrieved"] else "none"
                    lines.append(
                        f"- {failure['id']} ({failure['category']}) "
                        f"score {failure['blended_score']} "
                        f"agent_confidence {failure['agent_confidence']}"
                    )
                    lines.append(f"  question: {failure['question']}")
                    lines.append(f"  expected: {failure['expected']} {failure['expected_source']}")
                    lines.append(f"  retrieved: {retrieved}")
                    lines.append(f"  blended source: {failure['blended_source']}")
            else:
                lines.append("Failures: 0")
    return "\n".join(lines) + "\n"


def assert_flags_not_on_ask_route() -> None:
    """The eval flags stay off the student request model."""
    fields = set(AgentAskRequest.model_fields)
    leaked = fields & {"approved_only", "course_scoped", "course_material_only"}
    if leaked:
        raise RuntimeError(f"Student ask model exposes {sorted(leaked)}")
