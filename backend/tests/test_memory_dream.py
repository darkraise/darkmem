"""T2.12 — `memory_dream`: subsume, associate, refine; never merges, never deletes.

Doc 08 §5.4. Three Done-whens, two of them negatives, and a negative is where a
decorative guard hides: asserting a row still exists after a cycle that was
never going to remove it proves nothing. Every negative here is proven twice —
a differential arm (the same fixture builder, one flipped bit, asserting the
opposite outcome) and, where the claim is about code shape rather than
behaviour, a source scan carrying its own in-suite negative control.
"""
from __future__ import annotations

import ast
import json
import pathlib
import re
from dataclasses import fields
from datetime import datetime, timedelta, timezone
from uuid import UUID

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app.repositories import memory_relations as edges
from app.repositories.relational import PostgresMemoryRepository
from app.repositories.vector import MemoryFilter, PostgresVectorRepository
from app.services import memory_dream as dream
from app.services.embedder_registry import child_table
from app.utils.ids import new_id

PROJECT = "t212-dream"
OTHER_PROJECT = "t212-dream-other"

NOW = datetime(2026, 8, 2, 3, 0, tzinfo=timezone.utc)

FP = "t212-embedder|4"
OTHER_FP = "t212-rotated|4"


_INSERT_MEMORY = text(
    """
    INSERT INTO memories (
        id, content, source, project, status, is_archived, created_at,
        summary, metadata
    )
    VALUES (
        CAST(:id AS uuid), :content, 'api', CAST(:project AS text),
        CAST(:status AS memory_status), false,
        :created_at, :summary,
        CAST(:metadata AS jsonb)
    )
    """
)


async def seed_memory(
    session,
    *,
    project: str = PROJECT,
    content: str = "a memory",
    status: str = "active",
    created_at: datetime | None = None,
    summary: str | None = None,
    metadata: dict | None = None,
    memory_id: UUID | None = None,
) -> UUID:
    identifier = memory_id or new_id()
    await session.execute(
        _INSERT_MEMORY,
        {
            "id": str(identifier),
            "content": content,
            "project": project,
            "status": status,
            "created_at": created_at or NOW,
            "summary": summary,
            "metadata": json.dumps(metadata or {}),
        },
    )
    return identifier


async def read_edge(session, source, target, rel_type="RELATES_TO") -> dict | None:
    return await edges.get_edge(
        session,
        source_memory_id=source,
        target_memory_id=target,
        rel_type=rel_type,
    )


async def seed_partition(session, fingerprint: str = FP) -> str:
    """A four-dimension embedding partition, built inline so the suite stays
    offline and inside the rollback-isolated session."""
    await session.execute(
        text(
            "INSERT INTO embedders (fingerprint, model_id, dims, source) "
            "VALUES (:fp, 'stub', 4, 'llm') ON CONFLICT (fingerprint) DO NOTHING"
        ),
        {"fp": fingerprint},
    )
    child = child_table("memory_embeddings", fingerprint)
    await session.execute(
        text(
            f"CREATE TABLE IF NOT EXISTS {child} ("
            " memory_id UUID NOT NULL REFERENCES memories(id) ON DELETE CASCADE,"
            " fingerprint TEXT NOT NULL REFERENCES embedders(fingerprint),"
            " embedding vector(4) NOT NULL,"
            " payload JSONB NOT NULL DEFAULT '{}'::jsonb,"
            " PRIMARY KEY (memory_id, fingerprint))"
        )
    )
    return child


async def put_vector(session, memory_id, vector, fingerprint: str = FP) -> None:
    child = child_table("memory_embeddings", fingerprint)
    await session.execute(
        text(
            f"INSERT INTO {child} (memory_id, fingerprint, embedding) "
            "VALUES (CAST(:m AS uuid), :fp, CAST(:v AS vector)) "
            "ON CONFLICT (memory_id, fingerprint) DO UPDATE "
            "SET embedding = EXCLUDED.embedding"
        ),
        {"m": str(memory_id), "fp": fingerprint, "v": str(list(vector))},
    )


class StubLLM:
    """Orchestrator stand-in: a measured fingerprint from `embed`, scripted
    verdicts from `chat_completion`, and a record of every call."""

    def __init__(
        self,
        *,
        fingerprint: str = FP,
        configured_fingerprint: str | None = None,
        embed_error: Exception | None = None,
        pair_verdict=None,
        refine=None,
    ):
        self.fingerprint = fingerprint
        self.configured_fingerprint = configured_fingerprint or fingerprint
        self.embed_error = embed_error
        self.pair_verdict = pair_verdict
        self.refine = refine
        self.embed_calls: list[str] = []
        self.calls: list[dict] = []

    def llm_fingerprint(self) -> str:
        """What the orchestrator's own `llm_fingerprint()` answers: the
        *configured* dimensions, which is the `|0` sentinel whenever they are
        unset. Present so the drill that swaps the canary for this call is
        runnable and its outcome differs."""
        return self.configured_fingerprint

    async def embed(self, content: str):
        self.embed_calls.append(content)
        if self.embed_error is not None:
            raise self.embed_error
        return [1.0, 0.0, 0.0, 0.0], self.fingerprint

    async def chat_completion(self, purpose, messages, response_format=None, seed=None):
        self.calls.append({
            "purpose": purpose,
            "messages": messages,
            "response_format": response_format,
            "seed": seed,
        })
        system = messages[0]["content"]
        body = messages[-1]["content"]
        if system == dream.PAIR_SYSTEM_PROMPT:
            reply = self.pair_verdict
        else:
            reply = self.refine
        if callable(reply):
            reply = reply(body)
        if reply is None:
            reply = json.dumps({"verdict": "distinct", "reason": "stub default"})
        return reply if isinstance(reply, str) else json.dumps(reply)


# ── Step 1: the memory_relations writer ──────────────────────────────────


class TestEdgeWriter:
    async def test_upsert_creates_then_updates_and_reports_created(self, session):
        older = await seed_memory(session, content="older")
        newer = await seed_memory(session, content="newer")
        await session.flush()

        first = await edges.upsert_edge(
            session,
            source_memory_id=newer,
            target_memory_id=older,
            rel_type="ELABORATES",
            project=PROJECT,
            pass_key="near_duplicate",
            block={"score": 0.9},
        )
        assert first.created is True
        assert first.before is None

        second = await edges.upsert_edge(
            session,
            source_memory_id=newer,
            target_memory_id=older,
            rel_type="ELABORATES",
            project=PROJECT,
            pass_key="near_duplicate",
            block={"score": 0.95},
        )
        assert second.created is False
        assert second.before is not None
        assert edges.pass_block_of(second.before, "near_duplicate") == {"score": 0.9}

        row = await read_edge(session, newer, older, "ELABORATES")
        assert edges.pass_block_of(row, "near_duplicate") == {"score": 0.95}

    async def test_a_supersedes_write_is_refused(self, session):
        older = await seed_memory(session)
        newer = await seed_memory(session)
        await session.flush()

        with pytest.raises(edges.ProjectedRelationTypeError):
            await edges.upsert_edge(
                session,
                source_memory_id=newer,
                target_memory_id=older,
                rel_type="SUPERSEDES",
                project=PROJECT,
                pass_key="near_duplicate",
                block={},
            )

    async def test_an_unknown_type_falls_back_within_the_closed_set(self, session):
        older = await seed_memory(session)
        newer = await seed_memory(session)
        await session.flush()

        await edges.upsert_edge(
            session,
            source_memory_id=newer,
            target_memory_id=older,
            rel_type="INVENTED_BY_A_MODEL",
            project=PROJECT,
            pass_key="near_duplicate",
            block={},
        )
        stored = await session.execute(
            text(
                "SELECT rel_type FROM memory_relations "
                "WHERE source_memory_id = CAST(:s AS uuid)"
            ),
            {"s": str(newer)},
        )
        assert stored.scalar_one() == "RELATES_TO"

    async def test_a_cross_project_pair_is_rejected_by_the_composite_fk(self, session):
        """The guard is the schema's, not this module's — a cross-project edge is
        unrepresentable rather than merely forbidden."""
        here = await seed_memory(session, project=PROJECT)
        elsewhere = await seed_memory(session, project=OTHER_PROJECT)
        await session.flush()

        with pytest.raises(IntegrityError):
            async with session.begin_nested():
                await edges.upsert_edge(
                    session,
                    source_memory_id=here,
                    target_memory_id=elsewhere,
                    rel_type="RELATES_TO",
                    project=PROJECT,
                    pass_key="near_duplicate",
                    block={},
                )

    async def test_deleting_an_endpoint_removes_the_edge(self, session):
        older = await seed_memory(session)
        newer = await seed_memory(session)
        await session.flush()
        await edges.upsert_edge(
            session,
            source_memory_id=newer,
            target_memory_id=older,
            rel_type="RELATES_TO",
            project=PROJECT,
            pass_key="near_duplicate",
            block={},
        )
        assert await read_edge(session, newer, older) is not None

        await session.execute(
            text("DELETE FROM memories WHERE id = CAST(:id AS uuid)"),
            {"id": str(older)},
        )
        assert await read_edge(session, newer, older) is None

    @pytest.mark.parametrize(
        "existing",
        [None, {}, {"note": "x"}, {"dream": {"proximity": {"w": 1}}}],
        ids=["null", "empty", "foreign-key", "sibling-pass"],
    )
    async def test_the_block_lands_whatever_shape_the_row_already_had(
        self, session, existing
    ):
        """The nested `jsonb_set`'s reason for existing.

        A single `jsonb_set` on the two-element path returns its target
        unchanged — no error — for the first three shapes, so the block would
        never be written and `created=false` would still be reported.
        """
        older = await seed_memory(session)
        newer = await seed_memory(session)
        await session.flush()
        await session.execute(
            text(
                "INSERT INTO memory_relations "
                "(id, source_memory_id, target_memory_id, rel_type, project, "
                " properties) "
                "VALUES (CAST(:id AS uuid), CAST(:s AS uuid), CAST(:t AS uuid), "
                "'RELATES_TO', CAST(:p AS text), CAST(:props AS jsonb))"
            ),
            {
                "id": str(new_id()),
                "s": str(newer),
                "t": str(older),
                "p": PROJECT,
                "props": None if existing is None else json.dumps(existing),
            },
        )

        write = await edges.upsert_edge(
            session,
            source_memory_id=newer,
            target_memory_id=older,
            rel_type="RELATES_TO",
            project=PROJECT,
            pass_key="near_duplicate",
            block={"score": 0.91},
        )
        assert write.created is False

        row = await read_edge(session, newer, older)
        assert edges.pass_block_of(row, "near_duplicate") == {"score": 0.91}
        if existing:
            for key, value in existing.items():
                if key == "dream":
                    assert row["properties"]["dream"]["proximity"] == value["proximity"]
                else:
                    assert row["properties"][key] == value


