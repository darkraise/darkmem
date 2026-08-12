"""T2.11 — the Tier-C model contradiction scan (doc 08 §5.3, feeding §4.2).

Organised by the Done-when clause each group discharges:

* G1  the generator is **combined** — both arms, and the union is neither alone
* G2  adjudication has exactly one door, and it is the qualified judge
* G3  misses are counted, never hidden
* G4  a verdict reaches the veto, and stops reaching it when it should
* Inv the scan never writes a status, and never feeds its own input

**Every test here runs against a judge that refuses**, because no qualification
record exists on this branch and `VerificationJudge.judge` raises without one.
The three tests that need adjudication to actually happen take the
``qualified_judge_record`` fixture explicitly. It is **not autouse** on purpose:
an autouse version would open the gate for the whole module and the refusal
path — the property that makes this job safe to ship inert — would be untested
everywhere at once.
"""

from __future__ import annotations

import ast
import inspect
import json
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy import text

from app.models.config import Config
from app.repositories.fact_sources import FactSourceRepository
from app.repositories.knowledge_triples import KnowledgeTripleRepository
from app.services import contradiction_scan as scan_module
from app.services import verification_judge as vj
from app.services.contradiction_scan import (
    ARM_SAME_ENDPOINT,
    ARM_TRIGRAM,
    CONTRADICTED_VERDICT,
    generate_candidates,
    run_contradiction_scan,
)
from app.services.contradiction_veto import (
    RULE_SCANNED,
    detect_scanned_contradiction,
    windows_overlap,
)
from app.services.events import CONTRADICTION_SCANNED, record_event
from app.services.verification_judge import JUDGE_VERDICTS
from app.services.verification_ladder import recompute_fact

BACKEND = Path(__file__).resolve().parent.parent

# Fixed absolute timestamps, as in the veto suite: nothing derives from
# datetime.now(), so a window fixture cannot rot as the wall clock moves.
T0 = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
YEAR = timedelta(days=365)

PROJECT = "t2-11-scan"


# ─────────────────────────────── fixtures ───────────────────────────────


class StubLLM:
    """Records every dispatch and replays canned responses in order.

    ``responses`` may hold an exception instance, which is raised instead of
    returned — that is how a provider failure is exercised without reaching a
    network.
    """

    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []
        self.config = _judge_config()

    async def chat_completion(self, purpose, messages, response_format=None, seed=None):
        self.calls.append({"purpose": purpose, "messages": messages})
        answer = self.responses.pop(0) if self.responses else _verdict("unsupported")
        if isinstance(answer, Exception):
            raise answer
        return answer


def _judge_config(**overrides):
    from app.config import LLMPurposeConfig

    fields = {
        "model": "deepseek-v4-flash",
        "base_url": "https://api.deepseek.com/v1",
        "api_key": "sk-test",
        "api_kind": "deepseek",
        "params": {"temperature": 0},
    }
    fields.update(overrides)
    return {"verification": LLMPurposeConfig(**fields)}


def _verdict(name: str, reason: str = "because") -> str:
    return json.dumps({"verdict": name, "reason": reason})


@pytest_asyncio.fixture
async def qualified_judge_record(session, tmp_path, monkeypatch):
    """Mint a record that qualifies the judge for one test.

    **Opt-in, never autouse.** The judge refuses unconditionally while no
    canonical record exists, and that refusal is the property that lets this
    job ship before the qualification run happens. A fixture that opened the
    gate for the module would leave the refusal path unexercised everywhere at
    once, which is exactly the trap this epic has already been bitten by.

    It writes a ``contradiction_recall_bar`` config row because T2.109 barred
    that metric with no default: the fixture has to state the bar for the same
    reason a deployment does, and a test that qualified without one would be
    exercising a gate no operator can reach.

    Since the 2026-08-12 split it mints the **contradiction** role's record —
    the only one that can open this consumer's door, and the one that is
    unqualified in production and stays so.
    """
    identity = vj.judge_identity(_judge_config()["verification"])
    record = tmp_path / f"verification_qualification.{vj.CONTRADICTION_ROLE}.json"
    record.write_text(json.dumps({
        "role": vj.CONTRADICTION_ROLE,
        "judge_identity": {
            **identity,
            "identity_hash": vj.judge_identity_hash(identity),
        },
        "metrics": {
            "entailed_precision": 1.0,
            "entailed_recall": 1.0,
            "contradiction_precision": 1.0,
            "contradiction_recall": 1.0,
        },
        "gate_eligible": True,
        "gold_pairs_sha256": "f" * 64,
        "recorded_at": "2026-08-06T00:00:00+00:00",
    }), encoding="utf-8")
    monkeypatch.setitem(
        vj.QUALIFICATION_RECORD_PATHS, vj.CONTRADICTION_ROLE, record,
    )
    session.add(Config(key="contradiction_recall_bar", value={"value": 0.9}))
    await session.commit()
    return record


def _factory(session):
    """A session factory that hands back the test's own session.

    The scan opens and commits its own sessions; a real factory would write
    outside the fixture's transaction and leak rows between tests.
    """
    @asynccontextmanager
    async def ctx():
        yield session

    return ctx


async def _fact(
    session,
    *,
    subject: str,
    obj: str,
    rel: str = "USES",
    fact: str | None = None,
    project: str = PROJECT,
    valid_at: datetime | None = None,
    invalid_at: datetime | None = None,
    status: str | None = None,
    expired: bool = False,
) -> str:
    repo = KnowledgeTripleRepository(session)
    row = await repo.insert_open(
        triple_key=f"k-{uuid4()}",
        subject_name=subject,
        object_name=obj,
        rel_type=rel,
        fact=fact if fact is not None else f"{subject} {rel} {obj}",
        reference_time=T0,
        project=project,
        valid_at=valid_at,
    )
    if invalid_at is not None:
        await repo.close_window(row["id"], invalid_at)
    if status is not None:
        await repo.set_verification_status(row["id"], status)
    if expired:
        await repo.expire(row["id"])
    await session.commit()
    return row["id"]


async def _source(session, fact_id, origin_key, *, kind="memory") -> None:
    await FactSourceRepository(session).add_source(
        fact_id=fact_id,
        source_kind=kind,
        source_ref=f"{kind}:{origin_key}:{uuid4()}",
        origin_key=origin_key,
    )
    await session.commit()


async def _verification(session, fact_id) -> dict:
    row = await session.execute(
        text(
            "SELECT verification_status, review_state FROM knowledge_triples "
            "WHERE id = CAST(:id AS uuid)"
        ),
        {"id": str(fact_id)},
    )
    return dict(row.mappings().one())


async def _enqueue(session, fact_id) -> None:
    await record_event(
        session,
        event_type="sources_changed",
        object_type="fact",
        object_id=fact_id,
        project=PROJECT,
        payload={"fact_id": str(fact_id)},
    )
    await session.commit()


