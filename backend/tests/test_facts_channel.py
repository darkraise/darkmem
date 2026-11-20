"""The Layer-2 facts retrieval channel (doc 07 §2, T2.42).

Four properties this module exists to pin, each with a mutation that breaks it:

* **Born with pushdown.** ``project`` and the belief window are in the
  generating SQL. Asserted on the compiled statement *and* by ``EXPLAIN``, not
  only on the result set — a Python re-filter produces the same rows and the
  same green tests, which is exactly why doc 07 §7 calls the pushdown a
  correctness property rather than a performance one.
* **The belief predicate is currently-open-belief, not "live".** A
  window-closed row is retained history (doc 08 §3.1); serving it as current is
  the failure the narrower predicate exists to prevent.
* **Every row carries its verification state and belief window.**
* **A disputed fact is returned.** Never filtered, never silently one-sided.
"""
from __future__ import annotations

import ast
import asyncio
import contextlib
import inspect
import logging
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import async_sessionmaker

import app.services.facts_channel as facts_channel
from app.repositories.knowledge_triples import (
    LIVE_PREDICATE,
    OPEN_BELIEF_PREDICATE,
    KnowledgeTripleRepository,
)
from app.services import fact_access_stats
from app.services.facts_channel import (
    ARM_FETCH_MULTIPLIER,
    KEYWORD_ARM,
    LAYER,
    NAME_ARM,
    SEMANTIC_ARM,
    SEMANTIC_ARM_OWNER,
    FactsChannel,
)
from app.services.rank_fusion import normalize_row_id
from app.services.triple_key import compute_triple_key
from app.utils import background
from tests.conftest import test_engine

PROJECT = "t242-facts"
OTHER_PROJECT = "t242-elsewhere"
NOW = datetime(2026, 8, 1, 12, 0, 0, tzinfo=timezone.utc)

# A term no filler row carries, so a hit is the seeded fact and nothing else.
RARE_TERM = "zarquon"


async def _open_fact(
    session,
    *,
    subject: str = "darkmem",
    rel: str = "USES",
    obj: str = "postgres",
    fact: str | None = None,
    project: str = PROJECT,
    valid_at: datetime | None = None,
    **overrides,
) -> dict:
    repo = KnowledgeTripleRepository(session)
    return await repo.insert_open(
        triple_key=compute_triple_key(project, subject, rel, obj),
        subject_name=subject,
        object_name=obj,
        rel_type=rel,
        fact=fact if fact is not None else f"{subject} {rel} {obj} {RARE_TERM}",
        reference_time=NOW,
        project=project,
        valid_at=valid_at,
        **overrides,
    )


async def _set_status(session, fact_id: str, status: str, review_state=None) -> None:
    """Move the verification axis by hand.

    Deliberately raw SQL: the repository's writer refuses ``confirmed`` because
    only a human ratifies, and the verification ladder is not on trial here.
    """
    await session.execute(
        text(
            "UPDATE knowledge_triples SET verification_status = CAST(:s AS text), "
            "review_state = CAST(:r AS text) WHERE id = CAST(:id AS uuid)"
        ),
        {"s": status, "r": review_state, "id": str(fact_id)},
    )


def _ids(rows) -> set[str]:
    return {row["fact_id"] for row in rows}


# ── the predicates are in the SQL, not in Python ─────────────────────


@pytest.mark.asyncio
@pytest.mark.parametrize("arm", ["keyword_query", "name_query"])
async def test_both_arms_render_the_project_predicate_in_sql(session, arm):
    """Move this into a Python filter and this fails while every result-set
    assertion in the file still passes."""
    sql, params = getattr(FactsChannel(session), arm)(RARE_TERM, PROJECT, 20)

    assert "project = CAST(:project AS text)" in sql
    assert params["project"] == PROJECT


@pytest.mark.asyncio
@pytest.mark.parametrize("arm", ["keyword_query", "name_query"])
async def test_both_arms_render_the_open_belief_predicate_in_sql(session, arm):
    sql, _ = getattr(FactsChannel(session), arm)(RARE_TERM, PROJECT, 20)

    assert OPEN_BELIEF_PREDICATE in sql
    # The trap: `LIVE_PREDICATE` is a prefix of the open-belief one, so the
    # assertion above cannot tell them apart on its own.
    assert sql.count(LIVE_PREDICATE) == sql.count(OPEN_BELIEF_PREDICATE)


