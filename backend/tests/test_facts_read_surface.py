"""The facts read surface — list and detail (doc 12 §4, doc 13 §5.1, T2.36a).

Two properties get more attention than the rest because they are the ones a
plausible implementation gets wrong quietly.

**It is a door, not a ranking.** A browsing list over a table that also feeds
a review queue is exactly where a "show me the good ones" default gets added,
and a vault filtered to ``corroborated`` looks empty and healthy at the same
time. Every rung is listed, labelled, in arrival order.

**The badge's count is auditable.** The sources module groups ``fact_sources``
by ``origin_key`` so a reader can count the groups; the test below asserts
that number equals the ``origin_count`` the claim asserts, on a fixture where
a row count would give a different answer.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy import text

from app.repositories.fact_sources import FactSourceRepository
from app.repositories.knowledge_triples import KnowledgeTripleRepository
from app.services.events import record_event

pytestmark = pytest.mark.asyncio

T0 = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
AS_OF = datetime(2026, 7, 20, 9, 14, 0, tzinfo=timezone.utc)
PROJECT = "t2-36a-facts"
FACTS = "/api/v1/knowledge/facts"


async def _fact(
    session,
    *,
    subject: str = "postgres",
    rel: str = "RUNS_ON",
    obj: str = "docker",
    project: str = PROJECT,
    status: str | None = None,
    applies_when: dict | None = None,
    review_state: str | None = None,
    invalid_at: datetime | None = None,
    expired: bool = False,
) -> str:
    repo = KnowledgeTripleRepository(session)
    row = await repo.insert_open(
        triple_key=f"k-{uuid.uuid4()}",
        subject_name=subject,
        object_name=obj,
        rel_type=rel,
        fact=f"{subject} {rel} {obj}",
        reference_time=T0,
        project=project,
        valid_at=T0,
        applies_when=applies_when,
        review_state=review_state,
    )
    if status is not None:
        await session.execute(
            text(
                "UPDATE knowledge_triples SET verification_status = CAST(:s AS text) "
                "WHERE id = CAST(:id AS uuid)"
            ),
            {"s": status, "id": row["id"]},
        )
    if invalid_at is not None:
        await repo.close_window(row["id"], invalid_at)
    if expired:
        await repo.expire(row["id"])
    await session.flush()
    return row["id"]


async def _source(session, fact_id, *, kind="memory", origin=None, detail=None):
    await FactSourceRepository(session).add_source(
        fact_id=fact_id,
        source_kind=kind,
        source_ref=f"ref-{uuid.uuid4()}",
        origin_key=origin,
        detail=detail,
    )


async def _journal_verified(session, fact_id, *, at):
    await session.execute(
        text("SELECT events_ensure_partition(CAST(:at AS timestamptz)::date)"),
        {"at": at},
    )
    await session.execute(
        text(
            """
            INSERT INTO events (created_at, event_type, object_type, object_id,
                                project, payload)
            VALUES (
                CAST(:at AS timestamptz), 'verified', 'fact',
                CAST(:fid AS uuid), CAST(:project AS text),
                CAST(:payload AS jsonb)
            )
            """
        ),
        {
            "at": at,
            "fid": str(fact_id),
            "project": PROJECT,
            "payload": json.dumps(
                {
                    "before": {"verification_status": "candidate"},
                    "after": {"verification_status": "corroborated"},
                }
            ),
        },
    )
    await session.flush()


# ─────────────────────────────── the door ───────────────────────────────


async def test_the_list_requires_authentication(client):
    assert (await client.get(FACTS)).status_code == 401


async def test_the_detail_requires_authentication(client):
    assert (await client.get(f"{FACTS}/{uuid.uuid4()}")).status_code == 401


async def test_an_unknown_fact_is_a_404(client, auth_headers):
    response = await client.get(f"{FACTS}/{uuid.uuid4()}", headers=auth_headers)
    assert response.status_code == 404


async def test_an_empty_vault_is_an_empty_list_not_a_failure(client, auth_headers):
    """Doc 13 §5.1's cold start: a fresh install has no corroborated facts for
    months, so an empty vault is honest rather than broken."""
    response = await client.get(f"{FACTS}?project=nothing-here", headers=auth_headers)
    assert response.status_code == 200
    body = response.json()
    assert body == {"items": [], "total": 0, "limit": 50, "offset": 0}


async def test_the_list_answers_the_paginated_envelope(client, auth_headers, session):
    for index in range(3):
        fact_id = await _fact(session, obj=f"host-{index}")
        await _source(session, fact_id, origin=f"session-{index}")
    await session.flush()

    response = await client.get(
        f"{FACTS}?project={PROJECT}&limit=2&offset=0", headers=auth_headers
    )
    body = response.json()
    assert response.status_code == 200
    assert body["total"] == 3
    assert body["limit"] == 2
    assert body["offset"] == 0
    assert len(body["items"]) == 2

    page_two = await client.get(
        f"{FACTS}?project={PROJECT}&limit=2&offset=2", headers=auth_headers
    )
    assert len(page_two.json()["items"]) == 1


# ──────────────────────── never a gate on the read ────────────────────────


async def test_every_rung_is_listed_and_labelled_none_filtered_by_default(
    client, auth_headers, session, cleared_promotion_record):
    rungs = ("candidate", "corroborated", "disputed", "confirmed")
    for rung in rungs:
        fact_id = await _fact(
            session, obj=f"host-{rung}", status=rung,
            review_state="open" if rung == "disputed" else None,
        )
        await _source(session, fact_id, origin=f"session-{rung}")
    await session.flush()

    body = (
        await client.get(f"{FACTS}?project={PROJECT}", headers=auth_headers)
    ).json()
    assert body["total"] == 4
    assert {item["verification_status"] for item in body["items"]} == set(rungs)
    assert all(item["badge"] is not None for item in body["items"])


async def test_the_list_carries_the_unverified_label(client, auth_headers, session, cleared_promotion_record):
    """T2.56's cold-start label, at this door too (F9): ``row_labels``
    produces it for every fact row, but ``FactListItem`` had no field for
    it, so FastAPI's ``response_model`` silently dropped it here even
    though ``knowledge_search``'s composed read already carried it."""
    candidate = await _fact(session, obj="host-candidate", status="candidate")
    await _source(session, candidate, origin="session-candidate")
    confirmed = await _fact(session, obj="host-confirmed", status="confirmed")
    await _source(session, confirmed, origin="session-confirmed")
    await session.flush()

    body = (
        await client.get(f"{FACTS}?project={PROJECT}", headers=auth_headers)
    ).json()
    by_id = {item["id"]: item for item in body["items"]}
    assert by_id[str(candidate)]["unverified"] is True
    assert by_id[str(confirmed)]["unverified"] is False


