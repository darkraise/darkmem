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
from. ``synthesis-draft`` stays reserved with no producer (T3.02).
``l2-fact`` has a producer since T2.54's recorded harvest: a pair claiming
it must carry a ``fact_key`` that resolves against the committed harvest
manifest (``entailment/l2_harvest.json``), with the manifest row as source
of truth -- the pair's key fields byte-equal the row's and the premise
byte-equals the row's minted ``fact`` text. The manifest itself is
validated once per load against the imported ``compute_triple_key`` and
``fact_sentence`` (parity-by-import, never re-implemented), which also
makes any future change to ``fact_sentence``'s rendering fail this loader
loudly -- that is the sunset tripwire for the temporal slice's
hand-authored-premise exemption (doc 17 §11). The byte-binding's
brittleness is deliberate: an id anchor would dangle silently after every
bench schema reset, and a recomputation from the pair's own fields would
accept cased premises ``fact_lift`` never produced, because
``compute_triple_key`` canonicalises names while ``fact_sentence``
lowercases only the predicate.

File discipline mirrors the retrieval gold (doc 17 §11): append-only,
ascending ``eg-`` ids, wrong pairs retired in place with ``"retired": true``
-- never deleted, rewritten, or reordered. Declared counts track live pairs
only and move with every append, visibly.
"""
from __future__ import annotations

import hashlib
from functools import lru_cache
import json
from pathlib import Path

from app.services.fact_lift import fact_sentence
from app.services.triple_key import compute_triple_key

ENTAILMENT_DIR = Path(__file__).resolve().parent / "entailment"
GOLD_PATH = ENTAILMENT_DIR / "gold.json"
HARVEST_PATH = ENTAILMENT_DIR / "l2_harvest.json"

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
L2_PROVENANCE = "l2-fact"

# The anchor object an l2-fact pair must carry, resolved against the harvest
# manifest by triple_key with the manifest row as source of truth.
FACT_KEY_FIELDS = (
    "triple_key", "subject_name", "rel_type", "object_name", "project",
)

# `owner` is a third provenance, not a synonym for `adjudicated` (T2.54 Step 6,
# 2026-08-06). `adjudicated` means two independent blind passes agreed with the
# recorded verdict; `owner` means the escalation reached Layer 3 and a human
# ruled. Collapsing them would tell T2.41 that a label carried blind-pass
# agreement it never had — and the gate must report its metrics per population.
LABEL_SOURCES = frozenset({"author", "adjudicated", "owner"})


# ── the certification's content basis (T2.116) ───────────────────────────
#
# A resample certifies a *label error rate*, and until T2.116 nothing tied
# that certification to the labels it saw: `gate_eligibility` checked that
# the block *said* n >= 93 with <= 1 disagreement and carried its citation
# fields, so a verdict flipped after the sitting left eligibility green on a
# certification of a different file. Three rounds handled it correctly by
# hand, which is the tell — the protocol already understood what no code
# enforced.
#
# The basis is deliberately NARROWER than the file sha, and that is the
# whole point of hashing pairs rather than bytes. The certified sha has
# differed from the on-disk sha in every round to date (58ac1a90 against
# 98fc4b49, most recently), always annotation-only, because rationales get
# rewritten and notes get added long after a sitting. Hashing the file would
# make that ordinary churn indistinguishable from a label flip and the
# refusal would fire constantly until someone learned to ignore it — a
# guard that cries wolf is worse than none, because it trains the response.
#
# So the basis is exactly the judged claim: which pair (`id`), what the
# judge was shown (`premise`, `hypothesis`), and what the gold says the
# answer is (`verdict`). Everything else is annotation or is separately
# pinned — `slice_tags` by the declared slice-count pin, `provenance` by
# the declared provenance counts and the harvest manifest, `label_source`
# by the author-label condition in this same lock.
#
# It covers the LIVE population only, which is the population the
# certification actually describes: a resample draws from live pairs, the
# lock counts live pairs, and nothing anywhere scores a retired one.
# Retirement still invalidates a certification — a retired pair leaves the
# live map and the refusal reports it as removed — but churn *within* the
# retired archive does not, because no number the gate reads can move with
# it. Hashing retired pairs too was tried first and is wrong in a way worth
# recording: appending an already-retired pair would have turned
# eligibility red for a change that touches nothing measured, and a guard
# that fires on immaterial edits is one people learn to re-stamp past.
CERTIFIED_PAIR_FIELDS = ("id", "premise", "hypothesis", "verdict")

_PAIR_DIGEST_CHARS = 12


def _canonical(obj: object) -> bytes:
    return json.dumps(
        obj, sort_keys=True, ensure_ascii=False, separators=(",", ":"),
    ).encode("utf-8")


def pair_digest(pair: dict) -> str:
    """Digest of one pair's judged content, over ``CERTIFIED_PAIR_FIELDS``."""
    basis = {field: pair.get(field) for field in CERTIFIED_PAIR_FIELDS}
    return hashlib.sha256(_canonical(basis)).hexdigest()[:_PAIR_DIGEST_CHARS]


