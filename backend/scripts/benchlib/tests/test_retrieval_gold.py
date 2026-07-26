"""Pure-parsing validation of the retrieval gold set (no bench DB opt-in).

The machine-checkable half of the gold's trust story: shape, the closed set
of seven slices, the documented per-slice counts, the >= 100 floor, and that
every relevant_memory_ids entry resolves to a corpus-declared memory. The
DB-backed determinism half lives in test_retrieval_seed.py.
"""
import json

import pytest

from benchlib import retrieval_gold
from benchlib.retrieval_gold import (
    CAPABILITY_SLICES,
    QUERY_TYPE_SLICES,
    SLICES,
    load_retrieval_corpus,
    load_retrieval_gold,
    validate_gold_against_corpus,
)

# The documented claim (SLICES.md + gold.json's declared_slice_counts). A
# contributor appending pairs updates all three together -- a silent
# re-tagging or a drifted count shows up as a failure here.
DOCUMENTED_COUNTS = {
    "exact": 12,
    "paraphrase": 18,
    "typo": 14,
    "fact": 18,
    "multi-hop": 14,
    "temporal": 12,
    "knowledge-update": 14,
}


@pytest.fixture(scope="module")
def corpus():
    return load_retrieval_corpus()


@pytest.fixture(scope="module")
def gold():
    return load_retrieval_gold()


def test_the_seven_slices_are_exactly_the_doc_17_ones():
    assert QUERY_TYPE_SLICES == {"exact", "paraphrase", "typo", "fact"}
    assert CAPABILITY_SLICES == {"multi-hop", "temporal", "knowledge-update"}
    assert SLICES == QUERY_TYPE_SLICES | CAPABILITY_SLICES


CURRENT_ANCHORED = {
    "rg-0078", "rg-0080", "rg-0082", "rg-0083", "rg-0086", "rg-0088",
    "rg-0089", "rg-0090", "rg-0091", "rg-0092", "rg-0093", "rg-0094",
    "rg-0095", "rg-0096", "rg-0097", "rg-0098", "rg-0101", "rg-0103",
}
WHOLE_GROUP_ANCHORED = {"rg-0100", "rg-0102"}


def test_gold_loads_and_declares_version_and_counts(gold):
    assert gold["version"] == 2
    assert gold["declared_slice_counts"] == DOCUMENTED_COUNTS


def test_per_slice_counts_match_the_documentation(gold):
    computed: dict[str, int] = {s: 0 for s in SLICES}
    for pair in gold["pairs"]:
        if not pair.get("retired"):
            computed[pair["slice_tags"][0]] += 1
    assert computed == DOCUMENTED_COUNTS


def test_total_meets_the_doc_17_floor(gold):
    live = [p for p in gold["pairs"] if not p.get("retired")]
    assert len(live) >= 100
    assert sum(DOCUMENTED_COUNTS.values()) == len(live)


def test_every_slice_tag_is_one_of_the_seven(gold):
    for pair in gold["pairs"]:
        assert len(pair["slice_tags"]) == 1
        assert pair["slice_tags"][0] in SLICES


def test_no_slice_is_empty(gold):
    tagged = {p["slice_tags"][0] for p in gold["pairs"] if not p.get("retired")}
    assert tagged == SLICES


def test_every_relevant_id_resolves_to_a_declared_memory(gold, corpus):
    validate_gold_against_corpus(gold, corpus)


def test_a_dangling_relevant_id_is_rejected(gold, corpus):
    broken = json.loads(json.dumps(gold))
    broken["pairs"][0]["relevant_memory_ids"] = [
        "00000000-0000-4000-8000-000000000000"
    ]
    with pytest.raises(ValueError, match="not declared"):
        validate_gold_against_corpus(broken, corpus)


def test_corpus_ids_and_keys_are_unique_uuids(corpus):
    import uuid

    ids = [uuid.UUID(str(e["memory_id"])) for e in corpus]
    keys = [e["key"] for e in corpus]
    assert len(set(ids)) == len(corpus)
    assert len(set(keys)) == len(corpus)


def test_every_corpus_id_derives_from_its_key(corpus):
    for entry in corpus:
        assert entry["memory_id"] == retrieval_gold.memory_id_for_key(entry["key"])


