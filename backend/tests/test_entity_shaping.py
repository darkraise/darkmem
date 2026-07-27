"""Stage 1 of the extraction post-processor — entity shaping (T1.24b).

Doc 06 §4 S1 runs six non-mutating entity passes in a fixed order:
``_normalize_names``, ``_filter_noise`` / ``_filter_literals``,
``_snap_hardware_types`` / ``_apply_type_overrides``,
``_filter_hallucinated_names``, ``_filter_negation_only``,
``_dedup_entities``. Each pass is covered here in isolation; the ordered
sequence itself is pinned at the bottom of the file.
"""

import pytest

from app.services.extraction_clean import (
    _filter_noise,
    _normalize_names,
)


def _names(entities):
    return [e["name"] for e in entities]


def _types(entities):
    return {e["name"]: e["type"] for e in entities}


# ── _normalize_names ─────────────────────────────────────────────────


def test_normalize_names_drops_blank_and_whitespace_only_names():
    out = _normalize_names([
        {"name": "", "type": "tool"},
        {"name": "   ", "type": "tool"},
        {"name": "postgres", "type": "database"},
    ])
    assert _names(out) == ["postgres"]


def test_normalize_names_collapses_a_dotted_method_to_its_root():
    out = _normalize_names([
        {"name": "asyncio.create_task", "type": "tool"},
        {"name": "redis.asyncio.from_url", "type": "tool"},
    ])
    assert _names(out) == ["asyncio", "redis"]


def test_normalize_names_keeps_a_curated_dotted_name_intact():
    out = _normalize_names([{"name": "next.js", "type": "concept"}])
    assert _names(out) == ["next.js"]


def test_normalize_names_drops_names_under_three_chars():
    out = _normalize_names([{"name": "xy", "type": "tool"}])
    assert out == []


def test_normalize_names_keeps_allowlisted_short_tools():
    out = _normalize_names([
        {"name": "rg", "type": "tool"},
        {"name": "uv", "type": "tool"},
    ])
    assert _names(out) == ["rg", "uv"]


def test_normalize_names_strips_a_trailing_role_suffix():
    out = _normalize_names([{"name": "Redis cache store", "type": "database"}])
    assert _names(out) == ["Redis cache"]


def test_normalize_names_keeps_the_fuller_name_when_the_head_is_noise():
    # 'auth module' -> 'auth' would be deleted by _filter_noise, orphaning
    # every edge anchored to it, so the strip is declined.
    out = _normalize_names([{"name": "auth module", "type": "concept"}])
    assert _names(out) == ["auth module"]


def test_normalize_names_strips_an_infrastructure_descriptor():
    out = _normalize_names([
        {"name": "Postgres cluster", "type": "database"},
        {"name": "Proxmox host", "type": "tool"},
    ])
    assert _names(out) == ["Postgres", "Proxmox"]


def test_normalize_names_strips_a_leading_duration():
    out = _normalize_names([{"name": "30-minute outage", "type": "event"}])
    assert _names(out) == ["outage"]


def test_normalize_names_normalizes_the_type_through_the_closed_taxonomy():
    out = _normalize_names([
        {"name": "fastapi", "type": "framework"},
        {"name": "widget", "type": "not-a-real-type"},
    ])
    assert _types(out) == {"fastapi": "tool", "widget": "concept"}


def test_normalize_names_refines_a_library_named_project_to_tool():
    out = _normalize_names([{"name": "darkraise-ui", "type": "project"}])
    assert _types(out) == {"darkraise-ui": "tool"}


def test_normalize_names_does_not_mutate_its_input():
    given = [{"name": "asyncio.create_task", "type": "framework"}]
    _normalize_names(given)
    assert given == [{"name": "asyncio.create_task", "type": "framework"}]


@pytest.mark.parametrize("payload", [
    {"name": "postgres", "type": "database", "properties": {"display_name": "PostgreSQL"}},
])
def test_normalize_names_carries_unrelated_keys_forward(payload):
    out = _normalize_names([payload])
    assert out[0]["properties"] == {"display_name": "PostgreSQL"}


# ── _filter_noise ────────────────────────────────────────────────────


@pytest.mark.parametrize("name", [
    "value", "result", "config", "framework", "session", "codebase",
])
def test_filter_noise_drops_a_generic_noun(name):
    assert _filter_noise([{"name": name, "type": "concept"}]) == []


@pytest.mark.parametrize("name", [
    "pipeline.py", "backend/app/main.py", "docker-compose.yml",
    "requirements.lock.txt", "schema.sql",
])
def test_filter_noise_drops_a_filename(name):
    assert _filter_noise([{"name": name, "type": "artifact"}]) == []


@pytest.mark.parametrize("name", [
    "/api/v1/memories",
    "/mcp",
    "/api/v1/jobs/repo_sync/config?dry_run=true",
    "https://example.com/guide",
    "http://api.internal:8080/hooks",
    "http://localhost:8000/api",
    "postgresql+asyncpg://darkmem@localhost:5433/darkmem",
])
def test_filter_noise_drops_a_url(name):
    assert _filter_noise([{"name": name, "type": "artifact"}]) == []


def test_filter_noise_keeps_a_scheme_word_that_is_not_a_url():
    # 'https' alone is a protocol entity; only the '://' form is a URL.
    out = _filter_noise([{"name": "https", "type": "protocol"}])
    assert _names(out) == ["https"]


@pytest.mark.parametrize("name", [
    "DATABASE_URL", "MCP_ALLOWED_HOSTS", "JWT_SECRET", "DB_PASSWORD",
])
def test_filter_noise_drops_an_env_var(name):
    assert _filter_noise([{"name": name, "type": "concept"}]) == []


@pytest.mark.parametrize("name", [
    "2026-05-12", "2026/4/23", "2026-04", "2026", "23/04/2026",
    "v2.0", "1.2.3", "2.0.0-beta", "30s", "512MB", "30%", "1,000.5",
])
def test_filter_noise_drops_a_value_literal(name):
    assert _filter_noise([{"name": name, "type": "concept"}]) == []


@pytest.mark.parametrize("name", ["@darkraise/ui", "$HOME"])
def test_filter_noise_drops_a_sigil_prefixed_name(name):
    assert _filter_noise([{"name": name, "type": "tool"}]) == []


def test_filter_noise_drops_a_phrase_opening_with_an_article():
    out = _filter_noise([
        {"name": "the pipeline", "type": "concept"},
        {"name": "this outage", "type": "event"},
        {"name": "hybrid search", "type": "concept"},
    ])
    assert _names(out) == ["hybrid search"]


def test_filter_noise_keeps_real_entities():
    given = [
        {"name": "postgres", "type": "database"},
        {"name": "pgvector", "type": "tool"},
        {"name": "february outage", "type": "event"},
    ]
    assert _names(_filter_noise(given)) == ["postgres", "pgvector", "february outage"]


def test_filter_noise_drops_the_host_stem_left_by_a_collapsed_hostname():
    out = _filter_noise(_normalize_names([{"name": "www.example.com", "type": "artifact"}]))
    assert out == []


def test_filter_noise_does_not_mutate_its_input():
    given = [{"name": "value", "type": "concept"}, {"name": "postgres", "type": "database"}]
    _filter_noise(given)
    assert len(given) == 2
