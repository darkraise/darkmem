"""T2.101 — fusing two live entity rows without breaking the graph.

``tests/test_repo_entity_anchoring.py`` owns the end-to-end claim: the order a
real deployment produces (memories first, repo indexed later) now converges on
the same single node the eager order produces, at the same threshold and under
the same discriminator. This suite owns the half that claim rests on — that a
merge of two *live* rows moves everything that pointed at the losing one, and
that a merge which cannot complete leaves two intact nodes rather than one
corrupted one.

What is asserted here, and why each is a property a naive suite would miss:

* **Both endpoint directions move.** A relation *into* the loser is as much a
  dangling edge as one *out* of it, and a pass that repoints only
  ``source_entity_id`` passes any test whose fixture happens to write edges one
  way.
* **A repointed endpoint can collide, and the collision is a merge.**
  ``entity_relations`` is UNIQUE on ``(source, target, rel_type)``. Letting the
  constraint raise turns a routine merge into a failed one; silently dropping
  the duplicate loses whichever memories only that row asserted. The arrays are
  unioned and the greater weight kept, exactly as ``create_relationship``'s
  ``ON CONFLICT`` does.
* **The cascade is not allowed to clean up after the loop.** The FK onto
  ``entities.id`` is ``ON DELETE CASCADE``, so a relation the repointing missed
  would be *destroyed* by the final DELETE — no error, no symptom, another
  memory's edge simply gone. The pass counts them first and refuses.
* **``knowledge_triples`` follows the survivor.** ``subject_id``/``object_id``
  are entity ids with no foreign key, and ``review_ranking``'s salience arm
  reads a dangling one as zero neighbours — a degradation that is silent and
  permanent.
* **The threshold is the write path's, read out of the write path.** A literal
  copied into this module could drift from Phase 4's; the test reads Phase 4's
  own ``threshold=`` keyword out of ``pipeline.py``'s AST instead.

The unit tests run inside the rolled-back ``session`` fixture; only the
end-to-end order tests need a committing factory, and those live in the
anchoring suite beside the claim they close.
"""
from __future__ import annotations

import ast
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import text

from app.services import entity_merge as merge_mod
from app.services.embedder_registry import EmbedderInfo, child_table, embedder_registry
from app.services.entity_merge import (
    MERGE_THRESHOLD,
    EntityMergeRefused,
    merge_entities,
    merge_repo_entity_duplicates,
    repo_entity_merge_candidates,
)

BACKEND = Path(__file__).resolve().parent.parent
MODULE_PATH = BACKEND / "app" / "services" / "entity_merge.py"
PIPELINE_PATH = BACKEND / "app" / "services" / "pipeline.py"

DIMS = 8
FINGERPRINT = "merge-unit|8"


class FingerprintOnly:
    """The whole embedder surface this pass needs: it reads vectors, never
    produces them, so an orchestrator is only ever asked to name a partition."""

    def __init__(self, fingerprint: str = FINGERPRINT):
        self._fingerprint = fingerprint

    def llm_fingerprint(self) -> str:
        return self._fingerprint


@pytest.fixture(autouse=True)
def _forget_fingerprint():
    embedder_registry.forget(FINGERPRINT)
    yield
    embedder_registry.forget(FINGERPRINT)


def _vec(*values: float) -> list[float]:
    out = [0.0] * DIMS
    for index, value in enumerate(values):
        out[index] = value
    return out


async def _register(session) -> None:
    await embedder_registry.register(
        session,
        EmbedderInfo(
            fingerprint=FINGERPRINT, model_id="merge-unit", dims=DIMS, source="llm",
        ),
    )