async def test_a_queued_fact_is_listed_like_any_other(client, auth_headers, session):
    queued = await _fact(session, obj="queued", status="disputed", review_state="open")
    await _source(session, queued, origin="session-a")
    plain = await _fact(session, obj="plain", status="corroborated")
    await _source(session, plain, origin="session-b")
    await session.flush()

    body = (
        await client.get(f"{FACTS}?project={PROJECT}", headers=auth_headers)
    ).json()
    ids = [item["id"] for item in body["items"]]
    assert str(queued) in ids and str(plain) in ids
    queued_item = next(i for i in body["items"] if i["id"] == str(queued))
    assert queued_item["review_state"] == "open"


async def test_verification_status_is_an_opt_in_filter(
    client, auth_headers, session, cleared_promotion_record
):
    """The gate is open here because the subject is the filter being opt-in
    rather than defaulted. With it closed the filter still narrows, but on the
    served rung — which is `test_claim_serving_gates.py`'s subject, not this
    one."""
    kept = await _fact(session, obj="kept", status="corroborated")
    await _source(session, kept, origin="session-a")
    other = await _fact(session, obj="other", status="candidate")
    await _source(session, other, origin="session-b")
    await session.flush()

    body = (
        await client.get(
            f"{FACTS}?project={PROJECT}&verification_status=corroborated",
            headers=auth_headers,
        )
    ).json()
    assert [item["id"] for item in body["items"]] == [str(kept)]


