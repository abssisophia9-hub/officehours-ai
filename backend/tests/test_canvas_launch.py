import os

os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["OFFICEHOURS_CLUSTERING_BACKEND"] = "lexical"
os.environ["OFFICEHOURS_ALLOW_EXTERNAL_LLM"] = "false"
os.environ.pop("CANVAS_BASE_URL", None)
os.environ.pop("CANVAS_ACCESS_TOKEN", None)

from fastapi.testclient import TestClient

from app.database.session import Base, engine
from app.main import app

client = TestClient(app)


def setup_function():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def _approve_pending(client, token, course_id):
    headers = {"Authorization": f"Bearer {token}"}
    pending = client.get(
        f"/knowledge/?status=pending_review&course_id={course_id}",
        headers=headers,
    ).json()
    for entry in pending:
        response = client.patch(
            f"/knowledge/{entry['id']}",
            headers=headers,
            json={"status": "approved"},
        )
        assert response.status_code == 200, response.text


def _launch(**overrides):
    payload = {
        "canvas_course_id": "2101",
        "email": "o.tazi@aui.ma",
        "display_name": "Omar Tazi",
        "canvas_role": "StudentEnrollment",
        "student_id": "118220",
    }
    payload.update(overrides)
    response = client.post("/canvas/launch", json=payload)
    assert response.status_code == 201, response.text
    return response.json()


def test_student_click_provisions_course_user_and_agent():
    """One click inside a brand-new Canvas course sets up the whole tenant."""
    result = _launch()

    assert result["provisioned_course"] is True
    assert result["provisioned_user"] is True
    assert result["role"] == "student"
    assert result["course_code"] == "CSC 3351"
    assert result["course_title"] == "Operating Systems"
    assert result["synced"] is True
    assert result["agent_ready"] is False
    assert result["kb_chunks"] == 0
    assert result["sync"]["files_seen"] == 2
    assert result["sync"]["chunks_created"] >= 2

    # Session token works and shows the auto-created membership.
    headers = {"Authorization": f"Bearer {result['token']}"}
    me = client.get("/auth/me", headers=headers)
    assert me.status_code == 200
    body = me.json()
    assert body["email"] == "o.tazi@aui.ma"
    assert [c["role"] for c in body["courses"]] == ["student"]
    assert body["courses"][0]["canvas_course_id"] == "2101"

    # Slides are pending until a professor stamps them.
    blocked = client.post(
        "/agent/ask",
        headers=headers,
        json={
            "question": "What does round robin scheduling do with the time quantum?",
            "course_id": result["course_id"],
        },
    ).json()
    assert blocked["matched_count"] == 0
    assert blocked["should_seek_help"] is True

    professor = _launch(
        email="l.mansouri@aui.ma",
        display_name="Prof. Leila Mansouri",
        canvas_role="TeacherEnrollment",
        student_id=None,
    )
    _approve_pending(client, professor["token"], result["course_id"])
    answer = client.post(
        "/agent/ask",
        headers=headers,
        json={
            "question": "What does round robin scheduling do with the time quantum?",
            "course_id": result["course_id"],
        },
    ).json()
    assert answer["matched_count"] >= 1
    assert "quantum" in answer["answer"].lower() or "round robin" in answer["answer"].lower()


def test_teacher_launch_maps_professor_and_can_resync():
    result = _launch(
        email="l.mansouri@aui.ma",
        display_name="Prof. Leila Mansouri",
        canvas_role="TeacherEnrollment",
        student_id=None,
    )
    assert result["role"] == "professor"
    assert result["agent_ready"] is False

    # Professor session can hit the protected canvas status endpoint.
    status = client.get(
        f"/knowledge/canvas/status?course_id={result['course_id']}",
        headers={"Authorization": f"Bearer {result['token']}"},
    )
    assert status.status_code == 200
    assert status.json()["agent_ready"] is False
    pending = client.get(
        f"/knowledge/?status=pending_review&course_id={result['course_id']}",
        headers={"Authorization": f"Bearer {result['token']}"},
    ).json()
    assert len(pending) >= 2


