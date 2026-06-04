"""Tests for the clean_extraction guards added after the 2026-06-04 round-3 eval.

Each guard fixes a confirmed defect where ``clean_extraction`` either destroyed
correct LLM output or let a hallucination/false edge through:

* Fix A — suffix-stripping must not collapse a real entity into a NOISE word
  ('auth module' -> 'auth' -> dropped, orphaning its edges).
* Fix B — a dotted config-key stem ('producer' from 'producer.linger.ms') is
  not an entity, but a single-dot module root ('asyncio') still is.
* Fix C — ambiguous short tokens (the verb 'go') are not auto-rescued from prose.
* Fix D — value-fidelity: a multi-word phrase or date not grounded in the text
  is a fabrication and is dropped.
* Fix E — a REPLACES edge must be backed by a replacement/migration verb.
"""
from __future__ import annotations

from app.services.extraction import (
    _drop_unlinked_dates,
    _filter_event_edges,
    _filter_hallucinated_names,
    _filter_literals,
    _filter_noise,
    _gate_replaces_requires_verb,
    _normalize_names,
    _rescue_known_entities,
    clean_extraction,
)


def _names(entities: list[dict]) -> set[str]:
    return {(e.get("name") or "").strip().lower() for e in entities}


def _has(rels: list[dict], src: str, tgt: str, rtype: str) -> bool:
    return any(
        (r.get("source") or "").strip().lower() == src.lower()
        and (r.get("target") or "").strip().lower() == tgt.lower()
        and r.get("type") == rtype
        for r in rels
    )


# --- Fix A: suffix-strip must not produce a noise word --------------------


def test_suffix_strip_keeps_entity_when_head_is_noise():
    # 'auth module' -> trailing 'module' strip -> 'auth' (a NOISE word) would be
    # deleted by _filter_noise. The guard keeps the fuller name instead.
    out = _filter_noise(_normalize_names([{"name": "auth module", "type": "artifact"}]))
    assert "auth module" in _names(out)


def test_suffix_strip_still_collapses_canonical_head():
    # A non-noise head still collapses ('postgres server' -> 'postgres'); 'server'
    # is in _TRAILING_SUFFIXES and 'postgres' is neither noise nor too short.
    out = _normalize_names([{"name": "postgres server", "type": "database"}])
    assert "postgres" in _names(out)


def test_clean_extraction_preserves_auth_module_edges():
    raw = {
        "entities": [
            {"name": "auth module", "type": "artifact"},
            {"name": "RFC 7519", "type": "paper"},
            {"name": "Go", "type": "language"},
            {"name": "Marcus Lee", "type": "person"},
        ],
        "relationships": [
            {"source": "auth module", "target": "RFC 7519", "type": "IMPLEMENTS"},
            {"source": "auth module", "target": "Go", "type": "USES"},
            {"source": "auth module", "target": "Marcus Lee", "type": "AUTHORED_BY"},
        ],
    }
    content = "Marcus Lee shipped the auth module written in Go; it follows RFC 7519 for tokens."
    out = clean_extraction(raw, content, relation_rescue=True)
    assert "auth module" in _names(out["entities"])
    assert _has(out["relationships"], "auth module", "rfc 7519", "IMPLEMENTS")


# --- Fix B: dotted config-key stem -----------------------------------------


def test_dotted_config_stem_dropped():
    content = "Set producer.linger.ms to 50 before load testing."
    out = _filter_literals([{"name": "producer", "type": "concept"}], content)
    assert "producer" not in _names(out)


def test_single_dot_module_root_kept():
    content = "We call asyncio.create_task to schedule the worker."
    out = _filter_literals([{"name": "asyncio", "type": "tool"}], content)
    assert "asyncio" in _names(out)


# --- Fix C: ambiguous short tokens not auto-rescued ------------------------


def test_go_verb_not_rescued():
    out = _rescue_known_entities([], "all writes now go through the event bus")
    assert "go" not in _names(out)


def test_real_known_tool_still_rescued():
    out = _rescue_known_entities([], "we deploy the app with docker behind nginx")
    assert {"docker", "nginx"} & _names(out)


def test_go_language_kept_when_llm_emits_it():
    # The skip only suppresses rescue; an explicit LLM 'Go' mention survives.
    out = clean_extraction(
        {"entities": [{"name": "Go", "type": "language"}], "relationships": []},
        "The service is written in Go.",
    )
    assert "go" in _names(out["entities"])


