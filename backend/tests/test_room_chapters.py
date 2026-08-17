import os

from app.services.canvas_service import canvas_mode
from app.services.demo_mode import demo_mode
from app.services.room_chapters import (
    canvas_chapter_label,
    chapters_for_course,
    merge_course_chapters,
    resolve_chapter_source,
)


def test_canvas_module_prefix_strips_to_chapter_name():
    assert canvas_chapter_label("Module 2 — Divide & Conquer") == "Divide & Conquer"
    assert canvas_chapter_label("Module 4 - Hashing") == "Hashing"
    assert canvas_chapter_label("Shortest paths") == "Shortest paths"


def test_canvas_modules_merge_onto_syllabus():
    merged = merge_course_chapters(
        ["Divide & conquer", "Hashing", "Quiz prep"],
        ["Module 2 — Divide & Conquer", "Module 9 — NP-completeness"],
    )
    by_label = {label: source for label, source in merged}
    assert by_label["Divide & conquer"] == "both"
    assert by_label["Hashing"] == "syllabus"
    assert by_label["NP-completeness"] == "canvas"
    assert [label for label, _source in merged][0] == "Divide & conquer"


def test_demo_syllabus_is_gated(monkeypatch):
    monkeypatch.setenv("OFFICEHOURS_DEMO", "true")
    assert chapters_for_course("CSC 3323")
    monkeypatch.setenv("OFFICEHOURS_DEMO", "false")
    assert chapters_for_course("CSC 3323") == []
    assert chapters_for_course("COM 1301") == []


def test_production_chapter_source_is_canvas_or_empty():
    assert (
        resolve_chapter_source(syllabus=[], canvas_modules=["Graphs"], posted=False)
        == "canvas"
    )
    assert resolve_chapter_source(syllabus=[], canvas_modules=[], posted=False) == "empty"
    assert resolve_chapter_source(syllabus=[], canvas_modules=[], posted=True) == "posted"


def test_canvas_mode_is_none_without_demo_or_credentials(monkeypatch):
    monkeypatch.delenv("CANVAS_BASE_URL", raising=False)
    monkeypatch.delenv("CANVAS_ACCESS_TOKEN", raising=False)
    monkeypatch.delenv("OFFICEHOURS_CANVAS_MODE", raising=False)
    monkeypatch.setenv("OFFICEHOURS_DEMO", "false")
    assert demo_mode() is False
    assert canvas_mode() == "none"
    monkeypatch.setenv("OFFICEHOURS_DEMO", "true")
    assert canvas_mode() == "local"
