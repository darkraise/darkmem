"""Tests for the relation-rescue regex layer in ``extraction._rescue_relations``.

Three pattern families need coverage because the regexes are subtle and
silently degrade if a future tweak breaks a clause boundary, distance
guard, or negation suppression. The orchestrator (``_rescue_relations``)
is the public entry point; we test it end-to-end with concrete sentences
and a small entity list.
"""
from __future__ import annotations

import pytest

from app.services.extraction import _rescue_relations


def _entities(*names: str) -> list[dict]:
    return [{"name": n, "type": "tool", "properties": {}} for n in names]


def _has(rels: list[dict], src: str, tgt: str, rtype: str) -> bool:
    src_l = src.strip().lower()
    tgt_l = tgt.strip().lower()
    return any(
        (r.get("source") or "").strip().lower() == src_l
        and (r.get("target") or "").strip().lower() == tgt_l
        and r.get("type") == rtype
        for r in rels
    )


# --- REPLACES pattern A: "<transition_verb> ... from X to Y" ---------------


@pytest.mark.parametrize(
    "content",
    [
        "We switched from Jenkins to GitHub Actions",
        "Migrated darkmem from Qdrant to pgvector",
        "Moved the worker from Celery to asyncio",
        "We transitioned from Promtail to Alloy",
    ],
)
def test_rescue_replaces_pattern_a_from_to(content):
    """Pattern A: any transition verb in the clause followed by 'from X to Y'
    should emit ``Y REPLACES X``."""
    if "Jenkins" in content:
        ents = _entities("Jenkins", "GitHub Actions")
        out = _rescue_relations(ents, [], content)
        assert _has(out, "GitHub Actions", "Jenkins", "REPLACES")
    elif "Qdrant" in content:
        ents = _entities("Qdrant", "pgvector", "darkmem")
        out = _rescue_relations(ents, [], content)
        assert _has(out, "pgvector", "Qdrant", "REPLACES")
    elif "Celery" in content:
        ents = _entities("Celery", "asyncio")
        out = _rescue_relations(ents, [], content)
        assert _has(out, "asyncio", "Celery", "REPLACES")
    else:
        ents = _entities("Promtail", "Alloy")
        out = _rescue_relations(ents, [], content)
        assert _has(out, "Alloy", "Promtail", "REPLACES")


# --- REPLACES pattern B: "<replace_verb> X (with|by|for|in favor of) Y" ----


@pytest.mark.parametrize(
    "content,src,tgt",
    [
        ("Replaced Celery with asyncio", "asyncio", "Celery"),
        ("Replaced the broker with NATS", "NATS", None),  # X not entity, skipped
        ("Swapped Promtail for Alloy", "Alloy", "Promtail"),
        ("Phased out Jenkins in favor of GitHub Actions", "GitHub Actions", "Jenkins"),
    ],
)
def test_rescue_replaces_pattern_b_verb_x_prep_y(content, src, tgt):
    """Pattern B: replace-verb governs 'X (with|by|for|in favor of) Y'."""
    if tgt is None:
        # X is not a named entity; pattern should not fire.
        ents = _entities("NATS")
        out = _rescue_relations(ents, [], content)
        assert not any(r.get("type") == "REPLACES" for r in out)
        return
    ents = _entities(src, tgt)
    out = _rescue_relations(ents, [], content)
    assert _has(out, src, tgt, "REPLACES")


# --- REPLACES pattern C: "Y replaces/supersedes/deprecates X" --------------


@pytest.mark.parametrize(
    "content,src,tgt",
    [
        ("alloy supersedes promtail in our stack", "alloy", "promtail"),
        ("pgvector deprecates qdrant for darkmem", "pgvector", "qdrant"),
        ("GitHub Actions replaces Jenkins for CI", "GitHub Actions", "Jenkins"),
    ],
)
def test_rescue_replaces_pattern_c_supersedes(content, src, tgt):
    ents = _entities(src, tgt)
    out = _rescue_relations(ents, [], content)
    assert _has(out, src, tgt, "REPLACES")


