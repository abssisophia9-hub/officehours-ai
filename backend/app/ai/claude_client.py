"""
Ask Triage agent entrypoints — custom-trained models only.

FYP constraint: no prompted Claude calls and no USE_MOCK_CLAUDE deterministic
mocks on the runtime path. Analyzer / Matcher / Synthesizer use trained local
models (embeddings + classifiers) plus RAG over the teaching bank / approved KB.

Legacy Anthropic helpers remain in ``claude_client_legacy`` modules only if
imported explicitly behind ``OFFICEHOURS_ALLOW_EXTERNAL_LLM=true`` (disabled).
"""

from __future__ import annotations

import os
from typing import Any

from app.ai.analyzer_agent import analyze_with_classifier
from app.ai.matcher_model import match_with_model
from app.ai.synthesizer_model import synthesize_with_model


def _external_llm_allowed() -> bool:
    return os.getenv("OFFICEHOURS_ALLOW_EXTERNAL_LLM", "false").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def analyze_question(
    *,
    question_text: str,
    code_snippet: str | None = None,
    course: str | None = None,
) -> dict[str, Any]:
    """Analyzer: fine-tuned classifier by default."""
    backend = os.getenv("OFFICEHOURS_ANALYZER_BACKEND", "ml").strip().lower()
    if backend == "claude":
        if not _external_llm_allowed():
            raise RuntimeError(
                "OFFICEHOURS_ANALYZER_BACKEND=claude requires "
                "OFFICEHOURS_ALLOW_EXTERNAL_LLM=true. "
                "FYP default is the custom-trained Analyzer (ml)."
            )
        from app.ai import claude_client_legacy as legacy

        return legacy.analyze_question_llm(
            question_text=question_text,
            code_snippet=code_snippet,
            course=course,
        )

    return analyze_with_classifier(
        question_text=question_text,
        code_snippet=code_snippet,
        course=course,
    )


def match_ta(
    analyzer: dict[str, Any],
    roster: list[dict[str, Any]],
    *,
    question_text: str = "",
) -> dict[str, Any]:
    """Matcher: trained TA assignment classifier (+ queue penalty)."""
    return match_with_model(
        question_text=question_text
        or " ".join(str(tag) for tag in (analyzer.get("tags") or [])),
        analyzer=analyzer,
        roster=roster,
    )


def synthesize_solution(
    *,
    question_text: str,
    analyzer: dict[str, Any],
    similar_questions: list[dict[str, Any]],
    learning_style: str | None = None,
    code_snippet: str | None = None,
    course: str | None = None,
) -> dict[str, Any]:
    """Synthesizer: RAG over teaching bank / approved KB + style ranker."""
    return synthesize_with_model(
        question_text=question_text,
        analyzer=analyzer,
        similar_questions=similar_questions,
        learning_style=learning_style,
        code_snippet=code_snippet,
        course=course,
    )