async def test_belief_withdrawn_facts_leave_the_list(client, auth_headers, session):
    """The live set, not the open one: a window-closed fact is retained
    history and still listed, while a withdrawn belief is gone."""
    closed = await _fact(session, obj="closed", invalid_at=AS_OF)
    await _source(session, closed, origin="session-a")
    gone = await _fact(session, obj="gone", expired=True)
    await _source(session, gone, origin="session-b")
    await session.flush()

    body = (
        await client.get(f"{FACTS}?project={PROJECT}", headers=auth_headers)
    ).json()
    ids = [item["id"] for item in body["items"]]
    assert ids == [str(closed)]
    item = body["items"][0]
    assert item["belief_window"]["invalid_at"] is not None
    assert item["belief_window"]["expired_at"] is None


async def test_the_list_is_arrival_ordered_not_ranked(client, auth_headers, session):
    first = await _fact(session, obj="first")
    await _source(session, first, origin="session-a")
    second = await _fact(session, obj="second")
    await _source(session, second, origin="session-b")
    await session.flush()

    body = (
        await client.get(f"{FACTS}?project={PROJECT}", headers=auth_headers)
    ).json()
    assert [item["id"] for item in body["items"]] == [str(second), str(first)]


# ───────────────────── the badge on the wire, verbatim ─────────────────────


async def test_the_wire_badge_carries_doc_12s_fields_and_the_exact_claim(
    client, auth_headers, session, cleared_promotion_record):
    fact_id = await _fact(session, status="corroborated")
    await _source(session, fact_id, origin="session-a")
    await _source(session, fact_id, kind="code", origin="repo-b")
    await _journal_verified(session, fact_id, at=AS_OF)

    item = (
        await client.get(f"{FACTS}/{fact_id}", headers=auth_headers)
    ).json()
    assert item["badge"] == {
        "verification_status": "corroborated",
        "origin_count": 2,
        "origin_kinds": ["code", "memory"],
        "as_of": "2026-07-20T09:14:00Z",
        "contradiction": False,
        "human_ratified": False,
        "stale": False,
        "claim": (
            "asserted by 2 distinct origins of kinds [code, memory], "
            "no known contradiction, as of 2026-07-20"
        ),
    }


async def test_a_fact_row_carries_no_lifecycle_label(client, auth_headers, session):
    fact_id = await _fact(session, status="candidate")
    await _source(session, fact_id, origin="session-a")
    await session.flush()

    item = (await client.get(f"{FACTS}/{fact_id}", headers=auth_headers)).json()
    assert item["id_kind"] == "fact"
    assert item["lifecycle"] is None
    assert item["verification_status"] == "candidate"


# ─────────────────────── the sources module, audited ───────────────────────


async def test_sources_are_grouped_by_origin_and_the_count_is_auditable(
    client, auth_headers, session, cleared_promotion_record):
    """The fixture a row count gets wrong: three rows, two origins."""
    fact_id = await _fact(session, status="corroborated")
    await _source(session, fact_id, origin="session-a")
    await _source(session, fact_id, origin="session-a")
    await _source(
        session,
        fact_id,
        kind="code",
        origin="repo-b",
        detail={"commit_sha": "abc123", "file_path": "app/main.py", "symbol_key": "main"},
    )
    await session.flush()

    item = (await client.get(f"{FACTS}/{fact_id}", headers=auth_headers)).json()
    assert len(item["sources"]) == 2
    assert len(item["sources"]) == item["badge"]["origin_count"]
    assert sum(len(group["sources"]) for group in item["sources"]) == 3

    code_group = next(g for g in item["sources"] if g["origin_key"] == "repo-b")
    assert code_group["source_kinds"] == ["code"]
    assert code_group["sources"][0]["detail"]["commit_sha"] == "abc123"


async def test_anonymous_provenance_is_one_labelled_bucket(
    client, auth_headers, session
):
    fact_id = await _fact(session)
    for _ in range(3):
        await _source(session, fact_id, origin=None)
    await session.flush()

    item = (await client.get(f"{FACTS}/{fact_id}", headers=auth_headers)).json()
    assert len(item["sources"]) == 1
    assert item["sources"][0]["origin_key"] is None
    assert item["sources"][0]["unknown_origin"] is True
    assert item["badge"]["origin_count"] == 1