def test_the_two_predicates_are_not_the_same_thing():
    """The whole reason both spellings live side by side in the repository."""
    assert LIVE_PREDICATE != OPEN_BELIEF_PREDICATE
    assert "invalid_at IS NULL" not in LIVE_PREDICATE
    assert "invalid_at IS NULL" in OPEN_BELIEF_PREDICATE


@pytest.mark.asyncio
async def test_a_fact_in_another_project_is_unreachable(session):
    mine = await _open_fact(session)
    await _open_fact(session, project=OTHER_PROJECT, subject="other")

    rows = (await FactsChannel(session).search_with_trace(RARE_TERM, project=PROJECT)).results

    assert _ids(rows) == {mine["id"]}


@pytest.mark.asyncio
async def test_the_channel_cannot_be_called_without_a_project(session):
    """``project`` is keyword-only and required, the same structural choice
    ``get_live`` makes: an optional scope is a scope a caller can forget."""
    with pytest.raises(TypeError):
        (await FactsChannel(session).search_with_trace(RARE_TERM)).results  # type: ignore[call-arg]


# ── the belief window ────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_a_window_closed_fact_does_not_surface_as_current(session):
    """The mutation this guards: widening the predicate to ``LIVE_PREDICATE``
    leaves the row live — it is retained history — and it would surface here
    indistinguishable from a currently-held belief."""
    repo = KnowledgeTripleRepository(session)
    closed = await _open_fact(session, obj="mysql", valid_at=NOW - timedelta(days=30))
    await repo.close_window(closed["id"], NOW - timedelta(days=1))
    current = await _open_fact(session, obj="postgres")

    rows = (await FactsChannel(session).search_with_trace(RARE_TERM, project=PROJECT)).results

    assert _ids(rows) == {current["id"]}
    assert await repo.get_live(project=PROJECT, limit=50)  # still live history


@pytest.mark.asyncio
async def test_an_expired_fact_does_not_surface_at_all(session):
    repo = KnowledgeTripleRepository(session)
    gone = await _open_fact(session, obj="mysql")
    await repo.expire(gone["id"])
    kept = await _open_fact(session, obj="postgres")

    rows = (await FactsChannel(session).search_with_trace(RARE_TERM, project=PROJECT)).results

    assert _ids(rows) == {kept["id"]}


@pytest.mark.asyncio
async def test_the_name_arm_scopes_the_belief_window_too(session):
    """Both arms, not just the one the fact-text query happens to exercise."""
    repo = KnowledgeTripleRepository(session)
    closed = await _open_fact(session, subject="quenelle", obj="mysql")
    await repo.close_window(closed["id"], NOW)

    channel = FactsChannel(session)
    rows = await channel._run(channel.name_query("quenelle", PROJECT, 20), NAME_ARM)

    assert rows == []


# ── labels ride every row ────────────────────────────────────────────


@pytest.mark.asyncio
async def test_every_row_carries_its_verification_state_and_belief_window(session):
    fact = await _open_fact(session, confidence=0.8, applies_when={"env": "prod"})
    await _set_status(session, fact["id"], "corroborated")

    (row,) = (await FactsChannel(session).search_with_trace(RARE_TERM, project=PROJECT)).results

    assert row["verification_status"] == "corroborated"
    assert row["review_state"] is None
    assert row["confidence"] == pytest.approx(0.8)
    assert row["layer"] == LAYER
    assert row["id_kind"] == "fact"
    assert set(row["belief_window"]) == {
        "valid_at", "invalid_at", "expired_at", "reference_time",
    }
    assert row["belief_window"]["reference_time"] == NOW


@pytest.mark.asyncio
@pytest.mark.parametrize("marked", [True, False])
async def test_a_row_carries_the_under_sourced_overlay_it_is_wearing(session, marked):
    """T2.46's caution overlay, on the channel's own projection.

    Both halves matter: without the marked case the channel serves a fact one
    lost source from demotion as if it were healthy, and without the unmarked
    case a constant would pass.
    """
    fact = await _open_fact(session)
    await _set_status(session, fact["id"], "corroborated")
    if marked:
        await session.execute(
            text(
                "UPDATE knowledge_triples SET demotion_pending_since = "
                "CAST(:t AS timestamptz) WHERE id = CAST(:id AS uuid)"
            ),
            {"t": NOW, "id": fact["id"]},
        )

    (row,) = (await FactsChannel(session).search_with_trace(RARE_TERM, project=PROJECT)).results

    assert row["verification_status"] == "corroborated"
    assert row["demotion_pending_since"] == (NOW if marked else None)


