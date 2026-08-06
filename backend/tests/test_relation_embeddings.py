"""The `relation_embeddings` writer and its two-armed refresh (T2.49).

**Invariant 2 is enforced by the table, not by a predicate — and this suite
says so because a mutation drill proved it.** Deleting the
`AND e.fingerprint = :fp` clause from the missing-vector join leaves every test
here green, which is the correct outcome rather than a gap in the suite: each
fingerprint has its own child table, so a row under another embedder is
unreachable rather than filtered. The clause is redundant by construction. What
carries the invariant is `child_table(PARENT_TABLE, fingerprint)`, covered by
`test_every_child_table_is_reached_through_the_parent_constant` and by the two
behavioural tests below that ask the question from both fingerprints.

**The second is `test_the_module_never_calls_llm_fingerprint`.** The `|0`
sentinel trap (T2.68, T2.83) is worse for this job than for a reader: under a
phantom fingerprint the exact arm finds *every* relation missing, re-embeds the
whole graph into a table nothing reads, and reports a rising row count forever.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest
from sqlalchemy import text

from app.services import relation_embeddings as re_mod
from app.services.embedder_registry import child_table
from app.utils.ids import new_id

BACKEND = Path(__file__).resolve().parent.parent
MODULE_PATH = BACKEND / "app" / "services" / "relation_embeddings.py"

FINGERPRINT = "relation-probe|8"
OTHER_FINGERPRINT = "relation-probe-other|8"

PROJECT = "t249-relations"


class FakeEmbedder:
    """Returns a fixed vector per text under one fingerprint.

    Deliberately not a similarity model: this module's correctness is about
    which rows are written under which fingerprint, never about geometry.
    """

    def __init__(self, fingerprint: str = FINGERPRINT):
        self.fingerprint = fingerprint
        self.texts: list[str] = []
        self.calls = 0

    async def embed_batch_chunked(self, texts, chunk_size, concurrency):
        self.calls += 1
        self.texts.extend(texts)
        return [[float(i), 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
                for i, _ in enumerate(texts)], self.fingerprint


class MiscountingEmbedder(FakeEmbedder):
    async def embed_batch_chunked(self, texts, chunk_size, concurrency):
        vectors, fp = await super().embed_batch_chunked(texts, chunk_size, concurrency)
        return vectors[:-1], fp


@pytest.fixture(autouse=True)
def _forget_probe_fingerprints():
    """The registry cache is process-wide while the test database is rolled
    back; without this a later test finds the fingerprint "known", skips the
    DDL, and inserts into a child table its own transaction never created."""
    from app.services.embedder_registry import embedder_registry

    for fp in (FINGERPRINT, OTHER_FINGERPRINT):
        embedder_registry.forget(fp)
    yield
    for fp in (FINGERPRINT, OTHER_FINGERPRINT):
        embedder_registry.forget(fp)


# ── fixtures ─────────────────────────────────────────────────────────

_INSERT_MEMORY = text(
    """
    INSERT INTO memories (id, content, source, project, status)
    VALUES (CAST(:id AS uuid), :content, 'api', CAST(:project AS text), 'active')
    """
)

_INSERT_ENTITY = text(
    """
    INSERT INTO entities (name, entity_type, memory_ids)
    VALUES (:name, :entity_type, CAST(:memory_ids AS uuid[]))
    RETURNING id
    """
)

_INSERT_RELATION = text(
    """
    INSERT INTO entity_relations (source_entity_id, target_entity_id, rel_type)
    VALUES (CAST(:src AS uuid), CAST(:tgt AS uuid), :rel_type)
    RETURNING id
    """
)


async def seed_relation(session, src_name: str, tgt_name: str, rel_type="USES"):
    memory_id = new_id()
    await session.execute(
        _INSERT_MEMORY,
        {"id": str(memory_id), "content": "seed", "project": PROJECT},
    )
    src = (await session.execute(
        _INSERT_ENTITY,
        {"name": src_name, "entity_type": "tool", "memory_ids": [str(memory_id)]},
    )).scalar_one()
    tgt = (await session.execute(
        _INSERT_ENTITY,
        {"name": tgt_name, "entity_type": "tool", "memory_ids": [str(memory_id)]},
    )).scalar_one()
    return (await session.execute(
        _INSERT_RELATION,
        {"src": str(src), "tgt": str(tgt), "rel_type": rel_type},
    )).scalar_one()


async def stored(session, fingerprint=FINGERPRINT) -> set[str]:
    table = child_table(re_mod.PARENT_TABLE, fingerprint)
    rows = await session.execute(
        text(f"SELECT CAST(relation_id AS text) FROM {table} "
             f"WHERE fingerprint = CAST(:fp AS text)"),
        {"fp": fingerprint},
    )
    return {row[0] for row in rows}


# ── the writer ───────────────────────────────────────────────────────


async def test_a_relation_embeds_as_source_reltype_target(session):
    relation = await seed_relation(session, "redis", "valkey", "REPLACES")
    embedder = FakeEmbedder()

    result = await re_mod.embed_relations(
        session, embedder, relation_ids=[str(relation)],
    )

    assert result is not None
    assert result.written == 1
    assert result.fingerprint == FINGERPRINT
    assert embedder.texts == ["redis REPLACES valkey"]
    assert await stored(session) == {str(relation)}


async def test_an_empty_or_unmatched_request_writes_nothing(session):
    embedder = FakeEmbedder()
    assert await re_mod.embed_relations(session, embedder, relation_ids=[]) is None
    assert await re_mod.embed_relations(
        session, embedder, relation_ids=[str(new_id())],
    ) is None
    assert embedder.calls == 0


async def test_a_short_vector_batch_refuses_to_write_any(session):
    """Zipping a short vector list against the rows would pair each vector with
    the *wrong* relation from the mismatch onward and drop the last silently —
    every row present, every vector describing a different edge."""
    a = await seed_relation(session, "alpha", "beta")
    b = await seed_relation(session, "gamma", "delta")

    with pytest.raises(RuntimeError, match="refusing to write"):
        await re_mod.embed_relations(
            session, MiscountingEmbedder(), relation_ids=[str(a), str(b)],
        )


async def test_re_embedding_refreshes_the_vector_and_keeps_created_at(session):
    """`created_at` records when the relation entered the partition, which is
    what the rotation arm orders on. Bumping it on every write would make the
    rotation re-read whatever it just wrote and never advance past the first
    slice."""
    relation = await seed_relation(session, "alpha", "beta")
    embedder = FakeEmbedder()
    await re_mod.embed_relations(session, embedder, relation_ids=[str(relation)])

    table = child_table(re_mod.PARENT_TABLE, FINGERPRINT)
    first = (await session.execute(
        text(f"SELECT created_at, embedding FROM {table}")
    )).one()

    await re_mod.embed_relations(session, embedder, relation_ids=[str(relation)])

    after = (await session.execute(
        text(f"SELECT created_at, embedding, count(*) OVER () FROM {table}")
    )).one()
    assert after[0] == first[0]
    assert after[2] == 1


# ── the arms, and invariant 2 ────────────────────────────────────────


async def test_missing_finds_only_relations_without_a_vector(session):
    embedded = await seed_relation(session, "alpha", "beta")
    bare = await seed_relation(session, "gamma", "delta")
    await re_mod.embed_relations(
        session, FakeEmbedder(), relation_ids=[str(embedded)],
    )

    missing = await re_mod.relations_missing_vectors(session, FINGERPRINT, 10)

    assert missing == [str(bare)]


async def test_a_vector_under_another_fingerprint_is_still_missing(session):
    """A relation embedded under a previous embedder has no vector under the
    current one — its cosine to a current query vector is undefined — so it
    must still read as missing. The separation that makes this true is the
    child table, asserted outright at the end."""
    relation = await seed_relation(session, "alpha", "beta")
    await re_mod.embed_relations(
        session, FakeEmbedder(OTHER_FINGERPRINT), relation_ids=[str(relation)],
    )
    # The current fingerprint's partition must exist to be joined against.
    other = await seed_relation(session, "gamma", "delta")
    await re_mod.embed_relations(session, FakeEmbedder(), relation_ids=[str(other)])

    missing = await re_mod.relations_missing_vectors(session, FINGERPRINT, 10)

    assert str(relation) in missing
    assert await stored(session, OTHER_FINGERPRINT) == {str(relation)}
    # The mechanism, stated: two fingerprints are two tables.
    assert child_table(re_mod.PARENT_TABLE, FINGERPRINT) != child_table(
        re_mod.PARENT_TABLE, OTHER_FINGERPRINT
    )


async def test_the_question_is_asked_of_the_fingerprint_it_names(session):
    """The same property from the other side: a relation embedded under the
    *current* fingerprint is missing when asked about a different one. An
    implementation that resolved its table from anything but its argument —
    a module constant, the configured embedder — would pass the test above and
    fail this one."""
    relation = await seed_relation(session, "alpha", "beta")
    await re_mod.embed_relations(session, FakeEmbedder(), relation_ids=[str(relation)])
    other = await seed_relation(session, "gamma", "delta")
    await re_mod.embed_relations(
        session, FakeEmbedder(OTHER_FINGERPRINT), relation_ids=[str(other)],
    )

    assert str(relation) in await re_mod.relations_missing_vectors(
        session, OTHER_FINGERPRINT, 10
    )
    assert str(relation) not in await re_mod.relations_missing_vectors(
        session, FINGERPRINT, 10
    )


async def test_a_zero_batch_reads_nothing(session):
    assert await re_mod.relations_missing_vectors(session, FINGERPRINT, 0) == []
    assert await re_mod.relations_to_rotate(session, FINGERPRINT, 0) == []


async def test_rotation_returns_the_embedded_slice(session):
    a = await seed_relation(session, "alpha", "beta")
    b = await seed_relation(session, "gamma", "delta")
    await re_mod.embed_relations(
        session, FakeEmbedder(), relation_ids=[str(a), str(b)],
    )

    rotating = await re_mod.relations_to_rotate(session, FINGERPRINT, 10)

    assert set(rotating) == {str(a), str(b)}


# ── the refresh tick ─────────────────────────────────────────────────


class _ResolvingEmbedder(FakeEmbedder):
    """A fake whose *read* fingerprint resolution is stubbed by the test, since
    `resolve_read_fingerprint` is the vector repository's and needs real
    embedded memories to resolve against."""


@pytest.fixture
def resolved(monkeypatch):
    async def _resolve(session, llm):
        return getattr(llm, "fingerprint", FINGERPRINT)

    monkeypatch.setattr(re_mod, "resolve_read_fingerprint", _resolve)


async def test_the_exact_arm_short_circuits_the_rotation(session, resolved):
    """While relations have never been embedded at all, spending the run's
    budget re-embedding rows that already have vectors would starve the arm
    with real coverage to add."""
    embedded = await seed_relation(session, "alpha", "beta")
    await re_mod.embed_relations(
        session, FakeEmbedder(), relation_ids=[str(embedded)],
    )
    bare = await seed_relation(session, "gamma", "delta")

    embedder = FakeEmbedder()
    outcome = await re_mod.refresh_relation_embeddings(session, embedder)

    assert outcome.missing_written == 1
    assert outcome.rotated == 0
    assert embedder.texts == ["gamma USES delta"]
    assert await stored(session) == {str(embedded), str(bare)}


async def test_the_rotation_runs_once_nothing_is_missing(session, resolved):
    relation = await seed_relation(session, "alpha", "beta")
    await re_mod.embed_relations(
        session, FakeEmbedder(), relation_ids=[str(relation)],
    )

    embedder = FakeEmbedder()
    outcome = await re_mod.refresh_relation_embeddings(session, embedder)

    assert outcome.missing_written == 0
    assert outcome.rotated == 1
    assert embedder.texts == ["alpha USES beta"]


async def test_a_renamed_endpoint_is_corrected_by_the_rotation(session, resolved):
    """The drift the exact arm structurally cannot see: the phrase is derived,
    so a rename leaves an embedded vector describing text the row no longer
    produces, and no `LEFT JOIN` can find it."""
    relation = await seed_relation(session, "alpha", "beta")
    await re_mod.embed_relations(
        session, FakeEmbedder(), relation_ids=[str(relation)],
    )
    await session.execute(
        text("UPDATE entities SET name = 'renamed' WHERE name = 'alpha'")
    )

    assert await re_mod.relations_missing_vectors(session, FINGERPRINT, 10) == []

    embedder = FakeEmbedder()
    await re_mod.refresh_relation_embeddings(session, embedder)

    assert embedder.texts == ["renamed USES beta"]


async def test_zero_batches_disable_both_arms(session, resolved):
    await seed_relation(session, "alpha", "beta")
    embedder = FakeEmbedder()

    outcome = await re_mod.refresh_relation_embeddings(
        session, embedder, missing_batch=0, rotation_batch=0,
    )

    assert outcome.total == 0
    assert embedder.calls == 0


async def test_an_install_with_no_embeds_yet_refreshes_nothing(session, monkeypatch):
    """Cold start must not invent a fingerprint. Returning an empty outcome is
    correct: there is nothing to be covered until a real embed exists."""
    from app.repositories.vector import EmbedderFingerprintUnresolved

    async def _unresolved(session, llm):
        raise EmbedderFingerprintUnresolved("nothing embedded yet")

    monkeypatch.setattr(re_mod, "resolve_read_fingerprint", _unresolved)
    await seed_relation(session, "alpha", "beta")

    embedder = FakeEmbedder()
    outcome = await re_mod.refresh_relation_embeddings(session, embedder)

    assert outcome.total == 0
    assert outcome.fingerprint is None
    assert embedder.calls == 0


# ── structural guards ────────────────────────────────────────────────


def test_the_module_never_calls_llm_fingerprint():
    """The `|0` sentinel trap, and it bites harder here than on a read path:
    under a phantom fingerprint the exact arm finds every relation missing,
    re-embeds the whole graph into a table nothing reads, and reports a rising
    row count every run."""
    tree = ast.parse(MODULE_PATH.read_text())
    calls = [
        node for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
        and node.func.attr == "llm_fingerprint"
    ]
    assert not calls


def test_every_child_table_is_reached_through_the_parent_constant():
    tree = ast.parse(MODULE_PATH.read_text())
    parents = set()
    for node in ast.walk(tree):
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                and node.func.id == "child_table"):
            first = node.args[0]
            parents.add(first.value if isinstance(first, ast.Constant) else first.id)
    assert parents == {"PARENT_TABLE"}
    assert re_mod.PARENT_TABLE == "relation_embeddings"


def test_the_writer_is_never_reached_from_capture_or_retrieval():
    """Doc 07 §4 puts this off the hot path. Phase 5 writing a relation vector
    would add an embed round trip to every capture for a signal retrieval does
    not read until its flag is on."""
    offenders = []
    for name in ("pipeline.py", "hybrid_search.py", "layer_composition.py"):
        source = (BACKEND / "app" / "services" / name).read_text()
        if "relation_embeddings" in source:
            offenders.append(name)
    assert not offenders, (
        "a capture or retrieval module reached the relation-embedding writer: "
        + ", ".join(offenders)
    )


def test_the_template_is_no_longer_inert():
    from tests.test_inert_objects import INERT_TEMPLATES

    assert "relation_embeddings" not in INERT_TEMPLATES, (
        "T2.49 is this template's first writer; leaving it listed inert means "
        "the suite asserts nothing writes to a table this module writes to"
    )


def test_the_job_key_and_schema_are_coherent():
    from app.services.job_registry import is_valid_cron

    keys = {fd.key for fd in re_mod.RELATION_EMBEDDING_CONFIG_SCHEMA}
    assert {"missing_batch", "rotation_batch", "embed_chunk"} <= keys
    assert re_mod.RELATION_EMBEDDING_JOB_KEY == "relation_embedding_refresh"
    assert is_valid_cron("15 * * * *")


def test_the_job_is_registered_with_a_floor_and_a_schema():
    tree = ast.parse((BACKEND / "app" / "main.py").read_text())
    keywords = None
    for node in ast.walk(tree):
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                and node.func.id == "Job"):
            kw = {k.arg: k.value for k in node.keywords}
            key = kw.get("key")
            if isinstance(key, ast.Name) and key.id == "RELATION_EMBEDDING_JOB_KEY":
                keywords = kw
                break

    assert keywords is not None, "the relation-embedding refresh is not wired at boot"
    assert keywords["min_interval_seconds"].value >= 60
    assert "config_schema" in keywords
    assert "max_run_seconds" in keywords
