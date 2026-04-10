"""
memory_classifier.py — Zero-LLM memory type extraction.

Ported from MemPalace's general_extractor.py. Pure logic module — no darkmem
imports, no async, no database access.

Five memory types:
  decision   — explicit choices and architecture rationale
  preference — habits, rules, style preferences
  milestone  — breakthroughs, things that finally worked
  problem    — bugs, root causes, workarounds
  emotional  — feelings, vulnerability, relationships
"""

import re
from typing import Optional


# =============================================================================
# MARKER SETS
# =============================================================================

DECISION_MARKERS: list[str] = [
    r"\blet'?s (use|go with|try|pick|choose|switch to)\b",
    r"\bwe (should|decided|chose|went with|picked|settled on)\b",
    r"\bi'?m going (to|with)\b",
    r"\bbetter (to|than|approach|option|choice)\b",
    r"\binstead of\b",
    r"\brather than\b",
    r"\bthe reason (is|was|being)\b",
    r"\bbecause\b",
    r"\btrade-?off\b",
    r"\bpros and cons\b",
    r"\bover\b.*\bbecause\b",
    r"\barchitecture\b",
    r"\bapproach\b",
    r"\bstrategy\b",
    r"\bpattern\b",
    r"\bstack\b",
    r"\bframework\b",
    r"\binfrastructure\b",
    r"\bset (it |this )?to\b",
    r"\bconfigure\b",
    r"\bdefault\b",
]

PREFERENCE_MARKERS: list[str] = [
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
]

MILESTONE_MARKERS: list[str] = [
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
]

PROBLEM_MARKERS: list[str] = [
    r"\b(bug|error|crash|fail|broke|broken|issue|problem)\b",
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
]

EMOTION_MARKERS: list[str] = [
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
]

_ALL_MARKERS: dict[str, list[str]] = {
    "decision": DECISION_MARKERS,
    "preference": PREFERENCE_MARKERS,
    "milestone": MILESTONE_MARKERS,
    "problem": PROBLEM_MARKERS,
    "emotional": EMOTION_MARKERS,
}

_CROSS_CATEGORY_MARKERS: frozenset[str] = frozenset([
    r"\bfixed\b",
    r"\bsolved\b",
    r"\bresolved\b",
    r"\bturns out\b",
    r"\bfound (out|that)\b",
    r"\bbecause\b",
    r"\bdiscovered\b",
    r"\brealized\b",
    r"\bthe key (is|was|insight)\b",
    r"\bthe trick (is|was)\b",
])


# =============================================================================
# SENTIMENT
# =============================================================================

_POSITIVE_WORDS: set[str] = {
    "pride", "proud", "joy", "happy", "love", "loving", "beautiful", "amazing",
    "wonderful", "incredible", "fantastic", "brilliant", "perfect", "excited",
    "thrilled", "grateful", "warm", "breakthrough", "success", "works",
    "working", "solved", "fixed", "nailed", "heart", "hug", "precious", "adore",
}

_NEGATIVE_WORDS: set[str] = {
    "bug", "error", "crash", "crashing", "crashed", "fail", "failed", "failing",
    "failure", "broken", "broke", "breaking", "breaks", "issue", "problem",
    "wrong", "stuck", "blocked", "unable", "impossible", "missing", "terrible",
    "horrible", "awful", "worse", "worst", "panic", "disaster", "mess",
}


def _get_sentiment(text: str) -> str:
    words = {w.lower() for w in re.findall(r"\b\w+\b", text)}
    pos = len(words & _POSITIVE_WORDS)
    neg = len(words & _NEGATIVE_WORDS)
    if pos > neg:
        return "positive"
    elif neg > pos:
        return "negative"
    return "neutral"


def _has_resolution(text: str) -> bool:
    text_lower = text.lower()
    patterns = [
        r"\bfixed\b",
        r"\bsolved\b",
        r"\bresolved\b",
        r"\bpatched\b",
        r"\bgot it working\b",
        r"\bit works\b",
        r"\bnailed it\b",
        r"\bfigured (it )?out\b",
        r"\bthe (fix|answer|solution)\b",
    ]
    return any(re.search(p, text_lower) for p in patterns)


# =============================================================================
# CODE LINE FILTERING
# =============================================================================