@pytest.mark.asyncio
async def test_the_belief_window_labels_show_the_scope_actually_held(session):
    """Constant-NULL by the channel's own predicate — and carrying them anyway
    is what makes a scope failure observable instead of silent."""
    await _open_fact(session)

    (row,) = (await FactsChannel(session).search_with_trace(RARE_TERM, project=PROJECT)).results

    assert row["belief_window"]["invalid_at"] is None
    assert row["belief_window"]["expired_at"] is None


@pytest.mark.asyncio
async def test_the_id_spelling_is_one_string_under_both_keys(session):
    fact = await _open_fact(session)

    (row,) = (await FactsChannel(session).search_with_trace(RARE_TERM, project=PROJECT)).results

    assert isinstance(row["fact_id"], str)
    assert row["fact_id"] == row["id"] == str(uuid.UUID(fact["id"]))


@pytest.mark.asyncio
async def test_the_shared_fusion_can_key_a_fact_row(session):
    """The invariant-9 boundary. ``normalize_row_id`` reads ``memory_id`` or
    ``id``; a row it cannot key is dropped from a fusion without a word, so
    T2.43 would silently lose every fact."""
    await _open_fact(session)

    (row,) = (await FactsChannel(session).search_with_trace(RARE_TERM, project=PROJECT)).results

    assert normalize_row_id(row) == row["fact_id"]


@pytest.mark.asyncio
async def test_applies_when_arrives_as_a_mapping(session):
    await _open_fact(session, applies_when={"env": "prod"})

    (row,) = (await FactsChannel(session).search_with_trace(RARE_TERM, project=PROJECT)).results

    assert row["applies_when"] == {"env": "prod"}


# ── disputed facts are returned, never filtered ──────────────────────


@pytest.mark.asyncio
async def test_a_disputed_fact_is_returned(session):
    """Add ``AND verification_status != 'disputed'`` to either arm and this
    fails. That filter is the failure the clause exists to prevent."""
    disputed = await _open_fact(session, obj="mysql")
    await _set_status(session, disputed["id"], "disputed", review_state="open")
    plain = await _open_fact(session, obj="postgres")

    rows = (await FactsChannel(session).search_with_trace(RARE_TERM, project=PROJECT)).results

    assert _ids(rows) == {disputed["id"], plain["id"]}


@pytest.mark.asyncio
async def test_a_disputed_fact_is_returned_when_it_is_the_only_match(session):
    """The single-row case a set-comparison test can pass by accident."""
    disputed = await _open_fact(session)
    await _set_status(session, disputed["id"], "disputed", review_state="open")

    rows = (await FactsChannel(session).search_with_trace(RARE_TERM, project=PROJECT)).results

    assert _ids(rows) == {disputed["id"]}


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "status", ["candidate", "corroborated", "disputed", "confirmed"],
)
async def test_no_verification_status_is_filtered_out(session, status):
    """The CHECK's whole vocabulary survives the channel. Cold-start serves
    labelled candidates (doc 07 §5), so even the bottom rung is served."""
    fact = await _open_fact(session)
    await _set_status(session, fact["id"], status)

    (row,) = (await FactsChannel(session).search_with_trace(RARE_TERM, project=PROJECT)).results

    assert row["verification_status"] == status


_SCAN_TOKENS = (
    "contradiction_veto",
    "adjudicate_contradiction",
    "detect_open_contradiction",
    "ContradictionFinding",
)


def _executable_source(source: str) -> str:
    """``source`` with every docstring dropped and every comment gone.

    Scanning raw text would flag the prose *explaining* why the channel does not
    reach the scan, which is the fastest way to get a guard deleted as noise.
    ``ast.unparse`` drops comments for free; docstrings have to be popped.
    """
    tree = ast.parse(source)
    for node in ast.walk(tree):
        body = getattr(node, "body", None)
        if not isinstance(body, list) or not body:
            continue
        first = body[0]
        if (
            isinstance(first, ast.Expr)
            and isinstance(first.value, ast.Constant)
            and isinstance(first.value.value, str)
        ):
            body.pop(0)
    return ast.unparse(tree)


def _scan_references(source: str) -> list[str]:
    return [
        f"{lineno}: {line.strip()}"
        for lineno, line in enumerate(_executable_source(source).splitlines(), 1)
        if any(token in line for token in _SCAN_TOKENS)
    ]


