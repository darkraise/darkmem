"""Contradiction-pair gold: loader and validation (doc 17 §5.2, T2.57).

The gold lives as one JSON file, ``contradiction/gold.json`` -- labelled
*pairs of Layer-2 facts* that do and do not contradict. It is what T2.52's
miss-rate runner measures the combined candidate generator (same-endpoint +
``pg_trgm``, doc 08 §5.3) against, and its labels carry doc 08 §4.2's
**veto-grade** semantics: ``contradiction`` means the pair would justify the
absolute veto -- genuinely opposed content, over an overlapping validity
window, asserted by independent origins. Anything failing any one of those
three conjuncts is ``not-contradiction``, and each negative slice isolates
exactly one failing conjunct so a mislabel is attributable.

**Every side is materializable as a real ``knowledge_triples`` row, by
construction.** The generator under measurement is SQL over the fact table,
so a gold of free-text "facts" the production renderer cannot mint would
measure a distribution the table will never contain. The loader therefore
binds every side to the shipping machinery by import, never by
re-implementation: ``fact`` must equal ``fact_sentence(subject, rel,
object)``, names must be in ``compute_triple_key``'s canonical form,
``rel_type`` must be in the closed ``RELATIONSHIP_TYPES`` vocabulary, and
window overlap is decided by the *imported* ``windows_overlap`` from
``app.services.contradiction_veto`` -- the exact function the shipped veto
uses, so the gold's window semantics can never drift from the code's.

**Labels are structurally cross-checked where machine-checkable.** Each
slice constrains its lawful label (``SLICE_LABELS``) *and* carries
structural preconditions the loader enforces -- an ``echo`` pair whose
origin sets differ, or a ``non-overlap`` pair whose windows overlap, is a
labelling error the loader refuses, not a judgement call. What remains
human -- whether content genuinely opposes -- is recorded per pair in
``rationale`` against ``contradiction/LABELLING.md``'s named rules, so a
later reader re-adjudicates instead of re-guessing.

**Provenance is per side**, because a contradiction pair is almost never
two real facts: a coherent corpus does not mint opposing rows, so real
material enters one side at a time. An ``l2-fact`` side reuses the
entailment gold's anchor contract verbatim (same manifest, same
``fact_key`` fields, same byte-equal binding, manifest row as source of
truth); ``real-dispute`` is reserved at zero until the production
contradiction scan produces its first adjudicated dispute (doc 17 §5.2's
growth path). Origins and windows are gold-fixture dimensions the manifest
does not model; an anchored side must keep the open-ended window the
harvest actually minted (``fact_lift``'s one-reachable-branch finding).

File discipline mirrors the entailment gold (doc 17 §11): append-only,
ascending ``cg-`` ids, wrong pairs retired in place with ``"retired":
true`` -- never deleted, rewritten, or reordered. Declared counts track
live pairs only and move with every append, visibly.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from app.services.contradiction_veto import windows_overlap
from app.services.fact_lift import fact_sentence
from app.services.triple_key import compute_triple_key
from app.taxonomy import RELATIONSHIP_TYPES

from benchlib.entailment_gold import FACT_KEY_FIELDS, HARVEST_PATH, load_l2_harvest

CONTRADICTION_DIR = Path(__file__).resolve().parent / "contradiction"
GOLD_PATH = CONTRADICTION_DIR / "gold.json"

VARIANT = "fact-pair"

LABEL_CONTRADICTION = "contradiction"
LABEL_NOT_CONTRADICTION = "not-contradiction"
LABELS = frozenset({LABEL_CONTRADICTION, LABEL_NOT_CONTRADICTION})

# The two positive slices split the recall measurement: same-endpoint pairs
# are what the generator's index-lookup arm must catch; lexically-disjoint
# pairs are the trigram shortlist's designed blind spot, and the miss rate
# on that slice alone is what triggers the triple_embeddings writer
# (doc 17 §5.2's `contradiction_missrate_bar`).
CONTRADICTION_SLICES = frozenset({"same-endpoint", "lexically-disjoint"})

# Each negative slice isolates one reason a would-be contradiction is not
# veto-grade -- disjoint windows (succession), a non-independent origin
# (echo), no opposition despite surface similarity, or a multi-valued slot
# where both facts stand. The false-positive side is where the veto's
# absoluteness makes a gold error most expensive (LABELLING.md).
NOT_CONTRADICTION_SLICES = frozenset({
    "non-overlap", "echo", "similar-unrelated", "compatible-same-endpoint",
})
SLICES = CONTRADICTION_SLICES | NOT_CONTRADICTION_SLICES

SLICE_LABELS: dict[str, str] = {
    "same-endpoint": LABEL_CONTRADICTION,
    "lexically-disjoint": LABEL_CONTRADICTION,
    "non-overlap": LABEL_NOT_CONTRADICTION,
    "echo": LABEL_NOT_CONTRADICTION,
    "similar-unrelated": LABEL_NOT_CONTRADICTION,
    "compatible-same-endpoint": LABEL_NOT_CONTRADICTION,
}

SIDE_PROVENANCES = frozenset({
    "hand-authored-synthetic-fact",
    "l2-fact",
    "real-dispute",
})
L2_PROVENANCE = "l2-fact"

SIDE_KEYS = ("a", "b")
_SIDE_REQUIRED_STRINGS = ("subject_name", "rel_type", "object_name", "fact", "project")
_SIDE_FIELDS = frozenset((
    *_SIDE_REQUIRED_STRINGS, "valid_at", "invalid_at", "origin_keys",
    "provenance", "fact_key",
))

LABEL_SOURCES = frozenset({"author", "adjudicated"})


def _canonical(name: str) -> str:
    # compute_triple_key's canonicalisation, restated for the per-field
    # check; the loader additionally verifies the whole-triple identity
    # through the imported function, so a drift here cannot pass silently.
    return " ".join(name.strip().split()).lower()


def endpoint_names(side: dict) -> frozenset[str]:
    return frozenset({side["subject_name"], side["object_name"]})


def name_tokens(side: dict) -> frozenset[str]:
    return frozenset(side["subject_name"].split()) | frozenset(
        side["object_name"].split()
    )


def is_contradiction(pair: dict) -> bool:
    return pair["label"] == LABEL_CONTRADICTION


@dataclass(frozen=True)
class _SideView:
    valid_at: datetime | None
    invalid_at: datetime | None
    origins: frozenset[str]


def _parse_window(pair_id: str, side_key: str, side: dict, field: str) -> datetime | None:
    value = side.get(field)
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError(
            f"pair {pair_id} side {side_key}: {field} must be null or an "
            f"ISO-8601 string, got {value!r}"
        )
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(
            f"pair {pair_id} side {side_key}: {field} {value!r} is not "
            f"ISO-8601: {exc}"
        ) from None
    if parsed.tzinfo is None:
        raise ValueError(
            f"pair {pair_id} side {side_key}: {field} {value!r} is naive -- "
            "knowledge_triples windows are timestamptz, and a naive bound "
            "would crash the imported windows_overlap against aware ones"
        )
    return parsed


def _validate_side(
    pair_id: str, side_key: str, side: dict, manifest_by_key: dict
) -> _SideView:
    if not isinstance(side, dict) or not set(side) <= _SIDE_FIELDS:
        raise ValueError(
            f"pair {pair_id} side {side_key}: sides carry only the fields "
            f"{sorted(_SIDE_FIELDS)}"
        )
    for field in _SIDE_REQUIRED_STRINGS:
        value = side.get(field)
        if not isinstance(value, str) or not value.strip():
            raise ValueError(
                f"pair {pair_id} side {side_key}: missing non-empty {field!r}"
            )
    for field in ("valid_at", "invalid_at"):
        if field not in side:
            raise ValueError(
                f"pair {pair_id} side {side_key}: {field} must be present "
                "(null for an open bound) -- window state is load-bearing "
                "and may not be implicit"
            )

    if side["rel_type"] not in RELATIONSHIP_TYPES:
        raise ValueError(
            f"pair {pair_id} side {side_key}: rel_type {side['rel_type']!r} "
            "is not in the closed RELATIONSHIP_TYPES vocabulary -- "
            "knowledge_triples stores nothing else, so the generator can "
            "never meet this side"
        )
    for field in ("subject_name", "object_name"):
        if side[field] != _canonical(side[field]):
            raise ValueError(
                f"pair {pair_id} side {side_key}: {field} {side[field]!r} is "
                "not in canonical form -- fact_lift writes canonical "
                "lowercase names, so a cased side is a row the layer never "
                "mints"
            )
    rendered = fact_sentence(
        side["subject_name"], side["rel_type"], side["object_name"]
    )
    if side["fact"] != rendered:
        raise ValueError(
            f"pair {pair_id} side {side_key}: fact {side['fact']!r} is not "
            f"the shipping fact_sentence rendering {rendered!r} -- the "
            "trigram arm runs over fact texts the renderer minted, and a "
            "free-text side would measure a distribution the table cannot "
            "contain"
        )

    valid_at = _parse_window(pair_id, side_key, side, "valid_at")
    invalid_at = _parse_window(pair_id, side_key, side, "invalid_at")
    if valid_at is not None and invalid_at is not None and valid_at >= invalid_at:
        raise ValueError(
            f"pair {pair_id} side {side_key}: valid_at must precede "
            "invalid_at -- the window is half-open [valid_at, invalid_at)"
        )

    origins = side.get("origin_keys")
    if (
        not isinstance(origins, list)
        or not origins
        or not all(isinstance(o, str) and o.strip() for o in origins)
        or len(set(origins)) != len(origins)
    ):
        raise ValueError(
            f"pair {pair_id} side {side_key}: origin_keys must be a "
            "non-empty list of distinct non-empty strings -- the echo test "
            "is decided on origin identity, so a side without one is "
            "unadjudicable"
        )

    provenance = side.get("provenance")
    if provenance not in SIDE_PROVENANCES:
        raise ValueError(
            f"pair {pair_id} side {side_key}: provenance must be one of "
            f"{sorted(SIDE_PROVENANCES)}, got {provenance!r} -- a side whose "
            "origin cannot be stated honestly does not enter the file"
        )
    fact_key = side.get("fact_key")
    if provenance == L2_PROVENANCE:
        if not isinstance(fact_key, dict) or set(fact_key) != set(FACT_KEY_FIELDS):
            raise ValueError(
                f"pair {pair_id} side {side_key}: provenance "
                f"{L2_PROVENANCE!r} requires a 'fact_key' object with "
                f"exactly the fields {sorted(FACT_KEY_FIELDS)}"
            )
        row = manifest_by_key.get(fact_key["triple_key"])
        if row is None:
            raise ValueError(
                f"pair {pair_id} side {side_key}: fact_key.triple_key "
                f"{fact_key['triple_key']!r} does not resolve to a harvest "
                "manifest row -- re-adjudicate under retire-and-replace"
            )
        # Field equality against the manifest row, combined with the
        # renderer binding above and the manifest's own self-consistency
        # check, is what makes the side's fact byte-equal to the minted
        # text -- no separate byte comparison is needed or possible to
        # fail independently.
        for field in ("subject_name", "rel_type", "object_name", "project"):
            if fact_key[field] != row[field] or side[field] != row[field]:
                raise ValueError(
                    f"pair {pair_id} side {side_key}: {field} disagrees with "
                    "the manifest row -- the manifest row is the source of "
                    "truth; the side never self-supplies the authoritative "
                    "values"
                )
        if valid_at is not None or invalid_at is not None:
            raise ValueError(
                f"pair {pair_id} side {side_key}: an {L2_PROVENANCE!r} side "
                "must keep the open-ended window the harvest minted -- "
                "fact_lift renders every lifted row open (the "
                "one-reachable-branch finding), so a bounded anchored side "
                "is a row the recorded run never produced"
            )
    elif fact_key is not None:
        raise ValueError(
            f"pair {pair_id} side {side_key}: 'fact_key' is only lawful "
            f"under provenance {L2_PROVENANCE!r}"
        )

    return _SideView(
        valid_at=valid_at,
        invalid_at=invalid_at,
        origins=frozenset(origins),
    )


def pair_windows_overlap(pair: dict) -> bool:
    """The pair's window relation, through the imported shipped predicate."""

    def bound(side: dict, field: str) -> datetime | None:
        value = side[field]
        return None if value is None else datetime.fromisoformat(value)

    a, b = pair["a"], pair["b"]
    return windows_overlap(
        bound(a, "valid_at"), bound(a, "invalid_at"),
        bound(b, "valid_at"), bound(b, "invalid_at"),
    )