# --- REPLACES pattern D: "<verb> X out of A into B" ----------------------


@pytest.mark.parametrize(
    "content,a,b",
    [
        (
            "Seed data was moved out of migration 0001 into llm_seed.py",
            "migration 0001", "llm_seed.py",
        ),
        (
            "The provider list was extracted out of the SQL seed into services/seed.py",
            "SQL seed", "services/seed.py",
        ),
        (
            "We lifted the schema out of base.py into models.py",
            "base.py", "models.py",
        ),
    ],
)
def test_rescue_replaces_pattern_d_out_of_into(content, a, b):
    """Pattern D: relocation form 'moved out of A into B' -> B REPLACES A.
    Existing Pattern A only handles 'from X to Y'; refactor decision
    memories use 'out of … into …' instead, which Pattern D captures."""
    ents = _entities(a, b)
    out = _rescue_relations(ents, [], content)
    assert _has(out, b, a, "REPLACES"), (
        f"expected {b!r} REPLACES {a!r}; got {out}"
    )


def test_rescue_replaces_pattern_d_skips_when_endpoint_missing():
    """If only one endpoint is in the entity list, Pattern D emits nothing
    (consistent with Pattern A's 'both endpoints required' contract)."""
    ents = _entities("llm_seed.py")
    out = _rescue_relations(
        ents, [],
        "Seed data was moved out of migration 0001 into llm_seed.py",
    )
    assert not any(r.get("type") == "REPLACES" for r in out)


def test_rescue_replaces_pattern_d_negation_suppresses():
    """Clause-level negation guard applies to Pattern D too."""
    ents = _entities("migration 0001", "llm_seed.py")
    out = _rescue_relations(
        ents, [],
        "Seed data was not moved out of migration 0001 into llm_seed.py",
    )
    assert not any(r.get("type") == "REPLACES" for r in out)


def test_rescue_replaces_pattern_d_prefers_longest_a_zone_entity():
    """When two entities overlap in the A zone (e.g., 'alembic' and
    'alembic migration 0001' both extracted), Pattern D must pick the
    longest-span entity as the REPLACES target, not the shortest."""
    ents = _entities("alembic", "alembic migration 0001", "llm_seed.py")
    out = _rescue_relations(
        ents, [],
        "Seed data was moved out of Alembic migration 0001 into llm_seed.py",
    )
    # Should emit `llm_seed.py REPLACES alembic migration 0001`, NOT
    # `llm_seed.py REPLACES alembic` — the more specific entity wins
    # the A-zone tiebreak.
    assert _has(out, "llm_seed.py", "alembic migration 0001", "REPLACES"), (
        f"expected longest-span A-zone entity to win; got {out}"
    )
    assert not _has(out, "llm_seed.py", "alembic", "REPLACES"), (
        f"shorter overlapping entity must NOT be selected; got {out}"
    )


def test_rescue_replaces_pattern_d_b_zone_window_blocks_distant_entity():
    """When the obvious new-home file path isn't extracted as an entity,
    Pattern D must NOT fall through to a distant entity that happens to
    appear later in the clause. The 80-char B-zone window enforces this:
    the rescue declines to fire, which is the correct failure mode."""
    # `llm_seed.py` is intentionally NOT in the entity set — this
    # simulates the round-9 recall gap where the model failed to
    # extract the file path. `finalize handler` is far past the
    # file path in the same clause; the previous (windowless)
    # implementation incorrectly picked it as the new home.
    ents = _entities("alembic migration 0001", "finalize handler")
    out = _rescue_relations(
        ents, [],
        "Seed data was moved out of Alembic migration 0001 into "
        "backend/app/services/llm_seed.py and is now applied by the "
        "setup wizard's finalize handler instead.",
    )
    # No REPLACES at all is the correct outcome — the rescue cannot
    # invent the missing file-path entity, so it must decline.
    assert not any(r.get("type") == "REPLACES" for r in out), (
        f"rescue must decline when obvious target is unextracted; got {out}"
    )


