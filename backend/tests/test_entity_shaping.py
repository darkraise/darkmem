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
    ENTITY_TYPES,
    PASS_REGISTRY,
    CleanState,
    _TYPE_OVERRIDES,
    _apply_type_overrides,
    _dedup_entities,
    _filter_hallucinated_names,
    _filter_literals,
    _filter_negation_only,
    _filter_noise,
    _normalize_names,
    _snap_hardware_types,
    run_passes,
)
from app.services.extraction_pass_harness import index_of


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
    "value", "result", "config", "framework", "session", "codebase", "source",
])
def test_filter_noise_drops_a_generic_noun(name):
    assert _filter_noise([{"name": name, "type": "concept"}]) == []


def test_filter_noise_drops_the_stem_a_stripped_connector_leaves_behind():
    out = _filter_noise(_normalize_names([
        {"name": "Kafka source connector", "type": "service"},
        {"name": "source connector", "type": "concept"},
    ]))
    assert _names(out) == ["Kafka"]


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


# ── _filter_literals ─────────────────────────────────────────────────


@pytest.mark.parametrize("name", ["192.168.0.195", "192.168.0.195:8000", "127.0.0.1:5433"])
def test_filter_literals_drops_an_ip_or_ip_port(name):
    content = f"the api answers on {name} over the lan"
    assert _filter_literals([{"name": name, "type": "concept"}], content) == []


def test_filter_literals_drops_a_curated_config_stem_used_in_dotted_form():
    content = "set client.timeout to 30s and limits.max_body to 8mb"
    out = _filter_literals(
        [
            {"name": "client", "type": "concept"},
            {"name": "limits", "type": "concept"},
            {"name": "postgres", "type": "database"},
        ],
        content,
    )
    assert _names(out) == ["postgres"]


def test_filter_literals_keeps_a_curated_stem_never_written_in_dotted_form():
    content = "the client team owns the retry policy"
    out = _filter_literals([{"name": "client", "type": "concept"}], content)
    assert _names(out) == ["client"]


def test_filter_literals_drops_an_uncurated_stem_of_a_deep_dotted_key():
    content = "we raised producer.linger.ms to 20"
    out = _filter_literals([{"name": "producer", "type": "concept"}], content)
    assert out == []


def test_filter_literals_keeps_a_stem_that_also_appears_standalone():
    content = "we raised producer.linger.ms to 20 after the producer stalled"
    out = _filter_literals([{"name": "producer", "type": "concept"}], content)
    assert _names(out) == ["producer"]


def test_filter_literals_leaves_a_single_dot_module_root_alone():
    # 'asyncio.create_task' is one dot, so the root the name collapse produced
    # is a real library, not a config-key stem.
    content = "we replaced asyncio.create_task with a task group"
    out = _filter_literals([{"name": "asyncio", "type": "tool"}], content)
    assert _names(out) == ["asyncio"]


def test_filter_literals_does_not_mutate_its_input():
    given = [{"name": "192.168.0.195", "type": "concept"}]
    _filter_literals(given, "reachable at 192.168.0.195")
    assert given == [{"name": "192.168.0.195", "type": "concept"}]


def test_filter_literals_is_seated_beside_filter_noise_per_doc_06_s1():
    names = [p.name for p in PASS_REGISTRY]
    assert names[index_of(PASS_REGISTRY, "filter_noise") + 1] == "filter_literals"
    assert index_of(PASS_REGISTRY, "filter_literals") < index_of(
        PASS_REGISTRY, "snap_hardware_types"
    )


def test_the_literal_drop_commutes_with_the_type_snappers():
    # The move above is safe only because the two type passes rewrite `type`
    # and never membership or order, while the filter keys on `name` alone.
    given = [
        {"name": "gpu", "type": "artifact"},
        {"name": "qdrant", "type": "tool"},
        {"name": "192.168.0.195", "type": "concept"},
        {"name": "client", "type": "concept"},
    ]
    content = "the gpu box at 192.168.0.195 runs qdrant with client.timeout raised"

    literals_first = _apply_type_overrides(
        _snap_hardware_types(_filter_literals(given, content))
    )
    snappers_first = _filter_literals(
        _apply_type_overrides(_snap_hardware_types(given)), content
    )
    assert literals_first == snappers_first
    assert _types(literals_first) == {"gpu": "tool", "qdrant": "database"}


