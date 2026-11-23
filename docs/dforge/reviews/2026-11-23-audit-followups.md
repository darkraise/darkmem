# Review record: 2026-11-23-audit-followups

Plan: docs/dforge/plans/2026-11-23-audit-followups.md
Retained: 2026-11-23

Review depth: full (spec,task-risk:1)
Acceptance QA: complete — 40 pass, 1 fail, 0 flaky, 0 cannot-test, 1 demo
final review lens security — 0 Critical, 0 Important, 2 Minor; fixed 1, rejected 0
final review lens ui-ux — 0 Critical, 2 Important, 3 Minor; fixed 5, rejected 0
final review lens silent-failures — 0 Critical, 1 Important, 6 Minor; fixed 6, rejected 1
final review lens test-quality — 0 Critical, 2 Important, 6 Minor; fixed 7, rejected 1
final review lens code-quality — 0 Critical, 1 Important, 7 Minor; fixed 6, rejected 1; parts lang-bash=1,lang-python=1,lang-typescript=1,type-design=1,docs-comments=4
Test ratio: 5617 test / 1833 code lines (cee4bf4..fc65768)
Final review: clean (commits cee4bf4..fc65768, 4 parked)

## Amendments

## A1 — Task 34
Reason: Spec rule 3 puts the parity doc's ContextEcho correction in the commit that removes the echo, and that row is generated from `PARITY_TABLE`.
Cost if wrong: One note edit and a regenerate move one task earlier.
### Old
````text
2. Remove or adjust every other backend test the search names (they assert the removed surface).

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && . ../.dforge/test-env.sh && timeout 900 .venv/bin/python -m pytest -q tests/test_envelope.py tests/test_sdk_generator.py tests/test_sdk_contract_conformance.py tests/test_memory*.py`, then the guards leg from `CLAUDE.md` on `darkmem_test_2`, then `cd ../sdks && timeout 300 make generate` (expect no diff).
Expected: PASS; the guards leg passes apart from assertions this task removed.

- [ ] **Step 5: Commit**

```bash
git add backend
````
### New
````text
2. Remove or adjust every other backend test the search names (they assert the removed surface).
3. Rule 3: the `memory.search` row of `docs/two-door-parity.md` says the tool's bare array "has nowhere to carry the envelope's ContextEcho or excluded counts", and that row is generated from `PARITY_TABLE`. In `backend/tests/test_door_parity.py`, change that note to "...has nowhere to carry the envelope's excluded counts." and correct any other `PARITY_TABLE` note that `rg -n "ContextEcho|X-Darkmem-Context|declared context|declareContext" backend/tests/test_door_parity.py docs/two-door-parity.md` names. Then regenerate the table with `cd backend && timeout 300 .venv/bin/python -c "from tests.test_door_parity import render_markdown; print(render_markdown())"` and paste the output between the `<!-- BEGIN GENERATED PARITY TABLE -->` and `<!-- END GENERATED PARITY TABLE -->` markers; never edit a row by hand. Correct any matching prose outside the block by hand.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && . ../.dforge/test-env.sh && timeout 900 .venv/bin/python -m pytest -q tests/test_envelope.py tests/test_sdk_generator.py tests/test_sdk_contract_conformance.py tests/test_memory*.py`, then the guards leg from `CLAUDE.md` on `darkmem_test_2`, then `cd ../sdks && timeout 300 make generate` (expect no diff).
Expected: PASS; the guards leg (it includes `tests/test_door_parity.py`) passes apart from assertions this task removed.

- [ ] **Step 5: Commit**

