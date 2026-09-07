"""Upload hardening: extension allow-lists, size caps, and magic-byte sniffing."""

from __future__ import annotations

from pathlib import Path

from fastapi import HTTPException, status

# extension → accepted leading magic bytes (empty tuple = text / no magic)
_MAGIC: dict[str, tuple[bytes, ...]] = {
    ".pdf": (b"%PDF",),
    ".png": (b"\x89PNG\r\n\x1a\n",),
    ".jpg": (b"\xff\xd8\xff",),
    ".jpeg": (b"\xff\xd8\xff",),
    ".gif": (b"GIF87a", b"GIF89a"),
    ".webp": (b"RIFF",),  # RIFF....WEBP — checked further below
    ".docx": (b"PK\x03\x04", b"PK\x05\x06", b"PK\x07\x08"),
    ".pptx": (b"PK\x03\x04", b"PK\x05\x06", b"PK\x07\x08"),
    ".xlsx": (b"PK\x03\x04", b"PK\x05\x06", b"PK\x07\x08"),
    ".zip": (b"PK\x03\x04", b"PK\x05\x06", b"PK\x07\x08"),
    ".txt": (),
    ".md": (),
    ".csv": (),
    ".html": (),
    ".htm": (),
}


def safe_filename(original: str) -> str:
    """Drop path components; keep a short basename."""
    base = Path(original or "upload").name
    cleaned = "".join(ch if ch.isalnum() or ch in "._- " else "_" for ch in base)
    return (cleaned.strip(" ._") or "upload")[:120]


def extension_of(filename: str) -> str:
    return Path(filename or "").suffix.lower()


def assert_upload_allowed(
    *,
    filename: str,
    data: bytes,
    allowed_extensions: set[str],
    max_bytes: int,
) -> str:
    """Validate size, extension, and magic bytes. Returns normalized extension."""
    if len(data) > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds {max_bytes // 1_000_000} MB limit.",
        )
    if len(data) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Empty uploads are not allowed.",
        )
    ext = extension_of(filename)
    if ext not in allowed_extensions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File type {ext or '(none)'} is not allowed.",
        )
    _assert_magic(ext, data)
    return ext


def _assert_magic(ext: str, data: bytes) -> None:
    expected = _MAGIC.get(ext)
    if expected is None or expected == ():
        # Text-like: reject if it looks like an executable / ELF / PE
        if data.startswith((b"\x7fELF", b"MZ", b"\x00\x00")):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File content does not match a safe text upload.",
            )
        return
    if not any(data.startswith(magic) for magic in expected):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File content does not match its extension.",
        )
    if ext == ".webp" and b"WEBP" not in data[:16]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File content does not match its extension.",
        )
