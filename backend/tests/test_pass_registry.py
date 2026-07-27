"""The extraction post-processor's ordered pass registry (T1.24a).

Covers the scaffold contract: an explicit ordered sequence of pure passes,
each with its own fixture, the three load-bearing orderings from doc 06 §4,
and the zero-model-call property of the whole chain.
"""

import copy
import inspect
import socket

import httpx
import pytest

from app.services.extraction_clean import (
    ORDERING_CONSTRAINTS,
    PASS_REGISTRY,
    CleanState,
    Pass,
    RunsBefore,
    StraddlesPivot,
    clean_extraction,
    run_passes,
    validate_registry,
)
from app.services.extraction_pass_harness import (
    RegistryContractError,
    index_of,
    indices_of,
    without,
)


def _state(**kw) -> CleanState:
    kw.setdefault("raw_entities", kw.get("entities", []))
    return CleanState(**kw)


def _names(entities):
    return [e["name"] for e in entities]


def _triples(relationships):
    return {(r["source"], r["type"], r["target"]) for r in relationships}


def _reorder(registry, first, second):
    """Swap two single-occurrence passes, keeping every other position."""
    i, j = index_of(registry, first), index_of(registry, second)
    out = list(registry)
    out[i], out[j] = out[j], out[i]
    return tuple(out)


def _drop_occurrence(registry, name, ordinal):
    spot = indices_of(registry, name)[ordinal]
    return tuple(p for i, p in enumerate(registry) if i != spot)


# ── Per-pass fixtures ────────────────────────────────────────────────
#
# One entry per registry pass: the isolated input it runs on, and the
# effect that pass alone is responsible for. Keyed by pass name, so a new
# pass without a fixture fails ``test_every_pass_has_a_fixture``.

def _check_normalize_names(out):
    assert _names(out.entities) == ["Postgres"]


def _check_filter_noise(out):
    assert _names(out.entities) == ["postgres"]


def _check_snap_hardware_types(out):
    assert out.entities[0]["type"] == "tool"


def _check_apply_type_overrides(out):
    assert out.entities[0]["type"] == "database"


def _check_filter_literals(out):
    assert _names(out.entities) == ["postgres"]


def _check_filter_hallucinated_names(out):
    assert _names(out.entities) == ["february outage"]


def _check_filter_negation_only(out):
    assert _names(out.entities) == ["postgres"]
    assert out.negated_names == {"redis"}


def _check_dedup_entities(out):
    assert _names(out.entities) == ["Central Processing Unit"]


def _check_rescue_known_entities(out):
    assert "cpu" in _names(out.entities)


def _check_rescue_file_path_entities(out):
    added = [e for e in out.entities if e["name"] == "backend/app/main.py"]
    assert added and added[0]["type"] == "artifact"


def _check_rescue_happened_on(out):
    assert "2026-05-12" in _names(out.entities)
    assert ("outage", "HAPPENED_ON", "2026-05-12") in _triples(out.relationships)


def _check_rescue_relations(out):
    assert ("darkmem", "DEPLOYED_ON", "proxmox") in _triples(out.relationships)
    rescued = [r for r in out.relationships if (r.get("properties") or {}).get("rescue")]
    assert rescued


def _check_remap_to_valid_entities(out):
    assert _triples(out.relationships) == {("darkmem", "DEPLOYED_ON", "proxmox")}


def _check_drop_edges_to_negated(out):
    assert _triples(out.relationships) == {("darkmem", "USES", "postgres")}


def _check_gate_replaces_selection(out):
    assert out.relationships[0]["type"] == "IMPROVES_ON"


def _check_gate_replaces_requires_verb(out):
    assert out.relationships[0]["type"] == "RELATED_TO"


def _check_suppress_temporal_edges(out):
    assert out.relationships == []


def _check_downgrade_future_to_mentions(out):
    assert out.relationships[0]["type"] == "MENTIONS"


def _check_drop_date_misuse(out):
    assert _triples(out.relationships) == {("darkmem", "HAPPENED_ON", "2026-05-12")}


def _check_validate_directions(out):
    assert _triples(out.relationships) == {("pgvector", "REPLACES", "qdrant")}


def _check_validate_hosting_direction(out):
    assert _triples(out.relationships) == {("darkmem", "DEPLOYED_ON", "gpu")}


