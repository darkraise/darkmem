"""The dual-level global arm: relations ranked, resolved to memories (T2.94).

**The load-bearing test is `test_a_foreign_projects_relation_never_leaks`.**
`relation_embeddings` keys on `entity_relations`, which is global by design, so
this is the one channel whose scope cannot be pushed into its vector arm (doc
07 §11). The filter is re-applied on the *asserting memories* instead. Skip
that join and the arm returns rows from every project that happens to assert a
matching edge — a cross-project leak that looks like a good result, which is
why doc 07 restates the rule in two places and why it is pinned here.

**The second is `test_the_arm_is_inert_at_weight_zero`.** Same property T2.32's
PPR arm holds: inert has to mean the same rows, not merely the same scores,
because a zero-weight list still admits a row it alone found onto a page that
would not have contained it.
"""

from __future__ import annotations

import pytest
from sqlalchemy import text

from app.config import FEATURE_FLAGS_DEFAULTS
from app.repositories.vector import MemoryFilter
from app.services import relation_embeddings as re_mod
from app.services.hybrid_search import HybridSearchService
from app.services.rank_fusion import LIST_WEIGHT_KEYS, dual_list_weight
from app.utils.ids import new_id

FINGERPRINT = "dual-probe|8"
PROJECT = "t294-dual"
OTHER_PROJECT = "t294-dual-other"


class FakeEmbedder:
    def __init__(self, vectors: dict[str, list[float]], fingerprint: str = FINGERPRINT):
        self.vectors = vectors
        self.fingerprint = fingerprint

    async def embed_batch_chunked(self, texts, chunk_size, concurrency):
        return [self.vectors[t] for t in texts], self.fingerprint


@pytest.fixture(autouse=True)
def _forget_probe_fingerprint():
    from app.services.embedder_registry import embedder_registry

    embedder_registry.forget(FINGERPRINT)
    yield
    embedder_registry.forget(FINGERPRINT)


_INSERT_MEMORY = text(
    """
    INSERT INTO memories (id, content, source, project, status)
    VALUES (CAST(:id AS uuid), :content, 'api', CAST(:project AS text), 'active')
    """
)
_INSERT_ENTITY = text(
    """
    INSERT INTO entities (name, entity_type, memory_ids)
    VALUES (:name, 'tool', CAST(:memory_ids AS uuid[]))
    RETURNING id
    """
)
_INSERT_RELATION = text(
    """
    INSERT INTO entity_relations (
        source_entity_id, target_entity_id, rel_type, memory_ids
    )
    VALUES (CAST(:src AS uuid), CAST(:tgt AS uuid), :rel_type,
            CAST(:memory_ids AS uuid[]))
    RETURNING id
    """
)


def near() -> list[float]:
    return [1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]


def far() -> list[float]:
    return [0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]


async def seed_edge(session, src_name, tgt_name, *, project=PROJECT, rel_type="REPLACES"):
    """One memory asserting one relation, with both endpoint entities."""
    memory_id = new_id()
    await session.execute(
        _INSERT_MEMORY,
        {"id": str(memory_id), "content": f"{src_name} {rel_type} {tgt_name}",
         "project": project},
    )
    src = (await session.execute(
        _INSERT_ENTITY, {"name": src_name, "memory_ids": [str(memory_id)]}
    )).scalar_one()
    tgt = (await session.execute(
        _INSERT_ENTITY, {"name": tgt_name, "memory_ids": [str(memory_id)]}
    )).scalar_one()
    relation = (await session.execute(
        _INSERT_RELATION,
        {"src": str(src), "tgt": str(tgt), "rel_type": rel_type,
         "memory_ids": [str(memory_id)]},
    )).scalar_one()
    return memory_id, relation


async def embed(session, phrases: dict[str, list[float]], relation_ids):
    return await re_mod.embed_relations(
        session, FakeEmbedder(phrases), relation_ids=relation_ids,
    )


def service(session):
    return HybridSearchService(llm=None, session=session)


# ── the channel ──────────────────────────────────────────────────────


