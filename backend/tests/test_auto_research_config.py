"""The `auto_research` config row gets its one writer (T3.28, doc 09 §6).

Nothing wrote this row before: arming the loop meant a manual database write,
deliberately — "building the door is not arming the loop". The owner asked for
an operator surface, which is a different thing from arming it by default, so
the default stays `False` and every test below assumes a fresh install refuses.

**The `enabled` field is the one with teeth.** `bool("false")` is `True`, and
`{"enabled": "false"}` is the most natural malformed shape an operator writes —
T3.07's review found exactly that arming the master switch. So the writer
refuses non-booleans rather than coercing them, and each refused shape gets its
own case: a coercion that can only fail open has no safe direction, and a
single "bad value" test passes while three of the four shapes leak.
"""
from __future__ import annotations

import pytest
from sqlalchemy import text

from app.services.research_config import (
    AUTO_RESEARCH_CONFIG_KEY,
    AUTO_RESEARCH_DEFAULTS,
    load_budget,
    write_auto_research_config,
)

pytestmark = pytest.mark.asyncio


async def _stored(session) -> dict | None:
    row = (await session.execute(
        text("SELECT value FROM config WHERE key = :k"),
        {"k": AUTO_RESEARCH_CONFIG_KEY},
    )).scalar_one_or_none()
    return row


# ── the default is disarmed, and stays that way ──────────────────────


async def test_a_never_configured_install_is_disarmed(session):
    budget = await load_budget(session)
    assert budget.enabled is False
    assert AUTO_RESEARCH_DEFAULTS["enabled"] is False


async def test_writing_only_a_budget_does_not_arm_it(session):
    """Arming is an explicit act. Setting a cap must not turn the loop on as a
    side effect of touching the row for the first time."""
    budget = await write_auto_research_config(session, {"max_findings_per_run": 5})

    assert budget.enabled is False
    assert budget.max_findings_per_run == 5


# ── enabled fails closed on every non-boolean ────────────────────────


@pytest.mark.parametrize("value", ["false", "true", "1", 1, 0, None, [], {}])
async def test_enabled_refuses_every_non_boolean(session, value):
    with pytest.raises(ValueError) as raised:
        await write_auto_research_config(session, {"enabled": value})

    assert "boolean" in str(raised.value)
    assert await _stored(session) is None, "a refused write must leave no row"


async def test_enabled_accepts_a_real_boolean_both_ways(session):
    armed = await write_auto_research_config(session, {"enabled": True})
    assert armed.enabled is True

    disarmed = await write_auto_research_config(session, {"enabled": False})
    assert disarmed.enabled is False


# ── the rest of the shape ────────────────────────────────────────────


@pytest.mark.parametrize("key", ["max_findings_per_run", "max_content_chars"])
@pytest.mark.parametrize("value", [0, -1, "20", 2.5, True, None])
async def test_the_budgets_refuse_a_non_positive_integer(session, key, value):
    with pytest.raises(ValueError):
        await write_auto_research_config(session, {key: value})


async def test_an_unknown_key_is_refused_rather_than_ignored(session):
    """An operator who misspells a setting must be told, or they will believe
    they set a budget they did not."""
    with pytest.raises(ValueError) as raised:
        await write_auto_research_config(session, {"max_findings": 5})

    assert "max_findings" in str(raised.value)
    assert await _stored(session) is None


async def test_a_partial_update_does_not_reset_the_other_fields(session):
    await write_auto_research_config(
        session, {"enabled": True, "max_findings_per_run": 7},
    )

    budget = await write_auto_research_config(session, {"max_content_chars": 1234})

    assert budget.enabled is True, "a partial update reset the master switch"
    assert budget.max_findings_per_run == 7
    assert budget.max_content_chars == 1234


async def test_the_writer_returns_what_the_reader_resolves(session):
    """Not an echo of the request: the clamps and the fail-closed parse live on
    the read path, so an echo could disagree with what a run will do."""
    written = await write_auto_research_config(
        session, {"enabled": True, "max_findings_per_run": 10_000},
    )
    read = await load_budget(session)

    assert written == read
    assert written.max_findings_per_run < 10_000, "the reader's clamp must show"


# ── exactly one writer ───────────────────────────────────────────────


def test_the_config_row_has_exactly_one_writer():
    """A second writer is how a strict parse gets bypassed: the guard lives in
    `write_auto_research_config`, so anything else touching the row would arm
    the loop without passing it."""
    import ast
    from pathlib import Path

    backend = Path(__file__).resolve().parent.parent
    sources = [p for p in (backend / "app").rglob("*.py") if "__pycache__" not in str(p)]
    assert len(sources) > 100, "the scan would pass vacuously; check the glob"

    writer_module = backend / "app" / "services" / "research_config.py"
    offenders = []
    for path in sources:
        if path == writer_module:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            # A Config(...) construction or an assignment to `.value` in a
            # module that also names the key is the shape a second writer takes.
            if isinstance(node, ast.Constant) and node.value == AUTO_RESEARCH_CONFIG_KEY:
                source = path.read_text(encoding="utf-8")
                if "Config(" in source or ".value =" in source:
                    offenders.append(str(path.relative_to(backend)))
                break
    assert not offenders, f"a second writer of the auto_research row: {offenders}"
