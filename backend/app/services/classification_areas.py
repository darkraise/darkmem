"""
classification_areas.py — Domain-specific classification areas.

Each area defines regex marker patterns and LLM type descriptions.
Areas are toggled via the `classification_areas` feature flag.
The `general` area is always active. `fact` is the global fallback
when no markers match.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ClassificationArea:
    key: str
    display_name: str
    types: dict[str, list[str]]
    llm_types: dict[str, str]


# ── General (always on) ─────────────────────────────────────────────────

AREAS: dict[str, ClassificationArea] = {
    "general": ClassificationArea(
        key="general",
        display_name="General",
        types={
            "decision": [
                r"\blet'?s (use|go with|try|pick|choose|switch to)\b",
                r"\bwe (should|decided|chose|went with|picked|settled on)\b",
                r"\bi'?m going (to|with)\b",
                r"\bbetter (to|than|approach|option|choice)\b",
                r"\binstead of\b",
                r"\brather than\b",
                r"\bthe reason (is|was|being)\b",
                r"\btrade-?off\b",
                r"\bpros and cons\b",
                r"\bover\b.*\bbecause\b",
            ],
            "preference": [
                r"\bi prefer\b",
                r"\balways use\b",
                r"\bnever use\b",
                r"\bdon'?t (ever |like to )?(use|do|mock|stub|import)\b",
                r"\bi like (to|when|how)\b",
                r"\bi hate (when|how|it when)\b",
                r"\bplease (always|never|don'?t)\b",
                r"\bmy (rule|preference|style|convention) is\b",
                r"\bwe (always|never)\b",
                r"\bfunctional\b.*\bstyle\b",
                r"\bimperative\b",
                r"\bsnake_?case\b",
                r"\bcamel_?case\b",
                r"\btabs\b.*\bspaces\b",
                r"\bspaces\b.*\btabs\b",
                r"\buse\b.*\binstead of\b",
            ],
            "milestone": [
                r"\bit works\b",
                r"\bit worked\b",
                r"\bgot it working\b",
                r"\bfixed\b",
                r"\bsolved\b",
                r"\bbreakthrough\b",
                r"\bfigured (it )?out\b",
                r"\bnailed it\b",
                r"\bcracked (it|the)\b",
                r"\bfinally\b",
                r"\bfirst time\b",
                r"\bfirst ever\b",
                r"\bnever (done|been|had) before\b",
                r"\bdiscovered\b",
                r"\brealized\b",
                r"\bfound (out|that)\b",
                r"\bturns out\b",
                r"\bthe key (is|was|insight)\b",
                r"\bthe trick (is|was)\b",
                r"\bnow i (understand|see|get it)\b",
                r"\bbuilt\b",
                r"\bcreated\b",
                r"\bimplemented\b",
                r"\bshipped\b",
                r"\blaunched\b",
                r"\bdeployed\b",
                r"\breleased\b",
                r"\bprototype\b",
                r"\bproof of concept\b",
                r"\bdemo\b",
                r"\bversion \d",
                r"\bv\d+\.\d+",
                r"\d+x (compression|faster|slower|better|improvement|reduction)",
                r"\d+% (reduction|improvement|faster|better|smaller)",
            ],
            "problem": [
                r"\b(bug|crash|fail|broke|broken|issue|problem)\b",
                r"\bdoesn'?t work\b",
                r"\bnot working\b",
                r"\bwon'?t\b.*\bwork\b",
                r"\bkeeps? (failing|crashing|breaking|erroring)\b",
                r"\broot cause\b",
                r"\bthe (problem|issue|bug) (is|was)\b",
                r"\bturns out\b.*\b(was|because|due to)\b",
                r"\bthe fix (is|was)\b",
                r"\bworkaround\b",
                r"\bthat'?s why\b",
                r"\bthe reason it\b",
                r"\bfixed (it |the |by )\b",
                r"\bsolution (is|was)\b",
                r"\bresolved\b",
                r"\bpatched\b",
                r"\bthe answer (is|was)\b",
                r"\b(had|need) to\b.*\binstead\b",
            ],
            "emotional": [
                r"\blove\b",
                r"\bscared\b",
                r"\bafraid\b",
                r"\bproud\b",
                r"\bhurt\b",
                r"\bhappy\b",
                r"\bsad\b",
                r"\bcry\b",
                r"\bcrying\b",
                r"\bmiss\b",
                r"\bsorry\b",
                r"\bgrateful\b",
                r"\bangry\b",
                r"\bworried\b",
                r"\blonely\b",
                r"\bbeautiful\b",
                r"\bamazing\b",
                r"\bwonderful\b",
                r"i feel",
                r"i'm scared",
                r"i love you",
                r"i'm sorry",
                r"i can't",
                r"i wish",
                r"i miss",
                r"i need",
                r"never told anyone",
                r"nobody knows",
                r"\*[^*]+\*",
            ],
        },
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
        types={
            "reference": [
                r"\b(documentation|spec|rfc|standard|protocol|format)\b",
                r"\baccording to\b",
                r"\bdefined (by|in|as)\b",
                r"\b(api|sdk|library) (reference|docs?)\b",
            ],
            "architecture": [
                r"\barchitecture\b",
                r"\b(layer|module|component|service|pipeline)\b.*\b(handles|responsible|manages)\b",
                r"\bpattern\b",
                r"\bstack\b",
                r"\bframework\b",
                r"\bdesign(ed)? (to|for|so that)\b",
            ],
        },
        llm_types={
            "reference": "documentation pointers, specs, standards, protocol descriptions",
            "architecture": "system design, component responsibilities, data flow, structural patterns",
        },
    ),

    # ── Debugging ────────────────────────────────────────────────────────

    "debugging": ClassificationArea(
        key="debugging",
        display_name="Debugging",
        types={
            "root_cause": [
                r"\broot cause\b",
                r"\bthe (actual|real|underlying) (problem|issue|cause)\b",
                r"\bcaused by\b",
                r"\bdue to\b",
                r"\bbecause of\b.*\b(bug|error|failure|crash)\b",
                r"\bturns out\b.*\b(was|because|due to)\b",
            ],
            "workaround": [
                r"\bworkaround\b",
                r"\bhack\b",
                r"\btemporary fix\b",
                r"\buntil\b.*\b(fix|resolve|patch)\b",
                r"\bfor now\b.*\b(use|do|set)\b",
            ],
            "gotcha": [
                r"\bgotcha\b",
                r"\bwatch out\b",
                r"\bbe careful\b",
                r"\bnon-?obvious\b",
                r"\bsurprisingly\b",
                r"\bcounter-?intuitive\b",
                r"\bdon'?t forget\b",
                r"\bimportant(ly)?\b.*\bnot\b",
            ],
        },
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
        types={
            "deployment": [
                r"\bdeployed?\b",
                r"\brollout\b",
                r"\brelease\b",
                r"\bci/?cd\b",
                r"\bdocker\b",
                r"\bkubernetes\b",
                r"\bhelm\b",
                r"\binfrastructure\b",
                r"\bprovisioned?\b",
            ],
            "configuration": [
                r"\bset (it |this )?to\b",
                r"\bconfigure[ds]?\b",
                r"\bdefault\b",
                r"\benv(ironment)? var(iable)?\b",
                r"\b(config|settings?) (file|value|option)\b",
            ],
            "networking": [
                r"\b(port|ip|dns|proxy|firewall|vpn|ssl|tls)\b",
                r"\b(reverse proxy|load balancer|cdn|gateway)\b",
                r"\brouting\b",
                r"\bcors\b",
                r"\bwebsocket\b",
            ],
        },
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
        types={
            "planning": [
                r"\b(sprint|iteration|phase|milestone|roadmap)\b",
                r"\bplan(ned|ning)?\b",
                r"\bscope\b",
                r"\btimeline\b",
                r"\bdeadline\b",
                r"\bestimate\b",
            ],
            "status_update": [
                r"\bstatus\b",
                r"\bprogress\b",
                r"\bblocker\b",
                r"\bon track\b",
                r"\bdelayed\b",
                r"\bcompleted?\b.*\b(task|item|story)\b",
            ],
            "retrospective": [
                r"\bretro(spective)?\b",
                r"\bwhat went (well|wrong)\b",
                r"\blesson(s)? learned\b",
                r"\bnext time\b.*\b(should|will|could)\b",
                r"\bimprove(ment)?\b.*\b(process|workflow)\b",
            ],
        },
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
        types={
            "vulnerability": [
                r"\b(vulnerability|vuln|cve|exploit|attack)\b",
                r"\b(sql injection|xss|csrf|ssrf|rce)\b",
                r"\bpenetration test\b",
                r"\b(privilege escalation|auth(entication)? bypass)\b",
            ],
            "compliance": [
                r"\b(compliance|compliant|regulation|audit)\b",
                r"\b(gdpr|hipaa|soc ?2|pci|iso ?27001)\b",
                r"\bdata (protection|retention|classification)\b",
            ],
            "incident": [
                r"\b(incident|breach|outage|compromise)\b",
                r"\b(unauthorized access|data leak|exfiltration)\b",
                r"\bpost-?mortem\b",
                r"\bimpact (analysis|assessment)\b",
            ],
        },
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
        types={
            "hypothesis": [
                r"\bhypothesis\b",
                r"\bi (think|suspect|believe)\b.*\bbecause\b",
                r"\bmy theory\b",
                r"\bprediction\b",
                r"\bif\b.*\bthen\b.*\bshould\b",
            ],
            "finding": [
                r"\bfinding\b",
                r"\bresult(s)?\b",
                r"\bdata shows\b",
                r"\bmeasured?\b",
                r"\bbenchmark\b",
                r"\bmetric\b",
                r"\bperformance\b.*\b(test|result|number)\b",
            ],
            "comparison": [
                r"\bvs\.?\b",
                r"\bcompare[ds]?\b",
                r"\bcomparison\b",
                r"\bbetter than\b",
                r"\bworse than\b",
                r"\b(pro|con)s?\b.*\bof\b",
                r"\b(advantage|disadvantage)\b",
                r"\balternative\b",
            ],
        },
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
        types={
            "tutorial": [
                r"\bhow to\b",
                r"\bstep \d\b",
                r"\btutorial\b",
                r"\bguide\b",
                r"\bexample\b",
                r"\bwalkthrough\b",
                r"\bfollow(ing)? these steps\b",
            ],
            "concept": [
                r"\bconcept\b",
                r"\bexplain(s|ed|ing)?\b",
                r"\bmeans? (that|the)\b",
                r"\bdefinition\b",
                r"\bin (simple|other) terms\b",
                r"\bfundamental\b",
            ],
            "lesson_learned": [
                r"\blearned (that|about|from)\b",
                r"\btakeaway\b",
                r"\bnever again\b",
                r"\bwon'?t make (that|this) mistake\b",
                r"\bnow i know\b",
                r"\bkey (learning|insight|takeaway)\b",
            ],
        },
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
        types={
            "feedback": [
                r"\bfeedback\b",
                r"\bcode review\b",
                r"\bcomment(s|ed)? on\b",
                r"\bsuggestion\b",
                r"\bcritique\b",
            ],
            "agreement": [
                r"\bagreed?\b",
                r"\bconsensus\b",
                r"\baligned?\b",
                r"\bsame page\b",
                r"\bapproved?\b",
                r"\bsigned? off\b",
            ],
            "disagreement": [
                r"\bdisagree[ds]?\b",
                r"\bpushed? back\b",
                r"\bobjection\b",
                r"\bconcern(s|ed)?\b",
                r"\bcontention\b",
                r"\bdebate[ds]?\b",
            ],
        },
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
        types={
            "requirement": [
                r"\brequirement\b",
                r"\bmust (have|support|handle)\b",
                r"\bshall\b",
                r"\bneeds? to\b.*\b(support|handle|provide)\b",
                r"\bacceptance criteria\b",
            ],
            "user_story": [
                r"\bas a\b.*\bi want\b",
                r"\buser story\b",
                r"\bpersona\b",
                r"\buse case\b",
                r"\buser (flow|journey)\b",
            ],
            "feature_spec": [
                r"\bfeature\b.*\b(spec|specification|request)\b",
                r"\bfunctional(ity)?\b",
                r"\bbehavior\b.*\bwhen\b",
                r"\binput\b.*\boutput\b",
                r"\bscope\b.*\b(include|exclude)\b",
            ],
        },
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
        types={
            "journal": [
                r"\btoday i\b",
                r"\bthis (morning|evening|week)\b",
                r"\bdear diary\b",
                r"\bi (thought|felt|noticed|wondered)\b",
                r"\breflecting on\b",
            ],
            "reflection": [
                r"\blooking back\b",
                r"\bin retrospect\b",
                r"\bi'?ve (been|come to|realized)\b",
                r"\bover (time|the years)\b",
                r"\bgrowth\b",
                r"\bperspective\b",
            ],
            "goal": [
                r"\bgoal\b",
                r"\bobjective\b",
                r"\bi want to\b",
                r"\bi plan to\b",
                r"\bby (end of|next|this)\b.*\b(year|month|quarter|week)\b",
                r"\btarget\b",
                r"\baspire\b",
            ],
        },
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


def get_merged_markers(enabled_areas: list[str] | None = None, mode: str = "expanded") -> dict[str, list[str]]:
    """Merge regex markers from all enabled areas into a single type->markers dict."""
    if enabled_areas is None:
        enabled_areas = ["general"]

    merged: dict[str, list[str]] = {}
    for area_key in enabled_areas:
        area = AREAS.get(area_key)
        if not area:
            continue
        for type_name, markers in area.types.items():
            if type_name in merged:
                merged[type_name].extend(markers)
            else:
                merged[type_name] = list(markers)

    if mode == "simple":
        remapped: dict[str, list[str]] = {}
        for type_name, markers in merged.items():
            target = type_name if type_name in SIMPLE_TYPES else SIMPLE_NORMALIZATION.get(type_name)
            if target and target in SIMPLE_TYPES:
                if target in remapped:
                    remapped[target].extend(markers)
                else:
                    remapped[target] = list(markers)
        return remapped

    return merged


def get_merged_llm_types(enabled_areas: list[str] | None = None, mode: str = "expanded") -> dict[str, str]:
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
