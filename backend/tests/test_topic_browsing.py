"""T2.20 — topic browsing and the report's injectable unit (doc 09 §3.1,
§3.2): membership as a clean read, `report_status()` never re-derived, and
`get_injectable_report` as the seam T2.43 is expected to call from
retrieval — never called from here.
"""
from __future__ import annotations

from sqlalchemy import text

from app.repositories import memory_communities as repo
from app.services import topic_browsing as browsing
from app.services.memory_community_reports import (
    REPORT_STATUS_PENDING,
    REPORT_STATUS_READY,
    REPORT_STATUS_SKIPPED,
)
from app.utils.ids import new_id

PROJECT = "t220-browse"

_INSERT_MEMORY = text(
    "INSERT INTO memories (id, content, source, project, status) "
    "VALUES (CAST(:id AS uuid), :content, 'api', CAST(:project AS text), 'active')"
)


async def seed_memory(session, project: str = PROJECT, content: str = "seeded memory"):
    memory_id = new_id()
    await session.execute(
        _INSERT_MEMORY, {"id": str(memory_id), "content": content, "project": project}
    )
    return memory_id


async def test_browse_topics_lists_every_community_with_membership(session):
    a = await seed_memory(session)
    b = await seed_memory(session)
    await repo.replace_project_communities(
        session, PROJECT,
        [repo.CommunityDraft(label="alpha", memory_ids=(a, b), properties={"size": 2})],
    )
    await session.flush()

    topics = await browsing.browse_topics(session, PROJECT)
    assert len(topics) == 1
    assert topics[0].label == "alpha"
    assert topics[0].member_count == 2


async def test_get_topic_keys_on_label(session):
    a = await seed_memory(session)
    await repo.replace_project_communities(
        session, PROJECT,
        [repo.CommunityDraft(label="alpha", memory_ids=(a,), properties={"size": 1})],
    )
    await session.flush()

    topic = await browsing.get_topic(session, PROJECT, "alpha")
    assert topic is not None
    assert topic.label == "alpha"
    assert await browsing.get_topic(session, PROJECT, "does-not-exist") is None


async def test_topics_for_memory_finds_every_community_it_belongs_to(session):
    a = await seed_memory(session)
    b = await seed_memory(session)
    await repo.replace_project_communities(
        session, PROJECT,
        [
            repo.CommunityDraft(label="alpha", memory_ids=(a, b), properties={"size": 2}),
            repo.CommunityDraft(label="beta", memory_ids=(b,), properties={"size": 1}),
        ],
    )
    await session.flush()

    a_topics = {t.label for t in await browsing.topics_for_memory(session, PROJECT, a)}
    b_topics = {t.label for t in await browsing.topics_for_memory(session, PROJECT, b)}
    assert a_topics == {"alpha"}
    assert b_topics == {"alpha", "beta"}


async def test_report_status_distinguishes_skipped_from_pending(session):
    """The mandated guard: a `skipped` community (too small to ever get a
    report) and a `pending` one (eligible, not yet attempted) are both
    report-less, but must not read as the same state — that is exactly the
    distinction `report_status()` exists to preserve, and a browsing surface
    that re-derives from `report_string IS NULL` alone cannot tell them
    apart."""
    a = await seed_memory(session)
    b = await seed_memory(session)
    c = await seed_memory(session)
    await repo.replace_project_communities(
        session, PROJECT,
        [
            repo.CommunityDraft(label="tiny", memory_ids=(a,), properties={"size": 1}),
            repo.CommunityDraft(label="big-enough", memory_ids=(b, c), properties={"size": 3}),
        ],
    )
    await session.flush()

    topics = {t.label: t for t in await browsing.browse_topics(session, PROJECT)}
    assert topics["tiny"].report_status == REPORT_STATUS_SKIPPED
    assert topics["big-enough"].report_status == REPORT_STATUS_PENDING
    assert topics["tiny"].report_status != topics["big-enough"].report_status


async def test_report_string_is_only_surfaced_when_ready(session):
    a = await seed_memory(session)
    (community_id,) = await repo.replace_project_communities(
        session, PROJECT,
        [repo.CommunityDraft(label="alpha", memory_ids=(a,), properties={"size": 3})],
    )
    await session.flush()

    pending = await browsing.get_topic(session, PROJECT, "alpha")
    assert pending.report_status == REPORT_STATUS_PENDING
    assert pending.report_string is None

    await repo.set_report(session, community_id, report_string="a generated report")
    await session.flush()

    ready = await browsing.get_topic(session, PROJECT, "alpha")
    assert ready.report_status == REPORT_STATUS_READY
    assert ready.report_string == "a generated report"


async def test_get_injectable_report_is_none_until_ready(session):
    a = await seed_memory(session)
    (community_id,) = await repo.replace_project_communities(
        session, PROJECT,
        [repo.CommunityDraft(label="alpha", memory_ids=(a,), properties={"size": 3})],
    )
    await session.flush()

    assert await browsing.get_injectable_report(session, PROJECT, "alpha") is None

    await repo.set_report(session, community_id, report_string="the injectable text")
    await session.flush()
    assert (
        await browsing.get_injectable_report(session, PROJECT, "alpha")
        == "the injectable text"
    )


async def test_get_injectable_report_is_none_for_a_missing_label(session):
    assert await browsing.get_injectable_report(session, PROJECT, "nope") is None
