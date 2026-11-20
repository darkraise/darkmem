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
        provider = by_name[llm_seed.default_provider_row_name_for_purpose(pc.purpose)]
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


@pytest.mark.asyncio
async def test_provider_crud_round_trip(client, auth_headers):
    created = await client.post(
        "/api/v1/config/llm-providers",
        json={"name": "ds", "api_kind": "deepseek",
              "base_url": "https://api.deepseek.com/v1", "api_key": "sk-secret"},
        headers=auth_headers,
    )
    assert created.status_code == 201

    listed = await client.get("/api/v1/config/llm-providers", headers=auth_headers)
    assert listed.status_code == 200
    row = next(p for p in listed.json()["providers"] if p["name"] == "ds")
    assert row["api_key"] == "***"
    assert row["used_by"] == []
    assert row["serves_verification"] is False

    dup = await client.post(
        "/api/v1/config/llm-providers",
        json={"name": "ds", "api_kind": "openai", "base_url": "http://x/v1"},
        headers=auth_headers,
    )
    assert dup.status_code == 409

    deleted = await client.delete("/api/v1/config/llm-providers/ds", headers=auth_headers)
    assert deleted.status_code == 204


@pytest.mark.asyncio
@pytest.mark.parametrize("body, field, message", [
    ({"name": "bad", "base_url": "not a url"}, "base_url",
     "Enter an http:// or https:// address with a host"),
    ({"name": "bad", "base_url": "ftp://x/v1"}, "base_url",
     "Enter an http:// or https:// address with a host"),
    ({"name": "bad", "base_url": "http://"}, "base_url",
     "Enter an http:// or https:// address with a host"),
    # A "/" in the name made a row no `/llm-providers/{name}` route could
    # reach again: it could be created, never edited or deleted.
    ({"name": "a/b", "base_url": "http://x/v1"}, "name",
     "Use only letters, digits, dot, dash and underscore"),
    ({"name": "..", "base_url": "http://x/v1"}, "name",
     "Use only letters, digits, dot, dash and underscore"),
])
async def test_create_refuses_unusable_connection_fields(
    client, auth_headers, body, field, message,
):
    response = await client.post(
        "/api/v1/config/llm-providers",
        json={"api_kind": "openai", **body},
        headers=auth_headers,
    )
    assert response.status_code == 422
    assert response.json()["detail"].startswith(f"{field}: {message}")


@pytest.mark.asyncio
async def test_a_stored_row_with_a_bad_url_still_loads_and_can_be_fixed(
    client, auth_headers, session,
):
    """The check guards writes only: a row stored before it lists as it is,
    and saving it asks for a usable address."""
    await session.execute(text(
        "INSERT INTO llm_providers (name, api_kind, base_url) "
        "VALUES ('legacy','openai','not a url')"
    ))
    await session.commit()

    listed = await client.get("/api/v1/config/llm-providers", headers=auth_headers)
    assert listed.status_code == 200
    row = next(p for p in listed.json()["providers"] if p["name"] == "legacy")
    assert row["base_url"] == "not a url"

    kept = await client.put(
        "/api/v1/config/llm-providers/legacy",
        json={"api_kind": "openai", "base_url": "not a url"},
        headers=auth_headers,
    )
    assert kept.status_code == 422
    fixed = await client.put(
        "/api/v1/config/llm-providers/legacy",
        json={"api_kind": "openai", "base_url": "http://fixed/v1"},
        headers=auth_headers,
    )
    assert fixed.status_code == 200
    assert fixed.json()["base_url"] == "http://fixed/v1"


@pytest.mark.asyncio
async def test_masked_key_sentinel_does_not_rotate(client, auth_headers, session):
    await client.post(
        "/api/v1/config/llm-providers",
        json={"name": "k", "api_kind": "openai", "base_url": "http://x/v1", "api_key": "real"},
        headers=auth_headers,
    )
    await client.put(
        "/api/v1/config/llm-providers/k",
        json={"api_kind": "openai", "base_url": "http://x/v1", "api_key": "***"},
        headers=auth_headers,
    )
    stored = (await session.execute(
        text("SELECT api_key, base_url FROM llm_providers WHERE name = 'k'")
    )).one()
    assert stored[0] == "real"
    assert stored[1] == "http://x/v1"


@pytest.mark.asyncio
async def test_put_explicit_null_clears_the_key(client, auth_headers, session):
    await client.post(
        "/api/v1/config/llm-providers",
        json={"name": "clr", "api_kind": "openai", "base_url": "http://x/v1", "api_key": "real"},
        headers=auth_headers,
    )
    await client.put(
        "/api/v1/config/llm-providers/clr",
        json={"api_kind": "openai", "base_url": "http://x/v1", "api_key": None},
        headers=auth_headers,
    )
    stored = (await session.execute(
        text("SELECT api_key FROM llm_providers WHERE name = 'clr'")
    )).scalar_one()
    assert stored is None


