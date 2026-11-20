"""Truth-first inject fill under a token budget (T3.10, doc 15 §3.4).

The fill turns a composed F3 selection into the ``list[str]`` that
``inject_block.render_block`` already takes. It adds a *budget* and a *layer
priority* — never a ranking of its own, which doc 15 §3.1 reserves to the
composition.

**Fixtures build their labels through :func:`fact_badge.row_labels`**, the same
producer ``compose`` uses, rather than hand-rolling a dict. A hand-rolled label
would let these tests pass against a shape production never emits — and the
label path is the whole point of the file.

Plan and its two review rounds:
``docs/superpowers/plans/2026-08-11-t3.10-truth-first-inject-fill.md``.
"""
from datetime import datetime, timezone

import pytest

from app.services.fact_badge import Badge, row_labels
from app.services.inject_fill import HEADER_RESERVE, estimate_tokens, fill
from app.services.layer_composition import ComposedResult, ComposedRow

AS_OF = datetime(2026, 8, 11, tzinfo=timezone.utc)
WIDE = 10_000


def _badge(status: str, claim: str) -> Badge:
    return Badge(
        verification_status=status,
        origin_count=3,
        origin_kinds=("human", "mcp"),
        as_of=AS_OF,
        contradiction=False,
        human_ratified=False,
        stale=False,
        claim=claim,
    )


def _row(
    *,
    id_kind: str,
    ident: str,
    status: str | None = None,
    claim: str | None = None,
    row: dict | None = None,
    gate_open: bool = True,
    labels: dict | None = None,
    supported_by: tuple = (),
) -> ComposedRow:
    """One composed row, labelled the way `compose` labels it.

    `gate_open` is the honest lever: with it False, `row_labels` runs the real
    serving boundary, which downgrades a promoted rung to `candidate`, sets
    `label_suppressed`, and drops the badge to None — the case this module
    exists to render correctly.
    """
    layer = {"memory": "L0", "fact": "L2", "article": "L3"}[id_kind]
    if labels is None:
        badge = None if id_kind == "memory" else _badge(status, claim or "a claim")
        labels = row_labels(
            id_kind=id_kind,
            verification_status=status,
            lifecycle=row.get("status") if row and id_kind == "memory" else None,
            badge=badge,
        )
    return ComposedRow(
        key=f"{id_kind}:{ident}",
        id=ident,
        id_kind=id_kind,
        layer=layer,
        channel_rank=1,
        verification_status=status,
        tier=0,
        band=0,
        cross_layer_rrf=0.0,
        rank_fusion_factor=1.0,
        weighted_score=1.0,
        labels=labels,
        dispute=None,
        row=row or {},
        grouping=None,
        supported_by=supported_by,
    )


def _result(*rows: ComposedRow) -> ComposedResult:
    return ComposedResult(rows=list(rows), envelope=None)


def _verified_fact(ident: str, claim: str = "a claim") -> ComposedRow:
    """`confirmed`, not `corroborated`, and the difference is the whole gate.

    `claim_gates.PROMOTED_STATUSES` is `{"corroborated"}` alone, so with G-C
    open a corroborated row *serves* as `candidate` — it is not verified to a
    reader. `confirmed` is human-only and ungated, so it is the one rung that
    still serves verified today. A fixture using `corroborated` here would
    quietly be a cold-start fixture and half these tests would prove nothing.
    """
    return _row(id_kind="fact", ident=ident, status="confirmed", claim=claim)


def _candidate_fact(ident: str, claim: str = "a candidate claim") -> ComposedRow:
    return _row(id_kind="fact", ident=ident, status="candidate", claim=claim)


def _article(ident: str) -> ComposedRow:
    return _row(id_kind="article", ident=ident, status="confirmed", claim="an article claim")


def _memory(ident: str, summary: str = "a summary", **row) -> ComposedRow:
    return _row(id_kind="memory", ident=ident, row={"summary": summary, **row})


# ------------------------------------------------------------------ ordering

def test_fill_order_is_facts_then_articles_then_memories():
    """Doc 15 §3.4's truth-first order. Composition hands rows back
    interleaved by band; the layer priority is the one reorder this task owns."""
    out = fill(_result(_memory("m"), _article("a"), _verified_fact("f")), token_budget=WIDE)

    layers = [next(tag for tag in ("(L2", "(L3", "(L0") if tag in item) for item in out.items]
    assert layers == ["(L2", "(L3", "(L0"]


def test_within_a_layer_composition_order_is_untouched():
    """Re-ranking inside a layer would be a second ranking authority, which
    doc 15 §3.1 forbids: inject adds a transport and a budget, not an order."""
    out = fill(
        _result(_verified_fact("f1", "first"), _verified_fact("f2", "second")),
        token_budget=WIDE,
    )

    assert [i for i, item in enumerate(out.items) if "first" in item] < [
        i for i, item in enumerate(out.items) if "second" in item
    ]


# -------------------------------------------------------------------- budget

def test_the_budget_stops_the_fill_and_never_truncates_an_item():
    long_claim = "x" * 600
    out = fill(
        _result(_verified_fact("f1", long_claim), _verified_fact("f2", long_claim)),
        token_budget=HEADER_RESERVE + estimate_tokens(long_claim) + 40,
    )

    assert len(out.items) == 1
    assert long_claim in out.items[0], "an item was truncated mid-text"


def test_an_item_that_does_not_fit_stops_the_fill_rather_than_being_skipped():
    """Scanning on for a smaller item would silently reorder by size — a
    ranking this task may not invent (plan D4)."""
    out = fill(
        _result(_verified_fact("big", "x" * 4000), _verified_fact("small", "tiny")),
        token_budget=HEADER_RESERVE + 20,
    )

    assert out.items == []


