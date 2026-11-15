"""Help Coach — TA co-pilot while helping."""

import os

os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["OFFICEHOURS_CLUSTERING_BACKEND"] = "lexical"
os.environ["OFFICEHOURS_ALLOW_EXTERNAL_LLM"] = "false"

from fastapi.testclient import TestClient

from app.database.session import Base, SessionLocal, engine
from app.main import app
from app.services.demo_accounts import ensure_demo_accounts

client = TestClient(app)


def setup_function():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        ensure_demo_accounts(db)
    finally:
        db.close()


def _login(email: str) -> str:
    return client.post(
        "/auth/login",
        json={"email": email, "password": "aui-demo"},
    ).json()["token"]


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _csc2302(token: str) -> int:
    me = client.get("/auth/me", headers=_auth(token)).json()
    return next(c["id"] for c in me["courses"] if c["code"] == "CSC 2302")


def test_queue_includes_help_coach_and_similar_badge():
    student = _login("s.elidrissi@aui.ma")
    alice = _login("a.chen@aui.ma")
    course_id = _csc2302(student)

    first = client.post(
        "/requests/",
        headers=_auth(student),
        json={
            "text": "Red-black tree delete fixup loops forever after rotating uncle.",
            "anonymous": True,
            "course": "CSC 2302",
            "course_id": course_id,
            "help_mode": "message",
        },
    ).json()
    second = client.post(
        "/requests/",
        headers=_auth(student),
        json={
            "text": "My red-black deletion fixup never terminates on uncle rotation.",
            "anonymous": True,
            "course": "CSC 2302",
            "course_id": course_id,
            "help_mode": "message",
        },
    ).json()

    queue = client.get(
        f"/ta/queue/?course_id={course_id}&assignment=all",
        headers=_auth(alice),
    ).json()
    by_id = {item["request"]["id"]: item for item in queue}
    assert first["id"] in by_id
    assert second["id"] in by_id

    assert by_id[first["id"]]["help_coach"] is None
    assert by_id[first["id"]]["similar_open_count"] >= 1
    coach = client.get(
        f"/ta/coach/?request_id={first['id']}",
        headers=_auth(alice),
    ).json()
    assert coach["teaching_approach"]
    assert isinstance(coach["socratic_steps"], list)
    assert len(coach["socratic_steps"]) >= 1
    # Same category / cluster should surface a similar-open cue.
    assert coach["similar_open_count"] >= 1
    assert any(peer["id"] == second["id"] for peer in coach["similar_open"])


def test_assist_draft_reply_socratic_and_rewrite():
    student = _login("s.elidrissi@aui.ma")
    alice = _login("a.chen@aui.ma")
    course_id = _csc2302(student)

    created = client.post(
        "/requests/",
        headers=_auth(student),
        json={
            "text": "Hash table open addressing vs chaining — when does clustering hurt?",
            "anonymous": False,
            "student_name": "Sara",
            "course": "CSC 2302",
            "course_id": course_id,
            "help_mode": "message",
        },
    ).json()
    rid = created["id"]

    assert client.post("/ta/assist/", json={"request_id": rid}).status_code == 401

    draft = client.post(
        "/ta/assist/",
        headers=_auth(alice),
        json={"request_id": rid, "mode": "draft_reply"},
    )
    assert draft.status_code == 200, draft.text
    body = draft.json()
    assert body["mode"] == "draft_reply"
    assert body["draft_reply"]
    assert "hash" in body["draft_reply"].lower() or "path" in body["draft_reply"].lower()
    assert body["help_coach"]["socratic_steps"]

    socratic = client.post(
        "/ta/assist/",
        headers=_auth(alice),
        json={"request_id": rid, "mode": "socratic", "focus": "clustering"},
    ).json()
    assert socratic["mode"] == "socratic"
    assert any("clustering" in step.lower() for step in socratic["socratic_steps"])

    rewrite = client.post(
        "/ta/assist/",
        headers=_auth(alice),
        json={
            "request_id": rid,
            "mode": "rewrite_reply",
            "current_reply": "Try chaining first then open addressing.",
        },
    ).json()
    assert rewrite["mode"] == "rewrite_reply"
    assert rewrite["draft_reply"]
    assert "chaining" in rewrite["draft_reply"].lower()


