"""
AAAK Dialect -- Compressed Symbolic Memory Language.

Ported from MemPalace's dialect.py. Pure logic module — no darkmem imports,
no async, no database access.

FORMAT:
  Content: ZID:ENTITIES|topic_keywords|"key_quote"|EMOTIONS|FLAGS
  Header:  wing|room|date|source_stem
"""

import re
from typing import Optional


# === EMOTION CODES ===

EMOTION_CODES: dict[str, str] = {
    "vulnerability": "vul",
    "vulnerable": "vul",
    "joy": "joy",
    "joyful": "joy",
    "fear": "fear",
    "mild_fear": "fear",
    "trust": "trust",
    "trust_building": "trust",
    "grief": "grief",
    "raw_grief": "grief",
    "wonder": "wonder",
    "philosophical_wonder": "wonder",
    "rage": "rage",
    "anger": "rage",
    "love": "love",
    "devotion": "love",
    "hope": "hope",
    "despair": "despair",
    "hopelessness": "despair",
    "peace": "peace",
    "relief": "relief",
    "humor": "humor",
    "dark_humor": "humor",
    "tenderness": "tender",
    "raw_honesty": "raw",
    "brutal_honesty": "raw",
    "self_doubt": "doubt",
    "anxiety": "anx",
    "exhaustion": "exhaust",
    "conviction": "convict",
    "quiet_passion": "passion",
    "warmth": "warmth",
    "curiosity": "curious",
    "gratitude": "grat",
    "frustration": "frust",
    "confusion": "confuse",
    "satisfaction": "satis",
    "excitement": "excite",
    "determination": "determ",
    "surprise": "surprise",
}

# Keywords that signal emotions in plain text → emotion code
_EMOTION_SIGNALS: dict[str, str] = {
    "decided": "determ",
    "prefer": "convict",
    "worried": "anx",
    "excited": "excite",
    "frustrated": "frust",
    "confused": "confuse",
    "love": "love",
    "hate": "rage",
    "hope": "hope",
    "fear": "fear",
    "trust": "trust",
    "happy": "joy",
    "sad": "grief",
    "surprised": "surprise",
    "grateful": "grat",
    "curious": "curious",
    "wonder": "wonder",
    "anxious": "anx",
    "relieved": "relief",
    "satisf": "satis",
    "disappoint": "grief",
    "concern": "anx",
}

# Keywords that signal flags in plain text → flag name
_FLAG_SIGNALS: dict[str, str] = {
    "decided": "DECISION",
    "chose": "DECISION",
    "switched": "DECISION",
    "migrated": "DECISION",
    "replaced": "DECISION",
    "instead of": "DECISION",
    "because": "DECISION",
    "founded": "ORIGIN",
    "created": "ORIGIN",
    "started": "ORIGIN",
    "born": "ORIGIN",
    "launched": "ORIGIN",
    "first time": "ORIGIN",
    "core": "CORE",
    "fundamental": "CORE",
    "essential": "CORE",
    "principle": "CORE",
    "belief": "CORE",
    "always": "CORE",
    "never forget": "CORE",
    "turning point": "PIVOT",
    "changed everything": "PIVOT",
    "realized": "PIVOT",
    "breakthrough": "PIVOT",
    "epiphany": "PIVOT",
    "api": "TECHNICAL",
    "database": "TECHNICAL",
    "architecture": "TECHNICAL",
    "deploy": "TECHNICAL",
    "infrastructure": "TECHNICAL",
    "algorithm": "TECHNICAL",
    "framework": "TECHNICAL",
    "server": "TECHNICAL",
    "config": "TECHNICAL",
}

