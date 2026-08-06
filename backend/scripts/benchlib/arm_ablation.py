"""Arm-ablation harness for the retrieval eval (T2.44).

``--arm <flag>`` on ``run_retrieval_eval.py`` runs ONE ``rank_fusion_factor``
arm (``app/services/rank_fusion.RANK_ARMS``) on and off over the SAME
ingested corpus, in one invocation, and reports the per-slice MRR/hit@K
delta between the two legs -- never two separate runs a human diffs by hand
(brief done-when 1). This module builds the plumbing only: it does not
decide whether any arm's delta clears a bar, and it does not set any arm's
weight in shipped config (runbook §2's separation of powers; that judgment
belongs to each arm's own Fable-tier activation task, named on
``RankArm.activation``).

Three rulings this module is held to, the same three ``full_context.py`` and
``run_retrieval_eval.py`` are held to before it:

**No accuracy without its twin (brief done-when 2).** Each leg is scored
into a ``twin.EvalRun``, whose constructor already refuses to exist without
a real ``twin.Twin``; ``ArmComparison`` refuses to exist without two whole
``EvalRun``s (the same guarantee ``full_context.Comparison`` holds for its
own two arms), and ``record_arm_comparison`` is the only way anything here
reaches ``benchlib.ledger.record`` with one. ``full_context.Comparison`` /
``record_comparison`` are deliberately NOT reused directly for this: their
``id_audit`` and ``context`` fields describe the full-context arm's own read
of the whole corpus and what of it got dropped, which has no meaning for two
retrieval legs that differ only in one config weight, and their
``retrieval`` / ``full_context`` field names would mislabel an on/off
ablation of one arm as a retrieval-vs-full-context comparison in the ledger
-- exactly the kind of silent drift CLAUDE.md warns against. ``ArmComparison``
applies the same discipline (two required whole ``EvalRun``s, structurally
enforced) to the shape this comparison actually has.

**No cross-fingerprint comparison (brief done-when 3, CLAUDE.md invariant
2).** Both legs query the one corpus ``run_arm_ablation`` ingests. Querying
is fingerprinted by OBSERVATION, not by trusting config: ``run_arm_leg``
wraps ``llm.embed`` for the leg's duration
(``_collect_query_fingerprints``) and records what every query embed call
actually returned, deliberately not ``llm.llm_fingerprint()`` (a pure
function of the embedding purpose's config alone) -- see that helper's own
docstring for why a config read is assumed-equal rather than observed, and
is therefore the weaker of the two. ``ArmComparison`` asserts both legs
agree with each other AND with the corpus's own ingested fingerprint, so a
future change that let a leg's embedder rotate mid-run fails loudly instead
of silently producing a plausible, wrong delta.

**Nothing hardcoded from the corpus (ruling 2).** The valid ``--arm`` set is
read from ``RANK_ARMS`` at call time (``resolve_arm``), never a second
hand-written list -- the drift ``code_query.py``'s duplicate ``RRF_K`` was
until T2.58 collapsed it onto ``rank_fusion.py``'s, now guarded by the AST
scan in ``backend/tests/test_chat_retrieval_parity.py``.

Each leg runs on its OWN ``TwinningOrchestrator`` instance (sharing the disk
cache directory with ingest and with the other leg, but never its in-memory
token/latency counters): ingest's extraction/classification cost and the
other leg's query-time cost must not bleed into a leg's own twin, or the
ablation would report one leg as more expensive than it actually is purely
because it ran second.
"""
from __future__ import annotations

import uuid
from collections.abc import Mapping
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import select

from benchlib import bench_db, ledger, retrieval_gold, run_smoke  # noqa: F401  (DATABASE_URL override first)
from benchlib.ingest import GateConfig, run_ingest
from benchlib.retrieval_runner import run_retrieval
from benchlib.retrieval_scorer import score_retrieval
from benchlib.twin import EvalRun, Twin, TwinningOrchestrator, instrument_retrieval

from app.config import FEATURE_FLAGS_DEFAULTS
from app.models.config import Config
from app.services.config import get_llm_config
from app.services.feature_flags import FEATURE_FLAGS_KEY
from app.services.pipeline import _flag_cache_reset
from app.services.rank_fusion import (
    CONTEXT_BOOST_FLAG,
    LIST_WEIGHT_KEYS,
    RANK_ARMS,
    RankArm,
)

# Pinned to match run_retrieval_eval.py's own K/MIN_PAIRS: both runners
# measure over the same corpus/gold under the same scoring protocol. These
# are protocol constants, not corpus-derived ones (ruling 2 is about the
# CORPUS, e.g. never baking in "94 memories"), and are duplicated rather than
# imported to keep this module free of a load-order dependency on the other
# runner -- run_retrieval_eval.py imports THIS module from inside main(), not
# at top level, precisely to avoid that cycle.
K = 10
MIN_PAIRS = 10

CACHE_DIR = retrieval_gold.RETRIEVAL_DIR / "cache"
# RETRIEVAL_DIR = backend/scripts/benchlib/retrieval; parents[0..3] =
# benchlib, scripts, backend, repo root.
REPORT_DIR = retrieval_gold.RETRIEVAL_DIR.parents[3] / "docs" / "eval"

