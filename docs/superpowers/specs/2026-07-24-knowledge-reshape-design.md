# 05 — Knowledge Reshape Spec (memory / knowledge separation, code-as-facts, LLM simplification)

**Status:** design spec, 2026-07-24. Consolidates the maintainer's post-review feedback into binding decisions that amend the foundation docs (01 domain model, 03 stack, 04 schema). Produced through a brainstorm + four Fable reviews (knowledge-vault design, code-knowledge-base spike, open-questions advice). This is the approved reference the doc revisions apply; it does not replace docs 01/03/04, it directs their revision.

**Maintainer priority order (the lens every decision is judged on):** performance, correctness, stability, TRUTH. A confident-but-wrong "verified" result is the worst failure — the design prefers to under-claim.

---

## 1. Purpose & scope

The foundation docs modelled knowledge as *derived memory rows* (doc 04 §8.8: `insight`/`profile` memory_type + `DERIVED_FROM`, no new table). The maintainer's review reverses that: **knowledge is a first-class, verified vault separate from memory, built from memories + documents + code.** Five workstreams follow — the knowledge vault, code as a fact-originating knowledge base, LLM-config simplification, pipeline LM-injection redesign, and a set of clear schema decisions (generic audit, UUIDv7 + targeted partitioning, dropping the `llm_` prefix, one baseline migration). This spec fixes each decision; §7 lists the doc edits they imply, and §9 records the Fable-advised stance on every open question.

## 2. The knowledge vault — a four-layer epistemic ladder

Knowledge separates from memory as four layers, each with one job. Layers 0 and 1 exist today; Layers 2 and 3 are the target build.

- **Layer 0 — Memory (unchanged).** `memories` = episodic recall ("what was captured / said / happened"), append-only, never overwritten.
- **Layer 1 — Extracted graph (unchanged, raw).** Per-ingest `entities` / `entity_relations` = *candidate signal*, explicitly **not yet knowledge**. Feeds dedup, the `technologies` denorm, topics, and PPR; it is the derivation source for Layer 2 and stays.
- **Layer 2 — Verified facts (bi-temporal).** The `knowledge_triples` rebuild (doc 04 §8.3) **becomes** the verified-fact store, extended with a verification ladder, aggregated confidence, multi-source provenance, and structured context (below). This is where "final, verified understanding" physically lives; it keeps the bi-temporal "what did we believe as of date X".
- **Layer 3 — Subject articles (new `knowledge_articles` + `article_citations`).** One verified, synthesized write-up per subject, grounded with claim-level citations back to Layer 2. Retrievable → own per-fingerprint embedding partition. **Sequenced after Layer 2** and gated behind a groundedness metric (§2.4).

### 2.1 The verification ladder — `candidate → corroborated → confirmed`

A fact/article carries a `verification_status`: **`candidate`** (freshly extracted signal), **`corroborated`** (machine-promoted), **`confirmed`** (a human ratified it). The machine can never reach `confirmed` on its own — this operationalises the under-claiming preference and is surfaced everywhere (retrieval label, MCP payload field, UI badge, visually distinct from `confirmed`). A `disputed` sub-state marks conflicts.

**Promotion to `corroborated` counts `DISTINCT origin_key`, never rows** (echo is not evidence). Origin key by source kind: **memory → a captured session / agent-run identity** (a NEW ingest-time requirement the baseline must carry — `source`/`source_agent` alone are too coarse; populated at ingest from the MCP session or a per-boot agent-run id); **document → `document_id`**; **code → `repo_id`** (one origin per repo *regardless of commit count* — re-derivation refreshes, never multiplies); **human review decision → `source_kind='human'`, one origin, dominant**. The truth-critical degradation rule: **when origin identity is unknown, MERGE to one origin (undercount), never mint distinct ones** — undercounting delays promotion (the preferred failure); overcounting manufactures it (the worst failure).

Promotion requires ALL of:
1. **≥ N distinct origin keys.** N = **2** when the two origins differ in source-kind (memory+code, memory+block) **or** are ≥ 7 days apart across distinct sessions; otherwise **3**. N and the gap are `config` rows, tuned from measured promotion rates — start conservative, loosen only with evidence.
2. **Derived rows never corroborate** (Layer-2/Layer-3 rows are never sources — a structural exclusion, so the self-corroboration loop where an agent re-saves an article cannot inflate the count).
3. **Source-kind diversity outweighs raw count** (memory + document + code > three memories).
4. **No open contradiction** over an overlapping validity window, and **no newer REPLACES-family / supersession signal**. A single non-echo contradiction is an absolute **veto**, not a vote (consensus ≠ truth). Memory-level `CONTRADICTS` (§2.8) is an *input signal into* this fact-level dispute, never the dispute itself.

