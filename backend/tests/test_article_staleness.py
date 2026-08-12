"""T3.05 — the staleness gate and debounced re-synthesis (doc 09 §4.4).

Three properties, and each is asserted against the failure it prevents rather
than against the happy path:

* **The gate is the verified set.** A churning candidate must not move the
  hash — otherwise a hub subject re-synthesises on nearly every ingest, which
  is the cost §4.4 exists to avoid, and it fails silently as a bill rather than
  as an error.
* **The debounce is a quiet period, not a rate limit.** A burst that is still
  arriving must not produce a re-synthesis per tick, so the window has to
  restart when the fact set moves again.
* **Re-synthesis supersedes rather than mutating, and never loses a good
  article.** The prior row survives with a pointer to its replacement, and a
  draft that fails grounding leaves the standing article exactly where it was.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from sqlalchemy import text

from app.repositories.knowledge_triples import KnowledgeTripleRepository
from app.services import article_synthesis as ast_
from app.services import article_synthesis as asyn
from app.services.verification_judge import ENTAILMENT_ROLE, ProbeVerdict

pytestmark = pytest.mark.asyncio

T0 = datetime(2026, 6, 1, 12, 0, 0, tzinfo=timezone.utc)
# The debounce reads its own journal row back, and `record_event` stamps that
# row with the database clock — it takes no caller timestamp, and widening the
# one journal writer so a test could fast-forward it would be the tail wagging
# the audit substrate. So the debounce tests measure from *now* and move the
# comparison forward, which is also the direction production moves.
NOW = datetime.now(timezone.utc)
PROJECT = "t3-05-staleness"
SUBJECT = "postgres"
SUBJECT_KEY = f"{SUBJECT}::concept"


async def _fact(
    session, *, status: str = "corroborated", subject_name: str = SUBJECT,
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
    )
    await session.execute(
        text(
            "UPDATE knowledge_triples SET verification_status = CAST(:s AS text) "
            "WHERE id = CAST(:id AS uuid)"
        ),
        {"s": status, "id": row["id"]},
    )
    await session.flush()
    return str(row["id"])


async def _article(
    session, *, fact_set_hash: str, subject_key: str = SUBJECT_KEY,
    status: str = "corroborated", project: str = PROJECT,
) -> str:
    article_id = str(uuid4())
    await session.execute(
        text(
            "INSERT INTO knowledge_articles "
            "(id, subject_key, project, title, content, status, review_state, "
            " fact_set_hash, synthesized_at) "
            "VALUES (CAST(:id AS uuid), CAST(:k AS text), CAST(:p AS text), "
            "CAST(:k AS text), 'standing body', CAST(:st AS text), NULL, "
            "CAST(:h AS text), CAST(:now AS timestamptz))"
        ),
        {
            "id": article_id, "k": subject_key, "p": project, "st": status,
            "h": fact_set_hash, "now": T0,
        },
    )
    await session.flush()
    return article_id


async def _current_hash(session, *, project: str = PROJECT) -> str:
    return asyn.fact_set_hash(
        await asyn.all_verified_fact_ids(session, subject=SUBJECT, project=project)
    )


class _StubLLM:
    def __init__(self, fact_ids: list[str]):
        self.payload = json.dumps(
            {
                "lead": {"text": "A re-synthesised lead.", "fact_ids": fact_ids},
                "sentences": [
                    {"text": "A re-synthesised claim.", "fact_ids": fact_ids}
                ],
            }
        )
        self.embedded: list[str] = []

    async def chat_completion(self, purpose, *, messages, response_format=None, seed=None):
        return self.payload

    async def embed(self, text_body):
        self.embedded.append(text_body)
        raise RuntimeError("no embedder in this suite")


@pytest.fixture
async def factory(session):
    """A session factory on the `session` fixture's own connection.

    Same reasoning as `test_article_synthesis`'s: the pass opens a session per
    subject, and a second engine would see an empty database behind conftest's
    outer transaction — every driver test would then pass vacuously against
    zero projects.
    """
    from sqlalchemy.ext.asyncio import async_sessionmaker

    connection = await session.connection()
    return async_sessionmaker(bind=connection, expire_on_commit=False)


class _StubJudge:
    """Answers every pair the same way. `None` stands for a refusing judge."""

    def __init__(self, verdict: str | None):
        self.verdict = verdict

    async def judge(self, session, premise, hypothesis, *, role):
        # Enforced, not merely accepted: the resynthesis path measures article
        # coverage, so it must ask as the entailment role (doc 17 §6, amended
        # 2026-08-12). A stub that shrugged at the role would let a wrong-role
        # call read as a vendor outage here — `measure_coverage` turns any
        # exception into UNMEASURED, which is exactly how this went unnoticed.
        assert role == ENTAILMENT_ROLE
        if self.verdict is None:
            return ProbeVerdict(verdict=None, reason=None, raw="", valid=False)
        return ProbeVerdict(
            verdict=self.verdict, reason=None, raw=self.verdict, valid=True
        )


# ─────────────── the gate is the verified set ───────────────


class TestTheStalenessGate:
    async def test_a_matching_fact_set_is_not_stale(self, session):
        await _fact(session)
        await _article(session, fact_set_hash=await _current_hash(session))

        assert await ast_.stale_articles(session, project=PROJECT) == []

    async def test_a_new_verified_fact_makes_it_stale(self, session):
        await _fact(session)
        await _article(session, fact_set_hash=await _current_hash(session))

        await _fact(session)

        stale = await ast_.stale_articles(session, project=PROJECT)
        assert [a.subject_key for a in stale] == [SUBJECT_KEY]

    async def test_churning_candidates_never_move_the_hash(self, session):
        """The done-when's own test, and the reason the gate exists: a hub
        subject would otherwise re-synthesise on nearly every ingest."""
        await _fact(session)
        await _article(session, fact_set_hash=await _current_hash(session))

        for _ in range(5):
            await _fact(session, status="candidate")
        await _fact(session, status="disputed")

        assert await ast_.stale_articles(session, project=PROJECT) == []

    async def test_an_invalidated_fact_makes_it_stale(self, session):
        """§4.4's fourth trigger, live since the 2026-08-11 ruling."""
        fact_id = await _fact(session)
        await _fact(session)
        await _article(session, fact_set_hash=await _current_hash(session))

        await session.execute(
            text(
                "UPDATE knowledge_triples SET invalid_at = now() "
                "WHERE id = CAST(:id AS uuid)"
            ),
            {"id": fact_id},
        )
        await session.flush()

        assert len(await ast_.stale_articles(session, project=PROJECT)) == 1

    async def test_a_superseded_article_is_not_a_candidate(self, session):
        await _fact(session)
        await _article(session, fact_set_hash="a-hash-from-before", status="superseded")

        assert await ast_.stale_articles(session, project=PROJECT) == []


