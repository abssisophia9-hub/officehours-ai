"""Course chapter catalogs for the AUI Rooms community.

The inspo used a large engineering-discipline grid. Here the grid is the
active course's chapters — CSC 3323 is algorithms, CSC 2302 is data
structures — so discoverability stays inside the class, not a campus-wide
#BiomedicalEngineering feed.

Source of truth, in order:
1. Syllabus outline seeded per course code (this file) — the standing chapter
   list when Canvas is empty or unlinked.
2. Canvas module names for the linked LMS course, merged in when present.
   Live Canvas uses the modules API; demos use the local AUI mirror.
Students do not type this list. Professors do not edit it inside Rooms.
"""

from __future__ import annotations

import re

DEFAULT_CHAPTERS = (
    "Recursion",
    "Sorting",
    "Hashing",
    "Trees & AVL",
    "Heaps",
    "Graphs",
    "Greedy",
    "Dynamic Programming",
    "Complexity",
    "Proofs",
    "Quiz prep",
    "Project",
)

COURSE_CHAPTERS: dict[str, tuple[str, ...]] = {
    "CSC 2302": (
        "Arrays & lists",
        "Stacks & queues",
        "Recursion",
        "Trees",
        "BST",
        "AVL",
        "Hashing",
        "Heaps",
        "Graphs",
        "Sorting",
        "Complexity",
        "Project",
    ),
    "CSC 3323": (
        "Asymptotics",
        "Divide & conquer",
        "Recursion",
        "Sorting",
        "Hashing",
        "Greedy",
        "Dynamic programming",
        "Graphs",
        "Shortest paths",
        "NP-completeness",
        "Amortized analysis",
        "Quiz prep",
    ),
    "CSC 3351": (
        "Processes",
        "Threads",
        "Scheduling",
        "Synchronization",
        "Deadlock",
        "Memory",
        "Paging",
        "File systems",
        "I/O",
        "Virtualization",
        "Quiz prep",
        "Project",
    ),
    "CSC 3326": (
        "ER modeling",
        "Relational algebra",
        "SQL",
        "Normalization",
        "Indexing",
        "Transactions",
        "Concurrency",
        "Recovery",
        "NoSQL",
        "Quiz prep",
        "Project",
    ),
    "CSC 3324": (
        "Requirements",
        "Architecture",
        "UML",
        "Design patterns",
        "Testing",
        "Agile",
        "Git workflow",
        "Code review",
        "Quiz prep",
        "Project",
    ),
    "CSC 3374": (
        "Sockets",
        "RPC",
        "Consensus",
        "Replication",
        "CAP",
        "MapReduce",
        "Cloud patterns",
        "Quiz prep",
        "Project",
    ),
    "MTH 1304": (
        "Logic",
        "Sets",
        "Proofs",
        "Induction",
        "Counting",
        "Graphs",
        "Relations",
        "Boolean algebra",
        "Quiz prep",
    ),
    "COM 1301": (
        "Rhetoric",
        "Audience",
        "Structure",
        "Citations",
        "Oral delivery",
        "Visuals",
        "Peer review",
    ),
}


def chapters_for_course(code: str | None) -> list[str]:
    return list(COURSE_CHAPTERS.get((code or "").strip(), DEFAULT_CHAPTERS))


_MODULE_PREFIX = re.compile(r"^module\s+\d+\s*[—–\-:]+\s*", re.I)


def canvas_chapter_label(module_name: str) -> str:
    """Turn 'Module 2 — Divide & Conquer' into 'Divide & Conquer'."""
    text = (module_name or "").strip()
    stripped = _MODULE_PREFIX.sub("", text).strip()
    return stripped or text


def _chapter_key(label: str) -> str:
    return re.sub(r"\s+", " ", (label or "").strip()).casefold()


def merge_course_chapters(
    syllabus: list[str],
    canvas_modules: list[str],
) -> list[tuple[str, str]]:
    """Return (label, source) where source is syllabus | canvas | both.

    Syllabus order is kept so the grid stays a course outline. Canvas modules
    that match a syllabus chapter (ignoring 'Module N —' prefixes) are marked
    both. Extra Canvas modules append.
    """
    merged: list[tuple[str, str]] = []
    index_by_key: dict[str, int] = {}
    for label in syllabus:
        clean = (label or "").strip()
        if not clean:
            continue
        key = _chapter_key(clean)
        if key in index_by_key:
            continue
        index_by_key[key] = len(merged)
        merged.append((clean, "syllabus"))
    for raw in canvas_modules:
        label = canvas_chapter_label(raw)
        if not label:
            continue
        key = _chapter_key(label)
        if key in index_by_key:
            idx = index_by_key[key]
            prev_label, prev_source = merged[idx]
            merged[idx] = (prev_label, "both" if prev_source == "syllabus" else prev_source)
            continue
        index_by_key[key] = len(merged)
        merged.append((label, "canvas"))
    return merged
