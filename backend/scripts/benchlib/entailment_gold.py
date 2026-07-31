"""Entailment gold set: loader and validation (claim/fact variant, doc 17 §6).

The gold lives as one JSON file, ``entailment/gold.json`` -- labelled
``(premise, hypothesis, verdict)`` pairs in the *claim/fact* variant: the
premise is a Layer-2-style fact text and the hypothesis is an article-style
claim sentence. This is what G-D's judge qualification (T2.26) measures
against, so the file exists before the judge and is never tuned to one.
The claim/span variant (doc 16 §4, horizon) is a future sibling file, not
this one.

Verdicts are three-way. The primary binary ground truth G-D needs --
grounded vs ungrounded -- is derived, never stored separately:
``grounded == (verdict in GROUNDED_VERDICTS)``, i.e. exactly ``entailed``.
The finer split of ungrounded into ``contradicted`` / ``unsupported`` is
load-bearing for the veto consumer (doc 08 §4.2): T2.26 qualifies
precision on the contradiction verdict from the same file.

Slices are a closed set of eight, and each slice constrains which verdicts
its live pairs may carry (``SLICE_VERDICTS``) -- a ``value-swap`` pair
labelled ``entailed`` is a labelling error the loader refuses, not a
judgement call. Slice definitions, the decision procedures, and the edge
rulings (exclusive-slot, open-window, implicature-is-not-contradiction,
evaluation-time, reversal-exclusivity) live in ``entailment/LABELLING.md``.
Label against that file, not from memory of what a slice name suggests.

Provenance is a closed vocabulary declared per pair and counted at the top
level, because G-D's numbers inherit any overstatement of where a pair came
from. ``synthesis-draft`` and ``l2-fact`` are reserved values with no
producer yet (T3.02 and T2.10 respectively); the current file must carry
zero of each, pinned by test, so the first real harvest from either source
is a visible diff, never a silent relabel.

File discipline mirrors the retrieval gold (doc 17 §11): append-only,
ascending ``eg-`` ids, wrong pairs retired in place with ``"retired": true``
-- never deleted, rewritten, or reordered. Declared counts track live pairs
only and move with every append, visibly.
"""
from __future__ import annotations

import json
from pathlib import Path

ENTAILMENT_DIR = Path(__file__).resolve().parent / "entailment"
GOLD_PATH = ENTAILMENT_DIR / "gold.json"

VARIANT = "claim-fact"

VERDICTS = frozenset({"entailed", "contradicted", "unsupported"})

# The grounded/ungrounded binary G-D scores on. Kept here so T2.26 reads
# the mapping instead of re-deriving it: precision on "entailed" is the
# truth-critical number (doc 17 §6), and widening this set would silently
# reclassify ungrounded gold as grounded.
GROUNDED_VERDICTS = frozenset({"entailed"})

GROUNDED_SLICES = frozenset({"verbatim", "paraphrase", "weakening"})
MIXED_SLICES = frozenset({"temporal"})
UNGROUNDED_SLICES = frozenset({"direction", "overreach", "value-swap", "unrelated"})
SLICES = GROUNDED_SLICES | MIXED_SLICES | UNGROUNDED_SLICES

# Slice -> verdicts a live pair may carry. This is the labelling-consistency
# guard: each slice is defined by its construction (LABELLING.md), and a
# verdict outside its set means the pair was mis-sliced or mislabelled.
SLICE_VERDICTS: dict[str, frozenset[str]] = {
    "verbatim": frozenset({"entailed"}),
    "paraphrase": frozenset({"entailed"}),
    "weakening": frozenset({"entailed"}),
    "temporal": VERDICTS,
    "direction": frozenset({"contradicted", "unsupported"}),
    "overreach": frozenset({"contradicted", "unsupported"}),
    "value-swap": frozenset({"contradicted"}),
    "unrelated": frozenset({"unsupported"}),
}

# The slices whose pairs are hard near-misses -- high surface overlap with
# the opposite verdict's territory. These decide whether G-D's number means
# anything: a judge qualified only on verbatim/paraphrase/unrelated pairs
# will fail in production (doc 17 §6's "hard near-misses" requirement).
NEAR_MISS_SLICES = frozenset(
    {"weakening", "temporal", "direction", "overreach", "value-swap"}
)