def _check_filter_event_edges(out):
    assert _triples(out.relationships) == {("outage", "HAPPENED_ON", "2026-05-12")}


def _check_drop_uses_when_replaces_exists(out):
    assert _triples(out.relationships) == {("pgvector", "REPLACES", "qdrant")}


def _check_drop_uses_when_deployed_on_exists(out):
    assert _triples(out.relationships) == {("darkmem", "DEPLOYED_ON", "proxmox")}


def _check_dedup_by_target_predicate(out):
    assert _triples(out.relationships) == {("darkmem", "USES", "rrf")}


def _check_fan_out_coordinated(out):
    assert _triples(out.relationships) == {
        ("grafana", "USES", "postgres"),
        ("loki", "USES", "postgres"),
        ("promtail", "USES", "postgres"),
    }


def _check_drop_unlinked_dates(out):
    assert _names(out.entities) == ["postgres"]


PASS_FIXTURES: dict[str, tuple[CleanState, object]] = {
    "normalize_names": (
        _state(entities=[{"name": " Postgres cluster ", "type": "concept"}]),
        _check_normalize_names,
    ),
    "filter_noise": (
        _state(entities=[
            {"name": "config.yaml", "type": "artifact"},
            {"name": "postgres", "type": "database"},
        ]),
        _check_filter_noise,
    ),
    "snap_hardware_types": (
        _state(entities=[{"name": "GPU", "type": "artifact"}]),
        _check_snap_hardware_types,
    ),
    "apply_type_overrides": (
        _state(entities=[{"name": "Qdrant", "type": "tool"}]),
        _check_apply_type_overrides,
    ),
    "filter_literals": (
        _state(
            content="postgres answers on 192.168.0.5 today",
            entities=[
                {"name": "192.168.0.5", "type": "concept"},
                {"name": "postgres", "type": "database"},
            ],
        ),
        _check_filter_literals,
    ),
    "filter_hallucinated_names": (
        _state(
            content="the february outage took the cluster down",
            entities=[
                {"name": "february outage", "type": "event"},
                {"name": "march outage", "type": "event"},
            ],
        ),
        _check_filter_hallucinated_names,
    ),
    "filter_negation_only": (
        _state(
            content="we run postgres without redis",
            entities=[
                {"name": "postgres", "type": "database"},
                {"name": "redis", "type": "database"},
            ],
        ),
        _check_filter_negation_only,
    ),
    "dedup_entities": (
        _state(entities=[
            {"name": "Central Processing Unit", "type": "concept"},
            {"name": "CPU", "type": "tool"},
        ]),
        _check_dedup_entities,
    ),
    "rescue_known_entities": (
        _state(content="the CPU stayed pinned all night", entities=[]),
        _check_rescue_known_entities,
    ),
    "rescue_file_path_entities": (
        _state(content="the health route moved to backend/app/main.py", entities=[]),
        _check_rescue_file_path_entities,
    ),
    "rescue_happened_on": (
        _state(
            content="the outage happened on 2026-05-12",
            entities=[{"name": "outage", "type": "event"}],
        ),
        _check_rescue_happened_on,
    ),
    "rescue_relations": (
        _state(
            content="darkmem runs on proxmox",
            entities=[
                {"name": "darkmem", "type": "project"},
                {"name": "proxmox", "type": "tool"},
            ],
        ),
        _check_rescue_relations,
    ),
    "remap_to_valid_entities": (
        _state(
            entities=[
                {"name": "darkmem", "type": "project"},
                {"name": "proxmox", "type": "tool"},
            ],
            relationships=[
                {"source": "darkmem", "target": "proxmox", "type": "RUNS_ON"},
                {"source": "ghost", "target": "proxmox", "type": "USES"},
            ],
        ),
        _check_remap_to_valid_entities,
    ),
    "drop_edges_to_negated": (
        _state(
            negated_names={"redis"},
            relationships=[
                {"source": "darkmem", "target": "redis", "type": "USES"},
                {"source": "darkmem", "target": "postgres", "type": "USES"},
            ],
        ),
        _check_drop_edges_to_negated,
    ),
    "gate_replaces_selection": (
        _state(
            content="we chose pgvector over qdrant",
            relationships=[
                {"source": "pgvector", "target": "qdrant", "type": "REPLACES"},
            ],
        ),
        _check_gate_replaces_selection,
    ),
    "gate_replaces_requires_verb": (
        _state(
            content="all writes now go through the event bus",
            relationships=[
                {"source": "event bus", "target": "legacy ledger", "type": "REPLACES"},
            ],
        ),
        _check_gate_replaces_requires_verb,
    ),
    "suppress_temporal_edges": (
        _state(
            content="the outage happened after the deploy",
            relationships=[
                {"source": "outage", "target": "deploy", "type": "RELATED_TO"},
            ],
        ),
        _check_suppress_temporal_edges,
    ),
    "downgrade_future_to_mentions": (
        _state(
            content="we plan to add redis next quarter",
            relationships=[{"source": "darkmem", "target": "redis", "type": "USES"}],
        ),
        _check_downgrade_future_to_mentions,
    ),
    "drop_date_misuse": (
        _state(relationships=[
            {"source": "darkmem", "target": "2026-05-12", "type": "USES"},
            {"source": "darkmem", "target": "2026-05-12", "type": "HAPPENED_ON"},
        ]),
        _check_drop_date_misuse,
    ),
    "validate_directions": (
        _state(
            content="we migrated from qdrant to pgvector",
            relationships=[
                {"source": "qdrant", "target": "pgvector", "type": "REPLACES"},
            ],
        ),
        _check_validate_directions,
    ),
    "validate_hosting_direction": (
        _state(relationships=[
            {"source": "gpu", "target": "darkmem", "type": "DEPLOYED_ON"},
        ]),
        _check_validate_hosting_direction,
    ),
    "filter_event_edges": (
        _state(
            entities=[{"name": "outage", "type": "event"}],
            relationships=[
                {"source": "outage", "target": "disk", "type": "USES"},
                {"source": "outage", "target": "2026-05-12", "type": "HAPPENED_ON"},
            ],
        ),
        _check_filter_event_edges,
    ),
    "drop_uses_when_replaces_exists": (
        _state(relationships=[
            {"source": "pgvector", "target": "qdrant", "type": "REPLACES"},
            {"source": "qdrant", "target": "pgvector", "type": "USES"},
        ]),
        _check_drop_uses_when_replaces_exists,
    ),
    "drop_uses_when_deployed_on_exists": (
        _state(relationships=[
            {"source": "darkmem", "target": "proxmox", "type": "DEPLOYED_ON"},
            {"source": "darkmem", "target": "proxmox", "type": "USES"},
        ]),
        _check_drop_uses_when_deployed_on_exists,
    ),
    "dedup_by_target_predicate": (
        _state(relationships=[
            {"source": "darkmem", "target": "rrf", "type": "USES", "weight": 0.9},
            {"source": "qwen3-embedding", "target": "rrf", "type": "USES", "weight": 0.4},
        ]),
        _check_dedup_by_target_predicate,
    ),
    "fan_out_coordinated": (
        _state(
            content="grafana, loki and promtail all use postgres",
            entities=[
                {"name": "grafana", "type": "service"},
                {"name": "loki", "type": "service"},
                {"name": "promtail", "type": "service"},
                {"name": "postgres", "type": "database"},
            ],
            relationships=[
                {"source": "grafana", "target": "postgres", "type": "USES"},
            ],
        ),
        _check_fan_out_coordinated,
    ),
    "drop_unlinked_dates": (
        _state(entities=[
            {"name": "2026-05-12", "type": "concept"},
            {"name": "postgres", "type": "database"},
        ]),
        _check_drop_unlinked_dates,
    ),
}


