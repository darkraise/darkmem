"""T3.23 — the L3 articles retrieval channel (doc 07 §2, doc 04 §5.3).

Four done-whens, and what each is worth as a test:

- **The template loses its inert label.** Asserted on the writer existing and
  on the partition being written, not on the comment — a comment is not a
  writer.
- **Semantic channel with scope pushdown from the first commit.** The pushdown
  is tested by seeding a second project and proving its article never appears,
  *and* by proving the scope is in the SQL rather than applied after the fetch:
  a post-filter returns fewer than `limit` rows whenever the top-K crosses a
  project boundary, silently.
- **Composed under doc 07 §5's rules, never fused ad hoc.** The channel emits
  candidates and holds no ranking of its own.
- **A stale article is returned labelled stale, not withheld.** The one that
  most easily degrades into "withheld" by accident, so it is asserted both ways
  round: the stale row is present, and it is labelled.
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

import pytest
from sqlalchemy import text

from app.repositories.knowledge_triples import KnowledgeTripleRepository
from app.services import articles_channel as ac
from app.services import article_synthesis as asyn
from app.services.embedder_registry import (
    EmbedderInfo,
    child_table,
    embedder_registry,
)

pytestmark = pytest.mark.asyncio

T0 = datetime(2026, 6, 1, 12, 0, 0, tzinfo=timezone.utc)
PROJECT = "t3-23-articles"
DIMS = 4
# `parse_fingerprint` splits on "|", not ":" — the writer registers
# through the registry, so a colon here fails only in the writer test and
# would have read as a writer bug.
FINGERPRINT = f"test-article-embed|{DIMS}"


@pytest.fixture(autouse=True)
def _forget_registered_fingerprints():
    """`embedder_registry` memoizes per process; every test here rolls back.

    Without this the second test in the file finds the fingerprint "known",
    skips the CREATE, and inserts into a table the rollback removed — and it
    fails only in suite order, which reads as a writer bug rather than a
    fixture one. Autouse because the writer path memoizes too, so clearing
    inside `_partition` alone left `write_article_embedding` broken.
    """
    embedder_registry._known.clear()
    yield
    embedder_registry._known.clear()


async def _partition(session) -> str:
    await embedder_registry.register(
        session,
        EmbedderInfo(
            fingerprint=FINGERPRINT, model_id="test-article-embed", dims=DIMS,
            source="llm",
        ),
    )
    await session.flush()
    return child_table(ac.ARTICLE_EMBEDDINGS_PARENT, FINGERPRINT)


async def _article(
    session,
    *,
    subject_key: str,
    project: str = PROJECT,
    status: str = "candidate",
    fact_set_hash: str = "hash-a",
    vector: list[float] | None = None,
) -> str:
    article_id = str(uuid4())
    await session.execute(
        text(
            "INSERT INTO knowledge_articles "
            "(id, subject_key, project, title, content, status, review_state, "
            " fact_set_hash) "
            "VALUES (CAST(:id AS uuid), CAST(:s AS text), CAST(:p AS text), "
            "CAST(:s AS text), 'body text', CAST(:st AS text), 'open', "
            "CAST(:h AS text))"
        ),
        {"id": article_id, "s": subject_key, "p": project, "st": status,
         "h": fact_set_hash},
    )
    if vector is not None:
        table = await _partition(session)
        await session.execute(
            text(
                f"INSERT INTO {table} (article_id, fingerprint, embedding) "
                "VALUES (CAST(:id AS uuid), CAST(:fp AS text), CAST(:v AS vector))"
            ),
            {"id": article_id, "fp": FINGERPRINT, "v": str(vector)},
        )
    await session.flush()
    return article_id


async def _verified_fact(session, *, subject_name: str, project: str = PROJECT) -> str:
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
            "UPDATE knowledge_triples SET verification_status = 'corroborated' "
            "WHERE id = CAST(:id AS uuid)"
        ),
        {"id": row["id"]},
    )
    await session.flush()
    return str(row["id"])


# ─────────────── the semantic arm ───────────────


class TestTheSemanticArm:
    async def test_it_returns_the_nearest_article(self, session):
        await _partition(session)
        near = await _article(
            session, subject_key="near::concept", vector=[1.0, 0.0, 0.0, 0.0]
        )
        await _article(
            session, subject_key="far::concept", vector=[0.0, 0.0, 0.0, 1.0]
        )

        trace = await ac.ArticlesChannel(session).search_with_trace(
            [1.0, 0.0, 0.0, 0.0], fingerprint=FINGERPRINT, project=PROJECT, limit=1
        )

        assert [r["article_id"] for r in trace.results] == [near]

    async def test_it_carries_the_arm_score_for_the_trace(self, session):
        await _partition(session)
        article_id = await _article(
            session, subject_key="a::concept", vector=[1.0, 0.0, 0.0, 0.0]
        )

        trace = await ac.ArticlesChannel(session).search_with_trace(
            [1.0, 0.0, 0.0, 0.0], fingerprint=FINGERPRINT, project=PROJECT
        )

        assert trace.arm_scores[article_id][ac.SEMANTIC_ARM] == pytest.approx(1.0)
        assert trace.channel_status()[ac.SEMANTIC_ARM].ran is True
        assert trace.channel_status()[ac.SEMANTIC_ARM].failed is False

    async def test_a_superseded_article_is_not_a_result(self, session):
        """`ux_knowledge_articles_live` keeps one live row per subject;
        admitting superseded ones returns the same subject twice — once as it
        reads now and once as it used to."""
        await _partition(session)
        live = await _article(
            session, subject_key="s::concept", vector=[1.0, 0.0, 0.0, 0.0]
        )
        await _article(
            session, subject_key="old::concept", status="superseded",
            vector=[1.0, 0.0, 0.0, 0.0],
        )

        trace = await ac.ArticlesChannel(session).search_with_trace(
            [1.0, 0.0, 0.0, 0.0], fingerprint=FINGERPRINT, project=PROJECT
        )

        assert [r["article_id"] for r in trace.results] == [live]


# ─────────────── scope pushdown ───────────────


class TestScopePushdown:
    async def test_another_project_s_article_is_never_returned(self, session):
        await _partition(session)
        mine = await _article(
            session, subject_key="s::concept", vector=[1.0, 0.0, 0.0, 0.0]
        )
        await _article(
            session, subject_key="s::concept", project=f"{PROJECT}-other",
            vector=[1.0, 0.0, 0.0, 0.0],
        )

        trace = await ac.ArticlesChannel(session).search_with_trace(
            [1.0, 0.0, 0.0, 0.0], fingerprint=FINGERPRINT, project=PROJECT
        )

        assert [r["article_id"] for r in trace.results] == [mine]

    async def test_the_scope_is_in_the_sql_not_a_post_filter(self, session):
        """A post-filter returns fewer than `limit` rows whenever the top-K
        crosses a project boundary, and does it silently — the isolation
        failure reads as a thin result set."""
        await _partition(session)
        # Three nearer articles in another project would displace the whole
        # page if the scope were applied after the fetch.
        for _ in range(3):
            await _article(
                session, subject_key=f"o{uuid4().hex[:4]}::concept",
                project=f"{PROJECT}-other", vector=[1.0, 0.0, 0.0, 0.0],
            )
        mine = await _article(
            session, subject_key="mine::concept", vector=[0.9, 0.1, 0.0, 0.0]
        )

        trace = await ac.ArticlesChannel(session).search_with_trace(
            [1.0, 0.0, 0.0, 0.0], fingerprint=FINGERPRINT, project=PROJECT, limit=3
        )

        assert [r["article_id"] for r in trace.results] == [mine]
        assert "a.project = CAST(:project AS text)" in ac._SEARCH_SQL


# ─────────────── staleness is a label, never a filter ───────────────


class TestStaleness:
    async def test_a_stale_article_is_returned_and_labelled(self, session):
        """Both halves, because the failure mode is silent withholding: a
        stale article is still the best write-up of its subject, and hiding it
        leaves the reader with a fresher-looking absence."""
        await _partition(session)
        await _verified_fact(session, subject_name="postgres")
        article_id = await _article(
            session, subject_key="postgres::concept",
            fact_set_hash="a-hash-from-before", vector=[1.0, 0.0, 0.0, 0.0],
        )

        trace = await ac.ArticlesChannel(session).search_with_trace(
            [1.0, 0.0, 0.0, 0.0], fingerprint=FINGERPRINT, project=PROJECT
        )

        assert [r["article_id"] for r in trace.results] == [article_id]
        assert trace.results[0]["stale"] is True

    async def test_a_current_article_is_not_labelled_stale(self, session):
        await _partition(session)
        fact_id = await _verified_fact(session, subject_name="redis")
        current = asyn.fact_set_hash([fact_id])
        await _article(
            session, subject_key="redis::concept", fact_set_hash=current,
            vector=[1.0, 0.0, 0.0, 0.0],
        )

        trace = await ac.ArticlesChannel(session).search_with_trace(
            [1.0, 0.0, 0.0, 0.0], fingerprint=FINGERPRINT, project=PROJECT
        )

        assert trace.results[0]["stale"] is False

    async def test_a_subject_whose_facts_all_went_away_is_stale(self, session):
        """The strongest form of what staleness names: the knowledge the
        article was built on is gone."""
        await _partition(session)
        await _article(
            session, subject_key="ghost::concept", fact_set_hash="whatever",
            vector=[1.0, 0.0, 0.0, 0.0],
        )

        trace = await ac.ArticlesChannel(session).search_with_trace(
            [1.0, 0.0, 0.0, 0.0], fingerprint=FINGERPRINT, project=PROJECT
        )

        assert trace.results[0]["stale"] is True

    async def test_an_invalidated_fact_labels_the_article_stale(self, session):
        """Doc 09 §4.4's fourth trigger, servable since the 2026-08-11 ruling.

        The end-to-end half of the property `test_article_citations` pins on the
        hash: what the reader is actually handed is the label.
        """
        await _partition(session)
        fact_id = await _verified_fact(session, subject_name="kafka")
        await _article(
            session, subject_key="kafka::concept",
            fact_set_hash=asyn.fact_set_hash([fact_id]),
            vector=[1.0, 0.0, 0.0, 0.0],
        )

        fresh = await ac.ArticlesChannel(session).search_with_trace(
            [1.0, 0.0, 0.0, 0.0], fingerprint=FINGERPRINT, project=PROJECT
        )
        assert fresh.results[0]["stale"] is False

        await session.execute(
            text(
                "UPDATE knowledge_triples SET invalid_at = now() "
                "WHERE id = CAST(:id AS uuid)"
            ),
            {"id": fact_id},
        )
        await session.flush()

        trace = await ac.ArticlesChannel(session).search_with_trace(
            [1.0, 0.0, 0.0, 0.0], fingerprint=FINGERPRINT, project=PROJECT
        )
        assert trace.results[0]["stale"] is True


# ─────────────── an absent partition is not a failure ───────────────


class TestAnAbsentPartition:
    async def test_it_reports_not_run_rather_than_failed(self, session):
        """Every install that has not yet synthesised an article would
        otherwise serve every search flagged partially degraded, forever, for a
        layer it has no content in."""
        trace = await ac.ArticlesChannel(session).search_with_trace(
            [1.0, 0.0, 0.0, 0.0], fingerprint="never-registered|4", project=PROJECT
        )

        assert trace.results == []
        assert trace.channel_status()[ac.SEMANTIC_ARM].ran is False
        assert trace.channel_status()[ac.SEMANTIC_ARM].failed is False

    async def test_the_probe_leaves_the_transaction_usable(self, session):
        """Probing by running the query and catching the error would poison the
        transaction on the most ordinary state this channel has."""
        await ac.ArticlesChannel(session).search_with_trace(
            [1.0, 0.0, 0.0, 0.0], fingerprint="never-registered|4", project=PROJECT
        )

        assert (await session.execute(text("SELECT 1"))).scalar_one() == 1


# ─────────────── the writer ───────────────


class TestTheWriter:
    async def test_synthesis_embeds_the_article_it_wrote(self, session):
        """The template's inert label comes off because a writer exists, not
        because a comment changed."""

        class _Embedder:
            async def embed(self, _text):
                return [1.0, 0.0, 0.0, 0.0], FINGERPRINT

        article_id = await _article(session, subject_key="written::concept")

        fingerprint = await asyn.write_article_embedding(
            session, _Embedder(), article_id=article_id, text_body="body text"
        )
        await session.flush()

        assert fingerprint == FINGERPRINT
        table = child_table(ac.ARTICLE_EMBEDDINGS_PARENT, FINGERPRINT)
        count = (
            await session.execute(
                text(f"SELECT COUNT(*) FROM {table} WHERE article_id = CAST(:id AS uuid)"),
                {"id": article_id},
            )
        ).scalar_one()
        assert count == 1

    async def test_no_embedder_writes_nothing_rather_than_raising(self, session):
        """An install without an embedder still synthesises and stores; it has
        no L3 retrieval until it has one."""
        article_id = await _article(session, subject_key="unembedded::concept")

        assert await asyn.write_article_embedding(
            session, None, article_id=article_id, text_body="body"
        ) is None


# ─────────────── composed, never fused here ───────────────


class TestComposition:
    async def test_the_channel_is_wired_into_the_composition(self):
        """Doc 07 §5's composition is what merges layers; the slot the
        composition reserved with `ran=False` is now filled by this channel."""
        import inspect

        from app.services import layer_composition

        source = inspect.getsource(layer_composition.LayerCompositionService)
        assert "_article_channel" in source
        assert "article_candidate(row, channel_rank=rank)" in source

    async def test_the_channel_holds_no_ranking_of_its_own(self):
        """"Never fused ad hoc": the channel orders by semantic distance and
        emits candidates. Any weighting here would be a second ranking
        authority beside `rank_fusion`'s."""
        import inspect

        source = inspect.getsource(ac)
        for fusion in ("rrf", "RRF_K", "semantic_weight", "rank_fusion"):
            assert fusion not in source, f"the channel fuses: {fusion}"

    async def test_an_absent_embedder_reads_as_not_run_not_as_failed(self):
        """An embedder outage is already reported by the memory channel's own
        semantic arm; reporting it again here would flag L3 degraded for a
        layer that was never reached."""
        from app.services.articles_channel import ArticleChannelTrace

        trace = ArticleChannelTrace(results=[], semantic_ran=False)

        assert trace.channel_status()[ac.SEMANTIC_ARM].ran is False
        assert trace.channel_status()[ac.SEMANTIC_ARM].failed is False

    async def test_a_composed_read_serves_an_article_rather_than_raising(
        self, session
    ):
        """The regression the source-inspection test above could not see.

        A badge-less vault row raises by design, and nothing minted an L3
        badge — so the *first* embedded article in a project made every
        composed read in that project raise, on both doors, while every suite
        stayed green. Executing the path is the only thing that catches that,
        which is why this test drives `compose` instead of reading it.
        """
        from app.services.layer_composition import (
            LayerCompositionService,
            article_candidate,
        )

        await _partition(session)
        fact_id = await _verified_fact(session, subject_name="kafka")
        article_id = await _article(
            session, subject_key="kafka::concept",
            fact_set_hash=asyn.fact_set_hash([fact_id]),
            vector=[1.0, 0.0, 0.0, 0.0],
        )
        trace = await ac.ArticlesChannel(session).search_with_trace(
            [1.0, 0.0, 0.0, 0.0], fingerprint=FINGERPRINT, project=PROJECT
        )
        candidates = [
            article_candidate(row, channel_rank=i)
            for i, row in enumerate(trace.results, start=1)
        ]

        # `llm` is unused by the badge path — the producer reads rows and
        # the vault, never a model.
        service = LayerCompositionService(None, session)
        badges = await service.derive_badges(candidates)

        assert len(badges) == 1
        badge = next(iter(badges.values()))
        # Doc 12 §4's shape, with the L3 semantics ruled 2026-08-12: the count
        # is cited facts, and the claim names the coverage measurement rather
        # than borrowing the corroboration of the facts it cites.
        assert badge.origin_kinds == ("fact",)
        assert "grounded by" in badge.claim
        assert "claim-support coverage not measured" in badge.claim
        assert str(article_id)

    async def test_the_badge_carries_the_stale_flag_to_the_wire(self, session):
        """Doc 12 §4 makes `stale` an article-only badge field, and the badge
        is how it crosses: the composed row's own label map does not declare
        one, so a stale article was serving as current on both doors."""
        from app.services.layer_composition import (
            LayerCompositionService,
            article_candidate,
        )

        await _partition(session)
        await _verified_fact(session, subject_name="redis")
        await _article(
            session, subject_key="redis::concept",
            fact_set_hash="a-hash-from-before", vector=[1.0, 0.0, 0.0, 0.0],
        )
        trace = await ac.ArticlesChannel(session).search_with_trace(
            [1.0, 0.0, 0.0, 0.0], fingerprint=FINGERPRINT, project=PROJECT
        )
        assert trace.results[0]["stale"] is True

        badges = await LayerCompositionService(None, session).derive_badges(
            [article_candidate(trace.results[0], channel_rank=1)]
        )

        assert next(iter(badges.values())).stale is True