# --- Fix D: value-fidelity -------------------------------------------------


def test_multiword_phrase_with_absent_token_dropped():
    content = "After the February outage, the gateway dropped requests."
    out = _filter_hallucinated_names(
        [{"name": "march outage", "type": "event"}, {"name": "february outage", "type": "event"}],
        content,
    )
    assert "march outage" not in _names(out)
    assert "february outage" in _names(out)


def test_hallucinated_date_dropped_real_date_kept():
    content = "Marcus shipped the module on 2026-05-20."
    out = _filter_hallucinated_names(
        [{"name": "2026-05-12", "type": "concept"}, {"name": "2026-05-20", "type": "concept"}],
        content,
    )
    assert "2026-05-12" not in _names(out)
    assert "2026-05-20" in _names(out)


def test_single_token_canonical_shortform_not_policed():
    # 'postgres' from 'PostgreSQL' is a single token -> never value-fidelity-dropped.
    out = _filter_hallucinated_names([{"name": "postgres", "type": "database"}], "We run PostgreSQL.")
    assert "postgres" in _names(out)


# --- Fix E: REPLACES requires a replacement verb ---------------------------


def test_replaces_without_verb_downgraded():
    rels = [{"source": "event bus", "target": "legacy ledger", "type": "REPLACES"}]
    out = _gate_replaces_requires_verb(rels, "all writes now go through the event bus")
    assert out[0]["type"] == "RELATED_TO"


def test_replaces_with_migration_verb_kept():
    rels = [{"source": "nats", "target": "rabbitmq", "type": "REPLACES"}]
    out = _gate_replaces_requires_verb(rels, "we migrated the queue from rabbitmq to nats")
    assert out[0]["type"] == "REPLACES"


def test_replaces_with_improves_phrasing_kept():
    rels = [{"source": "event bus", "target": "legacy ledger", "type": "REPLACES"}]
    out = _gate_replaces_requires_verb(rels, "the event bus improves on the legacy ledger")
    assert out[0]["type"] == "REPLACES"


# --- Event-edge guard: events are passive temporal nodes ------------------


def _ents_with_event(name="january incident"):
    return [
        {"name": name, "type": "event"},
        {"name": "primary database", "type": "database"},
        {"name": "memory leak", "type": "concept"},
        {"name": "2026-03-15", "type": "concept"},
    ]


def test_event_forbidden_structural_edges_dropped():
    ents = _ents_with_event()
    rels = [
        {"source": "january incident", "type": "DEPLOYED_ON", "target": "primary database"},
        {"source": "january incident", "type": "USES", "target": "primary database"},
    ]
    out = _filter_event_edges(rels, ents)
    assert out == []


def test_event_legal_edges_kept():
    ents = _ents_with_event()
    rels = [
        {"source": "memory leak", "type": "CAUSES", "target": "january incident"},
        {"source": "january incident", "type": "HAPPENED_ON", "target": "2026-03-15"},
    ]
    out = _filter_event_edges(rels, ents)
    assert len(out) == 2


def test_event_guard_leaves_non_event_edges_untouched():
    ents = [{"name": "redis", "type": "database"}, {"name": "api", "type": "service"}]
    rels = [{"source": "api", "type": "DEPENDS_ON", "target": "redis"}]
    out = _filter_event_edges(rels, ents)
    assert out == rels


def test_event_guard_noop_without_events():
    rels = [{"source": "a", "type": "USES", "target": "b"}]
    assert _filter_event_edges(rels, [{"name": "a", "type": "service"}]) == rels


# --- Dangling-date guard: a date with no HAPPENED_ON edge is dropped -------


def test_unlinked_date_entity_dropped():
    ents = [{"name": "2026-03-15", "type": "concept"}, {"name": "darkmem", "type": "project"}]
    out = _drop_unlinked_dates(ents, relationships=[])
    assert "2026-03-15" not in _names(out)
    assert "darkmem" in _names(out)


def test_date_with_happened_on_edge_kept():
    ents = [{"name": "2026-03-15", "type": "concept"}, {"name": "phoenix v2", "type": "artifact"}]
    rels = [{"source": "phoenix v2", "type": "HAPPENED_ON", "target": "2026-03-15"}]
    out = _drop_unlinked_dates(ents, rels)
    assert {"2026-03-15", "phoenix v2"} <= _names(out)