def test_loader_rejects_an_id_that_does_not_derive_from_its_key(tmp_path, corpus):
    broken = {"memories": json.loads(json.dumps(corpus))}
    broken["memories"][0]["memory_id"] = "00000000-0000-4000-8000-000000000000"
    path = tmp_path / "corpus.json"
    path.write_text(json.dumps(broken), encoding="utf-8")
    with pytest.raises(ValueError, match="does not derive"):
        load_retrieval_corpus(path)


def test_every_corpus_entry_declares_a_created_at(corpus):
    from datetime import datetime

    for entry in corpus:
        parsed = datetime.fromisoformat(entry["created_at"])
        assert parsed.tzinfo is not None


def test_pair_ids_are_unique_and_appended_in_order(gold):
    ids = [p["id"] for p in gold["pairs"]]
    assert len(set(ids)) == len(ids)
    assert ids == sorted(ids)


def test_queries_are_nonempty_and_unique_among_live_pairs(gold):
    # A retired pair keeps its content forever, and its replacement may
    # legitimately reuse the query (rg-0099 -> rg-0103), so uniqueness is
    # asserted over the live set only.
    assert all(p["query"].strip() for p in gold["pairs"])
    live = [p["query"] for p in gold["pairs"] if not p.get("retired")]
    assert len(set(live)) == len(live)


def test_multi_hop_pairs_need_at_least_two_memories(gold):
    for pair in gold["pairs"]:
        if pair["slice_tags"][0] == "multi-hop" and not pair.get("retired"):
            assert len(pair["relevant_memory_ids"]) >= 2


def test_anchor_flags_match_the_adjudicated_sets(gold):
    """Pins which pairs are group-anchored, so silently dropping a flag (and
    with it the staleness guard) is as visible as dropping a pair."""
    current = {p["id"] for p in gold["pairs"]
               if p.get("anchor") == "current" and not p.get("retired")}
    whole = {p["id"] for p in gold["pairs"]
             if p.get("anchor") == "whole-group" and not p.get("retired")}
    assert current == CURRENT_ANCHORED
    assert whole == WHOLE_GROUP_ANCHORED


def test_appending_a_newer_snapshot_fails_latest_anchored_pairs(gold, corpus):
    """The trap Important-3 exists for: a contributor appends a t2d "pool at
    91%" memory and every latest-anchored pair over t2 must fail validation
    instead of silently marking the stale snapshot relevant."""
    grown = json.loads(json.dumps(corpus))
    grown.append({
        "key": "t2d-pool-91",
        "memory_id": retrieval_gold.memory_id_for_key("t2d-pool-91"),
        "content": "The storage pool has reached 91% capacity.",
        "memory_type": "fact",
        "source": "bench",
        "created_at": "2026-07-01T00:00:00+00:00",
        "project": "default",
        "group": "t2",
    })
    with pytest.raises(ValueError, match="rg-0080.*retire-and-replace"):
        validate_gold_against_corpus(gold, grown)


def test_appending_a_definitive_update_fails_present_state_pairs(gold, corpus):
    """A definitive u6c replacement makes u6a stale truth: the speculative
    trap's present-state pair must fail, not keep scoring u6a as gold."""
    grown = json.loads(json.dumps(corpus))
    grown.append({
        "key": "u6c-metrics-vector",
        "memory_id": retrieval_gold.memory_id_for_key("u6c-metrics-vector"),
        "content": "Metrics collection moved from Telegraf to Vector; the bake-off is over.",
        "memory_type": "decision",
        "source": "bench",
        "created_at": "2026-06-20T00:00:00+00:00",
        "project": "default",
        "group": "u6",
    })
    with pytest.raises(ValueError, match="rg-010[03].*retire-and-replace"):
        validate_gold_against_corpus(gold, grown)


def test_a_newer_speculative_sibling_does_not_stale_current_anchors(gold, corpus):
    """The 'current' rule is newest NON-speculative: another rumour about a
    switch does not displace the standing truth, so validation stays green
    for 'current' pairs -- only the whole-group change-status pairs demand
    re-adjudication when the group grows."""
    grown = json.loads(json.dumps(corpus))
    grown.append({
        "key": "u7c-forgejo-still-maybe",
        "memory_id": retrieval_gold.memory_id_for_key("u7c-forgejo-still-maybe"),
        "content": "Still weighing the Forgejo switch; no decision yet.",
        "memory_type": "decision",
        "source": "bench",
        "created_at": "2026-07-01T00:00:00+00:00",
        "project": "default",
        "group": "u7",
        "speculative": True,
    })
    with pytest.raises(ValueError, match="rg-0102.*whole-group"):
        validate_gold_against_corpus(gold, grown)


