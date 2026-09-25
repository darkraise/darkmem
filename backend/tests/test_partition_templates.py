"""The ten per-fingerprint parents exist as registry entries, not as DDL.

Inventory §6: doc 19 §2 rejects expressing child tables as static migrations
because their shape is parameterised by fingerprint. The four target-new
families land here as templates; T0.13 labels them inert and T0.14's
boot-time reconciliation creates them per registered fingerprint. Three are
still inert — ``triple_embeddings`` gained its writer in T2.33 — but the
template contract below is the same either way.
"""
from __future__ import annotations

from pathlib import Path

from app.services.embedder_registry import _AUX_INDEXES, _TABLE_TEMPLATES

EXPECTED_PARENTS = {
    "memory_embeddings",
    "entity_embeddings",
    "code_chunk_embeddings",
    "entity_embedding_cache",
    "block_embeddings",
    "page_embeddings",
    "relation_embeddings",
    "article_embeddings",
    "triple_embeddings",
    "worklog_embeddings",
}


def test_every_parent_has_a_template():
    assert set(_TABLE_TEMPLATES) == EXPECTED_PARENTS


def test_every_template_has_aux_indexes():
    assert set(_AUX_INDEXES) == EXPECTED_PARENTS


def test_every_template_is_parameterised_plain_sql():
    for parent, tmpl in _TABLE_TEMPLATES.items():
        assert "{name}" in tmpl, parent
        assert "{dims}" in tmpl, parent
        assert tmpl.lstrip().upper().startswith("CREATE TABLE IF NOT EXISTS"), parent


def test_triple_embeddings_does_not_cascade():
    # Facts are invalidate-not-delete (doc 04 §5.3/§8.3): a cascade would
    # destroy the history the fact layer exists to keep.
    tmpl = _TABLE_TEMPLATES["triple_embeddings"]
    assert "knowledge_triples(id)" in tmpl
    assert "ON DELETE CASCADE" not in tmpl


def test_relation_embeddings_cascades_on_the_real_relation_id():
    # No synthetic ids: strip-before-rewrite must kill the vector with the
    # relation rather than orphan it (doc 04 §5.3).
    tmpl = _TABLE_TEMPLATES["relation_embeddings"]
    assert "entity_relations(id) ON DELETE CASCADE" in tmpl


def test_no_migration_creates_a_child_table():
    root = Path(__file__).resolve().parent.parent / "migrations"
    for path in root.rglob("*.py"):
        src = path.read_text()
        for parent in EXPECTED_PARENTS:
            assert f"CREATE TABLE {parent}__" not in src
            assert f"CREATE TABLE IF NOT EXISTS {parent}__" not in src


def test_worklog_embeddings_cascades_on_the_entry_and_carries_its_project():
    # Purge and retention delete entries; the vectors must go with them, and
    # search filters one project's vectors through the project column.
    tmpl = _TABLE_TEMPLATES["worklog_embeddings"]
    assert "worklog_entries(id) ON DELETE CASCADE" in tmpl
    assert "project TEXT NOT NULL" in tmpl
