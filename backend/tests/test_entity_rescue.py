"""Stage 2 of the extraction post-processor — entity rescue (T1.24c).

Doc 06 §4 S2 adds back what the LLM dropped. The stage now runs four passes:
``_rescue_relation_endpoints`` reinstates a name the model asserted in one of
its own edges but omitted from its own entity list; ``_rescue_known_entities``
adds curated short and hardware names, negation-aware and span-guarded;
``_rescue_file_path_entities`` adds ``a/b/c.py`` tokens as artifacts (its
behaviour is covered in ``test_extraction_rescue.py``, its seat here);
``_rescue_happened_on`` keeps ISO dates alive for HAPPENED_ON.

The stage-level contract — rescue after dedup, endpoint rescue before the
remap that would otherwise delete the edges it exists to save — is pinned at
the bottom of the file.
"""

import pytest

from app.services.extraction_clean import (
    ORDERING_CONSTRAINTS,
    PASS_REGISTRY,
    STAGE_ENTITY_RESCUE,
    STAGE_ENTITY_SHAPING,
    CleanState,
    RunsBefore,
    _ARTIFACT_HEAD_NOUNS,
    _endpoint_entity_type,
    _rescue_happened_on,
    _rescue_known_entities,
    _rescue_relation_endpoints,
    clean_extraction,
    run_passes,
)
from app.services.extraction_pass_harness import index_of
from app.taxonomy import ENTITY_TYPES


def _names(entities):
    return [e["name"] for e in entities]


def _types(entities):
    return {e["name"]: e["type"] for e in entities}


# ── _rescue_relation_endpoints ───────────────────────────────────────
#
# The model's ``entities`` array is biased towards proper nouns: it lists
# Auth0 and RFC 7519 and drops the common-noun component the sentence is
# about, even while naming that component as an endpoint of its own edges.
# Every edge anchored to the missing name then dies in the remap.


def test_rescue_relation_endpoints_reinstates_an_asserted_source():
    content = "The design doc cites RFC 7519 and PEP 484."
    out = _rescue_relation_endpoints(
        [{"name": "RFC 7519", "type": "paper"}, {"name": "PEP 484", "type": "paper"}],
        [
            {"source": "design doc", "target": "RFC 7519", "type": "CITES"},
            {"source": "design doc", "target": "PEP 484", "type": "CITES"},
        ],
        content,
    )
    assert _types(out)["design doc"] == "artifact"


def test_rescue_relation_endpoints_reinstates_an_asserted_target():
    content = "The scheduler writes into the audit log every hour."
    out = _rescue_relation_endpoints(
        [{"name": "scheduler", "type": "artifact"}],
        [{"source": "scheduler", "target": "audit log", "type": "USES"}],
        content,
    )
    assert "audit log" in _names(out)


def test_rescue_relation_endpoints_adds_each_missing_name_once():
    content = (
        "The web app, the mobile app, and the CLI all authenticate through "
        "Auth0 and report metrics to Datadog."
    )
    out = _rescue_relation_endpoints(
        [{"name": "Auth0", "type": "service"}, {"name": "Datadog", "type": "service"}],
        [
            {"source": s, "target": t, "type": "USES"}
            for s in ("web app", "mobile app", "CLI")
            for t in ("Auth0", "Datadog")
        ],
        content,
    )
    assert sorted(_names(out)) == sorted(
        ["Auth0", "Datadog", "web app", "mobile app", "CLI"]
    )


def test_rescue_relation_endpoints_keeps_a_name_the_model_already_listed():
    content = "darkmem uses pgvector for search."
    given = [{"name": "darkmem", "type": "project"}, {"name": "pgvector", "type": "tool"}]
    out = _rescue_relation_endpoints(
        given, [{"source": "darkmem", "target": "pgvector", "type": "USES"}], content
    )
    assert out == given


def test_rescue_relation_endpoints_matches_an_existing_name_case_insensitively():
    content = "The CLI ships with darkmem."
    out = _rescue_relation_endpoints(
        [{"name": "cli", "type": "artifact"}, {"name": "darkmem", "type": "project"}],
        [{"source": "CLI", "target": "darkmem", "type": "USES"}],
        content,
    )
    assert _names(out) == ["cli", "darkmem"]