async def _row(session, fact_id) -> dict:
    result = await session.execute(
        text(
            "SELECT id, project, subject_name, rel_type, object_name, fact, "
            "valid_at, invalid_at FROM knowledge_triples "
            "WHERE id = CAST(:id AS uuid)"
        ),
        {"id": str(fact_id)},
    )
    return dict(result.mappings().one())


async def _scan_verdicts(session, fact_id) -> list[dict]:
    result = await session.execute(
        text(
            "SELECT payload FROM events WHERE object_type = 'fact' "
            "AND event_type = CAST(:kind AS text) "
            "AND object_id = CAST(:id AS uuid) ORDER BY created_at, id"
        ),
        {"id": str(fact_id), "kind": CONTRADICTION_SCANNED},
    )
    return [row[0] for row in result.all()]


def _later() -> datetime:
    """A ``now`` past the drain's commit-skew margin.

    The drain refuses to read an event newer than ``now - 5s`` so a watermark
    can never pass an in-flight producer. A test writes its events milliseconds
    before scanning, so it must supply a ``now`` from the other side of that
    margin rather than sleep through it.
    """
    return datetime.now(timezone.utc) + timedelta(minutes=1)


async def _run(session, llm, **kwargs):
    return await run_contradiction_scan(
        _factory(session), lambda: llm, now=_later(), **kwargs
    )


# ══════════ G1 — the generator is combined, and the union is neither arm ══════


class TestTheCombinedGenerator:
    async def test_the_same_endpoint_arm_finds_a_structural_neighbour(self, session):
        """Shares an endpoint; shares no vocabulary with the subject's text."""
        subject = await _fact(
            session, subject="darkmem", obj="postgres",
            fact="darkmem stores its vault in postgres",
        )
        neighbour = await _fact(
            session, subject="darkmem", obj="mysql",
            fact="zzz qqq vvv xxx yyy wwww",
        )
        pool = await generate_candidates(session, await _row(session, subject), top_k=10)
        found = {c.fact_id: c.arms for c in pool.candidates}
        assert found[str(neighbour)] == (ARM_SAME_ENDPOINT,)

    async def test_the_trigram_arm_finds_a_lexical_neighbour(self, session):
        """Shares neither endpoint; the trigram arm is the only way in.

        This is the half a same-endpoint-only generator cannot see at all: two
        claims about the same thing whose endpoints were canonicalised into
        different names.
        """
        subject = await _fact(
            session, subject="darkmem", obj="postgres",
            fact="the darkmem vault is stored in postgres",
        )
        lexical = await _fact(
            session, subject="dark-mem", obj="postgresql",
            fact="the darkmem vault is stored in postgresql",
        )
        pool = await generate_candidates(session, await _row(session, subject), top_k=10)
        found = {c.fact_id: c.arms for c in pool.candidates}
        assert found[str(lexical)] == (ARM_TRIGRAM,)

    async def test_the_union_is_larger_than_either_arm_alone(self, session):
        """The Done-when's own wording: a pool that happens to come entirely
        from one arm does not exercise the other."""
        subject = await _fact(
            session, subject="darkmem", obj="postgres",
            fact="the darkmem vault is stored in postgres",
        )
        structural = await _fact(
            session, subject="darkmem", obj="mysql",
            fact="zzz qqq vvv xxx yyy wwww",
        )
        lexical = await _fact(
            session, subject="dark-mem", obj="postgresql",
            fact="the darkmem vault is stored in postgresql",
        )
        pool = await generate_candidates(session, await _row(session, subject), top_k=10)
        by_arm = {
            arm: {c.fact_id for c in pool.candidates if arm in c.arms}
            for arm in (ARM_SAME_ENDPOINT, ARM_TRIGRAM)
        }
        whole = {c.fact_id for c in pool.candidates}
        assert str(structural) in by_arm[ARM_SAME_ENDPOINT]
        assert str(lexical) in by_arm[ARM_TRIGRAM]
        assert by_arm[ARM_SAME_ENDPOINT] != whole
        assert by_arm[ARM_TRIGRAM] != whole

    async def test_a_candidate_both_arms_reach_keeps_both_names(self, session):
        subject = await _fact(
            session, subject="darkmem", obj="postgres",
            fact="the darkmem vault is stored in postgres",
        )
        both = await _fact(
            session, subject="darkmem", obj="mysql",
            fact="the darkmem vault is stored in postgres now",
        )
        pool = await generate_candidates(session, await _row(session, subject), top_k=10)
        arms = {c.fact_id: c.arms for c in pool.candidates}[str(both)]
        assert set(arms) == {ARM_SAME_ENDPOINT, ARM_TRIGRAM}

    async def test_the_cap_never_starves_the_trigram_arm(self, session):
        """The mutant this kills: concatenate-then-cap.

        With more same-endpoint neighbours than the cap allows, a generator
        that appended the second arm after the first would return an
        all-structural pool and degrade to half of itself with nothing
        reporting it. The interleave is what keeps the lexical arm represented.
        """
        subject = await _fact(
            session, subject="darkmem", obj="postgres",
            fact="the darkmem vault is stored in postgres",
        )
        for index in range(6):
            await _fact(
                session, subject="darkmem", obj=f"store-{index}",
                fact=f"zzz qqq vvv {index} xxx yyy",
            )
        lexical = await _fact(
            session, subject="dark-mem", obj="postgresql",
            fact="the darkmem vault is stored in postgresql",
        )
        pool = await generate_candidates(session, await _row(session, subject), top_k=3)
        assert len(pool.candidates) == 3
        assert str(lexical) in {c.fact_id for c in pool.candidates}
        assert pool.truncated > 0

    async def test_a_disjoint_window_is_never_generated(self, session):
        """Succession, not contradiction (doc 08 §3.1). Filtered in SQL so the
        pair is never transported, let alone judged."""
        subject = await _fact(
            session, subject="darkmem", obj="postgres",
            fact="darkmem stores its vault in postgres",
            valid_at=T0 + YEAR,
        )
        await _fact(
            session, subject="darkmem", obj="mysql",
            fact="darkmem stores its vault in mysql",
            valid_at=T0, invalid_at=T0 + YEAR,
        )
        pool = await generate_candidates(session, await _row(session, subject), top_k=10)
        assert pool.candidates == ()

    async def test_an_overlapping_window_survives(self, session):
        subject = await _fact(
            session, subject="darkmem", obj="postgres",
            fact="darkmem stores its vault in postgres",
            valid_at=T0,
        )
        overlapping = await _fact(
            session, subject="darkmem", obj="mysql",
            fact="darkmem stores its vault in mysql",
            valid_at=T0 + YEAR,
        )
        pool = await generate_candidates(session, await _row(session, subject), top_k=10)
        assert {c.fact_id for c in pool.candidates} == {str(overlapping)}

    @pytest.mark.parametrize("a_valid", [None, T0, T0 + YEAR])
    @pytest.mark.parametrize("a_invalid", [None, T0 + YEAR, T0 + 2 * YEAR])
    @pytest.mark.parametrize("b_valid", [None, T0, T0 + YEAR])
    @pytest.mark.parametrize("b_invalid", [None, T0 + YEAR, T0 + 2 * YEAR])
    async def test_the_sql_overlap_predicate_matches_windows_overlap(
        self, session, a_valid, a_invalid, b_valid, b_invalid
    ):
        """The generator pushes the overlap filter into SQL, so the predicate
        exists twice — once in Python for the veto's read-back guard, once in
        SQL here. Swept rather than sampled, so the copy cannot drift on a
        corner the author did not think of."""
        if a_invalid is not None and a_valid is not None and a_valid >= a_invalid:
            pytest.skip("not a window")
        if b_invalid is not None and b_valid is not None and b_valid >= b_invalid:
            pytest.skip("not a window")
        subject = await _fact(
            session, subject="alpha", obj="beta", fact="alpha uses beta",
            valid_at=a_valid, invalid_at=a_invalid,
        )
        other = await _fact(
            session, subject="alpha", obj="gamma", fact="alpha uses gamma",
            valid_at=b_valid, invalid_at=b_invalid,
        )
        pool = await generate_candidates(session, await _row(session, subject), top_k=10)
        expected = windows_overlap(a_valid, a_invalid, b_valid, b_invalid)
        assert (str(other) in {c.fact_id for c in pool.candidates}) is expected

    async def test_another_project_is_never_a_candidate(self, session):
        subject = await _fact(
            session, subject="darkmem", obj="postgres",
            fact="darkmem stores its vault in postgres",
        )
        await _fact(
            session, subject="darkmem", obj="mysql",
            fact="darkmem stores its vault in mysql", project="other",
        )
        pool = await generate_candidates(session, await _row(session, subject), top_k=10)
        assert pool.candidates == ()

    async def test_the_trigram_arm_has_an_index_that_can_serve_it(self, session):
        """"Cheap SQL on the one Postgres" is a claim about the schema.

        The `%` operator was chosen over `similarity(...) >= floor` precisely
        because only the operator is indexable, and the index's partial
        predicate has to be the same liveness rule the arm selects on — a
        narrower one (the open-belief predicate the two FTS indexes use) does
        not apply to this arm at all, and the whole thing degrades to a scan of
        the fact layer with every other test in this file still green.

        Asserted against ``pg_indexes`` rather than an ``EXPLAIN`` on purpose:
        on a fixture-sized table every plan costs about the same and the
        planner's pick says nothing about whether the index applies.
        """
        definition = (await session.execute(
            text(
                "SELECT indexdef FROM pg_indexes "
                "WHERE tablename = 'knowledge_triples' "
                "AND indexname = 'ix_knowledge_triples_fact_trgm'"
            )
        )).scalar_one_or_none()
        assert definition is not None, "the trigram shortlist has no index"
        assert "gin (fact gin_trgm_ops)" in definition
        assert "WHERE (expired_at IS NULL)" in definition

    async def test_the_same_endpoint_arm_has_an_index_for_both_halves(self, session):
        """T2.98: each side of the `subject_name = X OR object_name = Y`
        shape needs *some* btree containing its column for a bitmap plan to
        exist at all. Without a leading index on `object_name`, that arm
        does not vanish from the plan — it degrades to a full traversal of
        the *other* index (a boundary-less `Index Cond` scanning every leaf
        page), or, under a skewed value and fresh statistics, the whole
        query falls back to a literal heap Seq Scan. `EXPLAIN` evidence for
        both the win and the degraded fallback (measured on seeded tables at
        realistic scale, not this fixture-sized one) lives in the T2.98
        report and its fix-round-1 report, for the same reason the trigram
        test above gives for asserting via `pg_indexes` here.
        """
        rows = (await session.execute(
            text(
                "SELECT indexname, indexdef FROM pg_indexes "
                "WHERE tablename = 'knowledge_triples' "
                "AND indexname IN ('ix_knowledge_triples_live', "
                "'ix_knowledge_triples_live_object')"
            )
        )).all()
        definitions = {row.indexname: row.indexdef for row in rows}
        assert set(definitions) == {
            "ix_knowledge_triples_live", "ix_knowledge_triples_live_object",
        }
        assert "(subject_name, rel_type, object_name)" in definitions[
            "ix_knowledge_triples_live"
        ]
        assert "(object_name, rel_type, subject_name)" in definitions[
            "ix_knowledge_triples_live_object"
        ]
        for definition in definitions.values():
            assert "WHERE (expired_at IS NULL)" in definition

    async def test_an_expired_fact_is_never_a_candidate(self, session):
        subject = await _fact(
            session, subject="darkmem", obj="postgres",
            fact="darkmem stores its vault in postgres",
        )
        await _fact(
            session, subject="darkmem", obj="mysql",
            fact="darkmem stores its vault in mysql", expired=True,
        )
        pool = await generate_candidates(session, await _row(session, subject), top_k=10)
        assert pool.candidates == ()


