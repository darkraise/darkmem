"""Retrieval gold set: loader, validation, and fixed-id corpus seeding.

The gold lives as two JSON files under ``retrieval/`` (doc 17 §4/§11):

- ``corpus.json`` -- the deterministic seeded bench corpus. Every entry
  carries a fixed ``memory_id`` UUID and a declared ``created_at``, so the
  same memory gets the same id and the same date on every ``darkmem_bench``
  reseed and gold ``relevant_memory_ids`` stay valid across DROP SCHEMA
  cycles.
- ``gold.json`` -- the labelled ``(query, relevant_memory_ids, slice_tags)``
  pairs, sliced by the seven doc-17 §4 slices. The file is append-only:
  a wrong pair is retired in place (``"retired": true``), never deleted or
  rewritten, so past entries stay diffable forever (doc 17 §11).

``run_ingest`` honours a caller-supplied ``memory_id`` by passing the entry
through untouched -- it does NOT create the base ``memories`` row for it
(ingest._create_memory_rows's pass-through is for already-created rows).
``seed_memory_rows`` is that missing creation step for a fixed-id corpus:
call it after ``bench_db.reset_bench_db()``, then hand its return value to
``run_ingest``.

Slice definitions -- decision procedures, negative examples, and the
authoring rules the corpus shape depends on -- live in
``retrieval/SLICES.md``. Add pairs against that file, not from memory.
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

from benchlib.corpus import load_corpus

RETRIEVAL_DIR = Path(__file__).resolve().parent / "retrieval"
CORPUS_PATH = RETRIEVAL_DIR / "corpus.json"
GOLD_PATH = RETRIEVAL_DIR / "gold.json"

QUERY_TYPE_SLICES = frozenset({"exact", "paraphrase", "typo", "fact"})
CAPABILITY_SLICES = frozenset({"multi-hop", "temporal", "knowledge-update"})
SLICES = QUERY_TYPE_SLICES | CAPABILITY_SLICES

MEMORY_ID_NAMESPACE = uuid.uuid5(
    uuid.NAMESPACE_URL, "darkmem://benchlib/retrieval-gold/v1"
)


def memory_id_for_key(key: str) -> str:
    """The corpus id-derivation rule: ``memory_id`` is uuid5 of the entry
    ``key`` under a fixed namespace. Deterministic by construction, so a new
    corpus entry's id is minted from its key, never generated at random --
    and a copy-pasted or hand-edited id cannot silently collide, because the
    loader enforces the derivation."""
    return str(uuid.uuid5(MEMORY_ID_NAMESPACE, key))


def load_retrieval_corpus(path: str | Path = CORPUS_PATH) -> list[dict]:
    """Load the retrieval corpus through ``load_corpus`` (closed-taxonomy
    validation) and enforce the retrieval-specific determinism fields.

    Raises:
        ValueError: If any entry lacks a unique UUID ``memory_id``, a
            parseable ISO-8601 ``created_at``, or a unique ``key``.
    """
    entries = load_corpus(path)
    seen_ids: set[uuid.UUID] = set()
    seen_keys: set[str] = set()
    for idx, entry in enumerate(entries):
        raw_id = entry.get("memory_id")
        try:
            mid = uuid.UUID(str(raw_id))
        except (ValueError, AttributeError, TypeError) as exc:
            raise ValueError(
                f"entry {idx}: memory_id {raw_id!r} is not a UUID"
            ) from exc
        if mid in seen_ids:
            raise ValueError(f"entry {idx}: duplicate memory_id {raw_id}")
        seen_ids.add(mid)

        raw_created = entry.get("created_at")
        if not isinstance(raw_created, str):
            raise ValueError(
                f"entry {idx}: created_at must be an ISO-8601 string, "
                f"got {raw_created!r}"
            )
        try:
            datetime.fromisoformat(raw_created)
        except ValueError as exc:
            raise ValueError(
                f"entry {idx}: created_at {raw_created!r} is not ISO-8601"
            ) from exc

        key = entry.get("key")
        if not isinstance(key, str) or not key:
            raise ValueError(f"entry {idx}: missing non-empty 'key'")
        if key in seen_keys:
            raise ValueError(f"entry {idx}: duplicate key {key!r}")
        seen_keys.add(key)

        expected_id = memory_id_for_key(key)
        if str(raw_id) != expected_id:
            raise ValueError(
                f"entry {idx}: memory_id {raw_id} does not derive from key "
                f"{key!r} (expected {expected_id}); mint ids with "
                "memory_id_for_key, never by hand"
            )
    return entries


def load_retrieval_gold(path: str | Path = GOLD_PATH) -> dict:
    """Load and structurally validate the gold pairs file.

    Returns the parsed document (``version``, ``declared_slice_counts``,
    ``pairs``). Cross-file checks against the corpus belong to
    ``validate_gold_against_corpus``.

    Raises:
        ValueError: On any shape violation -- an untabled slice tag, a pair
            carrying other than exactly one tag, duplicate or out-of-order
            pair ids (the append-only discipline: new pairs go at the end,
            old pairs are retired in place, never reordered), or declared
            per-slice counts that disagree with the live pairs.
    """
    path = Path(path)
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)

    if "pairs" not in data:
        raise ValueError(f"gold {path} has no 'pairs' key")
    pairs = data["pairs"]
    if not isinstance(pairs, list) or not pairs:
        raise ValueError(f"gold {path}: 'pairs' must be a non-empty list")

    declared = data.get("declared_slice_counts")
    if not isinstance(declared, dict):
        raise ValueError(f"gold {path}: missing 'declared_slice_counts' object")
    if set(declared) != SLICES:
        raise ValueError(
            f"gold {path}: declared_slice_counts must carry exactly the seven "
            f"slices; got {sorted(declared)}"
        )

    seen_pair_ids: list[str] = []
    computed: dict[str, int] = {s: 0 for s in SLICES}
    for idx, pair in enumerate(pairs):
        pid = pair.get("id")
        if not isinstance(pid, str) or not pid:
            raise ValueError(f"pair {idx}: missing non-empty 'id'")
        seen_pair_ids.append(pid)

        query = pair.get("query")
        if not isinstance(query, str) or not query.strip():
            raise ValueError(f"pair {pid}: missing non-empty 'query'")

        relevant = pair.get("relevant_memory_ids")
        if not isinstance(relevant, list) or not relevant:
            raise ValueError(f"pair {pid}: 'relevant_memory_ids' must be a non-empty list")
        for rid in relevant:
            try:
                uuid.UUID(str(rid))
            except (ValueError, AttributeError, TypeError) as exc:
                raise ValueError(
                    f"pair {pid}: relevant_memory_ids entry {rid!r} is not a UUID"
                ) from exc
        if len(set(relevant)) != len(relevant):
            raise ValueError(f"pair {pid}: duplicate relevant_memory_ids")

        tags = pair.get("slice_tags")
        if not isinstance(tags, list) or len(tags) != 1:
            raise ValueError(
                f"pair {pid}: slice_tags must carry exactly one tag "
                f"(the v1 discipline; see SLICES.md), got {tags!r}"
            )
        tag = tags[0]
        if tag not in SLICES:
            raise ValueError(f"pair {pid}: untabled slice tag {tag!r}")

        if tag == "multi-hop" and len(relevant) < 2 and not pair.get("retired"):
            raise ValueError(
                f"pair {pid}: a multi-hop pair answerable from one memory "
                "tests nothing; it needs >= 2 relevant_memory_ids"
            )

        if not pair.get("retired"):
            computed[tag] += 1

    if len(set(seen_pair_ids)) != len(seen_pair_ids):
        raise ValueError(f"gold {path}: duplicate pair ids")
    if seen_pair_ids != sorted(seen_pair_ids):
        raise ValueError(
            f"gold {path}: pair ids must be in ascending order -- append new "
            "pairs at the end, retire wrong ones in place, never reorder"
        )

    if computed != declared:
        raise ValueError(
            f"gold {path}: declared_slice_counts disagree with the live "
            f"(non-retired) pairs: declared={declared} computed={computed}"
        )

    return data


def validate_gold_against_corpus(gold: dict, entries: list[dict]) -> None:
    """Every ``relevant_memory_ids`` entry must resolve to a memory the
    corpus actually declares -- gold pointing at ids the seeded bench DB will
    never contain is gold nobody can score against.

    Raises:
        ValueError: Naming the first dangling id and its pair.
    """
    declared_ids = {str(e["memory_id"]) for e in entries}
    for pair in gold["pairs"]:
        for rid in pair["relevant_memory_ids"]:
            if str(rid) not in declared_ids:
                raise ValueError(
                    f"pair {pair['id']}: relevant memory {rid} is not declared "
                    "by the corpus"
                )


async def seed_memory_rows(session_factory, entries: list[dict]) -> list[dict]:
    """Create the base ``memories`` rows with the corpus-declared fixed ids
    and ``created_at``, and return process_batch-ready entries.

    ``run_ingest`` passes entries that already carry a ``memory_id`` through
    untouched, assuming the row exists; this is the creation step that makes
    that assumption true for a fixed-id corpus. Call it against a freshly
    reset bench DB -- re-seeding without a reset fails loudly on the primary
    key rather than silently duplicating or updating.

    ``created_at`` is set attribute-side before the commit, exactly as
    ingest._create_memory_rows does for its own creation path, so the row
    carries the declared date instead of the server stamp.
    """
    from app.models.memory import Memory

    prepared: list[dict] = []
    async with session_factory() as session:
        for entry in entries:
            memory = Memory(
                id=uuid.UUID(str(entry["memory_id"])),
                content=entry["content"],
                source=entry.get("source", "bench"),
                memory_type=entry.get("memory_type"),
                importance=entry.get("importance", 0.5),
                metadata_=entry.get("metadata", {}),
                project=entry.get("project", "default"),
            )
            created = datetime.fromisoformat(entry["created_at"])
            if created.tzinfo is None:
                created = created.replace(tzinfo=timezone.utc)
            memory.created_at = created
            session.add(memory)
            prepared.append({
                "memory_id": memory.id,
                "content": memory.content,
                "source": memory.source,
                "tags": [],
                "memory_type": memory.memory_type,
                "created_at": created.isoformat(),
            })
        await session.commit()
    return prepared
