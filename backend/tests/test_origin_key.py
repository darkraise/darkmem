"""`origin_key` — the corroboration-independence key, stamped at capture.

Doc 05 §2.1. Every verification count in E2 is `COUNT(DISTINCT origin_key)`,
never a row count, so this key decides whether two saved claims corroborate each
other or are one voice repeating itself.

The asymmetry that shapes every rule here: **undercounting only delays a
promotion; overcounting manufactures one.** A fact promoted on counterfeit
independence is the worst failure the system has, because every article citing
it inherits the lie. So when identity is genuinely unknown, capture merges to
ONE origin per `(source, project)` rather than minting distinct ones — an
untagged flood from a single tool can never self-corroborate.

The rule this file exists to enforce is therefore a negative one: **a
per-request random is forbidden** (doc 05 §12). Two undeclared captures must
produce the *same* key.
"""
from __future__ import annotations

import pytest
from sqlalchemy import text

from app.api.mcp.client_identity import (
    ORIGIN_HEADER,
    UNKNOWN_ORIGIN_PREFIX,
    resolve_origin_key,
)


class _Req:
    def __init__(self, headers: dict[str, str]):
        self.headers = headers


class _Ctx:
    """Mimics the shape `_request_from_ctx` reads."""

    def __init__(self, headers: dict[str, str] | None = None):
        self.request_context = type("RC", (), {"request": _Req(headers or {})})()


# ── The declared-identity branch ────────────────────────────────────


def test_declared_header_composes_source_and_origin_id():
    key = resolve_origin_key(
        None, _Ctx({ORIGIN_HEADER: "boot-abc123"}), source="claude-code", project="p"
    )
    assert key == "claude-code:boot-abc123"


def test_explicit_argument_wins_over_the_header():
    key = resolve_origin_key(
        "from-body", _Ctx({ORIGIN_HEADER: "from-header"}), source="api", project="p"
    )
    assert key == "api:from-body"


def test_two_distinct_declared_ids_stay_distinct():
    """The whole point of a declared identity: two genuinely different agent
    runs must count as two origins."""
    a = resolve_origin_key(None, _Ctx({ORIGIN_HEADER: "run-1"}), source="mcp", project="p")
    b = resolve_origin_key(None, _Ctx({ORIGIN_HEADER: "run-2"}), source="mcp", project="p")
    assert a != b


def test_a_colon_in_a_declared_id_cannot_forge_the_key_shape():
    key = resolve_origin_key(None, _Ctx({ORIGIN_HEADER: "a:b"}), source="mcp", project="p")
    assert key.count(":") == 1


# ── The merge-to-one fallback ───────────────────────────────────────


def test_unknown_identity_uses_the_documented_fallback_shape():
    key = resolve_origin_key(None, _Ctx({}), source="mcp", project="default")
    assert key == f"{UNKNOWN_ORIGIN_PREFIX}:mcp:default"


def test_two_undeclared_captures_produce_the_same_key():
    """**The forbidden-random test.** A per-request random here would mint two
    counterfeit origins from one agent and let it corroborate itself. Same
    source, same project, no declared identity — one origin."""
    first = resolve_origin_key(None, _Ctx({}), source="mcp", project="default")
    second = resolve_origin_key(None, _Ctx({}), source="mcp", project="default")
    assert first == second


def test_a_hundred_undeclared_captures_are_one_origin():
    """The flood case doc 05 §2.1 names: an untagged batch from one tool
    collapses to a single origin, so it can never self-corroborate."""
    keys = {
        resolve_origin_key(None, _Ctx({}), source="mcp", project="default")
        for _ in range(100)
    }
    assert len(keys) == 1


def test_the_fallback_still_separates_sources_and_projects():
    """Coarse, but not degenerate — two genuinely different tools are still two
    origins, otherwise undercounting would swallow real independence."""
    a = resolve_origin_key(None, _Ctx({}), source="mcp", project="p")
    b = resolve_origin_key(None, _Ctx({}), source="claude-code", project="p")
    c = resolve_origin_key(None, _Ctx({}), source="mcp", project="other")
    assert len({a, b, c}) == 3


@pytest.mark.parametrize("blank", ["", "   ", None])
def test_blank_declared_identity_falls_back_rather_than_minting(blank):
    key = resolve_origin_key(blank, _Ctx({}), source="mcp", project="default")
    assert key.startswith(f"{UNKNOWN_ORIGIN_PREFIX}:")


def test_resolution_never_raises_on_a_broken_context():
    """Attribution must not fail a write."""
    class Exploding:
        @property
        def request_context(self):
            raise RuntimeError("no request")

    key = resolve_origin_key(None, Exploding(), source="mcp", project="default")
    assert key == f"{UNKNOWN_ORIGIN_PREFIX}:mcp:default"


# ── It lands on the row ─────────────────────────────────────────────


@pytest.mark.asyncio
async def test_origin_key_persists_to_the_memory_row(session):
    from app.schemas.memory import MemoryCreate
    from app.services.memory import MemoryService

    service = MemoryService(session)
    result = await service.create_memory(
        MemoryCreate(content="a claim", source="mcp", origin_key="mcp:boot-1"),
        api_key_id=None, wait_process=True,
    )
    memory = result.memory
    assert memory is not None
    stored = (
        await session.execute(
            text("SELECT origin_key FROM memories WHERE id = CAST(:i AS uuid)"),
            {"i": str(memory.id)},
        )
    ).scalar_one()
    assert stored == "mcp:boot-1"


@pytest.mark.asyncio
async def test_two_unknown_identity_captures_do_not_count_as_two_origins(session):
    """The end-to-end form of the counting rule: two captures from one
    undeclared source land on ONE distinct origin_key, so the fact layer's
    COUNT(DISTINCT origin_key) sees a single voice."""
    from app.schemas.memory import MemoryCreate
    from app.services.memory import MemoryService

    service = MemoryService(session)
    fallback = resolve_origin_key(None, _Ctx({}), source="mcp", project="default")
    for content in ("postgres is fast", "postgres is fast, really"):
        await service.create_memory(
            MemoryCreate(
                content=content, source="mcp", project="default", origin_key=fallback
            ),
            api_key_id=None, wait_process=True,
        )

    distinct = (
        await session.execute(
            text(
                "SELECT count(DISTINCT origin_key) FROM memories "
                "WHERE origin_key = :k"
            ),
            {"k": fallback},
        )
    ).scalar_one()
    assert distinct == 1
