"""baseline

Revision ID: 0001
Revises:
Create Date: 2026-07-27

The single greenfield baseline. Doc 19 §2: the schema ships as ONE revision,
regenerated freely (paired with drop/recreate) until the first deploy whose
data must survive — the homelab cutover — at which event it is tagged ``0001``
and frozen, and every change after is a new linear revision forever. Until
then a schema change means editing THIS file and recreating the database, never
appending ``0002``; a CI assertion holds ``alembic history`` at exactly one
revision until the freeze tag exists.

**Freeze date: not yet frozen.** T0.15 owns the regeneration protocol and the
cutover task fills the real date.

Authored as plain SQL rather than ``op.create_table``. Doc 19 §2 binds every
table, constraint, index and trigger to stay expressible as plain SQL so the
deferred .NET port replays this file through DbUp as a mechanical transcription
rather than a re-derivation from ORM metadata. Expressing the DDL as SQLAlchemy
schema objects would defeat that, so the statements below are the SQL itself.

The object inventory this file implements — every table, index, constraint and
column traced to its owning design-doc section, with its disposition — is
``docs/planning/baseline-schema-inventory.md``. Read it before changing
anything here; a divergence between the two is a defect in one of them.

Per-fingerprint embedding child tables (``memory_embeddings__<slug>`` and its
seven siblings) are deliberately ABSENT. Their DDL is parameterised by
fingerprint, which no static migration can express, so they are registry
entries created by the boot-time reconciliation in ``embedder_registry``
(doc 19 §2, inventory §6). Nothing about them belongs in this file.

Built up by T0.12a (this pass), T0.12b and T0.12c. This pass lands the core
memory rows, the knowledge graph, the tag pair, ``config`` and the embedder
registry.
"""
from collections.abc import Sequence
from typing import Union

from alembic import op