# ─────────────── the debounce is a quiet period ───────────────


class TestTheDebounce:
    async def _stale(self, session) -> ast_.StaleArticle:
        await _fact(session)
        await _article(session, fact_set_hash="a-hash-from-before")
        return (await ast_.stale_articles(session, project=PROJECT))[0]

    async def test_the_first_observation_labels_and_waits(self, session):
        article = await self._stale(session)

        settled = await ast_.staleness_settled(
            session, article, project=PROJECT, debounce_hours=24, now=NOW
        )

        assert settled is False
        journalled = (
            await session.execute(
                text(
                    "SELECT payload FROM events WHERE object_id = CAST(:id AS uuid) "
                    "AND event_type = 'article_stale'"
                ),
                {"id": article.article_id},
            )
        ).scalars().all()
        assert [p["fact_set_hash"] for p in journalled] == [article.current_hash]

    async def test_the_same_set_after_the_window_is_settled(self, session):
        article = await self._stale(session)
        await ast_.staleness_settled(
            session, article, project=PROJECT, debounce_hours=24, now=NOW
        )

        assert await ast_.staleness_settled(
            session, article, project=PROJECT, debounce_hours=24,
            now=NOW + timedelta(hours=25),
        )

    async def test_the_same_set_inside_the_window_is_not(self, session):
        article = await self._stale(session)
        await ast_.staleness_settled(
            session, article, project=PROJECT, debounce_hours=24, now=NOW
        )

        assert not await ast_.staleness_settled(
            session, article, project=PROJECT, debounce_hours=24,
            now=NOW + timedelta(hours=23),
        )

    async def test_a_burst_restarts_the_window(self, session):
        """The property that makes this a quiet period rather than a rate
        limit: a fact set still moving at the end of the window does not
        re-synthesise, because the window began again when it moved."""
        article = await self._stale(session)
        await ast_.staleness_settled(
            session, article, project=PROJECT, debounce_hours=24, now=NOW
        )

        await _fact(session)
        moved = (await ast_.stale_articles(session, project=PROJECT))[0]
        assert moved.current_hash != article.current_hash

        # A full window has passed since the *first* observation, and it still
        # must not fire — the set changed inside it.
        assert not await ast_.staleness_settled(
            session, moved, project=PROJECT, debounce_hours=24,
            now=NOW + timedelta(hours=25),
        )
        # …and one window after the *last* move, it does.
        assert await ast_.staleness_settled(
            session, moved, project=PROJECT, debounce_hours=24,
            now=NOW + timedelta(hours=50),
        )


