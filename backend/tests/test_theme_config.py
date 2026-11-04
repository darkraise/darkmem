import pytest
from sqlalchemy import select

from app.api.routes.config import THEME_SETTINGS_KEY
from app.models.config import Config

VALID_SETTINGS = {
    "version": 7,
    "mode": "dark",
    "accentColor": "indigo",
    "surfaceColor": "slate",
    "tintWithAccent": "on",
    "signalColor": "none",
    "style": "glass",
    "preset": "mica-desk",
    "backgroundStyle": "solid",
    "backgroundIntensity": "balanced",
    "gradientPattern": "blobs",
    "glassTransparency": "medium",
    "glassBlur": "low",
    "font": "inter",
    "headingFont": "body",
    "density": "cozy",
    "elevation": "standard",
    "radius": "rounded",
    "fontSize": "medium",
    "contrast": "low",
    "darkAccentChroma": "vivid",
    "outerGlow": "none",
    "innerGlow": "none",
    "sidebarSelection": "auto",
}

# darkraise-ui 7's axis registry. An axis missing from ThemeSettingsPayload
# 422s every save that carries it while localStorage keeps the UI looking
# correct. Keep this in step with the axes in frontend/src/theme.config.ts.
PROVIDER_AXES = frozenset(VALID_SETTINGS) - {"version"}

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
async def test_get_theme_serves_a_darkraise_ui_6_row(client, session):
    # Saved before the 7 upgrade: its removed axes are dropped and the rest
    # served, unversioned, so the provider migrates it and saves it back.
    session.add(
        Config(
            key=THEME_SETTINGS_KEY,
            value={
                "accentColor": "rose",
                "surfaceColor": "slate",
                "preset": "default",
                "backgroundStyle": "solid",
                "mode": "light",
                "buttonElevation": "flat",
                "surfaceIntensity": "flat",
                "accentIntensity": "vivid",
                "controlDepth": "recessed",
                "presetAxisValues": {"glass": {"opacity": "medium"}},
            },
        )
    )
    await session.flush()

    resp = await client.get("/api/v1/config/theme")
    assert resp.status_code == 200
    assert resp.json()["settings"] == {
        "accentColor": "rose",
        "surfaceColor": "slate",
        "preset": "default",
        "backgroundStyle": "solid",
        "mode": "light",
    }


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
    minimal = {"version": 7, "accentColor": "indigo"}
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
