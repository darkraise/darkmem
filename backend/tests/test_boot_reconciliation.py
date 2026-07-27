"""Boot-time partition reconciliation is permanent and idempotent (T0.14).

Doc 19 §2 replaces the registry's old one-time creation sweep with a
reconciliation that runs at EVERY startup: it iterates the live ``embedders``
rows and runs each template's ``CREATE TABLE IF NOT EXISTS`` plus each aux
index's ``CREATE INDEX IF NOT EXISTS``. That is what dissolves the
sweep-versus-baseline coexistence problem — adding a partition family becomes a
template edit, and an existing deployment gains the new parent for its current
fingerprint at next boot with no re-register and no migration. It also
self-heals drift, and replays mechanically in the deferred .NET port because it
is a loop over rows running parameterised plain SQL.

G-A names idempotence explicitly, so it is asserted here rather than assumed.
"""
from __future__ import annotations

import pytest
from sqlalchemy import text

from app.services.embedder_registry import (
    _TABLE_TEMPLATES,
    EmbedderInfo,
    EmbedderRegistry,
    child_table,
)

FP = "reconcile-probe|8"


async def _register(session, registry: EmbedderRegistry, fingerprint: str = FP, dims: int = 8):
    await registry.register(
        session,
        EmbedderInfo(fingerprint=fingerprint, model_id="reconcile-probe", dims=dims, source="llm"),
    )


async def _child_tables(session, fingerprint: str = FP) -> set[str]:
    names = [child_table(parent, fingerprint) for parent in _TABLE_TEMPLATES]
    rows = (await session.execute(
        text("SELECT tablename FROM pg_tables "
             "WHERE schemaname = 'public' AND tablename = ANY(:names)"),
        {"names": names},
    )).scalars().all()
    return set(rows)


@pytest.mark.asyncio
async def test_reconcile_creates_every_parent_for_a_live_fingerprint(session):
    registry = EmbedderRegistry()
    await _register(session, registry)

    present = await _child_tables(session)
    assert len(present) == len(_TABLE_TEMPLATES), (
        f"expected a child table per parent, got {sorted(present)}"
    )


@pytest.mark.asyncio
async def test_second_reconcile_is_a_no_op(session):
    """Booting twice against the same database changes nothing the second time."""
    registry = EmbedderRegistry()
    await _register(session, registry)

    before = await _child_tables(session)
    result = await registry.reconcile(session)
    after = await _child_tables(session)

    assert after == before
    assert result["fingerprints"] >= 1
    assert result["parents"] == len(_TABLE_TEMPLATES)


@pytest.mark.asyncio
async def test_reconcile_regrows_exactly_the_missing_child(session):
    """A restored dump missing one child table regrows that one, not the rest."""
    registry = EmbedderRegistry()
    await _register(session, registry)

    victim = child_table("entity_embeddings", FP)
    await session.execute(text(f"DROP TABLE {victim} CASCADE"))
    await session.commit()
    assert victim not in await _child_tables(session)

    survivors_before = await _child_tables(session)
    await registry.reconcile(session)
    after = await _child_tables(session)

    assert victim in after, "the missing child was not regrown"
    assert after == survivors_before | {victim}, "reconcile touched more than the gap"


@pytest.mark.asyncio
async def test_reconcile_skips_retired_fingerprints(session):
    """Only live rows reconcile — a retired embedder is not resurrected."""
    registry = EmbedderRegistry()
    await _register(session, registry)
    await session.execute(
        text("UPDATE embedders SET retired_at = now() WHERE fingerprint = :fp"), {"fp": FP}
    )
    await session.commit()

    victim = child_table("entity_embeddings", FP)
    await session.execute(text(f"DROP TABLE {victim} CASCADE"))
    await session.commit()

    await registry.reconcile(session)
    assert victim not in await _child_tables(session)


@pytest.mark.asyncio
async def test_malformed_fingerprint_is_rejected_at_registration_not_ddl_time(session):
    """A fingerprint folding to an empty slug fails loudly before any DDL runs.

    Its child tables would be named ``<parent>__`` — addressable by nothing —
    so the failure belongs at registration, where it is one clear error, not at
    DDL time where it would leave half a partition set behind.

    ``@@@`` is the shape that folds empty: every character is a separator, so
    the slug regex maps the lot to ``_`` and the strip leaves nothing. (A
    fingerprint that came through ``parse_fingerprint`` always carries at least
    one digit from ``|<dims>``, so this guard is defence in depth for callers
    that build an ``EmbedderInfo`` by hand.)
    """
    registry = EmbedderRegistry()
    with pytest.raises(RuntimeError, match="empty partition slug"):
        await _register(session, registry, fingerprint="@@@")
    await session.rollback()

    leaked = (await session.execute(
        text("SELECT count(*) FROM pg_tables "
             "WHERE schemaname = 'public' AND tablename LIKE '%\\_\\_'")
    )).scalar()
    assert leaked == 0, "a malformed fingerprint created child tables before failing"


def test_child_tables_are_only_ever_named_through_child_table():
    """Invariant 2: no literal slug interpolation anywhere in the registry.

    ``child_table`` is the sole namer. The one place ``<parent>__<slug>`` is
    assembled is inside that function; anything else building the name by hand
    would drift the moment the slug rule changes.
    """
    from pathlib import Path

    src = Path(__file__).resolve().parent.parent / "app" / "services" / "embedder_registry.py"
    body = src.read_text()
    assert body.count('f"{parent}__') == 1, (
        "child-table names must be built only inside child_table()"
    )
