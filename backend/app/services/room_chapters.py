"""Course chapter catalogs for the AUI Rooms community.

Production: the grid is this course's **Canvas modules**. Students pick one;
they do not type a list; we do not ship a hardcoded CSC/MTH outline.

Demo (``OFFICEHOURS_DEMO=true``): a sample syllabus per seeded course code
plus the local Canvas mirror, so FYP walkthroughs have a full grid.
"""

from __future__ import annotations

import re

from app.services.demo_mode import demo_mode

DEFAULT_CHAPTERS = ()

# Sample outlines used only when OFFICEHOURS_DEMO=true.
DEMO_COURSE_CHAPTERS: dict[str, tuple[str, ...]] = {
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


def demo_syllabus_chapters(code: str | None) -> list[str]:
    if not demo_mode():
        return []
    return list(DEMO_COURSE_CHAPTERS.get((code or "").strip(), ()))


def chapters_for_course(code: str | None) -> list[str]:
    """Demo syllabus chapters, or empty in production."""
    return demo_syllabus_chapters(code)


_MODULE_PREFIX = re.compile(r"^module\s+\d+\s*[—–\-:]+\s*", re.I)


def canvas_chapter_label(module_name: str) -> str:
    """Turn 'Module 2 - Divide & Conquer' into 'Divide & Conquer'."""
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
    that match a syllabus chapter (ignoring 'Module N  - ' prefixes) are marked
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


def resolve_chapter_source(
    *,
    syllabus: list[str],
    canvas_modules: list[str],
    posted: bool,
) -> str:
    has_syllabus = bool(syllabus)
    has_canvas = bool(canvas_modules)
    if has_syllabus and has_canvas:
        return "demo-syllabus+canvas"
    if has_canvas:
        return "canvas"
    if has_syllabus:
        return "demo-syllabus"
    if posted:
        return "posted"
    return "empty"