# ── Step 2: pair generation, project scope, and the direction rule ───────


async def _pair_fixture(session):
    """OLD and NEW near-identical in project p; OTHER identical in project q."""
    await seed_partition(session)
    older = await seed_memory(
        session, content="postgres runs on 5433", created_at=NOW
    )
    newer = await seed_memory(
        session,
        content="postgres runs on port 5433",
        created_at=NOW + timedelta(hours=1),
    )
    other = await seed_memory(
        session,
        project=OTHER_PROJECT,
        content="postgres runs on 5433",
        created_at=NOW,
    )
    await session.flush()
    for identifier in (older, newer, other):
        await put_vector(session, identifier, [1.0, 0.0, 0.0, 0.0])
    return older, newer, other


async def _pairs(session, seeds, *, fanout=25, threshold_pct=50, candidates=5):
    outcome = dream.DreamOutcome()
    pairs = await dream.generate_pairs(
        session,
        seeds=seeds,
        fingerprint=FP,
        pair_candidates=candidates,
        near_duplicate_threshold_pct=threshold_pct,
        judge_fanout=fanout,
        outcome=outcome,
    )
    return pairs, outcome


class TestPairGeneration:
    async def test_pairs_never_cross_projects(self, session):
        older, newer, other = await _pair_fixture(session)
        seeds, _ = await dream.next_seeds(
            session, state=dream._State(), batch_size=50
        )
        in_project = [s for s in seeds if s.project == PROJECT]

        pairs, _ = await _pairs(session, in_project)

        proposed = {identifier for pair in pairs for identifier in pair.key}
        assert str(other) not in proposed
        assert pairs and pairs[0].key == {str(older), str(newer)}

    async def test_an_unfiltered_probe_would_have_proposed_the_foreign_row(
        self, session
    ):
        """The differential twin: `MemoryFilter` is enforcement, not decoration.

        The unfiltered probe lives here rather than in `app/` on purpose — the
        point is that dropping the filter changes the outcome, not that the
        service has a second code path."""
        older, _, other = await _pair_fixture(session)
        vectors = await dream.seed_vectors(
            session, fingerprint=FP, memory_ids=[str(older)]
        )
        repository = PostgresVectorRepository(session)

        unfiltered = await repository.search(
            vectors[str(older)], FP, limit=10, filters=None
        )
        filtered = await repository.search(
            vectors[str(older)],
            FP,
            limit=10,
            filters=MemoryFilter(project=PROJECT, statuses=("active",)),
        )

        assert str(other) in {str(r["memory_id"]) for r in unfiltered}
        assert str(other) not in {str(r["memory_id"]) for r in filtered}

    async def test_pairs_are_deduped_by_the_unordered_id_set(self, session):
        older, newer, _ = await _pair_fixture(session)
        seeds = list(
            (await dream.read_memories(session, [str(older), str(newer)])).values()
        )

        pairs, _ = await _pairs(session, seeds)

        assert len(pairs) == 1
        assert pairs[0].key == {str(older), str(newer)}

    @pytest.mark.parametrize("swap", [False, True])
    async def test_order_pair_agrees_with_the_primitive_on_a_tie(
        self, session, swap
    ):
        """Same-`created_at` rows are ordered by the id tie-break, and the
        answer must not depend on which way the pair arrives."""
        from app.services.supersede import successor_is_newer

        low = UUID("00000000-0000-0000-0000-00000000000a")
        high = UUID("ffffffff-0000-0000-0000-00000000000f")
        first = await seed_memory(session, memory_id=low, created_at=NOW)
        second = await seed_memory(session, memory_id=high, created_at=NOW)
        await session.flush()
        rows = await dream.read_memories(session, [str(first), str(second)])
        left, right = rows[str(first)], rows[str(second)]
        if swap:
            left, right = right, left

        older, newer = dream.order_pair(left, right)

        assert older.memory_id == str(low)
        assert newer.memory_id == str(high)
        assert successor_is_newer(
            candidate_created_at=older.created_at,
            candidate_id=older.memory_id,
            successor_created_at=newer.created_at,
            successor_id=newer.memory_id,
        )

    async def test_a_seed_with_no_vector_here_is_never_probed_elsewhere(
        self, session
    ):
        """A cross-fingerprint cosine has no defined meaning, so a seed missing
        from the active partition is counted and dropped — never resolved from
        the partition it does have a row in."""
        await seed_partition(session, FP)
        await seed_partition(session, OTHER_FP)
        stranded = await seed_memory(session, content="only in the old partition")
        neighbour = await seed_memory(session, content="only in the old partition too")
        await session.flush()
        await put_vector(session, stranded, [1.0, 0.0, 0.0, 0.0], OTHER_FP)
        await put_vector(session, neighbour, [1.0, 0.0, 0.0, 0.0], OTHER_FP)
        seeds = list(
            (
                await dream.read_memories(session, [str(stranded), str(neighbour)])
            ).values()
        )

        pairs, outcome = await _pairs(session, seeds)

        assert pairs == []
        assert outcome.pairs_skipped_no_vector == 2


class TestFingerprintCanary:
    async def test_a_measured_fingerprint_is_returned(self):
        assert await dream.resolve_fingerprint(StubLLM()) == FP

    async def test_the_zero_dimension_sentinel_is_refused(self):
        """`llm_fingerprint()` emits `model|0` under an unset `dimensions` — a
        legal config. Accepting it would point every probe at an empty partition
        and report a green, permanently inert run."""
        assert await dream.resolve_fingerprint(StubLLM(fingerprint="stub|0")) is None

    async def test_a_failed_canary_is_refused(self):
        stub = StubLLM(embed_error=RuntimeError("embedder down"))
        assert await dream.resolve_fingerprint(stub) is None


class TestSeedCursor:
    async def test_the_slice_advances_past_the_cursor(self, session):
        first = await seed_memory(session, content="first", created_at=NOW)
        second = await seed_memory(
            session, content="second", created_at=NOW + timedelta(hours=1)
        )
        await session.flush()

        rows, wrapped = await dream.next_seeds(
            session, state=dream._State(), batch_size=1
        )
        assert wrapped is False
        assert rows[0].memory_id == str(first)

        state = dream._State(
            seed_created_at=rows[0].created_at, seed_id=rows[0].memory_id
        )
        rows, _ = await dream.next_seeds(session, state=state, batch_size=1)
        assert rows[0].memory_id == str(second)

    async def test_the_cursor_wraps_rather_than_stalling(self, session):
        only = await seed_memory(session, content="only", created_at=NOW)
        await session.flush()
        rows, _ = await dream.next_seeds(session, state=dream._State(), batch_size=10)
        state = dream._State(
            seed_created_at=rows[-1].created_at, seed_id=rows[-1].memory_id
        )

        rows, wrapped = await dream.next_seeds(session, state=state, batch_size=10)

        assert wrapped is True
        assert str(only) in {row.memory_id for row in rows}

    async def test_superseded_and_archived_rows_are_not_eligible(self, session):
        live = await seed_memory(session, content="live")
        gone = await seed_memory(session, content="gone", status="deprecated")
        await session.flush()

        rows, _ = await dream.next_seeds(session, state=dream._State(), batch_size=50)

        identifiers = {row.memory_id for row in rows}
        assert str(live) in identifiers
        assert str(gone) not in identifiers


