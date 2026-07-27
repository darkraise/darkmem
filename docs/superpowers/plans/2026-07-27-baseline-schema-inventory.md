# T0.11 — Baseline Schema Inventory: Step-Level Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Produce `docs/planning/baseline-schema-inventory.md` — the explicit object inventory the single baseline migration (T0.12a–c) must land, reconciled from doc 04's target data model against the six existing Alembic revisions, with every table, index, constraint, trigger, type, column change and partition template dispositioned, traced to an owning doc section, and — where inert — named with the phase and task that will first write to it.

**Why this is a plan and not a direct execution.** T0.11 carries `Size: L`, and runbook §3 forbids executing an `L` task straight from its acceptance criteria. The task's own framing — "this is the task that prevents the baseline from being an accident of migration history" — is the tell: its output is the work order that T0.12a, T0.12b and T0.12c execute against, so an inventory that is merely plausible produces a baseline that is merely plausible.

**Architecture of the work.** The inventory is a **reconciliation of four sources that can and do disagree**, not a transcription of one:

| # | Source | What it is | Authority |
|---|---|---|---|
| A | The live schema built by `alembic upgrade head` on an empty database | What the six revisions **actually** land, after `0003`'s data-only reset and `0006`'s column drops | Ground truth for *current state*. Cannot be misread. |
| B | `docs/design/04-data-model-and-schema.md` | The target data model | **Authoritative for target table shapes** (doc 19 §1: "where they would conflict, doc 04's table shapes win") |
| C | `docs/design/19-migration-deployment-and-ops.md` §2–§3 | Single-baseline discipline, boot-time reconciliation, SQL-first rule, dormant-object disposition table | **Authoritative for operational sequencing and disposition** (doc 19 §1, same sentence) |
| D | `backend/app/models/*.py` and `backend/app/services/embedder_registry.py` | The ORM mirror and the partition templates | **No authority.** Doc 19 §2: "SQLAlchemy models mirror the SQL, not the reverse." A construct that lives only here is a *finding*, not a row. |

