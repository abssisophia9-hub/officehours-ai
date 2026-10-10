"""Extract plain text from uploaded course material files.

Supported today:

- ``.pdf``       — slide exports / lecture notes (pypdf)
- ``.docx``      — Word notes (python-docx)
- ``.txt``/``.md`` — plain notes
- ``.vtt``/``.srt`` — video transcripts / captions (the "video" path:
  professors upload the lecture recording's caption file; automatic
  speech-to-text, e.g. Whisper, can later feed this same route)

``extract_material_pages`` returns ``(pages, material_source)`` with PDF page
numbers kept. ``extract_material_text`` joins those pages for callers that
only need a string. Raises ``ValueError`` for unsupported or unreadable files.
"""

from __future__ import annotations

import io
import re
from dataclasses import dataclass

SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".txt", ".md", ".vtt", ".srt"}


@dataclass(frozen=True)
class MaterialPage:
    """One page of extracted text. Non-PDF files are a single page numbered 1."""

    page_number: int
    text: str


def extract_material_pages(filename: str, data: bytes) -> tuple[list[MaterialPage], str]:
    """Return ``(pages, material_source)``. PDF page numbers are 1-based."""
    name = (filename or "").lower().strip()
    extension = name[name.rfind(".") :] if "." in name else ""
    if extension not in SUPPORTED_EXTENSIONS:
        raise ValueError(
            "Unsupported file type. Upload PDF, DOCX, TXT, MD, or a video "
            "transcript (.vtt / .srt)."
        )

    if extension == ".pdf":
        return _extract_pdf_pages(data), "slides"
    if extension == ".docx":
        return [MaterialPage(1, _extract_docx(data))], "notes"
    if extension in {".vtt", ".srt"}:
        return [MaterialPage(1, _extract_transcript(data))], "video_transcript"
    return [MaterialPage(1, _decode(data))], "notes"


def extract_material_text(filename: str, data: bytes) -> tuple[str, str]:
    pages, source = extract_material_pages(filename, data)
    return "\n\n".join(page.text for page in pages), source


def _decode(data: bytes) -> str:
    return data.decode("utf-8", errors="ignore").strip()


def _extract_pdf_pages(data: bytes) -> list[MaterialPage]:
    from pypdf import PdfReader

    try:
        reader = PdfReader(io.BytesIO(data))
    except Exception as exc:  # pypdf raises many concrete types
        raise ValueError(f"Could not read PDF: {exc}") from exc
    pages: list[MaterialPage] = []
    for index, page in enumerate(reader.pages, start=1):
        try:
            text = (page.extract_text() or "").strip()
        except Exception:
            continue
        if text:
            pages.append(MaterialPage(index, text))
    if not pages:
        raise ValueError(
            "No extractable text found in the PDF (scanned images need OCR)."
        )
    return pages


def _extract_docx(data: bytes) -> str:
    from docx import Document

    try:
        document = Document(io.BytesIO(data))
    except Exception as exc:
        raise ValueError(f"Could not read DOCX: {exc}") from exc
    paragraphs = [p.text.strip() for p in document.paragraphs if p.text.strip()]
    if not paragraphs:
        raise ValueError("No text found in the DOCX file.")
    return "\n\n".join(paragraphs)


def _extract_transcript(data: bytes) -> str:
    """Strip cue numbers/timestamps from WebVTT / SRT caption files."""
    raw = _decode(data)
    lines = []
    for line in raw.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.upper().startswith("WEBVTT"):
            continue
        if "-->" in stripped:
            continue
        if re.fullmatch(r"\d+", stripped):
            continue
        if stripped.startswith(("NOTE", "STYLE", "REGION")):
            continue
        lines.append(stripped)
    if not lines:
        raise ValueError("No caption text found in the transcript file.")
    # Merge caption fragments into readable paragraphs.
    text = " ".join(lines)
    text = re.sub(r"\s+", " ", text)
    sentences = re.split(r"(?<=[.!?])\s+", text)
    paragraphs = []
    current: list[str] = []
    for sentence in sentences:
        current.append(sentence)
        if len(" ".join(current)) > 500:
            paragraphs.append(" ".join(current))
            current = []
    if current:
        paragraphs.append(" ".join(current))
    return "\n\n".join(paragraphs)
