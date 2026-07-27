# Baseline schema inventory

**Status:** complete, 2026-07-27. Produced by **T0.11** (`docs/planning/tasks/E0-baseline-and-harness.md`).
**Consumed by T0.12a, T0.12b and T0.12c**, which write the single baseline migration
against it, and by **T0.13**, which labels its inert objects.

**Purpose, in T0.11's own words:** "Before writing DDL: reconcile doc 04's target data
model against the six existing revisions and produce the explicit object inventory the
baseline must land — what carries over, what changes shape, what is new, and what lands
inert. **This is the task that prevents the baseline from being an accident of migration
history.**"

### What this document is not

It is **not** DDL and it does not prescribe SQL text. T0.12a–c own the migration file.
Where an object's form is genuinely undecided by the design corpus, this inventory records
the disagreement in §10 and, where it can, a recommendation — it never picks silently.

### Authority order

Four sources were reconciled, and they disagree. Doc 19 §1 fixes the precedence: "where
this doc and doc 04 §12 overlap, they agree; where they would conflict, **doc 04's table
shapes win** and **this doc's operational sequencing wins**."

| Source | What it is | Authority |
|---|---|---|
| **A** — the live schema built by `alembic upgrade head` on an empty database | What the six revisions **actually** land, after `0003`'s data-only reset and `0006`'s column drops | **Ground truth for current state.** Cannot be misread. Appendix A. |
| **B** — `docs/design/04-data-model-and-schema.md` | The target data model | **Authoritative for target table shapes** |
| **C** — `docs/design/19-migration-deployment-and-ops.md` §2–§3 | Single-baseline discipline, boot-time reconciliation, the SQL-first rule, the dormant-object disposition table | **Authoritative for operational sequencing and disposition** |
| **D** — `backend/app/models/*.py`, `backend/app/services/embedder_registry.py` | The ORM mirror and the partition templates | **No authority.** Doc 19 §2: "SQLAlchemy models mirror the SQL, not the reverse." A construct living only here is a **finding**, not a row (§9). |

Two corroborating, non-authoritative references: `docs/design/erd.md` (its own header
subordinates it — "key columns only; full column/constraint/index detail lives in doc 04")
and `docs/design/20-roadmap-and-sequencing.md` §6–§7, which fixes *when* an inert object's
tag may flip (§7) and makes the SQL-first rule standing across Phases 0–4.

**Source A is extracted mechanically and first**, because it is the only one of the four
that cannot be misread and because every later section diffs against it. The gap that
justifies the method: `0001` calls `op.create_table` **nineteen** times but the migrated
database holds **twenty-six** tables, and calls `op.create_index` **twenty-three** times
but the database holds **sixty-three** indexes.

### The freeze note

**The baseline is regenerated, not migrated, until the homelab cutover freezes it.** Doc
19 §2: the greenfield schema ships as one Alembic revision, "regenerated freely (paired
with drop/recreate) until the first deploy whose data must survive, at which event it is
tagged `0001` and **frozen**; every change after the freeze is a new linear revision
forever." The freeze trigger is an **event**, not a date — the homelab production cutover
(doc 19 §4) — and a CI assertion holds `alembic history` at exactly one revision until the
freeze tag exists, so nobody can quietly start a chain early.

> **Freeze date: _(deliberately blank — the cutover has not happened)_**

Leaving it blank is correct and load-bearing. T0.15 owns the regeneration protocol and
E1's cutover task (T1.54) fills the real date; writing a plausible date here would be
exactly the dishonesty the definition-of-done exists to prevent.

## 1. How to read this inventory

### The disposition legend

Four values govern §2–§6 — the objects the baseline **lands**:

| Disposition | Means | Decision rule |
|---|---|---|
| `carries-over` | The object exists in Appendix A and the target changes neither its columns, its keys, nor its constraints. | Doc 04 §3.2's "the target keeps them verbatim" is the canonical phrasing. |
| `reshaped` | The object exists in Appendix A and the target changes something about it. | **The disposition most often under-applied.** A table gaining one column, one index, or one UNIQUE support is `reshaped`, not `carries-over`. |
| `target-new` | No row in Appendix A — **or** the name survives but every column and semantic is new. | `knowledge_triples` is the latter: doc 04 §8.3 fixes the call, "treated as target-new, NOT as an activation of the dormant demo scaffolding". |
| `target-new, inert` | `target-new` **and** nothing in the target's own phase writes to it. | Doc 19 §3's disposition table is the **closed list** of what qualifies. Every such object names its first writer in §7. |

Dispositions in §3 and §4 are **per-object, not inherited from the table**: an unchanged
index on a `reshaped` table is `carries-over`. Those two sections add one value the four
cannot express, `dropped`, for an object present at HEAD that does not survive — its
reason lives in §8.

§8 has its own two-value vocabulary, `dropped` and `dropped, optional transform`, because
none of the four dispositions can express "present today, deliberately absent tomorrow".
That extension is amendment **A-01** in §10.

Three of doc 19 §3's five disposition labels fold into the four rather than needing their
own: `(rebuild)` is `target-new` with a note; `(activation)` is `carries-over` with an
activation note and a first-**reader** task id, because the schema does not change, only a
later phase's read path; and `(template only)` is `target-new, inert` with a note that the
template ships and the writer is deferred.

### Reading order

§2 is the spine — one row per target table. §3–§5 hang the fine-grained objects off it
(indexes, constraints, column changes). §6 is a different kind of row: registry entries the
baseline must **not** create as DDL. §7 is the inert register. §8 is what does not land. §9
is the SQL-first audit. §10 is where the sources disagree, **Tier-3 rows first**. Appendix
A is the machine-extracted current state; Appendix B is every check, re-runnable.


## 2. Tables — the target roll-call

**One row per table in the target.** `Owning doc §` is the *most specific* section of
doc 04 that fixes the table's shape. `Lands in` is the T0.12a–c pass (or other task) whose
own text names the table; `—` means **no task text names it**, which is a finding in §10,
not a guess. Dispositions are filled in §2 by Task 3 against the legend in §1.

Rows are ordered by their owning doc 04 section, so the roll-call reads as doc 04's own
spine. Tables present at HEAD but deliberately absent from the target are **not** here —
they are in §8, with their own vocabulary.

| Table | Owning doc § | Lands in | Disposition | Note |
|---|---|---|---|---|
| `memories` | 04 §3.1 | T0.12a | `reshaped` | The central row and the `active → superseded → deprecated` lifecycle. |
| `tags` | 04 §3.2 | T0.12a | `carries-over` | `id serial` PK, `name` UNIQUE. |
| `memory_tags` | 04 §3.2 | T0.12a | `carries-over` | T0.12a's text says "tags"; doc 04 §3.2 treats the pair as one unit (F-03). |
| `memory_crossrefs` | 04 §3.3 | — | `carries-over` | Live precomputed similarity edges, distinct from `memory_relations` (F-02). |
| `entities` | 04 §4.1 | T0.12a | `reshaped` | `repo_ids[]` arrives with T0.13 (§5). |
| `entity_relations` | 04 §4.2 | T0.12a | `reshaped` | `repo_ids[]` arrives with T0.13 (§5). |
| `embedders` | 04 §5.1 | T0.12a | `carries-over` | The fingerprint registry; owns the child-table DDL (§6). |
| `repositories` | 04 §6 | T0.12b | `reshaped` | Gains `index_debt` jsonb (§5). |
| `code_files` | 04 §6 | T0.12b | `carries-over` | |
| `code_symbols` | 04 §6 | T0.12b | `carries-over` | The live enrichment backlog is its partial index, not `enrichment_queue` (§8). |
| `code_graph_nodes` | 04 §6 | T0.12b | `carries-over` | `kind` is polymorphic — communities and processes are node kinds. |
| `code_edges` | 04 §6 | T0.12b | `carries-over` | |
| `llm_purpose_configs` | 04 §7 | — | `reshaped` | Six inline rows; drops `provider_id`/`profile_id`/`ml_profile_id`, gains `classifier_kind` (F-02, F-08, F-10). |
| `projects` | 04 §7 | T0.12b | `target-new` | `(name PK, display_name, properties, created_at)`; lazy registration, no FKs yet. |
| `config` | 04 §7 | T0.12a | `reshaped` | Key/value rows: feature flags, `job:<key>` state, `admin_password_hash`. Doc 04 §7 prints `value jsonb NOT NULL DEFAULT '{}'`; A.2 shows no server default (§5, F-09). |
| `token_blocklist` | 04 §7 | — | `carries-over` | JWT revocation store (F-02). |
| `pipeline_failures` | 04 §7 | — | `carries-over` | Polymorphic retry tracker, three partial indexes (F-02). |
| `conversations` | 04 §7 | — | `carries-over` | Chat surface; carried verbatim at cutover as user data (F-02). |
| `messages` | 04 §7 | — | `carries-over` | Chat surface (F-02). |
| `api_keys` | 04 §7, §9 | — | `carries-over` | Exists, unwired. Doc 19 §3 `(activation)`; schema unchanged in the baseline, first reader **T4.01** (F-02, F-04). |
| `events` | 04 §8.1 | T0.12b | `target-new` | `RANGE(created_at)` monthly; forbid-trigger is T1.06's. |
| `memory_relations` | 04 §8.2 | — | `target-new` | Five stored types; `SUPERSEDES` projected, never stored (F-02). |
| `knowledge_triples` | 04 §8.3 | T0.12b | `target-new` | Exists at HEAD but `target-new` by doc 04 §8.3 — "treated as target-new, NOT as an activation of the dormant demo scaffolding". |
| `fact_sources` | 04 §8.3 | T0.12b | `target-new` | Provenance child; `COUNT(DISTINCT origin_key)` is the corroboration signal. |
| `memory_communities` | 04 §8.4 | — | `target-new` | Leiden communities per project; ids churn every run (F-02). |
| `memory_community_members` | 04 §8.4 | — | `target-new` | Join table, PK `(community_id, memory_id)` (F-02). |
| `documents` | 04 §8.5 | T0.13 | `target-new, inert` | Horizon; lands empty and inert. |
| `blocks` | 04 §8.5 | T0.13 | `target-new, inert` | Horizon; lands empty and inert. |
| `memory_buffer` | 04 §8.6 | — | `target-new` | Tier-B durable buffer, `FOR UPDATE SKIP LOCKED` (F-02). |
| `project_repositories` | 04 §8.7 | — | `target-new` | M2M over one shared `Repository` (F-02). |
| `knowledge_articles` | 04 §8.8 | T0.12b | `target-new` | T0.12b's "articles and citations". |
| `article_citations` | 04 §8.8 | T0.12b | `target-new` | The one hard FK — `fact_id → knowledge_triples`. |
| `memory_access_stats` | 04 §9 | — | `target-new` | 1:1 ranking-prior side table; keeps read churn off `memories` (F-02). |
| `alembic_version` | — | n/a (Alembic) | `carries-over` | Alembic's own bookkeeping; doc 04 never names it (F-01). |

**34 rows.** Twenty-one are tables the as-is manifest (A.1) already holds; thirteen are
target-new. The remaining five of A.1's twenty-six are dropped and live in §8, so
`21 + 5 = 26` reconciles the roll-call against the manifest exactly.

