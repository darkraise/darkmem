"""Per-article claim-support coverage, as a distribution (T3.24, doc 20 §4).

**Plumbing, not judgment.** This module produces numbers; it renders no
pass/fail verdict. T3.22 (Fable, adversarial) reads what this emits and
writes G-E's verdict — runbook §2's standing rule that measurement design
and measurement plumbing are different tasks, and the same split
`promotion_metrics` holds for G-C. The bars are *reported* here because a
"share at or above the threshold" is not defined without one, and because a
probe whose threshold drifted from the runtime's would be measuring a bar
nobody enforces. They are never applied to produce a verdict.

**A distribution, not a mean**, which is G-E's whole shape: one
well-covered article does not clear this gate, and a mean hides the tail
that decides it. Percentiles are **nearest-rank over actual observations**,
never interpolated. At the article counts this will first run against, an
interpolated p90 is a number no article has, sitting between two that do —
and the question G-E asks is how many *articles* clear the bar.

**Unmeasured is not zero, and this is the module's spine** (T3.03's own
ruling, inherited rather than re-decided). `knowledge_articles.confidence`
is the coverage column and `write_coverage` writes it only on a measured
outcome, so NULL means "the entailment pass reached no verdict on this
prose" — a refusing judge, an outage and an invalid verdict all land there.
None of those is evidence that an article is ungrounded. So unmeasured
articles are counted and reported as their own population and are **never**
folded into the distribution as zeros, which would manufacture a low
coverage number out of a judge that never ran.

That is not a corner case today: G-D is open, `VerificationJudge.judge()`
refuses unconditionally without a qualification record, and so **every
article in existence is unmeasured**. A first run against production is
expected to report a measured population of zero and say so, exactly as
T2.40's G-C run reported *not evaluable* rather than inventing a verdict.

**Reproducible against a named snapshot** (done-when 3). The read is of a
live table that moves, so the report records what it read: a caller-supplied
snapshot name plus a `population_sha256` over the (id, coverage) pairs. Two
runs reporting the same share mean the same thing only if they also report
the same population hash, and a reader can tell without re-querying.
"""
from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from benchlib.coverage_bars import COVERAGE_BAR_DEFAULTS

# Below this many *measured* articles the share is reported as under-powered
# rather than as a percentage. Same value and same reasoning as
# `promotion_metrics.UNDER_POWERED_THRESHOLD`: a share over four articles is
# a number whose confidence interval spans the bar, and reporting it bare
# invites a verdict the data cannot support.
UNDER_POWERED_THRESHOLD = 5

REPORTED_PERCENTILES = (0, 10, 25, 50, 75, 90, 100)

# The live population, matching `ux_knowledge_articles_live`'s own predicate
# rather than restating it as `status = 'candidate'`-and-friends. A superseded
# article is a previous version of a subject that a re-synthesis retired; it
# is not withheld work and counting it would measure history.
_LIVE_ARTICLES_SQL = text(
    """
    SELECT id::text AS id, project, subject_key, confidence AS coverage
    FROM knowledge_articles
    WHERE status <> 'superseded'
    ORDER BY id
    """
)


@dataclass(frozen=True)
class CoverageDistributionReport:
    snapshot: str
    database_identity: str
    schema_present: bool
    read_at: datetime
    live_articles: int
    measured_articles: int
    unmeasured_articles: int
    percentiles: dict[int, float]
    at_or_above_threshold: int
    corpus_share: float | None
    threshold: float
    corpus_share_bar: float
    population_sha256: str
    under_powered: bool
    notes: tuple[str, ...]


def percentile(values: list[float], p: float) -> float:
    """Nearest-rank percentile: always an observation, never between two.

    ``p = 0`` is the minimum and ``p = 100`` the maximum. Deliberately not
    ``statistics.quantiles``, whose interpolation would report a coverage no
    article has — see the module docstring.
    """
    if not values:
        raise ValueError("percentile of an empty population is undefined")
    ordered = sorted(values)
    rank = math.ceil((p / 100) * len(ordered))
    return ordered[min(max(rank - 1, 0), len(ordered) - 1)]


