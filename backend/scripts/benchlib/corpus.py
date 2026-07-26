"""Pure-parsing corpus loader.

Loads corpus JSON (both smoke and gold shapes) and validates entries.
No database, no pipeline knowledge — just JSON parsing and taxonomy validation.
"""
import json
from pathlib import Path

from app.taxonomy import _ENTITY_TYPE_SET, _MEMORY_TYPE_SET, _RELATIONSHIP_TYPE_SET

EXPECTED_COUNT_KEYS = frozenset({"memories", "entities", "relations"})


def load_corpus(path: str | Path) -> list[dict]:
    """Load corpus JSON and validate entries.

    Accepts two shapes:
    - Smoke corpus: {"memories": [entries with content, source, memory_type, created_at]}
    - Gold corpus: {"_notes": str, "memories": [entries with id, content, hint, entities, relations]}

    Args:
        path: Path to corpus JSON file.

    Returns:
        List of entry dicts from the "memories" key.

    Raises:
        ValueError: If the file carries no "memories" key, or any entry is
            missing required fields or has untabled types.
    """
    path = Path(path)
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)

    # A renamed or typo'd key must not read as "a corpus of zero memories":
    # every downstream count would then be trivially satisfied by nothing.
    if "memories" not in data:
        raise ValueError(f"corpus {path} has no 'memories' key")

    entries = data["memories"]

    for idx, entry in enumerate(entries):
        if "content" not in entry:
            raise ValueError(
                f"entry {idx} missing required field 'content'"
            )

        _validate_gold_labels(entry, idx)
        _validate_memory_types(entry, idx)

    return entries


def load_expectations(path: str | Path) -> dict | None:
    """Return the corpus's declared expected-work counts, or None.

    A corpus declares what ingesting it should produce, so a run that
    silently does less work (a stale cache, a degraded extraction) can be
    caught against the corpus itself rather than against numbers hardcoded
    in a runner. Gold corpora carry no expectations; None is not an error.

    Raises:
        ValueError: If "expected" is present but is not an object of known
            keys mapped to non-negative integers.
    """
    path = Path(path)
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)

    expected = data.get("expected")
    if expected is None:
        return None
    if not isinstance(expected, dict):
        raise ValueError(f"corpus {path}: 'expected' must be an object")

    unknown = sorted(set(expected) - EXPECTED_COUNT_KEYS)
    if unknown:
        raise ValueError(
            f"corpus {path}: unknown 'expected' key(s) {unknown}; "
            f"known keys are {sorted(EXPECTED_COUNT_KEYS)}"
        )
    for key, value in expected.items():
        if not isinstance(value, int) or isinstance(value, bool) or value < 0:
            raise ValueError(
                f"corpus {path}: expected.{key} must be a non-negative integer, "
                f"got {value!r}"
            )
    return dict(expected)


def _validate_gold_labels(entry: dict, entry_idx: int) -> None:
    """Validate entity and relation types against closed taxonomy.

    Args:
        entry: A corpus entry dict.
        entry_idx: The 0-indexed position of this entry in the corpus.

    Raises:
        ValueError: If any entity or relation type is not in the closed taxonomy.
    """
    entities = entry.get("entities")
    if entities:
        for entity in entities:
            etype = entity.get("type")
            if etype not in _ENTITY_TYPE_SET:
                raise ValueError(
                    f"entry {entry_idx}: untabled entity type '{etype}'"
                )

    relations = entry.get("relations")
    if relations:
        for relation in relations:
            rtype = relation.get("type")
            if rtype not in _RELATIONSHIP_TYPE_SET:
                raise ValueError(
                    f"entry {entry_idx}: untabled relation type '{rtype}'"
                )


def _validate_memory_types(entry: dict, entry_idx: int) -> None:
    """Validate ``memory_type`` (smoke shape) and ``hint`` (gold shape)
    against MEMORY_TYPES, the third closed vocabulary.

    Held to the same raw-membership standard as the other two: a legacy
    alias such as ``debug`` or ``design`` is an untabled type here even
    though ``normalize_memory_type`` would rewrite it to ``problem`` /
    ``architecture`` on the way into the database.

    Raises:
        ValueError: If either field carries a value outside MEMORY_TYPES.
    """
    for field in ("memory_type", "hint"):
        value = entry.get(field)
        if value is None:
            continue
        if value not in _MEMORY_TYPE_SET:
            raise ValueError(
                f"entry {entry_idx}: untabled {field} '{value}'"
            )
