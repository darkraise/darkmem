import pytest
from sqlalchemy import select

from app.api.routes.config import THEME_SETTINGS_KEY
from app.models.config import Config

VALID_SETTINGS = {
    "accentColor": "indigo",
    "surfaceColor": "slate",
    "preset": "default",
    "backgroundStyle": "solid",
    "backgroundIntensity": "balanced",
    "gradientPattern": "blobs",
    "mode": "dark",
    "density": "cozy",
    "elevation": "medium",
    "buttonElevation": "flat",
    "radius": "rounded",
    "fontSize": "medium",
    "surfaceIntensity": "balanced",
    "accentIntensity": "balanced",
    "outerGlow": "none",
    "innerGlow": "none",
    "presetAxisValues": {"glass": {"opacity": "medium", "blur": "low"}},
}

# The theme provider PUTs its whole settings object on every change, so an
# axis missing from ThemeSettingsPayload 422s every save while localStorage
# keeps the UI looking correct. Keep this in step with the switcher axes in
# frontend/src/theme.config.ts.
PROVIDER_AXES = frozenset(VALID_SETTINGS) - {"presetAxisValues"}


@pytest.mark.asyncio
async def test_get_theme_is_public_and_null_when_unset(client):
    resp = await client.get("/api/v1/config/theme")
    assert resp.status_code == 200
    assert resp.json() == {"settings": None}


@pytest.mark.asyncio
async def test_put_theme_requires_auth(client):
    resp = await client.put(
        "/api/v1/config/theme", json={"settings": VALID_SETTINGS}
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_put_then_get_roundtrips_camelcase_verbatim(client, auth_headers):
    resp = await client.put(
        "/api/v1/config/theme",
        headers=auth_headers,
        json={"settings": VALID_SETTINGS},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["settings"] == VALID_SETTINGS

    resp = await client.get("/api/v1/config/theme")
    assert resp.status_code == 200
    assert resp.json()["settings"] == VALID_SETTINGS


@pytest.mark.asyncio
async def test_put_theme_replaces_existing_row(client, auth_headers, session):
    first = await client.put(
        "/api/v1/config/theme",
        headers=auth_headers,
        json={"settings": VALID_SETTINGS},
    )
    assert first.status_code == 200

    updated = {**VALID_SETTINGS, "accentColor": "rose", "mode": "light"}
    second = await client.put(
        "/api/v1/config/theme",
        headers=auth_headers,
        json={"settings": updated},
    )
    assert second.status_code == 200

    rows = (
        await session.execute(
            select(Config).where(Config.key == THEME_SETTINGS_KEY)
        )
    ).scalars().all()
    assert len(rows) == 1
    assert rows[0].value["accentColor"] == "rose"


@pytest.mark.asyncio
async def test_put_theme_rejects_unknown_keys(client, auth_headers):
    resp = await client.put(
        "/api/v1/config/theme",
        headers=auth_headers,
        json={"settings": {**VALID_SETTINGS, "sneaky": "value"}},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_put_theme_rejects_malformed_values(client, auth_headers):
    for bad in ("ROSE", "a" * 33, "<script>", "", "9lives"):
        resp = await client.put(
            "/api/v1/config/theme",
            headers=auth_headers,
            json={"settings": {**VALID_SETTINGS, "accentColor": bad}},
        )
        assert resp.status_code == 422, f"accepted {bad!r}"


@pytest.mark.asyncio
async def test_put_theme_rejects_malformed_preset_axis_values(
    client, auth_headers
):
    resp = await client.put(
        "/api/v1/config/theme",
        headers=auth_headers,
        json={
            "settings": {
                **VALID_SETTINGS,
                "presetAxisValues": {"glass": {"opacity": "NOT VALID"}},
            }
        },
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_get_theme_tolerates_incompatible_stored_row(client, session):
    session.add(
        Config(key=THEME_SETTINGS_KEY, value={"accentColor": "ROSE!!"})
    )
    await session.flush()

    resp = await client.get("/api/v1/config/theme")
    assert resp.status_code == 200
    assert resp.json() == {"settings": None}


@pytest.mark.asyncio
async def test_put_theme_omits_null_optionals_from_stored_row(
    client, auth_headers, session
):
    minimal = {
        "accentColor": "indigo",
        "surfaceColor": "slate",
        "preset": "default",
        "backgroundStyle": "solid",
        "mode": "dark",
    }
    resp = await client.put(
        "/api/v1/config/theme",
        headers=auth_headers,
        json={"settings": minimal},
    )
    assert resp.status_code == 200, resp.text

    row = (
        await session.execute(
            select(Config).where(Config.key == THEME_SETTINGS_KEY)
        )
    ).scalar_one()
    assert row.value == minimal


@pytest.mark.asyncio
async def test_put_theme_accepts_every_axis_the_provider_sends(
    client, auth_headers
):
    resp = await client.put(
        "/api/v1/config/theme",
        headers=auth_headers,
        json={"settings": VALID_SETTINGS},
    )
    assert resp.status_code == 200, resp.text
    assert PROVIDER_AXES <= set(resp.json()["settings"])