# ── Step 3: the judge — purpose, seed, parsers ───────────────────────────


def _row(content="c", summary=None, tags=()):
    return dream.MemoryRow(
        memory_id=str(new_id()),
        project=PROJECT,
        created_at=NOW,
        content=content,
        summary=summary,
        metadata={},
        tags=tuple(tags),
    )


class TestJudge:
    async def test_the_pair_call_dispatches_on_reasoning_and_nothing_else(self):
        stub = StubLLM(pair_verdict={"verdict": "distinct", "reason": "r"})
        older, newer = _row("older"), _row("newer")

        await dream.judge_pair(stub, older, newer)

        assert [call["purpose"] for call in stub.calls] == ["reasoning"]

    async def test_the_refine_call_dispatches_on_reasoning_and_nothing_else(self):
        stub = StubLLM(refine={"summary": "s", "tags": None})

        await dream.judge_refine(stub, _row("a memory"))

        assert [call["purpose"] for call in stub.calls] == ["reasoning"]

    async def test_the_seed_is_deterministic_and_input_sensitive(self):
        older, newer = _row("older"), _row("newer")
        assert dream.pair_seed(older, newer) == dream.pair_seed(older, newer)
        assert dream.pair_seed(older, newer) != dream.pair_seed(newer, older)
        assert dream.refine_seed(_row("x")) == dream.refine_seed(_row("x"))
        assert dream.refine_seed(_row("x")) != dream.refine_seed(_row("y"))

    async def test_the_seed_reaches_the_call(self):
        stub = StubLLM(pair_verdict={"verdict": "distinct", "reason": "r"})
        older, newer = _row("older"), _row("newer")

        await dream.judge_pair(stub, older, newer)

        assert stub.calls[0]["seed"] == dream.pair_seed(older, newer)

    @pytest.mark.parametrize(
        "raw",
        [
            "not json at all",
            "",
            json.dumps({"reason": "no verdict key"}),
            json.dumps({"verdict": "merge", "reason": "outside the closed set"}),
            '{"verdict": "subsum',
        ],
        ids=["prose", "empty", "missing-key", "unknown-verdict", "truncated"],
    )
    def test_every_unusable_pair_answer_raises_the_same_handled_error(self, raw):
        """One error for every unusable shape, and never a default verdict — a
        default would let a broken model drive real supersessions."""
        with pytest.raises(dream.JudgeError):
            dream.parse_pair_verdict(raw)

    @pytest.mark.parametrize("verdict", sorted(dream.PAIR_VERDICTS))
    def test_each_lawful_verdict_parses(self, verdict):
        parsed = dream.parse_pair_verdict(
            json.dumps({"verdict": verdict, "reason": "because"})
        )
        assert parsed.verdict == verdict
        assert parsed.reason == "because"

    def test_parse_refine_discards_a_content_key(self):
        """T-N2c. A dict-returning parser would carry it forward silently."""
        parsed = dream.parse_refine(
            json.dumps({"summary": "s", "content": "REWRITTEN", "tags": ["a"]})
        )
        assert parsed.summary == "s"
        assert parsed.tags == ("a",)
        assert not hasattr(parsed, "content")
        assert "content" not in {f.name for f in fields(parsed)}

    @pytest.mark.parametrize(
        "raw",
        [
            "not json",
            "",
            json.dumps({"summary": 7}),
            json.dumps({"tags": "not-a-list"}),
            json.dumps({"summary": None, "tags": None}),
        ],
        ids=["prose", "empty", "bad-summary", "bad-tags", "nothing-proposed"],
    )
    def test_every_unusable_refine_answer_raises_the_same_handled_error(self, raw):
        with pytest.raises(dream.JudgeError):
            dream.parse_refine(raw)

    def test_a_fenced_body_still_parses(self):
        parsed = dream.parse_pair_verdict(
            'Sure:\n```json\n{"verdict": "duplicate", "reason": "r"}\n```'
        )
        assert parsed.verdict == "duplicate"


# ── the cycle fixtures ───────────────────────────────────────────────────

# T-REF2. Every cycle run through `run_cycle` registers its outcome here, and
# the module's teardown asserts `refused_not_newer` is zero across all of them.
# The assertion is tree-wide by default — a new test is covered by the act of
# existing — and exempting one is the deliberate, greppable act of marking it
# `expect_refusals`. Narrowing this to a hand-picked list instead would leave a
# guard that reads far stronger than it is, which is the failure mode this whole
# file exists to prevent.
_REFUSAL_LEDGER: list[tuple[str, dream.DreamOutcome]] = []


@pytest.fixture(scope="session", autouse=True)
def successor_not_newer_never_arises():
    yield
    offenders = [
        f"{nodeid}: refused_not_newer={outcome.refused_not_newer}"
        for nodeid, outcome in _REFUSAL_LEDGER
        if outcome.refused_not_newer
    ]
    assert not offenders, (
        "a cycle hit `successor_not_newer`, which is unreachable on the happy "
        "path by construction — order_pair and the primitive call the same "
        "predicate. That refusal means the two disagreed:\n"
        + "\n".join(offenders)
    )


@pytest.fixture
def run_cycle(request):
    expects = request.node.get_closest_marker("expect_refusals") is not None

    async def _run(factory, llm, **knobs):
        outcome = await dream.run_memory_dream(factory, lambda: llm, **knobs)
        if not expects:
            _REFUSAL_LEDGER.append((request.node.nodeid, outcome))
        return outcome

    return _run


@pytest.fixture
async def committing(setup_database):
    """A real session factory with real commits.

    The rollback-isolated `session` fixture cannot express what a cycle does —
    it commits per write batch through its own sessions — so these tests own
    their cleanup.
    """
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    from app.config import settings

    engine = create_async_engine(settings.test_database_url)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    try:
        yield factory
    finally:
        async with factory() as cleanup:
            # `events` is append-only — a DELETE raises. Every cycle test gets
            # its own project instead, so one test's journal rows can never be
            # read by another.
            # Tags outlive their memories — `memory_tags` cascades but `tags`
            # does not — and a stray committed tag is an orphan every other
            # suite's tag-sweep assertions would then count.
            for statement in (
                "DELETE FROM memory_relations WHERE project LIKE 't212-%'",
                "DELETE FROM memories WHERE project LIKE 't212-%'",
                "DELETE FROM tags WHERE name LIKE 't212-%'",
                "DELETE FROM config WHERE key = 'memory_dream_state'",
            ):
                await cleanup.execute(text(statement))
            await cleanup.commit()
        await engine.dispose()


@pytest.fixture
def project() -> str:
    """A project of this test's own. `events` cannot be cleaned up between
    tests, so isolation comes from the scope key rather than from a DELETE."""
    return f"t212-{new_id().hex[:12]}"


async def build_pair(factory, project, *, older_content=None, newer_content=None):
    """OLD at T0 and NEW at T0+1h, near-identical, both with a vector; FAR
    unrelated in the same project; OTHER identical in another project."""
    async with factory() as session:
        await seed_partition(session)
        older = await seed_memory(
            session,
            project=project,
            content=older_content or "the api listens on port 8000",
            created_at=NOW,
        )
        newer = await seed_memory(
            session,
            project=project,
            content=newer_content or "the api listens on port 8000 with keepalive",
            created_at=NOW + timedelta(hours=1),
        )
        far = await seed_memory(
            session,
            project=project,
            content="unrelated: the tag sweeper runs hourly",
            created_at=NOW + timedelta(hours=2),
        )
        other = await seed_memory(
            session,
            project=f"{project}-other",
            content=older_content or "the api listens on port 8000",
            created_at=NOW,
        )
        for identifier in (older, newer, other):
            await put_vector(session, identifier, [1.0, 0.0, 0.0, 0.0])
        await put_vector(session, far, [0.0, 0.0, 0.0, 1.0])
        await session.commit()
    return older, newer, far, other


async def memory_row(factory, memory_id) -> dict:
    async with factory() as session:
        result = await session.execute(
            text(
                "SELECT status::text AS status, content, summary, "
                "       CAST(superseded_by AS text) AS superseded_by, "
                "       metadata, updated_at "
                "FROM memories WHERE id = CAST(:id AS uuid)"
            ),
            {"id": str(memory_id)},
        )
        return dict(result.mappings().one())


async def consolidated_events(factory, project, memory_id=None) -> list[dict]:
    async with factory() as session:
        clause = "AND object_id = CAST(:id AS uuid)" if memory_id else ""
        params = {"project": project}
        if memory_id:
            params["id"] = str(memory_id)
        result = await session.execute(
            text(
                "SELECT CAST(object_id AS text) AS object_id, payload, created_at "
                "FROM events WHERE event_type = 'consolidated' "
                f"AND project = CAST(:project AS text) {clause} "
                "ORDER BY created_at, id"
            ),
            params,
        )
        return [dict(row) for row in result.mappings()]