async def test_a_matching_edge_resolves_to_its_asserting_memory(session):
    memory_id, relation = await seed_edge(session, "redis", "valkey")
    await embed(session, {"redis REPLACES valkey": near()}, [str(relation)])

    rows = await service(session)._dual_level_search(
        near(), FINGERPRINT, MemoryFilter(project=PROJECT), 0.3, 50,
    )

    assert [r["memory_id"] for r in rows] == [str(memory_id)]
    assert rows[0]["score"] == pytest.approx(1.0, abs=1e-6)


async def test_a_foreign_projects_relation_never_leaks(session):
    """The rule doc 07 §11 states twice. `entity_relations` carries no project,
    so the vector arm cannot scope itself; the filter is re-applied on the
    asserting memories. Without that join this returns the foreign row, and it
    looks like a good hit."""
    mine, my_relation = await seed_edge(session, "redis", "valkey", project=PROJECT)
    theirs, their_relation = await seed_edge(
        session, "postgres", "mysql", project=OTHER_PROJECT,
    )
    await embed(
        session,
        {"redis REPLACES valkey": near(), "postgres REPLACES mysql": near()},
        [str(my_relation), str(their_relation)],
    )

    rows = await service(session)._dual_level_search(
        near(), FINGERPRINT, MemoryFilter(project=PROJECT), 0.3, 50,
    )

    returned = {r["memory_id"] for r in rows}
    assert str(mine) in returned
    assert str(theirs) not in returned


async def test_a_wide_request_returns_both_projects(session):
    """The complement: without a declared project there is nothing to leak
    *from*, and the arm behaves like every other wide read rather than
    inventing a scope of its own."""
    mine, my_relation = await seed_edge(session, "redis", "valkey", project=PROJECT)
    theirs, their_relation = await seed_edge(
        session, "postgres", "mysql", project=OTHER_PROJECT,
    )
    await embed(
        session,
        {"redis REPLACES valkey": near(), "postgres REPLACES mysql": near()},
        [str(my_relation), str(their_relation)],
    )

    rows = await service(session)._dual_level_search(near(), FINGERPRINT, None, 0.3, 50)

    assert {str(mine), str(theirs)} <= {r["memory_id"] for r in rows}


async def test_a_distant_edge_ranks_below_a_matching_one(session):
    close_mem, close_rel = await seed_edge(session, "redis", "valkey")
    far_mem, far_rel = await seed_edge(session, "python", "rust")
    await embed(
        session,
        {"redis REPLACES valkey": near(), "python REPLACES rust": far()},
        [str(close_rel), str(far_rel)],
    )

    rows = await service(session)._dual_level_search(
        near(), FINGERPRINT, MemoryFilter(project=PROJECT), 0.3, 50,
    )

    order = [r["memory_id"] for r in rows]
    assert order.index(str(close_mem)) < order.index(str(far_mem))


async def test_one_memory_asserting_two_edges_appears_once(session):
    """`memory_ids` is an array and one memory can assert several relations, so
    without the aggregate the same memory enters the fusion twice and splits
    its own RRF mass — the shape invariant 9's id drift takes."""
    memory_id, first = await seed_edge(session, "redis", "valkey")
    src = (await session.execute(
        _INSERT_ENTITY, {"name": "keydb", "memory_ids": [str(memory_id)]}
    )).scalar_one()
    tgt = (await session.execute(
        _INSERT_ENTITY, {"name": "memcached", "memory_ids": [str(memory_id)]}
    )).scalar_one()
    second = (await session.execute(
        _INSERT_RELATION,
        {"src": str(src), "tgt": str(tgt), "rel_type": "REPLACES",
         "memory_ids": [str(memory_id)]},
    )).scalar_one()
    await embed(
        session,
        {"redis REPLACES valkey": near(), "keydb REPLACES memcached": near()},
        [str(first), str(second)],
    )

    rows = await service(session)._dual_level_search(
        near(), FINGERPRINT, MemoryFilter(project=PROJECT), 0.3, 50,
    )

    assert [r["memory_id"] for r in rows].count(str(memory_id)) == 1