def _check_slice_structure(
    pair_id: str, tag: str, pair: dict, a: _SideView, b: _SideView
) -> None:
    shared_names = endpoint_names(pair["a"]) & endpoint_names(pair["b"])
    shared_tokens = name_tokens(pair["a"]) & name_tokens(pair["b"])
    overlap = windows_overlap(a.valid_at, a.invalid_at, b.valid_at, b.invalid_at)
    origins_shared = a.origins & b.origins
    origins_equal = a.origins == b.origins

    def refuse(precondition: str) -> None:
        raise ValueError(
            f"pair {pair_id}: slice {tag!r} requires {precondition} -- the "
            "pair is mis-sliced or mislabelled; see LABELLING.md"
        )

    if tag in CONTRADICTION_SLICES or tag in {
        "non-overlap", "similar-unrelated", "compatible-same-endpoint"
    }:
        if origins_shared:
            refuse(
                "disjoint origin_keys (independent witnesses; an echo-shaped "
                "origin structure belongs to the echo slice)"
            )
    if tag != "non-overlap" and not overlap:
        refuse("overlapping validity windows")

    if tag == "same-endpoint":
        if not shared_names:
            refuse("a shared endpoint name")
    elif tag == "lexically-disjoint":
        if shared_tokens:
            refuse(
                f"token-disjoint endpoint names (shared: {sorted(shared_tokens)})"
            )
    elif tag == "non-overlap":
        if overlap:
            refuse("disjoint validity windows (windows_overlap must be False)")
        if not shared_names:
            refuse(
                "a shared endpoint name (the slice tests the overlap filter "
                "on pairs the generator would otherwise surface)"
            )
    elif tag == "echo":
        if not origins_equal:
            refuse(
                "equal origin_keys sets (no direction has a fresh witness, "
                "which is what makes the pair an echo)"
            )
        if not shared_names:
            refuse("a shared endpoint name")
    elif tag == "similar-unrelated":
        if not shared_tokens:
            refuse("at least one shared endpoint-name token")
        if shared_names:
            refuse(
                "no shared full endpoint name (full-name sharing belongs to "
                "compatible-same-endpoint)"
            )
    elif tag == "compatible-same-endpoint":
        if not shared_names:
            refuse("a shared endpoint name")


