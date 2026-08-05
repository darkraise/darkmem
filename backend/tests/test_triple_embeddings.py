"""The `triple_embeddings` writer, its grouping, and the two silent invariants.

T2.33 ships the writer doc 08 §5.3 deferred, on the strength of T2.52's measured
41.7% (5/12) miss rate on the `lexically-disjoint` slice against a 20% bar
(`docs/eval/2026-08-05-t2.52-contradiction-missrate.md`). Both of the invariants
it lands under fail silently, so both are asserted here rather than reviewed:

1. It groups facts **for counting only** — never merges rows, never rewrites
   `triple_key`. Proved twice: a byte-comparison of every `knowledge_triples`
   row across a grouping run that really does group, and a source scan that
   fails the build if any verb but SELECT reaches that table from the module.
2. `names_distinct` is **carried into the grouping** — and completely, so a
   distinct pair cannot be merged through an intermediate that matches both.
"""
from __future__ import annotations

import ast
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import text

from app.services import triple_embeddings as te
from app.services.embedder_registry import child_table
from app.services.triple_key import compute_triple_key

BACKEND = Path(__file__).resolve().parent.parent
MODULE_PATH = BACKEND / "app" / "services" / "triple_embeddings.py"

FINGERPRINT = "triple-probe|8"
PROJECT = "t233-grouping"


class FakeEmbedder:
    """Returns the vector the test assigned to each text, under one fingerprint.

    Deliberately not a similarity model: every test states the geometry it needs
    outright, so a grouping decision can never be blamed on an accident of a
    real embedder's output.
    """

    def __init__(self, vectors: dict[str, list[float]], fingerprint: str = FINGERPRINT):
        self.vectors = vectors
        self.fingerprint = fingerprint
        self.calls = 0

    async def embed_batch_chunked(self, texts, chunk_size, concurrency):
        self.calls += 1
        return [self.vectors[t] for t in texts], self.fingerprint


def near(seed: float) -> list[float]:
    """A unit-ish vector a hair off [1, 0, ...] — cosine ~0.999 to its siblings."""
    return [1.0, seed, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]


def far() -> list[float]:
    return [0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0]


@pytest.fixture(autouse=True)
def _forget_probe_fingerprint():
    """The registry cache is process-wide; the test database is rolled back.

    Without this a later test finds the fingerprint "known", skips the DDL, and
    inserts into a child table its own transaction never created.
    """
    from app.services.embedder_registry import embedder_registry

    embedder_registry.forget(FINGERPRINT)
    yield
    embedder_registry.forget(FINGERPRINT)


async def insert_fact(
    session, *, subject: str, obj: str, rel: str = "USES", fact: str | None = None,
    project: str = PROJECT, invalid_at=None,
) -> str:
    fact_id = str(uuid4())
    await session.execute(
        text("""
            INSERT INTO knowledge_triples (
                id, subject_name, object_name, rel_type, reference_time,
                fact, project, triple_key, invalid_at
            ) VALUES (
                CAST(:id AS uuid), CAST(:subject AS text), CAST(:obj AS text),
                CAST(:rel AS text), NOW(), CAST(:fact AS text),
                CAST(:project AS text), CAST(:triple_key AS text),
                CAST(:invalid_at AS timestamptz)
            )
        """),
        {
            "id": fact_id,
            "subject": subject,
            "obj": obj,
            "rel": rel,
            "fact": fact if fact is not None else f"{subject} {rel.lower()} {obj}",
            "project": project,
            "triple_key": compute_triple_key(project, subject, rel, obj),
            "invalid_at": invalid_at,
        },
    )
    return fact_id


async def partition_rows(session) -> list[tuple[str, str]]:
    table = child_table(te.PARENT_TABLE, FINGERPRINT)
    rows = (await session.execute(
        text(f"SELECT CAST(fact_id AS text), embedding::text FROM {table} ORDER BY fact_id")
    )).all()
    return [(str(r[0]), str(r[1])) for r in rows]


async def fact_snapshot(session) -> list[str]:
    """Every column of every fact row, as text — the thing a merge would change."""
    return [
        str(row) for row in (await session.execute(
            text("SELECT knowledge_triples.* FROM knowledge_triples ORDER BY id")
        )).all()
    ]


# ── the writer ───────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_writer_fills_the_active_partition(session):
    a = await insert_fact(session, subject="darkmem", obj="postgres")
    b = await insert_fact(session, subject="darkmem", obj="pgvector")
    llm = FakeEmbedder({
        "darkmem uses postgres": near(0.01),
        "darkmem uses pgvector": far(),
    })

    result = await te.embed_facts(session, llm, fact_ids=[a, b])

    assert result is not None
    assert result.fingerprint == FINGERPRINT
    assert result.written == 2
    assert {fact_id for fact_id, _ in await partition_rows(session)} == {a, b}