# Where a pair's material actually came from. Honesty over volume: the two
# task-text sources (synthesis drafts, live L2 facts) have no producer as of
# T2.25 -- article_synthesis is a PlaceholderJobRunner until T3.02 and
# knowledge_triples has no writer until T2.10 -- so their values are
# reserved, accepted by this loader, and required to count zero today.
PROVENANCES = frozenset({
    "hand-authored-synthetic-fact",
    "hand-authored-bench-corpus",
    "synthesis-draft",
    "l2-fact",
})
CORPUS_PROVENANCES = frozenset({"hand-authored-bench-corpus"})

LABEL_SOURCES = frozenset({"author", "adjudicated"})


def is_grounded(pair: dict) -> bool:
    """The binary ground truth for a pair: grounded iff its verdict is in
    ``GROUNDED_VERDICTS``."""
    return pair["verdict"] in GROUNDED_VERDICTS


def load_entailment_gold(path: str | Path = GOLD_PATH) -> dict:
    """Load and structurally validate the entailment gold file.

    Returns the parsed document (``version``, ``variant``,
    ``declared_slice_counts``, ``declared_verdict_counts``,
    ``declared_provenance_counts``, ``pairs``). The cross-file check that
    corpus-derived premises still match the retrieval corpus belongs to
    ``validate_gold_against_corpus``.

    Raises:
        ValueError: On any shape violation -- a wrong variant, an untabled
            verdict, slice, provenance or label source, a live pair whose
            verdict falls outside its slice's allowed set, a corpus-derived
            pair without its ``corpus_key`` (or a non-corpus pair carrying
            one), a live pair without a labelling rationale, duplicate or
            out-of-order pair ids, a duplicate live (premise, hypothesis)
            pair, or declared counts that disagree with the live pairs.
    """
    path = Path(path)
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)

    if data.get("variant") != VARIANT:
        raise ValueError(
            f"gold {path}: variant must be {VARIANT!r}, got "
            f"{data.get('variant')!r} -- the claim/span variant is a "
            "separate file, never mixed into this one"
        )

    pairs = data.get("pairs")
    if not isinstance(pairs, list) or not pairs:
        raise ValueError(f"gold {path}: 'pairs' must be a non-empty list")

    declared_specs = (
        ("declared_slice_counts", SLICES),
        ("declared_verdict_counts", VERDICTS),
        ("declared_provenance_counts", PROVENANCES),
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
    seen_live_texts: set[tuple[str, str]] = set()
    computed_slices: dict[str, int] = {s: 0 for s in SLICES}
    computed_verdicts: dict[str, int] = {v: 0 for v in VERDICTS}
    computed_provenances: dict[str, int] = {p: 0 for p in PROVENANCES}

    for idx, pair in enumerate(pairs):
        pid = pair.get("id")
        if not isinstance(pid, str) or not pid:
            raise ValueError(f"pair {idx}: missing non-empty 'id'")
        seen_pair_ids.append(pid)

        for field in ("premise", "hypothesis"):
            value = pair.get(field)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"pair {pid}: missing non-empty {field!r}")

        verdict = pair.get("verdict")
        if verdict not in VERDICTS:
            raise ValueError(
                f"pair {pid}: verdict must be one of {sorted(VERDICTS)}, "
                f"got {verdict!r}"
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

        provenance = pair.get("provenance")
        if provenance not in PROVENANCES:
            raise ValueError(
                f"pair {pid}: provenance must be one of "
                f"{sorted(PROVENANCES)}, got {provenance!r} -- a pair whose "
                "origin cannot be stated honestly does not enter the file"
            )

        label_source = pair.get("label_source")
        if label_source not in LABEL_SOURCES:
            raise ValueError(
                f"pair {pid}: label_source must be one of "
                f"{sorted(LABEL_SOURCES)}, got {label_source!r}"
            )

        if pair.get("retired"):
            continue

        if verdict not in SLICE_VERDICTS[tag]:
            raise ValueError(
                f"pair {pid}: verdict {verdict!r} is not lawful for slice "
                f"{tag!r} (allowed: {sorted(SLICE_VERDICTS[tag])}) -- the "
                "pair is mis-sliced or mislabelled; see LABELLING.md"
            )

        if pair["premise"].strip() == pair["hypothesis"].strip():
            raise ValueError(
                f"pair {pid}: premise and hypothesis are identical -- a "
                "string-equality pair qualifies string comparison, not a "
                "judge; verbatim pairs must at least reorder (LABELLING.md)"
            )

        rationale = pair.get("rationale")
        if not isinstance(rationale, str) or not rationale.strip():
            raise ValueError(
                f"pair {pid}: a live pair must record its labelling "
                "'rationale' -- the per-pair half of the recorded-rationale "
                "requirement (T2.25 Done-when)"
            )

        corpus_key = pair.get("corpus_key")
        if provenance in CORPUS_PROVENANCES:
            if not isinstance(corpus_key, str) or not corpus_key:
                raise ValueError(
                    f"pair {pid}: provenance {provenance!r} requires "
                    "'corpus_key' naming the retrieval corpus entry the "
                    "premise came from"
                )
        elif corpus_key is not None:
            raise ValueError(
                f"pair {pid}: 'corpus_key' is only lawful under a corpus "
                f"provenance ({sorted(CORPUS_PROVENANCES)}); {provenance!r} "
                "pairs must not carry one"
            )

        texts = (pair["premise"].strip(), pair["hypothesis"].strip())
        if texts in seen_live_texts:
            raise ValueError(
                f"pair {pid}: duplicate live (premise, hypothesis) pair"
            )
        seen_live_texts.add(texts)

        computed_slices[tag] += 1
        computed_verdicts[verdict] += 1
        computed_provenances[provenance] += 1

    if len(set(seen_pair_ids)) != len(seen_pair_ids):
        raise ValueError(f"gold {path}: duplicate pair ids")
    if seen_pair_ids != sorted(seen_pair_ids):
        raise ValueError(
            f"gold {path}: pair ids must be in ascending order -- append "
            "new pairs at the end, retire wrong ones in place, never reorder"
        )

    computed_by_key = {
        "declared_slice_counts": computed_slices,
        "declared_verdict_counts": computed_verdicts,
        "declared_provenance_counts": computed_provenances,
    }
    for key, computed in computed_by_key.items():
        if data[key] != computed:
            raise ValueError(
                f"gold {path}: {key} disagree with the live (non-retired) "
                f"pairs: declared={data[key]} computed={computed}"
            )

    return data


def validate_gold_against_corpus(gold: dict, entries: list[dict]) -> None:
    """Cross-file validation of corpus-derived pairs against the retrieval
    corpus (``benchlib/retrieval/corpus.json``).

    A ``hand-authored-bench-corpus`` pair's premise is the named corpus
    entry's content **verbatim** -- that is what makes the provenance claim
    checkable rather than asserted. So a live pair whose ``corpus_key`` no
    longer resolves, or whose premise no longer equals that entry's content,
    fails here: the corpus moved under the pair, and the pair must be
    re-adjudicated under retire-and-replace instead of silently drifting
    away from its declared origin.

    Raises:
        ValueError: Naming the offending pair and why.
    """
    by_key = {e["key"]: e for e in entries if e.get("key")}
    for pair in gold["pairs"]:
        if pair.get("retired"):
            continue
        if pair.get("provenance") not in CORPUS_PROVENANCES:
            continue
        key = pair["corpus_key"]
        entry = by_key.get(key)
        if entry is None:
            raise ValueError(
                f"pair {pair['id']}: corpus_key {key!r} does not resolve to "
                "a retrieval corpus entry -- re-adjudicate under "
                "retire-and-replace"
            )
        if pair["premise"] != entry["content"]:
            raise ValueError(
                f"pair {pair['id']}: premise no longer equals corpus entry "
                f"{key!r}'s content -- the corpus moved under the pair; "
                "re-adjudicate under retire-and-replace"
            )