# ─────────────── re-synthesis supersedes, and keeps lineage ───────────────


async def _standing(session) -> tuple[str, ast_.StaleArticle, list[str]]:
    fact_ids = [await _fact(session), await _fact(session)]
    article_id = await _article(session, fact_set_hash="a-hash-from-before")
    stale = (await ast_.stale_articles(session, project=PROJECT))[0]
    return article_id, stale, fact_ids


class TestResynthesis:
    async def test_it_supersedes_the_prior_and_keeps_the_pointer(self, session):
        prior_id, stale, fact_ids = await _standing(session)

        new_id, reason = await ast_.resynthesise_subject(
            session, _StubLLM(fact_ids), _StubJudge("entailed"), stale,
            project=PROJECT, now=T0,
        )

        assert new_id is not None and new_id != prior_id
        row = (
            await session.execute(
                text(
                    "SELECT status, superseded_by, content FROM knowledge_articles "
                    "WHERE id = CAST(:id AS uuid)"
                ),
                {"id": prior_id},
            )
        ).mappings().one()
        assert row["status"] == "superseded"
        assert str(row["superseded_by"]) == new_id
        # Superseded, not mutated: the prior text is still the prior text.
        assert row["content"] == "standing body"

    async def test_the_replacement_carries_the_current_hash(self, session):
        _prior, stale, fact_ids = await _standing(session)

        new_id, _reason = await ast_.resynthesise_subject(
            session, _StubLLM(fact_ids), _StubJudge("entailed"), stale,
            project=PROJECT, now=T0,
        )

        stored = (
            await session.execute(
                text(
                    "SELECT fact_set_hash FROM knowledge_articles "
                    "WHERE id = CAST(:id AS uuid)"
                ),
                {"id": new_id},
            )
        ).scalar_one()
        assert stored == await _current_hash(session)
        # …so the subject is no longer stale, which is what ends the cycle.
        assert await ast_.stale_articles(session, project=PROJECT) == []

    async def test_exactly_one_live_article_survives(self, session):
        """`ux_knowledge_articles_live` is the constraint, and the ordering of
        the three writes is what keeps the insert legal."""
        _prior, stale, fact_ids = await _standing(session)

        await ast_.resynthesise_subject(
            session, _StubLLM(fact_ids), _StubJudge("entailed"), stale,
            project=PROJECT, now=T0,
        )

        live = (
            await session.execute(
                text(
                    "SELECT COUNT(*) FROM knowledge_articles "
                    "WHERE project = CAST(:p AS text) AND status <> 'superseded'"
                ),
                {"p": PROJECT},
            )
        ).scalar_one()
        assert live == 1

    async def test_a_held_draft_does_not_supersede(self, session):
        """§4.4's own rule: a subject never loses a good article to a bad
        re-synthesis. The judge answering `unsupported` puts coverage at 0."""
        prior_id, stale, fact_ids = await _standing(session)

        new_id, reason = await ast_.resynthesise_subject(
            session, _StubLLM(fact_ids), _StubJudge("unsupported"), stale,
            project=PROJECT, now=T0,
        )

        assert (new_id, reason) == (None, "held")
        status = (
            await session.execute(
                text(
                    "SELECT status FROM knowledge_articles WHERE id = CAST(:id AS uuid)"
                ),
                {"id": prior_id},
            )
        ).scalar_one()
        assert status == "corroborated"

    async def test_an_unmeasured_draft_will_not_retire_a_measured_article(
        self, session
    ):
        """Review finding F2. The freeze argument licenses superseding on an
        unmeasured outcome only where nothing is lost — candidate over
        candidate. One transient judge outage must not trade a *measured*
        article for prose nothing measured, because coverage runs at synthesis
        only: there is no path that would measure it back."""
        prior_id, stale, fact_ids = await _standing(session)
        await session.execute(
            text(
                "UPDATE knowledge_articles SET confidence = 0.98 "
                "WHERE id = CAST(:id AS uuid)"
            ),
            {"id": prior_id},
        )
        await session.flush()

        new_id, reason = await ast_.resynthesise_subject(
            session, _StubLLM(fact_ids), _StubJudge(None), stale,
            project=PROJECT, now=T0,
        )

        assert (new_id, reason) == (None, "standing_measured")
        row = (
            await session.execute(
                text(
                    "SELECT status, confidence FROM knowledge_articles "
                    "WHERE id = CAST(:id AS uuid)"
                ),
                {"id": prior_id},
            )
        ).mappings().one()
        assert row["status"] == "corroborated"
        assert row["confidence"] == pytest.approx(0.98, abs=1e-6)

    async def test_a_measured_draft_may_replace_a_measured_article(self, session):
        """The narrowing is about *unmeasured* drafts only — a re-synthesis
        that cleared the gate supersedes exactly as before."""
        prior_id, stale, fact_ids = await _standing(session)
        await session.execute(
            text(
                "UPDATE knowledge_articles SET confidence = 0.98 "
                "WHERE id = CAST(:id AS uuid)"
            ),
            {"id": prior_id},
        )
        await session.flush()

        new_id, _reason = await ast_.resynthesise_subject(
            session, _StubLLM(fact_ids), _StubJudge("entailed"), stale,
            project=PROJECT, now=T0,
        )

        assert new_id is not None
        assert (
            await session.execute(
                text("SELECT status FROM knowledge_articles WHERE id = CAST(:id AS uuid)"),
                {"id": prior_id},
            )
        ).scalar_one() == "superseded"

    async def test_a_refusing_judge_still_supersedes_unmeasured(self, session):
        """With G-D open every measurement refuses. Holding on that would
        freeze L3 at its first article on every install, permanently, for a
        gate that governs a badge."""
        _prior, stale, fact_ids = await _standing(session)

        new_id, reason = await ast_.resynthesise_subject(
            session, _StubLLM(fact_ids), _StubJudge(None), stale,
            project=PROJECT, now=T0,
        )

        assert new_id is not None and reason == "unmeasured"
        row = (
            await session.execute(
                text(
                    "SELECT status, review_state, confidence FROM knowledge_articles "
                    "WHERE id = CAST(:id AS uuid)"
                ),
                {"id": new_id},
            )
        ).mappings().one()
        assert (row["status"], row["review_state"]) == ("candidate", "open")
        assert row["confidence"] is None

    async def test_a_subject_with_no_facts_left_keeps_its_article(self, session):
        """The strongest staleness — the knowledge is gone — must not delete
        the write-up. It is labelled and left readable."""
        prior_id = await _article(session, fact_set_hash="a-hash-from-before")
        stale = (await ast_.stale_articles(session, project=PROJECT))[0]

        new_id, reason = await ast_.resynthesise_subject(
            session, _StubLLM([]), _StubJudge("entailed"), stale,
            project=PROJECT, now=T0,
        )

        assert (new_id, reason) == (None, "no_facts")
        assert (
            await session.execute(
                text(
                    "SELECT status FROM knowledge_articles WHERE id = CAST(:id AS uuid)"
                ),
                {"id": prior_id},
            )
        ).scalar_one() == "corroborated"

    async def test_the_supersession_journals_its_lineage(self, session):
        prior_id, stale, fact_ids = await _standing(session)

        new_id, _reason = await ast_.resynthesise_subject(
            session, _StubLLM(fact_ids), _StubJudge("entailed"), stale,
            project=PROJECT, now=T0,
        )

        payload = (
            await session.execute(
                text(
                    "SELECT payload FROM events WHERE object_id = CAST(:id AS uuid) "
                    "AND event_type = 'superseded'"
                ),
                {"id": prior_id},
            )
        ).scalars().one()
        assert payload["superseded_by"] == new_id
        assert payload["subject_key"] == SUBJECT_KEY


