"""`POST /reembed/prune-cache` may only drop a cache child when the active
fingerprint is resolved and registered (T2.82).

The prune keeps exactly one `entity_embedding_cache__<slug>` — the one the
active fingerprint names — and drops every other child it finds. That makes
the *keep* key load-bearing in a way no read path is: when the configured
fingerprint is not one an embed has ever registered, its child table does not
exist, nothing matches the keep, and the sweep takes every live cache in the
deployment.

`llm_fingerprint()` produces such a key from a legal configuration: with the
embedding purpose's `dimensions` unset it returns `f"{model}|0"`, and
`parse_fingerprint` rejects `dims <= 0` before any partition is created. The
sentinel is one instance of the class, not the class itself — a configured
`dimensions` that contradicts what the model emits (T2.83) yields an equally
unregistered non-zero key — so the guard here keys on registration, never on
the literal zero.
"""
from __future__ import annotations

from contextlib import asynccontextmanager

import pytest
import pytest_asyncio
from sqlalchemy import text
from types import SimpleNamespace

from app.config import LLMPurposeConfig
from app.main import app
from app.services.embedder_registry import EmbedderInfo, child_table, embedder_registry
from app.services.llm import LLMOrchestrator

pytestmark = pytest.mark.asyncio

MODEL_A = "prunecache-model-a"
MODEL_B = "prunecache-model-b"
DIMS = 4
FINGERPRINTS = (f"{MODEL_A}|{DIMS}", f"{MODEL_B}|{DIMS}")


@pytest_asyncio.fixture
async def live_caches(session) -> list[str]:
    """Two real registered fingerprints, each with its own cache child table."""
    for fingerprint, model in zip(FINGERPRINTS, (MODEL_A, MODEL_B)):
        await embedder_registry.register(
            session,
            EmbedderInfo(fingerprint=fingerprint, model_id=model, dims=DIMS, source="llm"),
        )
    tables = [child_table("entity_embedding_cache", fp) for fp in FINGERPRINTS]
    assert await _present(session, tables) == set(tables), "fixture failed to seed both caches"
    yield tables
    for fingerprint in FINGERPRINTS:
        embedder_registry.forget(fingerprint)


async def _present(session, tables: list[str]) -> set[str]:
    rows = (await session.execute(
        text(
            "SELECT tablename FROM pg_tables "
            "WHERE schemaname = 'public' AND tablename = ANY(CAST(:names AS text[]))"
        ),
        {"names": tables},
    )).scalars().all()
    return set(rows)


@asynccontextmanager
async def _embedding_purpose(model: str, dimensions: int | None):
    """Drive the route through a real orchestrator over a real purpose config,
    so the fingerprint under test is the one the configuration produces rather
    than a literal a test chose."""
    orchestrator = LLMOrchestrator(
        {"embedding": LLMPurposeConfig(model=model, dimensions=dimensions)}
    )
    previous = getattr(app.state, "pipeline", None)
    app.state.pipeline = SimpleNamespace(llm=orchestrator)
    try:
        yield orchestrator
    finally:
        app.state.pipeline = previous
        await orchestrator.close()


async def test_unset_dimensions_sentinel_never_drops_a_live_cache(
    client, auth_headers, session, live_caches,
):
    """The reproduction: an unset `dimensions` used to take every cache child."""
    async with _embedding_purpose(MODEL_A, None) as orchestrator:
        assert orchestrator.llm_fingerprint() == f"{MODEL_A}|0"
        response = await client.post("/api/v1/reembed/prune-cache", headers=auth_headers)

    survivors = await _present(session, live_caches)
    assert survivors == set(live_caches), (
        f"prune-cache dropped {sorted(set(live_caches) - survivors)} under the "
        f"unregistered fingerprint {MODEL_A}|0"
    )
    assert response.status_code == 409, response.text
    assert f"{MODEL_A}|0" in response.json()["error"]["message"]


