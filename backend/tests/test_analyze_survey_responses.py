from scripts.analyze_survey_responses import build_summary, main


def test_build_summary_meets_likert_targets():
    summary = build_summary()

    assert summary["pilot_context"]["student_respondents"] == 8
    assert summary["pilot_context"]["professor_respondents"] == 4

    for item in summary["student_likert"]:
        assert item["average"] >= 4.0

    for item in summary["professor_likert"]:
        assert item["average"] >= 4.0


def test_main_writes_summary_files(tmp_path, monkeypatch):
    import scripts.analyze_survey_responses as survey_analysis

    monkeypatch.setattr(survey_analysis, "OUTPUT_DIR", tmp_path)
    main()

    assert (tmp_path / "survey_evaluation_summary.json").exists()
    assert (tmp_path / "survey_evaluation_summary.md").exists()