_STOP_WORDS: set[str] = {
    "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "will", "would", "could",
    "should", "may", "might", "shall", "can", "to", "of", "in", "for",
    "on", "with", "at", "by", "from", "as", "into", "about", "between",
    "through", "during", "before", "after", "above", "below", "up", "down",
    "out", "off", "over", "under", "again", "further", "then", "once",
    "here", "there", "when", "where", "why", "how", "all", "each", "every",
    "both", "few", "more", "most", "other", "some", "such", "no", "nor",
    "not", "only", "own", "same", "so", "than", "too", "very", "just",
    "don", "now", "and", "but", "or", "if", "while", "that", "this",
    "these", "those", "it", "its", "i", "we", "you", "he", "she", "they",
    "me", "him", "her", "us", "them", "my", "your", "his", "our", "their",
    "what", "which", "who", "whom", "also", "much", "many", "like",
    "because", "since", "get", "got", "use", "used", "using", "make",
    "made", "thing", "things", "way", "well", "really", "want", "need",
}


def detect_emotions(text: str) -> list[str]:
    """Detect emotions from plain text using keyword signals.

    Args:
        text: Plain text to scan.

    Returns:
        List of up to 3 emotion codes (e.g. ["determ", "anx"]).
    """
    text_lower = text.lower()
    detected: list[str] = []
    seen: set[str] = set()
    for keyword, code in _EMOTION_SIGNALS.items():
        if keyword in text_lower and code not in seen:
            detected.append(code)
            seen.add(code)
    return detected[:3]


def detect_flags(text: str) -> list[str]:
    """Detect importance flags from plain text using keyword signals.

    SENSITIVE is intentionally omitted here — it is only assigned from
    structured zettel metadata (sensitivity field), not from prose.

    Args:
        text: Plain text to scan.

    Returns:
        List of up to 3 flag strings (e.g. ["DECISION", "TECHNICAL"]).
    """
    text_lower = text.lower()
    detected: list[str] = []
    seen: set[str] = set()
    for keyword, flag in _FLAG_SIGNALS.items():
        if keyword in text_lower and flag not in seen:
            detected.append(flag)
            seen.add(flag)
    return detected[:3]


def encode_entity(name: str) -> str:
    """Convert an entity name to its 3-letter uppercase code.

    Args:
        name: Entity name (e.g. "PostgreSQL").

    Returns:
        3-letter uppercase code (e.g. "POS").
    """
    return name[:3].upper()


def _extract_topics(text: str, max_topics: int = 3) -> list[str]:
    words = re.findall(r"[a-zA-Z][a-zA-Z_-]{2,}", text)
    freq: dict[str, int] = {}
    for w in words:
        w_lower = w.lower()
        if w_lower in _STOP_WORDS or len(w_lower) < 3:
            continue
        freq[w_lower] = freq.get(w_lower, 0) + 1

    for w in words:
        w_lower = w.lower()
        if w_lower in _STOP_WORDS:
            continue
        if w[0].isupper() and w_lower in freq:
            freq[w_lower] += 2
        if "_" in w or "-" in w or (any(c.isupper() for c in w[1:])):
            if w_lower in freq:
                freq[w_lower] += 2

    ranked = sorted(freq.items(), key=lambda x: -x[1])
    return [w for w, _ in ranked[:max_topics]]


def _extract_key_sentence(text: str) -> str:
    sentences = re.split(r"[.!?\n]+", text)
    sentences = [s.strip() for s in sentences if len(s.strip()) > 10]
    if not sentences:
        return ""

    decision_words = {
        "decided", "because", "instead", "prefer", "switched", "chose",
        "realized", "important", "key", "critical", "discovered", "learned",
        "conclusion", "solution", "reason", "why", "breakthrough", "insight",
    }
    scored: list[tuple[int, str]] = []
    for s in sentences:
        score = 0
        s_lower = s.lower()
        for w in decision_words:
            if w in s_lower:
                score += 2
        if len(s) < 80:
            score += 1
        if len(s) < 40:
            score += 1
        if len(s) > 150:
            score -= 2
        scored.append((score, s))

    scored.sort(key=lambda x: -x[0])
    best = scored[0][1]
    if len(best) > 55:
        best = best[:52] + "..."
    return best