revision: str = '0001'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ------------------------------------------------------------------
    # Extensions and types
    # ------------------------------------------------------------------
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # The ONE native enum in the schema (doc 04 §2, §11). Every other state
    # column is CHECK-constrained text and every "type" column is varchar
    # normalised in application code against a closed set; promoting any of
    # them to an enum would be a behaviour change, not a tidy-up.
    op.execute(
        "CREATE TYPE memory_status AS ENUM ('active', 'deprecated', 'superseded')"
    )

    # ------------------------------------------------------------------
    # Functions
    # ------------------------------------------------------------------
    op.execute(
        """
        CREATE FUNCTION memories_fts_trigger() RETURNS trigger AS $$
        BEGIN
            NEW.search_vector := to_tsvector('english', COALESCE(NEW.content, ''));
            RETURN NEW;
        END $$ LANGUAGE plpgsql
        """
    )

    # The updated_at auto-bump lives in SQL, not in SQLAlchemy's client-side
    # ``onupdate`` (inventory F-20, adjudicated 2026-07-27). onupdate fires only
    # for statements SQLAlchemy constructs: measured on a live database, a Core
    # update() bumps the column while a raw text() UPDATE does not, so the two
    # demote-before-delete paths silently left it stale on a status change.
    op.execute(
        """
        CREATE FUNCTION touch_updated_at() RETURNS trigger AS $$
        BEGIN
            NEW.updated_at := now();
            RETURN NEW;
        END $$ LANGUAGE plpgsql
        """
    )

    # ------------------------------------------------------------------
    # config — feature flags, job:<key> state, admin_password_hash
    # ------------------------------------------------------------------
    op.execute(
        """
        CREATE TABLE config (
            key   VARCHAR(255) PRIMARY KEY,
            value JSONB NOT NULL DEFAULT '{}'::jsonb
        )
        """
    )

    # ------------------------------------------------------------------
    # embedders — the fingerprint registry (doc 04 §5.1)
    # ------------------------------------------------------------------
    # It owns the DDL for each fingerprint's child tables and is the
    # register-before-insert authority and the sole namer. The source CHECK was
    # narrowed to the single value 'llm' when the ML/regex embedder arms were
    # scrubbed; the target does not widen it.
    op.execute(
        """
        CREATE TABLE embedders (
            fingerprint   TEXT PRIMARY KEY,
            model_id      TEXT NOT NULL,
            dims          INTEGER NOT NULL,
            source        TEXT NOT NULL,
            registered_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            retired_at    TIMESTAMPTZ,
            CONSTRAINT embedders_dims_check   CHECK (dims > 0),
            CONSTRAINT embedders_source_check CHECK (source = 'llm')
        )
        """
    )

    # ------------------------------------------------------------------
    # memories — the central rows and the status lifecycle (doc 04 §3.1)
    # ------------------------------------------------------------------
    # id is application-generated UUIDv7 (doc 04 §2) — time-ordered so B-tree
    # inserts stay local — hence no server default here. source keeps its
    # ORM-only 'api' default, which doc 04 §3.1 records deliberately.
    op.execute(
        """
        CREATE TABLE memories (
            id              UUID NOT NULL,
            content         TEXT NOT NULL,
            source          VARCHAR(100) NOT NULL,
            source_agent    VARCHAR(255),
            origin_key      TEXT,
            memory_type     VARCHAR(50),
            importance      DOUBLE PRECISION NOT NULL DEFAULT 0.5,
            metadata        JSONB NOT NULL DEFAULT '{}'::jsonb,
            created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
            expires_at      TIMESTAMPTZ,
            is_archived     BOOLEAN NOT NULL DEFAULT false,
            classified_type VARCHAR(50),
            summary         TEXT,
            emotions        JSONB,
            flags           JSONB,
            project         TEXT NOT NULL DEFAULT 'default',
            status          memory_status NOT NULL DEFAULT 'active',
            superseded_by   UUID,
            technologies    TEXT[] NOT NULL DEFAULT '{}'::text[],
            confidence      REAL NOT NULL DEFAULT 0.75,
            search_vector   TSVECTOR,
            CONSTRAINT memories_pkey PRIMARY KEY (id),
            CONSTRAINT chk_superseded_has_pointer
                CHECK (status != 'superseded' OR superseded_by IS NOT NULL),
            CONSTRAINT fk_memories_superseded_by
                FOREIGN KEY (superseded_by) REFERENCES memories(id) ON DELETE SET NULL
        )
        """
    )

    # Trivially satisfiable (id is already the PK) and it exists solely so
    # memory_relations' endpoint FKs can be declared as composite
    # (memory_id, project) references, which makes a cross-project edge
    # unrepresentable rather than merely forbidden (doc 04 §8.2, §10).
    # Without it memory_relations is undeclarable.
    op.execute(
        "ALTER TABLE memories ADD CONSTRAINT memories_id_project_key UNIQUE (id, project)"
    )

    op.execute("CREATE INDEX ix_memories_created_at ON memories (created_at)")
    op.execute(
        "CREATE INDEX ix_memories_is_archived ON memories (is_archived) "
        "WHERE is_archived = false"
    )
    op.execute("CREATE INDEX ix_memories_project ON memories (project)")
    op.execute("CREATE INDEX ix_memories_status ON memories (status)")
    # The reverse lineage query (`get_predecessors`) filters on this column;
    # the forward direction is a plain column read on the row already in
    # hand and needs no index of its own (T1.66).
    op.execute("CREATE INDEX ix_memories_superseded_by ON memories (superseded_by)")
    op.execute("CREATE INDEX ix_memories_technologies ON memories USING gin (technologies)")
    op.execute("CREATE INDEX ix_memories_fts ON memories USING gin (search_vector)")

    # The one index change the SQL filter-pushdown strictly requires
    # (doc 04 §10). Partial rather than a full composite: the pushed-down
    # predicate's common shape is "live rows in this project", and this is the
    # smallest of the three forms doc 04 offers. The semantic channel cannot
    # use it — an HNSW scan applies the predicate post-scan — so it serves the
    # keyword and direct-scan sides.
    op.execute(
        "CREATE INDEX ix_memories_project_live ON memories (project) "
        "WHERE status = 'active' AND is_archived = false"
    )

    op.execute(
        "CREATE TRIGGER memories_fts_update BEFORE INSERT OR UPDATE OF content "
        "ON memories FOR EACH ROW EXECUTE FUNCTION memories_fts_trigger()"
    )
    op.execute(
        "CREATE TRIGGER memories_touch_updated_at BEFORE UPDATE "
        "ON memories FOR EACH ROW EXECUTE FUNCTION touch_updated_at()"
    )

    # ------------------------------------------------------------------
    # tags, memory_tags (doc 04 §3.2)
    # ------------------------------------------------------------------
    op.execute(
        """
        CREATE TABLE tags (
            id       SERIAL PRIMARY KEY,
            name     VARCHAR(255) NOT NULL UNIQUE,
            category VARCHAR(50)
        )
        """
    )
    op.execute(
        """
        CREATE TABLE memory_tags (
            memory_id UUID    NOT NULL REFERENCES memories(id) ON DELETE CASCADE,
            tag_id    INTEGER NOT NULL REFERENCES tags(id)     ON DELETE CASCADE,
            CONSTRAINT memory_tags_pkey PRIMARY KEY (memory_id, tag_id)
        )
        """
    )

    # ------------------------------------------------------------------
    # entities, entity_relations — the knowledge graph (doc 04 §4)
    # ------------------------------------------------------------------
    # Non-memory-scoped: each row carries the memory_ids of every memory that
    # asserts it, so creating a duplicate appends rather than inserting.
    # These two keep server-side gen_random_uuid() (v4) rather than UUIDv7 —
    # they are ANN-probed and sweep-churned, not range-scanned, so insert
    # locality buys nothing (doc 04 §2). Names live lowercase on disk with the
    # original casing in properties.display_name.
    op.execute(
        """
        CREATE TABLE entities (
            id          UUID NOT NULL DEFAULT gen_random_uuid(),
            name        VARCHAR(500) NOT NULL,
            entity_type VARCHAR(100) NOT NULL,
            properties  JSONB  DEFAULT '{}'::jsonb,
            memory_ids  UUID[] DEFAULT '{}'::uuid[],
            -- target-new, INERT: the code-assertion analog of memory_ids, by
            -- which a repo asserts a graph row without a memory (invariant 8
            -- amendment, doc 04 §4.1/§4.2). Lands with empty arrays, so the
            -- sweeps' NOT EXISTS (live repo) clauses are vacuously true and
            -- behaviour is byte-identical. First writer: T2.27.
            repo_ids    UUID[] DEFAULT '{}'::uuid[],
            created_at  TIMESTAMPTZ DEFAULT now(),
            CONSTRAINT entities_pkey PRIMARY KEY (id),
            CONSTRAINT entities_name_entity_type_key UNIQUE (name, entity_type)
        )
        """
    )
    op.execute("CREATE INDEX ix_entities_memory_ids ON entities USING gin (memory_ids)")
    op.execute("CREATE INDEX ix_entities_repo_ids ON entities USING gin (repo_ids)")

    op.execute(
        """
        CREATE TABLE entity_relations (
            id               UUID NOT NULL DEFAULT gen_random_uuid(),
            source_entity_id UUID NOT NULL REFERENCES entities(id) ON DELETE CASCADE,
            target_entity_id UUID NOT NULL REFERENCES entities(id) ON DELETE CASCADE,
            rel_type         VARCHAR(100) NOT NULL,
            properties       JSONB  DEFAULT '{}'::jsonb,
            weight           DOUBLE PRECISION DEFAULT 0.5,
            memory_ids       UUID[] DEFAULT '{}'::uuid[],
            -- target-new, INERT — as on entities above. First writer: T2.27.
            repo_ids         UUID[] DEFAULT '{}'::uuid[],
            created_at       TIMESTAMPTZ DEFAULT now(),
            CONSTRAINT entity_relations_pkey PRIMARY KEY (id),
            CONSTRAINT entity_relations_source_entity_id_target_entity_id_rel_type_key
                UNIQUE (source_entity_id, target_entity_id, rel_type)
        )
        """
    )
    op.execute(
        "CREATE INDEX ix_entity_relations_memory_ids ON entity_relations USING gin (memory_ids)"
    )
    op.execute(
        "CREATE INDEX ix_entity_relations_repo_ids ON entity_relations USING gin (repo_ids)"
    )
    # Reverse-lookup, neighbour and orphan-guard queries filter on the target,
    # which the UNIQUE's source-prefix cannot serve.
    op.execute(
        "CREATE INDEX ix_entity_relations_target ON entity_relations (target_entity_id)"
    )

    _pass_two()


