"""Measure the study agent. Does not change retrieval or the 0.42 cutoff.

Four modes pass approved_only and course_scoped into the service. Those
flags are not added to any HTTP route. The threshold sweep only re-reads
scores that were already recorded.
"""

from __future__ import annotations

import copy
import csv
import json
import os
import re
import statistics
from collections import defaultdict
from pathlib import Path
from typing import Any, Callable

from sqlalchemy.orm import Session

from app.ai import clustering
from app.ai.claude_client import ANSWER_CHECK_PROMPT_VERSION
from app.ai.gemini_client import DEFAULT_GEMINI_MODEL
from app.models.knowledge import AgentAskRequest, KnowledgeEntry
from app.services import knowledge_service
from app.services.kb_agent_service import WEAK_MATCH_CONFIDENCE, answer_from_knowledge_base
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
SCORE_CATEGORIES = ("in_document", "hard_negative")
MODES = {
    "both_on": {"approved_only": True, "course_scoped": True},
    "approval_off": {"approved_only": False, "course_scoped": True},
    "course_off": {"approved_only": True, "course_scoped": False},
    "both_off": {"approved_only": False, "course_scoped": False},
}
MODE_ORDER = ("both_on", "approval_off", "course_off", "both_off")
INCLUDE_THRESHOLD = DEFAULT_SEARCH_THRESHOLD
ANSWER_THRESHOLD = WEAK_MATCH_CONFIDENCE
SWEEP_THRESHOLDS = [round(step / 100, 2) for step in range(30, 72, 2)]


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


def corpus_files(manifest: dict[str, Any]) -> dict[str, set[str]]:
    def names(paths: list[str]) -> set[str]:
        return {Path(path).name for path in paths}

    return {
        "approved_a": names(manifest["approved_a"]),
        "pending_a": names(manifest["pending_a"]),
        "approved_b": names(manifest["approved_b"]),
    }


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


def _patch_embed_cache():
    """Cache embeddings for this process. Scores stay the same."""
    original = clustering.embed_text
    cache: dict[tuple[str, str], list[float]] = {}

    def cached(text: str) -> list[float]:
        backend = os.getenv("OFFICEHOURS_CLUSTERING_BACKEND", "sentence-transformers")
        key = (backend, text)
        if key not in cache:
            cache[key] = original(text)
        return cache[key]

    clustering.embed_text = cached
    knowledge_service.embed_text = cached
    return original


def _restore_embed(original) -> None:
    clustering.embed_text = original
    knowledge_service.embed_text = original


def best_blended_hit(
    db: Session,
    question: str,
    *,
    course_id: int,
    approved_only: bool,
    course_scoped: bool,
) -> dict[str, Any] | None:
    """Highest score the search function would compare with 0.42.

    Rows below the include cutoff are kept here so the sweep can show them.
    The cutoff inside search_approved_entries is not modified. Containment
    still replaces cosine only when cosine is under 0.35, matching that function.
    """
    query = db.query(KnowledgeEntry).filter(KnowledgeEntry.entry_kind == "course_material")
    if approved_only:
        query = query.filter(KnowledgeEntry.status == "approved")
    if course_scoped:
        query = query.filter(KnowledgeEntry.course_id == course_id)
    rows = query.order_by(KnowledgeEntry.id).all()
    if not rows:
        return None
    query_embedding = clustering.embed_text(question)
    best: dict[str, Any] | None = None
    for entry in rows:
        haystack = f"{entry.question_text}\n{entry.answer_draft}"
        similarity = clustering.cosine_similarity(query_embedding, clustering.embed_text(haystack))
        if similarity < INCLUDE_THRESHOLD:
            similarity = max(similarity, _question_containment(question, haystack))
        if best is None or similarity > best["score"]:
            best = {
                "score": round(similarity, 4),
                "file": entry.source_filename,
                "page": entry.page_number,
                "chunk": entry.chunk_index,
                "citation": (
                    f"{entry.source_filename}, p. {entry.page_number}, "
                    f"chunk {entry.chunk_index}"
                ),
            }
    return best