@pytest.mark.asyncio
async def test_delete_is_blocked_while_referenced(client, auth_headers, session):
    from app.models.llm_config import LLMPurposeConfigRow

    await client.post(
        "/api/v1/config/llm-providers",
        json={"name": "held", "api_kind": "openai", "base_url": "http://x/v1"},
        headers=auth_headers,
    )
    session.add(LLMPurposeConfigRow(purpose="extraction", model="m", provider_name="held"))
    await session.commit()

    blocked = await client.delete("/api/v1/config/llm-providers/held", headers=auth_headers)
    assert blocked.status_code == 409
    assert "extraction" in blocked.json()["detail"]


@pytest.mark.asyncio
async def test_provider_edit_swaps_the_live_orchestrator(client, auth_headers):
    # No ``app`` fixture exists (conftest provides session/client/auth_headers
    # only), and the client fixture never sets ``app.state.llm`` — a bare
    # ``before = app.state.llm`` would raise AttributeError before the test
    # proves anything, so a sentinel stands in for "no orchestrator yet".
    from app.main import app

    await client.post(
        "/api/v1/config/llm-providers",
        json={"name": "sw", "api_kind": "openai", "base_url": "http://before/v1"},
        headers=auth_headers,
    )
    sentinel = object()
    app.state.llm = sentinel
    try:
        await client.put(
            "/api/v1/config/llm-providers/sw",
            json={"api_kind": "openai", "base_url": "http://after/v1", "api_key": "***"},
            headers=auth_headers,
        )
        assert app.state.llm is not sentinel
        assert app.state.llm.config["extraction"].base_url is not None
    finally:
        # ``app.state.llm`` is process-global across the test session; leaving
        # the sentinel (or this test's orchestrator) in place would fail
        # unrelated tests later in the run.
        app.state.llm = None


