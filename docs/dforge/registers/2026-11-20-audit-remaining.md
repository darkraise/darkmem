# Audit remaining items

**Source:** the open findings of `docs/2026-11-20-codebase-audit.md` and its eleven track files under `docs/2026-11-20-codebase-audit/`, the deferred rows of the three graph registers, and the embedder incident's follow-ups; the owner asked on 2026-11-20 to "resolve all remaining items". Findings the audit pass already fixed or removed (its sections 2 and 3) are not listed.
**Covers:** docs/dforge/specs/2026-11-20-audit-remaining-design.md

| # | Item | Assigned | Acceptance | State | Note |
|---|---|---|---|---|---|
| 1 | B1-1 remainder: split transient from deterministic extraction failures and make transient ones a hard step the buffer retries | docs/dforge/plans/2026-11-20-audit-remaining.md | test: Task 8 contracts | done | af32cc0 |
| 2 | B1-3: Phase 5 sessions upsert shared entity and relation rows in extraction order and hold the locks until commit (deadlock class) | docs/dforge/plans/2026-11-20-audit-remaining.md | A16 (Task 7) | done | 9e0f324 |
| 3 | B1-4: the supersession UPDATE has no status='active' predicate, so two concurrent writers re-point an already-superseded memory | docs/dforge/plans/2026-11-20-audit-remaining.md | A15 (Task 7) | done | 9e0f324 |
| 4 | B1-5: predicates written as :mid = ANY(memory_ids) cannot use the GIN index | docs/dforge/plans/2026-11-20-audit-remaining.md | A17 (Task 7) | done | 9e0f324 |
| 5 | B1-6: at its 10-second deadline wait_process cancels the in-flight flush, leaving the row claimed and discarding the LLM spend | docs/dforge/plans/2026-11-20-audit-remaining.md | A18 (Task 9) | done | 91d1bd5 |
| 6 | B1-7: the reprocess and pipeline-failure retry routes are not refused in read-only mode | docs/dforge/plans/2026-11-20-audit-remaining.md | A12 (Task 5) | done | 7d6e56b |
| 7 | B1-8: if the same-batch reconciliation raises, the backstop overwrites every already-committed status with vector and graph errors | docs/dforge/plans/2026-11-20-audit-remaining.md | test: Task 8 contracts | done | af32cc0 |
| 8 | B1-9: wait_process returns 201 with an unprocessed memory for a capture whose replay hard-failed | docs/dforge/plans/2026-11-20-audit-remaining.md | A18 (Task 9) | done | 91d1bd5 |
| 9 | B1-10: discarding an error buffer row leaves its already-materialized memory live with no vector or graph | docs/dforge/plans/2026-11-20-audit-remaining.md | A55 (Task 10/12) | done | e2dd580e, 0b3974ea |
| 10 | B1-11: the retry/reprocess entry dict is built in three places, and two of them omit project | docs/dforge/plans/2026-11-20-audit-remaining.md | test: Task 13 contracts | done | ea77b0f |
| 11 | B1-12: pipeline._get_feature_flags duplicates feature_flags.get_feature_flags_dict | docs/dforge/plans/2026-11-20-audit-remaining.md | test: Task 13 contracts | done | ea77b0f |
| 12 | B1-13: a caller-supplied importance is always overwritten by the extractor's value | docs/dforge/plans/2026-11-20-audit-remaining.md | test: Task 13 contracts | done | ea77b0f |
| 13 | B1-15: classifier_kind=local silently falls back to the LLM classifier in every shipped image; stale pyproject comment (owner ruling 2026-11-20: keep it, fail loudly) | docs/dforge/plans/2026-11-20-audit-remaining.md | A19 (Task 11/12) | done | cfa97c45, 0b3974ea |
| 14 | B1-18: the isinstance(extraction, Exception) branch and the except in run_extract cannot be reached | docs/dforge/plans/2026-11-20-audit-remaining.md | test: Task 8 contracts | done | af32cc0 |
| 15 | B1-19: a 116-name __all__ plus a star re-export exist only so tests and scripts can import private pass helpers | docs/dforge/plans/2026-11-20-audit-remaining.md | test: Task 13 contracts | done | ea77b0f |
| 16 | B1-20: EXTRACTION_SCHEMA is used by one eval script only | docs/dforge/plans/2026-11-20-audit-remaining.md | test: Task 13 contracts | done | ea77b0f |
| 17 | B1-21: _MAX_CONTENT_CHARS = 6000 is declared twice and is also reused as the reasoning context budget | docs/dforge/plans/2026-11-20-audit-remaining.md | test: Task 13 contracts | done | ea77b0f |
| 18 | B1-22: buffer_wait_timeout_seconds is a flag the API cannot set and nothing bounds | docs/dforge/plans/2026-11-20-audit-remaining.md | test: Task 9 contracts | done | 91d1bd5 |
| 19 | B2-2: chat and knowledge_search ignore hybrid_search_enabled and reranker_enabled, and no memory row carries confidence/importance | docs/dforge/plans/2026-11-20-audit-remaining.md | A13 (Task 6) | done | d9337ef |
| 20 | B2-4: no door passes a declared context, so w_context_boost never fires and community_injection_enabled has no reader (owner ruling 2026-11-20: remove) | docs/dforge/plans/2026-11-20-audit-remaining.md | A45 (Task 43/45) | done | b5db5ee |
| 21 | B2-6: chat leaves a transaction open, holding a pooled connection for the whole LLM stream | docs/dforge/plans/2026-11-20-audit-remaining.md | test: Task 14 contracts | done | 05e7497 |
| 22 | B2-7: on client disconnect the finally usage write is cancelled, so the row is lost | docs/dforge/plans/2026-11-20-audit-remaining.md | test: Task 14 contracts | done | 05e7497 |
| 23 | B2-8 and B3b-21: every project-scoped composed search embeds the query twice | docs/dforge/plans/2026-11-20-audit-remaining.md | test: Task 15 contracts | done | 3c69d90 |
| 24 | B2-9: a full provisional compose pass runs on every request to feed a reranker no production caller passes | docs/dforge/plans/2026-11-20-audit-remaining.md | test: Task 15 contracts | done | 3c69d90 |
| 25 | B2-11: watch_refresh, fill and inject_block are reached only by tests, so the Distribution tab's token budget, watch switch and curb steer nothing (owner ruling 2026-11-20: remove) | docs/dforge/plans/2026-11-20-audit-remaining.md | A44 (Task 44/45) | done | b5db5ee |
| 26 | B2-12 and B3a-5: triple_embeddings.py has no production caller, yet every embedder registration creates an empty table and index (owner ruling 2026-11-20: remove and drop) | docs/dforge/plans/2026-11-20-audit-remaining.md | A46 (Task 46) | done | b9e6723; A46 on the 2026-11-21 03:30 backup restored to the dev Postgres: stamp 0003 to head 0006, blocks 4 before and 4 after, triple_embeddings__qwen3_embedding_0_6b_1024 (0 rows) dropped, no table kept |
| 27 | B2-13: useVectorProjection has no consumer, and the route runs eigh inline on the event loop | docs/dforge/plans/2026-11-20-audit-remaining.md | test: Task 17/45 contracts | done | b5db5ee |
| 28 | B2-14: RRF is implemented again inline twice in code_query, whose arms lack savepoints and swallow failures | docs/dforge/plans/2026-11-20-audit-remaining.md | test: Task 16 contracts | done | 206716a |
| 29 | B2-15: graph path ids typed as str reach CAST AS uuid; an uppercase UUID lists the seed as its own neighbour; the 20 neighbours are an arbitrary slice | docs/dforge/plans/2026-11-20-audit-remaining.md | test: Task 16 contracts | done | 206716a |
| 30 | B2-16: FactsChannel.search is tests-only, the row-level dispute block is superseded, and the docstring is stale | docs/dforge/plans/2026-11-20-audit-remaining.md | test: Task 15 contracts | done | 3c69d90 |
| 31 | B2-17: search and search_with_trace duplicate the whole pipeline | docs/dforge/plans/2026-11-20-audit-remaining.md | test: Task 15 contracts | done | 3c69d90 |
| 32 | B2-18: flag_measurements is read but nothing writes it, so every flag shows unmeasured forever | docs/dforge/plans/2026-11-20-audit-remaining.md | test: Task 17/45 contracts | done | b5db5ee |
| 33 | B2-19: chat content has no length limit, and an untyped context with a non-string mention raises mid-stream | docs/dforge/plans/2026-11-20-audit-remaining.md | test: Task 14 contracts | done | 05e7497 |
| 34 | B2-20: CLUSTER_RE is unused, and the cluster: filter can never match | docs/dforge/plans/2026-11-20-audit-remaining.md | test: Task 14 contracts | done | 05e7497 |
| 35 | B2-21: with hybrid search off, the pure-vector and read-only branches never call _record_access | docs/dforge/plans/2026-11-20-audit-remaining.md | test: Task 6 contracts | done | d9337ef |
| 36 | B2-22: the hand-maintained route inventory trips on every new route or tool (owner decision) | - | - | deferred | declined in the spec: the inventory is the enumeration guard; moving it onto route metadata is its own design |
| 37 | B3a-1 (high): fact_lift and re-extraction can interleave so a fact keeps a source the memory no longer asserts; needs a two-session test | docs/dforge/plans/2026-11-20-audit-remaining.md | A1 (Task 18) | done | 635ebff |
| 38 | B3a-2 and B3b-11: while the judge refuses, the contradiction scan re-drains the same 20 events every 6 hours and re-commits duplicate clean verdicts | docs/dforge/plans/2026-11-20-audit-remaining.md | A24 (Task 19) | done | f5f8bdbe |
| 39 | B3a-3: the slow arm re-journals an identical blocked hold on every visit | docs/dforge/plans/2026-11-20-audit-remaining.md | test: Task 19 contracts | done | f5f8bdbe |
| 40 | B3a-4: knowledge_triples.stated_expiry has no production writer, so the every-2-minute close arm, its partial index and the merge's LEAST logic are dead (owner ruling 2026-11-20: remove and drop) | docs/dforge/plans/2026-11-20-audit-remaining.md | A47 (Task 47) | done | 043f7d6 |
| 41 | B3a-6: Tier-C ticks hold fact row locks until the tick commits, so withdrawal and memory delete block with no lock timeout | docs/dforge/plans/2026-11-20-audit-remaining.md | test: Task 20 contracts | done | 0bb607fd |
| 42 | B3a-7: no index on events serves the sources_changed drain, and an idle drain never advances the watermark | docs/dforge/plans/2026-11-20-audit-remaining.md | test: Task 20 contracts | done | 0bb607fd |
| 43 | B3a-8: joining on CAST(m.id AS text) = fs.source_ref defeats the memories primary key | docs/dforge/plans/2026-11-20-audit-remaining.md | test: Task 20 contracts | done | 0bb607fd |
| 44 | B3a-9: every 15-minute tick re-reads all code provenance and repo assertions even when no repository changed | docs/dforge/plans/2026-11-20-audit-remaining.md | test: Task 20 contracts | done | 0bb607fd |
| 45 | B3a-10: recompute_fact reads three config rows per fact rather than once per tick | docs/dforge/plans/2026-11-20-audit-remaining.md | test: Task 20 contracts | done | 0bb607fd |
| 46 | B3a-11 and B3a-D4: the promotion record JSON is opened and parsed from disk for every corroborated row served | docs/dforge/plans/2026-11-20-audit-remaining.md | test: Task 20 contracts | done | 0bb607fd |
| 47 | B3a-12: the suspicion marker columns are written onto confirmed facts | docs/dforge/plans/2026-11-20-audit-remaining.md | test: Task 19 contracts | done | f5f8bdbe |
| 48 | B3a-13: get_fact queries the latest verified event twice | docs/dforge/plans/2026-11-20-audit-remaining.md | test: Task 20 contracts | done | 0bb607fd |
| 49 | B3a-14: count_distinct_origins, facts_for_source and OriginProfile.required_origin_count are referenced only by tests and prose | docs/dforge/plans/2026-11-20-audit-remaining.md | test: Task 20 contracts | done | 0bb607fd |
| 50 | B3a-15 and B3a-16: stale prose and comments in verification_recompute, contradiction_scan, verification_judge, knowledge_triples and verification_ladder | docs/dforge/plans/2026-11-20-audit-remaining.md | test: Task 19 contracts | done | f5f8bdbe |
| 51 | B3a-17: the dismissal journal payload stores note untruncated | docs/dforge/plans/2026-11-20-audit-remaining.md | test: Task 19 contracts | done | f5f8bdbe |
| 52 | B3a-18: the merge fold moves sources onto the keeper fact without emitting sources_changed | docs/dforge/plans/2026-11-20-audit-remaining.md | test: Task 18 contracts | done | 635ebff |
| 53 | B3a-19: _FACTS_ON_LOSER filters on subject_id/object_id, which have no index (add if merge volume grows) | - | - | deferred | declined in the spec: the reviewer's own condition (merge volume grows) does not hold |
| 54 | B3b-2: annotate_undoability rebuilds the payload without pass_key, so the digest shows the wrong undoable state | docs/dforge/plans/2026-11-20-audit-remaining.md | A21 (Task 22) | done | b17e7fb |
| 55 | B3b-3: no distinct or duplicate verdict is remembered, so the same top-scoring pairs are re-judged every rotation and later pairs starve | docs/dforge/plans/2026-11-20-audit-remaining.md | test: Task 23 contracts | done | e352460 |
| 56 | B3b-4, B3b-R2 and B3b-R5: refine replaces caller-supplied tags (including project/ tags) with the model's list, with no length validation | docs/dforge/plans/2026-11-20-audit-remaining.md | A20 (Task 21) | done | bb80816 |
| 57 | B3b-5: CLAUDE.md says groundedness_gate stays closed, but the article surfaces gate on article_claim_gate; stale docstring | docs/dforge/plans/2026-11-20-audit-remaining.md | test: Task 25 contracts | done | 628ee76 |
| 58 | B3b-6: article gather, hash and staleness key on the subject name only while eligibility keys on name and entity_type | docs/dforge/plans/2026-11-20-audit-remaining.md | A23 (Task 24) | done | 0b1ab1a |
| 59 | B3b-7: pinned subjects with zero facts fill synthesis_budget on every tick | docs/dforge/plans/2026-11-20-audit-remaining.md | test: Task 24 contracts | done | 0b1ab1a |
| 60 | B3b-8: dream and hygiene actions ignore record_event's False return | docs/dforge/plans/2026-11-20-audit-remaining.md | A22 (Task 22) | done | b17e7fb |
| 61 | B3b-9: asymmetric top-N proximity appends a phantom associate journal row each rotation | docs/dforge/plans/2026-11-20-audit-remaining.md | test: Task 22 contracts | done | b17e7fb |
| 62 | B3b-10 and B3b-R1: the derivation contradiction arm is unreachable because EXCLUSIVE_RELATION_FAMILIES ships empty | docs/dforge/plans/2026-11-20-audit-remaining.md | test: Task 23 contracts | done | e352460 |
| 63 | B3b-12: re-synthesis attempts every settled stale article with no per-tick budget | docs/dforge/plans/2026-11-20-audit-remaining.md | test: Task 24 contracts | done | 0b1ab1a |
| 64 | B3b-13: a lock_timeout during undo surfaces as a 500 rather than a retryable conflict | docs/dforge/plans/2026-11-20-audit-remaining.md | test: Task 22 contracts | done | b17e7fb |
| 65 | B3b-14 and B3b-R4: undo's all-or-nothing holds only because the single HTTP caller rolls back; wrap the write phase in one begin_nested() | - | - | deferred | declined in the spec: CLAUDE.md records the no-savepoint shape as contract and an AST scan enforces it |
| 66 | B3b-15: cursor helpers, the article-gate resolver, the locked memory projection and the fact-set hash queries are each duplicated | docs/dforge/plans/2026-11-20-audit-remaining.md | test: Task 25 contracts | done | 628ee76 |
| 67 | B3b-16 and B3b-R3: the ResearchGatherer Protocol has one implementation that returns a supplied list; server.py wrongly calls the authenticated door unauthenticated | docs/dforge/plans/2026-11-20-audit-remaining.md | test: Task 25 contracts | done | 628ee76 |
| 68 | B3b-18: stale docstrings and annotations in article_synthesis, review_queue, hygiene_queue and verification_judge | docs/dforge/plans/2026-11-20-audit-remaining.md | test: Task 25 contracts | done | 628ee76 |
| 69 | B3b-19: the article runner discards both outcomes and logs nothing | docs/dforge/plans/2026-11-20-audit-remaining.md | test: Task 24 contracts | done | 0b1ab1a |
| 70 | B3b-20: the dispute-onset lateral on events has no created_at bound | docs/dforge/plans/2026-11-20-audit-remaining.md | test: Task 24 contracts | done | 0b1ab1a |
| 71 | B3b-17 and B3b-R6: research_rerun is a 320-line wrapper, live through the Settings Research UI | - | - | deferred | kept: the reviewer's own remedy is to keep it while the UI button exists |
| 72 | B3b-R7: review_ranking has one consumer and could be folded into review_queue (optional) | - | - | deferred | declined in the spec: saves no lines |
| 73 | B4-4: the working-tree drift scan hashes every file synchronously on the event loop | docs/dforge/plans/2026-11-20-audit-remaining.md | test: Task 30 contracts | done | 25029ab |
| 74 | B4-5: per-file deletes scan the whole repository's edge and node tables | docs/dforge/plans/2026-11-20-audit-remaining.md | test: Task 30 contracts | done | 25029ab |
| 75 | B4-6: one failed embed loses that file's code chunks until the file changes again | docs/dforge/plans/2026-11-20-audit-remaining.md | A33 (Task 28) | done | 96f9a23 |
| 76 | B4-7: incremental diff parsing breaks on non-ASCII and special-character paths | docs/dforge/plans/2026-11-20-audit-remaining.md | A34 (Task 28) | done | 96f9a23 |
| 77 | B4-8: incremental runs mis-key cross-file base classes defined in unchanged files | docs/dforge/plans/2026-11-20-audit-remaining.md | A34 (Task 28) | done | 96f9a23 |
| 78 | B4-9 and F1-4 backend half: blast radius and symbol lookup ignore repository and owner | docs/dforge/plans/2026-11-20-audit-remaining.md | A35 (Task 26) | done | eddcc5e |
| 79 | B4-10 and B6-4: MCP code_symbol probably raises MissingGreenlet on any hit; no result limit | docs/dforge/plans/2026-11-20-audit-remaining.md | A35 (Task 26) | done | eddcc5e |
| 80 | B4-11: unchanged dependent and debt files are re-embedded on every incremental run | docs/dforge/plans/2026-11-20-audit-remaining.md | A33 (Task 28) | done | 96f9a23 |
| 81 | B4-12: MCP code_search returns nothing without an embedder, while REST answers from the keyword arm | docs/dforge/plans/2026-11-20-audit-remaining.md | A14 (Task 27) | done | cf10951 |
| 82 | B4-13: a transient fetch failure deletes the managed clone and re-clones it, with no claim held | docs/dforge/plans/2026-11-20-audit-remaining.md | A36 (Task 29) | done | 4a02245 |
| 83 | B4-14: a file whose parse times out or raises is re-detected as drift on every tick | docs/dforge/plans/2026-11-20-audit-remaining.md | test: Task 30 contracts | done | 25029ab |
| 84 | B4-15: query-per-item loops in phases 03, 05 and 06 | docs/dforge/plans/2026-11-20-audit-remaining.md | test: Task 30 contracts | done | 25029ab |
| 85 | B4-16: phase 08 seeds every file's type environment with every symbol's return type, keyed by function name | docs/dforge/plans/2026-11-20-audit-remaining.md | test: Task 31 contracts | done | 6bb6606 |
| 86 | B4-17: Leiden and process tracing rewrite the repo's whole community/process layer on every run, under non-deterministic keys | docs/dforge/plans/2026-11-20-audit-remaining.md | test: Task 31 contracts | done | 6bb6606 |
| 87 | B4-18: property nodes are keyed by bare name and deleted together with the first owner's file | docs/dforge/plans/2026-11-20-audit-remaining.md | test: Task 31 contracts | done | 6bb6606 |
| 88 | B4-19: failure paths store unsanitised exception text; tokens sit in the git argv | docs/dforge/plans/2026-11-20-audit-remaining.md | A36 (Task 29) | done | 9124abd |
| 89 | B4-20: a local checkout's fetch lane fast-forwards whichever branch is checked out | docs/dforge/plans/2026-11-20-audit-remaining.md | test: Task 3 contracts | done | 4a02245 |
| 90 | B4-21 and removal 5: the wiki config row is orphaned on repo delete, and the cache check is dead | docs/dforge/plans/2026-11-20-audit-remaining.md | test: Task 32 contracts | done | e48b9f1 |
| 91 | B4-22: process_tracer reads a signature property nothing writes | docs/dforge/plans/2026-11-20-audit-remaining.md | test: Task 31 contracts | done | 6bb6606 |
| 92 | B4-23: code_deriver strips and rewrites every repo's assertions hourly, whether or not HEAD moved | docs/dforge/plans/2026-11-20-audit-remaining.md | test: Task 30 contracts | done | 25029ab |
| 93 | B4-24: cancel_repo_task does not check that the task belongs to the repository in the URL | docs/dforge/plans/2026-11-20-audit-remaining.md | test: Task 29 contracts | done | 4a02245 |
| 94 | B4-25: doc and comment drift in code_pipeline and repo_allowlist; CodeFile.last_commit_sha is served but never written | docs/dforge/plans/2026-11-20-audit-remaining.md | test: Task 32 contracts | done | e48b9f1 |
| 95 | B4 removals 3, 4, 6, 7: TaskRegistry.get_all_running and cleanup_completed, the CallResolver named_imports/wildcard_imports arguments, RepoManager.get_auth_token, _implements_split's discarded return value | docs/dforge/plans/2026-11-20-audit-remaining.md | test: Task 32 contracts | done | e48b9f1 |
| 96 | B4 removal 8: the CodeFile.last_commit_sha column | docs/dforge/plans/2026-11-20-audit-remaining.md | A47 (Task 32) | done | e48b9f1 |
| 97 | B5-2: a document block edit drops no vectors, so a failed embed after commit leaves the old-text vector forever and the route answers 500 for a write that landed | docs/dforge/plans/2026-11-20-audit-remaining.md | A25 (Task 33) | done | 6877a10 |
| 98 | B5-3: upload streams up to 50 MB inside the global attachment lock and an open transaction; the Notion import holds the same lock for up to 900 s | docs/dforge/plans/2026-11-20-audit-remaining.md | A26 (Task 34) | done | 5787a38 |
| 99 | B5-4: any content change re-embeds every block inline, and every unchanged re-push spends a real embed call | docs/dforge/plans/2026-11-20-audit-remaining.md | A28 (Task 33) | done | 6877a10 |
| 100 | B5-5: _PLACE rewrites every block row of the tree on every verb | docs/dforge/plans/2026-11-20-audit-remaining.md | test: Task 36 contracts | done | 2722f0a |
| 101 | B5-6: blocks.search_vector and ix_blocks_search_vector have no reader (owner ruling 2026-11-20: drop) | docs/dforge/plans/2026-11-20-audit-remaining.md | A46 (Task 48) | done | 9331528; A46 on the 2026-11-21 03:30 backup restored to the dev Postgres: stamp 0003 to head 0006, blocks 4 before and 4 after, blocks.search_vector and ix_blocks_search_vector gone, no table kept |
| 102 | B5-7: document_revisions stores a full content copy on every hash-changing put, with no prune | docs/dforge/plans/2026-11-20-audit-remaining.md | A27 (Task 35) | done | d11e188 |
| 103 | B5-8: substring(content ...) runs once per joined block row over a TOASTed content | docs/dforge/plans/2026-11-20-audit-remaining.md | test: Task 36 contracts | done | 2722f0a |
| 104 | B5-9: markdown-it parses up to 1M characters on the event loop, and MAX_BLOCKS is enforced only after every block row is inserted | docs/dforge/plans/2026-11-20-audit-remaining.md | test: Task 36 contracts | done | 2722f0a |
| 105 | B5-10: rename_documents takes no actor/api_key_id, so subtree renames journal with no attribution | docs/dforge/plans/2026-11-20-audit-remaining.md | test: Task 37 contracts | done | 11e6c8f |
| 106 | B5-11: parse_pdf cannot be reached in production; it still carries pdfplumber, pdfminer-six, pillow and pypdfium2 (owner ruling 2026-11-20: remove) | docs/dforge/plans/2026-11-20-audit-remaining.md | A48 (Task 48) | done | 9331528 |
| 107 | B5-12: ingest_documents, DocumentSource, file_documents_isolated, DocumentFileJob, DocumentFileFailure, resolve_read_fingerprint and block_vectors have only test callers | docs/dforge/plans/2026-11-20-audit-remaining.md | test: Task 37 contracts | done | 11e6c8f |
| 108 | B5-13: parent_id, after_block_id and new_parent_id are typed str on the document block routes, so a malformed id gets a 500 | docs/dforge/plans/2026-11-20-audit-remaining.md | test: Task 37 contracts | done | 11e6c8f |
| 109 | B5-14: document connections run one uncached ANN probe per block on every document view | docs/dforge/plans/2026-11-20-audit-remaining.md | test: Task 36 contracts | done | 2722f0a |
| 110 | B5-15: the document list joins and groups every block of every document before LIMIT/OFFSET | docs/dforge/plans/2026-11-20-audit-remaining.md | test: Task 36 contracts | done | 2722f0a |
| 111 | B5-16: an unembeddable block stays in the first batch and costs a failed batch call plus up to 500 single-row embeds on every tick | docs/dforge/plans/2026-11-20-audit-remaining.md | test: Task 33 contracts | done | 6877a10 |
| 112 | B5-17: four copies of the same register-the-fingerprint helper | docs/dforge/plans/2026-11-20-audit-remaining.md | test: Task 33 contracts | done | 6877a10 |
| 113 | B6-2: login runs bcrypt on the event loop, and the lockout check happens before an await, so concurrent attempts exceed five guesses | docs/dforge/plans/2026-11-20-audit-remaining.md | A7 (Task 1) | done | 1d02a7c |
| 114 | B6-3: MCP memory_reason, memory_overview and document_search call the LLM or embedder on the read-only backup worker | docs/dforge/plans/2026-11-20-audit-remaining.md | A12 (Task 5) | done | 7d6e56b |
| 115 | B6-5: get_session commits after the response is sent, so routes without an explicit commit return 200 before the write is durable | docs/dforge/plans/2026-11-20-audit-remaining.md | A29 (Task 38) | done | 703d4b7 |
| 116 | B6-6: the CORS fallback grants credentialed cross-origin access to localhost:3000 and :5173 | docs/dforge/plans/2026-11-20-audit-remaining.md | A8 (Task 1) | done | 1d02a7c |
| 117 | B6-7: SSH destination user/host go unvalidated into the ssh/scp argv | docs/dforge/plans/2026-11-20-audit-remaining.md | A9 (Task 3) | done | 9124abd |
| 118 | B6-8: every MCP request and every keyed REST call pays a fresh bcrypt | docs/dforge/plans/2026-11-20-audit-remaining.md | A11 (Task 2) | done | 6eb3cde |
| 119 | B6-9: min_interval_seconds is persisted into the job row on first save, so raising a floor in code never takes effect | docs/dforge/plans/2026-11-20-audit-remaining.md | A30 (Task 40) | done | f976565 |
| 120 | B6-10: PUT /jobs/{key} and its config twin wait on the per-job run lock | docs/dforge/plans/2026-11-20-audit-remaining.md | A30 (Task 40) | done | f976565 |
| 121 | B6-12: job_runs.trigger is never written, so the UI's manual badge never renders | docs/dforge/plans/2026-11-20-audit-remaining.md | test: Task 40 contracts | done | f976565 |
| 122 | B6-13: three hourly cleanup jobs write a maintenance_run row into the permanent journal even when they do nothing | docs/dforge/plans/2026-11-20-audit-remaining.md | test: Task 40 contracts | done | f976565 |
| 123 | B6-14: any boot exception in the LLM try leaves pipeline=None for the life of the process while /health returns 200 | docs/dforge/plans/2026-11-20-audit-remaining.md | A31 (Task 41) | done | bc01c8c |
| 124 | B6-15: code_rename matches with an unescaped LIKE | docs/dforge/plans/2026-11-20-audit-remaining.md | test: Task 27 contracts | done | cf10951 |
| 125 | B6-16: several MCP code tools call scalar_one_or_none() on Repository.name, which is not unique | docs/dforge/plans/2026-11-20-audit-remaining.md | A35 (Task 26) | done | eddcc5e |
| 126 | B6-17: a failed MCP call-log flush discards its popped batch uncounted, and validation-error text may echo content | docs/dforge/plans/2026-11-20-audit-remaining.md | test: Task 42 contracts | done | 4b30a14, c398c66, 58e067e |
| 127 | B6-18: a masked secret is resolved by name even when the URL or host changes | docs/dforge/plans/2026-11-20-audit-remaining.md | A10 (Task 3) | done | 9124abd |
| 128 | B6-19 and B6-D3: system-prompts, repo-allowlist and notifications read-modify-write their config rows without the row lock; about 12 config endpoints repeat the pattern three ways | docs/dforge/plans/2026-11-20-audit-remaining.md | A29 (Task 39) | done | 3754ed1 |
| 129 | B6-20: events partition maintenance rides on pipeline_failure_cleanup, which the UI can disable | docs/dforge/plans/2026-11-20-audit-remaining.md | A32 (Task 41) | done | bc01c8c |
| 130 | B6-21: each open WebSocket runs 2 database queries per second for revalidation, serially inside the send lock | docs/dforge/plans/2026-11-20-audit-remaining.md | test: Task 42 contracts | done | 4b30a14, c398c66, 58e067e |
| 131 | B6-22: stale statements: 48 tools, dream jobs called placeholders, the curb row's reader, and LLM_* env vars in CLAUDE.md | docs/dforge/plans/2026-11-20-audit-remaining.md | A51 (Task 69) | done | 132f803 |
| 132 | B6-D1: the lifespan carries boot steps for states that no longer occur | docs/dforge/plans/2026-11-20-audit-remaining.md | test: Task 41 contracts | done | bc01c8c; legacy enrichment copy kept, production has no enrichment_config row |
| 133 | B6-D2: about 830 lines of MCP code tools run raw SQL in the transport instead of CodeQueryService | docs/dforge/plans/2026-11-20-audit-remaining.md | test: Task 27 contracts | done | cf10951 |
| 134 | B6-D4: job last_* state is rewritten into config on every tick | docs/dforge/plans/2026-11-20-audit-remaining.md | A30 (Task 40) | done | f976565 |
| 135 | B6-D5: inject_* and client_connect live under app/services but are reached at runtime only by a CLI script | docs/dforge/plans/2026-11-20-audit-remaining.md | A51 (Task 69) | done | 132f803 |
| 136 | B6-D6: per-socket, per-second revalidation is a heavy polling contract; close sockets directly and drop the polling | - | - | deferred | declined in the spec: CLAUDE.md records the one-second revalidation as contract; B6-21 removes its cost |
| 137 | F1-1 (high): the Edit Repository dialog cannot save URL-cloned repositories | docs/dforge/plans/2026-11-20-audit-remaining.md | A3 (Task 49) | done | fd9b5c7 |
| 138 | F1-2 (high): the 3D graph data is rebuilt in 2D view, in O(n squared) | docs/dforge/plans/2026-11-20-audit-remaining.md | A4 (Task 53) | done | 6fb823d |
| 139 | F1-4: Blast Radius silently fails on the folded graph; no onError handler | docs/dforge/plans/2026-11-20-audit-remaining.md | test: Task 49 contracts | done | fd9b5c7 |
| 140 | F1-5: Code Graph and Wiki show No repositories indexed yet while loading or after an error | docs/dforge/plans/2026-11-20-audit-remaining.md | A41 (Task 50) | done | ff88573 |
| 141 | F1-6: the code canvas rebuilds Sigma and restarts the layout on every keystroke | docs/dforge/plans/2026-11-20-audit-remaining.md | test: Task 51 contracts | done | 8a4853d |
| 142 | F1-7: per-frame string-keyed density grid on the memory canvas | docs/dforge/plans/2026-11-20-audit-remaining.md | test: Task 54 contracts | done | 04172df |
| 143 | F1-9: dead or test-only exports in live modules (graph-geometry hull helpers, lightenHex, clusterAnchors, code-graph-theme colour functions, groupMemories, placeIslands, zoomLevel, setGraphReady, inner GraphSkeleton, duplicate stableHash) | docs/dforge/plans/2026-11-20-audit-remaining.md | test: Task 54 contracts | done | 04172df |
| 144 | F1-10: wiki and edit-repository mutation failures are not reported | docs/dforge/plans/2026-11-20-audit-remaining.md | test: Task 49 contracts | done | fd9b5c7 |
| 145 | F1-11: Copy Mermaid misreports and fails in production (navigator.clipboard undefined on plain HTTP) | docs/dforge/plans/2026-11-20-audit-remaining.md | test: Task 49 contracts | done | fd9b5c7 |
| 146 | F1-12: clicking an entity in 3D shows the graph summary | docs/dforge/plans/2026-11-20-audit-remaining.md | test: Task 53 contracts | done | 6fb823d |
| 147 | F1-13: colour-mode changes rebuild what is already recoloured in place | docs/dforge/plans/2026-11-20-audit-remaining.md | test: Task 53 contracts | done | 6fb823d |
| 148 | F1-14: the detail panel's close button has no accessible name | docs/dforge/plans/2026-11-20-audit-remaining.md | test: Task 53 contracts | done | 6fb823d |
| 149 | F1-15: graph and code loading and error states are inconsistent | docs/dforge/plans/2026-11-20-audit-remaining.md | A41 (Task 50) | done | ff88573 |
| 150 | F1-16: KIND_CHART defined three times; node sizing differs between 2D and 3D | docs/dforge/plans/2026-11-20-audit-remaining.md | test: Task 54 contracts | done | 04172df |
| 151 | F1-17: duplicated runner boilerplate and per-frame allocation during layout; collide() is O(k squared) | docs/dforge/plans/2026-11-20-audit-remaining.md | test: Task 54 contracts | done | 04172df |
| 152 | F1-18: symbolsByFile copies each file's array on every insert | docs/dforge/plans/2026-11-20-audit-remaining.md | test: Task 54 contracts | done | 04172df |
| 153 | F1-19: the graph payload carries full memory content for up to 50,000 nodes | docs/dforge/plans/2026-11-20-audit-remaining.md | test: Task 52/53 contracts | done | 6fb823d |
| 154 | F1-20: every theme consumer runs its own MutationObserver | docs/dforge/plans/2026-11-20-audit-remaining.md | test: Task 54 contracts | done | 04172df |
| 155 | F1-21: remembered-position maps grow without bound | docs/dforge/plans/2026-11-20-audit-remaining.md | test: Task 54 contracts | done | 04172df |
| 156 | F1-23: two layout engines; one engine could serve both canvases (owner call) | - | - | deferred | declined in the spec: the code graph would look different, and the constellation plan shipped it two days ago |
| 157 | F2-2: the Maintenance re-embed count goes stale (private cache name) | docs/dforge/plans/2026-11-20-audit-remaining.md | test: Task 58 contracts | done | e5be096 |
| 158 | F2-3: the WebSocket ignores the server's session-expired close and retries forever | docs/dforge/plans/2026-11-20-audit-remaining.md | test: Task 57 contracts | done | d169f7e |
| 159 | F2-4: demo mode still calls the API from Settings LLM | docs/dforge/plans/2026-11-20-audit-remaining.md | A43 (Task 58) | done | e5be096 |
| 160 | F2-5: Settings has five save models, three ways of showing a load failure, and three confirmation styles | docs/dforge/plans/2026-11-20-audit-remaining.md | A37 (Task 55) | done | fef8eb1 |
| 161 | F2-6: the LLM tab shows blank models and a fixture judge as if real on load failure | docs/dforge/plans/2026-11-20-audit-remaining.md | A41 (Task 50) | done | ff88573 |
| 162 | F2-7: Flags dialogs close on Save before the write lands; edits are lost | docs/dforge/plans/2026-11-20-audit-remaining.md | A37 (Task 55) | done | fef8eb1 |
| 163 | F2-8: number fields in the Flags dialogs commit only on blur while Save is disabled; one field type clamps silently, the other shows an error | docs/dforge/plans/2026-11-20-audit-remaining.md | test: Task 55 contracts | done | fef8eb1 |
| 164 | F2-9 and F3-4: the app never calls /auth/refresh, so every session ends hard after 24h and both editors lose in-memory drafts | docs/dforge/plans/2026-11-20-audit-remaining.md | A38 (Task 56/57) | done | d169f7e |
| 165 | F2-10: about 18 exported hooks in hooks/api have no production importer, plus WebSocket cache writes nothing reads | docs/dforge/plans/2026-11-20-audit-remaining.md | test: Task 59 contracts | done | cec12f6 |
| 166 | F2-11: unused auth code: useSession, useLogout, LogoutButton, authAdapter.me, lib/api.ts login() | docs/dforge/plans/2026-11-20-audit-remaining.md | test: Task 59 contracts | done | cec12f6 |
| 167 | F2-12 remainder: keepDialogOpenOnListEscape (7 call sites) is retirable by its own comment | docs/dforge/plans/2026-11-20-audit-remaining.md | test: Task 55 contracts | done | fef8eb1 |
| 168 | F2-13: formatDateTime is defined four times; both formatDuration copies print 1m 60s for 119.6 seconds | docs/dforge/plans/2026-11-20-audit-remaining.md | test: Task 58 contracts | done | e5be096 |
| 169 | F2-14: checkSetupStatus ignores the HTTP status, so a server error shows the setup wizard | docs/dforge/plans/2026-11-20-audit-remaining.md | test: Task 58 contracts | done | e5be096 |
| 170 | F2-15: the setup wizard keeps vendor API keys in localStorage until setup finishes | docs/dforge/plans/2026-11-20-audit-remaining.md | A43 (Task 58) | done | e5be096 |
| 171 | F2-16: the Research tab overwrites typed budgets on every reload of its settings | docs/dforge/plans/2026-11-20-audit-remaining.md | test: Task 58 contracts | done | e5be096 |
| 172 | F2-17: in development StrictMode leaves a duplicate WebSocket, so every event toasts twice | docs/dforge/plans/2026-11-20-audit-remaining.md | test: Task 57 contracts | done | d169f7e |
| 173 | F2-18: queries do not pass cancellation signals; the maintenance tab polls /jobs every 5s for one value; the project switcher says No project holds anything yet when loading fails | docs/dforge/plans/2026-11-20-audit-remaining.md | test: Task 50/58 contracts | done | e5be096 |
| 174 | F3-1 (high): sending in a second chat conversation silently aborts the first one's stream, and that answer is lost | docs/dforge/plans/2026-11-20-audit-remaining.md | A2 (Task 60) | done | 84735e6 |
| 175 | F3-2: the documents block editor throws away the typed text on any refused or failed write | docs/dforge/plans/2026-11-20-audit-remaining.md | A39 (Task 61) | done | 76c9235 |
| 176 | F3-3: hygiene queue checkbox selections survive project and page changes; Supersede instead acts only on the visible page, then clears every selection | docs/dforge/plans/2026-11-20-audit-remaining.md | A40 (Task 63) | done | 7a312ac |
| 177 | F3-5: every chat token re-parses the markdown of every earlier message | docs/dforge/plans/2026-11-20-audit-remaining.md | test: Task 60 contracts | done | 84735e6 |
| 178 | F3-6: a task filter on an open workstream re-downloads the whole ledger every 5 s | docs/dforge/plans/2026-11-20-audit-remaining.md | test: Task 64 contracts | done | 8f788aa |
| 179 | F3-7: after a refusal, the documents write queue re-reads the hash and sends the next write anyway | docs/dforge/plans/2026-11-20-audit-remaining.md | A39 (Task 61) | done | 76c9235 |
| 180 | F3-8: a failed page title rename is silent | docs/dforge/plans/2026-11-20-audit-remaining.md | test: Task 64 contracts | done | 8f788aa |
| 181 | F3-9a: dead code: useBlockMove, and rank_note/consequence computed but never shown | docs/dforge/plans/2026-11-20-audit-remaining.md | test: Task 59 contracts | done | cec12f6 |
| 182 | F3-9b: the pager is hand-written twice although darkraise-ui ships pagination; the two knowledge queues use different list patterns | docs/dforge/plans/2026-11-20-audit-remaining.md | test: Task 63 contracts | done | 7a312ac |
| 183 | F3-9c: the two block editors duplicate the hash-precondition plumbing and handle conflicts differently | docs/dforge/plans/2026-11-20-audit-remaining.md | test: Task 61 contracts | done | 76c9235 |
| 184 | F3-9d: a first chat turn that never completes leaves an Untitled conversation the client never learns about | docs/dforge/plans/2026-11-20-audit-remaining.md | test: Task 60 contracts | done | not reproduced: every exit of useChatStream's send (done, error event, EOF, fetch failure, abort) runs refreshAfterStream in finally, which invalidates [conversations]; a first-turn error test passed on the base and use-chat-stream-source-fields.test.tsx already pins the invalidation |
| 185 | F3-9e: deleting a conversation has no error handling | docs/dforge/plans/2026-11-20-audit-remaining.md | test: Task 60 contracts | done | 84735e6 |
| 186 | F3-9f: two quick board edits to one register conflict with each other | docs/dforge/plans/2026-11-20-audit-remaining.md | test: Task 64 contracts | done | 8f788aa |
| 187 | F3-9g: Notes does a full-document conversion on every keystroke | docs/dforge/plans/2026-11-20-audit-remaining.md | test: Task 64 contracts | done | 8f788aa |
| 188 | F3-9h: the facts list's filter options cover only the pages already loaded | docs/dforge/plans/2026-11-20-audit-remaining.md | test: Task 62/63 contracts | done | 7a312ac |
| 189 | F3 mirror note: no test pins the TypeScript copy of block_verbs.py's refusals to the Python one | docs/dforge/plans/2026-11-20-audit-remaining.md | test: Task 64 contracts | done | 8f788aa |
| 190 | P1-1 (high): the extension's auto-capture stores every partial state of a streaming reply as its own memory | docs/dforge/plans/2026-11-20-audit-remaining.md | A5 (Task 65) | done | 58b1518 |
| 191 | P1-2 (high): pull requests can run code on the self-hosted LAN runner; check the fork-approval setting | docs/dforge/plans/2026-11-20-audit-remaining.md | A6 (Task 4) | done | f0b79c0 |
| 192 | P1-3: a cancelled tag job still lets github-release create the tag on master's tip | docs/dforge/plans/2026-11-20-audit-remaining.md | A49 (Task 66) | done | 1583bda |
| 193 | P1-4: numpy is imported but not declared | docs/dforge/plans/2026-11-20-audit-remaining.md | A50 (Task 66) | done | 1583bda |
| 194 | P1-5: third-party actions are pinned to movable tags, not commit SHAs; the trivy job writes the cache publish reads | docs/dforge/plans/2026-11-20-audit-remaining.md | test: Task 4 contracts | done | f0b79c0 |
| 195 | P1-6: CONTRIBUTING.md describes the old release model | docs/dforge/plans/2026-11-20-audit-remaining.md | A51 (Task 69) | done | 132f803 |
| 196 | P1-7: release.sh cannot finish on this host (it runs gate.sh --full) | docs/dforge/plans/2026-11-20-audit-remaining.md | test: Task 66 contracts | done | 1583bda |
| 197 | P1-8: the e2e database reset bypasses the destructive-SQL guard on a false premise | docs/dforge/plans/2026-11-20-audit-remaining.md | test: Task 4 contracts | done | f0b79c0 |
| 198 | P1-9: the worker's restore loop treats every migrate failure as an old-baseline snapshot and exits 0 | docs/dforge/plans/2026-11-20-audit-remaining.md | A49 (Task 67) | done | 97a4026 |
| 199 | P1-10: start_dev_server.sh calls bare python and by default migrates localhost:5432, which is production on this host | docs/dforge/plans/2026-11-20-audit-remaining.md | test: Task 4 contracts | done | f0b79c0 |
| 200 | P1-11: five seed and test scripts are broken and unreferenced | docs/dforge/plans/2026-11-20-audit-remaining.md | test: Task 68 contracts | done | bfbd27a |
| 201 | P1-12 remainder: publish_production_models.sh changes into the deleted fine-tuning directory | docs/dforge/plans/2026-11-20-audit-remaining.md | test: Task 68 contracts | done | bfbd27a |
| 202 | P1-13: the cutover package is the one-time 0006-to-baseline loader and only its own tests use it (llm_providers_transition.py stays) | docs/dforge/plans/2026-11-20-audit-remaining.md | test: Task 68 contracts | done | bfbd27a |
| 203 | P1-14: entailment/cache_span (about 549 judge-cache files) appears to be tracked although judge output is quarantined | - | - | deferred | kept: faithfulness_gate.py reads the directory and the G-F replay ran from it |
| 204 | P1-15: CI skips the extension suite, both SDK suites and the SDK build | docs/dforge/plans/2026-11-20-audit-remaining.md | A50 (Task 66) | done | 1583bda |
| 205 | P1-16: the Dockerfile's chown -R duplicates layers and leaves the code writable; the app package is installed twice; Node 20 is end-of-life | docs/dforge/plans/2026-11-20-audit-remaining.md | test: Task 67 contracts | done | 97a4026 |
| 206 | P1-17: build-push.sh tags the HEAD sha even from a dirty tree | docs/dforge/plans/2026-11-20-audit-remaining.md | A49 (Task 67) | done | 97a4026 |
| 207 | P1-18: backup.sh accepts any complete dump, so a dump of the wrong database would push real dumps out of retention | docs/dforge/plans/2026-11-20-audit-remaining.md | A49 (Task 67) | done | 97a4026 |
| 208 | P1-19: frontend/nginx.conf is used by no build path | - | - | deferred | kept: frontend/Dockerfile:17 copies it for the deliberate nginx-in-image fallback |
| 209 | P1-20: stale comments: the ml extra in pyproject.toml, alembic.ini's ignored URL, the e2e README | docs/dforge/plans/2026-11-20-audit-remaining.md | test: Task 68 contracts | done | bfbd27a |
| 210 | P1-21: the two GitNexus files at the repo root are unreferenced | docs/dforge/plans/2026-11-20-audit-remaining.md | test: Task 68 contracts | done | bfbd27a |
| 211 | P1-22: eval_round3 is held in place by the guard test and still waits on owner decision D5 | - | - | deferred | owner decision D5 is not this programme's to make |
| 212 | P1-23: import_docs_corpus.py is likely superseded by the dr-forge mirror | - | - | deferred | declined in the spec: supersession by the dr-forge mirror is likely, not shown |
| 213 | P1-24: the worker compose comment says the receiver has no network, but it joins the default one | docs/dforge/plans/2026-11-20-audit-remaining.md | test: Task 67 contracts | done | 97a4026 |
| 214 | Section 6: lucide-react is not declared; 152 files import it through darkraise-ui | docs/dforge/plans/2026-11-20-audit-remaining.md | test: Task 66 contracts | done | 1583bda |
| 215 | Section 1 follow-up 2: requeue the 53 error rows on this host once the fixes are deployed (owner answer 2026-11-20: requeue here) | - | - | deferred | production write: an auto run performs none; carried out after the merge by the sequence at the end of Task 71 of docs/dforge/plans/2026-11-20-audit-remaining.md |
| 216 | P1-2 follow-up: read the repository's fork-approval setting with gh and report it | docs/dforge/plans/2026-11-20-audit-remaining.md | test: Task 71 contracts | done | 084c348; read 2026-11-21 with gh (no setting changed): actions/permissions/fork-pr-contributor-approval answers approval_policy first_time_contributors; repository visibility PUBLIC |
| 217 | Section 1 follow-ups 1 and 2 on 192.168.0.199: restore the embedding provider there and requeue its error rows | - | - | deferred | owner's: that instance is outside this host (owner answer 2026-11-20) |
| 218 | Section 1 follow-up 3: turn on job-failure notifications in Settings | - | - | deferred | owner's: needs a channel the owner chooses (owner answer 2026-11-20) |
| 219 | constellation-graphs row 5: no test asserts the memory renderer's one-frame deferred runner.start() | docs/dforge/plans/2026-11-20-audit-remaining.md | test: Task 53 contracts | done | 6fb823d (test only: graph-interactions.test.tsx pins the one-frame deferred runner.start; passes on the base by design) |
| 220 | constellation-graphs row 6: a code-canvas rebuild that changes the drawn node set opens at sigma's default camera and does not re-centre a persisting selection | docs/dforge/plans/2026-11-20-audit-remaining.md | test: Task 51 contracts | done | 8a4853d |
| 221 | constellation-graphs row 7: the code canvas's ring overlay, its follow-camera during the core run, and memory-renderer position reseeding across a rebuild have no unit test | docs/dforge/plans/2026-11-20-audit-remaining.md | test: Task 51 contracts | done | 8a4853d |
| 222 | constellation-real-data row 9: the placeOuter iteration of the 20,000-node timing loop is covered by A14 (for test-simplifier) | docs/dforge/plans/2026-11-20-audit-remaining.md | test: Task 54 contracts | done | 04172df |
| 223 | graph-cluster-quality row 1: switching graph Regions off leaves the region outlines and chips drawn until a repaint | docs/dforge/plans/2026-11-20-audit-remaining.md | test: Task 53 contracts | done | not reproduced: sigma 3.0.3 refresh() renders synchronously and afterRender redraws the hull canvas, so Regions off clears outlines and chips in the same frame; pinned by graph-interactions.test.tsx |
| 224 | graph-cluster-quality row 2: two clusters can receive the same computed name, so the filter panel lists two identical rows | docs/dforge/plans/2026-11-20-audit-remaining.md | test: Task 52 contracts | done | c03c42b |
| 225 | graph-cluster-quality row 3: a chosen term that is part of the prefix is not skipped, so a name can partly repeat its prefix | docs/dforge/plans/2026-11-20-audit-remaining.md | test: Task 52 contracts | done | c03c42b |
| 226 | graph-cluster-quality row 4: measure entity_terms_for_memories latency on an all_memories view | docs/dforge/plans/2026-11-20-audit-remaining.md | test: Task 52 contracts | done | c03c42b; measured 2026-11-21 on production (read-only EXPLAIN ANALYZE, view ids selected in the statement): all_memories view of 4,759 memories, execution 437 ms (310 ms in the ix_entities_memory_ids bitmap scan, 7,215 term rows) |
| 227 | graph-cluster-quality row 8: stale Louvain wording in a kept graph test comment | docs/dforge/plans/2026-11-20-audit-remaining.md | test: Task 52 contracts | done | not reproduced: grep -in louvain backend/tests/test_graph_scale.py finds only the method name get_louvain_clustered_vectors (7 hits), no comment |
| 228 | graph-cluster-quality row 7: gate.sh is GATE BLOCKED on this checkout because the F1 bench cache is missing | - | - | deferred | owner's: the cache needs DEEPSEEK_API_KEY, lost when the checkout was re-cloned |
| 229 | graph-cluster-quality rows 9 and 10: ENTITY_TERM_TYPES location; two cluster-naming tests deleted rather than rewritten | - | - | deferred | recorded decisions of that plan, no work owed |
| 230 | B3a-4 follow-up: drop knowledge_triples.stated_expiry and its partial index in a new revision | - | - | deferred | two-step drop: v1.17.0 still maps the column; ship in the release after the first release without a reader of it |
| 231 | B4 removal 8 follow-up: drop code_files.last_commit_sha in a new revision | - | - | deferred | two-step drop: v1.17.0 still maps the column; ship in the release after the first release without a reader of it |
| 232 | B3b-4 follow-up: restore the project/ tags a past refine removed, on this host | - | - | deferred | owner's: a production write; the script and its dry run are delivered, the restore waits for the owner's word. Dry run on the 2026-11-21 03:30 backup restored to the dev Postgres: memories: 39 (project/default 20, darkraise-framework 9, fshare-folder 4, form-capture 3, darkcloud 2, darkload 1) |
| 233 | test_classifier_kind.py::test_resolve_classifier_falls_back_to_llm_when_ml_unavailable is covered by test_local_classifier_availability.py::test_stored_local_row_classifies_with_the_llm | - | - | deferred | final review: for dforge:test-simplifier |
| 234 | Task 1 parked: preflight-38: CLAUDE.md not in Files | - | - | deferred | Ruling: the limiter sentences state no order; stage CLAUDE.md if it fires |
| 235 | Task 24 parked: preflight-61: test_dream_jobs.py not in Files | - | - | deferred | Ruling: git add backend/tests stages it |
| 236 | Task 64 parked: preflight-101: mirror names accepted in either file | - | - | deferred | Ruling: matches CLAUDE.md's recorded contract |
| 237 | Task 1 minor: backend/app/api/routes/auth.py:57-60 — a refusal caused only by in-flight saturation says "Too many failed login attempts; retry in 1s" | - | - | open | - |
| 238 | Task 1 minor: backend/tests/test_cors_fallback.py:20 — the test asserts on the environment rather than setting it | - | - | open | - |
| 239 | Task 1 minor: .dforge/sdd/2026-11-20-audit-remaining/task-1-report.md:43 — the GREEN run reports "9 warnings" and nobody explains them | - | - | open | - |
| 240 | Task 2 minor: backend/app/services/api_keys.py:162 — the comment says a rolled-back revoke "keeps the key refused in this process until restart", which is false | - | - | open | - |
| 241 | Task 2 minor: backend/tests/test_api_key_cache.py:0 — module-level `_verified` / `_revoked_ids` are never reset between tests | - | - | open | - |
| 242 | Task 2 minor: backend/tests/test_api_key_cache.py:289 — the expired-key test asserts on `authenticate(..., now=later)`, not on a 401 at the door as the brief words it | - | - | open | - |
| 243 | Task 2 parked: cv-warnings: unexplained 24 warnings | - | - | deferred | Ruling: environmental (test JWT secret length, pynvml import); -W error::DeprecationWarning run passes 7/7 |
| 244 | Task 3 minor: [lens:security] backend/app/services/code_pipeline.py:579 — log lines still write the raw exception | - | - | open | - |
| 245 | Task 3 minor: [lens:security] backend/app/services/repo_manager.py:408 — `http.extraHeader` is not scoped to the repository host | - | - | open | - |
| 246 | Task 3 minor: backend/app/api/routes/repos.py:375 — the background-run sanitisation has no test | - | - | open | - |
| 247 | Task 3 minor: frontend/src/features/graph/lib/__tests__/cluster-layout.test.ts:373 — out of scope: a hard 50 ms wall-clock threshold fails under host memory pressure (earlyoom/swap) and will recur as a false red in gate legs | - | - | open | - |
| 248 | Task 3 parked: cv-provider-url-normalisation | - | - | deferred | Ruling: _provider_base_url returns the value unchanged, so an unchanged masked save compares equal |
| 249 | Task 3 discovered: provider dialog sends the mask on a URL edit and now gets a 422 | - | - | open | - |
| 250 | Task 4 minor: backend/scripts/e2e/e2e_db.py:37 — [lens:security] the loopback set misses the rest of 127.0.0.0/8 and `0.0.0.0` | - | - | open | - |
| 251 | Task 4 minor: backend/tests/test_ci_workflows.py:105 — unused constant `TRUSTED_HEAD` (from agy) | - | - | open | - |
| 252 | Task 4 minor: backend/tests/test_ci_workflows.py:184 — the pinning test crashes on a `uses:` value with no `@` | - | - | open | - |
| 253 | Task 4 parked: cv-e2e-reset-port-scope | - | - | deferred | Ruling: loopback-only 5432 refusal stands; CI resets darkmem_e2e at postgres:5432 and the name check refuses production's darkmem on any host |
| 254 | Task 7 minor: backend/app/repositories/graph.py:580 — the strip still locks a memory's prior rows in scan order, so concurrent re-extractions can still deadlock | - | - | open | - |
| 255 | Task 7 minor: backend/tests/test_phase5_concurrency.py:341 — no test covers the relation sort | - | - | open | - |
| 256 | Task 7 minor: backend/tests/test_phase5_concurrency.py:364 — on the fixed code the test always spends the full 3 s timeout | - | - | open | - |
| 257 | Task 7 parked: cv-strip-ordering: B1-3 may require ordering the strip | - | - | deferred | Ruling: B1-3's remedy and the brief ask only for sorted upserts and keep the strip first in savepoint B; the strip's own lock order is outside this task (rulings-cannot-verify-7, seat answered inline) |
| 258 | Task 7 minor: backend/app/repositories/graph.py:577 — delete_by_memory_id's two strip UPDATEs lock shared rows in scan order, so concurrent re-extractions sharing rows can still deadlock in savepoint B (ruling seat grades it Important outside B1-3; fix: SELECT id … ORDER BY id FOR UPDATE before each UPDATE, plus a two-session re-extraction test) | - | - | open | - |
| 259 | Task 8 minor: backend/app/services/pipeline_failures.py:98 — the memory pipeline no longer produces extract=partial, so derive_memory_failed_step's extraction_partial branch (and the SPA's extraction_partial label) is unreachable for new rows | - | - | open | - |
| 260 | Task 8 minor: backend/app/services/pipeline.py:1300 — when the same-batch reconciliation fails, the batch's extracted journal rows (written in that session) are lost while the statuses survive | - | - | open | - |
| 261 | Task 9 minor: backend/app/services/memory.py:328 — with no pipeline, a flush that overruns the deadline keeps running on the request's own session after the request ends | - | - | open | - |
| 262 | Task 9 minor: backend/tests/test_wait_process.py:398 — the REST deadline test can't tell the pipeline's own session apart from the request session | - | - | open | - |
| 263 | Task 9 minor: backend/tests/test_wait_process.py:17 — the module docstring still names the removed `buffer_wait_timeout_seconds` flag | - | - | open | - |
| 264 | Task 9 minor: backend/app/services/wait_process.py:146 — a flush that raises is reported twice | - | - | open | - |
| 265 | Task 9 minor: backend/tests/test_wait_process.py:479 — the shutdown wiring is pinned by a source-string search | - | - | open | - |
| 266 | Task 9 minor: CLAUDE.md:372 — the wait_process contract sentence still says a flush running at the deadline "finishes as a tracked background task"; it omits that the flush is released to pending at the 290 s flush deadline and that a capture arriving with 8 flushes in flight is not driven at all (spec rule 3: contract sentences move with the code) | - | - | open | - |
| 267 | Task 9 minor: backend/app/services/wait_process.py:137 — the cap counts every tracked flush, including ones still inside their own 10 s request window, so it bounds concurrent wait_process drives overall rather than only flushes that outlived their request as the constant's name and comment at line 40 suggest | - | - | open | - |
| 268 | Task 9 discovered: a flush cut at shutdown refunds its attempt and repays the model spend | - | - | open | - |
| 269 | Task 10 minor: tests/test_memory_buffer.py emits an SAWarning 'transaction already deassociated from connection' at teardown (present on base 86818c87) | - | - | open | - |
| 270 | Task 10 discovered: SAWarning at teardown in tests/test_memory_buffer.py (pre-existing | - | - | open | - |
| 271 | Task 12 minor: the hook tests were written after use-memory-buffer-api.ts, so their only red is the missing module | - | - | open | - |
| 272 | Task 12 discovered: /health in Task 11 had used request DI and broke a direct-call test; Task 7 GIN test was planner-sensitive | - | - | open | - |
| 273 | Task 13 minor: a caller who sends importance exactly 0.5 is indistinguishable from one who sent none, so the extractor's value replaces it; the cutover backfill's importance restore is now needed only for default-importance rows | - | - | open | - |
| 274 | Task 13 discovered: test_cutover_backfill importance proofs went vacuous (reseeded at the default | - | - | open | - |
| 275 | Task 14 minor: a stream closed early by aclose (GeneratorExit, not a cancellation) still records ok=True with no payload, as before | - | - | open | - |
| 276 | Task 15 minor: with hybrid_search_enabled off and a failed shared embed, the pure-vector branch embeds again before raising (one extra embed attempt during an outage) | - | - | open | - |
| 277 | Task 15 discovered: hybrid_search embedder cooldown leaked across tests (autouse reset in conftest); the claim-gate scan had covered three score copies by a name coincidence | - | - | open | - |
| 278 | Task 16 minor: ChatService._lookup_entities passes ChatContext.selected_entity_id (an unvalidated str) to get_neighbors_by_id, so a malformed id from the chat body still raises a DataError mid-turn | - | - | open | - |
| 279 | Task 16 minor: get_memory_context slices the 20 smallest neighbour ids before the scope filter drops dead or foreign rows, so dead rows can still take slots | - | - | open | - |
| 280 | Task 16 discovered: chat selected_entity_id unvalidated; neighbour slice precedes the scope filter | - | - | open | - |
| 281 | Task 17 minor: frontend use-config-api.ts still types measurable_flags/measured_flags and use-graph-api.ts still calls /vectors/projection until the frontend cleanup (Task 45 names use-graph-api.ts, not use-config-api.ts) | - | - | open | - |
| 282 | Task 17 discovered: frontend types and the projection hook stay until the frontend cleanup | - | - | open | - |
| 283 | Task 18 minor: backend/tests/test_fact_lift_interleave.py:361 — the deferral test cannot tell `MemoriesBusy` apart from an unexpected DB error | - | - | open | - |
| 284 | Task 18 minor: backend/app/services/contradiction_scan.py:696 — the comment listing every `sources_changed` producer is now stale | - | - | open | - |
| 285 | Task 18 minor: the pipeline rewrites a caller's extraction entity dicts in place (canonical names), and tests/test_pipeline_savepoints.py's savepoint_bed shallow-copies the module-level EXTRACTION, so a test re-running the default extraction under the fake embedder leaks a pgvector→faiss rename into later tests | - | - | open | - |
| 286 | Task 18 minor: _open_fact_id still takes a blocking FOR UPDATE, so a lift waiting on a fact a re-extraction's reconcile holds can still close a cycle with that pipeline (pre-existing shape through two fact locks) | - | - | open | - |
| 287 | Task 18 discovered: the pipeline mutates extraction entity dicts in place (test fixture leak); _open_fact_id still blocks on FOR UPDATE (pre-existing cycle shape | - | - | open | - |
| 288 | Task 20 minor: fact_provenance._ORPHANED_PROVENANCE (reap backstop) still joins CAST(m.id AS text) = fs.source_ref; withdraw_memory_sources (REST memory delete) has no lock bound | - | - | open | - |
| 289 | Task 20 minor: backend/app/services/verification_recompute.py:807 — The `run_recompute` docstring still says "matching ``run_lift``'s contract" of not committing | - | - | open | - |
| 290 | Task 20 minor: backend/app/services/verification_recompute.py:537 — The idle watermark advance makes the 5 s commit-skew assumption bind on every idle tick, not only on busy ones | - | - | open | - |
| 291 | Task 20 minor: backend/tests/test_deriver_lift.py:1455 — The docstring of `test_a_suspected_contradiction_does_not_withhold_the_born_rung` still says "the consult above is a veto consult" | - | - | open | - |
| 292 | Task 20 parked: cannot-verify:0 facts_for_source / required_origin_count "exists at head" | - | - | deferred | Ruling: grep over every .py file outside .dforge finds neither name (backend/app, backend/tests, scripts: 0); the only hits are dated records (the audit track's B3a-14 text, the T2.03/T2.45 plans, the 2026-08-24 spec, this plan and register), which are history and are not rewritten; the commit body quotes the search and the count_distinct_origins oracle files (git log -1 0bb607fd) |
| 293 | Task 20 discovered: _ORPHANED_PROVENANCE keeps the text-cast join; REST memory delete withdrawal has no lock bound | - | - | open | - |
| 294 | Task 21 minor: backend/tests/test_restore_refine_project_tags.py:1544 — the `DATABASE_URL` setenv has no effect on the script | - | - | open | - |
| 295 | Task 21 minor: backend/scripts/restore_refine_project_tags.py:531 — the `#!/usr/bin/env python` shebang does not resolve on this host | - | - | open | - |
| 296 | Task 21 minor: backend/app/services/memory_dream.py:0 — `build_refine_messages` still shows the model the memory's current tags | - | - | open | - |
| 297 | Task 21 discovered: refine prompt still shows current tags as context; benchlib suites sharing the bench DB collide when run in one -n 4 invocation with tests/ | - | - | open | - |
| 298 | Task 25 minor: test_claim_serving_gates' AGGREGATES_NAMING_THE_RUNG comment still says article_eligibility's consumer "is held shut by G-D" (G-D cleared on the entailment role) | - | - | open | - |
| 299 | Task 29 minor: backend/tests/test_repo_fetch_safety.py:330 — `import pytest` is unused | - | - | open | - |
| 300 | Task 29 minor: backend/app/services/repo_manager.py:250 — No test covers `_reclone` releasing its claim when the clone raises or is cancelled | - | - | open | - |
| 301 | Task 29 discovered: a failed re-clone restores ready with the tree gone (the next index tick fails as before | - | - | open | - |
| 302 | Task 30 minor: backend/app/services/index_debt.py:5 — stale references to the removed `_delete_file_data` | - | - | open | - |
| 303 | Task 30 minor: backend/tests/test_code_index_cost.py:1921 — phase 07 reuse of phase 06's resolver is not asserted | - | - | open | - |
| 304 | Task 30 minor: backend/app/services/job_runners.py:1537 — a deploy that changes `assert_repo_graph` never re-derives repositories whose HEAD has not moved | - | - | open | - |
| 305 | Task 30 minor: backend/app/services/code_pipeline.py:302 — phase 01's `_list_all_files` moved to `asyncio.to_thread`, which the brief did not request | - | - | open | - |
| 306 | Task 30 minor: backend/tests/test_repo_lifecycle_journal.py:186 — the fake vector repository still stubs only the old `delete_code_chunks_by_file` | - | - | open | - |
| 307 | Task 30 parked: cv-revision-on-populated-db: 0004 ran only on an empty lane database | - | - | deferred | Ruling: the revision is two CREATE INDEX IF NOT EXISTS on an existing table and touches no row; Task 71 runs every new revision against a restored backup before the branch ships |
| 308 | Task 30 discovered: per-file enrichment snapshot query remains, stale cache/state entries for deleted repos, Task 20 reconcile stamp still wakes hourly | - | - | open | - |
| 309 | Task 31 minor: backend/app/services/code_pipeline.py:57 — the phase-skip digest covers edges only, not the node properties phases 09-10 read | - | - | open | - |
| 310 | Task 31 minor: backend/tests/test_code_graph_keys.py:933 — the community-stability test never shifts Leiden's community ids | - | - | open | - |
| 311 | Task 31 minor: backend/tests/test_code_graph_keys.py:1019 — the "decorated framework entry point" case scores no decorated node | - | - | open | - |
| 312 | Task 31 minor: backend/app/utils/graph_keys.py:18 — a property key is now textually identical to a same-named method key in the same owner | - | - | open | - |
| 313 | Task 31 minor: a property key name::file::Owner is textually equal to a same-named method key; nodes differ by kind, and key-only joins (the re-verifier, by design) could hit both | - | - | open | - |
| 314 | Task 31 discovered: property and method keys can be textually equal (kinds differ | - | - | open | - |
| 315 | Task 33 minor: put_document with embed_inline=False carries no vectors across a re-file (no fingerprint is resolved without an embedder), so a board register edit leaves every block for the sweep | - | - | open | - |
| 316 | Task 34 minor: backend/tests/test_document_attachment_concurrency.py:582 — the two "write within 2 s" tests assume the cleanup's exclusive request is queued after a fixed `asyncio.sleep(0.2)` | - | - | open | - |
| 317 | Task 34 minor: backend/app/services/page_attachments.py:253 — `store_upload` has no caller in the app any more; only tests use it | - | - | open | - |
| 318 | Task 34 minor: backend/app/api/routes/page_attachments.py:98 — a missing or trashed page now answers 404 only after the whole body (up to `attachment_max_bytes`) has been written to disk | - | - | open | - |
| 319 | Task 34 minor: backend/app/services/page_attachments.py:174 — an upload whose stream stalls for more than an hour can have its `.part` deleted by the cleanup and then fail with a 500 | - | - | open | - |
| 320 | Task 34 minor: page_attachments.insert_attachment_row's docstring still says an import writes attachment rows, pages and journal in one transaction (agy) | - | - | open | - |
| 321 | Task 34 minor: page_import._withdraw_attachments' rollback in its except handler is unguarded, so a dead connection there masks the import's original exception (agy) | - | - | open | - |
| 322 | Task 35 minor: backend/app/services/document_ingest.py:307 — `REVISIONS_PRUNED_EVENT` is a public module constant that is missing from `__all__`, unlike its sibling `DOCUMENT_FILED_EVENT` | - | - | open | - |
| 323 | Task 35 minor: CLAUDE.md:41 — the edited retention sentence runs well past the paragraph's wrap width ("…(the newest 50 and any younger than 90 days stay). Pasted secrets go through") | - | - | open | - |
| 324 | Task 35 minor: backend/app/services/document_ingest.py:328 — a block-first document never files another revision, so its pre-conversion history is never pruned and stays until the document is deleted | - | - | open | - |
| 325 | Task 36 minor: page_door.create_page still runs reproduces_source (a second markdown parse) on the event loop after the off-loop parse | - | - | open | - |
| 326 | Task 38 minor: backend/pyproject.toml:8 — `fastapi>=0.115.0` admits versions that lack `Depends(..., scope=...)` | - | - | open | - |
| 327 | Task 38 minor: backend/tests/test_session_scope.py:60 — the streaming-route detection is a source-text match on `"StreamingResponse("` | - | - | open | - |
| 328 | Task 38 minor: backend/tests/test_session_scope.py:100 — `assert checked > 100` is a magic floor | - | - | open | - |
| 329 | Task 38 discovered: three docstrings still say request-scoped for the per-request session (dream_undo, buffer_flush, repos | - | - | open | - |
| 330 | Task 41 minor: frontend/src/hooks/api/use-pipeline-api.ts's health type carries classifier_unavailable but not pipeline_state; nothing in the SPA reads the new key yet | - | - | open | - |
| 331 | Task 42 minor: automated security review — session_revocations loads once per process, so a revocation written outside the app's auth routes (manual SQL, a restore without an app restart) reaches open sockets only at restart; REST still checks the database per request, the auth routes are the only writers (grep: TokenBlocklist and admin_password_changed_at are written only in routes/auth.py), and the restore cycle stops the app; a once-a-minute process-wide reload would close it at one query per minute — passed to the Task 42 review | - | - | open | - |
| 332 | Task 42 minor: backend/app/api/websocket.py:244 — revocations written outside the three auth routes reach already-open sockets only after a restart (automated security review, deferred in the ledger) | - | - | open | - |
| 333 | Task 42 minor: backend/app/api/websocket.py:338 — validating before the send lock opens a window in which a socket revoked while the broadcast waits for the lock still gets the message | - | - | open | - |
| 334 | Task 42 minor: backend/tests/test_mcp_call_log_flush.py:848 — `assert mcp_call_log._INSERT_SQL is real_insert` asserts nothing, and the test makes the session factory fail rather than the INSERT | - | - | open | - |
| 335 | Task 42 minor: mcp_call_log row-by-row pass counts a refused row as dropped before a later outage in the same pass requeues the batch, so that row can be counted twice (rereview-1) | - | - | open | - |
| 336 | Task 42 minor: mcp_call_log classes InterfaceError as an outage, and asyncpg maps some deterministic client-side encode errors to it, so such a batch would retry at 60 s indefinitely now the attempt cap is gone (rereview-1) | - | - | open | - |
| 337 | Task 42 minor: REST require_auth still runs the blocklist and epoch queries per request; only sockets read session_revocations | - | - | open | - |
| 338 | Task 42 minor: mcp_call_log.drain stops early when a whole batch is dropped (flush_once returns 0 for it), leaving later entries queued at shutdown (rereview-2) | - | - | open | - |
| 339 | Task 42 minor: backend/app/services/mcp_call_log.py:261 — flush_once returns `len(rows) - refused`, so a batch whose entries were all dropped (unbuildable or refused) returns 0 with a non-empty buffer and `drain` (:325) stops early, leaving later queued calls unwritten at shutdown/test drain | - | - | open | - |
| 340 | Task 42 minor: .dforge/sdd/2026-11-20-audit-remaining/task-42-report.md:55 — the round 2 paragraph names the two new tests but shows no run output; the only `Verified` line before it (129 passed) predates the two new tests | - | - | open | - |
| 341 | Task 43 minor: until Task 45 the SPA Flags tab still renders the context-match and topic-summaries controls, and a save naming w_context_boost or community_injection_enabled now answers 422; frontend fixtures still carry by_context_conflict | - | - | open | - |
| 342 | Task 43 minor: the declared-context chain (MemorySearchRequest.context, X-Darkmem-Context, the envelope context echo, the SDK declareContext verb) now reaches no ranking at all — an owner decision whether to keep or remove the wire surface | - | - | open | - |
| 343 | Task 44 minor: until Task 45 the SPA Distribution tab reads policy, watched and refresh from GET /api/v1/distribution and saves through the removed PUT /policy (404); frontend comments in event-taxonomy.ts, use-day-events.ts, day-tab.tsx, demo/types.ts and use-distribution-api.ts still name the deleted inject modules | - | - | open | - |
| 344 | Task 45 discovered: the Distribution live half has no demo render, proven by component test only | - | - | open | - |
| 345 | Task 46 minor: facts_channel.SEMANTIC_ARM_OWNER "T2.33" is still served as the fact trace's semantic_deferred_to, naming a task whose writer is now removed (a wire value, left) | - | - | open | - |
| 346 | Task 46 minor: embedder_registry's module docstring says registration creates "the four child tables" (stale before this task; nine families now) | - | - | open | - |
| 347 | Task 46 minor: backend/app/services/facts_channel.py:108 — the comment above `SEMANTIC_ARM_OWNER` still says it names "the task that ships the ``triple_embeddings`` writer" | - | - | open | - |
| 348 | Task 46 minor: backend/app/services/block_embeddings.py:65 — re-flowed docstring lines run past the file's wrap width | - | - | open | - |
| 349 | Task 46 discovered: SEMANTIC_ARM_OWNER still serves T2.33 on the fact trace, registry docstring says four child tables | - | - | open | - |
| 350 | Task 47 discovered: the model reflection test needed a declared unmapped column | - | - | open | - |
| 351 | Task 48 minor: some test file commits a (postgresql, database) entity and leaves it in the worker database; test_repo_entity_merge's rolled-back calibration pair would collide with it the same way when they share a worker | - | - | open | - |
| 352 | Task 48 minor: docs/two-door-parity.md:0 — the new MCP `unsupported_source` envelope is not recorded on the documents.write row | - | - | open | - |
| 353 | Task 48 minor: backend/tests/test_document_parsers.py:1227 — the REST assertion ORs the two messages, so neither parametrized case pins which refusal it produced | - | - | open | - |
| 354 | Task 48 minor: backend/tests/test_document_parsers.py:1204 — a mid-file `from tests.test_document_routes import stub_llm` with `noqa: E402` | - | - | open | - |
| 355 | Task 48 discovered: memory search arms break no ties (Important, deferred), a committed postgresql entity leaks across test files | - | - | open | - |
| 356 | Task 49 minor: frontend/src/features/code/components/real-code-graph-view.tsx — the Copy Mermaid trigger stretches to the dialog width (grid item), as the old button did | - | - | open | - |
| 357 | Task 49 minor: frontend/src/features/settings/components/backups-tab.tsx — the restore command's Copy is now the library's outline trigger (was a ghost button); ClipboardTrigger takes no variant | - | - | open | - |
| 358 | Task 49 discovered: Copy Mermaid trigger stretches full width, backups Copy is outline not ghost | - | - | open | - |
| 359 | Task 50 minor: .storybook/preview.tsx — its RouterProvider renders a root route with no index, so every story shows "Not Found" at the top-left unless the story covers it | - | - | open | - |
| 360 | Task 50 minor: frontend/src/lib/api.ts — a 500 with an error envelope surfaces as "API error: 500" rather than the envelope's message in every failed state's description | - | - | open | - |
| 361 | Task 50 discovered: Storybook preview prints Not Found above every story, failed descriptions read API error: 500 | - | - | open | - |
| 362 | Task 54 minor: with hundreds of islands neither collide path fully separates them (400 random-size islands: 24% worst penetration on the pair loop at HEAD, 30% on the grid); the final 50 collision passes do not converge there | - | - | open | - |
| 363 | Task 54 minor: constellation-runner's mirror still builds two Maps per frame (pos and fitCoreToFarthest) on the code canvas; only the island runner's arrange was made allocation-free | - | - | open | - |
| 364 | Task 54 discovered: hundreds of islands do not fully separate (pre-existing), the code canvas mirror still allocates per frame | - | - | open | - |
| 365 | Task 55 minor: lib/portal-overlays.ts's remaining export ignorePortaledOverlayPointerDown has no importer outside its own file (grep over frontend/src) | - | - | open | - |
| 366 | Task 55 minor: the Backups tab's failed read is still a plain red line with no Retry (its binding exposes no refetch); the other Settings tabs now use the shared failed state | - | - | open | - |
| 367 | Task 55 discovered: ignorePortaledOverlayPointerDown is unused, the Backups failed read has no Retry | - | - | open | - |
| 368 | Task 56 minor: backend/scripts/e2e/tests/test_session_rotation.py:72 — the password-restore `finally` does not cover the change-password rotation itself | - | - | open | - |
| 369 | Task 56 minor: backend/app/api/websocket.py:146 — a rotation now waits behind any in-flight broadcast's sends | - | - | open | - |
| 370 | Task 56 minor: backend/tests/test_websocket.py:319 — `_shut(renewed_task)` sits inside the `try` body, so a failed assertion above it leaks the renewed socket's endpoint task | - | - | open | - |
| 371 | Task 56 minor: backend/app/api/routes/auth.py:30 — a cancellation while close_renewed_sockets awaits the send lock leaves the jti marked renewed with no forget_renewed, since the try only wraps the commit | - | - | open | - |
| 372 | Task 56 discovered: run_e2e.py BLOCKS on the default localhost model URL, a concurrent unit run on the same test database drops the e2e stack schema, a rotation waits behind in-flight broadcast sends | - | - | open | - |
| 373 | Task 57 discovered: the server has no session-lifetime setting for a running-app renewal proof | - | - | open | - |
| 374 | Task 58 discovered: search and paginated POST queries still pass no signal | - | - | open | - |
| 375 | Task 59 minor: five mutation onSuccess calls in hooks/api (use-memory-api x3, use-memory-buffer-api, use-code-api repoStats x4 and codeSymbols) still invalidate keys no query reads; harmless no-ops, and use-memory-buffer-api.test.tsx pins the memories one | - | - | open | - |
| 376 | Task 61 minor: the documents editor has no unload or navigation guard, so a held (saving or refused) block write and the writes queued behind it are lost when the operator leaves the document | - | - | open | - |
| 377 | Task 67 minor: scripts/backup.sh:625 — `.suspect` dumps are never pruned | - | - | open | - |
| 378 | Task 67 minor: [lens:lang-bash] scripts/worker/restore-cycle.sh:722 — the image-hash probe `$COMPOSE run` has no timeout | - | - | open | - |
| 379 | Task 67 minor: backend/tests/test_backup_script.py:245 — PEP 8 blank-line drift | - | - | open | - |
| 380 | Task 70 minor: at 1280x800 the Code Graph canvas is a 176 px strip between explorer, source pane and inspector, and one run's node click registered only after a window resize (Sigma follows window, not container, resize); git diff master -- frontend/src/features/code changes no pane width or resize handling, so it predates this branch | - | - | open | - |
| 381 | Task 70 minor: the Review queue's fact row nests a library Badge (div) inside a <p> (React warning), and axe reports list, target-size, nested-interactive (chat row containing Delete), aria-valid-attr-value and label findings on controls this branch did not change | - | - | open | - |
| 382 | Task 70 minor: the chat conversation row (role=button) contains its Delete button (axe nested-interactive); chat-sidebar.tsx is unchanged on this branch (last changed in 3f8aa650 on master), so it predates the branch | - | - | open | - |
| 383 | Task 70 discovered: Code Graph canvas 176 px at 1280x800 and the chat row nested Delete, both predating the branch, deferred | - | - | open | - |
| 384 | Task 71 minor: docs/dforge/registers/2026-11-20-audit-remaining.md:0 — the Step 3.3 EXPLAIN result is recorded in no tracked file | - | - | open | - |
| 385 | Task 71 minor: .dforge/sdd/2026-11-20-audit-remaining/task-71-report.md:24 — the Verified list reduces every command to "pass: 1 passed, 0 failed" and omits the EXPLAIN and post-drop checks | - | - | open | - |
| 386 | Task 71 minor: docs/dforge/registers/2026-11-20-audit-remaining.md:216 — row 216 is `done` with no commit sha in its Note | - | - | open | - |
| 387 | Task 71 discovered: production holds 0 code_edges rows, dev Postgres volume at 95 percent | - | - | open | - |
| 388 | UI proof judge (Important): failed-captures Discard stays enabled while a Requeue or Discard for its row runs; a confirm then sends nothing and says nothing (ab64a325 guard), and no test covers it | - | - | open | - |
| 389 | UI proof judge (minor): opening a block in the document editor puts the caret at the start, so typed text lands before the existing text | - | - | open | - |
| 390 | UI proof judge (minor): in the dark theme some disabled buttons look enabled (fix-wave fw-* screenshots) | - | - | open | - |
| 391 | Final review silent-failures, REST half: GET/POST /code/search answers a bare list with no per-arm marker when the keyword arm fails | - | - | deferred | Ruling: needs a response-schema change and SDK regeneration; Task 16's ruling stands (final-fix-report REJECTED-in-part) |