def test_the_channel_never_reaches_the_contradiction_scan():
    """Invariant 15's neighbour: the deterministic scan's sole legitimate
    caller is the verification ladder, and the veto's own suite fails the build
    on a second entry point. Re-deriving the counterpart here is forbidden by
    construction, not merely out of scope."""
    hits = _scan_references(Path(inspect.getfile(facts_channel)).read_text())

    assert not hits, (
        "the facts channel reached for the contradiction scan:\n" + "\n".join(hits)
    )


def test_the_scan_guard_rejects_a_synthesised_re_derivation():
    """In-suite negative control — the guard's teeth, proven every run."""
    smuggled = (
        "from app.services.contradiction_veto import detect_open_contradiction\n"
        "async def label(session, fact_id):\n"
        '    """No re-derivation here at all, honest."""\n'
        "    return await detect_open_contradiction(session, fact_id)\n"
    )

    assert _scan_references(smuggled)


# ── keyword-only, and the trace says so ──────────────────────────────


@pytest.mark.asyncio
async def test_the_trace_reports_the_channel_as_keyword_only(session):
    await _open_fact(session)

    trace = await FactsChannel(session).search_with_trace(RARE_TERM, project=PROJECT)

    assert trace.modalities == (KEYWORD_ARM, NAME_ARM)
    assert SEMANTIC_ARM not in trace.modalities
    assert trace.semantic_deferred_to == SEMANTIC_ARM_OWNER


@pytest.mark.asyncio
async def test_the_semantic_arm_is_reported_present_and_not_run(session):
    """Dropping the key is the silent gap doc 07 §2 forbids; marking it failed
    would put a deferred writer into the envelope's ``partial`` flag."""
    await _open_fact(session)

    status = (
        await FactsChannel(session).search_with_trace(RARE_TERM, project=PROJECT)
    ).channel_status()

    assert SEMANTIC_ARM in status
    assert status[SEMANTIC_ARM].ran is False
    assert status[SEMANTIC_ARM].failed is False
    assert status[KEYWORD_ARM].ran is True
    assert status[NAME_ARM].ran is True


@pytest.mark.asyncio
async def test_the_trace_carries_each_arms_contribution(session):
    fact = await _open_fact(session, subject="darkmem", obj="postgres")

    trace = await FactsChannel(session).search_with_trace("postgres", project=PROJECT)

    assert trace.arm_scores[fact["id"]].keys() == {KEYWORD_ARM, NAME_ARM}


# ── the honest-partial-results contract ──────────────────────────────


class _Boom(RuntimeError):
    pass


def _break(channel: FactsChannel, arm: str) -> None:
    def explode(*args, **kwargs):
        raise _Boom(arm)

    setattr(channel, arm, explode)


@pytest.mark.asyncio
async def test_one_arm_down_degrades_to_the_other(session):
    fact = await _open_fact(session)
    channel = FactsChannel(session)
    _break(channel, "keyword_query")

    trace = await channel.search_with_trace("darkmem", project=PROJECT)

    assert _ids(trace.results) == {fact["id"]}
    assert trace.keyword_failed is True
    assert trace.name_failed is False


@pytest.mark.asyncio
async def test_the_surviving_arm_alone_still_serves_rows(session):
    fact = await _open_fact(session)
    channel = FactsChannel(session)
    _break(channel, "name_query")

    trace = await channel.search_with_trace(RARE_TERM, project=PROJECT)

    assert _ids(trace.results) == {fact["id"]}
    assert trace.name_failed is True


@pytest.mark.asyncio
async def test_a_both_sided_failure_raises_rather_than_returning_empty(session):
    """An empty list is indistinguishable from a genuine no-match, which is
    exactly why the outage has to be loud (invariant 14)."""
    await _open_fact(session)
    channel = FactsChannel(session)
    _break(channel, "keyword_query")
    _break(channel, "name_query")

    with pytest.raises(RuntimeError, match="both the keyword and name arms"):
        await channel.search_with_trace(RARE_TERM, project=PROJECT)


@pytest.mark.asyncio
async def test_a_genuine_no_match_is_an_empty_list_not_a_raise(session):
    """The other half of the contract: silence is only wrong when it hides an
    outage."""
    await _open_fact(session)

    trace = await FactsChannel(session).search_with_trace("nothingmatchesthis", project=PROJECT)
    assert trace.results == []


# ── the same contract under a *database-level* failure (T2.66) ───────
#
# The section above breaks an arm in Python, before any SQL is sent. That
# leaves the transaction usable, so those tests pass whether or not the arms
# are isolated from each other — they cannot see the failure the per-arm
# savepoints exist for. A database error aborts the whole transaction, so
# without a savepoint the *next* arm's own valid SQL fails on the aborted
# transaction and a one-sided outage is reported as a both-sided one, naming
# an arm that never independently failed. Nothing below patches the channel:
# each arm is broken in the database.

