"""Test corpus loader."""
import json
import pytest
from pathlib import Path
from benchlib.corpus import load_corpus, load_expectations


# Use a temporary directory for test JSON files
@pytest.fixture
def corpus_dir(tmp_path):
    """Provide a temporary directory for corpus JSON files."""
    return tmp_path


def test_load_smoke_corpus(corpus_dir):
    """Load smoke corpus with simple structure."""
    smoke_json = corpus_dir / "smoke.json"
    smoke_data = {
        "memories": [
            {
                "content": "Darkmem stores memories in Postgres with pgvector for semantic search.",
                "source": "bench",
                "memory_type": "fact",
                "created_at": "2026-01-02T00:00:00+00:00",
            },
            {
                "content": "The ingestion pipeline runs five phases ending in a write step.",
                "source": "bench",
                "memory_type": "fact",
                "created_at": "2026-01-03T00:00:00+00:00",
            },
            {
                "content": "Retrieval fuses vector and full-text search with Reciprocal Rank Fusion.",
                "source": "bench",
                "memory_type": "fact",
                "created_at": "2026-01-04T00:00:00+00:00",
            },
        ]
    }
    smoke_json.write_text(json.dumps(smoke_data, indent=2))

    entries = load_corpus(smoke_json)
    assert len(entries) == 3
    assert all("content" in e for e in entries)
    assert entries[0]["content"] == "Darkmem stores memories in Postgres with pgvector for semantic search."


def test_load_gold_corpus(corpus_dir):
    """Load gold corpus with complex structure including entities and relations."""
    gold_json = corpus_dir / "gold.json"
    gold_data = {
        "_notes": "Test gold annotations",
        "memories": [
            {
                "id": "e1",
                "content": "We migrated the search backend from Elasticsearch to Meilisearch.",
                "hint": "decision",
                "entities": [
                    {"name": "elasticsearch", "type": "database"},
                    {"name": "meilisearch", "type": "database"},
                ],
                "relations": [
                    {"source": "meilisearch", "type": "REPLACES", "target": "elasticsearch"}
                ],
            },
            {
                "id": "e8",
                "content": "We upgraded to Phoenix v2 after the March outage.",
                "hint": "milestone",
                "entities": [
                    {"name": "phoenix v2", "type": "service"},
                    {"name": "march outage", "type": "event"},
                ],
                "relations": [],  # Empty relations list is valid
            },
        ],
    }
    gold_json.write_text(json.dumps(gold_data, indent=2))

    entries = load_corpus(gold_json)
    assert len(entries) == 2
    assert entries[0]["id"] == "e1"
    assert entries[1]["relations"] == []


def test_missing_content_error(corpus_dir):
    """Reject entry missing content field with index in error message."""
    bad_json = corpus_dir / "bad.json"
    bad_data = {
        "memories": [
            {"source": "bench", "memory_type": "fact"},  # Missing content at index 0
            {"content": "Valid entry", "source": "bench", "memory_type": "fact"},
        ]
    }
    bad_json.write_text(json.dumps(bad_data, indent=2))

    with pytest.raises(ValueError, match="entry 0.*content"):
        load_corpus(bad_json)


def test_invalid_entity_type_error(corpus_dir):
    """Reject entry with untabled entity type."""
    bad_json = corpus_dir / "bad_entity.json"
    bad_data = {
        "_notes": "Test",
        "memories": [
            {
                "id": "e1",
                "content": "Some content",
                "hint": "fact",
                "entities": [
                    {"name": "something", "type": "invalid_entity_type"}  # Untabled type
                ],
                "relations": [],
            }
        ],
    }
    bad_json.write_text(json.dumps(bad_data, indent=2))

    with pytest.raises(ValueError, match="entry 0.*invalid_entity_type"):
        load_corpus(bad_json)


