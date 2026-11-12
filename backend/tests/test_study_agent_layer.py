from __future__ import annotations

import json
from types import SimpleNamespace

from app.ai.study_agent_layer import AgentState, decide_next_action


class ScriptedClient:
    def __init__(self, replies):
        self.replies = list(replies)
        self.calls = []

    def complete(self, *, system: str, user: str):
        self.calls.append({"system": system, "user": user})
        reply = self.replies.pop(0)
        if isinstance(reply, Exception):
            raise reply
        return SimpleNamespace(
            text=json.dumps(reply),
            model="test-model",
            input_tokens=1,
            output_tokens=1,
            latency_ms=1.0,
        )


def _state(phase: str = "answer", **kwargs) -> AgentState:
    return AgentState(
        phase=phase,
        question="What does pop return?",
        chunks=(
            {
                "chunk_id": 11,
                "file": "notes.pdf",
                "page": 3,
                "text": "Pop returns the top value.",
                "status": "approved",
            },
        ),
        **kwargs,
    )


def test_agent_layer_returns_next_actions_without_retrying(monkeypatch):
    monkeypatch.setenv("OFFICEHOURS_ALLOW_EXTERNAL_LLM", "true")
    monkeypatch.setenv("OFFICEHOURS_DEMO", "true")
    broken = ScriptedClient([TimeoutError("down"), {"answerable": False}])
    step = decide_next_action(_state(), broken)
    assert step.action == "halt"
    assert step.result.outcome == "api_error"
    assert len(broken.calls) == 1


def test_agent_layer_maps_reasoning_phases_to_actions(monkeypatch):
    monkeypatch.setenv("OFFICEHOURS_ALLOW_EXTERNAL_LLM", "true")
    monkeypatch.setenv("OFFICEHOURS_DEMO", "true")
    answer = ScriptedClient(
        [
            {
                "answerable": True,
                "supporting_chunk_id": 11,
                "answer": "It returns the top value.",
                "quote": "returns the top value.",
            }
        ]
    )
    quote_step = decide_next_action(
        _state(session_history=({"role": "student", "text": "Earlier question"},)),
        answer,
    )
    assert quote_step.action == "call_tool"
    assert quote_step.tool == "judge_entailment"
    assert json.loads(answer.calls[0]["user"])["session_history"] == [
        {"role": "student", "text": "Earlier question"}
    ]

    entailment = ScriptedClient([{"supports": True}])
    supported = decide_next_action(
        _state(
            "entailment",
            answer="It returns the top value.",
            quote="returns the top value.",
        ),
        entailment,
    )
    assert supported.action == "return_answer"

    recovery = ScriptedClient([{"action": "widen"}])
    next_search = decide_next_action(
        _state(
            "recovery",
            answer="It returns the top value.",
            quote="returns the top value.",
        ),
        recovery,
    )
    assert next_search.action == "call_tool"
    assert next_search.tool == "search"
