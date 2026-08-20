"""The provider layer: one row per vendor connection, referenced by purpose.

Doc 04 §7's flattening is reversed by the owner ruling of 2026-08-20
(`docs/superpowers/specs/2026-08-20-llm-providers-design.md` §0). Connection
details live here; a purpose contributes only what varies per purpose.
"""
from __future__ import annotations

import pytest
from sqlalchemy import select, text

from app.models.llm_provider import LLMProviderRow


@pytest.mark.asyncio
async def test_llm_providers_table_exists(session):
    exists = (
        await session.execute(
            text("SELECT to_regclass('public.llm_providers') IS NOT NULL")
        )
    ).scalar_one()
    assert exists is True


@pytest.mark.asyncio
async def test_provider_row_round_trips(session):
    session.add(
        LLMProviderRow(
            name="deepseek-prod",
            api_kind="deepseek",
            base_url="https://api.deepseek.com/v1",
            api_key="sk-test",
        )
    )
    await session.flush()

    row = (
        await session.execute(
            select(LLMProviderRow).where(LLMProviderRow.name == "deepseek-prod")
        )
    ).scalar_one()
    assert row.api_kind == "deepseek"
    assert row.base_url == "https://api.deepseek.com/v1"
    assert row.api_key == "sk-test"
    assert row.updated_at is not None


@pytest.mark.asyncio
async def test_provider_name_is_unique(session):
    session.add(LLMProviderRow(name="dup", api_kind="openai", base_url="http://a/v1"))
    await session.flush()
    session.add(LLMProviderRow(name="dup", api_kind="openai", base_url="http://b/v1"))
    with pytest.raises(Exception):
        await session.flush()


def test_seeded_provider_rows_match_the_purpose_seed_connection():
    """The provider a purpose is seeded against must carry the api_kind and
    base_url that purpose resolves to today, or every fresh install silently
    changes wire protocol."""
    from app.services import llm_seed

    by_name = {p.name: p for p in llm_seed.DEFAULT_PROVIDER_ROWS}
    for pc in llm_seed.DEFAULT_PURPOSE_CONFIGS:
        expected = "verification-judge" if pc.purpose == "verification" else "ollama-local"
        provider = by_name[expected]
        assert provider.api_kind == pc.api_kind, pc.purpose
        assert provider.base_url == pc.base_url, pc.purpose


@pytest.mark.asyncio
async def test_purpose_row_carries_a_provider_reference(session):
    from app.models.llm_config import LLMPurposeConfigRow

    session.add(LLMProviderRow(name="p1", api_kind="openai", base_url="http://a/v1"))
    await session.flush()
    session.add(
        LLMPurposeConfigRow(purpose="extraction", model="m", provider_name="p1")
    )
    await session.flush()

    row = (
        await session.execute(
            select(LLMPurposeConfigRow).where(LLMPurposeConfigRow.purpose == "extraction")
        )
    ).scalar_one()
    assert row.provider_name == "p1"


@pytest.mark.asyncio
async def test_purpose_provider_reference_must_resolve(session):
    from app.models.llm_config import LLMPurposeConfigRow

    session.add(
        LLMPurposeConfigRow(purpose="extraction", model="m", provider_name="ghost")
    )
    with pytest.raises(Exception):
        await session.flush()


@pytest.mark.asyncio
@pytest.mark.parametrize("column", ["api_kind", "base_url", "api_key"])
async def test_connection_columns_left_the_purpose_table(session, column):
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


@pytest.mark.asyncio
async def test_provider_reference_is_required(session):
    from app.models.llm_config import LLMPurposeConfigRow

    session.add(LLMPurposeConfigRow(purpose="extraction", model="m"))
    with pytest.raises(Exception):
        await session.flush()


@pytest.mark.asyncio
async def test_a_referenced_provider_cannot_be_deleted(session):
    from app.models.llm_config import LLMPurposeConfigRow

    session.add(LLMProviderRow(name="held", api_kind="openai", base_url="http://a/v1"))
    await session.flush()
    session.add(LLMPurposeConfigRow(purpose="extraction", model="m", provider_name="held"))
    await session.flush()

    with pytest.raises(Exception):
        await session.execute(text("DELETE FROM llm_providers WHERE name = 'held'"))


@pytest.mark.asyncio
async def test_renaming_a_provider_carries_to_its_purposes(session):
    from app.models.llm_config import LLMPurposeConfigRow

    session.add(LLMProviderRow(name="old", api_kind="openai", base_url="http://a/v1"))
    await session.flush()
    session.add(LLMPurposeConfigRow(purpose="extraction", model="m", provider_name="old"))
    await session.flush()

    await session.execute(text("UPDATE llm_providers SET name = 'new' WHERE name = 'old'"))
    moved = (
        await session.execute(
            text("SELECT provider_name FROM llm_purpose_configs WHERE purpose = 'extraction'")
        )
    ).scalar_one()
    assert moved == "new"
