"""The carried-set column map and the three-bucket disposition.

Single source of truth for what moves, what is regenerated, and what dies with
the old schema. Every other module in this package reads its table and column
names from here rather than spelling them out, so a disposition change is one
edit and a divergence is impossible.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Column:
    """One carried column.

    ``source`` and ``target`` differ only for the four ``llm_*`` renames.
    ``staging_type`` is deliberately unconstrained (``TEXT`` where the source
    is ``VARCHAR(n)``): a staging table that reproduced the width would turn a
    loud over-length failure at load time into an early one at staging time,
    and nothing in the transform may narrow a value.
    """

    source: str
    target: str
    staging_type: str
    is_timestamp: bool = False


@dataclass(frozen=True)
class CarriedTable:
    name: str
    columns: tuple[Column, ...]
    key: tuple[str, ...]
    load_expressions: dict[str, str] = field(default_factory=dict)
    target_only: tuple[tuple[str, str], ...] = ()

    @property
    def staging_name(self) -> str:
        return f"cutover_stage_{self.name}"

    @property
    def source_columns(self) -> tuple[str, ...]:
        return tuple(c.source for c in self.columns)

    @property
    def target_columns(self) -> tuple[str, ...]:
        return tuple(c.target for c in self.columns)

    def column_by_source(self, name: str) -> Column:
        for column in self.columns:
            if column.source == name:
                return column
        raise KeyError(name)


MEMORIES = CarriedTable(
    name="memories",
    key=("id",),
    columns=(
        Column("id", "id", "UUID"),
        Column("content", "content", "TEXT"),
        Column("source", "source", "TEXT"),
        Column("source_agent", "source_agent", "TEXT"),
        Column("memory_type", "memory_type", "TEXT"),
        Column("importance", "importance", "DOUBLE PRECISION"),
        Column("metadata", "metadata", "JSONB"),
        Column("created_at", "created_at", "TIMESTAMPTZ", is_timestamp=True),
        Column("updated_at", "updated_at", "TIMESTAMPTZ", is_timestamp=True),
        Column("expires_at", "expires_at", "TIMESTAMPTZ", is_timestamp=True),
        Column("is_archived", "is_archived", "BOOLEAN"),
        Column("llm_classified_type", "classified_type", "TEXT"),
        Column("llm_summary", "summary", "TEXT"),
        Column("llm_emotions", "emotions", "JSONB"),
        Column("llm_flags", "flags", "JSONB"),
        Column("project", "project", "TEXT"),
        Column("status", "status", "TEXT"),
        Column("superseded_by", "superseded_by", "UUID"),
        Column("confidence", "confidence", "REAL"),
    ),
    # status is TEXT in staging and memory_status in the target.
    load_expressions={"status": "CAST(s.status AS memory_status)"},
    # origin_key: NULL means "no origin", never "one origin" — SQL's
    # COUNT(DISTINCT x) skips NULLs, and a carried memory carries no evidence
    # of which capture session produced it. technologies is rebuilt by the
    # re-extraction backfill, so it lands empty rather than stale.
    target_only=(
        ("origin_key", "CAST(NULL AS TEXT)"),
        ("technologies", "CAST('{}' AS TEXT[])"),
    ),
)

TAGS = CarriedTable(
    name="tags",
    key=("id",),
    columns=(
        Column("id", "id", "INTEGER"),
        Column("name", "name", "TEXT"),
        Column("category", "category", "TEXT"),
    ),
)

MEMORY_TAGS = CarriedTable(
    name="memory_tags",
    key=("memory_id", "tag_id"),
    columns=(
        Column("memory_id", "memory_id", "UUID"),
        Column("tag_id", "tag_id", "INTEGER"),
    ),
)

CONVERSATIONS = CarriedTable(
    name="conversations",
    key=("id",),
    columns=(
        Column("id", "id", "UUID"),
        Column("title", "title", "TEXT"),
        Column("is_archived", "is_archived", "BOOLEAN"),
        Column("created_at", "created_at", "TIMESTAMPTZ", is_timestamp=True),
        Column("updated_at", "updated_at", "TIMESTAMPTZ", is_timestamp=True),
    ),
)

MESSAGES = CarriedTable(
    name="messages",
    key=("id",),
    columns=(
        Column("id", "id", "UUID"),
        Column("conversation_id", "conversation_id", "UUID"),
        Column("role", "role", "TEXT"),
        Column("content", "content", "TEXT"),
        Column("context", "context", "JSONB"),
        Column("created_at", "created_at", "TIMESTAMPTZ", is_timestamp=True),
    ),
)

# Load order: parents before children, so every FK resolves as it is written.
CARRIED: tuple[CarriedTable, ...] = (TAGS, MEMORIES, MEMORY_TAGS, CONVERSATIONS, MESSAGES)

CARRIED_BY_NAME: dict[str, CarriedTable] = {t.name: t for t in CARRIED}

# Reverse FK order for --reset.
RESET_DELETE_ORDER: tuple[str, ...] = (
    "memory_tags",
    "messages",
    "memories",
    "conversations",
    "tags",
)

# Rows edited after the cutover keep their id, so the dump-membership id check
# cannot see them; only these two tables carry an updated_at to compare.
RESET_EDIT_CHECK_TABLES: tuple[str, ...] = ("memories", "conversations")

# Any of these holding a row means a derivation already exists over the carried
# set, and deleting a memory would cascade it away (or leave an array reference
# dangling, for the two graph tables). Widened from three to seven by the plan's
# review after reading pg_constraint: four cascading tables were missing.
RESET_REFUSAL_TABLES: tuple[str, ...] = (
    "entities",
    "entity_relations",
    "memory_crossrefs",
    "memory_access_stats",
    "memory_relations",
    "memory_community_members",
)

# Refusal trigger number seven: the per-fingerprint memory-vector partitions,
# whose ON DELETE CASCADE comes from the table template rather than the baseline.
RESET_REFUSAL_TABLE_PREFIX = "memory_embeddings__"

# Survives a cascade as a parent whose members were deleted, so the refusal
# report names it without refusing on it.
RESET_REPORT_ONLY_TABLES: tuple[str, ...] = ("memory_communities",)

# Appendix A.1 of docs/planning/baseline-schema-inventory.md — the 26 tables a
# database at revision 0006 holds, machine-extracted from the six brownfield
# revisions.
SOURCE_TABLES_A1: tuple[str, ...] = (
    "alembic_version",
    "api_keys",
    "audit_log",
    "code_edges",
    "code_files",
    "code_graph_nodes",
    "code_symbols",
    "config",
    "conversations",
    "embedders",
    "enrichment_queue",
    "entities",
    "entity_relations",
    "knowledge_triples",
    "llm_profiles",
    "llm_providers",
    "llm_purpose_configs",
    "memories",
    "memory_crossrefs",
    "memory_tags",
    "messages",
    "ml_profiles",
    "pipeline_failures",
    "repositories",
    "tags",
    "token_blocklist",
)

# A.1 was extracted from a freshly migrated database, which has no registered
# fingerprints. A real source has the runtime-minted children, so the source
# table-set assertion is subset-plus-pattern. The four parents are enumerated
# rather than accepting a bare `%__%`, which would also admit a hand-made
# `something__backup`.
SOURCE_CHILD_TABLE_PREFIXES: tuple[str, ...] = (
    "memory_embeddings__",
    "entity_embeddings__",
    "code_chunk_embeddings__",
    "entity_embedding_cache__",
)

SOURCE_REVISION = "0006"

# Rows are expected to be zero on both. api_keys is unwired at 0006 (every
# write passes api_key_id=None); knowledge_triples keeps its name in the target
# and nothing else, and its NOT NULL columns are not derivable from the source's
# subject/predicate/object — a mapping would have to manufacture fact identity.
SOURCE_MUST_BE_EMPTY: tuple[str, ...] = ("api_keys", "knowledge_triples")

# Emitted so the operator's by-hand re-declaration of repositories is a
# checklist. has_auth_token is derived; neither the token nor the
# auth_token_ref that points at it may enter a report the operator saves.
REPOSITORY_INVENTORY_COLUMNS: tuple[str, ...] = (
    "name",
    "url",
    "provider",
    "default_branch",
    "local_path",
    "auto_sync",
)

# The eleven columns T1.52's Phase-5 write can overwrite on a carried row —
# updated_at and confidence unconditionally, memory_type and importance
# conditionally, and the four enrichment columns whenever the classification
# dict is truthy (where `… or None` nulls a carried value on an empty field).
# status/superseded_by move when re-extraction emits a REPLACES-family relation.
SNAPSHOT_COLUMNS: tuple[str, ...] = (
    "id",
    "memory_type",
    "importance",
    "confidence",
    "updated_at",
    "status",
    "superseded_by",
    "classified_type",
    "summary",
    "emotions",
    "flags",
)

# Rebuilt: the target table exists and its rows are regenerated, because they
# are derivations of the carried set under a taxonomy, prompt or embedder the
# target changed.
REBUILT_TABLES: dict[str, str] = {
    "entities": "T1.52 re-extraction",
    "entity_relations": "T1.52 re-extraction",
    "memory_crossrefs": "T1.52 (Phase 5 crossref pass)",
    "embedders": "embedder_registry.register at runtime",
    "llm_purpose_configs": "setup wizard finalize, from llm_seed.py",
    "repositories": "operator re-declares by hand",
    "code_files": "POST /repos/{id}/reindex",
    "code_symbols": "reindex",
    "code_graph_nodes": "reindex",
    "code_edges": "reindex",
}

DROPPED_TABLES: dict[str, str] = {
    "pipeline_failures": "operational residue with no post-cutover meaning",
    "token_blocklist": "operational residue; revocations of a rotating secret",
    "config": "carry nothing — job state, auth root, secrets and runtime settings",
    "audit_log": "the audit_log -> events transform is declined on three blockers",
    "enrichment_queue": "no target table; zero code references",
    "llm_providers": "target table shares the name and nothing else; 0 source rows",
    "llm_profiles": "never exists in the baseline",
    "ml_profiles": "re-homed as the inline classifier_kind",
    "knowledge_triples": "name survives, every column and semantic is new",
    "api_keys": "unwired at 0006; rows expected to be zero",
    "alembic_version": "infrastructure; the target's row comes from alembic",
}

# Target tables with no source row at all, listed so a reviewer's sweep
# terminates. projects is the one the transform must handle: it is populated by
# lazy registration on capture, and carried rows never go through capture.
#
# llm_providers is the one entry that also appears in DROPPED_TABLES, and it is
# not a contradiction: the two lists answer different questions. A source table
# of that name exists at 0006 and holds zero rows, so it is dropped on the
# source side; the owner ruling of 2026-08-20 reinstated a table of the same
# name in the baseline with a different key and different columns, so it is new
# on the target side, and its rows come from the setup wizard's seed. Reading
# the drop as "no such target table" is what the corrected rationale above
# guards against.
TARGET_NEW_TABLES: tuple[str, ...] = (
    "projects",
    "llm_providers",
    "events",
    "memory_relations",
    "memory_access_stats",
    "memory_communities",
    "memory_community_members",
    "memory_buffer",
    "fact_sources",
    "knowledge_articles",
    "article_citations",
    "project_repositories",
    "documents",
    "blocks",
)

# Any sentinel outside the column's value domain. string_agg SKIPS NULL rows,
# so without it a NULL-position swap defeats the checksum, the NULL count and
# the distinct count at once — and an all-NULL column checksums to SQL NULL,
# which compares equal to the other side's NULL client-side.
NULL_SENTINEL = "␀"