# ── _snap_hardware_types ─────────────────────────────────────────────


@pytest.mark.parametrize("name", ["cpu", "gpu", "nvme", "vram", "cuda", "rocm"])
@pytest.mark.parametrize("given_type", ["entity", "artifact", "service", "concept"])
def test_snap_hardware_types_forces_a_hardware_token_to_tool(name, given_type):
    # The taxonomy has no hardware class, so the model scatters these across
    # several buckets; 'tool' is the closest one and is applied unconditionally.
    out = _snap_hardware_types([{"name": name, "type": given_type}])
    assert _types(out) == {name: "tool"}


def test_snap_hardware_types_matches_case_and_whitespace_insensitively():
    out = _snap_hardware_types([{"name": "  GPU  ", "type": "artifact"}])
    assert out[0]["type"] == "tool"


def test_snap_hardware_types_leaves_other_names_alone():
    out = _snap_hardware_types([{"name": "postgres", "type": "database"}])
    assert _types(out) == {"postgres": "database"}


def test_snap_hardware_types_keeps_every_entity():
    given = [{"name": "gpu", "type": "entity"}, {"name": "postgres", "type": "database"}]
    assert len(_snap_hardware_types(given)) == 2


def test_snap_hardware_types_does_not_mutate_its_input():
    given = [{"name": "gpu", "type": "artifact"}]
    _snap_hardware_types(given)
    assert given == [{"name": "gpu", "type": "artifact"}]


# ── _apply_type_overrides ────────────────────────────────────────────
#
# The curated map is where nuanced typing is fixed. The model flips the
# same well-known name between buckets from one run to the next, and six
# rounds of prompt patches failed to move it; the map settles it.


@pytest.mark.parametrize("name,expected", [
    ("darkmem", "project"),
    ("darkraise-ui", "tool"),
    ("qdrant", "database"),
    ("postgres", "database"),
    ("pgvector", "tool"),
    ("github", "service"),
    ("ollama", "service"),
    ("leiden", "algorithm"),
    ("mcp", "protocol"),
])
def test_apply_type_overrides_snaps_a_curated_name(name, expected):
    out = _apply_type_overrides([{"name": name, "type": "concept"}])
    assert _types(out) == {name: expected}


@pytest.mark.parametrize("guess", ["tool", "service", "concept", "database", "project"])
def test_apply_type_overrides_beats_every_guess_the_model_makes(guess):
    out = _apply_type_overrides([{"name": "qdrant", "type": guess}])
    assert out[0]["type"] == "database"


def test_apply_type_overrides_separates_a_store_from_its_extension():
    # pgvector is a Postgres extension, so it stays a tool while the vector
    # stores it competes with are databases.
    out = _apply_type_overrides([
        {"name": "pgvector", "type": "database"},
        {"name": "qdrant", "type": "tool"},
    ])
    assert _types(out) == {"pgvector": "tool", "qdrant": "database"}


def test_apply_type_overrides_separates_the_project_from_its_ui_library():
    out = _apply_type_overrides([
        {"name": "darkraise", "type": "tool"},
        {"name": "darkraise-ui", "type": "project"},
    ])
    assert _types(out) == {"darkraise": "project", "darkraise-ui": "tool"}


def test_apply_type_overrides_matches_case_insensitively():
    out = _apply_type_overrides([{"name": "PostgreSQL", "type": "tool"}])
    assert out[0]["type"] == "database"


def test_apply_type_overrides_leaves_an_uncurated_name_alone():
    out = _apply_type_overrides([{"name": "phoenix v2", "type": "tool"}])
    assert _types(out) == {"phoenix v2": "tool"}


def test_every_curated_type_is_in_the_closed_taxonomy():
    assert set(_TYPE_OVERRIDES.values()) <= set(ENTITY_TYPES)


def test_every_curated_key_is_lowercase():
    assert all(k == k.lower() for k in _TYPE_OVERRIDES)


def test_apply_type_overrides_does_not_mutate_its_input():
    given = [{"name": "qdrant", "type": "tool"}]
    _apply_type_overrides(given)
    assert given == [{"name": "qdrant", "type": "tool"}]


# ── _filter_hallucinated_names ───────────────────────────────────────