# Every RANK_ARMS weight ships at 0.0 (app/config.py FEATURE_FLAGS_DEFAULTS),
# so an ablation's "on" leg needs SOME nonzero value and there is no shipped
# default to read (brief done-when 1's open question). 1.0 is a probe
# magnitude, not a production recommendation: arm_factor is
# `1 + weight * (signal - baseline)`, and at weight=1.0 a signal spanning a
# natural [0, 1] range around a 0.5 baseline (today's only wired-for-activation
# signal, w_importance) swings the multiplier over [0.5, 1.5] -- wide enough
# to see whether the arm moves anything at all, without a magnitude so large
# the composed factor can go negative and hit arm_factor's own `max(0.0, ...)`
# floor. Deciding whether 1.0 -- or any other magnitude -- clears a bar is
# explicitly not this module's job; --weight exists so a Fable-tier task can
# probe other magnitudes without editing this file, and whatever value is
# actually used is always recorded in the run's own meta/report/ledger.
DEFAULT_PROBE_WEIGHT = 1.0

# **A list weight is not a factor weight, and 1.0 means something different in
# each class.** `arm_factor` composes as `1 + weight * (signal - baseline)`, so
# 1.0 there is a moderate swing around the identity. An RRF *list* weight is
# the list's whole share of the fusion, and the two shipped lists already split
# 1.0 between them (`semantic_weight` 0.7 / keyword 0.3) — so probing a third
# list at 1.0 gives it more voice than the entire existing fusion combined, and
# the delta then measures the probe rather than the arm.
#
# This is not hypothetical: the first `--arm w_ppr` run at 1.0 reported an
# aggregate MRR delta of **-0.4742**, which reads as "PPR is catastrophic" and
# is really "a list weighted above everything else dominates the order".
# 0.3 is the keyword side's own share — the natural "one more voice of
# comparable size" probe. Whether any magnitude clears a bar remains T2.50's
# judgment, not this module's; `--weight` still overrides.
LIST_PROBE_WEIGHT = 0.3

LEG_OFF = "off"
LEG_ON = "on"

PROTOCOL_FIELDS = ("k", "min_pairs", "n_pairs")


def resolve_arm(flag: str) -> RankArm:
    """The one arm named ``flag``, or a loud rejection naming the valid set.

    Reads ``RANK_ARMS`` at call time rather than a module-level hand list,
    so a fifth arm lands here automatically the moment it is added to
    ``rank_fusion.py`` -- the exact drift ``code_query.py``'s duplicate
    ``RRF_K`` was, until T2.58 collapsed it onto the canonical one.

    Accepts only the FLAG spelling (``w_importance``), not the short
    ``name`` (``importance``): the flag is what a config row and the task's
    own Verify line (``--arm w_importance``) actually name, and accepting a
    second spelling for the same arm is exactly the kind of ambiguity this
    function exists to foreclose.
    """
    for arm in RANK_ARMS:
        if arm.flag == flag:
            return arm
    valid = sorted(arm.flag for arm in RANK_ARMS)
    raise ValueError(f"unknown --arm {flag!r}; valid arms are {valid}")


async def _prepare_project_scoped_arm(session_factory):
    """Build the PPR snapshot for the ingested corpus and return its scope.

    Refuses rather than returning an empty scope in every case where the arm
    would be measurable-looking but vacuous:

    * **no project** — nothing was ingested;
    * **more than one project** — the corpus would need a scope choice this
      harness has no basis to make, and one project's snapshot cannot rank
      another's rows (invariant: no cross-project mass);
    * **an empty snapshot** — the graph had no entities to build from, so the
      arm would contribute nothing and the run would report a zero delta that
      reads exactly like a measured "no win".

    The project is read from what was actually ingested rather than assumed
    from the corpus file (ruling 2: nothing hardcoded from the corpus).
    """
    from sqlalchemy import text as sa_text

    from app.repositories.vector import MemoryFilter
    from app.services import ppr_snapshot

    async with session_factory() as session:
        rows = await session.execute(
            sa_text(
                "SELECT DISTINCT project FROM memories "
                "WHERE status = 'active' AND is_archived = false"
            )
        )
        projects = sorted(row[0] for row in rows)

    if not projects:
        raise ArmNotMeasurable(
            "the bench corpus ingested no live memories, so a project-scoped "
            "arm has nothing to rank"
        )
    if len(projects) > 1:
        raise ArmNotMeasurable(
            "the bench corpus spans more than one project "
            f"({projects}); a PPR snapshot is per project and mass has no "
            "defined meaning across two, so this harness cannot choose a "
            "scope for the legs"
        )

    project = projects[0]
    cache = ppr_snapshot.snapshot_cache()
    cache.clear()
    outcome = await ppr_snapshot.refresh_snapshots(
        session_factory, batch_size=len(projects), cache=cache,
    )
    snapshot = cache.get(project)
    if snapshot is None or snapshot.node_count == 0:
        reasons = [o.skipped_reason for o in outcome.outcomes if o.skipped_reason]
        raise ArmNotMeasurable(
            f"no PPR snapshot could be built for project {project!r} "
            f"({reasons or 'empty graph'}), so the arm would contribute "
            "nothing and the run would report a zero delta indistinguishable "
            "from a measured 'no win'"
        )

    print(
        f"      PPR snapshot for {project!r}: {snapshot.node_count} nodes, "
        f"{snapshot.edge_count} edges; both legs scoped to that project."
    )
    return MemoryFilter(project=project)


