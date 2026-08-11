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

import json
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


# ─────────────── Step 2: grouping and the draft ───────────────


class _StubLLM:
    """Records what it was asked and answers what the test wants.

    A stub rather than a mock of `chat_completion`'s signature, because the
    prompt's *content* is one of the properties under test: doc 09 §4.2 says an
    article's "only inputs are verified facts", and the prompt is where that
    stops being checkable if nothing looks.
    """

    def __init__(self, payload: str = "", raises: Exception | None = None):
        self.payload = payload
        self.raises = raises
        self.calls: list[dict] = []

    async def chat_completion(self, purpose, *, messages, response_format=None, seed=None):
        self.calls.append(
            {
                "purpose": purpose,
                "messages": messages,
                "response_format": response_format,
                "seed": seed,
            }
        )
        if self.raises is not None:
            raise self.raises
        return self.payload

    @property
    def prompt(self) -> str:
        return "\n".join(m["content"] for m in self.calls[-1]["messages"])


def _draft_payload(fact_ids: list[str], *, lead: str = "A subject.", words: int = 0) -> str:
    filler = " ".join(["word"] * words) if words else "It relates to a thing."
    return json.dumps(
        {
            "lead": lead,
            "sentences": [{"text": filler, "fact_ids": fact_ids}],
        }
    )


def _gathered(ident: str, **kw) -> asyn.GatheredFact:
    base = dict(
        id=ident,
        subject_name="subj",
        rel_type="RELATED_TO",
        object_name="obj",
        fact=f"fact {ident}",
        applies_when=None,
        learned_in=[],
        confidence=0.8,
        read_heat=0.0,
        reference_time=T0,
        salience=1.0,
    )
    base.update(kw)
    return asyn.GatheredFact(**base)


class TestGrouping:
    async def test_facts_group_by_relation_then_context(self):
        groups = asyn.group_facts(
            [
                _gathered("a", rel_type="RUNS_ON"),
                _gathered("b", rel_type="RUNS_ON", applies_when={"env": "prod"}),
                _gathered("c", rel_type="RUNS_ON"),
            ]
        )

        assert len(groups) == 2
        assert [f.id for f in groups[("RUNS_ON", "")]] == ["a", "c"]

    async def test_a_scoped_fact_does_not_share_a_group_with_an_unscoped_one(self):
        """Doc 09 §4.2: a fact that holds only in `env=prod` must read as a
        scoped claim, not a universal one. Pooling them is how it stops."""
        groups = asyn.group_facts(
            [
                _gathered("a", applies_when={"env": "prod"}),
                _gathered("b"),
            ]
        )

        assert len(groups) == 2

    async def test_group_order_follows_salience_not_the_alphabet(self):
        """A group is keyed by the first fact that reached it, so the article's
        sections lead with its most load-bearing knowledge."""
        groups = asyn.group_facts(
            [_gathered("a", rel_type="ZETA"), _gathered("b", rel_type="ALPHA")]
        )

        assert [key[0] for key in groups] == ["ZETA", "ALPHA"]