# ══════════ G2 — adjudication has exactly one door ═══════════════════════════


def _module_tree() -> ast.Module:
    return ast.parse(Path(inspect.getfile(scan_module)).read_text(encoding="utf-8"))


def _attribute_names(tree: ast.Module) -> list[str]:
    return [n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute)]


class TestOnlyTheQualifiedJudgeAdjudicates:
    def test_the_verdict_event_is_in_the_closed_vocabulary(self):
        """Taxonomy-first, and it needs its own assertion: ``record_event``
        warns on an unknown type and inserts the row anyway, so every
        round-trip test in this file would pass over a value that never
        joined the vocabulary."""
        from app.services.events import EVENT_TYPES, OBJECT_TYPES

        assert CONTRADICTION_SCANNED in EVENT_TYPES
        assert "fact" in OBJECT_TYPES

    def test_the_contradicted_verdict_is_the_judges_own(self):
        """A typo here would read as "no contradiction ever found" and pass
        every happy-path assertion in this file."""
        assert CONTRADICTED_VERDICT in JUDGE_VERDICTS

    def test_the_ungated_probe_is_unreachable(self):
        """Structural, and against the parsed tree rather than the raw text.

        The judge module's own single-door scan matches the module name as
        *text*, so it fires on prose in a comment — a guard written that way
        cannot tell an explanation from a call. This one reads nodes.
        """
        assert "qualification_probe" not in _attribute_names(_module_tree())

    def test_the_only_adjudicating_call_is_the_gated_door(self):
        """Every method this module invokes on its judge, enumerated.

        A second door — a probe, a bare ``chat_completion``, a helper that
        wraps either — would show up here as another attribute call on the
        judge object.
        """
        tree = _module_tree()
        judge_calls = {
            node.func.attr
            for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id == "judge"
        }
        assert judge_calls == {"judge"}

    def test_no_numeric_comparison_can_stand_in_for_a_verdict(self):
        """No local similarity threshold decides anything.

        The trigram floor is real and necessary, but it selects *candidates*.
        A comparison against a number anywhere in this module would be a second
        way to reach a conclusion about a pair, which is what "not a heuristic"
        forbids.
        """
        offenders = [
            ast.unparse(node)
            for node in ast.walk(_module_tree())
            if isinstance(node, ast.Compare)
            for operand in [*node.comparators, node.left]
            if isinstance(operand, ast.Constant)
            and isinstance(operand.value, (int, float))
            and not isinstance(operand.value, bool)
        ]
        assert not offenders, offenders

    def test_the_trigram_floor_never_leaves_the_generator(self):
        """It is a candidate-selection constant; a reference outside the
        generator would be it deciding something else."""
        tree = _module_tree()
        generator = next(
            node for node in ast.walk(tree)
            if isinstance(node, ast.AsyncFunctionDef)
            and node.name == "generate_candidates"
        )
        inside = {id(n) for n in ast.walk(generator)}
        stray = [
            node for node in ast.walk(tree)
            if isinstance(node, ast.Name)
            and node.id == "_TRIGRAM_FLOOR"
            and isinstance(node.ctx, ast.Load)
            and id(node) not in inside
        ]
        assert not stray

    def test_the_scan_never_writes_a_verification_status(self):
        """The scan is an *input* to the veto, never the verdict (doc 08 §4.2).
        The ladder owns every status write, and a second writer would journal
        transitions the recompute cannot reconcile."""
        attrs = set(_attribute_names(_module_tree()))
        assert "set_verification_status" not in attrs
        assert "recompute_fact" not in attrs

    async def test_a_refusing_judge_adjudicates_nothing(self, session):
        """The default state of this branch, and the whole reason the body can
        ship before the qualification run happens."""
        subject = await _fact(
            session, subject="darkmem", obj="postgres",
            fact="darkmem stores its vault in postgres",
        )
        await _source(session, subject, "sess-a")
        counter = await _fact(
            session, subject="darkmem", obj="mysql",
            fact="darkmem stores its vault in mysql",
        )
        await _source(session, counter, "sess-b")
        await _enqueue(session, subject)

        llm = StubLLM([_verdict("contradicted")])
        outcome = await _run(session, llm)

        assert outcome.judge_refused == 1
        assert outcome.disputes_recorded == 0
        assert outcome.facts_checked == 0
        assert llm.calls == [], "the refusal must precede any model dispatch"
        assert await _scan_verdicts(session, subject) == []

    async def test_a_refusal_holds_the_watermark_for_the_next_run(self, session):
        """A refusal is a global precondition failure, not a poisonous row.

        Advancing past the drained events would silently discard a backlog that
        becomes checkable the moment a record is minted — the one failure this
        module declines to skip past.
        """
        subject = await _fact(
            session, subject="darkmem", obj="postgres",
            fact="darkmem stores its vault in postgres",
        )
        await _source(session, subject, "sess-a")
        counter = await _fact(
            session, subject="darkmem", obj="mysql",
            fact="darkmem stores its vault in mysql",
        )
        await _source(session, counter, "sess-b")
        await _enqueue(session, subject)

        first = await _run(session, StubLLM([]))
        assert first.watermark_advanced is False
        second = await _run(session, StubLLM([]))
        assert second.events_scanned == first.events_scanned == 1

    async def test_a_qualified_judge_records_a_dispute(
        self, session, qualified_judge_record
    ):
        subject = await _fact(
            session, subject="darkmem", obj="postgres",
            fact="darkmem stores its vault in postgres",
        )
        await _source(session, subject, "sess-a")
        counter = await _fact(
            session, subject="darkmem", obj="mysql",
            fact="darkmem stores its vault in mysql",
        )
        await _source(session, counter, "sess-b")
        await _enqueue(session, subject)

        llm = StubLLM([_verdict("contradicted", "different exclusive store")])
        outcome = await _run(session, llm)

        assert outcome.disputes_recorded == 1
        assert outcome.watermark_advanced is True
        assert outcome.misses == 0
        payload = (await _scan_verdicts(session, subject))[0]
        assert payload["contradicted"] is True
        assert payload["counterpart_id"] == str(counter)
        assert payload["witness_origin"] == "sess-b"
        assert payload["reason"] == "different exclusive store"

    async def test_an_unsupported_verdict_records_a_clear(
        self, session, qualified_judge_record
    ):
        """Both stores can be true at once; the pair was judged and cleared."""
        subject = await _fact(
            session, subject="darkmem", obj="postgres",
            fact="darkmem stores its vault in postgres",
        )
        await _source(session, subject, "sess-a")
        counter = await _fact(
            session, subject="darkmem", obj="redis",
            fact="darkmem stores its cache in redis",
        )
        await _source(session, counter, "sess-b")
        await _enqueue(session, subject)

        outcome = await _run(session, StubLLM([_verdict("unsupported")]))
        assert (outcome.clears_recorded, outcome.disputes_recorded) == (1, 0)
        assert (await _scan_verdicts(session, subject))[0]["contradicted"] is False

    async def test_an_echo_candidate_is_never_judged(
        self, session, qualified_judge_record
    ):
        """One source restating itself is not testimony (doc 08 §4.2), so the
        pair costs no model call at all."""
        subject = await _fact(
            session, subject="darkmem", obj="postgres",
            fact="darkmem stores its vault in postgres",
        )
        await _source(session, subject, "sess-a")
        counter = await _fact(
            session, subject="darkmem", obj="mysql",
            fact="darkmem stores its vault in mysql",
        )
        await _source(session, counter, "sess-a")
        await _enqueue(session, subject)

        llm = StubLLM([_verdict("contradicted")])
        outcome = await _run(session, llm)
        assert outcome.pairs_echo == 1
        assert outcome.pairs_judged == 0
        assert llm.calls == []
        assert (await _scan_verdicts(session, subject))[0]["contradicted"] is False