async def test_a_fact_nothing_has_sourced_serves_with_an_empty_count(
    client, auth_headers, session
):
    fact_id = await _fact(session)
    await session.flush()

    item = (await client.get(f"{FACTS}/{fact_id}", headers=auth_headers)).json()
    assert item["sources"] == []
    assert item["badge"]["origin_count"] == 0
    assert item["badge"]["origin_kinds"] == []


# ───────────────────── the belief window and the context ─────────────────────


async def test_the_detail_serves_the_whole_belief_window(
    client, auth_headers, session
):
    fact_id = await _fact(session, invalid_at=AS_OF)
    await _source(session, fact_id, origin="session-a")
    await session.flush()

    item = (await client.get(f"{FACTS}/{fact_id}", headers=auth_headers)).json()
    assert item["belief_window"]["valid_at"] is not None
    assert item["belief_window"]["invalid_at"] is not None
    assert item["belief_window"]["expired_at"] is None


async def test_applies_when_is_served_as_normalised_labels(
    client, auth_headers, session
):
    fact_id = await _fact(
        session, applies_when={"Env": "Prod", "version": "17"}
    )
    await _source(session, fact_id, origin="session-a")
    await session.flush()

    item = (await client.get(f"{FACTS}/{fact_id}", headers=auth_headers)).json()
    assert item["applies_when"] == {"Env": "Prod", "version": "17"}
    assert item["applies_when_labels"] == [
        {"axis": "env", "value": "prod"},
        {"axis": "version", "value": "17"},
    ]


async def test_a_neutral_context_carries_an_empty_label_set(
    client, auth_headers, session
):
    fact_id = await _fact(session)
    await _source(session, fact_id, origin="session-a")
    await session.flush()

    item = (await client.get(f"{FACTS}/{fact_id}", headers=auth_headers)).json()
    assert item["applies_when_labels"] == []


