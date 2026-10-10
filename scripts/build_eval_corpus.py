#!/usr/bin/env python3
"""Write the synthetic DEMO DATA PDFs used by the study-agent eval.

Re-run from the repo root with the backend virtualenv if a page changes.
The committed PDFs are what the harness ingests.
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "backend" / "demo_data" / "eval"

# One list of lines per page. Keep each page well under 900 characters so
# ingest stores one chunk per page (chunk index matches the page number).
PAPERS: dict[str, list[list[str]]] = {
    "csc2302_lecture_notes.pdf": [
        [
            "DEMO DATA. Not a real lecture and not a real course.",
            "CSC 2302 Data Structures, synthetic notes, page 1.",
            "A stack is last-in first-out. Push puts a value on top. Pop takes the top value off.",
            "The lab trace for this demo section uses a stack named cedar-stack with capacity 6.",
            "Students write the trace in C. Recursion is not this page.",
        ],
        [
            "DEMO DATA. CSC 2302 synthetic notes, page 2.",
            "A queue is first-in first-out. Enqueue adds at the rear. Dequeue removes at the front.",
            "The circular queue lab wraps the rear index when it passes the last slot.",
            "This lab is about index wrap in C. It is not a count of mugs and it is not a heap.",
        ],
        [
            "DEMO DATA. CSC 2302 synthetic notes, page 3.",
            "Separate chaining handles a collision by hanging a linked list on that bucket.",
            "Open addressing is only named here. No probe sequence is taught on this page.",
            "A binary search tree puts smaller keys on the left. Recursion stops at a null child.",
            "Red-black deletion, splay trees, and AVL balance factors are not on this page.",
        ],
    ],
    "csc2302_policy_sheet.pdf": [
        [
            "DEMO DATA. Synthetic section sheet for CSC 2302. Not a university catalog.",
            "This demo section meets Monday, Wednesday, and Friday.",
            "The instructor records every miss. On the seventh recorded miss in the semester,",
            "the instructor may request an administrative withdrawal graded WF.",
            "A short illness starts at the Health Center, then the Dean of Student Affairs, then the instructor.",
            "A visa appointment still counts inside those seven misses.",
        ],
        [
            "DEMO DATA. CSC 2302 synthetic section sheet, page 2.",
            "Office hours for this section are Tuesdays from 14:10 to 15:40 in Building 8, room 211.",
            "Bring the smallest C snippet that shows where you are stuck.",
            "A late lab loses 10 points per calendar day and is refused after 72 hours.",
            "The late-policy token printed on this sheet is cedar-stamp.",
        ],
        [
            "DEMO DATA. CSC 2302 synthetic section sheet, page 3.",
            "Weights for this demo section: labs 25, quizzes 15, midterm 25, final 35.",
            "A make-up midterm exists only with a Health Center note brought within 48 hours.",
            "That make-up sits on the next Saturday at 09:00 in the SSE lab.",
            "The final is a common exam at the registrar's posted time. This sheet does not move it.",
            "The review meeting is the last class before that posted final.",
        ],
    ],
    "csc2302_exam_prep.pdf": [
        [
            "DEMO DATA. Synthetic exam-prep sheet for CSC 2302. Not a real exam.",
            "Practice: trace cedar-stack of capacity 6, then one queue index wrap, then one chaining collision.",
            "The prep-quiz passphrase on this sheet is atlas-cedar.",
            "Bring a pencil. Phones stay in your bag.",
        ],
        [
            "DEMO DATA. CSC 2302 synthetic exam-prep sheet, page 2.",
            "This prep sheet stops at hashing and binary search trees.",
            "It does not include red-black deletion, Dijkstra, or the master theorem.",
            "If a fact is not on the lecture notes, the policy sheet, or this prep sheet, it is outside the approved pack.",
        ],
    ],
    "csc2302_draft_exam_notice.pdf": [
        [
            "DEMO DATA. DRAFT. Not approved. Not a real exam announcement.",
            "Draft midterm for CSC 2302 section 77: Thursday 16 April at 18:30 in Auditorium 3.",
            "The draft seating code is orange-row-c.",
            "The approved policy sheet does not carry this date, this room, or this code.",
        ],
        [
            "DEMO DATA. DRAFT. Not approved. CSC 2302 draft exam notice, page 2.",
            "The draft allows one handwritten index card.",
            "The card-rule token on this draft is saffron-card.",
            "Do not treat this file as stamped. It stays pending until a professor approves it.",
        ],
    ],
    "csc2302_pending_lab_extension.pdf": [
        [
            "DEMO DATA. DRAFT. Not approved. Not a real deadline change.",
            "Pending note for CSC 2302 lab 4, the queue-wrap exercise in C.",
            "The draft moves that deadline to 11 May at 23:59.",
            "The extension code on this pending note is fig-harvest.",
            "The approved late rule is still 72 hours. This extension is not stamped.",
        ],
    ],
    "csc3323_lecture_notes.pdf": [
        [
            "DEMO DATA. Not a real lecture. CSC 3323 Analysis of Algorithms, synthetic notes, page 1.",
            "The worksheet rule named cedar-split says the recurrence T(n)=2T(n/2)+n solves to n log n.",
            "Here recursion means a recurrence. It is not the CSC 2302 null-child tree lab.",
        ],
        [
            "DEMO DATA. CSC 3323 synthetic notes, page 2.",
            "Dijkstra on the demo campus graph starts at the node named Ifrane-gate.",
            "The shortest-path token on this page is olive-path.",
            "Greedy choice and overlapping subproblems are named here. Separate chaining is not retaught.",
        ],
    ],
    "csc3323_policy_sheet.pdf": [
        [
            "DEMO DATA. Synthetic section sheet for CSC 3323. Not a university catalog.",
            "This demo section meets Tuesday and Thursday.",
            "On the fifth recorded miss the instructor may request an administrative withdrawal graded WF.",
            "Office hours are Thursdays from 11:00 to 12:20 in Building 6, room 104.",
        ],
        [
            "DEMO DATA. CSC 3323 synthetic section sheet, page 2.",
            "A late homework loses 15 points per calendar day and is refused after 48 hours.",
            "The exam-prep passphrase for this algorithms section is atlas-ridge.",
            "atlas-ridge is not atlas-cedar. A make-up quiz, if the Health Center note is in, is Friday at 16:00 in room 104.",
        ],
    ],
}


def _pdf(pages: list[list[str]]) -> bytes:
    objects: dict[int, bytes] = {
        1: b"<< /Type /Catalog /Pages 2 0 R >>",
        3: b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    }
    kids: list[int] = []
    next_id = 4
    for lines in pages:
        page_id = next_id
        content_id = next_id + 1
        next_id += 2
        kids.append(page_id)
        ops = ["BT /F1 11 Tf 72 740 Td"]
        for index, line in enumerate(lines):
            if index:
                ops.append("0 -16 Td")
            escaped = line.replace("\\", r"\\").replace("(", r"\(").replace(")", r"\)")
            ops.append(f"({escaped}) Tj")
        ops.append("ET")
        stream = "\n".join(ops).encode()
        if len(stream) > 800:
            raise SystemExit(f"page stream too long ({len(stream)} bytes); split the page")
        objects[content_id] = (
            b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream"
        )
        objects[page_id] = (
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            f"/Contents {content_id} 0 R /Resources << /Font << /F1 3 0 R >> >> >>"
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
    out += f"trailer\n<< /Size {next_id} /Root 1 0 R >>\nstartxref\n{xref_at}\n%%EOF\n".encode()
    return bytes(out)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for name, pages in PAPERS.items():
        path = OUT / name
        path.write_bytes(_pdf(pages))
        print(f"{name}: {len(pages)} pages, {path.stat().st_size} bytes")


if __name__ == "__main__":
    main()