def test_second_launch_is_idempotent():
    first = _launch()
    second = _launch()

    assert second["provisioned_course"] is False
    assert second["provisioned_user"] is False
    assert second["course_id"] == first["course_id"]
    # Student relaunch does not re-sync an already-provisioned agent.
    assert second["synced"] is False
    assert second["kb_chunks"] == first["kb_chunks"]

    # Membership was not duplicated.
    me = client.get(
        "/auth/me", headers={"Authorization": f"Bearer {second['token']}"}
    ).json()
    assert len(me["courses"]) == 1


def test_unknown_canvas_role_defaults_to_student():
    result = _launch(canvas_role="ObserverEnrollment")
    assert result["role"] == "student"


def test_ta_launch_maps_ta_role():
    result = _launch(
        email="k.bennis@aui.ma",
        display_name="Karim Bennis",
        canvas_role="TaEnrollment",
        student_id=None,
    )
    assert result["role"] == "ta"
    me = client.get(
        "/auth/me", headers={"Authorization": f"Bearer {result['token']}"}
    ).json()
    assert [c["role"] for c in me["courses"]] == ["ta"]


def test_full_community_loop_ask_ta_professor_agent():
    """The problem this product solves: one student's question, answered once
    by a human, becomes instant approved knowledge for the whole course."""
    student = _launch()  # Omar, CSC 3351
    course_id = student["course_id"]

    question = "Why does my scheduler starve long processes when I use priorities?"

    # 1. Slides don't cover starvation — the agent honestly says so.
    student_headers = {"Authorization": f"Bearer {student['token']}"}
    before = client.post(
        "/agent/ask",
        headers=student_headers,
        json={"question": question, "course_id": course_id},
    ).json()
    assert before["matched_count"] == 0

    # 2. Student submits a quiet ask; Ask Triage runs and seeds a pending draft.
    created = client.post(
        "/requests/",
        headers=student_headers,
        json={
            "text": question,
            "anonymous": True,
            "course": student["course_code"],
            "course_id": course_id,
        },
    )
    assert created.status_code == 201
    request_id = created.json()["id"]

    # 3. TA works the queue and writes the teaching answer.
    ta = _launch(
        email="k.bennis@aui.ma",
        display_name="Karim Bennis",
        canvas_role="TaEnrollment",
        student_id=None,
    )
    assert ta["role"] == "ta"
    queue = client.get(
        f"/ta/queue/?course_id={course_id}&assignment=all",
        headers={"Authorization": f"Bearer {ta['token']}"},
    ).json()
    assert any(item["request"]["id"] == request_id for item in queue)
    resolved = client.post(
        "/ta/resolve/",
        headers={"Authorization": f"Bearer {ta['token']}"},
        json={
            "request_id": request_id,
            "teaching_notes": (
                "Priority scheduling starves long low-priority processes because "
                "new higher-priority arrivals always preempt them. Fix it with "
                "aging: gradually raise the priority of waiting processes so "
                "every process eventually runs."
            ),
            "student_hint": "Look up aging — the fix for starvation in priority schedulers.",
            "resolution_status": "resolved",
        },
    )
    assert resolved.status_code == 200

    # 4. Still gated: nothing reaches students before professor approval.
    mid = client.post(
        "/agent/ask",
        headers=student_headers,
        json={"question": question, "course_id": course_id},
    ).json()
    assert mid["matched_count"] == 0

    # 5. Professor approves the curated draft.
    professor = _launch(
        email="l.mansouri@aui.ma",
        display_name="Prof. Leila Mansouri",
        canvas_role="TeacherEnrollment",
        student_id=None,
    )
    pending = client.get(
        f"/knowledge/?status=pending_review&course_id={course_id}",
        headers={"Authorization": f"Bearer {professor['token']}"},
    ).json()
    entry = next(e for e in pending if e["source_request_id"] == request_id)
    approved = client.patch(
        f"/knowledge/{entry['id']}",
        headers={"Authorization": f"Bearer {professor['token']}"},
        json={"status": "approved"},
    )
    assert approved.status_code == 200
    assert professor["role"] == "professor"

    # 6. The next student with the same struggle gets the answer instantly.
    after = client.post(
        "/agent/ask",
        headers=student_headers,
        json={"question": question, "course_id": course_id},
    ).json()
    assert after["matched_count"] >= 1
    assert "aging" in after["answer"].lower()


