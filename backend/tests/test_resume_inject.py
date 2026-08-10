"""Resume as a specialised inject (T3.17, doc 15 §3.2).

At session start the latest checkpoint leads the managed block, so a fresh
session loads a budgeted digest instead of reloading full context. Resume is
**not a second inject path**: it is the ordinary fill with the checkpoint
admitted first, spending the same budget through the same code.

The Done-when that shapes this file — *"resume reuses the T3.10 budget path,
not a parallel one"* — is only testable as an absence of a second budget. So
the tests below assert the lead is charged against the same budget and that a
missing checkpoint degrades to exactly the block the ordinary inject would have
produced, byte for byte.
"""
from app.services.inject_fill import HEADER_RESERVE, estimate_tokens, fill
from app.services.resume_inject import render_checkpoint

from tests.test_inject_fill import _memory, _result, _verified_fact


class _Checkpoint:
    """The two fields resume reads. Not the ORM row: these tests are pure, and
    binding them to the model would make a column rename read as a resume bug."""

    def __init__(self, summary="where I left off", next_steps=("do the thing",)):
        self.summary = summary
        self.next_steps = list(next_steps)


def test_the_checkpoint_leads_the_block():
    out = fill(_result(_verified_fact("f")), token_budget=10_000,
               lead=render_checkpoint(_Checkpoint()))

    assert "where I left off" in out.items[0]


def test_the_checkpoint_renders_its_next_steps():
    rendered = render_checkpoint(_Checkpoint(next_steps=("first thing", "second thing")))

    assert "first thing" in rendered
    assert "second thing" in rendered


def test_a_missing_checkpoint_degrades_to_the_ordinary_inject():
    """Byte-for-byte, not merely 'still works'. A resume path that produced a
    subtly different block when the checkpoint was absent would be the parallel
    path the Done-when forbids, and it would only show up on fresh runs."""
    rows = _result(_verified_fact("f"), _memory("m"))

    assert fill(rows, token_budget=10_000, lead=None) == fill(rows, token_budget=10_000)


def test_the_lead_is_charged_against_the_same_budget():
    """The lead is not free. If resume computed its own budget, the block would
    exceed the one the operator set by exactly the checkpoint's size."""
    lead = render_checkpoint(_Checkpoint(summary="y" * 300))
    rows = _result(_verified_fact("f", "x" * 300))

    with_lead = fill(rows, token_budget=10_000, lead=lead)
    without = fill(rows, token_budget=10_000)

    assert with_lead.tokens_used > without.tokens_used
    assert with_lead.tokens_used >= estimate_tokens(lead)


def test_a_lead_that_does_not_fit_stops_the_fill_and_emits_nothing():
    """The budget rule is the fill's, unchanged: an item that does not fit
    stops the fill rather than being skipped over."""
    out = fill(_result(_verified_fact("f", "tiny")), token_budget=HEADER_RESERVE + 5,
               lead=render_checkpoint(_Checkpoint(summary="z" * 4000)))

    assert out.items == []


def test_a_marker_bearing_checkpoint_is_dropped_not_raised():
    """A checkpoint is agent-authored prose about a run, so a run that touched
    the inject writer can quote the markers verbatim. It must degrade like any
    other item rather than failing every resume until it rotates out."""
    out = fill(_result(_verified_fact("f", "ordinary")), token_budget=10_000,
               lead=render_checkpoint(_Checkpoint(summary="see <!-- darkmem:begin -->")))

    body = "\n".join(out.items)
    assert "darkmem:begin" not in body
    assert "ordinary" in body
    assert out.dropped_markers == 1


def test_the_checkpoint_carries_no_verification_label():
    """T3.18's rule, enforced where the checkpoint reaches a model's context: a
    checkpoint is operational state, so it must not render beside the vault
    items wearing anything that reads as a rung."""
    rendered = render_checkpoint(_Checkpoint())

    for word in ("candidate", "corroborated", "confirmed", "disputed", "verified"):
        assert word not in rendered.lower()