def test_filter_hallucinated_names_drops_a_multiword_name_absent_from_the_source():
    content = "the february outage took the cluster down"
    out = _filter_hallucinated_names(
        [
            {"name": "february outage", "type": "event"},
            {"name": "march outage", "type": "event"},
        ],
        content,
    )
    assert _names(out) == ["february outage"]


def test_filter_hallucinated_names_requires_every_significant_token():
    content = "we tuned the retrieval path this week"
    out = _filter_hallucinated_names(
        [{"name": "retrieval reranker", "type": "concept"}], content
    )
    assert out == []


def test_filter_hallucinated_names_ignores_stopwords_and_short_tokens():
    content = "hybrid search over the memories table"
    out = _filter_hallucinated_names(
        [{"name": "hybrid search of memories", "type": "concept"}], content
    )
    assert _names(out) == ["hybrid search of memories"]


def test_filter_hallucinated_names_tolerates_a_plural_shift():
    content = "the savepoint wraps the graph write"
    out = _filter_hallucinated_names(
        [{"name": "savepoints wrap", "type": "concept"}], content
    )
    assert _names(out) == ["savepoints wrap"]


def test_filter_hallucinated_names_does_not_police_a_single_token():
    # 'postgres' is a canonical short form of 'PostgreSQL' and must survive
    # even though the exact token is absent.
    content = "we run PostgreSQL 16 in the homelab"
    out = _filter_hallucinated_names([{"name": "postgres", "type": "database"}], content)
    assert _names(out) == ["postgres"]


def test_filter_hallucinated_names_drops_a_fabricated_date():
    content = "the incident closed on 2026-05-20"
    out = _filter_hallucinated_names(
        [
            {"name": "2026-05-12", "type": "concept"},
            {"name": "2026-05-20", "type": "concept"},
        ],
        content,
    )
    assert _names(out) == ["2026-05-20"]


def test_filter_hallucinated_names_is_a_noop_without_content():
    given = [{"name": "march outage", "type": "event"}]
    assert _filter_hallucinated_names(given, "") == given


def test_filter_hallucinated_names_does_not_mutate_its_input():
    given = [{"name": "march outage", "type": "event"}]
    _filter_hallucinated_names(given, "the february outage")
    assert given == [{"name": "march outage", "type": "event"}]


# ── _filter_negation_only ────────────────────────────────────────────


def test_filter_negation_only_drops_an_entity_mentioned_only_negatively():
    kept, dropped = _filter_negation_only(
        [
            {"name": "postgres", "type": "database"},
            {"name": "redis", "type": "database"},
        ],
        "we run postgres without redis",
    )
    assert _names(kept) == ["postgres"]
    assert dropped == {"redis"}


@pytest.mark.parametrize("phrase", [
    "we use postgres, no redis",
    "we use postgres and never redis",
    "we use postgres and never use redis",
    "we use postgres and never used redis",
    "we use postgres, avoiding redis",
    "we use postgres and do not use redis",
    "we use postgres and don't use redis",
    "we use postgres, skipping redis",
])
def test_filter_negation_only_recognises_the_negation_markers(phrase):
    kept, dropped = _filter_negation_only(
        [
            {"name": "postgres", "type": "database"},
            {"name": "redis", "type": "database"},
        ],
        phrase,
    )
    assert _names(kept) == ["postgres"]
    assert dropped == {"redis"}


def test_filter_negation_only_keeps_an_entity_with_one_positive_mention():
    kept, dropped = _filter_negation_only(
        [{"name": "redis", "type": "database"}],
        "we deploy redis for the queue, though the cache runs without redis",
    )
    assert _names(kept) == ["redis"]
    assert dropped == set()


def test_filter_negation_only_treats_instead_of_as_a_selection_not_a_negation():
    # 'chose X instead of Y' keeps both endpoints so the IMPROVES_ON edge the
    # selection gate emits is not orphaned.
    kept, _ = _filter_negation_only(
        [{"name": "qdrant", "type": "database"}],
        "we chose pgvector instead of qdrant",
    )
    assert _names(kept) == ["qdrant"]


def test_filter_negation_only_keeps_an_entity_the_source_never_mentions():
    # Absence is the rescue passes' business, not this one's.
    kept, dropped = _filter_negation_only(
        [{"name": "clickhouse", "type": "database"}], "we run postgres"
    )
    assert _names(kept) == ["clickhouse"]
    assert dropped == set()