REGISTRY_NAMES = sorted({p.name for p in PASS_REGISTRY})


# ── Registry shape ───────────────────────────────────────────────────


def test_registry_is_an_explicit_ordered_sequence():
    assert isinstance(PASS_REGISTRY, tuple)
    assert all(isinstance(p, Pass) for p in PASS_REGISTRY)
    assert len(PASS_REGISTRY) == 28


def test_registry_validates_against_its_own_contract():
    validate_registry(PASS_REGISTRY, ORDERING_CONSTRAINTS)


def test_registry_bindings_name_real_state_fields():
    for p in PASS_REGISTRY:
        for field_name in p.reads + p.writes:
            assert hasattr(CleanState(), field_name)


def test_unknown_state_field_is_rejected():
    bogus = (Pass("bogus", "s", lambda x: x, ("nope",), ("entities",)),)
    with pytest.raises(RegistryContractError):
        validate_registry(bogus)


def test_stages_are_contiguous():
    seen: list[str] = []
    for p in PASS_REGISTRY:
        if not seen or seen[-1] != p.stage:
            assert p.stage not in seen, f"stage {p.stage} is not contiguous"
            seen.append(p.stage)
    assert seen == [
        "entity_shaping",
        "entity_rescue",
        "relation_synthesis",
        "relation_gating",
        "collapse_and_fanout",
    ]