async def _entity(
    session, name: str, entity_type: str = "tool", *,
    repo_ids=(), memory_ids=(), properties: str = "{}", created_at: datetime | None = None,
) -> str:
    # `created_at DEFAULT now()` is transaction time, so rows inserted in one
    # test share a timestamp — which would leave the survivor rule's age arm
    # decided by the random id tie-break. Any test that means to exercise age
    # states the timestamps.
    return (await session.execute(
        text("""
            INSERT INTO entities (name, entity_type, properties, memory_ids,
                                  repo_ids, created_at)
            VALUES (:name, :etype, CAST(:props AS jsonb),
                    CAST(:mids AS uuid[]), CAST(:rids AS uuid[]),
                    COALESCE(CAST(:created AS timestamptz), now()))
            RETURNING CAST(id AS text)
        """),
        {
            "name": name, "etype": entity_type, "props": properties,
            "mids": [str(m) for m in memory_ids],
            "rids": [str(r) for r in repo_ids],
            "created": created_at,
        },
    )).scalar_one()


async def _embed(session, entity_id: str, vector: list[float]) -> None:
    table = child_table(merge_mod.PARENT_TABLE, FINGERPRINT)
    await session.execute(
        text(f"""
            INSERT INTO {table} (entity_id, fingerprint, embedding)
            VALUES (CAST(:eid AS uuid), CAST(:fp AS text), CAST(:vec AS vector))
        """),
        {"eid": entity_id, "fp": FINGERPRINT, "vec": str(vector)},
    )


async def _relation(
    session, source: str, target: str, rel_type: str = "DEPENDS_ON", *,
    memory_ids=(), repo_ids=(), weight: float = 0.5, properties: str = "{}",
) -> str:
    return (await session.execute(
        text("""
            INSERT INTO entity_relations
                (source_entity_id, target_entity_id, rel_type, properties,
                 weight, memory_ids, repo_ids)
            VALUES (CAST(:src AS uuid), CAST(:tgt AS uuid), :rel,
                    CAST(:props AS jsonb), :w,
                    CAST(:mids AS uuid[]), CAST(:rids AS uuid[]))
            RETURNING CAST(id AS text)
        """),
        {
            "src": source, "tgt": target, "rel": rel_type, "props": properties,
            "w": weight,
            "mids": [str(m) for m in memory_ids],
            "rids": [str(r) for r in repo_ids],
        },
    )).scalar_one()


async def _edges(session) -> list[tuple]:
    rows = (await session.execute(text("""
        SELECT s.name, r.rel_type, t.name, r.weight,
               cardinality(r.memory_ids), cardinality(r.repo_ids)
        FROM entity_relations r
        JOIN entities s ON s.id = r.source_entity_id
        JOIN entities t ON t.id = r.target_entity_id
        ORDER BY s.name, r.rel_type, t.name
    """))).all()
    return [tuple(row) for row in rows]


async def _names(session) -> list[str]:
    return list((await session.execute(
        text("SELECT name FROM entities ORDER BY name")
    )).scalars().all())


async def _pair(session, *, loser_repo=False) -> tuple[str, str]:
    """``postgres`` (repo-asserted) and ``postgresql`` (memory-asserted), the
    calibration pair, embedded far enough apart to be well inside 0.85."""
    await _register(session)
    repo_id = uuid4()
    survivor = await _entity(session, "postgres", "database", repo_ids=[repo_id])
    loser = await _entity(
        session, "postgresql", "database",
        memory_ids=[uuid4()], repo_ids=[repo_id] if loser_repo else (),
    )
    await _embed(session, survivor, _vec(1.0))
    await _embed(session, loser, _vec(0.999, 0.0447))
    await session.flush()
    return survivor, loser


# ── relation endpoints ───────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_relation_endpoints_move_in_both_directions(session):
    """An inbound edge is as dangling as an outbound one."""
    survivor, loser = await _pair(session)
    app = await _entity(session, "our-app", "project")
    driver = await _entity(session, "asyncpg", "tool")
    await _relation(session, app, loser, "DEPENDS_ON")
    await _relation(session, loser, driver, "USES")
    await session.flush()

    pair = await merge_entities(session, survivor, loser)

    assert pair is not None
    assert (pair.survivor_name, pair.loser_name) == ("postgres", "postgresql")
    assert pair.relations_repointed == 2
    assert pair.relations_folded == 0
    assert await _edges(session) == [
        ("our-app", "DEPENDS_ON", "postgres", 0.5, 0, 0),
        ("postgres", "USES", "asyncpg", 0.5, 0, 0),
    ]
    assert "postgresql" not in await _names(session)