@pytest.mark.parametrize("fabricated", ["architecture review", "clickhouse"])
def test_rescue_relation_endpoints_declines_a_name_absent_from_the_source(fabricated):
    # An edge naming something the text never says is a fabrication, and the
    # entity list is the only corroboration a rescued endpoint could have had.
    # The single-token case is why groundedness is checked here rather than
    # left to the shaping stage: _filter_hallucinated_names polices only
    # multi-word names, so a one-word invention would sail through.
    content = "The design doc cites RFC 7519."
    out = _rescue_relation_endpoints(
        [{"name": "RFC 7519", "type": "paper"}],
        [{"source": fabricated, "target": "RFC 7519", "type": "CITES"}],
        content,
    )
    assert _names(out) == ["RFC 7519"]


def test_rescue_relation_endpoints_declines_a_negated_endpoint():
    content = "The finalize handler does NOT use savepoints; it commits per block."
    out = _rescue_relation_endpoints(
        [{"name": "finalize handler", "type": "artifact"}],
        [{"source": "finalize handler", "target": "savepoints", "type": "USES"}],
        content,
    )
    assert _names(out) == ["finalize handler"]


@pytest.mark.parametrize("endpoint", [
    "config", "https://example.com/guide", "DATABASE_URL", "192.168.0.195", "30%",
])
def test_rescue_relation_endpoints_declines_what_the_shaping_stage_drops(endpoint):
    content = f"darkmem reads {endpoint} at boot."
    out = _rescue_relation_endpoints(
        [{"name": "darkmem", "type": "project"}],
        [{"source": "darkmem", "target": endpoint, "type": "USES"}],
        content,
    )
    assert _names(out) == ["darkmem"]


def test_rescue_relation_endpoints_shapes_the_name_it_admits():
    # A rescued endpoint must land in the same canonical form a model-listed
    # entity would, or it re-introduces the very names stage 1 just collapsed.
    content = "The cache stampede caused a 30-minute outage."
    out = _rescue_relation_endpoints(
        [{"name": "cache stampede", "type": "event"}],
        [{"source": "cache stampede", "target": "30-minute outage", "type": "CAUSES"}],
        content,
    )
    assert _names(out) == ["cache stampede", "outage"]


def test_rescue_relation_endpoints_is_a_noop_without_relationships():
    given = [{"name": "darkmem", "type": "project"}]
    assert _rescue_relation_endpoints(given, [], "darkmem runs here") == given


def test_rescue_relation_endpoints_is_a_noop_without_content():
    given = [{"name": "darkmem", "type": "project"}]
    rels = [{"source": "darkmem", "target": "cli", "type": "USES"}]
    assert _rescue_relation_endpoints(given, rels, "") == given


def test_rescue_relation_endpoints_does_not_mutate_its_input():
    given = [{"name": "Auth0", "type": "service"}]
    rels = [{"source": "web app", "target": "Auth0", "type": "USES"}]
    _rescue_relation_endpoints(given, rels, "The web app uses Auth0.")
    assert given == [{"name": "Auth0", "type": "service"}]


def test_rescue_relation_endpoints_saves_the_edge_the_remap_would_delete():
    # The whole point of the pass: without the entity, _remap_to_valid_entities
    # drops both edges and the memory scores zero on relations.
    content = "The design doc cites RFC 7519 and PEP 484."
    raw = {
        "entities": [
            {"name": "RFC 7519", "type": "paper"},
            {"name": "PEP 484", "type": "paper"},
        ],
        "relationships": [
            {"source": "design doc", "target": "RFC 7519", "type": "CITES"},
            {"source": "design doc", "target": "PEP 484", "type": "CITES"},
        ],
    }
    out = clean_extraction(raw, content)
    assert {(r["source"], r["type"], r["target"]) for r in out["relationships"]} == {
        ("design doc", "CITES", "RFC 7519"),
        ("design doc", "CITES", "PEP 484"),
    }


# ── _endpoint_entity_type ────────────────────────────────────────────
#
# An edge endpoint carries no type of its own. The head noun decides it, and
# the two head-noun sets are transcribed from the frozen extraction system
# prompt's own rules — 7b's named app components and surfaces, 9j's
# first-class documents — never from a gold set.


