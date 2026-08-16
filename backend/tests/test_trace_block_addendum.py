"""The `block` id-kind and `document` layer are additive (TH1.07, doc 16 §4).

An addendum to a *shared* vocabulary has two halves and the second is the one
that is easy to skip. A block row must be labelled well enough that anything
generic over `id_kind` can read it — and the composition's closed vocabulary
must still refuse it, because a horizon kind that quietly joined the enum would
make every core consumer's exhaustiveness wrong without changing a line of
their code.

So this file asserts both directions, and it imports the real constants rather
than restating the strings: two copies of a vocabulary agree on paper for
exactly as long as nobody edits one.
"""
from __future__ import annotations

import pytest

from app.services.block_query import BLOCK_ID_KIND, BLOCK_LAYER, BlockHit
from app.services.layer_composition import (
    ID_KINDS,
    LAYER_BY_ID_KIND,
    LayerCandidate,
    composition_key,
)


def _hit(**overrides) -> BlockHit:
    base = dict(
        block_id="b1", document_id="d1", project="p", uri=None, type="paragraph",
        text="text", order_index=0, char_span=(0, 4), score=0.9,
    )
    base.update(overrides)
    return BlockHit(**base)


# ── the addendum exists and rides the row ────────────────────────────


def test_every_block_hit_is_labelled_with_its_kind_and_layer():
    hit = _hit()
    assert hit.id_kind == BLOCK_ID_KIND == "block"
    assert hit.layer == BLOCK_LAYER == "document"


def test_the_labels_ride_the_row_rather_than_an_envelope():
    """A row that travels alone — into a citation, a log line, a future
    document surface — must carry what kind of thing it is with it. An
    envelope-only label is lost the moment a row is passed on by itself."""
    hit = _hit()
    assert {"id_kind", "layer"} <= set(vars(hit))


# ── and the composition still refuses it ─────────────────────────────


def test_block_is_not_in_the_composition_vocabulary():
    assert BLOCK_ID_KIND not in ID_KINDS
    assert BLOCK_ID_KIND not in LAYER_BY_ID_KIND
    assert BLOCK_LAYER not in set(LAYER_BY_ID_KIND.values())


def test_the_composition_refuses_a_block_key_loudly():
    """Loudly, not silently: an unknown kind that produced a usable merge key
    would fuse a horizon row into the core read path, which is the firewall
    breach doc 16 §1 calls a Tier-3 amendment."""
    with pytest.raises(ValueError) as raised:
        composition_key(BLOCK_ID_KIND, "b1")
    assert BLOCK_ID_KIND in str(raised.value)


def test_a_block_layer_candidate_cannot_be_built():
    """The type is the composition's first refusal mechanism, and it refuses on
    the kind before anything downstream can drop the row silently."""
    with pytest.raises(TypeError) as raised:
        LayerCandidate(
            id="b1",
            id_kind=BLOCK_ID_KIND,
            layer=BLOCK_LAYER,
            channel_rank=1,
            row={},
        )
    assert BLOCK_ID_KIND in str(raised.value)


# ── the core trace schema is untouched ───────────────────────────────


def test_the_core_trace_schema_carries_nothing_block_shaped():
    """"Additive" has to mean the core contract did not move. A consumer that
    does not speak this channel must not acquire a field, an optional or a
    branch because the horizon exists."""
    from app.schemas.retrieval_trace import MemoryResultTrace, RetrievalEnvelope

    core_fields = set(MemoryResultTrace.model_fields) | set(RetrievalEnvelope.model_fields)
    assert not any("block" in name or "document" in name for name in core_fields)


def test_the_core_id_kind_vocabulary_is_exactly_the_three_layers():
    """Pinned, so adding a fourth composition kind is a deliberate diff rather
    than something a horizon lane can do by accident."""
    assert ID_KINDS == frozenset({"memory", "fact", "article"})
    assert set(LAYER_BY_ID_KIND) == {"memory", "fact", "article"}