def verdict(name: str, reason: str = "because"):
    return json.dumps({"verdict": name, "reason": reason})


# ── Step 4: the subsume arm ──────────────────────────────────────────────


class TestSubsumeArm:
    async def test_subsume_fires(self, committing, project, run_cycle):
        """T-A1."""
        older, newer, _, _ = await build_pair(committing, project)
        stub = StubLLM(pair_verdict=verdict("subsumes"), refine=None)

        outcome = await run_cycle(committing, stub, refine_batch=0)

        assert outcome.subsumed == 1
        row = await memory_row(committing, older)
        assert row["status"] == "superseded"
        assert row["superseded_by"] == str(newer)

        events = await consolidated_events(committing, project, older)
        assert len(events) == 1
        payload = events[0]["payload"]
        assert payload["action"] == "subsume"
        assert payload["before"] == {"status": "active", "superseded_by": None}
        assert payload["after"]["status"] == "superseded"
        assert payload["after"]["superseded_by"] == str(newer)
        assert payload["detector"] == "dedup"
        assert payload["pair"] == {"older": str(older), "newer": str(newer)}

    async def test_subsume_declines(self, committing, project, run_cycle):
        """T-A1b — the differential twin. One verdict string separates it."""
        older, _, _, _ = await build_pair(committing, project)
        stub = StubLLM(pair_verdict=verdict("distinct"), refine=None)

        outcome = await run_cycle(committing, stub, refine_batch=0)

        assert outcome.subsumed == 0
        row = await memory_row(committing, older)
        assert row["status"] == "active"
        assert row["superseded_by"] is None
        assert await consolidated_events(committing, project) == []

    async def test_the_judge_never_sees_an_unordered_pair(
        self, committing, project, run_cycle
    ):
        """D4: the direction is fixed before the model is asked anything."""
        older, newer, _, _ = await build_pair(committing, project)
        stub = StubLLM(pair_verdict=verdict("distinct"), refine=None)

        await run_cycle(committing, stub, refine_batch=0)

        body = stub.calls[0]["messages"][-1]["content"]
        assert body.index("OLDER:") < body.index("NEWER:")
        older_row = await memory_row(committing, older)
        newer_row = await memory_row(committing, newer)
        assert body.index(older_row["content"]) < body.index(newer_row["content"])

    async def test_already_superseded_is_ordinary(
        self, committing, project, run_cycle
    ):
        """T-REF1. Two pairs share the older memory, so the second action finds
        it already retired by the first — the expected steady state, not an
        anomaly, and the path D4 names."""
        async with committing() as session:
            await seed_partition(session)
            older = await seed_memory(
                session, project=project, content="one truth", created_at=NOW
            )
            first = await seed_memory(
                session,
                project=project,
                content="one truth, corrected",
                created_at=NOW + timedelta(hours=1),
            )
            second = await seed_memory(
                session,
                project=project,
                content="one truth, corrected again",
                created_at=NOW + timedelta(hours=2),
            )
            await put_vector(session, older, [1.0, 0.0, 0.0, 0.0])
            await put_vector(session, first, [0.99, 0.1, 0.0, 0.0])
            await put_vector(session, second, [0.99, -0.1, 0.0, 0.0])
            await session.commit()
        stub = StubLLM(pair_verdict=verdict("subsumes"), refine=None)

        outcome = await run_cycle(
            committing, stub, refine_batch=0, near_duplicate_threshold_pct=99
        )

        assert outcome.subsumed == 1
        assert outcome.refused_already_superseded == 1
        assert (await memory_row(committing, older))["status"] == "superseded"
        assert len(await consolidated_events(committing, project)) == 1

    @pytest.mark.expect_refusals
    async def test_a_not_newer_refusal_is_counted_and_never_retried_reversed(
        self, committing, project, monkeypatch, run_cycle
    ):
        """T-REF3. The one test exempted from the tree-wide collector.

        The refusal must never be worked around by swapping the endpoints: that
        retry supersedes a newer memory with an older one, which is invisible to
        the promotion blocker."""
        older, newer, _, _ = await build_pair(committing, project)
        monkeypatch.setattr(
            dream,
            "order_pair",
            lambda left, right: tuple(reversed(_true_order(left, right))),
        )
        stub = StubLLM(pair_verdict=verdict("subsumes"), refine=None)

        outcome = await run_cycle(committing, stub, refine_batch=0)

        assert outcome.refused_not_newer == 1
        assert outcome.subsumed == 0
        assert (await memory_row(committing, older))["status"] == "active"
        assert (await memory_row(committing, newer))["status"] == "active"
        assert await consolidated_events(committing, project) == []

    async def test_a_row_that_moved_between_phases_is_skipped(
        self, committing, project, monkeypatch, run_cycle
    ):
        """T-STALE. Content is the half only this check can catch: the verdict
        was reached on text the store has since replaced, so applying it would
        act on a snapshot that no longer exists."""
        older, newer, _, _ = await build_pair(committing, project)
        original = dream.apply_subsume

        async def mutate_then_apply(session, action, **kwargs):
            async with committing() as other:
                await other.execute(
                    text(
                        "UPDATE memories SET content = 're-extracted content' "
                        "WHERE id = CAST(:o AS uuid)"
                    ),
                    {"o": str(older)},
                )
                await other.commit()
            monkeypatch.setattr(dream, "apply_subsume", original)
            return await original(session, action, **kwargs)

        monkeypatch.setattr(dream, "apply_subsume", mutate_then_apply)
        stub = StubLLM(pair_verdict=verdict("subsumes"), refine=None)

        outcome = await run_cycle(committing, stub, refine_batch=0)

        assert outcome.stale_skipped == 1
        assert outcome.subsumed == 0
        assert (await memory_row(committing, older))["status"] == "active"
        assert await consolidated_events(committing, project) == []

    async def test_no_llm_provider_writes_and_deletes_nothing(self, committing, project):
        older, _, _, _ = await build_pair(committing, project)

        outcome = await dream.run_memory_dream(committing, lambda: None)

        assert outcome.skipped_reason == "llm_unavailable"
        assert (await memory_row(committing, older))["status"] == "active"
        assert await consolidated_events(committing, project) == []

    async def test_the_canary_beats_a_configured_sentinel(
        self, committing, project, run_cycle
    ):
        """F3's drill target. With the embedding purpose's `dimensions` unset —
        a legal config — `llm_fingerprint()` answers `model|0` while a real
        embed measures `model|4`, and boot has already registered the sentinel
        partition, so it exists and is empty. Resolving from the configured
        value therefore points every probe at that empty partition: no
        exception, no log line, a green cycle, and a feature that is inert
        forever."""
        older, _, _, _ = await build_pair(committing, project)
        async with committing() as session:
            await seed_partition(session, "t212-embedder|0")
            await session.commit()
        stub = StubLLM(
            pair_verdict=verdict("subsumes"),
            refine=None,
            configured_fingerprint="t212-embedder|0",
        )

        outcome = await run_cycle(committing, stub, refine_batch=0)

        assert outcome.subsumed == 1
        assert outcome.pairs_skipped_no_vector == 0
        assert outcome.skipped_reason is None
        assert (await memory_row(committing, older))["status"] == "superseded"

    async def test_an_unresolvable_fingerprint_stops_the_whole_run(
        self, committing, project, run_cycle
    ):
        """F3's drill in test form: `llm_fingerprint()` would have returned the
        `model|0` sentinel here and every seed would have landed in
        `pairs_skipped_no_vector` under a green run."""
        older, _, _, _ = await build_pair(committing, project)
        stub = StubLLM(fingerprint="stub|0", pair_verdict=verdict("subsumes"))

        outcome = await run_cycle(committing, stub, refine_batch=0)

        assert outcome.skipped_reason == "fingerprint_unresolved"
        assert outcome.seeds_visited == 0
        assert outcome.pairs_skipped_no_vector == 0
        assert (await memory_row(committing, older))["status"] == "active"
        assert await consolidated_events(committing, project) == []


def _true_order(left, right):
    from app.services.supersede import successor_is_newer

    if successor_is_newer(
        candidate_created_at=left.created_at,
        candidate_id=left.memory_id,
        successor_created_at=right.created_at,
        successor_id=right.memory_id,
    ):
        return left, right
    return right, left


# ── Step 5: the near-duplicate arm and the hygiene marker ────────────────


async def edge_row(factory, source, target, rel_type="RELATES_TO") -> dict | None:
    async with factory() as session:
        return await edges.get_edge(
            session,
            source_memory_id=source,
            target_memory_id=target,
            rel_type=rel_type,
        )


