"""Near-duplicate propositions in the entailment gold (ruling R-B, 2026-08-10).

The loader's uniqueness check compares bytes, which is necessary and not
sufficient. Round 3 of T2.115 anchored three `direction` slots on facts that
already carried a live `direction` pair; two produced byte-identical hypotheses
and were skipped, and the History recorded the instruction *"do not resolve it
by rewording the reversal — that passes the uniqueness check while leaving a
near-duplicate in a measurement set"*. The third never collided, so the
instruction could not reach it, and `eg-0367` entered the gated census asserting
the same proposition as live `eg-0093` in different words.

**Why this is a module and not a sentence in the rulebook.** The finding is
precisely that a prose instruction aimed at the collisions someone had seen
could not reach the one that did not collide. Replacing it with another
sentence would repeat the mistake at one remove.

**Blind to every judge, and to the gold's own difficulty signals.** It reads
premise text, hypothesis text, and the gold's `verdict` label — the last only to
group, for the reason given at the grouping. It reads no rationale, no slice, no
population, no judge output and no per-pair result, so nothing it reports can be
a function of how any model performed. (An earlier draft of this paragraph said
"nothing here reads a verdict", which the grouping change made false one edit
later — the same stale-claim defect this corpus keeps finding, caught here
before it shipped.)

It reports; it never retires. What happens to a reported pair is a ruling, and
rulings live in LABELLING.md.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# Tokens that carry no propositional content and whose presence or absence is
# exactly how a reworded reversal evades a byte comparison ("hv-27 is a part of
# the scratch partition" vs "The scratch partition has hv-27 as a part").
_STOPWORDS = frozenset({
    "a", "an", "the", "is", "are", "was", "were", "be", "been", "being",
    "of", "as", "to", "in", "on", "at", "by", "for", "with", "from",
    "that", "this", "these", "those", "it", "its", "and", "or",
    "has", "have", "had", "does", "do", "did",
})

# Internal dots and hyphens are kept — `hv-27`, `license-report`, `v1.2` are one
# token each and splitting them would make unrelated pairs look alike. Trailing
# ones are stripped, which is not cosmetic: the first version of this regex let
# a sentence-final period ride along, so `partition.` and `partition` were
# different tokens and the check missed **both** duplicates it was written for.
# Caught by running it against them instead of trusting it.
_WORD = re.compile(r"[a-z0-9](?:[a-z0-9._-]*[a-z0-9])?")

# Light suffix folding, not a stemmer. It exists for one measured reason:
# `replaces` and `replaced` are the same relation in active and passive voice,
# and without folding them the `eg-0194`/`eg-0251` reversal scored 0.6 and the
# check missed the second of the two duplicates it was written for.
_SUFFIXES = ("edly", "ing", "ed", "es", "s")


def _fold(word: str) -> str:
    for suffix in _SUFFIXES:
        if len(word) > 4 and word.endswith(suffix):
            return word[: -len(suffix)]
    return word

# Two hypotheses over one premise are reported when their content-word sets
# agree this closely. Deliberately high: this flags for a human, and a check
# that cried wolf would be muted, which is how the last one failed.
JACCARD_THRESHOLD = 0.85


@dataclass(frozen=True)
class DuplicateFinding:
    left: str
    right: str
    similarity: float

    def key(self) -> tuple[str, str]:
        return (self.left, self.right) if self.left <= self.right else (self.right, self.left)


def content_tokens(text: str) -> frozenset[str]:
    """The proposition's content words, order and function words discarded.

    Order is discarded **on purpose**: a reversal states the same relation
    between the same two entities, so word order is the very thing that differs
    between a duplicate and its rewording. A check that respected order would
    pass exactly the pair that motivated this module.
    """
    return frozenset(
        _fold(w) for w in _WORD.findall(text.lower()) if w not in _STOPWORDS
    )


def similarity(left: str, right: str) -> float:
    a, b = content_tokens(left), content_tokens(right)
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def find_duplicate_propositions(
    pairs, *, threshold: float = JACCARD_THRESHOLD
) -> list[DuplicateFinding]:
    """Every live pair sharing a premise whose hypotheses say the same thing.

    Scoped to a shared premise rather than run over the whole corpus: two pairs
    about different premises are different claims however similar their wording,
    and widening it would flag the corpus's deliberate near-misses — the hard
    negatives the gold exists to contain.
    """
    by_premise: dict[tuple[str, str], list[dict]] = {}
    for pair in pairs:
        if "retired" in pair or pair.get("retirement_kind"):
            continue
        # Grouped by premise **and verdict**. Order is discarded above, so two
        # pairs asserting opposite things about one premise have identical token
        # sets — without this the check reported 19 pairs, most of them a
        # reversal beside its non-reversal, and a check that cries wolf is a
        # check someone mutes. A duplicate asserts the *same* proposition, so a
        # shared verdict is necessary for one. The gold's own label, never a
        # judge's.
        by_premise.setdefault((pair.get("premise", ""), pair.get("verdict")), []).append(pair)

    findings: list[DuplicateFinding] = []
    for group in by_premise.values():
        for index, left in enumerate(group):
            for right in group[index + 1:]:
                score = similarity(left.get("hypothesis", ""), right.get("hypothesis", ""))
                if score >= threshold:
                    findings.append(
                        DuplicateFinding(left["id"], right["id"], round(score, 4))
                    )
    return sorted(findings, key=lambda f: f.key())


@dataclass(frozen=True)
class CrossGoldFinding:
    fresh_id: str
    archived_id: str
    premise_similarity: float
    hypothesis_similarity: float


def cross_gold_near_overlap(
    fresh_pairs, archived_pairs, *, threshold: float = JACCARD_THRESHOLD
) -> list[CrossGoldFinding]:
    """Fresh pairs that near-reproduce a live pair of the archived gold.

    ``find_duplicate_propositions`` cannot do this job across the two files
    and would report nothing if pointed at them: it groups on byte-identical
    premise + verdict, and a fresh gold whose premises are all excluded from
    the archived harvest shares no premise bytes with the archive at all —
    cross-file it is vacuous by construction (T2.124 plan review, verified in
    code). So the cross-file screen deliberately drops both groupings: a
    (fresh, archived-live) row pair is flagged when **both** sides clear the
    module's content-token Jaccard — ``similarity(premise, premise) >=
    threshold AND similarity(hypothesis, hypothesis) >= threshold`` — with no
    shared-premise grouping and no verdict grouping. Reversal hard-negatives
    of genuinely fresh premises score low on the premise side and stay
    unflagged; a rewording of an archived pair (the ``eg-0367`` shape, one
    file removed) scores high on both and is reported for re-authoring from
    a different premise, never for rewording.

    Byte-identical reproduction is the digest refusal's job
    (``retired_pair_overlap``); this screen exists for what the digest
    cannot see. Like everything in this module it reads pair text only —
    no rationale, no slice, no judge output — so nothing it reports can be
    a function of how any model performed.
    """
    archived_live = [
        pair for pair in archived_pairs
        if not ("retired" in pair or pair.get("retirement_kind"))
    ]
    findings: list[CrossGoldFinding] = []
    for fresh in fresh_pairs:
        if "retired" in fresh or fresh.get("retirement_kind"):
            continue
        for archived in archived_live:
            premise_score = similarity(
                fresh.get("premise", ""), archived.get("premise", "")
            )
            if premise_score < threshold:
                continue
            hypothesis_score = similarity(
                fresh.get("hypothesis", ""), archived.get("hypothesis", "")
            )
            if hypothesis_score >= threshold:
                findings.append(CrossGoldFinding(
                    fresh["id"], archived["id"],
                    round(premise_score, 4), round(hypothesis_score, 4),
                ))
    return sorted(findings, key=lambda f: (f.fresh_id, f.archived_id))