def test_rescue_replaces_pattern_d_b_zone_window_accepts_close_entity():
    """Sanity check the inverse: when the obvious new-home IS extracted
    and sits within the 80-char window, Pattern D fires normally."""
    ents = _entities("alembic migration 0001", "llm_seed.py", "finalize handler")
    out = _rescue_relations(
        ents, [],
        "Seed data was moved out of Alembic migration 0001 into "
        "llm_seed.py and is now applied by the finalize handler instead.",
    )
    assert _has(out, "llm_seed.py", "alembic migration 0001", "REPLACES"), (
        f"expected llm_seed.py REPLACES alembic migration 0001; got {out}"
    )


# --- Negation suppression --------------------------------------------------


def test_rescue_replaces_skips_negated_clause():
    """Clause containing 'not / no / without / never' is skipped entirely."""
    content = "We did not switch from Jenkins to GitHub Actions this quarter"
    ents = _entities("Jenkins", "GitHub Actions")
    out = _rescue_relations(ents, [], content)
    assert not _has(out, "GitHub Actions", "Jenkins", "REPLACES")


def test_rescue_replaces_clause_scope_holds():
    """A transition verb in one sentence cannot pull from/to anchors from
    the next. The pattern must respect ``. ! ? ;`` clause boundaries."""
    content = "We migrated. Jenkins from is fine; we use GitHub Actions to deploy."
    ents = _entities("Jenkins", "GitHub Actions")
    out = _rescue_relations(ents, [], content)
    assert not _has(out, "GitHub Actions", "Jenkins", "REPLACES")


# --- Adjacency connectors (subject tracking) -------------------------------


@pytest.mark.parametrize(
    "content,src,tgt,rtype",
    [
        # X uses Y
        ("darkmem uses pgvector for retrieval", "darkmem", "pgvector", "USES"),
        # X with Y / via Y
        ("Indexing is done with tree-sitter today", None, None, None),  # generic subject
        # X deployed on Y / runs on Y
        ("darkmem runs on CPU only", "darkmem", "CPU", "DEPLOYED_ON"),
        ("darkmem deployed on Postgres 17", "darkmem", "Postgres 17", "DEPLOYED_ON"),
    ],
)
def test_rescue_adjacency_basic(content, src, tgt, rtype):
    if src is None:
        # The 'with X' rescue should not fire when no upstream subject
        # entity exists in the clause.
        ents = _entities("tree-sitter")
        out = _rescue_relations(ents, [], content)
        assert not any(r.get("type") == "USES" for r in out)
        return
    ents = _entities(src, tgt)
    out = _rescue_relations(ents, [], content)
    assert _has(out, src, tgt, rtype)


def test_rescue_adjacency_skips_negated_pair():
    """``X with no Y`` must not infer USES."""
    content = "darkmem runs with no GPU acceleration"
    ents = _entities("darkmem", "GPU")
    out = _rescue_relations(ents, [], content)
    assert not _has(out, "darkmem", "GPU", "USES")


def test_rescue_adjacency_avoids_prepositional_object_subject():
    """Subject tracking must NOT pick a prepositional object as the
    subject of a later verb. ``Adding via MCP to confirm extraction with
    pgvector`` should not yield ``MCP USES pgvector``."""
    content = "Adding via MCP to confirm extraction with pgvector"
    ents = _entities("MCP", "pgvector")
    out = _rescue_relations(ents, [], content)
    assert not _has(out, "MCP", "pgvector", "USES")


# --- Idempotency -----------------------------------------------------------


# --- Same-pair USES + DEPLOYED_ON dedup ------------------------------------


