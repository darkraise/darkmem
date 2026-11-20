# Review record: 2026-11-20-graph-cluster-quality

Plan: docs/dforge/plans/2026-11-20-graph-cluster-quality.md
Retained: 2026-11-20

Review depth: standard (task-risk:4)
Acceptance QA: complete — 17 pass, 0 fail, 0 flaky, 0 cannot-test, 6 demo
final review lens-skipped silent-failures reason=cap
final review lens security — 0 Critical, 0 Important, 0 Minor; fixed 0, rejected 0
final review lens ui-ux — 0 Critical, 3 Important, 0 Minor; fixed 0, rejected 3
final review lens test-quality — 0 Critical, 2 Important, 0 Minor; fixed 2, rejected 0
final review lens code-quality — 0 Critical, 2 Important, 0 Minor; fixed 2, rejected 0; parts lang-python=1,lang-typescript=0,type-design=0,docs-comments=1
Test ratio: 1215 test / 245 code lines (4fba8d9..0e6335a)
Final review: clean (commits 4fba8d9..0e6335a)

## Amendments

## A1 — Task 4
Reason: the entity query shares the request session, so a database error would abort the transaction that the overlay and the final commit still use; the namer also needs list tags.
Cost if wrong: one SAVEPOINT round trip per uncached arm build.
### Old
````text
1. In `_build_memory_arm`, after building `memory_nodes`, build `tags` and `projects` keyed by memory id from the nodes. When `self.graph_repo` is set, `await self.graph_repo.entity_terms_for_memories(ids)` over every node id; on any exception, `logger.exception(...)`, use `{}` and report the arm degraded. Without `graph_repo`, use `{}`, not degraded. Name with `name_clusters(clusters, tags, projects, entity_terms)` and stop calling `_generate_cluster_names` (Task 5 deletes it).
````
### New
````text
1. In `_build_memory_arm`, after building `memory_nodes`, build `tags` (each node's `tags or []`) and `projects` keyed by memory id from the nodes. When `self.graph_repo` is set, run `await self.graph_repo.entity_terms_for_memories(ids)` over every node id inside `async with self.session.begin_nested():`. The repository shares the request session, so without the savepoint a failed statement aborts the request's transaction and every later statement in it (the entity overlay, the dependency's commit) fails; one comment names that why. On any exception, `logger.exception(...)`, use `{}` and report the arm degraded. Without `graph_repo`, use `{}`, not degraded. Name with `name_clusters(clusters, tags, projects, entity_terms)` and stop calling `_generate_cluster_names` (Task 5 deletes it).
````

## A2 — Task 5
Reason: `settings` is read only by the deleted `_generate_cluster_names`, so the import would be left unused.
Cost if wrong: none; the `rg` check keeps any import still in use.
### Old
````text
1. Delete `_generate_cluster_names`, `_tag_cluster_name`, `CLUSTER_NAME_LLM_CAP`, `_cluster_name_cache` with its comment, and `_CLUSTER_NAME_CACHE_SIZE` from `backend/app/services/graph.py`. In `reset_graph_caches`, drop the name-cache line and change its docstring to "Test hook: forget every cached memory arm." Remove imports nothing else in the module uses (`asyncio`, `hashlib`, `Counter`, `prompt`; check each with `rg`).
````
### New
````text
1. Delete `_generate_cluster_names`, `_tag_cluster_name`, `CLUSTER_NAME_LLM_CAP`, `_cluster_name_cache` with its comment, and `_CLUSTER_NAME_CACHE_SIZE` from `backend/app/services/graph.py`. In `reset_graph_caches`, drop the name-cache line and change its docstring to "Test hook: forget every cached memory arm." Remove imports nothing else in the module uses (`asyncio`, `hashlib`, `Counter`, `prompt`, and `from app.config import settings`, whose only reader is the deleted read-only check; check each with `rg`). Keep `OrderedDict`: `_result_cache` uses it. The read-only test patches `app.config.settings`, not an attribute of this module.
````

## A3 — Task 4
Reason: a stub that raises `RuntimeError` never touches the transaction, so the A13 test cannot catch the abort A1 prevents.
Cost if wrong: the test is a few lines longer.
### Old
````text
- `test_degraded_naming_is_not_cached` becomes `::test_failed_entity_terms_are_not_cached` (A13): with the existing non-raising `_FakeLLM` and a `graph_repo` stub whose `entity_terms_for_memories` raises `RuntimeError`, two identical `get_unified_graph(project="alpha", similarity_threshold=0.5)` calls run `get_louvain_clustered_vectors` twice (the existing counting monkeypatch), and the first response's `cluster_names` is `{"0": "retrieval · lexical"}`. Fails today because the service never calls `entity_terms_for_memories` and `_FakeLLM` names the cluster successfully, so the arm is not degraded, the second call hits the cache (count 1), and the name is `"named cluster"`.
````
### New
````text
- `test_degraded_naming_is_not_cached` becomes `::test_failed_entity_terms_are_not_cached` (A13): with the existing non-raising `_FakeLLM` and a `graph_repo` stub whose `entity_terms_for_memories` runs `await session.execute(text("SELECT CAST('not-a-uuid' AS uuid)"))` on the test's `session` (a real database error, which aborts the transaction unless the service's savepoint contains it), two identical `get_unified_graph(project="alpha", similarity_threshold=0.5)` calls run `get_louvain_clustered_vectors` twice (the existing counting monkeypatch), and both responses' `cluster_names` are `{"0": "retrieval · lexical"}`. The second response proves the session survived the failure: without the savepoint, the second call's first query raises `InFailedSQLTransactionError`, the outer handler answers an empty arm, and the count stays 1. Fails today because the service never calls `entity_terms_for_memories` and `_FakeLLM` names the cluster successfully, so the arm is not degraded, the second call hits the cache (count 1), and the name is `"named cluster"`.
````

## A4 — Task 4
Reason: spec A16 requires the response to keep its key types as well as its keys.
Cost if wrong: six more assertions.
### Old
````text
- Extend `::test_similarity_edges_come_from_the_knn_pass` (A16): the response's keys are exactly `{"memories", "clusters", "cluster_names", "similarity_edges", "total_memories", "memories_truncated", "fingerprint_unresolved"}`, and `cluster_names` has a non-empty value for every key of `clusters`.
````
### New
````text
- Extend `::test_similarity_edges_come_from_the_knn_pass` (A16): the response's keys are exactly `{"memories", "clusters", "cluster_names", "similarity_edges", "total_memories", "memories_truncated", "fingerprint_unresolved"}`; `memories` and `similarity_edges` are lists; `clusters` is a dict whose keys are `str` and whose values are lists of `str`; `cluster_names` is a dict with exactly the keys of `clusters` and a non-empty `str` value for each; `type(total_memories) is int`; and `memories_truncated` and `fingerprint_unresolved` are `bool`.
````

## A5 — Task 6
Reason: the step's own new test names `cluster_naming`, so the check as written can never come back empty.
Cost if wrong: none.
### Old
````text
5. Run `rg -n cluster_naming backend/app backend/tests frontend/src` and confirm no hit remains.
````
### New
````text
5. Run `rg -n cluster_naming backend/app frontend/src` and confirm no hit remains. Run `rg -n cluster_naming backend/tests` and confirm the only hits are in `test_llm_pipeline_config.py::test_cluster_naming_is_not_a_prompt_key`.
````

## A6 — Task 7
Reason: `gate.sh` exits 2 (`GATE BLOCKED`) when the F1 bench cache is missing, and it is missing on this checkout with no key to re-record it.
Cost if wrong: an extraction regression from another source goes unseen locally until CI runs the bench.
### Old
````text
Run: `./scripts/gate.sh` (repository root). A red leg exiting 143 is an `earlyoom` kill: check `free -h` and re-run that leg alone, as CLAUDE.md's Gate section says. After any backend route or MCP change the guards leg is mandatory, but this plan adds none.
Expected: exit 0.
````
### New
````text
Run: `./scripts/gate.sh` (repository root). A red leg exiting 143 is an `earlyoom` kill: check `free -h` and re-run that leg alone, as CLAUDE.md's Gate section says. After any backend route or MCP change the guards leg is mandatory, but this plan adds none.
Expected: exit 0.
If it instead exits 2 with `GATE BLOCKED — extraction bench cache missing` (the cache `backend/scripts/extraction_bench/.cache/manifest.json` was absent on 2026-11-20), do not run `run_bench.py` live and do not create a cache. Run the floor's other legs one at a time with the gate's commands and timeouts, each expected to exit 0: `cd backend && .venv/bin/python -m alembic heads` (exactly one head); `cd backend && TEST_DATABASE_URL=postgresql+asyncpg://darkmem:darkmem@localhost:5433/darkmem_test .venv/bin/python -m pytest -q -n 4 --dist loadfile`; `cd frontend && npm run typecheck && npm test && npm run build`; `cd extension && npm test`; `cd sdks/python && ../../backend/.venv/bin/python -m pytest -q`; `cd sdks/ts && npm test`; `cd sdks && PY="$PWD/../backend/.venv/bin/python" make build`; `cd backend && TEST_DATABASE_URL=postgresql+asyncpg://darkmem:darkmem@localhost:5433/darkmem_test BENCH_DATABASE_URL=postgresql+asyncpg://darkmem:darkmem@localhost:5433/darkmem_bench .venv/bin/python -m pytest scripts/benchlib/tests -q`. Record in the ledger that the F1 bench leg was not run, that the reason is the missing cache, and that this plan changes no extraction code.
````

## A7 — Task 7
Reason: the spec's UI-4 / A20 name a Settings → Assistant Prompts section and a chat prompt surface that the SPA does not have and never had, so the row cannot honestly pass, deviate or be accepted unverifiable as written.
Cost if wrong: the spec drops a never-true claim about a chat prompt surface; no code depends on it.
### Old
````text
- UI-4: Settings → Assistant Prompts, showing chat and agent instructions and no cluster naming prompt.
````
### New
````text
- UI-4: before capturing or writing the report, correct the spec `docs/dforge/specs/2026-11-20-graph-cluster-quality-design.md` (ruling `.dforge/sdd/2026-11-20-graph-cluster-quality/rulings-blocked-plan-7-report.md`, item ui4-surface). Make exactly these five edits and nothing else:
  (a) Replace the two-line UI-4 bullet ("**UI-4** — Settings → Assistant Prompts shows the chat and agent / instructions prompts and no cluster naming prompt.") with: `- **UI-4** — No Settings surface shows a cluster naming prompt: the LLM tab offers a System prompt only on the extraction, classification, reasoning and summarization purpose cards, and the Integration tab's "View injected MCP prompt" still opens the agent instructions prompt.`
  (b) Replace the A20 line with: `A20. [demo, high] UI-4: no Settings surface shows a cluster naming prompt; the LLM tab's System prompt buttons sit only on the extraction, classification, reasoning and summarization cards, and the Integration tab's injected MCP prompt dialog shows the agent instructions.`
  (c) In "### The `cluster_naming` prompt", replace the sentence "Settings → Assistant Prompts renders orphans from the API, so its textarea disappears with no frontend change." with: "No Settings surface ever rendered this key (the LLM tab shows prompts only for the four purposes in `PURPOSE_PROMPT_KEYS`, the Integration tab only `agent_instructions`), so nothing visible changes and no frontend code changes."
  (d) In the `**UI/UX depth:**` line, replace "and one prompt leaving Settings; no layout changes." with "; the cluster naming prompt leaves the API, and no Settings surface ever showed it; no layout changes."
  (e) Add this bullet to `## Decisions`, directly above the `- **Out of scope, reported:**` bullet: `- **UI-4 surface (ruling seat, 2026-11-20, `.dforge/sdd/2026-11-20-graph-cluster-quality/rulings-blocked-plan-7-report.md`).** The approved draft named a Settings → Assistant Prompts section showing the chat and agent instructions prompts. The SPA has no such section, and no Settings page ever showed `cluster_naming` or `chat`, so UI-4 and A20 now name the two surfaces that do render prompts.`
  Commit the spec alone: `git add docs/dforge/specs/2026-11-20-graph-cluster-quality-design.md && git commit -m "docs(spec): correct the UI-4 prompt surface"`. Then capture, at both viewports and both themes, the Settings LLM tab (record its text and that it contains no "cluster naming" string, case-insensitive, and that "System prompt" appears only on the four named cards), and the Integration tab with "View injected MCP prompt" clicked so the "Injected MCP instructions" dialog is open (opening it is a GET; record its text and that the agent instructions prompt loaded). The UI-4 Results row is `pass` and cites those screenshots plus the test `tests/test_llm_pipeline_config.py::test_cluster_naming_is_not_a_prompt_key`. If the dialog does not load the agent instructions, the row is `fail`; do not write `deviation` or `unverifiable` for UI-4.
````