_CODE_LINE_PATTERNS: list[re.Pattern] = [
    re.compile(r"^\s*[\$#]\s"),
    re.compile(
        r"^\s*(cd|source|echo|export|pip|npm|git|python|bash|curl|wget|mkdir|rm|cp|mv|ls|cat|grep|find|chmod|sudo|brew|docker)\s"
    ),
    re.compile(r"^\s*```"),
    re.compile(r"^\s*(import|from|def|class|function|const|let|var|return)\s"),
    re.compile(r"^\s*[A-Z_]{2,}="),
    re.compile(r"^\s*\|"),
    re.compile(r"^\s*[-]{2,}"),
    re.compile(r"^\s*[{}\[\]]\s*$"),
    re.compile(r"^\s*(if|for|while|try|except|elif|else:)\b"),
    re.compile(r"^\s*\w+\.\w+\("),
    re.compile(r"^\s*\w+ = \w+\.\w+"),
]


def _is_code_line(line: str) -> bool:
    stripped = line.strip()
    if not stripped:
        return False
    for pattern in _CODE_LINE_PATTERNS:
        if pattern.match(stripped):
            return True
    alpha_ratio = sum(1 for c in stripped if c.isalpha()) / max(len(stripped), 1)
    if alpha_ratio < 0.4 and len(stripped) > 10:
        return True
    return False


def _extract_prose(text: str) -> str:
    """Strip code lines before classification scoring.

    Args:
        text: Raw text potentially containing code blocks and shell lines.

    Returns:
        Prose-only text, falling back to the original if nothing remains.
    """
    lines = text.split("\n")
    prose: list[str] = []
    in_code = False
    for line in lines:
        if line.strip().startswith("```"):
            in_code = not in_code
            continue
        if in_code:
            continue
        if not _is_code_line(line):
            prose.append(line)
    result = "\n".join(prose).strip()
    return result if result else text


# =============================================================================
# SCORING
# =============================================================================


def _score_markers(
    text: str, markers: list[str]
) -> tuple[float, list[str]]:
    text_lower = text.lower()
    score = 0.0
    keywords: list[str] = []
    for marker in markers:
        matches = re.findall(marker, text_lower)
        if matches:
            weight = 0.5 if marker in _CROSS_CATEGORY_MARKERS else 1.0
            score += len(matches) * weight
            keywords.extend(
                m if isinstance(m, str) else (m[0] if m else marker)
                for m in matches
            )
    return score, list(set(keywords))


# =============================================================================
# TURN SPLITTER
# =============================================================================

_TURN_PATTERNS: list[re.Pattern] = [
    re.compile(r"^>\s"),
    re.compile(r"^(Human|User|Q)\s*:", re.I),
    re.compile(r"^(Assistant|AI|A|Claude|ChatGPT)\s*:", re.I),
]


def _split_by_turns(text: str) -> list[str]:
    """Split text into segments at each speaker-turn boundary.

    Recognises "> " (quote marker), "Human:", "User:", "Q:", "Assistant:",
    "AI:", "Claude:", and "ChatGPT:" prefixes.

    Args:
        text: Multi-turn conversation text.

    Returns:
        List of per-turn text segments.
    """
    lines = text.split("\n")
    segments: list[str] = []
    current: list[str] = []

    for line in lines:
        stripped = line.strip()
        is_turn = any(pat.match(stripped) for pat in _TURN_PATTERNS)
        if is_turn and current:
            segments.append("\n".join(current))
            current = [line]
        else:
            current.append(line)

    if current:
        segments.append("\n".join(current))

    return segments


def _split_into_segments(text: str) -> list[str]:
    lines = text.split("\n")
    turn_count = sum(
        1 for line in lines
        if any(pat.match(line.strip()) for pat in _TURN_PATTERNS)
    )

    if turn_count >= 3:
        return _split_by_turns(text)

    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]

    if len(paragraphs) <= 1 and len(lines) > 20:
        segments: list[str] = []
        for i in range(0, len(lines), 25):
            group = "\n".join(lines[i : i + 25]).strip()
            if group:
                segments.append(group)
        return segments

    return paragraphs


# =============================================================================
# DISAMBIGUATION
# =============================================================================


_PAST_TENSE_PROBLEM_PATTERNS: list[str] = [
    r"\bwas\b",
    r"\bhad been\b",
    r"\bused to\b",
    r"\bpreviously\b",
]

_DELIBERATE_CHOICE_PATTERNS: list[str] = [
    r"\bchose\b",
    r"\bdecided\b",
    r"\bwent with\b",
    r"\bpicked\b",
    r"\bsettled on\b",
    r"\boptd? (to|for)\b",
]


