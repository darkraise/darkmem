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
from sqlalchemy import text

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


@pytest.fixture
def qualified_judge_record(tmp_path, monkeypatch):
    """Mint a record that qualifies the judge for one test.

    **Opt-in, never autouse.** The judge refuses unconditionally while no
    canonical record exists, and that refusal is the property that lets this
    job ship before the qualification run happens. A fixture that opened the
    gate for the module would leave the refusal path unexercised everywhere at
    once, which is exactly the trap this epic has already been bitten by.
    """
    identity = vj.judge_identity(_judge_config()["verification"])
    record = tmp_path / "verification_qualification.json"
    record.write_text(json.dumps({
        "judge_identity": {
            **identity,
            "identity_hash": vj.judge_identity_hash(identity),
        },
        "metrics": {
            "entailed_precision": 1.0,
            "entailed_recall": 1.0,
            "contradiction_precision": 1.0,
        },
        "gate_eligible": True,
        "recorded_at": "2026-08-06T00:00:00+00:00",
    }), encoding="utf-8")
    monkeypatch.setattr(vj, "QUALIFICATION_RECORD_PATH", record)
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
            }
        ]
        assert len(buckets) == 6
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


class TestTheVerdictFeedsTheVeto:
    async def test_a_journalled_contradiction_disputes_the_fact(self, session):
        """End to end through the registry: the ladder is what writes the
        status, on a verdict this module never applied itself."""
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
        assert decision.contradiction_blocked is False

        await _record_verdict(session, subject, counterpart=counter, witness="sess-b")
        finding = await detect_scanned_contradiction(session, subject)
        assert finding is not None and finding.rule == RULE_SCANNED
        assert finding.counterpart_object == "mysql"

        decision = await recompute_fact(session, subject)
        assert decision.target_status == "disputed"

    async def test_a_later_clean_verdict_ends_the_dispute(self, session):
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
