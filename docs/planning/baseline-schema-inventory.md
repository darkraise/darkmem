# Baseline schema inventory

_(pending: Task 8 — §0 front matter)_

## 1. How to read this inventory

_(pending: Task 8)_

## 2. Tables — the target roll-call

**One row per table in the target.** `Owning doc §` is the *most specific* section of
doc 04 that fixes the table's shape. `Lands in` is the T0.12 pass (or other task) whose
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

_(pending: Task 4)_

## 4. Constraints, triggers, and types

_(pending: Task 4)_

## 5. Column-level changes on carried-over tables

_(pending: Task 4)_

## 6. Per-fingerprint partition templates (registry entries, not DDL)

_(pending: Task 5)_

## 7. Inert objects and their first writers

_(pending: Task 6)_

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

_(pending: Task 7)_

## 10. Findings — where the sources disagree

_(pending: Task 8 — consolidation and tiering)_

Findings accumulate here as each pass locates them. Task 8 assigns every row a runbook §5
tier and lifts the Tier-3 rows to the top under their own heading.

| # | Sources in conflict | What each says |
|---|---|---|
| F-01 | Appendix A.1 vs doc 04 | `alembic_version` exists in every migrated database; doc 04 never names it. It is Alembic's own bookkeeping table, so the honest disposition is `carries-over`, `Lands in: n/a (Alembic)`, traced to doc 19 §2 rather than to doc 04. Recorded so a reviewer does not read its absence as an oversight. |
| F-02 | §2 vs `E0-baseline-and-harness.md` T0.12a–c | **Thirteen target tables are named by no T0.12 pass.** T0.12a names `memories`, `entities`, `entity_relations`, tags, `config`, `embedders`; T0.12b names `knowledge_triples`, `fact_sources`, articles and citations, `projects`, `repositories` and the `code_*` tables, job state, and `events`. Neither names `memory_crossrefs`, `memory_access_stats`, `memory_relations`, `memory_communities`, `memory_community_members`, `memory_buffer`, `project_repositories`, `conversations`, `messages`, `pipeline_failures`, `token_blocklist`, `api_keys`, or `llm_purpose_configs`. **Recommendation (for the controller and T0.12b's executor to ratify, not applied here):** the memory satellites (`memory_crossrefs`, `memory_access_stats`, `memory_relations`, `memory_communities`, `memory_community_members`) belong to T0.12a's "core memory" pass; the operations, chat, auth and LLM-config tables (`pipeline_failures`, `token_blocklist`, `conversations`, `messages`, `api_keys`, `llm_purpose_configs`) and the ingest/bridge tables (`memory_buffer`, `project_repositories`) belong to T0.12b. Assigning by guess would send work to the wrong pass, and T0.12a–c are floor-exempt and merge as one atomic unit, so the mistake would not surface until T0.12c. |
| F-03 | `E0-baseline-and-harness.md` T0.12a vs doc 04 §3.2 | T0.12a's text says "tags" where doc 04 §3.2 fixes the pair `tags` + `memory_tags`. The roll-call reads "tags" as the pair, since the join table is undeclarable without both. Recorded because the reading is an inference, not a quotation. |
| F-04 | `erd.md` vs doc 04 §7/§9 | `erd.md` diagrams no `api_keys` table anywhere, while doc 04 §7 names it among the operations tables and §9 describes its activation, and doc 19 §3 carries an `(activation)` row for it. Doc 04 wins per the authority order: `api_keys` is in the target. `erd.md` reveals the gap; it never decides it. |
| F-05 | `erd.md` §4 vs doc 04 §5.2 | `erd.md` §4's diagram shows two of the four existing partition parents (`memory_embeddings__slug`, `entity_embeddings__slug`); `code_chunk_embeddings` and `entity_embedding_cache` appear only in its prose notes. This is diagram resolution rather than a table-set disagreement — `erd.md`'s own header says "key columns only" — but it is recorded so §6's eight rows are not read against the diagram's six. |
| F-06 | Appendix A.8 vs `CLAUDE.md` job registry | The migrations seed **four** `job:<key>` `config` rows against **seven** registered jobs. `graph_orphan_cleanup`, `tag_orphan_cleanup` and `expired_memory_cleanup` have no seeded state row and create theirs at runtime. Whether the baseline should seed all seven (uniform, greppable) or none (state is runtime data) is a decision for T0.12b's job-state work; today's split is neither. |
| F-07 | `E0-baseline-and-harness.md` T0.12b vs doc 04 §7 | T0.12b's scope names "job state", which is not a table: job state lives in `config` rows keyed `job:<key>` (doc 04 §7), and `config` is T0.12a's. So T0.12b's "job state" is seed data in a table an earlier pass creates, not an object of its own. |
| F-08 | doc 19 §3 vs Appendix A.2 | Doc 19 §3 drops "`llm_providers`, `llm_profiles`, `ml_profiles` + every `*_ref`". **No column named `*_ref` exists on `llm_purpose_configs`.** A.2 shows the three indirection columns are `provider_id`, `profile_id` and `ml_profile_id` (uuid, each with an `ON DELETE SET NULL` FK). The **only** `*_ref`-named column in the whole schema is `repositories.auth_token_ref`, which doc 04 §6 lists among `repositories`' target columns and which must be **kept**. A T0.12 executor following doc 19 §3 literally would drop the one column to keep and keep the three to drop. §8 names the three by their real names; `auth_token_ref` stays. |
| F-09 | doc 04 §7 vs Appendix A.2 | Doc 04 §7 prints `config` as `(key varchar(255) PK, value jsonb NOT NULL DEFAULT '{}')`. A.2 shows `config.value` as `NOT NULL` with **no server default**. Same class as the `memories` default deltas (§5, §9): the inventory records what A.2 says and dispositions `config` as `reshaped` on the assumption that the baseline authors the printed default. If §9's ORM-default question resolves the other way, `config` is `carries-over` and this row is a doc-04 description error instead. |
| F-10 | doc 04 §7 vs Appendix A.2 | Doc 04 §7 fixes the flattened `llm_purpose_configs` row as carrying `{model, base_url, api_key, api_kind, params jsonb, dimensions?, reasoning?}` plus `classifier_kind`. A.2 shows a **`provider varchar NOT NULL DEFAULT 'ollama'`** column at HEAD that this list does not mention. Doc 04 §7 also fixes `api_kind` as the sole vendor-quirk home (E1's T1.03 repeats it), which suggests `provider` is redundant and drops — but no doc says so. Whether `provider` is kept or dropped is a decision for T0.12b and E1's T1.01 (flatten `llm_purpose_configs`), not for this inventory. |

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

_(pending: Task 8)_
