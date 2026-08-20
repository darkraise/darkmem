"""Purpose resolution is ONE query, and `api_kind` is the only vendor field.

Doc 04 §7 and doc 11 §2 flattened the LLM config so that resolution was a
single un-joined read of `llm_purpose_configs`; the `llm_providers` /
`llm_profiles` / `ml_profiles` indirection cost three levels of resolution on
every call and was gone at the baseline. The 2026-08-20 owner ruling reverses
exactly one level of that: `llm_providers` is back, a purpose row references
one by name, and connection details resolve across a single inner join.
`llm_profiles` and `ml_profiles` stay gone, and one join is still one query.

The one-query property is the kind that decays silently — a later change that
resolves a reference per purpose still returns correct config, just six times
slower per call, and no functional test would notice. So it is asserted by
counting queries rather than by inspecting the result (T1.01).
"""
from __future__ import annotations

import pytest
from sqlalchemy import event, select, text

from app.models.llm_config import LLMPurposeConfigRow
from app.models.llm_provider import LLMProviderRow
from app.schemas.config import (
    LLMConfigUpdate,
    LLMPurposeConfigSchema,
    LLMPurposeConfigUpdate,
)
from app.services.config import PURPOSES, cfg_to_schema, get_llm_config
from tests.response_coverage import undeclared_keys


class _QueryCounter:
    """Counts SQL statements issued on one session's connection."""

    def __init__(self) -> None:
        self.statements: list[str] = []

    def __call__(self, conn, cursor, statement, parameters, context, executemany):
        self.statements.append(statement)

    @property
    def selects(self) -> list[str]:
        # `WITH` counts too: a reintroduced hierarchical resolution is most
        # naturally written as a CTE, and matching only SELECT would let exactly
        # the regression this test exists to catch walk straight past it.
        return [
            s
            for s in self.statements
            if s.lstrip().upper().startswith(("SELECT", "WITH"))
        ]


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

    await session.execute(
        text(
            "INSERT INTO llm_providers (name, api_kind, base_url) "
            "VALUES ('scale', 'openai', 'http://example.invalid/v1')"
        )
    )
    for purpose in PURPOSES:
        await session.execute(
            text(
                "INSERT INTO llm_purpose_configs (purpose, model, provider_name) "
                "VALUES (:p, 'a-model', 'scale')"
            ),
            {"p": purpose},
        )
    await session.flush()

    _, populated = await _count_resolution_queries(session)
    assert len(empty.selects) == len(populated.selects) == 1


@pytest.mark.asyncio
async def test_resolution_reads_connection_from_the_provider(session):
    session.add(LLMProviderRow(
        name="ds", api_kind="deepseek",
        base_url="https://api.deepseek.com/v1", api_key="sk-x",
    ))
    await session.flush()
    session.add(LLMPurposeConfigRow(
        purpose="extraction", model="deepseek-v4-flash", provider_name="ds",
    ))
    await session.flush()

    cfg = (await get_llm_config(session))["extraction"]
    assert cfg.model == "deepseek-v4-flash"
    assert cfg.api_kind == "deepseek"
    assert cfg.base_url == "https://api.deepseek.com/v1"
    assert cfg.api_key == "sk-x"


@pytest.mark.asyncio
async def test_resolution_is_one_query_with_one_join(session):
    _, counter = await _count_resolution_queries(session)
    sql = counter.selects[0].upper()
    assert sql.count("JOIN") == 1
    # An outer join contains "JOIN" once too, and would resolve a
    # provider-less purpose row to empty connection fields instead of letting
    # it fall back to the Settings default.
    assert "OUTER" not in sql
    assert "LLM_PROVIDERS" in sql
    assert "LLM_PROFILES" not in sql
    assert "ML_PROFILES" not in sql


# ── The indirection tables are gone, not merely unused ──────────────


@pytest.mark.asyncio
@pytest.mark.parametrize("table", ["llm_profiles", "ml_profiles"])
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
                "WHERE table_name = 'llm_providers' AND column_name = 'api_kind'"
            )
        )
    ).scalar_one()
    assert present == 1