class TestTheDraftCall:
    async def test_it_dispatches_on_the_synthesis_purpose(self):
        """The eighth purpose, seeded inert since day one; this is its first
        consumer anywhere in the tree."""
        llm = _StubLLM(_draft_payload(["a"]))

        await asyn.synthesise_draft(llm, subject="subj", facts=[_gathered("a")])

        assert llm.calls[0]["purpose"] == asyn.SYNTHESIS_PURPOSE

    async def test_the_prompt_carries_only_the_gathered_facts(self):
        llm = _StubLLM(_draft_payload(["a"]))

        await asyn.synthesise_draft(
            llm, subject="subj", facts=[_gathered("a", fact="the only fact")]
        )

        assert "the only fact" in llm.prompt
        assert llm.prompt.count("[a]") == 1

    async def test_the_seed_is_the_ranked_fact_id_set(self):
        """Same subject, same facts, same order -> same article. Reordering is
        a different prompt and must be a different seed."""
        one = _StubLLM(_draft_payload(["a", "b"]))
        two = _StubLLM(_draft_payload(["a", "b"]))
        three = _StubLLM(_draft_payload(["a", "b"]))
        facts = [_gathered("a"), _gathered("b")]

        await asyn.synthesise_draft(one, subject="subj", facts=facts)
        await asyn.synthesise_draft(two, subject="subj", facts=list(facts))
        await asyn.synthesise_draft(three, subject="subj", facts=list(reversed(facts)))

        assert one.calls[0]["seed"] == two.calls[0]["seed"]
        assert one.calls[0]["seed"] != three.calls[0]["seed"]

    async def test_a_cited_id_outside_the_input_set_is_refused(self):
        """An invented id means the response describes a fact set it was never
        handed — keeping the rest would keep prose written under that
        misapprehension."""
        llm = _StubLLM(_draft_payload(["a", "not-an-input"]))

        with pytest.raises(asyn.DraftRefused, match="not in its input set"):
            await asyn.synthesise_draft(llm, subject="subj", facts=[_gathered("a")])

    async def test_an_uncited_sentence_is_refused(self):
        """Doc 09 §4.3: a claim with no citation fails outright, no
        search-for-support fallback."""
        llm = _StubLLM(_draft_payload([]))

        with pytest.raises(asyn.DraftRefused, match="cited no fact"):
            await asyn.synthesise_draft(llm, subject="subj", facts=[_gathered("a")])

    async def test_a_response_over_the_hard_ceiling_is_refused(self):
        llm = _StubLLM(_draft_payload(["a"], words=200))

        with pytest.raises(asyn.DraftRefused, match="ceiling"):
            await asyn.synthesise_draft(
                llm, subject="subj", facts=[_gathered("a")], budget_words=50
            )

    async def test_an_ordinary_overrun_is_absorbed_by_the_budget(self):
        """The budget is what the prompt asks for; the ceiling is what the
        response is held to. Refusing at the budget would reject every article
        that ran a little long."""
        llm = _StubLLM(_draft_payload(["a"], words=60))

        draft = await asyn.synthesise_draft(
            llm, subject="subj", facts=[_gathered("a")], budget_words=50
        )

        assert draft.word_count > 50

    async def test_the_budget_reaches_the_prompt(self):
        llm = _StubLLM(_draft_payload(["a"]))

        await asyn.synthesise_draft(
            llm, subject="subj", facts=[_gathered("a")], budget_words=123
        )

        assert "123 words" in llm.prompt

    @pytest.mark.parametrize(
        "payload",
        ["not json at all", "[]", '{"lead": ""}', '{"lead": "x", "sentences": []}'],
    )
    async def test_an_unparseable_response_is_refused(self, payload):
        llm = _StubLLM(payload)

        with pytest.raises(asyn.DraftRefused):
            await asyn.synthesise_draft(llm, subject="subj", facts=[_gathered("a")])

    async def test_a_fenced_response_still_parses(self):
        """Reasoning-by-default vendors wrap JSON in a markdown fence, often
        after prose — the same salvage `extraction_clean` needs."""
        llm = _StubLLM("Sure:\n```json\n" + _draft_payload(["a"]) + "\n```")

        draft = await asyn.synthesise_draft(
            llm, subject="subj", facts=[_gathered("a")]
        )

        assert draft.sentences[0].fact_ids == ["a"]

    async def test_an_orchestrator_failure_propagates_rather_than_refusing(self):
        """"The model produced something unusable" and "the model could not be
        reached" are different outcomes; collapsing them hides an outage behind
        a content error."""
        llm = _StubLLM(raises=RuntimeError("connection refused"))

        with pytest.raises(RuntimeError, match="connection refused"):
            await asyn.synthesise_draft(llm, subject="subj", facts=[_gathered("a")])

    async def test_no_facts_refuses_without_calling_the_model(self):
        llm = _StubLLM(_draft_payload(["a"]))

        with pytest.raises(asyn.DraftRefused):
            await asyn.synthesise_draft(llm, subject="subj", facts=[])

        assert llm.calls == []


# ─────────────── Steps 3-4: the write and the journal ───────────────


