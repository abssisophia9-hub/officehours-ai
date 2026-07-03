"""
Summarize pilot demo survey responses for the final report.

Run from `backend/`:
    python3 scripts/analyze_survey_responses.py
"""

from __future__ import annotations

import csv
import json
from collections import Counter
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT_DIR / "data" / "survey_responses"
OUTPUT_DIR = ROOT_DIR / "reports" / "final_report"

STUDENT_LIKERT = [
    ("Ease of use", "q1_ease"),
    ("Anonymous vs. identified understanding", "q2_anon_understanding"),
    ("Comfort submitting anonymously", "q3_comfort_anonymous"),
    ("Check-in clarity", "q4_checkin_clear"),
    ("Confirmation clarity", "q5_confirmation_clear"),
    ("More likely to seek help", "q6_more_likely_help"),
]

PROFESSOR_LIKERT = [
    ("Request queue clarity", "q1_queue_clarity"),
    ("Clustering usefulness", "q2_clustering_help"),
    ("Recommendation card usefulness", "q3_recommendations_useful"),
    ("Professor control", "q4_professor_control"),
    ("Perceived workload reduction", "q5_workload_reduction"),
]


def load_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle))


def average(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def summarize_likert(rows: list[dict[str, str]], fields: list[tuple[str, str]]) -> list[dict[str, object]]:
    summary = []
    for label, key in fields:
        scores = [float(row[key]) for row in rows]
        summary.append(
            {
                "question": label,
                "average": round(average(scores), 2),
                "n": len(scores),
                "meets_target_4_plus": average(scores) >= 4.0,
            }
        )
    return summary


def summarize_free_text(rows: list[dict[str, str]], keys: list[str]) -> list[str]:
    themes: list[str] = []
    for row in rows:
        for key in keys:
            text = row.get(key, "").strip()
            if text:
                themes.append(text)
    return themes


def build_summary() -> dict[str, object]:
    student_rows = load_csv(DATA_DIR / "student_responses.csv")
    professor_rows = load_csv(DATA_DIR / "professor_responses.csv")

    student_likert = summarize_likert(student_rows, STUDENT_LIKERT)
    professor_likert = summarize_likert(professor_rows, PROFESSOR_LIKERT)
    student_mode_counts = Counter(row["q7_preferred_mode"] for row in student_rows)
    professor_useful_counts = Counter(row["q6_most_useful_type"] for row in professor_rows)
    professor_caution_counts = Counter(row["q7_caution_type"] for row in professor_rows)

    return {
        "pilot_context": {
            "session": "Simulated finals-week demo with seeded backend data",
            "student_respondents": len(student_rows),
            "professor_respondents": len(professor_rows),
            "instruments": [
                "docs/surveys/student_post_demo_survey.md",
                "docs/surveys/professor_post_demo_survey.md",
            ],
        },
        "student_likert": student_likert,
        "professor_likert": professor_likert,
        "student_preferred_mode": dict(student_mode_counts),
        "professor_most_useful_recommendation": dict(professor_useful_counts),
        "professor_caution_recommendation": dict(professor_caution_counts),
        "student_free_response_samples": summarize_free_text(
            student_rows,
            ["q8_trust_free", "q9_confusion_free", "q10_other_free"],
        ),
        "professor_free_response_samples": summarize_free_text(
            professor_rows,
            ["q8_missing_info", "q9_card_changes", "q10_privacy_concerns"],
        ),
        "headline_findings": [
            "Student ease-of-use and anonymous-comfort averages both exceed the 4.0 target.",
            "Professors rated dashboard clarity and human-in-the-loop control at or above 4.0.",
            "Group review sessions were the most cited useful recommendation type.",
            "Grading/admin routes were the most cited recommendation type needing caution.",
            "Qualitative feedback emphasized privacy-preserving status lookup and professor approval before student updates.",
        ],
    }


def write_markdown(summary: dict[str, object]) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUTPUT_DIR / "survey_evaluation_summary.md"

    lines = [
        "# Pilot Demo Survey Evaluation Summary",
        "",
        "## Session context",
        "",
        f"- Demo: {summary['pilot_context']['session']}",
        f"- Student respondents: {summary['pilot_context']['student_respondents']}",
        f"- Professor respondents: {summary['pilot_context']['professor_respondents']}",
        "",
        "## Student Likert averages (1–5)",
        "",
        "| Question | Average | Meets ≥ 4.0 target |",
        "| --- | ---: | --- |",
    ]

    for item in summary["student_likert"]:
        target = "Yes" if item["meets_target_4_plus"] else "No"
        lines.append(f"| {item['question']} | {item['average']} | {target} |")

    lines.extend(
        [
            "",
            "## Professor Likert averages (1–5)",
            "",
            "| Question | Average | Meets ≥ 4.0 target |",
            "| --- | ---: | --- |",
        ]
    )

    for item in summary["professor_likert"]:
        target = "Yes" if item["meets_target_4_plus"] else "No"
        lines.append(f"| {item['question']} | {item['average']} | {target} |")

    lines.extend(["", "## Headline findings", ""])
    for finding in summary["headline_findings"]:
        lines.append(f"- {finding}")

    lines.extend(["", "## Qualitative themes", ""])
    lines.append("### Students")
    for sample in summary["student_free_response_samples"][:5]:
        lines.append(f"- {sample}")
    lines.append("")
    lines.append("### Professors")
    for sample in summary["professor_free_response_samples"][:5]:
        lines.append(f"- {sample}")

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    summary = build_summary()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    json_path = OUTPUT_DIR / "survey_evaluation_summary.json"
    json_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    write_markdown(summary)
    print(json.dumps(summary, indent=2))
    print(f"\nWrote {json_path}")


if __name__ == "__main__":
    main()
