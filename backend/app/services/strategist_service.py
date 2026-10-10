"""Revision Strategist — LLM (or local planner) + web tools on a learner dossier.

Campus Study Agent still quotes stamps only. This agent recommends YouTube /
articles from how the student asks and learns. It never invents URLs.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.ai.clustering import cosine_similarity, embed_text
from app.models.strategist import (
    FocusTopicOut,
    GradeRowIn,
    ResourceHitOut,
    StrategistPlanOut,
    TodayBlockOut,
    ToolCallOut,
)
from app.services.strategist_llm import (
    llm_available,
    llm_model_name,
    plan_tool_queries_with_llm,
)
from app.services.strategist_profile import STYLE_LABELS, build_learner_dossier
from app.services.strategist_tools import article_search, youtube_search

STYLE_QUERY_HINTS = {
    "visual_structural": ("diagram", "visualization animation"),
    "step_by_step": ("step by step tutorial", "walkthrough"),
    "example_driven": ("worked example", "practice problems"),
    "conceptual": ("intuition explained", "why it works"),
    "unknown": ("explained", "introduction"),
}

STYLE_TODAY = {
    "visual_structural": (
        ("Start here · see it", 45, "Watch a diagram or animation of {topic}."),
        ("Sketch it", 60, "Draw {topic} from memory, then compare to the resource."),
        ("Check", 30, "Self-quiz: can you redraw {topic} without notes? Target 75%+."),
    ),
    "step_by_step": (
        ("Start here · walkthrough", 45, "Follow one ordered walkthrough of {topic}."),
        ("Trace it", 60, "Trace one full {topic} example on paper, line by line."),
        ("Check", 30, "Self-quiz the procedure for {topic}. Target 75%+."),
    ),
    "example_driven": (
        ("Start here · worked example", 45, "Study one worked {topic} example end to end."),
        ("Practice", 60, "Do two fresh {topic} problems without looking at the key."),
        ("Check", 30, "Self-quiz those problems. Target 75%+."),
    ),
    "conceptual": (
        ("Start here · why it works", 45, "Read or watch an intuition pass on {topic}."),
        ("Explain it", 60, "Write why {topic} works in your own words."),
        ("Check", 30, "Self-quiz the idea, not the steps. Target 75%+."),
    ),
    "unknown": (
        ("Start here · foundations", 45, "Core notes for {topic}."),
        ("Practice", 60, "Worked problems on {topic} until one clean pass."),
        ("Check", 30, "Self-quiz · target 75%+."),
    ),
}


def build_plan(
    db: Session,
    *,
    user_id: int,
    course_id: int,
    course_code: str | None = None,
    grades: list[GradeRowIn] | None = None,
    goal: str | None = None,
) -> StrategistPlanOut:
    dossier = build_learner_dossier(db, user_id=user_id, course_id=course_id)
    focus = _focus_topic(grades or [], course_code)
    natural_goal = (goal or "").strip() or _default_goal(dossier, focus)

    notes: list[str] = []
    tool_calls: list[dict[str, Any]] = []
    hits: list[dict[str, Any]] = []
    planner = "local-planner"
    model = "all-MiniLM-L6-v2 + web tools"

    def execute(tool: str, query: str) -> list[dict[str, Any]]:
        if tool == "youtube_search":
            return youtube_search(query)
        if tool == "article_search":
            return article_search(query)
        return []

    if llm_available():
        try:
            hits, tool_calls, model = plan_tool_queries_with_llm(
                goal=natural_goal,
                dossier=dossier.model_dump(),
                focus_topic=focus.topic,
                execute=execute,
            )
            planner = "llm"
        except Exception as exc:  # pragma: no cover - network/key failures
            notes.append(f"Hosted LLM planner failed ({exc.__class__.__name__}); local planner used.")
            hits, tool_calls = _local_tool_loop(
                dossier.dominant_style,
                focus.topic,
                natural_goal,
                execute,
                struggles=dossier.struggles,
            )
            planner = "local-planner"
            model = "all-MiniLM-L6-v2 + web tools"
    else:
        hits, tool_calls = _local_tool_loop(
            dossier.dominant_style,
            focus.topic,
            natural_goal,
            execute,
            struggles=dossier.struggles,
        )
        if not llm_available():
            notes.append(
                "Hosted LLM off — local planner still called YouTube/article tools "
                "from the learner dossier. Set OFFICEHOURS_ALLOW_EXTERNAL_LLM=true "
                "plus OPENAI_API_KEY or ANTHROPIC_API_KEY for the LLM loop."
            )

    ranked = _rank_hits(hits, dossier.dominant_style, focus.topic, natural_goal)
    if not ranked:
        notes.append(
            "Web tools returned no structured hits. Add YOUTUBE_API_KEY "
            "(or OFFICEHOURS_INVIDIOUS_URL) for videos; Wikipedia articles "
            "need outbound HTTPS."
        )

    resources = [
        ResourceHitOut(
            kind=str(hit.get("kind") or "article"),
            title=str(hit.get("title") or "Resource"),
            url=str(hit.get("url")),
            snippet=(str(hit.get("snippet") or "") or None),
            query=(str(hit.get("query") or "") or None),
            why=str(hit.get("why") or _why(hit, dossier.dominant_style, focus.topic)),
        )
        for hit in ranked
        if hit.get("url")
    ][:6]
    today, today_summary = _today_plan(dossier.dominant_style, focus, resources)

    return StrategistPlanOut(
        focus=focus,
        dossier=dossier,
        goal=natural_goal,
        planner=planner,
        model=model if planner == "llm" else model,
        resources=resources,
        tool_calls=[ToolCallOut(**call) for call in tool_calls],
        today=today,
        today_summary=today_summary,
        week=_week_plan(focus.topic),
        notes=notes,
        trace={
            "llm_available": llm_available(),
            "llm_model": llm_model_name(),
            "style": dossier.dominant_style,
            "course_code": course_code,
        },
    )


def _focus_topic(grades: list[GradeRowIn], course_code: str | None) -> FocusTopicOut:
    if grades:
        ranked = sorted(
            grades,
            key=lambda row: row.weight * max(0.0, 85.0 - row.score),
            reverse=True,
        )
        top = ranked[0]
        return FocusTopicOut(
            topic=top.topic,
            score=top.score,
            weight=top.weight,
            source=top.source,
            gap=round(top.weight * max(0.0, 85.0 - top.score), 2),
        )
    code = (course_code or "").upper()
    topic = "Trees & red-black" if code.startswith("CSC") or "ALGOR" in code else "Core concepts"
    return FocusTopicOut(topic=topic, score=None, weight=None, source="No grades yet")


def _default_goal(dossier, focus: FocusTopicOut) -> str:
    style = STYLE_LABELS.get(dossier.dominant_style, dossier.dominant_style)
    struggles = ", ".join(dossier.struggles[:4]) or "the topics in their recent asks"
    score = f" Current score {focus.score:.0f}%." if focus.score is not None else ""
    return (
        f"Find the best YouTube videos and articles for {focus.topic} for a student "
        f"who learns as {style}. They have asked about {struggles}. "
        f"{dossier.how_they_ask}{score}"
    )


def _clean_topic(topic: str) -> str:
    return " ".join((topic or "").replace("&", " ").replace("/", " ").split())


def _search_seeds(topic: str, struggles: list[str] | None) -> list[str]:
    clean = _clean_topic(topic)
    seeds: list[str] = []
    lowered = clean.lower()
    if "red-black" in lowered or "red black" in lowered:
        seeds.append("red-black tree")
    if "hash" in lowered:
        seeds.append("hash table")
    if "heap" in lowered:
        seeds.append("binary heap")
    if clean:
        seeds.append(clean)
    for item in struggles or []:
        token = _clean_topic(item)
        if len(token) >= 4:
            seeds.append(token)
    out: list[str] = []
    seen: set[str] = set()
    for seed in seeds:
        key = seed.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(seed)
    return out[:3]


def _local_tool_loop(
    style: str,
    topic: str,
    goal: str,
    execute,
    *,
    struggles: list[str] | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    hints = STYLE_QUERY_HINTS.get(style, STYLE_QUERY_HINTS["unknown"])
    seeds = _search_seeds(topic, struggles)
    queries = [f"{seeds[0]} {hints[0]}", seeds[0]] if seeds else [topic]
    if len(seeds) > 1:
        queries.append(seeds[1])
    hits: list[dict[str, Any]] = []
    calls: list[dict[str, Any]] = []
    seen_q: set[str] = set()
    for query in queries:
        q = query.strip()
        if not q or q.lower() in seen_q:
            continue
        seen_q.add(q.lower())
        for tool in ("youtube_search", "article_search"):
            found = execute(tool, q)
            hits.extend(found)
            calls.append({"tool": tool, "query": q, "hit_count": len(found)})
    return hits, calls


def _hit_matches_topic(hit: dict[str, Any], topic: str) -> bool:
    blob = f"{hit.get('title') or ''} {hit.get('snippet') or ''}".lower().replace("–", "-")
    clean = _clean_topic(topic).lower()
    if "red-black" in clean or "red black" in clean:
        return ("red-black" in blob or "red black" in blob) and "tree" in blob
    tokens = [part for part in clean.split() if len(part) > 3]
    return any(part in blob for part in tokens) if tokens else True


def _rank_hits(
    hits: list[dict[str, Any]],
    style: str,
    topic: str,
    goal: str,
) -> list[dict[str, Any]]:
    unique: list[dict[str, Any]] = []
    seen: set[str] = set()
    for hit in hits:
        url = str(hit.get("url") or "")
        if not url.startswith("http") or url in seen:
            continue
        if not _hit_matches_topic(hit, topic):
            continue
        seen.add(url)
        unique.append(hit)
    if not unique:
        return []
    query = f"{topic} {style} {goal}"
    q_vec = embed_text(query)
    scored: list[tuple[float, dict[str, Any]]] = []
    for hit in unique:
        blob = f"{hit.get('title') or ''} {hit.get('snippet') or ''}"
        scored.append((cosine_similarity(q_vec, embed_text(blob)), hit))
    scored.sort(key=lambda pair: pair[0], reverse=True)
    return [hit for _, hit in scored]


def _why(hit: dict[str, Any], style: str, topic: str) -> str:
    kind = "video" if hit.get("kind") == "youtube" else "article"
    return (
        f"{kind.title()} for {topic}, ranked for a {style.replace('_', ' ')} learner "
        f"from tool query “{hit.get('query') or topic}”."
    )


def _today_plan(
    style: str,
    focus: FocusTopicOut,
    resources: list[ResourceHitOut],
) -> tuple[list[TodayBlockOut], str]:
    short = _clean_topic(focus.topic) or "this topic"
    templates = STYLE_TODAY.get(style, STYLE_TODAY["unknown"])
    youtube = next((item for item in resources if item.kind == "youtube" and item.url), None)
    article = next((item for item in resources if item.kind == "article" and item.url), None)
    blocks: list[TodayBlockOut] = []
    for index, (title, minutes, action) in enumerate(templates):
        hit = youtube if index == 0 else article if index == 1 else None
        blocks.append(
            TodayBlockOut(
                title=title,
                minutes=minutes,
                action=(
                    f"{'Watch' if hit and hit.kind == 'youtube' else 'Read'}: {hit.title}"
                    if hit
                    else action.format(topic=short)
                ),
                resource_url=hit.url if hit else None,
                resource_title=hit.title if hit else None,
            )
        )
    total = sum(block.minutes for block in blocks)
    summary = f"{total} min · close the gap on {short}"
    return blocks, summary


def _week_plan(focus_topic: str) -> list[list[str]]:
    short = (focus_topic or "Focus").split("&")[0].strip()
    return [
        ["Mon", f"{short} · foundations", "2.5h"],
        ["Tue", f"{short} · practice", "2h"],
        ["Wed", f"{short} · check-in", "2.5h"],
        ["Thu", "Second priority", "2h"],
        ["Fri", "Keep / project", "1.5h"],
        ["Sat", "Light review", "1h"],
        ["Sun", "Rest", "—"],
    ]
