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
    op.execute("CREATE INDEX ix_memories_technologies ON memories USING gin (technologies)")
    op.execute("CREATE INDEX ix_memories_fts ON memories USING gin (search_vector)")

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
            created_at  TIMESTAMPTZ DEFAULT now(),
            CONSTRAINT entities_pkey PRIMARY KEY (id),
            CONSTRAINT entities_name_entity_type_key UNIQUE (name, entity_type)
        )
        """
    )
    op.execute("CREATE INDEX ix_entities_memory_ids ON entities USING gin (memory_ids)")

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
    # Reverse-lookup, neighbour and orphan-guard queries filter on the target,
    # which the UNIQUE's source-prefix cannot serve.
    op.execute(
        "CREATE INDEX ix_entity_relations_target ON entity_relations (target_entity_id)"
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

    op.execute("DROP TABLE IF EXISTS entity_relations CASCADE")
    op.execute("DROP TABLE IF EXISTS entities CASCADE")
    op.execute("DROP TABLE IF EXISTS memory_tags CASCADE")
    op.execute("DROP TABLE IF EXISTS tags CASCADE")
    op.execute("DROP TABLE IF EXISTS memories CASCADE")
    op.execute("DROP TABLE IF EXISTS embedders CASCADE")
    op.execute("DROP TABLE IF EXISTS config CASCADE")

    op.execute("DROP FUNCTION IF EXISTS touch_updated_at()")
    op.execute("DROP FUNCTION IF EXISTS memories_fts_trigger()")
    op.execute("DROP TYPE IF EXISTS memory_status")