@pytest.mark.asyncio
async def test_a_colliding_endpoint_is_folded_not_raised(session):
    """The `(source, target, rel_type)` constraint's case, and it is a merge.

    Both rows are real assertions: letting the constraint raise would abort a
    routine merge, and dropping the duplicate outright would lose whichever
    memories only it asserted.
    """
    survivor, loser = await _pair(session)
    app = await _entity(session, "our-app", "project")
    kept_memory, dropped_memory, repo = uuid4(), uuid4(), uuid4()
    await _relation(
        session, app, survivor, "DEPENDS_ON",
        memory_ids=[kept_memory], weight=0.4, properties='{"keep": 1}',
    )
    await _relation(
        session, app, loser, "DEPENDS_ON",
        memory_ids=[dropped_memory], repo_ids=[repo], weight=0.9,
        properties='{"keep": 2, "extra": 3}',
    )
    await session.flush()

    pair = await merge_entities(session, survivor, loser)

    assert (pair.relations_repointed, pair.relations_folded) == (0, 1)
    assert await _edges(session) == [
        ("our-app", "DEPENDS_ON", "postgres", 0.9, 2, 1)
    ], "the survivor's edge keeps both assertions and the greater weight"

    props = (await session.execute(text(
        "SELECT properties FROM entity_relations"
    ))).scalar_one()
    assert props == {"keep": 1, "extra": 3}, (
        "the keeper's own keys win; the folded row contributes what it alone had"
    )


@pytest.mark.asyncio
async def test_an_edge_between_the_pair_becomes_a_self_loop(session):
    """Kept, not dropped, because that is what the eager order produces.

    Phase 4 canonicalises both endpoint names onto one and Phase 5 then
    resolves both to the same id, so a retroactive pass that deleted the edge
    instead would make the two orders disagree again — in a different column.
    """
    survivor, loser = await _pair(session)
    await _relation(session, loser, survivor, "RELATED_TO")
    await session.flush()

    pair = await merge_entities(session, survivor, loser)

    assert (pair.relations_repointed, pair.relations_folded) == (1, 0)
    assert await _edges(session) == [("postgres", "RELATED_TO", "postgres", 0.5, 0, 0)]


@pytest.mark.asyncio
async def test_two_edges_collapsing_onto_one_self_loop_fold_together(session):
    """The collision partner can be an edge this same loop already moved."""
    survivor, loser = await _pair(session)
    left, right = uuid4(), uuid4()
    await _relation(session, loser, survivor, "RELATED_TO", memory_ids=[left])
    await _relation(session, survivor, loser, "RELATED_TO", memory_ids=[right])
    await session.flush()

    pair = await merge_entities(session, survivor, loser)

    assert (pair.relations_repointed, pair.relations_folded) == (1, 1)
    assert await _edges(session) == [
        ("postgres", "RELATED_TO", "postgres", 0.5, 2, 0)
    ]


@pytest.mark.asyncio
async def test_a_stranded_relation_refuses_the_merge_rather_than_cascading(
    session, monkeypatch,
):
    """The guard that stops the FK cascade from doing the cleanup silently.

    Driven by neutering the repointing rather than by contriving a graph the
    loop misses: what is asserted is that the pass *checks* before deleting, so
    an edge left behind for any reason aborts the merge instead of vanishing
    with the row.
    """
    survivor, loser = await _pair(session)
    app = await _entity(session, "our-app", "project")
    relation_id = await _relation(session, app, loser, "DEPENDS_ON")
    await session.flush()

    async def _no_repointing(session, *, survivor_id, loser_id):
        return 0, 0

    monkeypatch.setattr(merge_mod, "_repoint_relations", _no_repointing)

    with pytest.raises(EntityMergeRefused, match="still reference the losing"):
        await merge_entities(session, survivor, loser)

    assert sorted(await _names(session)) == ["our-app", "postgres", "postgresql"], (
        "a refused merge must leave two intact nodes, never one and a stump"
    )
    survivors = (await session.execute(
        text("SELECT CAST(target_entity_id AS text) FROM entity_relations "
             "WHERE id = CAST(:r AS uuid)"),
        {"r": relation_id},
    )).scalar_one()
    assert survivors == loser


