"""Canvas LMS → course KB bridge.

Two modes:

1. **Live Canvas** — set ``CANVAS_BASE_URL`` + ``CANVAS_ACCESS_TOKEN``.
   Sync pulls files/pages from the course's ``canvas_course_id``.

2. **Local AUI mirror (default)** — when live credentials are absent, sync
   uses seeded Canvas-style course files so professors can still push slides
   into the KB the same way a real LMS sync would.

Professors can also paste/upload text via ``POST /knowledge/materials``;
both paths call ``ingest_course_material`` so the student agent sees one KB.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin
from urllib.request import Request, urlopen

from sqlalchemy.orm import Session

from app.models.auth import Course
from app.models.knowledge import KnowledgeEntry
from app.services.knowledge_service import ingest_course_material

# Demo Canvas file mirror keyed by canvas_course_id.
LOCAL_CANVAS_FILES: dict[str, list[dict[str, str]]] = {
    "4001": [
        {
            "external_id": "cs400-week4-hashing",
            "title": "Week 4 — Hash tables (Canvas)",
            "content": (
                "Hash tables map keys to buckets using a hash function.\n\n"
                "Collisions are handled with chaining or open addressing.\n\n"
                "Chaining stores a linked list (or another structure) in each bucket.\n\n"
                "Open addressing probes for the next empty slot "
                "(linear, quadratic, or double hashing).\n\n"
                "Load factor affects lookup performance; rehash when it grows too high."
            ),
        },
        {
            "external_id": "cs400-week5-bst",
            "title": "Week 5 — Binary search trees (Canvas)",
            "content": (
                "A binary search tree keeps left children smaller and right children larger.\n\n"
                "Search, insert, and delete depend on balanced shape.\n\n"
                "Unbalanced trees can degrade to O(n); self-balancing trees keep height logarithmic."
            ),
        },
    ],
    "3301": [
        {
            "external_id": "cs330-week2-dc",
            "title": "Week 2 — Divide and conquer (Canvas)",
            "content": (
                "Divide and conquer splits a problem, solves subproblems, then combines.\n\n"
                "Mergesort is the classic example: split, sort halves, merge.\n\n"
                "Recurrence T(n) = 2T(n/2) + O(n) solves to O(n log n)."
            ),
        },
    ],
}


@dataclass
class CanvasFile:
    external_id: str
    title: str
    content: str
    source: str = "canvas"


def canvas_mode() -> str:
    base = (os.getenv("CANVAS_BASE_URL") or "").strip()
    token = (os.getenv("CANVAS_ACCESS_TOKEN") or "").strip()
    if base and token:
        return "live"
    return (os.getenv("OFFICEHOURS_CANVAS_MODE") or "local").strip().lower() or "local"


def canvas_status(course: Course) -> dict[str, Any]:
    mode = canvas_mode()
    canvas_id = getattr(course, "canvas_course_id", None)
    files = list_course_files(course)
    return {
        "mode": mode,
        "configured": mode == "live" or bool(canvas_id),
        "canvas_course_id": canvas_id,
        "course_id": course.id,
        "course_code": course.code,
        "available_files": [
            {"external_id": item.external_id, "title": item.title, "source": item.source}
            for item in files
        ],
        "message": (
            "Live Canvas API connected."
            if mode == "live"
            else (
                "Using local AUI Canvas mirror for this course "
                "(set CANVAS_BASE_URL + CANVAS_ACCESS_TOKEN for live sync)."
                if canvas_id
                else "No canvas_course_id on this course yet."
            )
        ),
    }


def list_course_files(course: Course) -> list[CanvasFile]:
    canvas_id = getattr(course, "canvas_course_id", None)
    if not canvas_id:
        return []
    if canvas_mode() == "live":
        return _list_live_canvas_files(str(canvas_id))
    return [
        CanvasFile(
            external_id=item["external_id"],
            title=item["title"],
            content=item["content"],
            source="canvas",
        )
        for item in LOCAL_CANVAS_FILES.get(str(canvas_id), [])
    ]


def sync_course_materials(
    db: Session,
    course: Course,
    *,
    auto_approve: bool = True,
) -> dict[str, Any]:
    files = list_course_files(course)
    if not files:
        return {
            "course_id": course.id,
            "canvas_course_id": getattr(course, "canvas_course_id", None),
            "mode": canvas_mode(),
            "files_seen": 0,
            "chunks_created": 0,
            "entry_ids": [],
            "skipped": [],
            "message": "No Canvas files found for this course.",
        }

    created_ids: list[int] = []
    skipped: list[str] = []
    chunks_total = 0
    for item in files:
        if _already_ingested(db, course.id, item.external_id):
            skipped.append(item.title)
            continue
        entries = ingest_course_material(
            db,
            title=item.title,
            content=item.content,
            source="canvas",
            course_id=course.id,
            course=course.code,
            auto_approve=auto_approve,
            external_id=item.external_id,
        )
        chunks_total += len(entries)
        created_ids.extend(entry.id for entry in entries)

    return {
        "course_id": course.id,
        "canvas_course_id": getattr(course, "canvas_course_id", None),
        "mode": canvas_mode(),
        "files_seen": len(files),
        "chunks_created": chunks_total,
        "entry_ids": created_ids,
        "skipped": skipped,
        "message": (
            f"Synced {len(files) - len(skipped)} Canvas file(s) into the course KB "
            f"({chunks_total} chunk(s)"
            f"{', skipped ' + str(len(skipped)) + ' already imported' if skipped else ''})."
        ),
    }


def _already_ingested(db: Session, course_id: int, external_id: str) -> bool:
    marker = f"canvas:{external_id}"
    return (
        db.query(KnowledgeEntry.id)
        .filter(
            KnowledgeEntry.course_id == course_id,
            KnowledgeEntry.material_source == "canvas",
            KnowledgeEntry.professor_note.contains(marker),
        )
        .first()
        is not None
    )


def _list_live_canvas_files(canvas_course_id: str) -> list[CanvasFile]:
    base = (os.getenv("CANVAS_BASE_URL") or "").rstrip("/") + "/"
    token = (os.getenv("CANVAS_ACCESS_TOKEN") or "").strip()
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}

    files: list[CanvasFile] = []
    # Pages (HTML → text)
    for page in _canvas_get_json(
        urljoin(base, f"api/v1/courses/{canvas_course_id}/pages?per_page=50"),
        headers,
    ):
        url = page.get("url")
        if not url:
            continue
        detail = _canvas_get_json(
            urljoin(base, f"api/v1/courses/{canvas_course_id}/pages/{url}"),
            headers,
        )
        body = _strip_html(str(detail.get("body") or ""))
        if len(body) < 20:
            continue
        files.append(
            CanvasFile(
                external_id=f"page-{url}",
                title=str(detail.get("title") or url),
                content=body,
                source="canvas",
            )
        )

    # Text-ish files with a download URL
    for item in _canvas_get_json(
        urljoin(base, f"api/v1/courses/{canvas_course_id}/files?per_page=50"),
        headers,
    ):
        name = str(item.get("display_name") or item.get("filename") or "Canvas file")
        lower = name.lower()
        if not lower.endswith((".txt", ".md", ".html", ".htm")):
            continue
        download_url = item.get("url")
        if not download_url:
            continue
        content = _canvas_get_text(str(download_url), headers)
        if len(content) < 20:
            continue
        files.append(
            CanvasFile(
                external_id=f"file-{item.get('id')}",
                title=name,
                content=content,
                source="canvas",
            )
        )
    return files


def _canvas_get_json(url: str, headers: dict[str, str]) -> list[dict[str, Any]]:
    try:
        request = Request(url, headers=headers)
        with urlopen(request, timeout=20) as response:
            import json

            payload = json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, TimeoutError, ValueError):
        return []
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    return []


def _canvas_get_text(url: str, headers: dict[str, str]) -> str:
    try:
        request = Request(url, headers=headers)
        with urlopen(request, timeout=20) as response:
            return response.read().decode("utf-8", errors="ignore")
    except (HTTPError, URLError, TimeoutError, ValueError):
        return ""


def _strip_html(raw: str) -> str:
    import re

    text = re.sub(r"(?is)<script.*?>.*?</script>", " ", raw)
    text = re.sub(r"(?is)<style.*?>.*?</style>", " ", text)
    text = re.sub(r"(?s)<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()