async def _prepare_relation_vectors(session_factory, llm_config, cache_dir):
    """Embed the ingested corpus's relations so the dual-level arm has vectors.

    `relation_embeddings` is written by a Tier-C refresh job that never runs in
    a bench process, so without this the partition is empty, the arm returns no
    candidates, and the run reports an exact zero on every slice — the same
    vacuity the PPR snapshot needed handling for, and the reason both arms
    declare `needs_artifact` rather than leaving it to a runner to remember.

    Refuses rather than proceeding on an empty partition: a zero delta measured
    against no vectors is indistinguishable from a measured "no win" once it
    reaches the ledger.
    """
    from app.services import relation_embeddings as relation_mod

    prep_llm = TwinningOrchestrator(llm_config, cache_dir=str(cache_dir))
    async with session_factory() as session:
        fingerprint = prep_llm.llm_fingerprint()
        relation_ids = await relation_mod.relations_missing_vectors(
            session, fingerprint, 100_000,
        )
        written = 0
        if relation_ids:
            result = await relation_mod.embed_relations(
                session, prep_llm, relation_ids=relation_ids,
            )
            written = result.written if result else 0
        await session.commit()

    if not written:
        raise ArmNotMeasurable(
            "the ingested corpus produced no relation vectors, so the "
            "dual-level arm has no candidates and the run would report a zero "
            "delta indistinguishable from a measured 'no win'"
        )
    print(f"      embedded {written} relation vector(s) for the dual-level arm.")


class ArmNotMeasurable(RuntimeError):
    """This arm cannot be ablated on this harness, and why.

    **The reason this type exists is that the alternative is a zero.** An arm
    whose signal cannot possibly be present still runs perfectly: both legs
    retrieve identically, every slice reports a delta of exactly 0.0000, and
    the report reads like a measured "no win". That has already happened
    twice — `w_heat` measured before its signal was wired, and `w_ppr` would
    measure the same way against an empty snapshot — and a zero of that kind
    is worse than no number, because it is indistinguishable from a real one
    once it reaches the arm-activation log.

    So an arm with an unsatisfiable precondition refuses **before** the bench
    reset and before any model call, naming what is missing and who owns it.
    """


@dataclass(frozen=True)
class AblatableArm:
    """One flag the harness can ablate, across all three signal classes.

    `RANK_ARMS` covers only the post-fusion multipliers. The read path has two
    other classes doc 07 §3 keeps deliberately separate — the RRF **list**
    weights (`LIST_WEIGHT_KEYS`) and the `applies_when` context boost — and
    both were rejected outright by the original resolver, so the tasks that
    own them (T2.35, T2.50) could not run their own stated Verify line.

    ``companions`` is what makes a list arm ablatable at all: `w_ppr` alone
    does nothing, because `ppr_list_weight` returns zero unless `ppr_enabled`
    is also set. Pinning the weight without its gate would measure the off leg
    twice and call the result a delta.
    """

    flag: str
    name: str
    kind: str
    activation: str | None = None
    arm: RankArm | None = None
    companions: Mapping[str, object] = field(default_factory=dict)
    project_scoped: bool = False
    # Names an artefact the arm reads that no bench ingest produces. Both
    # graph arms need one, and both fail identically without it — an exact
    # zero on every slice — so the preparation is part of resolving the arm
    # rather than something a runner may forget.
    needs_artifact: str | None = None
    blocked: str | None = None


KIND_FACTOR = "factor"
KIND_LIST = "list"
KIND_BOOST = "boost"


def _blocked_reasons() -> dict[str, str]:
    """Why each currently-unmeasurable arm is unmeasurable, in one place.

    Stated as prose the runner prints verbatim rather than as a boolean,
    because the useful part is *what would have to change*, and a caller who
    only learns "no" will reach for the zero instead.

    `w_dual` was here until T2.94 landed the reader; its entry was removed
    rather than left stale, which is that task's own last Done-when.
    """
    return {
        CONTEXT_BOOST_FLAG: (
            "the retrieval runner declares no context. `match_context` needs "
            "a DeclaredContext to produce anything but the neutral outcome, "
            "and the gold pairs carry no env/version/situation axis, so the "
            "boost is structurally inert at every magnitude. Needs a context "
            "axis on the gold set — gold-authoring work, not harness work."
        ),
    }


