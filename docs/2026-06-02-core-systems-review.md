# Darkmem — Memory & Code-Analysis Cores: Accuracy / Reliability / Efficiency Review

**Date:** 2026-06-02 · **Branch:** fix/eval-p0-2026-06-02 (post-hardening) · **Axes:** accuracy, reliability, efficiency

**Method.** Deep per-component review of the two algorithmic cores, each finding adversarially
re-verified against the current code (and the actual SQL / index definitions). The single
highest-stakes finding — that class methods are never extracted — was additionally confirmed by
running the parser directly. Efficiency was reviewed with explicit complexity / round-trip /
index-usage analysis, which the earlier app-wide review under-covered.

**Headline.** The memory pipeline is in good shape — prior hardening is visible and most of what
remains is efficiency tuning plus a few accuracy edges. The **code-analysis system has one
blocker that hollows out its entire structured graph**: class methods (and anything nested under
a class body) are never extracted as symbols, so the call graph, heritage/MRO, blast-radius,
rename, and the `code_symbol`/`code_context` tools are all empty of methods for object-oriented
code. Semantic code search still works at class-chunk granularity (method bodies live in the
class chunk), so the gap is in the *structured* features, not free-text search.

> Verified directly: `parse_file` on a Python class returns the class with `children == []`;
> `bar`/`baz` methods never appear in symbols. The same first-nesting-level drop applies to TS/JS
> (`class_body`/`statement_block`) and other body-wrapped grammars.

---

## Cross-cutting themes

### 1. The structured code graph is hollow for OO code  *(blocker)*
`_extract_symbol` scans only a node's **direct** children for nested symbols, but tree-sitter
nests methods under a `block`/`class_body`/`declaration_list`. So `code_symbols` holds only
top-level classes and free functions — **zero methods**. Everything keyed on methods degrades:
`lookup_by_owner`, heritage override/inherited detection, method `calls` edges, `code_blast_radius`,
`code_rename`, `code_context`, `code_file_symbols`, and chunk-level method granularity. Several
other code findings are "latent until methods exist." This is the root cause to fix first.

### 2. The code pipeline recomputes whole-repo work every run
Files are tree-sitter-parsed up to **3×** per run (phase 02, 06, 07) — and the 06/07 parses run
**synchronously on the event loop**, stalling the async server. The full symbol table is loaded
**twice** (phases 06 and 08) and its derived indexes rebuilt byte-for-byte. On incremental runs the
cost still scales with *total repo size*, not the change set. This is the dominant avoidable cost.

### 3. The ANN index is bypassed on the ingest hot path
`find_similar_memories` (run on **every** ingest for crossrefs) self-joins the partition with
`ORDER BY me1.embedding <=> me2.embedding` — a column-vs-column operand the HNSW index cannot serve,
so it sequentially scans the whole partition per ingest: O(N) per write, **O(N²) to build a corpus**.
The sibling `find_similar` does it right (fetch the vector, then order by `<=> :literal`). This is
the one place the otherwise-correct fingerprint partitioning is defeated.

### 4. Per-write graph maintenance is full-table
`delete_by_memory_id` runs on **every** memory write and issues two **unscoped full-table** sweeps
(`array_length(memory_ids,1) IS NULL` is non-sargable), and there is **no index on
`entity_relations.target_entity_id`**, so the neighbor query, `get_relations_between`, and the
orphan-guard `EXISTS` all fall to sequential scans that grow with the graph.

### 5. N+1 and per-call round-trips pervade the code tools and import resolvers
Import resolvers (`build_import_map` relative branch, JVM/Go resolvers, the per-resolver
`frozenset(file_paths)`) scan **all file paths per import**; `code_context` fires **7 serial**
queries; `code_processes` is **N+1** over processes; wiki generation is **N+1** symbol queries plus
**serial** per-module LLM calls. Each query is index-cheap — the cost is round-trip count and
serialized latency.

### 6. Several ranking/heuristic signals silently no-op
Each of these is computed but inert, so the feature looks tuned while doing nothing: the phase-08
skip heuristic divides mismatched populations (skips every incremental run); the process-trace
framework-decorator boost reads a `signature` property that's never written; the 0.90 named-import
tier keys on raw module strings `lookup_local` can never match; `search_code`'s keyword pass has no
`ORDER BY` so its RRF ranks are heap order; confidence weighting sits at the neutral default for most
rows; the reranker's max-normalization discards the absolute "no good match" signal.

---

## Prioritized roadmap