def test_launch_into_existing_course_joins_without_reprovision():
    """Launching from CSC 2302 (already seeded by demo accounts) just joins."""
    # Trigger demo seed via a login-dependent endpoint.
    from app.services.demo_accounts import DEMO_PASSWORD

    login = client.post(
        "/auth/login",
        json={"email": "a.benali@aui.ma", "password": DEMO_PASSWORD},
    )
    assert login.status_code == 200

    result = _launch(
        canvas_course_id="4001",
        email="n.berrada@aui.ma",
        display_name="Nadia Berrada",
        canvas_role="Learner",
        student_id="118350",
    )
    assert result["provisioned_course"] is False
    assert result["provisioned_user"] is True
    assert result["role"] == "student"
    assert result["course_code"] == "CSC 2302"

    assert result["agent_ready"] is False
    _approve_pending(client, login.json()["token"], result["course_id"])
    answer = client.post(
        "/agent/ask",
        headers={"Authorization": f"Bearer {result['token']}"},
        json={
            "question": "How do hash tables handle collisions?",
            "course_id": result["course_id"],
        },
    ).json()
    assert answer["matched_count"] >= 1


def test_course_agents_stay_isolated_across_launches():
    os_launch = _launch()  # CSC 3351
    ds_launch = _launch(
        canvas_course_id="4001",
        email="s.elidrissi@aui.ma",
        display_name="Sara El Idrissi",
        canvas_role="StudentEnrollment",
        student_id="117400",
    )

    professor = _launch(
        email="l.mansouri@aui.ma",
        display_name="Prof. Leila Mansouri",
        canvas_role="TeacherEnrollment",
        student_id=None,
    )
    _approve_pending(client, professor["token"], os_launch["course_id"])

    # CSC 3351 agent knows scheduling; CSC 2302 agent does not.
    scheduling_in_ds = client.post(
        "/agent/ask",
        headers={"Authorization": f"Bearer {ds_launch['token']}"},
        json={
            "question": "What does round robin scheduling do with the time quantum?",
            "course_id": ds_launch["course_id"],
        },
    ).json()
    assert scheduling_in_ds["matched_count"] == 0

    scheduling_in_os = client.post(
        "/agent/ask",
        headers={"Authorization": f"Bearer {os_launch['token']}"},
        json={
            "question": "What does round robin scheduling do with the time quantum?",
            "course_id": os_launch["course_id"],
        },
    ).json()
    assert scheduling_in_os["matched_count"] >= 1


def test_canvas_launch_secret_gate():
    """Optional OFFICEHOURS_CANVAS_LAUNCH_SECRET blocks unsigned demo abuse."""
    os.environ["OFFICEHOURS_CANVAS_LAUNCH_SECRET"] = "fyp-demo-lock"
    try:
        denied = client.post(
            "/canvas/launch",
            json={
                "canvas_course_id": "2101",
                "email": "o.tazi@aui.ma",
                "display_name": "Omar Tazi",
                "canvas_role": "StudentEnrollment",
            },
        )
        assert denied.status_code == 401

        ok = client.post(
            "/canvas/launch",
            json={
                "canvas_course_id": "2101",
                "email": "o.tazi@aui.ma",
                "display_name": "Omar Tazi",
                "canvas_role": "StudentEnrollment",
                "demo_secret": "fyp-demo-lock",
            },
        )
        assert ok.status_code == 201, ok.text
    finally:
        os.environ.pop("OFFICEHOURS_CANVAS_LAUNCH_SECRET", None)