def resolve_ablatable(flag: str) -> AblatableArm:
    """The one ablatable signal named ``flag``, across all three classes.

    Every class is derived at call time from the module that defines it —
    ``RANK_ARMS``, ``LIST_WEIGHT_KEYS``, ``CONTEXT_BOOST_FLAG`` — never a
    hand-written second list, which is the same discipline `resolve_arm` was
    written under and the drift `code_query.py`'s duplicate ``RRF_K`` was.
    """
    for arm in RANK_ARMS:
        if arm.flag == flag:
            return AblatableArm(
                flag=flag, name=arm.name, kind=KIND_FACTOR,
                activation=arm.activation, arm=arm,
            )

    blocked = _blocked_reasons()
    if flag in LIST_WEIGHT_KEYS and flag != "semantic_weight":
        return AblatableArm(
            flag=flag,
            name=flag.removeprefix("w_"),
            kind=KIND_LIST,
            activation="T2.50",
            companions={"ppr_enabled": True} if flag == "w_ppr" else {"dual_level_enabled": True},
            project_scoped=flag == "w_ppr",
            needs_artifact="ppr_snapshot" if flag == "w_ppr" else "relation_embeddings",
            blocked=blocked.get(flag),
        )
    if flag == CONTEXT_BOOST_FLAG:
        return AblatableArm(
            flag=flag, name="context_boost", kind=KIND_BOOST,
            activation="T2.35",
            blocked=blocked.get(flag),
        )

    valid = sorted(
        {arm.flag for arm in RANK_ARMS}
        | {f for f in LIST_WEIGHT_KEYS if f != "semantic_weight"}
        | {CONTEXT_BOOST_FLAG}
    )
    raise ValueError(f"unknown --arm {flag!r}; valid arms are {valid}")


async def _pin_arm_weight(
    session_factory, *, gate_config: dict, arm: RankArm, weight: float,
) -> dict:
    """Rewrite the WHOLE feature-flags row -- mirrors ``ingest.pin_gate_config``'s
    own discipline (doc 17 §7 / FROZEN.md "Gate pinning rewrites the whole
    feature-flags row") -- as defaults, plus the ingest run's own
    classification-mode / relation-rescue (retrieval does not read either,
    but pinning them keeps the row's OTHER fields identical to what
    ingestion measured under, not an unrelated leftover), plus exactly this
    arm's weight. Every other arm and every other flag stays at its shipped
    default, so a leg's own weight is the only thing that ever differs
    between the two legs' feature-flags row.
    """
    async with session_factory() as session:
        pinned = dict(FEATURE_FLAGS_DEFAULTS)
        pinned["classification_mode"] = gate_config.get(
            "classification_mode", FEATURE_FLAGS_DEFAULTS["classification_mode"]
        )
        pinned["relation_rescue"] = gate_config.get(
            "relation_rescue", FEATURE_FLAGS_DEFAULTS["relation_rescue"]
        )
        pinned[arm.flag] = weight
        # A list weight alone is inert: `ppr_list_weight` returns zero unless
        # `ppr_enabled` is also set, so pinning the weight without its gate
        # would run the off leg twice and report the difference as a delta.
        # Applied to the ON leg only — the off leg must stay exactly the
        # shipped configuration it is the control for.
        if weight and getattr(arm, "companions", None):
            pinned.update(arm.companions)

        result = await session.execute(select(Config).where(Config.key == FEATURE_FLAGS_KEY))
        row = result.scalar_one_or_none()
        if row is not None:
            row.value = pinned
        else:
            session.add(Config(key=FEATURE_FLAGS_KEY, value=pinned))
        await session.commit()

    # process_batch/semantic_search read feature flags through pipeline.py's
    # 5s TTL single-flight cache (app.services.pipeline._get_feature_flags_cached).
    # Without this reset, a leg run within 5s of the other leg's pin would
    # silently measure the PRIOR leg's weight -- ingest.pin_gate_config's own
    # reason for calling this, here for the same reason.
    _flag_cache_reset()
    return pinned


@dataclass(frozen=True)
class ArmLeg:
    """One leg's whole result: the weight it ran at, the embedder fingerprint
    it queried under, and its accuracy score bound to a real twin.

    ``run`` must be a real ``twin.EvalRun`` -- its own constructor already
    refuses to exist without a real ``twin.Twin`` -- so an ``ArmLeg`` cannot
    be built from a bare score. Re-asserted here (not just relied on via
    ``run``'s own type) so a caller that passes something EvalRun-shaped but
    not an actual ``EvalRun`` (e.g. a plain namespace during a refactor) is
    refused at the boundary closest to the mistake.
    """

    weight: float
    fingerprint: str
    run: EvalRun

    def __post_init__(self):
        if not isinstance(self.run, EvalRun):
            raise TypeError(
                f"ArmLeg requires a real EvalRun (score AND twin); got {self.run!r}"
            )


@contextmanager
def _collect_query_fingerprints(llm):
    """Patch ``llm.embed`` (instance level, restored on exit) to record every
    fingerprint a query embed call actually returns.

    Deliberately not ``llm.llm_fingerprint()`` (a pure function of the
    embedding purpose's CONFIG alone): that value only equals what a real
    embed call returns because ``LLMOrchestrator.embed`` derives its own
    fingerprint from the same config by construction -- true in production,
    but a fact about ``app/services/llm.py``, not something this harness
    should assume rather than observe. Mirrors ``CachingLLMOrchestrator.embed_batch``'s
    own ``fingerprints_seen`` bookkeeping (``caching_llm.py``), extended to
    the single-item ``embed()`` path query-time retrieval actually uses,
    which does not otherwise register into that set.
    """
    seen: set[str] = set()
    orig_embed = llm.embed
    had_instance_embed = "embed" in vars(llm)

    async def wrapped(text):
        vec, fp = await orig_embed(text)
        seen.add(fp)
        return vec, fp

    llm.embed = wrapped
    try:
        yield seen
    finally:
        if had_instance_embed:
            llm.embed = orig_embed
        else:
            del llm.embed