def test_invalid_relation_type_error(corpus_dir):
    """Reject entry with untabled relation type."""
    bad_json = corpus_dir / "bad_relation.json"
    bad_data = {
        "_notes": "Test",
        "memories": [
            {
                "id": "e1",
                "content": "Some content",
                "hint": "fact",
                "entities": [
                    {"name": "a", "type": "tool"},
                    {"name": "b", "type": "tool"},
                ],
                "relations": [
                    {"source": "a", "type": "INVALID_RELATION", "target": "b"}  # Untabled type
                ],
            }
        ],
    }
    bad_json.write_text(json.dumps(bad_data, indent=2))

    with pytest.raises(ValueError, match="entry 0.*INVALID_RELATION"):
        load_corpus(bad_json)


def test_legacy_entity_type_rejected(corpus_dir):
    """Reject legacy entity type aliases like 'framework' in gold data."""
    bad_json = corpus_dir / "legacy_entity.json"
    bad_data = {
        "_notes": "Test",
        "memories": [
            {
                "id": "e1",
                "content": "Some content",
                "hint": "fact",
                "entities": [
                    {"name": "something", "type": "framework"}  # Legacy alias, not current
                ],
                "relations": [],
            }
        ],
    }
    bad_json.write_text(json.dumps(bad_data, indent=2))

    with pytest.raises(ValueError, match="entry 0.*framework"):
        load_corpus(bad_json)


def test_legacy_relation_type_rejected(corpus_dir):
    """Reject legacy relation type aliases in gold data."""
    bad_json = corpus_dir / "legacy_relation.json"
    bad_data = {
        "_notes": "Test",
        "memories": [
            {
                "id": "e1",
                "content": "Some content",
                "hint": "fact",
                "entities": [
                    {"name": "a", "type": "tool"},
                    {"name": "b", "type": "tool"},
                ],
                "relations": [
                    {"source": "a", "type": "RUNS_ON", "target": "b"}  # Legacy alias
                ],
            }
        ],
    }
    bad_json.write_text(json.dumps(bad_data, indent=2))

    with pytest.raises(ValueError, match="entry 0.*RUNS_ON"):
        load_corpus(bad_json)


def test_no_entities_no_relations_valid(corpus_dir):
    """Entry with no gold labels (no entities/relations) is valid."""
    json_file = corpus_dir / "no_labels.json"
    data = {
        "memories": [
            {
                "content": "Just content, no entities or relations",
                "source": "bench",
                "memory_type": "fact",
            }
        ]
    }
    json_file.write_text(json.dumps(data, indent=2))

    entries = load_corpus(json_file)
    assert len(entries) == 1
    assert entries[0]["content"] == "Just content, no entities or relations"


def test_load_real_smoke_corpus():
    """Load the actual smoke corpus file."""
    test_dir = Path(__file__).parent.parent
    smoke_path = test_dir / "smoke" / "corpus.json"

    entries = load_corpus(smoke_path)
    assert len(entries) == 3
    assert all("content" in e for e in entries)


def test_load_real_gold_corpus():
    """Load the actual gold corpus file."""
    test_dir = Path(__file__).parent.parent
    gold_path = test_dir.parent / "extraction_bench" / "gold.json"

    entries = load_corpus(gold_path)
    assert len(entries) == 26


def test_load_real_gold_heldout_corpus():
    """Load the actual gold heldout corpus file."""
    test_dir = Path(__file__).parent.parent
    gold_heldout_path = test_dir.parent / "extraction_bench" / "gold_heldout.json"

    entries = load_corpus(gold_heldout_path)
    assert len(entries) == 10


def test_a_typoed_memories_key_is_a_load_error_not_an_empty_corpus(corpus_dir):
    """A merge accident that renames the key must not read as "a corpus of
    zero memories" -- every downstream count is then trivially satisfied by
    a run that ingested nothing."""
    typo_json = corpus_dir / "typo.json"
    typo_json.write_text(json.dumps({
        "memoires": [{"content": "Darkmem stores memories in Postgres."}]
    }))

    with pytest.raises(ValueError, match="no 'memories' key"):
        load_corpus(typo_json)