def pair_digests(pairs: list[dict]) -> dict[str, str]:
    """``{pair id: digest}`` over the **live** pairs, retired ones excluded.

    Same liveness predicate the eligibility lock counts on, so the basis
    and the counts describe one population.
    """
    return {
        pair["id"]: pair_digest(pair)
        for pair in pairs
        if not pair.get("retired")
    }


def digest_map_hash(digests: dict[str, str]) -> str:
    """Fold a ``{id: digest}`` map into the one hash a block records.

    Public because the eligibility lock re-folds the map a block *stored*
    to check it derives the aggregate it stored beside it. One definition
    of that fold, or the check would be comparing two different rules and
    could disagree with the writer for reasons that are not drift.
    """
    return hashlib.sha256(_canonical(digests)).hexdigest()


def pairs_content_hash(pairs: list[dict]) -> str:
    """The single hash a ``resample`` block records, over the pairs alone.

    Derived from ``pair_digests`` rather than from the pairs directly, so
    the aggregate and the per-pair map a refusal reads to name *which*
    pairs moved can never disagree about what they cover.
    """
    return digest_map_hash(pair_digests(pairs))


def load_l2_harvest(path: str | Path = HARVEST_PATH) -> dict:
    """Load the harvest manifest and validate its self-consistency.

    Every row must satisfy, against the *imported* shipping functions:
    ``compute_triple_key(project, subject_name, rel_type, object_name) ==
    triple_key`` and ``fact_sentence(subject_name, rel_type, object_name) ==
    fact``. That pins the manifest to the shipping identity and rendering,
    so drift in either fails the floor loudly instead of letting anchored
    pairs verify against a rendering ``fact_lift`` no longer produces. Rows
    must be sorted by ``triple_key`` with no duplicates -- the sorted,
    timestamp-free ``facts`` section is what a re-harvest byte-diffs to
    detect a hand-written row (T2.41's --gate evidence re-runs that diff).

    Raises:
        ValueError: naming the offending row and the check it failed.
    """
    path = Path(path)
    with open(path, encoding="utf-8") as fh:
        manifest = json.load(fh)

    facts = manifest.get("facts")
    if not isinstance(facts, list):
        raise ValueError(f"harvest manifest {path}: 'facts' must be a list")

    keys: list[str] = []
    for idx, row in enumerate(facts):
        for field in (*FACT_KEY_FIELDS, "fact"):
            value = row.get(field)
            if not isinstance(value, str) or not value:
                raise ValueError(
                    f"harvest manifest {path}: row {idx} is missing a "
                    f"non-empty {field!r}"
                )
        recomputed = compute_triple_key(
            row["project"], row["subject_name"], row["rel_type"],
            row["object_name"],
        )
        if recomputed != row["triple_key"]:
            raise ValueError(
                f"harvest manifest {path}: row {idx} triple_key "
                f"{row['triple_key']!r} is not the shipping "
                f"compute_triple_key identity of its own fields "
                f"({recomputed!r}) -- the manifest must be re-harvested, "
                "never hand-edited"
            )
        rendered = fact_sentence(
            row["subject_name"], row["rel_type"], row["object_name"]
        )
        if rendered != row["fact"]:
            raise ValueError(
                f"harvest manifest {path}: row {idx} fact {row['fact']!r} is "
                f"not the shipping fact_sentence rendering of its own fields "
                f"({rendered!r}); if fact_sentence's rendering changed, every "
                "l2-fact pair must be re-adjudicated under retire-and-replace "
                "and the temporal exemption re-argued (doc 17 §11)"
            )
        keys.append(row["triple_key"])

    if keys != sorted(keys):
        raise ValueError(
            f"harvest manifest {path}: facts must be sorted by triple_key"
        )
    if len(set(keys)) != len(keys):
        raise ValueError(f"harvest manifest {path}: duplicate triple_key rows")

    return manifest