# Both poisons work by overflowing `plainto_tsquery` past the server's
# `max_stack_depth`, which is the container's 2048kB default. A server
# configured with a much larger stack could parse them instead, and the arm
# under test would then succeed rather than fail.

# 'english' drops stopwords before the tsquery is built, so this overflows
# the name arm's 'simple' tsquery while the keyword arm still resolves to the
# single term that matches the seeded fact.
_NAME_ARM_POISON = "zarquon " + "the of and is a an " * 20_000

# No configuration drops these, so both arms' tsqueries overflow.
_BOTH_ARMS_POISON = "alpha beta gamma " * 20_000

_ARM_FAILURE_LOG = "app.services.facts_channel"


def _the_arm_failure(caplog, arm: str) -> str:
    (message,) = [
        record.getMessage()
        for record in caplog.records
        if record.getMessage().startswith(f"Facts {arm} arm failed:")
    ]
    return message


@contextlib.asynccontextmanager
async def _the_keyword_arms_column_retyped(session, channel: FactsChannel):
    """Make ``to_tsvector('english', fact)`` stop type-checking.

    Every column both arms select stays valid and the name arm's own
    expression reads different columns, so the break is one-sided and it
    lands inside the database rather than in front of it.

    Two cached name-arm plans have to be dealt with and they are *different*
    plans. asyncpg caches prepared statements per connection and that cache is
    not transactional, so neither the DDL nor the fixture's rollback empties
    it:

    * The plan cached against the pre-DDL schema, which the DDL invalidates.
      The suppressed execution below spends that invalidation, so the name arm
      fails on the poison under test rather than on a stale plan the channel
      never caused.
    * The plan that same execution then caches against the *altered* schema.
      The fixture's rollback restores ``fact text`` and leaves that one stale
      on a connection about to go back to the pool, where it would fire in
      whichever later test reaches the name arm first — a failure visible only
      in full-file runs. So the connection is invalidated on the way out and
      discarded instead of pooled.
    """
    await session.execute(
        text("ALTER TABLE knowledge_triples DROP COLUMN fact, ADD COLUMN fact bytea")
    )
    sql, params = channel.name_query(RARE_TERM, PROJECT, 1)
    with contextlib.suppress(DBAPIError):
        async with session.begin_nested():
            await session.execute(text(sql), params)
    try:
        yield
    finally:
        await (await session.connection()).invalidate()


async def _assert_the_session_survived(session) -> None:
    assert (await session.execute(text("SELECT 1"))).scalar() == 1


@pytest.mark.asyncio
async def test_a_database_level_keyword_failure_degrades_to_the_name_arm(session):
    fact = await _open_fact(session)
    channel = FactsChannel(session)

    async with _the_keyword_arms_column_retyped(session, channel):
        trace = await channel.search_with_trace("darkmem", project=PROJECT)

        assert trace.keyword_failed is True
        assert trace.name_failed is False
        assert _ids(trace.results) == {fact["id"]}
        await _assert_the_session_survived(session)


@pytest.mark.asyncio
async def test_a_database_level_name_failure_leaves_the_session_usable(session, caplog):
    """The arm that fails last poisons nothing the caller still needs.

    Its failure is the last thing the channel does, so no sibling arm can
    observe it — only the caller can, and it holds the request transaction.

    The logged cause is asserted, not just the failed flag: any server-side
    error aborts the transaction and would satisfy the flag, so a poison
    leaked in from an earlier test would let this pass while testing
    something else. Pinning the mechanism makes the verdict independent of
    what ran before.
    """
    fact = await _open_fact(session)

    with caplog.at_level(logging.ERROR, logger=_ARM_FAILURE_LOG):
        trace = await FactsChannel(session).search_with_trace(
            _NAME_ARM_POISON, project=PROJECT,
        )

    assert trace.name_failed is True
    assert trace.keyword_failed is False
    assert _ids(trace.results) == {fact["id"]}
    await _assert_the_session_survived(session)

    failure = _the_arm_failure(caplog, NAME_ARM)
    assert "stack depth limit exceeded" in failure
    assert "InvalidCachedStatementError" not in failure