async def edge_count(factory, project) -> int:
    async with factory() as session:
        result = await session.execute(
            text(
                "SELECT count(*) FROM memory_relations "
                "WHERE project = CAST(:p AS text)"
            ),
            {"p": project},
        )
        return result.scalar_one()


class TestAssociateArm:
    async def test_associate_fires(self, committing, project, run_cycle):
        """T-A2."""
        older, newer, _, _ = await build_pair(committing, project)
        stub = StubLLM(pair_verdict=verdict("duplicate"), refine=None)

        outcome = await run_cycle(committing, stub, refine_batch=0)

        assert outcome.associated == 1
        assert await edge_count(committing, project) == 1
        row = await edge_row(committing, newer, older)
        block = edges.pass_block_of(row, "near_duplicate")
        assert block["kind"] == "duplicate_candidate"
        assert block["hygiene_state"] == "open"

        events = await consolidated_events(committing, project, newer)
        assert len(events) == 1
        payload = events[0]["payload"]
        assert payload["action"] == "associate"
        assert payload["created"] is True
        assert payload["before"] == {"edge": None}
        assert payload["after"]["edge"]["rel_type"] == "RELATES_TO"

    async def test_associate_is_idempotent_and_silent(
        self, committing, project, run_cycle
    ):
        """T-A2b. A writer that re-upserted would accrete one `associate` event
        per cycle forever into an append-only journal."""
        older, newer, _, _ = await build_pair(committing, project)
        stub = StubLLM(pair_verdict=verdict("duplicate"), refine=None)

        first = await run_cycle(committing, stub, refine_batch=0)
        await _rewind_cursor(committing)
        second = await run_cycle(committing, stub, refine_batch=0)

        assert first.associated == 1
        assert second.associated == 0
        assert second.associate_unchanged == 1
        assert await edge_count(committing, project) == 1
        assert len(await consolidated_events(committing, project, newer)) == 1

    async def test_triage_survives_re_derivation(
        self, committing, project, run_cycle
    ):
        """T-A2c. A whole-object `SET properties` upsert resets this to "open",
        silently refilling the hygiene queue with items already actioned. This
        is the only test that catches it."""
        older, newer, _, _ = await build_pair(committing, project)
        stub = StubLLM(pair_verdict=verdict("duplicate"), refine=None)
        await run_cycle(committing, stub, refine_batch=0)

        async with committing() as session:
            await session.execute(
                text(
                    "UPDATE memory_relations SET properties = jsonb_set("
                    "  properties, '{dream,near_duplicate,hygiene_state}', "
                    "  CAST('\"dismissed\"' AS jsonb), true) "
                    "WHERE project = CAST(:p AS text)"
                ),
                {"p": project},
            )
            await session.commit()
        await _bump_score(committing, project)
        await _rewind_cursor(committing)

        await run_cycle(committing, stub, refine_batch=0)

        block = edges.pass_block_of(
            await edge_row(committing, newer, older), "near_duplicate"
        )
        assert block["hygiene_state"] == "dismissed"

    async def test_a_foreign_passs_block_survives(
        self, committing, project, run_cycle
    ):
        """T-A2d. A whole-object `SET properties` erases both a sibling pass's
        block and an unrelated top-level key."""
        older, newer, _, _ = await build_pair(committing, project)
        stub = StubLLM(pair_verdict=verdict("duplicate"), refine=None)
        await run_cycle(committing, stub, refine_batch=0)

        async with committing() as session:
            await session.execute(
                text(
                    "UPDATE memory_relations SET properties = "
                    "  jsonb_set(properties, '{dream,proximity}', "
                    "            CAST(:prox AS jsonb), true) "
                    "  || CAST(:other AS jsonb) "
                    "WHERE project = CAST(:p AS text)"
                ),
                {
                    "prox": json.dumps({"weight": 3}),
                    "other": json.dumps({"other": {"owned_by": "t2.16"}}),
                    "p": project,
                },
            )
            await session.commit()
        await _bump_score(committing, project)
        await _rewind_cursor(committing)

        await run_cycle(committing, stub, refine_batch=0)

        row = await edge_row(committing, newer, older)
        assert row["properties"]["dream"]["proximity"] == {"weight": 3}
        assert row["properties"]["other"] == {"owned_by": "t2.16"}
        assert edges.pass_block_of(row, "near_duplicate")["kind"] == (
            "duplicate_candidate"
        )

    @pytest.mark.parametrize(
        "existing",
        [None, {}, {"note": "x"}],
        ids=["null", "empty", "no-dream-key"],
    )
    async def test_a_dream_less_existing_edge_still_gets_its_block(
        self, committing, project, run_cycle, existing
    ):
        """T-A2e, and the only arm that catches the collapsed `jsonb_set`.

        T-A2d seeds a `dream` key, so it passes under the single-path form. The
        three shapes here do not: the write is silently dropped, `created=false`
        is still returned, the journalled `after` names a block the row does not
        have, and the identical-pass skip can then never fire — so every cycle
        re-upserts and re-journals the pair forever."""
        older, newer, _, _ = await build_pair(committing, project)
        async with committing() as session:
            await session.execute(
                text(
                    "INSERT INTO memory_relations "
                    "(id, source_memory_id, target_memory_id, rel_type, "
                    " project, properties) "
                    "VALUES (CAST(:id AS uuid), CAST(:s AS uuid), "
                    "        CAST(:t AS uuid), 'RELATES_TO', "
                    "        CAST(:p AS text), CAST(:props AS jsonb))"
                ),
                {
                    "id": str(new_id()),
                    "s": str(newer),
                    "t": str(older),
                    "p": project,
                    "props": None if existing is None else json.dumps(existing),
                },
            )
            await session.commit()
        stub = StubLLM(pair_verdict=verdict("duplicate"), refine=None)

        await run_cycle(committing, stub, refine_batch=0)

        row = await edge_row(committing, newer, older)
        block = edges.pass_block_of(row, "near_duplicate")
        assert block is not None
        assert block["kind"] == "duplicate_candidate"
        if existing:
            assert row["properties"]["note"] == "x"

        await _rewind_cursor(committing)
        second = await run_cycle(committing, stub, refine_batch=0)
        assert second.associate_unchanged == 1


async def _rewind_cursor(factory) -> None:
    """Send the rotating cursor back to the start so a second cycle in one test
    visits the same slice."""
    async with factory() as session:
        await session.execute(
            text("DELETE FROM config WHERE key = 'memory_dream_state'")
        )
        await session.commit()


async def _bump_score(factory, project) -> None:
    """Move the stored score out of its bucket so the identical-pass skip does
    not fire and the merge itself is what the test observes."""
    async with factory() as session:
        await session.execute(
            text(
                "UPDATE memory_relations SET properties = jsonb_set("
                "  properties, '{dream,near_duplicate,score}', "
                "  CAST('0.5' AS jsonb), true) "
                "WHERE project = CAST(:p AS text)"
            ),
            {"p": project},
        )
        await session.commit()


# ── Step 6: the refine arm and the content guard ─────────────────────────


def refine(summary=None, tags=None, **extra):
    body = {"summary": summary, "tags": tags}
    body.update(extra)
    return json.dumps(body)