def is_grounded(pair: dict) -> bool:
    """The binary ground truth for a pair: grounded iff its verdict is in
    ``GROUNDED_VERDICTS``."""
    return pair["verdict"] in GROUNDED_VERDICTS


def load_entailment_gold(
    path: str | Path = GOLD_PATH,
    harvest_path: str | Path = HARVEST_PATH,
) -> dict:
    """Load and structurally validate the entailment gold file.

    Returns the parsed document (``version``, ``variant``,
    ``declared_slice_counts``, ``declared_verdict_counts``,
    ``declared_provenance_counts``, ``pairs``). The cross-file check that
    corpus-derived premises still match the retrieval corpus belongs to
    ``validate_gold_against_corpus``; the ``l2-fact`` anchor is validated
    *inline* here against the committed harvest manifest -- a deliberate
    asymmetry, because the manifest is this gold's own required sibling
    while the retrieval corpus belongs to another subsystem.

    Raises:
        ValueError: On any shape violation -- a wrong variant, an untabled
            verdict, slice, provenance or label source, a live pair whose
            verdict falls outside its slice's allowed set, a corpus-derived
            pair without its ``corpus_key`` (or a non-corpus pair carrying
            one), an ``l2-fact`` pair whose ``fact_key`` is missing, does
            not resolve in the manifest, disagrees with the manifest row's
            fields, or whose premise is not byte-equal to the row's minted
            ``fact`` (or a non-``l2-fact`` pair carrying a ``fact_key``),
            a live pair without a labelling rationale, duplicate or
            out-of-order pair ids, a duplicate live (premise, hypothesis)
            pair, or declared counts that disagree with the live pairs.
    """
    path = Path(path)
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)

    # Once per load, unconditionally: the manifest self-consistency check is
    # also the fact_sentence-rendering tripwire, so it must bite even while
    # the file holds zero l2-fact pairs.
    manifest = load_l2_harvest(harvest_path)
    manifest_by_key = {row["triple_key"]: row for row in manifest["facts"]}

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

        fact_key = pair.get("fact_key")
        if provenance == L2_PROVENANCE:
            if not isinstance(fact_key, dict) or set(fact_key) != set(FACT_KEY_FIELDS):
                raise ValueError(
                    f"pair {pid}: provenance {L2_PROVENANCE!r} requires a "
                    f"'fact_key' object with exactly the fields "
                    f"{sorted(FACT_KEY_FIELDS)} anchoring the premise to the "
                    "harvest manifest row that minted it"
                )
            row = manifest_by_key.get(fact_key["triple_key"])
            if row is None:
                raise ValueError(
                    f"pair {pid}: fact_key.triple_key "
                    f"{fact_key['triple_key']!r} does not resolve to a "
                    "harvest manifest row -- re-adjudicate under "
                    "retire-and-replace"
                )
            for field in ("subject_name", "rel_type", "object_name", "project"):
                if fact_key[field] != row[field]:
                    raise ValueError(
                        f"pair {pid}: fact_key.{field} {fact_key[field]!r} "
                        f"!= the manifest row's {row[field]!r} -- the "
                        "manifest row is the source of truth; the pair never "
                        "self-supplies the authoritative values"
                    )
            if pair["premise"] != row["fact"]:
                raise ValueError(
                    f"pair {pid}: premise is not byte-equal to the minted "
                    f"fact {row['fact']!r} -- an {L2_PROVENANCE!r} premise is "
                    "the knowledge_triples.fact text verbatim, never a "
                    "recomputation from the pair's own (possibly cased) "
                    "fields; re-adjudicate under retire-and-replace"
                )
        elif fact_key is not None:
            raise ValueError(
                f"pair {pid}: 'fact_key' is only lawful under provenance "
                f"{L2_PROVENANCE!r}; {provenance!r} pairs must not carry one"
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


RETIRED_DIGESTS_PATH = ENTAILMENT_DIR / "retired_pair_digests.json"

# D1's audit copy of the retired pair set. Loaded by no production code path:
# the digest file above is the refusal's reference, and this file exists so
# the pin can be audited against the pairs it was taken from after the
# canonical path holds a fresh gold.
RETIRED_GOLD_ARCHIVE_PATH = ENTAILMENT_DIR / "retired" / "gold-4975c5cc.json"

# Basis without the id, deliberately: the id is the one field a re-author
# controls freely, and this census has twice reproduced a retired pair's exact
# premise and hypothesis under a new id (eg-0367, eg-0404). Keying on content
# is what makes "retired" a property of the pair rather than of its label.
RETIRED_DIGEST_FIELDS = ("premise", "hypothesis", "verdict")


def content_digest(pair: dict) -> str:
    basis = {field: pair.get(field) for field in RETIRED_DIGEST_FIELDS}
    return hashlib.sha256(_canonical(basis)).hexdigest()[:_PAIR_DIGEST_CHARS]


@lru_cache(maxsize=1)
def retired_pair_digests() -> frozenset[str]:
    """Content digests of every pair in a retired gold, pinned to disk.

    Pinned rather than recomputed: the point is to refuse a **future** gold
    that re-uses these pairs, and a future gold cannot be its own reference.
    An unreadable or absent file raises rather than returning an empty set —
    a stopping rule that silently stops stopping is worse than none.
    """
    raw = json.loads(RETIRED_DIGESTS_PATH.read_text(encoding="utf-8"))
    digests = raw["digests"]
    if not isinstance(digests, list) or not digests:
        raise ValueError(f"{RETIRED_DIGESTS_PATH} carries no retired digests")
    count = raw.get("count")
    if len(digests) != count or len(set(digests)) != count:
        # The list is the refusal's whole reach; before this check the
        # embedded count was decorative, so truncating the list to one entry
        # would silently disarm every other content refusal. The archived
        # gold's own coverage is asserted by test against
        # RETIRED_GOLD_ARCHIVE_PATH; this runtime check is the half that
        # must hold wherever the refusal machinery runs.
        raise ValueError(
            f"{RETIRED_DIGESTS_PATH}: 'digests' disagrees with its own "
            f"'count' ({len(digests)} listed, {len(set(digests))} distinct, "
            f"count={count!r}) -- the pin has been truncated or padded"
        )
    return frozenset(digests)


def retired_pair_overlap(pairs: list[dict]) -> set[str]:
    """The ids in ``pairs`` whose content is a retired pair's content."""
    retired = retired_pair_digests()
    return {
        pair["id"] for pair in pairs
        if content_digest(pair) in retired
    }
