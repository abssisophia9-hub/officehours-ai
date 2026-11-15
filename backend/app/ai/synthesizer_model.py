"""
Custom-trained Synthesizer (no external LLM / no Claude mocks).

Architecture (FYP-appropriate):
  1. Retrieve similar teaching entries from a curated teaching bank and/or
     professor-approved KB using sentence embeddings.
  2. Use a trained style/category ranker to prefer matching learning style.
  3. Compose student_hint + teaching_approach from retrieved content.

This is RAG + local models, not prompted Claude.
"""

from __future__ import annotations

import csv
import os
import re
from functools import lru_cache
from pathlib import Path
from typing import Any

import joblib
import numpy as np
from sklearn.linear_model import LogisticRegression

from app.ai.clustering import cosine_similarity
from app.ai.ml_classifier import encode_texts

MODEL_DIR = Path(__file__).resolve().parents[2] / "models"
DEFAULT_MODEL_PATH = MODEL_DIR / "synthesizer_ranker.joblib"
DEFAULT_BANK_PATH = (
    Path(__file__).resolve().parents[3] / "data" / "synthesizer_teaching_bank.csv"
)
DEFAULT_EMBEDDING_MODEL = "all-MiniLM-L6-v2"

# Logistics / policy categories — Help Coach must not invent a teaching method.
FACTUAL_CATEGORIES = frozenset(
    {
        "exam_logistics",
        "grading_dispute",
        "project_submission",
        "office_hours_access",
        "retake_request",
        "accessibility_accommodation",
        "academic_integrity",
    }
)

_FACTUAL_CUES = (
    "exam",
    "midterm",
    "final",
    "deadline",
    "due date",
    "due by",
    "syllabus",
    "coverage",
    "chapters on",
    "chapter on",
    "last part of the chapter",
    "grading",
    "grade",
    "rubric",
    "regrade",
    "allowed",
    "calculator",
    "cheat sheet",
    "formula sheet",
    "closed book",
    "open notes",
    "office hours",
    "when is",
    "what time",
    "what room",
    "late policy",
    "late work",
    "attendance",
)

_CONCEPTUAL_CUES = (
    "explain",
    "why does",
    "how does",
    "how do i",
    "prove",
    "proof",
    "induction",
    "red-black",
    "red black",
    "hash",
    "avl",
    "bst",
    "recursion",
    "invariant",
    "fixup",
    "rotation",
    "understand",
    "confused about",
    "derivation",
)


def is_factual_ask(
    *,
    question_text: str | None = None,
    category: str | None = None,
) -> bool:
    """Heuristic: logistics/policy facts vs conceptual teaching asks. No LLM."""
    cat = (category or "").strip().lower().replace(" ", "_")
    text = (question_text or "").strip().lower()

    conceptual_hit = any(cue in text for cue in _CONCEPTUAL_CUES)
    factual_hit = any(cue in text for cue in _FACTUAL_CUES)

    if cat in FACTUAL_CATEGORIES:
        # "How do I prepare for the final — trees or hashing first?" is still
        # logistics priority, not a teaching-bank checklist about exams.
        if conceptual_hit and not factual_hit:
            return False
        return True
    if cat == "conceptual_question":
        return False
    if factual_hit and not conceptual_hit:
        return True
    if factual_hit and conceptual_hit:
        # Exam + concept mixed → treat as factual when the ask is coverage/
        # policy shaped ("is X on the exam") rather than "explain X".
        coverage_shaped = any(
            cue in text
            for cue in (
                "on the exam",
                "on the midterm",
                "on the final",
                "covered",
                "coverage",
                "do we also have",
                "is the last",
                "allowed",
                "deadline",
                "due",
            )
        )
        return coverage_shaped
    return False


def build_ranker() -> LogisticRegression:
    return LogisticRegression(max_iter=4000, class_weight="balanced", C=2.0)


