"""Doc 07 §5's composition — the keyspace, the ordering, the labels (T2.43)."""

from __future__ import annotations

from uuid import uuid4

import pytest

from app.services import layer_composition as lc


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