async def test_a_withdrawn_fact_is_still_reachable_by_id(
    client, auth_headers, session
):
    """Retained history has to be readable, or the retention answers nothing."""
    fact_id = await _fact(session, expired=True)
    await _source(session, fact_id, origin="session-a")
    await session.flush()

    response = await client.get(f"{FACTS}/{fact_id}", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["belief_window"]["expired_at"] is not None


async def test_project_scope_filters_the_list(client, auth_headers, session):
    mine = await _fact(session, obj="mine")
    await _source(session, mine, origin="session-a")
    theirs = await _fact(session, obj="theirs", project="somebody-else")
    await _source(session, theirs, origin="session-b")
    await session.flush()

    scoped = (
        await client.get(f"{FACTS}?project={PROJECT}", headers=auth_headers)
    ).json()
    assert [item["id"] for item in scoped["items"]] == [str(mine)]

    unscoped = (await client.get(FACTS, headers=auth_headers)).json()
    assert {str(mine), str(theirs)} <= {item["id"] for item in unscoped["items"]}


# ───────────────── the ladder history and the dispute block (T2.86) ─────────────────


async def test_the_detail_serves_its_ladder_oldest_to_newest(
    client, auth_headers, session
):
    fact_id = await _fact(session, status="corroborated")
    await _source(session, fact_id, origin="session-a")
    await record_event(
        session,
        event_type="sources_changed",
        object_type="fact",
        object_id=uuid.UUID(fact_id),
        project=PROJECT,
        payload={"outcome": "corroborated"},
    )
    await record_event(
        session,
        event_type="verified",
        object_type="fact",
        object_id=uuid.UUID(fact_id),
        project=PROJECT,
        payload={"outcome": "corroborate"},
    )
    await session.commit()

    item = (await client.get(f"{FACTS}/{fact_id}", headers=auth_headers)).json()
    assert [e["event_type"] for e in item["ladder"]] == [
        "sources_changed",
        "verified",
    ]
    # A different fact's own history must never leak onto this one.
    other = await _fact(session, obj="unrelated")
    await record_event(
        session,
        event_type="verified",
        object_type="fact",
        object_id=uuid.UUID(other),
        project=PROJECT,
        payload={},
    )
    await session.commit()
    item = (await client.get(f"{FACTS}/{fact_id}", headers=auth_headers)).json()
    assert len(item["ladder"]) == 2


async def test_the_ladder_past_the_cap_keeps_the_newest_events_not_the_oldest(
    client, auth_headers, session
):
    """T2.86 fix round (F1): ``LADDER_LIMIT`` used to keep the *oldest* 50
    events (``ORDER BY created_at ASC ... LIMIT 50``), dropping the newest
    transitions — exactly the ones that explain the fact's current badge. A
    ladder is read to understand how a fact got to its present state, so the
    cap must drop from the old end. 55 events, each carrying its own ordinal
    in the payload, is deliberately more than ``LADDER_LIMIT`` (50): a
    fixture at or under the cap cannot distinguish "kept the newest 50" from
    "kept the oldest 50" — both would return everything.
    """
    fact_id = await _fact(session, status="corroborated")
    await _source(session, fact_id, origin="session-a")
    for seq in range(55):
        await record_event(
            session,
            event_type="sources_changed",
            object_type="fact",
            object_id=uuid.UUID(fact_id),
            project=PROJECT,
            payload={"seq": seq},
        )
    await session.commit()

    item = (await client.get(f"{FACTS}/{fact_id}", headers=auth_headers)).json()
    assert item["ladder_total"] == 55
    assert len(item["ladder"]) == 50
    seqs = [e["payload"]["seq"] for e in item["ladder"]]
    # The newest 50 (5..54), still oldest-to-newest for chronological display.
    assert seqs == list(range(5, 55))


async def test_a_fact_with_no_journal_history_serves_an_empty_ladder(
    client, auth_headers, session
):
    fact_id = await _fact(session)
    await _source(session, fact_id, origin="session-a")
    await session.flush()

    item = (await client.get(f"{FACTS}/{fact_id}", headers=auth_headers)).json()
    assert item["ladder"] == []
    assert item["ladder_total"] == 0


async def test_an_undisputed_fact_serves_no_dispute_block(
    client, auth_headers, session
):
    fact_id = await _fact(session, status="corroborated")
    await _source(session, fact_id, origin="session-a")
    await session.flush()

    item = (await client.get(f"{FACTS}/{fact_id}", headers=auth_headers)).json()
    assert item["dispute"] is None


async def test_a_disputed_fact_serves_both_sides_structurally(
    client, auth_headers, session
):
    fact_id = await _fact(
        session, status="disputed", review_state="open", obj="docker"
    )
    await _source(session, fact_id, origin="session-a")
    counterpart_id = str(uuid.uuid4())
    await record_event(
        session,
        event_type="verified",
        object_type="fact",
        object_id=uuid.UUID(fact_id),
        project=PROJECT,
        payload={
            "contradiction": {
                "counterpart_id": counterpart_id,
                "counterpart_subject": "postgres",
                "counterpart_rel_type": "DEPLOYED_ON",
                "counterpart_object": "fly.io",
                "rule": "functional_object_conflict",
                "witness_origin": "origin-7",
                "enumeration": "first_finding",
            }
        },
    )
    await session.commit()

    item = (await client.get(f"{FACTS}/{fact_id}", headers=auth_headers)).json()
    dispute = item["dispute"]
    assert dispute is not None
    assert dispute["review_state"] == "open"
    assert dispute["claim"]["subject"] == "postgres"
    assert dispute["claim"]["object"] == "docker"
    assert dispute["counterpart"]["object"] == "fly.io"
    assert dispute["counterpart"]["id"] == counterpart_id
    assert dispute["rule"] == "functional_object_conflict"
    assert dispute["witness_origin"] == "origin-7"
    assert dispute["enumeration"] == "first_finding"
    # The sentence itself is doc 12 §4's two-sided claim, verbatim on the badge.
    assert item["badge"]["claim"].startswith("disputed:")
    assert "postgres DEPLOYED_ON fly.io" in item["badge"]["claim"]


async def test_a_disputed_fact_with_no_recorded_counterpart_says_so(
    client, auth_headers, session
):
    fact_id = await _fact(session, status="disputed", review_state="open")
    await _source(session, fact_id, origin="session-a")
    await session.flush()

    item = (await client.get(f"{FACTS}/{fact_id}", headers=auth_headers)).json()
    dispute = item["dispute"]
    assert dispute is not None
    assert dispute["counterpart"] is None
    assert dispute["counterpart_absent"] == "no_finding_recorded"