def _pass_two() -> None:
    """T0.12b — knowledge vault, memory satellites, code graph, ops, events."""

    # ------------------------------------------------------------------
    # projects — the minimal namespace registry (doc 04 §7)
    # ------------------------------------------------------------------
    # Lazy auto-registration (INSERT … ON CONFLICT DO NOTHING on capture) and
    # NO FK enforcement yet — every scoped table keeps its bare project text
    # column. It lands now because knowledge_triples.triple_key embeds project
    # in FACT IDENTITY, so a typo'd project silently splits corroboration
    # across two identities.
    op.execute(
        """
        CREATE TABLE projects (
            name         TEXT PRIMARY KEY,
            display_name TEXT,
            properties   JSONB NOT NULL DEFAULT '{}'::jsonb,
            created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )

    # ------------------------------------------------------------------
    # Memory satellites (doc 04 §3.3, §8.2, §8.4, §9)
    # ------------------------------------------------------------------
    op.execute(
        """
        CREATE TABLE memory_crossrefs (
            memory_id         UUID NOT NULL REFERENCES memories(id) ON DELETE CASCADE,
            related_memory_id UUID NOT NULL REFERENCES memories(id) ON DELETE CASCADE,
            score             DOUBLE PRECISION NOT NULL,
            CONSTRAINT memory_crossrefs_pkey PRIMARY KEY (memory_id, related_memory_id)
        )
        """
    )
    op.execute(
        "CREATE INDEX ix_memory_crossrefs_related ON memory_crossrefs (related_memory_id)"
    )

    # 1:1 ranking priors live here rather than on memories: memories is the
    # widest hot row in the system, so a per-read bump would rewrite that whole
    # tuple version — MVCC bloat on the most-read table — and would fire the
    # updated_at bump, corrupting its "content changed" meaning (doc 04 §9).
    op.execute(
        """
        CREATE TABLE memory_access_stats (
            memory_id     UUID PRIMARY KEY REFERENCES memories(id) ON DELETE CASCADE,
            access_count  INTEGER NOT NULL DEFAULT 0,
            last_accessed TIMESTAMPTZ
        )
        """
    )

    # Typed, directed memory-to-memory edges. Stores exactly the FIVE
    # associative types — SUPERSEDES is a read-time projection over
    # memories.superseded_by and is never stored, so the pointer stays the
    # single source of truth (doc 04 §8.2). The endpoint FKs are COMPOSITE on
    # (memory_id, project), which is what makes a cross-project edge
    # unrepresentable rather than merely forbidden; they need the
    # memories UNIQUE (id, project) support landed in pass one.
    op.execute(
        """
        CREATE TABLE memory_relations (
            id               UUID NOT NULL,
            source_memory_id UUID NOT NULL,
            target_memory_id UUID NOT NULL,
            rel_type         TEXT NOT NULL,
            project          TEXT NOT NULL,
            properties       JSONB,
            created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT memory_relations_pkey PRIMARY KEY (id),
            CONSTRAINT memory_relations_source_target_type_key
                UNIQUE (source_memory_id, target_memory_id, rel_type),
            CONSTRAINT fk_memory_relations_source
                FOREIGN KEY (source_memory_id, project)
                REFERENCES memories(id, project) ON DELETE CASCADE,
            CONSTRAINT fk_memory_relations_target
                FOREIGN KEY (target_memory_id, project)
                REFERENCES memories(id, project) ON DELETE CASCADE
        )
        """
    )
    # "What points at this memory" filters on the target, which the UNIQUE's
    # source prefix cannot serve — entity_relations' migration-0002 lesson,
    # applied here from day one.
    op.execute(
        "CREATE INDEX ix_memory_relations_target ON memory_relations (target_memory_id)"
    )

    # Topics are Leiden communities over a project-scoped projection, never
    # entities: an entities row would fall through the closed ENTITY_TYPES
    # fallback to 'concept' and collide with UNIQUE(name, entity_type).
    # Re-derivation is delete-and-rewrite per project, so community ids CHURN
    # on every run — nothing durable may FK one (doc 04 §8.4).
    op.execute(
        """
        CREATE TABLE memory_communities (
            id            UUID NOT NULL,
            project       TEXT NOT NULL,
            label         TEXT,
            report_string TEXT,
            properties    JSONB,
            created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT memory_communities_pkey PRIMARY KEY (id)
        )
        """
    )
    op.execute(
        """
        CREATE TABLE memory_community_members (
            community_id UUID NOT NULL REFERENCES memory_communities(id) ON DELETE CASCADE,
            memory_id    UUID NOT NULL REFERENCES memories(id) ON DELETE CASCADE,
            CONSTRAINT memory_community_members_pkey PRIMARY KEY (community_id, memory_id)
        )
        """
    )
    op.execute(
        "CREATE INDEX ix_memory_community_members_memory "
        "ON memory_community_members (memory_id)"
    )

    # ------------------------------------------------------------------
    # memory_buffer — the durable Tier-B ingest buffer (doc 04 §8.6)
    # ------------------------------------------------------------------
    # Claimed via SELECT … FOR UPDATE SKIP LOCKED, so fast capture-ack is
    # decoupled from the five-phase pipeline with a durability an in-process
    # queue cannot give — and no external broker (invariant 1).
    op.execute(
        """
        CREATE TABLE memory_buffer (
            id         UUID NOT NULL,
            project    TEXT NOT NULL,
            source     TEXT,
            content    TEXT NOT NULL,
            token_size INTEGER,
            status     TEXT NOT NULL DEFAULT 'pending',
            attempts   INTEGER NOT NULL DEFAULT 0,
            last_error TEXT,
            metadata   JSONB,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            claimed_at TIMESTAMPTZ,
            claimed_by TEXT,
            CONSTRAINT memory_buffer_pkey PRIMARY KEY (id),
            CONSTRAINT memory_buffer_status_check
                CHECK (status IN ('pending', 'claimed', 'done', 'error'))
        )
        """
    )
    # The claim scan only ever reads pending rows, so the hot index stays small.
    op.execute(
        "CREATE INDEX ix_memory_buffer_pending ON memory_buffer (created_at) "
        "WHERE status = 'pending'"
    )

    # ------------------------------------------------------------------
    # knowledge_triples — the Layer-2 verified-fact store (doc 04 §8.3)
    # ------------------------------------------------------------------
    # A REBUILD that keeps a name, NOT an activation of the dormant demo
    # scaffolding: every column and semantic is new. The endpoints carry NO
    # hard FK — the graph side deletes entities aggressively while this
    # table's contract is invalidate-not-delete, so expired triples must
    # survive their endpoints. The denormalised lowercase names carry the
    # durable identity instead.
    op.execute(
        """
        CREATE TABLE knowledge_triples (
            id                  UUID NOT NULL,
            subject_id          UUID,
            object_id           UUID,
            subject_name        TEXT NOT NULL,
            object_name         TEXT NOT NULL,
            rel_type            TEXT NOT NULL,
            valid_at            TIMESTAMPTZ,
            invalid_at          TIMESTAMPTZ,
            expired_at          TIMESTAMPTZ,
            reference_time      TIMESTAMPTZ NOT NULL,
            fact                TEXT NOT NULL,
            project             TEXT NOT NULL DEFAULT 'default',
            triple_key          TEXT NOT NULL,
            verification_status TEXT NOT NULL DEFAULT 'candidate',
            confidence          REAL,
            applies_when        JSONB,
            learned_in          TEXT[],
            review_state        TEXT,
            source_file         TEXT,
            created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT knowledge_triples_pkey PRIMARY KEY (id),
            CONSTRAINT knowledge_triples_verification_status_check
                CHECK (verification_status IN
                       ('candidate', 'corroborated', 'disputed', 'confirmed'))
        )
        """
    )
    # Non-unique on purpose: disjoint validity windows legitimately leave
    # SEVERAL live rows on one subject/predicate/object.
    op.execute(
        "CREATE INDEX ix_knowledge_triples_live "
        "ON knowledge_triples (subject_name, rel_type, object_name) "
        "WHERE expired_at IS NULL"
    )
    op.execute(
        "CREATE INDEX ix_knowledge_triples_window ON knowledge_triples (valid_at, invalid_at)"
    )
    # At most one CURRENTLY-OPEN belief per fact. Window-closed rows
    # (invalid_at set) leave the unique's scope but remain live history, which
    # is exactly what the disjoint-window pass produces.
    op.execute(
        "CREATE UNIQUE INDEX ux_knowledge_triples_open ON knowledge_triples (triple_key) "
        "WHERE expired_at IS NULL AND invalid_at IS NULL"
    )
    op.execute(
        "CREATE INDEX ix_knowledge_triples_review ON knowledge_triples (review_state) "
        "WHERE review_state = 'open'"
    )

    # Provenance leaves the fact row entirely: a uuid[] cannot carry per-source
    # metadata, index per-kind reverse lookups, or compute
    # COUNT(DISTINCT origin_key) — which is the corroboration signal, because
    # echo is not evidence (doc 04 §8.3).
    op.execute(
        """
        CREATE TABLE fact_sources (
            id          UUID NOT NULL,
            fact_id     UUID NOT NULL REFERENCES knowledge_triples(id) ON DELETE CASCADE,
            source_kind TEXT,
            source_ref  TEXT,
            origin_key  TEXT,
            detail      JSONB,
            created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT fact_sources_pkey PRIMARY KEY (id),
            CONSTRAINT fact_sources_fact_kind_ref_key UNIQUE (fact_id, source_kind, source_ref)
        )
        """
    )
    # The member-source reverse lookup — "which facts does memory X assert" —
    # the role the removed source_memory_ids GIN played.
    op.execute(
        "CREATE INDEX ix_fact_sources_kind_ref ON fact_sources (source_kind, source_ref)"
    )
    op.execute("CREATE INDEX ix_fact_sources_fact ON fact_sources (fact_id)")

    # ------------------------------------------------------------------
    # knowledge_articles + article_citations — Layer 3 (doc 04 §8.8)
    # ------------------------------------------------------------------
    op.execute(
        """
        CREATE TABLE knowledge_articles (
            id             UUID NOT NULL,
            subject_key    TEXT NOT NULL,
            project        TEXT NOT NULL,
            title          TEXT,
            content        TEXT NOT NULL,
            status         TEXT NOT NULL DEFAULT 'candidate',
            confidence     REAL,
            applies_when   JSONB,
            learned_in     TEXT[],
            synthesized_at TIMESTAMPTZ,
            fact_set_hash  TEXT,
            review_state   TEXT,
            superseded_by  UUID REFERENCES knowledge_articles(id),
            created_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT knowledge_articles_pkey PRIMARY KEY (id),
            CONSTRAINT knowledge_articles_status_check
                CHECK (status IN ('candidate', 'corroborated', 'disputed',
                                  'confirmed', 'superseded'))
        )
        """
    )
    # Exactly one live article per subject.
    op.execute(
        "CREATE UNIQUE INDEX ux_knowledge_articles_live ON knowledge_articles (project, subject_key) "
        "WHERE status <> 'superseded'"
    )
    op.execute(
        "CREATE INDEX ix_knowledge_articles_review ON knowledge_articles (review_state) "
        "WHERE review_state = 'open'"
    )

    # fact_id takes a HARD FK — the deliberate contrast with §8.3's soft
    # endpoint refs. Facts are invalidate-not-delete (rows are never deleted),
    # so the hard FK is safe, and it buys integrity at the one place a dangling
    # citation would be a truth catastrophe: a dead citation under a
    # corroborated badge.
    op.execute(
        """
        CREATE TABLE article_citations (
            id         UUID NOT NULL,
            article_id UUID NOT NULL REFERENCES knowledge_articles(id) ON DELETE CASCADE,
            fact_id    UUID NOT NULL REFERENCES knowledge_triples(id),
            claim_span INT4RANGE,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT article_citations_pkey PRIMARY KEY (id)
        )
        """
    )
    op.execute("CREATE INDEX ix_article_citations_article ON article_citations (article_id)")

    # ------------------------------------------------------------------
    # Code graph (doc 04 §6)
    # ------------------------------------------------------------------
    # Repo-scoped, owner-qualified, and it never joins the memory-side entity
    # graph. index_debt lands inert — no doc 19 §3 row and no task list names
    # it (inventory F-13), so it lands with the table that owns it.
    op.execute(
        """
        CREATE TABLE repositories (
            id                  UUID NOT NULL,
            name                VARCHAR(255) NOT NULL,
            url                 VARCHAR(1024),
            local_path          VARCHAR(1024),
            provider            VARCHAR(50) NOT NULL DEFAULT 'local',
            default_branch      VARCHAR(100) NOT NULL DEFAULT 'main',
            auth_token_ref      VARCHAR(255),
            last_indexed_commit VARCHAR(64),
            last_indexed_at     TIMESTAMPTZ,
            index_debt          JSONB,
            auto_sync           BOOLEAN NOT NULL,
            status              VARCHAR(20) NOT NULL,
            status_message      VARCHAR(500),
            created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT repositories_pkey PRIMARY KEY (id)
        )
        """
    )
    # Partial: the repo_sync filter only ever wants auto-sync repos.
    op.execute(
        "CREATE INDEX ix_repositories_auto_sync ON repositories (id) WHERE auto_sync = true"
    )
    op.execute(
        "CREATE TRIGGER repositories_touch_updated_at BEFORE UPDATE "
        "ON repositories FOR EACH ROW EXECUTE FUNCTION touch_updated_at()"
    )

    op.execute(
        """
        CREATE TABLE code_files (
            id              UUID NOT NULL,
            repo_id         UUID NOT NULL REFERENCES repositories(id) ON DELETE CASCADE,
            file_path       VARCHAR(1024) NOT NULL,
            language        VARCHAR(50),
            last_commit_sha VARCHAR(64),
            content_hash    VARCHAR(64),
            indexed_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT code_files_pkey PRIMARY KEY (id)
        )
        """
    )
    op.execute("CREATE INDEX ix_code_files_repo_path ON code_files (repo_id, file_path)")

    op.execute(
        """
        CREATE TABLE code_symbols (
            id                  UUID NOT NULL,
            file_id             UUID NOT NULL REFERENCES code_files(id) ON DELETE CASCADE,
            name                VARCHAR(500) NOT NULL,
            kind                VARCHAR(50) NOT NULL,
            line_start          INTEGER NOT NULL,
            line_end            INTEGER NOT NULL,
            signature           TEXT,
            docstring           TEXT,
            visibility          VARCHAR(20),
            parent_symbol_id    UUID REFERENCES code_symbols(id) ON DELETE SET NULL,
            source_code         TEXT NOT NULL,
            summary             TEXT,
            enrichment_status   VARCHAR(20) NOT NULL DEFAULT 'pending',
            enrichment_priority INTEGER NOT NULL DEFAULT 0,
            enrichment_attempts INTEGER NOT NULL DEFAULT 0,
            CONSTRAINT code_symbols_pkey PRIMARY KEY (id)
        )
        """
    )
    op.execute("CREATE INDEX ix_code_symbols_file_id ON code_symbols (file_id)")
    # THE enrichment backlog. There is no queue table — enrichment_queue was
    # dormant scaffolding with zero references and is dropped (inventory §8).
    op.execute(
        "CREATE INDEX ix_code_symbols_enrichment_pending "
        "ON code_symbols (enrichment_attempts, enrichment_priority DESC) "
        "WHERE enrichment_status = 'pending'"
    )

    # kind is polymorphic: communities and processes are node KINDS, not
    # separate tables. Keys are owner-qualified (name::file_path::owner) so
    # method-level nodes resolve without collision.
    op.execute(
        """
        CREATE TABLE code_graph_nodes (
            id         BIGSERIAL,
            repo_id    UUID NOT NULL REFERENCES repositories(id) ON DELETE CASCADE,
            kind       VARCHAR(20) NOT NULL,
            key        VARCHAR(1024) NOT NULL,
            label      VARCHAR(500),
            properties JSONB DEFAULT '{}'::jsonb,
            CONSTRAINT code_graph_nodes_pkey PRIMARY KEY (id),
            CONSTRAINT code_graph_nodes_repo_id_kind_key_key UNIQUE (repo_id, kind, key)
        )
        """
    )

    op.execute(
        """
        CREATE TABLE code_edges (
            id          BIGSERIAL,
            repo_id     UUID NOT NULL REFERENCES repositories(id) ON DELETE CASCADE,
            source_kind VARCHAR(20) NOT NULL,
            source_key  VARCHAR(1024) NOT NULL,
            target_kind VARCHAR(20) NOT NULL,
            target_key  VARCHAR(1024) NOT NULL,
            edge_type   VARCHAR(50) NOT NULL,
            properties  JSONB DEFAULT '{}'::jsonb,
            CONSTRAINT code_edges_pkey PRIMARY KEY (id),
            CONSTRAINT code_edges_repo_id_source_kind_source_key_target_kind_targe_key
                UNIQUE (repo_id, source_kind, source_key, target_kind, target_key, edge_type)
        )
        """
    )
    op.execute("CREATE INDEX ix_code_edges_repo_type ON code_edges (repo_id, edge_type)")
    op.execute("CREATE INDEX ix_code_edges_repo_source ON code_edges (repo_id, source_key)")
    op.execute("CREATE INDEX ix_code_edges_repo_target ON code_edges (repo_id, target_key)")
    op.execute(
        "CREATE INDEX ix_code_edges_covering "
        "ON code_edges (repo_id, edge_type, source_key, target_key)"
    )

    # A registry-level association only — two projects referencing the same
    # remote own the SAME repo and its one code graph, not private copies. This
    # bridges the two graphs without merging them (doc 04 §8.7).
    op.execute(
        """
        CREATE TABLE project_repositories (
            project    TEXT NOT NULL,
            repo_id    UUID NOT NULL REFERENCES repositories(id),
            added_from TEXT,
            opt_out    BOOLEAN NOT NULL DEFAULT false,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT project_repositories_pkey PRIMARY KEY (project, repo_id)
        )
        """
    )

    # ------------------------------------------------------------------
    # Operations, auth, chat, LLM config (doc 04 §7)
    # ------------------------------------------------------------------
    # The polymorphic retry tracker — the substrate under honest partial
    # results. After Phase 5, derive_memory_failed_step records or resolves a
    # row here PER MEMORY, never collapsed to a batch pass/fail.
    op.execute(
        """
        CREATE TABLE pipeline_failures (
            id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            entity_type     VARCHAR(50) NOT NULL,
            entity_id       UUID NOT NULL,
            pipeline_name   VARCHAR(50) NOT NULL,
            failed_step     VARCHAR(100) NOT NULL,
            error_message   TEXT,
            attempts        INTEGER NOT NULL DEFAULT 1,
            first_failed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            last_attempt_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            resolved_at     TIMESTAMPTZ,
            metadata        JSONB NOT NULL DEFAULT '{}'::jsonb
        )
        """
    )
    # One OPEN failure per entity+pipeline.
    op.execute(
        "CREATE UNIQUE INDEX idx_pipeline_failures_unresolved "
        "ON pipeline_failures (entity_type, entity_id, pipeline_name) "
        "WHERE resolved_at IS NULL"
    )
    op.execute(
        "CREATE INDEX idx_pipeline_failures_pipeline_name ON pipeline_failures (pipeline_name) "
        "WHERE resolved_at IS NULL"
    )
    op.execute(
        "CREATE INDEX idx_pipeline_failures_resolved_at ON pipeline_failures (resolved_at) "
        "WHERE resolved_at IS NOT NULL"
    )

    # The live JWT revocation store, swept by token_blocklist_cleanup. Only the
    # UNIQUE lands: the pre-baseline schema also carried a plain btree on jti,
    # fully redundant under it, and doc 04 §7 specifies only jti UNIQUE
    # (inventory F-12).
    op.execute(
        """
        CREATE TABLE token_blocklist (
            id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            jti        VARCHAR(64) NOT NULL UNIQUE,
            expires_at TIMESTAMPTZ NOT NULL,
            revoked_at TIMESTAMPTZ DEFAULT now()
        )
        """
    )

    # Exists, unwired — a named gap, not a shipped feature. The activation is
    # a later phase's read path, so the schema carries over unchanged.
    op.execute(
        """
        CREATE TABLE api_keys (
            id           UUID NOT NULL,
            name         VARCHAR(255) NOT NULL,
            key_hash     VARCHAR(255) NOT NULL UNIQUE,
            scopes       JSONB NOT NULL,
            profile      VARCHAR(100),
            created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
            last_used_at TIMESTAMPTZ,
            expires_at   TIMESTAMPTZ,
            CONSTRAINT api_keys_pkey PRIMARY KEY (id)
        )
        """
    )

    op.execute(
        """
        CREATE TABLE conversations (
            id          UUID NOT NULL,
            title       TEXT,
            is_archived BOOLEAN NOT NULL DEFAULT false,
            created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT conversations_pkey PRIMARY KEY (id)
        )
        """
    )
    op.execute(
        "CREATE TRIGGER conversations_touch_updated_at BEFORE UPDATE "
        "ON conversations FOR EACH ROW EXECUTE FUNCTION touch_updated_at()"
    )
    op.execute(
        """
        CREATE TABLE messages (
            id              UUID NOT NULL,
            conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
            role            VARCHAR NOT NULL,
            content         TEXT NOT NULL,
            context         JSONB,
            created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT messages_pkey PRIMARY KEY (id)
        )
        """
    )

    # Six inline rows, PK (purpose). darkmem is not an LLM proxy, so the
    # provider/profile/ml_profile indirection is gone: llm_providers,
    # llm_profiles and ml_profiles never exist in the baseline, and their three
    # FK columns go with them (inventory §8, F-08 — none was named *_ref).
    # classifier_kind replaces the deleted ml_profiles reference.
    # The six rows themselves are written by the setup wizard's finalize step
    # from app/services/llm_seed.py, never by a migration.
    op.execute(
        """
        CREATE TABLE llm_purpose_configs (
            purpose         VARCHAR(64) PRIMARY KEY,
            model           VARCHAR(255) NOT NULL,
            dimensions      INTEGER,
            reasoning       BOOLEAN NOT NULL DEFAULT false,
            -- The sole vendor-quirk home (doc 04 §7, doc 11 §4). The `provider`
            -- column A.2 showed at HEAD is dropped (F-10, decided by T1.01):
            -- nothing ever dispatched on it — the wizard wrote it as a verbatim
            -- copy of api_kind and every read carried it along unused — so a
            -- second vendor column could only ever drift away from the one that
            -- decides behaviour.
            api_kind        VARCHAR(32) NOT NULL DEFAULT 'openai',
            base_url        VARCHAR(512) NOT NULL DEFAULT '',
            api_key         VARCHAR(1024),
            params          JSONB NOT NULL DEFAULT '{}'::jsonb,
            classifier_kind VARCHAR(16),
            updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT llm_purpose_configs_classifier_kind_check
                CHECK (classifier_kind IS NULL OR classifier_kind IN ('llm', 'local'))
        )
        """
    )

    # ------------------------------------------------------------------
    # documents + blocks — the PKM expansion horizon (doc 04 §8.5)
    # ------------------------------------------------------------------
    # Land empty and INERT: nothing writes them until the PKM pipeline
    # (TH1.02). They are here rather than in T0.13 because the
    # block_embeddings registry template references blocks(id), so a
    # fingerprint registration fails while the table is absent — the same
    # lands-here/labelled-there split the four templates already take
    # (T0.12c lands, T0.13 labels). T0.13 keeps repo_ids[], the inert
    # labelling, and the no-writer assertion.
    op.execute(
        """
        CREATE TABLE documents (
            id           UUID NOT NULL,
            project      TEXT NOT NULL,
            title        TEXT,
            source_type  TEXT,
            uri          TEXT,
            content_hash TEXT,
            properties   JSONB,
            created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT documents_pkey PRIMARY KEY (id)
        )
        """
    )
    # Identity key: re-filing the same source finds and re-ingests the
    # existing row (content_hash gates the actual work) instead of minting a
    # duplicate. uri-less sources (ad-hoc notes) are identified by id.
    op.execute(
        "CREATE UNIQUE INDEX ux_documents_project_uri ON documents (project, uri) "
        "WHERE uri IS NOT NULL"
    )
    op.execute(
        "CREATE TRIGGER documents_touch_updated_at BEFORE UPDATE "
        "ON documents FOR EACH ROW EXECUTE FUNCTION touch_updated_at()"
    )

    # A block is simultaneously the chunk unit, the citation anchor, the link
    # endpoint and the transclusion target. parent_id CASCADE makes the tree
    # delete take its subtree; re-ingest strips blocks by document_id before
    # re-chunking (strip-before-rewrite generalised).
    op.execute(
        """
        CREATE TABLE blocks (
            id          UUID NOT NULL,
            document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
            parent_id   UUID REFERENCES blocks(id) ON DELETE CASCADE,
            order_index INTEGER,
            type        TEXT,
            text        TEXT,
            properties  JSONB,
            char_span   INT4RANGE,
            CONSTRAINT blocks_pkey PRIMARY KEY (id)
        )
        """
    )
    op.execute("CREATE INDEX ix_blocks_document_order ON blocks (document_id, order_index)")
    op.execute("CREATE INDEX ix_blocks_parent ON blocks (parent_id)")

    # ------------------------------------------------------------------
    # events — the durable, append-only operation stream (doc 04 §8.1)
    # ------------------------------------------------------------------
    # The ONE declaratively partitioned table in the schema. memories is
    # deliberately not partitioned (a range key would have to enter every
    # unique/PK constraint, breaking its superseded_by self-FK, memory_tags,
    # memory_crossrefs, the embedding-child FKs and the composite (id, project)
    # FK), and the per-fingerprint embedding children already ARE the embedding
    # partitioning.
    #
    # bigint key: append-heavy and never referenced by a uuid FK. The partition
    # key must sit in the PK, and nothing joins events by id, so folding
    # created_at into the composite PK costs nothing.
    #
    op.execute(
        """
        CREATE TABLE events (
            id         BIGINT GENERATED ALWAYS AS IDENTITY,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            event_type TEXT NOT NULL,
            object_type TEXT NOT NULL,
            object_id  UUID,
            project    TEXT,
            actor      TEXT,
            api_key_id UUID,
            source     TEXT,
            payload    JSONB NOT NULL DEFAULT '{}'::jsonb,
            CONSTRAINT events_pkey PRIMARY KEY (id, created_at)
        ) PARTITION BY RANGE (created_at)
        """
    )

    # Append-only is enforced structurally, not by convention (doc 04 §8.1).
    # Role-agnostic on purpose: a REVOKE-based owner/app split would not survive
    # dump/restore and would complicate the one-image surface.
    op.execute(
        """
        CREATE FUNCTION events_forbid_write() RETURNS trigger AS $$
        BEGIN
            RAISE EXCEPTION
                'events is append-only: % is forbidden (doc 04 8.1)', TG_OP
                USING ERRCODE = 'restrict_violation';
        END $$ LANGUAGE plpgsql
        """
    )

    # Two triggers, because one cannot cover all three verbs: TRUNCATE fires
    # only statement-level, UPDATE/DELETE are guarded per row.
    op.execute(
        "CREATE TRIGGER events_forbid_row BEFORE UPDATE OR DELETE ON events "
        "FOR EACH ROW EXECUTE FUNCTION events_forbid_write()"
    )
    op.execute(
        "CREATE TRIGGER events_forbid_truncate BEFORE TRUNCATE ON events "
        "FOR EACH STATEMENT EXECUTE FUNCTION events_forbid_write()"
    )

    # Every path that creates a monthly child goes through this function, so the
    # per-child TRUNCATE guard can never be forgotten by one of them. Measured on
    # PostgreSQL 17: a row-level trigger on a partitioned parent DOES cascade to
    # children (present and future), but a statement-level BEFORE TRUNCATE
    # trigger does NOT — `TRUNCATE events_202607` on a child bypasses the
    # parent's trigger entirely and silently erases that month of the audit
    # trail. Hence a truncate trigger on the parent AND on every child.
    #
    # Concurrency: two callers can reach a fresh month at once (boot racing the
    # cleanup arm), and `CREATE TABLE IF NOT EXISTS ... PARTITION OF` is NOT
    # atomic against that — the loser raises duplicate_table. Caught and treated
    # as success, because the winner produced exactly the row this call wanted.
    op.execute(
        """
        CREATE FUNCTION events_ensure_partition(month_start date)
        RETURNS text AS $$
        DECLARE
            -- Normalise first: a mid-month argument would otherwise create a
            -- child named for the month but bounded [the 15th, the 15th), which
            -- then blocks the correctly-aligned partition forever.
            m0         date := date_trunc('month', month_start)::date;
            m1         date := (date_trunc('month', month_start) + interval '1 month')::date;
            child      text := 'events_' || to_char(m0, 'YYYYMM');
            guard      text := 'events_' || to_char(m0, 'YYYYMM') || '_forbid_truncate';
            -- Pinned to UTC midnight by construction. Rendering these back out
            -- with %L always carries an offset, so the literal denotes the same
            -- instant whatever the session TimeZone happens to be.
            lo         timestamptz := (m0::text || ' 00:00:00+00')::timestamptz;
            hi         timestamptz := (m1::text || ' 00:00:00+00')::timestamptz;
        BEGIN
            -- The bounds MUST carry an explicit UTC offset. `events.created_at`
            -- is timestamptz, so a bare date literal is resolved against the
            -- session TimeZone at DDL time: create one month under UTC and the
            -- next under a +07 session and the pair silently leaves a 7-hour
            -- hole, after which an insert in the gap raises "no partition of
            -- relation events found for row" — which propagates out through
            -- record_event and fails the request being journaled. pg_dump emits
            -- partition bounds the same way, for the same reason.
            EXECUTE format(
                'CREATE TABLE IF NOT EXISTS %I PARTITION OF events '
                'FOR VALUES FROM (%L) TO (%L)', child, lo, hi);
            -- Match the trigger on the child's OID, not on a bare relname: a
            -- same-named table in any other schema would otherwise satisfy this
            -- check and the real child would silently ship unguarded.
            IF NOT EXISTS (
                SELECT 1 FROM pg_trigger t
                WHERE t.tgrelid = to_regclass(child)
                  AND t.tgname = guard
                  AND NOT t.tgisinternal
            ) THEN
                EXECUTE format(
                    'CREATE TRIGGER %I BEFORE TRUNCATE ON %I '
                    'FOR EACH STATEMENT EXECUTE FUNCTION events_forbid_write()',
                    guard, child);
            END IF;
            RETURN child;
        EXCEPTION
            WHEN duplicate_table OR duplicate_object THEN
                RETURN child;
        END $$ LANGUAGE plpgsql
        """
    )

    # A RANGE-partitioned parent with no matching child REJECTS every insert,
    # and neither doc 04 §8.1 nor doc 19 §9 says whether the baseline lands
    # month-0 (inventory F-15). It must: the first events write happens as soon
    # as the journaling ships. Create the current and next month; the boot
    # reconciliation and the partition-maintenance arm on
    # pipeline_failure_cleanup keep it ahead of need from there.
    op.execute(
        """
        SELECT events_ensure_partition(
            date_trunc('month', now() AT TIME ZONE 'UTC')::date);
        """
    )
    op.execute(
        """
        SELECT events_ensure_partition(
            (date_trunc('month', now() AT TIME ZONE 'UTC')
             + interval '1 month')::date);
        """
    )

    # Reconstructs one object's timeline. Accepted limitation: bigint-keyed
    # code-graph objects carry their key in payload, so their timelines are
    # payload-queried and cannot use this index — a deliberate trade.
    op.execute(
        "CREATE INDEX ix_events_object ON events (object_type, object_id, created_at)"
    )
    # The calendar date bucket MUST use AT TIME ZONE 'UTC': a bare
    # created_at::date on a timestamptz is only STABLE (it reads the session
    # TimeZone GUC) so it cannot be indexed, and the UTC form also fixes what
    # "a day" means on the calendar.
    op.execute(
        "CREATE INDEX ix_events_day "
        "ON events (project, ((created_at AT TIME ZONE 'UTC')::date))"
    )


def downgrade() -> None:
    # Drop every per-fingerprint child table the registry created. The set is
    # not known at migration time, so walk pg_tables for all EIGHT parent
    # patterns — the four that exist today plus the four target-new families
    # (inventory F-17: the pre-baseline sweep covered only four and would
    # strand the rest).
    op.execute(
        """
        DO $$
        DECLARE
            t record;
        BEGIN
            FOR t IN
                SELECT tablename FROM pg_tables
                WHERE schemaname = 'public'
                  AND (tablename LIKE 'memory_embeddings\\_\\_%'
                       OR tablename LIKE 'entity_embeddings\\_\\_%'
                       OR tablename LIKE 'code_chunk_embeddings\\_\\_%'
                       OR tablename LIKE 'entity_embedding_cache\\_\\_%'
                       OR tablename LIKE 'block_embeddings\\_\\_%'
                       OR tablename LIKE 'relation_embeddings\\_\\_%'
                       OR tablename LIKE 'article_embeddings\\_\\_%'
                       OR tablename LIKE 'triple_embeddings\\_\\_%')
            LOOP
                EXECUTE format('DROP TABLE IF EXISTS %I CASCADE', t.tablename);
            END LOOP;
        END $$;
        """
    )

    for table in (
        # pass two — dropped before the pass-one tables they reference
        "events",
        "llm_purpose_configs",
        "messages",
        "conversations",
        "api_keys",
        "token_blocklist",
        "pipeline_failures",
        "project_repositories",
        "code_edges",
        "code_graph_nodes",
        "code_symbols",
        "code_files",
        "repositories",
        "article_citations",
        "knowledge_articles",
        "fact_sources",
        "knowledge_triples",
        "blocks",
        "documents",
        "memory_buffer",
        "memory_community_members",
        "memory_communities",
        "memory_relations",
        "memory_access_stats",
        "memory_crossrefs",
        "projects",
        # pass one
        "entity_relations",
        "entities",
        "memory_tags",
        "tags",
        "memories",
        "embedders",
        "config",
    ):
        op.execute(f"DROP TABLE IF EXISTS {table} CASCADE")

    op.execute("DROP FUNCTION IF EXISTS touch_updated_at()")
    op.execute("DROP FUNCTION IF EXISTS memories_fts_trigger()")
    op.execute("DROP TYPE IF EXISTS memory_status")