# ══════════ G2b — the verdict channel has exactly one writer ═════════════════
#
# The door proofs above pin adjudication inside this module. They stop one hop
# short of the veto, which trusts `payload["contradicted"]` on any row of this
# event type and cannot re-derive it — a verdict is a model's judgement, not a
# guard that can be recomputed from live rows. So the single-door property
# rests on nothing under `app/` but the scan being able to write that row, and
# these scans are what make that structural rather than merely true today. One
# bare `record_event` call from anywhere else would put a fact on a human's
# review queue with no judge in the story at all. That is a smaller harm than
# the `disputed` this used to describe — the rewire (T2.109) is what shrank it
# — and it is still a claim about truth arriving from nowhere, so the door
# stays single.

_VERDICT_EMITTER = "app/services/contradiction_scan.py"

# Where the event type may be *named* at all: the vocabulary that declares it,
# the one module that writes it, the one module that reads it back. Joining
# this set means taking on a share of the channel's integrity — it is not a
# formality, and a raw `INSERT INTO events` is exactly what it exists to catch.
_VERDICT_REFERENCE_ALLOWLIST = {
    "app/services/events.py",
    "app/services/contradiction_scan.py",
    "app/services/contradiction_veto.py",
}

_VERDICT_CONSTANT = "CONTRADICTION_SCANNED"


