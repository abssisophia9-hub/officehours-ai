"""Stateless, model-driven decisions for the Study Agent.

The orchestration wrapper owns loops, retries, timeouts, budgets, persistence,
and session history. This module receives one immutable state snapshot, makes
exactly one model-backed decision, and returns the next action. It never loops
or retries on its own.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from app.ai.claude_client import (
    AnswerCheckClient,
    AnswerCheckResult,
    choose_recovery,
    judge_entailment,
    verify_course_answer,
)

AgentPhase = Literal["answer", "entailment", "recovery"]
AgentAction = Literal["call_tool", "return_answer", "halt"]


@dataclass(frozen=True)
class AgentState:
    phase: AgentPhase
    question: str
    chunks: tuple[dict[str, Any], ...]
    session_history: tuple[dict[str, Any], ...] = ()
    answer: str = ""
    quote: str = ""


@dataclass(frozen=True)
class AgentStep:
    action: AgentAction
    result: AnswerCheckResult
    tool: str | None = None


def decide_next_action(
    state: AgentState, client: AnswerCheckClient | None
) -> AgentStep:
    """Make one model-driven decision from the supplied state snapshot."""
    if state.phase == "answer":
        result = verify_course_answer(
            state.question,
            list(state.chunks),
            client=client,
            emit_log=False,
            session_history=list(state.session_history),
        )
        if result.outcome == "passed" and result.supporting_chunk_id is not None:
            return AgentStep(action="call_tool", tool="judge_entailment", result=result)
        return AgentStep(action="halt", result=result)

    if state.phase == "entailment":
        assert client is not None
        result = judge_entailment(state.answer, state.quote, client)
        if result.outcome == "supported":
            return AgentStep(action="return_answer", result=result)
        if result.outcome == "unsupported":
            return AgentStep(action="call_tool", tool="choose_recovery", result=result)
        return AgentStep(action="halt", result=result)

    assert client is not None
    result = choose_recovery(
        client,
        question=state.question,
        answer=state.answer,
        quote=state.quote,
    )
    if result.outcome in {"reformulate", "widen", "narrow"}:
        return AgentStep(action="call_tool", tool="search", result=result)
    return AgentStep(action="halt", result=result)
