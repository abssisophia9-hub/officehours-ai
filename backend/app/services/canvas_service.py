"""Canvas LMS → course KB bridge (SaaS-style).

Two modes:

1. **Live Canvas** — set ``CANVAS_BASE_URL`` + ``CANVAS_ACCESS_TOKEN``.
   Sync pulls course **modules** (then pages/files) from the course's
   ``canvas_course_id``.

2. **Local AUI mirror (default)** — when live credentials are absent, sync
   uses a seeded module-structured Canvas mirror so the exact same launch /
   sync path works in demos without AUI credentials.

Entry points:

- ``POST /canvas/launch`` — one click inside a Canvas course: auto-provision
  user + course + membership, ingest module slides, spawn the course agent.
- ``POST /knowledge/canvas/sync`` — professor-triggered re-sync.
- ``POST /knowledge/materials`` — manual paste; same ingest, same KB.
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
from app.services.demo_mode import demo_mode
from app.services.knowledge_service import ingest_course_material

# Module-structured Canvas mirror keyed by canvas_course_id.
# "2101" (CSC 3351 Operating Systems) is intentionally NOT pre-seeded in demo
# accounts: launching from that Canvas course proves SaaS-style auto-provisioning.
# Canvas course IDs stay stable for demos; codes/titles match AUI catalog.
LOCAL_CANVAS_COURSES: dict[str, dict[str, Any]] = {
    "4001": {
        "code": "CSC 2302",
        "title": "Data Structures",
        "term": "Spring 2026",
        "modules": [
            {
                "name": "Module 4 — Hashing",
                "items": [
                    {
                        "external_id": "csc2302-week4-hashing",
                        "title": "Week 4 — Hash tables (slides)",
                        "content": (
                            "Hash tables map keys to buckets using a hash function.\n\n"
                            "Collisions are handled with chaining or open addressing.\n\n"
                            "Chaining stores a linked list (or another structure) in each bucket.\n\n"
                            "Open addressing probes for the next empty slot "
                            "(linear, quadratic, or double hashing).\n\n"
                            "Load factor affects lookup performance; rehash when it grows too high."
                        ),
                    },
                ],
            },
            {
                "name": "Module 5 — Trees",
                "items": [
                    {
                        "external_id": "csc2302-week5-bst",
                        "title": "Week 5 — Binary search trees (slides)",
                        "content": (
                            "A binary search tree keeps left children smaller and right children larger.\n\n"
                            "Search, insert, and delete depend on balanced shape.\n\n"
                            "Unbalanced trees can degrade to O(n); self-balancing trees keep height logarithmic."
                        ),
                    },
                ],
            },
        ],
    },
    "3301": {
        "code": "CSC 3323",
        "title": "Analysis of Algorithms",
        "term": "Spring 2026",
        "modules": [
            {
                "name": "Module 2 — Divide & Conquer",
                "items": [
                    {
                        "external_id": "csc3323-week2-dc",
                        "title": "Week 2 — Divide and conquer (slides)",
                        "content": (
                            "Divide and conquer splits a problem, solves subproblems, then combines.\n\n"
                            "Mergesort is the classic example: split, sort halves, merge.\n\n"
                            "Recurrence T(n) = 2T(n/2) + O(n) solves to O(n log n)."
                        ),
                    },
                ],
            },
        ],
    },
    "2101": {
        "code": "CSC 3351",
        "title": "Operating Systems",
        "term": "Spring 2026",
        "modules": [
            {
                "name": "Module 1 — Processes",
                "items": [
                    {
                        "external_id": "csc3351-week1-processes",
                        "title": "Week 1 — Processes and threads (slides)",
                        "content": (
                            "A process is a running program with its own address space.\n\n"
                            "Threads share the process address space but have their own stacks.\n\n"
                            "A context switch saves one process state and restores another; "
                            "it is pure overhead, so schedulers try to minimize it."
                        ),
                    },
                ],
            },
            {
                "name": "Module 2 — Scheduling",
                "items": [
                    {
                        "external_id": "csc3351-week2-scheduling",
                        "title": "Week 2 — CPU scheduling (slides)",
                        "content": (
                            "First-come first-served runs jobs in arrival order and suffers convoy effects.\n\n"
                            "Shortest job first minimizes average waiting time but needs burst estimates.\n\n"
                            "Round robin gives each process a time quantum; small quanta increase "
                            "context-switch overhead, large quanta approach FCFS."
                        ),
                    },
                ],
            },
        ],
    },
    "3374": {
        "code": "CSC 3374",
        "title": "Adv. Distributed Programming Paradigms",
        "term": "Spring 2026",
        "modules": [
            {
                "name": "Module 1 — Message Passing",
                "items": [
                    {
                        "external_id": "csc3374-week1-mpi",
                        "title": "Week 1 — Message-passing and RPC (slides)",
                        "content": (
                            "Distributed programs coordinate across machines with message passing or RPC.\n\n"
                            "Synchronous RPC blocks until a reply; asynchronous messaging decouples senders.\n\n"
                            "Partial failure is normal: design for timeouts, retries, and idempotent handlers."
                        ),
                    },
                ],
            },
        ],
    },
}


@dataclass
class CanvasFile:
    external_id: str
    title: str
    content: str
    module: str = ""
    source: str = "canvas"


def canvas_mode() -> str:
    base = (os.getenv("CANVAS_BASE_URL") or "").strip()
    token = (os.getenv("CANVAS_ACCESS_TOKEN") or "").strip()
    if base and token:
        return "live"
    explicit = (os.getenv("OFFICEHOURS_CANVAS_MODE") or "").strip().lower()
    if explicit:
        return explicit
    if demo_mode():
        return "local"
    return "none"


def canvas_course_snapshot(canvas_course_id: str) -> dict[str, Any] | None:
    """Course metadata used to auto-provision a tenant on first launch."""
    if canvas_mode() == "live":
        base = (os.getenv("CANVAS_BASE_URL") or "").rstrip("/") + "/"
        token = (os.getenv("CANVAS_ACCESS_TOKEN") or "").strip()
        detail = _canvas_get_single(
            urljoin(base, f"api/v1/courses/{canvas_course_id}"),
            {"Authorization": f"Bearer {token}", "Accept": "application/json"},
        )
        if detail:
            return {
                "code": str(detail.get("course_code") or f"CANVAS-{canvas_course_id}"),
                "title": str(detail.get("name") or f"Canvas course {canvas_course_id}"),
                "term": None,
            }
        return None
    if canvas_mode() != "local":
        return None
    spec = LOCAL_CANVAS_COURSES.get(str(canvas_course_id))
    if spec is None:
        return None
    return {"code": spec["code"], "title": spec["title"], "term": spec.get("term")}


def canvas_status(db: Session, course: Course) -> dict[str, Any]:
    mode = canvas_mode()
    canvas_id = getattr(course, "canvas_course_id", None)
    files = list_course_files(course)
    approved_chunks = (
        db.query(KnowledgeEntry.id)
        .filter(
            KnowledgeEntry.course_id == course.id,
            KnowledgeEntry.status == "approved",
        )
        .count()
    )
    return {
        "mode": mode,
        "configured": mode == "live" or bool(canvas_id),
        "canvas_course_id": canvas_id,
        "course_id": course.id,
        "course_code": course.code,
        "agent_ready": approved_chunks > 0,
        "kb_chunks": approved_chunks,
        "available_files": [
            {
                "external_id": item.external_id,
                "title": item.title,
                "module": item.module,
                "source": item.source,
            }
            for item in files
        ],
        "message": (
            "Live Canvas API connected."
            if mode == "live"
            else (
                "Using local AUI Canvas mirror for this demo course "
                "(set CANVAS_BASE_URL + CANVAS_ACCESS_TOKEN for a community deploy)."
                if mode == "local" and canvas_id
                else (
                    "No canvas_course_id on this course yet."
                    if not canvas_id
                    else "Canvas is not configured. Set CANVAS_BASE_URL + CANVAS_ACCESS_TOKEN, or OFFICEHOURS_DEMO=true for the local mirror."
                )
            )
        ),
    }


def list_course_files(course: Course) -> list[CanvasFile]:
    canvas_id = getattr(course, "canvas_course_id", None)
    if not canvas_id:
        return []
    return list_canvas_files_by_id(str(canvas_id))


def list_canvas_module_names(course: Course | None) -> list[str]:
    """Module titles from the linked Canvas course (live API or local mirror).

    Used by Rooms as the LMS half of the chapter grid. Empty when the course
    has no canvas_course_id or the mirror/API has no modules.
    """
    if course is None:
        return []
    canvas_id = getattr(course, "canvas_course_id", None)
    if not canvas_id:
        return []
    if canvas_mode() == "live":
        return _list_live_module_names(str(canvas_id))
    if canvas_mode() != "local":
        return []
    spec = LOCAL_CANVAS_COURSES.get(str(canvas_id)) or {}
    names: list[str] = []
    for module in spec.get("modules", []):
        name = str(module.get("name") or "").strip()
        if name:
            names.append(name)
    return names


def _list_live_module_names(canvas_course_id: str) -> list[str]:
    base = (os.getenv("CANVAS_BASE_URL") or "").rstrip("/") + "/"
    token = (os.getenv("CANVAS_ACCESS_TOKEN") or "").strip()
    if not token:
        return []
    modules = _canvas_get_json(
        urljoin(base, f"api/v1/courses/{canvas_course_id}/modules?per_page=50"),
        {"Authorization": f"Bearer {token}", "Accept": "application/json"},
    )
    names: list[str] = []
    for module in modules:
        name = str(module.get("name") or "").strip()
        if name:
            names.append(name)
    return names


def list_canvas_files_by_id(canvas_course_id: str) -> list[CanvasFile]:
    if canvas_mode() == "live":
        return _list_live_canvas_files(canvas_course_id)
    if canvas_mode() != "local":
        return []
    spec = LOCAL_CANVAS_COURSES.get(canvas_course_id)
    if spec is None:
        return []
    files: list[CanvasFile] = []
    for module in spec.get("modules", []):
        for item in module.get("items", []):
            files.append(
                CanvasFile(
                    external_id=item["external_id"],
                    title=item["title"],
                    content=item["content"],
                    module=str(module.get("name") or ""),
                    source="canvas",
                )
            )
    return files


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
        title = f"{item.module} · {item.title}" if item.module else item.title
        entries = ingest_course_material(
            db,
            title=title,
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

    # Preferred: module structure (what professors curate for students).
    modules = _canvas_get_json(
        urljoin(base, f"api/v1/courses/{canvas_course_id}/modules?per_page=50"),
        headers,
    )
    for module in modules:
        module_id = module.get("id")
        module_name = str(module.get("name") or "")
        if not module_id:
            continue
        for item in _canvas_get_json(
            urljoin(
                base,
                f"api/v1/courses/{canvas_course_id}/modules/{module_id}/items?per_page=50",
            ),
            headers,
        ):
            kind = str(item.get("type") or "")
            if kind == "Page" and item.get("page_url"):
                detail = _canvas_get_single(
                    urljoin(
                        base,
                        f"api/v1/courses/{canvas_course_id}/pages/{item['page_url']}",
                    ),
                    headers,
                )
                body = _strip_html(str((detail or {}).get("body") or ""))
                if len(body) >= 20:
                    files.append(
                        CanvasFile(
                            external_id=f"page-{item['page_url']}",
                            title=str(item.get("title") or item["page_url"]),
                            content=body,
                            module=module_name,
                        )
                    )
            elif kind == "File" and item.get("content_id"):
                detail = _canvas_get_single(
                    urljoin(base, f"api/v1/files/{item['content_id']}"),
                    headers,
                )
                name = str(
                    (detail or {}).get("display_name") or item.get("title") or "file"
                )
                url = (detail or {}).get("url")
                if url and name.lower().endswith((".txt", ".md", ".html", ".htm")):
                    content = _canvas_get_text(str(url), headers)
                    if len(content) >= 20:
                        files.append(
                            CanvasFile(
                                external_id=f"file-{item['content_id']}",
                                title=name,
                                content=content,
                                module=module_name,
                            )
                        )
    if files:
        return files

    # Fallback: bare pages + files listing for courses without modules.
    for page in _canvas_get_json(
        urljoin(base, f"api/v1/courses/{canvas_course_id}/pages?per_page=50"),
        headers,
    ):
        url = page.get("url")
        if not url:
            continue
        detail = _canvas_get_single(
            urljoin(base, f"api/v1/courses/{canvas_course_id}/pages/{url}"),
            headers,
        )
        body = _strip_html(str((detail or {}).get("body") or ""))
        if len(body) >= 20:
            files.append(
                CanvasFile(
                    external_id=f"page-{url}",
                    title=str((detail or {}).get("title") or url),
                    content=body,
                )
            )
    for item in _canvas_get_json(
        urljoin(base, f"api/v1/courses/{canvas_course_id}/files?per_page=50"),
        headers,
    ):
        name = str(item.get("display_name") or item.get("filename") or "Canvas file")
        if not name.lower().endswith((".txt", ".md", ".html", ".htm")):
            continue
        download_url = item.get("url")
        if not download_url:
            continue
        content = _canvas_get_text(str(download_url), headers)
        if len(content) >= 20:
            files.append(
                CanvasFile(
                    external_id=f"file-{item.get('id')}",
                    title=name,
                    content=content,
                )
            )
    return files


def _canvas_get_json(url: str, headers: dict[str, str]) -> list[dict[str, Any]]:
    """Follow Canvas ``Link: rel=next`` pagination so a full module list is read."""
    import json
    import re

    collected: list[dict[str, Any]] = []
    next_url: str | None = url
    pages = 0
    while next_url and pages < 20:
        pages += 1
        try:
            request = Request(next_url, headers=headers)
            with urlopen(request, timeout=20) as response:
                payload = json.loads(response.read().decode("utf-8"))
                link = response.headers.get("Link") or response.headers.get("link") or ""
        except (HTTPError, URLError, TimeoutError, ValueError):
            break
        if isinstance(payload, list):
            collected.extend(item for item in payload if isinstance(item, dict))
        match = re.search(r'<([^>]+)>;\s*rel="next"', link)
        next_url = match.group(1) if match else None
    return collected


def _canvas_get_single(url: str, headers: dict[str, str]) -> dict[str, Any] | None:
    try:
        request = Request(url, headers=headers)
        with urlopen(request, timeout=20) as response:
            import json

            payload = json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, TimeoutError, ValueError):
        return None
    return payload if isinstance(payload, dict) else None


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