# ── everything else that pointed at the losing id ────────────────────────


@pytest.mark.asyncio
async def test_knowledge_triple_endpoints_follow_the_survivor(session):
    """No foreign key holds these, and nothing would report the dangling id —
    ``review_ranking``'s salience arm would just read zero neighbours forever."""
    survivor, loser = await _pair(session)
    fact_id = uuid4()
    await session.execute(
        text("""
            INSERT INTO knowledge_triples
                (id, subject_id, object_id, subject_name, object_name,
                 rel_type, reference_time, fact, triple_key)
            VALUES (CAST(:id AS uuid), CAST(:subj AS uuid), CAST(:obj AS uuid),
                    'postgresql', 'postgresql', 'RELATED_TO', now(),
                    'we run postgresql', 'k')
        """),
        {"id": str(fact_id), "subj": loser, "obj": loser},
    )
    await session.flush()

    await merge_entities(session, survivor, loser)

    row = (await session.execute(text(
        "SELECT CAST(subject_id AS text), CAST(object_id AS text) "
        "FROM knowledge_triples"
    ))).one()
    assert tuple(row) == (survivor, survivor)


@pytest.mark.asyncio
async def test_the_losing_rows_vector_goes_with_it(session):
    """Through the partition's ``ON DELETE CASCADE``, which reaches every
    fingerprint's child table rather than only the active one — the reason this
    pass needs no cross-partition sweep of its own (invariant 2)."""
    survivor, loser = await _pair(session)

    await merge_entities(session, survivor, loser)

    table = child_table(merge_mod.PARENT_TABLE, FINGERPRINT)
    remaining = (await session.execute(
        text(f"SELECT CAST(entity_id AS text) FROM {table}")
    )).scalars().all()
    assert remaining == [survivor]


@pytest.mark.asyncio
async def test_the_survivors_display_name_still_renders_its_own_name(session):
    """Invariant 7 pairs a lowercase name with the original casing of *that*
    name. Adopting a losing ``postgresql`` row's ``PostgreSQL`` onto a surviving
    ``postgres`` row would make the UI render a name the graph does not hold."""
    await _register(session)
    repo_id = uuid4()
    survivor = await _entity(
        session, "postgres", "database", repo_ids=[repo_id], properties="{}",
    )
    loser = await _entity(
        session, "postgresql", "database", memory_ids=[uuid4()],
        properties='{"display_name": "PostgreSQL", "note": "kept"}',
    )
    await session.flush()

    await merge_entities(session, survivor, loser)

    props = (await session.execute(text(
        "SELECT properties FROM entities WHERE name = 'postgres'"
    ))).scalar_one()
    assert props == {"note": "kept"}, (
        "other keys are inherited; a display_name that does not lowercase to "
        "the surviving name is not"
    )


@pytest.mark.asyncio
async def test_merging_a_non_tech_type_leaves_every_memory_row_alone(session):
    """``technologies_for_memory`` projects only ``TECH_TYPES`` members, so a
    ``concept`` merge cannot change any array — and recomputing anyway would
    bump ``updated_at`` through the trigger on memories nothing changed."""
    await _register(session)
    memory_id = uuid4()
    await session.execute(
        text("INSERT INTO memories (id, content, source) "
             "VALUES (CAST(:id AS uuid), 'a note', 'api')"),
        {"id": str(memory_id)},
    )
    survivor = await _entity(session, "caching", "concept", repo_ids=[uuid4()])
    loser = await _entity(session, "caches", "concept", memory_ids=[memory_id])
    await session.flush()
    before = (await session.execute(
        text("SELECT updated_at FROM memories WHERE id = CAST(:m AS uuid)"),
        {"m": str(memory_id)},
    )).scalar_one()

    pair = await merge_entities(session, survivor, loser)

    assert pair.memories_retouched == 0
    after = (await session.execute(
        text("SELECT updated_at, technologies FROM memories "
             "WHERE id = CAST(:m AS uuid)"),
        {"m": str(memory_id)},
    )).one()
    assert (after[0], after[1]) == (before, [])