# ------------------------------------------------- the serving boundary (D8)

def test_a_suppressed_rung_renders_as_candidate_and_never_as_its_raw_status():
    """THE test. With G-C open the gate downgrades a promoted rung, and the
    row's own `verification_status` still holds the raw value wrapped in
    `unserved_status`. Rendering that field would put an ungated
    `corroborated` into text a model reads."""
    labels = row_labels(
        id_kind="fact", verification_status="corroborated", badge=_badge("corroborated", "c")
    )
    assert labels["verification_status"] == "candidate", "gate is not closed; test is vacuous"
    assert labels["label_suppressed"], "no suppression to render; test is vacuous"

    out = fill(_result(_row(id_kind="fact", ident="f", status="corroborated", labels=labels)),
               token_budget=WIDE)

    body = "\n".join(out.items)
    assert "corroborated" not in body
    assert "candidate" in body
    assert str(labels["label_suppressed"]) in body


def test_a_suppressed_row_renders_no_claim_and_does_not_raise():
    """A withheld status must not carry the badge asserting the corroboration
    it was withheld for, so `row_labels` sets badge=None. The fill renders the
    status and the reason instead of crashing on a missing claim (D8)."""
    labels = row_labels(
        id_kind="fact", verification_status="corroborated", badge=_badge("corroborated", "SECRET")
    )
    assert labels["badge"] is None, "suppression no longer drops the badge; revisit D8"

    out = fill(_result(_row(id_kind="fact", ident="f", status="corroborated", labels=labels)),
               token_budget=WIDE)

    assert "SECRET" not in "\n".join(out.items)
    assert len(out.items) == 1


def test_a_row_whose_labels_carry_no_badge_key_raises():
    """The `compose(badges=None)` path. Distinct from suppression, which is
    present-and-None: collapsing the two makes the gate working read as a bug."""
    labels = row_labels(id_kind="fact", verification_status="candidate", badge=None)
    del labels["badge"]

    with pytest.raises(KeyError):
        fill(_result(_row(id_kind="fact", ident="f", status="candidate", labels=labels)),
             token_budget=WIDE)


# ---------------------------------------------------------------- cold start

def test_candidates_are_absent_when_verified_items_landed():
    """Half one of D3. Without this, the cold-start test below passes against
    a fill that simply admits everything."""
    out = fill(
        _result(_verified_fact("ok", "verified claim"), _candidate_fact("no", "candidate claim")),
        token_budget=WIDE,
    )

    assert "candidate claim" not in "\n".join(out.items)


def test_candidates_are_injected_labelled_when_nothing_verified_fits():
    """Half two. Doc 15 §3.4: candidates are served only labelled, and only
    when nothing verified fits."""
    out = fill(_result(_candidate_fact("c", "the only claim")), token_budget=WIDE)

    body = "\n".join(out.items)
    assert "the only claim" in body
    assert "candidate" in body


def test_a_disputed_fact_is_unverified_and_therefore_cold_start_only():
    out = fill(
        _result(_verified_fact("ok", "verified claim"),
                _row(id_kind="fact", ident="d", status="disputed", claim="disputed claim")),
        token_budget=WIDE,
    )

    assert "disputed claim" not in "\n".join(out.items)


# --------------------------------------------------------------- L0 rendering

def test_a_memory_renders_its_summary_and_never_its_content():
    out = fill(
        _result(_memory("m", summary="the digest", content="the full prose")),
        token_budget=WIDE,
    )

    body = "\n".join(out.items)
    assert "the digest" in body
    assert "the full prose" not in body


def test_a_memory_with_no_summary_is_skipped_never_falling_back_to_content():
    out = fill(
        _result(_memory("m", summary="", content="the full prose")),
        token_budget=WIDE,
    )

    assert out.items == []


def test_a_superseded_memory_is_labelled_and_never_emitted_as_active():
    out = fill(
        _result(_memory("m", summary="old news", status="superseded")),
        token_budget=WIDE,
    )

    assert "superseded" in "\n".join(out.items)


# ------------------------------------------------------- structural absences

def test_an_absent_l3_channel_yields_an_empty_tier_never_an_error():
    """The Done-when added 2026-08-11 with the T3.23 dependency drop. Every
    fresh install has zero articles, so this is permanent behaviour."""
    out = fill(_result(_verified_fact("f"), _memory("m")), token_budget=WIDE)

    assert out.per_layer["L3"] == 0
    assert out.items, "the other tiers must still fill"


def test_nested_supporting_rows_are_not_rendered():
    """Plan D5: v1 spends the budget on distinct claims; the fact's badge
    already states its origin count."""
    nested = _memory("supporting", summary="the supporting memory")
    out = fill(
        _result(_row(id_kind="fact", ident="f", status="corroborated",
                     claim="a claim", supported_by=(nested,))),
        token_budget=WIDE,
    )

    assert "the supporting memory" not in "\n".join(out.items)


def test_a_marker_bearing_item_is_dropped_rather_than_failing_the_inject():
    """render_block raises on an embedded marker, and darkmem stores memories
    about darkmem — one such row would fail every session-start inject until
    it rotated out. The fill is the only layer that can degrade (D6)."""
    out = fill(
        _result(_memory("bad", summary="quoting <!-- darkmem:begin --> here"),
                _memory("good", summary="ordinary text")),
        token_budget=WIDE,
    )

    body = "\n".join(out.items)
    assert "darkmem:begin" not in body
    assert "ordinary text" in body
    assert out.dropped_markers == 1