def test_dedup_drops_uses_when_deployed_on_exists_same_pair():
    """The qwen3/ollama failure mode: LLM emits ``A USES B`` and the
    rescue adjacency pass emits ``A DEPLOYED_ON B`` for the same pair.
    DEPLOYED_ON is the more specific predicate; USES is redundant.
    """
    from app.services.extraction import _drop_uses_when_deployed_on_exists

    rels = [
        {"source": "qwen3-embedding:0.6b", "target": "ollama", "type": "USES", "weight": 0.8},
        {"source": "qwen3-embedding:0.6b", "target": "ollama",
         "type": "DEPLOYED_ON", "weight": 0.6, "properties": {"rescue": True}},
    ]
    out = _drop_uses_when_deployed_on_exists(rels)
    assert len(out) == 1
    assert out[0]["type"] == "DEPLOYED_ON"


def test_dedup_keeps_uses_when_no_deployed_on_pair():
    """A USES whose pair has no DEPLOYED_ON survives untouched."""
    from app.services.extraction import _drop_uses_when_deployed_on_exists

    rels = [
        {"source": "darkmem", "target": "pgvector", "type": "USES", "weight": 0.8},
        {"source": "hnsw", "target": "postgres 17", "type": "DEPLOYED_ON", "weight": 0.8},
    ]
    out = _drop_uses_when_deployed_on_exists(rels)
    assert len(out) == 2


def test_dedup_keeps_reverse_pair_uses():
    """A USES on the reversed pair (B → A) does NOT get dropped by an
    A DEPLOYED_ON B. Could be a legitimate "host uses its own service"."""
    from app.services.extraction import _drop_uses_when_deployed_on_exists

    rels = [
        {"source": "qwen3-embedding:0.6b", "target": "ollama",
         "type": "DEPLOYED_ON", "weight": 0.8},
        # Reverse direction — host using its deployed service. Keep.
        {"source": "ollama", "target": "qwen3-embedding:0.6b", "type": "USES", "weight": 0.7},
    ]
    out = _drop_uses_when_deployed_on_exists(rels)
    assert len(out) == 2


def test_dedup_drops_only_uses_not_other_predicates():
    """The dedup is specific to USES vs DEPLOYED_ON; other predicates
    (DEPENDS_ON, HAS_PART) are passed through even on the same pair."""
    from app.services.extraction import _drop_uses_when_deployed_on_exists

    rels = [
        {"source": "qwen3-embedding:0.6b", "target": "ollama",
         "type": "DEPLOYED_ON", "weight": 0.8},
        {"source": "qwen3-embedding:0.6b", "target": "ollama",
         "type": "DEPENDS_ON", "weight": 0.6},
    ]
    out = _drop_uses_when_deployed_on_exists(rels)
    assert len(out) == 2


def test_rescue_does_not_duplicate_existing_relations():
    """If the model already emitted ``Y REPLACES X``, the rescue should
    not add a second triple for the same canonical pair+predicate."""
    content = "We switched from Jenkins to GitHub Actions"
    ents = _entities("Jenkins", "GitHub Actions")
    seed = [{
        "source": "GitHub Actions", "target": "Jenkins",
        "type": "REPLACES", "properties": {}, "weight": 0.9,
    }]
    out = _rescue_relations(ents, seed, content)
    replaces = [r for r in out if r.get("type") == "REPLACES"]
    assert len(replaces) == 1


# --- Subject-anchoring fix (2026-05-02) ------------------------------------
#
# All eleven extraction-model evaluation runs reproduced the same three
# wrong-subject rescue triples on the Phoenix v2 / Triton memory:
#
#   - "phoenix is written in rust and depends on tokio"
#       expected: phoenix v2 DEPENDS_ON tokio
#       broken:   rust DEPENDS_ON tokio  (rust is object of "in")
#   - "phoenix runs on kubernetes in the eu-west-1 region and uses clickhouse"
#       expected: phoenix v2 USES clickhouse
#       broken:   eu-west-1 USES clickhouse  (eu-west-1 is object of "in the")
#   - "phoenix v2, ... authored by riya patel that replaces the legacy triton"
#       expected: phoenix v2 REPLACES triton
#       broken:   riya patel REPLACES triton  (riya is object of "by")
#
# Fix: when the closest preceding entity to a connector / replace verb is
# an object of a preposition, fall back to the clause's syntactic subject
# (first non-prepositional-object entity in the clause).