# ── Per-pass purity and fixtures ─────────────────────────────────────


@pytest.mark.parametrize("name", REGISTRY_NAMES)
def test_every_pass_has_a_fixture(name):
    assert name in PASS_FIXTURES


@pytest.mark.parametrize("name", REGISTRY_NAMES)
def test_pass_fixture_effect(name):
    state, check = PASS_FIXTURES[name]
    step = PASS_REGISTRY[index_of(PASS_REGISTRY, name)]
    check(run_passes((step,), state))


@pytest.mark.parametrize("name", REGISTRY_NAMES)
def test_pass_does_not_mutate_its_input(name):
    state, _ = PASS_FIXTURES[name]
    before = copy.deepcopy(
        (state.entities, state.relationships, state.raw_entities, state.content)
    )
    step = PASS_REGISTRY[index_of(PASS_REGISTRY, name)]
    run_passes((step,), state)
    assert (
        state.entities,
        state.relationships,
        state.raw_entities,
        state.content,
    ) == before


@pytest.mark.parametrize("name", REGISTRY_NAMES)
def test_pass_is_a_plain_sync_function(name):
    step = PASS_REGISTRY[index_of(PASS_REGISTRY, name)]
    assert inspect.isfunction(step.fn)
    assert not inspect.iscoroutinefunction(step.fn)


# ── Ordering constraint 1: entity rescue after entity dedup ──────────


def test_entity_rescue_runs_after_entity_dedup():
    assert index_of(PASS_REGISTRY, "dedup_entities") < index_of(
        PASS_REGISTRY, "rescue_known_entities"
    )


def test_rescue_before_dedup_loses_the_canonical_short_name():
    content = "The Github  Actions runner reported that github actions timed out."
    state = _state(
        content=content,
        entities=[{"name": "Github  Actions", "type": "service"}],
    )
    kept = _names(run_passes(PASS_REGISTRY, state).entities)
    swapped = _reorder(PASS_REGISTRY, "dedup_entities", "rescue_known_entities")
    lost = _names(run_passes(swapped, state).entities)
    assert "github actions" in kept
    assert "github actions" not in lost


def test_swapping_dedup_and_rescue_breaks_the_declared_contract():
    swapped = _reorder(PASS_REGISTRY, "dedup_entities", "rescue_known_entities")
    with pytest.raises(RegistryContractError):
        validate_registry(swapped, ORDERING_CONSTRAINTS)


# ── Ordering constraint 2: fan-out last ──────────────────────────────


def test_fan_out_runs_after_target_predicate_dedup():
    assert index_of(PASS_REGISTRY, "dedup_by_target_predicate") < index_of(
        PASS_REGISTRY, "fan_out_coordinated"
    )


def test_dedup_after_fan_out_collapses_the_coordinated_set():
    state = _state(
        content="grafana, loki and promtail all use postgres",
        entities=[
            {"name": "grafana", "type": "service"},
            {"name": "loki", "type": "service"},
            {"name": "promtail", "type": "service"},
            {"name": "postgres", "type": "database"},
        ],
        relationships=[{"source": "grafana", "target": "postgres", "type": "USES"}],
    )
    sources = {
        r["source"] for r in run_passes(PASS_REGISTRY, state).relationships
        if r["type"] == "USES" and r["target"] == "postgres"
    }
    assert sources == {"grafana", "loki", "promtail"}

    swapped = _reorder(PASS_REGISTRY, "dedup_by_target_predicate", "fan_out_coordinated")
    collapsed = {
        r["source"] for r in run_passes(swapped, state).relationships
        if r["type"] == "USES" and r["target"] == "postgres"
    }
    assert len(collapsed) == 1