def load_contradiction_gold(
    path: str | Path = GOLD_PATH,
    harvest_path: str | Path = HARVEST_PATH,
) -> dict:
    """Load and structurally validate the contradiction-pair gold file.

    Returns the parsed document (``version``, ``variant``,
    ``declared_slice_counts``, ``declared_label_counts``,
    ``declared_side_provenance_counts``, ``pairs``). Side-provenance counts
    count *sides* (two per live pair), because provenance is a per-side
    property here.

    Raises:
        ValueError: On any shape violation -- a wrong variant; an untabled
            label, slice, side provenance or label source; a label unlawful
            for its slice; a side whose fact is not the shipping
            ``fact_sentence`` rendering, whose names are not canonical,
            whose ``rel_type`` is untabled, whose windows are malformed or
            naive, or whose ``l2-fact`` anchor fails the manifest binding;
            sides in different projects; sides sharing one ``triple_key``;
            a slice structural precondition violated; a live pair without a
            rationale; duplicate or out-of-order ids; a duplicate live pair
            (unordered); or declared counts that disagree with the live
            pairs.
    """
    path = Path(path)
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)

    # Once per load, unconditionally: the manifest self-consistency check is
    # also the fact_sentence-rendering tripwire (see entailment_gold).
    manifest = load_l2_harvest(harvest_path)
    manifest_by_key = {row["triple_key"]: row for row in manifest["facts"]}

    if data.get("variant") != VARIANT:
        raise ValueError(
            f"gold {path}: variant must be {VARIANT!r}, got "
            f"{data.get('variant')!r}"
        )

    pairs = data.get("pairs")
    if not isinstance(pairs, list) or not pairs:
        raise ValueError(f"gold {path}: 'pairs' must be a non-empty list")

    declared_specs = (
        ("declared_slice_counts", SLICES),
        ("declared_label_counts", LABELS),
        ("declared_side_provenance_counts", SIDE_PROVENANCES),
    )
    for key, vocabulary in declared_specs:
        declared = data.get(key)
        if not isinstance(declared, dict) or set(declared) != vocabulary:
            raise ValueError(
                f"gold {path}: {key} must carry exactly the keys "
                f"{sorted(vocabulary)}; got "
                f"{sorted(declared) if isinstance(declared, dict) else declared!r}"
            )

    seen_pair_ids: list[str] = []
    seen_live_texts: set[frozenset[str]] = set()
    computed_slices: dict[str, int] = {s: 0 for s in SLICES}
    computed_labels: dict[str, int] = {v: 0 for v in LABELS}
    computed_provenances: dict[str, int] = {p: 0 for p in SIDE_PROVENANCES}

    for idx, pair in enumerate(pairs):
        pid = pair.get("id")
        if not isinstance(pid, str) or not pid:
            raise ValueError(f"pair {idx}: missing non-empty 'id'")
        seen_pair_ids.append(pid)

        label = pair.get("label")
        if label not in LABELS:
            raise ValueError(
                f"pair {pid}: label must be one of {sorted(LABELS)}, got "
                f"{label!r}"
            )

        tags = pair.get("slice_tags")
        if not isinstance(tags, list) or len(tags) != 1:
            raise ValueError(
                f"pair {pid}: slice_tags must carry exactly one tag "
                f"(the v1 discipline; see LABELLING.md), got {tags!r}"
            )
        tag = tags[0]
        if tag not in SLICES:
            raise ValueError(f"pair {pid}: untabled slice tag {tag!r}")

        label_source = pair.get("label_source")
        if label_source not in LABEL_SOURCES:
            raise ValueError(
                f"pair {pid}: label_source must be one of "
                f"{sorted(LABEL_SOURCES)}, got {label_source!r}"
            )

        if pair.get("retired"):
            continue

        if label != SLICE_LABELS[tag]:
            raise ValueError(
                f"pair {pid}: label {label!r} is not lawful for slice "
                f"{tag!r} (required: {SLICE_LABELS[tag]!r}) -- the pair is "
                "mis-sliced or mislabelled; see LABELLING.md"
            )

        rationale = pair.get("rationale")
        if not isinstance(rationale, str) or not rationale.strip():
            raise ValueError(
                f"pair {pid}: a live pair must record its labelling "
                "'rationale' so a later reader re-adjudicates instead of "
                "re-guessing (T2.57 Done-when)"
            )

        for side_key in SIDE_KEYS:
            if side_key not in pair:
                raise ValueError(f"pair {pid}: missing side {side_key!r}")
        a = _validate_side(pid, "a", pair["a"], manifest_by_key)
        b = _validate_side(pid, "b", pair["b"], manifest_by_key)

        if pair["a"]["project"] != pair["b"]["project"]:
            raise ValueError(
                f"pair {pid}: sides must share one project -- the generator "
                "scans within a project (doc 08 §5.3), and triple_key embeds "
                "project in fact identity, so a cross-project pair is "
                "outside the veto's universe"
            )

        keys = tuple(
            compute_triple_key(
                pair[s]["project"], pair[s]["subject_name"],
                pair[s]["rel_type"], pair[s]["object_name"],
            )
            for s in SIDE_KEYS
        )
        if keys[0] == keys[1]:
            raise ValueError(
                f"pair {pid}: both sides carry one triple_key -- fact_lift "
                "resolves them to the same open row, so the pair is one "
                "fact, not two, and cannot be materialized for the generator"
            )

        _check_slice_structure(pid, tag, pair, a, b)

        texts = frozenset({pair["a"]["fact"], pair["b"]["fact"]})
        if texts in seen_live_texts:
            raise ValueError(
                f"pair {pid}: duplicate live pair (unordered fact texts)"
            )
        seen_live_texts.add(texts)

        computed_slices[tag] += 1
        computed_labels[label] += 1
        for side_key in SIDE_KEYS:
            computed_provenances[pair[side_key]["provenance"]] += 1

    if len(set(seen_pair_ids)) != len(seen_pair_ids):
        raise ValueError(f"gold {path}: duplicate pair ids")
    if seen_pair_ids != sorted(seen_pair_ids):
        raise ValueError(
            f"gold {path}: pair ids must be in ascending order -- append "
            "new pairs at the end, retire wrong ones in place, never reorder"
        )

    computed_by_key = {
        "declared_slice_counts": computed_slices,
        "declared_label_counts": computed_labels,
        "declared_side_provenance_counts": computed_provenances,
    }
    for key, computed in computed_by_key.items():
        if data[key] != computed:
            raise ValueError(
                f"gold {path}: {key} disagree with the live (non-retired) "
                f"pairs: declared={data[key]} computed={computed}"
            )

    return data