def test_rescue_uses_promotes_clause_subject_when_closest_entity_is_object_of_preposition():
    """``Phoenix runs on Kubernetes in the eu-west-1 region and uses
    ClickHouse`` should yield ``phoenix v2 USES clickhouse`` — NOT
    ``eu-west-1 USES clickhouse``. eu-west-1 is the object of ``in``
    (with article ``the`` between), so it must be disqualified as the
    USES subject."""
    content = (
        "Phoenix v2 runs on Kubernetes in the eu-west-1 region "
        "and uses ClickHouse for analytics storage."
    )
    ents = _entities("Phoenix v2", "Kubernetes", "eu-west-1", "ClickHouse")
    out = _rescue_relations(ents, [], content)
    assert _has(out, "Phoenix v2", "ClickHouse", "USES"), (
        f"expected phoenix v2 USES clickhouse, got: "
        f"{[(r['source'], r['type'], r['target']) for r in out if r.get('type') == 'USES']}"
    )
    assert not _has(out, "eu-west-1", "ClickHouse", "USES"), (
        "eu-west-1 is the object of 'in', must not anchor USES"
    )


def test_rescue_depends_on_promotes_clause_subject():
    """``Phoenix is written in Rust and depends on Tokio for async I/O``
    -> phoenix v2 DEPENDS_ON tokio (NOT rust DEPENDS_ON tokio). Rust is
    object of ``in``."""
    content = (
        "Phoenix v2 is written in Rust and depends on Tokio for async I/O."
    )
    ents = _entities("Phoenix v2", "Rust", "Tokio")
    out = _rescue_relations(ents, [], content)
    assert _has(out, "Phoenix v2", "Tokio", "DEPENDS_ON"), (
        f"expected phoenix v2 DEPENDS_ON tokio, got: "
        f"{[(r['source'], r['type'], r['target']) for r in out if r.get('type') == 'DEPENDS_ON']}"
    )
    assert not _has(out, "Rust", "Tokio", "DEPENDS_ON"), (
        "rust is the object of 'in', must not anchor DEPENDS_ON"
    )


def test_rescue_replaces_pattern_c_promotes_clause_subject():
    """``Phoenix v2, a new ingestion service authored by Riya Patel that
    replaces the legacy Triton pipeline`` -> phoenix v2 REPLACES triton
    (NOT riya patel REPLACES triton). Riya Patel is object of ``by``."""
    content = (
        "Phoenix v2, a new ingestion service authored by Riya Patel "
        "that replaces the legacy Triton pipeline."
    )
    ents = _entities("Phoenix v2", "Riya Patel", "Triton")
    out = _rescue_relations(ents, [], content)
    assert _has(out, "Phoenix v2", "Triton", "REPLACES"), (
        f"expected phoenix v2 REPLACES triton, got: "
        f"{[(r['source'], r['type'], r['target']) for r in out if r.get('type') == 'REPLACES']}"
    )
    assert not _has(out, "Riya Patel", "Triton", "REPLACES"), (
        "riya patel is the object of 'by', must not anchor REPLACES"
    )


def test_rescue_subject_promotion_does_not_fire_when_closest_entity_is_real_subject():
    """Regression guard: when the closest preceding entity IS the clause
    subject (not a prepositional object), don't promote anything. The
    subject-promotion logic must not activate on clean inputs.
    ``Postgres uses HNSW indexing`` -> postgres USES hnsw (no change)."""
    content = "Postgres uses HNSW indexing for vector search."
    ents = _entities("Postgres", "HNSW")
    out = _rescue_relations(ents, [], content)
    assert _has(out, "Postgres", "HNSW", "USES")