def test_filter_negation_only_is_a_noop_without_content():
    given = [{"name": "redis", "type": "database"}]
    kept, dropped = _filter_negation_only(given, "")
    assert kept == given
    assert dropped == set()


def test_filter_negation_only_does_not_mutate_its_input():
    given = [{"name": "redis", "type": "database"}]
    _filter_negation_only(given, "we run postgres without redis")
    assert given == [{"name": "redis", "type": "database"}]


# ── _dedup_entities ──────────────────────────────────────────────────


def test_dedup_entities_collapses_an_acronym_onto_its_expansion():
    out = _dedup_entities([
        {"name": "Central Processing Unit", "type": "concept"},
        {"name": "CPU", "type": "tool"},
    ])
    assert _names(out) == ["Central Processing Unit"]


def test_dedup_entities_is_whitespace_and_case_insensitive():
    out = _dedup_entities([
        {"name": "GitHub Actions", "type": "service"},
        {"name": "githubactions", "type": "tool"},
    ])
    assert _names(out) == ["GitHub Actions"]


def test_dedup_entities_keeps_the_longest_name():
    out = _dedup_entities([
        {"name": "rrf", "type": "algorithm"},
        {"name": "R R F", "type": "concept"},
    ])
    assert _names(out) == ["R R F"]


def test_dedup_entities_does_not_merge_on_substrings():
    # Deliberately NOT a substring rule: 'cpu' inside 'cpu_fallback' is a
    # different entity, and the rescue pass downstream depends on that.
    out = _dedup_entities([
        {"name": "cpu_fallback", "type": "concept"},
        {"name": "cpu", "type": "tool"},
    ])
    assert sorted(_names(out)) == ["cpu", "cpu_fallback"]


def test_dedup_entities_keeps_distinct_names():
    out = _dedup_entities([
        {"name": "postgres", "type": "database"},
        {"name": "qdrant", "type": "database"},
    ])
    assert sorted(_names(out)) == ["postgres", "qdrant"]


def test_dedup_entities_does_not_mutate_its_input():
    given = [
        {"name": "CPU", "type": "tool"},
        {"name": "Central Processing Unit", "type": "concept"},
    ]
    _dedup_entities(given)
    assert _names(given) == ["CPU", "Central Processing Unit"]


# ── The ordered stage ────────────────────────────────────────────────


def test_stage_one_runs_the_six_shaping_steps_in_doc_06_s1_order():
    shaping = [p.name for p in PASS_REGISTRY if p.stage == "entity_shaping"]
    assert shaping == [
        "normalize_names",
        "filter_noise",
        "filter_literals",
        "snap_hardware_types",
        "apply_type_overrides",
        "filter_hallucinated_names",
        "filter_negation_only",
        "dedup_entities",
    ]


def test_stage_one_is_the_first_stage():
    assert PASS_REGISTRY[0].stage == "entity_shaping"


def test_stage_one_shapes_a_realistic_batch_end_to_end():
    content = (
        "darkmem runs on the Proxmox host at 192.168.0.195:8000 behind nginx. "
        "The GPU box embeds with BGE; docs live at https://example.com/guide and "
        "the config sets client.timeout to 30s. We never use Redis."
    )
    state = CleanState(
        content=content,
        entities=[
            {"name": "darkmem", "type": "tool"},
            {"name": "Proxmox host", "type": "service"},
            {"name": "192.168.0.195:8000", "type": "concept"},
            {"name": "nginx", "type": "service"},
            {"name": "GPU", "type": "artifact"},
            {"name": "bge", "type": "concept"},
            {"name": "https://example.com/guide", "type": "artifact"},
            {"name": "client", "type": "concept"},
            {"name": "30s", "type": "concept"},
            {"name": "redis", "type": "database"},
            {"name": "the config", "type": "concept"},
            {"name": "march outage", "type": "event"},
        ],
    )
    shaping = tuple(p for p in PASS_REGISTRY if p.stage == "entity_shaping")
    out = run_passes(shaping, state)

    assert _types(out.entities) == {
        "darkmem": "project",
        "Proxmox": "tool",
        "nginx": "tool",
        "GPU": "tool",
        "bge": "tool",
    }
    assert out.negated_names == {"redis"}
