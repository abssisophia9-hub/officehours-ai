"""
Backward-compatible shim for the former \"Oracle\" module name.

Prefer ``app.services.triage_service`` — Ask Triage (Analyzer → Matcher → Synthesizer).
"""

from app.services.triage_service import (  # noqa: F401
    apply_oracle_to_request,
    apply_triage_to_request,
    build_oracle_public_payload,
    build_triage_public_payload,
    ensure_default_roster,
    lifetime_confusion_topics,
    run_oracle_pipeline,
    run_triage_pipeline,
)