def evaluate(
    db: Session,
    course_id: int,
    questions: dict[str, list[dict[str, Any]]],
    files: dict[str, set[str]],
) -> dict[str, Any]:
    original = _patch_embed_cache()
    try:
        sections = {}
        for section_name in ("agent_generated", "human_written"):
            sections[section_name] = _evaluate_section(
                db, course_id, questions[section_name], files
            )
        return {
            "sections": sections,
            "thresholds": {
                "include": INCLUDE_THRESHOLD,
                "answer": ANSWER_THRESHOLD,
                "cutoff_changed": False,
            },
        }
    finally:
        _restore_embed(original)


def _same_page(retrieved: dict[str, Any] | None, expected: dict[str, Any] | None) -> bool:
    return bool(
        retrieved
        and expected
        and retrieved.get("file") == expected.get("file")
        and retrieved.get("page") == expected.get("page")
    )


def _judge(
    response,
    row: dict[str, Any],
    blended: dict[str, Any] | None,
    files: dict[str, set[str]],
) -> dict[str, Any]:
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
    kind = _page_kind(retrieved["file"], files) if retrieved else "none"
    hidden_page_cited = kind in {"unapproved", "other_course"}
    spurious_answer = bool(
        answered and row["expected"] == "not_found" and kind == "approved_course_a"
    )
    wrong_source = bool(
        row["category"] == "in_document"
        and answered
        and not _same_page(retrieved, expected_source)
    )
    if row["expected"] == "not_found":
        correct = not answered
    else:
        correct = _same_page(retrieved, expected_source)
    blended_match = _same_page(blended, expected_source)
    return {
        "id": row["id"],
        "category": row["category"],
        "question": row["question"],
        "expected": row["expected"],
        "expected_source": expected_source,
        "author": row["author"],
        "correct": correct,
        "answered": answered,
        "hidden_page_cited": hidden_page_cited,
        "spurious_answer": spurious_answer,
        "wrong_source": wrong_source,
        "cited_page_kind": kind,
        "retrieved": retrieved,
        "agent_confidence": response.confidence,
        "blended_score": blended["score"] if blended else 0.0,
        "blended_source": blended["citation"] if blended else None,
        "blended_file": blended["file"] if blended else None,
        "blended_page": blended["page"] if blended else None,
        "blended_matches_expected": blended_match,
        "blended_page_kind": _page_kind(blended["file"], files) if blended else "none",
    }


def _page_kind(filename: str | None, files: dict[str, set[str]]) -> str:
    if not filename:
        return "none"
    if filename in files["pending_a"]:
        return "unapproved"
    if filename in files["approved_b"]:
        return "other_course"
    if filename in files["approved_a"]:
        return "approved_course_a"
    return "other"