def test_refresh_teaching_updates_pending_draft():
    student = _login("s.elidrissi@aui.ma")
    alice = _login("a.chen@aui.ma")
    course_id = _csc2302(student)

    created = client.post(
        "/requests/",
        headers=_auth(student),
        json={
            "text": "Explain AVL rotations after a double imbalance on insert.",
            "anonymous": True,
            "course": "CSC 2302",
            "course_id": course_id,
        },
    ).json()
    rid = created["id"]

    refreshed = client.post(
        "/ta/assist/",
        headers=_auth(alice),
        json={"request_id": rid, "mode": "refresh_teaching"},
    )
    assert refreshed.status_code == 200, refreshed.text
    assert refreshed.json()["teaching_approach"]

    queue = client.get(
        f"/ta/queue/?course_id={course_id}&assignment=all",
        headers=_auth(alice),
    ).json()
    item = next(row for row in queue if row["request"]["id"] == rid)
    assert item["knowledge_entry"] is not None
    assert item["knowledge_entry"]["answer_draft"]
    coach = client.get(
        f"/ta/coach/?request_id={rid}",
        headers=_auth(alice),
    ).json()
    assert coach["teaching_approach"]


def test_student_cannot_use_help_coach_on_other_course():
    """Sara is student-only on CSC 2302 — assist must reject."""
    student = _login("s.elidrissi@aui.ma")
    course_id = _csc2302(student)
    created = client.post(
        "/requests/",
        headers=_auth(student),
        json={
            "text": "Quick BST height question for coach auth check.",
            "anonymous": True,
            "course": "CSC 2302",
            "course_id": course_id,
        },
    ).json()
    denied = client.post(
        "/ta/assist/",
        headers=_auth(student),
        json={"request_id": created["id"], "mode": "draft_reply"},
    )
    assert denied.status_code in {403, 401}


def test_socratic_steps_grounded_in_student_ask():
    from app.services.help_coach_service import _socratic_steps

    steps = _socratic_steps(
        teaching_approach="1. Restate the stuck point.\n2. Try a small example.",
        difficulty="MEDIUM",
        category="probability",
        learning_style="step_by_step",
        ask_text="I am stuck on exam chapter 4 Bayes theorem for the midterm.",
    )
    assert steps
    assert any("Bayes" in step or "exam chapter 4" in step for step in steps)


def test_bank_match_requires_token_overlap_for_exam_chapter():
    """Off-topic bank rows must not drive coaching for an exam-chapter ask."""
    from app.ai.synthesizer_model import _bank_shares_tokens, synthesize_with_model

    assert not _bank_shares_tokens(
        "exam chapter 4 probability Bayes theorem",
        {
            "category": "trees",
            "teaching_approach": "AVL rotate left then right",
            "student_hint": "balance factor",
        },
    )
    out = synthesize_with_model(
        question_text="Exam chapter 4: how do I apply Bayes theorem to the weather example?",
        analyzer={
            "category": "Probability",
            "ml_category": "probability",
            "tags": ["exam", "chapter-4"],
        },
        similar_questions=[],
        learning_style="step_by_step",
        course="MTH 1304",
    )
    teaching = (out.get("teaching_approach") or "").lower()
    assert "avl" not in teaching
    assert "red-black" not in teaching
    # Prefer seek-help / template fallback over a distant CSC bank hit.
    assert "bank_rag" not in str(out.get("backend") or "")


def test_factual_exam_ask_skips_teaching_bank():
    """Exam coverage ask must not surface TB007 / teaching checklists."""
    from app.ai.synthesizer_model import is_factual_ask, synthesize_with_model

    ask = "please for the exam do we also have the last part of the chapter or not"
    assert is_factual_ask(question_text=ask, category="exam_logistics")
    out = synthesize_with_model(
        question_text=ask,
        analyzer={
            "category": "Exam Logistics",
            "ml_category": "exam_logistics",
            "tags": ["exam"],
        },
        similar_questions=[],
        learning_style="step_by_step",
        course="CSC 3347",
    )
    teaching = out.get("teaching_approach") or ""
    assert out.get("ask_kind") == "factual"
    assert "factual question" in teaching.lower()
    assert "no teaching method" in teaching.lower()
    assert "course material doesn't cover this" in teaching.lower()
    assert "4-step checklist" not in teaching.lower()
    assert "TB007" not in (out.get("kb_insight") or "")
    assert "bank_rag" not in str(out.get("backend") or "")