def _app_sources(root: Path) -> list[Path]:
    return [p for p in (root / "app").rglob("*.py") if "__pycache__" not in str(p)]


def _rel(path: Path, root: Path) -> str:
    return str(path.relative_to(root)).replace("\\", "/")


def _string_bindings(tree: ast.Module) -> dict[str, str]:
    """Module-level names that provably hold a string, resolved one hop.

    Enough to follow the two ways a call site reaches this event type without
    spelling it inline: importing the constant, and rebinding either the
    constant or the literal to a module-level name of its own.
    """
    bindings: dict[str, str] = {}
    for node in tree.body:
        if isinstance(node, ast.ImportFrom) and node.module == "app.services.events":
            for alias in node.names:
                if alias.name == _VERDICT_CONSTANT:
                    bindings[alias.asname or alias.name] = CONTRADICTION_SCANNED
        if not isinstance(node, ast.Assign):
            continue
        value = None
        if isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
            value = node.value.value
        elif isinstance(node.value, ast.Name):
            value = bindings.get(node.value.id)
        elif isinstance(node.value, ast.Attribute):
            value = (
                CONTRADICTION_SCANNED
                if node.value.attr == _VERDICT_CONSTANT else None
            )
        if value is None:
            continue
        for target in node.targets:
            if isinstance(target, ast.Name):
                bindings[target.id] = value
    return bindings


def _names_the_verdict(node: ast.expr, bindings: dict[str, str]) -> bool:
    if isinstance(node, ast.Constant):
        return node.value == CONTRADICTION_SCANNED
    if isinstance(node, ast.Name):
        return bindings.get(node.id) == CONTRADICTION_SCANNED
    if isinstance(node, ast.Attribute):
        return node.attr == _VERDICT_CONSTANT
    return False


def _verdict_emitters(paths: list[Path], root: Path) -> set[str]:
    """Every file holding a ``record_event`` call that journals this verdict.

    Against the parsed tree, and on the keyword rather than the line: the
    argument is keyword-only in ``record_event``'s signature, so there is no
    positional spelling to miss, and a co-occurrence rule over raw text would
    fire on the prose above while missing a call split across lines.
    """
    emitters: set[str] = set()
    for path in paths:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        bindings = _string_bindings(tree)
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            called = func.attr if isinstance(func, ast.Attribute) else getattr(
                func, "id", None
            )
            if called != "record_event":
                continue
            for keyword in node.keywords:
                if keyword.arg == "event_type" and _names_the_verdict(
                    keyword.value, bindings
                ):
                    emitters.add(_rel(path, root))
    return emitters


def _verdict_referrers(paths: list[Path], root: Path) -> set[str]:
    """Every file that names this event type at all, however it spells it.

    The emitter scan resolves names it can follow; this one needs no
    resolution, so it is what closes the routes that scan cannot see — a raw
    ``INSERT INTO events`` carrying the type as SQL text, or a name laundered
    through a caller's argument. Between them a module cannot write this
    channel without either being caught or never mentioning the value it
    writes.
    """
    referrers: set[str] = set()
    for path in paths:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            named = (
                (isinstance(node, ast.Constant) and isinstance(node.value, str)
                 and CONTRADICTION_SCANNED in node.value)
                or (isinstance(node, ast.Name) and node.id == _VERDICT_CONSTANT)
                or (isinstance(node, ast.Attribute) and node.attr == _VERDICT_CONSTANT)
                or (isinstance(node, ast.alias) and node.name == _VERDICT_CONSTANT)
            )
            if named:
                referrers.add(_rel(path, root))
    return referrers


class TestOnlyTheScanWritesTheVerdict:
    def test_the_scan_module_is_the_only_emitter(self):
        paths = _app_sources(BACKEND)
        assert len(paths) > 100, (
            f"only found {len(paths)} files under app/ — the scan would pass "
            "vacuously; check BACKEND / the glob path"
        )
        emitters = _verdict_emitters(paths, BACKEND)
        assert emitters == {_VERDICT_EMITTER}, (
            "the contradiction verdict is journalled from somewhere other than "
            f"the scan: {sorted(emitters)}. The veto trusts that bit and cannot "
            "re-derive it, so a second writer is a heuristic contradiction "
            "detector with the judge removed from the path."
        )

    def test_only_the_channel_s_three_modules_name_the_verdict(self):
        paths = _app_sources(BACKEND)
        referrers = _verdict_referrers(paths, BACKEND)
        assert referrers == _VERDICT_REFERENCE_ALLOWLIST, (
            "app code outside the verdict channel names the event type: "
            f"{sorted(referrers - _VERDICT_REFERENCE_ALLOWLIST)}. A module that "
            "does not declare, write or read this channel has no use for its "
            "name — and a raw INSERT is the emitter scan's blind spot."
        )

    def test_the_emitter_scan_flags_a_bare_record_event(self, tmp_path):
        """Negative control, and the reviewer's own bypass verbatim: one
        `record_event` call, disputing a fact with no judge in the path."""
        module = tmp_path / "app" / "services" / "eager_verdict.py"
        module.parent.mkdir(parents=True)
        module.write_text(
            "from app.services.events import record_event\n"
            "async def dispute(session, fact_id):\n"
            "    await record_event(\n"
            "        session,\n"
            "        event_type='contradiction_scanned',\n"
            "        object_type='fact',\n"
            "        object_id=fact_id,\n"
            "        payload={'contradicted': True},\n"
            "    )\n",
            encoding="utf-8",
        )
        assert _verdict_emitters([module], tmp_path) == {
            "app/services/eager_verdict.py"
        }

    def test_the_emitter_scan_follows_the_constant_and_its_aliases(self, tmp_path):
        """The same bypass one indirection deeper. A guard matching only the
        inline literal would pass this and report the tree clean."""
        module = tmp_path / "app" / "services" / "laundered_verdict.py"
        module.parent.mkdir(parents=True)
        module.write_text(
            "from app.services.events import CONTRADICTION_SCANNED, record_event\n"
            "KIND = CONTRADICTION_SCANNED\n"
            "async def dispute(session, fact_id):\n"
            "    await record_event(session, event_type=KIND, object_type='fact')\n",
            encoding="utf-8",
        )
        assert _verdict_emitters([module], tmp_path) == {
            "app/services/laundered_verdict.py"
        }

    def test_the_emitter_scan_ignores_an_unrelated_event(self, tmp_path):
        """The other direction: a guard that flagged every `record_event` call
        would be unfalsifiable, and its green run would mean nothing."""
        module = tmp_path / "app" / "services" / "ordinary_writer.py"
        module.parent.mkdir(parents=True)
        module.write_text(
            "from app.services.events import record_event\n"
            "async def note(session, fact_id):\n"
            "    await record_event(\n"
            "        session, event_type='sources_changed', object_type='fact'\n"
            "    )\n",
            encoding="utf-8",
        )
        assert _verdict_emitters([module], tmp_path) == set()
        assert _verdict_referrers([module], tmp_path) == set()

    def test_the_reference_scan_flags_a_raw_insert(self, tmp_path):
        """Negative control for the scan that covers the emitter scan's blind
        spot: no `record_event` call anywhere, the type spelled in SQL."""
        module = tmp_path / "app" / "services" / "sql_verdict.py"
        module.parent.mkdir(parents=True)
        module.write_text(
            "from sqlalchemy import text\n"
            "STMT = text(\"INSERT INTO events (event_type, object_type) \"\n"
            "            \"VALUES ('contradiction_scanned', 'fact')\")\n",
            encoding="utf-8",
        )
        assert _verdict_referrers([module], tmp_path) == {
            "app/services/sql_verdict.py"
        }


