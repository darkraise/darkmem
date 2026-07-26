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
from datetime import datetime
from pathlib import Path

from benchlib.corpus import load_corpus

RETRIEVAL_DIR = Path(__file__).resolve().parent / "retrieval"
CORPUS_PATH = RETRIEVAL_DIR / "corpus.json"
GOLD_PATH = RETRIEVAL_DIR / "gold.json"

QUERY_TYPE_SLICES = frozenset({"exact", "paraphrase", "typo", "fact"})
CAPABILITY_SLICES = frozenset({"multi-hop", "temporal", "knowledge-update"})
SLICES = QUERY_TYPE_SLICES | CAPABILITY_SLICES

# The multi-hop saturation bar (SLICES.md, multi-hop): a live pair must
# record the consequence memory's measured hybrid-only baseline rank over
# the full corpus, and that rank must be WORSE than this K -- the k=10
# reporting cutoff the baseline is scored at. A pair whose consequence
# memory already ranks at or inside K is reachable by the semantic channel
# without the hop, so it can never demonstrate graph-arm headroom.
MULTI_HOP_BASELINE_K = 10

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
    group_dates: dict[str, set[str]] = {}
    group_sizes: dict[str, int] = {}
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

        group = entry.get("group")
        if group is not None:
            if not isinstance(group, str) or not group:
                raise ValueError(f"entry {idx}: 'group' must be a non-empty string")
            if raw_created in group_dates.setdefault(group, set()):
                raise ValueError(
                    f"entry {idx}: group {group!r} has two members with "
                    f"created_at {raw_created} -- 'newest' would be ill-defined"
                )
            group_dates[group].add(raw_created)
            group_sizes[group] = group_sizes.get(group, 0) + 1
        speculative = entry.get("speculative")
        if speculative is not None and not isinstance(speculative, bool):
            raise ValueError(f"entry {idx}: 'speculative' must be a boolean")

    lone = sorted(g for g, n in group_sizes.items() if n < 2)
    if lone:
        raise ValueError(
            f"group(s) {lone} have a single member; temporal and update groups "
            "exist to hold siblings"
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
            old pairs are retired in place, never reordered), declared
            per-slice counts that disagree with the live pairs, or a live
            multi-hop pair that fails the saturation bar (missing
            ``consequence_memory_id`` / ``baseline_consequence_rank``, or a
            recorded rank at or inside ``MULTI_HOP_BASELINE_K``).
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

        if tag == "multi-hop" and not pair.get("retired"):
            consequence = pair.get("consequence_memory_id")
            if consequence is None or str(consequence) not in {
                str(rid) for rid in relevant
            }:
                raise ValueError(
                    f"pair {pid}: a live multi-hop pair must name its "
                    "consequence memory via 'consequence_memory_id', one of "
                    "its relevant_memory_ids (SLICES.md, multi-hop)"
                )
            if "baseline_consequence_rank" not in pair:
                raise ValueError(
                    f"pair {pid}: a live multi-hop pair must record "
                    "'baseline_consequence_rank' -- the consequence memory's "
                    "measured hybrid-only baseline rank over the full corpus, "
                    "or null if it was not retrieved (SLICES.md, multi-hop)"
                )
            rank = pair["baseline_consequence_rank"]
            if rank is not None and (
                not isinstance(rank, int) or isinstance(rank, bool) or rank < 1
            ):
                raise ValueError(
                    f"pair {pid}: baseline_consequence_rank must be a "
                    f"positive integer or null, got {rank!r}"
                )
            if rank is not None and rank <= MULTI_HOP_BASELINE_K:
                raise ValueError(
                    f"pair {pid}: saturated -- baseline_consequence_rank "
                    f"{rank} is not worse than MULTI_HOP_BASELINE_K="
                    f"{MULTI_HOP_BASELINE_K}, so the hybrid-only baseline "
                    "already reaches the consequence memory without the hop; "
                    "re-adjudicate under retire-and-replace (SLICES.md, "
                    "multi-hop)"
                )

        anchor = pair.get("anchor")
        if anchor is not None and anchor not in ("current", "whole-group"):
            raise ValueError(f"pair {pid}: unknown anchor {anchor!r}")

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
    """Cross-file validation of the gold pairs against the corpus.

    Two duties. First, every ``relevant_memory_ids`` entry must resolve to a
    memory the corpus actually declares -- gold pointing at ids the seeded
    bench DB will never contain is gold nobody can score against. Second,
    anchored pairs must still hold against the group state they were
    adjudicated under: a pair whose gold is "the current truth" or "the whole
    story" goes stale the moment a newer sibling is appended to its corpus
    group, so appending a t2d snapshot or a definitive u6c replacement must
    fail here -- forcing re-adjudication under retire-and-replace -- instead
    of silently marking the wrong memory relevant.

    Anchor semantics:
    - ``current``: every relevant memory that belongs to a group must be the
      newest non-speculative member of that group. Covers latest-anchored
      temporal pairs, definitive-update present-state pairs, and speculative
      traps in one rule (a speculative newest member does not displace the
      older truth).
    - ``whole-group``: the relevant set must equal one group's full
      membership (change-status queries -- any group growth changes the
      story and requires re-adjudication).

    Raises:
        ValueError: Naming the offending pair and why.
    """
    declared_ids = {str(e["memory_id"]) for e in entries}
    by_id = {str(e["memory_id"]): e for e in entries}
    groups: dict[str, list[dict]] = {}
    for entry in entries:
        group = entry.get("group")
        if group:
            groups.setdefault(group, []).append(entry)

    for pair in gold["pairs"]:
        for rid in pair["relevant_memory_ids"]:
            if str(rid) not in declared_ids:
                raise ValueError(
                    f"pair {pair['id']}: relevant memory {rid} is not declared "
                    "by the corpus"
                )
        if pair.get("retired"):
            continue

        anchor = pair.get("anchor")
        if anchor == "current":
            grouped = [
                by_id[str(rid)]
                for rid in pair["relevant_memory_ids"]
                if by_id[str(rid)].get("group")
            ]
            if not grouped:
                raise ValueError(
                    f"pair {pair['id']}: anchor 'current' is inert without at "
                    "least one relevant memory in a corpus group"
                )
            for entry in grouped:
                members = groups[entry["group"]]
                candidates = [m for m in members if not m.get("speculative")]
                newest = max(
                    candidates,
                    key=lambda m: datetime.fromisoformat(m["created_at"]),
                )
                if entry["memory_id"] != newest["memory_id"]:
                    raise ValueError(
                        f"pair {pair['id']}: anchor 'current' but "
                        f"{entry['key']} is no longer the newest "
                        f"non-speculative member of group {entry['group']!r} "
                        f"({newest['key']} is) -- re-adjudicate the pair under "
                        "retire-and-replace"
                    )
        elif anchor == "whole-group":
            relevant = {str(rid) for rid in pair["relevant_memory_ids"]}
            member_groups = {by_id[rid].get("group") for rid in relevant}
            if len(member_groups) != 1 or None in member_groups:
                raise ValueError(
                    f"pair {pair['id']}: anchor 'whole-group' needs every "
                    "relevant memory in one corpus group"
                )
            group = next(iter(member_groups))
            member_ids = {m["memory_id"] for m in groups[group]}
            if relevant != member_ids:
                raise ValueError(
                    f"pair {pair['id']}: anchor 'whole-group' but the relevant "
                    f"set no longer equals group {group!r}'s full membership "
                    "-- re-adjudicate the pair under retire-and-replace"
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
    from benchlib.ingest import _parse_created_at

    prepared: list[dict] = []
    async with session_factory() as session:
        for idx, entry in enumerate(entries):
            memory = Memory(
                id=uuid.UUID(str(entry["memory_id"])),
                content=entry["content"],
                source=entry.get("source", "bench"),
                memory_type=entry.get("memory_type"),
                importance=entry.get("importance", 0.5),
                metadata_=entry.get("metadata", {}),
                project=entry.get("project", "default"),
            )
            created = _parse_created_at(entry["created_at"], idx)
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
