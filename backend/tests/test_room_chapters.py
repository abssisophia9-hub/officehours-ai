from app.services.room_chapters import canvas_chapter_label, merge_course_chapters


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
