"""T2.12 — `memory_dream`: subsume, associate, refine; never merges, never deletes.

Doc 08 §5.4. Three Done-whens, two of them negatives, and a negative is where a
decorative guard hides: asserting a row still exists after a cycle that was
never going to remove it proves nothing. Every negative here is proven twice —
a differential arm (the same fixture builder, one flipped bit, asserting the
opposite outcome) and, where the claim is about code shape rather than
behaviour, a source scan carrying its own in-suite negative control.
"""
from __future__ import annotations

import json
from dataclasses import fields
from datetime import datetime, timedelta, timezone
from uuid import UUID

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app.repositories import memory_relations as edges
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
        embed_error: Exception | None = None,
        pair_verdict=None,
        refine=None,
    ):
        self.fingerprint = fingerprint
        self.embed_error = embed_error
        self.pair_verdict = pair_verdict
        self.refine = refine
        self.embed_calls: list[str] = []
        self.calls: list[dict] = []

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
            for statement in (
                "DELETE FROM memory_relations WHERE project LIKE 't212-%'",
                "DELETE FROM memories WHERE project LIKE 't212-%'",
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