class TestRefineArm:
    async def test_refine_fires(self, committing, project, run_cycle):
        """T-A3."""
        async with committing() as session:
            await seed_partition(session)
            target = await seed_memory(
                session, project=project, content="the sweeper runs hourly"
            )
            await put_vector(session, target, [0.0, 1.0, 0.0, 0.0])
            await session.commit()
        stub = StubLLM(
            pair_verdict=verdict("distinct"),
            refine=refine(summary="An hourly sweeper.", tags=["t212-ops"]),
        )

        outcome = await run_cycle(committing, stub, judge_fanout=0)

        assert outcome.refined == 1
        row = await memory_row(committing, target)
        assert row["summary"] == "An hourly sweeper."
        marker = row["metadata"]["dream"]["refine"]
        assert marker["content_sha"] == dream.content_sha("the sweeper runs hourly")

        events = await consolidated_events(committing, project, target)
        assert len(events) == 1
        payload = events[0]["payload"]
        assert payload["action"] == "refine"
        assert payload["before"]["summary"] is None
        assert payload["after"]["summary"] == "An hourly sweeper."
        assert "tags" in payload["fields"]

    async def test_refine_is_suppressed_on_a_re_run(
        self, committing, project, run_cycle
    ):
        """T-A3b. Deleting the marker check makes the second run write again and
        churn `updated_at` nightly for content that never changed."""
        async with committing() as session:
            await seed_partition(session)
            target = await seed_memory(
                session, project=project, content="the sweeper runs hourly"
            )
            await put_vector(session, target, [0.0, 1.0, 0.0, 0.0])
            await session.commit()
        stub = StubLLM(
            pair_verdict=verdict("distinct"), refine=refine(summary="An hourly sweeper.")
        )

        await run_cycle(committing, stub, judge_fanout=0)
        after_first = await memory_row(committing, target)
        await _rewind_cursor(committing)
        second = await run_cycle(committing, stub, judge_fanout=0)

        assert second.refined == 0
        after_second = await memory_row(committing, target)
        assert after_second["updated_at"] == after_first["updated_at"]
        assert len(await consolidated_events(committing, project, target)) == 1

    async def test_a_restored_summary_does_not_re_arm_the_refine(
        self, committing, project, run_cycle
    ):
        """D7's undo-interaction rule. Keying suppression on `summary_sha` as
        well as `content_sha` would re-apply the refine here and silently
        reverse T2.13's undo."""
        async with committing() as session:
            await seed_partition(session)
            target = await seed_memory(
                session,
                project=project,
                content="the sweeper runs hourly",
                summary="the original",
            )
            await put_vector(session, target, [0.0, 1.0, 0.0, 0.0])
            await session.commit()
        stub = StubLLM(
            pair_verdict=verdict("distinct"), refine=refine(summary="a rewrite")
        )
        await run_cycle(committing, stub, judge_fanout=0)

        async with committing() as session:
            await session.execute(
                text(
                    "UPDATE memories SET summary = 'the original' "
                    "WHERE id = CAST(:id AS uuid)"
                ),
                {"id": str(target)},
            )
            await session.commit()
        await _rewind_cursor(committing)

        second = await run_cycle(committing, stub, judge_fanout=0)

        assert second.refined == 0
        assert (await memory_row(committing, target))["summary"] == "the original"

    async def test_the_model_tries_to_rewrite_content_and_is_refused(
        self, committing, project, run_cycle
    ):
        """T-N2a, and the non-vacuous proof of Done-when 2: the model actively
        attempted the forbidden write and the code refused it. Asserting content
        is unchanged when nothing tried to change it proves nothing."""
        async with committing() as session:
            await seed_partition(session)
            target = await seed_memory(
                session, project=project, content="the sweeper runs hourly"
            )
            await put_vector(session, target, [0.0, 1.0, 0.0, 0.0])
            await session.commit()
        stub = StubLLM(
            pair_verdict=verdict("distinct"),
            refine=refine(summary="s", content="REWRITTEN"),
        )

        outcome = await run_cycle(committing, stub, judge_fanout=0)

        assert outcome.refined == 1
        row = await memory_row(committing, target)
        assert row["content"] == "the sweeper runs hourly"
        assert row["summary"] == "s"
        events = await consolidated_events(committing, project, target)
        assert "content" not in events[0]["payload"]["after"]

    def test_the_allowlist_raises_on_a_forbidden_column(self):
        """T-N2b. The allowlist is enforcement, not documentation."""
        with pytest.raises(dream.RefinableColumnError) as caught:
            dream.build_refine_update({"content": "x"})
        assert "content" in str(caught.value)

    def test_the_allowlist_accepts_only_what_it_names(self):
        assignments, ordered = dream.build_refine_update({"summary": "s"})
        assert ordered == ("summary",)
        assert assignments == "summary = :summary"


# ── the source scans, and their negative controls ────────────────────────
#
# What these prove and what they do not. They raise the cost of a content
# write and of a removal: the four write shapes that exist today fail the
# build. They do **not** establish that no removal is expressible — a column
# name arriving as a bound parameter (`SET :col = ...`) is invisible to an AST
# walk by construction, and so is a computed attribute name. Stated rather than
# implied, because a reader trusts a guard, and an overclaimed one is worse
# than the gap it hides.

BACKEND = pathlib.Path(__file__).resolve().parent.parent

_SCANNED = (
    "app/services/memory_dream.py",
    "app/repositories/memory_relations.py",
)

_UPDATE_MEMORIES = re.compile(r"UPDATE\s+memories", re.IGNORECASE)
_DELETE_MEMORIES = re.compile(r"DELETE\s+FROM\s+memories", re.IGNORECASE)
_ANY_UPDATE = re.compile(r"UPDATE\s+\w+", re.IGNORECASE)


class _ForbiddenWriteVisitor(ast.NodeVisitor):
    """Rules C1-C4 (content) and R1-R3 (removal).

    C1 flags a raw statement that updates `memories` and mentions `content` in
    the same constant. C2 flags an attribute assignment to `.content`, and is
    deliberately blind to a bare `Name` target so the dataclass's own field
    declaration is not flagged. C3 flags `setattr(x, "content", y)`. C4 flags a
    `.values()` / model construction carrying `content`, both as a keyword and
    as a literal dict passed positionally or splatted. R1 flags a raw
    `DELETE FROM memories`, R2 any `.delete()` call, and R3 a `memory_ids`
    rewrite — the three shapes a hard merge can take.
    """

    def __init__(self, rel: str):
        self.rel = rel
        self.offenders: list[str] = []

    def _flag(self, node, rule: str, detail: str) -> None:
        self.offenders.append(f"{self.rel}:{node.lineno}: {rule} {detail}")

    def visit_Constant(self, node: ast.Constant) -> None:
        if isinstance(node.value, str):
            if _UPDATE_MEMORIES.search(node.value) and "content" in node.value:
                self._flag(node, "C1", "raw UPDATE memories mentioning content")
            if _DELETE_MEMORIES.search(node.value):
                self._flag(node, "R1", "raw DELETE FROM memories")
            if _ANY_UPDATE.search(node.value) and "memory_ids" in node.value:
                # Repointing another table's references from one memory to
                # another is the third shape a hard merge can take, and the
                # only one neither of the row-set snapshots would notice.
                self._flag(node, "R3", "a memory_ids rewrite")
        self.generic_visit(node)

    def _check_target(self, target, node) -> None:
        if isinstance(target, ast.Attribute) and target.attr == "content":
            self._flag(node, "C2", "attribute assignment to .content")
        elif isinstance(target, (ast.Tuple, ast.List)):
            for element in target.elts:
                self._check_target(element, node)

    def visit_Assign(self, node: ast.Assign) -> None:
        for target in node.targets:
            self._check_target(target, node)
        self.generic_visit(node)

    def visit_AnnAssign(self, node: ast.AnnAssign) -> None:
        self._check_target(node.target, node)
        self.generic_visit(node)

    def visit_AugAssign(self, node: ast.AugAssign) -> None:
        self._check_target(node.target, node)
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        func = node.func
        if isinstance(func, ast.Name) and func.id == "setattr":
            if (
                len(node.args) >= 2
                and isinstance(node.args[1], ast.Constant)
                and node.args[1].value == "content"
            ):
                self._flag(node, "C3", "setattr of content")
        writes_a_row = (
            isinstance(func, ast.Attribute) and func.attr == "values"
        ) or (isinstance(func, ast.Name) and func.id == "Memory")
        if writes_a_row:
            if any(keyword.arg == "content" for keyword in node.keywords):
                self._flag(node, "C4", "content keyword on a row write")
            literals = [arg for arg in node.args if isinstance(arg, ast.Dict)]
            literals += [
                keyword.value
                for keyword in node.keywords
                if keyword.arg is None and isinstance(keyword.value, ast.Dict)
            ]
            for literal in literals:
                if any(
                    isinstance(key, ast.Constant) and key.value == "content"
                    for key in literal.keys
                ):
                    self._flag(node, "C4", "content key in a row-write dict")
        if isinstance(func, ast.Attribute) and func.attr == "delete":
            self._flag(node, "R2", "a .delete() call")
        self.generic_visit(node)


def _forbidden_writes(paths, root) -> list[str]:
    offenders: list[str] = []
    for path in paths:
        visitor = _ForbiddenWriteVisitor(str(path.relative_to(root)))
        visitor.visit(ast.parse(path.read_text()))
        offenders.extend(visitor.offenders)
    return offenders


def _scanned_paths() -> list[pathlib.Path]:
    return [BACKEND / rel for rel in _SCANNED]


