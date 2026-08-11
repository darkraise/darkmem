"""The articles read surface — list and detail (doc 12 §4, doc 13 §5.2, T3.06).

Four properties carry the weight, and each is the one a plausible
implementation gets wrong quietly:

**The rung passes the claim gate.** `knowledge_articles`' CHECK admits
`corroborated`, so an article promoted by any writer reaches a reader here
unless this door goes through `row_labels`. With G-D open a promoted article
must serve as `candidate` with a stated suppression reason — and a suppressed
rung must not read like a genuinely-candidate one.

**Coverage is on the list row, not only on the detail.** Doc 13 §5.2 makes the
number an honesty signal shown in both detail levels, and a surface can only
show in Simple what the list already carries.

**Stale is a label, never a filter.** A stale article is returned like any
other, flagged.

**Lineage is reachable from both ends.** A superseded article is out of the
list and readable by id, and each end names the other.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy import text

from app.repositories.knowledge_triples import KnowledgeTripleRepository
from app.services import article_synthesis as asyn
from app.services import articles_read
from tests.response_coverage import undeclared_keys

pytestmark = pytest.mark.asyncio

T0 = datetime(2026, 6, 1, 12, 0, 0, tzinfo=timezone.utc)
PROJECT = "t3-06-articles"
SUBJECT = "postgres"
SUBJECT_KEY = f"{SUBJECT}::concept"
ARTICLES = "/api/v1/knowledge/articles"


async def _fact(session, *, status: str = "corroborated", fact: str = "postgres runs") -> str:
    repo = KnowledgeTripleRepository(session)
    row = await repo.insert_open(
        triple_key=f"k-{uuid.uuid4()}",
        subject_name=SUBJECT,
        object_name=f"o-{uuid.uuid4()}",
        rel_type="RELATED_TO",
        fact=fact,
        reference_time=T0,
        project=PROJECT,
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
    session,
    *,
    fact_set_hash: str,
    status: str = "corroborated",
    confidence: float | None = 0.97,
    subject_key: str = SUBJECT_KEY,
    content: str = "Postgres is a database. It relates to a thing.",
    review_state: str | None = None,
) -> str:
    article_id = str(uuid.uuid4())
    await session.execute(
        text(
            "INSERT INTO knowledge_articles "
            "(id, subject_key, project, title, content, status, confidence, "
            " review_state, fact_set_hash, synthesized_at, learned_in) "
            "VALUES (CAST(:id AS uuid), CAST(:k AS text), CAST(:p AS text), "
            "CAST(:k AS text), CAST(:c AS text), CAST(:st AS text), "
            "CAST(:conf AS real), CAST(:rs AS text), CAST(:h AS text), "
            "CAST(:now AS timestamptz), CAST(:li AS text[]))"
        ),
        {
            "id": article_id, "k": subject_key, "p": PROJECT, "c": content,
            "st": status, "conf": confidence, "rs": review_state,
            "h": fact_set_hash, "now": T0, "li": ["project/darkmem"],
        },
    )
    await session.flush()
    return article_id


async def _cite(session, article_id: str, fact_id: str, lo: int = 0, hi: int = 24) -> None:
    await session.execute(
        text(
            "INSERT INTO article_citations (id, article_id, fact_id, claim_span) "
            "VALUES (gen_random_uuid(), CAST(:a AS uuid), CAST(:f AS uuid), "
            "int4range(:lo, :hi))"
        ),
        {"a": article_id, "f": fact_id, "lo": lo, "hi": hi},
    )
    await session.flush()


async def _current_hash(session) -> str:
    return asyn.fact_set_hash(
        await asyn.all_verified_fact_ids(session, subject=SUBJECT, project=PROJECT)
    )


# ─────────────── the door ───────────────


async def test_the_list_requires_authentication(client):
    assert (await client.get(ARTICLES)).status_code == 401


async def test_the_detail_requires_authentication(client):
    assert (await client.get(f"{ARTICLES}/{uuid.uuid4()}")).status_code == 401


async def test_an_unknown_article_is_a_404(client, auth_headers):
    response = await client.get(f"{ARTICLES}/{uuid.uuid4()}", headers=auth_headers)
    assert response.status_code == 404


# ─────────────── the rung passes the gate ───────────────


class TestTheClaimGate:
    async def test_a_promoted_article_serves_as_candidate_while_the_gate_is_shut(
        self, session
    ):
        """G-D is open, so nothing has certified an article's grounding. The
        column keeps `corroborated`; the reader is told `candidate`, with the
        reason, so a withheld rung and an unmeasured one do not read alike."""
        await _fact(session)
        await _article(session, fact_set_hash=await _current_hash(session))

        items, _total = await articles_read.list_articles(session, project=PROJECT)

        assert items[0]["status"] == "candidate"
        assert items[0]["label_suppressed"]
        assert items[0]["unverified"] is True

    async def test_the_stored_column_is_untouched(self, session):
        """The gate withholds a label; it does not rewrite the vault."""
        await _fact(session)
        article_id = await _article(session, fact_set_hash=await _current_hash(session))

        await articles_read.list_articles(session, project=PROJECT)

        stored = (
            await session.execute(
                text("SELECT status FROM knowledge_articles WHERE id = CAST(:id AS uuid)"),
                {"id": article_id},
            )
        ).scalar_one()
        assert stored == "corroborated"

    async def test_a_candidate_article_carries_no_suppression_reason(self, session):
        """Suppression means a promoted rung was withheld. A candidate asserts
        nothing that needs evidence, so nothing about it is being withheld."""
        await _fact(session)
        await _article(
            session, fact_set_hash=await _current_hash(session), status="candidate"
        )

        items, _total = await articles_read.list_articles(session, project=PROJECT)

        assert items[0]["status"] == "candidate"
        assert items[0]["label_suppressed"] is None


# ─────────────── coverage, staleness, lineage ───────────────


class TestTheListRow:
    async def test_coverage_rides_the_list_row(self, session):
        """Doc 13 §5.2 shows the number in Simple as well as Advanced, and the
        list is what Simple renders."""
        await _fact(session)
        await _article(session, fact_set_hash=await _current_hash(session))

        items, total = await articles_read.list_articles(session, project=PROJECT)

        assert total == 1
        assert items[0]["coverage"] == pytest.approx(0.97, abs=1e-6)

    async def test_a_stale_article_is_listed_and_flagged(self, session):
        await _fact(session)
        await _article(session, fact_set_hash="a-hash-from-before")

        items, _total = await articles_read.list_articles(session, project=PROJECT)

        assert len(items) == 1
        assert items[0]["stale"] is True

    async def test_a_current_article_is_not_flagged(self, session):
        await _fact(session)
        await _article(session, fact_set_hash=await _current_hash(session))

        items, _total = await articles_read.list_articles(session, project=PROJECT)

        assert items[0]["stale"] is False

    async def test_an_invalidated_fact_makes_it_stale_here_too(self, session):
        """The same basis as the retrieval channel and the synthesis job — one
        ruling, three surfaces, and they must agree or a reader sees a label
        the tab and the search disagree about."""
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

        items, _total = await articles_read.list_articles(session, project=PROJECT)
        assert items[0]["stale"] is True

    async def test_a_superseded_article_is_out_of_the_list(self, session):
        await _fact(session)
        await _article(
            session, fact_set_hash=await _current_hash(session), status="superseded"
        )

        _items, total = await articles_read.list_articles(session, project=PROJECT)
        assert total == 0

    async def test_the_project_filter_scopes_the_page(self, session):
        await _fact(session)
        await _article(session, fact_set_hash=await _current_hash(session))

        _items, total = await articles_read.list_articles(session, project="somewhere-else")
        assert total == 0


class TestTheDetail:
    async def test_every_claim_citation_carries_its_fact(self, session):
        """"Reachable in one click" is a property of the payload before it is a
        property of the UI: a citation that carried only an id would need a
        second fetch per claim to render anything a reader could follow."""
        fact_id = await _fact(session, fact="postgres relates to a thing")
        article_id = await _article(session, fact_set_hash=await _current_hash(session))
        await _cite(session, article_id, fact_id, 0, 24)

        item = await articles_read.get_article(session, article_id)

        assert [c["fact_id"] for c in item["citations"]] == [fact_id]
        assert item["citations"][0]["fact"] == "postgres relates to a thing"
        assert item["citations"][0]["claim_span"] == [0, 24]
        assert item["citations"][0]["believed"] is True

    async def test_a_citation_to_an_unbelieved_fact_still_renders_flagged(self, session):
        """Hiding it would leave an uncited claim on the page, which §4.3 calls
        a permanent grounding failure. It is flagged instead."""
        fact_id = await _fact(session)
        article_id = await _article(session, fact_set_hash=await _current_hash(session))
        await _cite(session, article_id, fact_id)
        await session.execute(
            text(
                "UPDATE knowledge_triples SET invalid_at = now() "
                "WHERE id = CAST(:id AS uuid)"
            ),
            {"id": fact_id},
        )
        await session.flush()

        item = await articles_read.get_article(session, article_id)

        assert len(item["citations"]) == 1
        assert item["citations"][0]["believed"] is False

    async def test_a_superseded_article_is_readable_by_id(self, session):
        """A lineage that 404s is not lineage."""
        await _fact(session)
        prior = await _article(
            session, fact_set_hash=await _current_hash(session),
            status="superseded", subject_key=f"{SUBJECT}-prior::concept",
        )

        item = await articles_read.get_article(session, prior)
        assert item is not None and item["id"] == prior

    async def test_lineage_is_reachable_from_both_ends(self, session):
        await _fact(session)
        current = await _article(session, fact_set_hash=await _current_hash(session))
        prior = await _article(
            session, fact_set_hash="older", status="superseded",
            subject_key=f"{SUBJECT}-prior::concept",
        )
        await session.execute(
            text(
                "UPDATE knowledge_articles SET superseded_by = CAST(:new AS uuid) "
                "WHERE id = CAST(:id AS uuid)"
            ),
            {"new": current, "id": prior},
        )
        await session.flush()

        assert (await articles_read.get_article(session, prior))["superseded_by"] == current
        assert (await articles_read.get_article(session, current))["supersedes"] == prior

    async def test_the_body_is_served_whole(self, session):
        await _fact(session)
        article_id = await _article(
            session, fact_set_hash=await _current_hash(session),
            content="A lead sentence. A second one.",
        )

        item = await articles_read.get_article(session, article_id)
        assert item["content"] == "A lead sentence. A second one."


# ─────────────── the wire ───────────────


class TestTheWire:
    async def test_the_list_response_declares_every_key_the_service_builds(
        self, session, client, auth_headers
    ):
        await _fact(session)
        await _article(session, fact_set_hash=await _current_hash(session))
        await session.commit()

        built, _total = await articles_read.list_articles(session, project=PROJECT)
        served = (
            await client.get(ARTICLES, params={"project": PROJECT}, headers=auth_headers)
        ).json()

        assert undeclared_keys(built[0], served["items"][0]) == []

    async def test_the_detail_response_declares_every_key_the_service_builds(
        self, session, client, auth_headers
    ):
        fact_id = await _fact(session)
        article_id = await _article(session, fact_set_hash=await _current_hash(session))
        await _cite(session, article_id, fact_id)
        await session.commit()

        built = await articles_read.get_article(session, article_id)
        served = (
            await client.get(f"{ARTICLES}/{article_id}", headers=auth_headers)
        ).json()

        assert undeclared_keys(built, served) == []
