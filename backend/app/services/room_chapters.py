"""Course chapter catalogs for the AUI Rooms community.

The inspo used a large engineering-discipline grid. Here the grid is the
active course's chapters — CSC 3323 is algorithms, CSC 2302 is data
structures — so discoverability stays inside the class, not a campus-wide
#BiomedicalEngineering feed.
"""

from __future__ import annotations

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
