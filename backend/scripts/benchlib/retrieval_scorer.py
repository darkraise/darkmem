"""Pure sliced-accuracy scorer: MRR and hit@K over ranked ids vs gold.

``(ranked_ids_by_pair, gold_pairs) -> per-slice and aggregate MRR/hit@K``,
with no database and no knowledge of how the ranking was produced (T0.07
brief §7) -- that is what lets ``test_retrieval_scorer.py`` run offline and
fast. The module that drives the shipping retriever to produce
``ranked_ids_by_pair`` in the first place lives in ``retrieval_runner.py``;
its output is exactly this module's input. The split mirrors ``corpus.py``
(pure) vs ``ingest.py`` (DB-backed).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping, Sequence

from benchlib.retrieval_gold import SLICES

# Live per-slice pair counts today (task-T0.07-brief.md §5 / SLICES.md):
# exact 12, paraphrase 18, typo 14, fact 18, multi-hop 14, temporal 12,
# knowledge-update 14. 10 sits below every one of those with margin, so no
# currently-declared slice is ever flagged by accident, while a narrower ad
# hoc population -- e.g. this task's own 9-pair multi-hop headroom check
# (rg-0063/64, rg-0065/0066, rg-0069/0070, rg-0073/0074, rg-0076) -- still
# trips it: below 10, one pair flipping moves the mean by >=10 points, which
# is exactly the regime a reported number would misrepresent as precision.
DEFAULT_MIN_PAIRS = 10


def normalize_memory_id(value: object) -> str:
    """Collapse the memory_id type drift at one named boundary.

    CLAUDE.md's cross-cutting invariants, first entry: hybrid search
    returns string ids, ``PostgresVectorRepository.search`` returns
    ``UUID`` objects, and a bare ``==`` between the two is always False --
    silently turning a real hit into a miss with no error anywhere. Every
    id -- ranked or gold, from either side -- passes through this exact
    function before any comparison. ``.lower()`` also absorbs a
    same-value-different-case UUID string rendering, which ``str()`` alone
    would not.
    """
    return str(value).strip().lower()


@dataclass(frozen=True)
class PairScore:
    pair_id: str
    slice_tag: str
    reciprocal_rank: float
    hit: bool
    n_relevant: int
    n_found: int


@dataclass(frozen=True)
class SliceScore:
    slice_tag: str
    n_pairs: int
    powered: bool
    mrr: float | None
    hit_at_k: float | None


@dataclass(frozen=True)
class ScoreReport:
    k: int
    retrieval_limit: int
    min_pairs: int
    n_pairs: int
    slices: dict[str, SliceScore]
    aggregate_powered: bool
    aggregate_mrr: float | None
    aggregate_hit_at_k: float | None
    pair_scores: dict[str, PairScore]


def _score_one_pair(pair: Mapping, ranked_ids: Sequence, k: int) -> PairScore:
    # MRR and hit@K are both computed from the SAME top-k prefix. Scoring
    # MRR over the whole (possibly much longer) ranked list while hit@K
    # truncates at k makes a table headed "k=10" secretly report MRR@limit
    # -- a real bug found by adversarial review: rg-0016's gold sat at rank
    # 12 in a limit=72 retrieval run and was credited 1/12 by a
    # full-list reciprocal rank while correctly missing hit@10, so the two
    # metrics disagreed about what "k=10" meant.
    ranked_norm = [normalize_memory_id(rid) for rid in ranked_ids][:k]
    relevant_norm = {normalize_memory_id(rid) for rid in pair["relevant_memory_ids"]}

    reciprocal_rank = 0.0
    for rank, rid in enumerate(ranked_norm, start=1):
        if rid in relevant_norm:
            reciprocal_rank = 1.0 / rank
            break

    # hit@K is coverage, not "any relevant id showed up": for a multi-hop
    # pair the gold set is {A, B} and a retriever that returns only the
    # lexically anchored A must NOT count as a hit (SLICES.md, multi-hop:
    # "hit@K over the full relevant set fails"). For every other slice
    # (exactly one relevant id) this collapses to ordinary hit@K, so one
    # definition covers all seven slices without a special case.
    n_found = len(relevant_norm & set(ranked_norm))
    hit = n_found == len(relevant_norm)

    return PairScore(
        pair_id=pair["id"],
        slice_tag=pair["slice_tags"][0],
        reciprocal_rank=reciprocal_rank,
        hit=hit,
        n_relevant=len(relevant_norm),
        n_found=n_found,
    )


def _aggregate(
    scores: Sequence[PairScore], min_pairs: int,
) -> tuple[bool, float | None, float | None]:
    n = len(scores)
    if n < min_pairs:
        return False, None, None
    mrr = sum(s.reciprocal_rank for s in scores) / n
    hit_at_k = sum(1 for s in scores if s.hit) / n
    return True, mrr, hit_at_k


def score_retrieval(
    ranked_ids_by_pair: Mapping[str, Sequence],
    gold_pairs: Iterable[Mapping],
    *,
    retrieval_limit: int,
    k: int = 10,
    min_pairs: int = DEFAULT_MIN_PAIRS,
) -> ScoreReport:
    """Score one retrieval run against gold, sliced and in aggregate.

    ``gold_pairs`` is the raw pairs list as ``load_retrieval_gold()["pairs"]``
    returns it (or any subset of it) -- retired pairs are dropped HERE,
    at scoring time, rather than by the caller: "excluded from scoring" is
    a scoring-time rule (brief §3), and doing it in one place means every
    caller gets it for free instead of re-implementing the filter.

    ``retrieval_limit`` is the fetch depth the run behind
    ``ranked_ids_by_pair`` was actually run at (e.g. the ``limit`` passed to
    ``retrieval_runner.run_retrieval``) -- it is keyword-only and has no
    default, forcing every caller to state it rather than let two runs at
    different fetch depths be compared under the same ``k`` without the
    mismatch being visible anywhere (a real bug found by adversarial
    review: MRR used to be computed over the whole ranked list rather than
    the top-``k`` prefix, so a table headed "k=10" silently reported MRR at
    whatever depth the retriever happened to fetch). Two invariants follow
    directly: ``k`` can never exceed ``retrieval_limit`` here (scoring
    deeper than what was fetched cannot measure anything beyond the
    fetched prefix), and no individual ranked list may be longer than the
    declared ``retrieval_limit`` (a caller that mislabels its own fetch
    depth is exactly the silent mismatch this parameter exists to catch).
    Both are recorded on the returned ``ScoreReport`` so a downstream
    comparison of two reports can check they used the same protocol before
    trusting a delta between them.

    Every live (non-retired) pair must have a matching entry in
    ``ranked_ids_by_pair``, or this raises ``KeyError`` naming the missing
    pair ids. A retrieval driver that silently failed to query a pair must
    not be indistinguishable from one that queried it and scored zero.

    The aggregate is a single pooled (micro-averaged) mean over every live
    pair supplied, not a macro-average of the per-slice means -- so a
    31-pair scoring run's aggregate reflects the actual query mix, and a
    small slice never carries the same weight in the one aggregate number
    as a slice with more pairs. Slices are still reported in full
    regardless (doc 17 §4: "the aggregate never replaces the slices").

    A slice (or the aggregate) with fewer than ``min_pairs`` live pairs
    reports ``powered=False`` and ``mrr=None`` / ``hit_at_k=None`` --
    distinct states, not a number with an asterisk, so a consumer cannot
    accidentally average or plot an under-powered estimate as if it were
    measured (brief §5).
    """
    if k > retrieval_limit:
        raise ValueError(
            f"k={k} exceeds retrieval_limit={retrieval_limit}: a run fetched "
            "only retrieval_limit results per query, so scoring at a deeper "
            "k cannot measure anything beyond what was actually returned"
        )

    live_pairs = [p for p in gold_pairs if not p.get("retired")]
    missing = [p["id"] for p in live_pairs if p["id"] not in ranked_ids_by_pair]
    if missing:
        raise KeyError(
            f"no ranked results for {len(missing)} live pair(s): {missing[:5]}"
            + (" ..." if len(missing) > 5 else "")
        )

    oversized = [
        p["id"] for p in live_pairs
        if len(ranked_ids_by_pair[p["id"]]) > retrieval_limit
    ]
    if oversized:
        raise ValueError(
            f"retrieval_limit={retrieval_limit} but {len(oversized)} pair(s) carry "
            f"more ranked ids than that: {oversized[:5]}"
            + (" ..." if len(oversized) > 5 else "")
            + " -- retrieval_limit must be the true fetch depth, not an understatement of it"
        )

    pair_scores = {
        p["id"]: _score_one_pair(p, ranked_ids_by_pair[p["id"]], k)
        for p in live_pairs
    }

    # Every declared slice is reported even at zero pairs (an empty
    # population is trivially under-powered, not a crash or an omission);
    # an unrecognised tag from a hand-built test fixture still gets its own
    # bucket rather than a KeyError, since this function trusts its input
    # is validated gold but must not blow up on a caller that isn't.
    all_tags = SLICES | {s.slice_tag for s in pair_scores.values()}
    by_slice: dict[str, list[PairScore]] = {tag: [] for tag in all_tags}
    for score in pair_scores.values():
        by_slice[score.slice_tag].append(score)

    slices: dict[str, SliceScore] = {}
    for tag, scores in by_slice.items():
        powered, mrr, hit_at_k = _aggregate(scores, min_pairs)
        slices[tag] = SliceScore(
            slice_tag=tag, n_pairs=len(scores), powered=powered,
            mrr=mrr, hit_at_k=hit_at_k,
        )

    agg_powered, agg_mrr, agg_hit = _aggregate(list(pair_scores.values()), min_pairs)

    return ScoreReport(
        k=k,
        retrieval_limit=retrieval_limit,
        min_pairs=min_pairs,
        n_pairs=len(pair_scores),
        slices=slices,
        aggregate_powered=agg_powered,
        aggregate_mrr=agg_mrr,
        aggregate_hit_at_k=agg_hit,
        pair_scores=pair_scores,
    )
