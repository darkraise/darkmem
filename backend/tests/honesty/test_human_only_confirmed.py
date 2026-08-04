"""honesty/human-only-confirmed — no machine path reaches ``confirmed``.

The machine's ceiling is ``corroborated``; ``confirmed`` is the human's floor
above it (doc 08 §4.4). That is the under-claiming preference made structural
rather than declared, and it is worth a tree-wide assertion because the failure
it guards is silent: a badge reading "human-ratified" over a fact no person
ever saw looks exactly like one that earned it.

Two arms, because the property has two halves that fail independently:

- **Behavioural.** The ladder is driven to its own ceiling with an
  overwhelming pile of agreement and never crosses. Asserting this through the
  real applier is what makes it a claim about the shipped promotion path rather
  than about a constant.
- **Structural.** Exactly one method in the tree writes the literal, and it
  cannot execute without a ``human``-kind ``fact_sources`` row. A source scan
  holds the "exactly one" half, because a second writer added later would pass
  every behavioural test in this file — it would simply be a path this file
  never drove.
"""
from __future__ import annotations

import ast
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import text

from app.repositories.fact_sources import FactSourceRepository
from app.repositories.knowledge_triples import (
    CONFIRMED,
    HUMAN_SOURCE_KIND,
    HumanSourceRequired,
    KnowledgeTripleRepository,
)
from app.services.verification_ladder import recompute_fact

PROJECT = "honesty-human-only-confirmed"
REFERENCE = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
CORROBORATIONS = 25

_BACKEND = Path(__file__).resolve().parents[2]
_APP = _BACKEND / "app"

# The one method permitted to write the literal, as ``file::qualname``. A new
# entry here is a new way to reach `confirmed` and must be argued in review,
# not added to make this test pass.
_PERMITTED_WRITER = "app/repositories/knowledge_triples.py::KnowledgeTripleRepository.ratify"


async def _fact(session, *, subject: str, obj: str) -> str:
    row = await KnowledgeTripleRepository(session).insert_open(
        triple_key=f"honesty-{uuid4()}",
        subject_name=subject,
        object_name=obj,
        rel_type="USES",
        fact=f"{subject} uses {obj}",
        reference_time=REFERENCE,
        project=PROJECT,
    )
    await session.flush()
    return row["id"]


async def _assert_origin(session, fact_id: str, origin_key: str) -> None:
    await FactSourceRepository(session).add_source(
        fact_id=fact_id,
        source_kind="memory",
        source_ref=f"memory:{origin_key}",
        origin_key=origin_key,
    )
    await session.flush()


async def _status(session, fact_id: str) -> str:
    result = await session.execute(
        text(
            "SELECT verification_status FROM knowledge_triples "
            "WHERE id = CAST(:id AS uuid)"
        ),
        {"id": str(fact_id)},
    )
    return result.scalar_one()


# ─────────────────────────── the behavioural arm ───────────────────────────


@pytest.mark.asyncio
async def test_the_ladder_stops_at_corroborated_however_much_agrees(session):
    """Twenty-five independent origins, diverse enough to fire the loose gate,
    nothing contradicting: the strongest case the machine can build. It reaches
    corroborated and stops."""
    fact_id = await _fact(session, subject="darkmem", obj="pgvector")
    for index in range(CORROBORATIONS):
        await _assert_origin(session, fact_id, f"session-{index}")

    await recompute_fact(session, fact_id)
    await session.flush()

    assert await _status(session, fact_id) == "corroborated"


@pytest.mark.asyncio
async def test_repeated_recomputes_never_drift_upward(session):
    """A ceiling that holds once but creeps on re-entry is the same defect
    arriving later — the recompute runs every two minutes in production."""
    fact_id = await _fact(session, subject="darkmem", obj="asyncpg")
    for index in range(CORROBORATIONS):
        await _assert_origin(session, fact_id, f"session-{index}")

    for _ in range(3):
        await recompute_fact(session, fact_id)
        await session.flush()
        assert await _status(session, fact_id) != CONFIRMED

    assert await _status(session, fact_id) == "corroborated"


@pytest.mark.asyncio
async def test_the_machine_writer_refuses_the_literal(session):
    fact_id = await _fact(session, subject="darkmem", obj="fastapi")
    with pytest.raises(ValueError, match="only a human may ratify"):
        await KnowledgeTripleRepository(session).set_verification_status(
            fact_id, CONFIRMED
        )
    assert await _status(session, fact_id) == "candidate"


@pytest.mark.asyncio
async def test_the_human_door_itself_refuses_without_a_human_source(session):
    """The one permitted writer is not a bypass: it is refused too when the
    provenance that entitles the fact to be confirmed does not exist. Nothing
    in the tree can reach the literal on machine evidence alone."""
    fact_id = await _fact(session, subject="darkmem", obj="alembic")
    for index in range(CORROBORATIONS):
        await _assert_origin(session, fact_id, f"session-{index}")
    await recompute_fact(session, fact_id)
    await session.flush()
    assert await _status(session, fact_id) == "corroborated"

    with pytest.raises(HumanSourceRequired):
        await KnowledgeTripleRepository(session).ratify(fact_id)

    assert await _status(session, fact_id) == "corroborated"