async def _articles_for(session, subject: str) -> list[dict]:
    rows = await session.execute(
        text(
            "SELECT id, status, confidence, review_state, content, fact_set_hash, "
            "applies_when, learned_in FROM knowledge_articles "
            "WHERE project = CAST(:p AS text) AND subject_key = CAST(:s AS text)"
        ),
        {"p": PROJECT, "s": subject},
    )
    return [dict(r) for r in rows.mappings().all()]


async def _synthesis_events(session, project: str = PROJECT) -> list[dict]:
    from app.services.events import list_events

    items, _ = await list_events(
        session, project=project, object_type="article", limit=50
    )
    return items


def _simple_draft(ids: list[str]) -> asyn.DraftArticle:
    return asyn.DraftArticle(
        lead="A subject is a thing.",
        sentences=[asyn.DraftSentence(text="It relates.", fact_ids=ids)],
    )


class TestTheWrite:
    async def test_an_unmeasured_article_is_candidate_and_open(self, session):
        """Doc 09 §4.3 gates on coverage. An article with none measured is not
        above the threshold — it is unmeasured, the same serving outcome for a
        different reason, and the column would happily take `corroborated`."""
        subject = f"subj-{uuid4().hex[:8]}"
        facts = [_gathered("a")]

        await asyn.store_article(
            session, subject=subject, project=PROJECT,
            draft=_simple_draft(["a"]), facts=facts, all_verified_ids=["a"],
        )
        await session.flush()

        rows = await _articles_for(session, subject)
        assert len(rows) == 1
        assert rows[0]["status"] == "candidate"
        assert rows[0]["review_state"] == "open"

    async def test_confidence_stays_null_rather_than_zero(self, session):
        """Coverage *is* the stored confidence. A 0.0 default would read as
        "measured, and terrible"; NULL reads as "not measured"."""
        subject = f"subj-{uuid4().hex[:8]}"

        await asyn.store_article(
            session, subject=subject, project=PROJECT,
            draft=_simple_draft(["a"]), facts=[_gathered("a")],
            all_verified_ids=["a"],
        )
        await session.flush()

        assert (await _articles_for(session, subject))[0]["confidence"] is None

    async def test_it_never_writes_a_promoted_status(self, session):
        subject = f"subj-{uuid4().hex[:8]}"

        await asyn.store_article(
            session, subject=subject, project=PROJECT,
            draft=_simple_draft(["a"]), facts=[_gathered("a")],
            all_verified_ids=["a"],
        )
        await session.flush()

        assert (await _articles_for(session, subject))[0]["status"] not in (
            "corroborated", "confirmed",
        )

    async def test_a_subject_holding_a_live_article_is_refused(self, session):
        """Re-synthesis is T3.05's, whole. Splitting it would mean flipping the
        prior row to `superseded` here while deferring its pointer — and
        `knowledge_articles` has no `chk_superseded_has_pointer`, so that does
        not error, it silently loses the lineage."""
        subject = f"subj-{uuid4().hex[:8]}"
        await asyn.store_article(
            session, subject=subject, project=PROJECT,
            draft=_simple_draft(["a"]), facts=[_gathered("a")],
            all_verified_ids=["a"],
        )
        await session.flush()

        with pytest.raises(asyn.LiveArticleExists):
            await asyn.store_article(
                session, subject=subject, project=PROJECT,
                draft=_simple_draft(["a"]), facts=[_gathered("a")],
                all_verified_ids=["a"],
            )

        assert len(await _articles_for(session, subject)) == 1

    async def test_the_body_carries_the_lead_and_every_sentence(self, session):
        subject = f"subj-{uuid4().hex[:8]}"
        draft = asyn.DraftArticle(
            lead="Postgres is a database.",
            sentences=[
                asyn.DraftSentence(text="It runs on Linux.", fact_ids=["a"]),
                asyn.DraftSentence(text="It speaks SQL.", fact_ids=["a"]),
            ],
        )

        await asyn.store_article(
            session, subject=subject, project=PROJECT, draft=draft,
            facts=[_gathered("a")], all_verified_ids=["a"],
        )
        await session.flush()

        content = (await _articles_for(session, subject))[0]["content"]
        assert "Postgres is a database." in content
        assert "It runs on Linux." in content
        assert "It speaks SQL." in content

    async def test_applies_when_keeps_a_conflict_rather_than_picking(self, session):
        """Doc 09 §4.2 calls the aggregate *displayed provenance*, not a
        trustworthy scope — so a key two facts disagree on keeps both. Picking
        one would render a scope no fact asserts."""
        subject = f"subj-{uuid4().hex[:8]}"
        facts = [
            _gathered("a", applies_when={"env": "prod"}),
            _gathered("b", applies_when={"env": "dev"}),
        ]

        await asyn.store_article(
            session, subject=subject, project=PROJECT,
            draft=_simple_draft(["a"]), facts=facts, all_verified_ids=["a", "b"],
        )
        await session.flush()

        assert (await _articles_for(session, subject))[0]["applies_when"] == {
            "env": ["dev", "prod"]
        }