async def test_a_cold_partition_costs_the_order_nothing(session):
    """No relation vectors under this fingerprint yet is a not-yet, not a
    fault: the arm returns empty and the base channels answer alone."""
    rows = await service(session)._dual_level_search(
        near(), "never-registered|8", MemoryFilter(project=PROJECT), 0.3, 50,
    )
    assert rows == []


async def test_the_arm_is_skipped_entirely_at_zero_weight(session):
    """Inert must also mean free — no partition read on every query."""
    _, relation = await seed_edge(session, "redis", "valkey")
    await embed(session, {"redis REPLACES valkey": near()}, [str(relation)])

    rows = await service(session)._dual_level_search(
        near(), FINGERPRINT, MemoryFilter(project=PROJECT), 0.0, 50,
    )
    assert rows == []


# ── inertness and the flag surface ───────────────────────────────────


def test_the_dual_flags_ship_off():
    assert FEATURE_FLAGS_DEFAULTS["dual_level_enabled"] is False
    assert FEATURE_FLAGS_DEFAULTS["w_dual"] == 0.0


def test_a_weight_without_its_flag_stays_inert():
    assert dual_list_weight({}) == 0.0
    assert dual_list_weight({"w_dual": 0.4}) == 0.0
    assert dual_list_weight({"dual_level_enabled": True, "w_dual": 0.4}) == 0.4
    assert dual_list_weight({"dual_level_enabled": True}) == 0.0
    assert "w_dual" in LIST_WEIGHT_KEYS


def test_the_arm_is_inert_at_weight_zero():
    semantic = [{"memory_id": "m1", "score": 0.9}, {"memory_id": "m2", "score": 0.5}]
    keyword = [{"memory_id": "m2", "score": 0.4}]
    intruder = [{"memory_id": "m9", "score": 1.0}]

    without = HybridSearchService._rrf_fuse(semantic, keyword, 0.7, 10)
    with_inert = HybridSearchService._rrf_fuse(
        semantic, keyword, 0.7, 10, None, 0.0, intruder, 0.0,
    )

    assert [r["memory_id"] for r in with_inert] == [r["memory_id"] for r in without]
    assert [r["rrf_score"] for r in with_inert] == [r["rrf_score"] for r in without]
    assert "m9" not in {r["memory_id"] for r in with_inert}


def test_the_arm_moves_the_order_once_it_carries_weight():
    semantic = [{"memory_id": "m1", "score": 0.9}, {"memory_id": "m2", "score": 0.5}]
    keyword = [{"memory_id": "m2", "score": 0.4}]
    graph = [{"memory_id": "m2", "score": 1.0}]

    fused = HybridSearchService._rrf_fuse(
        semantic, keyword, 0.7, 10, None, 0.0, graph, 5.0,
    )
    assert fused[0]["memory_id"] == "m2"


def test_both_doors_derive_the_weight_through_one_helper():
    """Two doors reading the flag pair separately agree exactly while the arm
    is off and diverge the moment it is flipped on — the T2.58 shape."""
    import ast
    from pathlib import Path

    backend = Path(__file__).resolve().parents[1]
    for name in ("pipeline.py", "layer_composition.py"):
        source = (backend / "app" / "services" / name).read_text()
        assert "dual_list_weight" in source, f"{name} does not use the helper"
        tree = ast.parse(source)
        # No door may read the flag pair directly; that is the helper's job.
        literals = {
            node.value
            for node in ast.walk(tree)
            if isinstance(node, ast.Constant) and isinstance(node.value, str)
        }
        assert "dual_level_enabled" not in literals, (
            f"{name} reads the gate flag directly instead of through "
            "dual_list_weight"
        )


def test_the_harness_no_longer_blocks_the_dual_arm():
    """T2.94's last Done-when: the blocked reason is removed rather than left
    stale, so `--arm w_dual` measures instead of refusing."""
    import sys

    backend = str(__import__("pathlib").Path(__file__).resolve().parents[1] / "scripts")
    if backend not in sys.path:
        sys.path.insert(0, backend)
    from benchlib import arm_ablation

    assert arm_ablation.resolve_ablatable("w_dual").blocked is None