async def run_arm_leg(
    llm: TwinningOrchestrator,
    session_factory,
    gold_pairs,
    *,
    arm: RankArm,
    weight: float,
    gate_config: dict,
    retrieval_limit: int,
    k: int = K,
    min_pairs: int = MIN_PAIRS,
    filters=None,
) -> ArmLeg:
    """Pin ``arm`` to ``weight``, run every live gold pair through the
    shipping retriever, and score it -- one leg of an ablation.

    The reported fingerprint is what the queries actually embedded under
    (``_collect_query_fingerprints``), not a static config read, so a real
    mid-run embedder rotation (CLAUDE.md: "the fingerprint may change... if
    the active embedder rotated") is observed rather than assumed away. A
    leg whose own queries land on more than one fingerprint refuses loudly
    -- the same shape ``run_ingest`` already refuses a mixed-fingerprint
    ingest with.
    """
    await _pin_arm_weight(session_factory, gate_config=gate_config, arm=arm, weight=weight)
    with _collect_query_fingerprints(llm) as fingerprints_seen:
        with instrument_retrieval(llm) as recorder:
            ranked = await run_retrieval(
                llm, session_factory, gold_pairs, limit=retrieval_limit,
                filters=filters,
            )
    if len(fingerprints_seen) > 1:
        raise RuntimeError(
            f"leg at weight={weight!r} mixed embedder fingerprints, which "
            f"invariant 2 forbids: {sorted(fingerprints_seen)}"
        )
    fingerprint = next(iter(fingerprints_seen)) if fingerprints_seen else llm.llm_fingerprint()
    score = score_retrieval(
        ranked, gold_pairs, retrieval_limit=retrieval_limit, k=k, min_pairs=min_pairs,
    )
    run = EvalRun(score=score, twin=Twin.capture(recorder, llm.tokens))
    return ArmLeg(weight=weight, fingerprint=fingerprint, run=run)


@dataclass(frozen=True)
class ArmComparison:
    """Two legs of ONE arm, on and off, and nothing less -- the same
    discipline ``full_context.Comparison`` holds for its own two arms,
    applied to this comparison's actual shape (module docstring).
    """

    arm: RankArm
    off: ArmLeg
    on: ArmLeg
    ingest_fingerprint: str

    def __post_init__(self):
        for label, leg in ((LEG_OFF, self.off), (LEG_ON, self.on)):
            if not isinstance(leg, ArmLeg):
                raise TypeError(
                    f"ArmComparison requires a whole ArmLeg for the {label!r} "
                    f"leg; got {leg!r}. An ablation states both legs or does "
                    "not exist."
                )

        # "off" means weight zero, not a separate code path (brief: "What
        # weight does 'on' use? ... 'off' should mean weight zero"); enforced
        # here so a caller cannot silently swap which leg is which.
        if self.off.weight != 0.0:
            raise ValueError(
                "the OFF leg must run at weight 0.0 ('off' means weight "
                "zero, not a separate code path -- rank_fusion.arm_factor's "
                f"own guarantee); got weight={self.off.weight!r}"
            )
        if self.on.weight == 0.0:
            raise ValueError(
                f"the ON leg's weight is 0.0, which is not an ablation of "
                f"{self.arm.name!r} at all -- pass a nonzero weight"
            )

        mismatched = [
            f"{f}: {getattr(self.off.run.score, f)!r} vs {getattr(self.on.run.score, f)!r}"
            for f in PROTOCOL_FIELDS
            if getattr(self.off.run.score, f) != getattr(self.on.run.score, f)
        ]
        if mismatched:
            raise ValueError(
                "the two legs were scored under different protocols, so no "
                f"delta between them is meaningful: {'; '.join(mismatched)}"
            )
        if set(self.off.run.score.pair_scores) != set(self.on.run.score.pair_scores):
            raise ValueError(
                "the two legs were scored over different gold pairs; a "
                "comparison is only defined over one shared pair set"
            )

        # Invariant 2 (CLAUDE.md): no cross-fingerprint comparison. Both legs
        # must land on the SAME partition as each other and as the corpus
        # they were actually ingested into -- a query-time embedder rotation
        # between legs would otherwise produce a plausible, wrong delta,
        # which is the worst failure mode for a measurement harness.
        for label, leg in ((LEG_OFF, self.off), (LEG_ON, self.on)):
            if leg.fingerprint != self.ingest_fingerprint:
                raise ValueError(
                    f"the {label} leg queried under fingerprint "
                    f"{leg.fingerprint!r}, but the corpus was ingested under "
                    f"fingerprint {self.ingest_fingerprint!r} -- invariant 2 "
                    "forbids a cross-fingerprint comparison"
                )
        if self.off.fingerprint != self.on.fingerprint:
            raise ValueError(
                f"the two legs ran under different fingerprints "
                f"({self.off.fingerprint!r} vs {self.on.fingerprint!r}) -- "
                "invariant 2 forbids a cross-fingerprint comparison"
            )

    def deltas(self) -> dict:
        """on minus off, per slice and in aggregate.

        ``None`` propagates: a delta against an under-powered slice (whose
        mrr/hit are ``None``, not zero) is itself unknown, and reporting it
        as a number would invent a measurement neither leg made. The slice
        set is whatever ``score_retrieval`` produced for either leg -- read
        from the gold at scoring time, never a slice list hardcoded here.
        """
        def diff(a, b):
            return None if a is None or b is None else a - b

        off_score, on_score = self.off.run.score, self.on.run.score
        slices = {}
        for tag in sorted(set(off_score.slices) | set(on_score.slices)):
            off_s, on_s = off_score.slices.get(tag), on_score.slices.get(tag)
            slices[tag] = {
                "mrr": diff(on_s.mrr if on_s else None, off_s.mrr if off_s else None),
                "hit_at_k": diff(
                    on_s.hit_at_k if on_s else None, off_s.hit_at_k if off_s else None
                ),
            }
        return {
            "direction": f"{LEG_ON} minus {LEG_OFF}",
            "slices": slices,
            "aggregate": {
                "mrr": diff(on_score.aggregate_mrr, off_score.aggregate_mrr),
                "hit_at_k": diff(on_score.aggregate_hit_at_k, off_score.aggregate_hit_at_k),
            },
        }

    def to_ledger_payload(self) -> dict:
        return {
            "arm_comparison": {
                "arm": self.arm.name,
                "flag": self.arm.flag,
                "activation": self.arm.activation,
                "fingerprint": self.ingest_fingerprint,
                "k": self.off.run.score.k,
                "min_pairs": self.off.run.score.min_pairs,
                "n_pairs": self.off.run.score.n_pairs,
                "legs": {
                    LEG_OFF: {"weight": self.off.weight, **self.off.run.to_ledger_payload()},
                    LEG_ON: {"weight": self.on.weight, **self.on.run.to_ledger_payload()},
                },
                "deltas": self.deltas(),
            }
        }