def test_corpus_loader_rejects_a_group_with_duplicate_dates(tmp_path, corpus):
    broken = json.loads(json.dumps(corpus))
    t2 = [e for e in broken if e.get("group") == "t2"]
    t2[1]["created_at"] = t2[0]["created_at"]
    path = tmp_path / "corpus.json"
    path.write_text(json.dumps({"memories": broken}), encoding="utf-8")
    with pytest.raises(ValueError, match="ill-defined"):
        load_retrieval_corpus(path)


def test_corpus_loader_rejects_a_single_member_group(tmp_path, corpus):
    broken = json.loads(json.dumps(corpus))
    for entry in broken:
        if entry["key"] == "t2c-pool-83":
            entry["group"] = "t9"
    path = tmp_path / "corpus.json"
    path.write_text(json.dumps({"memories": broken}), encoding="utf-8")
    with pytest.raises(ValueError, match="single member"):
        load_retrieval_corpus(path)


def test_gold_loader_rejects_an_unknown_anchor(tmp_path, gold):
    broken = json.loads(json.dumps(gold))
    broken["pairs"][0]["anchor"] = "newest"
    path = tmp_path / "gold.json"
    path.write_text(json.dumps(broken), encoding="utf-8")
    with pytest.raises(ValueError, match="unknown anchor"):
        load_retrieval_gold(path)


def test_loader_rejects_an_untabled_slice_tag(tmp_path, gold):
    broken = json.loads(json.dumps(gold))
    broken["pairs"][0]["slice_tags"] = ["vibes"]
    path = tmp_path / "gold.json"
    path.write_text(json.dumps(broken), encoding="utf-8")
    with pytest.raises(ValueError, match="untabled slice tag"):
        load_retrieval_gold(path)


def test_loader_rejects_declared_counts_that_drift(tmp_path, gold):
    broken = json.loads(json.dumps(gold))
    broken["declared_slice_counts"]["exact"] += 1
    path = tmp_path / "gold.json"
    path.write_text(json.dumps(broken), encoding="utf-8")
    with pytest.raises(ValueError, match="disagree"):
        load_retrieval_gold(path)


def test_loader_rejects_out_of_order_pair_ids(tmp_path, gold):
    broken = json.loads(json.dumps(gold))
    broken["pairs"][0], broken["pairs"][1] = broken["pairs"][1], broken["pairs"][0]
    path = tmp_path / "gold.json"
    path.write_text(json.dumps(broken), encoding="utf-8")
    with pytest.raises(ValueError, match="ascending order"):
        load_retrieval_gold(path)


def test_loader_rejects_a_single_memory_multi_hop_pair(tmp_path, gold):
    broken = json.loads(json.dumps(gold))
    for pair in broken["pairs"]:
        if pair["slice_tags"][0] == "multi-hop":
            pair["relevant_memory_ids"] = pair["relevant_memory_ids"][:1]
            break
    path = tmp_path / "gold.json"
    path.write_text(json.dumps(broken), encoding="utf-8")
    with pytest.raises(ValueError, match="multi-hop"):
        load_retrieval_gold(path)


def test_a_retired_pair_leaves_counts_untouched_but_stays_in_the_file(tmp_path, gold):
    """The append-only discipline: retiring excludes a pair from the counts
    without deleting it, so the declared counts drop by one and the file
    still carries the entry."""
    doc = json.loads(json.dumps(gold))
    victim = doc["pairs"][0]
    victim["retired"] = True
    tag = victim["slice_tags"][0]
    doc["declared_slice_counts"][tag] -= 1
    path = tmp_path / "gold.json"
    path.write_text(json.dumps(doc), encoding="utf-8")

    reloaded = load_retrieval_gold(path)
    assert len(reloaded["pairs"]) == len(gold["pairs"])
    assert reloaded["declared_slice_counts"][tag] == DOCUMENTED_COUNTS[tag] - 1


def test_default_paths_point_inside_the_retrieval_dir():
    assert retrieval_gold.CORPUS_PATH.name == "corpus.json"
    assert retrieval_gold.GOLD_PATH.name == "gold.json"
    assert retrieval_gold.CORPUS_PATH.parent == retrieval_gold.RETRIEVAL_DIR