def test_factual_exam_ask_with_approved_material_is_reference_only():
    """Approved syllabus note is TA-only reference, not a Help Coach answer."""
    from app.ai.synthesizer_model import synthesize_with_model

    ask = "please for the exam do we also have the last part of the chapter or not"
    similar = [
        {
            "id": 8,
            "question_text": "Syllabus exam coverage note",
            "category": "exam_logistics",
            "score": 0.71,
            "answer_draft": (
                "Exam covers chapters 1–8 including the last section of chapter 8. "
                "Yes — the last part of the chapter is on the exam."
            ),
            "student_hint": "This answer comes from course materials (paste): Syllabus.",
        }
    ]
    out = synthesize_with_model(
        question_text=ask,
        analyzer={
            "category": "Exam Logistics",
            "ml_category": "exam_logistics",
            "tags": ["exam"],
        },
        similar_questions=similar,
        learning_style="step_by_step",
        course="CSC 3347",
    )
    teaching = out.get("teaching_approach") or ""
    assert out.get("ask_kind") == "factual"
    assert "factual question" in teaching.lower()
    assert "not a Help Coach answer" in teaching
    assert "Source: Syllabus exam coverage note" in teaching
    assert "last part of the chapter is on the exam" in teaching
    assert "Teaching approach adapted from approved KB" not in teaching
    assert "4-step checklist" not in teaching.lower()


def test_conceptual_ask_keeps_suggested_approach():
    student = _login("s.elidrissi@aui.ma")
    alice = _login("a.chen@aui.ma")
    course_id = _csc2302(student)

    created = client.post(
        "/requests/",
        headers=_auth(student),
        json={
            "text": (
                "Why does red-black deletion fixup restore black-height "
                "after deleting a black leaf?"
            ),
            "anonymous": True,
            "course": "CSC 2302",
            "course_id": course_id,
            "help_mode": "message",
        },
    ).json()
    coach = client.get(
        f"/ta/coach/?request_id={created['id']}",
        headers=_auth(alice),
    ).json()
    assert coach["ask_kind"] == "conceptual"
    assert coach["teaching_approach"]
    assert "factual question" not in (coach["teaching_approach"] or "").lower()
    assert len(coach["socratic_steps"]) >= 1
    assert "Suggested approach" in (coach.get("coach_summary") or "")


def test_factual_coach_endpoint_no_socratic_checklist():
    student = _login("s.elidrissi@aui.ma")
    alice = _login("a.chen@aui.ma")
    professor = _login("a.benali@aui.ma")
    course_id = _csc2302(student)

    created = client.post(
        "/requests/",
        headers=_auth(student),
        json={
            "text": (
                "please for the exam do we also have the last part of "
                "the chapter or not"
            ),
            "anonymous": True,
            "course": "CSC 2302",
            "course_id": course_id,
            "help_mode": "message",
        },
    ).json()
    coach = client.get(
        f"/ta/coach/?request_id={created['id']}",
        headers=_auth(alice),
    ).json()
    assert coach["ask_kind"] == "factual"
    teaching = coach["teaching_approach"] or ""
    assert "factual question" in teaching.lower()
    assert "no teaching method" in teaching.lower()
    assert "4-step checklist" not in teaching.lower()
    assert coach["socratic_steps"] == []
    assert "Course material doesn't cover this" in teaching

    pasted = client.post(
        "/knowledge/materials",
        headers=_auth(professor),
        json={
            "course_id": course_id,
            "title": "Syllabus exam coverage note",
            "content": (
                "Exam covers chapters 1–8 including the last section of chapter 8. "
                "Yes — the last part of the chapter is on the exam."
            ),
            "auto_approve": True,
        },
    )
    assert pasted.status_code in {200, 201}, pasted.text
    coach2 = client.get(
        f"/ta/coach/?request_id={created['id']}",
        headers=_auth(alice),
    ).json()
    assert coach2["ask_kind"] == "factual"
    text2 = coach2["teaching_approach"] or ""
    assert "factual question" in text2.lower()
    assert "not a Help Coach answer" in text2
    assert "last part of the chapter is on the exam" in text2
    assert "4-step checklist" not in text2.lower()
    assert coach2["socratic_steps"] == []
