"""T3.01 — the subject eligibility gate and the priority score (doc 09 §4.1).

Doc 09's decision is a **gated composite**: a hard eligibility gate on verified
fact count, and only then a weighted priority score that orders the survivors
under a per-run budget. The two halves fail differently, so they are tested
differently.

**The gate is the truth-first half.** "An article that cannot be grounded is
worse than no article", so a subject below the floor is ineligible *regardless*
of how central or how frequently read it is. The tests that matter here are the
ones where score and gate disagree: a red-hot, highly-central subject one fact
short of the floor must not appear, and no priority may be computed for it at
all. A scorer that ranked first and filtered second would pass a test that only
checked the final list length.

**The score is the ordering half**, and every weight and the budget are
``config`` rows — deliberately unlike ``review_ranking``'s code-constant
weights. See ``article_eligibility``'s module docstring for why the two
conventions coexist and what the config row does *not* license.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

import pytest
from sqlalchemy import text

from app.repositories.knowledge_triples import KnowledgeTripleRepository
from app.repositories.pinned_subjects import PINNED_KEY, append_subject
from app.services import article_eligibility as ae

pytestmark = pytest.mark.asyncio

T0 = datetime(2026, 6, 1, 12, 0, 0, tzinfo=timezone.utc)
PROJECT = "t3-01-articles"


async def _entity(session, name: str, entity_type: str = "concept") -> UUID:
    entity_id = uuid4()
    await session.execute(
        text(
            "INSERT INTO entities (id, name, entity_type, memory_ids) "
            "VALUES (CAST(:id AS uuid), CAST(:name AS text), "
            "CAST(:etype AS text), '{}'::uuid[])"
        ),
        {"id": str(entity_id), "name": name, "etype": entity_type},
    )
    return entity_id


async def _neighbours(session, hub: UUID, count: int) -> None:
    """`count` distinct graph neighbours for `hub` — the centrality signal."""
    for index in range(count):
        other = await _entity(session, f"n-{hub}-{index}")
        await session.execute(
            text(
                "INSERT INTO entity_relations "
                "(id, source_entity_id, target_entity_id, rel_type, memory_ids) "
                "VALUES (gen_random_uuid(), CAST(:s AS uuid), CAST(:t AS uuid), "
                "'RELATED_TO', '{}'::uuid[])"
            ),
            {"s": str(hub), "t": str(other)},
        )


async def _fact(
    session,
    *,
    subject_name: str,
    subject_id: UUID | None = None,
    status: str = "corroborated",
    expired: bool = False,
    project: str = PROJECT,
) -> str:
    repo = KnowledgeTripleRepository(session)
    row = await repo.insert_open(
        triple_key=f"k-{uuid4()}",
        subject_name=subject_name,
        object_name=f"o-{uuid4()}",
        rel_type="RELATED_TO",
        fact=f"{subject_name} relates",
        reference_time=T0,
        project=project,
        subject_id=subject_id,
    )
    # Raw, not through `set_verification_status`: this is fixture seeding, and
    # routing it through the ladder's writer would journal transitions the
    # suite makes no claim about.
    await session.execute(
        text(
            "UPDATE knowledge_triples SET verification_status = CAST(:s AS text) "
            "WHERE id = CAST(:id AS uuid)"
        ),
        {"s": status, "id": row["id"]},
    )
    if expired:
        await session.execute(
            text(
                "UPDATE knowledge_triples SET expired_at = now() "
                "WHERE id = CAST(:id AS uuid)"
            ),
            {"id": row["id"]},
        )
    await session.flush()
    return row["id"]


async def _subject_with(session, name: str, *, verified: int, **kw) -> UUID:
    entity_id = await _entity(session, name)
    for _ in range(verified):
        await _fact(session, subject_name=name, subject_id=entity_id, **kw)
    return entity_id


async def _config(session, value: dict) -> None:
    await session.execute(
        text(
            "INSERT INTO config (key, value) "
            "VALUES (CAST(:k AS text), CAST(:v AS jsonb)) "
            "ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value"
        ),
        {"k": ae.ARTICLE_SELECTION_CONFIG_KEY, "v": __import__("json").dumps(value)},
    )
    await session.flush()


# ─────────────── clause 1: eligibility is boolean, and first ───────────────


class TestTheGateRunsBeforeTheScore:
    async def test_a_subject_below_the_floor_is_ineligible(self, session):
        await _subject_with(session, "sparse", verified=ae.DEFAULT_MIN_VERIFIED_FACTS - 1)

        candidates = await ae.candidate_subjects(session, project=PROJECT)

        sparse = next(c for c in candidates if c.subject_key.startswith("sparse::"))
        assert sparse.eligible is False
        assert sparse.verified_fact_count == ae.DEFAULT_MIN_VERIFIED_FACTS - 1

    async def test_an_ineligible_subject_carries_no_priority_at_all(self, session):
        """The clause with teeth. A scorer that ranked first and filtered
        second would satisfy every list-membership assertion in this file
        while still having computed a priority for a subject that cannot be
        grounded — and the next task to reach for `.priority` would find a
        number that doc 09 says must not exist.
        """
        hub = await _subject_with(
            session, "hot-but-sparse", verified=ae.DEFAULT_MIN_VERIFIED_FACTS - 1
        )
        await _neighbours(session, hub, 25)

        candidates = await ae.candidate_subjects(session, project=PROJECT)
        sparse = next(c for c in candidates if c.subject_key.startswith("hot-but-sparse::"))

        assert sparse.eligible is False
        assert sparse.priority is None

    async def test_centrality_cannot_buy_eligibility(self, session):
        """Doc 09's own sentence, asserted: a hub retrieved constantly but
        holding no verified facts "has nothing to ground against"."""
        hub = await _subject_with(
            session, "hub", verified=ae.DEFAULT_MIN_VERIFIED_FACTS - 1
        )
        await _neighbours(session, hub, 40)
        await _subject_with(session, "quiet", verified=ae.DEFAULT_MIN_VERIFIED_FACTS)

        selected = await ae.select_for_synthesis(session, project=PROJECT)

        keys = [c.subject_key for c in selected]
        assert any(k.startswith("quiet::") for k in keys)
        assert not any(k.startswith("hub::") for k in keys)


# ─────────────── clause 1b: what counts toward the floor ───────────────


class TestWhatTheFloorCounts:
    async def test_candidate_facts_do_not_count(self, session):
        """"Candidate facts are never a synthesis input" — counting them would
        launder unverified signal into apparent knowledge."""
        await _subject_with(
            session, "unverified", verified=ae.DEFAULT_MIN_VERIFIED_FACTS,
            status="candidate",
        )

        candidates = await ae.candidate_subjects(session, project=PROJECT)

        assert not any(c.subject_key.startswith("unverified::") for c in candidates)

    async def test_disputed_facts_do_not_count(self, session):
        await _subject_with(
            session, "contested", verified=ae.DEFAULT_MIN_VERIFIED_FACTS,
            status="disputed",
        )

        candidates = await ae.candidate_subjects(session, project=PROJECT)

        assert not any(c.subject_key.startswith("contested::") for c in candidates)

    async def test_expired_facts_do_not_count(self, session):
        """The belief axis is orthogonal to the verification axis: a fact can
        be well-verified and no longer current, and an article states what is
        currently understood."""
        name = "lapsed"
        entity_id = await _entity(session, name)
        for _ in range(ae.DEFAULT_MIN_VERIFIED_FACTS):
            await _fact(session, subject_name=name, subject_id=entity_id, expired=True)

        candidates = await ae.candidate_subjects(session, project=PROJECT)

        assert not any(c.subject_key.startswith("lapsed::") for c in candidates)

    async def test_confirmed_counts_alongside_corroborated(self, session):
        """The human rung is not a different kind of verification for this
        gate — it is a higher one."""
        name = "ratified"
        entity_id = await _entity(session, name)
        await _fact(session, subject_name=name, subject_id=entity_id, status="confirmed")
        for _ in range(ae.DEFAULT_MIN_VERIFIED_FACTS - 1):
            await _fact(session, subject_name=name, subject_id=entity_id)

        candidates = await ae.candidate_subjects(session, project=PROJECT)
        ratified = next(c for c in candidates if c.subject_key.startswith("ratified::"))

        assert ratified.verified_fact_count == ae.DEFAULT_MIN_VERIFIED_FACTS
        assert ratified.eligible is True

    async def test_two_types_sharing_one_name_are_two_subjects(self, session):
        """Task review, Important 2. Uniqueness on `entities` is
        `(name, entity_type)`, so one name can be two subjects. Grouping on
        the name alone summed their counts into one floor neither had earned,
        and keyed the result by the lexicographically smallest type.
        """
        name = "mercury"
        floor = ae.DEFAULT_MIN_VERIFIED_FACTS
        planet = await _entity(session, name, entity_type="concept")
        tool = await _entity(session, name, entity_type="tool")
        for _ in range(floor - 1):
            await _fact(session, subject_name=name, subject_id=planet)
        await _fact(session, subject_name=name, subject_id=tool)

        candidates = await ae.candidate_subjects(session, project=PROJECT)
        mine = {c.subject_key: c for c in candidates if c.subject_key.startswith(f"{name}::")}

        assert set(mine) == {f"{name}::concept", f"{name}::tool"}
        assert mine[f"{name}::concept"].verified_fact_count == floor - 1
        assert mine[f"{name}::tool"].verified_fact_count == 1
        # Neither earned the floor, so pooling them would have invented one.
        assert not any(c.eligible for c in mine.values())

    async def test_another_project_s_facts_do_not_count(self, session):
        name = "shared-name"
        entity_id = await _entity(session, name)
        await _fact(session, subject_name=name, subject_id=entity_id)
        for _ in range(ae.DEFAULT_MIN_VERIFIED_FACTS):
            await _fact(
                session, subject_name=name, subject_id=entity_id, project="somewhere-else"
            )

        candidates = await ae.candidate_subjects(session, project=PROJECT)
        shared = next(c for c in candidates if c.subject_key.startswith("shared-name::"))

        assert shared.verified_fact_count == 1
        assert shared.eligible is False


# ─────────────── clause 1c: pinned subjects bypass the gate ───────────────


class TestPinnedSubjects:
    async def test_a_pinned_subject_is_eligible_below_the_floor(self, session):
        """Doc 09: "pinned subjects are always eligible". A human asking for an
        article is a different claim from the machine deciding one is earned.
        """
        await _subject_with(session, "pinned-thin", verified=0)
        key = ae.subject_soft_key("pinned-thin", "concept")
        await append_subject(session, PROJECT, PINNED_KEY, key)
        await session.flush()

        candidates = await ae.candidate_subjects(session, project=PROJECT)
        pinned = next(c for c in candidates if c.subject_key == key)

        assert pinned.pinned is True
        assert pinned.eligible is True
        assert pinned.priority is not None

    async def test_a_pinned_subject_with_no_facts_at_all_still_appears(self, session):
        key = ae.subject_soft_key("never-asserted", "concept")
        await _entity(session, "never-asserted")
        await append_subject(session, PROJECT, PINNED_KEY, key)
        await session.flush()

        candidates = await ae.candidate_subjects(session, project=PROJECT)
        pinned = next(c for c in candidates if c.subject_key == key)

        assert (pinned.verified_fact_count, pinned.eligible) == (0, True)


# ─────────────── clause 2: weights and budget are config rows ───────────────


class TestTheConfigRows:
    async def test_the_defaults_apply_with_no_row(self, session):
        config = await ae.get_synthesis_config(session)
        assert config.min_verified_facts == ae.DEFAULT_MIN_VERIFIED_FACTS
        assert config.synthesis_budget == ae.DEFAULT_SYNTHESIS_BUDGET

    async def test_the_floor_is_operator_settable(self, session):
        await _config(session, {"min_verified_facts": 1})
        await _subject_with(session, "thin", verified=1)

        candidates = await ae.candidate_subjects(session, project=PROJECT)
        thin = next(c for c in candidates if c.subject_key.startswith("thin::"))

        assert thin.eligible is True

    async def test_the_budget_bounds_one_run(self, session):
        await _config(session, {"synthesis_budget": 2})
        for index in range(4):
            await _subject_with(
                session, f"s{index}", verified=ae.DEFAULT_MIN_VERIFIED_FACTS
            )

        selected = await ae.select_for_synthesis(session, project=PROJECT)

        assert len(selected) == 2

    async def test_a_weight_of_zero_removes_its_signal(self, session):
        """Each weight is a real multiplier, not a label on a fixed formula."""
        hub = await _subject_with(
            session, "central", verified=ae.DEFAULT_MIN_VERIFIED_FACTS
        )
        await _neighbours(session, hub, 30)

        with_central = await ae.candidate_subjects(session, project=PROJECT)
        await _config(session, {"w_central": 0.0})
        without_central = await ae.candidate_subjects(session, project=PROJECT)

        before = next(c for c in with_central if c.subject_key.startswith("central::"))
        after = next(c for c in without_central if c.subject_key.startswith("central::"))
        assert before.priority is not None and after.priority is not None
        assert after.priority < before.priority

    async def test_a_malformed_row_degrades_loudly_to_the_default(self, session, caplog):
        """The row is operator-edited with no schema in front of it. A bad
        value must not take the synthesis job down — `review_ranking`'s rule,
        applied to the same kind of surface."""
        await _config(session, {"min_verified_facts": "three", "nonsense": 1})

        with caplog.at_level("WARNING"):
            config = await ae.get_synthesis_config(session)

        assert config.min_verified_facts == ae.DEFAULT_MIN_VERIFIED_FACTS
        assert "nonsense" in caplog.text

    async def test_a_non_finite_value_falls_back_instead_of_crashing(self, session):
        """Task review, Important 3. `min`/`max` propagate NaN rather than
        clamping it, so the clamp "succeeded" and `int(nan)` then raised --
        taking the job down, which is the one thing this loader exists not to
        do. In a weight there was no raise at all: every priority silently NaN.
        """
        # The *strings* are the reachable vector, and that is the finding's
        # own shape: jsonb refuses a bare NaN token outright, so a float NaN
        # can never reach this row -- but "nan" is valid JSON and `float()`
        # parses it happily. A first draft of this test used the float and
        # proved nothing but Postgres's own validation.
        await _config(session, {"min_verified_facts": "nan", "w_heat": "inf"})

        config = await ae.get_synthesis_config(session)

        assert config.min_verified_facts == ae.DEFAULT_MIN_VERIFIED_FACTS
        assert config.w_heat == ae.DEFAULT_W_HEAT

    async def test_an_out_of_range_value_is_clamped(self, session):
        await _config(session, {"synthesis_budget": 10_000_000})
        config = await ae.get_synthesis_config(session)
        assert config.synthesis_budget == ae.PARAM_BOUNDS["synthesis_budget"][1]


# ─────────────── clause 3: one live article per (project, subject) ───────────────


class TestOneLiveArticlePerSubject:
    async def test_a_second_live_article_for_one_subject_is_refused(self, session):
        """Enforced by `ux_knowledge_articles_live`, not by application code —
        the done-when says constraint, and a check in the writer would be one
        race away from two live articles under one subject."""
        from sqlalchemy.exc import IntegrityError

        key = ae.subject_soft_key("postgres", "tool")
        insert = text(
            "INSERT INTO knowledge_articles (id, subject_key, project, content) "
            "VALUES (gen_random_uuid(), CAST(:k AS text), CAST(:p AS text), 'x')"
        )
        await session.execute(insert, {"k": key, "p": PROJECT})

        # The database refuses on the statement itself, not at flush — the
        # index is enforcing, not advisory.
        with pytest.raises(IntegrityError):
            await session.execute(insert, {"k": key, "p": PROJECT})

    async def test_a_superseded_article_leaves_room_for_its_replacement(self, session):
        """The partial predicate's whole purpose: re-synthesis retires the old
        article and writes a new one, and both rows survive."""
        key = ae.subject_soft_key("redis", "tool")
        await session.execute(
            text(
                "INSERT INTO knowledge_articles "
                "(id, subject_key, project, content, status) "
                "VALUES (gen_random_uuid(), CAST(:k AS text), CAST(:p AS text), "
                "'old', 'superseded')"
            ),
            {"k": key, "p": PROJECT},
        )
        await session.execute(
            text(
                "INSERT INTO knowledge_articles (id, subject_key, project, content) "
                "VALUES (gen_random_uuid(), CAST(:k AS text), CAST(:p AS text), 'new')"
            ),
            {"k": key, "p": PROJECT},
        )
        await session.flush()

        live = (await session.execute(
            text(
                "SELECT COUNT(*) FROM knowledge_articles WHERE project = CAST(:p AS text) "
                "AND subject_key = CAST(:k AS text) AND status <> 'superseded'"
            ),
            {"p": PROJECT, "k": key},
        )).scalar_one()
        assert live == 1

    async def test_a_subject_that_already_has_a_live_article_is_not_reselected(
        self, session
    ):
        """The budget is for subjects that need an article. Re-synthesis of an
        existing one is T3.05's staleness gate, on its own trigger — spending
        this run's budget on it would starve subjects with no article at all.
        """
        await _subject_with(session, "already", verified=ae.DEFAULT_MIN_VERIFIED_FACTS)
        await session.execute(
            text(
                "INSERT INTO knowledge_articles (id, subject_key, project, content) "
                "VALUES (gen_random_uuid(), CAST(:k AS text), CAST(:p AS text), 'x')"
            ),
            {"k": ae.subject_soft_key("already", "concept"), "p": PROJECT},
        )
        await session.flush()

        selected = await ae.select_for_synthesis(session, project=PROJECT)

        assert not any(c.subject_key.startswith("already::") for c in selected)


# ─────────────── clause 2b: the ordering the score exists for ───────────────


class TestPriorityOrdering:
    async def test_eligible_subjects_come_back_in_priority_order(self, session):
        await _subject_with(session, "low", verified=ae.DEFAULT_MIN_VERIFIED_FACTS)
        rich = await _subject_with(
            session, "high", verified=ae.DEFAULT_MIN_VERIFIED_FACTS + 6
        )
        await _neighbours(session, rich, 12)

        selected = await ae.select_for_synthesis(session, project=PROJECT)

        keys = [c.subject_key for c in selected]
        assert keys.index("high::concept") < keys.index("low::concept")

    def test_the_order_is_total_and_stable_under_ties(self):
        """Two subjects with identical signals must not swap between runs: a
        budget that cuts a tied list needs a deterministic cut, or the same
        corpus synthesises different subjects on consecutive runs.

        Tested on the pure ordering rather than through the database, and the
        difference is what makes it a guard: whether the planner returns a
        tied pair in one order or the other is not pinnable, so a DB-level
        version passed with the tie-break deleted — Python's sort is stable,
        so it simply preserved whatever arrival order it was given. Handing
        the tie in *reverse* is the only way the assertion can fail when the
        tie-break goes.
        """
        tied = [
            ae.SubjectCandidate(
                subject_key=key, project=PROJECT, verified_fact_count=3,
                read_heat=0.0, centrality=0, pinned=False, eligible=True,
                priority=1.0,
            )
            for key in ("tie-c::concept", "tie-b::concept", "tie-a::concept")
        ]

        ordered = ae.order_for_budget(tied, ae.SynthesisConfig())

        assert [c.subject_key for c in ordered] == [
            "tie-a::concept", "tie-b::concept", "tie-c::concept",
        ]

    def test_ordering_refuses_an_ineligible_subject(self):
        """Task review, Important 1. `-(priority or 0.0)` adopted 0.0 for the
        one object doc 09 forbids ranking, so handing this the output of
        `candidate_subjects` -- which deliberately includes ineligibles --
        filled spare budget with subjects that cleared no floor.
        """
        mixed = [
            ae.SubjectCandidate(
                subject_key="ok::concept", project=PROJECT, verified_fact_count=3,
                read_heat=0.0, centrality=0, pinned=False, eligible=True, priority=1.0,
            ),
            ae.SubjectCandidate(
                subject_key="under::concept", project=PROJECT, verified_fact_count=1,
                read_heat=0.0, centrality=0, pinned=False, eligible=False, priority=None,
            ),
        ]

        with pytest.raises(ValueError, match="ineligible"):
            ae.order_for_budget(mixed, ae.SynthesisConfig())

    def test_the_budget_cuts_the_head_of_the_order_not_the_tail(self):
        """The cut keeps the highest-priority subjects. Slicing the wrong end
        would synthesise exactly the subjects the score ranked last, and the
        list length would look right either way."""
        candidates = [
            ae.SubjectCandidate(
                subject_key=f"s{index}::concept", project=PROJECT,
                verified_fact_count=3, read_heat=0.0, centrality=0, pinned=False,
                eligible=True, priority=float(index),
            )
            for index in range(5)
        ]

        ordered = ae.order_for_budget(candidates, ae.SynthesisConfig(synthesis_budget=2))

        assert [c.priority for c in ordered] == [4.0, 3.0]
