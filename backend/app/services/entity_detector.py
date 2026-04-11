"""
entity_detector.py — Auto-detect people and projects from text content.

Ported from MemPalace's entity_detector.py. Pure logic module — no darkmem
imports, no async, no database access.

Two-pass approach:
  Pass 1 — extract_candidates: scan text, collect capitalized words (3+ occurrences).
  Pass 2 — score_entity + classify_entity: weighted signal scoring.

Classification threshold: person_ratio >= 0.7 with 2+ distinct signal
categories AND person score >= 5.
"""

import re
from collections import defaultdict


# =============================================================================
# SIGNAL PATTERNS
# =============================================================================

_PERSON_VERB_PATTERNS: list[str] = [
    r"\b{name}\s+said\b",
    r"\b{name}\s+asked\b",
    r"\b{name}\s+told\b",
    r"\b{name}\s+replied\b",
    r"\b{name}\s+laughed\b",
    r"\b{name}\s+smiled\b",
    r"\b{name}\s+cried\b",
    r"\b{name}\s+felt\b",
    r"\b{name}\s+thinks?\b",
    r"\b{name}\s+wants?\b",
    r"\b{name}\s+loves?\b",
    r"\b{name}\s+hates?\b",
    r"\b{name}\s+knows?\b",
    r"\b{name}\s+decided\b",
    r"\b{name}\s+pushed\b",
    r"\b{name}\s+wrote\b",
    r"\bhey\s+{name}\b",
    r"\bthanks?\s+{name}\b",
    r"\bhi\s+{name}\b",
    r"\bdear\s+{name}\b",
]

_PRONOUN_PATTERNS: list[str] = [
    r"\bshe\b",
    r"\bher\b",
    r"\bhers\b",
    r"\bhe\b",
    r"\bhim\b",
    r"\bhis\b",
    r"\bthey\b",
    r"\bthem\b",
    r"\btheir\b",
]

_DIALOGUE_PATTERNS: list[str] = [
    r"^>\s*{name}[:\s]",
    r"^{name}:\s",
    r"^\[{name}\]",
    r'"{name}\s+said',
]

_PROJECT_VERB_PATTERNS: list[str] = [
    r"\bbuilding\s+{name}\b",
    r"\bbuilt\s+{name}\b",
    r"\bship(?:ping|ped)?\s+{name}\b",
    r"\blaunch(?:ing|ed)?\s+{name}\b",
    r"\bdeploy(?:ing|ed)?\s+{name}\b",
    r"\binstall(?:ing|ed)?\s+{name}\b",
    r"\bthe\s+{name}\s+architecture\b",
    r"\bthe\s+{name}\s+pipeline\b",
    r"\bthe\s+{name}\s+system\b",
    r"\bthe\s+{name}\s+repo\b",
    r"\b{name}\s+v\d+\b",
    r"\b{name}\.py\b",
    r"\b{name}-core\b",
    r"\b{name}-local\b",
    r"\bimport\s+{name}\b",
    r"\bpip\s+install\s+{name}\b",
]

_STOPWORDS: set[str] = {
    "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for",
    "of", "with", "by", "from", "as", "is", "was", "are", "were", "be",
    "been", "being", "have", "has", "had", "do", "does", "did", "will",
    "would", "could", "should", "may", "might", "must", "shall", "can",
    "this", "that", "these", "those", "it", "its", "they", "them", "their",
    "we", "our", "you", "your", "i", "my", "me", "he", "she", "his", "her",
    "who", "what", "when", "where", "why", "how", "which", "if", "then",
    "so", "not", "no", "yes", "ok", "okay", "just", "very", "really",
    "also", "already", "still", "even", "only", "here", "there", "now",
    "then", "too", "up", "out", "about", "like", "use", "get", "got",
    "make", "made", "take", "put", "come", "go", "see", "know", "think",
    "true", "false", "none", "null", "new", "old", "all", "any", "some",
    "return", "print", "def", "class", "import", "from",
    "step", "usage", "run", "check", "find", "add", "get", "set", "list",
    "args", "dict", "str", "int", "bool", "path", "file", "type", "name",
    "note", "example", "option", "result", "error", "warning", "info",
    "every", "each", "more", "less", "next", "last", "first", "second",
    "stack", "layer", "mode", "test", "stop", "start", "copy", "move",
    "source", "target", "output", "input", "data", "item", "key", "value",
    "returns", "raises", "yields", "self", "cls", "kwargs",
    "world", "well", "want", "topic", "choose", "social", "cars", "phones",
    "healthcare", "ex", "machina", "deus", "human", "humans", "people",
    "things", "something", "nothing", "everything", "anything", "someone",
    "everyone", "anyone", "way", "time", "day", "life", "place", "thing",
    "part", "kind", "sort", "case", "point", "idea", "fact", "sense",
    "question", "answer", "reason", "number", "version", "system",
    "hey", "hi", "hello", "thanks", "thank", "right", "let", "ok",
    "click", "hit", "press", "tap", "drag", "drop", "open", "close",
    "save", "load", "launch", "install", "download", "upload", "scroll",
    "select", "enter", "submit", "cancel", "confirm", "delete", "copy",
    "paste", "write", "read", "search", "find", "show", "hide",
    "desktop", "documents", "downloads", "users", "home", "library",
    "applications", "preferences", "settings", "terminal",
    "actor", "vector", "remote", "control", "duration", "fetch",
    "agents", "tools", "others", "guards", "ethics", "regulation",
    "learning", "thinking", "memory", "language", "intelligence",
    "technology", "society", "culture", "future", "history", "science",
    "model", "models", "network", "networks", "training", "inference",
}


