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
        c["id"] for c in login.json()["user"]["courses"] if c["code"] == "CSC 2302"
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


def _multipage_pdf(pages: list[str]) -> bytes:
    """Build a valid PDF with one short text line per page."""
    font_id = 3
    objects: dict[int, bytes] = {
        1: b"<< /Type /Catalog /Pages 2 0 R >>",
        3: b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    }
    kids: list[int] = []
    next_id = 4
    for text in pages:
        page_id = next_id
        content_id = next_id + 1
        next_id += 2
        kids.append(page_id)
        escaped = text.replace("\\", r"\\").replace("(", r"\(").replace(")", r"\)")
        stream = f"BT /F1 12 Tf 72 720 Td ({escaped}) Tj ET".encode()
        objects[content_id] = (
            b"<< /Length "
            + str(len(stream)).encode()
            + b" >>\nstream\n"
            + stream
            + b"\nendstream"
        )
        objects[page_id] = (
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            f"/Contents {content_id} 0 R /Resources << /Font << /F1 {font_id} 0 R >> >> >>"
        ).encode()
    kids_ref = " ".join(f"{kid} 0 R" for kid in kids)
    objects[2] = f"<< /Type /Pages /Kids [{kids_ref}] /Count {len(pages)} >>".encode()

    out = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for index in range(1, next_id):
        offsets.append(len(out))
        out += f"{index} 0 obj\n".encode() + objects[index] + b"\nendobj\n"
    xref_at = len(out)
    out += f"xref\n0 {next_id}\n".encode()
    out += b"0000000000 65535 f \n"
    for offset in offsets[1:]:
        out += f"{offset:010d} 00000 n \n".encode()
    out += (
        f"trailer\n<< /Size {next_id} /Root 1 0 R >>\n"
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
        data={"course_id": str(course_id), "title": "Week 6 — AVL notes", "auto_approve": "true"},
        files={"file": ("avl_notes.txt", body.encode(), "text/plain")},
    )
    assert response.status_code == 201, response.text
    assert response.json()["chunks_created"] >= 1
    assert response.json()["source"] == "notes"

    answer = client.post(
        "/agent/ask",
        headers=headers,
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
        data={"course_id": str(course_id), "title": "Week 7 — Dijkstra slides", "auto_approve": "true"},
        files={"file": ("dijkstra.pdf", pdf, "application/pdf")},
    )
    assert response.status_code == 201, response.text
    assert response.json()["source"] == "slides"
    assert response.json()["chunks_created"] >= 1

    answer = client.post(
        "/agent/ask",
        headers=headers,
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
        data={"course_id": str(course_id), "title": "Lecture 9 video — DP", "auto_approve": "true"},
        files={"file": ("lecture9.vtt", vtt.encode(), "text/vtt")},
    )
    assert response.status_code == 201, response.text
    assert response.json()["source"] == "video_transcript"

    entry_id = response.json()["entry_ids"][0]
    entry = client.get(f"/knowledge/{entry_id}", headers=headers).json()
    assert "-->" not in entry["answer_draft"]
    assert "memoization" in entry["answer_draft"].lower()

    answer = client.post(
        "/agent/ask",
        headers=headers,
        json={
            "question": "What does memoization cache in dynamic programming?",
            "course_id": course_id,
        },
    ).json()
    assert answer["matched_count"] >= 1


def test_pdf_citation_uses_filename_page_and_chunk():
    headers, course_id = _professor()
    pdf = _multipage_pdf(
        [
            "Zephyr valves open when the copper kettle reaches a rolling boil.",
            "Lantern buffers store spare wicks for the night lab.",
        ]
    )
    response = client.post(
        "/knowledge/materials/upload",
        headers=headers,
        data={"course_id": str(course_id), "title": "Demo lab notes", "auto_approve": "true"},
        files={"file": ("lab-notes.pdf", pdf, "application/pdf")},
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["chunks_created"] == 2

    stored = client.get(f"/knowledge/{body['entry_ids'][1]}", headers=headers).json()
    assert stored["source_filename"] == "lab-notes.pdf"
    assert stored["page_number"] == 2
    assert stored["chunk_index"] == 2
    assert stored["entry_kind"] == "course_material"

    answer = client.post(
        "/agent/ask",
        headers=headers,
        json={
            "question": "What do lantern buffers store for the night lab?",
            "course_id": course_id,
        },
    ).json()
    assert answer["matched_count"] >= 1
    assert answer["answer"].startswith("Lantern buffers store spare wicks for the night lab.")
    assert "based on lab-notes.pdf, p.2 approved by the professor" in answer["answer"]


def test_upload_scoped_to_course():
    headers, course_id = _professor()
    client.post(
        "/knowledge/materials/upload",
        headers=headers,
        data={"course_id": str(course_id), "title": "Week 6 — AVL notes", "auto_approve": "true"},
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
    other = next(c["id"] for c in login["user"]["courses"] if c["code"] == "CSC 3323")
    miss = client.post(
        "/agent/ask",
        headers={"Authorization": f"Bearer {login['token']}"},
        json={"question": "How do AVL rotations rebalance the tree?", "course_id": other},
    ).json()
    assert miss["matched_count"] == 0
