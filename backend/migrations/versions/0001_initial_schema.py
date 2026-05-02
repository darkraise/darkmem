"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-04-29

Single greenfield schema. Consolidated migration that produces the final
post-per-fingerprint embedding layout in one shot. Includes:

  - Core tables (api_keys, memories, tags, memory_tags, config, audit_log)
  - Chat tables (conversations, messages)
  - Code indexing (repositories, code_files, code_symbols)
  - Knowledge graph (entities, entity_relations, code_graph_nodes, code_edges)
  - Knowledge triples + memory crossrefs
  - Embedder registry (``embedders``); per-fingerprint child tables
    (``memory_embeddings__<slug>``, ``entity_embeddings__<slug>``,
    ``code_chunk_embeddings__<slug>``, ``entity_embedding_cache__<slug>``)
    are created lazily by ``EmbedderRegistry`` the first time a fingerprint
    is observed, so the migration only seeds the parent registry row.
  - Full-text search on memories (tsvector + GIN + trigger)
  - Pipeline operations (enrichment_queue, pipeline_failures)
  - Auth + revocation (token_blocklist)
"""
from collections.abc import Sequence
from typing import Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '0001'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # -- Extensions + types --
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.execute("CREATE TYPE memory_status AS ENUM ('active', 'deprecated', 'superseded')")

    # -- Core tables --
    op.create_table('api_keys',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('key_hash', sa.String(255), nullable=False),
        sa.Column('scopes', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('profile', sa.String(100)),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('last_used_at', sa.DateTime(timezone=True)),
        sa.Column('expires_at', sa.DateTime(timezone=True)),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('key_hash'),
    )

    op.create_table('config',
        sa.Column('key', sa.String(255), nullable=False),
        sa.Column('value', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.PrimaryKeyConstraint('key'),
    )

    op.create_table('audit_log',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('action', sa.String(50), nullable=False),
        sa.Column('memory_id', sa.UUID()),
        sa.Column('api_key_id', sa.UUID()),
        sa.Column('details', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('timestamp', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )

    op.create_table('tags',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('category', sa.String(50)),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name'),
    )

    op.create_table('memories',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('source', sa.String(100), nullable=False),
        sa.Column('source_agent', sa.String(255)),
        sa.Column('memory_type', sa.String(50)),
        sa.Column('importance', sa.Float(), nullable=False),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True)),
        sa.Column('is_archived', sa.Boolean(), nullable=False),
        sa.Column('classified_type', sa.String(50)),
        sa.Column('classified_confidence', sa.Float()),
        sa.Column('llm_classified_type', sa.String(50)),
        sa.Column('llm_summary', sa.Text()),
        sa.Column('llm_emotions', postgresql.JSONB()),
        sa.Column('llm_flags', postgresql.JSONB()),
        sa.Column('project', sa.Text(), nullable=False, server_default='default'),
        sa.Column(
            'status',
            postgresql.ENUM('active', 'deprecated', 'superseded', name='memory_status', create_type=False),
            nullable=False,
            server_default='active',
        ),
        sa.Column('superseded_by', postgresql.UUID(as_uuid=True)),
        sa.Column('technologies', postgresql.ARRAY(sa.Text()), nullable=False, server_default='{}'),
        sa.Column('confidence', sa.REAL(), nullable=False, server_default='0.75'),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['superseded_by'], ['memories.id'], name='fk_memories_superseded_by', ondelete='SET NULL'),
        sa.CheckConstraint(
            "status != 'superseded' OR superseded_by IS NOT NULL",
            name='chk_superseded_has_pointer',
        ),
    )

    op.create_table('memory_tags',
        sa.Column('memory_id', sa.UUID(), nullable=False),
        sa.Column('tag_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['memory_id'], ['memories.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['tag_id'], ['tags.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('memory_id', 'tag_id'),
    )

    # -- Chat tables --
    op.create_table('conversations',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('title', sa.Text()),
        sa.Column('is_archived', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )

    op.create_table('messages',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('conversation_id', sa.UUID(), nullable=False),
        sa.Column('role', sa.String(), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('context', postgresql.JSONB(astext_type=sa.Text())),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['conversation_id'], ['conversations.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )

    # -- Code indexing --
    op.create_table('repositories',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('url', sa.String(1024)),
        sa.Column('local_path', sa.String(1024)),
        sa.Column('provider', sa.String(50), nullable=False),
        sa.Column('default_branch', sa.String(100), nullable=False),
        sa.Column('auth_token_ref', sa.String(255)),
        sa.Column('last_indexed_commit', sa.String(64)),
        sa.Column('last_indexed_at', sa.DateTime(timezone=True)),
        sa.Column('sync_interval_minutes', sa.Integer(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('status', sa.String(20), nullable=False),
        sa.Column('status_message', sa.String(500)),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )

    op.create_table('code_files',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('repo_id', sa.UUID(), nullable=False),
        sa.Column('file_path', sa.String(1024), nullable=False),
        sa.Column('language', sa.String(50)),
        sa.Column('last_commit_sha', sa.String(64)),
        sa.Column('content_hash', sa.String(64)),
        sa.Column('indexed_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['repo_id'], ['repositories.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    # Phase 3 of the indexer hits this lookup once per changed file; without
    # the compound index the planner sequential-scans on repo_id which grows
    # with file count.
    op.execute(
        "CREATE INDEX ix_code_files_repo_path ON code_files(repo_id, file_path)"
    )

    op.create_table('code_symbols',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('file_id', sa.UUID(), nullable=False),
        sa.Column('name', sa.String(500), nullable=False),
        sa.Column('kind', sa.String(50), nullable=False),
        sa.Column('line_start', sa.Integer(), nullable=False),
        sa.Column('line_end', sa.Integer(), nullable=False),
        sa.Column('signature', sa.Text()),
        sa.Column('docstring', sa.Text()),
        sa.Column('visibility', sa.String(20)),
        sa.Column('parent_symbol_id', sa.UUID()),
        sa.Column('source_code', sa.Text(), nullable=False),
        sa.Column('summary', sa.Text()),
        sa.Column('enrichment_status', sa.String(20), nullable=False),
        sa.Column('enrichment_priority', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['file_id'], ['code_files.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['parent_symbol_id'], ['code_symbols.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    # Phase 6/8 join code_symbols on file_id — the FK declaration alone
    # does not create an index, and growing symbol counts make the join
    # increasingly expensive without one.
    op.execute(
        "CREATE INDEX ix_code_symbols_file_id ON code_symbols(file_id)"
    )

    # -- Knowledge graph: entities + relations (no inline embedding column —
    # vectors live in per-fingerprint child tables created by the registry).
    op.create_table('entities',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column('name', sa.String(500), nullable=False),
        sa.Column('entity_type', sa.String(100), nullable=False),
        sa.Column('properties', postgresql.JSONB, server_default=sa.text("'{}'::jsonb")),
        sa.Column('memory_ids', postgresql.ARRAY(postgresql.UUID(as_uuid=True)), server_default=sa.text("'{}'::uuid[]")),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint('name', 'entity_type'),
    )
    op.execute("CREATE INDEX ix_entities_memory_ids ON entities USING gin (memory_ids)")

    op.create_table('entity_relations',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column('source_entity_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('entities.id', ondelete='CASCADE'), nullable=False),
        sa.Column('target_entity_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('entities.id', ondelete='CASCADE'), nullable=False),
        sa.Column('rel_type', sa.String(100), nullable=False),
        sa.Column('properties', postgresql.JSONB, server_default=sa.text("'{}'::jsonb")),
        sa.Column('weight', sa.Float, server_default=sa.text('0.5')),
        sa.Column('memory_ids', postgresql.ARRAY(postgresql.UUID(as_uuid=True)), server_default=sa.text("'{}'::uuid[]")),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint('source_entity_id', 'target_entity_id', 'rel_type'),
    )
    op.execute("CREATE INDEX ix_entity_relations_memory_ids ON entity_relations USING gin (memory_ids)")

    # -- Code graph (replaces Neo4j) --
    op.create_table('code_graph_nodes',
        sa.Column('id', sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column('repo_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('repositories.id', ondelete='CASCADE'), nullable=False),
        sa.Column('kind', sa.String(20), nullable=False),
        sa.Column('key', sa.String(1024), nullable=False),
        sa.Column('label', sa.String(500)),
        sa.Column('properties', postgresql.JSONB, server_default=sa.text("'{}'::jsonb")),
        sa.UniqueConstraint('repo_id', 'kind', 'key'),
    )

    op.create_table('code_edges',
        sa.Column('id', sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column('repo_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('repositories.id', ondelete='CASCADE'), nullable=False),
        sa.Column('source_kind', sa.String(20), nullable=False),
        sa.Column('source_key', sa.String(1024), nullable=False),
        sa.Column('target_kind', sa.String(20), nullable=False),
        sa.Column('target_key', sa.String(1024), nullable=False),
        sa.Column('edge_type', sa.String(50), nullable=False),
        sa.Column('properties', postgresql.JSONB, server_default=sa.text("'{}'::jsonb")),
        sa.UniqueConstraint('repo_id', 'source_kind', 'source_key', 'target_kind', 'target_key', 'edge_type'),
    )
    op.create_index('ix_code_edges_repo_type', 'code_edges', ['repo_id', 'edge_type'])
    op.create_index('ix_code_edges_repo_source', 'code_edges', ['repo_id', 'source_key'])
    op.create_index('ix_code_edges_repo_target', 'code_edges', ['repo_id', 'target_key'])
    op.create_index('ix_code_edges_covering', 'code_edges', ['repo_id', 'edge_type', 'source_key', 'target_key'])

    # -- Knowledge triples (temporal) --
    op.create_table('knowledge_triples',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('subject', sa.Text, nullable=False),
        sa.Column('predicate', sa.String(200), nullable=False),
        sa.Column('object', sa.Text, nullable=False),
        sa.Column('valid_from', sa.Date),
        sa.Column('valid_to', sa.Date),
        sa.Column('confidence', sa.Float, server_default=sa.text('1.0')),
        sa.Column('source_memory_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('memories.id', ondelete='SET NULL')),
        sa.Column('source_file', sa.String(500)),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index('ix_knowledge_triples_subject', 'knowledge_triples', ['subject'])
    op.create_index('ix_knowledge_triples_object', 'knowledge_triples', ['object'])
    op.create_index('ix_knowledge_triples_predicate', 'knowledge_triples', ['predicate'])
    op.create_index('ix_knowledge_triples_valid', 'knowledge_triples', ['valid_from', 'valid_to'])

    # -- Embedder registry. Per-fingerprint child tables (memory_embeddings__<slug>,
    # entity_embeddings__<slug>, code_chunk_embeddings__<slug>,
    # entity_embedding_cache__<slug>) are created on demand by
    # ``EmbedderRegistry.register`` when a new fingerprint is observed.
    op.execute(
        """
        CREATE TABLE embedders (
            fingerprint    TEXT PRIMARY KEY,
            model_id       TEXT NOT NULL,
            dims           INTEGER NOT NULL CHECK (dims > 0),
            source         TEXT NOT NULL CHECK (source = 'llm'),
            registered_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            retired_at     TIMESTAMPTZ
        )
        """
    )

    # -- Full-text search on memories: tsvector column + GIN index + trigger --
    op.execute("ALTER TABLE memories ADD COLUMN search_vector tsvector")
    op.execute("CREATE INDEX ix_memories_fts ON memories USING gin(search_vector)")
    op.execute("""
        CREATE OR REPLACE FUNCTION memories_fts_trigger() RETURNS trigger AS $$
        BEGIN
            NEW.search_vector := to_tsvector('english', COALESCE(NEW.content, ''));
            RETURN NEW;
        END
        $$ LANGUAGE plpgsql
    """)
    op.execute("""
        CREATE TRIGGER memories_fts_update
        BEFORE INSERT OR UPDATE OF content ON memories
        FOR EACH ROW EXECUTE FUNCTION memories_fts_trigger()
    """)

    # -- Token blocklist for JWT revocation --
    op.create_table('token_blocklist',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('jti', sa.String(64), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('revoked_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('jti'),
    )
    op.create_index('ix_token_blocklist_jti', 'token_blocklist', ['jti'])

    # -- Enrichment queue for code symbol enrichment --
    op.create_table('enrichment_queue',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('symbol_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('code_symbols.id', ondelete='CASCADE'), nullable=False),
        sa.Column('status', sa.String(20), nullable=False, server_default=sa.text("'pending'")),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('symbol_id'),
    )

    # -- Pipeline failures (polymorphic retry tracking) --
    op.execute(
        """
        CREATE TABLE pipeline_failures (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            entity_type VARCHAR(50) NOT NULL,
            entity_id UUID NOT NULL,
            pipeline_name VARCHAR(50) NOT NULL,
            failed_step VARCHAR(100) NOT NULL,
            error_message TEXT,
            attempts INTEGER NOT NULL DEFAULT 1,
            first_failed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            last_attempt_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            resolved_at TIMESTAMPTZ,
            metadata JSONB NOT NULL DEFAULT '{}'::jsonb
        )
        """
    )
    op.execute(
        "CREATE UNIQUE INDEX idx_pipeline_failures_unresolved "
        "ON pipeline_failures(entity_type, entity_id, pipeline_name) "
        "WHERE resolved_at IS NULL"
    )
    op.execute(
        "CREATE INDEX idx_pipeline_failures_pipeline_name "
        "ON pipeline_failures(pipeline_name) "
        "WHERE resolved_at IS NULL"
    )
    op.execute(
        "CREATE INDEX idx_pipeline_failures_resolved_at "
        "ON pipeline_failures(resolved_at) "
        "WHERE resolved_at IS NOT NULL"
    )

    # -- Memories: performance + schema-v2 retrieval indexes --
    op.create_index('ix_memories_created_at', 'memories', ['created_at'])
    op.create_index('ix_memories_is_archived', 'memories', ['is_archived'], postgresql_where=sa.text('is_archived = false'))
    op.create_index('ix_memories_project', 'memories', ['project'])
    op.create_index('ix_memories_status', 'memories', ['status'])
    op.create_index('ix_memories_technologies', 'memories', ['technologies'], postgresql_using='gin')

    # -- Memory cross-references (similarity edges) --
    op.create_table('memory_crossrefs',
        sa.Column('memory_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('memories.id', ondelete='CASCADE'), nullable=False),
        sa.Column('related_memory_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('memories.id', ondelete='CASCADE'), nullable=False),
        sa.Column('score', sa.Float(), nullable=False),
        sa.PrimaryKeyConstraint('memory_id', 'related_memory_id'),
    )
    op.create_index('ix_memory_crossrefs_related', 'memory_crossrefs', ['related_memory_id'])

    # -- LLM provider / profile / purpose tables. Replaces the old
    # ``config`` JSONB blobs (llm_providers / llm_profiles / llm_config)
    # so we get DB-enforced uniqueness, FK delete protection,
    # rename support, and an explicit profile_id link from each
    # purpose row (the dropdown reads it directly -- no more
    # reverse-matching by parameter equality).
    op.execute(
        """
        CREATE TABLE llm_providers (
            id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            name                VARCHAR(64) NOT NULL UNIQUE,
            provider            VARCHAR(64) NOT NULL,
            base_url            VARCHAR(512) NOT NULL,
            api_key             VARCHAR(1024),
            api_kind            VARCHAR(32) NOT NULL DEFAULT 'openai',
            supports_embedding  BOOLEAN NOT NULL DEFAULT TRUE,
            created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            api_key_rotated_at  TIMESTAMPTZ
        )
        """
    )
    op.execute(
        """
        CREATE TABLE llm_profiles (
            id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            name          VARCHAR(64) NOT NULL UNIQUE,
            provider_id   UUID NOT NULL REFERENCES llm_providers(id) ON DELETE RESTRICT,
            model         VARCHAR(255) NOT NULL,
            params        JSONB NOT NULL DEFAULT '{}'::jsonb,
            is_embedding  BOOLEAN NOT NULL DEFAULT FALSE,
            reasoning     BOOLEAN NOT NULL DEFAULT FALSE,
            created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
        """
    )
    op.execute(
        """
        CREATE TABLE llm_purpose_configs (
            purpose       VARCHAR(64) PRIMARY KEY,
            provider_id   UUID REFERENCES llm_providers(id) ON DELETE SET NULL,
            profile_id    UUID REFERENCES llm_profiles(id) ON DELETE SET NULL,
            model         VARCHAR(255) NOT NULL,
            dimensions    INTEGER,
            reasoning     BOOLEAN NOT NULL DEFAULT FALSE,
            api_kind      VARCHAR(32) NOT NULL DEFAULT 'openai',
            provider      VARCHAR(64) NOT NULL DEFAULT 'ollama',
            base_url      VARCHAR(512) NOT NULL DEFAULT '',
            api_key       VARCHAR(1024),
            params        JSONB NOT NULL DEFAULT '{}'::jsonb,
            updated_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
        """
    )

    # Seed providers (one row per supported vendor).
    op.execute(
        """
        INSERT INTO llm_providers (name, provider, base_url, api_key, api_kind, supports_embedding) VALUES
            ('ollama', 'ollama', 'http://localhost:11434/v1', NULL, 'ollama', TRUE),
            ('openai', 'openai', 'https://api.openai.com/v1', NULL, 'openai', TRUE),
            ('anthropic', 'anthropic', 'https://api.anthropic.com/v1', NULL, 'anthropic', FALSE),
            ('google', 'google', 'https://generativelanguage.googleapis.com/v1beta/openai', NULL, 'google', TRUE),
            ('deepseek', 'deepseek', 'https://api.deepseek.com/v1', NULL, 'deepseek', FALSE),
            ('zai', 'zai', 'https://api.z.ai/api/paas/v4', NULL, 'zai', TRUE)
        """
    )

    # Seed profiles. provider_id resolves via subquery so the seed stays readable.
    op.execute(
        """
        INSERT INTO llm_profiles (name, provider_id, model, params, is_embedding, reasoning) VALUES
            ('ollama-embedding', (SELECT id FROM llm_providers WHERE name = 'ollama'), 'qwen3-embedding:0.6b', '{}'::jsonb, TRUE, FALSE),
            ('ollama-extraction', (SELECT id FROM llm_providers WHERE name = 'ollama'), 'qwen2.5:3b', '{"temperature": 0}'::jsonb, FALSE, FALSE),
            ('ollama-classification', (SELECT id FROM llm_providers WHERE name = 'ollama'), 'qwen2.5:3b', '{"temperature": 0}'::jsonb, FALSE, FALSE),
            ('ollama-reasoning', (SELECT id FROM llm_providers WHERE name = 'ollama'), 'qwen3:4b', '{"temperature": 0.7}'::jsonb, FALSE, TRUE),
            ('ollama-summarization', (SELECT id FROM llm_providers WHERE name = 'ollama'), 'qwen2.5:3b', '{"temperature": 0.3}'::jsonb, FALSE, FALSE),
            ('ollama-reranker', (SELECT id FROM llm_providers WHERE name = 'ollama'), 'qwen2.5:3b', '{"temperature": 0}'::jsonb, FALSE, FALSE),
            ('openai-embedding', (SELECT id FROM llm_providers WHERE name = 'openai'), 'text-embedding-3-small', '{}'::jsonb, TRUE, FALSE),
            ('openai-embedding-large', (SELECT id FROM llm_providers WHERE name = 'openai'), 'text-embedding-3-large', '{}'::jsonb, TRUE, FALSE),
            ('openai-extraction', (SELECT id FROM llm_providers WHERE name = 'openai'), 'gpt-5.4-mini', '{"temperature": 1, "reasoning_effort": "none", "verbosity": "low", "max_completion_tokens": 2048}'::jsonb, FALSE, FALSE),
            ('openai-nano-extraction', (SELECT id FROM llm_providers WHERE name = 'openai'), 'gpt-5.4-nano', '{"temperature": 1, "reasoning_effort": "none", "verbosity": "low", "max_completion_tokens": 2048}'::jsonb, FALSE, FALSE),
            ('openai-classification', (SELECT id FROM llm_providers WHERE name = 'openai'), 'gpt-5.4-nano', '{"temperature": 1, "reasoning_effort": "none", "verbosity": "low", "max_completion_tokens": 64}'::jsonb, FALSE, FALSE),
            ('openai-reasoning', (SELECT id FROM llm_providers WHERE name = 'openai'), 'gpt-5.4', '{"temperature": 1, "reasoning_effort": "high", "verbosity": "medium", "max_completion_tokens": 4096}'::jsonb, FALSE, TRUE),
            ('openai-summarization', (SELECT id FROM llm_providers WHERE name = 'openai'), 'gpt-5.4-mini', '{"temperature": 1, "reasoning_effort": "none", "verbosity": "medium", "max_completion_tokens": 512}'::jsonb, FALSE, FALSE),
            ('openai-reranker', (SELECT id FROM llm_providers WHERE name = 'openai'), 'gpt-5.4-nano', '{"temperature": 1, "reasoning_effort": "none", "verbosity": "low", "max_completion_tokens": 32}'::jsonb, FALSE, FALSE),
            ('zai-flash-extraction', (SELECT id FROM llm_providers WHERE name = 'zai'), 'glm-4.7-flash', '{"temperature": 0, "max_tokens": 2048}'::jsonb, FALSE, FALSE),
            ('zai-flash-classification', (SELECT id FROM llm_providers WHERE name = 'zai'), 'glm-4.5-flash', '{"temperature": 0, "max_tokens": 64}'::jsonb, FALSE, FALSE),
            ('zai-flash-summarization', (SELECT id FROM llm_providers WHERE name = 'zai'), 'glm-4.5-flash', '{"temperature": 0.3, "max_tokens": 512}'::jsonb, FALSE, FALSE),
            ('zai-flash-reranker', (SELECT id FROM llm_providers WHERE name = 'zai'), 'glm-4.5-flash', '{"temperature": 0, "max_tokens": 32}'::jsonb, FALSE, FALSE),
            ('zai-turbo-extraction', (SELECT id FROM llm_providers WHERE name = 'zai'), 'glm-5-turbo', '{"temperature": 0, "max_tokens": 2048}'::jsonb, FALSE, FALSE),
            ('zai-turbo-classification', (SELECT id FROM llm_providers WHERE name = 'zai'), 'glm-5-turbo', '{"temperature": 0, "max_tokens": 64}'::jsonb, FALSE, FALSE),
            ('zai-turbo-summarization', (SELECT id FROM llm_providers WHERE name = 'zai'), 'glm-5-turbo', '{"temperature": 0.3, "max_tokens": 512}'::jsonb, FALSE, FALSE),
            ('zai-turbo-reranker', (SELECT id FROM llm_providers WHERE name = 'zai'), 'glm-5-turbo', '{"temperature": 0, "max_tokens": 32}'::jsonb, FALSE, FALSE),
            ('zai-turbo-reasoning', (SELECT id FROM llm_providers WHERE name = 'zai'), 'glm-5-turbo', '{"temperature": 0.7, "max_tokens": 4096}'::jsonb, FALSE, TRUE),
            ('deepseek-flash-extraction', (SELECT id FROM llm_providers WHERE name = 'deepseek'), 'deepseek-v4-flash', '{"temperature": 0, "max_tokens": 2048, "thinking": {"type": "disabled"}}'::jsonb, FALSE, FALSE),
            ('deepseek-pro-extraction', (SELECT id FROM llm_providers WHERE name = 'deepseek'), 'deepseek-v4-pro', '{"temperature": 0, "max_tokens": 2048, "thinking": {"type": "disabled"}}'::jsonb, FALSE, FALSE),
            ('deepseek-flash-classification', (SELECT id FROM llm_providers WHERE name = 'deepseek'), 'deepseek-chat', '{"temperature": 0, "max_tokens": 64}'::jsonb, FALSE, FALSE),
            ('deepseek-flash-summarization', (SELECT id FROM llm_providers WHERE name = 'deepseek'), 'deepseek-chat', '{"temperature": 0.3, "max_tokens": 512}'::jsonb, FALSE, FALSE),
            ('deepseek-flash-reranker', (SELECT id FROM llm_providers WHERE name = 'deepseek'), 'deepseek-chat', '{"temperature": 0, "max_tokens": 32}'::jsonb, FALSE, FALSE),
            ('deepseek-flash-reasoning', (SELECT id FROM llm_providers WHERE name = 'deepseek'), 'deepseek-reasoner', '{"temperature": 0.7, "max_tokens": 4096}'::jsonb, FALSE, TRUE),
            ('deepseek-pro-reasoning', (SELECT id FROM llm_providers WHERE name = 'deepseek'), 'deepseek-v4-pro', '{"temperature": 0.7, "max_tokens": 4096}'::jsonb, FALSE, TRUE),
            ('anthropic-haiku-extraction', (SELECT id FROM llm_providers WHERE name = 'anthropic'), 'claude-haiku-4-5', '{"temperature": 0, "max_tokens": 2048}'::jsonb, FALSE, FALSE),
            ('anthropic-sonnet-extraction', (SELECT id FROM llm_providers WHERE name = 'anthropic'), 'claude-sonnet-4-6', '{"temperature": 0, "max_tokens": 2048}'::jsonb, FALSE, FALSE),
            ('google-embedding', (SELECT id FROM llm_providers WHERE name = 'google'), 'gemini-embedding-001', '{}'::jsonb, TRUE, FALSE),
            ('google-lite-extraction', (SELECT id FROM llm_providers WHERE name = 'google'), 'gemini-2.5-flash-lite', '{"temperature": 0, "max_tokens": 2048, "reasoning_effort": "none"}'::jsonb, FALSE, FALSE),
            ('google-flash-extraction', (SELECT id FROM llm_providers WHERE name = 'google'), 'gemini-2.5-flash', '{"temperature": 0, "max_tokens": 2048, "reasoning_effort": "none"}'::jsonb, FALSE, FALSE),
            ('google-flash-classification', (SELECT id FROM llm_providers WHERE name = 'google'), 'gemini-2.5-flash', '{"temperature": 0, "max_tokens": 64, "reasoning_effort": "none"}'::jsonb, FALSE, FALSE),
            ('google-flash-summarization', (SELECT id FROM llm_providers WHERE name = 'google'), 'gemini-2.5-flash', '{"temperature": 0.3, "max_tokens": 512, "reasoning_effort": "none"}'::jsonb, FALSE, FALSE),
            ('google-flash-reranker', (SELECT id FROM llm_providers WHERE name = 'google'), 'gemini-2.5-flash', '{"temperature": 0, "max_tokens": 32, "reasoning_effort": "none"}'::jsonb, FALSE, FALSE),
            ('google-pro-extraction', (SELECT id FROM llm_providers WHERE name = 'google'), 'gemini-2.5-pro', '{"temperature": 0, "max_tokens": 2048, "reasoning_effort": "none"}'::jsonb, FALSE, FALSE),
            ('google-pro-reasoning', (SELECT id FROM llm_providers WHERE name = 'google'), 'gemini-2.5-pro', '{"temperature": 0.7, "max_tokens": 4096, "reasoning_effort": "high"}'::jsonb, FALSE, TRUE),
            ('anthropic-haiku-classification', (SELECT id FROM llm_providers WHERE name = 'anthropic'), 'claude-haiku-4-5', '{"temperature": 0, "max_tokens": 64}'::jsonb, FALSE, FALSE),
            ('anthropic-haiku-summarization', (SELECT id FROM llm_providers WHERE name = 'anthropic'), 'claude-haiku-4-5', '{"temperature": 0.3, "max_tokens": 512}'::jsonb, FALSE, FALSE),
            ('anthropic-haiku-reranker', (SELECT id FROM llm_providers WHERE name = 'anthropic'), 'claude-haiku-4-5', '{"temperature": 0, "max_tokens": 32}'::jsonb, FALSE, FALSE),
            ('anthropic-sonnet-reasoning', (SELECT id FROM llm_providers WHERE name = 'anthropic'), 'claude-sonnet-4-6', '{"temperature": 0.7, "max_tokens": 4096}'::jsonb, FALSE, TRUE)
        """
    )

    # Seed purpose configs with the same defaults as ``Settings.llm_*``.
    op.execute(
        """
        INSERT INTO llm_purpose_configs (purpose, provider_id, model, dimensions, reasoning, api_kind, provider, base_url, params) VALUES
            ('embedding', (SELECT id FROM llm_providers WHERE name = 'ollama'), 'qwen3-embedding:0.6b', 1024, FALSE, 'openai', 'ollama', 'http://localhost:11434/v1', '{}'::jsonb),
            ('extraction', (SELECT id FROM llm_providers WHERE name = 'ollama'), 'qwen2.5:3b', NULL, FALSE, 'openai', 'ollama', 'http://localhost:11434/v1', '{"temperature": 0}'::jsonb),
            ('classification', (SELECT id FROM llm_providers WHERE name = 'ollama'), 'qwen2.5:3b', NULL, FALSE, 'openai', 'ollama', 'http://localhost:11434/v1', '{"temperature": 0}'::jsonb),
            ('reasoning', (SELECT id FROM llm_providers WHERE name = 'ollama'), 'qwen2.5:3b', NULL, FALSE, 'openai', 'ollama', 'http://localhost:11434/v1', '{"temperature": 0.7}'::jsonb),
            ('summarization', (SELECT id FROM llm_providers WHERE name = 'ollama'), 'qwen2.5:3b', NULL, FALSE, 'openai', 'ollama', 'http://localhost:11434/v1', '{"temperature": 0.3}'::jsonb),
            ('reranker', (SELECT id FROM llm_providers WHERE name = 'ollama'), 'qwen2.5:3b', NULL, FALSE, 'openai', 'ollama', 'http://localhost:11434/v1', '{"temperature": 0}'::jsonb)
        """
    )


def downgrade() -> None:
    # Drop every per-fingerprint child table created by the registry. The set
    # isn't known at migration time so we walk pg_tables for the pattern.
    op.execute(
        """
        DO $$
        DECLARE
            t record;
        BEGIN
            FOR t IN
                SELECT tablename FROM pg_tables
                WHERE schemaname = 'public'
                  AND (tablename LIKE 'memory_embeddings__%'
                       OR tablename LIKE 'entity_embeddings__%'
                       OR tablename LIKE 'code_chunk_embeddings__%'
                       OR tablename LIKE 'entity_embedding_cache__%')
            LOOP
                EXECUTE format('DROP TABLE IF EXISTS %I CASCADE', t.tablename);
            END LOOP;
        END $$;
        """
    )

    op.execute("DROP TRIGGER IF EXISTS memories_fts_update ON memories")
    op.execute("DROP FUNCTION IF EXISTS memories_fts_trigger()")

    op.drop_table('memory_crossrefs')
    op.drop_index('ix_memories_technologies', table_name='memories')
    op.drop_index('ix_memories_status', table_name='memories')
    op.drop_index('ix_memories_project', table_name='memories')
    op.drop_index('ix_memories_is_archived', table_name='memories')
    op.drop_index('ix_memories_created_at', table_name='memories')
    op.execute("DROP TABLE IF EXISTS pipeline_failures CASCADE")
    op.drop_table('enrichment_queue')
    op.drop_table('token_blocklist')
    op.execute("DROP TABLE IF EXISTS embedders CASCADE")
    op.drop_table('knowledge_triples')
    op.drop_table('code_edges')
    op.drop_table('code_graph_nodes')
    op.drop_table('entity_relations')
    op.drop_table('entities')
    op.drop_table('code_symbols')
    op.drop_table('code_files')
    op.drop_table('repositories')
    op.drop_table('messages')
    op.drop_table('conversations')
    op.drop_table('memory_tags')
    op.drop_table('memories')
    op.drop_table('tags')
    op.drop_table('audit_log')
    op.drop_table('config')
    op.drop_table('api_keys')
    op.execute("DROP TYPE IF EXISTS memory_status")
    op.execute("DROP EXTENSION IF EXISTS vector")