# ── the survivor rule, and the refusals ──────────────────────────────────


@pytest.mark.asyncio
async def test_the_repo_asserted_row_survives_whichever_side_is_named_first(
    session,
):
    """Order-independence, which is the whole point: the pass may reach either
    row first and must land on the same node either way."""
    survivor, loser = await _pair(session)

    pair = await merge_entities(session, loser, survivor)

    assert (pair.survivor_name, pair.loser_name) == ("postgres", "postgresql")


@pytest.mark.asyncio
@pytest.mark.parametrize("older", ["postgres", "postgresql"])
async def test_two_repo_asserted_rows_break_the_tie_on_age(session, older):
    """With no repo/memory asymmetry the rule falls back to the older row, id
    as tie-break — the supersession detector's shape, and for the same reason.

    Driven from both sides: a rule that always kept the first-named row would
    pass one parameter and fail the other.
    """
    await _register(session)
    repo_id = uuid4()
    recent = datetime(2026, 1, 1, tzinfo=UTC)
    stamps = {"postgres": recent, "postgresql": recent}
    stamps[older] = datetime(2025, 1, 1, tzinfo=UTC)
    first = await _entity(
        session, "postgres", "database", repo_ids=[repo_id],
        created_at=stamps["postgres"],
    )
    second = await _entity(
        session, "postgresql", "database", repo_ids=[repo_id],
        created_at=stamps["postgresql"],
    )
    await session.flush()

    pair = await merge_entities(session, first, second)

    assert pair.survivor_name == older


@pytest.mark.asyncio
async def test_equal_timestamps_fall_through_to_the_id_tie_break(session):
    """Same-transaction rows share ``now()``, so age decides nothing and the
    outcome must still not depend on which side the scan reached first."""
    survivor, loser = await _pair(session, loser_repo=True)
    expected = min(survivor, loser)

    pair = await merge_entities(session, loser, survivor)

    assert pair.survivor_id == expected


@pytest.mark.asyncio
async def test_merge_refuses_across_entity_type(session):
    """A name embedding cannot tell a ``tool`` named ``react`` from a
    ``concept`` named ``react``. The probe is type-constrained so this is
    unreachable through the pass; it is asserted rather than assumed because
    fusing them corrupts the ``(name, entity_type)`` binding the graph rests on.
    """
    await _register(session)
    tool = await _entity(session, "react", "tool", repo_ids=[uuid4()])
    concept = await _entity(session, "react", "concept", memory_ids=[uuid4()])
    await session.flush()

    with pytest.raises(EntityMergeRefused, match="across entity_type"):
        await merge_entities(session, tool, concept)

    assert await _names(session) == ["react", "react"]


# ── the pass ─────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_the_pass_merges_the_pair_and_a_second_run_changes_nothing(
    session,
):
    """Idempotence stated as byte-identity of the surviving rows, not as a
    merge count: a second pass that re-wrote the same values with a different
    array order would pass a count assertion and still be a rewrite."""
    survivor, loser = await _pair(session)
    app = await _entity(session, "our-app", "project")
    await _relation(session, app, loser, "DEPENDS_ON")
    await session.flush()

    first = await merge_repo_entity_duplicates(session, FingerprintOnly())
    assert (first.merged, first.fingerprint) == (1, FINGERPRINT)
    snapshot = (await session.execute(text(
        "SELECT CAST(id AS text), name, entity_type, properties, "
        "       CAST(memory_ids AS text), CAST(repo_ids AS text), created_at "
        "FROM entities ORDER BY id"
    ))).all()
    edges = await _edges(session)

    second = await merge_repo_entity_duplicates(session, FingerprintOnly())

    assert second.merged == 0
    assert (await session.execute(text(
        "SELECT CAST(id AS text), name, entity_type, properties, "
        "       CAST(memory_ids AS text), CAST(repo_ids AS text), created_at "
        "FROM entities ORDER BY id"
    ))).all() == snapshot
    assert await _edges(session) == edges