def _detect_entities_in_text(
    text: str, entity_codes: dict[str, str]
) -> list[str]:
    found: list[str] = []
    for name, code in entity_codes.items():
        if not name.islower() and name.lower() in text.lower():
            if code not in found:
                found.append(code)
    if found:
        return found

    words = text.split()
    for i, w in enumerate(words):
        clean = re.sub(r"[^a-zA-Z]", "", w)
        if (
            len(clean) >= 2
            and clean[0].isupper()
            and clean[1:].islower()
            and i > 0
            and clean.lower() not in _STOP_WORDS
        ):
            code = clean[:3].upper()
            if code not in found:
                found.append(code)
            if len(found) >= 3:
                break
    return found


def compress(
    text: str,
    entities: Optional[dict[str, str]] = None,
    metadata: Optional[dict[str, str]] = None,
) -> str:
    """Compress plain text into AAAK pipe format.

    Args:
        text: Plain text content to compress.
        entities: Mapping of full names to short codes,
                  e.g. {"Alice": "ALC", "Bob": "BOB"}.
        metadata: Optional dict with keys "source_file", "wing", "room", "date".

    Returns:
        AAAK-compressed string.
    """
    entity_codes: dict[str, str] = {}
    if entities:
        for name, code in entities.items():
            entity_codes[name] = code
            entity_codes[name.lower()] = code

    metadata = metadata or {}

    found_entities = _detect_entities_in_text(text, entity_codes)
    entity_str = "+".join(found_entities[:3]) if found_entities else "???"

    topics = _extract_topics(text)
    topic_str = "_".join(topics[:3]) if topics else "misc"

    quote = _extract_key_sentence(text)
    quote_part = f'"{quote}"' if quote else ""

    emotions = detect_emotions(text)
    emotion_str = "+".join(emotions) if emotions else ""

    flags = detect_flags(text)
    flag_str = "+".join(flags) if flags else ""

    source = metadata.get("source_file", "")
    wing = metadata.get("wing", "")
    room = metadata.get("room", "")
    date = metadata.get("date", "")

    lines: list[str] = []

    if source or wing:
        from pathlib import Path

        header_parts = [
            wing or "?",
            room or "?",
            date or "?",
            Path(source).stem if source else "?",
        ]
        lines.append("|".join(header_parts))

    parts = [f"0:{entity_str}", topic_str]
    if quote_part:
        parts.append(quote_part)
    if emotion_str:
        parts.append(emotion_str)
    if flag_str:
        parts.append(flag_str)

    lines.append("|".join(parts))
    return "\n".join(lines)


def decode(aaak_text: str) -> dict:
    """Parse an AAAK Dialect string back into a structured dict.

    Args:
        aaak_text: AAAK-formatted string.

    Returns:
        Dict with keys "header", "arc", "zettels", "tunnels".
    """
    lines = aaak_text.strip().split("\n")
    result: dict = {"header": {}, "arc": "", "zettels": [], "tunnels": []}

    for line in lines:
        if line.startswith("ARC:"):
            result["arc"] = line[4:]
        elif line.startswith("T:"):
            result["tunnels"].append(line)
        elif "|" in line and ":" in line.split("|")[0]:
            result["zettels"].append(line)
        elif "|" in line:
            parts = line.split("|")
            result["header"] = {
                "file": parts[0] if len(parts) > 0 else "",
                "entities": parts[1] if len(parts) > 1 else "",
                "date": parts[2] if len(parts) > 2 else "",
                "title": parts[3] if len(parts) > 3 else "",
            }

    return result


def compression_stats(original: str, compressed: str) -> dict:
    """Measure compression ratio between original text and AAAK output.

    Token estimate uses the ~3 chars/token heuristic from MemPalace.

    Args:
        original: Original plain text.
        compressed: AAAK-compressed string.

    Returns:
        Dict with original_tokens, compressed_tokens, ratio,
        original_chars, compressed_chars.
    """
    orig_tokens = len(original) // 3
    comp_tokens = len(compressed) // 3
    return {
        "original_tokens": orig_tokens,
        "compressed_tokens": comp_tokens,
        "ratio": orig_tokens / max(comp_tokens, 1),
        "original_chars": len(original),
        "compressed_chars": len(compressed),
    }