```bash
git add backend docs/two-door-parity.md
````

## A2 — Task 20
Reason: The `documents.write` row is inside the generated parity table, so a hand edit fails `test_the_committed_table_is_the_enforced_table`.
Cost if wrong: One extra test runs in Task 20.
### Old
````text
4. Row 352: the `documents.write` row of `docs/two-door-parity.md` gains one clause naming MCP's `unsupported_source` envelope as the twin of REST's 422 (outside any generated block).

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && . ../.dforge/test-env.sh && timeout 900 .venv/bin/python -m pytest -q tests/test_repo_entity_merge.py tests/test_document_parsers.py tests/test_document_routes.py tests/<leaking file> && timeout 1500 .venv/bin/python -m pytest -q -n 4 --dist loadfile tests/test_repo_entity_merge.py tests/test_pipeline_savepoints.py tests/test_extraction*.py tests/test_usage_attribution.py tests/test_merged_extraction.py tests/test_entity_shaping.py tests/test_communities.py`, then the `entities` read on the leaking file's lane database.
````
### New
````text
4. Row 352: the `documents.write` row's `note` in `PARITY_TABLE` (`backend/tests/test_door_parity.py`) gains one clause naming MCP's `unsupported_source` envelope as the twin of REST's 422. That row sits inside `docs/two-door-parity.md`'s generated table (between `<!-- BEGIN GENERATED PARITY TABLE -->` and `<!-- END GENERATED PARITY TABLE -->`), so regenerate the block with `cd backend && timeout 300 .venv/bin/python -c "from tests.test_door_parity import render_markdown; print(render_markdown())"` and paste the output between the markers; never edit the row by hand.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && . ../.dforge/test-env.sh && timeout 900 .venv/bin/python -m pytest -q tests/test_repo_entity_merge.py tests/test_document_parsers.py tests/test_document_routes.py tests/test_door_parity.py::test_the_committed_table_is_the_enforced_table tests/<leaking file> && timeout 1500 .venv/bin/python -m pytest -q -n 4 --dist loadfile tests/test_repo_entity_merge.py tests/test_pipeline_savepoints.py tests/test_extraction*.py tests/test_usage_attribution.py tests/test_merged_extraction.py tests/test_entity_shaping.py tests/test_communities.py`, then the `entities` read on the leaking file's lane database.
````

## A3 — Task 28
Reason: `DocumentLeaveGuard`'s `onDiscard` must clear the held writes, but the editor exposes only a focus handle.
Cost if wrong: The editor gains one unused imperative method.
### Old
````text
2. Row 376, in `BlockEditor`: a `beforeunload` listener is active while any write is held (saving, refused or queued), as `features/notes/use-page-sync.ts` does; an optional `onHeldWritesChange(state: "none" | "saving" | "refused")` prop reports the held state (`"refused"` covers writes queued behind a refused one), and the editor exposes a way for its parent to return focus to the held block's edit box, or to the block when it has none.
````
### New
````text
2. Row 376, in `BlockEditor`: a `beforeunload` listener is active while any write is held (saving, refused or queued), as `features/notes/use-page-sync.ts` does; an optional `onHeldWritesChange(state: "none" | "saving" | "refused")` prop reports the held state (`"refused"` covers writes queued behind a refused one). The editor exposes two parent-callable actions: one returns focus to the held block's edit box, or to the block when it has none, and one discards the held writes by the same code path as its own Discard button, so the held-write state then reports `"none"`.
````

## A4 — Task 35
Reason: A1 moves the parity-doc correction to Task 34. A hand edit of the generated table fails its guard, and removing doc 12's sections could strand the parity note's "doc 12 section 3" citation.
Cost if wrong: The task carries one redundant check.
### Old
````text
2. `docs/design/12` and `docs/design/15`: remove the declared-context sections (or the sentences that describe the header, the request field, the echo and the verb), leaving a one-line statement that declared context was removed on 2026-11-23 because nothing ranked by it. `docs/two-door-parity.md`: remove or correct any row that names the context field, header or echo.
````
### New
````text
2. `docs/design/12` and `docs/design/15`: remove the declared-context sections (or the sentences that describe the header, the request field, the echo and the verb), leaving a one-line statement that declared context was removed on 2026-11-23 because nothing ranked by it. Keep doc 12's section-3 rule that a breaking tool change ships as a new tool name, which the `memory.search` parity note cites; if that rule moves, correct the citation in that row's `note` in `PARITY_TABLE` (`backend/tests/test_door_parity.py`) and regenerate the doc's generated table, never by hand. Task 34 already corrected `docs/two-door-parity.md`: `rg -n "ContextEcho|X-Darkmem-Context|declareContext" docs/two-door-parity.md` prints nothing.
````
