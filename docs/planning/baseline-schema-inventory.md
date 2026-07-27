# Baseline schema inventory

**Status:** under construction — Appendix A only. §0–§10 arrive in Task 2 of
[`../superpowers/plans/2026-07-27-baseline-schema-inventory.md`](../superpowers/plans/2026-07-27-baseline-schema-inventory.md).

---

## Appendix A — as-is object manifest, machine-extracted from the six revisions

This appendix is the **current-state** side of the T0.11 reconciliation. It is not a
reading of `backend/migrations/versions/*.py`; it is the schema those six revisions
actually produce, extracted from a database built by `alembic upgrade head` on an empty
scratch database and dropped again immediately afterwards.

Reading the revision files by eye is the failure mode this appendix exists to avoid.
`0001` calls `op.create_table` nineteen times, but the migrated database holds
**twenty-six** tables — five more arrive as raw `CREATE TABLE` inside `op.execute`, plus
Alembic's own `alembic_version`. `0001` calls `op.create_index` twenty-three times, but
the database holds **sixty-three** indexes, the remainder implied by PRIMARY KEY and
UNIQUE constraints. Every completeness check in §2–§9 diffs against the listings below,
so they must be ground truth rather than a transcription.

### How this was produced

```bash
# Step 1 — build a throwaway database from the six revisions
docker exec darkmem-postgres-1 psql -U darkmem -d postgres \
  -c "DROP DATABASE IF EXISTS darkmem_inv_probe;" \
  -c "CREATE DATABASE darkmem_inv_probe;"
cd /root/repositories/darkmem/backend
DATABASE_URL=postgresql+asyncpg://darkmem:darkmem@localhost:5433/darkmem_inv_probe \
  timeout 300 ./.venv/bin/python -m alembic upgrade head

# Step 2 — extract (each query below), pipe-separated, tuples only
D() { docker exec darkmem-postgres-1 psql -U darkmem -d darkmem_inv_probe -tAF'|' -c "$1"; }

# Step 4 — drop the probe database, leaving no residue
docker exec darkmem-postgres-1 psql -U darkmem -d postgres \
  -c "DROP DATABASE IF EXISTS darkmem_inv_probe;"
```

`alembic upgrade head` emitted six `Running upgrade` lines, ending
`0005 -> 0006, drop regex classification columns`.