**Three classes of name doc 04 backticks are deliberately not roll-call rows.** The eight
per-fingerprint **partition parents** (`memory_embeddings`, `entity_embeddings`,
`code_chunk_embeddings`, `entity_embedding_cache`, `block_embeddings`,
`relation_embeddings`, `article_embeddings`, `triple_embeddings`) are registry entries,
not migration DDL, and live in §6 — putting them here would invite exactly the eight
`CREATE TABLE`s doc 19 §2 forbids. The one **native enum** `memory_status` is a type, and
lives in §4. And two names doc 04 raises **conditionally** are not in the target at all:
`pinned_subjects` ("promoted to a dedicated `pinned_subjects` store **only if** they grow
large" — doc 04 §7; today the lists ride `projects.properties`) and `retrieval_traces`
("persist a `retrieval_traces` table **only if** the ADE viewer or eval harness needs
durable audit" — doc 04 §13, whose recommendation for v1 is no table). Neither is a
finding; both are recorded so the reviewer's over-collecting sweep resolves without
re-reading doc 04.

### 2.1 Seed data the baseline carries

Seed rows are an inventory concern, not just DDL, because a table that exists but is
empty behaves differently from one the migration populates.

| Table | Rows seeded by the migrations (A.8) | Target |
|---|---|---|
| `config` | 4 — `job:code_enrichment`, `job:pipeline_failure_cleanup`, `job:repo_sync`, `job:token_blocklist_cleanup` | The other three registered jobs create their state rows at runtime (F-06). |
| `llm_purpose_configs` | 0 | The six purpose rows are written by the setup wizard's finalize step from `app/services/llm_seed.py`, never by a migration (doc 04 §7). |
| `embedders` | 0 | Registered at runtime by `embedder_registry.register` (doc 04 §5.1). |
| `llm_providers` | 0 | Dropped (§8). |
| `tags` | 0 | Tags are created on use. |

## 3. Indexes

**Every index in Appendix A.3 appears below, including those on dropped tables.** The plan
this task executes said rows belonging to a §8-dropped table are *removed*; its own
verification then asserts that "carries-over index rows plus dropped-with-table index rows
equals 63", which only holds if they are present. Keeping them is the stronger reading:
the set difference against A.3 is then total, with no "except" clause a reviewer has to
take on trust (F-11).

**Dispositions here are per-object, not inherited from the table.** An index on a
`reshaped` table that is itself unchanged is `carries-over` — `ix_memories_created_at` does
not become `reshaped` because `memories` gained a column. Three values appear:
`carries-over` (in A.3, target keeps it identically), `target-new` (not in A.3), and
`dropped` (in A.3, does not survive — the table went in §8, or the columns it sits on
cease to exist under a rebuild). `target-new, inert` marks a target-new index on an inert
column.

### 3.1 Indexes present at HEAD (Appendix A.3, all 63)

| Index | On table | Definition | Disposition | Doc § | Lands in |
|---|---|---|---|---|---|
| `alembic_version_pkc` | `alembic_version` | `CREATE UNIQUE INDEX alembic_version_pkc ON public.alembic_version USING btree (version_num)` | `carries-over` | 19 §2 | n/a (Alembic) |
| `api_keys_key_hash_key` | `api_keys` | `CREATE UNIQUE INDEX api_keys_key_hash_key ON public.api_keys USING btree (key_hash)` | `carries-over` | 04 §7 | — |
| `api_keys_pkey` | `api_keys` | `CREATE UNIQUE INDEX api_keys_pkey ON public.api_keys USING btree (id)` | `carries-over` | 04 §7 | — |
| `audit_log_pkey` | `audit_log` | `CREATE UNIQUE INDEX audit_log_pkey ON public.audit_log USING btree (id)` | `dropped` | 04 §7 | — |
| `code_edges_pkey` | `code_edges` | `CREATE UNIQUE INDEX code_edges_pkey ON public.code_edges USING btree (id)` | `carries-over` | 04 §6 | T0.12b |
| `code_edges_repo_id_source_kind_source_key_target_kind_targe_key` | `code_edges` | `CREATE UNIQUE INDEX code_edges_repo_id_source_kind_source_key_target_kind_targe_key ON public.code_edges USING btree (repo_id, source_kind, source_key, target_kind, target_key, edge_type)` | `carries-over` | 04 §6 | T0.12b |
| `ix_code_edges_covering` | `code_edges` | `CREATE INDEX ix_code_edges_covering ON public.code_edges USING btree (repo_id, edge_type, source_key, target_key)` | `carries-over` | 04 §6 | T0.12b |
| `ix_code_edges_repo_source` | `code_edges` | `CREATE INDEX ix_code_edges_repo_source ON public.code_edges USING btree (repo_id, source_key)` | `carries-over` | 04 §6 | T0.12b |
| `ix_code_edges_repo_target` | `code_edges` | `CREATE INDEX ix_code_edges_repo_target ON public.code_edges USING btree (repo_id, target_key)` | `carries-over` | 04 §6 | T0.12b |
| `ix_code_edges_repo_type` | `code_edges` | `CREATE INDEX ix_code_edges_repo_type ON public.code_edges USING btree (repo_id, edge_type)` | `carries-over` | 04 §6 | T0.12b |
| `code_files_pkey` | `code_files` | `CREATE UNIQUE INDEX code_files_pkey ON public.code_files USING btree (id)` | `carries-over` | 04 §6 | T0.12b |
| `ix_code_files_repo_path` | `code_files` | `CREATE INDEX ix_code_files_repo_path ON public.code_files USING btree (repo_id, file_path)` | `carries-over` | 04 §6 | T0.12b |
| `code_graph_nodes_pkey` | `code_graph_nodes` | `CREATE UNIQUE INDEX code_graph_nodes_pkey ON public.code_graph_nodes USING btree (id)` | `carries-over` | 04 §6 | T0.12b |
| `code_graph_nodes_repo_id_kind_key_key` | `code_graph_nodes` | `CREATE UNIQUE INDEX code_graph_nodes_repo_id_kind_key_key ON public.code_graph_nodes USING btree (repo_id, kind, key)` | `carries-over` | 04 §6 | T0.12b |
| `code_symbols_pkey` | `code_symbols` | `CREATE UNIQUE INDEX code_symbols_pkey ON public.code_symbols USING btree (id)` | `carries-over` | 04 §6 | T0.12b |
| `ix_code_symbols_enrichment_pending` | `code_symbols` | `CREATE INDEX ix_code_symbols_enrichment_pending ON public.code_symbols USING btree (enrichment_attempts, enrichment_priority DESC) WHERE ((enrichment_status)::text = 'pending'::text)` | `carries-over` | 04 §6 | T0.12b |
| `ix_code_symbols_file_id` | `code_symbols` | `CREATE INDEX ix_code_symbols_file_id ON public.code_symbols USING btree (file_id)` | `carries-over` | 04 §6 | T0.12b |
| `config_pkey` | `config` | `CREATE UNIQUE INDEX config_pkey ON public.config USING btree (key)` | `carries-over` | 04 §7 | T0.12a |
| `conversations_pkey` | `conversations` | `CREATE UNIQUE INDEX conversations_pkey ON public.conversations USING btree (id)` | `carries-over` | 04 §7 | — |
| `embedders_pkey` | `embedders` | `CREATE UNIQUE INDEX embedders_pkey ON public.embedders USING btree (fingerprint)` | `carries-over` | 04 §5.1 | T0.12a |
| `enrichment_queue_pkey` | `enrichment_queue` | `CREATE UNIQUE INDEX enrichment_queue_pkey ON public.enrichment_queue USING btree (id)` | `dropped` | 04 §6 | — |
| `enrichment_queue_symbol_id_key` | `enrichment_queue` | `CREATE UNIQUE INDEX enrichment_queue_symbol_id_key ON public.enrichment_queue USING btree (symbol_id)` | `dropped` | 04 §6 | — |
| `entities_name_entity_type_key` | `entities` | `CREATE UNIQUE INDEX entities_name_entity_type_key ON public.entities USING btree (name, entity_type)` | `carries-over` | 04 §4.1 | T0.12a |
| `entities_pkey` | `entities` | `CREATE UNIQUE INDEX entities_pkey ON public.entities USING btree (id)` | `carries-over` | 04 §4.1 | T0.12a |
| `ix_entities_memory_ids` | `entities` | `CREATE INDEX ix_entities_memory_ids ON public.entities USING gin (memory_ids)` | `carries-over` | 04 §4.1 | T0.12a |
| `entity_relations_pkey` | `entity_relations` | `CREATE UNIQUE INDEX entity_relations_pkey ON public.entity_relations USING btree (id)` | `carries-over` | 04 §4.2 | T0.12a |
| `entity_relations_source_entity_id_target_entity_id_rel_type_key` | `entity_relations` | `CREATE UNIQUE INDEX entity_relations_source_entity_id_target_entity_id_rel_type_key ON public.entity_relations USING btree (source_entity_id, target_entity_id, rel_type)` | `carries-over` | 04 §4.2 | T0.12a |
| `ix_entity_relations_memory_ids` | `entity_relations` | `CREATE INDEX ix_entity_relations_memory_ids ON public.entity_relations USING gin (memory_ids)` | `carries-over` | 04 §4.2 | T0.12a |
| `ix_entity_relations_target` | `entity_relations` | `CREATE INDEX ix_entity_relations_target ON public.entity_relations USING btree (target_entity_id)` | `carries-over` | 04 §4.2 | T0.12a |
| `ix_knowledge_triples_object` | `knowledge_triples` | `CREATE INDEX ix_knowledge_triples_object ON public.knowledge_triples USING btree (object)` | `dropped` | 04 §8.3 | — |
| `ix_knowledge_triples_predicate` | `knowledge_triples` | `CREATE INDEX ix_knowledge_triples_predicate ON public.knowledge_triples USING btree (predicate)` | `dropped` | 04 §8.3 | — |
| `ix_knowledge_triples_subject` | `knowledge_triples` | `CREATE INDEX ix_knowledge_triples_subject ON public.knowledge_triples USING btree (subject)` | `dropped` | 04 §8.3 | — |
| `ix_knowledge_triples_valid` | `knowledge_triples` | `CREATE INDEX ix_knowledge_triples_valid ON public.knowledge_triples USING btree (valid_from, valid_to)` | `dropped` | 04 §8.3 | — |
| `knowledge_triples_pkey` | `knowledge_triples` | `CREATE UNIQUE INDEX knowledge_triples_pkey ON public.knowledge_triples USING btree (id)` | `dropped` | 04 §8.3 | — |
| `llm_profiles_name_key` | `llm_profiles` | `CREATE UNIQUE INDEX llm_profiles_name_key ON public.llm_profiles USING btree (name)` | `dropped` | 04 §7 | — |
| `llm_profiles_pkey` | `llm_profiles` | `CREATE UNIQUE INDEX llm_profiles_pkey ON public.llm_profiles USING btree (id)` | `dropped` | 04 §7 | — |
| `llm_providers_name_key` | `llm_providers` | `CREATE UNIQUE INDEX llm_providers_name_key ON public.llm_providers USING btree (name)` | `dropped` | 04 §7 | — |
| `llm_providers_pkey` | `llm_providers` | `CREATE UNIQUE INDEX llm_providers_pkey ON public.llm_providers USING btree (id)` | `dropped` | 04 §7 | — |
| `llm_purpose_configs_pkey` | `llm_purpose_configs` | `CREATE UNIQUE INDEX llm_purpose_configs_pkey ON public.llm_purpose_configs USING btree (purpose)` | `carries-over` | 04 §7 | — |
| `ix_memories_created_at` | `memories` | `CREATE INDEX ix_memories_created_at ON public.memories USING btree (created_at)` | `carries-over` | 04 §3.1 | T0.12a |
| `ix_memories_fts` | `memories` | `CREATE INDEX ix_memories_fts ON public.memories USING gin (search_vector)` | `carries-over` | 04 §3.1 | T0.12a |
| `ix_memories_is_archived` | `memories` | `CREATE INDEX ix_memories_is_archived ON public.memories USING btree (is_archived) WHERE (is_archived = false)` | `carries-over` | 04 §3.1 | T0.12a |
| `ix_memories_project` | `memories` | `CREATE INDEX ix_memories_project ON public.memories USING btree (project)` | `carries-over` | 04 §3.1 | T0.12a |
| `ix_memories_status` | `memories` | `CREATE INDEX ix_memories_status ON public.memories USING btree (status)` | `carries-over` | 04 §3.1 | T0.12a |
| `ix_memories_technologies` | `memories` | `CREATE INDEX ix_memories_technologies ON public.memories USING gin (technologies)` | `carries-over` | 04 §3.1 | T0.12a |
| `memories_pkey` | `memories` | `CREATE UNIQUE INDEX memories_pkey ON public.memories USING btree (id)` | `carries-over` | 04 §3.1 | T0.12a |
| `ix_memory_crossrefs_related` | `memory_crossrefs` | `CREATE INDEX ix_memory_crossrefs_related ON public.memory_crossrefs USING btree (related_memory_id)` | `carries-over` | 04 §3.3 | — |
| `memory_crossrefs_pkey` | `memory_crossrefs` | `CREATE UNIQUE INDEX memory_crossrefs_pkey ON public.memory_crossrefs USING btree (memory_id, related_memory_id)` | `carries-over` | 04 §3.3 | — |
| `memory_tags_pkey` | `memory_tags` | `CREATE UNIQUE INDEX memory_tags_pkey ON public.memory_tags USING btree (memory_id, tag_id)` | `carries-over` | 04 §3.2 | T0.12a |
| `messages_pkey` | `messages` | `CREATE UNIQUE INDEX messages_pkey ON public.messages USING btree (id)` | `carries-over` | 04 §7 | — |
| `ml_profiles_name_key` | `ml_profiles` | `CREATE UNIQUE INDEX ml_profiles_name_key ON public.ml_profiles USING btree (name)` | `dropped` | 04 §7 | — |
| `ml_profiles_pkey` | `ml_profiles` | `CREATE UNIQUE INDEX ml_profiles_pkey ON public.ml_profiles USING btree (id)` | `dropped` | 04 §7 | — |
| `idx_pipeline_failures_pipeline_name` | `pipeline_failures` | `CREATE INDEX idx_pipeline_failures_pipeline_name ON public.pipeline_failures USING btree (pipeline_name) WHERE (resolved_at IS NULL)` | `carries-over` | 04 §7 | — |
| `idx_pipeline_failures_resolved_at` | `pipeline_failures` | `CREATE INDEX idx_pipeline_failures_resolved_at ON public.pipeline_failures USING btree (resolved_at) WHERE (resolved_at IS NOT NULL)` | `carries-over` | 04 §7 | — |
| `idx_pipeline_failures_unresolved` | `pipeline_failures` | `CREATE UNIQUE INDEX idx_pipeline_failures_unresolved ON public.pipeline_failures USING btree (entity_type, entity_id, pipeline_name) WHERE (resolved_at IS NULL)` | `carries-over` | 04 §7 | — |
| `pipeline_failures_pkey` | `pipeline_failures` | `CREATE UNIQUE INDEX pipeline_failures_pkey ON public.pipeline_failures USING btree (id)` | `carries-over` | 04 §7 | — |
| `ix_repositories_auto_sync` | `repositories` | `CREATE INDEX ix_repositories_auto_sync ON public.repositories USING btree (id) WHERE (auto_sync = true)` | `carries-over` | 04 §6 | T0.12b |
| `repositories_pkey` | `repositories` | `CREATE UNIQUE INDEX repositories_pkey ON public.repositories USING btree (id)` | `carries-over` | 04 §6 | T0.12b |
| `tags_name_key` | `tags` | `CREATE UNIQUE INDEX tags_name_key ON public.tags USING btree (name)` | `carries-over` | 04 §3.2 | T0.12a |
| `tags_pkey` | `tags` | `CREATE UNIQUE INDEX tags_pkey ON public.tags USING btree (id)` | `carries-over` | 04 §3.2 | T0.12a |
| `ix_token_blocklist_jti` | `token_blocklist` | `CREATE INDEX ix_token_blocklist_jti ON public.token_blocklist USING btree (jti)` | `carries-over` | 04 §7 | — |
| `token_blocklist_jti_key` | `token_blocklist` | `CREATE UNIQUE INDEX token_blocklist_jti_key ON public.token_blocklist USING btree (jti)` | `carries-over` | 04 §7 | — |
| `token_blocklist_pkey` | `token_blocklist` | `CREATE UNIQUE INDEX token_blocklist_pkey ON public.token_blocklist USING btree (id)` | `carries-over` | 04 §7 | — |

**Nine of the 63 sit on §8-dropped tables** (`audit_log` 1, `enrichment_queue` 1,
`llm_providers` 3, `llm_profiles` 3, `ml_profiles` 1) and **five more belong to
`knowledge_triples`' HEAD shape** — four indexes on `subject`, `predicate`, `object`,
`valid_from`/`valid_to`, columns the §8.3 rebuild replaces entirely, plus its PK. The
rebuilt table's `id uuid` PK is a **new object on a new shape** (UUIDv7, §4.3), not a
survival of this one; labelling it `carries-over` inside a `target-new` table would be the
exact "activation" reading doc 04 §8.3 forbids. Forty-nine carry over.

Two rows deserve a reader's attention. `ix_repositories_auto_sync` is a **partial** index
on `(id) WHERE auto_sync = true`, which is what makes the `repo_sync` filter cheap; the
partiality, not the column, is the load-bearing part. And `token_blocklist` carries
**both** `token_blocklist_jti_key` (UNIQUE) and `ix_token_blocklist_jti` (a plain btree)
on the same column — the plain btree is redundant under the unique, and doc 04 §7
specifies only `jti UNIQUE` (F-12).

### 3.2 Target-new indexes

| Index | On table | Definition | Disposition | Doc § | Lands in |
|---|---|---|---|---|---|
| composite `(project, status)` support | `memories` | `(project, status)`, **or** `(project, status, is_archived)`, **or** partial `WHERE status='active' AND is_archived=false` | `target-new` | 04 §10 | T0.12c |
| `ix_entities_repo_ids` | `entities` | GIN on `(repo_ids)` | `target-new, inert` | 04 §4.1 | T0.13 |
| `ix_entity_relations_repo_ids` | `entity_relations` | GIN on `(repo_ids)` | `target-new, inert` | 04 §4.2 | T0.13 |
| object-timeline index | `events` | `(object_type, object_id, created_at)` | `target-new` | 04 §8.1, §10 | T0.12b |
| calendar date-bucket index | `events` | `(project, ((created_at AT TIME ZONE 'UTC')::date))` — the `AT TIME ZONE 'UTC'` form is required; a bare `created_at::date` on a `timestamptz` is only STABLE and cannot be indexed | `target-new` | 04 §8.1, §10 | T0.12b |
| live-fact lookup | `knowledge_triples` | partial **non-unique** `(subject_name, rel_type, object_name) WHERE expired_at IS NULL` — non-unique because disjoint validity windows legitimately leave several live rows on one S/P/O | `target-new` | 04 §8.3, §10 | T0.12b |
| validity-window index | `knowledge_triples` | btree `(valid_at, invalid_at)` | `target-new` | 04 §8.3, §10 | T0.12b |
| open-belief identity | `knowledge_triples` | **partial-unique** `triple_key WHERE expired_at IS NULL AND invalid_at IS NULL` — at most one currently-open belief per fact; window-closed rows leave the unique's scope but remain live history | `target-new` | 04 §8.3, §10 | T0.12b |
| review queue | `knowledge_triples` | partial `(review_state) WHERE review_state='open'` | `target-new` | 04 §8.3, §10 | T0.12b |
| member-source reverse lookup | `fact_sources` | btree `(source_kind, source_ref)` — the role the removed `source_memory_ids` GIN played | `target-new` | 04 §8.3, §10 | T0.12b |
| fact fan-out | `fact_sources` | btree `(fact_id)` | `target-new` | 04 §8.3, §10 | T0.12b |
| one live article per subject | `knowledge_articles` | **partial-unique** `(project, subject_key) WHERE status <> 'superseded'` | `target-new` | 04 §8.8, §10 | T0.12b |
| review queue | `knowledge_articles` | partial `(review_state) WHERE review_state='open'` | `target-new` | 04 §8.8, §10 | T0.12b |
| cite set | `article_citations` | btree `(article_id)` | `target-new` | 04 §8.8, §10 | T0.12b |
| reverse traversal | `memory_relations` | btree `(target_memory_id)` — "what points at this memory" filters on the target, which the UNIQUE's source prefix cannot serve; this is `entity_relations`' migration-`0002` lesson applied from day one | `target-new` | 04 §8.2, §10 | — (F-02) |
| claim scan | `memory_buffer` | partial `(created_at) WHERE status='pending'` — the `SKIP LOCKED` claim only ever reads pending rows | `target-new` | 04 §8.6, §10 | — (F-02) |
| topic membership | `memory_community_members` | btree `(memory_id)` | `target-new` | 04 §8.4 | — (F-02) |
| document identity | `documents` | partial **UNIQUE** `(project, uri) WHERE uri IS NOT NULL` | `target-new, inert` | 04 §8.5, §10 | T0.13 |
| block order | `blocks` | `(document_id, order_index)` | `target-new, inert` | 04 §8.5, §10 | T0.13 |
| block tree | `blocks` | `(parent_id)` | `target-new, inert` | 04 §8.5, §10 | T0.13 |

**The HNSW and aux indexes on the eight per-fingerprint parents are deliberately not
here** — they are created at runtime by the registry, per fingerprint, and are inventoried
in §6.

**The `(project, status)` composite is the one index change the pushdown strictly
requires, and doc 04 §10 does not pick among its three forms.** The recommendation this
inventory records for T0.12c is the **partial** `WHERE status='active' AND
is_archived=false`: the pushed-down predicate's overwhelmingly common shape is "live rows
in this project", the partial index is the smallest of the three, and the two full
composites remain available if a later measurement shows scans that need `status` values
other than `'active'`. One honest caveat doc 04 §10 states and the recommendation does not
change: **the semantic channel cannot use this index at all** — an HNSW scan applies the
predicate as a post-scan filter over its candidate stream — so the composite serves the
keyword and direct-scan sides, and the semantic side's win is correctness and reduced
over-fetch, not an index-scan plan. If T0.12c's executor judges the pick to be a design
decision rather than an inventory one, it is F-14 to adjudicate, not a silent choice.

## 4. Constraints, triggers, and types

Same rule as §3: **every constraint in Appendix A.4 appears below**, dispositioned rather
than removed, plus the one trigger (A.5), the one non-extension function (A.6), and the
one enum type (A.7). `Kind` is `PK` / `FK` / `UNIQUE` / `CHECK` / `trigger` / `function` /
`enum` / `partitioning`.

### 4.1 Constraints present at HEAD (Appendix A.4, all 59)

| Object | Kind | On | Definition | Disposition | Doc § | Lands in |
|---|---|---|---|---|---|---|
| `alembic_version_pkc` | PK | `alembic_version` | `PRIMARY KEY (version_num)` | `carries-over` | 19 §2 | n/a (Alembic) |
| `api_keys_key_hash_key` | UNIQUE | `api_keys` | `UNIQUE (key_hash)` | `carries-over` | 04 §7 | — |
| `api_keys_pkey` | PK | `api_keys` | `PRIMARY KEY (id)` | `carries-over` | 04 §7 | — |
| `audit_log_pkey` | PK | `audit_log` | `PRIMARY KEY (id)` | `dropped` | 04 §7 | — |
| `code_edges_pkey` | PK | `code_edges` | `PRIMARY KEY (id)` | `carries-over` | 04 §6 | T0.12b |
| `code_edges_repo_id_fkey` | FK | `code_edges` | `FOREIGN KEY (repo_id) REFERENCES repositories(id) ON DELETE CASCADE` | `carries-over` | 04 §6 | T0.12b |
| `code_edges_repo_id_source_kind_source_key_target_kind_targe_key` | UNIQUE | `code_edges` | `UNIQUE (repo_id, source_kind, source_key, target_kind, target_key, edge_type)` | `carries-over` | 04 §6 | T0.12b |
| `code_files_pkey` | PK | `code_files` | `PRIMARY KEY (id)` | `carries-over` | 04 §6 | T0.12b |
| `code_files_repo_id_fkey` | FK | `code_files` | `FOREIGN KEY (repo_id) REFERENCES repositories(id) ON DELETE CASCADE` | `carries-over` | 04 §6 | T0.12b |
| `code_graph_nodes_pkey` | PK | `code_graph_nodes` | `PRIMARY KEY (id)` | `carries-over` | 04 §6 | T0.12b |
| `code_graph_nodes_repo_id_fkey` | FK | `code_graph_nodes` | `FOREIGN KEY (repo_id) REFERENCES repositories(id) ON DELETE CASCADE` | `carries-over` | 04 §6 | T0.12b |
| `code_graph_nodes_repo_id_kind_key_key` | UNIQUE | `code_graph_nodes` | `UNIQUE (repo_id, kind, key)` | `carries-over` | 04 §6 | T0.12b |
| `code_symbols_file_id_fkey` | FK | `code_symbols` | `FOREIGN KEY (file_id) REFERENCES code_files(id) ON DELETE CASCADE` | `carries-over` | 04 §6 | T0.12b |
| `code_symbols_parent_symbol_id_fkey` | FK | `code_symbols` | `FOREIGN KEY (parent_symbol_id) REFERENCES code_symbols(id) ON DELETE SET NULL` | `carries-over` | 04 §6 | T0.12b |
| `code_symbols_pkey` | PK | `code_symbols` | `PRIMARY KEY (id)` | `carries-over` | 04 §6 | T0.12b |
| `config_pkey` | PK | `config` | `PRIMARY KEY (key)` | `carries-over` | 04 §7 | T0.12a |
| `conversations_pkey` | PK | `conversations` | `PRIMARY KEY (id)` | `carries-over` | 04 §7 | — |
| `embedders_dims_check` | CHECK | `embedders` | `CHECK ((dims > 0))` | `carries-over` | 04 §5.1 | T0.12a |
| `embedders_pkey` | PK | `embedders` | `PRIMARY KEY (fingerprint)` | `carries-over` | 04 §5.1 | T0.12a |
| `embedders_source_check` | CHECK | `embedders` | `CHECK ((source = 'llm'::text))` | `carries-over` | 04 §5.1 | T0.12a |
| `enrichment_queue_pkey` | PK | `enrichment_queue` | `PRIMARY KEY (id)` | `dropped` | 04 §6 | — |
| `enrichment_queue_symbol_id_fkey` | FK | `enrichment_queue` | `FOREIGN KEY (symbol_id) REFERENCES code_symbols(id) ON DELETE CASCADE` | `dropped` | 04 §6 | — |
| `enrichment_queue_symbol_id_key` | UNIQUE | `enrichment_queue` | `UNIQUE (symbol_id)` | `dropped` | 04 §6 | — |
| `entities_name_entity_type_key` | UNIQUE | `entities` | `UNIQUE (name, entity_type)` | `carries-over` | 04 §4.1 | T0.12a |
| `entities_pkey` | PK | `entities` | `PRIMARY KEY (id)` | `carries-over` | 04 §4.1 | T0.12a |
| `entity_relations_pkey` | PK | `entity_relations` | `PRIMARY KEY (id)` | `carries-over` | 04 §4.2 | T0.12a |
| `entity_relations_source_entity_id_fkey` | FK | `entity_relations` | `FOREIGN KEY (source_entity_id) REFERENCES entities(id) ON DELETE CASCADE` | `carries-over` | 04 §4.2 | T0.12a |
| `entity_relations_source_entity_id_target_entity_id_rel_type_key` | UNIQUE | `entity_relations` | `UNIQUE (source_entity_id, target_entity_id, rel_type)` | `carries-over` | 04 §4.2 | T0.12a |
| `entity_relations_target_entity_id_fkey` | FK | `entity_relations` | `FOREIGN KEY (target_entity_id) REFERENCES entities(id) ON DELETE CASCADE` | `carries-over` | 04 §4.2 | T0.12a |
| `knowledge_triples_pkey` | PK | `knowledge_triples` | `PRIMARY KEY (id)` | `dropped` | 04 §8.3 | — |
| `knowledge_triples_source_memory_id_fkey` | FK | `knowledge_triples` | `FOREIGN KEY (source_memory_id) REFERENCES memories(id) ON DELETE SET NULL` | `dropped` | 04 §8.3 | — |
| `llm_profiles_name_key` | UNIQUE | `llm_profiles` | `UNIQUE (name)` | `dropped` | 04 §7 | — |
| `llm_profiles_pkey` | PK | `llm_profiles` | `PRIMARY KEY (id)` | `dropped` | 04 §7 | — |
| `llm_profiles_provider_id_fkey` | FK | `llm_profiles` | `FOREIGN KEY (provider_id) REFERENCES llm_providers(id) ON DELETE RESTRICT` | `dropped` | 04 §7 | — |
| `llm_providers_name_key` | UNIQUE | `llm_providers` | `UNIQUE (name)` | `dropped` | 04 §7 | — |
| `llm_providers_pkey` | PK | `llm_providers` | `PRIMARY KEY (id)` | `dropped` | 04 §7 | — |
| `llm_purpose_configs_ml_profile_id_fkey` | FK | `llm_purpose_configs` | `FOREIGN KEY (ml_profile_id) REFERENCES ml_profiles(id) ON DELETE SET NULL` | `dropped` | 04 §7 | — |
| `llm_purpose_configs_pkey` | PK | `llm_purpose_configs` | `PRIMARY KEY (purpose)` | `carries-over` | 04 §7 | — |
| `llm_purpose_configs_profile_id_fkey` | FK | `llm_purpose_configs` | `FOREIGN KEY (profile_id) REFERENCES llm_profiles(id) ON DELETE SET NULL` | `dropped` | 04 §7 | — |
| `llm_purpose_configs_provider_id_fkey` | FK | `llm_purpose_configs` | `FOREIGN KEY (provider_id) REFERENCES llm_providers(id) ON DELETE SET NULL` | `dropped` | 04 §7 | — |
| `chk_superseded_has_pointer` | CHECK | `memories` | `CHECK (((status <> 'superseded'::memory_status) OR (superseded_by IS NOT NULL)))` | `carries-over` | 04 §3.1 | T0.12a |
| `fk_memories_superseded_by` | FK | `memories` | `FOREIGN KEY (superseded_by) REFERENCES memories(id) ON DELETE SET NULL` | `carries-over` | 04 §3.1 | T0.12a |
| `memories_pkey` | PK | `memories` | `PRIMARY KEY (id)` | `carries-over` | 04 §3.1 | T0.12a |
| `memory_crossrefs_memory_id_fkey` | FK | `memory_crossrefs` | `FOREIGN KEY (memory_id) REFERENCES memories(id) ON DELETE CASCADE` | `carries-over` | 04 §3.3 | — |
| `memory_crossrefs_pkey` | PK | `memory_crossrefs` | `PRIMARY KEY (memory_id, related_memory_id)` | `carries-over` | 04 §3.3 | — |
| `memory_crossrefs_related_memory_id_fkey` | FK | `memory_crossrefs` | `FOREIGN KEY (related_memory_id) REFERENCES memories(id) ON DELETE CASCADE` | `carries-over` | 04 §3.3 | — |
| `memory_tags_memory_id_fkey` | FK | `memory_tags` | `FOREIGN KEY (memory_id) REFERENCES memories(id) ON DELETE CASCADE` | `carries-over` | 04 §3.2 | T0.12a |
| `memory_tags_pkey` | PK | `memory_tags` | `PRIMARY KEY (memory_id, tag_id)` | `carries-over` | 04 §3.2 | T0.12a |
| `memory_tags_tag_id_fkey` | FK | `memory_tags` | `FOREIGN KEY (tag_id) REFERENCES tags(id) ON DELETE CASCADE` | `carries-over` | 04 §3.2 | T0.12a |
| `messages_conversation_id_fkey` | FK | `messages` | `FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE` | `carries-over` | 04 §7 | — |
| `messages_pkey` | PK | `messages` | `PRIMARY KEY (id)` | `carries-over` | 04 §7 | — |
| `ml_profiles_name_key` | UNIQUE | `ml_profiles` | `UNIQUE (name)` | `dropped` | 04 §7 | — |
| `ml_profiles_pkey` | PK | `ml_profiles` | `PRIMARY KEY (id)` | `dropped` | 04 §7 | — |
| `pipeline_failures_pkey` | PK | `pipeline_failures` | `PRIMARY KEY (id)` | `carries-over` | 04 §7 | — |
| `repositories_pkey` | PK | `repositories` | `PRIMARY KEY (id)` | `carries-over` | 04 §6 | T0.12b |
| `tags_name_key` | UNIQUE | `tags` | `UNIQUE (name)` | `carries-over` | 04 §3.2 | T0.12a |
| `tags_pkey` | PK | `tags` | `PRIMARY KEY (id)` | `carries-over` | 04 §3.2 | T0.12a |
| `token_blocklist_jti_key` | UNIQUE | `token_blocklist` | `UNIQUE (jti)` | `carries-over` | 04 §7 | — |
| `token_blocklist_pkey` | PK | `token_blocklist` | `PRIMARY KEY (id)` | `carries-over` | 04 §7 | — |

**Eleven of the 59 sit on §8-dropped tables**, three are the `llm_purpose_configs`
indirection FKs that go with their columns (§8), and two belong to `knowledge_triples`'
HEAD shape: its PK (§3.1's note) and its FK `source_memory_id → memories ON DELETE SET
NULL`, which goes with the rebuild — the target externalises provenance into
`fact_sources` and holds endpoints as soft references with no FK at all (doc 04 §8.3).
Forty-three carry over.

`chk_superseded_has_pointer` is reproduced verbatim from A.4 above and is the constraint
T0.12a's acceptance names explicitly. Its paired self-FK `fk_memories_superseded_by … ON
DELETE SET NULL` is what makes the demote-before-delete order load-bearing: the FK nulls a
dependent's pointer while it is still `superseded`, the CHECK fails, and the batch aborts.
Both carry over unchanged.

### 4.2 Triggers, functions, and types present at HEAD (A.5–A.7)

| Object | Kind | On | Definition | Disposition | Doc § | Lands in |
|---|---|---|---|---|---|---|
| `memories_fts_update` | trigger | `memories` | `CREATE TRIGGER memories_fts_update BEFORE INSERT OR UPDATE OF content ON public.memories FOR EACH ROW EXECUTE FUNCTION memories_fts_trigger()` | `carries-over` | 04 §3.1; 19 §2 | T0.12a |
| `memories_fts_trigger` | function | — | `plpgsql`; sets `NEW.search_vector := to_tsvector('english', COALESCE(NEW.content, ''))` | `carries-over` | 04 §3.1; 19 §2 | T0.12a |
| `memory_status` | enum | — | `ENUM ('active','deprecated','superseded')` | `carries-over` | 04 §2, §11 | T0.12a |

`memory_status` is the **one** native enum in the schema and doc 04 §2 fixes it as such:
every other state column (`verification_status`, article `status`, `memory_buffer.status`,
`review_state`) is CHECK-constrained `text`, and every "type" column
(`entity_type`, `rel_type`, `memory_type`) is `varchar` normalised in application code
against a closed set. A baseline that promoted any of them to an enum would be a
behaviour change, not a tidy-up.

### 4.3 Target-new constraints, triggers, and partitioning

| Object | Kind | On | Definition | Disposition | Doc § | Lands in |
|---|---|---|---|---|---|---|
| `UNIQUE (id, project)` support | UNIQUE | `memories` | Trivially satisfiable (`id` is already the PK). Exists **solely** so `memory_relations`' endpoint FKs can be declared composite `(memory_id, project)`, which makes a cross-project edge unrepresentable rather than merely forbidden. Omitting it makes `memory_relations` undeclarable — a hard prerequisite, not a nicety. | `target-new` | 04 §8.2, §10 | T0.12a |
| `touch_updated_at` | function | — | `plpgsql`; sets `NEW.updated_at := now()` and returns `NEW` | `target-new` | **F-20 resolution** (§9.2); doc 19 §2 rule, doc 04 §3.1/§9 semantic | T0.12a |
| `memories_touch_updated_at` | trigger | `memories` | `BEFORE UPDATE ON memories FOR EACH ROW EXECUTE FUNCTION touch_updated_at()` — replaces SQLAlchemy's client-side `onupdate`, which no raw-SQL writer honours | `target-new` | **F-20 resolution** (§9.2) | T0.12a |
| `conversations_touch_updated_at` | trigger | `conversations` | As above on `conversations` | `target-new` | **F-20 resolution** (§9.2) | T0.12b (F-02) |
| `repositories_touch_updated_at` | trigger | `repositories` | As above on `repositories` | `target-new` | **F-20 resolution** (§9.2) | T0.12b |
| `knowledge_triples` PK | PK | `knowledge_triples` | `id uuid PRIMARY KEY`, application-generated **UUIDv7** — the rebuild keeps a name, not an object (doc 04 §8.3) | `target-new` | 04 §8.3 | T0.12b |
| `events` composite PK | PK | `events` | `(id, created_at)` — the partition key must sit in the PK; nothing joins events by id, so folding `created_at` in costs nothing | `target-new` | 04 §8.1 | T0.12b |
| `events` monthly range partitioning | partitioning | `events` | `PARTITION BY RANGE(created_at)`, monthly, from day one — the **only** declaratively partitioned table in the schema | `target-new` | 04 §8.1, §2 | T0.12b |
| `events` append-only forbid-trigger | trigger | `events` | `BEFORE UPDATE OR DELETE OR TRUNCATE` … `RAISE`; role-agnostic, so it survives dump/restore. A `REVOKE`-based owner/app split is the recorded multi-user upgrade path. | `target-new` | 04 §8.1, §11; 19 §2 | **T1.06** — T0.12b's own text: "`events` is `RANGE(created_at)` partitioned (the trigger is T1.06's)" |
| `verification_status` CHECK | CHECK | `knowledge_triples` | `CHECK (verification_status IN ('candidate','corroborated','disputed','confirmed'))` | `target-new` | 04 §8.3, §10 | T0.12b |
| `fact_sources` dedupe key | UNIQUE | `fact_sources` | `UNIQUE (fact_id, source_kind, source_ref)` | `target-new` | 04 §8.3, §10 | T0.12b |
| `fact_sources` parent FK | FK | `fact_sources` | `fact_id → knowledge_triples(id) ON DELETE CASCADE` | `target-new` | 04 §8.3 | T0.12b |
| article `status` CHECK | CHECK | `knowledge_articles` | `CHECK (status IN ('candidate','corroborated','disputed','confirmed','superseded'))` | `target-new` | 04 §8.8 | T0.12b |
| article lineage self-FK | FK | `knowledge_articles` | `superseded_by → knowledge_articles(id)` | `target-new` | 04 §8.8 | T0.12b |
| citation parent FK | FK | `article_citations` | `article_id → knowledge_articles(id) ON DELETE CASCADE` | `target-new` | 04 §8.8 | T0.12b |
| citation **hard** fact FK | FK | `article_citations` | `fact_id → knowledge_triples(id)` — **the one hard FK**, and the deliberate contrast with §8.3's soft endpoint refs: facts are invalidate-not-delete, so the hard FK is safe and buys integrity at the one place a dangling citation would be a truth catastrophe | `target-new` | 04 §8.8 | T0.12b |
| `memory_relations` uniqueness | UNIQUE | `memory_relations` | `UNIQUE (source_memory_id, target_memory_id, rel_type)` | `target-new` | 04 §8.2, §10 | — (F-02) |
| `memory_relations` endpoint FKs | FK | `memory_relations` | `(source_memory_id, project) → memories(id, project) ON DELETE CASCADE` and the same for `target_memory_id` — **composite**, which is why the `UNIQUE (id, project)` support above exists | `target-new` | 04 §8.2 | — (F-02) |
| `memory_buffer` status CHECK | CHECK | `memory_buffer` | `CHECK (status IN ('pending','claimed','done','error'))` | `target-new` | 04 §8.6 | — (F-02) |
| `memory_community_members` PK + FKs | PK, FK | `memory_community_members` | `PRIMARY KEY (community_id, memory_id)`; `community_id → memory_communities ON DELETE CASCADE`; `memory_id → memories ON DELETE CASCADE` | `target-new` | 04 §8.4 | — (F-02) |
| `memory_access_stats` PK + FK | PK, FK | `memory_access_stats` | `memory_id uuid PRIMARY KEY REFERENCES memories(id) ON DELETE CASCADE` | `target-new` | 04 §9 | — (F-02) |
| `project_repositories` PK + FK | PK, FK | `project_repositories` | `PRIMARY KEY (project, repo_id)`; `repo_id → repositories(id)` | `target-new` | 04 §8.7, §10 | — (F-02) |
| `projects` PK | PK | `projects` | `PRIMARY KEY (name)` — lazy `INSERT … ON CONFLICT (name) DO NOTHING`; **no FK enforcement yet**, every scoped table keeps its bare `project text` | `target-new` | 04 §7, §10 | T0.12b |
| `documents` / `blocks` FKs | FK | `documents`, `blocks` | `blocks.document_id → documents ON DELETE CASCADE`; `blocks.parent_id → blocks ON DELETE CASCADE` (deleting a block takes its subtree) | `target-new, inert` | 04 §8.5 | T0.13 |

**Whether the baseline creates `events`' first monthly child partition is unresolved by
both docs.** Doc 04 §8.1 fixes monthly `RANGE(created_at)` from day one and doc 19 §9
stance 3 puts the *pre-create* arm on `pipeline_failure_cleanup`'s schedule, but neither
says whether the baseline itself lands month-0. **A partitioned parent with no matching
child rejects every insert**, so this is not cosmetic: a baseline that omits it produces a
database in which the first `events` write fails. Recorded as F-15 for T0.12b rather than
decided here.

## 5. Column-level changes on carried-over tables

One row per column change on a table §2 dispositions `reshaped`, plus the activations that
change no column at all. **Every "server default" statement here is read from Appendix
A.2, not from the default doc 04's tables print** — the two disagree, and §9 audits the
disagreement rather than reconciling it silently here.

| Table.column | Change | Disposition | Doc § | Note |
|---|---|---|---|---|
| `memories.origin_key` | **ADD** `text NULL` | `target-new` | 04 §3.1, §8.3 | Capture-session / agent-run identity — the corroboration-independence key. `COUNT(DISTINCT origin_key)` per fact is the promotion signal, so this column is why `fact_sources` can count origins instead of rows. Set NULL for every carried row at the cutover: unknown identity **merges to one origin (undercount), never mints distinct ones** (doc 19 §4). |
| `memories.llm_classified_type` → `classified_type` | **RENAME** | `reshaped` | 04 §3.1 | The `llm_` prefix drops because the classifier may be the local model — the column is source-neutral. **The target name collides with a column dropped at revision `0006`** carrying regex-classifier semantics (§8); a baseline built from migration history is exactly what gets that reuse wrong. |
| `memories.llm_summary` → `summary` | **RENAME** | `reshaped` | 04 §3.1 | |
| `memories.llm_emotions` → `emotions` | **RENAME** | `reshaped` | 04 §3.1 | |
| `memories.llm_flags` → `flags` | **RENAME** | `reshaped` | 04 §3.1 | |
| `memories.id` | v4 → **UUIDv7**, application-generated | `reshaped` | 04 §2, §3.1 | **No DDL change** — A.2 shows `uuid NOT NULL` with no server default today, and the target keeps exactly that. The change is in the generator, so a schema diff would show nothing; recorded here because the whole point of UUIDv7 (time-ordered B-tree insert locality) is lost silently if the generator is not changed with the baseline. `entities` and `entity_relations` deliberately keep server-side `gen_random_uuid()` (v4) — ANN-probed, not range-scanned, so insert locality buys nothing. |
| `memories.updated_at` | auto-bump moves from ORM `onupdate` to a **SQL trigger** | `reshaped` | **F-20 resolution** (§9.2) | No column-type change — `timestamptz NOT NULL DEFAULT now()` either way. The change is that `touch_updated_at` now maintains it, so a raw-SQL `UPDATE` bumps it too. `conversations.updated_at` and `repositories.updated_at` take the same treatment. Keep the ORM's `onupdate=` or drop it — with the trigger authoritative it is redundant either way, and the model still mirrors the SQL. |
| `memories.{id, content, source, importance, metadata, is_archived}` | server defaults | **see §9** | 04 §3.1 vs A.2 | A.2 shows all six `NOT NULL` with **no server default**. Doc 04 §3.1 prints `0.5`, `{}` and `false` for `importance`/`metadata`/`is_archived` as if they were DDL defaults, and prints `source`'s as "ORM `'api'`". A plain-SQL INSERT omitting any of them fails today. Adjudicated in §9, not here. |
| `memories.importance` | **activation by read** — no schema change | `carries-over` | 04 §9; 19 §3 | Populated at ingest today, never read by ranking. The target reads it behind a `w_*` flag defaulting to 0. First reader **T2.30** (§7). |
| `memories.expires_at` | **activation by population** — no schema change | `carries-over` | 04 §3.1, §8.3 | Swept by `expired_memory_cleanup` today; the target additionally populates it from a fact's own stated expiry (self-expiring dated facts). First writer **T2.34** (§7). |
| `memories.confidence` | value-quality change — no schema change | `carries-over` | 04 §9 | Already read by ranking (`_apply_confidence_weighting`). The change is replacing a placeholder value with a real estimate. |
| `entities.repo_ids` | **ADD** `uuid[] DEFAULT '{}'` | `target-new, inert` | 04 §4.1, §4.2; 19 §3 | The invariant-8 amendment: a repo id is the code-side analog of a memory id, letting code assert a graph row without a memory. Lands with **empty arrays**, so both orphan sweeps' amended `NOT EXISTS (live repo)` predicates are vacuously true and behaviour is byte-identical to today. First writer in §7. |
| `entity_relations.repo_ids` | **ADD** `uuid[] DEFAULT '{}'` | `target-new, inert` | 04 §4.2; 19 §3 | As above. |
| `repositories.index_debt` | **ADD** `jsonb` | `target-new, inert` | 04 §6 | Persists the T2 re-trace drain: the 500-caller cap currently drops work silently, so outstanding debt is recorded and drained in continuation batches. **Doc 19 §3's disposition table does not carry a row for it and T0.13's object list does not name it** (F-13). First writer in §7. |
| `llm_purpose_configs.provider_id`, `.profile_id`, `.ml_profile_id` | **DROP** | `dropped` (§8) | 04 §7; 19 §3 | The indirection columns doc 19 §3 calls "every `*_ref`" — none is actually named `*_ref` (F-08). |
| `llm_purpose_configs.classifier_kind` | **ADD** `text` on the `classification` purpose row | `target-new` | 04 §7 | `llm \| local` — the in-process classifier re-homed inline, replacing the deleted `ml_profiles` reference. When the `[ml]` extra is absent, classification falls back to the LLM-backed classifier. |
| `llm_purpose_configs.provider` | **unresolved** — kept or dropped | see F-10 | 04 §7 vs A.2 | A.2 shows `provider varchar NOT NULL DEFAULT 'ollama'` at HEAD; doc 04 §7's inline field list does not mention it, and fixes `api_kind` as the sole vendor-quirk home. Not decided here. |
| `config.value` | server default `'{}'` | see F-09 | 04 §7 vs A.2 | Doc 04 §7 prints `value jsonb NOT NULL DEFAULT '{}'`; A.2 shows no server default. Same class as the `memories` deltas — adjudicated in §9. |
| `repositories.{id, provider, default_branch, auto_sync, status}` | server defaults | **see §9** | 04 §6 vs A.2 | A.2 shows all five `NOT NULL` with **no server default**, while doc 04 §6 prints `provider 'local'` and `default_branch 'main'`. The plan for this task located the ORM-default class on `memories` alone; it is wider (§9). |

**`memories`' column ordinals carry the fingerprint of the `0006` drop.** A.2 shows
`memories` jumping from ordinal 11 (`is_archived`) to ordinal 14 (`llm_classified_type`) —
positions 12 and 13 are the dropped `classified_type` and `classified_confidence`. The
baseline, built from empty, will not reproduce that gap, which is a cosmetic difference and
the only one: no code reads a column by ordinal.

## 6. Per-fingerprint partition templates (registry entries, not DDL)

**A row here is not something the baseline creates — it is something the baseline must
NOT create.** Doc 19 §2 expressly rejects static child-table DDL: "expressing the child
tables as static migrations — the DDL is runtime-parameterised by fingerprint, which no
static migration can express". T0.12c says the same in its own words: "The four
per-fingerprint embedding templates land here as **registry entries** … nothing about
them belongs in the Alembic file." So this section exists loudly enough that a T0.12c
executor reading only §3 does not add eight `CREATE TABLE`s.

The evidence is empirical, not asserted. **A freshly migrated database holds zero
`*__<slug>` child tables** (Appendix A, assertion row 7), and no migration statement
creates one (Appendix B check 5). Child tables are minted at `register` time and, in the
target, reconciled at every boot (T0.14).

`<N>` is the fingerprint's `dims`. **Every** child, existing or target-new, additionally
carries an HNSW index on `embedding vector_cosine_ops WITH (m = 16, ef_construction =
128)`, whose name is a blake2b digest (`ix_hnsw_<16hex>`) rather than a derived name,
because `ix_<child>_hnsw` can exceed Postgres' 63-character `NAMEDATALEN` limit for the
longest parent plus a 48-character slug — where the server *silently truncates* and two
fingerprints could collide. The `Aux indexes` column below lists what each parent carries
**in addition** to that HNSW index.

| Parent | Child pattern | Key columns / PK | Aux indexes | Disposition | Doc § | Registry entry lands in | First writer |
|---|---|---|---|---|---|---|---|
| `memory_embeddings` | `memory_embeddings__<slug>` | `memory_id uuid → memories(id) CASCADE`, `fingerprint text → embedders(fingerprint)`, `embedding vector(N) NOT NULL`, `payload jsonb NOT NULL DEFAULT '{}'`, `created_at`; **PK `(memory_id, fingerprint)`** | `(memory_id)` | `carries-over` | 04 §5.2 | already registered — unchanged by the baseline; reconciled by **T0.14** | — (no inert row; live today) |
| `entity_embeddings` | `entity_embeddings__<slug>` | `entity_id uuid → entities(id) CASCADE`, `fingerprint`, `embedding vector(N) NOT NULL`, `created_at`; **PK `(entity_id, fingerprint)`** | `(entity_id)` | `carries-over` | 04 §5.2 | as above | — (no inert row; live today) |
| `code_chunk_embeddings` | `code_chunk_embeddings__<slug>` | `id uuid DEFAULT gen_random_uuid()`, `fingerprint`, `repo_id uuid → repositories(id) CASCADE`, `file_path varchar(1024) NOT NULL`, `language`, `symbol_name`, `chunk_content`, `line_start`, `line_end`, `embedding vector(N)`, `created_at`; **PK `(id, fingerprint)`** | `(repo_id)`, `(repo_id, file_path)` | `carries-over` | 04 §5.2 | as above | — (no inert row; live today) |
| `entity_embedding_cache` | `entity_embedding_cache__<slug>` | `name_lower varchar(255)`, `fingerprint`, `embedding vector(N)`, `created_at`, `last_used_at`, `hit_count int DEFAULT 1`; **PK `(name_lower, fingerprint)`** | `(last_used_at)` | `carries-over` | 04 §5.2 | as above | — (no inert row; live today) |
| `block_embeddings` | `block_embeddings__<slug>` | `block_id uuid → blocks(id) CASCADE`, `fingerprint`, `embedding vector(N)`, `payload jsonb DEFAULT '{}'`, `created_at`; **PK `(block_id, fingerprint)`** | mirrors `memory_embeddings` | `target-new, inert` | 04 §5.3; 19 §3 | **T0.12c** (inert labelling **T0.13**) | **TH1.05** (§7) |
| `relation_embeddings` | `relation_embeddings__<slug>` | `relation_id uuid → entity_relations(id) CASCADE`, `fingerprint`, `embedding vector(N)`, `created_at`; **PK `(relation_id, fingerprint)`** | HNSW only | `target-new, inert` | 04 §5.3 | **T0.12c** (inert labelling **T0.13**) | **T2.49** (§7) |
| `article_embeddings` | `article_embeddings__<slug>` | `article_id uuid → knowledge_articles(id) CASCADE`, `fingerprint`, `embedding vector(N)`, `payload jsonb DEFAULT '{}'`, `created_at`; **PK `(article_id, fingerprint)`** | mirrors `memory_embeddings` | `target-new, inert` | 04 §5.3 | **T0.12c** (inert labelling **T0.13**) | **T3.23** (§7) |
| `triple_embeddings` | `triple_embeddings__<slug>` | `fact_id uuid → knowledge_triples(id)` — **no cascade** — `fingerprint`, `embedding vector(N)`, `created_at`; **PK `(fact_id, fingerprint)`** | HNSW only | `target-new, inert` — **template only** | 04 §5.3, §13; 19 §3 | **T0.12c** (inert labelling **T0.13**) | **T2.33**, conditional (§7) |

**Three rules in that table are load-bearing and silent when broken.**

`relation_embeddings` keys on the **real `entity_relations.id`** with `ON DELETE CASCADE`
— no synthetic ids — so when re-extraction's strip-before-rewrite or the self-healing
delete removes a relation, its vector dies with it instead of orphaning. And because
`entity_relations` is **global**, this channel carries **no project predicate of its own**:
a project-scoped retrieval that consults it must scope through the asserting memories'
`memory_ids`, or label the results, or it re-opens exactly the cross-project leak the
filter-pushdown work closes (doc 04 §5.3, §10, invariant 14).

`triple_embeddings` references `knowledge_triples.id` with **no cascade**, because facts
are **invalidate-not-delete**: a cascade would destroy the history the fact layer exists
to keep. It is also the one row that is `template only` — the template ships now, the
**writer is deferred** behind a measured `pg_trgm`-on-`fact` undercount, and when it ships
it groups facts **for counting only, never merging rows or rewriting `triple_key`**,
carrying the `names_distinct` guard.

**Adding a template is near-free only because the creation sweep is retired.** The
registry creates a fingerprint's children at *register* time, so every already-registered
fingerprint would be missing a newly-added parent. That is why doc 04 §5.3 and doc 19 §2
replace the one-time sweep with a **permanent boot-time reconciliation** (T0.14) that
iterates the live `embedders` rows and runs each template's `CREATE TABLE IF NOT EXISTS`
plus each aux index's `CREATE INDEX IF NOT EXISTS`, idempotently. This is also what makes
a restored dump self-heal, and what makes the deferred .NET replay a loop over rows
running parameterised plain SQL rather than a re-derivation.

**One thing the baseline's `downgrade()` must get right that today's does not.** Migration
`0001`'s `downgrade()` walks `pg_tables` and drops child tables matching four `LIKE`
patterns — `memory_embeddings__%`, `entity_embeddings__%`, `code_chunk_embeddings__%`,
`entity_embedding_cache__%`. Once the four target-new families exist, that sweep leaves
`block_embeddings__*`, `relation_embeddings__*`, `article_embeddings__*` and
`triple_embeddings__*` behind. It is moot for the six revisions (which the baseline
deletes) but not for the baseline's own downgrade, which must cover all eight (F-17).

## 7. Inert objects and their first writers

**"Every inert object names the phase and the task that will first write to it" is only
satisfied if the cited task exists and actually writes that object.** A plausible-looking
id that resolves to a different task is worse than a blank, because it reads as verified.
Two independent defences back every row below. `check_plan.py` already lints every
`T…`-shaped reference in `docs/planning/*.md` against the defined task set, so an invented
id fails mechanically the moment this file lands (Appendix B check 6) — but that proves
only that an id *exists*. The **task's own words** column proves it is the *right* id, and
it is quoted so a reviewer can check the pairing without opening the epic file.

The phase comes from doc 20 §6's honesty-tag timeline first, and the id search is then
scoped to the epic that owns that phase — E1 is Phase 1, E2 is Phase 2, E3 is Phase 3, E4
is Phase 4, EH1 is the H1 horizon. An id found in the wrong epic for its phase would be a
finding, not a row; none was.

| Object | Disposition | Phase | First-writer task | The task's own words | Doc § |
|---|---|---|---|---|---|
| `entities.repo_ids[]` | `target-new, inert` | **Phase 2** (doc 20 §6: "C4: `repo_ids[]` writer — the deriver, doc 10, after G-C") | **T2.27** — `assert_from_repo` — imports-only, LLM-free | "A narrow deterministic deriver minting Layer-1 assertions from a repo's import edges only, tagged into the inert `entities.repo_ids[]` / `entity_relations.repo_ids[]` landed in T0.13 — **this is their first writer**." | 04 §4.1, §4.2; 19 §3 |
| `entity_relations.repo_ids[]` | `target-new, inert` | **Phase 2** | **T2.27** | As above — the same task writes both arrays. | 04 §4.2; 19 §3 |
| `ix_entities_repo_ids`, `ix_entity_relations_repo_ids` | `target-new, inert` | **Phase 2** | **T2.27** | The GIN indexes exist from the baseline; T2.27 is the first task whose writes make them non-empty. | 04 §4.1, §4.2 |
| `repositories.index_debt` | `target-new, inert` | **Phase 1** | **T1.39** — T2 index-debt drain | "Dependent-caller re-trace overflow past the retrace cap persists to `repositories.index_debt` and drains in continuation batches. **Never dropped** — silent truncation here is a graph that is quietly wrong." | 04 §6 (**not** in doc 19 §3's table — F-13) |
| `documents` (table + its partial-unique index) | `target-new, inert` | **H1 horizon** | **TH1.02** — `documents` / `blocks` first writer | "First writer to the tables landed inert in T0.13. Document identity is the partial `UNIQUE (project, uri)` with `content_hash` as the re-ingest change gate … the tables lose their inert label." | 04 §8.5; 19 §3 |
| `blocks` (table + its two indexes) | `target-new, inert` | **H1 horizon** | **TH1.02** | As above — one task writes both tables. | 04 §8.5; 19 §3 |
| `block_embeddings` template | `target-new, inert` | **H1 horizon** | **TH1.05** — `block_embeddings__<slug>` writer | "First writer to the block partition template landed inert in T0.13." | 04 §5.3; 19 §3 |
| `relation_embeddings` template | `target-new, inert` | **Phase 2** | **T2.49** — `relation_embeddings` refresh job + writer | "First writer to one of the two inert partition templates that had no named owner … **The template loses its inert label and the schema inventory records this task as its first writer**." | 04 §5.3 |
| `article_embeddings` template | `target-new, inert` | **Phase 3** | **T3.23** — Articles retrieval channel + `article_embeddings` writer | "The template loses its inert label; **the schema inventory names this as its writer** (it is the last of the four **mainline** templates — `block_embeddings` waits for the EH1 horizon, and `triple_embeddings` may never ship at all)." | 04 §5.3 |
| `triple_embeddings` template | `target-new, inert` — **template only** | **Phase 2, conditional** | **T2.33** — `triple_embeddings` writer, miss-rate gated | "First writer to the template landed inert in T0.13 — and it ships **only** if T2.11's measured `pg_trgm` shortlist miss rate exceeds its stated bar … if the bar is not exceeded, the task closes as 'not needed, measured' and **the template stays inert**." | 04 §5.3, §13; 19 §3 |

**Four of these ten rows are confirmed by a reciprocal promise, which is the strongest
evidence available.** T2.27, T2.49, T3.23, T2.33, TH1.02 and TH1.05 each name T0.13 as the
task that landed the object inert, and T2.49 and T3.23 go further, carrying an acceptance
checkbox that this inventory records them as the writer. An object whose future writer's
own acceptance promises to update this file is a pairing neither side can drift from
silently.

**`triple_embeddings` is the one row whose writer may never ship, and that is by design.**
It is `template only`: the template lands, and T2.33 is gated on a measured miss rate it
may not clear. If it does not, the honest end state is a template that stays inert
forever — which is why doc 19 §3 gives it its own `(target-new, template only)`
disposition rather than folding it in with the others.

**Two activations are not inert objects and are recorded separately.** `api_keys` and
`memories.importance` exist today and their schema does not change; only a later phase's
*read* path does, so §2 and §5 disposition them `carries-over` with a first-**reader**
rather than a first-writer. `api_keys`' reader is **T4.01** (Phase 4: "The `api_keys` table
exists today and is unwired — every write passes `api_key_id=None`. Wire it to
`dmk_<key_id>_<secret>` with a closed scope set"); `memories.importance`' reader is
**T2.30** (Phase 2: "The column is populated but unread today. Measure, then activate or
leave at zero"). `memories.expires_at` is an activation-by-population whose first writer is
**T2.34** — self-expiring dated facts.

## 8. Not landed — dropped objects, and why

**The four dispositions of §2 govern objects the baseline *lands*; they cannot express
"present today, deliberately absent tomorrow".** Recording exactly that is the point of a
task whose purpose is to prevent the baseline from being an accident of migration
history: without this section a reader cannot tell a deliberate omission from an
oversight. So dropped objects get their own two-value vocabulary — `dropped`, and
`dropped, optional transform` for the one object whose rows may be carried at cutover as
a convenience. The vocabulary extension is recorded as a Tier-2 amendment in §10 (A-01).

| Object | Present at HEAD | Disposition | Doc § | Why it does not land |
|---|---|---|---|---|
| `audit_log` (table) | yes | `dropped, optional transform` | 04 §7, §8.1; 19 §3, §4 | `events` (§2) is the sole audit substrate from day one. Coarse, memory-level, no FKs, no indexes beyond the PK, and its `api_key_id` is always NULL because `api_keys` is unwired. The greenfield has no compatibility window. Doc 19 §4 keeps a one-time transform of legacy rows into `events` at the homelab cutover — `action → event_type`, `memory_id → object_id`, `details → payload` — as a **convenience taken only if the mapping is trivial**, skipped without loss otherwise, which is why this is not a plain drop. |
| `enrichment_queue` (table) | yes | `dropped` | 04 §6, §12; 19 §3 | Zero code references — no app path inserts or selects from it. The live enrichment backlog is the `code_symbols.enrichment_status='pending'` partial index added at revision `0005`. Doc 04 §12 calls it "droppable once confirmed unreferenced" and doc 04 §7's operations-table set already omits it; doc 19 §3 resolves "droppable" to "never created" for the greenfield. |
| `llm_providers` (table) | yes | `dropped` | 04 §7; 19 §3 | The LLM-config flattening. darkmem is not an LLM proxy, so the provider indirection is removed and each purpose row carries its connection inline. Doc 19 §3: these "**never exist** in the baseline — the flattening is greenfield, not a transform". |
| `llm_profiles` (table) | yes | `dropped` | 04 §7; 19 §3 | Same flattening; the profile-management UI goes with it. |
| `ml_profiles` (table) | yes | `dropped` | 04 §7; 19 §3 | Same flattening. The in-process classifier is re-homed as an inline `classifier_kind = llm \| local` on the `classification` purpose row, not referenced through a profile table. |
| `llm_purpose_configs.provider_id` (column, uuid FK) | yes | `dropped` | 04 §7; 19 §3 | One of the three indirection columns doc 19 §3 calls "every `*_ref`". None is actually named `*_ref` — see F-08. |
| `llm_purpose_configs.profile_id` (column, uuid FK) | yes | `dropped` | 04 §7; 19 §3 | As above. |
| `llm_purpose_configs.ml_profile_id` (column, uuid FK) | yes | `dropped` | 04 §7; 19 §3 | As above; its replacement is the inline `classifier_kind`. |
| `memories.classified_type` (regex-era column) | **no** — dropped at `0006` | `dropped` | 04 §3.1 | The regex classifier's verdict column, removed when LLM classification became unconditional. Listed here because **the name returns**: the target reuses `classified_type` as the rename target of `llm_classified_type`, carrying the LLM-or-local-classifier verdict, not the old regex semantics (§5). A baseline built from migration history is exactly what would get that name reuse wrong. |
| `memories.classified_confidence` (regex-era column) | **no** — dropped at `0006` | `dropped` | 04 §3.1 | The regex classifier's confidence score. Doc 04 §3.1 is explicit that it is **not** reintroduced — unlike `classified_type`, the name does not return. |

**Indexes and constraints belonging to a dropped table leave with it** and are not
dispositioned individually in §3/§4 — §8 already records why they go. The set-difference
check in Appendix B accounts for them on that basis rather than by omission.

## 9. SQL-first audit

**The rule being audited, quoted so the verdict column means something.** Doc 19 §2:
"Every table, constraint, index, trigger, and the reconciliation's own DDL stays
expressible as plain SQL — **no ORM-only construct is load-bearing anywhere in the
schema** … the FTS trigger, the `events` forbid-trigger and its monthly
`RANGE(created_at)` partitioning, the partial and composite indexes, the
`chk_superseded_has_pointer` CHECK, and the one native enum are all authored as SQL in the
baseline; SQLAlchemy models mirror the SQL, not the reverse. A schema change that only an
ORM construct can express is rejected at review as a portability regression." Doc 20 §7
makes it standing across Phases 0–4.

**`In the DDL?` is answered from Appendix A, never from reading the migration.** A
construct is in the DDL if and only if the extracted manifest shows it. That is the whole
methodology of this section: the phantom UNIQUE below is invisible to anyone who audits by
reading `__table_args__` against `0001`.

**Completeness of the sweep, stated as a number.** The two `rg` sweeps of Appendix B check
7 return hits across nine construct kinds: `server_default` (21 declarations),
`UniqueConstraint` (5 declarations), `__table_args__` (5 blocks), `onupdate=` (3),
`CheckConstraint` (1), `Index(` (1), `create_type=False` (1), `event.listen` (1), and no
hits at all for `server_onupdate`, `@validates`, `@hybrid_property`, `DDL(`, `Computed(` or
`Identity(` — so those six construct classes simply do not exist in this codebase, which is
itself a compliance result. §9.1 carries one row per distinct construct; the one bulk kind
is `server_default`, and it is dispatched mechanically rather than row by row: **all 21
declarations are mirrored by a real server default in Appendix A.2 — zero are ORM-only**
(Appendix B check 8). The kinds that survive that filter are the rows below, plus the two
sections that follow.

### 9.1 Structural constructs

| Construct | Where | What it does | In the DDL? | Load-bearing? | Verdict | Action for T0.12a–c |
|---|---|---|---|---|---|---|
| `CheckConstraint("status != 'superseded' OR superseded_by IS NOT NULL", name="chk_superseded_has_pointer")` | `models/memory.py:72–77` | The supersession lifecycle contract | **Yes** — A.4 shows it verbatim | Yes | **Compliant** — the ORM mirrors SQL that exists | Author as SQL; T0.12a's acceptance already names it |
| `ForeignKey("memories.id", ondelete="SET NULL")` on `superseded_by` | `models/memory.py:61–65` | The self-FK that forces demote-before-delete | **Yes** — `fk_memories_superseded_by` in A.4 | Yes | **Compliant** | Author as SQL |
| `Enum(*MEMORY_STATUS_VALUES, name="memory_status", **create_type=False**)` | `models/memory.py:58` | The one native enum | **Yes** — A.7 | Yes | **Compliant, and deliberately so.** `create_type=False` is the ORM explicitly declining to own the type: the SQL creates it, the model mirrors it. This is doc 19 §2's rule already implemented. | Author `CREATE TYPE` as SQL; keep `create_type=False` |
| `UniqueConstraint("name", "entity_type")` | `models/graph.py:23` | Entity uniqueness (inv. 4) | **Yes** — A.4 | Yes | **Compliant** | Author as SQL |
| `UniqueConstraint("source_entity_id", "target_entity_id", "rel_type")` | `models/graph.py:43` | Relation uniqueness (inv. 4) | **Yes** — A.4 | Yes | **Compliant** | Author as SQL |
| `UniqueConstraint("repo_id", "kind", "key")` / `(...6 cols...)` on edges | `models/code.py:82, 99–101` | Code-graph node/edge identity | **Yes** — A.4 | Yes | **Compliant** | Author as SQL |
| `Index("ix_token_blocklist_jti", "jti")` | `models/token_blocklist.py:20` | A plain btree on `jti` | **Yes** — A.3 | **No** — fully redundant under `token_blocklist_jti_key` (UNIQUE) | **Compliant but redundant** (F-12) | Land the UNIQUE only; drop the model's `Index` with it |
| `UniqueConstraint("purpose", name="uq_llm_purpose_configs_purpose")` | `models/llm_config.py:174` | Intended belt-and-suspenders over the PK | **NO** — A.4 shows `llm_purpose_configs` carrying only its PK on `purpose` and three FKs | No | **Phantom.** The table is built by raw `CREATE TABLE` inside `op.execute`, so `__table_args__` never reached the database. **Doc 04 §12 reasons about this object** — "The `llm_purpose_configs` redundant `UNIQUE(purpose)` … can stay or be dropped; it is harmless" — i.e. it discusses keeping or dropping a constraint **that was never created**. Harmless in effect, and the cleanest possible demonstration that this audit is not ceremonial. | Nothing to carry. `llm_purpose_configs` is `reshaped` anyway; do not resurrect the constraint from ORM metadata |
| `_TABLE_TEMPLATES` / `_AUX_INDEXES` | `services/embedder_registry.py:31–97` | The per-fingerprint child DDL | n/a — runtime, by design (§6) | Yes | **Compliant.** Every template is a **plain-SQL string** with `{name}`/`{dims}` placeholders, not a SQLAlchemy schema object, so doc 19 §2's "the reconciliation's own DDL" clause holds: the .NET port's equivalent is a loop over `embedders` rows running the same parameterised SQL. The HNSW index name is a blake2b digest rather than a derived name, which is a `NAMEDATALEN` defence, not an ORM dependency. | Keep as strings; T0.12c adds four entries, T0.14 runs the reconciliation |
| `@event.listens_for(engine.sync_engine, "connect")` setting `hnsw.ef_search=100`, `hnsw.iterative_scan=relaxed_order` | `database.py:19–25` | Per-connection pgvector GUCs | n/a — session settings, not schema | Yes, for recall behaviour | **Out of scope for doc 19 §2** (it governs the schema), but recorded: it is the codebase's only `event.listen`, and a .NET port must reproduce it in Npgsql connection setup or silently change ANN recall. | No baseline action; noted for the doc 19 §7 replay residuals |

### 9.2 The `updated_at` auto-bump — **Tier 3, escalated, not resolved here**

`models/memory.py:48` declares `updated_at … server_default=func.now(), onupdate=func.now()`.
SQLAlchemy's `onupdate` is **client-side**: it emits the new value in the ORM's own UPDATE
and does nothing to the database. Appendix A.2 shows `memories.updated_at` with server
default `now()` and A.5 shows the **only** user trigger in the entire schema is
`memories_fts_update`. So the bump exists solely in Python. `conversations.updated_at`
(`models/chat.py:19`) and `repositories.updated_at` (`models/code.py:28`) carry the
identical construct.

The contradiction, with both sides quoted:

- **Doc 04 §3.1** lists the column as `now() (onupdate)` in its schema table, and **doc 04
  §9 reasons *from* the bump as a semantic worth protecting** — it is the entire
  justification for `memory_access_stats` being a side table rather than two columns on
  `memories`: "any ORM-path update would additionally fire `onupdate=now()`, silently
  corrupting `updated_at`'s 'content changed' meaning."
- **Doc 19 §2** forbids a load-bearing ORM-only construct and enumerates the triggers the
  baseline authors — the FTS trigger and the `events` forbid-trigger — **with no third**.
  **Doc 04 §12**'s own enumeration of what the baseline creates names no `updated_at`
  trigger either.

**Either the baseline gains a trigger no doc lists, or a documented semantic stays ORM-only
in violation of a rule both doc 19 §2 and doc 20 §7 state as binding.** The .NET replay
sharpens it: `onupdate` is SQLAlchemy-specific behaviour that a DbUp replay would have to
re-derive from ORM metadata, which is precisely what doc 19 §2 says a replay must never do.
Neither doc resolves it. Under runbook §5 this was **Tier 3 — a design doc is wrong or
ambiguous — and Tier 3 means do not proceed to resolve it.** It was escalated with both
readings stated and no pick.

#### The measurement that informed the decision

Before escalating, the two live code paths that write `memories.status` were tested against
a scratch database built from the six revisions (dropped afterwards, no residue):

| Update form | Used by | `updated_at` bumped? |
|---|---|---|
| SQLAlchemy Core `update(Memory)` | `services/supersession.py:128–132` (the supersession flip) | **Yes** |
| Raw `text("UPDATE memories SET status='deprecated' …")` | `services/memory.py:148–154` and `services/job_runners.py:170` (demote-before-delete) | **No** |

So **today's behaviour is already inconsistent**: the same logical operation — a status
change on a memory — moves `updated_at` or does not, depending on which construct the
author reached for. That is an artifact, not a design, and no doc describes it.

#### Resolution — maintainer decision, 2026-07-27

**Reading 1 is adopted: the baseline authors the bump as SQL.** One `plpgsql` function and
a `BEFORE UPDATE` trigger on each table carrying `updated_at`:

```sql
CREATE FUNCTION touch_updated_at() RETURNS trigger AS $$
BEGIN
    NEW.updated_at := now();
    RETURN NEW;
END $$ LANGUAGE plpgsql;

CREATE TRIGGER memories_touch_updated_at BEFORE UPDATE ON memories
    FOR EACH ROW EXECUTE FUNCTION touch_updated_at();
-- likewise conversations, repositories
```

**Why.** It satisfies doc 19 §2's SQL-first rule rather than excusing an exception to it,
and it makes doc 04 §9's reasoning — that `updated_at` means "content changed" and must not
be corrupted — true on **every** write path instead of only the ORM ones. It also closes the
measured hole above: after this, a status demotion bumps `updated_at` whichever path
performs it. The behaviour change versus today is confined to the two raw-SQL
demote-before-delete paths, which currently leave the column stale on a change they made.

**The obligation this creates, stated so it is not lost.** Doc 04 §12 and doc 19 §2 each
enumerate the triggers the baseline authors — the FTS trigger and the `events`
forbid-trigger — and **neither lists a third**. Adopting Reading 1 means those two
enumerations are now incomplete. **The controller must amend doc 04 §12 and doc 19 §2 to
name `touch_updated_at` and its three triggers.** No step of T0.11 edits the design corpus;
the decision is recorded here and the doc edit is surfaced in the completion report.

The rows themselves are in §4.3.

### 9.3 Column defaults that live only in the ORM

**Scope first, because the plan for this task under-counted it.** That plan named "five NOT
NULL columns on `memories`". Cross-referencing every client-side `default=` in
`app/models/*.py` against A.2's nullability and server default gives **twelve non-key
columns across five surviving tables**, plus seven uuid primary keys:

| Table | NOT NULL columns whose only default is in the ORM | ORM default |
|---|---|---|
| `memories` | `source`, `importance`, `metadata`, `is_archived` | `'api'`, `0.5`, `dict`, `False` |
| `repositories` | `provider`, `default_branch`, `status`, `auto_sync` | `'local'`, `'main'`, `'pending'`, `True` |
| `code_symbols` | `enrichment_status`, `enrichment_priority` | `'pending'`, `0` |
| `api_keys` | `scopes` | `lambda: ["read", "write"]` |
| `config` | `value` | `dict` |

A plain-SQL `INSERT` omitting any of them fails today. **The uuid primary keys are
deliberately not in this class**: doc 04 §2 fixes application generation as the design
("every application-generated uuid PK is **UUIDv7**"), with server-side
`gen_random_uuid()` only for `entities`/`entity_relations`. `code_graph_nodes`/`code_edges`
carry `bigserial` sequences in the DDL and their models' `default=uuid.uuid4` is dead
metadata the database overrides — cosmetic, not load-bearing.

**Verdict: this is Tier 2, not Tier 3 — the corpus does answer it.** Applying the stated
test (*does doc 19 §2's "no ORM-only construct is load-bearing in the schema" cover column
value defaults, or only structural objects?*): doc 19 §2's own enumeration is entirely
structural — trigger, partitioning, indexes, CHECK, enum — and its rationale is that a
replay must not "re-derive behaviour from ORM metadata". A missing column default does not
make the schema inexpressible in SQL; it makes callers supply a value. So doc 19 §2 does
**not** independently force these defaults into the DDL.

What does force three of them is **doc 04 itself**, which doc 19 §1 makes authoritative for
table shapes: doc 04 §3.1 prints `0.5`, `{}` and `false` for `importance`, `metadata` and
`is_archived` in its target column table, with no ORM annotation — so the **target** shape
carries them as DDL defaults even though HEAD does not, which is why §5 records those as
`reshaped`. Doc 04 §3.1 annotates `source`'s as **"ORM `'api'`"**, knowingly recording an
ORM-only default, so `source` stays as it is. `config.value` is the same case as the first
three (doc 04 §7 prints `NOT NULL DEFAULT '{}'`, F-09) and `repositories`' four are the
same as `source`'s in reverse — doc 04 §6 prints `provider 'local'` and
`default_branch 'main'` without saying which side owns them (F-18).

**Action for T0.12a–c:** author server defaults for `memories.{importance, metadata,
is_archived}` and `config.value`; leave `memories.source` ORM-only as doc 04 §3.1
specifies; treat `repositories.{provider, default_branch}` as doc-04-printed defaults and
author them too, recording the reading. Cost is one clause per column; the benefit is that
a hand-written `INSERT` — in a migration, a fixture, a psql session, or the .NET replay —
behaves the same as an ORM write.

## 10. Findings — where the sources disagree

Twenty-one findings and one amendment, each tiered against
[`agent-runbook.md`](agent-runbook.md) §5. **Tier 1** is task-local. **Tier 2** reaches
beyond this task — it changes what a later task must do, so it is corrected, logged, and
*surfaced*. **Tier 3** contradicts the design corpus and **stops execution** rather than
being resolved here.

| Tier | Count | Findings |
|---|---|---|
| **3 — escalated, answered 2026-07-27** | 1 | F-20 — resolved, no longer blocking |
| **2 — changes a later task's work** | 8 findings + 1 amendment | F-02, F-08, F-09, F-13, F-14, F-15, F-17, F-21, and A-01 |
| **1 — task-local, recorded** | 12 | F-01, F-03, F-04, F-05, F-06, F-07, F-10, F-11, F-12, F-16, F-18, F-19 |

### Tier 3 — not resolved here

> **Runbook §5: "Do not proceed. Write up what you found, what the doc says, and why they
> cannot both be true, and stop."** The finding below was escalated on 2026-07-27 and
> **answered the same day by the maintainer**; it is retained in full — the contradiction,
> both readings, and the resolution — because a Tier-3 that is silently deleted once
> answered leaves the next reader unable to tell a decision from an oversight. **T0.12a is
> unblocked.**

| # | Sources in conflict | What each says | Status |
|---|---|---|---|
| **F-20** | doc 04 §3.1 + §9 vs doc 19 §2 + doc 04 §12 | **`updated_at`'s auto-bump has no SQL home.** `backend/app/models/memory.py:48` declares `updated_at … server_default=func.now(), onupdate=func.now()`. SQLAlchemy's `onupdate` is **client-side** — it emits the value in the ORM's own UPDATE and does nothing to the database. Appendix A.2 shows the column with server default `now()`; Appendix A.5 shows the **only** user trigger in the whole schema is `memories_fts_update`. The bump exists solely in Python, and `conversations.updated_at` (`models/chat.py:19`) and `repositories.updated_at` (`models/code.py:28`) carry the identical construct.<br><br>**Reading 1 — the baseline gains a trigger.** Doc 04 §3.1 lists the column's default as `now() (onupdate)`, and **doc 04 §9 reasons *from* the bump as a semantic worth protecting**: it is the entire justification for `memory_access_stats` being a side table — "any ORM-path update would additionally fire `onupdate=now()`, silently corrupting `updated_at`'s 'content changed' meaning." A semantic a design doc reasons from should not live only in ORM metadata.<br><br>**Reading 2 — it stays ORM-only.** Doc 19 §2 enumerates the triggers the baseline authors — the FTS trigger and the `events` forbid-trigger — **with no third**, and doc 04 §12's own enumeration of what the baseline creates names no `updated_at` trigger either. Adding one means the baseline lands an object no doc lists.<br><br>**Why they cannot both be true:** doc 19 §2 and doc 20 §7 state as binding that "no ORM-only construct is load-bearing anywhere in the schema" and that a DbUp replay must never "re-derive behaviour from ORM metadata" — and `onupdate` is precisely SQLAlchemy-specific behaviour a replay would have to re-derive. So either a documented, reasoned-from semantic is load-bearing and ORM-only (violating a binding rule), or the baseline authors a trigger three docs decline to list. | **ADJUDICATED 2026-07-27 by the maintainer: Reading 1 — the baseline authors a SQL trigger.** See §9.2's resolution block for the decision, the measurement that informed it, and the doc amendment it obliges. |

### Tier 2 and Tier 1

| # | Tier | Sources in conflict | What each says |
|---|---|---|---|
|---|---|---|---|
| F-02 | **2** | §2 vs `E0-baseline-and-harness.md` T0.12a–c | **Thirteen target tables are named by no T0.12a–c pass.** T0.12a names `memories`, `entities`, `entity_relations`, tags, `config`, `embedders`; T0.12b names `knowledge_triples`, `fact_sources`, articles and citations, `projects`, `repositories` and the `code_*` tables, job state, and `events`. Neither names `memory_crossrefs`, `memory_access_stats`, `memory_relations`, `memory_communities`, `memory_community_members`, `memory_buffer`, `project_repositories`, `conversations`, `messages`, `pipeline_failures`, `token_blocklist`, `api_keys`, or `llm_purpose_configs`. **Recommendation (for the controller and T0.12b's executor to ratify, not applied here):** the memory satellites (`memory_crossrefs`, `memory_access_stats`, `memory_relations`, `memory_communities`, `memory_community_members`) belong to T0.12a's "core memory" pass; the operations, chat, auth and LLM-config tables (`pipeline_failures`, `token_blocklist`, `conversations`, `messages`, `api_keys`, `llm_purpose_configs`) and the ingest/bridge tables (`memory_buffer`, `project_repositories`) belong to T0.12b. Assigning by guess would send work to the wrong pass, and T0.12a–c are floor-exempt and merge as one atomic unit, so the mistake would not surface until T0.12c. |
| F-08 | **2** | doc 19 §3 vs Appendix A.2 | Doc 19 §3 drops "`llm_providers`, `llm_profiles`, `ml_profiles` + every `*_ref`". **No column named `*_ref` exists on `llm_purpose_configs`.** A.2 shows the three indirection columns are `provider_id`, `profile_id` and `ml_profile_id` (uuid, each with an `ON DELETE SET NULL` FK). The **only** `*_ref`-named column in the whole schema is `repositories.auth_token_ref`, which doc 04 §6 lists among `repositories`' target columns and which must be **kept**. A T0.12a–c executor following doc 19 §3 literally would drop the one column to keep and keep the three to drop. §8 names the three by their real names; `auth_token_ref` stays. |
| F-09 | **2** | doc 04 §7 vs Appendix A.2 | Doc 04 §7 prints `config` as `(key varchar(255) PK, value jsonb NOT NULL DEFAULT '{}')`. A.2 shows `config.value` as `NOT NULL` with **no server default**. Same class as the `memories` default deltas (§5, §9): the inventory records what A.2 says and dispositions `config` as `reshaped` on the assumption that the baseline authors the printed default. If §9's ORM-default question resolves the other way, `config` is `carries-over` and this row is a doc-04 description error instead. |
| F-13 | **2** | doc 04 §6 vs doc 19 §3 vs `E0-baseline-and-harness.md` T0.13 | `repositories.index_debt` is described by doc 04 §6 as landing **inert** ("It lands as an inert column here"), but **doc 19 §3's disposition table carries no row for it** — and doc 19 §3 is the section T0.11 is chartered against for dispositions. T0.13's own object list ("`repo_ids[]` on `entities`/`entity_relations`, the empty `documents`/`blocks` tables, and all four per-fingerprint partition templates") does not name it either, so no task text lands it and no task text labels it inert. §5 dispositions it `target-new, inert` on doc 04 §6's authority and §7 names its first writer; the gap in doc 19 §3's table and in T0.13's list is for the controller to close. |
| F-14 | **2** | doc 04 §10, internally | The `(project, status)` pushdown support has **three stated forms** — bare `(project, status)`, `(project, status, is_archived)`, or partial `WHERE status='active' AND is_archived=false` — and doc 04 §10 does not pick. §3.2 records a recommendation (the partial) with its reasoning and marks the alternatives. T0.12c must write exactly one. If its executor judges this a design decision rather than an inventory one, it is adjudicated here, not chosen silently. |
| F-15 | **2** | doc 04 §8.1 vs doc 19 §9 stance 3 | **Whether the baseline creates `events`' first monthly child partition is unresolved by both docs.** Doc 04 §8.1 fixes monthly `RANGE(created_at)` from day one; doc 19 §9 stance 3 puts the *pre-create* arm on `pipeline_failure_cleanup`'s schedule. Neither says whether the baseline lands month-0. A `RANGE`-partitioned parent with no matching child **rejects every insert**, so a baseline that omits it produces a database whose first `events` write fails — and the first write happens as soon as T1.07's journaling ships. For T0.12b to decide, with the obvious safe answer being that the baseline creates the current month's child and the cleanup arm creates the next. |
| F-17 | **2** | Migration `0001` `downgrade()` vs doc 04 §5.3 | `0001`'s `downgrade()` drops runtime child tables by walking `pg_tables` for **four** `LIKE` patterns. The target has **eight** parents, so the same sweep would strand `block_embeddings__*`, `relation_embeddings__*`, `article_embeddings__*` and `triple_embeddings__*`. Moot for the six revisions the baseline deletes; **not** moot for the baseline's own `downgrade()`, which T0.12c writes. Recorded against T0.12c. |
| F-01 | **1** | Appendix A.1 vs doc 04 | `alembic_version` exists in every migrated database; doc 04 never names it. It is Alembic's own bookkeeping table, so the honest disposition is `carries-over`, `Lands in: n/a (Alembic)`, traced to doc 19 §2 rather than to doc 04. Recorded so a reviewer does not read its absence as an oversight. |
| F-03 | **1** | `E0-baseline-and-harness.md` T0.12a vs doc 04 §3.2 | T0.12a's text says "tags" where doc 04 §3.2 fixes the pair `tags` + `memory_tags`. The roll-call reads "tags" as the pair, since the join table is undeclarable without both. Recorded because the reading is an inference, not a quotation. |
| F-04 | **1** | `erd.md` vs doc 04 §7/§9 | `erd.md` diagrams no `api_keys` table anywhere, while doc 04 §7 names it among the operations tables and §9 describes its activation, and doc 19 §3 carries an `(activation)` row for it. Doc 04 wins per the authority order: `api_keys` is in the target. `erd.md` reveals the gap; it never decides it. |
| F-05 | **1** | `erd.md` §4 vs doc 04 §5.2 | `erd.md` §4's diagram shows two of the four existing partition parents (`memory_embeddings__slug`, `entity_embeddings__slug`); `code_chunk_embeddings` and `entity_embedding_cache` appear only in its prose notes. This is diagram resolution rather than a table-set disagreement — `erd.md`'s own header says "key columns only" — but it is recorded so §6's eight rows are not read against the diagram's six. |
| F-06 | **1** | Appendix A.8 vs `CLAUDE.md` job registry | The migrations seed **four** `job:<key>` `config` rows against **seven** registered jobs. `graph_orphan_cleanup`, `tag_orphan_cleanup` and `expired_memory_cleanup` have no seeded state row and create theirs at runtime. Whether the baseline should seed all seven (uniform, greppable) or none (state is runtime data) is a decision for T0.12b's job-state work; today's split is neither. |
| F-07 | **1** | `E0-baseline-and-harness.md` T0.12b vs doc 04 §7 | T0.12b's scope names "job state", which is not a table: job state lives in `config` rows keyed `job:<key>` (doc 04 §7), and `config` is T0.12a's. So T0.12b's "job state" is seed data in a table an earlier pass creates, not an object of its own. |
| F-10 | **1** | doc 04 §7 vs Appendix A.2 | Doc 04 §7 fixes the flattened `llm_purpose_configs` row as carrying `{model, base_url, api_key, api_kind, params jsonb, dimensions?, reasoning?}` plus `classifier_kind`. A.2 shows a **`provider varchar NOT NULL DEFAULT 'ollama'`** column at HEAD that this list does not mention. Doc 04 §7 also fixes `api_kind` as the sole vendor-quirk home (E1's T1.03 repeats it), which suggests `provider` is redundant and drops — but no doc says so. Whether `provider` is kept or dropped is a decision for T0.12b and E1's T1.01 (flatten `llm_purpose_configs`), not for this inventory. |
| F-11 | **1** | This task's own step-level plan, internally | Task 4 Step 1 says rows belonging to a §8-dropped table are "**removed**, not dispositioned"; Task 4 Step 4 then asserts "the count of `carries-over` index rows **plus dropped-with-table index rows** equals 63", which only holds if they are present. §3 and §4 keep every row and disposition it `dropped`, because that makes the set difference against A.3/A.4 total — no "except" clause a reviewer must take on trust. Recorded so the deviation from the plan text is visible rather than silent. |
| F-12 | **1** | Appendix A.3 vs doc 04 §7 | `token_blocklist` carries **two** indexes on `jti`: `token_blocklist_jti_key` (UNIQUE, from the constraint) and `ix_token_blocklist_jti` (a plain btree). The plain btree is fully redundant under the unique. Doc 04 §7 specifies only `jti UNIQUE`. **Recommendation:** the baseline lands the UNIQUE alone. Harmless either way, which is why it is recorded rather than escalated — but a baseline that reproduces it reproduces an accident of migration history, which is the thing T0.11 exists to prevent. |
| F-16 | **1** | `E0-baseline-and-harness.md` T0.12c vs T0.13 | T0.12c says the four target-new templates "land here as **registry entries** … (their inert labelling is T0.13's)"; T0.13's own **What** says it lands "all four per-fingerprint partition templates (block, relation, article, `triple_embeddings`)". Both cannot be the landing task. §6 follows T0.12c, whose statement is the more specific of the two (it names the mechanism, `_TABLE_TEMPLATES`/`_AUX_INDEXES`, and explicitly hands labelling to T0.13). T0.13's wording should be narrowed to labelling and the no-writer assertion. |
| F-18 | **1** | doc 04 §6 vs Appendix A.2 | `repositories.{provider, default_branch, status, auto_sync}` are `NOT NULL` with **no server default**; doc 04 §6 prints `provider 'local'` and `default_branch 'main'` without saying which side owns them, and says nothing about `status` or `auto_sync`. Same class as F-09 and §9.3. §9.3's action treats the two doc-04-printed ones as DDL defaults and records the reading; `status` and `auto_sync` have no doc-04 default to honour and stay as they are unless T0.12b decides otherwise. |
| F-19 | **1** | `models/*.py` vs Appendix A.2 | `code_graph_nodes.id` and `code_edges.id` carry `default=uuid.uuid4` in the ORM while the DDL gives them `bigserial` sequences (`nextval(...)`), which the database applies and the ORM value never reaches. Dead metadata, cosmetic only — recorded so the audit's "every sweep hit is a row" claim is literally true and a reviewer does not read the omission as an oversight. The baseline should not mirror it. |
| F-21 | **2** | `E0-baseline-and-harness.md` T0.12c vs `backend/app/` | **T0.12c's floor assertion cannot be met by DDL alone, and no T0.12a–c task authorises the code change it needs.** T0.12c requires "the **full backend suite passes** against a database built from the baseline alone", but the baseline renames four `memories` columns (`llm_classified_type → classified_type`, `llm_summary → summary`, `llm_emotions → emotions`, `llm_flags → flags`, §5) and drops the `llm_purpose_configs` indirection columns (§8). Measured blast radius at the T0.12a commit: **24 occurrences across five app files** (`models/memory.py`, `schemas/memory.py`, `api/routes/memories.py`, `services/pipeline.py`, `utils/serialization.py`) plus **7 in `tests/`** for the renames, and five more app files for `provider_id`/`profile_id`/`ml_profile_id`. Until those are updated the suite cannot pass, so T0.12c is not "write the remaining indexes and prove the suite carries" — it necessarily includes bringing the ORM mirror and every call site onto the target column names. **Recommendation:** state that scope in T0.12c explicitly and re-size it from `M` to `L`, which under runbook §3 means it needs a reviewed step-level plan before execution. The alternative — deferring the renames into E1 — is worse: it would put the baseline out of step with doc 04 §3.1 on day one, which is the exact failure T0.11 exists to prevent. |

### Amendments proposed to the task corpus

Recorded as proposals with a recommended disposition. **No step of T0.11 edits an epic
file or `progress.md`** — `docs/planning/` is canonical on `master` and the controller
owns propagation (runbook §5).

| # | Amendment | Tier | Recommended disposition |
|---|---|---|---|
| A-01 | **T0.11's four dispositions cannot express a dropped object.** The acceptance criterion names `carries-over` / `reshaped` / `target-new` / `target-new, inert`, and doc 19 §3's own table uses a wider set: `(target-new, inert)`, `(target-new, template only)`, `(activation)`, `(dropped)`, `(rebuild)`. Three fold cleanly — `(rebuild)` is `target-new` with a note (doc 04 §8.3 fixes `knowledge_triples` as "target-new, NOT an activation"), `(activation)` is `carries-over` with an activation note and a first-reader task id (`api_keys`, `memories.importance`), and `(template only)` is `target-new, inert` with a note (`triple_embeddings`). **`(dropped)` does not fold**, and T0.11's `Doc:` field names 19 **§3** — the section that is entirely about dropped and dormant objects. | **Tier 2** — changes T0.11's acceptance criteria. | Adopt as executed here: the four dispositions govern §2–§6 (objects the baseline lands) and §8 carries dropped objects under its own two-value vocabulary, `dropped` / `dropped, optional transform`. The controller adds the amendment to `E0-baseline-and-harness.md`'s amendment log and, if T0.11's checkbox text is restated, to `progress.md`. |

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

## Appendix B — reproducible checks

**Every factual claim in §2–§9 that a machine can check is checked here**, grouped by what
it proves. A reviewer re-runs these rather than trusting the tables. Prerequisites: the
dev-compose Postgres on `127.0.0.1:5433` (`docker exec darkmem-postgres-1 …`), and
`backend/.venv/bin/python` — `python` is not on PATH.

**These are the mechanical half only.** The other half — that every row traces to the
*right* doc section, and that every §7 first-writer id is the *right* id — rests on the
reviewer's reading. "No unexplained entries" (T0.11's Verify) needs both: no script can
tell you a citation points at the wrong section, only that it points somewhere.

### Group 1 — the manifest is ground truth (proves Appendix A)

**Check 1 — rebuild and re-extract.** Re-run Appendix A's "How this was produced" block in
full. The eight assertion-block counts must reproduce exactly: 26 tables, 63 indexes,
26/19/11/3 constraints, 1 trigger, 1 function, 1 enum, **0** child tables, 4 seeded
`config` rows. Re-run on 2026-07-27 produced output byte-identical to the pasted listings
across all eight queries.

**Check 2 — no residue.** After the drop,
`docker exec darkmem-postgres-1 psql -U darkmem -d postgres -tAc "SELECT datname FROM pg_database ORDER BY 1;"`
lists exactly `darkmem`, `darkmem_bench`, `darkmem_test`, `postgres`, `template0`,
`template1`.

### Group 2 — nothing is unaccounted (proves §2, §3, §4, §8)

**Check 3 — every table is dispositioned.** Set difference of Appendix A.1's table list
against the union of §2's and §8's first columns. Expected: **empty in both directions**.
Measured: A.1 = 26; §2 = 34 rows (21 shared with A.1 + 13 target-new); §8 = the remaining
5. `21 + 5 = 26`.

**Check 4 — every index, constraint, trigger, function and enum is dispositioned.** Five
set differences of A.3–A.7 against §3 and §4. Expected: **five empty differences**.
Measured: 63 index names all present in §3 (49 `carries-over` + 14 `dropped` = 63); 59
constraint names all present in §4 (43 + 16 = 59); the one trigger, one function and one
enum present in §4.2. Every §3/§4 row carries a non-empty `Lands in`.

```python
# the shape of checks 3 and 4, run against this file
import re, pathlib
t = pathlib.Path("docs/planning/baseline-schema-inventory.md").read_text()
a1 = {l.split("|")[0] for l in t.split("### A.1 —")[1].split("### A.2 —")[0].split("```")[1].strip().splitlines()}
s2 = set(re.findall(r"^\| `([a-z_]+)` \| ", t.split("## 2. Tables")[1].split("### 2.1")[0], re.M))
s8 = set(re.findall(r"^\| `([a-z_]+)` \(table\)", t.split("## 8. Not landed")[1].split("## 9.")[0], re.M))
assert not (a1 - s2 - s8) and not (s8 - a1)
```

**Check 5 — the partition templates are not migration DDL** (proves §6):

```bash
cd /root/repositories/darkmem
rg -n '__[a-z0-9_]+.*(CREATE TABLE|create_table)' backend/migrations/      # expect: no matches
rg -in 'create (table|index)[^\n]*(embeddings__|entity_embedding_cache__)' backend/migrations/   # expect: no matches
```

Both come back empty. **A caveat on the second check**, because a naive form of it
misleads: `rg -c 'embeddings__|entity_embedding_cache__' backend/migrations/` reports
**nine** hits in `0001_initial_schema.py`. All nine are non-creating — a module docstring,
an explanatory comment, and the `downgrade()` sweep that walks `pg_tables` for four `LIKE`
patterns to drop whatever the registry created (which is F-17). The claim §6 makes is that
no migration **creates** a child table, and the `CREATE`-shaped check above is the one that
proves it. Paired with Appendix A's zero-child-tables assertion, the evidence is empirical
rather than asserted.

### Group 3 — every cited task id exists and is the right one (proves §7)

**Check 6 — the linter.** `check_plan.py` globs `*.md` in `docs/planning/` and asserts that
every `T(?:H1|[0-4])\.\d{2}[a-z]?`-shaped reference resolves to a defined task, so this
file is linted the moment it lands in that directory:

```bash
cd /root/repositories/darkmem/docs/planning
/root/repositories/darkmem/backend/.venv/bin/python scripts/check_plan.py
```

Expected and measured: `PLAN GREEN — 205 tasks, all structural claims verified`. It earned
its keep during this task: a first draft referred to the baseline pass family without its
`a`/`b`/`c` suffix, and the linter failed with `reference to undefined task` in ten
seconds. Cite `T0.12a`, `T0.12b`, `T0.12c` or the range `T0.12a–c` — never the stem.

**`check_plan.py` proves an id *exists*; only §7's quoted-words column proves it is the
*right* id.** Both are required, and the second is the reviewer's job. Six of the ten §7
rows are additionally confirmed by a **reciprocal promise** — T2.27, T2.33, T2.49, T3.23,
TH1.02 and TH1.05 each name T0.13 as the task that landed the object inert, and T2.49 and
T3.23 carry an acceptance checkbox that this inventory records them as the writer.

**Check 7 — every inert object has a §7 row.** Set difference of the `target-new, inert`
rows in §2/§3/§5/§6 against §7's objects. Expected: empty. Measured: 14 inert objects, all
covered — the three that match by table rather than by name (§3.2's `document identity`,
`block order` and `block tree` index labels) are covered by §7's `documents` and `blocks`
rows, which explicitly carry their indexes.

### Group 4 — the SQL-first audit is complete (proves §9)

**Check 8 — the sweeps, and the one bulk kind.**

```bash
cd /root/repositories/darkmem/backend
rg -n 'onupdate=|default=|server_default|server_onupdate|__table_args__|CheckConstraint|UniqueConstraint|Index\(|ForeignKey\(|create_type=False|event\.listen|@validates|@hybrid_property' app/models/*.py
rg -n 'DDL\(|event\.listen|Computed\(|Identity\(' app/
```

Every construct kind the sweeps return appears in §9: `server_default` (21 declarations),
`UniqueConstraint` (5), `__table_args__` (5), `onupdate=` (3), `CheckConstraint` (1),
`Index(` (1), `create_type=False` (1), `event.listen` (1). Six kinds return **zero** hits —
`server_onupdate`, `@validates`, `@hybrid_property`, `DDL(`, `Computed(`, `Identity(` —
which is itself a compliance result.

The one bulk kind is dispatched mechanically: cross-referencing every `server_default=`
declaration against A.2's `column_default` shows **21 of 21 mirrored by a real server
default, zero ORM-only**. The same cross-reference run against client-side `default=`
declarations is what produced §9.3's twelve-column table, and it is why the plan's "five
NOT NULL columns on `memories`" undercounted.

### Group 5 — the work stayed in bounds

**Check 9 — only two files changed.**

```bash
cd /root/repositories/darkmem
git diff --name-only master...HEAD -- docs/planning/baseline-schema-inventory.md docs/superpowers/plans/2026-07-27-baseline-schema-inventory.md
git diff --name-only master...HEAD | grep -E '^(backend|frontend)/' || echo "no code touched"
```

The second command must print `no code touched`. T0.11 produces an inventory; T0.12a–c
write the DDL.

**Check 10 — T0.15's grep hits.** `rg -n "freeze" docs/planning/baseline-schema-inventory.md`
must return the §0 freeze note. T0.15's Verify greps this file by name, so the note is a
contract with a downstream task, not decoration.

**Check 11 — no pending markers.** `rg -n 'pending:\s+Task' docs/planning/baseline-schema-inventory.md`
returns nothing. Each section carried such a marker until the pass that filled it, so a
half-built inventory was never mistakable for a finished one. (The regex is written with
`\s+` rather than a literal space so this line does not match itself.)

**Check 12 — the repo floor is untouched.** `cd backend && python -m pytest -q` reads the
same as before this work began. This is a no-op assertion by construction — no code
changed — and its value is precisely that: a different number means something outside this
work moved, which is a finding to report, not a result to absorb.
