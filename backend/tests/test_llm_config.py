"""Purpose resolution is ONE query, and `api_kind` is the only vendor field.

Doc 04 §7 and doc 11 §2 flatten the LLM config: each of the six purposes is one
inline `llm_purpose_configs` row carrying its own connection details, so
resolution is a single un-joined read. The `llm_providers` / `llm_profiles` /
`ml_profiles` indirection cost three levels of resolution on every call and is
gone.

The one-query property is the kind that decays silently — a later change that
resolves a reference per purpose still returns correct config, just six times
slower per call, and no functional test would notice. So it is asserted by
counting queries rather than by inspecting the result (T1.01).
"""
from __future__ import annotations

import pytest
from sqlalchemy import event, text

from app.services.config import PURPOSES, get_llm_config


class _QueryCounter:
    """Counts SQL statements issued on one session's connection."""

    def __init__(self) -> None:
        self.statements: list[str] = []

    def __call__(self, conn, cursor, statement, parameters, context, executemany):
        self.statements.append(statement)

    @property
    def selects(self) -> list[str]:
        return [s for s in self.statements if s.lstrip().upper().startswith("SELECT")]


async def _count_resolution_queries(session):
    # Listen on the engine rather than the session's Connection: reaching the
    # connection from here would itself do IO outside the greenlet. Nothing else
    # runs against this engine during a test, so every statement counted is the
    # one call under test.
    from tests.conftest import test_engine

    counter = _QueryCounter()
    target = test_engine.sync_engine
    event.listen(target, "before_cursor_execute", counter)
    try:
        config = await get_llm_config(session)
    finally:
        event.remove(target, "before_cursor_execute", counter)
    return config, counter


@pytest.mark.asyncio
async def test_purpose_resolution_is_a_single_query(session):
    config, counter = await _count_resolution_queries(session)

    assert len(counter.selects) == 1, (
        "purpose resolution must be one query; got "
        f"{len(counter.selects)}:\n" + "\n".join(counter.selects)
    )
    assert set(config) == set(PURPOSES)


@pytest.mark.asyncio
async def test_resolution_does_not_scale_with_the_number_of_rows(session):
    """One query for zero rows and one for six. A per-purpose resolution would
    show up here as six, which is exactly the indirection this replaced."""
    _, empty = await _count_resolution_queries(session)

    for purpose in PURPOSES:
        await session.execute(
            text(
                "INSERT INTO llm_purpose_configs (purpose, model, api_kind, base_url) "
                "VALUES (:p, 'a-model', 'openai', 'http://example.invalid/v1')"
            ),
            {"p": purpose},
        )
    await session.flush()

    _, populated = await _count_resolution_queries(session)
    assert len(empty.selects) == len(populated.selects) == 1


@pytest.mark.asyncio
async def test_resolution_joins_nothing(session):
    _, counter = await _count_resolution_queries(session)
    sql = counter.selects[0].upper()
    assert "JOIN" not in sql
    assert "LLM_PROVIDERS" not in sql
    assert "LLM_PROFILES" not in sql
    assert "ML_PROFILES" not in sql


# ── The indirection tables are gone, not merely unused ──────────────


@pytest.mark.asyncio
@pytest.mark.parametrize("table", ["llm_providers", "llm_profiles", "ml_profiles"])
async def test_indirection_tables_do_not_exist(session, table):
    exists = (
        await session.execute(
            text("SELECT to_regclass(:t) IS NOT NULL"), {"t": f"public.{table}"}
        )
    ).scalar_one()
    assert exists is False


@pytest.mark.asyncio
@pytest.mark.parametrize("column", ["provider_id", "profile_id", "ml_profile_id"])
async def test_ref_columns_are_gone_from_the_table(session, column):
    present = (
        await session.execute(
            text(
                "SELECT count(*) FROM information_schema.columns "
                "WHERE table_name = 'llm_purpose_configs' AND column_name = :c"
            ),
            {"c": column},
        )
    ).scalar_one()
    assert present == 0


# ── api_kind is the sole vendor field (F-10) ────────────────────────


@pytest.mark.asyncio
async def test_provider_column_is_dropped(session):
    """`provider` duplicated `api_kind` — the wizard wrote it as a verbatim copy
    and nothing ever dispatched on it, so a second vendor column could only
    drift away from the one that decides behaviour."""
    present = (
        await session.execute(
            text(
                "SELECT count(*) FROM information_schema.columns "
                "WHERE table_name = 'llm_purpose_configs' AND column_name = 'provider'"
            )
        )
    ).scalar_one()
    assert present == 0


@pytest.mark.asyncio
async def test_api_kind_survives_as_the_vendor_field(session):
    present = (
        await session.execute(
            text(
                "SELECT count(*) FROM information_schema.columns "
                "WHERE table_name = 'llm_purpose_configs' AND column_name = 'api_kind'"
            )
        )
    ).scalar_one()
    assert present == 1


@pytest.mark.asyncio
async def test_resolved_config_carries_the_inline_connection_details(session):
    await session.execute(
        text(
            "INSERT INTO llm_purpose_configs "
            "(purpose, model, api_kind, base_url, api_key, params) "
            "VALUES ('extraction', 'a-model', 'deepseek', "
            "'https://api.example.invalid/v1', 'sk-test', '{\"temperature\": 0}'::jsonb)"
        )
    )
    await session.flush()

    config = await get_llm_config(session)
    extraction = config["extraction"]
    assert extraction.model == "a-model"
    assert extraction.api_kind == "deepseek"
    assert extraction.base_url == "https://api.example.invalid/v1"
    assert extraction.api_key == "sk-test"
    assert extraction.params == {"temperature": 0}


@pytest.mark.asyncio
async def test_absent_purposes_fall_back_to_settings_defaults(session):
    # A fresh install has no rows until the wizard finalizes; resolution must
    # still return all six purposes rather than raising.
    config = await get_llm_config(session)
    assert set(config) == set(PURPOSES)
    assert config["embedding"].model