Plus two corroborating, non-authoritative references: `docs/design/erd.md` (its own header says "Key columns only — full column/constraint/index detail lives in doc 04") and `docs/design/20-roadmap-and-sequencing.md` §6–§7 (the honesty-tag timeline that says *when* an inert object's tag may flip, and the standing SQL-first constraint).

**The sequencing principle.** Source A is extracted **mechanically and first**, because it is the only one of the four that cannot be misread, and because every later step diffs against it. Reading the six revision files by eye is the failure mode this plan exists to avoid: `0001` calls `op.create_table` nineteen times but the migrated database holds twenty-six tables (five more come from raw `CREATE TABLE` in `op.execute`, plus `alembic_version`); it calls `op.create_index` twenty-three times but the database holds sixty-three indexes (the rest are implied by PK and UNIQUE constraints). Then the target roll-call fixes the **row set**; every later task fills **columns** on rows that already exist, so no step re-derives what an earlier step decided.

**Tech stack:** Markdown only, plus `docker exec … psql` for the source-A extraction, `rg` for the sweeps, and `docs/planning/scripts/check_plan.py` (already green at 205 tasks) which lints every task id in `docs/planning/*.md` — so the inventory's future-writer citations are machine-checked the moment the file lands in that directory. No new code, no new dependency, no test.

---

## Global Constraints

- **Out of bounds for every task in this plan.** No step may modify `backend/migrations/`, `backend/app/`, or anything under `frontend/`. T0.11 produces an inventory; T0.12a–c write the actual baseline and are separate tasks on their own lane branch. A step that finds itself wanting to *fix* the schema has misread its assignment — the fix belongs in the Findings section (§10) as a row addressed to T0.12a–c.
- **No step touches `docs/planning/progress.md` or any file under `docs/planning/tasks/`.** `docs/planning/` is canonical on `master` and the controller owns propagation. Amendments this work discovers are **written into the inventory's Findings section and surfaced in the completion report**; the controller applies them to the E0 amendment log and `progress.md`. This is the only reason a Tier-2 amendment here does not edit the epic file itself (runbook §5) — the propagation, not the amendment, is delegated.
- **Exactly two files change across the whole plan:** `docs/planning/baseline-schema-inventory.md` (created, then built up in passes) and this plan file (checkbox ticks). Every task's verification asserts that, and it is what keeps the repo floor untouched by construction.
- **The repo floor is green on this branch as of 2026-07-27:** `cd backend && python -m pytest -q` → `614 passed, 1 skipped` in 33s. Nothing in this plan changes code, so the floor must still read exactly that at Task 8. If it does not, that is a finding about something else, not about this work — record it, do not absorb it.
- **`python` is not on PATH.** Use `/root/repositories/darkmem/backend/.venv/bin/python`, and run backend commands from `backend/`.
- **`psql` is not on the host.** Reach Postgres through `docker exec darkmem-postgres-1 psql -U darkmem -d <db> -c "…"`. Databases: `darkmem` is **write-forbidden** and has no schema on this machine; `darkmem_test` belongs to pytest alone; `darkmem_bench` belongs to benchlib. This plan uses a **dedicated throwaway `darkmem_inv_probe`**, created and dropped inside Task 1 so it leaves no residue and collides with no other lane.
- **Kill every process you start.** The only long-lived thing this plan creates is the probe database, and Task 1 drops it in its own final step.
- **Doc quotes are load-bearing.** Where the inventory states what a doc says, it cites the section and — for anything contested — quotes it. "No unexplained entries" (the task's Verify) means a Fable reviewer can check every row against its cited section without re-reading the whole corpus.

## The document skeleton — fixed here, filled by the tasks

Task 2 creates the file with all headings present and every unfilled section carrying a literal `_(pending: Task N)_` marker, so a half-built inventory is never mistakable for a finished one. Each task below owns exactly one or two sections.

```
docs/planning/baseline-schema-inventory.md

 §0  Front matter — status, purpose, authority order, the freeze note   [Task 8]
 §1  How to read this inventory — the disposition legend                [Task 2 stub, Task 8 final]
 §2  Tables — the target roll-call                                      [Task 2 rows, Task 3 dispositions]
 §3  Indexes                                                            [Task 4]
 §4  Constraints, triggers, and types                                   [Task 4]
 §5  Column-level changes on carried-over tables                        [Task 4]
 §6  Per-fingerprint partition templates (registry entries, not DDL)    [Task 5]
 §7  Inert objects and their first writers                              [Task 6]
 §8  Not landed — dropped objects, and why                              [Task 3]
 §9  SQL-first audit                                                    [Task 7]
 §10 Findings — where the sources disagree                              [Task 8 consolidates]
 App A  As-is object manifest, machine-extracted from the six revisions [Task 1]
 App B  Reproducible checks — every command in this document            [Task 8]
```

## The disposition vocabulary — and the one amendment it needs

T0.11's acceptance names four dispositions: `carries-over` / `reshaped` / `target-new` / `target-new, inert`. Doc 19 §3's own disposition table uses a wider set: `(target-new, inert)`, `(target-new, template only)`, `(activation)`, `(dropped)`, `(rebuild)`.

Three of those five fold cleanly into the four:

- **`(rebuild)`** — `knowledge_triples` lands with an entirely new shape, so it is `target-new` with a note. Doc 04 §8.3 is explicit that it is "treated as target-new, NOT as an activation".
- **`(activation)`** — `api_keys` and `memories.importance` already exist and the baseline lands them unchanged; the activation is a *read-path* change in a later phase. They are `carries-over` with a note and a first-reader task id.
- **`(template only)`** — `triple_embeddings` is `target-new, inert` with a note that the template ships and the writer is deferred.

**`(dropped)` does not fold.** `audit_log`, `enrichment_queue`, `llm_providers`, `llm_profiles`, `ml_profiles` and every `*_ref` column exist at HEAD and are deliberately **not** in the target. None of the four dispositions can express "present today, deliberately absent tomorrow" — yet recording exactly that is the point of a task whose stated purpose is to prevent the baseline from being an accident of migration history. Without it, a reader cannot distinguish a deliberate omission from an oversight, which is the specific failure T0.11 exists to prevent, and T0.11's `Doc:` field names 19 **§3** — the section that is entirely about dropped and dormant objects.

**Resolution this plan adopts:** the four dispositions govern §2–§6 (objects the baseline *lands*), and dropped objects get their own section §8 with its own two-value vocabulary (`dropped` / `dropped, optional transform`). This is a **Tier-2 amendment** to T0.11 under runbook §5 (changed acceptance criteria). Per the Global Constraints, Task 3 writes the amendment text into §10 and the completion report surfaces it; the controller applies it to E0's amendment log.

---

### Task 1: Appendix A — the machine-extracted as-is manifest

**Files:**
- Create: `docs/planning/baseline-schema-inventory.md` (Appendix A only; §0–§10 arrive in Task 2)

**Produces:** a literal, sorted listing of every object the six revisions land — tables, columns with nullability and server defaults, indexes with definitions, constraints with definitions, triggers with definitions, non-extension functions, enum types, and migration-seeded rows — plus the exact commands that produced it.

**Consumes:** nothing but the six revision files, executed rather than read.

**Why first:** it is the only one of the four sources that cannot be misread, and Tasks 3, 4, 6 and 7 all diff against it. It also settles, before any judgement call, three facts that reading the Python would get wrong: how many objects actually exist, that the per-fingerprint child tables are *absent* from a freshly migrated database, and which columns have a real server default versus an ORM-only one.

- [x] **Step 1: Build a throwaway database from the six revisions**

```bash
docker exec darkmem-postgres-1 psql -U darkmem -d postgres \
  -c "DROP DATABASE IF EXISTS darkmem_inv_probe;" \
  -c "CREATE DATABASE darkmem_inv_probe;"
cd /root/repositories/darkmem/backend
DATABASE_URL=postgresql+asyncpg://darkmem:darkmem@localhost:5433/darkmem_inv_probe \
  timeout 300 ./.venv/bin/python -m alembic upgrade head
```

Expected: five `Running upgrade` lines ending `0005 -> 0006, drop regex classification columns`. `darkmem_inv_probe` is dedicated to this task and dropped in Step 4 — never point this at `darkmem`, `darkmem_test`, or `darkmem_bench`.

- [x] **Step 2: Extract the manifest**

Run each query with the pipe-separated tuples-only form, and paste the output verbatim into Appendix A under a subheading per query. Define once: `D="docker exec darkmem-postgres-1 psql -U darkmem -d darkmem_inv_probe -tAF|"`.

```sql
-- A.1 tables (relkind r = ordinary, p = partitioned)
SELECT c.relname, c.relkind FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE n.nspname = 'public' AND c.relkind IN ('r','p') ORDER BY 1;

-- A.2 columns, with nullability and the SERVER default (empty = no server default)
SELECT table_name, ordinal_position, column_name, data_type, is_nullable, column_default
FROM information_schema.columns WHERE table_schema = 'public'
ORDER BY table_name, ordinal_position;

-- A.3 indexes, with full definitions
SELECT tablename, indexname, indexdef FROM pg_indexes WHERE schemaname = 'public' ORDER BY 1, 2;

-- A.4 constraints, with full definitions  (c.oid is required — a bare `oid` is ambiguous here)
SELECT c.conrelid::regclass::text, c.conname, c.contype, pg_get_constraintdef(c.oid)
FROM pg_constraint c JOIN pg_namespace n ON n.oid = c.connamespace
WHERE n.nspname = 'public' ORDER BY 1, 2;

-- A.5 triggers (user-defined only)
SELECT c.relname, t.tgname, pg_get_triggerdef(t.oid) FROM pg_trigger t
JOIN pg_class c ON c.oid = t.tgrelid WHERE NOT t.tgisinternal ORDER BY 1, 2;

-- A.6 functions, excluding everything pgvector installed
SELECT p.proname FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
WHERE n.nspname = 'public'
  AND NOT EXISTS (SELECT 1 FROM pg_depend d WHERE d.objid = p.oid AND d.deptype = 'e')
ORDER BY 1;

-- A.7 enum types and their labels
SELECT t.typname, string_agg(e.enumlabel, ',' ORDER BY e.enumsortorder)
FROM pg_type t JOIN pg_enum e ON e.enumtypid = t.oid GROUP BY 1 ORDER BY 1;

-- A.8 rows the migration seeds (seed data is an inventory concern, not just DDL)
SELECT 'config:' || key FROM config
UNION ALL SELECT 'llm_purpose_configs=' || count(*)::text FROM llm_purpose_configs
UNION ALL SELECT 'llm_providers='       || count(*)::text FROM llm_providers
UNION ALL SELECT 'embedders='           || count(*)::text FROM embedders
UNION ALL SELECT 'tags='                || count(*)::text FROM tags
ORDER BY 1;
```

- [x] **Step 3: Record the headline counts as an assertion block**

Write these into Appendix A as a short table headed "Assertions — re-run Step 1 + Step 2 and these must reproduce exactly". They are the manifest's checksum, and Tasks 3 and 4 read them.

| Object class | Count |
|---|---|
| Tables (`relkind` r or p, incl. `alembic_version`) | 26 |
| Indexes (`pg_indexes`) | 63 |
| Constraints: PRIMARY KEY / FOREIGN KEY / UNIQUE / CHECK | 26 / 19 / 11 / 3 |
| User triggers | 1 (`memories_fts_update`) |
| Non-extension functions | 1 (`memories_fts_trigger`) |
| Enum types | 1 (`memory_status` = active,deprecated,superseded) |
| Per-fingerprint `*__<slug>` child tables | **0** |
| Migration-seeded `config` rows | 4 (`job:code_enrichment`, `job:pipeline_failure_cleanup`, `job:repo_sync`, `job:token_blocklist_cleanup`) |

Two of these carry information that later tasks need and no reading of the migration files would surface. **Zero child tables** is the empirical proof of doc 19 §2's claim that the partition DDL is runtime, not migration — Task 5 cites it. **Four seeded `config` rows against seven registered jobs** (`CLAUDE.md`: `repo_sync`, `code_enrichment`, `token_blocklist_cleanup`, `pipeline_failure_cleanup`, `graph_orphan_cleanup`, `tag_orphan_cleanup`, `expired_memory_cleanup`) means three job-state rows are created at runtime, not seeded — a seed-data row for §2 and a finding for §10.

- [x] **Step 4: Drop the probe database**

```bash
docker exec darkmem-postgres-1 psql -U darkmem -d postgres -c "DROP DATABASE IF EXISTS darkmem_inv_probe;"
```
Expected: `DROP DATABASE`. Then confirm no residue: `docker exec darkmem-postgres-1 psql -U darkmem -d postgres -tAc "SELECT datname FROM pg_database ORDER BY 1;"` lists exactly `darkmem`, `darkmem_bench`, `darkmem_test`, `postgres`, `template0`, `template1`.

- [x] **Step 5: Verify and commit**

Verification is reproduction: re-run Steps 1, 2 and 4 from a clean shell and confirm the assertion block still holds and the pasted output is unchanged. Then:

```bash
cd /root/repositories/darkmem
git status --porcelain            # must show only docs/planning/baseline-schema-inventory.md
git add docs/planning/baseline-schema-inventory.md
git commit -m "docs(planning): extract the as-is schema manifest

Machine-extracted from a database built by alembic upgrade head on an
empty scratch database, so the current-state side of the T0.11
reconciliation is ground truth rather than a reading of six revision
files. Records the counts as re-runnable assertions.

Task: T0.11"
```

---

### Task 2: The target table roll-call — the row set and its doc traces

**Files:**
- Modify: `docs/planning/baseline-schema-inventory.md` (add §0–§10 headings with pending markers; fill §2's rows, leaving the disposition column blank)

**Produces:** §2 as a table with one row per table in the target, each carrying its **owning doc section** and its **landing pass** — and nothing else. Dispositions are deliberately withheld to Task 3, so this task cannot smuggle a judgement into what is meant to be an enumeration.

**Consumes:** doc 04 §2 (the object map), §3, §4, §5.1, §6, §7, §8.1–§8.8, §9, §12; doc 19 §3; Appendix A (for tables that exist today); `erd.md` as a cross-check only; `E0-baseline-and-harness.md` T0.12a and T0.12b for the landing pass.

**Row schema — fixed here, never widened by a later task:**

| Table | Owning doc § | Lands in | Disposition | Note |
|---|---|---|---|---|

`Lands in` is `T0.12a` / `T0.12b` / `T0.12c` / `—` (not landed) / `n/a (runtime)`. T0.12a's own text names `memories`, `entities`, `entity_relations`, tags, `config`, `embedders`; T0.12b's names `knowledge_triples`, `fact_sources`, articles and citations, `projects`, `repositories` and the `code_*` tables, job state, and `events` with its partitioning. **A table named by neither is a finding, not a guess** — record it in §10 addressed to T0.12b's executor. That assignment is what turns this inventory from a description into the work order T0.12a–c execute against.

- [x] **Step 1: Create the skeleton**

Write all headings §0–§10 plus Appendix B, each unfilled one carrying `_(pending: Task N)_`. Appendix A already exists from Task 1 and moves below them.

- [x] **Step 2: Enumerate from doc 04, section by section, in doc order**

Walk doc 04 §2's object map first (it is the spine and names every table or explicitly says "no new table"), then §3–§9 for the tables each section owns, then §12's own enumeration of what the baseline creates as a cross-check against your list. Every row cites the **most specific** section that fixes its shape — `§8.3` for `knowledge_triples`, not `§8`.

Then sweep Appendix A's table list and add any table present today that doc 04 never mentions. Such a row gets doc § `—` and is a **finding**, not a silent carry-over: doc 19 §3's disposition table is finite, so an object in neither doc 04 nor doc 19 §3 has no owner and cannot be dispositioned by anyone but a human.

- [x] **Step 3: Cross-check against `erd.md` and record disagreements as findings**

`erd.md` §1–§5 diagram the same target at lower resolution and its own header subordinates it to doc 04. Diff its table set against §2's. Every table in one and not the other is a §10 row naming both sources — **not** a silent adoption of either. `erd.md` never wins; it only reveals.

- [x] **Step 4: Verify — bidirectional completeness**

Two checks, both mechanical, both recorded in Appendix B:

```bash
cd /root/repositories/darkmem
# (a) every table name doc 04 sets in backticks appears in the roll-call
rg -o '`[a-z][a-z0-9_]{3,}`' docs/design/04-data-model-and-schema.md | sort -u > /tmp/doc04.txt
# (b) every table in the as-is manifest appears in the roll-call or is queued for §8
```

Check (a) over-collects (it catches column and function names too), which is the point: the reviewer's job is to confirm each *unmatched* identifier is genuinely not a table, and an over-collecting filter fails safe. Check (b) is a strict set difference against Appendix A.1 and must come out empty — a table that exists today and appears in neither §2 nor the §8 queue is an object nobody has dispositioned.

Then assert every row carries a non-empty `Owning doc §` or is listed in §10, and that `git status --porcelain` shows only the inventory file.

- [x] **Step 5: Commit**

```bash
git add docs/planning/baseline-schema-inventory.md
git commit -m "docs(planning): enumerate the target table roll-call

One row per target table with its owning doc 04 section and the T0.12
pass that lands it. Dispositions deliberately left blank; the row set
is fixed here so later passes fill columns rather than re-deriving
which objects exist.

Task: T0.11"
```

---

### Task 3: Dispositions, and §8 — the objects that do not land

**Files:**
- Modify: `docs/planning/baseline-schema-inventory.md` (fill §2's `Disposition` column; write §8; open §10 with the vocabulary amendment)

**Produces:** every §2 row dispositioned `carries-over` / `reshaped` / `target-new` / `target-new, inert`; §8 listing every object present at HEAD and deliberately absent from the target; and the first §10 entry, the Tier-2 amendment recorded in this plan's vocabulary section.

**Consumes:** §2 (Task 2), Appendix A (Task 1), doc 19 §3's disposition table, doc 04 §7 and §12.

**§8 row schema:**

| Object | Present at HEAD | Disposition | Doc § | Why it does not land |
|---|---|---|---|---|

- [x] **Step 1: Disposition every §2 row**

The decision rule, stated once so it is checkable rather than intuitive:

- **`carries-over`** — the object exists in Appendix A and the target changes neither its columns, its keys, nor its constraints. Doc 04 §3.2's "the target keeps them verbatim" is the canonical phrasing.
- **`reshaped`** — the object exists in Appendix A and the target changes something about it. This is the disposition that most often gets under-applied: a table gaining one target-new column, one new index, or one new UNIQUE support is `reshaped`, not `carries-over`. Three specific traps, each of which is a real target change to a table that otherwise looks untouched: `memories` gains `origin_key`, drops the `llm_` prefix on four columns, and gains a target-new `UNIQUE (id, project)` support that exists solely so `memory_relations`' composite FKs can be declared (doc 04 §8.2, §10); `entities` and `entity_relations` each gain `repo_ids[]` and its GIN index (doc 04 §4.1/§4.2); `repositories` gains `index_debt` (doc 04 §6).
- **`target-new`** — no row in Appendix A, or the name survives but every column and semantic is new. `knowledge_triples` is the latter and doc 04 §8.3 fixes the call: "treated as target-new, NOT as an activation of the dormant demo scaffolding".
- **`target-new, inert`** — `target-new` *and* nothing in the target's own phase writes to it. Doc 19 §3's table is the closed list of what qualifies; Task 6 supplies each one's writer.

Objects that exist today and are `(activation)` in doc 19 §3 — `api_keys`, `memories.importance` — are **`carries-over` with an activation note and a first-reader task id**, because their schema does not change; only a later phase's read path does.

- [x] **Step 2: Write §8**

Doc 19 §3 supplies the disposition and the reason for `enrichment_queue`, `audit_log`, `llm_providers`, `llm_profiles`, `ml_profiles` and every `*_ref`; doc 04 §7 and §12 corroborate. `audit_log` takes `dropped, optional transform` — doc 19 §4 keeps the legacy-row transform into `events` as a cutover convenience "taken only if the mapping is trivial", so it is not a plain drop.

Add the two column-level drops that already happened: `memories.classified_type` and `memories.classified_confidence` were dropped at revision `0006`, and doc 04 §3.1 states that `classified_confidence` is **not** reintroduced while the *name* `classified_type` returns as the rename target of `llm_classified_type` carrying different semantics. That name reuse across a semantic change is exactly the kind of thing a baseline built from migration history gets wrong, so it earns its own §8 row and a pointer from §5.

- [x] **Step 3: Open §10 with the vocabulary amendment**

Write the Tier-2 amendment this plan's vocabulary section specifies: T0.11's four dispositions cannot express `dropped`; §8 is added with its own two-value vocabulary; the change is to T0.11's acceptance criteria; the controller applies it to E0's amendment log and `progress.md`. State it as an amendment **proposal with a recommended disposition**, not as an accomplished edit, since no step here may touch the epic file.

- [x] **Step 4: Verify — nothing in Appendix A is unaccounted at table level**

```bash
cd /root/repositories/darkmem/docs/planning
# every table name in Appendix A.1 must appear in §2 or §8
```

Record the check in Appendix B as a reproducible `rg`/`comm` pipeline over Appendix A.1's table list versus the union of §2's and §8's first columns. Expected: empty difference. `alembic_version` is an object in that list and needs a disposition like any other — it is Alembic's own bookkeeping table, `carries-over`, `Lands in: n/a (Alembic)`, doc 19 §2. Recording it is cheaper than the reviewer wondering why it is missing.

Then assert every §2 row has a non-empty disposition, and `git status --porcelain` shows only the inventory file.

- [x] **Step 5: Commit**

```bash
git add docs/planning/baseline-schema-inventory.md
git commit -m "docs(planning): disposition every target table, add drops

Fills the disposition column against doc 19 s3's table and adds s8 for
objects present at HEAD and deliberately absent from the target, which
the four-value vocabulary cannot express. Records that gap as a
Tier-2 amendment proposal in s10.

Task: T0.11"
```

---

### Task 4: Indexes, constraints, triggers, types, and column changes

**Files:**
- Modify: `docs/planning/baseline-schema-inventory.md` (fill §3, §4, §5)

**Produces:** the fine-grained object rows that hang off §2's table spine — every index, every constraint, every trigger, the one enum type, and every column-level change on a `reshaped` table.

**Consumes:** Appendix A.2–A.7 (the mechanical bulk), doc 04 §3.1, §4.1, §4.2, §5.2, §6, §7, §8.1–§8.8, §10, §11 (the target's own index and constraint list), and §2's dispositions.

**Row schemas:**

```
§3  | Index | On table | Definition | Disposition | Doc § | Lands in |
§4  | Object | Kind | On | Definition | Disposition | Doc § | Lands in |     (Kind: PK/FK/UNIQUE/CHECK/trigger/function/enum)
§5  | Table.column | Change | Disposition | Doc § | Note |
```

**Why this is one task and not three:** the three sections share a single mechanical spine — Appendix A.2–A.4 supply every carried-over row verbatim, and doc 04 §10 supplies the target-new ones in one place ("The new tables carry their own load-bearing indexes, summarised here so §12 can order their creation"). Splitting them would triple the number of times someone re-reads the same two sources.

- [x] **Step 1: Seed §3 and §4 from Appendix A**

Every index in A.3 and every constraint in A.5 becomes a row, `Definition` copied verbatim from `indexdef`/`pg_get_constraintdef`. Disposition follows its owning table's from §2 unless the object itself changes. Rows belonging to a §8-dropped table are **removed**, not dispositioned — they leave with their table, and §8 already records why.

- [x] **Step 2: Add the target-new indexes and constraints from doc 04 §10 and §11**

Doc 04 §10's second paragraph enumerates the new tables' load-bearing indexes; §11 restates the schema-level constraints. Two additions are easy to miss because they sit on tables that otherwise carry over:

- The **composite `(project, status)`** support on `memories` — doc 04 §10 calls it "the one index change the pushdown strictly requires", with `(project, status, is_archived)` or a partial `WHERE status='active' AND is_archived=false` as stated options. The inventory records the decision it recommends and marks the alternatives, because T0.12c has to write one of them.
- The **`UNIQUE (id, project)`** support on `memories` — doc 04 §8.2 and §10. It is trivially satisfiable and exists solely so `memory_relations`' endpoint FKs can be composite. Omitting it makes `memory_relations` undeclarable, so it is a hard prerequisite, not a nicety.

Also record the two SQL triggers doc 19 §2 says the baseline authors — the `memories` FTS trigger (exists today, `carries-over`, Appendix A.5 has its exact definition) and the `events` `BEFORE UPDATE OR DELETE OR TRUNCATE` forbid-trigger (`target-new`, doc 04 §8.1) — and note against the second that **T1.06 owns it**, per T0.12b's own text: "`events` is `RANGE(created_at)` partitioned (the trigger is T1.06's)". An inventory row whose landing task disagrees with T0.12b's text is a finding.

- [x] **Step 3: Write §5 — column-level changes**

One row per column change on a `reshaped` table. Doc 04 §3.1's table is the source for `memories`; §4.1/§4.2 for the graph; §6 for `repositories`; §9 for the surgical list. The `llm_` prefix drop is four rows (`llm_classified_type → classified_type`, `llm_summary → summary`, `llm_emotions → emotions`, `llm_flags → flags`), each noting that the target *name* `classified_type` collides with a name dropped at `0006` under different semantics (cross-reference §8).

Column rows carry the **server default from Appendix A.2**, not the default doc 04's table prints — because those disagree, and Task 7 needs the disagreement recorded here to audit it. On `memories`, A.2 shows `id`, `content`, `source`, `importance`, `metadata` and `is_archived` as `NOT NULL` with **no server default at all**, while doc 04 §3.1 prints `0.5`, `{}` and `false` for three of them. Record what A.2 says and flag the delta; do not reconcile it here.

- [x] **Step 4: Verify — full set difference against Appendix A**

This is the strict version of Task 3's table-level check, now over every object class:

```
every index    in A.3 → appears in §3, or its table is in §8
every constraint in A.4 → appears in §4, or its table is in §8
every trigger  in A.5 → appears in §4
every function in A.6 → appears in §4
every enum     in A.7 → appears in §4
```

Record the pipeline in Appendix B. Expected: five empty differences. Additionally assert that every §3/§4 row has a `Lands in` value and that the count of `carries-over` index rows plus `dropped-with-table` index rows equals 63.

Then `git status --porcelain` shows only the inventory file.

- [x] **Step 5: Commit**

```bash
git add docs/planning/baseline-schema-inventory.md
git commit -m "docs(planning): inventory indexes, constraints, columns

Seeds the carried-over rows verbatim from the machine-extracted
manifest and adds the target-new ones from doc 04 s10/s11, including
the (project, status) pushdown support and the UNIQUE (id, project)
that memory_relations' composite FKs require.

Task: T0.11"
```

---

### Task 5: §6 — the per-fingerprint partition templates

**Files:**
- Modify: `docs/planning/baseline-schema-inventory.md` (write §6)

**Produces:** eight rows — four existing parents and four target-new — each explicitly marked **registry entry, not migration DDL**, with its `_TABLE_TEMPLATES` and `_AUX_INDEXES` shape, the task that lands the registry entry, the task that labels it inert, and the task that exercises it.

**Consumes:** doc 04 §5.1–§5.3, doc 19 §2, doc 20 §6; `backend/app/services/embedder_registry.py` (read-only, for the current template and aux-index shape); Appendix A's zero-child-tables assertion; E0's T0.12c, T0.13 and T0.14.

**Why these are a different kind of row.** Doc 19 §2 expressly rejects static child-table DDL: "expressing the child tables as static migrations — the DDL is runtime-parameterised by fingerprint, which no static migration can express". T0.12c says the same in its own words: "The four per-fingerprint embedding templates land here as **registry entries** … nothing about them belongs in the Alembic file." So a §6 row is not something the baseline creates; it is something the baseline must **not** create, and the inventory has to say so loudly enough that a T0.12c executor reading only §3 does not add eight `CREATE TABLE`s.

**Row schema:**

| Parent | Child pattern | Key columns / PK | Aux indexes | Disposition | Doc § | Registry entry lands in | First writer |
|---|---|---|---|---|---|---|---|

- [x] **Step 1: The four existing parents**

`memory_embeddings`, `entity_embeddings`, `code_chunk_embeddings`, `entity_embedding_cache` — doc 04 §5.2's table gives key columns, PK and FKs; the same section names the aux indexes (`memory_id`, `entity_id`, `(repo_id)` + `(repo_id, file_path)`, `last_used_at`) and the HNSW settings (`vector_cosine_ops WITH (m=16, ef_construction=128)`). Disposition `carries-over`. Cross-check the recorded shape against `_TABLE_TEMPLATES` / `_AUX_INDEXES` in `embedder_registry.py` and record any disagreement as a §10 finding — doc 04 wins, per the authority order.

- [x] **Step 2: The four target-new parents**

`block_embeddings`, `relation_embeddings`, `article_embeddings`, `triple_embeddings` — doc 04 §5.3's table gives each one's key columns, PK, FK and cascade behaviour. Two rules from §5.3 are load-bearing and belong in the Note column, because getting them wrong is silent: `relation_embeddings` keys on the real `entity_relations.id` with `ON DELETE CASCADE` (no synthetic ids, so strip-before-rewrite kills the vector with the relation), and it carries **no project predicate of its own** because `entity_relations` is global. `triple_embeddings` references `knowledge_triples.id` with **no cascade** — facts are invalidate-not-delete.

All four are `target-new, inert`. `triple_embeddings` additionally notes "template ships, writer deferred behind a measured `pg_trgm`-on-`fact` undercount" (doc 04 §5.3, doc 19 §3).

- [x] **Step 3: Name the three tasks each template passes through**

Registry entry lands in **T0.12c** ("All four templates present as registry entries"). Inert labelling is **T0.13** ("their inert labelling is T0.13's"). The reconciliation that creates the child tables at boot is **T0.14**. The `First writer` column is Task 6's territory and is filled there; leave it and let Task 6 fill it, so the two tasks do not both search the epic corpus for the same ids.

- [x] **Step 4: Verify — prove the templates are not migration DDL**

Two mechanical checks, both in Appendix B:

```bash
cd /root/repositories/darkmem
rg -n '__[a-z0-9_]+.*(CREATE TABLE|create_table)' backend/migrations/   # expect: no matches
rg -c 'embeddings__|entity_embedding_cache__' backend/migrations/       # expect: no matches
```

Plus Appendix A's assertion that a freshly migrated database holds **zero** `*__<slug>` tables. Together these establish empirically, not by assertion, that the child tables are runtime objects — which is exactly the claim §6 makes.

Then `git status --porcelain` shows only the inventory file.

- [x] **Step 5: Commit**

```bash
git add docs/planning/baseline-schema-inventory.md
git commit -m "docs(planning): inventory the eight partition templates

Eight registry entries, not migration DDL. Doc 19 s2 rejects static
child-table DDL because the shape is fingerprint-parameterised, so
these rows record what the baseline must NOT create, verified against
a freshly migrated database holding zero child tables.

Task: T0.11"
```

---

### Task 6: §7 — the inert register and its first writers

**Files:**
- Modify: `docs/planning/baseline-schema-inventory.md` (write §7; fill §6's `First writer` column)

**Produces:** one row per `target-new, inert` object naming the **phase** and the **task id** that will first write to it, with the cited task's own words quoted so the claim is checkable without opening the epic file.

**Consumes:** §2, §5 and §6's inert rows; doc 19 §3's writer/activator column; doc 20 §6's honesty-tag timeline (which fixes *which phase* a tag may flip in); `docs/planning/tasks/E1-engine-core.md`, `E2-truth-core.md`, `E3-synthesis-and-reach.md`, `E4-hardening-and-scale.md`, `EH1-documents-pkm.md`.

**Row schema:**

| Object | Disposition | Phase | First-writer task | The task's own words | Doc § |
|---|---|---|---|---|---|

**This is the task with the sharpest failure mode.** "Every inert object names the phase and the task that will first write to it" is only satisfied if the cited task **exists** and **actually writes that object**. A plausible-looking id that resolves to a different task is worse than a blank, because it reads as verified. Two independent defences are built in below: `check_plan.py` catches ids that do not exist at all, and the quoted-words column catches ids that exist but write something else.

- [x] **Step 1: Establish the phase from doc 20 §6 before searching for task ids**

Doc 20 §6's diagram places each inert family in a phase — `repo_ids[]` and the document/block tables and the embedding templates in Phase 0 (landing), their activations in Phase 2 (`C4: repo_ids[] writer — the deriver, doc 10, after G-C`), Phase 3, Phase 4 and the H1 horizon lane. Fixing the phase first turns the id search from "grep five files for a plausible match" into "grep the one epic that owns that phase" — E1 is Phase 1, E2 is Phase 2, E3 is Phase 3, E4 is Phase 4, EH1 is H1. An id found in the wrong epic for its phase is a finding, not a row.

- [x] **Step 2: Find each writer and quote it**

```bash
cd /root/repositories/darkmem/docs/planning/tasks
rg -n 'repo_ids|index_debt|triple_embeddings|relation_embeddings|article_embeddings|block_embeddings|api_keys|importance|memory_access_stats' \
   E1-engine-core.md E2-truth-core.md E3-synthesis-and-reach.md E4-hardening-and-scale.md EH1-documents-pkm.md
```

For each hit, open the enclosing `#### T…` block and quote the clause that establishes it as the writer. The corpus already carries this convention and its precedent format — E1's T1.05 reads "Labelled inert in the schema inventory naming their first-writer tasks (T2.26 for `verification`, T3.02 for `synthesis`)", and E2 and E3 carry the reciprocal acceptance ("The template loses its inert label and the schema inventory records this task as its writer"). Those reciprocal checkboxes are the strongest evidence available: an object whose future writer's task already promises to update this inventory is a confirmed pairing, and one without such a promise needs the quoted words to carry the whole claim.

Fill §6's `First writer` column in the same pass.

- [x] **Step 3: Verify — `check_plan.py` lints the inventory automatically**

This is the load-bearing check and it costs nothing, because `check_plan.py` already globs `*.md` in `docs/planning/` and asserts that every `T(?:H1|[0-4])\.\d{2}[a-z]?`-shaped reference resolves to a defined task:

```bash
cd /root/repositories/darkmem/docs/planning
/root/repositories/darkmem/backend/.venv/bin/python scripts/check_plan.py
```

Expected: `PLAN GREEN — 205 tasks, all structural claims verified`. A `FAIL [refs] reference to undefined task Tx.yy` means the inventory invented an id. Run this **before** committing, not after — it is the difference between a typo caught in ten seconds and a wrong citation shipped into a Fable review.

Note for the reviewer, and record it in Appendix B: `check_plan.py` proves an id *exists*; only the quoted-words column proves it is the *right* id. Both are required.

Second check: every §2/§5/§6 row dispositioned `target-new, inert` has a §7 row, and every §7 row has a non-empty phase, task id and quote. Set difference, expected empty.

Then `git status --porcelain` shows only the inventory file.

- [x] **Step 4: Commit**

```bash
git add docs/planning/baseline-schema-inventory.md
git commit -m "docs(planning): name every inert object's first writer

Each inert row carries its phase from doc 20 s6 and its first-writer
task id, quoted from that task's own text so the pairing is checkable
without opening the epic file. check_plan.py lints every cited id.

Task: T0.11"
```

---

### Task 7: §9 — the SQL-first audit

**Files:**
- Modify: `docs/planning/baseline-schema-inventory.md` (write §9)

**Produces:** a per-construct verdict over every ORM-side construct in `backend/app/models/` and `embedder_registry.py`, stating for each whether it is load-bearing and what the baseline must do about it.

**Consumes:** `backend/app/models/*.py` (read-only), `backend/app/services/embedder_registry.py` (read-only), Appendix A.2 and A.4, doc 19 §2, doc 20 §7, doc 04 §12.

**The rule being audited, quoted so the verdict column means something.** Doc 19 §2: "Every table, constraint, index, trigger, and the reconciliation's own DDL stays expressible as plain SQL — **no ORM-only construct is load-bearing anywhere in the schema** … the FTS trigger, the `events` forbid-trigger and its monthly `RANGE(created_at)` partitioning, the partial and composite indexes, the `chk_superseded_has_pointer` CHECK, and the one native enum are all authored as SQL in the baseline; SQLAlchemy models mirror the SQL, not the reverse. A schema change that only an ORM construct can express is rejected at review as a portability regression." Doc 20 §7 makes it standing on Phases 0–4: "It is the one place the deferred migration reaches back into the committed path, and it costs nothing to honour now while being expensive to retrofit."

**Row schema:**

| Construct | Where | What it does | In the DDL? | Load-bearing? | Verdict | Action for T0.12a–c |
|---|---|---|---|---|---|---|

- [x] **Step 1: Sweep the ORM for every candidate construct**

```bash
cd /root/repositories/darkmem/backend
rg -n 'onupdate=|default=|server_default|server_onupdate|__table_args__|CheckConstraint|UniqueConstraint|Index\(|ForeignKey\(|create_type=False|event\.listen|@validates|@hybrid_property' app/models/*.py
rg -n 'DDL\(|event\.listen|Computed\(|Identity\(' app/
```

Every hit becomes a row. The `In the DDL?` column is answered from Appendix A, never from reading the migration: a construct is in the DDL if and only if the extracted manifest shows it.

- [x] **Step 2: Adjudicate the three findings this plan already located**

These are named here so they are audited rather than rediscovered, and so a reviewer can check the executing agent's verdict against the same evidence. Each was confirmed against a live database built from the six revisions, not inferred.

**(a) `updated_at`'s auto-bump has no SQL home. Escalate as Tier-3.** `backend/app/models/memory.py:48` declares `updated_at … server_default=func.now(), onupdate=func.now()`. SQLAlchemy's `onupdate` is **client-side**: it emits the new value in the ORM's own UPDATE and does nothing to the database. Appendix A.2 shows `updated_at` with server default `now()`, and Appendix A.5 shows the *only* user trigger in the whole schema is `memories_fts_update`. So the bump exists solely in Python. Doc 04 §3.1 nonetheless lists the column as `now() (onupdate)` in its schema table, and doc 04 §9 reasons *from* the bump as a semantic worth protecting — it is the whole justification for `memory_access_stats` being a side table rather than two columns on `memories`: "any ORM-path update would additionally fire `onupdate=now()`, silently corrupting `updated_at`'s 'content changed' meaning." Doc 19 §2 forbids a load-bearing ORM-only construct and enumerates the triggers the baseline authors — the FTS trigger and the `events` forbid-trigger — with no third. Doc 04 §12's own enumeration of what the baseline creates names no `updated_at` trigger either. **Either the baseline gains a trigger no doc lists, or a documented semantic stays ORM-only in violation of a rule both doc 19 §2 and doc 20 §7 state as binding.** Neither doc resolves it, and `conversations.updated_at` (`chat.py:19`) and `repositories.updated_at` (`code.py:28`) carry the identical construct. Under runbook §5 this is Tier-3 — "a design doc is wrong or ambiguous" — and Tier-3 means **do not proceed to resolve it**: write it up in §10, state both readings, and stop rather than picking one.

**(b) Five NOT NULL columns on `memories` whose only default is in the ORM.** Appendix A.2 shows `id`, `content`, `source`, `importance`, `metadata` and `is_archived` as `NOT NULL` with an **empty** `column_default`. `app/models/memory.py:40–50` supplies `default=uuid.uuid4`, `default="api"`, `default=0.5`, `default=dict`, `default=False`. A plain-SQL INSERT omitting any of them fails. Doc 04 §3.1 prints `0.5`, `{}` and `false` as if they were DDL defaults, and prints `source`'s as "ORM `'api'`" — so for `source`, doc 04 *knowingly records* an ORM-only default while doc 19 §2 forbids load-bearing ORM-only constructs. The audit must state a verdict and an action: the natural one is that the baseline authors the server defaults (making the §5 rows `reshaped`), which honours both docs at the cost of one line of DDL per column. Whether `source`'s doc-04 annotation makes that a doc-vs-doc contradiction or merely a doc describing today's state is the judgement call — apply the stated test: *does doc 19 §2's "no ORM-only construct is load-bearing in the schema" cover column value defaults, or only structural objects?* If the executing agent cannot answer from the corpus, it is Tier-3 and stops. `id`'s app-generated UUIDv7 is explicitly **not** in this class — doc 04 §2 fixes application generation as the design, with server-side `gen_random_uuid()` only for `entities`/`entity_relations`.

**(c) A constraint doc 04 discusses that does not exist.** `app/models/llm_config.py:174` declares `UniqueConstraint("purpose", name="uq_llm_purpose_configs_purpose")`, and doc 04 §12 offers a choice about it — "The `llm_purpose_configs` redundant `UNIQUE(purpose)` (belt-and-suspenders over the PK) can stay or be dropped; it is harmless." Appendix A.4 shows `llm_purpose_configs` carrying only its PK on `purpose` and three FKs: **the UNIQUE was never created**. The table is built by raw `CREATE TABLE` inside `op.execute`, so the ORM's `__table_args__` never reached the database. Doc 04 §12 is therefore reasoning about an object that exists only in ORM metadata. The verdict is straightforward (`llm_purpose_configs` is `reshaped` anyway under the LLM flattening, and the phantom UNIQUE simply does not carry), but the row belongs in §9 because it is the cleanest possible demonstration of why this audit is not ceremonial.

- [x] **Step 3: Audit the registry's DDL for SQL-first compliance**

Doc 19 §2 binds "the reconciliation's own DDL" to the same rule, because the .NET replay moves it into "the registry's C# equivalent" as "a loop over rows running parameterised plain-SQL DDL". Read `_TABLE_TEMPLATES` and `_AUX_INDEXES` in `embedder_registry.py` and record whether each template is a plain-SQL string (portable) or built through SQLAlchemy schema objects (not). Record the verdict; do not change the file.

- [x] **Step 4: Verify — the audit is complete and reproducible**

Every `rg` hit from Step 1 appears as a §9 row (set difference over the sweep output, expected empty), every row has a non-empty verdict, and every row whose verdict is "load-bearing and ORM-only" has either an action for T0.12a–c or a §10 finding. Record the sweep commands in Appendix B so a reviewer re-runs them rather than trusting the list.

Then `git status --porcelain` shows only the inventory file.

- [x] **Step 5: Commit**

```bash
git add docs/planning/baseline-schema-inventory.md
git commit -m "docs(planning): audit the schema for ORM-only constructs

Per-construct verdict over app/models and the embedder registry
against doc 19 s2's SQL-first rule, with each verdict checked against
the machine-extracted manifest rather than against the migration
source. Three constructs need a decision; one is escalated Tier-3.

Task: T0.11"
```

---

### Task 8: Front matter, findings, and the hand-off

**Files:**
- Modify: `docs/planning/baseline-schema-inventory.md` (write §0, §1, §10, Appendix B; remove every remaining pending marker)

**Produces:** the finished document — a reader's entry point, the disposition legend, the consolidated and tiered findings, and the appendix of re-runnable checks that makes the whole thing verifiable rather than merely reviewed.

**Consumes:** everything above; runbook §5 for the amendment tiers; T0.15's text for the one downstream consumer constraint.

- [x] **Step 1: §0 front matter and §1 legend**

§0 states status and date, the purpose in T0.11's own words, the **authority order** (doc 04 wins on table shapes, doc 19 wins on operational sequencing and disposition — doc 19 §1 fixes this; `erd.md` and the ORM have no authority), and the four-source table from this plan's Architecture section. §1 gives the disposition legend and the decision rule from Task 3 Step 1, so a later reader can check a row's disposition rather than accept it.

**One downstream consumer constraint.** T0.15's Verify is `rg -n "freeze" CLAUDE.md docs/planning/baseline-schema-inventory.md`, and E1's cutover task requires that "`CLAUDE.md` and the schema inventory record the freeze date — the real one". So §0 must carry a **freeze note**: that the baseline is regenerated rather than migrated until the homelab cutover freezes it at `0001` (doc 19 §2), that a CI assertion holds `alembic history` at exactly one revision until then, and that the freeze date is **deliberately blank** until the cutover happens. Leaving the placeholder is correct; T0.15 owns the protocol and E1's cutover task fills the date. Writing a fictional date would be the exact dishonesty runbook §4 exists to prevent.

- [x] **Step 2: §10 — consolidate and tier every finding**

Findings accumulate through Tasks 2–7; this step gathers them into one table and assigns a runbook §5 tier to each.

| # | Sources in conflict | What each says | Tier | Disposition |
|---|---|---|---|---|

The tiering rule, applied not assumed: **Tier 1** is task-local (a wrong path, a missing row). **Tier 2** reaches beyond this task — the disposition-vocabulary amendment from Task 3, and any object §2 could not assign to a T0.12 pass, both belong here because they change what a later task must do. **Tier 3** is a design-corpus contradiction and it **stops execution** rather than being resolved: at minimum the `updated_at` finding (Task 7 Step 2a), plus the `source` ORM-default question if the executing agent could not settle it from the corpus.

Tier-3 rows are set apart at the **top** of §10 under their own heading, not sorted in among the typos. Runbook §7 says stop and do not improvise when a Tier-3 surfaces or when two design docs disagree; the inventory's job is to state the contradiction precisely enough that a human can adjudicate it, and to make it impossible to miss. Each Tier-3 row quotes both sides verbatim, names the file and line where the code sits, and states explicitly that it is **not resolved here**.

- [x] **Step 3: Appendix B — every check in one place**

Collect the verification commands from Tasks 1–7 into one runnable appendix, grouped by what they prove. A reviewer must be able to re-derive the whole inventory's factual basis without re-reading this plan. Note against the set-difference checks that they are the mechanical half and the doc-section traces are the human half — "no unexplained entries" needs both.

- [x] **Step 4: Verify — the whole document, and the untouched floor**

```bash
cd /root/repositories/darkmem
rg -n 'pending: Task' docs/planning/baseline-schema-inventory.md          # expect: no matches
cd docs/planning && /root/repositories/darkmem/backend/.venv/bin/python scripts/check_plan.py
cd /root/repositories/darkmem && rg -n 'freeze' docs/planning/baseline-schema-inventory.md   # T0.15's grep must hit
git diff --name-only master...HEAD
```

`check_plan.py` must print `PLAN GREEN — 205 tasks, all structural claims verified`. `git diff --name-only master...HEAD` must list **only** `docs/planning/baseline-schema-inventory.md` and `docs/superpowers/plans/2026-07-27-baseline-schema-inventory.md` among this plan's additions — anything under `backend/` or `frontend/` means a step went out of bounds.

Then re-run all of Appendix B and confirm every check still passes, and assert the floor:

```bash
cd /root/repositories/darkmem/backend && timeout 1500 ./.venv/bin/python -m pytest -q
```

Expected: `614 passed, 1 skipped` — identical to the pre-work reading recorded in this plan's Global Constraints. This is a no-op assertion by construction (no code changed), and its value is precisely that: a different number means something outside this work moved, which is a finding to report, not a result to absorb.

- [x] **Step 5: Commit and hand off**

```bash
git add docs/planning/baseline-schema-inventory.md
git commit -m "docs(planning): complete the baseline schema inventory

Front matter, disposition legend, consolidated findings tiered under
runbook s5, and the reproducible-check appendix. Carries the freeze
note T0.15's verification greps for, with the date deliberately blank
until the cutover.

Task: T0.11"
```

The completion report must carry, verbatim and prominently: every **Tier-3** finding (these block T0.12a); every **Tier-2** amendment the controller must propagate to `E0-baseline-and-harness.md`'s amendment log and `progress.md`; and the real output of the floor run. T0.11's Verify is a **Fable-tier adversarial review** against docs 04 and 19 — the review is chartered to find an object that traces to no doc section, not to confirm that most of them do — so the hand-off states which checks are mechanical (Appendix B) and which rest on the reviewer's reading (the doc-section traces, and the quoted-words column in §7).

---

## Self-Review

**Coverage against T0.11's five acceptance checkboxes.**

| T0.11 "Done when" | Where it lands | How it is checked |
|---|---|---|
| Every table, index, constraint, and partition template enumerated | §2 (Task 2), §3/§4/§5 (Task 4), §6 (Task 5) | Bidirectional set difference against Appendix A, five object classes, all empty |
| Each marked with one of the four dispositions | §2 disposition column (Task 3), carried into §3–§6 | Assert no row has an empty disposition |
| Every inert object names the phase and the task that will first write to it | §7 (Task 6), §6's `First writer` | `check_plan.py` proves the id exists; the quoted-words column proves it is the right one |
| SQL-first checked | §9 (Task 7) | Every `rg` sweep hit appears as a row with a verdict; verdicts checked against Appendix A, not against the migration source |
| Written to `docs/planning/baseline-schema-inventory.md` | Task 1 creates it; Tasks 2–8 build it in passes | `git diff --name-only master...HEAD` |

**Sizing.** Task 1 is S (mechanical, ~30 min). Tasks 2, 3, 4, 6, 7 are M. Task 5 is S–M. Task 8 is M and bounded by re-running checks rather than by new judgement. No step is itself an `L`, which is runbook §3's requirement for a plan over an `L` task.

**Sequencing — what each step constrains downstream.** Task 1's manifest is the denominator for every completeness check in Tasks 3, 4 and 7, and its zero-child-tables assertion is Task 5's evidence. Task 2 fixes the **row set** so Tasks 3–7 fill columns; no later task may add a §2 row without recording why Task 2 missed it. Task 3's dispositions select Task 6's inert subset. Task 4's column rows carry the server-default facts Task 7 audits. Task 8 only consolidates. The one deliberate forward reference is §6's `First writer` column, left blank by Task 5 and filled by Task 6, so the epic-corpus search happens once.

**Risk-first ordering.** The three risks this plan judges largest, and where each is attacked: (1) *reading the six revisions wrong* — Task 1, first, by executing rather than reading, and the 19-vs-26 tables and 23-vs-63 indexes gaps prove the risk is real, not theoretical; (2) *a fabricated future-writer task id* — Task 6, defended twice, once mechanically by a linter that already exists and once by quotation; (3) *silently resolving a doc contradiction instead of escalating it* — Task 7 names the three findings already located so they are adjudicated on the record, and Task 8 puts Tier-3 rows at the top of §10 under their own heading.

**Placeholder scan.** The only intentionally-blank item in the deliverable is the freeze **date** in §0, and it is blank by design — T0.15 owns the protocol and E1's cutover task fills the real date. No `TODO`, no "handle the rest", no "similar to Task N".

**What this plan deliberately does not do.** It does not write a line of DDL — T0.12a–c own that and are separate tasks on a separate lane branch. It does not resolve the Tier-3 findings — runbook §5 forbids it. It does not touch `progress.md` or any epic file, so the controller's propagation model stays intact. And it adds no script to the repo: every check is a recorded command a reviewer re-runs, which is what keeps the repo floor untouched from the first commit to the last.

## Known risks (surface during execution, not placeholders)

- **A table doc 04 never names may exist at HEAD.** Task 2 Step 2 routes it to §10 rather than inventing a disposition. If one appears, it is at minimum Tier-2 and possibly Tier-3, because doc 19 §3's disposition table is finite and an unlisted object has no owner.
- **The `Lands in` column may not resolve for every table.** T0.12a and T0.12b name their tables explicitly, but between them they may not cover the full target set. Task 2 records the gap as a finding addressed to T0.12b's executor rather than assigning by guess — a wrong assignment sends work to the wrong pass, and T0.12a–c are floor-exempt and merge as one atomic unit, so the mistake would not surface until T0.12c.
- **The `(project, status)` composite has three stated forms** in doc 04 §10 — bare, plus `is_archived`, or a partial `WHERE status='active' AND is_archived=false`. Doc 04 does not pick. Task 4 records a recommendation and marks the alternatives; if the executing agent judges the pick to be a design decision rather than an inventory one, that is a §10 row for T0.12c, not a silent choice.
- **Whether the baseline creates `events`' first monthly child partitions is unresolved by both docs.** Doc 04 §8.1 fixes monthly `RANGE(created_at)` from day one and doc 19 §9 stance-3 puts the *pre-create* arm on `pipeline_failure_cleanup`, but neither says whether the baseline itself lands month-0. A partitioned parent with no child accepts no inserts, so this matters. Task 4 records it as a finding for T0.12b rather than deciding it.
- **A Tier-3 finding blocks T0.12a.** If Task 7 escalates, T0.11 completes (the inventory is written, and the finding is part of its content) but the Lane C serialisation means T0.12a should not start until the escalation is answered. The completion report must say so explicitly — runbook §7's "stop, do not improvise" applies to the *next* task, not to finishing this one.