Deterministic **code-originated facts are born `corroborated`** (the parse *is* the verification) with a distinct `code@commit` badge. Human review sits above everything.

**The badge's honest claim.** The independence heuristic has a known ceiling (two agents reading the same wrong README is not detectable from provenance), so the design states what the badge cannot: machine `corroborated` means exactly **"asserted by K distinct origins of kinds [X, Y], no known contradiction, as of T"** — never "true", never "verified" in UI copy. Under-claiming is the design, not a caveat. The asymmetry justifies conservatism: a delayed promotion costs a label (candidates are served, labeled, above nothing); a wrong promotion costs every article that cites it and every agent that propagates it.

### 2.2 Provenance — a `fact_sources` child table (not parallel arrays)

`source_memory_ids uuid[]` cannot carry per-source metadata, index per-kind reverse lookups, or compute `COUNT(DISTINCT origin_key)`. Replace with **`fact_sources`**: `(id uuidv7 PK, fact_id FK→knowledge_triples ON DELETE CASCADE, source_kind, source_ref, origin_key, detail jsonb, created_at)`, btree `(source_kind, source_ref)` and `(fact_id)`, dedupe on `(source_kind, source_ref)`. All source refs are **soft** (no FK to memories/blocks/code — consistent with §8.3's endpoint doctrine and required by code's commit-addressed refs). A **human review decision is itself a `human`-kind source row** (who/when/what-was-shown), so the source-emptying sweep can never silently discard a `confirmed` fact. Per-kind delete/re-verify sweeps: memory re-extract/delete → re-evaluate; document re-ingest → block refs re-resolved/stale; repo re-index → code refs re-verified at new HEAD.

### 2.3 Context — `applies_when` + `learned_in`, boost/label/conflict-filter with a declared context

Facts and articles carry `applies_when jsonb` (structured: env / version / situation) and `learned_in` (auto-populated from project + source — trustworthy). **The agent's current context arrives by explicit declaration, with a precedence chain:** (1) an explicit per-call `context` argument on the search/vault MCP tools; (2) a per-session context declared once (an MCP tool call or `X-Darkmem-Context` header, mirroring `X-Darkmem-Client`); (3) per-project defaults on the `projects` registry row (§6.5); (4) nothing.

