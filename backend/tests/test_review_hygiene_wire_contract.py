"""Wire contract: the TS interfaces T2.37 mirrors from this backend must not
silently drift from what it actually returns (F10, review-findings.md).

No cross-language contract test existed anywhere in this repo before this
file. What does exist is a strong backend-internal convention for asserting a
hand-assembled dict's keys against a Pydantic model's (or a literal set) —
``test_serialization_parity.py``'s ``assert set(row) == set(Model.model_fields)``
and ``test_review_state_transitions.py``'s
``TestThePayloadShape...::test_the_payload_shape_is_the_one_gc_reads``. This
extends that idiom across the language boundary: it regex-extracts each TS
interface's own field names from its source file and asserts them against the
Pydantic model (or, for the two hand-built dicts on the evidence/contradiction
path, against the real keys a direct call produces) — so a backend rename
that forgets the frontend fails here, loudly, naming the field, rather than
leaving the TS interface and its own tests agreeing with each other while
disagreeing with the wire.
"""

from __future__ import annotations

import re
from pathlib import Path

from app.schemas.facts import FactListItem
from app.schemas.hygiene_queue import HygieneDuplicateItem, HygieneMemoryItem
from app.schemas.review_queue import ReviewQueueFactItem
from app.services.contradiction_veto import ContradictionFinding
from app.services.verification_ladder import contradiction_evidence

FRONTEND_HOOKS = (
    Path(__file__).resolve().parents[2] / "frontend" / "src" / "hooks" / "api"
)


def _ts_interface_fields(file_name: str, interface: str) -> set[str]:
    text = (FRONTEND_HOOKS / file_name).read_text()
    match = re.search(rf"export interface {interface} \{{(.*?)\n\}}", text, re.S)
    assert match, (
        f"{interface} not found in {file_name} — the TS side was renamed or "
        "moved; update this test's target alongside it"
    )
    body = match.group(1)
    return set(re.findall(r"^\s*(\w+)\??:\s", body, re.M))


def test_review_queue_fact_item_matches_ts():
    assert _ts_interface_fields(
        "use-review-queue-api.ts", "ReviewQueueFactItem"
    ) == set(ReviewQueueFactItem.model_fields)


def test_hygiene_duplicate_item_matches_ts():
    assert _ts_interface_fields(
        "use-hygiene-queue-api.ts", "HygieneDuplicateItem"
    ) == set(HygieneDuplicateItem.model_fields)


def test_hygiene_memory_item_matches_ts():
    assert _ts_interface_fields(
        "use-hygiene-queue-api.ts", "HygieneMemoryItem"
    ) == set(HygieneMemoryItem.model_fields)


def test_fact_list_item_matches_ts():
    """N2 (T2.56 fix round 2): F9 widened ``FactListItem`` with ``unverified``
    on the backend but the TS mirror in ``use-knowledge-api.ts`` had no
    contract test to catch the drift — this closes that gap the way the
    other three surfaces above already are.
    """
    assert _ts_interface_fields(
        "use-knowledge-api.ts", "FactListItem"
    ) == set(FactListItem.model_fields)


def test_contradiction_evidence_matches_ts():
    """``contradiction_evidence`` returns a plain dict, not a Pydantic model
    or TypedDict — exercised directly (no DB needed, ``ContradictionFinding``
    is a plain frozen dataclass) rather than pinned as a literal, so a field
    added or dropped there is caught by calling the real function.
    """
    finding = ContradictionFinding(
        fact_id="f1",
        counterpart_id="f2",
        rule="direct_negation",
        witness_origin="human:tester",
    )
    assert _ts_interface_fields(
        "use-review-queue-api.ts", "VerifiedEvidenceContradiction"
    ) == set(contradiction_evidence(finding))


def test_verified_evidence_payload_matches_ts():
    """The exact key set ``knowledge_triples.set_verification_status``
    journals for a disputed transition with a fired contradiction veto —
    proved live, against a real DB-produced payload, by
    ``test_review_state_transitions.py::TestThePayloadShape...
    ::test_the_payload_shape_is_the_one_gc_reads``. Duplicated here as a
    literal rather than imported (that test builds the payload through a full
    fixture + ``recompute_fact`` round trip, not a reusable constant) — if the
    backend widens the payload without updating that test, that test fails
    first; this one only guards the TS side staying in step with the same
    known-correct set.
    """
    backend_keys = {
        "before",
        "after",
        "outcome",
        "origin_count",
        "required_n",
        "gate_fired",
        "source_kinds",
        "contradiction_blocked",
        "supersession_blocked",
        "confidence",
        "contradiction",
    }
    assert (
        _ts_interface_fields("use-review-queue-api.ts", "VerifiedEvidencePayload")
        == backend_keys
    )