# =============================================================================
# CANDIDATE EXTRACTION
# =============================================================================


def extract_candidates(text: str) -> list[str]:
    """Extract capitalized proper-noun candidates appearing 3 or more times.

    Also detects multi-word proper nouns (e.g. "Memory Palace").

    Args:
        text: Source text to scan.

    Returns:
        List of candidate name strings.
    """
    raw = re.findall(r"\b([A-Z][a-z]{1,19})\b", text)
    counts: dict[str, int] = defaultdict(int)
    for word in raw:
        if word.lower() not in _STOPWORDS and len(word) > 1:
            counts[word] += 1

    multi = re.findall(r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\b", text)
    for phrase in multi:
        if not any(w.lower() in _STOPWORDS for w in phrase.split()):
            counts[phrase] += 1

    return [name for name, count in counts.items() if count >= 3]


# =============================================================================
# SIGNAL SCORING
# =============================================================================


def _build_patterns(name: str) -> dict:
    n = re.escape(name)
    return {
        "dialogue": [
            re.compile(p.format(name=n), re.MULTILINE | re.IGNORECASE)
            for p in _DIALOGUE_PATTERNS
        ],
        "person_verbs": [
            re.compile(p.format(name=n), re.IGNORECASE)
            for p in _PERSON_VERB_PATTERNS
        ],
        "project_verbs": [
            re.compile(p.format(name=n), re.IGNORECASE)
            for p in _PROJECT_VERB_PATTERNS
        ],
        "direct": re.compile(
            rf"\bhey\s+{n}\b|\bthanks?\s+{n}\b|\bhi\s+{n}\b", re.IGNORECASE
        ),
        "versioned": re.compile(rf"\b{n}[-v]\w+", re.IGNORECASE),
        "code_ref": re.compile(
            rf"\b{n}\.(py|js|ts|yaml|yml|json|sh)\b", re.IGNORECASE
        ),
    }


def score_entity(name: str, text: str) -> dict:
    """Score a candidate entity as person vs project.

    Weights (matching MemPalace):
      direct address  ×4
      dialogue marker ×3
      versioned/hyphenated ×3
      code file ref   ×3
      person verbs    ×2
      pronoun proximity ×2
      project verbs   ×2

    Args:
        name: Candidate entity name.
        text: Full text to score against.

    Returns:
        Dict with person_score, project_score, person_signals, project_signals.
    """
    lines = text.splitlines()
    patterns = _build_patterns(name)
    person_score = 0
    project_score = 0
    person_signals: list[str] = []
    project_signals: list[str] = []

    for rx in patterns["dialogue"]:
        matches = len(rx.findall(text))
        if matches > 0:
            person_score += matches * 3
            person_signals.append(f"dialogue marker ({matches}x)")

    for rx in patterns["person_verbs"]:
        matches = len(rx.findall(text))
        if matches > 0:
            person_score += matches * 2
            person_signals.append(f"'{name} ...' action ({matches}x)")

    name_lower = name.lower()
    name_line_indices = [
        i for i, line in enumerate(lines) if name_lower in line.lower()
    ]
    pronoun_hits = 0
    for idx in name_line_indices:
        window_text = " ".join(lines[max(0, idx - 2) : idx + 3]).lower()
        for pronoun_pattern in _PRONOUN_PATTERNS:
            if re.search(pronoun_pattern, window_text):
                pronoun_hits += 1
                break
    if pronoun_hits > 0:
        person_score += pronoun_hits * 2
        person_signals.append(f"pronoun nearby ({pronoun_hits}x)")

    direct = len(patterns["direct"].findall(text))
    if direct > 0:
        person_score += direct * 4
        person_signals.append(f"addressed directly ({direct}x)")

    for rx in patterns["project_verbs"]:
        matches = len(rx.findall(text))
        if matches > 0:
            project_score += matches * 2
            project_signals.append(f"project verb ({matches}x)")

    versioned = len(patterns["versioned"].findall(text))
    if versioned > 0:
        project_score += versioned * 3
        project_signals.append(f"versioned/hyphenated ({versioned}x)")

    code_ref = len(patterns["code_ref"].findall(text))
    if code_ref > 0:
        project_score += code_ref * 3
        project_signals.append(f"code file reference ({code_ref}x)")

    return {
        "person_score": person_score,
        "project_score": project_score,
        "person_signals": person_signals[:3],
        "project_signals": project_signals[:3],
    }


# =============================================================================
# CLASSIFY
# =============================================================================


def classify_entity(name: str, frequency: int, scores: dict) -> dict:
    """Classify an entity as person, project, or uncertain.

    Person threshold: person_ratio >= 0.7, 2+ distinct signal categories,
    and person score >= 5.

    Args:
        name: Entity name string.
        frequency: How many times it appeared in source text.
        scores: Output of score_entity().

    Returns:
        Dict with name, type, confidence, frequency, signals.
    """
    ps = scores["person_score"]
    prs = scores["project_score"]
    total = ps + prs

    if total == 0:
        confidence = min(0.4, frequency / 50)
        return {
            "name": name,
            "type": "uncertain",
            "confidence": round(confidence, 2),
            "frequency": frequency,
            "signals": [f"appears {frequency}x, no strong type signals"],
        }

    person_ratio = ps / total

    signal_categories: set[str] = set()
    for s in scores["person_signals"]:
        if "dialogue" in s:
            signal_categories.add("dialogue")
        elif "action" in s:
            signal_categories.add("action")
        elif "pronoun" in s:
            signal_categories.add("pronoun")
        elif "addressed" in s:
            signal_categories.add("addressed")

    has_two_signal_types = len(signal_categories) >= 2

    if person_ratio >= 0.7 and has_two_signal_types and ps >= 5:
        entity_type = "person"
        confidence = min(0.99, 0.5 + person_ratio * 0.5)
        signals = scores["person_signals"] or [f"appears {frequency}x"]
    elif person_ratio >= 0.7 and (not has_two_signal_types or ps < 5):
        entity_type = "uncertain"
        confidence = 0.4
        signals = scores["person_signals"] + [f"appears {frequency}x — pronoun-only match"]
    elif person_ratio <= 0.3:
        entity_type = "project"
        confidence = min(0.99, 0.5 + (1 - person_ratio) * 0.5)
        signals = scores["project_signals"] or [f"appears {frequency}x"]
    else:
        entity_type = "uncertain"
        confidence = 0.5
        signals = (scores["person_signals"] + scores["project_signals"])[:3]
        signals.append("mixed signals — needs review")

    return {
        "name": name,
        "type": entity_type,
        "confidence": round(confidence, 2),
        "frequency": frequency,
        "signals": signals,
    }


# =============================================================================
# MAIN ENTRY POINT
# =============================================================================


def detect_entities(text: str) -> dict:
    """Detect and classify all entity candidates in text.

    Args:
        text: Source text to analyse.

    Returns:
        Dict with "people", "projects", "uncertain" — each a list of entity
        dicts sorted by confidence descending.
    """
    candidates = extract_candidates(text)
    if not candidates:
        return {"people": [], "projects": [], "uncertain": []}

    word_counts: dict[str, int] = defaultdict(int)
    for word in re.findall(r"\b([A-Z][a-z]{1,19})\b", text):
        if word.lower() not in _STOPWORDS:
            word_counts[word] += 1
    for phrase in re.findall(r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\b", text):
        if not any(w.lower() in _STOPWORDS for w in phrase.split()):
            word_counts[phrase] += 1

    people: list[dict] = []
    projects: list[dict] = []
    uncertain: list[dict] = []

    for name in candidates:
        frequency = word_counts.get(name, 3)
        scores = score_entity(name, text)
        entity = classify_entity(name, frequency, scores)

        if entity["type"] == "person":
            people.append(entity)
        elif entity["type"] == "project":
            projects.append(entity)
        else:
            uncertain.append(entity)

    people.sort(key=lambda x: x["confidence"], reverse=True)
    projects.sort(key=lambda x: x["confidence"], reverse=True)
    uncertain.sort(key=lambda x: x["frequency"], reverse=True)

    return {
        "people": people[:15],
        "projects": projects[:10],
        "uncertain": uncertain[:8],
    }