**Matching is boost-plus-label by default, hard-exclusion only on explicit conflict.** A fact whose `applies_when` matches gets a rank boost; a fact with unstated context is neutral and carries its context as a visible label; a fact in *explicit conflict* (caller says env=prod, fact says dev-only) is excluded **with a count surfaced** ("3 facts excluded by context conflict" — invariant 14's no-silent-degradation on the new axis). Never filter-out by default (most callers pass no context; a filter-default turns an over-tagged vault into one that returns nothing). Discipline: `env`/`situation` axes are closed vocabularies (invariant 5) or matching rots on drift (prod/production/prd); version comparison is app-side post-scoring, not jsonb; LLM-guessed `applies_when` tags are displayed provenance, never a conflict-exclusion basis, until human-touched. Boost is a deterministic post-fusion multiplier, so the negated-exists GIN trap that filtering would hit never materialises.

### 2.4 Articles — subjects, grounding, citations, lifecycle

- **Subjects = salient entities (soft key `(name_lower, entity_type)`) + pinned subjects only.** Leiden communities feed **pin suggestions** (diffed across runs — needs durable `memory_communities` rows), never a `subject_ref` (community ids churn every run). This removes polymorphic-ref complexity.
- **Grounding is enforced, not asserted, with claim-level citations.** One row per article + a **`article_citations`** child table: `(id uuidv7 PK, article_id FK→knowledge_articles ON DELETE CASCADE, fact_id FK→knowledge_triples, claim_span int4range, created_at)`. The `fact_id` takes a **hard FK** — facts are invalidate-not-delete (rows never deleted), so it is safe and buys referential integrity at the one place a dangling citation would be a truth catastrophe (a dead citation under a corroborated badge). Synthesis input is **only** the subject's non-disputed `corroborated`/`confirmed` facts; a **claim-level entailment pass** (the doc-00 §8 / F7 groundedness metric — reuse it) checks every article sentence against its cited fact; uncited spans fail the article; article `confidence` = claim-support coverage; failures route to the review queue. Do **not** reuse the documents/blocks machinery (L3 must not couple to the unshipped PKM horizon).
- **Lifecycle.** One active article per `(project, subject_key)` — partial-unique `WHERE status='active'`. Articles carry `synthesized_at` + a hash of their supporting verified-fact set; a change **labels the article stale** (retrieval surfaces the label — honest partial results), and re-synthesis runs **debounced in the dream job** (materiality gate = the *verified* set changed, not candidate churn; hub subjects capped to top-K facts by salience). Re-synthesis is strip-before-rewrite by `article_id` (citations cascade). Embeddings: `article_embeddings__<slug>` keyed `(article_id, fingerprint)`; chunk long articles at embed time via payload spans, not block rows.

### 2.5 Verification recomputation — Tier-C only, orthogonal to belief-lifecycle

`verification_status` is recomputed **only by the Tier-C consolidation job**, never inline in Phase 5 or `delete_by_memory_id` (which merely enqueues affected facts). A strip-before-rewrite that lands the identical `triple_key` set is a **provenance no-op** (no verified↔candidate thrash); demotion carries **hysteresis** (persist past a full job cycle, or demote to a labeled "under-sourced" sub-state). Verification and belief-lifecycle are **orthogonal axes**: `(open / window-closed / expired)` × `(candidate / corroborated / disputed / confirmed)`. Every verification transition is journaled as an `events` row so "what did we believe as of X" answers the verification dimension too.

### 2.6 Review queue — an override, never a stage on the path

Disputed facts and low-confidence articles are a **status + partial index** (`WHERE review_state='open'`, the `pipeline_failures` pattern), not a churning table; prioritised by **consequence** (retrieval frequency, subject salience), not FIFO; stale disputes auto-expire to a labeled state. Disputed knowledge is **served labeled with both sides**, never gated on review — the system stays useful with a large unreviewed backlog (a solo maintainer cannot be the throughput bottleneck of the truth system).

### 2.7 Retrieval composition across the four layers

Every returned row carries **`layer` + `verification_status` labels** (never silently dropped, never silently included — invariant 14). Default agent retrieval returns `confirmed`/`corroborated` above labeled `candidate`; `disputed` rows are served **labeled with both sides**; a memory already covered by a returned cited fact is **grouped under it** ("supports fact F"), not triple-counted. **Both new channels (facts, articles) are born with SQL project/status pushdown** (invariant 14). Cold-start: a verified-only default is empty for months, so `candidate` results are served **labeled** until corroboration accumulates.

### 2.8 The stored memory-relation vocabulary — five types (`DERIVED_FROM` cut)

`memory_relations` (own table, composite `(id, project)` FKs, `SUPERSEDES` projected from `superseded_by` and never stored) stores exactly **five** associative types: `CONTRADICTS`, `ELABORATES`, `DEPENDS_ON`, `FOLLOWS`, `RELATES_TO`. **`DERIVED_FROM` is cut for v1** — the reshape removed its only writer (knowledge left memory rows), and one provenance mechanism per layer is the rule: `fact_sources` for L2→sources, `article_citations` for L3→L2, projected `superseded_by` for supersession. Shipping a zero-writer edge type would violate invariant 23; if consolidation later grows a real derived-memory writer, reintroduce it then, taxonomy-first.

## 3. Code as a fact-originating knowledge base (point 6)

**The code graph is already incrementally maintained** (verified in `code_pipeline.py`: `phase_01_file_discovery` diffs `last_indexed_commit → HEAD`, rename-aware, per-file strip-before-rewrite, content-hash skip, dependent-caller re-trace cap 500; full wipe only on `--full`/first index). The work is **hardening the truth, not building incremental reindex**, plus a narrow fact-origination bridge. **No separate code-knowledge table** — the parsed `code_*` graph *is* the structural KB (a mirror = the two-drifting-stores disease).

### 3.1 Four truth-holes to close
- **T1 fail-stale, not fail-empty.** A pipeline exception currently runs `_delete_all_repo_data` (wipes the repo graph); a force-push makes the diff fail → wipe + permanent error loop. Fix: diff-failure falls back to a full index; the error path leaves the last-good graph in place and marks it stale.
- **T2 index-debt drain.** The 500-caller re-trace cap silently drops work. Persist `repositories.index_debt`; drain via continuation batches.
- **T3 a periodic `code_reconcile` job** hashing the working tree vs `code_files.content_hash`, feeding mismatches through the incremental path.
- **T4 summary carry-over** keyed on name/kind/owner/source-hash, so summaries are not wiped and re-billed on every file change.

### 3.2 Fact origination — narrow, deterministic, no LLM
A deriver mints, from **imports only** (v1): `repo → project` entity; external import modules (already `module` nodes) → `tool` / `database` / `language` via the existing `normalize_entity_type` + overrides; facts `repo —USES/DEPENDS_ON→ dep`, `repo —USES→ language` (~10–200 facts/repo, existing taxonomy). **Symbols, calls, communities, processes never originate facts** — symbol-level claims stay memory-asserted with commit-addressed code **citations** (evidence). The deriver upserts entities/relations at **Layer 1** (like a memory), tagged with a repo assertion array; consolidation lifts corroborated ones to Layer-2 facts, giving dedup anchoring (`postgres` from code == `postgres` from memory). Manifest parsing (versions, declared-unimported deps) is v2.

### 3.3 Invariant-8 amendment — lands INERT in the baseline
Add `entities.repo_ids uuid[]` + `entity_relations.repo_ids uuid[]` (+ GIN). Both orphan sweeps (`delete_by_memory_id`, `prune_orphan_entities`) gain one `NOT EXISTS (live repo)` predicate each; new `assert_from_repo` / `strip_repo_assertions` primitives (strip-before-rewrite per repo); dangling `repo_ids` self-heal exactly like dangling `memory_ids`. **This amendment lands in the v1 baseline inert** — empty `repo_ids` arrays make the amended sweeps byte-identical to today, so the load-bearing deletion-logic change is reviewed, tested, and frozen while it is riskless; the deriver job (its only writer) ships later (§8). Blast radius: 2 columns + 2 methods + tests. `technologies`, supersession, retrieval untouched. **Never-join reworded, not weakened:** no *query* joins the two graphs; the sanctioned crossings are two application-level one-direction components (the deriver projection, the citation re-verifier). "A symbol is not an entity" stands verbatim.

### 3.4 Code-fact lifecycle
Dependency removed → code source withdrawn → if sole source, **invalidate-not-delete** (`invalid_at` closes the window). Symbol deleted → its citation marked stale, the citing fact's badge downgraded and queued — never auto-expired. Unchanged at new HEAD → provenance no-op. Provenance: `fact_sources(kind='code', origin_key='repo_id', detail={commit_sha, basis, file_path, symbol_key})` — owner-qualified names + commit shas, never the churning bigint ids.

## 4. LLM configuration simplification (point 7)

**Keep the six purposes; drop the indirection.** darkmem is not an LLM proxy. Each purpose becomes an inline config row `{model, base_url, api_key, api_kind, params, dimensions?, reasoning?}`. **Drop `llm_providers`, `llm_profiles`, `ml_profiles`** and every `*_ref` column, plus the profile-management UI. The `classification` purpose carries an inline `classifier_kind = llm | local` choice — a lightweight local classifier stays as a fast/cheap no-LLM path at volume, re-homed inline rather than via `ml_profiles`. The stale `[ml]` pyproject comment is rewritten to the post-flattening truth ("when `[ml]` is absent, classification falls back to the LLM-backed classifier").

## 5. Pipeline LM-injection redesign (point 8)

**Call topology — one LLM touch per memory.** The merged extraction+classification call is the default and only LLM ingest path (one structured call returns entities + relations + `classified_type` + `summary` + enrichment fields). When the local classifier is enabled it runs out-of-band and the LLM call is extraction-only — never two LLM round-trips. Embeddings stay batched; reranking stays retrieval-side. **Prompt construction — one canonical schema + content + reproducibility seed + minimal rules;** strip the inline prompt rules the ~40 deterministic cleanup passes already enforce downstream (they are the moat and stay post-processing). This leaves a clean seam for the later area-detection pre-pass (the dynamic-taxonomy note, doc 06) to inject a domain-appropriate type vocabulary without touching the call topology.

## 6. Clear schema decisions

### 6.1 Generic audit — `events` replaces `audit_log` (point 3)
One universal append-only `events` substrate for **every** entity (memory, entity, relation, fact, article, topic, document, repository). **`audit_log` is dropped outright** (it does not exist in the greenfield baseline — no compatibility window; an optional one-time transform of old rows into `events` at the homelab cutover if the mapping is trivial). Append-only is enforced by a **BEFORE UPDATE OR DELETE OR TRUNCATE forbid-trigger** for v1 (role-agnostic, survives dump/restore, keeps the one-image surface simple); a `REVOKE`-based owner/app role split is recorded as the multi-user upgrade path.

### 6.2 UUIDv7 (point 4, id policy)
**UUIDv7 for every uuid PK the application generates** (memories, documents, blocks, articles, triples, fact_sources, buffer, repositories, article_citations) — v7's time-ordering gives B-tree insert locality; v4's randomness fragments indexes at scale, at zero extra cost, one generation rule. `entities` / `entity_relations` keep server-side `gen_random_uuid()` (v4) — they are ANN-probed and sweep-churned, not range-scanned, so locality buys nothing (switch to native `uuidv7()` only if the Postgres major is ≥ 18). `events` and the code-graph node/edge tables stay **bigint** (narrow key, never uuid-referenced).

### 6.3 Partitioning — targeted, `events` only (point 4, scale)
**Partition ONLY `events`: RANGE(created_at), monthly, from day one** (PK `(id, created_at)` — nothing joins events by id; retention = future `DETACH`; a small partition-maintenance arm on a cleanup job pre-creates next month). **Do NOT partition `memories`** — Postgres forces the partition key into every unique/PK constraint, so a range key would break the `superseded_by` self-FK, `memory_tags`, `memory_crossrefs`, the embedding-child FKs, and the composite `(id, project)` FK; UUIDv7 locality + the existing partial indexes are this table's scale mitigations. The per-fingerprint embedding child tables **are** the embedding partitioning (never partition inside a child — invariant 2). `knowledge_triples`/`fact_sources`/`documents`/`blocks`/`memory_buffer` stay single tables (live-subset partial indexes keep the hot set small; revisit only on measured size).

### 6.4 Drop the `llm_` prefix (point 5)
`llm_classified_type → classified_type`, `llm_summary → summary`, `llm_emotions → emotions`, `llm_flags → flags` — source-neutral, since the classifier may be the local model.

### 6.5 A minimal `projects` registry (Fable-advised change)
Create **`projects(name text PK, display_name, properties jsonb, created_at)`** in the baseline, with lazy auto-registration (`INSERT … ON CONFLICT DO NOTHING` on capture) and **no FK enforcement yet**. The reshape forces this now: `triple_key` embeds `project` in *fact identity*, so a typo'd project silently splits corroboration across two identities; the registry also anchors per-project `applies_when` defaults (§2.3), review-queue scoping, and one-active-article-per-subject. Every scoped table keeps its bare `project text` column (no FKs) — FK/ACL enforcement stays the later tenancy phase.

### 6.6 One baseline migration — freeze by event (point 9)
Collapse the Alembic chain to a **single baseline** that is regenerated freely (paired with drop/recreate) until the **first deploy whose data must survive** (the homelab production cutover); at that event tag it `0001` and every change after is a new linear revision forever. A **CI assertion** holds `alembic history` at exactly one revision until the freeze tag exists. The partition-parent creation sweep is **retired** and replaced by a **permanent boot-time reconciliation** in `embedder_registry`: at startup, iterate live `embedders` rows and run every template's `CREATE TABLE IF NOT EXISTS` + `CREATE INDEX IF NOT EXISTS` — idempotent, works identically pre/post-freeze, self-heals drift, replays mechanically in the deferred .NET port. This dissolves the sweep/baseline coexistence problem entirely.

## 7. What this amends in the foundation docs

- **Doc 01 (domain model):** reverse §3.4/§9 (knowledge-as-derived-rows); add the four-layer ladder, the verification states + honest badge, the context model, the review queue, and code-as-fact-source; `insight`/`profile` move out of `MEMORY_TYPES`-as-knowledge (`episodic`/`procedural` stay as memory kinds); memory-level `CONTRADICTS` is a signal into fact-level dispute.
- **Doc 03 (stack):** §5.5/§5.6/§5.13 LLM-config flattening (drop indirection tables, inline `classifier_kind`); the merged-call injection topology; UUIDv7 policy in §3.4/§5.2; pin numpy and the mechanical floor-bump cadence (§7); the `events`/`audit_log` replacement; the stale-`[ml]`-comment fix.
- **Doc 04 (schema):** `knowledge_articles` + `article_citations` + `article_embeddings` partition (a **fourth** per-fingerprint family — amend §5.3's "exactly three"); the `triple_embeddings` template (writer deferred, §9); `fact_sources`; `verification_status` (+ CHECK) / aggregated `confidence` / `applies_when` / `learned_in` on the fact layer; `memory_relations` five-type vocabulary (`DERIVED_FROM` cut); review-queue state; `entities.repo_ids` + `entity_relations.repo_ids` + the inert invariant-8 sweep amendment; the four code truth-hole fixes; generic `events` replacing `audit_log` (monthly RANGE, forbid-trigger); UUIDv7 policy + `events`-only partitioning; drop the `llm_` prefix; drop `llm_providers`/`llm_profiles`/`ml_profiles`; the `projects` registry; single baseline + boot-time reconciliation. Keep the honest framing: the fact layer is the §8.3 *rebuild extended*, never an activation of the dormant scaffolding (invariant 23).

## 8. Sequencing

1. **Code-KB truth hardening (T1/T2/T3/T4)** ships first — independent, pure truth-hardening of an existing subsystem.
2. **The invariant-8 amendment** (`repo_ids[]` + sweep predicates) lands in the v1 baseline **inert** (byte-identical without a writer — reviewed and frozen while riskless).
3. **Layer 2** (verified facts + verification ladder + `fact_sources` + review queue + the `projects` registry + the memories `origin_key`) ships next — the truth core.
4. **The code deriver job** ships after L2 is proven live (its born-`corroborated` facts need a working ladder).
5. **Layer 3** (articles + `article_citations` + `article_embeddings`) ships last, gated behind the claim-level groundedness metric.

Partition templates (`article_embeddings`, `relation_embeddings`, `triple_embeddings`) are added to `_TABLE_TEMPLATES` up front (near-free with boot-time reconciliation); the `triple_embeddings` **writer** is deferred behind a measured undercount of the `pg_trgm`-on-`fact` candidate set, and when it ships it groups facts **for counting only, never merges rows or rewrites `triple_key`**, carrying the `names_distinct` guard.

## 9. Open questions — Fable-advised stances (point 10)

Every open question in doc 03 §7 and doc 04 §13, plus the reshape-new ones, was advised through the performance/correctness/stability/truth lens. Resolved stances:

- **numpy pin** — adopt; pin tracking the lock. **Floor-bump cadence** — mechanical, every `--universal` lock regen bumps direct-dep floors to the last-tested minor. **nginx-in-image trigger** — keep app-as-edge; reshape adds no pressure. **`[ml]` comment** — fix, folded into the LLM flattening. **psutil/pynvml matrix gap** — doc-19 pickup.
- **`memory_relations` form** — own table + composite `(id, project)` FKs + projected `SUPERSEDES`; five stored types. **Topics** — materialise (needed to diff pin-suggestions). **PPR** — single-worker in-process for v1. **`entities` tenancy key** — later phase (vault isolation rides the fact layer; code deriver benefits from global entities). **Block↔memory provenance** — on the derived row; fact side answered by `fact_sources(kind='block')`. **Retrieval trace** — transient (verification transitions journaled to `events` cover the audit need).
- **Articles** — materialise + `article_citations` + hard FK to facts (§2.4). **Corroboration** — N=2 with the diversity/time gate, merge-on-unknown, honest badge (§2.1). **`DERIVED_FROM`** — cut for v1 (§2.8). **`applies_when` retrieval** — context by declaration, boost/label/conflict-count (§2.3). **UUIDv7 + partitioning** — v7 all app PKs, partition only `events` (§6.2/§6.3). **`events`** — drop `audit_log` outright, forbid-trigger, monthly RANGE (§6.1/§6.3). **Baseline** — freeze-by-event + boot-time reconciliation (§6.6). **Code sequencing** — three-way split (§8). **`triple_embeddings`** — template now, writer measured (§8).

**Highest-stakes calls (Fable):** (1) origin-key capture + merge-on-unknown + the honest badge — the line between a truth system and a popularity counter; (2) enforced claim-level grounding + one provenance mechanism per layer; (3) freeze-by-event + boot-time reconciliation — removes the "production DB no migration can reach" failure class; (4) landing the orphan-sweep amendment inert in the baseline while it is riskless.

---

*Downstream: this spec directs the revision of docs 01, 03, and 04, and is the reference for the ERD (`erd.md`). The subsystem docs 06–11 inherit its mechanics (06 extraction + the dynamic-taxonomy pre-pass; 07 retrieval + the four-layer composition + `applies_when` matching; 08 temporal + the verification ladder; 09 knowledge synthesis + articles + grounding; 10 code-KB hardening + fact origination; 11 LLM orchestration flattening).*