# ══════════ G3 — misses are counted, not hidden ══════════════════════════════


class TestMissesAreCounted:
    async def test_a_truncated_pool_is_counted(self, session, qualified_judge_record):
        """The count is a **floor**, and the floor is the honest claim.

        Each arm is drawn one row past the cap so the cap's bite is observable
        at all; an exact count would mean transporting the whole neighbourhood,
        which is what the cap exists to avoid. What must never happen is a
        silent zero on a fact where candidates went unexamined.
        """
        subject = await _fact(
            session, subject="darkmem", obj="postgres",
            fact="darkmem stores its vault in postgres",
        )
        await _source(session, subject, "sess-a")
        for index in range(4):
            other = await _fact(
                session, subject="darkmem", obj=f"store-{index}",
                fact=f"zzz qqq vvv {index} xxx yyy",
            )
            await _source(session, other, f"sess-{index}")
        await _enqueue(session, subject)

        outcome = await _run(session, StubLLM([]), top_k=2)
        assert outcome.candidates_generated == 2
        assert outcome.candidates_truncated >= 1
        assert outcome.misses >= 1
        payload = (await _scan_verdicts(session, subject))[0]
        assert payload["candidates_truncated"] == outcome.candidates_truncated

    async def test_a_provider_failure_leaves_the_pass_incomplete(
        self, session, qualified_judge_record
    ):
        """An incomplete pass writes no verdict at all.

        Writing "clean" over a pair that was never decided would let the veto's
        read-back resolve a standing dispute on evidence nobody gathered, so
        the previous verdict is left alone and the fact is counted as a miss.
        """
        subject = await _fact(
            session, subject="darkmem", obj="postgres",
            fact="darkmem stores its vault in postgres",
        )
        await _source(session, subject, "sess-a")
        counter = await _fact(
            session, subject="darkmem", obj="mysql",
            fact="darkmem stores its vault in mysql",
        )
        await _source(session, counter, "sess-b")
        await _enqueue(session, subject)

        outcome = await _run(session, StubLLM([RuntimeError("provider down")]))
        assert outcome.judge_failed == 1
        assert outcome.facts_incomplete == 1
        assert outcome.facts_checked == 0
        assert outcome.misses >= 2
        assert await _scan_verdicts(session, subject) == []

    async def test_an_unparseable_verdict_is_a_miss_not_a_clear(
        self, session, qualified_judge_record
    ):
        subject = await _fact(
            session, subject="darkmem", obj="postgres",
            fact="darkmem stores its vault in postgres",
        )
        await _source(session, subject, "sess-a")
        counter = await _fact(
            session, subject="darkmem", obj="mysql",
            fact="darkmem stores its vault in mysql",
        )
        await _source(session, counter, "sess-b")
        await _enqueue(session, subject)

        outcome = await _run(session, StubLLM(["not a verdict at all"]))
        assert outcome.judge_invalid == 1
        assert outcome.facts_incomplete == 1
        assert await _scan_verdicts(session, subject) == []

    async def test_a_swallowed_journal_write_is_a_miss_not_a_dispute(
        self, session, qualified_judge_record, monkeypatch
    ):
        """``record_event`` never raises, and this journal row is the whole
        output. Counting the dispute anyway would drop a paid, judge-confirmed
        finding and report the run clean — the exact shape this clause exists
        to forbid, arriving through the one path that is not a judge failure.
        """
        subject = await _fact(
            session, subject="darkmem", obj="postgres",
            fact="darkmem stores its vault in postgres",
        )
        await _source(session, subject, "sess-a")
        counter = await _fact(
            session, subject="darkmem", obj="mysql",
            fact="darkmem stores its vault in mysql",
        )
        await _source(session, counter, "sess-b")
        await _enqueue(session, subject)

        async def _swallowed(*args, **kwargs):
            return None

        monkeypatch.setattr(scan_module, "record_event", _swallowed)
        outcome = await _run(session, StubLLM([_verdict("contradicted")]))

        assert outcome.journal_failed == 1
        assert outcome.disputes_recorded == 0
        assert outcome.clears_recorded == 0
        assert outcome.facts_checked == 0
        assert outcome.misses >= 1
        assert await _scan_verdicts(session, subject) == []

    async def test_a_lost_verdict_leaves_its_event_to_be_drained_again(
        self, session, qualified_judge_record, monkeypatch
    ):
        """The watermark holds, so the fact is re-checked rather than skipped.

        A miss counter that reported the loss while the queue position moved
        past it would name a fact nothing will ever return to.
        """
        subject = await _fact(
            session, subject="darkmem", obj="postgres",
            fact="darkmem stores its vault in postgres",
        )
        await _source(session, subject, "sess-a")
        counter = await _fact(
            session, subject="darkmem", obj="mysql",
            fact="darkmem stores its vault in mysql",
        )
        await _source(session, counter, "sess-b")
        await _enqueue(session, subject)

        async def _swallowed(*args, **kwargs):
            return None

        monkeypatch.setattr(scan_module, "record_event", _swallowed)
        lost = await _run(session, StubLLM([_verdict("contradicted")]))
        assert lost.watermark_advanced is False
        assert lost.skipped_reason == "a verdict could not be journalled"

        # Restored by name rather than `monkeypatch.undo()`, which would also
        # revert the qualification fixture's own patch and leave the second run
        # refusing for an entirely different reason.
        monkeypatch.setattr(scan_module, "record_event", record_event)
        recovered = await _run(session, StubLLM([_verdict("contradicted")]))
        assert recovered.events_scanned == 1
        assert recovered.disputes_recorded == 1
        assert recovered.journal_failed == 0
        assert (await _scan_verdicts(session, subject))[0]["contradicted"] is True

    async def test_an_earlier_runs_verdict_cannot_mask_a_swallowed_write(
        self, session, qualified_judge_record, monkeypatch
    ):
        """The read-back's ``scan_run_id`` predicate, in the steady state.

        A fact cleared once and re-checked later already carries a verdict row
        of this type on this object. Matching on ``(fact, type)`` alone would
        find that row and report the second run's swallowed write as a success
        — resurrecting the defect the read-back exists to close, and doing it
        only for facts that have been scanned before, which is every fact after
        the first cycle.
        """
        subject = await _fact(
            session, subject="darkmem", obj="postgres",
            fact="darkmem stores its vault in postgres",
        )
        await _source(session, subject, "sess-a")
        counter = await _fact(
            session, subject="darkmem", obj="mysql",
            fact="darkmem stores its vault in mysql",
        )
        await _source(session, counter, "sess-b")
        await _enqueue(session, subject)

        cleared = await _run(session, StubLLM([_verdict("unsupported")]))
        assert cleared.clears_recorded == 1
        assert cleared.journal_failed == 0
        assert len(await _scan_verdicts(session, subject)) == 1

        # The fact is still servable — a clear leaves it where it was, which is
        # what puts a prior verdict row in front of the next run's read-back.
        await _enqueue(session, subject)

        async def _swallowed(*args, **kwargs):
            return None

        monkeypatch.setattr(scan_module, "record_event", _swallowed)
        lost = await _run(session, StubLLM([_verdict("contradicted")]))

        assert lost.journal_failed == 1
        assert lost.disputes_recorded == 0
        assert lost.watermark_advanced is False
        # Still the one row from the first run: the second wrote nothing, and
        # the run said so rather than reading the first row as its own.
        assert len(await _scan_verdicts(session, subject)) == 1

    async def test_a_refusal_counts_the_facts_it_never_reached(self, session):
        for index in range(3):
            subject = await _fact(
                session, subject=f"svc-{index}", obj="postgres",
                fact=f"svc-{index} stores its vault in postgres",
            )
            await _source(session, subject, f"sess-{index}")
            counter = await _fact(
                session, subject=f"svc-{index}", obj="mysql",
                fact=f"svc-{index} stores its vault in mysql",
            )
            await _source(session, counter, f"other-{index}")
            await _enqueue(session, subject)

        outcome = await _run(session, StubLLM([]))
        assert outcome.facts_touched == 3
        assert outcome.facts_unscanned == 3
        assert outcome.judge_refused == 1

    async def test_an_unservable_fact_is_reported_apart_from_the_misses(
        self, session
    ):
        """Not a miss: a disputed or expired fact is correctly out of scope,
        and folding it into the miss count would overstate the gap."""
        disputed = await _fact(
            session, subject="darkmem", obj="postgres",
            fact="darkmem stores its vault in postgres", status="disputed",
        )
        await _enqueue(session, disputed)
        outcome = await _run(session, StubLLM([]))
        assert outcome.facts_skipped_unservable == 1
        assert outcome.misses == 0

    async def test_misses_sums_every_bucket(self):
        """The property, not an instance: a bucket added without joining the
        sum would silently stop being reported."""
        from dataclasses import fields

        outcome = scan_module.ScanOutcome()
        buckets = [
            f.name for f in fields(outcome)
            if f.name in {
                "facts_incomplete", "facts_unscanned", "candidates_truncated",
                "judge_refused", "judge_failed", "judge_invalid",
                "journal_failed",
            }
        ]
        assert len(buckets) == 7
        for index, name in enumerate(buckets, start=1):
            assert scan_module.ScanOutcome(**{name: index}).misses == index


