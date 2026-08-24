"""Prices are an operator setting, and metering is on in production.

Two gaps this closes, both of which would have shipped a feature that measures
nothing. The recorder has to actually be handed to the orchestrator -- at boot
and on every live config swap, since a settings save replaces the orchestrator
object. And the price table has to be readable and writable, or the shipped
defaults are the only rates that will ever exist.
"""
from __future__ import annotations

import pytest
import pytest_asyncio
from sqlalchemy import select

from app.api.auth import require_auth
from app.main import app
from app.models.config import Config
from app.services.usage_pricing import (
    MODEL_PRICES_CONFIG_KEY,
    DEFAULT_MODEL_PRICES,
    resolve_rates,
)


@pytest_asyncio.fixture
async def authed(client):
    app.dependency_overrides[require_auth] = lambda: {"sub": "admin"}
    yield client
    app.dependency_overrides.pop(require_auth, None)


@pytest.mark.asyncio
async def test_prices_read_returns_shipped_defaults_when_nothing_is_set(authed):
    body = (await authed.get("/api/v1/usage/prices")).json()
    shipped = {r["model"]: r for r in body["models"]}
    assert set(shipped) >= set(DEFAULT_MODEL_PRICES)
    assert all(r["overridden"] is False for r in body["models"])


@pytest.mark.asyncio
async def test_an_override_is_stored_and_reported_as_an_override(authed, session):
    r = await authed.put("/api/v1/usage/prices", json={
        "prices": {"deepseek-v4-flash": {"input_micros_per_mtok": 999_999}},
    })
    assert r.status_code == 200
    row = (await session.execute(
        select(Config).where(Config.key == MODEL_PRICES_CONFIG_KEY)
    )).scalar_one()
    assert row.value["deepseek-v4-flash"]["input_micros_per_mtok"] == 999_999

    body = (await authed.get("/api/v1/usage/prices")).json()
    entry = next(m for m in body["models"] if m["model"] == "deepseek-v4-flash")
    assert entry["overridden"] is True
    assert entry["input_micros_per_mtok"] == 999_999
    # A partial override keeps the shipped values it did not mention: someone
    # correcting one number must not silently zero the other two.
    assert entry["output_micros_per_mtok"] == (
        DEFAULT_MODEL_PRICES["deepseek-v4-flash"].output_micros_per_mtok
    )


@pytest.mark.asyncio
async def test_a_model_with_no_shipped_default_can_be_priced(authed):
    r = await authed.put("/api/v1/usage/prices", json={
        "prices": {"house-model-1": {
            "input_micros_per_mtok": 1, "cached_micros_per_mtok": 1,
            "output_micros_per_mtok": 2,
        }},
    })
    assert r.status_code == 200
    body = (await authed.get("/api/v1/usage/prices")).json()
    assert any(m["model"] == "house-model-1" for m in body["models"])


@pytest.mark.asyncio
async def test_a_negative_rate_is_refused(authed):
    """A negative rate would produce a negative cost, and a total that a
    per-model edit can drive below zero is not a total."""
    r = await authed.put("/api/v1/usage/prices", json={
        "prices": {"deepseek-v4-flash": {"input_micros_per_mtok": -5}},
    })
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_an_unknown_rate_field_is_refused(authed):
    """Silently dropping it would leave the operator looking at a form that
    accepted their number and did nothing with it."""
    r = await authed.put("/api/v1/usage/prices", json={
        "prices": {"deepseek-v4-flash": {"per_request_micros": 5}},
    })
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_the_stored_row_is_what_pricing_resolves_against(authed, session):
    await authed.put("/api/v1/usage/prices", json={
        "prices": {"deepseek-v4-flash": {"input_micros_per_mtok": 42}},
    })
    row = (await session.execute(
        select(Config).where(Config.key == MODEL_PRICES_CONFIG_KEY)
    )).scalar_one()
    rates = resolve_rates("deepseek-v4-flash", row.value)
    assert rates.input_micros_per_mtok == 42


# ── the wiring that makes any of it happen ────────────────────────────

def test_the_boot_orchestrator_is_built_with_a_recorder():
    """Without this the whole feature is inert in production: every path
    reports to ``self._recorder``, and nothing was ever passing one."""
    import ast
    from pathlib import Path

    import app.main as main

    tree = ast.parse(Path(main.__file__).read_text())
    calls = [
        node for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "LLMOrchestrator"
    ]
    assert calls, "app/main.py no longer constructs an LLMOrchestrator"
    assert all(
        any(kw.arg == "recorder" for kw in call.keywords) for call in calls
    )


@pytest.mark.parametrize("module_name", ["app.api.routes.config", "app.api.routes.setup"])
def test_every_live_swap_rebuilds_with_a_recorder(module_name):
    """A settings save replaces the orchestrator object. One that forgot the
    recorder would turn metering off silently, and the symptom -- a cost graph
    that simply stops -- looks like an absence of spend."""
    import ast
    import importlib
    from pathlib import Path

    module = importlib.import_module(module_name)
    tree = ast.parse(Path(module.__file__).read_text())
    calls = [
        node for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "LLMOrchestrator"
    ]
    assert calls, f"{module_name} no longer constructs an LLMOrchestrator"
    assert all(
        any(kw.arg == "recorder" for kw in call.keywords) for call in calls
    )