def load_teaching_bank(path: Path | None = None) -> list[dict[str, str]]:
    """Load curated teaching banks (base + CSC + multi-department supplements)."""
    primary = path or Path(os.getenv("OFFICEHOURS_TEACHING_BANK", DEFAULT_BANK_PATH))
    banks = [primary]
    bank_dir = Path(os.getenv("OFFICEHOURS_TEACHING_BANK_CSC", DEFAULT_BANK_PATH)).parent
    if path is None:
        for name in (
            "synthesizer_teaching_bank_csc.csv",
            "synthesizer_teaching_bank_multidept.csv",
        ):
            extra = bank_dir / name
            if extra.exists() and extra != primary:
                banks.append(extra)

    rows: list[dict[str, str]] = []
    for bank_path in banks:
        if not bank_path.exists():
            continue
        with bank_path.open(newline="", encoding="utf-8") as handle:
            rows.extend(list(csv.DictReader(handle)))
    return rows


def train_synthesizer_ranker(
    texts: list[str],
    learning_styles: list[str],
    *,
    model_name: str | None = None,
) -> dict[str, object]:
    embedding_model = model_name or os.getenv(
        "OFFICEHOURS_EMBEDDING_MODEL", DEFAULT_EMBEDDING_MODEL
    )
    features = encode_texts(texts, embedding_model)
    classifier = build_ranker()
    classifier.fit(features, learning_styles)
    bank = load_teaching_bank()
    return {
        "embedding_model": embedding_model,
        "style_classifier": classifier,
        "labels": sorted(set(learning_styles)),
        "bank_size": len(bank),
        "strategy": "rag-teaching-bank + style-classifier",
    }


def save_synthesizer(bundle: dict[str, object], path: Path = DEFAULT_MODEL_PATH) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(bundle, path)
    return path


@lru_cache(maxsize=1)
def load_synthesizer(path: str | None = None) -> dict[str, object]:
    model_path = Path(
        path or os.getenv("OFFICEHOURS_SYNTHESIZER_MODEL", DEFAULT_MODEL_PATH)
    )
    if not model_path.exists():
        raise FileNotFoundError(
            f"Synthesizer model not found at {model_path}. "
            "Run backend/scripts/train_synthesizer.py first."
        )
    return joblib.load(model_path)


@lru_cache(maxsize=1)
def _bank_embeddings(bank_fingerprint: str) -> tuple[list[dict[str, str]], np.ndarray]:
    bank = load_teaching_bank()
    if not bank:
        return [], np.zeros((0, 1))
    texts = [
        f"{row['category']} {row['learning_style']} {row['topic']} {row['teaching_approach']}"
        for row in bank
    ]
    vectors = encode_texts(texts)
    return bank, vectors


def _department_from_course(course: str | None) -> str | None:
    if not course:
        return None
    token = course.strip().split()[0].upper() if course.strip() else ""
    return token or None


def _bank_shares_tokens(question_text: str, row: dict[str, str]) -> bool:
    """Require at least one meaningful token from the ask in the bank row text."""
    tokens = [
        part
        for part in re.split(r"[^a-z0-9]+", (question_text or "").lower())
        if len(part) > 3
    ]
    if not tokens:
        return True
    blob = " ".join(
        [
            str(row.get("category") or ""),
            str(row.get("teaching_approach") or ""),
            str(row.get("student_hint") or ""),
            str(row.get("entry_id") or ""),
        ]
    ).lower()
    return any(token in blob for token in tokens)