@pytest.mark.asyncio
async def test_writer_reports_nothing_embedded_rather_than_a_fingerprint(session):
    """An empty work set is not a failure, and it measures no fingerprint."""
    llm = FakeEmbedder({})

    assert await te.embed_facts(session, llm, fact_ids=[]) is None
    assert await te.embed_facts(session, llm, fact_ids=[str(uuid4())]) is None
    assert llm.calls == 0


@pytest.mark.asyncio
async def test_re_embedding_refreshes_in_place(session):
    a = await insert_fact(session, subject="darkmem", obj="postgres")
    llm = FakeEmbedder({"darkmem uses postgres": near(0.01)})
    await te.embed_facts(session, llm, fact_ids=[a])
    table = child_table(te.PARENT_TABLE, FINGERPRINT)
    first_written = (await session.execute(
        text(f"SELECT created_at FROM {table}")
    )).scalar_one()

    llm.vectors["darkmem uses postgres"] = far()
    await te.embed_facts(session, llm, fact_ids=[a])

    rows = await partition_rows(session)
    assert len(rows) == 1, "a re-embed must refresh the row, never add a second"
    assert rows[0][1].startswith("[0")
    assert (await session.execute(text(f"SELECT created_at FROM {table}"))).scalar_one() \
        == first_written


@pytest.mark.asyncio
async def test_writer_keeps_window_closed_history(session):
    """Bi-temporal contradiction search reads the past; dropping its vector
    would blind the arm to exactly what it is for."""
    from datetime import datetime, timezone

    closed = await insert_fact(
        session, subject="darkmem", obj="sqlite",
        invalid_at=datetime.now(timezone.utc),
    )
    llm = FakeEmbedder({"darkmem uses sqlite": far()})

    result = await te.embed_facts(session, llm, fact_ids=[closed])

    assert result is not None and result.written == 1


@pytest.mark.asyncio
async def test_writer_refuses_a_short_vector_batch(session):
    """Zipping a short batch would store one fact's vector under another's id."""
    a = await insert_fact(session, subject="darkmem", obj="postgres")
    b = await insert_fact(session, subject="darkmem", obj="pgvector")

    class ShortEmbedder(FakeEmbedder):
        async def embed_batch_chunked(self, texts, chunk_size, concurrency):
            return [near(0.01)], self.fingerprint

    with pytest.raises(RuntimeError, match="refusing to write vectors"):
        await te.embed_facts(session, ShortEmbedder({}), fact_ids=[a, b])


# ── grouping: counting only ──────────────────────────────────────────────


@pytest.mark.asyncio
async def test_grouping_groups_surface_variants(session):
    a = await insert_fact(session, subject="darkmem", obj="postgres")
    b = await insert_fact(session, subject="darkmem", obj="postgresql")
    await te.embed_facts(session, FakeEmbedder({
        "darkmem uses postgres": near(0.01),
        "darkmem uses postgresql": near(0.02),
    }), fact_ids=[a, b])

    groups = await te.group_facts(session, fingerprint=FINGERPRINT, project=PROJECT)

    assert [g.fact_ids for g in groups] == [tuple(sorted((a, b)))]


@pytest.mark.asyncio
async def test_grouping_writes_nothing_to_the_fact_rows(session):
    """The invariant: it counts, it does not merge.

    The grouping below really does group — asserted, so this is not vacuously
    true of a run that found nothing — and every fact row survives byte-for-byte,
    `triple_key` included.
    """
    a = await insert_fact(session, subject="darkmem", obj="postgres")
    b = await insert_fact(session, subject="darkmem", obj="postgresql")
    await te.embed_facts(session, FakeEmbedder({
        "darkmem uses postgres": near(0.01),
        "darkmem uses postgresql": near(0.02),
    }), fact_ids=[a, b])
    before = await fact_snapshot(session)

    groups = await te.group_facts(session, fingerprint=FINGERPRINT, project=PROJECT)

    assert any(g.size == 2 for g in groups), "the guard below must not be vacuous"
    assert await fact_snapshot(session) == before
    assert len(before) == 2, "no row was merged away"


@pytest.mark.asyncio
async def test_grouping_partitions_every_fact_in_scope(session):
    a = await insert_fact(session, subject="darkmem", obj="postgres")
    b = await insert_fact(session, subject="darkmem", obj="redis")
    await te.embed_facts(session, FakeEmbedder({
        "darkmem uses postgres": near(0.01),
        "darkmem uses redis": far(),
    }), fact_ids=[a, b])

    groups = await te.group_facts(session, fingerprint=FINGERPRINT, project=PROJECT)

    assert sorted(fid for g in groups for fid in g.fact_ids) == sorted([a, b])
    assert all(g.size == 1 for g in groups)