# ══════════ G4 — the verdict reaches the veto, and stops when it should ══════


async def _record_verdict(session, fact_id, *, counterpart, witness) -> None:
    await record_event(
        session,
        event_type=CONTRADICTION_SCANNED,
        object_type="fact",
        object_id=fact_id,
        project=PROJECT,
        payload={
            "contradicted": True,
            "counterpart_id": str(counterpart),
            "witness_origin": witness,
        },
    )
    await session.commit()


class TestTheVerdictOpensReview:
    async def test_a_journalled_contradiction_flags_the_fact_without_disputing(
        self, session
    ):
        """Doc 08 §4.2 as amended 2026-08-08 (T2.109), end to end.

        The verdict reaches the ladder, the ladder queues the fact for a human,
        and the rung does not move. Both halves are asserted: a change that
        routed this signal back into ``open_contradiction`` would keep the queue
        assertion green while silently restoring the veto wiring three G-D runs
        measured.
        """
        subject = await _fact(
            session, subject="darkmem", obj="postgres",
            fact="darkmem stores its vault in postgres",
        )
        await _source(session, subject, "sess-a")
        counter = await _fact(
            session, subject="darkmem", obj="mysql",
            fact="darkmem stores its vault in mysql",
        )
        await _source(session, counter, "sess-b")

        decision = await recompute_fact(session, subject)
        await session.commit()
        assert decision.contradiction_blocked is False
        assert decision.contradiction_suspected is False
        before = await _verification(session, subject)

        await _record_verdict(session, subject, counterpart=counter, witness="sess-b")
        finding = await detect_scanned_contradiction(session, subject)
        assert finding is not None and finding.rule == RULE_SCANNED
        assert finding.counterpart_object == "mysql"

        decision = await recompute_fact(session, subject)
        await session.commit()
        assert decision.contradiction_suspected is True
        assert decision.contradiction_blocked is False
        assert decision.target_status != "disputed"

        after = await _verification(session, subject)
        assert after["verification_status"] == before["verification_status"], (
            "a suspected contradiction moves no rung"
        )
        assert after["review_state"] == "open"

    async def test_a_clean_verdict_clears_the_flag_and_the_queue(self, session):
        """The self-healing the rewire bought.

        While the finding wrote ``disputed`` this was unreachable: the scan
        skips already-disputed facts, so no second verdict was ever written and
        a judge false positive stood until a guard lapsed or a human ruled. A
        flagged fact keeps its rung, stays servable and stays in the scan's
        working set, so the next clean pass supersedes the finding and the
        derivation drops the queue entry.
        """
        subject = await _fact(
            session, subject="darkmem", obj="postgres",
            fact="darkmem stores its vault in postgres",
        )
        await _source(session, subject, "sess-a")
        counter = await _fact(
            session, subject="darkmem", obj="mysql",
            fact="darkmem stores its vault in mysql",
        )
        await _source(session, counter, "sess-b")
        await _record_verdict(session, subject, counterpart=counter, witness="sess-b")
        await recompute_fact(session, subject)
        await session.commit()
        assert (await _verification(session, subject))["review_state"] == "open"

        await record_event(
            session,
            event_type=CONTRADICTION_SCANNED,
            object_type="fact",
            object_id=subject,
            project=PROJECT,
            payload={"contradicted": False},
        )
        await session.commit()

        decision = await recompute_fact(session, subject)
        await session.commit()
        assert decision.contradiction_suspected is False
        assert (await _verification(session, subject))["review_state"] is None

    async def test_a_ratified_fact_is_never_flagged(self, session):
        """Doc 08 §4.4: a ratified fact is immune, so it is not queued for an
        adjudication that could change nothing."""
        subject = await _fact(
            session, subject="darkmem", obj="postgres",
            fact="darkmem stores its vault in postgres",
        )
        await _source(session, subject, "sess-a")
        counter = await _fact(
            session, subject="darkmem", obj="mysql",
            fact="darkmem stores its vault in mysql",
        )
        await _source(session, counter, "sess-b")
        await _record_verdict(session, subject, counterpart=counter, witness="sess-b")
        await session.execute(
            text(
                "UPDATE knowledge_triples SET verification_status = 'confirmed' "
                "WHERE id = CAST(:id AS uuid)"
            ),
            {"id": str(subject)},
        )
        await session.commit()

        decision = await recompute_fact(session, subject)
        await session.commit()
        assert decision.contradiction_suspected is False
        assert (await _verification(session, subject))["review_state"] is None

    async def test_a_later_clean_verdict_supersedes_an_earlier_one(self, session):
        """The newest row wins, read at the detector level."""
        subject = await _fact(
            session, subject="darkmem", obj="postgres",
            fact="darkmem stores its vault in postgres",
        )
        await _source(session, subject, "sess-a")
        counter = await _fact(
            session, subject="darkmem", obj="mysql",
            fact="darkmem stores its vault in mysql",
        )
        await _source(session, counter, "sess-b")
        await _record_verdict(session, subject, counterpart=counter, witness="sess-b")
        assert await detect_scanned_contradiction(session, subject) is not None

        await record_event(
            session,
            event_type=CONTRADICTION_SCANNED,
            object_type="fact",
            object_id=subject,
            project=PROJECT,
            payload={"contradicted": False},
        )
        await session.commit()
        assert await detect_scanned_contradiction(session, subject) is None

    async def test_a_verdict_whose_counterpart_expired_is_silence(self, session):
        subject = await _fact(
            session, subject="darkmem", obj="postgres",
            fact="darkmem stores its vault in postgres",
        )
        await _source(session, subject, "sess-a")
        counter = await _fact(
            session, subject="darkmem", obj="mysql",
            fact="darkmem stores its vault in mysql",
        )
        await _source(session, counter, "sess-b")
        await _record_verdict(session, subject, counterpart=counter, witness="sess-b")

        await KnowledgeTripleRepository(session).expire(counter)
        await session.commit()
        assert await detect_scanned_contradiction(session, subject) is None

    async def test_a_verdict_whose_windows_no_longer_overlap_is_silence(self, session):
        subject = await _fact(
            session, subject="darkmem", obj="postgres",
            fact="darkmem stores its vault in postgres", valid_at=T0 + YEAR,
        )
        await _source(session, subject, "sess-a")
        counter = await _fact(
            session, subject="darkmem", obj="mysql",
            fact="darkmem stores its vault in mysql", valid_at=T0,
        )
        await _source(session, counter, "sess-b")
        await _record_verdict(session, subject, counterpart=counter, witness="sess-b")
        assert await detect_scanned_contradiction(session, subject) is not None

        await KnowledgeTripleRepository(session).close_window(counter, T0 + YEAR)
        await session.commit()
        assert await detect_scanned_contradiction(session, subject) is None

    async def test_a_witness_the_counterpart_no_longer_carries_is_silence(
        self, session
    ):
        subject = await _fact(
            session, subject="darkmem", obj="postgres",
            fact="darkmem stores its vault in postgres",
        )
        await _source(session, subject, "sess-a")
        counter = await _fact(
            session, subject="darkmem", obj="mysql",
            fact="darkmem stores its vault in mysql",
        )
        await _source(session, counter, "sess-b")
        await _record_verdict(session, subject, counterpart=counter, witness="ghost")
        assert await detect_scanned_contradiction(session, subject) is None

    async def test_a_witness_the_subject_also_carries_is_an_echo(self, session):
        """Re-checked at read time, not only at scan time: an origin that joins
        the subject after the verdict makes the objection an echo."""
        subject = await _fact(
            session, subject="darkmem", obj="postgres",
            fact="darkmem stores its vault in postgres",
        )
        await _source(session, subject, "sess-a")
        counter = await _fact(
            session, subject="darkmem", obj="mysql",
            fact="darkmem stores its vault in mysql",
        )
        await _source(session, counter, "sess-b")
        await _record_verdict(session, subject, counterpart=counter, witness="sess-b")
        assert await detect_scanned_contradiction(session, subject) is not None

        await _source(session, subject, "sess-b")
        assert await detect_scanned_contradiction(session, subject) is None

    async def test_an_expired_subject_is_not_adjudicated(self, session):
        subject = await _fact(
            session, subject="darkmem", obj="postgres",
            fact="darkmem stores its vault in postgres",
        )
        await _source(session, subject, "sess-a")
        counter = await _fact(
            session, subject="darkmem", obj="mysql",
            fact="darkmem stores its vault in mysql",
        )
        await _source(session, counter, "sess-b")
        await _record_verdict(session, subject, counterpart=counter, witness="sess-b")
        await KnowledgeTripleRepository(session).expire(subject)
        await session.commit()
        assert await detect_scanned_contradiction(session, subject) is None