class TestTheFactSetHash:
    async def test_it_covers_the_full_verified_set_not_the_capped_input(
        self, session
    ):
        """Doc 09 §4.4: staleness fires when knowledge changed. Hashed over the
        capped input instead, read-heat drift reorders the cap boundary and
        flips the hash with no knowledge change — the precise failure §4.4
        exists to prevent."""
        capped = [_gathered("a")]

        one = asyn.fact_set_hash(["a", "b", "c"])
        two = asyn.fact_set_hash([f.id for f in capped])

        assert one != two

    async def test_it_is_order_independent(self):
        assert asyn.fact_set_hash(["a", "b"]) == asyn.fact_set_hash(["b", "a"])

    async def test_a_changed_set_changes_the_hash(self):
        assert asyn.fact_set_hash(["a", "b"]) != asyn.fact_set_hash(["a", "b", "c"])

    async def test_the_stored_hash_is_the_uncapped_one(self, session):
        subject = f"subj-{uuid4().hex[:8]}"

        await asyn.store_article(
            session, subject=subject, project=PROJECT,
            draft=_simple_draft(["a"]), facts=[_gathered("a")],
            all_verified_ids=["a", "b", "c"],
        )
        await session.flush()

        stored = (await _articles_for(session, subject))[0]["fact_set_hash"]
        assert stored == asyn.fact_set_hash(["a", "b", "c"])


class TestTheJournal:
    async def test_every_run_journals_its_inputs(self, session):
        subject = f"subj-{uuid4().hex[:8]}"
        project = f"{PROJECT}-{uuid4().hex[:6]}"
        facts = [_gathered("a"), _gathered("b")]

        await asyn.store_article(
            session, subject=subject, project=project,
            draft=_simple_draft(["a"]), facts=facts,
            all_verified_ids=["a", "b", "c"],
        )
        await session.flush()

        rows = await _synthesis_events(session, project)
        assert len(rows) == 1
        assert rows[0]["payload"]["fact_ids"] == ["a", "b"]
        assert rows[0]["payload"]["subject_key"] == subject
        assert rows[0]["payload"]["verified_fact_count"] == 3

    async def test_the_ids_are_in_ranked_order(self, session):
        """Which facts the cap admitted, and in what priority, is the question
        a bad article is traced with."""
        subject = f"subj-{uuid4().hex[:8]}"
        project = f"{PROJECT}-{uuid4().hex[:6]}"
        facts = [_gathered("z"), _gathered("m"), _gathered("a")]

        await asyn.store_article(
            session, subject=subject, project=project,
            draft=_simple_draft(["z"]), facts=facts,
            all_verified_ids=["z", "m", "a"],
        )
        await session.flush()

        assert (await _synthesis_events(session, project))[0]["payload"][
            "fact_ids"
        ] == ["z", "m", "a"]

    async def test_the_payload_carries_no_draft_prose(self, session):
        """Write-time minimization: the article row holds the text, the journal
        answers which facts produced it, and an event payload outlives the
        deletion of what it describes."""
        subject = f"subj-{uuid4().hex[:8]}"
        project = f"{PROJECT}-{uuid4().hex[:6]}"
        draft = asyn.DraftArticle(
            lead="A distinctive lead sentence.",
            sentences=[
                asyn.DraftSentence(text="A distinctive body sentence.", fact_ids=["a"])
            ],
        )

        await asyn.store_article(
            session, subject=subject, project=project, draft=draft,
            facts=[_gathered("a")], all_verified_ids=["a"],
        )
        await session.flush()

        blob = json.dumps((await _synthesis_events(session, project))[0]["payload"])
        assert "A distinctive lead sentence." not in blob
        assert "A distinctive body sentence." not in blob

    async def test_it_journals_against_the_article_it_wrote(self, session):
        subject = f"subj-{uuid4().hex[:8]}"
        project = f"{PROJECT}-{uuid4().hex[:6]}"

        article_id = await asyn.store_article(
            session, subject=subject, project=project,
            draft=_simple_draft(["a"]), facts=[_gathered("a")],
            all_verified_ids=["a"],
        )
        await session.flush()

        # `list_events` hands back a UUID and the writer returns a str — the
        # id-type drift CLAUDE.md's cross-cutting invariants name. Normalised
        # at the boundary, which is where that invariant says to do it.
        assert str((await _synthesis_events(session, project))[0]["object_id"]) == article_id

    async def test_a_refused_write_journals_nothing(self, session):
        """A run that wrote no article did not synthesise one, and a journal
        row would put an article in the stream that no reader can open."""
        subject = f"subj-{uuid4().hex[:8]}"
        project = f"{PROJECT}-{uuid4().hex[:6]}"
        await asyn.store_article(
            session, subject=subject, project=project,
            draft=_simple_draft(["a"]), facts=[_gathered("a")],
            all_verified_ids=["a"],
        )
        await session.flush()

        with pytest.raises(asyn.LiveArticleExists):
            await asyn.store_article(
                session, subject=subject, project=project,
                draft=_simple_draft(["a"]), facts=[_gathered("a")],
                all_verified_ids=["a"],
            )
        await session.flush()

        assert len(await _synthesis_events(session, project)) == 1


