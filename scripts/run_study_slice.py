#!/usr/bin/env python3
"""Terminal vertical slice for the course-scoped study agent.

Logs in as the demo professor, uploads the synthetic kettle PDF, approves
every chunk in one call, then asks three in-document questions and three
absent questions. Repeats the same six with the approval and course filters
off (plain RAG).

The embedding backend is all-MiniLM-L6-v2 unless OFFICEHOURS_CLUSTERING_BACKEND
is already set (use ``lexical`` to match the test suite).
"""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
BACKEND = REPO / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

os.environ.setdefault("OFFICEHOURS_DEMO", "true")
os.environ.setdefault("OFFICEHOURS_ALLOW_EXTERNAL_LLM", "false")
os.environ.setdefault("OFFICEHOURS_RATE_LIMIT", "false")
os.environ.setdefault("OFFICEHOURS_CLUSTERING_BACKEND", "sentence-transformers")

_DB_DIR = tempfile.mkdtemp(prefix="study-slice-")
os.environ["DATABASE_URL"] = f"sqlite:///{_DB_DIR}/study_slice.db"

from fastapi.testclient import TestClient  # noqa: E402

from app.database.session import SessionLocal  # noqa: E402
from app.main import app  # noqa: E402
from app.services.demo_accounts import DEMO_PASSWORD  # noqa: E402
from app.services.kb_agent_service import answer_from_knowledge_base  # noqa: E402

PDF_PATH = BACKEND / "demo_data" / "demo_kettle_notes.pdf"
PROFESSOR_EMAIL = "a.benali@aui.ma"
COURSE_CODE = "CSC 2302"

IN_DOCUMENT = [
    "What data structure stores brew tickets in the demo kettle?",
    "How many mugs can the circular queue hold?",
    "How does the locker-code hash table handle a collision?",
]
ABSENT = [
    "What is the midterm date for quantum blockchain yoga?",
    "Who invented the telephone in 1876?",
    "What is the chemical formula of sodium chloride?",
]


def _citation(answer: str) -> str:
    if "— " not in answer:
        return ""
    tail = answer.split("— ", 1)[1]
    return tail.split(":", 1)[0].strip()


def _print_round(title: str, rows: list[tuple[str, str, bool, str]]) -> tuple[int, int]:
    print(f"\n=== {title} ===")
    answered = 0
    missing = 0
    in_doc_total = 0
    absent_total = 0
    for kind, question, hit, text in rows:
        print(f"\n[{kind}] {question}")
        if kind == "in-document":
            in_doc_total += 1
            if hit:
                answered += 1
        else:
            absent_total += 1
            if not hit:
                missing += 1
        if not hit:
            print("not found")
            continue
        print(text)
        cite = _citation(text)
        if cite:
            print(f"citation: {cite}")
    print(
        f"\n{title}: {answered}/{in_doc_total} answered, "
        f"{missing}/{absent_total} not found"
    )
    return answered, missing


def main() -> int:
    if not PDF_PATH.is_file():
        print(f"Missing demo PDF: {PDF_PATH}", file=sys.stderr)
        return 1

    backend = os.environ["OFFICEHOURS_CLUSTERING_BACKEND"]
    print(f"Embedding backend: {backend}")
    print(f"Demo PDF: {PDF_PATH}")
    print(f"Database: {os.environ['DATABASE_URL']}")

    with TestClient(app) as client:
        login = client.post(
            "/auth/login",
            json={"email": PROFESSOR_EMAIL, "password": DEMO_PASSWORD},
        )
        if login.status_code != 200:
            print(login.text, file=sys.stderr)
            return 1
        token = login.json()["token"]
        headers = {"Authorization": f"Bearer {token}"}
        course_id = next(
            course["id"]
            for course in login.json()["user"]["courses"]
            if course["code"] == COURSE_CODE
        )
        print(f"Professor: {PROFESSOR_EMAIL}  course: {COURSE_CODE} ({course_id})")

        with PDF_PATH.open("rb") as handle:
            uploaded = client.post(
                "/knowledge/materials/upload",
                headers=headers,
                data={"course_id": str(course_id), "title": "Demo kettle notes"},
                files={"file": (PDF_PATH.name, handle, "application/pdf")},
            )
        if uploaded.status_code != 201:
            print(uploaded.text, file=sys.stderr)
            return 1
        upload = uploaded.json()
        print(
            f"Uploaded {upload['chunks_created']} chunk(s), "
            f"upload_id={upload['upload_id']}, status pending"
        )

        approved = client.post(
            f"/knowledge/uploads/{upload['upload_id']}/approve",
            headers=headers,
        )
        if approved.status_code != 200:
            print(approved.text, file=sys.stderr)
            return 1
        print(f"Approved {approved.json()['approved_count']} chunk(s) in one call")

        def ask_filtered(question: str) -> tuple[bool, str]:
            response = client.post(
                "/agent/ask",
                headers=headers,
                json={"question": question, "course_id": course_id},
            )
            response.raise_for_status()
            body = response.json()
            hit = not body["should_seek_help"] and body["matched_count"] >= 1
            return hit, body["answer"]

        def ask_plain(question: str) -> tuple[bool, str]:
            db = SessionLocal()
            try:
                body = answer_from_knowledge_base(
                    db,
                    question,
                    course_id=course_id,
                    approved_only=False,
                    course_scoped=False,
                )
            finally:
                db.close()
            hit = not body.should_seek_help and body.matched_count >= 1
            return hit, body.answer

        filtered_rows = []
        plain_rows = []
        for kind, questions in (("in-document", IN_DOCUMENT), ("absent", ABSENT)):
            for question in questions:
                hit, text = ask_filtered(question)
                filtered_rows.append((kind, question, hit, text))
                hit, text = ask_plain(question)
                plain_rows.append((kind, question, hit, text))

    filtered_ok = _print_round(
        "Filtered (approved_only=true, course_scoped=true)", filtered_rows
    )
    plain_ok = _print_round(
        "Plain RAG (approved_only=false, course_scoped=false)", plain_rows
    )
    if filtered_ok != (3, 3) or plain_ok != (3, 3):
        print(
            "\nExpected 3/3 answered and 3/3 not found in both modes "
            "on this isolated demo PDF.",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
