"""Harvest real block spans for the claim/span faithfulness gold (TH1.10).

**Why this exists.** Doc 17 §6's recorded stance is that the qualification gold
is seeded from real block answers and that *synthetic-only entailment gold is
rejected as unrepresentative*. TH1.01 §5 reserved the ``document-span`` and
``qa-draft`` provenances at zero pairs "until their producer task exists";
TH1.02 and TH1.08 shipped, and the owner ruled on 2026-08-17 that the gold uses
real block spans and real QA drafts. This is the producer that makes a premise
*real* in the sense §5 means: **the shipping parser produced the block and the
span**, not a hand-written fixture.

**The reproducibility problem this solves, and it is the whole design.** A gold
that anchored directly into ``blocks`` rows would only resolve where that
database exists, which makes every pair unverifiable anywhere else — an
anecdote, in the ledger's own vocabulary. So this walks the same road the
claim/fact gold walks with ``l2_harvest.json``: ingest the committed sources
through ``block_pipeline.ingest_document`` (the shipping path, so the parser is
the real one), then **export the resulting blocks to a committed manifest** with
their hashes. Pairs anchor into the manifest, and the manifest is a file in the
repository. Real *and* reproducible, rather than one at the cost of the other.

Re-running the harvest over unchanged sources must reproduce the manifest
byte-identically. That is not a nicety — it is a parser-determinism check that
runs every time anyone regenerates, and a drifting parser is exactly the thing
that would silently invalidate an anchored gold.

**What this does NOT do.** It authors nothing. It selects nothing: the caller
supplies the source directory, because *which* documents are harvested shapes
the gold's distribution and that is a composition decision the owner owns
(`autonomous-loop.md` §7). It writes no gold file, no hypothesis and no label.
It produces the premise pool an author then draws from.

Usage::

    cd backend && python scripts/benchlib/span_harvest.py \\
        --sources scripts/benchlib/entailment/span_sources \\
        --out scripts/benchlib/entailment/span_harvest.json \\
        --database-url postgresql+asyncpg://darkmem:darkmem@localhost:5433/darkmem_span_harvest

The database it uses is disposable and its identity never reaches the manifest:
blocks are keyed by their position in the parsed tree, not by the row id a
particular ingest happened to mint.
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[2]
SCRIPTS = Path(__file__).resolve().parents[1]
# Both, in the order run_faithfulness_gate.py uses: BACKEND resolves `app.*` and
# SCRIPTS resolves `benchlib.*`. Inserting only BACKEND left `from benchlib
# import db_target` an ImportError that killed the tool outright — and, because
# the crash happened before the target guard could run, a smoke test of that
# guard read as "refused" when nothing had been checked at all.
for _path in (str(BACKEND), str(SCRIPTS)):
    if _path not in sys.path:
        sys.path.insert(0, _path)

from sqlalchemy import text  # noqa: E402
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine  # noqa: E402

from benchlib import db_target  # noqa: E402

from app.services.block_pipeline import URI_SUFFIX_SOURCE_TYPES, ingest_document  # noqa: E402

HARVEST_PROJECT = "span-gold-harvest"

# **This tool WRITES documents and blocks, so where it points matters.** The
# first version defaulted to `darkmem_test` — pytest's database, which conftest
# drops the schema of at session start — while its own sibling
# `run_faithfulness_gate.py` explicitly refuses that name. A harvest run with no
# flag would have written rows into a database another process concurrently
# destroys, producing either a truncated manifest or test failures
# indistinguishable from a real regression. Found by the Fable dispatch that
# first used it (2026-08-17).
DEFAULT_HARVEST_DATABASE_NAME = "darkmem_span_harvest"
DEFAULT_HARVEST_DATABASE_URL = (
    "postgresql+asyncpg://darkmem:darkmem@localhost:5433/"
    + DEFAULT_HARVEST_DATABASE_NAME
)


def assert_harvest_target_allowed(url: str) -> None:
    """Refuse pytest's databases and the live one.

    The same rule `db_target.assert_destructive_target_allowed` enforces for the
    bench resets, applied here because this writer is destructive in the way that
    matters: it files documents and replaces their block trees. Reusing that
    helper rather than re-deriving the name set keeps one list of forbidden
    targets.
    """
    db_target.assert_destructive_target_allowed(url, actor="span_harvest.py")

# Raw SQL because `blocks` carries no ORM model — `app/repositories/documents.py`
# is `text()` throughout, and this reads the same way rather than introducing a
# mapper the tree does not have. The ORDER BY is total: `order_index` is the
# parse order, and `id` breaks a tie so the manifest cannot reorder between two
# runs that produced the same tree.
_READ_BLOCKS = text(
    """
    SELECT id, order_index, type, text, char_span
    FROM blocks
    WHERE document_id = CAST(:document_id AS uuid)
    ORDER BY order_index, id
    """
)


def source_files(sources_dir: Path) -> list[Path]:
    """Every parseable source under ``sources_dir``, in a stable order.

    Sorted by POSIX-relative path rather than by directory-walk order, which is
    filesystem-dependent — the manifest has to be byte-stable across machines,
    and an unordered walk would reorder it without changing a single document.
    """
    known = tuple(URI_SUFFIX_SOURCE_TYPES)
    found = [
        path
        for path in sources_dir.rglob("*")
        if path.is_file() and path.suffix.lower() in known
    ]
    return sorted(found, key=lambda p: p.relative_to(sources_dir).as_posix())


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def block_digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def span_bounds(raw) -> list[int] | None:
    """``[start, end)`` as a plain pair, from whatever the driver hands back.

    ``blocks.char_span`` is an ``int4range`` and asyncpg returns a ``Range``
    object, not a tuple — the repository writes it through ``_span_literal``
    and nothing in the tree had ever read it back. Half-open is preserved
    verbatim rather than normalised: a block spanning characters 3 through 9 is
    ``[3,10)`` precisely so two adjacent blocks cannot both claim offset 10, and
    silently converting to an inclusive pair here would make every anchored
    premise one character longer than the block the parser actually produced.
    """
    if raw is None:
        return None
    lower, upper = getattr(raw, "lower", None), getattr(raw, "upper", None)
    if lower is None or upper is None:
        # A tuple-ish driver, or an unbounded range. Unbounded is not a span
        # this gold can anchor into, so it is refused rather than guessed at.
        try:
            lower, upper = raw
        except (TypeError, ValueError):
            raise ValueError(f"cannot read char_span bounds from {raw!r}") from None
    return [int(lower), int(upper)]


async def harvest(sources_dir: Path, database_url: str) -> dict:
    engine = create_async_engine(database_url, echo=False)
    maker = async_sessionmaker(engine, expire_on_commit=False)
    documents: list[dict] = []

    try:
        for path in source_files(sources_dir):
            rel = path.relative_to(sources_dir).as_posix()
            content = _read(path)
            async with maker() as session:
                ingest = await ingest_document(
                    session,
                    project=HARVEST_PROJECT,
                    content=content,
                    uri=rel,
                    title=path.stem,
                )
                await session.commit()

                rows = (
                    await session.execute(
                        _READ_BLOCKS, {"document_id": str(ingest.document_id)}
                    )
                ).mappings().all()

            blocks = []
            for position, row in enumerate(rows):
                span = span_bounds(row["char_span"])
                block_text = row["text"] or ""
                blocks.append(
                    {
                        # Position in the parsed tree, never the row id: a
                        # re-ingest mints new uuids and the manifest must not
                        # move because of it.
                        "block_key": f"b{position}",
                        "order_index": row["order_index"],
                        "type": row["type"],
                        # Where this block sits in the SOURCE file. Exported for
                        # traceability only. It is NOT the coordinate system a
                        # citation uses and must never be copied into a pair's
                        # char_span — see `_notes`.
                        "source_char_span": span,
                        # The premise basis. `faithfulness_gate._entails` puts
                        # `block.text[start:end]` to the judge, so a pair's
                        # char_span indexes into THIS string, from 0.
                        "text": block_text,
                        "text_length": len(block_text),
                        "text_sha256": block_digest(block_text),
                    }
                )

            # `ingest.blocks_written` is deliberately NOT recorded. It describes
            # the ingest *event*, not the harvested content: `file_document`'s
            # change gate short-circuits on an unchanged content_hash, so it
            # reads 6 on a fresh database and 0 on a re-ingest of the same
            # source. Including it made the manifest depend on whether the
            # harvest database happened to be empty, which turned `--check`
            # into a coin flip — a determinism check that fails for a reason
            # having nothing to do with determinism is worse than none.
            documents.append(
                {
                    "uri": rel,
                    "source_type": path.suffix.lower().lstrip("."),
                    "content_hash": ingest.content_hash,
                    "blocks": blocks,
                }
            )
    finally:
        await engine.dispose()

    return {
        "_notes": (
            "Real block spans harvested through app.services.block_pipeline."
            "ingest_document — the shipping parser, so a premise drawn from here"
            " is `document-span` provenance in TH1.01 §5's sense. Generated by"
            " scripts/benchlib/span_harvest.py; do not hand-edit. Re-running"
            " over unchanged sources must reproduce this file byte-identically,"
            " which is also the parser-determinism check."
            " TWO COORDINATE SYSTEMS, and confusing them silently misbuilds the"
            " gold: `source_char_span` is where the block sits in the source"
            " file and is exported for traceability only, while a citation's"
            " char_span indexes into the block's own `text` from 0 — that is"
            " what faithfulness_gate._entails slices when it puts a premise to"
            " the judge (`block.text[start:end]`). Author pairs against `text`"
            " and bound them by `text_length`; never copy `source_char_span`"
            " into a pair."
        ),
        "harvest_project": HARVEST_PROJECT,
        "document_count": len(documents),
        "block_count": sum(len(d["blocks"]) for d in documents),
        "documents": documents,
    }


def serialise(manifest: dict) -> str:
    # sort_keys so key order cannot drift with dict construction order, and a
    # trailing newline so the file is well-formed for line-oriented tools.
    return json.dumps(manifest, indent=2, ensure_ascii=False, sort_keys=True) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sources", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument(
        "--database-url",
        default=os.environ.get(
            "SPAN_HARVEST_DATABASE_URL", DEFAULT_HARVEST_DATABASE_URL
        ),
        help="a DISPOSABLE database; the harvest writes documents and blocks. "
             f"Defaults to {DEFAULT_HARVEST_DATABASE_NAME}; pytest's databases "
             "and the live one are refused.",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="re-harvest and fail if the manifest would change, without writing",
    )
    args = parser.parse_args()

    if not args.sources.is_dir():
        print(f"no source directory at {args.sources}", file=sys.stderr)
        return 2

    files = source_files(args.sources)
    if not files:
        print(
            f"no parseable sources under {args.sources} "
            f"(known suffixes: {', '.join(sorted(URI_SUFFIX_SOURCE_TYPES))})",
            file=sys.stderr,
        )
        return 2

    assert_harvest_target_allowed(args.database_url)

    manifest = asyncio.run(harvest(args.sources, args.database_url))
    rendered = serialise(manifest)

    if args.check:
        if not args.out.exists():
            print(f"no manifest at {args.out} to check against", file=sys.stderr)
            return 1
        current = args.out.read_text(encoding="utf-8")
        if current != rendered:
            print(
                f"{args.out} is stale — a re-harvest of the same sources does not "
                "reproduce it. Either a source changed or the parser did; both "
                "invalidate every pair anchored into it.",
                file=sys.stderr,
            )
            return 1
        print(f"{args.out} reproduces exactly ({manifest['block_count']} blocks)")
        return 0

    args.out.write_text(rendered, encoding="utf-8")
    print(
        f"harvested {manifest['document_count']} document(s), "
        f"{manifest['block_count']} block(s) -> {args.out}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