def test_untabled_memory_type_rejected(corpus_dir):
    """MEMORY_TYPES is closed too: an entry the pipeline would silently
    rewrite must fail the load instead."""
    bad_json = corpus_dir / "bad_memory_type.json"
    bad_json.write_text(json.dumps({
        "memories": [{"content": "Some content", "memory_type": "banana"}]
    }))

    with pytest.raises(ValueError, match="entry 0.*memory_type.*banana"):
        load_corpus(bad_json)


def test_legacy_memory_type_alias_rejected(corpus_dir):
    """`debug` is a LEGACY_MEMORY_TYPE_MAP alias that normalize_memory_type
    rewrites to `problem` on the way into the database. Accepting it would
    mean the bench DB no longer holds what the corpus declared."""
    bad_json = corpus_dir / "legacy_memory_type.json"
    bad_json.write_text(json.dumps({
        "memories": [{"content": "Some content", "memory_type": "debug"}]
    }))

    with pytest.raises(ValueError, match="entry 0.*memory_type.*debug"):
        load_corpus(bad_json)


def test_legacy_hint_alias_rejected(corpus_dir):
    """Gold's classification label goes through the same vocabulary:
    `design` loads clean while the pipeline stores `architecture`, which is
    an unavoidable gold-side miss for any scorer that string-matches."""
    bad_json = corpus_dir / "legacy_hint.json"
    bad_json.write_text(json.dumps({
        "_notes": "Test",
        "memories": [{"id": "e1", "content": "Some content", "hint": "design",
                      "entities": [], "relations": []}],
    }))

    with pytest.raises(ValueError, match="entry 0.*hint.*design"):
        load_corpus(bad_json)


def test_entry_without_memory_type_or_hint_is_valid(corpus_dir):
    json_file = corpus_dir / "no_type.json"
    json_file.write_text(json.dumps({"memories": [{"content": "Just content"}]}))

    assert len(load_corpus(json_file)) == 1


# ── declared expected-work counts ─────────────────────────────────────


def test_load_expectations_reads_the_declared_counts(corpus_dir):
    json_file = corpus_dir / "with_expected.json"
    json_file.write_text(json.dumps({
        "expected": {"memories": 3, "entities": 6, "relations": 3},
        "memories": [{"content": "Some content"}],
    }))

    assert load_expectations(json_file) == {"memories": 3, "entities": 6, "relations": 3}


def test_load_expectations_returns_none_for_a_corpus_without_them(corpus_dir):
    """Gold files carry no expectations; that is not a validation failure."""
    json_file = corpus_dir / "no_expected.json"
    json_file.write_text(json.dumps({"memories": [{"content": "Some content"}]}))

    assert load_expectations(json_file) is None


def test_load_expectations_rejects_an_unknown_key(corpus_dir):
    json_file = corpus_dir / "bad_expected_key.json"
    json_file.write_text(json.dumps({
        "expected": {"memoires": 3},
        "memories": [{"content": "Some content"}],
    }))

    with pytest.raises(ValueError, match="unknown 'expected' key"):
        load_expectations(json_file)


@pytest.mark.parametrize("value", [-1, "3", 3.5, True, None])
def test_load_expectations_rejects_a_non_count_value(corpus_dir, value):
    json_file = corpus_dir / "bad_expected_value.json"
    json_file.write_text(json.dumps({
        "expected": {"entities": value},
        "memories": [{"content": "Some content"}],
    }))

    with pytest.raises(ValueError, match="expected.entities"):
        load_expectations(json_file)


def test_the_real_gold_corpora_declare_no_expectations():
    bench_dir = Path(__file__).parent.parent.parent / "extraction_bench"
    assert load_expectations(bench_dir / "gold.json") is None
    assert load_expectations(bench_dir / "gold_heldout.json") is None


def test_the_real_smoke_corpus_declares_its_healthy_baseline():
    smoke_path = Path(__file__).parent.parent / "smoke" / "corpus.json"
    assert load_expectations(smoke_path) == {"memories": 3, "entities": 6, "relations": 3}
