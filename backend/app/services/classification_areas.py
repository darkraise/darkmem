"""
classification_areas.py — Domain-specific classification areas.

Each area defines LLM type descriptions. Areas are toggled via the
`classification_areas` feature flag. The `general` area is always active.
`fact` is the global fallback when no type fits.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ClassificationArea:
    key: str
    display_name: str
    llm_types: dict[str, str]


# ── General (always on) ─────────────────────────────────────────────────

AREAS: dict[str, ClassificationArea] = {
    "general": ClassificationArea(
        key="general",
        display_name="General",
        llm_types={
            "decision": "explicit choices made, architecture rationale, trade-offs with reasoning",
            "preference": "habits, rules, style preferences, always/never statements",
            "milestone": "breakthroughs, things that finally worked, achievements, releases",
            "problem": "bugs found, errors encountered, root causes identified, workarounds applied",
            "emotional": "feelings, vulnerability, relationships, personal reflections",
        },
    ),

    # ── Technical ────────────────────────────────────────────────────────

    "technical": ClassificationArea(
        key="technical",
        display_name="Technical",
        llm_types={
            "reference": "documentation pointers, specs, standards, protocol descriptions",
            "architecture": "system design, component responsibilities, data flow, structural patterns",
        },
    ),

    # ── Debugging ────────────────────────────────────────────────────────

    "debugging": ClassificationArea(
        key="debugging",
        display_name="Debugging",
        llm_types={
            "root_cause": "identified root causes of bugs, errors, or failures with explanation",
            "workaround": "temporary workarounds, hacks, or interim fixes for known issues",
            "gotcha": "non-obvious pitfalls, counter-intuitive behavior, things to watch out for",
        },
    ),

    # ── Infrastructure ───────────────────────────────────────────────────

    "infrastructure": ClassificationArea(
        key="infrastructure",
        display_name="Infrastructure",
        llm_types={
            "deployment": "deployment procedures, CI/CD configurations, container orchestration",
            "configuration": "configuration settings, environment variables, parameter tuning",
            "networking": "network topology, proxy rules, DNS, ports, firewall, SSL/TLS",
        },
    ),

    # ── Project Management ───────────────────────────────────────────────

    "project": ClassificationArea(
        key="project",
        display_name="Project Management",
        llm_types={
            "planning": "sprint planning, roadmap items, scope definitions, timelines",
            "status_update": "progress reports, blockers, task completion updates",
            "retrospective": "retrospective insights, process improvements, lessons learned",
        },
    ),

    # ── Security ─────────────────────────────────────────────────────────

    "security": ClassificationArea(
        key="security",
        display_name="Security",
        llm_types={
            "vulnerability": "security vulnerabilities, exploits, attack vectors found",
            "compliance": "regulatory compliance, audit findings, data protection requirements",
            "incident": "security incidents, breaches, outages, post-mortem analysis",
        },
    ),

    # ── Research ─────────────────────────────────────────────────────────

    "research": ClassificationArea(
        key="research",
        display_name="Research",
        llm_types={
            "hypothesis": "theories, predictions, suspected causes awaiting validation",
            "finding": "research results, benchmark data, measured performance outcomes",
            "comparison": "technology comparisons, alternative evaluations, pros/cons analysis",
        },
    ),

    # ── Learning ─────────────────────────────────────────────────────────

    "learning": ClassificationArea(
        key="learning",
        display_name="Learning",
        llm_types={
            "tutorial": "how-to guides, step-by-step instructions, walkthroughs",
            "concept": "concept explanations, definitions, educational descriptions",
            "lesson_learned": "lessons learned from experience, takeaways, insights gained",
        },
    ),

    # ── Collaboration ────────────────────────────────────────────────────

    "collaboration": ClassificationArea(
        key="collaboration",
        display_name="Collaboration",
        llm_types={
            "feedback": "code review feedback, suggestions, critique from team members",
            "agreement": "team consensus, approvals, alignment on decisions",
            "disagreement": "pushback, objections, debates, unresolved concerns",
        },
    ),

    # ── Product ──────────────────────────────────────────────────────────

    "product": ClassificationArea(
        key="product",
        display_name="Product",
        llm_types={
            "requirement": "functional requirements, acceptance criteria, must-have capabilities",
            "user_story": "user stories, personas, use cases, user journeys",
            "feature_spec": "feature specifications, behavioral descriptions, scope definitions",
        },
    ),

    # ── Personal ─────────────────────────────────────────────────────────

    "personal": ClassificationArea(
        key="personal",
        display_name="Personal",
        llm_types={
            "journal": "daily journal entries, observations, stream-of-consciousness notes",
            "reflection": "retrospective reflections, personal growth observations, perspective shifts",
            "goal": "personal or professional goals, objectives, aspirations with timelines",
        },
    ),
}


SIMPLE_TYPES: dict[str, str] = {
    "fact": "neutral factual information, how things work, definitions, specifications",
    "decision": "explicit choices made, architecture rationale, trade-offs with reasoning",
    "preference": "habits, rules, style preferences, always/never statements",
    "problem": "bugs, errors, root causes, workarounds, gotchas, debugging insights",
    "reference": "documentation pointers, specs, standards, protocol descriptions",
    "architecture": "system design, component responsibilities, patterns, data flow",
    "milestone": "breakthroughs, achievements, releases, things that finally worked",
}

SIMPLE_NORMALIZATION: dict[str, str] = {
    "solution": "problem",
    "fix": "problem",
    "workaround": "problem",
    "root_cause": "problem",
    "gotcha": "problem",
    "debug": "problem",
    "incident": "problem",
    "vulnerability": "problem",
    "recommendation": "decision",
    "comparison": "decision",
    "agreement": "decision",
    "disagreement": "decision",
    "feedback": "decision",
    "finding": "fact",
    "configuration": "fact",
    "networking": "fact",
    "compliance": "fact",
    "status_update": "fact",
    "hypothesis": "fact",
    "tutorial": "reference",
    "concept": "reference",
    "requirement": "reference",
    "feature_spec": "reference",
    "user_story": "reference",
    "deployment": "architecture",
    "planning": "architecture",
    "lesson_learned": "milestone",
    "retrospective": "milestone",
    "journal": "milestone",
    "reflection": "milestone",
    "goal": "milestone",
    "emotional": "preference",
}


def get_merged_llm_types(enabled_areas: list[str] | None = None, mode: str = "simple") -> dict[str, str]:
    """Merge LLM type descriptions from all enabled areas. Always includes 'fact'."""
    if mode == "simple":
        return dict(SIMPLE_TYPES)

    if enabled_areas is None:
        enabled_areas = ["general"]

    merged: dict[str, str] = {
        "fact": "neutral factual information, how things work, definitions, specifications, descriptions without opinion or action",
    }
    for area_key in enabled_areas:
        area = AREAS.get(area_key)
        if not area:
            continue
        merged.update(area.llm_types)
    return merged