`darkmem_inv_probe` is dedicated to this task. It is never pointed at `darkmem`
(write-forbidden, no schema on this machine), `darkmem_test` (pytest's alone), or
`darkmem_bench` (benchlib's).

### Assertions — re-run Step 1 + Step 2 and these must reproduce exactly

| Object class | Count | Recorded |
|---|---|---|
| Tables (`relkind` r or p, incl. `alembic_version`) | 26 | A.1 |
| Indexes (`pg_indexes`) | 63 | A.3 |
| Constraints: PRIMARY KEY / FOREIGN KEY / UNIQUE / CHECK | 26 / 19 / 11 / 3 | A.4 |
| User triggers | 1 (`memories_fts_update`) | A.5 |
| Non-extension functions | 1 (`memories_fts_trigger`) | A.6 |
| Enum types | 1 (`memory_status` = active,deprecated,superseded) | A.7 |
| Per-fingerprint `*__<slug>` child tables | **0** | A.1 |
| Migration-seeded `config` rows | 4 (`job:code_enrichment`, `job:pipeline_failure_cleanup`, `job:repo_sync`, `job:token_blocklist_cleanup`) | A.8 |

All eight reproduced exactly on the extraction run of 2026-07-27.

Two of these carry information no reading of the migration files would surface.

**Zero child tables** is the empirical proof of doc 19 §2's claim that the
per-fingerprint partition DDL is runtime, not migration — §6 cites it.

**Four seeded `config` rows against seven registered jobs** (`repo_sync`,
`code_enrichment`, `token_blocklist_cleanup`, `pipeline_failure_cleanup`,
`graph_orphan_cleanup`, `tag_orphan_cleanup`, `expired_memory_cleanup`) means three
job-state rows are created at runtime rather than seeded — a seed-data row for §2 and a
finding for §10.

Note also that `embedders`, `llm_providers`, `llm_purpose_configs` and `tags` all come
up **empty**: the migrations seed no LLM configuration and no embedder registry row. LLM
seeds live in `app/services/llm_seed.py` and are written by the setup wizard's finalize
step; the embedder row is registered at runtime by `embedder_registry.register`.

### A.1 — Tables (`relkind` r = ordinary, p = partitioned)

```
alembic_version|r
api_keys|r
audit_log|r
code_edges|r
code_files|r
code_graph_nodes|r
code_symbols|r
config|r
conversations|r
embedders|r
enrichment_queue|r
entities|r
entity_relations|r
knowledge_triples|r
llm_profiles|r
llm_providers|r
llm_purpose_configs|r
memories|r
memory_crossrefs|r
memory_tags|r
messages|r
ml_profiles|r
pipeline_failures|r
repositories|r
tags|r
token_blocklist|r
```

### A.2 — Columns, with nullability and the SERVER default (empty final field = no server default)

`table_name|ordinal_position|column_name|data_type|is_nullable|column_default`

```
alembic_version|1|version_num|character varying|NO|
api_keys|1|id|uuid|NO|
api_keys|2|name|character varying|NO|
api_keys|3|key_hash|character varying|NO|
api_keys|4|scopes|jsonb|NO|
api_keys|5|profile|character varying|YES|
api_keys|6|created_at|timestamp with time zone|NO|now()
api_keys|7|last_used_at|timestamp with time zone|YES|
api_keys|8|expires_at|timestamp with time zone|YES|
audit_log|1|id|integer|NO|nextval('audit_log_id_seq'::regclass)
audit_log|2|action|character varying|NO|
audit_log|3|memory_id|uuid|YES|
audit_log|4|api_key_id|uuid|YES|
audit_log|5|details|jsonb|NO|
audit_log|6|timestamp|timestamp with time zone|NO|now()
code_edges|1|id|bigint|NO|nextval('code_edges_id_seq'::regclass)
code_edges|2|repo_id|uuid|NO|
code_edges|3|source_kind|character varying|NO|
code_edges|4|source_key|character varying|NO|
code_edges|5|target_kind|character varying|NO|
code_edges|6|target_key|character varying|NO|
code_edges|7|edge_type|character varying|NO|
code_edges|8|properties|jsonb|YES|'{}'::jsonb
code_files|1|id|uuid|NO|
code_files|2|repo_id|uuid|NO|
code_files|3|file_path|character varying|NO|
code_files|4|language|character varying|YES|
code_files|5|last_commit_sha|character varying|YES|
code_files|6|content_hash|character varying|YES|
code_files|7|indexed_at|timestamp with time zone|NO|now()
code_graph_nodes|1|id|bigint|NO|nextval('code_graph_nodes_id_seq'::regclass)
code_graph_nodes|2|repo_id|uuid|NO|
code_graph_nodes|3|kind|character varying|NO|
code_graph_nodes|4|key|character varying|NO|
code_graph_nodes|5|label|character varying|YES|
code_graph_nodes|6|properties|jsonb|YES|'{}'::jsonb
code_symbols|1|id|uuid|NO|
code_symbols|2|file_id|uuid|NO|
code_symbols|3|name|character varying|NO|
code_symbols|4|kind|character varying|NO|
code_symbols|5|line_start|integer|NO|
code_symbols|6|line_end|integer|NO|
code_symbols|7|signature|text|YES|
code_symbols|8|docstring|text|YES|
code_symbols|9|visibility|character varying|YES|
code_symbols|10|parent_symbol_id|uuid|YES|
code_symbols|11|source_code|text|NO|
code_symbols|12|summary|text|YES|
code_symbols|13|enrichment_status|character varying|NO|
code_symbols|14|enrichment_priority|integer|NO|
code_symbols|15|enrichment_attempts|integer|NO|0
config|1|key|character varying|NO|
config|2|value|jsonb|NO|
conversations|1|id|uuid|NO|
conversations|2|title|text|YES|
conversations|3|is_archived|boolean|NO|false
conversations|4|created_at|timestamp with time zone|NO|now()
conversations|5|updated_at|timestamp with time zone|NO|now()
embedders|1|fingerprint|text|NO|
embedders|2|model_id|text|NO|
embedders|3|dims|integer|NO|
embedders|4|source|text|NO|
embedders|5|registered_at|timestamp with time zone|NO|now()
embedders|6|retired_at|timestamp with time zone|YES|
enrichment_queue|1|id|uuid|NO|gen_random_uuid()
enrichment_queue|2|symbol_id|uuid|NO|
enrichment_queue|3|status|character varying|NO|'pending'::character varying
enrichment_queue|4|created_at|timestamp with time zone|YES|now()
entities|1|id|uuid|NO|gen_random_uuid()
entities|2|name|character varying|NO|
entities|3|entity_type|character varying|NO|
entities|4|properties|jsonb|YES|'{}'::jsonb
entities|5|memory_ids|ARRAY|YES|'{}'::uuid[]
entities|6|created_at|timestamp with time zone|YES|now()
entity_relations|1|id|uuid|NO|gen_random_uuid()
entity_relations|2|source_entity_id|uuid|NO|
entity_relations|3|target_entity_id|uuid|NO|
entity_relations|4|rel_type|character varying|NO|
entity_relations|5|properties|jsonb|YES|'{}'::jsonb
entity_relations|6|weight|double precision|YES|0.5
entity_relations|7|memory_ids|ARRAY|YES|'{}'::uuid[]
entity_relations|8|created_at|timestamp with time zone|YES|now()
knowledge_triples|1|id|uuid|NO|gen_random_uuid()
knowledge_triples|2|subject|text|NO|
knowledge_triples|3|predicate|character varying|NO|
knowledge_triples|4|object|text|NO|
knowledge_triples|5|valid_from|date|YES|
knowledge_triples|6|valid_to|date|YES|
knowledge_triples|7|confidence|double precision|YES|1.0
knowledge_triples|8|source_memory_id|uuid|YES|
knowledge_triples|9|source_file|character varying|YES|
knowledge_triples|10|created_at|timestamp with time zone|YES|now()
llm_profiles|1|id|uuid|NO|gen_random_uuid()
llm_profiles|2|name|character varying|NO|
llm_profiles|3|provider_id|uuid|NO|
llm_profiles|4|model|character varying|NO|
llm_profiles|5|params|jsonb|NO|'{}'::jsonb
llm_profiles|6|is_embedding|boolean|NO|false
llm_profiles|7|reasoning|boolean|NO|false
llm_profiles|8|purpose|character varying|YES|
llm_profiles|9|created_at|timestamp with time zone|NO|now()
llm_profiles|10|updated_at|timestamp with time zone|NO|now()
llm_providers|1|id|uuid|NO|gen_random_uuid()
llm_providers|2|name|character varying|NO|
llm_providers|3|provider|character varying|NO|
llm_providers|4|base_url|character varying|NO|
llm_providers|5|api_key|character varying|YES|
llm_providers|6|api_kind|character varying|NO|'openai'::character varying
llm_providers|7|supports_embedding|boolean|NO|true
llm_providers|8|created_at|timestamp with time zone|NO|now()
llm_providers|9|updated_at|timestamp with time zone|NO|now()
llm_providers|10|api_key_rotated_at|timestamp with time zone|YES|
llm_purpose_configs|1|purpose|character varying|NO|
llm_purpose_configs|2|provider_id|uuid|YES|
llm_purpose_configs|3|profile_id|uuid|YES|
llm_purpose_configs|4|ml_profile_id|uuid|YES|
llm_purpose_configs|5|model|character varying|NO|
llm_purpose_configs|6|dimensions|integer|YES|
llm_purpose_configs|7|reasoning|boolean|NO|false
llm_purpose_configs|8|api_kind|character varying|NO|'openai'::character varying
llm_purpose_configs|9|provider|character varying|NO|'ollama'::character varying
llm_purpose_configs|10|base_url|character varying|NO|''::character varying
llm_purpose_configs|11|api_key|character varying|YES|
llm_purpose_configs|12|params|jsonb|NO|'{}'::jsonb
llm_purpose_configs|13|updated_at|timestamp with time zone|NO|now()
memories|1|id|uuid|NO|
memories|2|content|text|NO|
memories|3|source|character varying|NO|
memories|4|source_agent|character varying|YES|
memories|5|memory_type|character varying|YES|
memories|6|importance|double precision|NO|
memories|7|metadata|jsonb|NO|
memories|8|created_at|timestamp with time zone|NO|now()
memories|9|updated_at|timestamp with time zone|NO|now()
memories|10|expires_at|timestamp with time zone|YES|
memories|11|is_archived|boolean|NO|
memories|14|llm_classified_type|character varying|YES|
memories|15|llm_summary|text|YES|
memories|16|llm_emotions|jsonb|YES|
memories|17|llm_flags|jsonb|YES|
memories|18|project|text|NO|'default'::text
memories|19|status|USER-DEFINED|NO|'active'::memory_status
memories|20|superseded_by|uuid|YES|
memories|21|technologies|ARRAY|NO|'{}'::text[]
memories|22|confidence|real|NO|'0.75'::real
memories|23|search_vector|tsvector|YES|
memory_crossrefs|1|memory_id|uuid|NO|
memory_crossrefs|2|related_memory_id|uuid|NO|
memory_crossrefs|3|score|double precision|NO|
memory_tags|1|memory_id|uuid|NO|
memory_tags|2|tag_id|integer|NO|
messages|1|id|uuid|NO|
messages|2|conversation_id|uuid|NO|
messages|3|role|character varying|NO|
messages|4|content|text|NO|
messages|5|context|jsonb|YES|
messages|6|created_at|timestamp with time zone|NO|now()
ml_profiles|1|id|uuid|NO|gen_random_uuid()
ml_profiles|2|name|character varying|NO|
ml_profiles|3|model_repo|character varying|NO|
ml_profiles|4|ttl_seconds|integer|NO|0
ml_profiles|5|created_at|timestamp with time zone|NO|now()
ml_profiles|6|updated_at|timestamp with time zone|NO|now()
pipeline_failures|1|id|uuid|NO|gen_random_uuid()
pipeline_failures|2|entity_type|character varying|NO|
pipeline_failures|3|entity_id|uuid|NO|
pipeline_failures|4|pipeline_name|character varying|NO|
pipeline_failures|5|failed_step|character varying|NO|
pipeline_failures|6|error_message|text|YES|
pipeline_failures|7|attempts|integer|NO|1
pipeline_failures|8|first_failed_at|timestamp with time zone|NO|now()
pipeline_failures|9|last_attempt_at|timestamp with time zone|NO|now()
pipeline_failures|10|resolved_at|timestamp with time zone|YES|
pipeline_failures|11|metadata|jsonb|NO|'{}'::jsonb
repositories|1|id|uuid|NO|
repositories|2|name|character varying|NO|
repositories|3|url|character varying|YES|
repositories|4|local_path|character varying|YES|
repositories|5|provider|character varying|NO|
repositories|6|default_branch|character varying|NO|
repositories|7|auth_token_ref|character varying|YES|
repositories|8|last_indexed_commit|character varying|YES|
repositories|9|last_indexed_at|timestamp with time zone|YES|
repositories|10|auto_sync|boolean|NO|
repositories|11|status|character varying|NO|
repositories|12|status_message|character varying|YES|
repositories|13|created_at|timestamp with time zone|NO|now()
repositories|14|updated_at|timestamp with time zone|NO|now()
tags|1|id|integer|NO|nextval('tags_id_seq'::regclass)
tags|2|name|character varying|NO|
tags|3|category|character varying|YES|
token_blocklist|1|id|uuid|NO|gen_random_uuid()
token_blocklist|2|jti|character varying|NO|
token_blocklist|3|expires_at|timestamp with time zone|NO|
token_blocklist|4|revoked_at|timestamp with time zone|YES|now()
```

### A.3 — Indexes, with full definitions

`tablename|indexname|indexdef`

```
alembic_version|alembic_version_pkc|CREATE UNIQUE INDEX alembic_version_pkc ON public.alembic_version USING btree (version_num)
api_keys|api_keys_key_hash_key|CREATE UNIQUE INDEX api_keys_key_hash_key ON public.api_keys USING btree (key_hash)
api_keys|api_keys_pkey|CREATE UNIQUE INDEX api_keys_pkey ON public.api_keys USING btree (id)
audit_log|audit_log_pkey|CREATE UNIQUE INDEX audit_log_pkey ON public.audit_log USING btree (id)
code_edges|code_edges_pkey|CREATE UNIQUE INDEX code_edges_pkey ON public.code_edges USING btree (id)
code_edges|code_edges_repo_id_source_kind_source_key_target_kind_targe_key|CREATE UNIQUE INDEX code_edges_repo_id_source_kind_source_key_target_kind_targe_key ON public.code_edges USING btree (repo_id, source_kind, source_key, target_kind, target_key, edge_type)
code_edges|ix_code_edges_covering|CREATE INDEX ix_code_edges_covering ON public.code_edges USING btree (repo_id, edge_type, source_key, target_key)
code_edges|ix_code_edges_repo_source|CREATE INDEX ix_code_edges_repo_source ON public.code_edges USING btree (repo_id, source_key)
code_edges|ix_code_edges_repo_target|CREATE INDEX ix_code_edges_repo_target ON public.code_edges USING btree (repo_id, target_key)
code_edges|ix_code_edges_repo_type|CREATE INDEX ix_code_edges_repo_type ON public.code_edges USING btree (repo_id, edge_type)
code_files|code_files_pkey|CREATE UNIQUE INDEX code_files_pkey ON public.code_files USING btree (id)
code_files|ix_code_files_repo_path|CREATE INDEX ix_code_files_repo_path ON public.code_files USING btree (repo_id, file_path)
code_graph_nodes|code_graph_nodes_pkey|CREATE UNIQUE INDEX code_graph_nodes_pkey ON public.code_graph_nodes USING btree (id)
code_graph_nodes|code_graph_nodes_repo_id_kind_key_key|CREATE UNIQUE INDEX code_graph_nodes_repo_id_kind_key_key ON public.code_graph_nodes USING btree (repo_id, kind, key)
code_symbols|code_symbols_pkey|CREATE UNIQUE INDEX code_symbols_pkey ON public.code_symbols USING btree (id)
code_symbols|ix_code_symbols_enrichment_pending|CREATE INDEX ix_code_symbols_enrichment_pending ON public.code_symbols USING btree (enrichment_attempts, enrichment_priority DESC) WHERE ((enrichment_status)::text = 'pending'::text)
code_symbols|ix_code_symbols_file_id|CREATE INDEX ix_code_symbols_file_id ON public.code_symbols USING btree (file_id)
config|config_pkey|CREATE UNIQUE INDEX config_pkey ON public.config USING btree (key)
conversations|conversations_pkey|CREATE UNIQUE INDEX conversations_pkey ON public.conversations USING btree (id)
embedders|embedders_pkey|CREATE UNIQUE INDEX embedders_pkey ON public.embedders USING btree (fingerprint)
enrichment_queue|enrichment_queue_pkey|CREATE UNIQUE INDEX enrichment_queue_pkey ON public.enrichment_queue USING btree (id)
enrichment_queue|enrichment_queue_symbol_id_key|CREATE UNIQUE INDEX enrichment_queue_symbol_id_key ON public.enrichment_queue USING btree (symbol_id)
entities|entities_name_entity_type_key|CREATE UNIQUE INDEX entities_name_entity_type_key ON public.entities USING btree (name, entity_type)
entities|entities_pkey|CREATE UNIQUE INDEX entities_pkey ON public.entities USING btree (id)
entities|ix_entities_memory_ids|CREATE INDEX ix_entities_memory_ids ON public.entities USING gin (memory_ids)
entity_relations|entity_relations_pkey|CREATE UNIQUE INDEX entity_relations_pkey ON public.entity_relations USING btree (id)
entity_relations|entity_relations_source_entity_id_target_entity_id_rel_type_key|CREATE UNIQUE INDEX entity_relations_source_entity_id_target_entity_id_rel_type_key ON public.entity_relations USING btree (source_entity_id, target_entity_id, rel_type)
entity_relations|ix_entity_relations_memory_ids|CREATE INDEX ix_entity_relations_memory_ids ON public.entity_relations USING gin (memory_ids)
entity_relations|ix_entity_relations_target|CREATE INDEX ix_entity_relations_target ON public.entity_relations USING btree (target_entity_id)
knowledge_triples|ix_knowledge_triples_object|CREATE INDEX ix_knowledge_triples_object ON public.knowledge_triples USING btree (object)
knowledge_triples|ix_knowledge_triples_predicate|CREATE INDEX ix_knowledge_triples_predicate ON public.knowledge_triples USING btree (predicate)
knowledge_triples|ix_knowledge_triples_subject|CREATE INDEX ix_knowledge_triples_subject ON public.knowledge_triples USING btree (subject)
knowledge_triples|ix_knowledge_triples_valid|CREATE INDEX ix_knowledge_triples_valid ON public.knowledge_triples USING btree (valid_from, valid_to)
knowledge_triples|knowledge_triples_pkey|CREATE UNIQUE INDEX knowledge_triples_pkey ON public.knowledge_triples USING btree (id)
llm_profiles|llm_profiles_name_key|CREATE UNIQUE INDEX llm_profiles_name_key ON public.llm_profiles USING btree (name)
llm_profiles|llm_profiles_pkey|CREATE UNIQUE INDEX llm_profiles_pkey ON public.llm_profiles USING btree (id)
llm_providers|llm_providers_name_key|CREATE UNIQUE INDEX llm_providers_name_key ON public.llm_providers USING btree (name)
llm_providers|llm_providers_pkey|CREATE UNIQUE INDEX llm_providers_pkey ON public.llm_providers USING btree (id)
llm_purpose_configs|llm_purpose_configs_pkey|CREATE UNIQUE INDEX llm_purpose_configs_pkey ON public.llm_purpose_configs USING btree (purpose)
memories|ix_memories_created_at|CREATE INDEX ix_memories_created_at ON public.memories USING btree (created_at)
memories|ix_memories_fts|CREATE INDEX ix_memories_fts ON public.memories USING gin (search_vector)
memories|ix_memories_is_archived|CREATE INDEX ix_memories_is_archived ON public.memories USING btree (is_archived) WHERE (is_archived = false)
memories|ix_memories_project|CREATE INDEX ix_memories_project ON public.memories USING btree (project)
memories|ix_memories_status|CREATE INDEX ix_memories_status ON public.memories USING btree (status)
memories|ix_memories_technologies|CREATE INDEX ix_memories_technologies ON public.memories USING gin (technologies)
memories|memories_pkey|CREATE UNIQUE INDEX memories_pkey ON public.memories USING btree (id)
memory_crossrefs|ix_memory_crossrefs_related|CREATE INDEX ix_memory_crossrefs_related ON public.memory_crossrefs USING btree (related_memory_id)
memory_crossrefs|memory_crossrefs_pkey|CREATE UNIQUE INDEX memory_crossrefs_pkey ON public.memory_crossrefs USING btree (memory_id, related_memory_id)
memory_tags|memory_tags_pkey|CREATE UNIQUE INDEX memory_tags_pkey ON public.memory_tags USING btree (memory_id, tag_id)
messages|messages_pkey|CREATE UNIQUE INDEX messages_pkey ON public.messages USING btree (id)
ml_profiles|ml_profiles_name_key|CREATE UNIQUE INDEX ml_profiles_name_key ON public.ml_profiles USING btree (name)
ml_profiles|ml_profiles_pkey|CREATE UNIQUE INDEX ml_profiles_pkey ON public.ml_profiles USING btree (id)
pipeline_failures|idx_pipeline_failures_pipeline_name|CREATE INDEX idx_pipeline_failures_pipeline_name ON public.pipeline_failures USING btree (pipeline_name) WHERE (resolved_at IS NULL)
pipeline_failures|idx_pipeline_failures_resolved_at|CREATE INDEX idx_pipeline_failures_resolved_at ON public.pipeline_failures USING btree (resolved_at) WHERE (resolved_at IS NOT NULL)
pipeline_failures|idx_pipeline_failures_unresolved|CREATE UNIQUE INDEX idx_pipeline_failures_unresolved ON public.pipeline_failures USING btree (entity_type, entity_id, pipeline_name) WHERE (resolved_at IS NULL)
pipeline_failures|pipeline_failures_pkey|CREATE UNIQUE INDEX pipeline_failures_pkey ON public.pipeline_failures USING btree (id)
repositories|ix_repositories_auto_sync|CREATE INDEX ix_repositories_auto_sync ON public.repositories USING btree (id) WHERE (auto_sync = true)
repositories|repositories_pkey|CREATE UNIQUE INDEX repositories_pkey ON public.repositories USING btree (id)
tags|tags_name_key|CREATE UNIQUE INDEX tags_name_key ON public.tags USING btree (name)
tags|tags_pkey|CREATE UNIQUE INDEX tags_pkey ON public.tags USING btree (id)
token_blocklist|ix_token_blocklist_jti|CREATE INDEX ix_token_blocklist_jti ON public.token_blocklist USING btree (jti)
token_blocklist|token_blocklist_jti_key|CREATE UNIQUE INDEX token_blocklist_jti_key ON public.token_blocklist USING btree (jti)
token_blocklist|token_blocklist_pkey|CREATE UNIQUE INDEX token_blocklist_pkey ON public.token_blocklist USING btree (id)
```

### A.4 — Constraints, with full definitions

`table|conname|contype (p=PK, f=FK, u=UNIQUE, c=CHECK)|definition`

```
alembic_version|alembic_version_pkc|p|PRIMARY KEY (version_num)
api_keys|api_keys_key_hash_key|u|UNIQUE (key_hash)
api_keys|api_keys_pkey|p|PRIMARY KEY (id)
audit_log|audit_log_pkey|p|PRIMARY KEY (id)
code_edges|code_edges_pkey|p|PRIMARY KEY (id)
code_edges|code_edges_repo_id_fkey|f|FOREIGN KEY (repo_id) REFERENCES repositories(id) ON DELETE CASCADE
code_edges|code_edges_repo_id_source_kind_source_key_target_kind_targe_key|u|UNIQUE (repo_id, source_kind, source_key, target_kind, target_key, edge_type)
code_files|code_files_pkey|p|PRIMARY KEY (id)
code_files|code_files_repo_id_fkey|f|FOREIGN KEY (repo_id) REFERENCES repositories(id) ON DELETE CASCADE
code_graph_nodes|code_graph_nodes_pkey|p|PRIMARY KEY (id)
code_graph_nodes|code_graph_nodes_repo_id_fkey|f|FOREIGN KEY (repo_id) REFERENCES repositories(id) ON DELETE CASCADE
code_graph_nodes|code_graph_nodes_repo_id_kind_key_key|u|UNIQUE (repo_id, kind, key)
code_symbols|code_symbols_file_id_fkey|f|FOREIGN KEY (file_id) REFERENCES code_files(id) ON DELETE CASCADE
code_symbols|code_symbols_parent_symbol_id_fkey|f|FOREIGN KEY (parent_symbol_id) REFERENCES code_symbols(id) ON DELETE SET NULL
code_symbols|code_symbols_pkey|p|PRIMARY KEY (id)
config|config_pkey|p|PRIMARY KEY (key)
conversations|conversations_pkey|p|PRIMARY KEY (id)
embedders|embedders_dims_check|c|CHECK ((dims > 0))
embedders|embedders_pkey|p|PRIMARY KEY (fingerprint)
embedders|embedders_source_check|c|CHECK ((source = 'llm'::text))
enrichment_queue|enrichment_queue_pkey|p|PRIMARY KEY (id)
enrichment_queue|enrichment_queue_symbol_id_fkey|f|FOREIGN KEY (symbol_id) REFERENCES code_symbols(id) ON DELETE CASCADE
enrichment_queue|enrichment_queue_symbol_id_key|u|UNIQUE (symbol_id)
entities|entities_name_entity_type_key|u|UNIQUE (name, entity_type)
entities|entities_pkey|p|PRIMARY KEY (id)
entity_relations|entity_relations_pkey|p|PRIMARY KEY (id)
entity_relations|entity_relations_source_entity_id_fkey|f|FOREIGN KEY (source_entity_id) REFERENCES entities(id) ON DELETE CASCADE
entity_relations|entity_relations_source_entity_id_target_entity_id_rel_type_key|u|UNIQUE (source_entity_id, target_entity_id, rel_type)
entity_relations|entity_relations_target_entity_id_fkey|f|FOREIGN KEY (target_entity_id) REFERENCES entities(id) ON DELETE CASCADE
knowledge_triples|knowledge_triples_pkey|p|PRIMARY KEY (id)
knowledge_triples|knowledge_triples_source_memory_id_fkey|f|FOREIGN KEY (source_memory_id) REFERENCES memories(id) ON DELETE SET NULL
llm_profiles|llm_profiles_name_key|u|UNIQUE (name)
llm_profiles|llm_profiles_pkey|p|PRIMARY KEY (id)
llm_profiles|llm_profiles_provider_id_fkey|f|FOREIGN KEY (provider_id) REFERENCES llm_providers(id) ON DELETE RESTRICT
llm_providers|llm_providers_name_key|u|UNIQUE (name)
llm_providers|llm_providers_pkey|p|PRIMARY KEY (id)
llm_purpose_configs|llm_purpose_configs_ml_profile_id_fkey|f|FOREIGN KEY (ml_profile_id) REFERENCES ml_profiles(id) ON DELETE SET NULL
llm_purpose_configs|llm_purpose_configs_pkey|p|PRIMARY KEY (purpose)
llm_purpose_configs|llm_purpose_configs_profile_id_fkey|f|FOREIGN KEY (profile_id) REFERENCES llm_profiles(id) ON DELETE SET NULL
llm_purpose_configs|llm_purpose_configs_provider_id_fkey|f|FOREIGN KEY (provider_id) REFERENCES llm_providers(id) ON DELETE SET NULL
memories|chk_superseded_has_pointer|c|CHECK (((status <> 'superseded'::memory_status) OR (superseded_by IS NOT NULL)))
memories|fk_memories_superseded_by|f|FOREIGN KEY (superseded_by) REFERENCES memories(id) ON DELETE SET NULL
memories|memories_pkey|p|PRIMARY KEY (id)
memory_crossrefs|memory_crossrefs_memory_id_fkey|f|FOREIGN KEY (memory_id) REFERENCES memories(id) ON DELETE CASCADE
memory_crossrefs|memory_crossrefs_pkey|p|PRIMARY KEY (memory_id, related_memory_id)
memory_crossrefs|memory_crossrefs_related_memory_id_fkey|f|FOREIGN KEY (related_memory_id) REFERENCES memories(id) ON DELETE CASCADE
memory_tags|memory_tags_memory_id_fkey|f|FOREIGN KEY (memory_id) REFERENCES memories(id) ON DELETE CASCADE
memory_tags|memory_tags_pkey|p|PRIMARY KEY (memory_id, tag_id)
memory_tags|memory_tags_tag_id_fkey|f|FOREIGN KEY (tag_id) REFERENCES tags(id) ON DELETE CASCADE
messages|messages_conversation_id_fkey|f|FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
messages|messages_pkey|p|PRIMARY KEY (id)
ml_profiles|ml_profiles_name_key|u|UNIQUE (name)
ml_profiles|ml_profiles_pkey|p|PRIMARY KEY (id)
pipeline_failures|pipeline_failures_pkey|p|PRIMARY KEY (id)
repositories|repositories_pkey|p|PRIMARY KEY (id)
tags|tags_name_key|u|UNIQUE (name)
tags|tags_pkey|p|PRIMARY KEY (id)
token_blocklist|token_blocklist_jti_key|u|UNIQUE (jti)
token_blocklist|token_blocklist_pkey|p|PRIMARY KEY (id)
```

### A.5 — Triggers (user-defined only)

`table|tgname|definition`

```
memories|memories_fts_update|CREATE TRIGGER memories_fts_update BEFORE INSERT OR UPDATE OF content ON public.memories FOR EACH ROW EXECUTE FUNCTION memories_fts_trigger()
```

### A.6 — Functions, excluding everything pgvector installed

```
memories_fts_trigger
```

### A.7 — Enum types and their labels

```
memory_status|active,deprecated,superseded
```

### A.8 — Rows the migrations seed

```
config:job:code_enrichment
config:job:pipeline_failure_cleanup
config:job:repo_sync
config:job:token_blocklist_cleanup
embedders=0
llm_providers=0
llm_purpose_configs=0
tags=0
```