def record_arm_comparison(
    comparison: ArmComparison, path=ledger.DEFAULT_PATH, *, metadata: dict | None = None,
) -> None:
    """The sanctioned way to append an arm-ablation comparison to the
    ledger -- mirrors ``full_context.record_comparison``'s own guarantee:
    takes only a whole ``ArmComparison``, whose constructor already refused
    to exist without two whole ``EvalRun``s (each already refusing to exist
    without its own twin), so no call here can record a delta, or a bare
    accuracy figure, on its own. There is no ``ledger.record`` call anywhere
    else in this module.
    """
    if not isinstance(comparison, ArmComparison):
        raise TypeError(
            f"record_arm_comparison takes an ArmComparison (both legs), got {comparison!r}"
        )
    payload = comparison.to_ledger_payload()
    if metadata:
        overlap = set(metadata) & set(payload)
        if overlap:
            raise ValueError(
                f"metadata key(s) {sorted(overlap)} collide with the payload's "
                "own top-level key(s) -- rename the metadata field(s)"
            )
        payload = {**metadata, **payload}
    ledger.record(payload, path=path)


# ── human-readable rendering ─────────────────────────────────────────────


def _num(value, width: int = 8) -> str:
    return "n/a".rjust(width) if value is None else f"{value:{width}.4f}"


def _pct_line(stats) -> str:
    if stats.n == 0:
        return "no samples"
    if not stats.powered:
        return f"n={stats.n:>4} under-powered (p50/p95 withheld)"
    return f"n={stats.n:>4}  p50={stats.p50:.5f}  p95={stats.p95:.5f}"


def report_path(run_date, arm: RankArm, report_dir: Path = REPORT_DIR) -> Path:
    """``docs/eval/<date>-retrieval-eval-arm-<flag>.md``. Overwriting an
    existing same-date/same-arm report is the caller's job (``Path.write_text``
    already does that) -- a same-day re-run of the same arm is a correction,
    matching run_retrieval_eval.py's own ruling 4."""
    return Path(report_dir) / f"{run_date.isoformat()}-retrieval-eval-arm-{arm.flag}.md"


