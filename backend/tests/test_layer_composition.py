"""Doc 07 §5's composition — the keyspace, the ordering, the labels (T2.43)."""

from __future__ import annotations

import json
from uuid import uuid4

import pytest
from sqlalchemy import text

from app.services import layer_composition as lc
from app.services.events import record_event
from app.services.verified_evidence import latest_verified_evidence

PROJECT = "t2-43-layer-composition"


def _memory_row(memory_id, **extra) -> dict:
    row = {
        "memory_id": memory_id,
        "payload": {"content": "a memory"},
        "project": "default",
        "status": "active",
        "rrf_score": 0.1,
    }
    row.update(extra)
    return row


def _fact_row(fact_id, *, verification_status="candidate", **extra) -> dict:
    row = {
        "fact_id": fact_id,
        "id": fact_id,
        "fact": "a fact",
        "subject_name": "postgres",
        "rel_type": "DEPLOYED_ON",
        "object_name": "homelab",
        "project": "default",
        "verification_status": verification_status,
        "review_state": None,
        "rrf_score": 0.1,
    }
    row.update(extra)
    return row


def _article_row(article_id, *, verification_status="candidate", **extra) -> dict:
    row = {
        "article_id": article_id,
        "title": "an article",
        "project": "default",
        "verification_status": verification_status,
        "review_state": None,
        "rrf_score": 0.1,
    }
    row.update(extra)
    return row


# ───────────────────────── the keyspace (D1) ─────────────────────────


def test_a_fact_and_a_memory_sharing_a_uuid_stay_two_rows():
    shared = uuid4()
    memory = lc.memory_candidate(_memory_row(shared), channel_rank=1)
    fact = lc.fact_candidate(_fact_row(shared), channel_rank=1)

    assert memory.key != fact.key
    assert memory.key == f"memory:{shared}"
    assert fact.key == f"fact:{shared}"
    assert memory.layer == "L0"
    assert fact.layer == "L2"


def test_a_uuid_and_its_string_are_one_row():
    raw = uuid4()
    as_uuid = lc.memory_candidate(_memory_row(raw), channel_rank=1)
    as_str = lc.memory_candidate(_memory_row(str(raw)), channel_rank=2)

    assert as_uuid.key == as_str.key
    assert as_uuid.id == str(raw)


def test_the_wire_id_is_the_bare_id_and_agrees_with_the_key():
    from uuid import UUID

    raw = uuid4()
    for candidate in (
        lc.memory_candidate(_memory_row(raw), channel_rank=1),
        lc.fact_candidate(_fact_row(raw), channel_rank=1),
        lc.article_candidate(_article_row(raw), channel_rank=1),
    ):
        assert candidate.key == f"{candidate.id_kind}:{candidate.id}"
        assert UUID(candidate.id) == raw


def test_composition_key_refuses_an_unnormalised_id():
    with pytest.raises(TypeError):
        lc.composition_key("memory", uuid4())


def test_composition_key_refuses_a_foreign_space():
    with pytest.raises(ValueError):
        lc.composition_key("code", str(uuid4()))


def test_a_candidate_cannot_claim_a_foreign_layer():
    with pytest.raises(TypeError):
        lc.LayerCandidate(
            id=str(uuid4()), id_kind="fact", layer="L0", channel_rank=1, row={},
        )


# ─────────────── the dispute, served with both sides (D8) ───────────────


def _counterpart_block(**overrides) -> dict:
    block = {
        "counterpart_id": str(uuid4()),
        "counterpart_subject": "postgres",
        "counterpart_rel_type": "DEPLOYED_ON",
        "counterpart_object": "fly.io",
        "rule": "functional_object_conflict",
        "witness_origin": "origin-7",
        "enumeration": "first_finding",
    }
    block.update(overrides)
    return block


def test_an_undisputed_fact_has_no_dispute_label():
    row = _fact_row(uuid4(), verification_status="corroborated")
    assert lc.dispute_label(row, None) is None


def test_both_sides_are_rendered_in_the_same_shape():
    block = _counterpart_block()
    row = _fact_row(uuid4(), verification_status="disputed", review_state="open")
    label = lc.dispute_label(row, {"payload": {"contradiction": block}})

    assert set(label["claim"]) == set(label["counterpart"])
    assert set(label["claim"]) == {"subject", "rel_type", "object", "id"}
    assert label["claim"]["subject"] == "postgres"
    assert label["claim"]["object"] == "homelab"
    assert label["counterpart"]["object"] == "fly.io"
    assert label["counterpart"]["id"] == block["counterpart_id"]
    assert label["rule"] == "functional_object_conflict"
    assert label["witness_origin"] == "origin-7"


def test_an_absent_block_is_not_an_absent_dispute():
    row = _fact_row(uuid4(), verification_status="disputed", review_state="open")
    label = lc.dispute_label(row, {"payload": {"outcome": "dispute"}})

    assert label is not None
    assert label["counterpart"] is None
    assert label["counterpart_absent"] == lc.COUNTERPART_ABSENT_NO_FINDING
    assert lc.dispute_label(_fact_row(uuid4()), None) is None


def test_the_dispute_label_carries_no_count():
    block = _counterpart_block()
    row = _fact_row(uuid4(), verification_status="disputed", review_state="open")
    label = lc.dispute_label(row, {"payload": {"contradiction": block}})

    assert label["enumeration"] == "first_finding"
    for banned in ("count", "total", "contradiction_count", "contradiction_total"):
        assert banned not in label


@pytest.mark.asyncio
async def test_the_counterpart_comes_from_the_latest_verified_event(session):
    fact_id = uuid4()
    # The stale event is written *second* so it holds the higher identity
    # column. Ordering by identity alone would therefore serve it — which is
    # what makes the created_at term in the reader's ORDER BY breakable.
    await record_event(
        session,
        event_type="verified",
        object_type="fact",
        object_id=fact_id,
        project=PROJECT,
        payload={"contradiction": _counterpart_block(counterpart_object="fresh")},
    )
    await session.execute(
        text(
            "INSERT INTO events (created_at, event_type, object_type, object_id, "
            "project, payload) VALUES (now() - interval '1 minute', 'verified', "
            "'fact', CAST(:id AS uuid), :project, CAST(:payload AS jsonb))"
        ),
        {
            "id": str(fact_id),
            "project": PROJECT,
            "payload": json.dumps(
                {"contradiction": _counterpart_block(counterpart_object="stale")}
            ),
        },
    )
    await session.commit()

    evidence = await latest_verified_evidence(session, [str(fact_id)])
    row = _fact_row(fact_id, verification_status="disputed", review_state="open")
    label = lc.dispute_label(row, evidence.get(str(fact_id)))

    assert label["counterpart"]["object"] == "fresh"
