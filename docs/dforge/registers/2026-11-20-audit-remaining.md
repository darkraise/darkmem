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
| 20 | B2-4: no door passes a declared context, so w_context_boost never fires and community_injection_enabled has no reader (owner ruling 2026-11-20: remove) | docs/dforge/plans/2026-11-20-audit-remaining.md | A45 (Task 43/45) | doing | - |
| 21 | B2-6: chat leaves a transaction open, holding a pooled connection for the whole LLM stream | docs/dforge/plans/2026-11-20-audit-remaining.md | test: Task 14 contracts | done | 05e7497 |
| 22 | B2-7: on client disconnect the finally usage write is cancelled, so the row is lost | docs/dforge/plans/2026-11-20-audit-remaining.md | test: Task 14 contracts | done | 05e7497 |
| 23 | B2-8 and B3b-21: every project-scoped composed search embeds the query twice | docs/dforge/plans/2026-11-20-audit-remaining.md | test: Task 15 contracts | done | 3c69d90 |
| 24 | B2-9: a full provisional compose pass runs on every request to feed a reranker no production caller passes | docs/dforge/plans/2026-11-20-audit-remaining.md | test: Task 15 contracts | done | 3c69d90 |
| 25 | B2-11: watch_refresh, fill and inject_block are reached only by tests, so the Distribution tab's token budget, watch switch and curb steer nothing (owner ruling 2026-11-20: remove) | docs/dforge/plans/2026-11-20-audit-remaining.md | A44 (Task 44/45) | doing | - |
| 26 | B2-12 and B3a-5: triple_embeddings.py has no production caller, yet every embedder registration creates an empty table and index (owner ruling 2026-11-20: remove and drop) | docs/dforge/plans/2026-11-20-audit-remaining.md | A46 (Task 46) | doing | - |
| 27 | B2-13: useVectorProjection has no consumer, and the route runs eigh inline on the event loop | docs/dforge/plans/2026-11-20-audit-remaining.md | test: Task 17/45 contracts | doing | - |
| 28 | B2-14: RRF is implemented again inline twice in code_query, whose arms lack savepoints and swallow failures | docs/dforge/plans/2026-11-20-audit-remaining.md | test: Task 16 contracts | done | 206716a |
| 29 | B2-15: graph path ids typed as str reach CAST AS uuid; an uppercase UUID lists the seed as its own neighbour; the 20 neighbours are an arbitrary slice | docs/dforge/plans/2026-11-20-audit-remaining.md | test: Task 16 contracts | done | 206716a |
| 30 | B2-16: FactsChannel.search is tests-only, the row-level dispute block is superseded, and the docstring is stale | docs/dforge/plans/2026-11-20-audit-remaining.md | test: Task 15 contracts | done | 3c69d90 |
| 31 | B2-17: search and search_with_trace duplicate the whole pipeline | docs/dforge/plans/2026-11-20-audit-remaining.md | test: Task 15 contracts | done | 3c69d90 |
| 32 | B2-18: flag_measurements is read but nothing writes it, so every flag shows unmeasured forever | docs/dforge/plans/2026-11-20-audit-remaining.md | test: Task 17/45 contracts | doing | - |
| 33 | B2-19: chat content has no length limit, and an untyped context with a non-string mention raises mid-stream | docs/dforge/plans/2026-11-20-audit-remaining.md | test: Task 14 contracts | done | 05e7497 |
| 34 | B2-20: CLUSTER_RE is unused, and the cluster: filter can never match | docs/dforge/plans/2026-11-20-audit-remaining.md | test: Task 14 contracts | done | 05e7497 |
| 35 | B2-21: with hybrid search off, the pure-vector and read-only branches never call _record_access | docs/dforge/plans/2026-11-20-audit-remaining.md | test: Task 6 contracts | done | d9337ef |
| 36 | B2-22: the hand-maintained route inventory trips on every new route or tool (owner decision) | - | - | deferred | declined in the spec: the inventory is the enumeration guard; moving it onto route metadata is its own design |
| 37 | B3a-1 (high): fact_lift and re-extraction can interleave so a fact keeps a source the memory no longer asserts; needs a two-session test | docs/dforge/plans/2026-11-20-audit-remaining.md | A1 (Task 18) | done | 635ebff |
| 38 | B3a-2 and B3b-11: while the judge refuses, the contradiction scan re-drains the same 20 events every 6 hours and re-commits duplicate clean verdicts | docs/dforge/plans/2026-11-20-audit-remaining.md | A24 (Task 19) | done | f5f8bdbe |
| 39 | B3a-3: the slow arm re-journals an identical blocked hold on every visit | docs/dforge/plans/2026-11-20-audit-remaining.md | test: Task 19 contracts | done | f5f8bdbe |
| 40 | B3a-4: knowledge_triples.stated_expiry has no production writer, so the every-2-minute close arm, its partial index and the merge's LEAST logic are dead (owner ruling 2026-11-20: remove and drop) | docs/dforge/plans/2026-11-20-audit-remaining.md | A47 (Task 47) | doing | - |
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
| 57 | B3b-5: CLAUDE.md says groundedness_gate stays closed, but the article surfaces gate on article_claim_gate; stale docstring | docs/dforge/plans/2026-11-20-audit-remaining.md | test: Task 25 contracts | doing | - |
| 58 | B3b-6: article gather, hash and staleness key on the subject name only while eligibility keys on name and entity_type | docs/dforge/plans/2026-11-20-audit-remaining.md | A23 (Task 24) | doing | - |
| 59 | B3b-7: pinned subjects with zero facts fill synthesis_budget on every tick | docs/dforge/plans/2026-11-20-audit-remaining.md | test: Task 24 contracts | doing | - |
| 60 | B3b-8: dream and hygiene actions ignore record_event's False return | docs/dforge/plans/2026-11-20-audit-remaining.md | A22 (Task 22) | done | b17e7fb |
| 61 | B3b-9: asymmetric top-N proximity appends a phantom associate journal row each rotation | docs/dforge/plans/2026-11-20-audit-remaining.md | test: Task 22 contracts | done | b17e7fb |
| 62 | B3b-10 and B3b-R1: the derivation contradiction arm is unreachable because EXCLUSIVE_RELATION_FAMILIES ships empty | docs/dforge/plans/2026-11-20-audit-remaining.md | test: Task 23 contracts | done | e352460 |
| 63 | B3b-12: re-synthesis attempts every settled stale article with no per-tick budget | docs/dforge/plans/2026-11-20-audit-remaining.md | test: Task 24 contracts | doing | - |
| 64 | B3b-13: a lock_timeout during undo surfaces as a 500 rather than a retryable conflict | docs/dforge/plans/2026-11-20-audit-remaining.md | test: Task 22 contracts | done | b17e7fb |
| 65 | B3b-14 and B3b-R4: undo's all-or-nothing holds only because the single HTTP caller rolls back; wrap the write phase in one begin_nested() | - | - | deferred | declined in the spec: CLAUDE.md records the no-savepoint shape as contract and an AST scan enforces it |
| 66 | B3b-15: cursor helpers, the article-gate resolver, the locked memory projection and the fact-set hash queries are each duplicated | docs/dforge/plans/2026-11-20-audit-remaining.md | test: Task 25 contracts | doing | - |
| 67 | B3b-16 and B3b-R3: the ResearchGatherer Protocol has one implementation that returns a supplied list; server.py wrongly calls the authenticated door unauthenticated | docs/dforge/plans/2026-11-20-audit-remaining.md | test: Task 25 contracts | doing | - |
| 68 | B3b-18: stale docstrings and annotations in article_synthesis, review_queue, hygiene_queue and verification_judge | docs/dforge/plans/2026-11-20-audit-remaining.md | test: Task 25 contracts | doing | - |
| 69 | B3b-19: the article runner discards both outcomes and logs nothing | docs/dforge/plans/2026-11-20-audit-remaining.md | test: Task 24 contracts | doing | - |
| 70 | B3b-20: the dispute-onset lateral on events has no created_at bound | docs/dforge/plans/2026-11-20-audit-remaining.md | test: Task 24 contracts | doing | - |
| 71 | B3b-17 and B3b-R6: research_rerun is a 320-line wrapper, live through the Settings Research UI | - | - | deferred | kept: the reviewer's own remedy is to keep it while the UI button exists |
| 72 | B3b-R7: review_ranking has one consumer and could be folded into review_queue (optional) | - | - | deferred | declined in the spec: saves no lines |
| 73 | B4-4: the working-tree drift scan hashes every file synchronously on the event loop | docs/dforge/plans/2026-11-20-audit-remaining.md | test: Task 30 contracts | doing | - |
| 74 | B4-5: per-file deletes scan the whole repository's edge and node tables | docs/dforge/plans/2026-11-20-audit-remaining.md | test: Task 30 contracts | doing | - |
| 75 | B4-6: one failed embed loses that file's code chunks until the file changes again | docs/dforge/plans/2026-11-20-audit-remaining.md | A33 (Task 28) | doing | - |
| 76 | B4-7: incremental diff parsing breaks on non-ASCII and special-character paths | docs/dforge/plans/2026-11-20-audit-remaining.md | A34 (Task 28) | doing | - |
| 77 | B4-8: incremental runs mis-key cross-file base classes defined in unchanged files | docs/dforge/plans/2026-11-20-audit-remaining.md | A34 (Task 28) | doing | - |
| 78 | B4-9 and F1-4 backend half: blast radius and symbol lookup ignore repository and owner | docs/dforge/plans/2026-11-20-audit-remaining.md | A35 (Task 26) | doing | - |
| 79 | B4-10 and B6-4: MCP code_symbol probably raises MissingGreenlet on any hit; no result limit | docs/dforge/plans/2026-11-20-audit-remaining.md | A35 (Task 26) | doing | - |
| 80 | B4-11: unchanged dependent and debt files are re-embedded on every incremental run | docs/dforge/plans/2026-11-20-audit-remaining.md | A33 (Task 28) | doing | - |
| 81 | B4-12: MCP code_search returns nothing without an embedder, while REST answers from the keyword arm | docs/dforge/plans/2026-11-20-audit-remaining.md | A14 (Task 27) | doing | - |
| 82 | B4-13: a transient fetch failure deletes the managed clone and re-clones it, with no claim held | docs/dforge/plans/2026-11-20-audit-remaining.md | A36 (Task 29) | doing | - |
| 83 | B4-14: a file whose parse times out or raises is re-detected as drift on every tick | docs/dforge/plans/2026-11-20-audit-remaining.md | test: Task 30 contracts | doing | - |
| 84 | B4-15: query-per-item loops in phases 03, 05 and 06 | docs/dforge/plans/2026-11-20-audit-remaining.md | test: Task 30 contracts | doing | - |
| 85 | B4-16: phase 08 seeds every file's type environment with every symbol's return type, keyed by function name | docs/dforge/plans/2026-11-20-audit-remaining.md | test: Task 31 contracts | doing | - |
| 86 | B4-17: Leiden and process tracing rewrite the repo's whole community/process layer on every run, under non-deterministic keys | docs/dforge/plans/2026-11-20-audit-remaining.md | test: Task 31 contracts | doing | - |
| 87 | B4-18: property nodes are keyed by bare name and deleted together with the first owner's file | docs/dforge/plans/2026-11-20-audit-remaining.md | test: Task 31 contracts | doing | - |
| 88 | B4-19: failure paths store unsanitised exception text; tokens sit in the git argv | docs/dforge/plans/2026-11-20-audit-remaining.md | A36 (Task 29) | done | 9124abd |
| 89 | B4-20: a local checkout's fetch lane fast-forwards whichever branch is checked out | docs/dforge/plans/2026-11-20-audit-remaining.md | test: Task 3 contracts | doing | - |
| 90 | B4-21 and removal 5: the wiki config row is orphaned on repo delete, and the cache check is dead | docs/dforge/plans/2026-11-20-audit-remaining.md | test: Task 32 contracts | doing | - |
| 91 | B4-22: process_tracer reads a signature property nothing writes | docs/dforge/plans/2026-11-20-audit-remaining.md | test: Task 31 contracts | doing | - |
| 92 | B4-23: code_deriver strips and rewrites every repo's assertions hourly, whether or not HEAD moved | docs/dforge/plans/2026-11-20-audit-remaining.md | test: Task 30 contracts | doing | - |
| 93 | B4-24: cancel_repo_task does not check that the task belongs to the repository in the URL | docs/dforge/plans/2026-11-20-audit-remaining.md | test: Task 29 contracts | doing | - |
| 94 | B4-25: doc and comment drift in code_pipeline and repo_allowlist; CodeFile.last_commit_sha is served but never written | docs/dforge/plans/2026-11-20-audit-remaining.md | test: Task 32 contracts | doing | - |
| 95 | B4 removals 3, 4, 6, 7: TaskRegistry.get_all_running and cleanup_completed, the CallResolver named_imports/wildcard_imports arguments, RepoManager.get_auth_token, _implements_split's discarded return value | docs/dforge/plans/2026-11-20-audit-remaining.md | test: Task 32 contracts | doing | - |
| 96 | B4 removal 8: the CodeFile.last_commit_sha column | docs/dforge/plans/2026-11-20-audit-remaining.md | A47 (Task 32) | doing | - |
| 97 | B5-2: a document block edit drops no vectors, so a failed embed after commit leaves the old-text vector forever and the route answers 500 for a write that landed | docs/dforge/plans/2026-11-20-audit-remaining.md | A25 (Task 33) | doing | - |
| 98 | B5-3: upload streams up to 50 MB inside the global attachment lock and an open transaction; the Notion import holds the same lock for up to 900 s | docs/dforge/plans/2026-11-20-audit-remaining.md | A26 (Task 34) | doing | - |
| 99 | B5-4: any content change re-embeds every block inline, and every unchanged re-push spends a real embed call | docs/dforge/plans/2026-11-20-audit-remaining.md | A28 (Task 33) | doing | - |
| 100 | B5-5: _PLACE rewrites every block row of the tree on every verb | docs/dforge/plans/2026-11-20-audit-remaining.md | test: Task 36 contracts | doing | - |
| 101 | B5-6: blocks.search_vector and ix_blocks_search_vector have no reader (owner ruling 2026-11-20: drop) | docs/dforge/plans/2026-11-20-audit-remaining.md | A46 (Task 48) | doing | - |
| 102 | B5-7: document_revisions stores a full content copy on every hash-changing put, with no prune | docs/dforge/plans/2026-11-20-audit-remaining.md | A27 (Task 35) | doing | - |
| 103 | B5-8: substring(content ...) runs once per joined block row over a TOASTed content | docs/dforge/plans/2026-11-20-audit-remaining.md | test: Task 36 contracts | doing | - |
| 104 | B5-9: markdown-it parses up to 1M characters on the event loop, and MAX_BLOCKS is enforced only after every block row is inserted | docs/dforge/plans/2026-11-20-audit-remaining.md | test: Task 36 contracts | doing | - |
| 105 | B5-10: rename_documents takes no actor/api_key_id, so subtree renames journal with no attribution | docs/dforge/plans/2026-11-20-audit-remaining.md | test: Task 37 contracts | doing | - |
| 106 | B5-11: parse_pdf cannot be reached in production; it still carries pdfplumber, pdfminer-six, pillow and pypdfium2 (owner ruling 2026-11-20: remove) | docs/dforge/plans/2026-11-20-audit-remaining.md | A48 (Task 48) | doing | - |
| 107 | B5-12: ingest_documents, DocumentSource, file_documents_isolated, DocumentFileJob, DocumentFileFailure, resolve_read_fingerprint and block_vectors have only test callers | docs/dforge/plans/2026-11-20-audit-remaining.md | test: Task 37 contracts | doing | - |
| 108 | B5-13: parent_id, after_block_id and new_parent_id are typed str on the document block routes, so a malformed id gets a 500 | docs/dforge/plans/2026-11-20-audit-remaining.md | test: Task 37 contracts | doing | - |
| 109 | B5-14: document connections run one uncached ANN probe per block on every document view | docs/dforge/plans/2026-11-20-audit-remaining.md | test: Task 36 contracts | doing | - |
| 110 | B5-15: the document list joins and groups every block of every document before LIMIT/OFFSET | docs/dforge/plans/2026-11-20-audit-remaining.md | test: Task 36 contracts | doing | - |
| 111 | B5-16: an unembeddable block stays in the first batch and costs a failed batch call plus up to 500 single-row embeds on every tick | docs/dforge/plans/2026-11-20-audit-remaining.md | test: Task 33 contracts | doing | - |
| 112 | B5-17: four copies of the same register-the-fingerprint helper | docs/dforge/plans/2026-11-20-audit-remaining.md | test: Task 33 contracts | doing | - |
| 113 | B6-2: login runs bcrypt on the event loop, and the lockout check happens before an await, so concurrent attempts exceed five guesses | docs/dforge/plans/2026-11-20-audit-remaining.md | A7 (Task 1) | done | 1d02a7c |
| 114 | B6-3: MCP memory_reason, memory_overview and document_search call the LLM or embedder on the read-only backup worker | docs/dforge/plans/2026-11-20-audit-remaining.md | A12 (Task 5) | done | 7d6e56b |
| 115 | B6-5: get_session commits after the response is sent, so routes without an explicit commit return 200 before the write is durable | docs/dforge/plans/2026-11-20-audit-remaining.md | A29 (Task 38) | doing | - |
| 116 | B6-6: the CORS fallback grants credentialed cross-origin access to localhost:3000 and :5173 | docs/dforge/plans/2026-11-20-audit-remaining.md | A8 (Task 1) | done | 1d02a7c |
| 117 | B6-7: SSH destination user/host go unvalidated into the ssh/scp argv | docs/dforge/plans/2026-11-20-audit-remaining.md | A9 (Task 3) | done | 9124abd |
| 118 | B6-8: every MCP request and every keyed REST call pays a fresh bcrypt | docs/dforge/plans/2026-11-20-audit-remaining.md | A11 (Task 2) | done | 6eb3cde |
| 119 | B6-9: min_interval_seconds is persisted into the job row on first save, so raising a floor in code never takes effect | docs/dforge/plans/2026-11-20-audit-remaining.md | A30 (Task 40) | doing | - |
| 120 | B6-10: PUT /jobs/{key} and its config twin wait on the per-job run lock | docs/dforge/plans/2026-11-20-audit-remaining.md | A30 (Task 40) | doing | - |
| 121 | B6-12: job_runs.trigger is never written, so the UI's manual badge never renders | docs/dforge/plans/2026-11-20-audit-remaining.md | test: Task 40 contracts | doing | - |
| 122 | B6-13: three hourly cleanup jobs write a maintenance_run row into the permanent journal even when they do nothing | docs/dforge/plans/2026-11-20-audit-remaining.md | test: Task 40 contracts | doing | - |
| 123 | B6-14: any boot exception in the LLM try leaves pipeline=None for the life of the process while /health returns 200 | docs/dforge/plans/2026-11-20-audit-remaining.md | A31 (Task 41) | doing | - |
| 124 | B6-15: code_rename matches with an unescaped LIKE | docs/dforge/plans/2026-11-20-audit-remaining.md | test: Task 27 contracts | doing | - |
| 125 | B6-16: several MCP code tools call scalar_one_or_none() on Repository.name, which is not unique | docs/dforge/plans/2026-11-20-audit-remaining.md | A35 (Task 26) | doing | - |
| 126 | B6-17: a failed MCP call-log flush discards its popped batch uncounted, and validation-error text may echo content | docs/dforge/plans/2026-11-20-audit-remaining.md | test: Task 42 contracts | doing | - |
| 127 | B6-18: a masked secret is resolved by name even when the URL or host changes | docs/dforge/plans/2026-11-20-audit-remaining.md | A10 (Task 3) | done | 9124abd |
| 128 | B6-19 and B6-D3: system-prompts, repo-allowlist and notifications read-modify-write their config rows without the row lock; about 12 config endpoints repeat the pattern three ways | docs/dforge/plans/2026-11-20-audit-remaining.md | A29 (Task 39) | doing | - |
| 129 | B6-20: events partition maintenance rides on pipeline_failure_cleanup, which the UI can disable | docs/dforge/plans/2026-11-20-audit-remaining.md | A32 (Task 41) | doing | - |
| 130 | B6-21: each open WebSocket runs 2 database queries per second for revalidation, serially inside the send lock | docs/dforge/plans/2026-11-20-audit-remaining.md | test: Task 42 contracts | doing | - |
| 131 | B6-22: stale statements: 48 tools, dream jobs called placeholders, the curb row's reader, and LLM_* env vars in CLAUDE.md | docs/dforge/plans/2026-11-20-audit-remaining.md | A51 (Task 69) | doing | - |
| 132 | B6-D1: the lifespan carries boot steps for states that no longer occur | docs/dforge/plans/2026-11-20-audit-remaining.md | test: Task 41 contracts | doing | - |
| 133 | B6-D2: about 830 lines of MCP code tools run raw SQL in the transport instead of CodeQueryService | docs/dforge/plans/2026-11-20-audit-remaining.md | test: Task 27 contracts | doing | - |
| 134 | B6-D4: job last_* state is rewritten into config on every tick | docs/dforge/plans/2026-11-20-audit-remaining.md | A30 (Task 40) | doing | - |
| 135 | B6-D5: inject_* and client_connect live under app/services but are reached at runtime only by a CLI script | docs/dforge/plans/2026-11-20-audit-remaining.md | A51 (Task 69) | doing | - |
| 136 | B6-D6: per-socket, per-second revalidation is a heavy polling contract; close sockets directly and drop the polling | - | - | deferred | declined in the spec: CLAUDE.md records the one-second revalidation as contract; B6-21 removes its cost |
| 137 | F1-1 (high): the Edit Repository dialog cannot save URL-cloned repositories | docs/dforge/plans/2026-11-20-audit-remaining.md | A3 (Task 49) | doing | - |
| 138 | F1-2 (high): the 3D graph data is rebuilt in 2D view, in O(n squared) | docs/dforge/plans/2026-11-20-audit-remaining.md | A4 (Task 53) | doing | - |
| 139 | F1-4: Blast Radius silently fails on the folded graph; no onError handler | docs/dforge/plans/2026-11-20-audit-remaining.md | test: Task 49 contracts | doing | - |
| 140 | F1-5: Code Graph and Wiki show No repositories indexed yet while loading or after an error | docs/dforge/plans/2026-11-20-audit-remaining.md | A41 (Task 50) | doing | - |
| 141 | F1-6: the code canvas rebuilds Sigma and restarts the layout on every keystroke | docs/dforge/plans/2026-11-20-audit-remaining.md | test: Task 51 contracts | doing | - |
| 142 | F1-7: per-frame string-keyed density grid on the memory canvas | docs/dforge/plans/2026-11-20-audit-remaining.md | test: Task 54 contracts | doing | - |
| 143 | F1-9: dead or test-only exports in live modules (graph-geometry hull helpers, lightenHex, clusterAnchors, code-graph-theme colour functions, groupMemories, placeIslands, zoomLevel, setGraphReady, inner GraphSkeleton, duplicate stableHash) | docs/dforge/plans/2026-11-20-audit-remaining.md | test: Task 54 contracts | doing | - |
| 144 | F1-10: wiki and edit-repository mutation failures are not reported | docs/dforge/plans/2026-11-20-audit-remaining.md | test: Task 49 contracts | doing | - |
| 145 | F1-11: Copy Mermaid misreports and fails in production (navigator.clipboard undefined on plain HTTP) | docs/dforge/plans/2026-11-20-audit-remaining.md | test: Task 49 contracts | doing | - |
| 146 | F1-12: clicking an entity in 3D shows the graph summary | docs/dforge/plans/2026-11-20-audit-remaining.md | test: Task 53 contracts | doing | - |
| 147 | F1-13: colour-mode changes rebuild what is already recoloured in place | docs/dforge/plans/2026-11-20-audit-remaining.md | test: Task 53 contracts | doing | - |
| 148 | F1-14: the detail panel's close button has no accessible name | docs/dforge/plans/2026-11-20-audit-remaining.md | test: Task 53 contracts | doing | - |
| 149 | F1-15: graph and code loading and error states are inconsistent | docs/dforge/plans/2026-11-20-audit-remaining.md | A41 (Task 50) | doing | - |
| 150 | F1-16: KIND_CHART defined three times; node sizing differs between 2D and 3D | docs/dforge/plans/2026-11-20-audit-remaining.md | test: Task 54 contracts | doing | - |
| 151 | F1-17: duplicated runner boilerplate and per-frame allocation during layout; collide() is O(k squared) | docs/dforge/plans/2026-11-20-audit-remaining.md | test: Task 54 contracts | doing | - |
| 152 | F1-18: symbolsByFile copies each file's array on every insert | docs/dforge/plans/2026-11-20-audit-remaining.md | test: Task 54 contracts | doing | - |
| 153 | F1-19: the graph payload carries full memory content for up to 50,000 nodes | docs/dforge/plans/2026-11-20-audit-remaining.md | test: Task 52/53 contracts | doing | - |
| 154 | F1-20: every theme consumer runs its own MutationObserver | docs/dforge/plans/2026-11-20-audit-remaining.md | test: Task 54 contracts | doing | - |
| 155 | F1-21: remembered-position maps grow without bound | docs/dforge/plans/2026-11-20-audit-remaining.md | test: Task 54 contracts | doing | - |
| 156 | F1-23: two layout engines; one engine could serve both canvases (owner call) | - | - | deferred | declined in the spec: the code graph would look different, and the constellation plan shipped it two days ago |
| 157 | F2-2: the Maintenance re-embed count goes stale (private cache name) | docs/dforge/plans/2026-11-20-audit-remaining.md | test: Task 58 contracts | doing | - |
| 158 | F2-3: the WebSocket ignores the server's session-expired close and retries forever | docs/dforge/plans/2026-11-20-audit-remaining.md | test: Task 57 contracts | doing | - |
| 159 | F2-4: demo mode still calls the API from Settings LLM | docs/dforge/plans/2026-11-20-audit-remaining.md | A43 (Task 58) | doing | - |
| 160 | F2-5: Settings has five save models, three ways of showing a load failure, and three confirmation styles | docs/dforge/plans/2026-11-20-audit-remaining.md | A37 (Task 55) | doing | - |
| 161 | F2-6: the LLM tab shows blank models and a fixture judge as if real on load failure | docs/dforge/plans/2026-11-20-audit-remaining.md | A41 (Task 50) | doing | - |
| 162 | F2-7: Flags dialogs close on Save before the write lands; edits are lost | docs/dforge/plans/2026-11-20-audit-remaining.md | A37 (Task 55) | doing | - |
| 163 | F2-8: number fields in the Flags dialogs commit only on blur while Save is disabled; one field type clamps silently, the other shows an error | docs/dforge/plans/2026-11-20-audit-remaining.md | test: Task 55 contracts | doing | - |
| 164 | F2-9 and F3-4: the app never calls /auth/refresh, so every session ends hard after 24h and both editors lose in-memory drafts | docs/dforge/plans/2026-11-20-audit-remaining.md | A38 (Task 56/57) | doing | - |
| 165 | F2-10: about 18 exported hooks in hooks/api have no production importer, plus WebSocket cache writes nothing reads | docs/dforge/plans/2026-11-20-audit-remaining.md | test: Task 59 contracts | doing | - |
| 166 | F2-11: unused auth code: useSession, useLogout, LogoutButton, authAdapter.me, lib/api.ts login() | docs/dforge/plans/2026-11-20-audit-remaining.md | test: Task 59 contracts | doing | - |
| 167 | F2-12 remainder: keepDialogOpenOnListEscape (7 call sites) is retirable by its own comment | docs/dforge/plans/2026-11-20-audit-remaining.md | test: Task 55 contracts | doing | - |
| 168 | F2-13: formatDateTime is defined four times; both formatDuration copies print 1m 60s for 119.6 seconds | docs/dforge/plans/2026-11-20-audit-remaining.md | test: Task 58 contracts | doing | - |
| 169 | F2-14: checkSetupStatus ignores the HTTP status, so a server error shows the setup wizard | docs/dforge/plans/2026-11-20-audit-remaining.md | test: Task 58 contracts | doing | - |
| 170 | F2-15: the setup wizard keeps vendor API keys in localStorage until setup finishes | docs/dforge/plans/2026-11-20-audit-remaining.md | A43 (Task 58) | doing | - |
| 171 | F2-16: the Research tab overwrites typed budgets on every reload of its settings | docs/dforge/plans/2026-11-20-audit-remaining.md | test: Task 58 contracts | doing | - |
| 172 | F2-17: in development StrictMode leaves a duplicate WebSocket, so every event toasts twice | docs/dforge/plans/2026-11-20-audit-remaining.md | test: Task 57 contracts | doing | - |
| 173 | F2-18: queries do not pass cancellation signals; the maintenance tab polls /jobs every 5s for one value; the project switcher says No project holds anything yet when loading fails | docs/dforge/plans/2026-11-20-audit-remaining.md | test: Task 50/58 contracts | doing | - |
| 174 | F3-1 (high): sending in a second chat conversation silently aborts the first one's stream, and that answer is lost | docs/dforge/plans/2026-11-20-audit-remaining.md | A2 (Task 60) | doing | - |
| 175 | F3-2: the documents block editor throws away the typed text on any refused or failed write | docs/dforge/plans/2026-11-20-audit-remaining.md | A39 (Task 61) | doing | - |
| 176 | F3-3: hygiene queue checkbox selections survive project and page changes; Supersede instead acts only on the visible page, then clears every selection | docs/dforge/plans/2026-11-20-audit-remaining.md | A40 (Task 63) | doing | - |
| 177 | F3-5: every chat token re-parses the markdown of every earlier message | docs/dforge/plans/2026-11-20-audit-remaining.md | test: Task 60 contracts | doing | - |
| 178 | F3-6: a task filter on an open workstream re-downloads the whole ledger every 5 s | docs/dforge/plans/2026-11-20-audit-remaining.md | test: Task 64 contracts | doing | - |
| 179 | F3-7: after a refusal, the documents write queue re-reads the hash and sends the next write anyway | docs/dforge/plans/2026-11-20-audit-remaining.md | A39 (Task 61) | doing | - |
| 180 | F3-8: a failed page title rename is silent | docs/dforge/plans/2026-11-20-audit-remaining.md | test: Task 64 contracts | doing | - |
| 181 | F3-9a: dead code: useBlockMove, and rank_note/consequence computed but never shown | docs/dforge/plans/2026-11-20-audit-remaining.md | test: Task 59 contracts | doing | - |
| 182 | F3-9b: the pager is hand-written twice although darkraise-ui ships pagination; the two knowledge queues use different list patterns | docs/dforge/plans/2026-11-20-audit-remaining.md | test: Task 63 contracts | doing | - |
| 183 | F3-9c: the two block editors duplicate the hash-precondition plumbing and handle conflicts differently | docs/dforge/plans/2026-11-20-audit-remaining.md | test: Task 61 contracts | doing | - |
| 184 | F3-9d: a first chat turn that never completes leaves an Untitled conversation the client never learns about | docs/dforge/plans/2026-11-20-audit-remaining.md | test: Task 60 contracts | doing | - |
| 185 | F3-9e: deleting a conversation has no error handling | docs/dforge/plans/2026-11-20-audit-remaining.md | test: Task 60 contracts | doing | - |
| 186 | F3-9f: two quick board edits to one register conflict with each other | docs/dforge/plans/2026-11-20-audit-remaining.md | test: Task 64 contracts | doing | - |
| 187 | F3-9g: Notes does a full-document conversion on every keystroke | docs/dforge/plans/2026-11-20-audit-remaining.md | test: Task 64 contracts | doing | - |
| 188 | F3-9h: the facts list's filter options cover only the pages already loaded | docs/dforge/plans/2026-11-20-audit-remaining.md | test: Task 62/63 contracts | doing | - |
| 189 | F3 mirror note: no test pins the TypeScript copy of block_verbs.py's refusals to the Python one | docs/dforge/plans/2026-11-20-audit-remaining.md | test: Task 64 contracts | doing | - |
| 190 | P1-1 (high): the extension's auto-capture stores every partial state of a streaming reply as its own memory | docs/dforge/plans/2026-11-20-audit-remaining.md | A5 (Task 65) | doing | - |
| 191 | P1-2 (high): pull requests can run code on the self-hosted LAN runner; check the fork-approval setting | docs/dforge/plans/2026-11-20-audit-remaining.md | A6 (Task 4) | done | f0b79c0 |
| 192 | P1-3: a cancelled tag job still lets github-release create the tag on master's tip | docs/dforge/plans/2026-11-20-audit-remaining.md | A49 (Task 66) | doing | - |
| 193 | P1-4: numpy is imported but not declared | docs/dforge/plans/2026-11-20-audit-remaining.md | A50 (Task 66) | doing | - |
| 194 | P1-5: third-party actions are pinned to movable tags, not commit SHAs; the trivy job writes the cache publish reads | docs/dforge/plans/2026-11-20-audit-remaining.md | test: Task 4 contracts | done | f0b79c0 |
| 195 | P1-6: CONTRIBUTING.md describes the old release model | docs/dforge/plans/2026-11-20-audit-remaining.md | A51 (Task 69) | doing | - |
| 196 | P1-7: release.sh cannot finish on this host (it runs gate.sh --full) | docs/dforge/plans/2026-11-20-audit-remaining.md | test: Task 66 contracts | doing | - |
| 197 | P1-8: the e2e database reset bypasses the destructive-SQL guard on a false premise | docs/dforge/plans/2026-11-20-audit-remaining.md | test: Task 4 contracts | done | f0b79c0 |
| 198 | P1-9: the worker's restore loop treats every migrate failure as an old-baseline snapshot and exits 0 | docs/dforge/plans/2026-11-20-audit-remaining.md | A49 (Task 67) | doing | - |
| 199 | P1-10: start_dev_server.sh calls bare python and by default migrates localhost:5432, which is production on this host | docs/dforge/plans/2026-11-20-audit-remaining.md | test: Task 4 contracts | done | f0b79c0 |
| 200 | P1-11: five seed and test scripts are broken and unreferenced | docs/dforge/plans/2026-11-20-audit-remaining.md | test: Task 68 contracts | doing | - |
| 201 | P1-12 remainder: publish_production_models.sh changes into the deleted fine-tuning directory | docs/dforge/plans/2026-11-20-audit-remaining.md | test: Task 68 contracts | doing | - |
| 202 | P1-13: the cutover package is the one-time 0006-to-baseline loader and only its own tests use it (llm_providers_transition.py stays) | docs/dforge/plans/2026-11-20-audit-remaining.md | test: Task 68 contracts | doing | - |
| 203 | P1-14: entailment/cache_span (about 549 judge-cache files) appears to be tracked although judge output is quarantined | - | - | deferred | kept: faithfulness_gate.py reads the directory and the G-F replay ran from it |
| 204 | P1-15: CI skips the extension suite, both SDK suites and the SDK build | docs/dforge/plans/2026-11-20-audit-remaining.md | A50 (Task 66) | doing | - |
| 205 | P1-16: the Dockerfile's chown -R duplicates layers and leaves the code writable; the app package is installed twice; Node 20 is end-of-life | docs/dforge/plans/2026-11-20-audit-remaining.md | test: Task 67 contracts | doing | - |
| 206 | P1-17: build-push.sh tags the HEAD sha even from a dirty tree | docs/dforge/plans/2026-11-20-audit-remaining.md | A49 (Task 67) | doing | - |
| 207 | P1-18: backup.sh accepts any complete dump, so a dump of the wrong database would push real dumps out of retention | docs/dforge/plans/2026-11-20-audit-remaining.md | A49 (Task 67) | doing | - |
| 208 | P1-19: frontend/nginx.conf is used by no build path | - | - | deferred | kept: frontend/Dockerfile:17 copies it for the deliberate nginx-in-image fallback |
| 209 | P1-20: stale comments: the ml extra in pyproject.toml, alembic.ini's ignored URL, the e2e README | docs/dforge/plans/2026-11-20-audit-remaining.md | test: Task 68 contracts | doing | - |
| 210 | P1-21: the two GitNexus files at the repo root are unreferenced | docs/dforge/plans/2026-11-20-audit-remaining.md | test: Task 68 contracts | doing | - |
| 211 | P1-22: eval_round3 is held in place by the guard test and still waits on owner decision D5 | - | - | deferred | owner decision D5 is not this programme's to make |
| 212 | P1-23: import_docs_corpus.py is likely superseded by the dr-forge mirror | - | - | deferred | declined in the spec: supersession by the dr-forge mirror is likely, not shown |
| 213 | P1-24: the worker compose comment says the receiver has no network, but it joins the default one | docs/dforge/plans/2026-11-20-audit-remaining.md | test: Task 67 contracts | doing | - |
| 214 | Section 6: lucide-react is not declared; 152 files import it through darkraise-ui | docs/dforge/plans/2026-11-20-audit-remaining.md | test: Task 66 contracts | doing | - |
| 215 | Section 1 follow-up 2: requeue the 53 error rows on this host once the fixes are deployed (owner answer 2026-11-20: requeue here) | - | - | deferred | production write: an auto run performs none; carried out after the merge by the sequence at the end of Task 71 of docs/dforge/plans/2026-11-20-audit-remaining.md |
| 216 | P1-2 follow-up: read the repository's fork-approval setting with gh and report it | docs/dforge/plans/2026-11-20-audit-remaining.md | test: Task 71 contracts | doing | - |
| 217 | Section 1 follow-ups 1 and 2 on 192.168.0.199: restore the embedding provider there and requeue its error rows | - | - | deferred | owner's: that instance is outside this host (owner answer 2026-11-20) |
| 218 | Section 1 follow-up 3: turn on job-failure notifications in Settings | - | - | deferred | owner's: needs a channel the owner chooses (owner answer 2026-11-20) |
| 219 | constellation-graphs row 5: no test asserts the memory renderer's one-frame deferred runner.start() | docs/dforge/plans/2026-11-20-audit-remaining.md | test: Task 53 contracts | doing | - |
| 220 | constellation-graphs row 6: a code-canvas rebuild that changes the drawn node set opens at sigma's default camera and does not re-centre a persisting selection | docs/dforge/plans/2026-11-20-audit-remaining.md | test: Task 51 contracts | doing | - |
| 221 | constellation-graphs row 7: the code canvas's ring overlay, its follow-camera during the core run, and memory-renderer position reseeding across a rebuild have no unit test | docs/dforge/plans/2026-11-20-audit-remaining.md | test: Task 51 contracts | doing | - |
| 222 | constellation-real-data row 9: the placeOuter iteration of the 20,000-node timing loop is covered by A14 (for test-simplifier) | docs/dforge/plans/2026-11-20-audit-remaining.md | test: Task 54 contracts | doing | - |
| 223 | graph-cluster-quality row 1: switching graph Regions off leaves the region outlines and chips drawn until a repaint | docs/dforge/plans/2026-11-20-audit-remaining.md | test: Task 53 contracts | doing | - |
| 224 | graph-cluster-quality row 2: two clusters can receive the same computed name, so the filter panel lists two identical rows | docs/dforge/plans/2026-11-20-audit-remaining.md | test: Task 52 contracts | doing | - |
| 225 | graph-cluster-quality row 3: a chosen term that is part of the prefix is not skipped, so a name can partly repeat its prefix | docs/dforge/plans/2026-11-20-audit-remaining.md | test: Task 52 contracts | doing | - |
| 226 | graph-cluster-quality row 4: measure entity_terms_for_memories latency on an all_memories view | docs/dforge/plans/2026-11-20-audit-remaining.md | test: Task 52 contracts | doing | - |
| 227 | graph-cluster-quality row 8: stale Louvain wording in a kept graph test comment | docs/dforge/plans/2026-11-20-audit-remaining.md | test: Task 52 contracts | doing | - |
| 228 | graph-cluster-quality row 7: gate.sh is GATE BLOCKED on this checkout because the F1 bench cache is missing | - | - | deferred | owner's: the cache needs DEEPSEEK_API_KEY, lost when the checkout was re-cloned |
| 229 | graph-cluster-quality rows 9 and 10: ENTITY_TERM_TYPES location; two cluster-naming tests deleted rather than rewritten | - | - | deferred | recorded decisions of that plan, no work owed |
| 230 | B3a-4 follow-up: drop knowledge_triples.stated_expiry and its partial index in a new revision | - | - | deferred | two-step drop: v1.17.0 still maps the column; ship in the release after the first release without a reader of it |
| 231 | B4 removal 8 follow-up: drop code_files.last_commit_sha in a new revision | - | - | deferred | two-step drop: v1.17.0 still maps the column; ship in the release after the first release without a reader of it |
| 232 | B3b-4 follow-up: restore the project/ tags a past refine removed, on this host | - | - | deferred | owner's: a production write; the script and its dry run are delivered, the restore waits for the owner's word |