def render_arm_report(comparison: ArmComparison, meta: dict) -> str:
    off_score, on_score = comparison.off.run.score, comparison.on.run.score
    deltas = comparison.deltas()
    lines: list[str] = []

    lines.append(f"# Retrieval eval — arm ablation: `{comparison.arm.flag}` — {meta['date']}")
    lines.append("")
    lines.append(f"- run id: `{meta['run_id']}` (recorded {meta['timestamp']})")
    lines.append(f"- git sha: `{meta['git_sha']}`")
    lines.append(f"- embedder fingerprint: `{meta['fingerprint']}` (pinned across both legs)")
    lines.append(
        f"- arm: `{comparison.arm.name}` (flag `{comparison.arm.flag}`), "
        f"activation task `{comparison.arm.activation}`"
    )
    lines.append(f"- weights: off=`{comparison.off.weight}`, on=`{comparison.on.weight}`")
    lines.append(
        f"- corpus: {meta['corpus_entries']} memories, gold v{meta['gold_version']}, "
        f"{meta['n_pairs_authored']} pairs authored ({meta['n_pairs_live']} live)"
    )
    lines.append(
        f"- protocol: k={off_score.k}, min_pairs={off_score.min_pairs}, "
        f"retrieval_limit={off_score.retrieval_limit}"
    )
    lines.append("")
    lines.append(
        "This report states the measured delta only. Whether it clears any "
        "bar, and whether the arm ships at a nonzero weight, is out of scope "
        f"here (runbook §2) -- that judgment belongs to `{comparison.arm.activation}`."
    )
    lines.append("")

    lines.append("## Per-slice delta (off | on | delta)")
    lines.append("")
    header = (
        f"{'slice':<18}{'n':>4}  {'off.mrr':>8} {'on.mrr':>8} {'d.mrr':>9}   "
        f"{'off.hit':>8} {'on.hit':>8} {'d.hit':>9}"
    )
    lines.append(header)
    for tag in sorted(set(off_score.slices) | set(on_score.slices)):
        off_s, on_s = off_score.slices.get(tag), on_score.slices.get(tag)
        d = deltas["slices"][tag]
        lines.append(
            f"{tag:<18}{(off_s.n_pairs if off_s else 0):>4}  "
            f"{_num(off_s.mrr if off_s else None)} {_num(on_s.mrr if on_s else None)} "
            f"{_num(d['mrr'], 9)}   "
            f"{_num(off_s.hit_at_k if off_s else None)} {_num(on_s.hit_at_k if on_s else None)} "
            f"{_num(d['hit_at_k'], 9)}"
        )
    lines.append(
        f"{'AGGREGATE':<18}{off_score.n_pairs:>4}  "
        f"{_num(off_score.aggregate_mrr)} {_num(on_score.aggregate_mrr)} "
        f"{_num(deltas['aggregate']['mrr'], 9)}   "
        f"{_num(off_score.aggregate_hit_at_k)} {_num(on_score.aggregate_hit_at_k)} "
        f"{_num(deltas['aggregate']['hit_at_k'], 9)}"
    )
    lines.append("")

    for label, leg in ((LEG_OFF, comparison.off), (LEG_ON, comparison.on)):
        lines.append(
            f"--- {label} leg (weight={leg.weight}): latency by channel "
            f"(seconds, {leg.run.twin.percentile_method}, "
            f"min_samples={leg.run.twin.min_samples_for_percentile}) ---"
        )
        for name in sorted(leg.run.twin.channels):
            stats = leg.run.twin.channels[name]
            lines.append(f"{name:<18} live   {_pct_line(stats.live)}")
            lines.append(f"{name:<18} cache  {_pct_line(stats.cache)}")
        lines.append(f"--- {label} leg: token cost by purpose ---")
        if not leg.run.twin.tokens_by_purpose:
            lines.append("  (no LLM calls attributed)")
        for purpose in sorted(leg.run.twin.tokens_by_purpose):
            lines.append(f"  {purpose}: {leg.run.twin.tokens_by_purpose[purpose]}")
        lines.append("")

    return "\n".join(lines) + "\n"


# ── orchestration ────────────────────────────────────────────────────────


@dataclass
class ArmAblationResult:
    comparison: ArmComparison
    meta: dict
    report_text: str
    report_path: Path
    ledger_path: Path