async def test_a_dimension_no_embed_ever_produced_never_drops_a_live_cache(
    client, auth_headers, session, live_caches,
):
    """Same class, non-zero key: `dimensions` set to a width this model never
    emits names a partition nothing registered, so the keep matches nothing."""
    async with _embedding_purpose(MODEL_A, 1024) as orchestrator:
        assert orchestrator.llm_fingerprint() == f"{MODEL_A}|1024"
        response = await client.post("/api/v1/reembed/prune-cache", headers=auth_headers)

    assert await _present(session, live_caches) == set(live_caches)
    assert response.status_code == 409, response.text


async def test_a_registered_fingerprint_whose_cache_child_is_gone_refuses(
    client, auth_headers, session, live_caches,
):
    """The guard's second arm. A registry row without the child table it
    implies leaves nothing to keep, so the sweep would again take every other
    cache; registration alone is not enough to authorise a drop."""
    keep = child_table("entity_embedding_cache", FINGERPRINTS[0])
    await session.execute(text(f"DROP TABLE {keep}"))

    async with _embedding_purpose(MODEL_A, DIMS):
        response = await client.post("/api/v1/reembed/prune-cache", headers=auth_headers)

    assert response.status_code == 409, response.text
    assert keep in response.json()["error"]["message"]
    assert await _present(session, live_caches) == {live_caches[1]}


async def test_a_retired_registry_row_refuses_and_spares_the_live_sibling(
    client, auth_headers, session, live_caches,
):
    """The guard's first arm, isolated. A retired fingerprint still has its
    registry row and its cache child, so arm 2 admits it; only
    `retired_at IS NULL` stands between the operator and a sweep that keeps
    the retired cache and drops every live one."""
    await session.execute(
        text("UPDATE embedders SET retired_at = NOW() WHERE fingerprint = :fp"),
        {"fp": FINGERPRINTS[0]},
    )

    async with _embedding_purpose(MODEL_A, DIMS):
        response = await client.post("/api/v1/reembed/prune-cache", headers=auth_headers)

    survivors = await _present(session, live_caches)
    assert survivors == set(live_caches), (
        f"prune-cache under a RETIRED keep fingerprint dropped "
        f"{sorted(set(live_caches) - survivors)}"
    )
    assert response.status_code == 409, response.text
    assert FINGERPRINTS[0] in response.json()["error"]["message"]


async def test_a_registered_fingerprint_still_prunes_the_retired_children(
    client, auth_headers, session, live_caches,
):
    """The guard refuses ambiguity, not the operation: with the active
    fingerprint registered, the prune drops the others exactly as before."""
    keep, retired = live_caches[0], live_caches[1]

    async with _embedding_purpose(MODEL_A, DIMS):
        response = await client.post("/api/v1/reembed/prune-cache", headers=auth_headers)

    assert response.status_code == 200, response.text
    assert response.json()["deleted"] >= 1
    assert await _present(session, live_caches) == {keep}
    assert retired not in await _present(session, live_caches)


async def test_a_refused_prune_journals_its_refusal(
    client, auth_headers, session, live_caches,
):
    """A destructive maintenance op that refuses silently is invisible to the
    timeline; the refusal journals `outcome=error` on the same operation the
    successful run journals."""
    async with _embedding_purpose(MODEL_A, None):
        response = await client.post("/api/v1/reembed/prune-cache", headers=auth_headers)
    assert response.status_code == 409

    payload = (await session.execute(
        text(
            "SELECT payload FROM events "
            "WHERE event_type = 'maintenance_run' "
            "AND payload->>'operation' = 'prune_caches' "
            "ORDER BY created_at DESC LIMIT 1"
        ),
    )).scalars().first()
    assert payload, "a refused prune-cache journalled nothing"
    assert payload["outcome"] == "error"
    assert payload["detail"]["fingerprint"] == f"{MODEL_A}|0"
    assert payload["detail"]["deleted"] == 0
