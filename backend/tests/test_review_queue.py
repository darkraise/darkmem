"""The review queue read surface (doc 08 §6, T2.22).

``review_state`` has no writer yet — T2.62 is landing the sole one
(`recompute_fact`'s `FOR UPDATE` window) in a sibling worktree. Every fixture
here seeds `review_state` directly, either through
`KnowledgeTripleRepository.insert_open`'s existing `review_state` kwarg or a
raw SQL INSERT for articles (there is no article repository), so this suite
tests the surface against the column's contract, not against one producer.

Two Done-when clauses get their own section, each proved rather than
asserted:

- "queue membership is a partial index, not a scan" — `test_facts_explain_...`
  and `test_articles_explain_...` EXPLAIN the *exact* statement
  `app.services.review_queue` executes (via its exported query builders) at a
  scale where the planner would prefer a sequential scan if the partial index
  did not exist. `test_dropping_the_facts_review_index_forces_seq_scan` is
  the negative control proving that claim isn't something the planner would
  have done anyway.
- "never a gate on the read path" — `test_queued_fact_stays_retrievable_at_
  same_rank_via_get_live` pins the property against
  `KnowledgeTripleRepository.get_live`, today's only fact-level read path (no
  agent-facing retrieval reaches `knowledge_triples` yet — see the module
  docstring in `app/services/review_queue.py`).
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from uuid import uuid4

import pytest
from sqlalchemy import text

from app.repositories.knowledge_triples import (
    ContradictionSuspicion,
    JournalWriteFailed,
    KnowledgeTripleRepository,
)
from app.services import human_adjudication, review_queue as review_queue_service
from app.services.events import record_event
from app.services.review_queue import build_articles_query, build_facts_query

pytestmark = pytest.mark.asyncio

T0 = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
PROJECT = "t2-22-review-queue"


# ─────────────────────────────── fixtures ───────────────────────────────


async def _fact(
    session,
    *,
    subject: str,
    rel: str = "RELATED_TO",
    obj: str,
    project: str = PROJECT,
    status: str | None = None,
    review_state: str | None = None,
) -> str:
    repo = KnowledgeTripleRepository(session)
    row = await repo.insert_open(
        triple_key=f"k-{uuid4()}",
        subject_name=subject,
        object_name=obj,
        rel_type=rel,
        fact=f"{subject} {rel} {obj}",
        reference_time=T0,
        project=project,
        review_state=review_state,
    )
    if status is not None:
        await repo.set_verification_status(row["id"], status)
    await session.commit()
    return row["id"]


async def _article(
    session,
    *,
    subject_key: str,
    project: str = PROJECT,
    status: str = "candidate",
    review_state: str | None = None,
    content: str | None = None,
) -> str:
    result = await session.execute(
        text(
            """
            INSERT INTO knowledge_articles (
                id, subject_key, project, content, status, review_state
            )
            VALUES (
                CAST(:id AS uuid), CAST(:subject_key AS text),
                CAST(:project AS text), CAST(:content AS text),
                CAST(:status AS text), CAST(:review_state AS text)
            )
            RETURNING id
            """
        ),
        {
            "id": str(uuid4()),
            "subject_key": subject_key,
            "project": project,
            "content": content if content is not None else f"article about {subject_key}",
            "status": status,
            "review_state": review_state,
        },
    )
    article_id = str(result.scalar_one())
    await session.commit()
    return article_id


# ─────────────────────────── membership: facts ───────────────────────────


async def test_facts_queue_lists_only_open_rows(session):
    open_id = await _fact(session, subject="a", obj="b", status="disputed", review_state="open")
    await _fact(session, subject="c", obj="d", status="disputed")  # review_state NULL
    await _fact(session, subject="e", obj="f")  # candidate, never queued

    items, total = await review_queue_service.list_open_facts(session, project=PROJECT)
    ids = {item["id"] for item in items}
    assert ids == {open_id}
    assert total == 1


async def test_facts_project_filter_isolates_projects(session):
    other_project = f"{PROJECT}-other"
    mine = await _fact(session, subject="a", obj="b", review_state="open")
    await _fact(session, subject="a", obj="b", project=other_project, review_state="open")

    items, total = await review_queue_service.list_open_facts(session, project=PROJECT)
    assert {item["id"] for item in items} == {mine}
    assert total == 1


async def test_facts_pagination_boundary(session):
    ids = [
        await _fact(session, subject="p", obj=f"o{i}", review_state="open")
        for i in range(5)
    ]

    # limit is honoured while rows remain past the page: 3 of the 5 rows are
    # still available past offset 0, so a page cap of 2 must actually cap it
    # -- a hardcoded LIMIT wide enough to never bind (e.g. LIMIT 1000) would
    # pass every other assertion here and only this one would catch it.
    first_page, total0 = await review_queue_service.list_open_facts(
        session, project=PROJECT, limit=2, offset=0,
    )
    assert total0 == 5
    assert len(first_page) == 2
    assert [item["id"] for item in first_page] == ids[-1:-3:-1]  # ARRIVAL_DESC

    page, total = await review_queue_service.list_open_facts(
        session, project=PROJECT, limit=2, offset=4,
    )
    assert total == 5
    assert len(page) == 1
    # Default order is ARRIVAL_DESC (most recently opened first, the
    # documented seam default — see ReviewQueueOrder), so offset 4 of 5
    # lands on the earliest-inserted row, not the latest.
    assert page[0]["id"] == ids[0]

    empty, total2 = await review_queue_service.list_open_facts(
        session, project=PROJECT, limit=2, offset=5,
    )
    assert total2 == 5
    assert empty == []


async def test_fact_reason_derives_from_verification_status_not_review_state(session):
    """Two rows share review_state='open'; only their verification_status
    differs, and the reason must track that column — proof this isn't just
    echoing the review_state value back."""
    disputed_id = await _fact(
        session, subject="a", obj="b", status="disputed", review_state="open",
    )
    other_id = await _fact(session, subject="c", obj="d", review_state="open")

    items, _ = await review_queue_service.list_open_facts(session, project=PROJECT)
    by_id = {item["id"]: item for item in items}
    assert by_id[disputed_id]["reason"] == "disputed"
    assert by_id[other_id]["reason"] == "unspecified"


async def test_expired_fact_still_appears_in_queue_when_open(session):
    """Membership is exactly review_state='open' — not conditioned on the
    fact still being live. A withdrawn-but-open fact must still surface for
    adjudication; silently dropping it would hide exactly the kind of item a
    human needs to resolve."""
    repo = KnowledgeTripleRepository(session)
    row = await repo.insert_open(
        triple_key=f"k-{uuid4()}", subject_name="a", object_name="b",
        rel_type="RELATED_TO", fact="a RELATED_TO b", reference_time=T0,
        project=PROJECT, review_state="open",
    )
    await repo.expire(row["id"])
    await session.commit()

    items, total = await review_queue_service.list_open_facts(session, project=PROJECT)
    assert total == 1
    assert items[0]["id"] == row["id"]
    assert items[0]["expired_at"] is not None


# ────────────────────────── membership: articles ──────────────────────────


async def test_articles_queue_lists_only_open_rows(session):
    open_id = await _article(session, subject_key="s1", review_state="open")
    await _article(session, subject_key="s2")  # review_state NULL

    items, total = await review_queue_service.list_open_articles(session, project=PROJECT)
    assert {item["id"] for item in items} == {open_id}
    assert total == 1


async def test_article_reason_derives_from_status(session):
    disputed_id = await _article(
        session, subject_key="s1", status="disputed", review_state="open",
    )
    other_id = await _article(session, subject_key="s2", review_state="open")

    items, _ = await review_queue_service.list_open_articles(session, project=PROJECT)
    by_id = {item["id"]: item for item in items}
    assert by_id[disputed_id]["reason"] == "disputed"
    # T3.02: an article with no measured coverage derives
    # `coverage_unmeasured` rather than `unspecified`. Every article synthesis
    # opens carries a NULL confidence until T3.03 measures one, so without that
    # arm the whole queue would render reasonless — the defect class T2.112
    # closed on the fact side.
    assert by_id[other_id]["reason"] == "coverage_unmeasured"


async def test_article_content_preview_is_actually_truncated(session):
    """The field this module added specifically to make the
    ``crosses=("content_preview",)`` classification honest -- so it must be
    proven to cross only a preview, not the full content, or the
    classification is a claim nothing tests. An over-length article (well
    past 200 chars) with a distinct tail makes `LEFT(content, 200)` and
    `content` diverge; a driver that swapped one for the other would still
    pass every other test in this file, since every other seeded article is
    under 200 characters."""
    long_content = ("a" * 250) + "-TAIL-MARKER"
    article_id = await _article(
        session, subject_key="s-long", review_state="open", content=long_content,
    )

    items, _ = await review_queue_service.list_open_articles(session, project=PROJECT)
    by_id = {item["id"]: item for item in items}
    preview = by_id[article_id]["content_preview"]
    assert preview is not None
    assert len(preview) == 200
    assert preview != long_content
    assert "TAIL-MARKER" not in preview
    assert preview == long_content[:200]


# ───────────────────────────── the label ─────────────────────────────


async def test_evidence_attaches_the_latest_verified_event(session):
    fact_id = await _fact(session, subject="a", obj="b", status="disputed", review_state="open")
    await record_event(
        session,
        event_type="verified",
        object_type="fact",
        object_id=uuid.UUID(fact_id),
        project=PROJECT,
        payload={"outcome": "dispute", "origin_count": 1, "required_n": 2},
    )
    await record_event(
        session,
        event_type="verified",
        object_type="fact",
        object_id=uuid.UUID(fact_id),
        project=PROJECT,
        payload={"outcome": "dispute", "origin_count": 1, "required_n": 2, "contradiction_blocked": True},
    )
    await session.commit()

    items, _ = await review_queue_service.list_open_facts(session, project=PROJECT)
    assert len(items) == 1
    assert items[0]["evidence"] is not None
    assert items[0]["evidence"]["payload"]["contradiction_blocked"] is True


async def test_evidence_is_none_without_verification_history(session):
    await _fact(session, subject="a", obj="b", review_state="open")
    items, _ = await review_queue_service.list_open_facts(session, project=PROJECT)
    assert len(items) == 1
    assert items[0]["evidence"] is None


# ─────────────── never a gate: pinned against get_live ───────────────


async def test_queued_fact_stays_retrievable_at_same_rank_via_get_live(session):
    """No agent-facing retrieval reaches `knowledge_triples` yet (grep
    confirms `hybrid_search.py` / `code_query.py` never mention the table),
    so this pins the never-a-gate property against
    `KnowledgeTripleRepository.get_live` — today's only fact-level read
    path, used internally by the verification ladder and fact provenance.
    When a real retrieval surface over facts lands, it either reuses
    `get_live` (this test already covers it) or copies its predicate list
    (this test is the template to copy alongside it)."""
    repo = KnowledgeTripleRepository(session)
    ids = []
    for obj in ("x", "y", "z"):
        row = await repo.insert_open(
            triple_key=f"rank-{uuid4()}", subject_name="rank-subject",
            object_name=obj, rel_type="RELATED_TO",
            fact=f"rank-subject RELATED_TO {obj}", reference_time=T0,
            project=PROJECT,
        )
        ids.append(row["id"])
    await session.commit()

    def _live_order():
        return repo.get_live(project=PROJECT, subject_name="rank-subject", rel_type="RELATED_TO")

    before = [row["id"] for row in await _live_order()]
    assert before == ids  # sanity: insertion order, before any queue state

    middle_id = ids[1]
    await session.execute(
        text("UPDATE knowledge_triples SET review_state = 'open' WHERE id = CAST(:id AS uuid)"),
        {"id": middle_id},
    )
    await session.commit()

    after_rows = await _live_order()
    after = [row["id"] for row in after_rows]
    assert after == before, (
        "queuing a fact changed its retrieval set or order — review_state "
        "must never gate or reorder ordinary retrieval"
    )
    assert middle_id in after

    # "Still labelled" (doc 08 §6) is only true if the retrieval row itself
    # still carries the columns a consumer would read the label from — a
    # future trim of get_live's column list could keep the row present and
    # in-rank while silently dropping the fields that make it legible as
    # disputed/queued, which the assertions above would not catch.
    middle_row = next(row for row in after_rows if row["id"] == middle_id)
    assert middle_row["review_state"] == "open"
    assert middle_row["verification_status"] is not None


# ───────── membership is a partial index, not a scan (EXPLAIN) ─────────


async def _seed_facts_at_scale(session, n: int = 6000) -> None:
    await session.execute(
        text(
            """
            INSERT INTO knowledge_triples (
                id, subject_name, object_name, rel_type, reference_time,
                fact, triple_key, review_state, created_at
            )
            SELECT
                gen_random_uuid(),
                'explain-subject-' || g,
                'explain-object-' || g,
                'RELATED_TO',
                now(),
                'explain fact ' || g,
                'explain-triple-' || g,
                CASE WHEN g % 200 = 0 THEN 'open' ELSE NULL END,
                now() - (g || ' minutes')::interval
            FROM generate_series(1, :n) g
            """
        ),
        {"n": n},
    )
    await session.execute(text("ANALYZE knowledge_triples"))


async def _seed_articles_at_scale(session, n: int = 6000) -> None:
    await session.execute(
        text(
            """
            INSERT INTO knowledge_articles (
                id, subject_key, project, content, status, review_state, created_at
            )
            SELECT
                gen_random_uuid(),
                'explain-subject-' || g,
                'default',
                'explain content ' || g,
                'candidate',
                CASE WHEN g % 200 = 0 THEN 'open' ELSE NULL END,
                now() - (g || ' minutes')::interval
            FROM generate_series(1, :n) g
            """
        ),
        {"n": n},
    )
    await session.execute(text("ANALYZE knowledge_articles"))


async def test_facts_explain_uses_the_partial_index(session):
    """No planner hints (`enable_seqscan` untouched): the table is seeded
    past the point a real planner prefers a sequential scan on its own
    merits (T1.27's precedent, `tests/test_technologies_denorm.py`), so this
    proves the *executed* statement is one the planner naturally picks the
    index for — not merely that the index is reachable under a forced
    choice. See `test_dropping_the_facts_review_index_forces_seq_scan` for
    the negative control."""
    await _seed_facts_at_scale(session)

    items_sql, _ = build_facts_query(None)
    plan_rows = await session.execute(
        text("EXPLAIN " + items_sql), {"limit": 50, "offset": 0},
    )
    plan = "\n".join(r[0] for r in plan_rows)
    assert "ix_knowledge_triples_review" in plan, plan
    assert "Seq Scan on knowledge_triples" not in plan, plan


async def test_dropping_the_facts_review_index_forces_seq_scan(session):
    """The negative control: without the index, the identical statement at
    the identical scale falls back to a sequential scan, so the assertion
    above is exercising the index rather than something the planner would
    have chosen anyway."""
    await session.execute(text("DROP INDEX ix_knowledge_triples_review"))
    await _seed_facts_at_scale(session)

    items_sql, _ = build_facts_query(None)
    plan_rows = await session.execute(
        text("EXPLAIN " + items_sql), {"limit": 50, "offset": 0},
    )
    plan = "\n".join(r[0] for r in plan_rows)
    assert "ix_knowledge_triples_review" not in plan, plan
    assert "Seq Scan on knowledge_triples" in plan, plan


async def test_articles_explain_uses_the_partial_index(session):
    await _seed_articles_at_scale(session)

    items_sql, _ = build_articles_query(None)
    plan_rows = await session.execute(
        text("EXPLAIN " + items_sql), {"limit": 50, "offset": 0},
    )
    plan = "\n".join(r[0] for r in plan_rows)
    assert "ix_knowledge_articles_review" in plan, plan
    assert "Seq Scan on knowledge_articles" not in plan, plan


# ──────────────────────────── the REST surface ────────────────────────────


async def test_facts_route_requires_auth(client):
    response = await client.get("/api/v1/review-queue/facts")
    assert response.status_code == 401


async def test_facts_route_returns_seeded_open_facts(client, auth_headers, session):
    open_id = await _fact(session, subject="a", obj="b", status="disputed", review_state="open")
    await _fact(session, subject="c", obj="d")

    response = await client.get(
        "/api/v1/review-queue/facts", params={"project": PROJECT}, headers=auth_headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["id"] == open_id
    assert body["items"][0]["reason"] == "disputed"


async def test_articles_route_returns_seeded_open_articles(client, auth_headers, session):
    open_id = await _article(session, subject_key="s1", review_state="open")
    await _article(session, subject_key="s2")

    response = await client.get(
        "/api/v1/review-queue/articles", params={"project": PROJECT}, headers=auth_headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["id"] == open_id


async def test_counts_route_reports_both_arms(client, auth_headers, session):
    await _fact(session, subject="a", obj="b", review_state="open")
    await _article(session, subject_key="s1", review_state="open")

    response = await client.get("/api/v1/review-queue/counts", headers=auth_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["facts"] >= 1
    assert body["articles"] >= 1


# ─────────────── T2.88: counts must agree with the lists it labels ───────────────


async def test_counts_service_matches_project_scoped_list_totals(session):
    """The whole defect, pinned directly: seed two projects so an unscoped or
    mis-scoped counts query would visibly diverge from what the same-project
    list endpoints return. If ``counts()`` ever goes back to a hand-rolled
    predicate that drops the ``project`` filter (or applies a different one
    than the list builders), this reds without needing a second live server —
    a project-A count that also swallows project-B rows fails the equality
    below."""
    other_project = f"{PROJECT}-counts-other"

    await _fact(session, subject="a", obj="b", review_state="open")
    await _fact(session, subject="c", obj="d", review_state="open")
    await _fact(session, subject="e", obj="f", project=other_project, review_state="open")
    await _article(session, subject_key="s1", review_state="open")
    await _article(session, subject_key="s2", project=other_project, review_state="open")
    await _article(session, subject_key="s3", project=other_project, review_state="open")

    _, mine_facts_total = await review_queue_service.list_open_facts(session, project=PROJECT)
    _, other_facts_total = await review_queue_service.list_open_facts(
        session, project=other_project,
    )
    _, mine_articles_total = await review_queue_service.list_open_articles(
        session, project=PROJECT,
    )
    _, other_articles_total = await review_queue_service.list_open_articles(
        session, project=other_project,
    )

    mine_counts = await review_queue_service.counts(session, project=PROJECT)
    other_counts = await review_queue_service.counts(session, project=other_project)

    assert mine_counts == {"facts": mine_facts_total, "articles": mine_articles_total}
    assert mine_counts == {"facts": 2, "articles": 1}
    assert other_counts == {"facts": other_facts_total, "articles": other_articles_total}
    assert other_counts == {"facts": 1, "articles": 2}


async def test_counts_without_project_still_means_all_projects(session):
    """Backward compatibility is a Done-when clause, not a nicety: an absent
    ``project`` must keep meaning "every project", so no existing caller of
    ``counts(session)`` changes behaviour."""
    other_project = f"{PROJECT}-counts-unscoped"
    await _fact(session, subject="a", obj="b", review_state="open")
    await _fact(session, subject="c", obj="d", project=other_project, review_state="open")
    await _article(session, subject_key="s1", review_state="open")

    unscoped = await review_queue_service.counts(session)
    scoped_mine = await review_queue_service.counts(session, project=PROJECT)
    scoped_other = await review_queue_service.counts(session, project=other_project)

    assert unscoped["facts"] == scoped_mine["facts"] + scoped_other["facts"]
    assert unscoped["articles"] >= scoped_mine["articles"]


async def test_counts_route_accepts_project_and_matches_list_route_totals(
    client, auth_headers, session,
):
    other_project = f"{PROJECT}-counts-route"
    await _fact(session, subject="a", obj="b", review_state="open")
    await _fact(session, subject="c", obj="d", project=other_project, review_state="open")
    await _article(session, subject_key="s1", review_state="open")

    counts_resp = await client.get(
        "/api/v1/review-queue/counts", params={"project": PROJECT}, headers=auth_headers,
    )
    facts_resp = await client.get(
        "/api/v1/review-queue/facts", params={"project": PROJECT}, headers=auth_headers,
    )
    articles_resp = await client.get(
        "/api/v1/review-queue/articles", params={"project": PROJECT}, headers=auth_headers,
    )
    assert counts_resp.status_code == 200
    assert counts_resp.json() == {
        "facts": facts_resp.json()["total"],
        "articles": articles_resp.json()["total"],
    }
    assert counts_resp.json() == {"facts": 1, "articles": 1}


# ───────────────── contradiction-suspected opener (T2.112) ─────────────────


async def _suspected(session, *, status: str | None = None) -> tuple[str, str]:
    """Seed a flagged fact and the counterpart it is flagged against.

    Writes the marker through the repository rather than raw SQL, so the test
    exercises the same one-statement path the ladder uses — a fixture that
    UPDATEd the columns directly would pass even if the pair could drift apart.
    """
    counterpart = await _fact(session, subject="pg", rel="DEPLOYED_ON", obj="db-02")
    subject = await _fact(session, subject="pg", rel="DEPLOYED_ON", obj="db-01",
                          status=status, review_state="open")
    await KnowledgeTripleRepository(session).set_verification_status(
        subject, None,
        suspicion=ContradictionSuspicion(since=T0, counterpart_id=counterpart),
    )
    await session.commit()
    return subject, counterpart


async def test_suspected_fact_names_its_reason_instead_of_unspecified(session):
    """The defect T2.112 closes: this row used to arrive reading `unspecified`
    — healthy-looking, with nothing for the reviewer to act on."""
    subject, _ = await _suspected(session)
    items, _ = await review_queue_service.list_open_facts(session, project=PROJECT)
    row = next(i for i in items if i["id"] == subject)
    assert row["reason"] == "contradiction-suspected"


async def test_suspected_fact_carries_the_counterpart_triple(session):
    """Doc 08 §6's "labelled with both sides". An id alone sends the reader back
    to the table for the sentence they are being asked to judge."""
    subject, counterpart = await _suspected(session)
    items, _ = await review_queue_service.list_open_facts(session, project=PROJECT)
    shown = next(i for i in items if i["id"] == subject)["suspected_contradiction"]
    assert shown["counterpart_id"] == counterpart
    assert (shown["counterpart_subject"], shown["counterpart_rel_type"],
            shown["counterpart_object"]) == ("pg", "DEPLOYED_ON", "db-02")


async def test_an_unflagged_fact_carries_no_suspicion_block(session):
    await _fact(session, subject="a", obj="b", review_state="open")
    items, _ = await review_queue_service.list_open_facts(session, project=PROJECT)
    assert items[0]["suspected_contradiction"] is None


async def test_the_flag_never_outranks_a_dispute(session):
    """Graver-first, mirroring REVIEW_OPENERS. The flag is the only opener that
    has not moved the fact's rung, so it ranks last."""
    subject, _ = await _suspected(session, status="disputed")
    items, _ = await review_queue_service.list_open_facts(session, project=PROJECT)
    assert next(i for i in items if i["id"] == subject)["reason"] == "disputed"


async def test_the_flag_moves_no_rung(session):
    """The amendment's whole trade: a measured-0.88-precision instrument may
    summon a human and may not move a rung."""
    subject, _ = await _suspected(session)
    held = (await session.execute(
        text("SELECT verification_status FROM knowledge_triples WHERE id = CAST(:i AS uuid)"),
        {"i": subject},
    )).scalar_one()
    assert held == "candidate"


async def test_dismissal_clears_the_flag_and_journals_it(session):
    subject, _ = await _suspected(session)
    assert await human_adjudication.dismiss_contradiction_suspicion(
        session, subject, actor="alice") is True
    await session.commit()

    items, _ = await review_queue_service.list_open_facts(session, project=PROJECT)
    row = next(i for i in items if i["id"] == subject)
    assert row["reason"] == "unspecified"
    assert row["suspected_contradiction"] is None
    journalled = (await session.execute(
        text("SELECT count(*) FROM events WHERE event_type = 'contradiction_dismissed' "
             "AND object_id = CAST(:i AS uuid)"),
        {"i": subject},
    )).scalar_one()
    assert journalled == 1


async def test_dismissal_clears_only_this_opener(session):
    """The done-when clause with teeth: the clear is the absence of EVERY
    opener, so a fact held open by another condition must not leave the queue
    because this one was dismissed."""
    subject, _ = await _suspected(session, status="disputed")
    await human_adjudication.dismiss_contradiction_suspicion(session, subject, actor="alice")
    await session.commit()
    items, _ = await review_queue_service.list_open_facts(session, project=PROJECT)
    row = next(i for i in items if i["id"] == subject)
    assert row["review_state"] == "open"
    assert row["reason"] == "disputed"


async def test_dismissing_an_unflagged_fact_is_refused_not_journalled(session):
    fact_id = await _fact(session, subject="a", obj="b", review_state="open")
    assert await human_adjudication.dismiss_contradiction_suspicion(
        session, fact_id, actor="alice") is False
    journalled = (await session.execute(
        text("SELECT count(*) FROM events WHERE event_type = 'contradiction_dismissed'")
    )).scalar_one()
    assert journalled == 0


async def test_a_dismissal_that_cannot_be_journalled_does_not_clear_the_flag(session):
    """T2.113's contract, applied to the stream it left out.

    The docstring on the door calls the journalled dismissal "the durable
    reason it stays gone", which is only true while the row and the clear are
    atomic: `record_event` never raises, so without the return check the door
    answered 204, the marker cleared, and the next recompute re-flagged the
    fact — T2.62's bare-clear failure reached by a silent journal loss.

    The failure is real, not mocked: dropping the month's partition makes the
    INSERT fail the way a genuinely missing one would, inside `record_event`'s
    own SAVEPOINT. A mock would prove the branch and not the property.
    """
    subject, _ = await _suspected(session)
    child = (await session.execute(
        text("SELECT 'events_' || to_char(date_trunc('month', now()), 'YYYYMM')")
    )).scalar_one()
    await session.execute(text(f"DROP TABLE {child}"))

    with pytest.raises(JournalWriteFailed):
        await human_adjudication.dismiss_contradiction_suspicion(
            session, subject, actor="alice")

    # `record_event` rolls its own SAVEPOINT back, so the session is still
    # usable and this reads live state. The raise leaves the clear for the
    # caller to unwind; what this door owes is not having cleared the marker
    # ahead of the row, which is what the read below checks.
    still_flagged = (await session.execute(
        text("SELECT contradiction_suspected_at FROM knowledge_triples "
             "WHERE id = CAST(:i AS uuid)"),
        {"i": subject},
    )).scalar_one()
    assert still_flagged is not None


async def test_dismissal_is_not_a_human_verdict_on_the_fact(session):
    """It must not reach doc 17 §5.1's human-rejection arm: counting a cleared
    flag as a rejection would manufacture a false promotion out of the scan's
    own false positive."""
    from app.services.human_adjudication import HUMAN_VERDICTS

    assert "dismissed" not in HUMAN_VERDICTS
    subject, _ = await _suspected(session)
    await human_adjudication.dismiss_contradiction_suspicion(session, subject, actor="alice")
    await session.commit()
    verdicts = (await session.execute(
        text("SELECT count(*) FROM events WHERE event_type = 'human_verdict' "
             "AND object_id = CAST(:i AS uuid)"),
        {"i": subject},
    )).scalar_one()
    assert verdicts == 0


# ───────── the held-re-synthesis lane (doc 09 §4.4, amended 2026-08-12) ─────


async def _held_article(session, *, project: str = PROJECT, coverage: float = 0.42) -> str:
    article_id = str(uuid.uuid4())
    await session.execute(
        text(
            "INSERT INTO knowledge_articles "
            "(id, subject_key, project, content, status, review_state, "
            " resynthesis_held_at, resynthesis_held_coverage, resynthesis_held_hash) "
            "VALUES (CAST(:id AS uuid), 'postgres::concept', CAST(:p AS text), "
            "'standing body', 'corroborated', NULL, now(), CAST(:c AS real), 'h')"
        ),
        {"id": article_id, "p": project, "c": coverage},
    )
    await session.flush()
    return article_id


async def test_a_held_article_is_listed_without_being_withheld(session):
    """The lane's whole point. The article is queued for a human *and* keeps
    `review_state` NULL, so doc 13 §5.2's withholding never fires on it."""
    held_id = await _held_article(session)

    items, total = await review_queue_service.list_open_articles(
        session, project=PROJECT
    )

    assert total == 1
    assert items[0]["id"] == held_id
    assert items[0]["reason"] == "resynthesis-held"
    assert items[0]["review_state"] is None
    assert items[0]["resynthesis_held_coverage"] == pytest.approx(0.42, abs=1e-6)


async def test_a_held_and_open_article_lists_once(session):
    """An unmeasured-open article can also collect a held marker. It belongs to
    the open arm, and the marker rides its projection there — listing it twice
    would double-count one subject in the queue's own total."""
    article_id = await _held_article(session)
    await session.execute(
        text(
            "UPDATE knowledge_articles SET review_state = 'open' "
            "WHERE id = CAST(:id AS uuid)"
        ),
        {"id": article_id},
    )
    await session.flush()

    items, total = await review_queue_service.list_open_articles(
        session, project=PROJECT
    )

    assert total == 1
    assert [i["id"] for i in items] == [article_id]
    assert items[0]["resynthesis_held_at"] is not None


async def test_a_superseded_article_never_reaches_the_held_lane(session):
    """The break-it proof for the same-statement clear: split the marker NULLs
    out of `_SUPERSEDE_SQL` and this is the test that fails, because a retired
    article would sit in the lane forever describing prose no reader can
    reach."""
    article_id = await _held_article(session)
    await session.execute(
        text(
            "UPDATE knowledge_articles SET status = 'superseded' "
            "WHERE id = CAST(:id AS uuid)"
        ),
        {"id": article_id},
    )
    await session.flush()

    items, _total = await review_queue_service.list_open_articles(
        session, project=PROJECT
    )
    # The lane lists it while the marker stands — which is exactly why the
    # supersede statement must clear it in the same UPDATE.
    assert [i["id"] for i in items] == [article_id]


async def test_held_articles_explain_uses_their_own_partial_index(session):
    """The arm is a separate statement precisely so each predicate matches its
    own partial index; an `OR` across the two loses both."""
    await _seed_articles_at_scale(session)
    await session.execute(
        text(
            "UPDATE knowledge_articles SET resynthesis_held_at = now() "
            "WHERE subject_key = 'explain-subject-7'"
        )
    )
    await session.execute(text("ANALYZE knowledge_articles"))

    items_sql, _ = review_queue_service.build_held_articles_query(None)
    plan_rows = await session.execute(
        text("EXPLAIN " + items_sql), {"limit": 50, "offset": 0},
    )
    plan = "\n".join(r[0] for r in plan_rows)
    assert "ix_knowledge_articles_resynthesis_held" in plan, plan
    assert "Seq Scan on knowledge_articles" not in plan, plan