# ══════════ Inv — the scan never feeds its own input ═════════════════════════


class TestTheScanDoesNotFeedItself:
    async def test_no_run_emits_a_sources_changed_event(
        self, session, qualified_judge_record
    ):
        """The obvious shortcut — emit `sources_changed` so the recompute picks
        the dispute up now — is a trap: this job *drains* that stream, so an
        emit would feed its own input and it would scan the same fact forever.
        """
        subject = await _fact(
            session, subject="darkmem", obj="postgres",
            fact="darkmem stores its vault in postgres",
        )
        await _source(session, subject, "sess-a")
        counter = await _fact(
            session, subject="darkmem", obj="mysql",
            fact="darkmem stores its vault in mysql",
        )
        await _source(session, counter, "sess-b")
        await _enqueue(session, subject)

        before = await session.execute(
            text("SELECT count(*) FROM events WHERE event_type = 'sources_changed'")
        )
        await _run(session, StubLLM([_verdict("contradicted")]))
        after = await session.execute(
            text("SELECT count(*) FROM events WHERE event_type = 'sources_changed'")
        )
        assert after.scalar_one() == before.scalar_one()

    async def test_a_second_run_drains_nothing_new(
        self, session, qualified_judge_record
    ):
        subject = await _fact(
            session, subject="darkmem", obj="postgres",
            fact="darkmem stores its vault in postgres",
        )
        await _source(session, subject, "sess-a")
        await _enqueue(session, subject)

        first = await _run(session, StubLLM([]))
        assert first.events_scanned == 1 and first.watermark_advanced is True
        second = await _run(session, StubLLM([]))
        assert second.events_scanned == 0
