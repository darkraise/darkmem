"""The Tier-C consolidation ("dreaming") job family umbrella — doc 08 §5.

**Decision (doc 08 §5).** Consolidation is *several* cooperating Tier-C
`JobRegistry` jobs under one logical schedule umbrella, not one monolithic
job — each with its own cron, floor, ceiling, and per-job `asyncio.Lock`.
That gives every member the whole Tier-C discipline already built and
tested (the per-job lock, the `min_interval_seconds` floor, the
`max_run_seconds` ceiling, the `config` row state) while a light dependency
order keeps them cooperating. **No LLM call ever sits on Tier A or Tier B**
(invariant 15) — every job registered here is background-only, and nothing
outside this module and `app.main`'s registration call may reference a
family job (`tests/test_dream_jobs.py` enforces this as a source scan, not
a convention).

T2.08 landed the umbrella only, and every runner started as a
`PlaceholderJobRunner` — a distinct, introspectable type, not a bare
no-op closure — so a later reader can tell "registered but unimplemented"
from "shipped" without reading the body. `SHIPPED_DREAM_JOBS` names the
members whose owning task has since landed:

| Job | Owner | State |
|---|---|---|
| `verification_recompute` | T2.09 | shipped |
| fact lifting | T2.10 | shipped |
| `contradiction_scan` | T2.11 | shipped |
| memory dreaming | T2.12 | shipped |
| `article_synthesis` | T3.02 | shipped |
| `topic_detection` | T2.53 | shipped |

**All six have shipped and the family holds no placeholders**; this row read
`placeholder` from T2.14 until 2026-08-16, through T3.02's landing and past
`SHIPPED_DREAM_JOBS` in this same file already listing the key. Do not read
this table as the authority — `SHIPPED_DREAM_JOBS` is, and
`test_the_family_holds_no_placeholders_left` is what fails if a future member
lands inert. The table is kept for the owner column.

Each owning task replaces its job's `runner=` (and, if it needs one, its
`config_schema=`) with the real implementation; the registration shape,
cron, floor and ceiling here are a starting point tuned from doc 08 §5's
cadence table, not a contract the owning task must preserve verbatim.
`contradiction_scan`'s two fields are the config rows doc 08 §5.3 names by
value (`contradiction_scan_batch`, `contradiction_candidate_top_k`); the
remaining placeholders get a single generic `batch_size` knob, since
doc 08 §5 does not name theirs. **Whoever replaces a `config_schema` here
must also clear any `batch_size` (or other placeholder key) already
persisted in that job's `config` row** — `JobRegistry.set_config` merges
`{**cfg.config, **partial}` and never drops a key on its own, so a stale
placeholder value survives a schema swap silently unless the owning task's
migration/first-run explicitly strips it. T2.10 sidestepped that rather
than solving it: `LIFT_CONFIG_SCHEMA` keeps `batch_size` under its
placeholder key, default and bounds, so no persisted value is orphaned and
none needs stripping. T2.09 does the same: `RECOMPUTE_CONFIG_SCHEMA`'s
`batch_size` field keeps the placeholder's key, default (100) and ceiling
(2000) verbatim, and its two new fields (`slow_arm_batch_size`,
`slow_arm_interval_seconds`) are additions, not renames, so nothing
persisted under the placeholder schema is orphaned by the swap. T2.53
inherits that for free: `TOPIC_DETECTION_CONFIG_SCHEMA`'s `batch_size`
carries the same key, the same default (5) and the same ceiling (100) the
generic placeholder knob had, so no persisted value is orphaned and its
four additional fields are additions rather than renames.
"""
from __future__ import annotations

import logging
from dataclasses import asdict, dataclass


