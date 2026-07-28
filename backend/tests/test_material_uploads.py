import os

os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["OFFICEHOURS_CLUSTERING_BACKEND"] = "lexical"
os.environ["OFFICEHOURS_ALLOW_EXTERNAL_LLM"] = "false"

from fastapi.testclient import TestClient

from app.database.session import Base, engine
from app.main import app
from app.services.demo_accounts import DEMO_PASSWORD

client = TestClient(app)


def setup_function():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def _professor():
    login = client.post(
        "/auth/login",
        json={"email": "a.benali@aui.ma", "password": DEMO_PASSWORD},
    )
    assert login.status_code == 200
    token = login.json()["token"]
    course_id = next(
        c["id"] for c in login.json()["user"]["courses"] if c["code"] == "CS 400"
    )
    return {"Authorization": f"Bearer {token}"}, course_id


def _minimal_pdf(text: str) -> bytes:
    """Build a tiny but valid single-page PDF containing `text`."""
    escaped = text.replace("\\", r"\\").replace("(", r"\(").replace(")", r"\)")
    stream = f"BT /F1 12 Tf 72 720 Td ({escaped}) Tj ET".encode()
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        (
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            b"/Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>"
        ),
        b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    out = bytearray(b"%PDF-1.4\n")
    offsets = []
    for index, body in enumerate(objects, start=1):
        offsets.append(len(out))
        out += f"{index} 0 obj\n".encode() + body + b"\nendobj\n"
    xref_at = len(out)
    out += f"xref\n0 {len(objects) + 1}\n".encode()
    out += b"0000000000 65535 f \n"
    for offset in offsets:
        out += f"{offset:010d} 00000 n \n".encode()
    out += (
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\n"
        f"startxref\n{xref_at}\n%%EOF\n"
    ).encode()
    return bytes(out)


def test_upload_requires_professor_auth():
    _, course_id = _professor()
    response = client.post(
        "/knowledge/materials/upload",
        data={"course_id": str(course_id)},
        files={"file": ("notes.txt", b"AVL rotations rebalance the tree.", "text/plain")},
    )
    assert response.status_code == 401


def test_upload_rejects_unsupported_extension():
    headers, course_id = _professor()
    response = client.post(
        "/knowledge/materials/upload",
        headers=headers,
        data={"course_id": str(course_id)},
        files={"file": ("malware.exe", b"MZ...", "application/octet-stream")},
    )
    assert response.status_code == 400
    assert "Unsupported" in response.json()["detail"]


def test_upload_txt_feeds_course_agent():
    headers, course_id = _professor()
    body = (
        "AVL trees stay balanced through rotations.\n\n"
        "A left rotation fixes a right-heavy subtree; a right rotation fixes "
        "a left-heavy subtree. After every insertion, update heights and "
        "rotate at the first unbalanced ancestor."
    )
    response = client.post(
        "/knowledge/materials/upload",
        headers=headers,
        data={"course_id": str(course_id), "title": "Week 6 — AVL notes"},
        files={"file": ("avl_notes.txt", body.encode(), "text/plain")},
    )
    assert response.status_code == 201, response.text
    assert response.json()["chunks_created"] >= 1
    assert response.json()["source"] == "notes"

    answer = client.post(
        "/agent/ask",
        json={
            "question": "How do AVL rotations rebalance the tree?",
            "course_id": course_id,
        },
    ).json()
    assert answer["matched_count"] >= 1
    assert "rotation" in answer["answer"].lower()


def test_upload_pdf_extracts_text():
    headers, course_id = _professor()
    pdf = _minimal_pdf("Dijkstra relaxes edges using a priority queue of distances.")
    response = client.post(
        "/knowledge/materials/upload",
        headers=headers,
        data={"course_id": str(course_id), "title": "Week 7 — Dijkstra slides"},
        files={"file": ("dijkstra.pdf", pdf, "application/pdf")},
    )
    assert response.status_code == 201, response.text
    assert response.json()["source"] == "slides"
    assert response.json()["chunks_created"] >= 1

    answer = client.post(
        "/agent/ask",
        json={
            "question": "How does Dijkstra use a priority queue?",
            "course_id": course_id,
        },
    ).json()
    assert answer["matched_count"] >= 1
    assert "priority queue" in answer["answer"].lower()


def test_upload_vtt_video_transcript():
    headers, course_id = _professor()
    vtt = (
        "WEBVTT\n\n"
        "1\n00:00:01.000 --> 00:00:05.000\n"
        "Today we cover memoization in dynamic programming.\n\n"
        "2\n00:00:05.000 --> 00:00:11.000\n"
        "Memoization caches subproblem results so each state is solved once.\n\n"
        "3\n00:00:11.000 --> 00:00:16.000\n"
        "Without it, naive recursion recomputes the same states exponentially.\n"
    )
    response = client.post(
        "/knowledge/materials/upload",
        headers=headers,
        data={"course_id": str(course_id), "title": "Lecture 9 video — DP"},
        files={"file": ("lecture9.vtt", vtt.encode(), "text/vtt")},
    )
    assert response.status_code == 201, response.text
    assert response.json()["source"] == "video_transcript"

    entry_id = response.json()["entry_ids"][0]
    entry = client.get(f"/knowledge/{entry_id}").json()
    assert "-->" not in entry["answer_draft"]
    assert "memoization" in entry["answer_draft"].lower()

    answer = client.post(
        "/agent/ask",
        json={
            "question": "What does memoization cache in dynamic programming?",
            "course_id": course_id,
        },
    ).json()
    assert answer["matched_count"] >= 1


def test_upload_scoped_to_course():
    headers, course_id = _professor()
    client.post(
        "/knowledge/materials/upload",
        headers=headers,
        data={"course_id": str(course_id), "title": "Week 6 — AVL notes"},
        files={
            "file": (
                "avl.txt",
                b"AVL rotations rebalance the tree after insertions and deletions.",
                "text/plain",
            )
        },
    )
    login = client.post(
        "/auth/login",
        json={"email": "a.benali@aui.ma", "password": DEMO_PASSWORD},
    ).json()
    other = next(c["id"] for c in login["user"]["courses"] if c["code"] == "CS 330")
    miss = client.post(
        "/agent/ask",
        json={"question": "How do AVL rotations rebalance the tree?", "course_id": other},
    ).json()
    assert miss["matched_count"] == 0