@pytest.mark.asyncio
async def test_resolved_config_carries_the_provider_connection_details(session):
    await session.execute(
        text(
            "INSERT INTO llm_providers (name, api_kind, base_url, api_key) "
            "VALUES ('vendor', 'deepseek', "
            "'https://api.example.invalid/v1', 'sk-test')"
        )
    )
    await session.execute(
        text(
            "INSERT INTO llm_purpose_configs "
            "(purpose, model, provider_name, params) "
            "VALUES ('extraction', 'a-model', 'vendor', "
            "'{\"temperature\": 0}'::jsonb)"
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


# ───────────────── the undeclared-field guard (T2.104) ─────────────────


@pytest.mark.asyncio
async def test_config_llm_route_serves_every_purpose_it_resolves(
    client, auth_headers, session
):
    """`get_llm_config` resolves all eight `PURPOSES` and `GET /config/llm`
    always builds a payload keyed on all eight of them, but
    `LLMConfigResponse` used to declare six — dropping `synthesis` and
    `verification` exactly like `facts_read`'s fields, one directory over.
    Diffs the resolved purpose set against the served JSON instead of
    hand-listing eight names, so a ninth purpose added later is covered
    without a new assertion.
    """
    config = await get_llm_config(session)
    built = {
        purpose: cfg_to_schema(cfg).model_dump() for purpose, cfg in config.items()
    }

    response = await client.get("/api/v1/config/llm", headers=auth_headers)
    served = response.json()

    missing = undeclared_keys(built, served)
    assert not missing, f"LLMConfigResponse dropped: {missing}"
    assert set(PURPOSES) <= set(served)


@pytest.mark.asyncio
async def test_config_llm_serves_the_provider_each_purpose_resolves_through(
    client, auth_headers, session
):
    """The connection fields are joined from a provider row, so the settings
    surface needs the row's name to render which provider serves a purpose and
    to keep a saved change visible across the refetch that follows it. Served
    nowhere else: without this field the picker renders empty and every save
    reads back as a revert."""
    session.add(LLMProviderRow(
        name="reranker-vendor", api_kind="openai",
        base_url="https://api.example.invalid/v1",
    ))
    session.add(LLMProviderRow(
        name="reranker-successor", api_kind="openai",
        base_url="https://successor.example.invalid/v1",
    ))
    await session.flush()
    session.add(LLMPurposeConfigRow(
        purpose="reranker", model="a-model", provider_name="reranker-vendor",
    ))
    await session.flush()

    served = await client.get("/api/v1/config/llm", headers=auth_headers)
    assert served.json()["reranker"]["provider_name"] == "reranker-vendor"

    written = await client.post(
        "/api/v1/config/llm",
        headers=auth_headers,
        json={"reranker": {"provider_name": "reranker-successor"}},
    )
    assert written.status_code == 200
    assert written.json()["reranker"]["provider_name"] == "reranker-successor"

    refetched = await client.get("/api/v1/config/llm", headers=auth_headers)
    assert refetched.json()["reranker"]["provider_name"] == "reranker-successor"


# ───────── the write-side asymmetry, decided per purpose (T2.106) ─────────


def test_llm_config_update_declares_synthesis_but_not_verification():
    """The read side (`LLMConfigResponse`) declares all eight purposes; the
    write side deliberately does not mirror that. `synthesis` is seeded
    inert (no consumer until T3.02) so widening its write is cheap.
    `verification` is live (`VerificationJudge`, T2.26) and its qualification
    record is G-D's gate evidence — repointing it through this route is a
    real capability whose write-time guard would mean touching the
    verification ladder, which is out of this task's scope. The asymmetry
    is asserted directly on the schema so a future edit that reintroduces
    (or accidentally removes) either field fails loudly here rather than
    being noticed only via a route-level probe."""
    fields = set(LLMConfigUpdate.model_fields)
    assert fields == {
        "embedding", "extraction", "classification", "reasoning",
        "summarization", "reranker", "synthesis",
    }
    assert "verification" not in fields


@pytest.mark.asyncio
async def test_post_config_llm_writes_synthesis(client, auth_headers, session):
    """`synthesis` is now writable end to end: the row is created/updated
    and the change is visible both in the response and in the underlying
    table, exactly like the six always-writable purposes."""
    # The row has to exist with a provider before the POST: resolution inner
    # joins `llm_providers`, and a provider-less row resolves to the Settings
    # default instead of what was just written.
    session.add(LLMProviderRow(
        name="synthesis-vendor", api_kind="openai",
        base_url="https://synthesis-vendor.invalid/v1",
    ))
    await session.flush()
    session.add(LLMPurposeConfigRow(
        purpose="synthesis", model="", provider_name="synthesis-vendor",
    ))
    await session.flush()

    resp = await client.post(
        "/api/v1/config/llm",
        headers=auth_headers,
        json={
            "synthesis": {
                "provider_name": "synthesis-vendor",
                "model": "synthesis-test-model",
            }
        },
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["synthesis"]["model"] == "synthesis-test-model"
    # Served from the provider, which is the only place the connection lives.
    assert resp.json()["synthesis"]["base_url"] == "https://synthesis-vendor.invalid/v1"

    row = (await session.execute(
        select(LLMPurposeConfigRow).where(LLMPurposeConfigRow.purpose == "synthesis")
    )).scalar_one()
    assert row.model == "synthesis-test-model"


@pytest.mark.asyncio
async def test_post_config_llm_ignores_verification_write(client, auth_headers, session):
    """A `verification` key on the POST body is not a declared field on
    `LLMConfigUpdate`, so pydantic's default `extra="ignore"` drops it
    before the route ever sees it — no row is created or changed, and the
    served config for `verification` is untouched. This is the deliberate
    read-only ruling, proven rather than merely stated in a comment: an
    operator's settings form cannot repoint the qualified judge's model
    through this door, silently or otherwise."""
    resp = await client.post(
        "/api/v1/config/llm",
        headers=auth_headers,
        json={
            "verification": {
                "base_url": "https://repointed.invalid/v1",
                "model": "a-different-judge-model",
                "api_kind": "openai",
            }
        },
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["verification"]["model"] != "a-different-judge-model"

    row = (await session.execute(
        select(LLMPurposeConfigRow).where(LLMPurposeConfigRow.purpose == "verification")
    )).scalar_one_or_none()
    assert row is None or row.model != "a-different-judge-model"


# ───────── classifier_kind reaches the door, not just the column ─────────


@pytest.mark.asyncio
async def test_config_llm_serves_classifier_kind_on_the_classification_purpose(
    client, auth_headers
):
    """The column exists and `resolve_classifier` reads it, but the response
    schema never declared it, so the settings UI had no value to render and
    fell back to "llm" forever. `test_classifier_kind.py` missed this by
    setting the column directly, never through the route."""
    response = await client.get("/api/v1/config/llm", headers=auth_headers)
    assert response.status_code == 200
    assert "classifier_kind" in response.json()["classification"]


@pytest.mark.asyncio
async def test_config_llm_persists_a_classifier_kind_write(
    client, auth_headers, session
):
    """`config.py`'s write loop already listed the field, but
    `LLMPurposeConfigUpdate` did not declare it, so it could never appear in
    `model_fields_set` and that loop entry was dead. The POST returned 200 and
    wrote nothing."""
    # The row has to exist with a provider before the POST: resolution inner
    # joins `llm_providers`, and a provider-less row resolves to the Settings
    # default instead of what was just written.
    session.add(LLMProviderRow(
        name="classification-vendor", api_kind="openai",
        base_url="https://api.example.invalid/v1",
    ))
    await session.flush()
    session.add(LLMPurposeConfigRow(
        purpose="classification", model="a-model",
        provider_name="classification-vendor",
    ))
    await session.flush()

    response = await client.post(
        "/api/v1/config/llm",
        headers=auth_headers,
        json={"classification": {"classifier_kind": "local"}},
    )
    assert response.status_code == 200
    assert response.json()["classification"]["classifier_kind"] == "local"

    fresh = await client.get("/api/v1/config/llm", headers=auth_headers)
    assert fresh.json()["classification"]["classifier_kind"] == "local"


@pytest.mark.asyncio
async def test_config_llm_rejects_an_unknown_classifier_kind(client, auth_headers):
    """Two values only. A free-form string would reach `resolve_classifier`,
    which treats anything that is not "local" as the LLM — a silent misread
    rather than a refusal."""
    response = await client.post(
        "/api/v1/config/llm",
        headers=auth_headers,
        json={"classification": {"classifier_kind": "regex"}},
    )
    assert response.status_code == 422


# ───────── the write side names a provider, it never carries one ─────────


@pytest.mark.asyncio
async def test_purpose_write_takes_a_provider_name(client, auth_headers, session):
    """A purpose write points at a provider and the response resolves the
    connection across the join. The POSTed body carries no base URL at all,
    so the served one can only have come from the referenced row."""
    session.add(LLMProviderRow(
        name="p2", api_kind="openai", base_url="http://b/v1",
    ))
    await session.flush()

    resp = await client.post(
        "/api/v1/config/llm",
        json={"extraction": {"provider_name": "p2", "model": "m2"}},
        headers=auth_headers,
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["extraction"]["base_url"] == "http://b/v1"
    assert resp.json()["extraction"]["model"] == "m2"

    row = (await session.execute(
        select(LLMPurposeConfigRow).where(LLMPurposeConfigRow.purpose == "extraction")
    )).scalar_one()
    assert row.provider_name == "p2"


@pytest.mark.asyncio
async def test_unknown_provider_is_a_422(client, auth_headers):
    """The FK would refuse this anyway, but as an IntegrityError the caller
    sees a 500 naming a constraint. A name that resolves to nothing is a
    client error and answers as one."""
    resp = await client.post(
        "/api/v1/config/llm",
        json={"extraction": {"provider_name": "ghost", "model": "m"}},
        headers=auth_headers,
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_creating_a_rowless_purpose_requires_a_provider(client, auth_headers):
    """`provider_name` is NOT NULL, so the route cannot invent a row from a
    model alone. Refusing here keeps that a 422 rather than the 500 the
    not-null violation would produce."""
    resp = await client.post(
        "/api/v1/config/llm",
        json={"reranker": {"model": "only-a-model"}},
        headers=auth_headers,
    )
    assert resp.status_code == 422
    assert "provider_name" in resp.text


@pytest.mark.asyncio
async def test_connection_fields_are_not_writable_on_a_purpose(
    client, auth_headers, session
):
    """A POSTed `base_url` / `api_kind` / `api_key` used to be written onto the
    purpose row, where resolution no longer reads it and where the column no
    longer exists — so an operator rotating a key got a 200 and no change.
    They are not declared on the update schema at all now, which makes the
    write unrepresentable rather than merely ineffective."""
    assert not set(LLMPurposeConfigUpdate.model_fields) & {
        "base_url", "api_kind", "api_key",
    }

    session.add(LLMProviderRow(
        name="inert-vendor", api_kind="openai",
        base_url="http://provider-side.invalid/v1", api_key="provider-key",
    ))
    await session.flush()
    session.add(LLMPurposeConfigRow(
        purpose="reranker", model="a-model", provider_name="inert-vendor",
    ))
    await session.flush()

    resp = await client.post(
        "/api/v1/config/llm",
        headers=auth_headers,
        json={
            "reranker": {
                "base_url": "http://posted-side.invalid/v1",
                "api_kind": "ollama",
                "api_key": "posted-key",
                "model": "another-model",
            }
        },
    )
    assert resp.status_code == 200, resp.text
    served = resp.json()["reranker"]
    assert served["model"] == "another-model"
    assert served["base_url"] == "http://provider-side.invalid/v1"
    assert served["api_kind"] == "openai"


def test_llm_purpose_schemas_carry_no_dropped_indirection_fields():
    """provider_ref / profile_ref / ml_profile_ref were dropped at the
    baseline (doc 04 section 7) and stayed on the wire as inert nulls. Serving
    a field no table has invites a client to write it and believe it took."""
    for schema in (LLMPurposeConfigSchema, LLMPurposeConfigUpdate):
        declared = set(schema.model_fields)
        assert not declared & {"provider_ref", "profile_ref", "ml_profile_ref"}