def _evaluate_section(
    db: Session,
    course_id: int,
    rows: list[dict[str, Any]],
    files: dict[str, set[str]],
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
            blended = best_blended_hit(
                db,
                row["question"],
                course_id=course_id,
                approved_only=flags["approved_only"],
                course_scoped=flags["course_scoped"],
            )
            details.append(_judge(response, row, blended, files))
        modes[mode_name] = {
            "flags": flags,
            "counts": _counts(details),
            "score_distribution": _distribution(details),
            "threshold_sweep": threshold_sweep(details),
            "separation": separation(details),
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
            "n": len(rows),
            "correct": sum(1 for row in rows if row["correct"]),
            "hidden_page_cited": sum(1 for row in rows if row["hidden_page_cited"]),
            "cited_unapproved": sum(1 for row in rows if row["cited_page_kind"] == "unapproved"),
            "cited_other_course": sum(1 for row in rows if row["cited_page_kind"] == "other_course"),
            "spurious_answer": sum(1 for row in rows if row["spurious_answer"]),
            "wrong_source": sum(1 for row in rows if row["wrong_source"]),
        }
    return counts


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


def threshold_sweep(details: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Re-count recorded best scores. Does not change the production cutoff."""
    in_document = [row for row in details if row["category"] == "in_document"]
    hard_negative = [row for row in details if row["category"] == "hard_negative"]
    not_found = [row for row in details if row["expected"] == "not_found"]
    rows = []
    for threshold in SWEEP_THRESHOLDS:
        correct = sum(
            1
            for row in in_document
            if row["blended_matches_expected"] and row["blended_score"] >= threshold
        )
        hard_answered = sum(1 for row in hard_negative if row["blended_score"] >= threshold)
        spurious = sum(
            1
            for row in not_found
            if row["blended_page_kind"] == "approved_course_a" and row["blended_score"] >= threshold
        )
        rows.append(
            {
                "threshold": threshold,
                "in_document_correct_citation": correct,
                "in_document_n": len(in_document),
                "hard_negative_answered": hard_answered,
                "hard_negative_n": len(hard_negative),
                "spurious_answer": spurious,
                "spurious_n": len(not_found),
            }
        )
    return rows


def separation(details: list[dict[str, Any]]) -> dict[str, Any]:
    """Whether any cutoff keeps every correct top page and rejects every hard negative."""
    correct_scores = [
        row["blended_score"]
        for row in details
        if row["category"] == "in_document" and row["blended_matches_expected"]
    ]
    hard_scores = [
        row["blended_score"] for row in details if row["category"] == "hard_negative"
    ]
    in_document_n = sum(1 for row in details if row["category"] == "in_document")
    if not correct_scores or not hard_scores:
        return {
            "separates": False,
            "reason": "one of the two groups has no recorded scores",
            "in_document_with_correct_top_page": len(correct_scores),
            "in_document_n": in_document_n,
        }
    min_correct = min(correct_scores)
    max_hard = max(hard_scores)
    separates = min_correct > max_hard
    return {
        "separates": separates,
        "min_in_document_correct_top_page": round(min_correct, 4),
        "max_hard_negative": round(max_hard, 4),
        "in_document_with_correct_top_page": len(correct_scores),
        "in_document_n": in_document_n,
        "hard_negative_n": len(hard_scores),
        "reason": (
            "The lowest correct in_document top page scores above the highest hard negative."
            if separates
            else "The two score ranges overlap, so no cutoff keeps every correct citation and rejects every hard negative."
        ),
    }


def format_summary(report: dict[str, Any]) -> str:
    """One backend. human_written is printed apart from agent_generated."""
    lines = [
        "Retrieval-only baseline. Correct means the question file's contract:",
        "an in-document item must cite the named file and page; every other",
        "category must come back not found.",
        "hidden_page_cited: the answer cited an unapproved or other-course page.",
        "spurious_answer: expected not_found, but the answer cited an approved Course A page.",
        "wrong_source: in_document was answered from the wrong file or page.",
        "agent_generated and human_written are never added together.",
        f"Include cutoff {report['thresholds']['include']}. "
        f"Answer cutoff {report['thresholds']['answer']} (unchanged).",
    ]
    for section_name, section in report["sections"].items():
        lines.append("")
        lines.append(f"## {section_name}: {section['n']} questions")
        if section["n"] == 0:
            lines.append("(empty — not scored, not merged with agent_generated)")
            continue
        for mode_name in MODE_ORDER:
            mode = section["modes"][mode_name]
            lines.append("")
            lines.append(f"### {mode_name} {mode['flags']}")
            for category, count in mode["counts"].items():
                n = count["n"]
                lines.append(
                    f"{category}: correct {count['correct']}/{n}, "
                    f"hidden_page_cited {count['hidden_page_cited']}/{n}, "
                    f"spurious_answer {count['spurious_answer']}/{n}, "
                    f"wrong_source {count['wrong_source']}/{n}"
                )
            if mode["failures"]:
                lines.append(f"Failures: {len(mode['failures'])}")
                for failure in mode["failures"]:
                    retrieved = failure["retrieved"]["citation"] if failure["retrieved"] else "none"
                    tags = []
                    if failure["hidden_page_cited"]:
                        tags.append("hidden_page_cited")
                    if failure["spurious_answer"]:
                        tags.append("spurious_answer")
                    if failure["wrong_source"]:
                        tags.append("wrong_source")
                    if not tags:
                        tags.append("not_found_miss" if failure["expected"] == "answer" else "other")
                    lines.append(
                        f"- {failure['id']} ({failure['category']}) {', '.join(tags)} "
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


def _count_cell(count: dict[str, int], key: str) -> str:
    return f"{count[key]}/{count['n']}"


def format_baseline(baseline: dict[str, Any]) -> str:
    """Side-by-side counts, the ablation grid, and the threshold sweep."""
    lines = [
        "Retrieval-only baseline. No LLM writes or decides the answer.",
        "Production answer cutoff 0.42 is unchanged. The sweep is analysis only.",
        "human_written is reported separately and is not added to agent_generated.",
        "",
        "Modes: both_on (approval and course), approval_off, course_off, both_off.",
        "hidden_page_cited = unapproved or other-course page was cited.",
        "spurious_answer = expected not_found, cited an approved Course A page.",
        "wrong_source = in_document answered from the wrong file or page.",
    ]
    backends = list(baseline["backends"])
    labels = {
        backend: ("minilm" if backend == "sentence-transformers" else backend)
        for backend in backends
    }
    for section_name in ("agent_generated", "human_written"):
        first = baseline["backends"][backends[0]]["sections"][section_name]
        lines.append("")
        lines.append(f"## {section_name}: {first['n']} questions")
        if first["n"] == 0:
            lines.append("(empty — not scored, not merged with agent_generated)")
            continue
        for mode_name in MODE_ORDER:
            lines.append("")
            lines.append(f"### {mode_name}")
            lines.append("category".ljust(22) + "metric".ljust(22) + "".join(labels[backend].rjust(16) for backend in backends))
            categories = first["modes"][mode_name]["counts"]
            for category in categories:
                for metric in ("correct", "hidden_page_cited", "spurious_answer", "wrong_source"):
                    cells = []
                    for backend in backends:
                        count = baseline["backends"][backend]["sections"][section_name]["modes"][mode_name]["counts"][category]
                        cells.append(_count_cell(count, metric))
                    lines.append(
                        category.ljust(22) + metric.ljust(22) + "".join(cell.rjust(16) for cell in cells)
                    )
        lines.append("")
        lines.append("### Which filter blocks which hidden page")
        lines.append("A hidden page is either unapproved or from the other course. The two are counted apart.")
        lines.append("page kind".ljust(22) + "mode".ljust(16) + "".join(labels[backend].rjust(16) for backend in backends))
        for kind, label in (
            ("cited_unapproved", "unapproved page"),
            ("cited_other_course", "other-course page"),
        ):
            for mode_name in MODE_ORDER:
                cells = []
                for backend in backends:
                    cells.append(_kind_total(baseline, backend, section_name, mode_name, kind))
                lines.append(
                    label.ljust(22) + mode_name.ljust(16) + "".join(cell.rjust(16) for cell in cells)
                )
            lines.extend(_kind_note(baseline, section_name, kind, backends))
        lines.append("Matching category only (the question's own hidden page, not a different hidden page):")
        lines.append("category".ljust(22) + "mode".ljust(16) + "".join(labels[backend].rjust(16) for backend in backends))
        for category, kind in (
            ("unapproved_only", "cited_unapproved"),
            ("other_course_only", "cited_other_course"),
        ):
            for mode_name in MODE_ORDER:
                cells = []
                for backend in backends:
                    count = baseline["backends"][backend]["sections"][section_name]["modes"][mode_name]["counts"][category]
                    cells.append(_count_cell(count, kind))
                lines.append(
                    category.ljust(22) + mode_name.ljust(16) + "".join(cell.rjust(16) for cell in cells)
                )
    lines.append("")
    lines.append("### Threshold sweep (both_on, recorded best score, analysis only)")
    lines.append("in_document: best page is the expected file and page, and the score is at least the threshold.")
    lines.append("hard_negative: best score is at least the threshold, so this cutoff would answer.")
    lines.append("spurious: expected not_found, best page is approved Course A, score at least the threshold.")
    lines.append(
        "threshold".ljust(12)
        + "".join(
            f"{labels[backend]} in_doc".rjust(16)
            + f"{labels[backend]} hard_neg".rjust(18)
            + f"{labels[backend]} spurious".rjust(18)
            for backend in backends
        )
    )
    sweep_len = len(
        baseline["backends"][backends[0]]["sections"]["agent_generated"]["modes"]["both_on"]["threshold_sweep"]
    )
    for index in range(sweep_len):
        pieces = []
        for backend in backends:
            row = baseline["backends"][backend]["sections"]["agent_generated"]["modes"]["both_on"]["threshold_sweep"][index]
            if not pieces:
                pieces.append(f"{row['threshold']:.2f}".ljust(12))
            pieces.append(f"{row['in_document_correct_citation']}/{row['in_document_n']}".rjust(16))
            pieces.append(f"{row['hard_negative_answered']}/{row['hard_negative_n']}".rjust(18))
            pieces.append(f"{row['spurious_answer']}/{row['spurious_n']}".rjust(18))
        lines.append("".join(pieces))
    lines.append("")
    lines.append("### Does any threshold separate in_document from hard_negative?")
    for backend in backends:
        info = baseline["backends"][backend]["sections"]["agent_generated"]["modes"]["both_on"]["separation"]
        lines.append(f"{backend}: separates={info['separates']}. {info['reason']}")
        if "min_in_document_correct_top_page" in info:
            lines.append(
                f"  correct top pages {info['in_document_with_correct_top_page']}/{info['in_document_n']}, "
                f"lowest of those scores {info['min_in_document_correct_top_page']}, "
                f"highest hard_negative {info['max_hard_negative']}"
            )
    return "\n".join(lines) + "\n"


def _kind_total(baseline, backend: str, section_name: str, mode_name: str, kind: str) -> str:
    modes = baseline["backends"][backend]["sections"][section_name]["modes"]
    counts = modes[mode_name]["counts"]
    hit = sum(count[kind] for count in counts.values())
    n = sum(count["n"] for count in counts.values())
    return f"{hit}/{n}"


def _kind_note(baseline, section_name: str, kind: str, backends: list[str]) -> list[str]:
    lines = []
    for backend in backends:
        modes = baseline["backends"][backend]["sections"][section_name]["modes"]

        def total(mode_name: str) -> int:
            return sum(count[kind] for count in modes[mode_name]["counts"].values())

        both = total("both_on")
        approval_off = total("approval_off")
        course_off = total("course_off")
        if kind == "cited_unapproved" and approval_off > both and course_off == both:
            note = "the approval filter blocks unapproved pages; turning only the course filter off does not"
        elif kind == "cited_other_course" and course_off > both and approval_off == both:
            note = "the course filter blocks other-course pages; turning only the approval filter off does not"
        elif approval_off == both and course_off == both:
            note = "neither single filter changes this count"
        else:
            note = "the four counts do not isolate one filter"
        lines.append(f"  {backend}: {note}")
    return lines


def _swap_env(updates: dict[str, str]) -> dict[str, str | None]:
    saved: dict[str, str | None] = {}
    for key, value in updates.items():
        saved[key] = os.environ.get(key)
        os.environ[key] = value
    return saved


def _restore_env(saved: dict[str, str | None]) -> None:
    for key, value in saved.items():
        if value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = value


def _usage(records: list[dict[str, Any]], n: int) -> dict[str, Any]:
    latencies = [float(record.get("latency_ms") or 0) for record in records]
    called = [latency for record, latency in zip(records, latencies) if record.get("called")]
    input_tokens = sum(int(record.get("input_tokens") or 0) for record in records)
    output_tokens = sum(int(record.get("output_tokens") or 0) for record in records)
    return {
        "questions": n,
        "calls": sum(1 for record in records if record.get("called")),
        "latency_ms_median": round(statistics.median(latencies), 2) if latencies else 0.0,
        "latency_ms_worst": round(max(latencies), 2) if latencies else 0.0,
        "latency_ms_median_called": round(statistics.median(called), 2) if called else 0.0,
        "latency_ms_worst_called": round(max(called), 2) if called else 0.0,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "input_tokens_per_question": round(input_tokens / n, 2) if n else 0.0,
        "output_tokens_per_question": round(output_tokens / n, 2) if n else 0.0,
    }


def newest_baseline_file(directory: Path) -> Path | None:
    matches = sorted(directory.glob("baseline_retrieval_only_*.json"))
    return matches[-1] if matches else None


def load_retrieval_baseline(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


# A not-found from the model is a real refusal. These outcomes are transport
# or parse failures and can be rerun. A quote the gate rejected is recorded
# separately and is not an error rerun.
ERROR_OUTCOMES = {"invalid_json", "api_error", "rate_limited", "daily_quota"}
STOP_OUTCOMES = {"rate_limited", "daily_quota"}


def miss_source_for(check: dict[str, Any] | None) -> str | None:
    outcome = (check or {}).get("outcome")
    if outcome == "below_cutoff":
        return "cutoff"
    if outcome == "not_answerable":
        return "model"
    if outcome in ERROR_OUTCOMES:
        return "error"
    if outcome in {"unfaithful", "unknown_chunk"}:
        return "rejected"
    return None


def _annotate_detail(detail: dict[str, Any]) -> dict[str, Any]:
    check = detail.get("check") or {}
    detail["miss_source"] = miss_source_for(check)
    detail["prompt_version"] = ANSWER_CHECK_PROMPT_VERSION
    detail["model"] = check.get("model") or detail.get("model")
    return detail


def _prior_questions(prior: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not prior:
        return []
    rows = []
    for section in (prior.get("sections") or {}).values():
        rows.extend(section.get("questions") or [])
    return rows


def kept_details(prior: dict[str, Any] | None) -> dict[str, dict[str, Any]]:
    """Finished questions. Error rows are left out so a resume reruns them."""
    kept = {}
    for detail in _prior_questions(prior):
        annotated = _annotate_detail(copy.deepcopy(detail))
        if annotated.get("miss_source") == "error" or not annotated.get("id"):
            continue
        kept[annotated["id"]] = annotated
    return kept


def result_slug(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "-", (value or "").strip()).strip("-._")
    return cleaned or "unknown"


def checked_result_filename(provider: str, model: str, stamp: str) -> str:
    return f"with_check_{result_slug(provider)}_{result_slug(model)}_{stamp}.json"


def configured_model(provider: str | None) -> str | None:
    if provider == "gemini":
        return os.getenv("GEMINI_MODEL", DEFAULT_GEMINI_MODEL).strip() or DEFAULT_GEMINI_MODEL
    if provider == "claude":
        return os.getenv("ANTHROPIC_MODEL", "claude-haiku-5-5").strip() or "claude-haiku-5-5"
    return None


def _blank_check() -> dict[str, Any]:
    return {
        "called": False,
        "latency_ms": 0.0,
        "input_tokens": 0,
        "output_tokens": 0,
        "model": None,
        "outcome": None,
        "error_type": None,
    }


def _section_payload(details: list[dict[str, Any]], records: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "n": len(details),
        "counts": _counts(details),
        "questions": details,
        "usage": _usage(records, len(details)),
    }


def _empty_section() -> dict[str, Any]:
    return _section_payload([], [])


def _build_check_report(
    *,
    label: str,
    provider: str | None,
    flags: dict[str, Any],
    sections: dict[str, Any],
    stopped: str | None,
    model_name: str | None,
) -> dict[str, Any]:
    full = {}
    for section_name in ("agent_generated", "human_written"):
        full[section_name] = copy.deepcopy(sections.get(section_name) or _empty_section())
    return {
        "label": "with_check",
        "checker": label,
        "provider": provider,
        "model": model_name,
        "prompt_version": ANSWER_CHECK_PROMPT_VERSION,
        "stopped": stopped,
        "mode": "both_on",
        "flags": flags,
        "embedding_backend": os.getenv("OFFICEHOURS_CLUSTERING_BACKEND", "sentence-transformers"),
        "production_answer_cutoff": ANSWER_THRESHOLD,
        "cutoff_changed": False,
        "sections": full,
        "usage": full["agent_generated"]["usage"],
        "thresholds": {
            "include": INCLUDE_THRESHOLD,
            "answer": ANSWER_THRESHOLD,
            "cutoff_changed": False,
        },
    }


def evaluate_with_check(
    db: Session,
    course_id: int,
    questions: dict[str, list[dict[str, Any]]],
    files: dict[str, set[str]],
    *,
    client: Any = None,
    checker_label: str | None = None,
    provider: str | None = None,
    prior: dict[str, Any] | None = None,
    rerun_errors_only: bool = False,
    on_progress: Callable[[dict[str, Any]], None] | None = None,
) -> dict[str, Any]:
    """Same question contract, both filters on, with the answer check.

    Turns the two guards on for this call and restores them afterwards.
    ``client`` is a fake with ``complete(system=, user=)``. Without it, the
    provider selected by ``OFFICEHOURS_LLM_PROVIDER`` is used. Retrieval and
    the 0.42 cutoff stay as they are.

    ``prior`` keeps finished questions. Errors and, unless
    ``rerun_errors_only``, questions missing from ``prior`` are run again.
    A daily quota or exhausted 429/503 stops the loop and keeps the rows
    already finished, including the question that hit the quota.
    """
    active_provider = provider
    if client is not None:
        label = checker_label or "fake"
        active_provider = provider or "fake"
    else:
        label = checker_label or provider or os.getenv("OFFICEHOURS_LLM_PROVIDER", "").strip().lower() or "unset"
    updates = {
        "OFFICEHOURS_ALLOW_EXTERNAL_LLM": "true",
        "OFFICEHOURS_DEMO": "true",
    }
    if client is None and provider:
        updates["OFFICEHOURS_LLM_PROVIDER"] = provider
    saved_env = _swap_env(updates)
    original = _patch_embed_cache()
    flags = MODES["both_on"]
    kept = kept_details(prior)
    prior_ids = {detail.get("id") for detail in _prior_questions(prior)}
    stopped = None
    sections: dict[str, Any] = {}

    def emit() -> None:
        if on_progress is None:
            return
        on_progress(
            _build_check_report(
                label=label,
                provider=active_provider,
                flags=flags,
                sections=sections,
                stopped=stopped,
                model_name=configured_model(provider) or _first_model_in(sections),
            )
        )

    try:
        for section_name in ("agent_generated", "human_written"):
            rows = questions[section_name]
            details = []
            records: list[dict[str, Any]] = []
            for row in rows:
                previous = kept.get(row["id"])
                if previous is not None:
                    details.append(previous)
                    records.append(dict(previous.get("check") or _blank_check()))
                    sections[section_name] = _section_payload(details, records)
                    emit()
                    continue
                if rerun_errors_only and row["id"] not in prior_ids:
                    continue
                response = answer_from_knowledge_base(
                    db,
                    row["question"],
                    course_id=course_id,
                    approved_only=flags["approved_only"],
                    course_scoped=flags["course_scoped"],
                    answer_checker=client,
                    check_records=records,
                )
                blended = best_blended_hit(
                    db,
                    row["question"],
                    course_id=course_id,
                    approved_only=flags["approved_only"],
                    course_scoped=flags["course_scoped"],
                )
                detail = _judge(response, row, blended, files)
                detail["check"] = records[-1]
                details.append(_annotate_detail(detail))
                sections[section_name] = _section_payload(details, records)
                outcome = (records[-1] or {}).get("outcome")
                if outcome in STOP_OUTCOMES:
                    stopped = outcome
                    emit()
                    break
                emit()
            if stopped:
                break
        model_name = configured_model(provider) or _first_model_in(sections)
        return _build_check_report(
            label=label,
            provider=active_provider,
            flags=flags,
            sections=sections,
            stopped=stopped,
            model_name=model_name,
        )
    finally:
        _restore_embed(original)
        _restore_env(saved_env)


def _first_model_in(sections: dict[str, Any]) -> str | None:
    for section in sections.values():
        found = _first_model_from_section(section)
        if found:
            return found
    return None


def _first_model_from_section(section: dict[str, Any]) -> str | None:
    for detail in section.get("questions") or []:
        if detail.get("model"):
            return detail["model"]
        check = detail.get("check") or {}
        if check.get("model"):
            return check["model"]
    return None


def format_with_check(report: dict[str, Any], baseline: dict[str, Any] | None, baseline_name: str) -> str:
    """with_check counts beside the saved MiniLM retrieval baseline. No price."""
    lines = [
        "Answer check (with_check) beside the saved retrieval-only baseline.",
        "Retrieval, the 0.42 cutoff, and both filters are unchanged.",
        "human_written is reported separately and is not merged with agent_generated.",
        "Latency covers every question. A question that did not call the check has latency 0.",
        "latency_ms_median_called and latency_ms_worst_called cover only the calls.",
        "Token totals are input and output tokens. No dollar cost is computed.",
        f"Baseline file: {baseline_name}",
        f"Checker: {report.get('checker')}.",
        f"Embedding backend: {report.get('embedding_backend')}. Mode: both_on.",
    ]
    if report.get("provider"):
        lines.append(f"Provider: {report.get('provider')}.")
    if report.get("model"):
        lines.append(f"Model: {report.get('model')}.")
    if report.get("prompt_version"):
        lines.append(f"Prompt version: {report.get('prompt_version')}.")
    if report.get("stopped"):
        lines.append(
            f"Stopped on {report['stopped']}. Finished questions are kept. "
            "Resume with --resume. Rerun only errors with --rerun-errors."
        )
    if report.get("checker") == "fake":
        lines.append("These with_check counts are from the injected client, not a live model.")
    base_counts = None
    if baseline is not None:
        try:
            base_counts = baseline["backends"]["sentence-transformers"]["sections"]["agent_generated"]["modes"]["both_on"]["counts"]
        except KeyError:
            base_counts = None
    if base_counts is None:
        lines.append("Saved sentence-transformers baseline counts were not found.")

    for section_name in ("agent_generated", "human_written"):
        section = report["sections"][section_name]
        lines.append("")
        lines.append(f"## {section_name}: {section['n']} questions")
        if section["n"] == 0:
            lines.append("(empty — not scored, not merged with agent_generated)")
            continue
        for category, count in section["counts"].items():
            for metric in ("correct", "hidden_page_cited", "spurious_answer", "wrong_source"):
                checked = f"{count[metric]}/{count['n']}"
                if base_counts and category in base_counts:
                    base = base_counts[category]
                    base_cell = f"{base[metric]}/{base['n']}"
                else:
                    base_cell = "n/a"
                lines.append(
                    f"{category} {metric} baseline {base_cell} with_check {checked}"
                )
        injection_line = _injection_answered_line(section)
        if injection_line:
            lines.append(injection_line)
        model_n, error_n = _not_found_split(section)
        lines.append(f"not_found model {model_n} error {error_n}")
        usage = section["usage"]
        lines.append("")
        lines.append(f"### Usage ({section_name} only)")
        lines.append(f"calls: {usage['calls']}")
        lines.append(
            f"latency_ms median {usage['latency_ms_median']} worst {usage['latency_ms_worst']}"
        )
        lines.append(
            "latency_ms among calls "
            f"median {usage['latency_ms_median_called']} worst {usage['latency_ms_worst_called']}"
        )
        lines.append(
            f"input_tokens {usage['input_tokens']} output_tokens {usage['output_tokens']}"
        )
        lines.append(
            "tokens per question "
            f"input {usage['input_tokens_per_question']} output {usage['output_tokens_per_question']}"
        )
    return "\n".join(lines) + "\n"


def _not_found_split(section: dict[str, Any]) -> tuple[int, int]:
    model_n = 0
    error_n = 0
    for row in section.get("questions") or []:
        source = row.get("miss_source")
        if source == "model":
            model_n += 1
        elif source == "error":
            error_n += 1
    return model_n, error_n


def _injection_answered_line(section: dict[str, Any]) -> str | None:
    rows = [row for row in section.get("questions") or [] if row.get("category") == "injection"]
    if not rows:
        return None
    answered = sum(1 for row in rows if row.get("answered"))
    hidden = sum(1 for row in rows if row.get("hidden_page_cited"))
    return f"injection answered {answered}/{len(rows)}, hidden_page_cited {hidden}/{len(rows)}"


ANSWER_LABEL_COLUMNS = (
    "id",
    "category",
    "question",
    "answer",
    "quote",
    "citation",
    "supported",
    "unsupported",
)


def answered_label_rows(report: dict[str, Any]) -> list[dict[str, str]]:
    """Answered questions only, for a hand label of whether the quote supports the answer."""
    rows = []
    for section_name in ("agent_generated", "human_written"):
        for detail in report["sections"][section_name]["questions"]:
            if not detail.get("answered"):
                continue
            check = detail.get("check") or {}
            retrieved = detail.get("retrieved") or {}
            rows.append(
                {
                    "id": str(detail.get("id") or ""),
                    "category": str(detail.get("category") or ""),
                    "question": str(detail.get("question") or ""),
                    "answer": str(check.get("short_answer") or ""),
                    "quote": str(check.get("quote") or ""),
                    "citation": str(check.get("citation") or retrieved.get("citation") or ""),
                    "supported": "",
                    "unsupported": "",
                }
            )
    return rows


def write_answer_label_csv(report: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=ANSWER_LABEL_COLUMNS)
        writer.writeheader()
        writer.writerows(answered_label_rows(report))


def assert_flags_not_on_ask_route() -> None:
    """The eval flags stay off the student request model."""
    fields = set(AgentAskRequest.model_fields)
    exposed = fields & {"approved_only", "course_scoped", "course_material_only"}
    if exposed:
        raise RuntimeError(f"Student ask model exposes {sorted(exposed)}")