# ─────────────── the window is a config row, and it is wired ───────────────


class TestTheConfigRow:
    """Review finding F3: the done-when's own artifact had no test.

    The field's *existence* and the runner's *forwarding* are asserted apart,
    because a schema entry nothing reads is exactly the shape that passes a
    schema test while the knob does nothing.
    """

    async def test_the_window_is_a_field_on_the_job_schema(self):
        from app.services.dream_jobs import ARTICLE_SYNTHESIS_CONFIG_SCHEMA

        field = next(
            f for f in ARTICLE_SYNTHESIS_CONFIG_SCHEMA if f.key == "debounce_hours"
        )
        assert field.default == ast_.DEFAULT_DEBOUNCE_HOURS
        assert field.min == 1

    async def test_the_runner_forwards_it_from_that_row(self):
        import ast as pyast
        import inspect
        import textwrap

        from app.services import dream_jobs

        source = inspect.getsource(dream_jobs._make_article_runner)
        tree = pyast.parse(textwrap.dedent(source))
        forwarded = {
            keyword.arg
            for node in pyast.walk(tree)
            if isinstance(node, pyast.Call)
            and getattr(node.func, "id", None) == "run_article_resynthesis"
            for keyword in node.keywords
        }
        assert "debounce_hours" in forwarded

    async def test_the_default_is_stated_once(self):
        """Three copies of 24 was the shape review finding F5 named."""
        from app.services import dream_jobs

        assert dream_jobs.DEFAULT_DEBOUNCE_HOURS is ast_.DEFAULT_DEBOUNCE_HOURS


