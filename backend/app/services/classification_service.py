"""
Service responsible for calling AI classification logic and turning results
into a recommended action.
"""

from app.ai.classifier import classify


RECOMMENDATIONS_BY_CATEGORY = {
    "conceptual_question": "Review in office hours; schedule a group session if repeated",
    "exam_logistics": "Post or update a final-exam FAQ response",
    "retake_request": "Route to makeup exam / admin process",
    "accessibility_accommodation": "Route to accommodation confirmation workflow",
    "grading_dispute": "Route to grading review workflow",
    "emotional_stress": "Offer priority one-to-one meeting and support resources",
    "project_submission": "Create TA-led project support block",
    "office_hours_access": "Open or extend office-hours availability",
    "academic_integrity": "Route to professor for private academic-integrity follow-up",
    "uncategorized": "Review manually",
}


def classify_and_recommend(text: str) -> dict[str, object]:
    classification = classify(text)
    category = str(classification["category"])

    return {
        **classification,
        "recommended_action": _recommend_action(
            category=category,
            urgency=str(classification["urgency"]),
        ),
    }


def _recommend_action(category: str, urgency: str) -> str:
    if urgency == "urgent":
        return "Offer priority one-to-one meeting and support resources"

    return RECOMMENDATIONS_BY_CATEGORY.get(category, "Review manually")