class TestSourceScans:
    def test_no_content_write_and_no_removal_exists(self):
        """T-N1c / T-N2d."""
        paths = _scanned_paths()
        assert len(paths) >= 2
        for path in paths:
            assert path.exists(), f"{path} is not there to scan"

        assert _forbidden_writes(paths, BACKEND) == []

    @pytest.mark.parametrize(
        ("source", "rule"),
        [
            ('SQL = "UPDATE memories SET content = :c"', "C1"),
            ("def f(memory):\n    memory.content = 'x'\n", "C2"),
            ("def f(memory):\n    setattr(memory, 'content', 'x')\n", "C3"),
            ("def f(stmt):\n    stmt.values(content='x')\n", "C4"),
            ("def f(stmt):\n    stmt.values({'content': 'x'})\n", "C4"),
            ("def f(stmt):\n    stmt.values(**{'content': 'x'})\n", "C4"),
            ('SQL = "DELETE FROM memories WHERE id = :id"', "R1"),
            ("def f(session, m):\n    session.delete(m)\n", "R2"),
            ('SQL = "UPDATE entities SET memory_ids = :ids"', "R3"),
        ],
    )
    def test_the_scan_flags_every_shape_it_claims_to(self, tmp_path, source, rule):
        """T-N1d / T-N2d's negative control: a scan that found nothing to scan
        would pass silently, and so would one whose rules had been deleted."""
        offending = tmp_path / "violation.py"
        offending.write_text(source)

        offenders = _forbidden_writes([offending], tmp_path)

        assert offenders, f"rule {rule} did not flag its own violation"
        assert any(rule in offender for offender in offenders)

    def test_the_scan_admits_the_shapes_that_are_legitimate(self, tmp_path):
        """The rules must not widen into "any mention of content": reading the
        column, naming it in a comparison, and declaring a dataclass field are
        all things this module legitimately does."""
        innocent = tmp_path / "innocent.py"
        innocent.write_text(
            "from dataclasses import dataclass\n"
            'SQL = "SELECT content FROM memories WHERE id = :id"\n'
            'OTHER = "UPDATE memories SET summary = :summary"\n'
            "\n"
            "@dataclass\n"
            "class Row:\n"
            "    content: str\n"
            "\n"
            "def f(row, other):\n"
            "    return row.content == other.content\n"
        )

        assert _forbidden_writes([innocent], tmp_path) == []


# ── Step 7: the negatives and the journalling contract ───────────────────


async def _three_action_fixture(committing, project):
    """A cycle that provably does all three things at once.

    OLD/NEW subsume, DUP_A/DUP_B associate, and LONE refines — so the row-set
    invariance assertion below is made against a cycle that definitely acted.
    """


    def refined_already(content: str) -> dict:
        """A marker matching the row's own content, so the refine arm passes it
        over and LONE is the only memory this cycle refines."""
        return {"dream": {"refine": {"content_sha": dream.content_sha(content)}}}

    async with committing() as session:
        await seed_partition(session)
        older = await seed_memory(
            session, project=project, content="the api listens on 8000",
            created_at=NOW,
            metadata=refined_already("the api listens on 8000"),
        )
        newer = await seed_memory(
            session, project=project,
            content="the api listens on 8000 with keepalive",
            created_at=NOW + timedelta(hours=1),
            metadata=refined_already("the api listens on 8000 with keepalive"),
        )
        dup_a = await seed_memory(
            session, project=project, content="the sweeper runs hourly",
            created_at=NOW + timedelta(hours=2),
            metadata=refined_already("the sweeper runs hourly"),
        )
        dup_b = await seed_memory(
            session, project=project, content="the sweeper runs every hour",
            created_at=NOW + timedelta(hours=3),
            metadata=refined_already("the sweeper runs every hour"),
        )
        lone = await seed_memory(
            session, project=project, content="the vite proxy listens on 3636",
            created_at=NOW + timedelta(hours=4),
        )
        await put_vector(session, older, [1.0, 0.0, 0.0, 0.0])
        await put_vector(session, newer, [1.0, 0.0, 0.0, 0.0])
        await put_vector(session, dup_a, [0.0, 1.0, 0.0, 0.0])
        await put_vector(session, dup_b, [0.0, 1.0, 0.0, 0.0])
        await put_vector(session, lone, [0.0, 0.0, 1.0, 0.0])
        await session.commit()

    def pair_reply(body: str) -> str:
        return verdict("subsumes" if "listens on 8000" in body else "duplicate")

    stub = StubLLM(
        pair_verdict=pair_reply,
        refine=refine(summary="A refined summary.", tags=["t212-ops"]),
    )
    return {
        "older": older, "newer": newer, "dup_a": dup_a, "dup_b": dup_b,
        "lone": lone, "stub": stub,
    }


async def _all_memories(factory) -> dict[str, str]:
    async with factory() as session:
        result = await session.execute(
            text("SELECT CAST(id AS text) AS id, content FROM memories")
        )
        return {row["id"]: dream.content_sha(row["content"]) for row in result.mappings()}


async def _reference_counts(factory, memory_id) -> dict[str, int]:
    """Every table that points at a memory, counted by endpoint. A hard merge
    would have moved these onto the surviving row."""
    async with factory() as session:
        counts = {}
        for name, statement in (
            (
                "memory_relations_source",
                "SELECT count(*) FROM memory_relations "
                "WHERE source_memory_id = CAST(:id AS uuid)",
            ),
            (
                "memory_relations_target",
                "SELECT count(*) FROM memory_relations "
                "WHERE target_memory_id = CAST(:id AS uuid)",
            ),
            (
                "memory_crossrefs",
                "SELECT count(*) FROM memory_crossrefs "
                "WHERE memory_id = CAST(:id AS uuid)",
            ),
            (
                # fact_sources references a memory by text `source_ref`, not by
                # a uuid column.
                "fact_sources",
                "SELECT count(*) FROM fact_sources "
                "WHERE source_kind = 'memory' AND source_ref = CAST(:id AS text)",
            ),
        ):
            result = await session.execute(text(statement), {"id": str(memory_id)})
            counts[name] = result.scalar_one()
        return counts


class TestNoPathDeletesOrHardMerges:
    async def test_the_row_set_is_invariant_under_a_cycle_that_acted(
        self, committing, project, run_cycle
    ):
        """T-N1a. The outcome assertion is the whole point: without it a cycle
        that did nothing would pass this trivially."""
        fixture = await _three_action_fixture(committing, project)
        before = await _all_memories(committing)

        outcome = await run_cycle(committing, fixture["stub"])

        assert outcome.subsumed >= 1
        assert outcome.associated >= 1
        assert outcome.refined >= 1
        assert await _all_memories(committing) == before

    async def test_the_cycle_moved_state_without_rewriting_a_row(
        self, committing, project, run_cycle
    ):
        """T-N1b, the differential twin: the invariance above is not because the
        cycle is inert."""
        fixture = await _three_action_fixture(committing, project)
        before = await memory_row(committing, fixture["older"])

        await run_cycle(committing, fixture["stub"])

        after = await memory_row(committing, fixture["older"])
        assert before["status"] == "active"
        assert after["status"] == "superseded"
        assert after["content"] == before["content"]

    async def test_references_to_a_subsumed_memory_are_not_repointed(
        self, committing, project, run_cycle
    ):
        """The third shape of a hard merge: moving another table's references
        from the retired memory onto the survivor."""
        fixture = await _three_action_fixture(committing, project)
        before = await _reference_counts(committing, fixture["older"])

        await run_cycle(committing, fixture["stub"])

        assert (await memory_row(committing, fixture["older"]))["status"] == (
            "superseded"
        )
        assert await _reference_counts(committing, fixture["older"]) == before


