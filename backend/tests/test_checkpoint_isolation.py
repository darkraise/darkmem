"""A checkpoint is operational state, never vault knowledge (T3.18, doc 13 §6).

A checkpoint is what an agent said about its own run. Nothing judged it, so a
verification rung on one would be an unearned badge on unverified prose, and a
checkpoint reaching the fact ladder would put agent notes into the vault beside
corroborated facts.

**Every test here asserts an ABSENCE, and that is deliberate.** T3.16 already
built most of the isolation — `session_checkpoints` is its own table with no
foreign key to `memories`, and checkpoints never touch `memory_buffer` or the
pipeline — so the tempting shape, "filter checkpoints out of the fact query" or
"assert no badge renders on the checkpoint list", would quantify over an empty
set and pass forever while proving nothing. That is the T2.108 vacuity pattern.
What is testable is that no route *exists*: no module outside the checkpoint
slice reaches the table, no verification column exists to serve, and no field on
the wire could carry a badge.
"""
from pathlib import Path

from app.models.checkpoint import SessionCheckpoint
from app.schemas.checkpoint import CheckpointResponse
from app.services.embedder_registry import _TABLE_TEMPLATES

from tests._reachability_scan import (
    ReachabilityRules,
    app_sources,
    find_forbidden_reach,
)

BACKEND = Path(__file__).resolve().parent.parent

# The whole checkpoint slice: the model, its export, and the one service every
# door goes through. `app/api/routes/checkpoints.py` and the MCP door are
# deliberately NOT here — they reach the *service*, never the table, and this
# allowlist is what keeps that true.
CHECKPOINT_SLICE = frozenset({
    "app/models/checkpoint.py",
    "app/models/__init__.py",
    "app/services/checkpoints.py",
})

# The six operational fields. Written out rather than counted, so adding a
# seventh is a decision someone makes in this file with the docstring above in
# view — not a number that quietly increments.
OPERATIONAL_FIELDS = {"id", "origin_key", "project", "summary", "next_steps", "created_at"}


def test_no_module_outside_the_checkpoint_slice_reaches_the_table():
    """The fact ladder, the retrieval channels, the dream family and the
    embedding writers must have no route to `session_checkpoints` at all.

    Stated as an allowlist rather than a blocklist of vault modules: a
    blocklist protects only the modules someone remembered to name, and the
    module that wires checkpoints into the vault next year will be one nobody
    listed. Anything new that needs checkpoints goes through the service.
    """
    rules = ReachabilityRules(
        forbidden_modules=frozenset({"app.models.checkpoint"}),
        forbidden_attrs=frozenset({"SessionCheckpoint"}),
        forbidden_literals=frozenset({"session_checkpoints"}),
    )
    offenders = find_forbidden_reach(
        app_sources(BACKEND), BACKEND, rules, skip_files=CHECKPOINT_SLICE
    )

    assert offenders == [], (
        "these modules reach the checkpoint table directly. A checkpoint is "
        "operational state; a path from the vault or retrieval into it is how "
        "unverified agent notes become indistinguishable from judged facts. "
        f"Go through app/services/checkpoints.py instead: {offenders}"
    )


def test_a_checkpoint_carries_no_verification_column():
    """There is no rung to serve, so no reader can invent one.

    The model's own docstring reserves this rule for T3.18; this is where it
    becomes enforceable. Any column beyond the six operational ones has to be
    argued for here first.
    """
    columns = {c.name for c in SessionCheckpoint.__table__.columns}

    assert columns == OPERATIONAL_FIELDS, (
        "session_checkpoints' columns changed. A verification, status, badge or "
        "confidence column here would be a rung on prose no ladder judged: "
        f"unexpected={sorted(columns - OPERATIONAL_FIELDS)} "
        f"missing={sorted(OPERATIONAL_FIELDS - columns)}"
    )


def test_the_checkpoint_response_serves_no_badge():
    """The wire cannot carry a badge, so no UI can render one.

    T3.21 builds the only checkpoint surface and does not exist yet, so a
    "no badge renders" assertion against the DOM would have nothing to render
    against. Enforcing it at the schema means the guard is already standing
    when that surface arrives — and T3.21 inherits the pixel-level half.
    """
    served = set(CheckpointResponse.model_fields)

    assert served == OPERATIONAL_FIELDS, (
        "CheckpointResponse's fields changed; a verification or badge field "
        f"here would render on T3.21's surface: {sorted(served ^ OPERATIONAL_FIELDS)}"
    )


def test_checkpoints_have_no_embedding_partition():
    """No embedding writer means checkpoints cannot enter a retrieval channel.

    The vault channels search per-fingerprint partitions. A table with no
    parent template has nothing for `child_table` to address, so the exclusion
    holds by construction rather than by a filter somebody has to remember.
    """
    assert "session_checkpoints" not in _TABLE_TEMPLATES
    assert not any("checkpoint" in parent for parent in _TABLE_TEMPLATES), (
        "an embedding partition parent now mentions checkpoints: "
        f"{sorted(_TABLE_TEMPLATES)}"
    )