def synthesize_with_model(
    *,
    question_text: str,
    analyzer: dict[str, Any],
    similar_questions: list[dict[str, Any]],
    learning_style: str | None = None,
    code_snippet: str | None = None,
    model_path: str | None = None,
    course: str | None = None,
) -> dict[str, Any]:
    style = (learning_style or "unknown").strip() or "unknown"
    category = str(analyzer.get("ml_category") or "uncategorized")
    tags = list(analyzer.get("tags") or [])
    topic = str(analyzer.get("category") or category).replace("_", " ")
    factual = is_factual_ask(question_text=question_text, category=category)

    predicted_style = style
    backend = "custom_synthesizer_rag"
    try:
        bundle = load_synthesizer(model_path)
        from app.ai.ml_classifier import _load_embedder

        embedder = _load_embedder(str(bundle["embedding_model"]))
        features = np.asarray(embedder.encode([question_text], show_progress_bar=False))
        predicted_style = str(bundle["style_classifier"].predict(features)[0])
        if style == "unknown":
            style = predicted_style
        backend = "custom_synthesizer"
    except FileNotFoundError:
        backend = "custom_synthesizer_untrained_rag"

    # Factual / logistics asks: never invent a teaching-bank checklist (e.g. TB007).
    if factual:
        return _factual_synthesizer_result(
            similar_questions=similar_questions,
            style=style,
            backend=backend,
        )

    # Prefer professor-approved KB hits when available (true RAG).
    if similar_questions:
        best = similar_questions[0]
        teaching = (
            f"Teaching approach adapted from approved KB #{best.get('id')} "
            f"({best.get('category') or topic}):\n"
            f"1. Review the approved explanation for this similar question.\n"
            f"2. Map the student's stuck point onto that explanation.\n"
            f"3. Re-teach with the inferred style `{style}`.\n"
            f"4. Check understanding with one short follow-up question.\n"
            f"Similar question: {best.get('question_text', '')}"
        )
        hint = (
            "Compare your case to a similar past question your course already solved - "
            "what is the one difference that still confuses you?"
        )
        if code_snippet:
            teaching += (
                "\n\nCode focus: isolate the failing branch and verify state updates "
                "after each transformation."
            )
        return {
            "student_hint": hint,
            "teaching_approach": teaching,
            "similar_count": len(similar_questions),
            "similar_questions": similar_questions[:3],
            "kb_insight": (
                f"Retrieved {len(similar_questions)} similar approved KB entries "
                "for the Synthesizer RAG path."
            ),
            "learning_style": style,
            "backend": backend + "_kb_rag",
            "ask_kind": "conceptual",
        }

    # Otherwise retrieve from curated teaching bank with embedding similarity.
    bank, vectors = _bank_embeddings(_fingerprint_bank())
    if len(bank) == 0 or vectors.size == 0:
        return _template_fallback(topic, style, tags, question_text, code_snippet, backend)

    from app.ai.ml_classifier import _load_embedder

    embedder_name = os.getenv("OFFICEHOURS_EMBEDDING_MODEL", DEFAULT_EMBEDDING_MODEL)
    try:
        bundle = load_synthesizer(model_path)
        embedder_name = str(bundle["embedding_model"])
    except FileNotFoundError:
        pass
    embedder = _load_embedder(embedder_name)
    query_vec = np.asarray(embedder.encode([question_text], show_progress_bar=False))[0]

    department = _department_from_course(course)
    ranked: list[tuple[float, dict[str, str]]] = []
    for row, vector in zip(bank, vectors):
        row_dept = (row.get("department") or "").strip().upper()
        if department and department != "CSC" and row_dept != department:
            continue
        if department == "CSC" and row_dept and row_dept != "CSC":
            continue
        score = float(cosine_similarity(query_vec.tolist(), vector.tolist()))
        if row.get("learning_style") == style:
            score += 0.08
        if row.get("category") == category:
            score += 0.12
        ranked.append((score, row))
    if not ranked:
        return _seek_help_fallback(topic, style, tags, question_text, code_snippet, backend)
    ranked.sort(key=lambda item: item[0], reverse=True)
    # Weak / off-topic bank match → do not pretend we solved it; push human help.
    # Require both a higher cosine floor and at least one meaningful token overlap
    # with the student question so distant CSC bank rows cannot drive Socratic.
    best_score = None
    best_row = None
    for score, row in ranked:
        if score < 0.48:
            break
        if _bank_shares_tokens(question_text, row):
            best_score, best_row = score, row
            break
    if best_row is None:
        return _seek_help_fallback(topic, style, tags, question_text, code_snippet, backend)

    teaching = best_row["teaching_approach"]
    if code_snippet:
        teaching += (
            "\n\nCode focus: walk the failing branch in the snippet and verify "
            "state/pointer updates after each step."
        )
    return {
        "student_hint": best_row["student_hint"],
        "teaching_approach": teaching,
        "similar_count": 0,
        "similar_questions": [],
        "kb_insight": (
            f"No approved KB hit yet; retrieved curated teaching-bank entry "
            f"{best_row.get('entry_id')} (custom Synthesizer RAG)."
        ),
        "learning_style": style,
        "backend": backend + "_bank_rag",
        "ask_kind": "conceptual",
    }