@pytest.mark.parametrize("name", [
    "web app", "mobile app", "cli", "api", "gateway", "dashboard",
    "admin console", "billing portal", "background worker", "design doc",
    "postmortem", "incident report", "openapi spec",
])
def test_endpoint_entity_type_types_a_prompt_named_surface_as_artifact(name):
    assert _endpoint_entity_type(name) == "artifact"


@pytest.mark.parametrize("name", ["savepoints", "commit-per-block", "tail latency"])
def test_endpoint_entity_type_falls_back_for_anything_else(name):
    # The prompt types 'savepoint' `concept` explicitly; an untyped endpoint
    # outside the two artifact sets takes the taxonomy's unknown default.
    assert _endpoint_entity_type(name) == "concept"


def test_endpoint_entity_type_reads_the_head_noun_not_the_whole_phrase():
    assert _endpoint_entity_type("kafka consumer") == "concept"
    assert _endpoint_entity_type("consumer dashboard") == "artifact"


def test_endpoint_entity_type_tolerates_a_plural_head():
    assert _endpoint_entity_type("release notes docs") == "artifact"


def test_every_artifact_head_noun_is_stated_by_the_system_prompt():
    # The set is a transcription, not a curated list of its own: a name that
    # is not already in the frozen prompt has no independent justification.
    import re

    from app.services import prompt as prompt_module

    system_prompt = prompt_module.get("extraction").lower()
    for noun in _ARTIFACT_HEAD_NOUNS:
        assert re.search(
            rf"(?<![a-z0-9_]){re.escape(noun)}s?(?![a-z0-9_])", system_prompt
        ), noun


def test_the_endpoint_type_is_in_the_closed_taxonomy():
    assert {"artifact", _endpoint_entity_type("tail latency")} <= set(ENTITY_TYPES)


# ── _rescue_known_entities ───────────────────────────────────────────


@pytest.mark.parametrize("name,expected", [
    ("cpu", "tool"),
    ("cuda", "tool"),
    ("nvme", "tool"),
    ("rg", "tool"),
    ("ollama", "service"),
    ("qdrant", "database"),
    ("lxc", "tool"),
])
def test_rescue_known_entities_adds_a_curated_name_the_model_dropped(name, expected):
    out = _rescue_known_entities([], f"we run the workload on {name} today")
    assert _types(out) == {name: expected}


def test_rescue_known_entities_leaves_an_uncurated_name_alone():
    out = _rescue_known_entities([], "we run clickhouse for the rollups")
    assert out == []


def test_rescue_known_entities_does_not_re_add_a_name_the_model_kept():
    given = [{"name": "GPU", "type": "tool"}]
    out = _rescue_known_entities(given, "the GPU box embeds nightly")
    assert _names(out) == ["GPU"]


@pytest.mark.parametrize("content", ["CPU.", "the CPU-bound path", "a CPU/GPU split"])
def test_rescue_known_entities_treats_punctuation_as_a_word_boundary(content):
    out = _rescue_known_entities([], content)
    assert "cpu" in _names(out)


def test_rescue_known_entities_does_not_split_an_identifier_on_an_underscore():
    # An underscore binds rather than separates, so 'CPU_count' is one
    # identifier and surfacing 'cpu' out of it is the same class of error the
    # span guard prevents.
    assert _rescue_known_entities([], "read CPU_count from the file") == []


def test_rescue_known_entities_skips_a_short_token_that_is_a_common_word():
    # 'go' is allowlisted as a name the model may emit, but auto-rescuing it
    # from prose turns 'all writes now go through' into a tool.
    out = _rescue_known_entities([], "all writes now go through the event bus")
    assert "go" not in _names(out)


def test_rescue_known_entities_drops_a_bare_prefix_its_compound_covers():
    out = _rescue_known_entities(
        [{"name": "docker", "type": "tool"}], "the stack is docker-compose only"
    )
    assert _names(out) == ["docker-compose"]


# ── the span guard (recorded regression) ─────────────────────────────
#
# Both of these shipped once and were fixed once. The word-boundary regex
# treats '-' and ' ' as breaks, so without a span guard the short curated
# name matches inside the longer mention the model already extracted.


def test_span_guard_does_not_re_add_darkraise_inside_darkraise_ui():
    given = [{"name": "darkraise-ui", "type": "tool"}]
    out = _rescue_known_entities(given, "the darkraise-ui theme tokens landed")
    assert _names(out) == ["darkraise-ui"]


