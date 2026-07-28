"""The runner: pre-flight, stage, verify, load, verify, seed, commit.

Everything from staging to the commit runs in **one** transaction on the
target, so the answer to "what does a half-finished run leave behind" is
"nothing" for every failure except an abort after the ``setval``, which leaves
the sequence advanced and nothing else.

Usage, from ``backend/``::

    .venv/bin/python scripts/cutover/__main__.py \
        --source-dsn postgresql://user:pw@host:5433/restored_copy \
        --target-dsn postgresql://user:pw@host:5433/fresh_baseline \
        --report-dir /var/tmp/cutover
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
import uuid
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path

import asyncpg

if __package__ in (None, ""):  # direct `python scripts/cutover/__main__.py`
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    __package__ = "cutover"

from . import spec, stage, transform, verify  # noqa: E402
from .db import (  # noqa: E402
    CutoverError,
    assert_distinct_databases,
    assert_distinct_live_databases,
    assert_source_not_production,
    connect_source,
    connect_target,
)
from .preflight import run_preflight  # noqa: E402


def _json_default(value):
    if isinstance(value, uuid.UUID):
        return str(value)
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    raise TypeError(f"not JSON-serialisable: {type(value).__name__}")


def _stamp() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H-%M-%SZ")


@dataclass
class CutoverResult:
    preflight: dict = field(default_factory=dict)
    staged: dict[str, int] = field(default_factory=dict)
    reset: dict = field(default_factory=dict)
    source_vs_staging: dict = field(default_factory=dict)
    staging_vs_target: dict = field(default_factory=dict)
    positive_assertions: dict = field(default_factory=dict)
    post_seed: dict = field(default_factory=dict)
    sequence_value: int | None = None

    def to_dict(self) -> dict:
        return {
            "preflight": self.preflight,
            "staged": self.staged,
            "reset": self.reset,
            "source_vs_staging": self.source_vs_staging,
            "staging_vs_target": self.staging_vs_target,
            "positive_assertions": self.positive_assertions,
            "post_seed": self.post_seed,
            "tags_id_seq": self.sequence_value,
        }


def _aggregates_to_dict(aggregates: dict[str, verify.TableAggregate]) -> dict:
    return {name: value.to_dict() for name, value in aggregates.items()}


async def run_cutover(
    source: asyncpg.Connection,
    target: asyncpg.Connection,
    *,
    reset: bool = False,
    acknowledged_row_loss: int | None = None,
    batch_size: int = stage.DEFAULT_BATCH_SIZE,
    result: CutoverResult | None = None,
) -> CutoverResult:
    result = result if result is not None else CutoverResult()

    await assert_distinct_live_databases(source, target)

    report = await run_preflight(source, target, reset=reset)
    result.preflight = report.to_dict()
    report.raise_if_failed()

    async with target.transaction():
        result.staged = await stage.stage_all(source, target, batch_size)

        # Leg one, before the first carried-table write. The source-to-staging
        # hop is the only place a carried value passes through Python, and a
        # defect there lands identically in staging and in the target, so every
        # later check would agree with itself and pass. Failing here means
        # nothing was written to a carried table at all.
        source_side = await verify.aggregate_side(source, target_names=False)
        staging_side = await verify.aggregate_side(
            target, staging=True, target_names=False
        )
        problems = verify.compare_aggregates(
            "source", "staging", source_side, staging_side
        )
        result.source_vs_staging = {
            "source": _aggregates_to_dict(source_side),
            "staging": _aggregates_to_dict(staging_side),
            "problems": problems,
        }
        if problems:
            raise CutoverError(
                "source-to-staging parity failed; nothing was written to a "
                "carried table:\n  " + "\n  ".join(problems)
            )

        if reset:
            guard = await transform.reset_dump_membership(target)
            result.reset = {"guard": guard.to_dict()}
            transform.assert_reset_allowed(guard, acknowledged_row_loss)
            result.reset["deleted"] = await transform.reset_delete(target)

        for table in spec.CARRIED:
            await transform.load_table(target, table)

        # Leg two, inside the transaction and ahead of the setval, so a
        # value-level mismatch aborts the load rather than reporting on a
        # database that has already committed.
        target_side = await verify.aggregate_side(target, target_names=True)
        problems = verify.compare_aggregates(
            "staging", "target", staging_side, target_side
        )
        result.staging_vs_target = {
            "target": _aggregates_to_dict(target_side),
            "problems": problems,
        }
        measured, positive_problems = await verify.positive_assertions(target)
        result.positive_assertions = {
            "measured": measured,
            "problems": positive_problems,
        }
        if problems or positive_problems:
            raise CutoverError(
                "staging-to-target verification failed; the load is rolled "
                "back:\n  " + "\n  ".join(problems + positive_problems)
            )

        result.sequence_value = await transform.advance_tag_sequence(target)
        await transform.seed_projects(target)

        measured, problems = await verify.post_seed_assertions(target)
        result.post_seed = {"measured": measured, "problems": problems}
        if problems:
            raise CutoverError(
                "post-seed verification failed; the load is rolled back:\n  "
                + "\n  ".join(problems)
            )

        await stage.drop_staging_tables(target)

    return result


async def write_snapshot(target: asyncpg.Connection, path: Path) -> int:
    """The pre-backfill control, taken after the commit.

    Detection is not prevention: the re-extraction backfill overwrites these
    eleven columns and every other post-cutover check stays green while it
    happens. This file is the only "before" that will ever exist. It is user
    data and is never committed.
    """
    columns = ", ".join(f'"{c}"' for c in spec.SNAPSHOT_COLUMNS)
    rows = await target.fetch(f"SELECT {columns} FROM memories ORDER BY id")
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(dict(row), default=_json_default) + "\n")
    return len(rows)


def _write_json(path: Path, payload: dict) -> None:
    path.write_text(
        json.dumps(payload, indent=2, default=_json_default) + "\n", encoding="utf-8"
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cutover",
        description="Move the carried set from a restored 0006 copy onto the baseline.",
    )
    parser.add_argument("--source-dsn", required=True, help="a RESTORED COPY, never production")
    parser.add_argument("--target-dsn", required=True, help="a fresh database at the baseline")
    parser.add_argument("--report-dir", required=True, type=Path)
    parser.add_argument(
        "--reset",
        action="store_true",
        help="delete the five carried tables first; refuses against a live target",
    )
    parser.add_argument(
        "--i-know-rows-will-be-lost",
        type=int,
        default=None,
        metavar="N",
        dest="acknowledged_row_loss",
        help="override the --reset refusal; N must equal the count just reported",
    )
    parser.add_argument("--preflight-only", action="store_true")
    parser.add_argument("--batch-size", type=int, default=stage.DEFAULT_BATCH_SIZE)
    return parser


async def _amain(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    assert_source_not_production(args.source_dsn)
    assert_distinct_databases(args.source_dsn, args.target_dsn)

    report_dir: Path = args.report_dir
    report_dir.mkdir(parents=True, exist_ok=True)
    stamp = _stamp()

    source = await connect_source(args.source_dsn)
    target = await connect_target(args.target_dsn)
    try:
        if args.preflight_only:
            report = await run_preflight(source, target, reset=args.reset)
            _write_json(report_dir / f"cutover-preflight-{stamp}.json", report.to_dict())
            report.raise_if_failed()
            print(f"pre-flight passed ({len(report.checks)} checks)")
            return 0

        result = CutoverResult()
        try:
            await run_cutover(
                source,
                target,
                reset=args.reset,
                acknowledged_row_loss=args.acknowledged_row_loss,
                batch_size=args.batch_size,
                result=result,
            )
        except CutoverError:
            payload = result.to_dict()
            payload["aborted"] = True
            _write_json(report_dir / f"cutover-aborted-{stamp}.json", payload)
            raise

        _write_json(report_dir / f"cutover-verification-{stamp}.json", result.to_dict())
        written = await write_snapshot(
            target, report_dir / f"cutover-snapshot-{stamp}.jsonl"
        )
        print(
            f"cutover committed: {result.staged} staged, {written} memories snapshotted"
        )
        print(f"reports in {report_dir} — user data, never commit them")
        return 0
    finally:
        await source.close()
        await target.close()


def main(argv: list[str] | None = None) -> int:
    try:
        return asyncio.run(_amain(argv))
    except CutoverError as error:
        print(f"CUTOVER ABORTED\n{error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