### P0 — code-graph correctness (broad blast radius)
| # | Fix | Component | Effort |
|---|-----|-----------|--------|
| 1 | **Extract class methods** — unwrap body nodes (`block`/`class_body`/…) in `_extract_symbol` (reuse `_find_docstring`'s unwrap) | code parsing | medium |
| 2 | Wire inherited-method resolution into call tracing (`find_inherited_method` is dead code; use the in-memory `parent_map`/`method_map`) | call/heritage | medium |
| 3 | Qualify method symbol keys by owner class (`Owner::name::file_path`) to stop same-name method collisions | call/heritage | large |
| 4 | Fix phase-08 skip heuristic: compare resolved-vs-resolvable on the **same** file set (it currently skips every incremental run) | code pipeline | medium |

### P0 — hot-path efficiency (scales with corpus/repo)
| # | Fix | Component | Effort |
|---|-----|-----------|--------|
| 5 | `find_similar_memories`: fetch the source vector then ANN-search with `<=> :literal` (kill the O(N²) crossref scan) | vector/ingest | small |
| 6 | `delete_by_memory_id`: scope sweeps to touched rows (`RETURNING` the affected ids) **and** add `ix_entity_relations_target` | graph | small/med |
| 7 | Code pipeline: build type-envs + symbol table **once** and reuse across phases 06/07/08; offload the parses to an executor | code pipeline | medium |

### P1 — accuracy
| # | Fix | Component |
|---|-----|-----------|
| 8 | ANN entity dedup must respect `entity_type` (`canonical_map` keyed by `(name,type)`) | graph |
| 9 | Extraction: key final dedup on `(source,target,family_key)` not target-only; validate direction per-relation via `finditer` | extraction |
| 10 | `plainto_tsquery` → `websearch_to_tsquery` for keyword recall | retrieval |
| 11 | Over-fetch by filter selectivity, or push equality/overlap filters into the semantic/keyword SQL before LIMIT | retrieval |
| 12 | `search_code`: order the keyword pass before ranking; reconcile the two fusion keys; index `source_code` (pg_trgm) or route through the semantic-only path | code query |
| 13 | `_delete_file_data`: also delete orphaned `route`/`tool` graph nodes (phantom routes/processes accumulate) | code pipeline |
| 14 | `param_count`: structural param parse (top-level commas) + normalize the `self`/`this` receiver convention vs `arg_count` | call/heritage |
| 15 | `_fetch_entity_overlay`: push the `memory_ids && :plotted` filter into SQL (GIN-indexed); drop the unordered `LIMIT 500` | graph |
| 16 | Negation window: cover the cues the prompt teaches (`no longer`, `rather than`, `rejected`…) so rescue doesn't re-add negated entities | extraction |

### P1 — efficiency
| # | Fix | Component |
|---|-----|-----------|
| 17 | Reranker: cap candidates to ~`2·limit`, raise/￼config the concurrency, prefer one batched scoring call (it runs ~70 LLM calls at concurrency 3) | retrieval |
| 18 | Import resolvers: precompute one suffix/normalized-path map per repo (kill the O(files) scan per import in `build_import_map`, JVM/Go); build `file_set` once | imports |
| 19 | Code tools: combine `code_context`'s 7 queries into one edge query + `gather`; batch `code_processes`'s per-process step lookup; wiki single symbol query + concurrent module LLM | code query / pipeline |
| 20 | Classifier resolution: skip when `llm_enrichment_enabled` is off (2 wasted round-trips per ingest); batch Phase-5 entity/relation writes | ingestion |

### P1 — reliability
| # | Fix | Component |
|---|-----|-----------|
| 21 | Decouple the vector upsert from the graph savepoint so a graph-write failure doesn't discard the (successful) vector | ingestion |
| 22 | Phase-13 enrichment: scope the pending-symbol select by `repo_id` and bound it (currently cross-repo and silently caps at 1000) | code pipeline |
| 23 | Compute crossrefs in one phase after the whole batch commits (fixes the order-dependent intra-batch sibling-link loss) | ingestion |

---

## Findings by component (verified)

Axis legend: **A**ccuracy · **R**eliability · **E**fficiency. Severities are post-verification.

### Memory system

**Ingestion pipeline** — *solid: phased checkpoints, partition discipline, idempotent re-extraction, bounded concurrency.*
| Finding | Axis | Sev |
|---|---|---|
| Crossref `find_similar_memories` self-join can't use HNSW → O(N) scan per ingest, O(N²) to build a corpus | E | high |
| Classifier resolution (2 DB round-trips) runs every ingest even when enrichment is off | E | med |
| Phase-5 writes are N+1 (no bulk `create_entities`/`create_relationships`) | E | med |
| Intra-batch crossrefs race on commit order → order-dependent lost sibling links | A | med |
| Graph savepoint rolls back the already-successful vector upsert on any graph-write failure | R | med |
| Dedup canonical map can rewrite to a different-type homonym | A | low |
| `regex_classify`/`estimate_confidence` run inside the write session | E | low |
| Websocket event type derived separately from the persisted failure step (latent drift) | R | low |

**Extraction / rescue / dedup** — *solid: JSON salvage, seed reproducibility, constrained rescue layers.*
| Finding | Axis | Sev |
|---|---|---|
| Final dedup keys on `(target,predicate)` only → drops legitimately distinct multi-subject edges | A | high |
| `_validate_directions` uses the first pattern match for every relation of a type → cross-clause contamination | A | med |
| Negation window narrower than the prompt's cues → rescue re-adds negated entities | A | med |
| Rescue recompiles per-entity patterns and re-scans spans across three passes (bounded by 60-char break + 6k cap) | E | low |
| `_dedup_by_target_predicate` keys on raw type, not `family_key` (subsumed by the dedup-key fix) | A | low |
| `_salvage_json_object` returns the first balanced object, not necessarily the extraction object | R | low |

**Entity graph / ANN dedup / supersession** — *solid: memory_ids append, orphan-safe delete, all six supersession gates.*
| Finding | Axis | Sev |
|---|---|---|
| No index on `entity_relations.target_entity_id` → seq scans on neighbor/relations/orphan-guard, on every write | E | high |
| `delete_by_memory_id` runs two unscoped full-table sweeps per memory write | E | high |
| ANN dedup ignores `entity_type` → cross-type canonical collapse | A | med |
| `_fetch_entity_overlay` uses an unordered `LIMIT 500` decoupled from request limit → can drop plotted entities | A | med |
| `get_neighbors_by_name` resolves by name only → arbitrary same-name entity, partial subgraph | A | low |
| `create_entity` shallow `jsonb ||` clobbers nested props (latent; display_name-only today) | A | low |
| Phase-4 dedup opens one session per unique name | E | low |
| Speculative gate uses substring target match + bare modal markers | A | low |

**Retrieval (hybrid / RRF / reranker / confidence)** — *solid: id normalization, fail-loud on dual failure, `ef_search=100`+`iterative_scan`, rank order preserved.*
| Finding | Axis | Sev |
|---|---|---|
| Reranker fires one LLM call per fused doc (~70) at concurrency 3 → multi-second latency | E | high |
| `plainto_tsquery` AND-joins all terms → keyword recall collapses on multi-word queries | A | med |
| Over-fetch uses a fixed `+50` slack → selective in-memory filters silently under-return a page | A | med |
| Reranker max-normalization discards absolute relevance; reported score ≠ imposed order | A | low |
| Confidence weighting: extra round-trip + near-neutral coverage when `gamma>0` | E/A | low |
| `search_code` ignores `semantic_weight` and swallows exceptions into `[]` | R | low |
| *(Dropped: RRF "math wrong" and `ef_search` default — refuted by the code.)* | — | — |

**Embedders / partitioning / vector ops** — *solid: partition guards, slug-collision reject, dimension guard, vectorized sparse edges, Louvain sample-cap.*
| Finding | Axis | Sev |
|---|---|---|
| `find_similar_memories` literal-vector rewrite (same root as ingestion crossref) | E | high |
| Reembed anti-join re-runs per 100-row batch (index-backed; operator-triggered) | E | low |
| `_count_missing_code_chunks` DISTINCT-over-UNION-ALL on the poll-reachable counts endpoint | E | low |
| `find_similar` over-fetches then post-filters threshold in Python | E | low |
| Slug-collision scan refetches all other fingerprints; the lock is per-process only | E | low |
| `reembed_code_chunks` reports the missing count through the `errors` channel | R | low |

### Code-analysis system

**Code parsing / symbol table / type env**
| Finding | Axis | Sev |
|---|---|---|
| **Class methods (and body-nested symbols) are never extracted — symbol table has zero methods** | A | **blocker** |
| Function-scoped type bindings never consulted (callers use `scope="file"`) — latent on the methods fix | A | med |
| `self`/`this` typing structurally unreachable (string-slice from a `file` scope) — latent | A | med |
| Phases 06/07 re-parse every file from scratch (tree discarded by `parse_file`) | E | high |
| `lookup_by_owner` co-location fallback can scan the whole symbol table per ambiguous call | E | med |
| `propagate_types` cyclic-import fallback is non-deterministic and bounded to 2 hops | A | low |
| Constructor/typed-assignment extraction is Python-only; misses TS/Java receivers | A | low |
| `dialect.encode_entity` collides on 3-letter prefixes; re-lowers text per entity | A | low |

**Import resolution / named bindings / suffix index**
| Finding | Axis | Sev |
|---|---|---|
| `build_import_map` relative branch is O(files) per ext per import — and mostly fails to match (bad tail) | E | high |
| JVM/Go resolvers scan all file paths per import with no index | E | high |
| `build_named_imports` keys the 0.90 tier on raw module strings `lookup_local` can't match → tier no-ops | A | med |
| Per-resolver `frozenset(file_paths)` rebuilt on every unresolved import | E | med |
| Python bare-import proximity walk can bind the wrong same-named module | A | low |
| Binding-chain resolution: redundant one-hop peek, no memo | A | low |
| `CallResolver.resolve` re-filters the global candidate list multiple times; `resolve_chain` linear id scan | E | low |
| *(Dropped: SuffixIndex "ambiguous bucket shadowing" and "regex redundant with parser" — both misreads.)* | — | — |

**Call resolution / heritage / MRO**
| Finding | Axis | Sev |
|---|---|---|
| Inherited-method calls produce no edge (`find_inherited_method` is dead code) | A | high |
| Method symbol keys `name::file_path` collide for same-named methods in one file | A | high |
| `param_count` from bracket-naive signature stripping + receiver-convention mismatch → arity disambiguation misleading | A | med |
| Phases 06/08 rebuild the full symbol table twice | E | med |
| `resolve` cache key omits `call_form`/`arg_count` | A | low |
| `resolve_chain` linear id lookup; no by-id index | E | low |
| Interface default methods (Java/Kotlin/C#) excluded from the inheritance MRO | A | low |

**Code pipeline / communities / processes / wiki**
| Finding | Axis | Sev |
|---|---|---|
| Phase-08 skip heuristic divides mismatched populations → skips every incremental run; `unresolved_count` dead | A | high |
| Phases 06/07 re-parse the whole repo (synchronously on the event loop) | E | high |
| Phases 06/08 reload the entire symbol table twice | E | med |
| `_delete_file_data` leaks route/tool graph nodes → phantom routes/processes accumulate | R/A | med |
| Process-trace framework-decorator boost reads a `signature` property never written | A | med |
| Phase-13 enrichment is cross-repo and silently caps at 1000 symbols | R | med |
| Wiki: N+1 symbol queries + serial per-module LLM calls, inline in the indexing run | E | med |
| Per-file chunk deletes fan out across every fingerprint (index seeks; round-trip count) | E | low |
| Process tracer subset dedup is O(processes²); redundant endpoint guard | E | low |

**Code query / blast radius / code search** — *solid: keyspace consistent, `code_edges` well-indexed (incl. covering index), tools commit/rollback-wrapped.*
| Finding | Axis | Sev |
|---|---|---|
| `search_code` keyword pass has no `ORDER BY` → RRF ranks are heap order | A | high |
| Two RRF passes use mismatched fusion keys (chunk vs symbol `line_start`) → agreement never fuses | A | med |
| `code_context` issues ~7 sequential round-trips per call | E | med |
| Blast-radius CTE uses `UNION` with no visited-set guard → cyclic graphs re-expand to the depth cap | E | med |
| `code_processes` is N+1 over processes | E | med |
| `code_blast_radius`/`code_context` pick an arbitrary same-named symbol (non-deterministic, understates radius) | A | med |
| Blast radius conflates heritage/access edges with call impact in the risk tier | A | low |
| `CodeQueryService.search_code` diverges from the semantic-only contract; `source_code` ILIKE is a leading-wildcard full scan | R/E | low |

---

## What's solid (verified, no action)
Memory: fingerprint partitioning end-to-end; idempotent re-extraction with orphan-safe relation
preservation; all six supersession gates incl. strict-older and clause-scoped speculative; id
str/UUID normalization at every boundary; fail-loud on dual search failure; `ef_search=100` +
`iterative_scan=relaxed_order`; batched cache/crossref upserts; the JSON-salvage path. Code:
grammar load/negative-cache + line-based fallback; `code_edges` four-index coverage incl. the
covering index; consistent `compose_key` keyspace; idempotent edge writes; vectorized sparse-edge
build and Leiden sample-cap/timeout; incremental dependent re-trace cap; chunk partitions indexed
on `(repo_id, file_path)`.

## Method note
This review reads code, the contract, the SQL, and the migration indexes; the methods-not-extracted
blocker was confirmed by executing `parse_file`. Runtime-only magnitudes (real latencies, planner
choices under load) would need a live profile. Findings were adversarially re-verified; several
draft claims were dropped as misreads (RRF math, `ef_search` default, SuffixIndex shadowing,
named-binding/parser redundancy, a missing `code_edges` index). Full per-component prose lives in
`scripts/eval_cores_reports.md`.