def test_span_guard_does_not_re_add_github_inside_github_actions():
    given = [{"name": "GitHub Actions", "type": "service"}]
    out = _rescue_known_entities(given, "the release runs on GitHub Actions nightly")
    assert _names(out) == ["GitHub Actions"]


def test_span_guard_still_rescues_a_standalone_mention_elsewhere():
    # The guard suppresses the mention inside the longer span, not the name.
    given = [{"name": "GitHub Actions", "type": "service"}]
    out = _rescue_known_entities(
        given, "GitHub Actions builds the image; the source lives on GitHub itself"
    )
    assert _types(out) == {"GitHub Actions": "service", "github": "service"}


def test_span_guard_suppresses_the_mention_not_the_name():
    # The over-correction is as wrong as the regression: one contained mention
    # must not veto a name the text also uses on its own.
    given = [{"name": "darkraise-ui", "type": "tool"}]
    out = _rescue_known_entities(
        given, "darkraise-ui is the kit; darkraise is the product behind it"
    )
    assert _types(out) == {"darkraise-ui": "tool", "darkraise": "project"}


# ── negation awareness ───────────────────────────────────────────────


@pytest.mark.parametrize("content", [
    "the box has no CUDA at all",
    "we build without CUDA",
    "we never use CUDA here",
    "the runtime avoids CUDA entirely",
])
def test_rescue_known_entities_does_not_rescue_a_negated_mention(content):
    assert _rescue_known_entities([], content) == []


def test_rescue_known_entities_rescues_when_one_mention_is_positive():
    content = "the trainer needs CUDA, though the inference box ships without CUDA"
    out = _rescue_known_entities([], content)
    assert "cuda" in _names(out)


def test_rescue_known_entities_is_a_noop_without_content():
    assert _rescue_known_entities([{"name": "gpu", "type": "tool"}], "") == [
        {"name": "gpu", "type": "tool"}
    ]


def test_rescue_known_entities_does_not_mutate_its_input():
    given = [{"name": "docker", "type": "tool"}]
    _rescue_known_entities(given, "the stack is docker-compose only")
    assert given == [{"name": "docker", "type": "tool"}]


# ── _rescue_happened_on ──────────────────────────────────────────────
#
# _filter_noise strips an ISO date as a value literal, which orphans a
# correct HAPPENED_ON edge; the model also drops the relation outright more
# often than any other.


def test_rescue_happened_on_re_adds_a_date_an_existing_edge_points_at():
    content = "The Helios migration completed on 2026-04-09."
    entities, relations = _rescue_happened_on(
        [{"name": "Helios migration", "type": "event"}],
        [{"source": "Helios migration", "target": "2026-04-09", "type": "HAPPENED_ON"}],
        content,
    )
    assert "2026-04-09" in _names(entities)
    assert len(relations) == 1


def test_rescue_happened_on_anchors_an_unlinked_date_to_the_nearest_subject():
    content = "The Helios migration completed on 2026-04-09."
    entities, relations = _rescue_happened_on(
        [{"name": "Helios migration", "type": "event"}], [], content
    )
    assert "2026-04-09" in _names(entities)
    assert (relations[0]["source"], relations[0]["type"], relations[0]["target"]) == (
        "Helios migration", "HAPPENED_ON", "2026-04-09",
    )


def test_rescue_happened_on_anchors_to_the_preceding_subject_not_a_later_one():
    content = "The Helios migration completed on 2026-04-09; Kafka came later."
    _, relations = _rescue_happened_on(
        [
            {"name": "Helios migration", "type": "event"},
            {"name": "Kafka", "type": "service"},
        ],
        [],
        content,
    )
    assert [r["source"] for r in relations] == ["Helios migration"]


def test_rescue_happened_on_declines_when_no_anchor_is_in_range():
    # 90 characters is the reach; beyond it the date has no owner and stays a
    # dangling value node that _drop_unlinked_dates removes.
    content = "The Helios migration shipped. " + "filler text " * 10 + "on 2026-04-09."
    entities, relations = _rescue_happened_on(
        [{"name": "Helios migration", "type": "event"}], [], content
    )
    assert relations == []
    assert "2026-04-09" not in _names(entities)