@pytest.mark.asyncio
async def test_a_both_sided_database_failure_raises_rather_than_returning_empty(session):
    """Invariant 14 does not soften because the failure was a real one."""
    await _open_fact(session)

    with pytest.raises(RuntimeError, match="both the keyword and name arms"):
        (await FactsChannel(session).search_with_trace(_BOTH_ARMS_POISON, project=PROJECT)).results

    await _assert_the_session_survived(session)


# ── intra-channel fusion ─────────────────────────────────────────────


@pytest.mark.asyncio
async def test_rows_carry_rrf_score_as_the_ordering_signal(session):
    await _open_fact(session)

    (row,) = (await FactsChannel(session).search_with_trace(RARE_TERM, project=PROJECT)).results

    assert row["rrf_score"] > 0


@pytest.mark.asyncio
async def test_a_name_only_match_carries_rank_mass(session):
    """The name arm's fusion weight is observable. Zeroing it leaves a
    name-only match present but scored 0.0 and sorted last, which is a
    silent reduction to keyword-ranked-only that a presence assertion
    cannot see."""
    seeded = await _open_fact(session, subject="darkmem", obj=RARE_TERM,
                              fact="the store is reached over a socket")

    (row,) = (await FactsChannel(session).search_with_trace(RARE_TERM, project=PROJECT)).results

    assert row["fact_id"] == seeded["id"]
    assert row["rrf_score"] > 0


@pytest.mark.asyncio
async def test_a_fact_both_arms_find_outranks_one_only_one_arm_finds(session):
    both = await _open_fact(session, subject="darkmem", obj="postgres",
                            fact="darkmem uses postgres")
    one = await _open_fact(session, subject="darkmem", obj="redis",
                           fact="darkmem uses postgres for the queue too")

    rows = (await FactsChannel(session).search_with_trace("postgres", project=PROJECT)).results

    assert [row["fact_id"] for row in rows][0] == both["id"]
    assert one["id"] in _ids(rows)


@pytest.mark.asyncio
async def test_each_arm_fetches_past_the_limit_so_the_fuse_can_reorder(session):
    """A fact sitting just past the cut in *both* arms carries more RRF mass
    than one leading a single arm. Fetching exactly the limit would lose it
    outright, which is a recall loss rather than a reordering."""
    channel = FactsChannel(session)
    seen: list[int] = []
    original = channel.keyword_query

    def spy(query, project, limit):
        seen.append(limit)
        return original(query, project, limit)

    channel.keyword_query = spy
    await channel.search_with_trace(RARE_TERM, project=PROJECT, limit=7)

    assert seen == [7 * ARM_FETCH_MULTIPLIER]


@pytest.mark.asyncio
async def test_the_limit_bounds_the_result(session):
    for i in range(5):
        await _open_fact(session, obj=f"store{i}")

    rows = (await FactsChannel(session).search_with_trace(RARE_TERM, project=PROJECT, limit=2)).results

    assert len(rows) == 2


# ── index plans, read out of EXPLAIN ─────────────────────────────────
#
# `enable_seqscan` is forced off for the same reason the keyword/graph pushdown
# suite does it: what is under test is that the query SHAPE is index-eligible
# — predicate columns and expression form — not that the planner picks the
# index at every row count.


async def _seed_bulk_facts(session, rows: int = 4000) -> None:
    await session.execute(
        text(
            "INSERT INTO knowledge_triples "
            "(id, subject_name, object_name, rel_type, reference_time, fact, "
            " project, triple_key) "
            "SELECT gen_random_uuid(), 'filler' || i, 'store' || i, 'USES', "
            "now(), 'filler fact number ' || i, "
            "CASE WHEN i % 3 = 0 THEN :other ELSE :project END, "
            "'key-' || i FROM generate_series(1, :n) i"
        ),
        {"n": rows, "project": PROJECT, "other": OTHER_PROJECT},
    )


async def _settle_statistics(session) -> None:
    """A GIN index buffers fresh entries in a pending list and the planner
    charges a scan for the whole of it, so a bulk insert makes both FTS indexes
    look arbitrarily expensive until the list is flushed."""
    for index in ("ix_knowledge_triples_fact_fts", "ix_knowledge_triples_name_fts"):
        await session.execute(text(f"SELECT gin_clean_pending_list('{index}')"))
    await session.execute(text("ANALYZE knowledge_triples"))


async def _plan(session, sql: str, params: dict) -> str:
    await session.execute(text("SET LOCAL enable_seqscan = off"))
    rows = await session.execute(text(f"EXPLAIN {sql}"), params)
    return "\n".join(r[0] for r in rows)


