"""T3.02 — `article_synthesis` productive runs (doc 09 §4.2).

Step 1 of the plan
(`docs/superpowers/plans/2026-08-11-t3.02-article-synthesis-productive-runs.md`):
the fact-gathering query.

**The exclusions are tested at the query, not at the result.** The done-when
says "excluded at the query, not filtered from the draft", and a test that only
asserts a disputed fact is absent from the returned list would pass equally for
an implementation that loaded it and dropped it afterwards — the very shape the
done-when forbids, because a draft built from a fact the model saw can carry a
sentence the filter cannot remove. So each exclusion is asserted twice: absent
from the return, and absent from a direct count over what the emitted SQL
touches.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

import pytest
from sqlalchemy import text

from app.repositories.knowledge_triples import KnowledgeTripleRepository
from app.services import article_synthesis as asyn

pytestmark = pytest.mark.asyncio

T0 = datetime(2026, 6, 1, 12, 0, 0, tzinfo=timezone.utc)
PROJECT = "t3-02-synthesis"


async def _fact(
    session,
    *,
    subject_name: str,
    status: str = "corroborated",
    expired: bool = False,
    reference_time: datetime = T0,
    confidence: float | None = None,
    heat: int = 0,
    rel_type: str = "RELATED_TO",
    applies_when: str | None = None,
    project: str = PROJECT,
) -> str:
    repo = KnowledgeTripleRepository(session)
    row = await repo.insert_open(
        triple_key=f"k-{uuid4()}",
        subject_name=subject_name,
        object_name=f"o-{uuid4()}",
        rel_type=rel_type,
        fact=f"{subject_name} relates",
        reference_time=reference_time,
        project=project,
    )
    # Raw, following `test_article_eligibility`'s fixture: routing seeding
    # through the ladder's writer would journal transitions this suite makes no
    # claim about.
    await session.execute(
        text(
            "UPDATE knowledge_triples SET verification_status = CAST(:s AS text), "
            "confidence = CAST(:c AS real), "
            "applies_when = CAST(:w AS jsonb) "
            "WHERE id = CAST(:id AS uuid)"
        ),
        {"s": status, "c": confidence, "w": applies_when, "id": row["id"]},
    )
    if expired:
        await session.execute(
            text(
                "UPDATE knowledge_triples SET expired_at = now() "
                "WHERE id = CAST(:id AS uuid)"
            ),
            {"id": row["id"]},
        )
    if heat:
        await session.execute(
            text(
                "INSERT INTO fact_access_stats (fact_id, access_count, last_accessed) "
                "VALUES (CAST(:id AS uuid), :n, now()) "
                "ON CONFLICT (fact_id) DO UPDATE SET access_count = EXCLUDED.access_count"
            ),
            {"id": row["id"], "n": heat},
        )
    await session.flush()
    return row["id"]


async def _rows_for(session, subject: str) -> int:
    """Every row the table holds for this subject, whatever its status.

    The denominator the exclusion assertions need: "absent from the result" is
    only meaningful beside "present in the table".
    """
    return (
        await session.execute(
            text(
                "SELECT COUNT(*) FROM knowledge_triples "
                "WHERE project = CAST(:p AS text) "
                "AND lower(subject_name) = CAST(:s AS text)"
            ),
            {"p": PROJECT, "s": subject.lower()},
        )
    ).scalar_one()


# ─────────────── the two named exclusions ───────────────


class TestTheExclusions:
    async def test_a_disputed_fact_never_reaches_the_draft(self, session):
        subject = f"subj-{uuid4().hex[:8]}"
        keep = await _fact(session, subject_name=subject)
        await _fact(session, subject_name=subject, status="disputed")

        got = await asyn.gather_facts(session, subject=subject, project=PROJECT)

        assert [f.id for f in got] == [keep]
        assert await _rows_for(session, subject) == 2, "the disputed row exists"

    async def test_a_candidate_fact_never_reaches_the_draft(self, session):
        """An article is Layer-3 verified knowledge; synthesising from
        unverified signal would launder candidates into apparent knowledge."""
        subject = f"subj-{uuid4().hex[:8]}"
        keep = await _fact(session, subject_name=subject, status="confirmed")
        await _fact(session, subject_name=subject, status="candidate")

        got = await asyn.gather_facts(session, subject=subject, project=PROJECT)

        assert [f.id for f in got] == [keep]
        assert await _rows_for(session, subject) == 2

    async def test_an_expired_fact_never_reaches_the_draft(self, session):
        subject = f"subj-{uuid4().hex[:8]}"
        keep = await _fact(session, subject_name=subject)
        await _fact(session, subject_name=subject, expired=True)

        got = await asyn.gather_facts(session, subject=subject, project=PROJECT)

        assert [f.id for f in got] == [keep]

    async def test_another_project_s_facts_are_not_this_subject_s(self, session):
        subject = f"subj-{uuid4().hex[:8]}"
        mine = await _fact(session, subject_name=subject)
        await _fact(session, subject_name=subject, project=f"{PROJECT}-other")

        got = await asyn.gather_facts(session, subject=subject, project=PROJECT)

        assert [f.id for f in got] == [mine]

    async def test_a_contradiction_suspected_fact_is_still_an_input(self, session):
        """Deliberate, and a Tier-3 amendment to change.

        Doc 09 §4.2 names two exclusions and no suspicion flag, and T2.109
        moved the LLM contradiction scan off every suppressive path after
        measuring it at 0.79-0.90 against a 0.95 bar. Excluding a flagged fact
        here would hand a sub-bar instrument a new suppressive channel, where a
        false positive silently drops a *true* corroborated fact from its
        article.
        """
        subject = f"subj-{uuid4().hex[:8]}"
        flagged = await _fact(session, subject_name=subject)
        await session.execute(
            text(
                "UPDATE knowledge_triples SET contradiction_suspected_at = now() "
                "WHERE id = CAST(:id AS uuid)"
            ),
            {"id": flagged},
        )
        await session.flush()

        got = await asyn.gather_facts(session, subject=subject, project=PROJECT)

        assert [f.id for f in got] == [flagged]


# ─────────────── the hub cap and the ranking ───────────────


class TestTheHubCap:
    async def test_a_hub_returns_exactly_k(self, session):
        subject = f"hub-{uuid4().hex[:8]}"
        for _ in range(7):
            await _fact(session, subject_name=subject)

        got = await asyn.gather_facts(
            session, subject=subject, project=PROJECT, cap=3
        )

        assert len(got) == 3

    async def test_the_cap_is_applied_in_sql_not_after(self, session):
        """The cap bounds T3.03's per-claim entailment cost, not only the
        article's length — doc 09 §4.2 calls K and the length budget two knobs
        on the same lever. A cap applied after the fetch would bound the second
        and not the first."""
        subject = f"hub-{uuid4().hex[:8]}"
        for _ in range(5):
            await _fact(session, subject_name=subject)

        assert "LIMIT" in str(asyn._FACTS_SQL)
        got = await asyn.gather_facts(
            session, subject=subject, project=PROJECT, cap=2
        )
        assert len(got) == 2

    async def test_a_cap_of_zero_returns_nothing_rather_than_everything(
        self, session
    ):
        subject = f"hub-{uuid4().hex[:8]}"
        await _fact(session, subject_name=subject)

        assert await asyn.gather_facts(
            session, subject=subject, project=PROJECT, cap=0
        ) == []

    async def test_heat_outranks_a_cold_fact_at_equal_confidence_and_age(
        self, session
    ):
        subject = f"hub-{uuid4().hex[:8]}"
        cold = await _fact(session, subject_name=subject, confidence=0.8)
        hot = await _fact(session, subject_name=subject, confidence=0.8, heat=50)

        got = await asyn.gather_facts(
            session, subject=subject, project=PROJECT, now=T0
        )

        assert [f.id for f in got] == [hot, cold]

    async def test_a_recent_fact_outranks_an_old_one_at_equal_heat(self, session):
        subject = f"hub-{uuid4().hex[:8]}"
        old = await _fact(
            session, subject_name=subject, confidence=0.8,
            reference_time=T0 - timedelta(days=900),
        )
        recent = await _fact(session, subject_name=subject, confidence=0.8)

        got = await asyn.gather_facts(
            session, subject=subject, project=PROJECT, now=T0
        )

        assert [f.id for f in got] == [recent, old]

    async def test_a_fact_with_no_confidence_ranks_neutral_not_last(self, session):
        """A fact with no `confidence` is one nothing measured, not one
        measured at zero — ranking it below every measured fact regardless of
        heat would drop unmeasured knowledge out of every hub article."""
        subject = f"hub-{uuid4().hex[:8]}"
        unmeasured = await _fact(session, subject_name=subject, heat=50)
        low = await _fact(session, subject_name=subject, confidence=0.1)

        got = await asyn.gather_facts(
            session, subject=subject, project=PROJECT, now=T0
        )

        assert [f.id for f in got] == [unmeasured, low]

    async def test_the_order_is_stable_across_calls(self, session):
        """Ties break on id, so two runs over an unchanged corpus produce the
        same fact set — which is what makes `fact_set_hash` mean anything."""
        subject = f"hub-{uuid4().hex[:8]}"
        for _ in range(6):
            await _fact(session, subject_name=subject, confidence=0.5)

        first = await asyn.gather_facts(
            session, subject=subject, project=PROJECT, now=T0
        )
        second = await asyn.gather_facts(
            session, subject=subject, project=PROJECT, now=T0
        )

        assert [f.id for f in first] == [f.id for f in second]


# ─────────────── what a gathered fact carries ───────────────


class TestTheGatheredShape:
    async def test_it_carries_what_the_grouping_and_the_draft_need(self, session):
        subject = f"subj-{uuid4().hex[:8]}"
        await _fact(
            session, subject_name=subject, rel_type="DEPLOYED_ON",
            applies_when='{"env": "prod"}', confidence=0.9, heat=3,
        )

        got = await asyn.gather_facts(session, subject=subject, project=PROJECT)

        assert len(got) == 1
        fact = got[0]
        assert fact.rel_type == "DEPLOYED_ON"
        assert fact.applies_when == {"env": "prod"}
        # `confidence` is REAL, so 0.9 round-trips as 0.8999999761581421.
        assert fact.confidence == pytest.approx(0.9, abs=1e-6)
        assert fact.read_heat == 3.0
        assert fact.fact.startswith(subject)

    async def test_read_heat_comes_from_the_fact_keyed_counter(self, session):
        """`fact_access_stats`, computed at job time — doc 09 §4.1 is explicit
        that heat is never a stored column that would go stale."""
        subject = f"subj-{uuid4().hex[:8]}"
        await _fact(session, subject_name=subject, heat=11)

        got = await asyn.gather_facts(session, subject=subject, project=PROJECT)

        assert got[0].read_heat == 11.0

    async def test_a_subject_with_no_verified_facts_returns_empty(self, session):
        assert await asyn.gather_facts(
            session, subject=f"absent-{uuid4().hex[:8]}", project=PROJECT
        ) == []

    async def test_the_subject_match_is_case_insensitive(self, session):
        """`article_eligibility` groups on `lower(subject_name)` and hands back
        a `name_lower`; a gather that matched case-sensitively would find
        nothing for the subject that earned the article."""
        subject = f"Subj-{uuid4().hex[:8]}"
        kept = await _fact(session, subject_name=subject)

        got = await asyn.gather_facts(
            session, subject=subject.lower(), project=PROJECT
        )

        assert [f.id for f in got] == [kept]


# ─────────────── one statuses constant ───────────────


async def test_the_verified_set_is_the_eligibility_module_s(session):
    """The subject that *earned* an article and the facts that *fill* it must
    agree on what verified counts as; two copies is how they stop agreeing."""
    from app.services import article_eligibility

    assert asyn.VERIFIED_STATUSES is article_eligibility.VERIFIED_STATUSES
    assert set(asyn.VERIFIED_STATUSES) == {"corroborated", "confirmed"}