# ─────────────── the window and its own lookback ───────────────


class TestTheAnchorLookback:
    """Review finding F1. The anchor read is bounded so it does not scan every
    monthly `events` child, and that bound must always exceed the window — a
    fixed 90 days silently disabled re-synthesis for any longer window, and it
    failed *quietly*: the `debounced` counter climbing reads exactly like the
    damping working."""

    async def test_the_lookback_always_exceeds_the_window(self):
        for hours in (1, 24, 24 * 90, 24 * 365, 8760):
            assert ast_._anchor_lookback(hours) > timedelta(hours=hours), hours

    async def test_it_holds_the_floor_for_short_windows(self):
        assert ast_._anchor_lookback(1) == timedelta(days=90)

    async def test_a_year_long_window_still_settles(self, session):
        """The config admits 8760 hours. Before the fix this could not return
        True on any path, for any corpus."""
        await _fact(session)
        await _article(session, fact_set_hash="a-hash-from-before")
        article = (await ast_.stale_articles(session, project=PROJECT))[0]

        assert not await ast_.staleness_settled(
            session, article, project=PROJECT, debounce_hours=8760, now=NOW
        )
        assert await ast_.staleness_settled(
            session, article, project=PROJECT, debounce_hours=8760,
            now=NOW + timedelta(hours=8761),
        )


# ─────────────── the pass, end to end ───────────────


class TestThePass:
    async def test_a_stale_subject_needs_two_ticks(self, session, factory):
        """The first tick labels, the second re-synthesises. That is the
        debounce doing its job, not a missed run."""
        _prior, _stale, fact_ids = await _standing(session)
        await session.commit()

        first = await ast_.run_article_resynthesis(
            factory, _StubLLM(fact_ids), projects=[PROJECT],
            debounce_hours=1, now=NOW,
        )
        assert (first.stale, first.debounced, first.resynthesised) == (1, 1, 0)

        second = await ast_.run_article_resynthesis(
            factory, _StubLLM(fact_ids), projects=[PROJECT],
            debounce_hours=1, now=NOW + timedelta(hours=2),
        )
        assert (second.stale, second.resynthesised) == (1, 1)

    async def test_a_settled_corpus_is_a_clean_no_op(self, session, factory):
        await _fact(session)
        await _article(session, fact_set_hash=await _current_hash(session))
        await session.commit()

        outcome = await ast_.run_article_resynthesis(
            factory, _StubLLM([]), projects=[PROJECT], now=T0
        )

        assert (outcome.stale, outcome.attempted, outcome.failed) == (0, 0, 0)