@pytest.mark.asyncio
async def test_the_keyword_arm_can_use_the_fact_fts_index(session):
    await _seed_bulk_facts(session)
    await _open_fact(session)
    await _settle_statistics(session)

    sql, params = FactsChannel(session).keyword_query(RARE_TERM, PROJECT, 20)
    plan = await _plan(session, sql, params)

    assert "ix_knowledge_triples_fact_fts" in plan, plan
    assert "Seq Scan on knowledge_triples" not in plan, plan


@pytest.mark.asyncio
async def test_the_name_arm_can_use_the_name_fts_index(session):
    await _seed_bulk_facts(session)
    await _open_fact(session, subject="quenelle")
    await _settle_statistics(session)

    sql, params = FactsChannel(session).name_query("quenelle", PROJECT, 20)
    plan = await _plan(session, sql, params)

    assert "ix_knowledge_triples_name_fts" in plan, plan
    assert "Seq Scan on knowledge_triples" not in plan, plan


@pytest.mark.asyncio
async def test_the_scope_alone_can_use_the_open_belief_project_index(session):
    """Without a search term the scope must still be sargable — the
    direct-scan side of the same pushdown."""
    await _seed_bulk_facts(session)
    await session.execute(text("ANALYZE knowledge_triples"))

    plan = await _plan(
        session,
        "SELECT id FROM knowledge_triples "
        f"WHERE project = CAST(:project AS text) AND {OPEN_BELIEF_PREDICATE} LIMIT 20",
        {"project": PROJECT},
    )

    assert "ix_knowledge_triples_project_open" in plan, plan
    assert "Seq Scan on knowledge_triples" not in plan, plan


@pytest.mark.asyncio
async def test_widening_the_belief_predicate_loses_every_partial_index(session):
    """The plan-level statement of the same trap the behaviour tests cover: a
    query that asks only for ``LIVE_PREDICATE`` no longer implies the partial
    indexes' own predicate, so it leaves their scope as well as returning
    history."""
    await _seed_bulk_facts(session)
    await _settle_statistics(session)

    plan = await _plan(
        session,
        "SELECT id FROM knowledge_triples "
        f"WHERE project = CAST(:project AS text) AND {LIVE_PREDICATE} LIMIT 20",
        {"project": PROJECT},
    )

    assert "ix_knowledge_triples_project_open" not in plan, plan


# ── T2.84: the fact-keyed retrieval-heat counter ────────────────────────
#
# T2.65 measured that this channel called nothing analogous to
# ``access_stats.spawn_record_access``, so a served fact never touched any
# heat counter. T2.84 wires ``fact_access_stats.spawn_record_access`` into
# both public methods, off the hot path, matching ``HybridSearchService``'s
# own idiom (``test_access_stats.py``'s "off-the-hot-path proof" section,
# which these tests mirror).


class _FakeAsyncCtx:
    """A no-op ``async with ... as session`` stand-in, so the real
    ``spawn_record_access`` -> ``async with factory() as session`` shape
    runs without touching the app's real database."""

    async def __aenter__(self):
        return None

    async def __aexit__(self, *exc):
        return False


async def _drain_fact_heat_tasks() -> None:
    pending = [
        t for t in background._background_tasks if t.get_name() == "fact-access-stats-bump"
    ]
    while pending:
        await asyncio.wait_for(asyncio.gather(*pending, return_exceptions=True), timeout=5)
        pending = [
            t for t in background._background_tasks if t.get_name() == "fact-access-stats-bump"
        ]


@pytest.mark.asyncio
@pytest.mark.parametrize("method_name", ["search_with_trace"])
async def test_a_served_fact_schedules_its_heat_write_without_awaiting_it(
    session, monkeypatch, method_name,
):
    """The off-hot-path proof, on the channel's public method."""
    fact_id = (await _open_fact(session, subject="heat-scheduling"))["id"]
    await session.commit()

    calls: list[list[str]] = []

    async def fake_flush_counts(_session, counts):
        calls.append(sorted(counts.keys()))

    monkeypatch.setattr(fact_access_stats, "_flush_counts", fake_flush_counts)
    monkeypatch.setattr(fact_access_stats, "async_session_factory", lambda: _FakeAsyncCtx())
    monkeypatch.setattr(fact_access_stats, "_FLUSH_DELAY_SECONDS", 0.01)

    channel = FactsChannel(session)
    method = getattr(channel, method_name)
    result = await method("heat-scheduling", project=PROJECT, limit=5)
    served = result.results if method_name == "search_with_trace" else result
    assert any(row["fact_id"] == fact_id for row in served)

    # Scheduled, not awaited: asyncio never runs a task created via
    # create_task before the creating coroutine yields, and the method
    # returns with no further await after scheduling it.
    pending = [
        t for t in background._background_tasks if t.get_name() == "fact-access-stats-bump"
    ]
    assert len(pending) == 1, "expected exactly one scheduled fact-access-stats task"
    assert calls == [], "the write must not have run before the method returned"

    await pending[0]
    assert calls == [[fact_id]]


