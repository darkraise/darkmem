"""Pure-parsing corpus loader.

Loads corpus JSON (both smoke and gold shapes) and validates entries.
No database, no pipeline knowledge — just JSON parsing and taxonomy validation.
"""
import json
from pathlib import Path

from app.taxonomy import _ENTITY_TYPE_SET, _RELATIONSHIP_TYPE_SET


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
        ValueError: If any entry is missing required fields or has untabled types.
    """
    path = Path(path)
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)

    entries = data.get("memories", [])

    for idx, entry in enumerate(entries):
        if "content" not in entry:
            raise ValueError(
                f"entry {idx} missing required field 'content'"
            )

        _validate_gold_labels(entry, idx)

    return entries


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