@pytest.mark.asyncio
async def test_grouping_never_crosses_a_project(session):
    a = await insert_fact(session, subject="darkmem", obj="postgres")
    b = await insert_fact(
        session, subject="darkmem", obj="postgres", project="other-project",
    )
    await te.embed_facts(session, FakeEmbedder({
        "darkmem uses postgres": near(0.01),
    }), fact_ids=[a, b])

    groups = await te.group_facts(session, fingerprint=FINGERPRINT, project=PROJECT)

    assert [g.fact_ids for g in groups] == [(a,)]


# ── grouping: names_distinct is carried ──────────────────────────────────


@pytest.mark.asyncio
async def test_a_version_discriminator_blocks_a_near_identical_pair(session):
    """`postgres 14` and `postgres 15` embed alike and are different claims.

    The similarity is asserted first, so the split below is provably the name
    guard's doing and not the threshold quietly rejecting the pair.
    """
    a = await insert_fact(session, subject="darkmem", obj="postgres 14")
    b = await insert_fact(session, subject="darkmem", obj="postgres 15")
    await te.embed_facts(session, FakeEmbedder({
        "darkmem uses postgres 14": near(0.01),
        "darkmem uses postgres 15": near(0.02),
    }), fact_ids=[a, b])

    neighbours = await te.similar_facts(
        session, fingerprint=FINGERPRINT, project=PROJECT,
        fact_id=a, vector=near(0.01),
    )
    assert neighbours and neighbours[0].similarity > te.DEFAULT_GROUP_THRESHOLD

    groups = await te.group_facts(session, fingerprint=FINGERPRINT, project=PROJECT)

    assert sorted(g.fact_ids for g in groups) == sorted([(a,), (b,)])


@pytest.mark.asyncio
async def test_a_month_discriminator_blocks_a_near_identical_pair(session):
    a = await insert_fact(session, subject="darkmem", obj="march release")
    b = await insert_fact(session, subject="darkmem", obj="april release")
    await te.embed_facts(session, FakeEmbedder({
        "darkmem uses march release": near(0.01),
        "darkmem uses april release": near(0.02),
    }), fact_ids=[a, b])

    groups = await te.group_facts(session, fingerprint=FINGERPRINT, project=PROJECT)

    assert sorted(g.fact_ids for g in groups) == sorted([(a,), (b,)])


@pytest.mark.asyncio
async def test_a_discriminator_on_the_subject_blocks_the_pair(session):
    """Both endpoints are guarded, not just the object."""
    a = await insert_fact(session, subject="darkmem v1", obj="postgres")
    b = await insert_fact(session, subject="darkmem v2", obj="postgres")
    await te.embed_facts(session, FakeEmbedder({
        "darkmem v1 uses postgres": near(0.01),
        "darkmem v2 uses postgres": near(0.02),
    }), fact_ids=[a, b])

    groups = await te.group_facts(session, fingerprint=FINGERPRINT, project=PROJECT)

    assert sorted(g.fact_ids for g in groups) == sorted([(a,), (b,)])


@pytest.mark.asyncio
async def test_a_differing_predicate_blocks_the_pair(session):
    a = await insert_fact(session, subject="darkmem", obj="postgres", rel="USES")
    b = await insert_fact(session, subject="darkmem", obj="postgres", rel="DEPLOYED_ON")
    await te.embed_facts(session, FakeEmbedder({
        "darkmem uses postgres": near(0.01),
        "darkmem deployed_on postgres": near(0.02),
    }), fact_ids=[a, b])

    groups = await te.group_facts(session, fingerprint=FINGERPRINT, project=PROJECT)

    assert sorted(g.fact_ids for g in groups) == sorted([(a,), (b,)])


def test_the_guard_is_not_transitive():
    """`names_distinct` is nearly, but not exactly, an equivalence.

    Its "same string modulo punctuation" early return makes `gpt-4 ~ gpt4`
    mergeable while their discriminating-token keys differ, so a chain through
    `gpt4` reaches `gpt4 turbo`, which `gpt-4` is distinct from. This is the
    shape complete linkage exists to block, pinned here so a future
    simplification to union-find fails loudly rather than silently.
    """
    def row(name: str) -> te.FactRow:
        return te.FactRow(
            fact_id=name, subject_name="darkmem", object_name=name, rel_type="USES",
        )

    assert te.may_group(row("gpt-4"), row("gpt4"))
    assert te.may_group(row("gpt4"), row("gpt4 turbo"))
    assert not te.may_group(row("gpt-4"), row("gpt4 turbo"))