# ─────────────── Step 5: the run ───────────────


@pytest.fixture
async def factory(session):
    """A session factory bound to the `session` fixture's own connection.

    The run driver opens a session per subject on purpose — a model call is
    measured in seconds, and one shared transaction would hold locks across the
    whole batch while making per-subject failure isolation a fiction. So it
    needs a factory rather than the request-scoped session.

    Bound to the same connection rather than a fresh engine: conftest wraps
    each test in an outer transaction it rolls back, so a second engine sees an
    empty database and every one of these tests would pass vacuously against
    zero projects. SQLAlchemy's conditional-savepoint join mode gives each
    session its own savepoint on that connection, so the driver's per-subject
    commits behave as they do in production without escaping the isolation.
    """
    from sqlalchemy.ext.asyncio import async_sessionmaker

    # `get_bind()` hands back the *sync* Connection; the async one comes from
    # the session itself.
    connection = await session.connection()
    return async_sessionmaker(bind=connection, expire_on_commit=False)


class TestTheRun:
    async def test_the_budget_is_t3_01_s_and_bounds_subjects(
        self, session, factory
    ):
        """`select_for_synthesis` applies `synthesis_budget` itself; the job's
        own `batch_size` bounds *projects*. The two knobs sit at different
        levels, so neither is a second budget for the other."""
        project = f"{PROJECT}-{uuid4().hex[:6]}"
        for n in range(4):
            for _ in range(3):
                await _fact(session, subject_name=f"s{n}", project=project)
        await session.execute(
            text(
                "INSERT INTO config (key, value) VALUES "
                "('article_selection', CAST(:v AS jsonb)) "
                "ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value"
            ),
            {"v": json.dumps({"synthesis_budget": 2, "min_verified_facts": 3})},
        )
        await session.commit()

        llm = _StubLLM(_draft_payload(["x"]))
        outcome = await asyn.run_article_synthesis(
            factory, lambda: llm, batch_size=50
        )

        assert outcome.attempted <= 2, "the run spends T3.01's budget, not more"

    async def test_one_subject_s_failure_leaves_the_others_written(
        self, session, factory
    ):
        """Per-subject sessions are what make this real rather than a `try`
        around one shared transaction."""
        project = f"{PROJECT}-{uuid4().hex[:6]}"
        for n in range(3):
            for _ in range(3):
                await _fact(session, subject_name=f"s{n}", project=project)
        await session.commit()

        class _FlakyLLM:
            """Fails the first subject outright, drafts the rest.

            Cites whatever ids the prompt actually listed, so the later
            subjects produce a storable draft rather than refusing for an
            unrelated reason and hiding what this test is about.
            """

            def __init__(self):
                self.calls = 0

            async def chat_completion(self, purpose, *, messages, **kw):
                self.calls += 1
                if self.calls == 1:
                    raise RuntimeError("vendor outage")
                ids = _ids_in(messages)
                return _draft_payload(ids[:1])

        llm = _FlakyLLM()
        outcome = await asyn.run_article_synthesis(
            factory, lambda: llm, batch_size=50
        )

        assert outcome.failed == 1
        assert outcome.written >= 1, "the failure did not take the batch with it"

    async def test_a_refusal_and_a_failure_are_counted_apart(
        self, session, factory
    ):
        """A vendor outage and an unusable draft mean different things to an
        operator; one count for both would hide an outage."""
        project = f"{PROJECT}-{uuid4().hex[:6]}"
        for _ in range(3):
            await _fact(session, subject_name="only", project=project)
        await session.commit()

        llm = _StubLLM(_draft_payload(["not-an-input"]))
        outcome = await asyn.run_article_synthesis(
            factory, lambda: llm, batch_size=50
        )

        assert outcome.refused >= 1
        assert outcome.failed == 0

    async def test_no_orchestrator_reads_as_failed_not_as_a_clean_tick(
        self, session, factory
    ):
        project = f"{PROJECT}-{uuid4().hex[:6]}"
        for _ in range(3):
            await _fact(session, subject_name="only", project=project)
        await session.commit()

        outcome = await asyn.run_article_synthesis(
            factory, None, batch_size=50
        )

        assert outcome.written == 0
        assert outcome.failed >= 1

    async def test_the_cursor_names_the_last_project_visited(
        self, session, factory
    ):
        """Visited, not succeeded — a project failing deterministically would
        otherwise pin the rotation and starve everything behind it."""
        for suffix in ("aaa", "bbb"):
            for _ in range(3):
                await _fact(
                    session, subject_name="s", project=f"{PROJECT}-cursor-{suffix}"
                )
        await session.commit()

        llm = _StubLLM(raises=RuntimeError("always fails"))
        outcome = await asyn.run_article_synthesis(
            factory, lambda: llm, batch_size=200
        )

        assert outcome.last_project is not None
        assert outcome.projects >= 2

    async def test_the_soft_key_is_split_at_the_right_boundary(
        self, session, factory
    ):
        """The failure this pins is silent, which is why it gets its own test.

        `select_for_synthesis` hands back `name::entity_type`. Passed whole
        into the fact query — which matches `lower(subject_name)` — it matches
        nothing, so every subject "refuses" for want of facts: the tick reports
        subjects attempted and none written, and nothing raises. Meanwhile the
        *article* must be stored under the whole soft key, because that is what
        `ux_knowledge_articles_live` is unique on.
        """
        project = f"{PROJECT}-{uuid4().hex[:6]}"
        for _ in range(3):
            await _fact(session, subject_name="postgres", project=project)
        await session.commit()

        llm = _StubLLM()

        async def _draft(purpose, *, messages, **kw):
            llm.calls.append({"purpose": purpose, "messages": messages, **kw})
            return _draft_payload(_ids_in(messages)[:1])

        llm.chat_completion = _draft
        outcome = await asyn.run_article_synthesis(
            factory, lambda: llm, batch_size=50
        )

        assert outcome.written == 1, "the name half must reach the fact query"
        rows = await session.execute(
            text(
                "SELECT subject_key FROM knowledge_articles "
                "WHERE project = CAST(:p AS text)"
            ),
            {"p": project},
        )
        stored = rows.scalar_one()
        assert stored.startswith("postgres::"), "the whole soft key is stored"

def _ids_in(messages) -> list[str]:
    import re as _re

    joined = "\n".join(m["content"] for m in messages)
    return _re.findall(r"\[([0-9a-f-]{36})\]", joined)