def _disambiguate(scores: dict[str, float], text: str) -> Optional[str]:
    """Reclassify ambiguous top categories, returning corrected type or None.

    Args:
        scores: Per-type float scores from marker matching.
        text: Prose text (already code-stripped).

    Returns:
        Corrected memory type string, or None if no reclassification needed.
    """
    max_type = max(scores, key=scores.get)  # type: ignore[arg-type]
    text_lower = text.lower()

    if max_type == "milestone" and scores.get("problem", 0) > 0:
        if any(re.search(p, text_lower) for p in _PAST_TENSE_PROBLEM_PATTERNS):
            return "milestone"

    if max_type == "decision" and scores.get("problem", 0) > 0:
        if any(re.search(p, text_lower) for p in _DELIBERATE_CHOICE_PATTERNS):
            return "decision"

    if max_type != "problem":
        return None

    sentiment = _get_sentiment(text)
    if _has_resolution(text):
        if scores.get("emotional", 0) > 0 and sentiment == "positive":
            return "emotional"
        return "milestone"

    if sentiment == "positive":
        if scores.get("milestone", 0) > 0:
            return "milestone"
        if scores.get("emotional", 0) > 0:
            return "emotional"

    return None


# =============================================================================
# PUBLIC API
# =============================================================================


def classify(text: str, min_confidence: float = 0.3, enabled_areas: list[str] | None = None, mode: str = "expanded") -> dict:
    """Classify a text chunk into a memory type using zero-LLM heuristics.

    Args:
        text: Text to classify (any format — conversations, notes, docs).
        min_confidence: Minimum confidence threshold (0.0–1.0).
        enabled_areas: List of classification area keys to use. Defaults to ["general"].

    Returns:
        Dict with keys:
          "hall"        — the best-match memory type string, or "fact" as fallback.
          "emotions"    — list of detected emotion codes.
          "flags"       — list of detected flag strings.
          "memory_type" — same as "hall" for API symmetry.
          "confidence"  — float confidence score.
          "scores"      — per-type raw scores dict.
    """
    from .classification_areas import get_merged_markers
    from .dialect import detect_emotions, detect_flags

    markers = get_merged_markers(enabled_areas, mode=mode)
    prose = _extract_prose(text)

    scores: dict[str, float] = {}
    for mem_type, type_markers in markers.items():
        score, _ = _score_markers(prose, type_markers)
        if score > 0:
            scores[mem_type] = score

    emotions = detect_emotions(text)
    flags = detect_flags(text)

    if not scores:
        return {
            "hall": "fact",
            "memory_type": "fact",
            "emotions": emotions,
            "flags": flags,
            "confidence": 0.0,
            "scores": {},
        }

    length_bonus = 2 if len(text) > 500 else (1 if len(text) > 200 else 0)
    max_type = max(scores, key=scores.get)  # type: ignore[arg-type]
    max_score = scores[max_type] + length_bonus

    reclassified = _disambiguate(scores, prose)
    if reclassified:
        max_type = reclassified

    confidence = min(1.0, max_score / 5.0)

    if confidence < min_confidence:
        return {
            "hall": "fact",
            "memory_type": "fact",
            "emotions": emotions,
            "flags": flags,
            "confidence": confidence,
            "scores": scores,
        }

    return {
        "hall": max_type,
        "memory_type": max_type,
        "emotions": emotions,
        "flags": flags,
        "confidence": round(confidence, 3),
        "scores": scores,
    }


def extract_memories(text: str, min_confidence: float = 0.3, enabled_areas: list[str] | None = None, mode: str = "expanded") -> list[dict]:
    """Extract typed memory chunks from a text string.

    Splits the text into segments (by speaker turns or paragraphs), classifies
    each segment, and returns only those that meet the confidence threshold.

    Args:
        text: Source text in any format.
        min_confidence: Minimum confidence threshold (0.0–1.0).
        enabled_areas: List of classification area keys. Defaults to ["general"].

    Returns:
        List of dicts: {"content": str, "memory_type": str, "chunk_index": int}.
    """
    segments = _split_into_segments(text)
    memories: list[dict] = []

    for segment in segments:
        if len(segment.strip()) < 20:
            continue

        result = classify(segment, min_confidence=min_confidence, enabled_areas=enabled_areas, mode=mode)
        if result["hall"] == "fact" and result["confidence"] == 0.0:
            continue

        memories.append(
            {
                "content": segment.strip(),
                "memory_type": result["memory_type"],
                "chunk_index": len(memories),
            }
        )

    return memories