from app.services.article_synthesis import (
    DEFAULT_DEBOUNCE_HOURS,
    run_article_resynthesis,
    run_article_synthesis,
)
from app.services.contradiction_scan import (
    CANDIDATE_TOP_K_KEY,
    CONTRADICTION_SCAN_CONFIG_SCHEMA,
    DEFAULT_CANDIDATE_TOP_K,
    DEFAULT_SCAN_BATCH,
    SCAN_BATCH_KEY,
    run_contradiction_scan,
)
from app.services.fact_lift import (
    DEFAULT_LIFT_BATCH,
    DEFAULT_MIN_ASSERTING_MEMORIES,
    LIFT_CONFIG_SCHEMA,
    run_code_lift,
    run_lift,
)
from app.services.job_registry import FieldDescriptor, Job, JobRegistry, JobRunner
from app.services.memory_community_detection import (
    DEFAULT_BATCH_SIZE as DEFAULT_TOPIC_BATCH_SIZE,
    TOPIC_DETECTION_CONFIG_SCHEMA,
    run_topic_detection,
)
from app.services.memory_dream import (
    MEMORY_DREAM_CONFIG_SCHEMA,
    run_memory_dream,
)
from app.services.verification_recompute import (
    DEFAULT_FAST_BATCH,
    DEFAULT_SLOW_ARM_INTERVAL_SECONDS,
    DEFAULT_SLOW_BATCH,
    RECOMPUTE_CONFIG_SCHEMA,
    run_recompute,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class PlaceholderJobRunner:
    """A registered-but-unimplemented job body.

    Calling it does nothing but log — it exists purely so its job is
    schedulable, lockable, and configurable (T2.08's Done-when) before the
    owning task lands the real work. Structural, not a comment:
    `isinstance(job.runner, PlaceholderJobRunner)` is what
    `tests/test_dream_jobs.py` asserts so a shipped runner can never
    silently keep wearing this marker.
    """

    job_key: str
    owner_task: str

    async def __call__(self) -> None:
        logger.info(
            "Job %s is a T2.08 placeholder awaiting %s; no-op run",
            self.job_key, self.owner_task,
        )


VERIFICATION_RECOMPUTE_JOB_KEY = "verification_recompute"
FACT_LIFT_JOB_KEY = "fact_lift"
CONTRADICTION_SCAN_JOB_KEY = "contradiction_scan"
MEMORY_DREAM_JOB_KEY = "memory_dream"
ARTICLE_SYNTHESIS_JOB_KEY = "article_synthesis"
TOPIC_DETECTION_JOB_KEY = "topic_detection"

# Doc 08 §5's table, keyed by job so the placeholder marker and the
# registration below can never drift from the owner list.
DREAM_JOB_OWNERS: dict[str, str] = {
    FACT_LIFT_JOB_KEY: "T2.10",
    VERIFICATION_RECOMPUTE_JOB_KEY: "T2.09",
    CONTRADICTION_SCAN_JOB_KEY: "T2.11",
    MEMORY_DREAM_JOB_KEY: "T2.12",
    TOPIC_DETECTION_JOB_KEY: "T2.53",
    ARTICLE_SYNTHESIS_JOB_KEY: "T3.02",
}

DREAM_JOB_KEYS: tuple[str, ...] = tuple(DREAM_JOB_OWNERS)

# The members whose owning task has landed, mapped to the module holding the
# runner's real body. Structural, like the marker it complements:
# `tests/test_dream_jobs.py` asserts both directions off this mapping, so a
# shipped job can never regress to a placeholder and a placeholder can never be
# mistaken for shipped.
#
# **The module name is not decoration.** Invariant 15's source scan derives the
# modules it forbids the hot path from importing out of this file's own
# imports; the values here are what pins that derivation to the jobs it is
# meant to cover, so a member wired without an umbrella import fails the guard
# instead of quietly losing it. A later member adds its key and its module here
# in the same edit that replaces its `PlaceholderJobRunner`.
SHIPPED_DREAM_JOBS: dict[str, str] = {
    ARTICLE_SYNTHESIS_JOB_KEY: "article_synthesis",
    FACT_LIFT_JOB_KEY: "fact_lift",
    VERIFICATION_RECOMPUTE_JOB_KEY: "verification_recompute",
    CONTRADICTION_SCAN_JOB_KEY: "contradiction_scan",
    MEMORY_DREAM_JOB_KEY: "memory_dream",
    TOPIC_DETECTION_JOB_KEY: "memory_community_detection",
}


_GENERIC_PLACEHOLDER_HELP = (
    "Placeholder tuning knob so the job is configurable before its owning "
    "task lands; that task may replace this schema."
)


def _placeholder_job(
    key: str,
    display_name: str,
    description: str,
    *,
    default_cron: str,
    min_interval_seconds: int,
    max_run_seconds: float,
    config_schema: list[FieldDescriptor],
) -> Job:
    return Job(
        key=key,
        display_name=display_name,
        description=description,
        default_cron=default_cron,
        min_interval_seconds=min_interval_seconds,
        runner=PlaceholderJobRunner(key, DREAM_JOB_OWNERS[key]),
        max_run_seconds=max_run_seconds,
        config_schema=config_schema,
    )


def _make_lift_runner(registry: JobRegistry, key: str) -> JobRunner:
    """The fact-lifting tick, bound to the registry's own session factory.

    The runner reads its thresholds from the job's `config` row on every tick
    rather than closing over them, so an operator edit takes effect on the next
    run without a restart. It opens and commits its own session: the registry
    hands the runner nothing, and a lift that never commits would re-derive the
    same candidates forever.
    """
    async def run() -> None:
        cfg = await registry.load_config(key)
        settings = {**registry.get(key).default_config, **cfg.config}
        async with registry.session_factory() as session:
            batch_size = int(settings.get("batch_size", DEFAULT_LIFT_BATCH))
            outcome = await run_lift(
                session,
                batch_size=batch_size,
                min_asserting_memories=int(
                    settings.get("min_asserting_memories", DEFAULT_MIN_ASSERTING_MEMORIES)
                ),
            )
            # The code half rides the same tick and the same `batch_size`
            # rather than its own job (doc 10 §6 assigns the lift to
            # consolidation, and a second job key would be a seventh family
            # member the invariant-15 scan derives from this module's imports).
            # `min_asserting_memories` is the memory half's salience bar and
            # has no code analogue: a repository's import either exists or does
            # not, so there is no count to threshold.
            code = await run_code_lift(session, batch_size=batch_size)
            await session.commit()
        logger.info(
            "Fact lifting scanned %d candidate(s): %d fact(s) created, "
            "%d source(s) added, %d sources_changed event(s) emitted",
            outcome.candidates, outcome.facts_created,
            outcome.sources_added, outcome.events_emitted,
        )
        logger.info(
            "Code fact lifting scanned %d candidate(s): %d fact(s) born "
            "corroborated, %d source(s) added, %d source(s) withdrawn, "
            "%d fact(s) invalidated, %d rung(s) restored",
            code.candidates, code.facts_created, code.sources_added,
            code.sources_withdrawn, code.facts_invalidated,
            code.rungs_restored,
        )

    return run


def _make_recompute_runner(registry: JobRegistry, key: str) -> JobRunner:
    """The verification recompute tick, bound to the registry's own session
    factory. Mirrors ``_make_lift_runner``: config is re-read every tick
    rather than closed over, and the runner opens and commits its own
    session so an operator's config edit takes effect on the next run
    without a restart.
    """
    async def run() -> None:
        cfg = await registry.load_config(key)
        settings_ = {**registry.get(key).default_config, **cfg.config}
        async with registry.session_factory() as session:
            outcome = await run_recompute(
                session,
                batch_size=int(settings_.get("batch_size", DEFAULT_FAST_BATCH)),
                slow_arm_batch_size=int(
                    settings_.get("slow_arm_batch_size", DEFAULT_SLOW_BATCH)
                ),
                slow_arm_interval_seconds=int(
                    settings_.get(
                        "slow_arm_interval_seconds", DEFAULT_SLOW_ARM_INTERVAL_SECONDS
                    )
                ),
            )
            await session.commit()
        logger.info(
            "Verification recompute drained %d sources_changed event(s) "
            "touching %d fact(s): %d recomputed (%d failed, %d skipped dead), "
            "%d transition(s). Slow arm %s: scanned %d fact(s), healed %d "
            "(%d skipped dead)%s",
            outcome.drain.events_scanned, outcome.drain.facts_touched,
            outcome.drain.facts_recomputed, outcome.drain.facts_failed,
            outcome.drain.facts_skipped_expired, outcome.drain.transitions,
            "ran" if outcome.slow_arm_ran else "skipped (not due)",
            outcome.reconcile.facts_scanned, outcome.reconcile.facts_healed,
            outcome.reconcile.facts_skipped_expired,
            " (wrapped to start)" if outcome.reconcile.wrapped else "",
        )

    return run


# The rotation cursor, in its own `config` row rather than in the job's
# `config` dict. Same reasoning `verification_recompute` records for its
# watermark: `JobRegistry.set_config` validates every write against the job's
# schema and is the operator-facing surface behind
# `PUT /api/v1/jobs/{key}/config`, so a cursor routed through `cfg.config`
# would either be rejected as an unknown key or — if added to the schema to
# make it pass — become an operator-editable field. It is neither a tunable
# nor a thing an operator should set to an arbitrary project name.
_TOPIC_STATE_CONFIG_KEY = "topic_detection_state"


async def _load_topic_cursor(session) -> str | None:
    from sqlalchemy import select

    from app.models.config import Config

    row = (
        await session.execute(select(Config).where(Config.key == _TOPIC_STATE_CONFIG_KEY))
    ).scalar_one_or_none()
    if row is None or not isinstance(row.value, dict):
        return None
    cursor = row.value.get("last_project")
    return cursor if isinstance(cursor, str) and cursor else None


async def _save_topic_cursor(session, last_project: str | None) -> None:
    from sqlalchemy import select

    from app.models.config import Config

    row = (
        await session.execute(select(Config).where(Config.key == _TOPIC_STATE_CONFIG_KEY))
    ).scalar_one_or_none()
    value = {"last_project": last_project}
    if row is None:
        session.add(Config(key=_TOPIC_STATE_CONFIG_KEY, value=value))
    else:
        row.value = value


def _make_topic_runner(registry: JobRegistry, key: str, llm_provider) -> JobRunner:
    """The topic-detection tick (T2.53), bound to the registry's session factory.

    Config is re-read every tick rather than closed over, so an operator's edit
    takes effect on the next run without a restart — the same shape the lift
    and recompute runners carry.

    **The cursor is saved even when the batch partly failed.**
    ``run_topic_detection`` advances ``last_project`` per project *before*
    attempting it and swallows a per-project failure into ``skipped``, so the
    outcome's cursor names the last project *visited*, not the last one that
    succeeded. Persisting it regardless is what keeps the rotation moving: a
    project that fails deterministically would otherwise pin the cursor and
    starve every project behind it, which is the failure this job's whole
    rotating design exists to avoid. The failure itself is not lost — the
    detector journals an abort per project from its own session.
    """
    async def run() -> None:
        cfg = await registry.load_config(key)
        settings_ = {**registry.get(key).default_config, **cfg.config}
        async with registry.session_factory() as session:
            after_project = await _load_topic_cursor(session)

        knobs = {
            field.key: settings_[field.key]
            for field in TOPIC_DETECTION_CONFIG_SCHEMA
            if field.key != "batch_size" and field.key in settings_
        }
        batch_size = int(settings_.get("batch_size", DEFAULT_TOPIC_BATCH_SIZE))
        outcome = await run_topic_detection(
            registry.session_factory,
            llm_provider,
            batch_size=batch_size,
            after_project=after_project,
            **knobs,
        )

        # **The rotation has to wrap, or the job goes inert after one pass.**
        # `next_projects` selects strictly `project > :after_project`, so once
        # the cursor reaches the lexicographically last project every later
        # tick claims nothing — forever, while still logging and recording
        # `last_status="ok"`. A project created after that point sorts before
        # the cursor and is never detected at all. A short batch means the end
        # of the rotation was reached, so the cursor resets and the next tick
        # starts from the beginning. This mirrors `verification_recompute`'s
        # slow arm, which resets on `len(rows) < batch_size` for the same
        # reason — the precedent this runner's cursor was modelled on, and the
        # half of it the first version missed.
        wrapped = outcome.visited < batch_size
        cursor = None if wrapped else outcome.last_project

        async with registry.session_factory() as session:
            await _save_topic_cursor(session, cursor)
            await session.commit()

        logger.info(
            "Topic detection visited %d project(s) from cursor %r: %d "
            "communities written, %d skipped; cursor now %r%s",
            outcome.visited, after_project, outcome.communities,
            outcome.skipped, cursor,
            " (wrapped to start)" if wrapped else "",
        )

    return run


def _make_dream_runner(
    registry: JobRegistry, key: str, llm_provider
) -> JobRunner:
    """The dreaming tick, bound to the registry's own session factory.

    The provider is a callable rather than an orchestrator instance because
    `app.state.llm` is replaced whole on a config save, so a closed-over
    instance goes stale and keeps dispatching at the previous configuration.
    The runner owns its sessions: it opens one per phase and commits each,
    since a read transaction held across the model fan-out would sit
    `idle in transaction` for minutes.
    """
    async def run() -> None:
        cfg = await registry.load_config(key)
        settings_ = {**registry.get(key).default_config, **cfg.config}
        outcome = await run_memory_dream(
            registry.session_factory,
            llm_provider,
            batch_size=int(settings_.get("batch_size", 50)),
            pair_candidates=int(settings_.get("pair_candidates", 5)),
            near_duplicate_threshold_pct=int(
                settings_.get("near_duplicate_threshold_pct", 92)
            ),
            judge_fanout=int(settings_.get("judge_fanout", 25)),
            refine_batch=int(settings_.get("refine_batch", 25)),
            write_batch=int(settings_.get("write_batch", 25)),
            llm_concurrency=int(settings_.get("llm_concurrency", 4)),
            derivation_enabled=int(settings_.get("derivation_enabled", 1)),
            overlap_threshold_pct=int(settings_.get("overlap_threshold_pct", 50)),
            proximity_threshold_pct=int(
                settings_.get("proximity_threshold_pct", 85)
            ),
            derivation_batch=int(settings_.get("derivation_batch", 200)),
            derivation_hot_entity_cap=int(
                settings_.get("derivation_hot_entity_cap", 50)
            ),
            derivation_neighbours=int(
                settings_.get("derivation_neighbours", 5)
            ),
        )
        logger.info(
            "Memory dreaming visited %d seed(s): %d subsumed, %d associated "
            "(%d unchanged), %d refined, %d stale-skipped, %d failed; "
            "%d edge(s) derived from %d candidate(s) (%d truncated), "
            "%d stripped, %d spared as unmeasured%s",
            outcome.seeds_visited, outcome.subsumed, outcome.associated,
            outcome.associate_unchanged, outcome.refined,
            outcome.stale_skipped, outcome.failed,
            outcome.derived, outcome.derivation_candidates,
            outcome.candidates_truncated, outcome.derivation_stripped,
            outcome.derivation_spared_unmeasured,
            f", skipped: {outcome.skipped_reason}" if outcome.skipped_reason else "",
        )

    return run


def _make_contradiction_runner(
    registry: JobRegistry, key: str, llm_provider
) -> JobRunner:
    """The contradiction-scan tick, bound to the registry's session factory.

    The provider is a callable for the same reason the dreaming pass takes one:
    `app.state.llm` is replaced whole on a config save, so a closed-over
    orchestrator keeps dispatching at the previous configuration. The scan owns
    its sessions rather than being handed one — its adjudication phase is a
    model fan-out, and a session held across that would sit idle in transaction
    for as long as the provider takes.
    """
    async def run() -> None:
        cfg = await registry.load_config(key)
        settings_ = {**registry.get(key).default_config, **cfg.config}
        outcome = await run_contradiction_scan(
            registry.session_factory,
            llm_provider,
            batch_size=int(settings_.get(SCAN_BATCH_KEY, DEFAULT_SCAN_BATCH)),
            top_k=int(settings_.get(CANDIDATE_TOP_K_KEY, DEFAULT_CANDIDATE_TOP_K)),
        )
        logger.info(
            "Contradiction scan drained %d event(s) touching %d fact(s): "
            "%d checked (%d unservable), %d candidate(s) over %d judged pair(s) "
            "-> %d dispute(s), %d clear(s). Misses %d "
            "(%d incomplete, %d unscanned, %d truncated, %d refused, "
            "%d failed, %d invalid); watermark %s%s",
            outcome.events_scanned, outcome.facts_touched,
            outcome.facts_checked, outcome.facts_skipped_unservable,
            outcome.candidates_generated, outcome.pairs_judged,
            outcome.disputes_recorded, outcome.clears_recorded,
            outcome.misses, outcome.facts_incomplete, outcome.facts_unscanned,
            outcome.candidates_truncated, outcome.judge_refused,
            outcome.judge_failed, outcome.judge_invalid,
            "advanced" if outcome.watermark_advanced else "held",
            f", skipped: {outcome.skipped_reason}" if outcome.skipped_reason else "",
        )

    return run


def _generic_batch_schema(default: int, maximum: int) -> list[FieldDescriptor]:
    return [FieldDescriptor(
        key="batch_size", label="Batch Size", default=default,
        min=1, max=maximum, help=_GENERIC_PLACEHOLDER_HELP,
    )]


ARTICLE_SYNTHESIS_CONFIG_SCHEMA: list[FieldDescriptor] = [
    FieldDescriptor(
        key="batch_size", label="Projects Per Run", default=10, min=1, max=200,
        help=(
            "How many projects one tick rotates over. Bounds *projects*, not "
            "subjects — the per-project subject budget is `synthesis_budget` "
            "on the `article_selection` config row (T3.01), so the two knobs "
            "compose rather than contradict. Keeps the placeholder's key, "
            "default and ceiling so no persisted value is orphaned."
        ),
    ),
    FieldDescriptor(
        key="hub_cap", label="Facts Per Article", default=40, min=1, max=200,
        help=(
            "Doc 09 §4.2's top-K cap. A cost knob as much as a length one: an "
            "article's claim count is bounded by its fact count, so this "
            "bounds T3.03's per-claim entailment bill too."
        ),
    ),
    FieldDescriptor(
        key="length_budget_words", label="Length Budget (words)",
        default=400, min=50, max=5000,
        help=(
            "Doc 09 §4.2's length budget, asked for in the prompt. The hard "
            "ceiling the response is held to is 1.5x this; an ordinary "
            "overrun is absorbed, one that ignored the instruction is refused."
        ),
    ),
    FieldDescriptor(
        key="debounce_hours", label="Re-synthesis Quiet Period (hours)",
        default=DEFAULT_DEBOUNCE_HOURS, min=1, max=8760,
        help=(
            "Doc 09 §4.4's quiet period (T3.05). A stale article re-synthesises "
            "only once its fact set has held the same shape for this long, so a "
            "burst of corroborations produces one re-synthesis rather than one "
            "per tick. A window shorter than the job's own cadence damps "
            "nothing — the tick is already the sampling rate."
        ),
    ),
]


def _make_article_runner(registry: JobRegistry, key: str, llm_provider) -> JobRunner:
    """The article-synthesis tick (T3.02), bound to the registry's factory.

    Config is re-read every tick rather than closed over, so an operator's edit
    takes effect on the next run without a restart — the shape every sibling
    runner here carries.

    **The cursor advances over projects visited, not projects that succeeded**,
    for the reason `_make_topic_runner` states: a project failing
    deterministically would otherwise pin the rotation and starve every project
    behind it.
    """
    async def run() -> dict:
        cfg = await registry.load_config(key)
        settings_ = {**registry.get(key).default_config, **cfg.config}
        async with registry.session_factory() as session:
            after_project = await _load_article_cursor(session)

        batch_size = int(settings_.get("batch_size", 10))
        outcome = await run_article_synthesis(
            registry.session_factory,
            llm_provider,
            batch_size=batch_size,
            after_project=after_project,
            hub_cap=int(settings_.get("hub_cap", 40)),
            budget_words=int(settings_.get("length_budget_words", 400)),
        )
        # T3.05's second pass, over the batch the first pass rotated onto — new
        # articles first, then the standing ones whose knowledge moved. The
        # order matters only in that a subject cannot be in both: the selector
        # excludes subjects holding a live article, and this pass reads only
        # subjects that hold one.
        resynthesis = await run_article_resynthesis(
            registry.session_factory,
            llm_provider,
            projects=outcome.visited,
            debounce_hours=float(settings_.get("debounce_hours", DEFAULT_DEBOUNCE_HOURS)),
            hub_cap=int(settings_.get("hub_cap", 40)),
            budget_words=int(settings_.get("length_budget_words", 400)),
        )
        # The same wrap as `_make_topic_runner`'s, for the same reason: the
        # sweep reads strictly past the cursor and echoes it back when nothing
        # remains, so saving it unchanged parks the job on the last project.
        wrapped = len(outcome.visited) < batch_size
        async with registry.session_factory() as session:
            await _save_article_cursor(session, None if wrapped else outcome.last_project)
            await session.commit()
        logger.info(
            "article_synthesis: projects=%d attempted=%d written=%d refused=%d; "
            "resynthesis: stale=%d debounced=%d attempted=%d resynthesised=%d "
            "held=%d over_budget=%d failed=%d%s",
            outcome.projects, outcome.attempted, outcome.written, outcome.refused,
            resynthesis.stale, resynthesis.debounced, resynthesis.attempted,
            resynthesis.resynthesised, resynthesis.held, resynthesis.over_budget,
            resynthesis.failed,
            ", rotation wrapped" if wrapped else "",
        )
        return {"synthesis": asdict(outcome), "resynthesis": asdict(resynthesis)}

    return run


_ARTICLE_STATE_CONFIG_KEY = "article_synthesis_state"


async def _load_article_cursor(session) -> str | None:
    from sqlalchemy import select

    from app.models.config import Config

    row = (
        await session.execute(
            select(Config).where(Config.key == _ARTICLE_STATE_CONFIG_KEY)
        )
    ).scalar_one_or_none()
    if row is None or not isinstance(row.value, dict):
        return None
    cursor = row.value.get("last_project")
    return cursor if isinstance(cursor, str) and cursor else None


async def _save_article_cursor(session, last_project: str | None) -> None:
    """Persist the rotation cursor; ``None`` restarts the rotation."""
    from sqlalchemy import select

    from app.models.config import Config

    row = (
        await session.execute(
            select(Config).where(Config.key == _ARTICLE_STATE_CONFIG_KEY)
        )
    ).scalar_one_or_none()
    value = {"last_project": last_project}
    if row is None:
        session.add(Config(key=_ARTICLE_STATE_CONFIG_KEY, value=value))
    else:
        row.value = value


def register_dream_jobs(registry: JobRegistry, llm_provider=None) -> None:
    """Register the six-member consolidation family (doc 08 §5).

    Staggered so a single worker never stampedes (§5.1): `fact_lift` and
    `verification_recompute` are frequent (no LLM call), `contradiction_scan`
    and the dreaming pass are slow LLM passes, and `topic_detection` /
    `article_synthesis` are daily, offset from each other. `llm_provider` is a
    callable returning the live orchestrator (or ``None`` in Postgres-only
    mode), passed rather than closed over because `app.state.llm` is replaced
    whole on a config save; the members whose task has not landed are still
    `PlaceholderJobRunner`s (`DREAM_JOB_OWNERS`).
    """
    registry.register(Job(
        key=FACT_LIFT_JOB_KEY,
        display_name="Fact Lift",
        description=(
            "Turns extracted graph relations into candidate facts."
        ),
        default_cron="*/15 * * * *",
        min_interval_seconds=60,
        runner=_make_lift_runner(registry, FACT_LIFT_JOB_KEY),
        max_run_seconds=300,
        config_schema=LIFT_CONFIG_SCHEMA,
    ))
    registry.register(Job(
        key=VERIFICATION_RECOMPUTE_JOB_KEY,
        display_name="Verification Recompute",
        description=(
            "Recomputes each fact's verification status when its sources "
            "change."
        ),
        default_cron="*/2 * * * *", min_interval_seconds=30,
        runner=_make_recompute_runner(registry, VERIFICATION_RECOMPUTE_JOB_KEY),
        max_run_seconds=120,
        config_schema=RECOMPUTE_CONFIG_SCHEMA,
    ))
    registry.register(Job(
        key=CONTRADICTION_SCAN_JOB_KEY,
        display_name="Contradiction Scan",
        description=(
            "Checks facts for contradictions with a model and flags suspected "
            "ones for review."
        ),
        default_cron="0 */6 * * *", min_interval_seconds=300,
        runner=_make_contradiction_runner(
            registry, CONTRADICTION_SCAN_JOB_KEY, llm_provider
        ),
        max_run_seconds=1800,
        # Doc 08 §5.3 names these two rows by value and no third; the schema
        # keeps the placeholder's two keys, defaults and bounds verbatim, so no
        # value an operator already persisted is orphaned by this swap.
        config_schema=CONTRADICTION_SCAN_CONFIG_SCHEMA,
    ))
    registry.register(Job(
        key=MEMORY_DREAM_JOB_KEY,
        display_name="Memory Dream",
        description=(
            "Retires duplicate memories, refreshes summaries and links "
            "near-duplicates. Every change can be undone."
        ),
        default_cron="0 3 * * *", min_interval_seconds=300,
        runner=_make_dream_runner(
            registry, MEMORY_DREAM_JOB_KEY, llm_provider
        ),
        max_run_seconds=1800,
        config_schema=MEMORY_DREAM_CONFIG_SCHEMA,
    ))
    registry.register(Job(
        key=TOPIC_DETECTION_JOB_KEY,
        display_name="Topic Detection",
        description=(
            "Groups each project's graph into topics, a few projects per run."
        ),
        default_cron="0 4 * * *", min_interval_seconds=300,
        runner=_make_topic_runner(registry, TOPIC_DETECTION_JOB_KEY, llm_provider),
        max_run_seconds=900,
        # T2.18's own schema, not the generic batch stand-in the placeholder
        # carried: the detector has four knobs beyond batch size, and an
        # operator editing `hub_cap` through `PUT /jobs/{key}/config` would
        # have been rejected as an unknown key by the placeholder's schema.
        config_schema=TOPIC_DETECTION_CONFIG_SCHEMA,
    ))
    registry.register(Job(
        key=ARTICLE_SYNTHESIS_JOB_KEY,
        display_name="Article Synthesis",
        description=(
            "Writes a summary article for each subject from its verified "
            "facts."
        ),
        default_cron="0 5 * * *", min_interval_seconds=300,
        runner=_make_article_runner(registry, ARTICLE_SYNTHESIS_JOB_KEY, llm_provider),
        max_run_seconds=900,
        # T3.02's own schema. `batch_size` keeps the placeholder's key, default
        # (10) and ceiling (200) verbatim — `set_config` merges and never drops
        # a key, so a renamed or removed field would orphan a persisted value
        # silently. The two additions are additions, not renames.
        config_schema=ARTICLE_SYNTHESIS_CONFIG_SCHEMA,
    ))