class TestJournalling:
    async def test_every_action_writes_one_before_after_payload(
        self, committing, project, run_cycle
    ):
        """T-J1, table-driven over the three actions."""
        fixture = await _three_action_fixture(committing, project)
        snapshot = {
            "subsume": await memory_row(committing, fixture["older"]),
            "refine": await memory_row(committing, fixture["lone"]),
        }

        outcome = await run_cycle(committing, fixture["stub"])

        events = await consolidated_events(committing, project)
        by_action: dict[str, list[dict]] = {}
        for event in events:
            by_action.setdefault(event["payload"]["action"], []).append(event)
        assert set(by_action) == {"subsume", "associate", "refine"}

        for action, rows in by_action.items():
            assert len(rows) == 1, f"{action} journalled {len(rows)} rows"
            payload = rows[0]["payload"]
            assert "before" in payload and "after" in payload
            assert payload["before"] != payload["after"]
            assert payload["cycle_id"] == outcome.cycle_id

        assert by_action["subsume"][0]["payload"]["before"]["status"] == (
            snapshot["subsume"]["status"]
        )
        assert by_action["refine"][0]["payload"]["before"]["summary"] == (
            snapshot["refine"]["summary"]
        )

    async def test_a_second_cycle_carries_a_different_cycle_id(
        self, committing, project, run_cycle
    ):
        fixture = await _three_action_fixture(committing, project)
        first = await run_cycle(committing, fixture["stub"])
        await _rewind_cursor(committing)
        second = await run_cycle(committing, fixture["stub"])

        assert first.cycle_id != second.cycle_id

    async def test_a_declined_pair_journals_nothing(
        self, committing, project, run_cycle
    ):
        """T-J3. `events` is append-only, so a phantom transition row can never
        be removed once written."""
        await build_pair(committing, project)
        stub = StubLLM(pair_verdict=verdict("distinct"), refine=None)

        await run_cycle(committing, stub, refine_batch=0)

        assert await consolidated_events(committing, project) == []

    async def test_each_payload_is_sufficient_to_invert_its_action(
        self, committing, project, run_cycle
    ):
        """T-J2, the strongest form: the inverse is applied by hand here, from
        the payload and nothing else, and the object must land back where it
        started field-for-field — with two exclusions asserted positively rather
        than skipped."""
        fixture = await _three_action_fixture(committing, project)
        before_subsume = await memory_row(committing, fixture["older"])
        before_refine = await memory_row(committing, fixture["lone"])

        await run_cycle(committing, fixture["stub"])
        after_refine = await memory_row(committing, fixture["lone"])

        events = {
            event["payload"]["action"]: event["payload"]
            for event in await consolidated_events(committing, project)
        }

        # Subsume: one statement, because the CHECK forbids the two-statement
        # form.
        payload = events["subsume"]
        async with committing() as session:
            await session.execute(
                text(
                    "UPDATE memories SET status = CAST(:status AS memory_status), "
                    "superseded_by = CAST(:pointer AS uuid) "
                    "WHERE id = CAST(:id AS uuid)"
                ),
                {
                    "status": payload["before"]["status"],
                    "pointer": payload["before"]["superseded_by"],
                    "id": payload["pair"]["older"],
                },
            )
            await session.commit()
        restored = await memory_row(committing, fixture["older"])
        assert restored["status"] == before_subsume["status"]
        assert restored["superseded_by"] == before_subsume["superseded_by"]

        # Associate: `created` decides the inverse, and it was a fresh row.
        payload = events["associate"]
        assert payload["created"] is True
        async with committing() as session:
            await session.execute(
                text(
                    "DELETE FROM memory_relations "
                    "WHERE source_memory_id = CAST(:s AS uuid) "
                    "AND target_memory_id = CAST(:t AS uuid) "
                    "AND rel_type = CAST(:r AS text)"
                ),
                {
                    "s": payload["after"]["edge"]["source"],
                    "t": payload["after"]["edge"]["target"],
                    "r": payload["after"]["edge"]["rel_type"],
                },
            )
            await session.commit()
        assert await edge_count(committing, project) == 0

        # Refine: summary and tags, and nothing else.
        payload = events["refine"]
        async with committing() as session:
            await session.execute(
                text(
                    "UPDATE memories SET summary = :summary "
                    "WHERE id = CAST(:id AS uuid)"
                ),
                {"summary": payload["before"]["summary"], "id": str(fixture["lone"])},
            )
            await PostgresMemoryRepository(session).set_tags(
                fixture["lone"], payload["before"]["tags"]
            )
            await session.commit()
        undone = await memory_row(committing, fixture["lone"])
        assert undone["summary"] == before_refine["summary"]

        # The two named exclusions, asserted rather than skipped. Restoring the
        # marker would clear it on a first refine and re-arm the very loop the
        # suppression rule closes; `updated_at` is the trigger's and no inverse
        # can restore it.
        assert (
            undone["metadata"]["dream"]["refine"]
            == after_refine["metadata"]["dream"]["refine"]
        )
        assert undone["updated_at"] > after_refine["updated_at"]

    async def test_an_undone_refine_stays_undone(
        self, committing, project, run_cycle
    ):
        """T-J2b, the executable form of the marker rule. An inverse that
        restored `metadata.dream.refine` passes T-J2 and fails only here."""
        fixture = await _three_action_fixture(committing, project)
        before = await memory_row(committing, fixture["lone"])
        await run_cycle(committing, fixture["stub"])

        payload = {
            event["payload"]["action"]: event["payload"]
            for event in await consolidated_events(committing, project)
        }["refine"]
        async with committing() as session:
            await session.execute(
                text(
                    "UPDATE memories SET summary = :summary "
                    "WHERE id = CAST(:id AS uuid)"
                ),
                {"summary": payload["before"]["summary"], "id": str(fixture["lone"])},
            )
            await PostgresMemoryRepository(session).set_tags(
                fixture["lone"], payload["before"]["tags"]
            )
            await session.commit()
        await _rewind_cursor(committing)

        second = await run_cycle(committing, fixture["stub"])

        assert second.refined == 0
        after = await memory_row(committing, fixture["lone"])
        assert after["summary"] == before["summary"]
        assert len(
            [
                event
                for event in await consolidated_events(committing, project)
                if event["payload"]["action"] == "refine"
            ]
        ) == 1

    async def test_one_poisonous_action_does_not_void_its_siblings(
        self, committing, project, run_cycle, monkeypatch
    ):
        """Without the per-action savepoint the first action's write would go
        with the second's failure."""
        fixture = await _three_action_fixture(committing, project)
        original = dream.apply_associate
        calls = {"n": 0}

        async def explode(session, action, **kwargs):
            calls["n"] += 1
            raise RuntimeError("poisonous action")

        monkeypatch.setattr(dream, "apply_associate", explode)

        outcome = await run_cycle(committing, fixture["stub"])

        assert calls["n"] >= 1
        assert outcome.failed >= 1
        assert outcome.subsumed == 1
        assert outcome.refined >= 1
        assert (await memory_row(committing, fixture["older"]))["status"] == (
            "superseded"
        )


# ── Step 8: the primitive's journal reason (D11) ─────────────────────────


async def superseded_events(factory, project, memory_id) -> list[dict]:
    async with factory() as session:
        result = await session.execute(
            text(
                "SELECT payload FROM events WHERE event_type = 'superseded' "
                "AND project = CAST(:project AS text) "
                "AND object_id = CAST(:id AS uuid) ORDER BY created_at, id"
            ),
            {"project": project, "id": str(memory_id)},
        )
        return [dict(row) for row in result.mappings()]


class TestJournalReason:
    async def test_a_dedup_subsumption_is_labelled_truthfully(
        self, committing, project, run_cycle
    ):
        """T-RSN1. Before the thread, the primitive labelled this
        "status_bridge" — a claim that a fact invalidation produced it, which is
        false for every dream-driven subsumption."""
        older, _, _, _ = await build_pair(committing, project)
        stub = StubLLM(pair_verdict=verdict("subsumes"), refine=None)

        await run_cycle(committing, stub, refine_batch=0)

        events = await superseded_events(committing, project, older)
        assert len(events) == 1
        assert events[0]["payload"]["reason"] == "dream_dedup"

    async def test_the_defaulted_call_still_reads_status_bridge(
        self, committing, project
    ):
        """T-RSN2. One keyword argument separates this from T-RSN1; together
        they prove the parameter is threaded rather than the literal renamed."""
        from app.services.supersede import supersede

        async with committing() as session:
            older = await seed_memory(
                session, project=project, content="older", created_at=NOW
            )
            newer = await seed_memory(
                session,
                project=project,
                content="newer",
                created_at=NOW + timedelta(hours=1),
            )
            await session.commit()
        async with committing() as session:
            result = await supersede(
                session, memory_id=older, superseded_by=newer
            )
            await session.commit()

        assert result.applied is True
        events = await superseded_events(committing, project, older)
        assert events[0]["payload"]["reason"] == "status_bridge"


# ── Step 9: the job wiring ───────────────────────────────────────────────


class TestJobWiring:
    async def test_a_persisted_batch_size_survives_the_schema_swap(self):
        """`JobRegistry.set_config` merges and never drops a key, so renaming
        the placeholder's knob would orphan an operator's value silently. The
        key, default and ceiling are kept verbatim instead."""
        from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

        from app.config import settings
        from app.services.dream_jobs import MEMORY_DREAM_JOB_KEY, register_dream_jobs
        from app.services.job_registry import JobRegistry

        engine = create_async_engine(settings.test_database_url)
        registry = JobRegistry(async_sessionmaker(engine, expire_on_commit=False))
        register_dream_jobs(registry)
        try:
            cfg = await registry.set_config(MEMORY_DREAM_JOB_KEY, {"batch_size": 7})
            assert cfg.config["batch_size"] == 7
            reloaded = await registry.load_config(MEMORY_DREAM_JOB_KEY)
            assert reloaded.config["batch_size"] == 7

            schema = {
                field.key: field
                for field in registry.get(MEMORY_DREAM_JOB_KEY).config_schema
            }
            assert schema["batch_size"].default == 50
            assert schema["batch_size"].max == 1000
        finally:
            await registry.stop_all()
            async with async_sessionmaker(engine)() as cleanup:
                await cleanup.execute(
                    text("DELETE FROM config WHERE key = 'job:memory_dream'")
                )
                await cleanup.commit()
            await engine.dispose()

    def test_the_job_module_never_quotes_its_own_key(self):
        """Invariant 15's scan runs over every file under `app/` and exempts
        only the umbrella, so a quoted `"memory_dream"` inside the job's own
        body fails the build. `logging.getLogger(__name__)` is what keeps it
        out; the state config key is safe because the pattern needs a closing
        quote immediately after."""
        source = (BACKEND / "app" / "services" / "memory_dream.py").read_text()
        assert '"memory_dream"' not in source
        assert "'memory_dream'" not in source
        assert '"memory_dream_state"' in source

    def test_the_runner_is_no_longer_a_placeholder(self):
        from app.services.dream_jobs import (
            MEMORY_DREAM_JOB_KEY,
            SHIPPED_DREAM_JOBS,
        )

        assert SHIPPED_DREAM_JOBS[MEMORY_DREAM_JOB_KEY] == "memory_dream"