def _factual_synthesizer_result(
    *,
    similar_questions: list[dict[str, Any]],
    style: str,
    backend: str,
) -> dict[str, Any]:
    """Logistics/policy: plain note + optional material reference. No bank HOW."""
    plain = "This is a factual question. There's no teaching method to suggest."
    if similar_questions:
        best = similar_questions[0]
        source = str(best.get("question_text") or "").strip()
        preview = str(best.get("answer_draft") or "").strip()
        lines = [
            plain,
            "",
            "Reference (approved course material — for the TA only; "
            "not a Help Coach answer):",
        ]
        if source:
            lines.append(f"Source: {source}")
        if preview:
            lines.append(preview[:400])
        teaching = "\n".join(lines).strip()
        insight = (
            f"Factual ask; approved material #{best.get('id')} shown as "
            "TA-only reference (no teaching method)."
        )
    else:
        teaching = (
            f"{plain}\n\n"
            "Course material doesn't cover this. Ask the professor."
        )
        insight = "Factual ask; no approved course material matched."
    return {
        "student_hint": "",
        "teaching_approach": teaching,
        "similar_count": len(similar_questions),
        "similar_questions": similar_questions[:3],
        "kb_insight": insight,
        "learning_style": style,
        "backend": backend + "_factual",
        "ask_kind": "factual",
    }


def _fingerprint_bank() -> str:
    paths = [
        Path(os.getenv("OFFICEHOURS_TEACHING_BANK", DEFAULT_BANK_PATH)),
        Path(os.getenv("OFFICEHOURS_TEACHING_BANK", DEFAULT_BANK_PATH)).parent
        / "synthesizer_teaching_bank_csc.csv",
        Path(os.getenv("OFFICEHOURS_TEACHING_BANK", DEFAULT_BANK_PATH)).parent
        / "synthesizer_teaching_bank_multidept.csv",
    ]
    parts: list[str] = []
    for path in paths:
        if not path.exists():
            parts.append(f"{path}:missing")
            continue
        stat = path.stat()
        parts.append(f"{path}:{stat.st_mtime_ns}:{stat.st_size}")
    return "|".join(parts)


def draft_kb_with_model(
    *,
    question_text: str,
    category: str | None = None,
    tags: list[str] | None = None,
    learning_style: str | None = None,
    urgency: str | None = None,
    code_snippet: str | None = None,
    similar_questions: list[dict[str, Any]] | None = None,
) -> dict[str, str]:
    """Compose a pending KB draft from the custom Synthesizer (no Claude)."""
    analyzer = {
        "category": category or "General",
        "ml_category": category or "uncategorized",
        "tags": list(tags or []),
        "urgency": urgency or "medium",
    }
    result = synthesize_with_model(
        question_text=question_text,
        analyzer=analyzer,
        similar_questions=list(similar_questions or []),
        learning_style=learning_style,
        code_snippet=code_snippet,
    )
    return {
        "answer_draft": str(result["teaching_approach"]),
        "student_hint": str(result["student_hint"]),
        "drafter_backend": str(result.get("backend") or "custom_synthesizer"),
    }


def _seek_help_fallback(
    topic: str,
    style: str,
    tags: list[str],
    question_text: str,
    code_snippet: str | None,
    backend: str,
) -> dict[str, Any]:
    """When RAG has nothing solid, steer the student to humans - don't stall."""
    focus = tags[0] if tags else topic
    teaching = (
        f"No strong approved FAQ or teaching-bank match for {topic}.\n"
        "1. Do not keep rephrasing into the study agent - materials may not cover this yet.\n"
        "2. Use Quiet ask (anonymous) or reach out to the assigned TA / professor.\n"
        f"3. Bring one minimal example around `{focus}` that shows the stuck point.\n"
        f"Original question: {question_text.strip()}"
    )
    if code_snippet:
        teaching += "\n\nInclude the failing snippet so office hours can start immediately."
    return {
        "student_hint": (
            "Seek help now via Quiet ask - waiting on incomplete course materials "
            "wastes time. Staff will unblock you faster than guessing."
        ),
        "teaching_approach": teaching,
        "similar_count": 0,
        "similar_questions": [],
        "kb_insight": "Weak RAG match; synthesizer encouraged human outreach.",
        "learning_style": style,
        "backend": backend + "_seek_help",
        "should_seek_help": True,
        "ask_kind": "conceptual",
    }


def _template_fallback(
    topic: str,
    style: str,
    tags: list[str],
    question_text: str,
    code_snippet: str | None,
    backend: str,
) -> dict[str, Any]:
    return _seek_help_fallback(
        topic, style, tags, question_text, code_snippet, backend + "_template"
    )
