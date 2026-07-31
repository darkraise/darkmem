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

This module lands the umbrella only. Every runner below is a
`PlaceholderJobRunner` — a distinct, introspectable type, not a bare
no-op closure — so a later reader can tell "registered but unimplemented"
from "shipped" without reading the body:

| Job | Owner |
|---|---|
| `verification_recompute` | T2.09 |
| `fact_lift` | T2.10 |
| `contradiction_scan` | T2.11 |
| `memory_dream` | T2.12 |
| `article_synthesis` | T3.02 |
| `topic_detection` | T2.53 |

Each owning task replaces its job's `runner=` (and, if it needs one, its
`config_schema=`) with the real implementation; the registration shape,
cron, floor and ceiling here are a starting point tuned from doc 08 §5's
cadence table, not a contract the owning task must preserve verbatim.
`contradiction_scan`'s two fields are the config rows doc 08 §5.3 names by
value (`contradiction_scan_batch`, `contradiction_candidate_top_k`); the
other five jobs get a single generic `batch_size` placeholder knob, since
doc 08 §5 does not name theirs. **Whoever replaces a `config_schema` here
must also clear any `batch_size` (or other placeholder key) already
persisted in that job's `config` row** — `JobRegistry.set_config` merges
`{**cfg.config, **partial}` and never drops a key on its own, so a stale
placeholder value survives a schema swap silently unless the owning task's
migration/first-run explicitly strips it.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass

from app.services.job_registry import FieldDescriptor, Job, JobRegistry

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


def _generic_batch_schema(default: int, maximum: int) -> list[FieldDescriptor]:
    return [FieldDescriptor(
        key="batch_size", label="Batch Size", default=default,
        min=1, max=maximum, help=_GENERIC_PLACEHOLDER_HELP,
    )]


def register_dream_jobs(registry: JobRegistry) -> None:
    """Register the six-member consolidation family (doc 08 §5).

    Staggered so a single worker never stampedes (§5.1): `fact_lift` and
    `verification_recompute` are frequent (no LLM call), `contradiction_scan`
    and `memory_dream` are slow LLM passes, and `topic_detection` /
    `article_synthesis` are daily, offset from `memory_dream` and from each
    other. Every runner is a `PlaceholderJobRunner` — T2.08 lands only the
    umbrella; each job's real work ships from its own task (`DREAM_JOB_OWNERS`).
    """
    registry.register(_placeholder_job(
        FACT_LIFT_JOB_KEY, "Fact Lift",
        "Derives Layer-2 candidate facts and their fact_sources from the "
        "Layer-1 candidate graph, then runs the two temporal passes "
        f"(doc 08 §5.2). Placeholder — real work lands in "
        f"{DREAM_JOB_OWNERS[FACT_LIFT_JOB_KEY]}.",
        default_cron="*/15 * * * *", min_interval_seconds=60,
        max_run_seconds=300,
        config_schema=_generic_batch_schema(default=50, maximum=1000),
    ))
    registry.register(_placeholder_job(
        VERIFICATION_RECOMPUTE_JOB_KEY, "Verification Recompute",
        "Drains sources_changed, counts distinct origins, applies the "
        "contradiction veto and hysteresis (doc 08 §4.3). Placeholder — "
        f"real work lands in {DREAM_JOB_OWNERS[VERIFICATION_RECOMPUTE_JOB_KEY]}.",
        default_cron="*/2 * * * *", min_interval_seconds=30,
        max_run_seconds=120,
        config_schema=_generic_batch_schema(default=100, maximum=2000),
    ))
    registry.register(_placeholder_job(
        CONTRADICTION_SCAN_JOB_KEY, "Contradiction Scan",
        "LLM contradiction check over same-endpoint and pg_trgm candidates, "
        "feeding disputes into the verification veto (doc 08 §5.3). "
        f"Placeholder — real work lands in "
        f"{DREAM_JOB_OWNERS[CONTRADICTION_SCAN_JOB_KEY]}.",
        default_cron="0 */6 * * *", min_interval_seconds=300,
        max_run_seconds=1800,
        # Doc 08 §5.3 names these two rows by value ("bounded by
        # contradiction_scan_batch (facts per cycle) and
        # contradiction_candidate_top_k (candidates per fact), both config
        # rows") — matched verbatim rather than the generic batch_size knob.
        config_schema=[
            FieldDescriptor(
                key="contradiction_scan_batch", label="Facts Per Cycle",
                default=20, min=1, max=500,
                help="Facts drained and checked per contradiction_scan run.",
            ),
            FieldDescriptor(
                key="contradiction_candidate_top_k", label="Candidates Per Fact",
                default=10, min=1, max=100,
                help="pg_trgm shortlist size per fact needing a check.",
            ),
        ],
    ))
    registry.register(_placeholder_job(
        MEMORY_DREAM_JOB_KEY, "Memory Dream",
        "Dedups via supersede(), refines derived enrichment, derives "
        "associative memory-relation edges (doc 08 §5.4/§5.5). "
        f"Placeholder — real work lands in "
        f"{DREAM_JOB_OWNERS[MEMORY_DREAM_JOB_KEY]}.",
        default_cron="0 3 * * *", min_interval_seconds=300,
        max_run_seconds=1800,
        config_schema=_generic_batch_schema(default=50, maximum=1000),
    ))
    registry.register(_placeholder_job(
        TOPIC_DETECTION_JOB_KEY, "Topic Detection",
        "Leiden community detection per active project and report_string "
        "generation (doc 06 mechanics, scheduled under this umbrella per "
        f"doc 08 §5.6). Placeholder — real work lands in "
        f"{DREAM_JOB_OWNERS[TOPIC_DETECTION_JOB_KEY]}.",
        default_cron="0 4 * * *", min_interval_seconds=300,
        max_run_seconds=900,
        config_schema=_generic_batch_schema(default=5, maximum=100),
    ))
    registry.register(_placeholder_job(
        ARTICLE_SYNTHESIS_JOB_KEY, "Article Synthesis",
        "Re-synthesises stale articles on fact_set_hash change, debounced "
        "(doc 09 mechanics, triggered under this umbrella per doc 08 §5.6). "
        f"Placeholder inert (T2.14) — productive runs land in "
        f"{DREAM_JOB_OWNERS[ARTICLE_SYNTHESIS_JOB_KEY]}.",
        default_cron="0 5 * * *", min_interval_seconds=300,
        max_run_seconds=900,
        config_schema=_generic_batch_schema(default=10, maximum=200),
    ))