def test_swapping_dedup_and_fan_out_breaks_the_declared_contract():
    swapped = _reorder(PASS_REGISTRY, "dedup_by_target_predicate", "fan_out_coordinated")
    with pytest.raises(RegistryContractError):
        validate_registry(swapped, ORDERING_CONSTRAINTS)


# ── Ordering constraint 3: the event guard runs twice ────────────────


def test_filter_event_edges_straddles_fan_out():
    spots = indices_of(PASS_REGISTRY, "filter_event_edges")
    pivot = index_of(PASS_REGISTRY, "fan_out_coordinated")
    assert len(spots) == 2
    assert spots[0] < pivot < spots[1]


def test_second_event_guard_catches_edges_fan_out_mints():
    state = _state(
        content="postgres, redis and the outage all relate to disk",
        entities=[
            {"name": "postgres", "type": "database"},
            {"name": "redis", "type": "database"},
            {"name": "outage", "type": "event"},
            {"name": "disk", "type": "tool"},
        ],
        relationships=[{"source": "postgres", "target": "disk", "type": "USES"}],
        relation_rescue=False,
    )
    guarded = _triples(run_passes(PASS_REGISTRY, state).relationships)
    assert ("redis", "USES", "disk") in guarded
    assert ("outage", "USES", "disk") not in guarded

    single = _drop_occurrence(PASS_REGISTRY, "filter_event_edges", 1)
    assert ("outage", "USES", "disk") in _triples(
        run_passes(single, state).relationships
    )


def test_dropping_the_second_event_guard_breaks_the_declared_contract():
    single = _drop_occurrence(PASS_REGISTRY, "filter_event_edges", 1)
    with pytest.raises(RegistryContractError):
        validate_registry(single, ORDERING_CONSTRAINTS)


def test_ordering_constraints_are_declared_as_data():
    assert {type(c) for c in ORDERING_CONSTRAINTS} == {RunsBefore, StraddlesPivot}
    assert all(c.why for c in ORDERING_CONSTRAINTS)


# ── Harness behaviour ────────────────────────────────────────────────


def test_a_pass_is_individually_reversible():
    state = _state(
        content="grafana, loki and promtail all use postgres",
        entities=[
            {"name": "grafana", "type": "service"},
            {"name": "loki", "type": "service"},
            {"name": "promtail", "type": "service"},
            {"name": "postgres", "type": "database"},
        ],
        relationships=[{"source": "grafana", "target": "postgres", "type": "USES"}],
    )
    full = run_passes(PASS_REGISTRY, state).relationships
    reduced = run_passes(without(PASS_REGISTRY, "fan_out_coordinated"), state)
    assert len(full) > len(reduced.relationships)


def test_gated_pass_is_skipped_when_its_flag_is_off():
    state = _state(
        content="darkmem runs on proxmox",
        entities=[
            {"name": "darkmem", "type": "project"},
            {"name": "proxmox", "type": "tool"},
        ],
        relation_rescue=False,
    )
    assert run_passes(PASS_REGISTRY, state).relationships == []


def test_clean_extraction_runs_the_registry():
    raw = {
        "entities": [
            {"name": "darkmem", "type": "project"},
            {"name": "proxmox", "type": "tool"},
        ],
        "relationships": [],
        "memory_type": "fact",
    }
    out = clean_extraction(raw, "darkmem runs on proxmox")
    assert out["memory_type"] == "fact"
    assert ("darkmem", "DEPLOYED_ON", "proxmox") in _triples(out["relationships"])


def test_whole_chain_makes_zero_model_calls(monkeypatch):
    def _boom(*args, **kwargs):
        raise AssertionError("a deterministic pass attempted network I/O")

    monkeypatch.setattr(httpx.Client, "__init__", _boom)
    monkeypatch.setattr(httpx.AsyncClient, "__init__", _boom)
    monkeypatch.setattr(socket.socket, "connect", _boom)
    monkeypatch.setattr(socket, "create_connection", _boom)

    raw = {
        "entities": [
            {"name": "darkmem", "type": "project"},
            {"name": "qdrant", "type": "database"},
            {"name": "pgvector", "type": "tool"},
        ],
        "relationships": [
            {"source": "qdrant", "target": "pgvector", "type": "REPLACES"},
        ],
    }
    out = clean_extraction(raw, "we migrated darkmem from qdrant to pgvector")
    assert ("pgvector", "REPLACES", "qdrant") in _triples(out["relationships"])