# ─────────── the held marker: attention without withholding (§4.4) ─────────
#
# Doc 09 §4.4 as amended 2026-08-12. The clause "it routes to review" was
# unimplementable as written — routing the *draft* means storing it, and
# storing it means superseding the article the same sentence protects — so what
# routes is the **subject**: the standing article is marked, and deliberately
# not withheld.


async def _held_columns(session, article_id: str) -> dict:
    return (
        await session.execute(
            text(
                "SELECT status, review_state, resynthesis_held_at, "
                "resynthesis_held_coverage, resynthesis_held_hash "
                "FROM knowledge_articles WHERE id = CAST(:id AS uuid)"
            ),
            {"id": article_id},
        )
    ).mappings().one()


class TestTheHeldMarker:
    async def test_a_held_draft_marks_the_standing_article(self, session):
        prior_id, stale, fact_ids = await _standing(session)

        new_id, reason = await ast_.resynthesise_subject(
            session, _StubLLM(fact_ids), _StubJudge("unsupported"), stale,
            project=PROJECT, now=T0,
        )

        assert (new_id, reason) == (None, "held")
        row = await _held_columns(session, prior_id)
        assert row["resynthesis_held_at"] is not None
        assert row["resynthesis_held_coverage"] == pytest.approx(0.0, abs=1e-6)
        assert row["resynthesis_held_hash"] == stale.current_hash

    async def test_it_never_touches_review_state_or_status(self, session):
        """The whole reason the marker exists rather than `review_state`: doc 13
        §5.2 withholds an open article from the corroborated view, so setting it
        here would take a *good* article from readers because a *different*
        draft could not be grounded."""
        prior_id, stale, fact_ids = await _standing(session)

        await ast_.resynthesise_subject(
            session, _StubLLM(fact_ids), _StubJudge("unsupported"), stale,
            project=PROJECT, now=T0,
        )

        row = await _held_columns(session, prior_id)
        assert row["review_state"] is None
        assert row["status"] == "corroborated"

    async def test_the_marked_article_is_still_served(self, session):
        """The non-withholding proof, and the article twin of the review
        queue's a-queued-fact-stays-retrievable property."""
        from app.services import articles_read

        prior_id, stale, fact_ids = await _standing(session)
        await ast_.resynthesise_subject(
            session, _StubLLM(fact_ids), _StubJudge("unsupported"), stale,
            project=PROJECT, now=T0,
        )

        items, total = await articles_read.list_articles(session, project=PROJECT)

        assert total == 1
        assert items[0]["id"] == prior_id
        assert items[0]["resynthesis_held_at"] is not None
        # The badge is untouched: the finding is about the subject's verified
        # set, not about this prose.
        assert items[0]["status"] == "candidate"

    async def test_it_journals_the_measurement_and_never_the_prose(self, session):
        prior_id, stale, fact_ids = await _standing(session)

        await ast_.resynthesise_subject(
            session, _StubLLM(fact_ids), _StubJudge("unsupported"), stale,
            project=PROJECT, now=T0,
        )

        payload = (
            await session.execute(
                text(
                    "SELECT payload FROM events WHERE object_id = CAST(:id AS uuid) "
                    "AND event_type = 'resynthesis_held'"
                ),
                {"id": prior_id},
            )
        ).scalars().one()
        assert payload["coverage"] == pytest.approx(0.0, abs=1e-6)
        assert payload["threshold"] == pytest.approx(0.95, abs=1e-6)
        assert payload["fact_set_hash"] == stale.current_hash
        # Write-time minimization: the held draft's text exists nowhere.
        assert "A re-synthesised claim." not in json.dumps(payload)

    async def test_the_hold_opened_once_while_the_coverage_refreshes(self, session):
        """`_at` is when the hold opened — T2.112's `since` semantics — while
        the measurement and the fact set it was taken against refresh, which is
        what tells "still failing on the same knowledge" from "failing again on
        knowledge that moved"."""
        prior_id, stale, fact_ids = await _standing(session)
        await ast_.resynthesise_subject(
            session, _StubLLM(fact_ids), _StubJudge("unsupported"), stale,
            project=PROJECT, now=T0,
        )
        first = await _held_columns(session, prior_id)

        await _fact(session)
        moved = (await ast_.stale_articles(session, project=PROJECT))[0]
        await ast_.resynthesise_subject(
            session, _StubLLM(fact_ids), _StubJudge("unsupported"), moved,
            project=PROJECT, now=T0 + timedelta(days=1),
        )
        second = await _held_columns(session, prior_id)

        assert second["resynthesis_held_at"] == first["resynthesis_held_at"]
        assert second["resynthesis_held_hash"] != first["resynthesis_held_hash"]

    async def test_a_successful_resynthesis_clears_the_marker(self, session):
        """Exit one. The retirement and the clear are one statement: a
        superseded row still carrying a marker would sit in the queue's held
        lane forever, describing an article no reader can reach."""
        prior_id, stale, fact_ids = await _standing(session)
        await ast_.resynthesise_subject(
            session, _StubLLM(fact_ids), _StubJudge("unsupported"), stale,
            project=PROJECT, now=T0,
        )
        assert (await _held_columns(session, prior_id))["resynthesis_held_at"]

        await _fact(session)
        moved = (await ast_.stale_articles(session, project=PROJECT))[0]
        new_id, _reason = await ast_.resynthesise_subject(
            session, _StubLLM(fact_ids), _StubJudge("entailed"), moved,
            project=PROJECT, now=T0 + timedelta(days=2),
        )

        assert new_id is not None
        row = await _held_columns(session, prior_id)
        assert row["status"] == "superseded"
        assert row["resynthesis_held_at"] is None
        assert row["resynthesis_held_hash"] is None

    async def test_the_tick_clears_a_marker_whose_subject_stopped_being_stale(
        self, session, factory
    ):
        """Exit three, the one no re-synthesis performs: the verified set
        reverted to what the standing article was built from, so the finding
        describes nothing."""
        prior_id, stale, fact_ids = await _standing(session)
        await ast_.resynthesise_subject(
            session, _StubLLM(fact_ids), _StubJudge("unsupported"), stale,
            project=PROJECT, now=T0,
        )
        # The article's stored hash now matches the live set: not stale.
        await session.execute(
            text(
                "UPDATE knowledge_articles SET fact_set_hash = CAST(:h AS text) "
                "WHERE id = CAST(:id AS uuid)"
            ),
            {"h": await _current_hash(session), "id": prior_id},
        )
        await session.commit()

        outcome = await ast_.run_article_resynthesis(
            factory, _StubLLM(fact_ids), projects=[PROJECT], now=NOW,
        )

        assert outcome.cleared == 1
        assert (await _held_columns(session, prior_id))["resynthesis_held_at"] is None

    async def test_the_same_fact_set_is_not_re_attempted(self, session, factory):
        """The retry policy the routing licenses. Before it, a chronically
        ungroundable subject paid one draft plus a full entailment pass every
        tick, forever, discarded, with an in-memory counter as its only trace."""
        _prior, stale, fact_ids = await _standing(session)
        await ast_.resynthesise_subject(
            session, _StubLLM(fact_ids), _StubJudge("unsupported"), stale,
            project=PROJECT, now=T0,
        )
        await session.commit()

        outcome = await ast_.run_article_resynthesis(
            factory, _StubLLM(fact_ids), projects=[PROJECT],
            debounce_hours=1, now=NOW + timedelta(hours=48),
        )

        assert outcome.held_suppressed == 1
        assert outcome.attempted == 0

    async def test_a_moved_fact_set_is_attempted_again(self, session, factory):
        """...and the suppression is keyed on the knowledge, not on a clock, so
        it lifts exactly when there is something new to attempt."""
        _prior, stale, fact_ids = await _standing(session)
        await ast_.resynthesise_subject(
            session, _StubLLM(fact_ids), _StubJudge("unsupported"), stale,
            project=PROJECT, now=T0,
        )
        await _fact(session)
        await session.commit()

        first = await ast_.run_article_resynthesis(
            factory, _StubLLM(fact_ids), projects=[PROJECT],
            debounce_hours=1, now=NOW,
        )
        second = await ast_.run_article_resynthesis(
            factory, _StubLLM(fact_ids), projects=[PROJECT],
            debounce_hours=1, now=NOW + timedelta(hours=48),
        )

        assert first.held_suppressed == 0
        assert second.attempted == 1
