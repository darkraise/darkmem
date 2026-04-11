"""
convo_miner.py — Conversation mining and room detection.

Ported from MemPalace's convo_miner.py. Pure logic module — no darkmem
imports, no async, no database access.

Two chunking modes:
  exchange — user turn ("> " prefix) + AI response truncated to 8 lines
  general  — paragraph fallback for non-conversational text

detect_room() assigns a topic slug by keyword scoring.
"""

import re


MIN_CHUNK_SIZE = 30


# =============================================================================
# TOPIC KEYWORDS FOR ROOM DETECTION
# =============================================================================

TOPIC_KEYWORDS: dict[str, list[str]] = {
    "technical": [
        "code", "python", "function", "bug", "error", "api", "database",
        "server", "deploy", "git", "test", "debug", "refactor",
    ],
    "architecture": [
        "architecture", "design", "pattern", "structure", "schema",
        "interface", "module", "component", "service", "layer",
    ],
    "planning": [
        "plan", "roadmap", "milestone", "deadline", "priority", "sprint",
        "backlog", "scope", "requirement", "spec",
    ],
    "decisions": [
        "decided", "chose", "picked", "switched", "migrated", "replaced",
        "trade-off", "alternative", "option", "approach",
    ],
    "problems": [
        "problem", "issue", "broken", "failed", "crash", "stuck",
        "workaround", "fix", "solved", "resolved",
    ],
}


# =============================================================================
# CHUNKING
# =============================================================================


def _chunk_by_exchange(lines: list[str]) -> list[dict]:
    """One user turn ("> " prefix) + the AI response that follows = one chunk.

    AI response is truncated to 8 non-empty lines to keep chunks compact.
    """
    chunks: list[dict] = []
    i = 0

    while i < len(lines):
        line = lines[i]
        if line.strip().startswith(">"):
            user_turn = line.strip()
            i += 1

            ai_lines: list[str] = []
            while i < len(lines):
                next_line = lines[i]
                if next_line.strip().startswith(">") or next_line.strip().startswith("---"):
                    break
                if next_line.strip():
                    ai_lines.append(next_line.strip())
                i += 1

            ai_response = " ".join(ai_lines[:8])
            content = f"{user_turn}\n{ai_response}" if ai_response else user_turn

            if len(content.strip()) > MIN_CHUNK_SIZE:
                chunks.append(
                    {
                        "content": content,
                        "chunk_index": len(chunks),
                        "mode": "exchange",
                    }
                )
        else:
            i += 1

    return chunks


def _chunk_by_paragraph(content: str) -> list[dict]:
    """Fallback: chunk by paragraph breaks (double newlines).

    If no paragraph breaks are present and the content is long,
    chunks into groups of 25 lines.
    """
    chunks: list[dict] = []
    paragraphs = [p.strip() for p in content.split("\n\n") if p.strip()]

    if len(paragraphs) <= 1 and content.count("\n") > 20:
        lines = content.split("\n")
        for i in range(0, len(lines), 25):
            group = "\n".join(lines[i : i + 25]).strip()
            if len(group) > MIN_CHUNK_SIZE:
                chunks.append(
                    {
                        "content": group,
                        "chunk_index": len(chunks),
                        "mode": "general",
                    }
                )
        return chunks

    for para in paragraphs:
        if len(para) > MIN_CHUNK_SIZE:
            chunks.append(
                {
                    "content": para,
                    "chunk_index": len(chunks),
                    "mode": "general",
                }
            )

    return chunks


def chunk_exchanges(text: str) -> list[dict]:
    """Chunk text into exchange pairs (user turn + AI response).

    Uses exchange-pair mode when 3 or more "> " quote lines are found,
    otherwise falls back to paragraph chunking.

    Args:
        text: Raw conversation or document text.

    Returns:
        List of chunk dicts with "content", "chunk_index", and "mode".
    """
    lines = text.split("\n")
    quote_lines = sum(1 for line in lines if line.strip().startswith(">"))

    if quote_lines >= 3:
        return _chunk_by_exchange(lines)
    return _chunk_by_paragraph(text)


# =============================================================================
# ROOM DETECTION
# =============================================================================


def detect_room(text: str) -> str:
    """Assign a topic room slug by keyword scoring.

    Scans the first 3 000 characters of text against TOPIC_KEYWORDS. Returns
    the room with the highest keyword hit count, or "general" if none match.

    Args:
        text: Text to classify (conversation chunk or document).

    Returns:
        Room slug string: one of "technical", "architecture", "planning",
        "decisions", "problems", or "general".
    """
    content_lower = text[:3000].lower()
    scores: dict[str, int] = {}
    for room, keywords in TOPIC_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw in content_lower)
        if score > 0:
            scores[room] = score
    if scores:
        return max(scores, key=scores.get)  # type: ignore[arg-type]
    return "general"


# =============================================================================
# MINING ENTRY POINT
# =============================================================================


def mine_text(
    text: str,
    extract_mode: str = "exchange",
    source_file: str = "",
) -> list[dict]:
    """Mine plain text into memory chunks with room labels.

    Args:
        text: Source text to process.
        extract_mode: "exchange" for Q+A pair chunking, or "general" to
                      use memory_classifier for typed memory extraction.
        source_file: Optional source file name recorded in chunk metadata.

    Returns:
        List of chunk dicts. Each dict includes "content", "chunk_index",
        "mode", "room", and optionally "memory_type" (in general mode).
    """
    if not text or len(text.strip()) < MIN_CHUNK_SIZE:
        return []

    if extract_mode == "general":
        from .memory_classifier import extract_memories

        raw_chunks = extract_memories(text)
        chunks: list[dict] = []
        for chunk in raw_chunks:
            memory_type = chunk.get("memory_type", "general")
            chunks.append(
                {
                    "content": chunk["content"],
                    "chunk_index": len(chunks),
                    "mode": "general",
                    "room": memory_type,
                    "memory_type": memory_type,
                    "source_file": source_file,
                }
            )
        return chunks

    raw_chunks = chunk_exchanges(text)
    room = detect_room(text)
    result: list[dict] = []
    for chunk in raw_chunks:
        chunk["room"] = room
        chunk["source_file"] = source_file
        result.append(chunk)
    return result


# =============================================================================
# TURN NORMALISATION (speaker prefix detection)
# =============================================================================

_TURN_RE = re.compile(
    r"^(?:Human|User|Q|Assistant|AI|Claude|ChatGPT)\s*:",
    re.IGNORECASE,
)


def is_conversation(text: str) -> bool:
    """Return True if the text looks like a multi-turn conversation.

    Checks for "> " quote lines or labelled speaker prefixes
    (Human:, User:, Assistant:, etc.).

    Args:
        text: Text to inspect.

    Returns:
        True if conversation markers are found.
    """
    lines = text.split("\n")
    quote_count = sum(1 for line in lines if line.strip().startswith(">"))
    turn_count = sum(1 for line in lines if _TURN_RE.match(line.strip()))
    return (quote_count + turn_count) >= 3