async def run_arm_ablation(
    *,
    arm_flag: str,
    weight: float | None = None,
    deepseek_api_key: str | None = None,
    session_factory=bench_db.session_factory,
    cache_dir: str | Path = CACHE_DIR,
    corpus_path: str | Path = retrieval_gold.CORPUS_PATH,
    gold_path: str | Path = retrieval_gold.GOLD_PATH,
    k: int = K,
    min_pairs: int = MIN_PAIRS,
    report_dir: str | Path = REPORT_DIR,
    ledger_path: str | Path = ledger.DEFAULT_PATH,
    now: datetime | None = None,
) -> ArmAblationResult:
    """Reset -> seed -> ingest once, then run ``arm`` off and on over the
    same corpus, in one invocation (brief done-when 1). Mirrors
    ``run_retrieval_eval.run_eval``'s own preamble (reset_bench_db ->
    seed_llm_purpose_configs -> load corpus/gold -> seed_memory_rows ->
    run_ingest(GateConfig())) deliberately kept as a separate copy here
    rather than a shared helper: ``run_eval``'s tests monkeypatch its
    module-level ``TwinningOrchestrator`` name to inject a stub LLM, so
    moving orchestrator construction behind a shared function would break
    that seam. This module owns its own ``TwinningOrchestrator`` name for
    exactly the same reason, tested the same way.
    """
    arm = resolve_ablatable(arm_flag)
    default_probe = (
        LIST_PROBE_WEIGHT if arm.kind == KIND_LIST else DEFAULT_PROBE_WEIGHT
    )
    on_weight = default_probe if weight is None else float(weight)
    if on_weight == 0.0:
        raise ValueError(
            "--weight must be nonzero: weight 0.0 is not an ablation, it is "
            "the off leg"
        )

    # Before the reset and before any model call. An arm whose signal cannot
    # be present would otherwise run to completion and report an exact zero on
    # every slice, which is indistinguishable from a measured "no win" once it
    # reaches the ledger.
    if arm.blocked:
        raise ArmNotMeasurable(
            f"--arm {arm.flag} cannot be measured on this harness: {arm.blocked}"
        )

    api_key = deepseek_api_key or run_smoke.require_deepseek_api_key()
    run_date = (now or datetime.now()).date()

    print(f"[1/4] resetting darkmem_bench and seeding LLM purpose configs (arm={arm.flag})...")
    await bench_db.reset_bench_db()
    await run_smoke.seed_llm_purpose_configs(session_factory, api_key)

    entries = retrieval_gold.load_retrieval_corpus(corpus_path)
    gold = retrieval_gold.load_retrieval_gold(gold_path)
    retrieval_gold.validate_gold_against_corpus(gold, entries)
    pairs = gold["pairs"]
    retrieval_limit = len(entries)
    print(
        f"[2/4] {len(entries)} corpus entries, {len(pairs)} gold pairs, "
        f"gold version {gold.get('version', 'unknown')}."
    )

    async with session_factory() as session:
        llm_config = await get_llm_config(session)

    prepared = await retrieval_gold.seed_memory_rows(session_factory, entries)

    # Three separate orchestrator instances sharing one disk cache directory
    # (module docstring): ingest's cost must not bleed into either leg's
    # twin, and neither leg's cost may bleed into the other's -- each needs
    # its OWN in-memory TokenLedger/live_calls counter, which is per-instance
    # state, while a warm query embedding is still reused across all three
    # via the shared cache_dir.
    ingest_llm = TwinningOrchestrator(llm_config, cache_dir=str(cache_dir))
    ingest_result = await run_ingest(ingest_llm, prepared, GateConfig(), session_factory)
    print(
        f"[3/4] ingested {len(entries)} entries -- live LLM calls: "
        f"{ingest_result.live_calls}, fingerprint: {ingest_result.fingerprint}"
    )

    # A project-scoped arm needs two things this harness did not previously
    # provide, and both fail the same silent way — an exact zero on every
    # slice. First the artefact: the PPR snapshot is built by a Tier-C job
    # that never runs in a bench process, so an unbuilt cache makes the arm
    # contribute nothing. Second the scope: `run_retrieval` queries wide by
    # default, and a wide request skips the arm outright because a snapshot
    # is per project and mass has no meaning across two. Both legs get the
    # same scope, so the delta stays internally consistent.
    leg_filters = None
    if arm.needs_artifact == "ppr_snapshot":
        leg_filters = await _prepare_project_scoped_arm(session_factory)
    elif arm.needs_artifact == "relation_embeddings":
        await _prepare_relation_vectors(session_factory, llm_config, cache_dir)

    off_llm = TwinningOrchestrator(llm_config, cache_dir=str(cache_dir))
    off_leg = await run_arm_leg(
        off_llm, session_factory, pairs, arm=arm, weight=0.0,
        gate_config=ingest_result.gate_config, retrieval_limit=retrieval_limit,
        k=k, min_pairs=min_pairs, filters=leg_filters,
    )

    on_llm = TwinningOrchestrator(llm_config, cache_dir=str(cache_dir))
    on_leg = await run_arm_leg(
        on_llm, session_factory, pairs, arm=arm, weight=on_weight,
        gate_config=ingest_result.gate_config, retrieval_limit=retrieval_limit,
        k=k, min_pairs=min_pairs, filters=leg_filters,
    )
    print(
        f"[4/4] arm={arm.flag}: off n_pairs={off_leg.run.score.n_pairs}, "
        f"on n_pairs={on_leg.run.score.n_pairs}, "
        f"delta(aggregate mrr)={on_leg.run.score.aggregate_mrr!r} - "
        f"{off_leg.run.score.aggregate_mrr!r}"
    )

    comparison = ArmComparison(
        arm=arm, off=off_leg, on=on_leg, ingest_fingerprint=ingest_result.fingerprint,
    )

    meta = {
        "run_id": str(uuid.uuid4()),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "date": run_date.isoformat(),
        "git_sha": run_smoke.git_sha(),
        "fingerprint": ingest_result.fingerprint,
        "arm": arm.name,
        "flag": arm.flag,
        "weight_off": off_leg.weight,
        "weight_on": on_leg.weight,
        "corpus_entries": len(entries),
        "gold_version": gold.get("version", "unknown"),
        "n_pairs_authored": len(pairs),
        "n_pairs_live": off_leg.run.score.n_pairs,
    }

    report_text = render_arm_report(comparison, meta)
    out_path = report_path(run_date, arm, report_dir)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(report_text, encoding="utf-8")

    record_arm_comparison(
        comparison, path=ledger_path,
        metadata={
            "run_id": meta["run_id"], "timestamp": meta["timestamp"],
            "git_sha": meta["git_sha"], "fingerprint": meta["fingerprint"],
        },
    )

    return ArmAblationResult(
        comparison=comparison, meta=meta, report_text=report_text,
        report_path=out_path, ledger_path=Path(ledger_path),
    )