@pytest.mark.asyncio
async def test_a_distinct_pair_cannot_merge_through_an_intermediate(session):
    """Complete linkage, end to end: three mutually-similar facts, one distinct
    pair among them, and that pair never lands in one group."""
    a = await insert_fact(session, subject="darkmem", obj="gpt-4")
    b = await insert_fact(session, subject="darkmem", obj="gpt4")
    c = await insert_fact(session, subject="darkmem", obj="gpt4 turbo")
    await te.embed_facts(session, FakeEmbedder({
        "darkmem uses gpt-4": near(0.010),
        "darkmem uses gpt4": near(0.011),
        "darkmem uses gpt4 turbo": near(0.030),
    }), fact_ids=[a, b, c])

    groups = await te.group_facts(session, fingerprint=FINGERPRINT, project=PROJECT)

    home = {fid: g.fact_ids for g in groups for fid in g.fact_ids}
    assert home[a] != home[c], "a distinct pair was merged through an intermediate"
    assert sorted(fid for g in groups for fid in g.fact_ids) == sorted([a, b, c])


@pytest.mark.asyncio
async def test_a_fact_with_no_vector_stays_ungrouped(session):
    """No cross-fingerprint fallback: an unembedded fact is its own group."""
    a = await insert_fact(session, subject="darkmem", obj="postgres")
    b = await insert_fact(session, subject="darkmem", obj="postgresql")
    await te.embed_facts(session, FakeEmbedder({
        "darkmem uses postgres": near(0.01),
    }), fact_ids=[a])

    groups = await te.group_facts(session, fingerprint=FINGERPRINT, project=PROJECT)

    assert sorted(g.fact_ids for g in groups) == sorted([(a,), (b,)])


# ── the module's own shape ───────────────────────────────────────────────


def _code_strings() -> list[str]:
    """Every string constant in the module except its docstrings.

    Docstrings are excluded deliberately: the prose below discusses the very
    things these scans forbid in code, and a scan that could not tell the two
    apart would either flag its own explanation or be loosened until it flagged
    nothing.
    """
    tree = ast.parse(MODULE_PATH.read_text())
    docstrings = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            body = getattr(node, "body", [])
            if (body and isinstance(body[0], ast.Expr)
                    and isinstance(body[0].value, ast.Constant)
                    and isinstance(body[0].value.value, str)):
                docstrings.add(id(body[0].value))
    return [
        node.value for node in ast.walk(tree)
        if isinstance(node, ast.Constant) and isinstance(node.value, str)
        and id(node) not in docstrings
    ]


def test_the_module_issues_no_write_against_knowledge_triples():
    """The counting-only invariant, enforced structurally.

    Every SQL string in the module is checked: `knowledge_triples` may be
    SELECTed and JOINed, never INSERTed, UPDATEd or DELETEd. A writer that
    merged rows would be data loss with no error, so it fails the build here
    rather than being caught in review.
    """
    offenders = []
    for literal in _code_strings():
        upper = " ".join(literal.upper().split())
        for verb in ("INSERT INTO KNOWLEDGE_TRIPLES", "UPDATE KNOWLEDGE_TRIPLES",
                     "DELETE FROM KNOWLEDGE_TRIPLES"):
            if verb in upper:
                offenders.append(verb)
    assert not offenders, (
        "the triple_embeddings writer must group facts for counting only, "
        f"never merge rows: {offenders}"
    )


def test_the_module_never_names_triple_key_in_code():
    """The other half of the counting-only invariant.

    A fact's identity is its `triple_key`; rewriting one would silently move a
    fact onto another's identity. Prose may discuss it — this checks the code:
    no identifier, no attribute, and no SQL string in the module names it.
    """
    tree = ast.parse(MODULE_PATH.read_text())
    named = [
        node for node in ast.walk(tree)
        if (isinstance(node, ast.Name) and node.id == "triple_key")
        or (isinstance(node, ast.Attribute) and node.attr == "triple_key")
    ]
    assert not named
    assert not [literal for literal in _code_strings() if "triple_key" in literal]


def test_the_module_names_only_its_own_partition():
    """`child_table` is the only sanctioned namer, and this writer owns one
    parent — a call with any other parent would be a second family's writer
    hiding in this one."""
    tree = ast.parse(MODULE_PATH.read_text())
    parents = set()
    for node in ast.walk(tree):
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                and node.func.id == "child_table"):
            first = node.args[0]
            parents.add(first.value if isinstance(first, ast.Constant) else first.id)
    assert parents == {"PARENT_TABLE"}
    assert te.PARENT_TABLE == "triple_embeddings"


def test_the_module_never_calls_llm_fingerprint():
    """The `model|0` sentinel trap (T2.68, T2.83, T2.12's F3).

    The writer takes its fingerprint from an embed call's return value and the
    read side delegates to `resolve_read_fingerprint`; a bare `llm_fingerprint()`
    would name a partition no embed ever wrote to and read empty forever.
    """
    tree = ast.parse(MODULE_PATH.read_text())
    calls = [
        node for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
        and node.func.attr == "llm_fingerprint"
    ]
    assert not calls