def test_rescue_happened_on_does_not_relink_a_date_that_already_has_an_edge():
    content = "The Helios migration completed on 2026-04-09."
    _, relations = _rescue_happened_on(
        [
            {"name": "Helios migration", "type": "event"},
            {"name": "2026-04-09", "type": "concept"},
        ],
        [{"source": "Helios migration", "target": "2026-04-09", "type": "HAPPENED_ON"}],
        content,
    )
    assert len(relations) == 1


def test_rescue_happened_on_is_a_noop_without_a_date():
    entities = [{"name": "Helios migration", "type": "event"}]
    assert _rescue_happened_on(entities, [], "the migration finished") == (entities, [])


def test_an_iso_date_survives_the_whole_chain_as_a_happened_on_target():
    raw = {
        "entities": [
            {"name": "Helios migration", "type": "event"},
            {"name": "2026-04-09", "type": "concept"},
        ],
        "relationships": [
            {"source": "Helios migration", "target": "2026-04-09", "type": "HAPPENED_ON"},
        ],
    }
    out = clean_extraction(raw, "The Helios migration completed on 2026-04-09.")
    assert "2026-04-09" in _names(out["entities"])
    assert ("Helios migration", "HAPPENED_ON", "2026-04-09") in {
        (r["source"], r["type"], r["target"]) for r in out["relationships"]
    }


# ── The ordered stage ────────────────────────────────────────────────


def test_stage_two_runs_the_four_rescue_steps_in_doc_06_s2_order():
    rescue = [p.name for p in PASS_REGISTRY if p.stage == STAGE_ENTITY_RESCUE]
    assert rescue == [
        "rescue_relation_endpoints",
        "rescue_known_entities",
        "rescue_file_path_entities",
        "rescue_happened_on",
    ]


def test_stage_two_follows_stage_one():
    stages = [p.stage for p in PASS_REGISTRY]
    assert stages.index(STAGE_ENTITY_RESCUE) == stages.index(STAGE_ENTITY_SHAPING) + len(
        [p for p in PASS_REGISTRY if p.stage == STAGE_ENTITY_SHAPING]
    )


def test_every_rescue_runs_after_the_local_dedup():
    # Doc 06 §4's first load-bearing ordering. It bites through dedup's
    # whitespace-collapse equality, not through a substring rule (T1.24a).
    dedup = index_of(PASS_REGISTRY, "dedup_entities")
    assert all(
        i > dedup
        for i, p in enumerate(PASS_REGISTRY)
        if p.stage == STAGE_ENTITY_RESCUE
    )


def test_the_endpoint_rescue_runs_before_the_remap_it_exists_to_survive():
    assert index_of(PASS_REGISTRY, "rescue_relation_endpoints") < index_of(
        PASS_REGISTRY, "remap_to_valid_entities"
    )


def test_both_endpoint_orderings_are_declared_constraints_not_conventions():
    declared = {
        (c.earlier, c.later)
        for c in ORDERING_CONSTRAINTS
        if isinstance(c, RunsBefore)
    }
    assert ("dedup_entities", "rescue_relation_endpoints") in declared
    assert ("rescue_relation_endpoints", "remap_to_valid_entities") in declared


def test_stage_two_rescues_a_realistic_batch_end_to_end():
    content = (
        "The web app and the CLI authenticate through Auth0. "
        "The rollout landed on 2026-04-09 and the notes live in "
        "docs/release/notes.md. We build without CUDA."
    )
    state = CleanState(
        content=content,
        entities=[
            {"name": "Auth0", "type": "service"},
            {"name": "rollout", "type": "event"},
        ],
        relationships=[
            {"source": "web app", "target": "Auth0", "type": "USES"},
            {"source": "CLI", "target": "Auth0", "type": "USES"},
        ],
    )
    rescue = tuple(p for p in PASS_REGISTRY if p.stage == STAGE_ENTITY_RESCUE)
    out = run_passes(rescue, state)

    assert _types(out.entities) == {
        "Auth0": "service",
        "rollout": "event",
        "web app": "artifact",
        "CLI": "artifact",
        "docs/release/notes.md": "artifact",
        "2026-04-09": "concept",
    }
    assert ("rollout", "HAPPENED_ON", "2026-04-09") in {
        (r["source"], r["type"], r["target"]) for r in out.relationships
    }