@pytest.mark.asyncio
async def test_flipping_to_a_no_embeddings_vendor_names_the_purpose(
    client, auth_headers, session
):
    from app.models.llm_config import LLMPurposeConfigRow

    await client.post(
        "/api/v1/config/llm-providers",
        json={"name": "emb", "api_kind": "openai", "base_url": "http://x/v1"},
        headers=auth_headers,
    )
    session.add(LLMPurposeConfigRow(purpose="embedding", model="e", provider_name="emb"))
    await session.commit()

    resp = await client.put(
        "/api/v1/config/llm-providers/emb",
        json={"api_kind": "deepseek", "base_url": "https://api.deepseek.com/v1"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["no_embedding_purposes"] == ["embedding"]


# ── the judge provider's frozen identity fields ──────────────────────────


async def _point_verification_at(session, name: str):
    from app.models.llm_config import LLMPurposeConfigRow
    from app.services.config import VERIFICATION_PURPOSE

    session.add(LLMProviderRow(
        name=name, api_kind="openai", base_url="https://api.openai.com/v1",
    ))
    await session.flush()
    session.add(LLMPurposeConfigRow(
        purpose=VERIFICATION_PURPOSE, model="gpt-5.5", provider_name=name,
    ))
    await session.commit()


@pytest.mark.asyncio
async def test_identity_fields_are_frozen_on_the_judge_provider(
    client, auth_headers, session
):
    await _point_verification_at(session, "judge")
    for field, value in (("base_url", "http://elsewhere/v1"), ("api_kind", "deepseek")):
        payload = {
            "api_kind": "openai",
            "base_url": "https://api.openai.com/v1",
            field: value,
        }
        resp = await client.put(
            "/api/v1/config/llm-providers/judge", json=payload, headers=auth_headers
        )
        assert resp.status_code == 409, field
        assert "verification" in resp.json()["detail"]

    stored = (await session.execute(
        text("SELECT api_kind, base_url FROM llm_providers WHERE name = 'judge'")
    )).one()
    assert stored == ("openai", "https://api.openai.com/v1")


@pytest.mark.asyncio
async def test_the_judge_key_still_rotates(client, auth_headers, session):
    """api_key is not an identity field — rotating a credential is not a model
    swap — and the owner ruling of 2026-08-20 requires this key to be
    rotatable without a direct database write."""
    await _point_verification_at(session, "judge2")
    resp = await client.put(
        "/api/v1/config/llm-providers/judge2",
        json={
            "api_kind": "openai",
            "base_url": "https://api.openai.com/v1",
            "api_key": "sk-rotated",
        },
        headers=auth_headers,
    )
    assert resp.status_code == 200
    stored = (await session.execute(
        text("SELECT api_key FROM llm_providers WHERE name = 'judge2'")
    )).scalar_one()
    assert stored == "sk-rotated"


@pytest.mark.asyncio
async def test_a_provider_serving_no_judge_is_not_frozen(client, auth_headers, session):
    """The freeze is scoped to the provider the judge purpose points at, not
    to every provider that happens to look like a judge connection."""
    await _point_verification_at(session, "judge-real")
    await client.post(
        "/api/v1/config/llm-providers",
        json={"name": "free", "api_kind": "openai", "base_url": "http://x/v1"},
        headers=auth_headers,
    )
    resp = await client.put(
        "/api/v1/config/llm-providers/free",
        json={"api_kind": "deepseek", "base_url": "http://moved/v1"},
        headers=auth_headers,
    )
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_resending_the_judge_connection_unchanged_is_not_a_change(
    client, auth_headers, session
):
    """The form is a full replace, so an unrelated edit resends both frozen
    fields; refusing that would make the row uneditable rather than frozen."""
    await _point_verification_at(session, "judge-noop")
    resp = await client.put(
        "/api/v1/config/llm-providers/judge-noop",
        json={
            "api_kind": "openai",
            "base_url": "https://api.openai.com/v1",
            "api_key": "***",
        },
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["serves_verification"] is True


@pytest.mark.asyncio
async def test_the_settings_panel_body_rotates_a_frozen_key(
    client, auth_headers, session
):
    """Pin the wire contract on the side that defines it.

    The providers panel is the only caller of this route, and its own tests
    mock the fetch layer, so nothing on that side can prove the body it builds
    is one this route accepts. A body that omits the two unchanged connection
    fields is a 422 — which is every realistic edit, including the judge key
    rotation the freeze exists to keep possible — so the panel must send all
    three, resending the frozen pair verbatim.
    """
    await _point_verification_at(session, "judge-panel")

    patch_shaped = await client.put(
        "/api/v1/config/llm-providers/judge-panel",
        json={"api_key": "sk-not-sent-this-way"},
        headers=auth_headers,
    )
    assert patch_shaped.status_code == 422
    assert {
        entry["loc"][-1] for entry in patch_shaped.json()["error"]["details"]
    } == {"api_kind", "base_url"}

    full_replace = await client.put(
        "/api/v1/config/llm-providers/judge-panel",
        json={
            "api_kind": "openai",
            "base_url": "https://api.openai.com/v1",
            "api_key": "sk-rotated-from-the-panel",
        },
        headers=auth_headers,
    )
    assert full_replace.status_code == 200, full_replace.text
    assert full_replace.json()["serves_verification"] is True
    stored = (await session.execute(
        text("SELECT api_key FROM llm_providers WHERE name = 'judge-panel'")
    )).scalar_one()
    assert stored == "sk-rotated-from-the-panel"


@pytest.mark.asyncio
async def test_no_other_purpose_may_join_the_judge_provider(
    client, auth_headers, session
):
    await _point_verification_at(session, "judge3")
    resp = await client.post(
        "/api/v1/config/llm",
        json={"extraction": {"provider_name": "judge3", "model": "m"}},
        headers=auth_headers,
    )
    assert resp.status_code == 409
    assert "judge3" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_a_shared_judge_provider_is_reported_not_deadlocked(
    client, auth_headers, session
):
    """A direct-SQL restore can produce sharing the API would refuse. The
    remedy must stay reachable: repoint the *other* purpose off it."""
    from app.models.llm_config import LLMPurposeConfigRow

    await _point_verification_at(session, "shared")
    session.add(LLMPurposeConfigRow(
        purpose="extraction", model="m", provider_name="shared",
    ))
    await session.commit()

    listed = await client.get("/api/v1/config/llm-providers", headers=auth_headers)
    row = next(p for p in listed.json()["providers"] if p["name"] == "shared")
    assert row["serves_verification"] is True
    assert set(row["used_by"]) == {"verification", "extraction"}

    await session.execute(text(
        "INSERT INTO llm_providers (name, api_kind, base_url) "
        "VALUES ('other','openai','http://o/v1')"
    ))
    await session.commit()
    freed = await client.post(
        "/api/v1/config/llm",
        json={"extraction": {"provider_name": "other"}},
        headers=auth_headers,
    )
    assert freed.status_code == 200


@pytest.mark.asyncio
async def test_a_shared_purpose_may_still_be_edited_in_place(
    client, auth_headers, session
):
    """In the restore-produced shared state the other purpose keeps sharing
    until someone moves it; a save that leaves the reference alone adds no
    new sharing and must not be refused."""
    from app.models.llm_config import LLMPurposeConfigRow

    await _point_verification_at(session, "shared2")
    session.add(LLMPurposeConfigRow(
        purpose="extraction", model="m", provider_name="shared2",
    ))
    await session.commit()

    resp = await client.post(
        "/api/v1/config/llm",
        json={"extraction": {"provider_name": "shared2", "model": "m2"}},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    model = (await session.execute(text(
        "SELECT model FROM llm_purpose_configs WHERE purpose = 'extraction'"
    ))).scalar_one()
    assert model == "m2"