@pytest.mark.asyncio
async def test_a_human_source_written_by_hand_is_not_a_machine_path(session):
    """Stated rather than left implicit: any code that writes a ``human`` row
    can then confirm the fact. That is not a hole in the guard — it is what
    "the ratification IS the source row" means, and the row's identity is what
    the audit reads. The guard's job is that no path reaches ``confirmed``
    *without leaving that record*, and this asserts the record is required and
    attributable, not that impersonation is impossible."""
    fact_id = await _fact(session, subject="darkmem", obj="pydantic")
    await FactSourceRepository(session).add_source(
        fact_id=fact_id,
        source_kind=HUMAN_SOURCE_KIND,
        source_ref="human:admin",
        origin_key="human:admin",
        detail={"ratified_by": "admin"},
    )
    await session.flush()

    await KnowledgeTripleRepository(session).ratify(fact_id)
    await session.flush()

    assert await _status(session, fact_id) == CONFIRMED
    rows = (await session.execute(
        text(
            "SELECT detail FROM fact_sources WHERE fact_id = CAST(:id AS uuid) "
            "AND source_kind = CAST(:kind AS text)"
        ),
        {"id": str(fact_id), "kind": HUMAN_SOURCE_KIND},
    )).scalars().all()
    assert rows and rows[0]["ratified_by"] == "admin"


# ─────────────────────────── the structural arm ───────────────────────────


def _confirmed_writers(root: Path) -> list[str]:
    """Every function under ``root`` whose body writes the literal 'confirmed'
    into ``verification_status``.

    Matched on the SQL/text level rather than by import graph, because the
    write is a raw statement: a new module could reach the column without
    importing anything this scan could follow. The predicate is deliberately
    broad — an assignment of the literal anywhere near the column name — so a
    second writer trips it and has to argue itself onto the allowlist.
    """
    offenders: list[str] = []
    for path in sorted(root.rglob("*.py")):
        source = path.read_text(encoding="utf-8")
        if CONFIRMED not in source:
            continue
        try:
            rel = path.relative_to(_BACKEND).as_posix()
        except ValueError:
            # The two self-tests below drive this scan over a tmp_path tree,
            # which is not under the backend root.
            rel = path.name
        tree = ast.parse(source, filename=str(path))
        for node, qualname in _functions(tree):
            body = ast.get_source_segment(source, node) or ""
            if "verification_status" not in body:
                continue
            if not _assigns_confirmed(body):
                continue
            offenders.append(f"{rel}::{qualname}")
    return offenders


def _functions(tree: ast.AST, prefix: str = ""):
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            yield node, f"{prefix}{node.name}"
        elif isinstance(node, ast.ClassDef):
            yield from _functions(node, prefix=f"{prefix}{node.name}.")


def _assigns_confirmed(body: str) -> bool:
    """A write, not a comparison or a docstring mention.

    ``verification_status = 'confirmed'`` and ``verification_status =
    CAST(:confirmed ...)`` are writes; ``!= 'confirmed'``, ``== 'confirmed'``
    and ``'confirmed'`` inside a tuple of readable states are not.
    """
    for line in body.splitlines():
        stripped = line.strip()
        if "verification_status" not in stripped:
            continue
        head, _, tail = stripped.partition("verification_status")
        if not tail.lstrip().startswith("="):
            continue
        if tail.lstrip().startswith("=="):
            continue
        if head.rstrip().endswith(("!", "<", ">")):
            continue
        assigned = tail.lstrip()[1:]
        if CONFIRMED in assigned or ":confirmed" in assigned:
            return True
    return False


def test_exactly_one_function_in_the_tree_writes_confirmed():
    writers = _confirmed_writers(_APP)
    assert writers == [_PERMITTED_WRITER], (
        f"expected {_PERMITTED_WRITER} to be the only writer of "
        f"{CONFIRMED!r}, found {writers}. A second path to the human's floor "
        f"is the forged-ratification failure this spec exists to refuse: it "
        f"would pass every behavioural test above simply by never being "
        f"driven. If the new writer is legitimate, it must carry the same "
        f"human-source precondition and be argued onto the allowlist."
    )


def test_the_scan_would_catch_a_second_writer(tmp_path):
    """A guard that cannot fail is not a guard. This drives the scan over a
    file shaped like the regression it exists to catch."""
    offender = tmp_path / "eager_confirm.py"
    offender.write_text(
        "async def promote(session, fact_id):\n"
        "    await session.execute(\n"
        "        \"UPDATE knowledge_triples SET verification_status = 'confirmed'\"\n"
        "    )\n",
        encoding="utf-8",
    )
    found = _confirmed_writers(tmp_path)
    assert any(name.endswith("::promote") for name in found), found


def test_the_scan_ignores_reads_of_the_literal(tmp_path):
    """The tree is full of legitimate mentions — the ladder holds a confirmed
    fact, the recompute excludes it from its slice. A scan that flagged those
    would be turned off within a week."""
    reader = tmp_path / "reads.py"
    reader.write_text(
        "def hold(row):\n"
        "    if row.verification_status == 'confirmed':\n"
        "        return 'hold'\n"
        "    if row.verification_status != 'confirmed':\n"
        "        return 'move'\n",
        encoding="utf-8",
    )
    assert _confirmed_writers(tmp_path) == []