@pytest.mark.asyncio
async def test_only_repo_asserted_entities_with_a_vector_are_probed(session):
    """The scope, on both halves. A memory-only entity is not this pass's
    business — Phase 4 already deduped it against everything embedded at write
    time — and a repo entity with no vector is the anchoring job's, not this
    one's."""
    await _register(session)
    embedded = await _entity(session, "repo-tool", repo_ids=[uuid4()])
    await _embed(session, embedded, _vec(1.0))
    unembedded = await _entity(session, "repo-tool-no-vector", repo_ids=[uuid4()])
    memory_only = await _entity(session, "memory-tool", memory_ids=[uuid4()])
    await _embed(session, memory_only, _vec(0.0, 1.0))
    await session.flush()

    candidates = await repo_entity_merge_candidates(session, FINGERPRINT, 100)

    assert [row["entity_id"] for row in candidates] == [embedded]
    assert unembedded not in {row["entity_id"] for row in candidates}


@pytest.mark.asyncio
async def test_a_zero_batch_disables_the_pass(session):
    """The knob's documented off position, exercised rather than described."""
    await _pair(session)

    outcome = await merge_repo_entity_duplicates(
        session, FingerprintOnly(), candidate_batch=0,
    )

    assert (outcome.merged, outcome.probed) == (0, 0)
    assert "postgresql" in await _names(session)


@pytest.mark.asyncio
async def test_an_install_with_no_embedded_fingerprint_is_a_no_op(session):
    """Nothing embedded means no partition to read, and the pass says so rather
    than inventing a fingerprint from static config."""
    outcome = await merge_repo_entity_duplicates(session, FingerprintOnly())

    assert (outcome.merged, outcome.fingerprint) == (0, None)


# ── structural guards ────────────────────────────────────────────────────


def test_the_retroactive_threshold_is_the_write_paths():
    """Read out of ``pipeline.py``'s AST, not copied.

    "The same 0.85 the write path uses" is only true while the two agree, and
    nothing else would notice them drifting: a looser bar here merges pairs
    Phase 4 refuses, which is the one edit the task's scope forbids.
    """
    tree = ast.parse(PIPELINE_PATH.read_text(), filename=str(PIPELINE_PATH))
    thresholds = {
        keyword.value.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "find_similar_entity"
        for keyword in node.keywords
        if keyword.arg == "threshold" and isinstance(keyword.value, ast.Constant)
    }
    assert thresholds == {MERGE_THRESHOLD}


def test_the_module_never_calls_llm_fingerprint():
    """``llm_fingerprint()`` is a formatter over static config and can name a
    partition no embed ever wrote to. Keying the candidate query on one would
    make this pass report that no repo entity has a duplicate, every run,
    forever."""
    tree = ast.parse(MODULE_PATH.read_text(), filename=str(MODULE_PATH))
    called = {
        node.func.attr
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
    }
    assert "llm_fingerprint" not in called


def test_every_child_table_is_reached_through_the_parent_constant():
    """One hardcoded ``__<slug>`` child and every probe silently answers about
    the wrong embedder."""
    tree = ast.parse(MODULE_PATH.read_text(), filename=str(MODULE_PATH))
    parents = set()
    for node in ast.walk(tree):
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                and node.func.id == "child_table"):
            first = node.args[0]
            parents.add(first.value if isinstance(first, ast.Constant) else first.id)
    assert parents == {"PARENT_TABLE"}
    assert merge_mod.PARENT_TABLE == "entity_embeddings"