def population_hash(rows: list[dict]) -> str:
    """Digest of exactly what was read, so a share is attributable.

    Covers the unmeasured articles too, by their NULL: a run whose measured
    set is identical but which saw ten more unmeasured articles read a
    different corpus, and the share it reports means something different.
    """
    basis = sorted((row["id"], row["coverage"]) for row in rows)
    return hashlib.sha256(
        json.dumps(basis, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def summarise(
    rows: list[dict],
    *,
    snapshot: str,
    database_identity: str,
    read_at: datetime,
    threshold: float | None = None,
    corpus_share_bar: float | None = None,
) -> CoverageDistributionReport:
    threshold = (
        COVERAGE_BAR_DEFAULTS["article_coverage_threshold"]
        if threshold is None else threshold
    )
    corpus_share_bar = (
        COVERAGE_BAR_DEFAULTS["article_coverage_corpus_share"]
        if corpus_share_bar is None else corpus_share_bar
    )

    measured = [row["coverage"] for row in rows if row["coverage"] is not None]
    unmeasured = len(rows) - len(measured)
    at_or_above = sum(1 for value in measured if value >= threshold)

    notes: list[str] = []
    if not measured:
        notes.append(
            "No article carries a coverage number. With G-D open the "
            "entailment judge refuses unconditionally, so this is the "
            "expected standing state rather than a fault — and it is NOT a "
            "coverage of zero. G-E is not evaluable on this snapshot."
        )
    elif len(measured) < UNDER_POWERED_THRESHOLD:
        notes.append(
            f"Only {len(measured)} measured article(s), below the "
            f"under-powered threshold of {UNDER_POWERED_THRESHOLD}. The share "
            f"is reported for completeness and cannot carry a verdict."
        )
    if unmeasured:
        notes.append(
            f"{unmeasured} of {len(rows)} live article(s) are unmeasured and "
            f"are excluded from the distribution, never counted as zero: an "
            f"absent verdict is not evidence of an ungrounded article."
        )

    return CoverageDistributionReport(
        snapshot=snapshot,
        database_identity=database_identity,
        schema_present=True,
        read_at=read_at,
        live_articles=len(rows),
        measured_articles=len(measured),
        unmeasured_articles=unmeasured,
        percentiles={p: percentile(measured, p) for p in REPORTED_PERCENTILES}
        if measured else {},
        at_or_above_threshold=at_or_above,
        corpus_share=(at_or_above / len(measured)) if measured else None,
        threshold=threshold,
        corpus_share_bar=corpus_share_bar,
        population_sha256=population_hash(rows),
        under_powered=len(measured) < UNDER_POWERED_THRESHOLD,
        notes=tuple(notes),
    )


async def compute_coverage_distribution(
    session: AsyncSession,
    *,
    snapshot: str,
    database_identity: str,
    read_at: datetime,
) -> CoverageDistributionReport:
    result = await session.execute(_LIVE_ARTICLES_SQL)
    rows = [dict(row) for row in result.mappings()]
    return summarise(
        rows,
        snapshot=snapshot,
        database_identity=database_identity,
        read_at=read_at,
    )


def no_schema_report(
    *, snapshot: str, database_identity: str, read_at: datetime,
) -> CoverageDistributionReport:
    """The database has never been migrated -- no `knowledge_articles` table.

    Distinct from a migrated database with no articles: both are
    under-powered at zero measured articles, but this path is labelled so a
    reader does not read "never deployed" as "deployed and producing
    nothing".
    """
    return CoverageDistributionReport(
        snapshot=snapshot,
        database_identity=database_identity,
        schema_present=False,
        read_at=read_at,
        live_articles=0,
        measured_articles=0,
        unmeasured_articles=0,
        percentiles={},
        at_or_above_threshold=0,
        corpus_share=None,
        threshold=COVERAGE_BAR_DEFAULTS["article_coverage_threshold"],
        corpus_share_bar=COVERAGE_BAR_DEFAULTS["article_coverage_corpus_share"],
        population_sha256=population_hash([]),
        under_powered=True,
        notes=(
            "No `knowledge_articles` table: this database has never been "
            "migrated. Reported separately from an empty corpus so 'never "
            "deployed' is not read as 'deployed and quiet'.",
        ),
    )


def render_report(report: CoverageDistributionReport) -> str:
    lines = [
        f"# Coverage distribution — {report.snapshot}",
        "",
        f"- Database: `{report.database_identity}`",
        f"- Read at: {report.read_at.isoformat()}",
        f"- Population sha256: `{report.population_sha256}`",
        f"- Schema present: {'yes' if report.schema_present else 'NO'}",
        "",
        "## Population",
        "",
        f"- Live articles: {report.live_articles}",
        f"- Measured: {report.measured_articles}",
        f"- Unmeasured: {report.unmeasured_articles}",
        "",
    ]

    if report.percentiles:
        lines += ["## Distribution (nearest-rank, over measured articles)", ""]
        lines.append("| Percentile | Coverage |")
        lines.append("|---|---|")
        for p in REPORTED_PERCENTILES:
            lines.append(f"| p{p} | {report.percentiles[p]:.4f} |")
        lines.append("")
    else:
        lines += ["## Distribution", "", "No measured article: no distribution.", ""]

    share = (
        "under-powered" if report.corpus_share is None
        else f"{report.corpus_share:.4f}"
    )
    lines += [
        "## Share at or above the threshold",
        "",
        f"- Threshold (per-article, enforced at runtime): {report.threshold}",
        f"- At or above: {report.at_or_above_threshold} of "
        f"{report.measured_articles} measured",
        f"- Corpus share: {share}",
        f"- G-E's corpus-share bar, for reference: {report.corpus_share_bar}",
        "",
        "**No verdict is rendered here.** T3.22 owns G-E's verdict; this "
        "runner is plumbing (runbook §2).",
        "",
    ]

    if report.notes:
        lines += ["## Notes", ""] + [f"- {note}" for note in report.notes] + [""]
    return "\n".join(lines)


def to_ledger_row(
    report: CoverageDistributionReport, *, extra: dict | None = None,
) -> dict:
    row = {
        "kind": "coverage_distribution",
        "snapshot": report.snapshot,
        "database_identity": report.database_identity,
        "schema_present": report.schema_present,
        "read_at": report.read_at.isoformat(),
        "live_articles": report.live_articles,
        "measured_articles": report.measured_articles,
        "unmeasured_articles": report.unmeasured_articles,
        "percentiles": {str(p): v for p, v in report.percentiles.items()},
        "at_or_above_threshold": report.at_or_above_threshold,
        "corpus_share": report.corpus_share,
        "threshold": report.threshold,
        "corpus_share_bar": report.corpus_share_bar,
        "population_sha256": report.population_sha256,
        "under_powered": report.under_powered,
        "notes": list(report.notes),
    }
    return {**row, **(extra or {})}
