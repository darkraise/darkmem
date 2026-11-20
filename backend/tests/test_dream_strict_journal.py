"""Dream and hygiene actions commit only together with their journal row."""
from __future__ import annotations

from datetime import timedelta

from app.services import events as events_module
from app.services import hygiene_queue
from app.services import memory_dream as dream
from app.utils.ids import new_id
from tests.test_dream_undo import (  # noqa: F401 - fixtures
    NOW,
    committing,
    edge_row,
    memory_row,
    memory_row_of,
    project,
    seed_memory,
)


async def _refuse(*args, **kwargs) -> bool:
    return False


async def _pair(factory, project):
    async with factory() as session:
        older = await seed_memory(
            session, project=project, content="old truth", created_at=NOW
        )
        newer = await seed_memory(
            session, project=project, content="new truth",
            created_at=NOW + timedelta(hours=1),
        )
        await session.commit()
    return older, newer


def _candidate(project, older, newer) -> dream.PairCandidate:
    return dream.PairCandidate(
        older=memory_row_of(older, project=project, content="old truth"),
        newer=memory_row_of(
            newer, project=project, content="new truth",
            created_at=NOW + timedelta(hours=1),
        ),
        score=0.97,
    )


async def _run_dream_action(factory, action) -> dream.DreamOutcome:
    outcome = dream.DreamOutcome()
    async with factory() as session:
        await dream._apply(session, action, cycle_id=str(new_id()), outcome=outcome)
        await session.commit()
    return outcome


async def test_action_with_a_failed_journal_write_commits_nothing(
    committing, project, monkeypatch
):
    monkeypatch.setattr(dream, "record_event", _refuse)
    monkeypatch.setattr(hygiene_queue, "record_event", _refuse)

    older, newer = await _pair(committing, project)
    pair = _candidate(project, older, newer)

    subsume = await _run_dream_action(
        committing,
        dream.SubsumeAction(pair=pair, verdict=dream.PairVerdict("subsumes", "r")),
    )
    associate = await _run_dream_action(
        committing,
        dream.AssociateAction(pair=pair, verdict=dream.PairVerdict("duplicate", "r")),
    )
    refine = await _run_dream_action(
        committing,
        dream.RefineAction(
            memory=memory_row_of(older, project=project, content="old truth"),
            verdict=dream.RefineVerdict(summary="a refined summary"),
        ),
    )
    async with committing() as session:
        _, superseded = await hygiene_queue.bulk_supersede(
            session, [{"memory_id": older, "superseded_by": newer}], actor="admin"
        )
        _, pruned = await hygiene_queue.bulk_prune(session, [older], actor="admin")
        await session.commit()

    assert [o.failed for o in (subsume, associate, refine)] == [1, 1, 1]
    assert (subsume.subsumed, associate.associated, refine.refined) == (0, 0, 0)
    assert [r.reason for r in superseded + pruned] == [
        hygiene_queue.JOURNAL_FAILED, hygiene_queue.JOURNAL_FAILED
    ]
    assert not any(r.applied for r in superseded + pruned)
    row = await memory_row(committing, older)
    assert (row["status"], row["superseded_by"], row["summary"]) == (
        "active", None, None
    )
    assert await edge_row(committing, newer, older, "RELATES_TO") is None


async def test_other_actions_of_the_tick_still_land(committing, project, monkeypatch):
    real = events_module.record_event
    calls: list[int] = []

    async def fail_the_second(*args, **kwargs) -> bool:
        calls.append(1)
        if len(calls) == 2:
            return False
        return await real(*args, **kwargs)

    monkeypatch.setattr(dream, "record_event", fail_the_second)
    memories = []
    async with committing() as session:
        for index in range(3):
            memories.append(
                await seed_memory(session, project=project, content=f"memory {index}")
            )
        await session.commit()

    outcome = dream.DreamOutcome()
    async with committing() as session:
        for index, memory in enumerate(memories):
            await dream._apply(
                session,
                dream.RefineAction(
                    memory=memory_row_of(
                        memory, project=project, content=f"memory {index}"
                    ),
                    verdict=dream.RefineVerdict(summary=f"summary {index}"),
                ),
                cycle_id=str(new_id()),
                outcome=outcome,
            )
        await session.commit()

    assert (outcome.refined, outcome.failed) == (2, 1)
    summaries = [
        (await memory_row(committing, memory))["summary"] for memory in memories
    ]
    assert summaries == ["summary 0", None, "summary 2"]
