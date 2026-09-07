"""Optional limit/offset pages. Omit limit → return a raw list (existing tests)."""

from __future__ import annotations

from typing import Any, TypeVar

T = TypeVar("T")

MAX_LIMIT = 200


def clamp_page(limit: int | None, offset: int | None) -> tuple[int | None, int]:
    off = max(0, int(offset or 0))
    if limit is None:
        return None, off
    return max(1, min(int(limit), MAX_LIMIT)), off


def page_or_list(items: list[T], *, limit: int | None, offset: int) -> list[T] | dict[str, Any]:
    if limit is None:
        return items
    total = len(items)
    chunk = items[offset : offset + limit]
    return {
        "items": chunk,
        "total": total,
        "limit": limit,
        "offset": offset,
        "has_more": offset + len(chunk) < total,
    }


def paginate_query(query, *, limit: int | None, offset: int):
    if limit is None:
        return query.all()
    total = query.count()
    chunk = query.offset(offset).limit(limit).all()
    return {
        "items": chunk,
        "total": total,
        "limit": limit,
        "offset": offset,
        "has_more": offset + len(chunk) < total,
    }