@pytest.mark.asyncio
@pytest.mark.parametrize("method_name", ["search_with_trace"])
async def test_a_heat_write_failure_never_reaches_the_caller(session, monkeypatch, method_name):
    """The clause every counter in this corpus repeats: a counting failure
    degrades to "this search's heat is lost", never to "this search failed".
    Proven by making the write raise and asserting the channel's own results
    are untouched — this is the failure mode a caller of ``FactsChannel``
    (and, through it, ``knowledge_search``) actually experiences if
    ``fact_access_stats`` is ever unreachable."""
    fact_id = (await _open_fact(session, subject="heat-failure"))["id"]
    await session.commit()

    async def boom(_session, _counts):
        raise RuntimeError("simulated fact-heat write failure")

    monkeypatch.setattr(fact_access_stats, "_flush_counts", boom)
    monkeypatch.setattr(fact_access_stats, "async_session_factory", lambda: _FakeAsyncCtx())
    monkeypatch.setattr(fact_access_stats, "_FLUSH_DELAY_SECONDS", 0.01)

    channel = FactsChannel(session)
    method = getattr(channel, method_name)
    result = await method("heat-failure", project=PROJECT, limit=5)
    served = result.results if method_name == "search_with_trace" else result
    assert any(row["fact_id"] == fact_id for row in served), (
        "the channel's own results must be intact even though the counter write will raise"
    )

    # Let the failing write run to completion; spawn_record_access's own
    # try/except must swallow it -- a raised task shows up only as a logged
    # "Background task failed" error, never as an exception surfacing here.
    await _drain_fact_heat_tasks()


@pytest.mark.asyncio
@pytest.mark.parametrize("method_name", ["search_with_trace"])
async def test_fifty_real_searches_actually_write_the_direct_counter(
    monkeypatch, method_name,
):
    """The end-to-end proof behind T2.84's Done-when: real
    SQL, not a fake flush, and the real (default) ``async_session_factory``
    -- not the transactional ``session`` fixture, whose writes live inside a
    SAVEPOINT one connection deep and are invisible to the background
    flush's genuinely separate connection (the same constraint
    ``test_access_stats.py`` documents for its own SQL-correctness tests).
    ``conftest.py`` pins ``DATABASE_URL`` to ``TEST_DATABASE_URL`` before any
    app module is imported, so the default factory already targets this
    suite's database -- no monkeypatch needed for it, only for speed."""
    factory = async_sessionmaker(test_engine, expire_on_commit=False)
    async with factory() as setup:
        repo = KnowledgeTripleRepository(setup)
        fact = await repo.insert_open(
            triple_key=compute_triple_key(PROJECT, "zarquon-heat", "USES", "postgres"),
            subject_name="zarquon-heat",
            object_name="postgres",
            rel_type="USES",
            fact=f"zarquon-heat USES postgres {RARE_TERM}",
            reference_time=NOW,
            project=PROJECT,
        )
        await setup.commit()
    fact_id = fact["id"]

    monkeypatch.setattr(fact_access_stats, "_FLUSH_DELAY_SECONDS", 0.01)
    try:
        async with factory() as channel_session:
            channel = FactsChannel(channel_session)
            method = getattr(channel, method_name)
            for _ in range(50):
                result = await method("zarquon-heat", project=PROJECT, limit=5)
                served = result.results if method_name == "search_with_trace" else result
                assert any(row["fact_id"] == fact_id for row in served)

        await _drain_fact_heat_tasks()

        async with factory() as check:
            row = (
                await check.execute(
                    text(
                        "SELECT access_count FROM fact_access_stats "
                        "WHERE fact_id = CAST(:id AS uuid)"
                    ),
                    {"id": fact_id},
                )
            ).mappings().one()
            assert row["access_count"] == 50
    finally:
        async with factory() as cleanup:
            await cleanup.execute(
                text("DELETE FROM knowledge_triples WHERE id = CAST(:id AS uuid)"),
                {"id": fact_id},
            )
            await cleanup.commit()
