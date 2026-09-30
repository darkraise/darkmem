# Work-log increment 6: UI and checkpoint removal — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: the skill the **Execution:** line names — dr-superpowers:subagent-driven-development for `subagent`, dr-superpowers:executing-plans for `inline`. Steps use checkbox (`- [ ]`) syntax for tracking.

**Plan review:** 2026-09-28 — dr-superpowers:judge-opus — executability 17 / coherence 18 / coverage 17 / assumptions 17 (round 2)

**Goal:** The SPA shows the work log (a Work log view under the project board, a cross-project list of open workstreams on the Activity route, and a Revisions sheet with a line diff on the document view), and then `session_checkpoints` is dropped along with its model, schema, service, routes, MCP tools, resume path and event vocabulary.

**Architecture:** The UI lands first, because the SPA's checkpoint surfaces read the routes this increment removes (spec §9, amended 2026-09-23). `GET /api/v1/projects` gains work-log counts additively, so the Activity list can find the projects that have open workstreams without a new route. New hand-written TanStack Query hooks call the existing work-log and document-revision REST routes, which already admit a login session through `require_scope`. Then the backend removal runs in four steps: run-key resolution moves into `worklog.py`, the two checkpoint doors go, the store goes (table, model, service, resume path, the projects endpoint's checkpoint fields), and the vocabulary and prose follow.

**Tech Stack:** Python 3.13, FastAPI, SQLAlchemy async (asyncpg), PostgreSQL 16, pytest; React 19, TypeScript, TanStack Query and Router, darkraise-ui, vitest with jsdom, `diff` (jsdiff).

**Spec:** docs/superpowers/specs/2026-09-23-work-log-lane-design.md

**Execution:** inline — `claude --model opus --effort high` — 3 of 18 tasks are heavy (13, 14, 16), so not a majority. Seven tasks total exactly 4 (1, 5, 7, 8, 12, 15, 17), more than a third of the plan, so they are self-implemented and the session runs Opus; effort is high because the three heavy tasks are delegated.

## Global Constraints

- Spec §9, increment 6: "Work log tab, Activity list, Revisions sheet, demo fixtures; then drop `session_checkpoints`, its tools and routes, and move `resolve_checkpoint_origin` into `worklog.py`." The UI tasks (1–12) land before the removal tasks (13–17); Task 18 adds the demo fixtures, which nothing else waits on, since every work-log query is already disabled in demo mode.
- Owner ruling 2026-09-28: the project workspace's Progress tab keeps its project board on top. The Work log replaces the checkpoint runs underneath it. Only the empty-state text that names the ledger path (`LEDGER_SUFFIX`) goes from `project-workspace.tsx`. `features/progress/` and `tests/project-progress-board.spec.ts` stay.
- Spec §8 Work log: "Left: the project's workstreams, open first, closed collapsed, each with title, key, last-entry time and state. Right: the selected workstream's entries on darkraise-ui `virtualized-timeline` — kind badge, run, time; checkpoints as expandable markdown, ledger lines compact; kind filter; refetch every 5 s while the workstream is open. Header: links to `plan_uri`, `spec_uri`, `handoff_uri` in the Artifacts tab; close/reopen; purge behind a confirmation dialog. A search box runs `worklog_search` for the project."
- Spec §8 Activity: "`CheckpointsTab` becomes a cross-project list of open workstreams with their latest entry, linking into the project's Work log. `use-checkpoint-runs.ts` (events-derived history) is deleted."
- Spec §8 Documents: "A Revisions sheet (darkraise-ui `sheet`) on the document view: the revision list and a line diff between any two. darkraise-ui has no diff component, so this adds the `diff` package and a small local renderer whose comment names that gap."
- Spec §8 Demo mode: "Every new hook carries `enabled: !DEMO`, with demo fixtures for the Work log." Demo mode makes no API request (`frontend/tests/demo-makes-no-api-calls.spec.ts`); a demo mutation fails with an error instead of calling the API.
- Spec §2 Removed: "`checkpoint_save`, `checkpoint_latest`, `POST /api/v1/checkpoints`, `GET /api/v1/checkpoints/latest`, and `resume_inject.py`". MCP tools go 48 → 46: capture 15 → 14, read 30 → 29, admin stays 3.
- Spec §1 Events: "`checkpoint_saved` and `resumed` leave the vocabulary with their emitter." `checkpoint` leaves `OBJECT_TYPES`.
- Greenfield (CLAUDE.md, owner ruling 2026-08-31): regenerate `0001_baseline.py` in place, no `0002`, no compatibility shim.
- UI components come from darkraise-ui first. Always import `EmptyState` from `@/components/darkmem`; `empty-state-single-door.test.ts` fails on the library's.
- Every new TanStack Query leading key is registered in `frontend/src/lib/query-keys.ts` `QUERY_KEY_SCOPE`, camelCase letters only. `query-keys.test.ts` fails on an unregistered key or a registered key that no hook uses.
- Hand-written frontend API types live in `frontend/src/hooks/api/use-*-api.ts` and are re-exported from `frontend/src/hooks/api/index.ts`. `apiFetch` (`frontend/src/lib/api.ts`) prefixes `/api/v1` and throws `ApiError` (with `status`) on a non-2xx answer.
- Frontend tests run from `frontend/` with `npx vitest run <path>`. Mock the API with `vi.mock("@/lib/api", …)` and `vi.mock("@/lib/demo-flag", () => ({ DEMO: false }))`; there is no msw. `npm run typecheck` is `tsc -b`, never plain `tsc`. Never run a repo-wide `prettier --write`.
- Backend tests run from `backend/` as `.venv/bin/python -m pytest`, always with `TEST_DATABASE_URL=postgresql+asyncpg://darkmem:darkmem@localhost:5433/darkmem_test_2` and a Bash timeout. Never point pytest at production, and never run it without that variable.
- After any task that registers or removes a route or MCP tool (14), run the guards leg named in CLAUDE.md on `darkmem_test_2`, and re-read `docs/two-door-parity.md`'s headline counts and CLAUDE.md's tool count by hand.
- If the dev Postgres is stopped, start only its service: `docker compose -f docker-compose.dev.yml up -d postgres` (repo root).
- `rg` is a shell function on this host: never pipe a file list into `xargs rg`.
- The merge gate, the Playwright leg (`backend/scripts/e2e/run_playwright_e2e.py`, never bare `npx playwright test`) and the production redeploy belong to the controller at finishing, not to any task. The redeploy needs the empty-table path of Assumptions, not a plain `docker compose up -d`.
- Commits: `<type>(<scope>): <subject>`, subject ≤ 50 characters, imperative.

## Contracts

- **`GET /api/v1/projects` rows** (Task 1): `ProjectSummary` gains `workstream_count: int` (every workstream, open or closed), `open_workstream_count: int` and `last_worklog_at: datetime | None` (the newest `workstreams.last_entry_at` of the project). A project holding only workstreams is listed. Task 15 removes `checkpoint_count` and `last_checkpoint_at`.
- **Frontend `ProjectSummary`** (`frontend/src/hooks/api/use-projects-api.ts`, Task 2): gains `workstream_count: number`, `open_workstream_count: number`, `last_worklog_at: string | null`. Task 15 removes `checkpoint_count` and `last_checkpoint_at`.
- **`frontend/src/hooks/api/use-worklog-api.ts`** (Task 3; Task 18 adds its demo branch), re-exported from `hooks/api/index.ts`:
  - types `WorklogKind = "checkpoint" | "ledger" | "note"`, `WorkstreamState = "open" | "closed"`, `Workstream`, `WorklogEntry`, `WorkstreamPage`, `WorklogEntryPage`, `WorklogResume`, `WorklogSearchHit`, `WorklogSearchResponse`, `WorkstreamPatch` (fields exactly as the backend schemas in `backend/app/schemas/worklog.py`, dates as ISO strings).
  - `useWorkstreams(project: string, state: WorkstreamState)` → `useInfiniteQuery`, key `["worklogWorkstreams", project, state]`.
  - `useWorklogEntries(workstreamId: string | null, kind: WorklogKind | null, live: boolean)` → `useInfiniteQuery`, key `["worklogEntries", workstreamId, kind]`, `refetchInterval: live ? WORKLOG_LIVE_MS : false`.
  - `WORKLOG_LIVE_MS = 5_000`.
  - `useWorklogResume(project: string, key: string, enabled = true)` → `useQuery<WorklogResume | null>`, key `["worklogResume", project, key]`; a 404 resolves to `null`.
  - `useWorklogSearch()` → `useMutation<WorklogSearchResponse, Error, { project: string; query: string; workstream?: string; kind?: WorklogKind }>`.
  - `useWorkstreamUpdate()` → `useMutation<Workstream, Error, { id: string } & WorkstreamPatch>`; `useWorkstreamPurge()` → `useMutation<void, Error, string>`. Both invalidate every `worklogWorkstreams`, `worklogEntries` and `worklogResume` query.
- **`frontend/src/demo/worklog.ts`** (Task 18): `DEMO_WORKSTREAMS: Workstream[]` and `DEMO_WORKLOG_ENTRIES: Record<string, WorklogEntry[]>` keyed by workstream id.
- **`EntryTimeline`** and **`firstLine`** (`frontend/src/features/worklog/components/entry-timeline.tsx`, Task 4): `EntryTimeline({ workstream }: { workstream: Workstream })`, which Task 6 extends with `initialEntryId?: string`; `firstLine(body: string): string` answers the first non-blank line without heading hashes.
- **`WorkLogPanel`** (`frontend/src/features/worklog/components/work-log-panel.tsx`): `WorkLogPanel({ project, initialWorkstream }: { project: string; initialWorkstream?: string })` from Task 4, which Task 5 extends with `onOpenDocument?: (uri: string) => void`. `initialWorkstream` is a workstream key.
- **`WorkstreamHeader`** (`frontend/src/features/worklog/components/workstream-header.tsx`, Task 5): `WorkstreamHeader({ workstream, onOpenDocument }: { workstream: Workstream; onOpenDocument?: (uri: string) => void })`.
- **`WorklogSearch`** (`frontend/src/features/worklog/components/worklog-search.tsx`, Task 6): `WorklogSearch({ project, onOpen }: { project: string; onOpen: (workstreamKey: string, entryId: string) => void })`.
- **`ProjectWorkspace`** (Task 7): gains an optional `workstream?: string` prop, passed to `WorkLogPanel` as `initialWorkstream`. The route `projects_.$project.tsx` gains an optional `workstream` search param.
- **`OpenWorkstreams`** (`frontend/src/features/worklog/components/open-workstreams.tsx`, Task 8): no props. The Activity route's tab value `checkpoints` becomes `worklog`.
- **`LineDiff`** (`frontend/src/features/documents/components/line-diff.tsx`, Task 10): `LineDiff({ before, after }: { before: string; after: string })`.
- **`frontend/src/hooks/api/use-document-revisions-api.ts`** (Task 11): types `DocumentRevisionItem`, `DocumentRevisionPage`, `DocumentRevision`; `useDocumentRevisions(documentId: string, enabled: boolean)` → `useInfiniteQuery`, key `["documentRevisions", documentId]`; `useDocumentRevision(documentId: string, revisionId: string | null)` → `useQuery`, key `["documentRevision", documentId, revisionId]`.
- **`RevisionsSheet`** (`frontend/src/features/documents/components/revisions-sheet.tsx`, Task 12): `RevisionsSheet({ documentId, open, onOpenChange })`.
- **`worklog.resolve_run_key(declared, *, source: str, project: str) -> str`** and **`worklog.UndeclaredRun(ValueError)`** (Task 13), in `backend/app/services/worklog.py`, both in `__all__`. Same derivation and refusals as today's `checkpoints.resolve_checkpoint_origin`.

## Assumptions (evidence)

- Production holds 0 `session_checkpoints` rows, 0 `events` rows with `event_type IN ('checkpoint_saved','resumed')` or `object_type='checkpoint'`, and no foreign key points at the table (psql on `darkmem-prod-postgres-1`, 2026-09-28). The finishing redeploy therefore takes the empty-table path of the memory note "Empty-table additive deploy": back up, stop the app, `DROP TABLE session_checkpoints;`, delete the `schema_baseline_sha` config row, start, then prove the schema with the runbook's step-5 diff. No other table changes, so there is no DDL to recreate.
- `require_scope` admits a login session first and a key second (`backend/app/api/auth.py:156-196`), so the SPA can call every work-log route and both revision routes with its cookie (read 2026-09-28).
- `list_workstreams` pages newest-created first on `(created_at, id)` with a `next_before` cursor and requires `project` (`backend/app/services/worklog.py:543-576`, `backend/app/api/routes/worklog.py:100-114`); `list_entries` pages oldest first on `seq` with `next_after` (`worklog.py:579-604`). There is no cross-project list route, so the Activity list reads `GET /projects` for `open_workstream_count > 0` and asks each such project for its open workstreams. The latest entry is read through `resume` per row, which is bounded by the server (read 2026-09-28).
- darkraise-ui's `VirtualizedTimeline` renders its items under jsdom: a throwaway vitest render with `layout="list"`, `rowHeight={40}` and one inline bucket found the item text (probe run 2026-09-28, then deleted). Its row height is fixed, so a checkpoint's markdown renders in a detail pane beside the timeline when its row is clicked, rather than growing the row.
- `diff@9.0.0` is npm's `latest` and ships its own types (`libesm/index.d.ts`, `npm view diff@9.0.0 types exports`, 2026-09-28); the repository holds only 8.0.4, transitively.
- `VirtualizedTimeline`'s `onItemClick` fires on a user click under jsdom with the clicked item (the probe was extended to click a row, 2026-09-28, then deleted), which Task 4's and Task 6's click tests rely on.
- `app.api.mcp.client_identity` imports only `logging` and `re` (its `import_closure` is itself alone, run 2026-09-28), so `worklog.py` can import `resolve_origin_key` without widening the work-log wall's closure.
- `inject_fill.fill`'s `lead` parameter has one caller, `resume_inject.resume_fill` (`rg "lead=" backend/app`, 2026-09-28), so it goes with `resume_inject.py`.
- `docs/planning/baseline-schema-inventory.md` does not list `workstreams` or `worklog_entries` (`rg -c`, 2026-09-28): it is a pre-freeze inventory that stopped tracking new tables, so its `session_checkpoints` rows are left as history, like the other planning documents that name checkpoints.
- The frontend event taxonomy already carries the four `workstream_*` types and `capture_flagged` (`frontend/src/features/activity/event-taxonomy.ts:55`, `:142-145`); `backend/tests/test_event_taxonomy_map.py` requires every emitted type to appear, so `checkpoint_saved` and `resumed` leave that file only in Task 17, after their emitters are gone.
- The removal commits (Tasks 14, 16) carry no `!` and no `BREAKING CHANGE` footer. A push to master derives the next version from commit types (CLAUDE.md, Build, deploy, release), and greenfield (owner ruling 2026-08-31) owes no compatibility, so whether dropping the checkpoint doors warrants a major version is the owner's call at release, not a side effect of a commit subject.
- Codex is off on this host (`codex-gate usable=false reason=free-plan lane=false`, 2026-09-28), so no task carries an `**Executor:**` line.
- The **Execution** line names the controller session; each task's **Implementer** line names the subagent a delegated task is dispatched to.

## Task index

1. Projects endpoint reports work-log activity
2. Frontend project summaries read the work log
3. Work-log API hooks
4. Work log panel
5. Work log header actions
6. Work log search
7. Mount the Work log in the project workspace
8. Activity Work log tab
9. Remove the checkpoint UI
10. Line diff renderer
11. Document revision hooks
12. Revisions sheet on the document view
13. Move run-key resolution into the work log
14. Remove the checkpoint doors
15. Projects endpoint drops its checkpoint fields
16. Drop the checkpoint store
17. Retire the checkpoint vocabulary and prose
18. Work-log demo fixtures

---

### Task 1: Projects endpoint reports work-log activity

**Files:**
- Modify: `backend/app/api/routes/projects.py` (`ProjectSummary`, `_UNION_SQL`)
- Test: `backend/tests/test_projects_endpoint.py`

**Interfaces:**
- Consumes: nothing from other tasks.
- Produces: the `GET /api/v1/projects` row fields of Contracts.

**Items:** 1

**Implementer:** dr-superpowers:impl-opus-low
**Evaluation:** files 1 - spec 0 - coupling 2 - risk 1 = 4

- [ ] **Step 1: Write the failing tests**

In `backend/tests/test_projects_endpoint.py`, extend the exact-equality dict in `test_counts_every_status_not_only_active` so it reads:

```python
    assert mixed == {
        "name": "mixed",
        "kind": "project",
        "memory_count": 2,
        "document_count": 0,
        "checkpoint_count": 0,
        "page_count": 0,
        "last_checkpoint_at": None,
        "workstream_count": 0,
        "open_workstream_count": 0,
        "last_worklog_at": None,
        "last_event_day": None,
    }
```

and add this test after `test_a_checkpoint_only_project_is_visible`:

```python
@pytest.mark.asyncio
async def test_a_worklog_only_project_is_visible(client, auth_headers, session):
    """The Activity route's open-workstream list finds its projects here."""
    from app.services import worklog

    first = await worklog.append(
        session, project="worklog-only", key="plan-a", run_key="r",
        entries=[{"kind": "note", "body": "a"}],
    )
    await worklog.append(
        session, project="worklog-only", key="plan-b", run_key="r",
        entries=[{"kind": "note", "body": "b"}],
    )
    await worklog.update_workstream(session, first.workstream.id, state="closed")
    await session.flush()

    resp = await client.get("/api/v1/projects", headers=auth_headers)
    body = {p["name"]: p for p in resp.json()}
    assert "worklog-only" in body
    row = body["worklog-only"]
    assert row["workstream_count"] == 2
    assert row["open_workstream_count"] == 1
    assert row["last_worklog_at"] is not None
    assert row["memory_count"] == 0
```

- [ ] **Step 2: Run them to verify they fail**

Run (from `backend/`): `TEST_DATABASE_URL=postgresql+asyncpg://darkmem:darkmem@localhost:5433/darkmem_test_2 timeout 600 .venv/bin/python -m pytest -q tests/test_projects_endpoint.py`
Expected: the two tests FAIL (`KeyError` / missing keys in the dict comparison, and `worklog-only` absent).

- [ ] **Step 3: Implement**

In `backend/app/api/routes/projects.py`, add three fields to `ProjectSummary` after `last_checkpoint_at`:

```python
    workstream_count: int
    open_workstream_count: int
    last_worklog_at: datetime | None
```

and replace `_UNION_SQL` with:

```python
_UNION_SQL = text(
    """
    WITH names AS (
        SELECT project FROM memories
        UNION
        SELECT project FROM documents
        UNION
        SELECT project FROM session_checkpoints
        UNION
        SELECT project FROM workstreams
        UNION
        SELECT project FROM pages WHERE deleted_at IS NULL
        UNION
        -- A registered personal space appears even holding nothing: it is the
        -- notes workspace's own scope, not a project that happens to exist.
        SELECT name FROM projects WHERE kind = 'personal'
    ),
    m AS (SELECT project, count(*) AS n FROM memories GROUP BY project),
    d AS (SELECT project, count(*) AS n FROM documents GROUP BY project),
    c AS (SELECT project, count(*) AS n, max(created_at) AS latest
          FROM session_checkpoints GROUP BY project),
    w AS (SELECT project, count(*) AS n,
                 count(*) FILTER (WHERE state = 'open') AS open_n,
                 max(last_entry_at) AS latest
          FROM workstreams GROUP BY project),
    pg AS (SELECT project, count(*) AS n FROM pages
           WHERE deleted_at IS NULL GROUP BY project),
    e AS (SELECT project,
                 max((created_at AT TIME ZONE 'UTC')::date) AS latest_day
          FROM events GROUP BY project)
    SELECT names.project AS name,
           COALESCE(p.kind, 'project') AS kind,
           COALESCE(m.n, 0) AS memory_count,
           COALESCE(d.n, 0) AS document_count,
           COALESCE(c.n, 0) AS checkpoint_count,
           COALESCE(pg.n, 0) AS page_count,
           c.latest AS last_checkpoint_at,
           COALESCE(w.n, 0) AS workstream_count,
           COALESCE(w.open_n, 0) AS open_workstream_count,
           w.latest AS last_worklog_at,
           e.latest_day AS last_event_day
    FROM names
    LEFT JOIN m ON m.project = names.project
    LEFT JOIN d ON d.project = names.project
    LEFT JOIN c ON c.project = names.project
    LEFT JOIN w ON w.project = names.project
    LEFT JOIN pg ON pg.project = names.project
    LEFT JOIN e ON e.project = names.project
    LEFT JOIN projects p ON p.name = names.project
    WHERE names.project IS NOT NULL AND names.project <> ''
    ORDER BY COALESCE(m.n, 0) + COALESCE(d.n, 0) + COALESCE(c.n, 0)
             + COALESCE(w.n, 0) + COALESCE(pg.n, 0) DESC,
             names.project ASC
    """
)
```

In the `ProjectSummary` docstring, change "a memory, a document, a checkpoint or a page carries it" to "a memory, a document, a checkpoint, a workstream or a page carries it", and in `list_projects`' docstring change "memories, documents, checkpoints and pages" to "memories, documents, checkpoints, workstreams and pages".

- [ ] **Step 4: Run the tests to verify they pass**

Run: the Step 2 command, then `TEST_DATABASE_URL=postgresql+asyncpg://darkmem:darkmem@localhost:5433/darkmem_test_2 timeout 600 .venv/bin/python -m pytest -q tests/test_projects_route.py`
Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/api/routes/projects.py backend/tests/test_projects_endpoint.py
git commit -m "feat(projects): report work-log activity per project"
```

### Task 2: Frontend project summaries read the work log

**Files:**
- Modify: `frontend/src/hooks/api/use-projects-api.ts` (`ProjectSummary`)
- Modify: `frontend/src/routes/_authenticated/projects.tsx` (`ProjectCard`, two descriptions), `frontend/src/routes/_authenticated/documents.tsx` (one description)
- Modify: `frontend/src/components/app-chrome/project-switcher.tsx` (`itemHint` and the doc comment above it)
- Modify: `frontend/src/demo/projects.ts`
- Test (fixtures): `frontend/src/routes/_authenticated/__tests__/projects-index.test.tsx`, `frontend/src/routes/_authenticated/__tests__/notes.test.tsx`, `frontend/src/routes/_authenticated/__tests__/documents.test.tsx`, `frontend/src/components/app-chrome/__tests__/project-switcher.test.tsx`, `frontend/src/features/knowledge/__tests__/topics-scope.test.tsx`

**Interfaces:**
- Consumes: the `GET /api/v1/projects` row fields (Contracts, Task 1).
- Produces: the frontend `ProjectSummary` fields (Contracts).

**Items:** 1

**Implementer:** dr-superpowers:impl-sonnet-high
**Evaluation:** files 1 - spec 0 - coupling 2 - risk 0 = 3

- [ ] **Step 1: Write the failing test**

In `frontend/src/components/app-chrome/__tests__/project-switcher.test.tsx`, in the test `counts pages in a project's item total`, replace the fixture's `checkpoint_count: 3,` line with `checkpoint_count: 0,` and add `workstream_count: 3, open_workstream_count: 1, last_worklog_at: null,` beside it, so the total still reads 1 + 2 + 3 + 4 = 10 only if the hint counts workstreams.

- [ ] **Step 2: Run it to verify it fails**

Run (from `frontend/`): `timeout 300 npx vitest run src/components/app-chrome/__tests__/project-switcher.test.tsx`
Expected: FAIL on the `10 items` assertion (the hint still sums `checkpoint_count`, now 0).

- [ ] **Step 3: Implement**

In `frontend/src/hooks/api/use-projects-api.ts`, add to `ProjectSummary` after `last_checkpoint_at`:

```ts
  /** Every workstream the project holds, open or closed. */
  workstream_count: number
  open_workstream_count: number
  /** The newest entry across the project's workstreams. */
  last_worklog_at: string | null
```

In `frontend/src/components/app-chrome/project-switcher.tsx`, make `itemHint` sum `row.memory_count + row.document_count + row.workstream_count + row.page_count`, and in the doc comment above the switcher change "a memory, document or checkpoint carries it" to "a memory, document, workstream or page carries it".

In `frontend/src/routes/_authenticated/projects.tsx`, in `ProjectCard` replace the third `Stat` and the paragraph under the stats with:

```tsx
          <Stat value={row.workstream_count} label="workstreams" />
        </div>
        <p className="text-muted-foreground text-sm">
          {row.last_worklog_at
            ? `last work-log entry ${relativeTime(row.last_worklog_at)}`
            : "no work log yet"}
          {activity ? ` · ${activity}` : ""}
        </p>
```

Change the user-facing strings that name checkpoints:

- `frontend/src/routes/_authenticated/projects.tsx`: the `PageChrome` description "Every project the corpus holds — memories, documents and checkpoint runs." becomes "Every project the corpus holds — memories, documents and work logs.", and the empty state's "A project appears here as soon as a memory, document or checkpoint carries its name." becomes "A project appears here as soon as a memory, document or workstream carries its name.";
- `frontend/src/routes/_authenticated/documents.tsx`: "A project appears here once a memory, document or checkpoint carries its name." becomes "A project appears here once a memory, document or workstream carries its name.".

In `frontend/src/demo/projects.ts` and in every test fixture object listed under **Files** that carries `checkpoint_count`, add the three new fields next to the old ones: `workstream_count` equal to that object's `checkpoint_count`, `open_workstream_count: 0`, and `last_worklog_at` equal to that object's `last_checkpoint_at` (`null` where the object has no `last_checkpoint_at`). The one exception is the Step 1 fixture, already edited. The partial fixture in `project-switcher.test.tsx`'s `offers All projects first` gets `workstream_count: 0` only.

- [ ] **Step 4: Run tests and typecheck**

Run (from `frontend/`): `timeout 300 npx vitest run src/components/app-chrome src/routes/_authenticated/__tests__ src/features/knowledge/__tests__/topics-scope.test.tsx && timeout 300 npm run typecheck`
Expected: PASS, and typecheck reports no error.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/hooks/api/use-projects-api.ts frontend/src/routes/_authenticated/projects.tsx frontend/src/routes/_authenticated/documents.tsx frontend/src/components/app-chrome/project-switcher.tsx frontend/src/demo/projects.ts frontend/src/routes/_authenticated/__tests__ frontend/src/components/app-chrome/__tests__/project-switcher.test.tsx frontend/src/features/knowledge/__tests__/topics-scope.test.tsx
git commit -m "feat(projects): show work-log activity per project"
```

### Task 3: Work-log API hooks

**Files:**
- Create: `frontend/src/hooks/api/use-worklog-api.ts`
- Modify: `frontend/src/hooks/api/index.ts` (one export line)
- Modify: `frontend/src/lib/query-keys.ts` (`QUERY_KEY_SCOPE`)
- Test: `frontend/src/hooks/api/__tests__/use-worklog-api.test.tsx`

**Interfaces:**
- Consumes: nothing from other tasks.
- Produces: `use-worklog-api.ts` (Contracts). Its queries carry `enabled: !DEMO`; the demo fixtures arrive in Task 18.

**Items:** 1

**Implementer:** dr-superpowers:impl-sonnet-high
**Evaluation:** files 1 - spec 0 - coupling 2 - risk 0 = 3

- [ ] **Step 1: Write the failing tests**

Create `frontend/src/hooks/api/__tests__/use-worklog-api.test.tsx`:

```tsx
import { describe, expect, it, vi, beforeEach } from "vitest"
import { renderHook, waitFor } from "@testing-library/react"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import type { ReactNode } from "react"

vi.mock("@/lib/demo-flag", () => ({ DEMO: false }))
vi.mock("@/lib/api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/api")>()),
  apiFetch: vi.fn(),
}))

import { ApiError, apiFetch } from "@/lib/api"
import {
  useWorklogEntries,
  useWorklogResume,
  useWorklogSearch,
  useWorkstreamPurge,
  useWorkstreams,
  useWorkstreamUpdate,
} from "../use-worklog-api"

function wrapper({ children }: { children: ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>
}

beforeEach(() => {
  vi.mocked(apiFetch).mockReset()
})

describe("work-log reads", () => {
  it("lists one state of a project's workstreams and pages back on next_before", async () => {
    vi.mocked(apiFetch)
      .mockResolvedValueOnce({ items: [{ id: "w1" }], next_before: "cursor-1" })
      .mockResolvedValueOnce({ items: [{ id: "w2" }], next_before: null })
    const { result } = renderHook(() => useWorkstreams("darkmem", "open"), { wrapper })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(vi.mocked(apiFetch).mock.calls[0]![0]).toBe(
      "/worklog/workstreams?project=darkmem&state=open&limit=50",
    )
    expect(result.current.hasNextPage).toBe(true)
    await result.current.fetchNextPage()
    await waitFor(() => expect(result.current.data?.pages).toHaveLength(2))
    expect(vi.mocked(apiFetch).mock.calls[1]![0]).toBe(
      "/worklog/workstreams?project=darkmem&state=open&limit=50&before=cursor-1",
    )
    expect(result.current.hasNextPage).toBe(false)
  })

  it("reads entries forward on next_after, filtered by kind", async () => {
    vi.mocked(apiFetch)
      .mockResolvedValueOnce({ items: [{ id: "e1", seq: 4 }], next_after: 4 })
      .mockResolvedValueOnce({ items: [], next_after: null })
    const { result } = renderHook(() => useWorklogEntries("w1", "ledger", false), { wrapper })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(vi.mocked(apiFetch).mock.calls[0]![0]).toBe(
      "/worklog/workstreams/w1/entries?limit=200&kind=ledger",
    )
    await result.current.fetchNextPage()
    await waitFor(() => expect(vi.mocked(apiFetch)).toHaveBeenCalledTimes(2))
    expect(vi.mocked(apiFetch).mock.calls[1]![0]).toBe(
      "/worklog/workstreams/w1/entries?limit=200&kind=ledger&after=4",
    )
  })

  it("stays idle without a workstream", () => {
    const { result } = renderHook(() => useWorklogEntries(null, null, true), { wrapper })
    expect(result.current.fetchStatus).toBe("idle")
    expect(vi.mocked(apiFetch)).not.toHaveBeenCalled()
  })

  it("answers null for a workstream that does not exist", async () => {
    vi.mocked(apiFetch).mockRejectedValueOnce(new ApiError("No workstream", 404))
    const { result } = renderHook(() => useWorklogResume("darkmem", "nope"), { wrapper })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data).toBeNull()
    expect(vi.mocked(apiFetch).mock.calls[0]![0]).toBe(
      "/worklog/resume?project=darkmem&workstream=nope",
    )
  })

  it("reads no resume while disabled", () => {
    const { result } = renderHook(() => useWorklogResume("darkmem", "plan", false), { wrapper })
    expect(result.current.fetchStatus).toBe("idle")
    expect(vi.mocked(apiFetch)).not.toHaveBeenCalled()
  })

  it("surfaces any other resume failure as an error", async () => {
    vi.mocked(apiFetch).mockRejectedValueOnce(new ApiError("boom", 500))
    const { result } = renderHook(() => useWorklogResume("darkmem", "plan"), { wrapper })
    await waitFor(() => expect(result.current.isError).toBe(true))
  })
})

describe("work-log writes", () => {
  it("patches, purges and searches through the work-log routes", async () => {
    vi.mocked(apiFetch).mockResolvedValue({ items: [], semantic_ran: true })
    const update = renderHook(() => useWorkstreamUpdate(), { wrapper })
    await update.result.current.mutateAsync({ id: "w1", state: "closed" })
    expect(vi.mocked(apiFetch)).toHaveBeenLastCalledWith("/worklog/workstreams/w1", {
      method: "PATCH",
      body: JSON.stringify({ state: "closed" }),
    })

    const purge = renderHook(() => useWorkstreamPurge(), { wrapper })
    await purge.result.current.mutateAsync("w1")
    expect(vi.mocked(apiFetch)).toHaveBeenLastCalledWith("/worklog/workstreams/w1", {
      method: "DELETE",
    })

    const search = renderHook(() => useWorklogSearch(), { wrapper })
    await search.result.current.mutateAsync({ project: "darkmem", query: "retention" })
    expect(vi.mocked(apiFetch)).toHaveBeenLastCalledWith("/worklog/search", {
      method: "POST",
      body: JSON.stringify({ project: "darkmem", query: "retention" }),
    })
  })
})
```

- [ ] **Step 2: Run them to verify they fail**

Run (from `frontend/`): `timeout 300 npx vitest run src/hooks/api/__tests__/use-worklog-api.test.tsx`
Expected: FAIL (cannot resolve `../use-worklog-api`).

- [ ] **Step 3: Create the hooks**

Create `frontend/src/hooks/api/use-worklog-api.ts`:

```ts
import {
  useInfiniteQuery,
  useMutation,
  useQuery,
  useQueryClient,
  type QueryClient,
} from "@tanstack/react-query"
import { ApiError, apiFetch } from "@/lib/api"
import { DEMO } from "@/lib/demo-flag"

export type WorklogKind = "checkpoint" | "ledger" | "note"
export type WorkstreamState = "open" | "closed"

export interface Workstream {
  id: string
  project: string
  key: string
  title: string | null
  client: string | null
  state: WorkstreamState
  closed_at: string | null
  retain: boolean
  properties: Record<string, unknown>
  last_entry_at: string
  created_at: string
  updated_at: string
}

export interface WorklogEntry {
  id: string
  workstream_id: string
  seq: number
  run_key: string
  kind: WorklogKind
  body: string
  properties: Record<string, unknown>
  created_at: string
}

export interface WorkstreamPage {
  items: Workstream[]
  next_before: string | null
}

export interface WorklogEntryPage {
  items: WorklogEntry[]
  next_after: number | null
}

export interface WorklogResume {
  workstream: Workstream
  checkpoint: WorklogEntry | null
  notes: WorklogEntry[]
  notes_truncated: boolean
  ledger: WorklogEntry[]
}

export interface WorklogSearchHit {
  entry: WorklogEntry
  workstream: string
  rrf_score: number
  arms: ("keyword" | "semantic")[]
}

export interface WorklogSearchResponse {
  items: WorklogSearchHit[]
  semantic_ran: boolean
}

export interface WorklogSearchParams {
  project: string
  query: string
  workstream?: string
  kind?: WorklogKind
}

export interface WorkstreamPatch {
  state?: WorkstreamState
  retain?: boolean
  title?: string | null
  properties?: Record<string, unknown>
}

/** How often an open workstream's entries are re-read (spec §8). */
export const WORKLOG_LIVE_MS = 5_000
const WORKSTREAM_PAGE = 50
const ENTRY_PAGE = 200
/** One state of a project's workstreams, newest-created first, paged back on
 *  the server's `(created_at, id)` cursor. */
export function useWorkstreams(project: string, state: WorkstreamState) {
  return useInfiniteQuery({
    queryKey: ["worklogWorkstreams", project, state],
    initialPageParam: null as string | null,
    queryFn: ({ pageParam }) => {
      const qs = new URLSearchParams({ project, state, limit: String(WORKSTREAM_PAGE) })
      if (pageParam) qs.set("before", pageParam)
      return apiFetch<WorkstreamPage>(`/worklog/workstreams?${qs}`)
    },
    getNextPageParam: (last: WorkstreamPage) => last.next_before,
    enabled: !DEMO,
  })
}

/** A workstream's entries oldest first, paged forward on `seq`. `live` re-reads
 *  every loaded page on WORKLOG_LIVE_MS; a short last page re-read with the same
 *  cursor picks up whatever was appended since. */
export function useWorklogEntries(
  workstreamId: string | null,
  kind: WorklogKind | null,
  live: boolean,
) {
  return useInfiniteQuery({
    queryKey: ["worklogEntries", workstreamId, kind],
    initialPageParam: null as number | null,
    queryFn: ({ pageParam }) => {
      const qs = new URLSearchParams({ limit: String(ENTRY_PAGE) })
      if (kind) qs.set("kind", kind)
      if (pageParam !== null) qs.set("after", String(pageParam))
      return apiFetch<WorklogEntryPage>(`/worklog/workstreams/${workstreamId}/entries?${qs}`)
    },
    getNextPageParam: (last: WorklogEntryPage) => last.next_after,
    enabled: !DEMO && workstreamId !== null,
    refetchInterval: live && !DEMO ? WORKLOG_LIVE_MS : false,
  })
}

/** What a new session would load for one workstream; `null` when the key names
 *  no workstream in that project, which the route answers with a 404. */
export function useWorklogResume(project: string, key: string, enabled = true) {
  return useQuery<WorklogResume | null>({
    queryKey: ["worklogResume", project, key],
    queryFn: async () => {
      const qs = new URLSearchParams({ project, workstream: key })
      try {
        return await apiFetch<WorklogResume>(`/worklog/resume?${qs}`)
      } catch (error) {
        if (error instanceof ApiError && error.status === 404) return null
        throw error
      }
    },
    enabled: !DEMO && enabled,
  })
}

export function useWorklogSearch() {
  return useMutation<WorklogSearchResponse, Error, WorklogSearchParams>({
    mutationFn: (params) =>
      apiFetch<WorklogSearchResponse>("/worklog/search", {
        method: "POST",
        body: JSON.stringify(params),
      }),
  })
}

function invalidateWorklog(qc: QueryClient) {
  for (const key of ["worklogWorkstreams", "worklogEntries", "worklogResume"]) {
    void qc.invalidateQueries({ queryKey: [key] })
  }
}

export function useWorkstreamUpdate() {
  const qc = useQueryClient()
  return useMutation<Workstream, Error, { id: string } & WorkstreamPatch>({
    mutationFn: ({ id, ...patch }) =>
      apiFetch<Workstream>(`/worklog/workstreams/${id}`, {
        method: "PATCH",
        body: JSON.stringify(patch),
      }),
    onSuccess: () => invalidateWorklog(qc),
  })
}

export function useWorkstreamPurge() {
  const qc = useQueryClient()
  return useMutation<void, Error, string>({
    mutationFn: (id) => apiFetch<void>(`/worklog/workstreams/${id}`, { method: "DELETE" }),
    onSuccess: () => invalidateWorklog(qc),
  })
}
```

In `frontend/src/hooks/api/index.ts`, add `export * from "./use-worklog-api"` beside the other exports.

In `frontend/src/lib/query-keys.ts`, add to `QUERY_KEY_SCOPE` (next to `documentsAll`):

```ts
  worklogWorkstreams: {
    kind: "manual",
    reason:
      "GET /worklog/workstreams requires an explicit `project`; the Work log passes the workspace's route param and the Activity list passes each project it enumerates, never the global switcher",
  },
  worklogEntries: {
    kind: "global",
    reason:
      "Addressed by workstream id and carrying no project param, the same shape as documentBlocks",
  },
  worklogResume: {
    kind: "manual",
    reason:
      "GET /worklog/resume takes an explicit `project` and workstream key, supplied per row by the Activity list",
  },
```

- [ ] **Step 4: Run the tests and typecheck**

Run (from `frontend/`): `timeout 300 npx vitest run src/hooks/api/__tests__/use-worklog-api.test.tsx src/lib/__tests__/query-keys.test.ts && timeout 300 npm run typecheck`
Expected: PASS; typecheck reports no error.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/hooks/api/use-worklog-api.ts frontend/src/hooks/api/index.ts frontend/src/lib/query-keys.ts frontend/src/hooks/api/__tests__/use-worklog-api.test.tsx
git commit -m "feat(worklog): add the SPA's work-log hooks"
```

### Task 4: Work log panel

**Files:**
- Create: `frontend/src/features/worklog/components/entry-timeline.tsx`
- Create: `frontend/src/features/worklog/components/work-log-panel.tsx`
- Test: `frontend/src/features/worklog/__tests__/work-log-panel.test.tsx`

**Interfaces:**
- Consumes: `useWorkstreams`, `useWorklogEntries`, `useWorklogResume`, `Workstream`, `WorklogEntry`, `WorklogKind` (Contracts, Task 3).
- Produces: `WorkLogPanel({ project, initialWorkstream })` and `EntryTimeline` (Contracts). Task 5 adds the header and `onOpenDocument`.

**Items:** 1

**Implementer:** dr-superpowers:impl-sonnet-high
**Evaluation:** files 1 - spec 1 - coupling 1 - risk 0 = 3

- [ ] **Step 1: Write the failing test**

Create `frontend/src/features/worklog/__tests__/work-log-panel.test.tsx`:

```tsx
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { render, screen, waitFor, within } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import type { ReactNode } from "react"
import { beforeEach, describe, expect, it, vi } from "vitest"

vi.mock("@/lib/demo-flag", () => ({ DEMO: false }))
vi.mock("@/lib/api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/api")>()),
  apiFetch: vi.fn(),
}))

import { ApiError, apiFetch } from "@/lib/api"
import type { WorklogEntry, Workstream } from "@/hooks/api"
import { WorkLogPanel } from "../components/work-log-panel"

const OPEN: Workstream = {
  id: "w-open",
  project: "darkmem",
  key: "plan-a",
  title: "Plan A",
  client: "dr-superpowers",
  state: "open",
  closed_at: null,
  retain: false,
  properties: {},
  last_entry_at: "2026-09-28T10:00:00Z",
  created_at: "2026-09-28T08:00:00Z",
  updated_at: "2026-09-28T10:00:00Z",
}
const CLOSED: Workstream = {
  ...OPEN,
  id: "w-closed",
  key: "plan-old",
  title: "Old plan",
  state: "closed",
  closed_at: "2026-09-01T00:00:00Z",
}
const FAR: Workstream = { ...OPEN, id: "w-far", key: "plan-z", title: "Far plan" }
const ENTRIES: WorklogEntry[] = [
  {
    id: "e1",
    workstream_id: "w-open",
    seq: 1,
    run_key: "claude-code:r1",
    kind: "ledger",
    body: "Task 1: done\n",
    properties: {},
    created_at: "2026-09-28T09:00:00Z",
  },
  {
    id: "e2",
    workstream_id: "w-open",
    seq: 2,
    run_key: "claude-code:r1",
    kind: "checkpoint",
    body: "## Where it stands\n\nHalfway there",
    properties: {},
    created_at: "2026-09-28T10:00:00Z",
  },
]

function routeApi(workstreams: { open: Workstream[]; closed: Workstream[] }) {
  vi.mocked(apiFetch).mockImplementation((path: string) => {
    if (path.startsWith("/worklog/workstreams?")) {
      const qs = new URLSearchParams(path.split("?")[1])
      const items = qs.get("state") === "open" ? workstreams.open : workstreams.closed
      // One workstream per page, so paging is observable with two of them.
      const at = qs.get("before") ? 1 : 0
      return Promise.resolve({
        items: items.slice(at, at + 1),
        next_before: items.length > at + 1 ? "cursor" : null,
      })
    }
    if (path.startsWith("/worklog/resume?")) {
      const key = new URLSearchParams(path.split("?")[1]).get("workstream")
      return key === FAR.key
        ? Promise.resolve({ workstream: FAR, checkpoint: null, notes: [], notes_truncated: false, ledger: [] })
        : Promise.reject(new ApiError("No workstream", 404))
    }
    const entries = path.match(/^\/worklog\/workstreams\/([^/]+)\/entries\?(.*)$/)
    if (entries) {
      const kind = new URLSearchParams(entries[2]).get("kind")
      const items = entries[1] === "w-open" ? ENTRIES : []
      return Promise.resolve({
        items: kind ? items.filter((e) => e.kind === kind) : items,
        next_after: null,
      })
    }
    return Promise.reject(new Error(`unrouted ${path}`))
  })
}

function wrapper({ children }: { children: ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>
}

beforeEach(() => {
  vi.mocked(apiFetch).mockReset()
})

describe("WorkLogPanel", () => {
  it("opens on the first open workstream and reads an entry in full", async () => {
    routeApi({ open: [OPEN], closed: [CLOSED] })
    const user = userEvent.setup()
    render(<WorkLogPanel project="darkmem" />, { wrapper })

    expect(await screen.findByText("Task 1: done")).toBeInTheDocument()
    await user.click(screen.getByText("Where it stands"))
    const detail = screen.getByRole("article", { name: "entry" })
    expect(within(detail).getByText("Halfway there")).toBeInTheDocument()
  })

  it("keeps closed workstreams collapsed until asked", async () => {
    routeApi({ open: [OPEN], closed: [CLOSED] })
    const user = userEvent.setup()
    render(<WorkLogPanel project="darkmem" />, { wrapper })

    await screen.findByText("Plan A")
    expect(screen.queryByText("Old plan")).toBeNull()
    await user.click(screen.getByRole("button", { name: "Closed (1)" }))
    await user.click(screen.getByText("Old plan"))
    expect(await screen.findByText("No entries yet")).toBeInTheDocument()
  })

  it("filters entries by kind on the server", async () => {
    routeApi({ open: [OPEN], closed: [] })
    const user = userEvent.setup()
    render(<WorkLogPanel project="darkmem" />, { wrapper })

    await screen.findByText("Where it stands")
    await user.click(screen.getByRole("radio", { name: "Ledger" }))
    await waitFor(() => expect(screen.queryByText("Where it stands")).toBeNull())
    expect(screen.getByText("Task 1: done")).toBeInTheDocument()
    expect(
      vi.mocked(apiFetch).mock.calls.some(([path]) => String(path).includes("kind=ledger")),
    ).toBe(true)
  })

  it("selects the workstream it is handed, even a closed one", async () => {
    routeApi({ open: [OPEN], closed: [CLOSED] })
    render(<WorkLogPanel project="darkmem" initialWorkstream="plan-old" />, { wrapper })

    expect(await screen.findByRole("region", { name: "workstream plan-old" })).toBeInTheDocument()
    expect(screen.getByText("Old plan", { selector: "h3" })).toBeInTheDocument()
  })

  it("pages through a project's workstreams", async () => {
    routeApi({ open: [OPEN, { ...OPEN, id: "w-two", key: "plan-b", title: "Plan B" }], closed: [] })
    const user = userEvent.setup()
    render(<WorkLogPanel project="darkmem" />, { wrapper })

    await screen.findByText("Plan A")
    expect(screen.queryByText("Plan B")).toBeNull()
    await user.click(screen.getByRole("button", { name: "More open workstreams" }))
    expect(await screen.findByText("Plan B")).toBeInTheDocument()
  })

  it("looks up a workstream past the loaded pages instead of replacing it", async () => {
    routeApi({ open: [OPEN], closed: [] })
    render(<WorkLogPanel project="darkmem" initialWorkstream="plan-z" />, { wrapper })

    expect(await screen.findByRole("region", { name: "workstream plan-z" })).toBeInTheDocument()
    expect(screen.getByText("Far plan", { selector: "h3" })).toBeInTheDocument()
  })

  it("says so when the project has no work log", async () => {
    routeApi({ open: [], closed: [] })
    render(<WorkLogPanel project="darkmem" />, { wrapper })
    expect(await screen.findByText("No work log yet")).toBeInTheDocument()
  })

  it("reports a failed read as a failure, not as an empty log", async () => {
    vi.mocked(apiFetch).mockRejectedValue(new Error("boom"))
    render(<WorkLogPanel project="darkmem" />, { wrapper })
    expect(await screen.findByText("Could not read the work log")).toBeInTheDocument()
  })
})
```

- [ ] **Step 2: Run it to verify it fails**

Run (from `frontend/`): `timeout 300 npx vitest run src/features/worklog/__tests__/work-log-panel.test.tsx`
Expected: FAIL (cannot resolve `../components/work-log-panel`).

- [ ] **Step 3: Create the entry timeline**

Create `frontend/src/features/worklog/components/entry-timeline.tsx`:

```tsx
import { useMemo, useState } from "react"
import { Badge } from "darkraise-ui/components/badge"
import { Button } from "darkraise-ui/components/button"
import {
  SegmentGroup,
  SegmentGroupIndicator,
  SegmentGroupItem,
} from "darkraise-ui/components/segment-group"
import { Skeleton } from "darkraise-ui/components/skeleton"
import {
  VirtualizedTimeline,
  type TimelineBucket,
} from "darkraise-ui/components/virtualized-timeline"
import { cn } from "darkraise-ui/lib"
import { EmptyState } from "@/components/darkmem"
import { AppMarkdown } from "@/components/markdown"
import {
  useWorklogEntries,
  type WorklogEntry,
  type WorklogKind,
  type Workstream,
} from "@/hooks/api"
import { formatWhen } from "@/lib/format"

type KindFilter = "all" | WorklogKind

const KIND_VARIANT: Record<WorklogKind, "default" | "secondary" | "outline"> = {
  checkpoint: "default",
  ledger: "outline",
  note: "secondary",
}

const ROW_HEIGHT = 40

/** The line a row shows: the first non-blank line, without a heading's hashes. */
export function firstLine(body: string): string {
  const line = body.split("\n").find((l) => l.trim()) ?? ""
  return line.replace(/^#+\s*/, "").trim()
}

/** UTC day buckets in entry order, so a ledger still reads forward. */
function bucketsByDay(entries: WorklogEntry[]): TimelineBucket<WorklogEntry>[] {
  const days = new Map<string, WorklogEntry[]>()
  for (const entry of entries) {
    const day = entry.created_at.slice(0, 10)
    const bucket = days.get(day)
    if (bucket) bucket.push(entry)
    else days.set(day, [entry])
  }
  return [...days].map(([day, items]) => ({ id: day, date: day, count: items.length, items }))
}

function KindBadge({ kind }: { kind: WorklogKind }) {
  return <Badge variant={KIND_VARIANT[kind]}>{kind}</Badge>
}

function EntryRow({ entry, selected }: { entry: WorklogEntry; selected: boolean }) {
  return (
    <div
      className={cn(
        "flex h-full items-center gap-2 px-2 text-sm",
        selected && "bg-primary/5",
      )}
    >
      <KindBadge kind={entry.kind} />
      <span className="text-muted-foreground w-12 shrink-0 font-mono text-xs">
        {entry.created_at.slice(11, 16)}
      </span>
      <span className="min-w-0 flex-1 truncate">{firstLine(entry.body)}</span>
      <span className="text-muted-foreground hidden max-w-40 truncate font-mono text-xs md:inline">
        {entry.run_key}
      </span>
    </div>
  )
}

/** A checkpoint or note renders as markdown; a ledger chunk stays verbatim,
 *  because its bytes are the ledger file's own. */
function EntryDetail({ entry }: { entry: WorklogEntry | null }) {
  if (!entry) {
    return (
      <p className="text-muted-foreground text-sm">
        Select an entry to read it in full.
      </p>
    )
  }
  return (
    <article aria-label="entry" className="border-border min-w-0 space-y-2 rounded-md border p-3">
      <div className="flex flex-wrap items-center gap-2">
        <KindBadge kind={entry.kind} />
        <span className="text-muted-foreground font-mono text-xs">
          #{entry.seq} · {entry.run_key} · {formatWhen(entry.created_at)}
        </span>
      </div>
      {entry.kind === "ledger" ? (
        <pre className="bg-muted/40 overflow-x-auto rounded p-2 font-mono text-sm whitespace-pre-wrap">
          {entry.body}
        </pre>
      ) : (
        <AppMarkdown>{entry.body}</AppMarkdown>
      )}
    </article>
  )
}

/** One workstream's entries: kind filter, a day-bucketed timeline of one-line
 *  rows, and the selected entry in full beside it. The timeline's rows have a
 *  fixed height, so a checkpoint expands into the detail pane, not in place. */
export function EntryTimeline({ workstream }: { workstream: Workstream }) {
  const [kind, setKind] = useState<KindFilter>("all")
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const entries = useWorklogEntries(
    workstream.id,
    kind === "all" ? null : kind,
    workstream.state === "open",
  )
  const items = useMemo(
    () => entries.data?.pages.flatMap((page) => page.items) ?? [],
    [entries.data],
  )
  const buckets = useMemo(() => bucketsByDay(items), [items])
  const selected = items.find((e) => e.id === selectedId) ?? null

  let body
  if (entries.isError) {
    body = (
      <EmptyState
        kind="failed"
        title="Could not read this workstream"
        description={entries.error.message}
      />
    )
  } else if (entries.isPending) {
    body = <Skeleton className="h-64 w-full" />
  } else if (items.length === 0 && kind !== "all") {
    body = <EmptyState kind="filtered" title={`No ${kind} entries`} />
  } else if (items.length === 0) {
    body = <EmptyState kind="empty" title="No entries yet" />
  } else {
    body = (
      <div className="grid gap-3 lg:grid-cols-2">
        <VirtualizedTimeline<WorklogEntry>
          className="h-96"
          layout="list"
          rowHeight={ROW_HEIGHT}
          granularity="day"
          buckets={buckets}
          getItemId={(entry) => entry.id}
          onItemClick={(entry) => setSelectedId(entry.id)}
          renderItem={({ item }) => (
            <EntryRow entry={item} selected={item.id === selectedId} />
          )}
        />
        <EntryDetail entry={selected} />
      </div>
    )
  }

  return (
    <div className="space-y-3">
      <SegmentGroup
        value={kind}
        onValueChange={(next) => {
          if (next) {
            setKind(next as KindFilter)
            setSelectedId(null)
          }
        }}
        variant="default"
        aria-label="entry kind"
      >
        <SegmentGroupIndicator />
        <SegmentGroupItem value="all">All</SegmentGroupItem>
        <SegmentGroupItem value="checkpoint">Checkpoints</SegmentGroupItem>
        <SegmentGroupItem value="ledger">Ledger</SegmentGroupItem>
        <SegmentGroupItem value="note">Notes</SegmentGroupItem>
      </SegmentGroup>
      {body}
      {entries.hasNextPage ? (
        <Button
          variant="outline"
          disabled={entries.isFetchingNextPage}
          onClick={() => void entries.fetchNextPage()}
        >
          Load later entries
        </Button>
      ) : null}
    </div>
  )
}
```

- [ ] **Step 4: Create the panel**

Create `frontend/src/features/worklog/components/work-log-panel.tsx`:

```tsx
import { useMemo, useState } from "react"
import { ScrollText } from "lucide-react"
import { Button } from "darkraise-ui/components/button"
import { Skeleton } from "darkraise-ui/components/skeleton"
import { cn } from "darkraise-ui/lib"
import { EmptyState, listItemClass } from "@/components/darkmem"
import { useWorklogResume, useWorkstreams, type Workstream } from "@/hooks/api"
import { formatWhen } from "@/lib/format"
import { EntryTimeline } from "./entry-timeline"

function WorkstreamList({
  items,
  selectedKey,
  onSelect,
}: {
  items: Workstream[]
  selectedKey: string | null
  onSelect: (key: string) => void
}) {
  return (
    <ul className="space-y-1.5">
      {items.map((w) => (
        <li key={w.id}>
          <button
            type="button"
            aria-pressed={w.key === selectedKey}
            onClick={() => onSelect(w.key)}
            className={listItemClass({
              interactive: true,
              className: cn(
                "bg-card flex w-full flex-col gap-0.5 p-2.5 text-left",
                w.key === selectedKey && "border-primary/45 bg-primary/5",
              ),
            })}
          >
            <span className="truncate text-sm font-semibold">{w.title ?? w.key}</span>
            <span className="text-muted-foreground truncate font-mono text-xs">
              {w.key} · {w.state} · {formatWhen(w.last_entry_at)}
            </span>
          </button>
        </li>
      ))}
    </ul>
  )
}

function MoreButton({
  query,
  label,
}: {
  query: { hasNextPage: boolean; isFetchingNextPage: boolean; fetchNextPage: () => unknown }
  label: string
}) {
  if (!query.hasNextPage) return null
  return (
    <Button
      variant="ghost"
      size="sm"
      disabled={query.isFetchingNextPage}
      onClick={() => void query.fetchNextPage()}
    >
      {label}
    </Button>
  )
}

function WorkstreamSummary({ workstream }: { workstream: Workstream }) {
  return (
    <div className="space-y-0.5">
      <h3 className="text-base font-semibold">{workstream.title ?? workstream.key}</h3>
      <p className="text-muted-foreground font-mono text-xs">
        {workstream.key} · {workstream.state}
        {workstream.client ? ` · ${workstream.client}` : ""}
      </p>
    </div>
  )
}

/** A project's work log (spec §8): its workstreams, open first and closed
 *  collapsed, beside the selected one's entries. `initialWorkstream` is a
 *  workstream key; without it the newest open workstream is selected. */
export function WorkLogPanel({
  project,
  initialWorkstream,
}: {
  project: string
  initialWorkstream?: string
}) {
  const open = useWorkstreams(project, "open")
  const closed = useWorkstreams(project, "closed")
  const openItems = useMemo(
    () => open.data?.pages.flatMap((page) => page.items) ?? [],
    [open.data],
  )
  const closedItems = useMemo(
    () => closed.data?.pages.flatMap((page) => page.items) ?? [],
    [closed.data],
  )
  const [selectedKey, setSelectedKey] = useState<string | null>(initialWorkstream ?? null)
  const [showClosed, setShowClosed] = useState(false)

  const listed =
    selectedKey === null
      ? undefined
      : (openItems.find((w) => w.key === selectedKey) ??
        closedItems.find((w) => w.key === selectedKey))
  // A key past the loaded pages (a link from Activity, a search hit) is looked
  // up on its own rather than silently replaced by the first open workstream.
  const unlisted =
    selectedKey !== null && listed === undefined && !open.isPending && !closed.isPending
  const lookup = useWorklogResume(project, selectedKey ?? "", unlisted)
  const resolving = unlisted && lookup.isLoading
  const selected =
    listed ?? (unlisted ? lookup.data?.workstream : undefined) ?? openItems[0] ?? null
  const closedVisible = showClosed || selected?.state === "closed"

  if (open.isError || closed.isError) {
    return (
      <EmptyState
        kind="failed"
        title="Could not read the work log"
        description={(open.error ?? closed.error)?.message}
      />
    )
  }
  if (open.isPending || closed.isPending) {
    return <Skeleton className="h-48 w-full" />
  }
  if (openItems.length === 0 && closedItems.length === 0) {
    return (
      <EmptyState
        kind="empty"
        icon={ScrollText}
        title="No work log yet"
        description="A coding client's checkpoints, ledger and notes appear here once it appends to a workstream in this project with worklog_append."
      />
    )
  }

  return (
    <div className="grid gap-4 md:grid-cols-[16rem_minmax(0,1fr)]">
      <nav aria-label="workstreams" className="space-y-3">
        <WorkstreamList
          items={openItems}
          selectedKey={selected?.key ?? null}
          onSelect={setSelectedKey}
        />
        <MoreButton query={open} label="More open workstreams" />
        {closedItems.length > 0 ? (
          <div className="space-y-1.5">
            <Button
              variant="ghost"
              size="sm"
              aria-expanded={closedVisible}
              onClick={() => setShowClosed((shown) => !shown)}
            >
              {closedVisible
                ? "Hide closed"
                : `Closed (${closedItems.length}${closed.hasNextPage ? "+" : ""})`}
            </Button>
            {closedVisible ? (
              <>
                <WorkstreamList
                  items={closedItems}
                  selectedKey={selected?.key ?? null}
                  onSelect={setSelectedKey}
                />
                <MoreButton query={closed} label="More closed workstreams" />
              </>
            ) : null}
          </div>
        ) : null}
      </nav>
      {resolving ? (
        <Skeleton className="h-64 w-full" />
      ) : selected ? (
        <section aria-label={`workstream ${selected.key}`} className="min-w-0 space-y-3">
          <WorkstreamSummary workstream={selected} />
          <EntryTimeline key={selected.id} workstream={selected} />
        </section>
      ) : (
        <EmptyState
          kind="empty"
          icon={ScrollText}
          title="No open workstream"
          description="Every workstream in this project is closed; open one from the closed list to read it."
        />
      )}
    </div>
  )
}
```

- [ ] **Step 5: Run the test and typecheck**

Run (from `frontend/`): `timeout 300 npx vitest run src/features/worklog/__tests__/work-log-panel.test.tsx && timeout 300 npm run typecheck`
Expected: PASS; typecheck reports no error.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/features/worklog
git commit -m "feat(worklog): add the Work log panel"
```

### Task 5: Work log header actions

**Files:**
- Create: `frontend/src/features/worklog/components/workstream-header.tsx`
- Modify: `frontend/src/features/worklog/components/work-log-panel.tsx` (replace `WorkstreamSummary`; add `onOpenDocument`)
- Test: `frontend/src/features/worklog/__tests__/workstream-header.test.tsx`

**Interfaces:**
- Consumes: `useWorkstreamUpdate`, `useWorkstreamPurge`, `Workstream` (Contracts, Task 3); `WorkLogPanel` (Task 4).
- Produces: `WorkstreamHeader({ workstream, onOpenDocument })`; `WorkLogPanel` gains `onOpenDocument?: (uri: string) => void` (Contracts).

**Items:** 1

**Implementer:** dr-superpowers:impl-opus-low
**Evaluation:** files 1 - spec 1 - coupling 1 - risk 1 = 4

- [ ] **Step 1: Write the failing test**

Create `frontend/src/features/worklog/__tests__/workstream-header.test.tsx`:

```tsx
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { render, screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import type { ReactNode } from "react"
import { beforeEach, describe, expect, it, vi } from "vitest"

vi.mock("@/lib/demo-flag", () => ({ DEMO: false }))
vi.mock("@/lib/api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/api")>()),
  apiFetch: vi.fn(),
}))
vi.mock("darkraise-ui/components/sonner", () => ({
  toast: { error: vi.fn(), success: vi.fn() },
  Toaster: () => null,
}))

import { apiFetch } from "@/lib/api"
import type { Workstream } from "@/hooks/api"
import { WorkstreamHeader } from "../components/workstream-header"

const WORKSTREAM: Workstream = {
  id: "w1",
  project: "darkmem",
  key: "plan-a",
  title: "Plan A",
  client: "dr-superpowers",
  state: "open",
  closed_at: null,
  retain: false,
  properties: {
    plan_uri: "superpowers/plans/plan-a.md",
    spec_uri: "superpowers/specs/spec-a.md",
  },
  last_entry_at: "2026-09-28T10:00:00Z",
  created_at: "2026-09-28T08:00:00Z",
  updated_at: "2026-09-28T10:00:00Z",
}

function wrapper({ children }: { children: ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>
}

beforeEach(() => {
  vi.mocked(apiFetch).mockReset()
  vi.mocked(apiFetch).mockResolvedValue({})
})

describe("WorkstreamHeader", () => {
  it("links the documents the workstream names, and only those", async () => {
    const onOpen = vi.fn()
    const user = userEvent.setup()
    render(<WorkstreamHeader workstream={WORKSTREAM} onOpenDocument={onOpen} />, { wrapper })

    await user.click(screen.getByRole("button", { name: "Plan" }))
    expect(onOpen).toHaveBeenCalledWith("superpowers/plans/plan-a.md")
    expect(screen.getByRole("button", { name: "Spec" })).toBeInTheDocument()
    expect(screen.queryByRole("button", { name: "Handoff" })).toBeNull()
  })

  it("closes an open workstream and reopens a closed one", async () => {
    const user = userEvent.setup()
    const { rerender } = render(<WorkstreamHeader workstream={WORKSTREAM} />, { wrapper })

    await user.click(screen.getByRole("button", { name: "Close" }))
    expect(vi.mocked(apiFetch)).toHaveBeenLastCalledWith("/worklog/workstreams/w1", {
      method: "PATCH",
      body: JSON.stringify({ state: "closed" }),
    })

    rerender(
      <WorkstreamHeader
        workstream={{ ...WORKSTREAM, state: "closed", closed_at: "2026-09-28T11:00:00Z" }}
      />,
    )
    await user.click(screen.getByRole("button", { name: "Reopen" }))
    expect(vi.mocked(apiFetch)).toHaveBeenLastCalledWith("/worklog/workstreams/w1", {
      method: "PATCH",
      body: JSON.stringify({ state: "open" }),
    })
  })

  it("purges only after the confirmation", async () => {
    const user = userEvent.setup()
    render(<WorkstreamHeader workstream={WORKSTREAM} />, { wrapper })

    await user.click(screen.getByRole("button", { name: "Purge workstream" }))
    expect(vi.mocked(apiFetch)).not.toHaveBeenCalled()
    await user.click(await screen.findByRole("button", { name: "Purge" }))
    await waitFor(() =>
      expect(vi.mocked(apiFetch)).toHaveBeenCalledWith("/worklog/workstreams/w1", {
        method: "DELETE",
      }),
    )
  })
})
```

- [ ] **Step 2: Run it to verify it fails**

Run (from `frontend/`): `timeout 300 npx vitest run src/features/worklog/__tests__/workstream-header.test.tsx`
Expected: FAIL (cannot resolve `../components/workstream-header`).

- [ ] **Step 3: Create the header**

Create `frontend/src/features/worklog/components/workstream-header.tsx`:

```tsx
import { useState } from "react"
import { Trash2 } from "lucide-react"
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "darkraise-ui/components/alert-dialog"
import { Button } from "darkraise-ui/components/button"
import { toast } from "darkraise-ui/components/sonner"
import { IconButton } from "@/components/darkmem"
import { useWorkstreamPurge, useWorkstreamUpdate, type Workstream } from "@/hooks/api"

/** The workstream properties a client may point at a filed document with. */
const LINKS = [
  ["plan_uri", "Plan"],
  ["spec_uri", "Spec"],
  ["handoff_uri", "Handoff"],
] as const

export function WorkstreamHeader({
  workstream,
  onOpenDocument,
}: {
  workstream: Workstream
  onOpenDocument?: (uri: string) => void
}) {
  const [confirmOpen, setConfirmOpen] = useState(false)
  const update = useWorkstreamUpdate()
  const purge = useWorkstreamPurge()
  const closing = workstream.state === "open"
  const links = LINKS.flatMap(([property, label]) => {
    const uri = workstream.properties[property]
    return typeof uri === "string" && uri ? [{ uri, label }] : []
  })

  return (
    <div className="flex flex-wrap items-start gap-3">
      <div className="min-w-0 flex-1 space-y-0.5">
        <h3 className="text-base font-semibold">{workstream.title ?? workstream.key}</h3>
        <p className="text-muted-foreground font-mono text-xs">
          {workstream.key} · {workstream.state}
          {workstream.client ? ` · ${workstream.client}` : ""}
          {workstream.retain ? " · retained" : ""}
        </p>
        {links.length > 0 ? (
          <div className="flex flex-wrap items-center gap-1">
            {links.map(({ uri, label }) =>
              onOpenDocument ? (
                <Button
                  key={label}
                  variant="link"
                  size="sm"
                  title={uri}
                  onClick={() => onOpenDocument(uri)}
                >
                  {label}
                </Button>
              ) : (
                <span key={label} className="text-muted-foreground font-mono text-xs">
                  {label}: {uri}
                </span>
              ),
            )}
          </div>
        ) : null}
      </div>
      <div className="flex items-center gap-1">
        <Button
          variant="outline"
          size="sm"
          disabled={update.isPending}
          onClick={() =>
            update.mutate(
              { id: workstream.id, state: closing ? "closed" : "open" },
              { onError: (error) => toast.error(error.message) },
            )
          }
        >
          {closing ? "Close" : "Reopen"}
        </Button>
        <IconButton
          icon={Trash2}
          label="Purge workstream"
          variant="ghost"
          className="text-destructive hover:text-destructive"
          onClick={() => setConfirmOpen(true)}
        />
      </div>

      <AlertDialog open={confirmOpen} onOpenChange={setConfirmOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Purge {workstream.title ?? workstream.key}?</AlertDialogTitle>
            <AlertDialogDescription>
              This erases the workstream and every entry in it. The journal
              keeps only that it was purged and how many entries went. This
              cannot be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={() =>
                purge.mutate(workstream.id, {
                  onSuccess: () => {
                    toast.success("Workstream purged")
                    setConfirmOpen(false)
                  },
                  onError: (error) => toast.error(error.message),
                })
              }
            >
              Purge
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  )
}
```

- [ ] **Step 4: Use it in the panel**

In `frontend/src/features/worklog/components/work-log-panel.tsx`:

- delete the `WorkstreamSummary` function and add `import { WorkstreamHeader } from "./workstream-header"`;
- add `onOpenDocument` to the props:

```tsx
export function WorkLogPanel({
  project,
  initialWorkstream,
  onOpenDocument,
}: {
  project: string
  initialWorkstream?: string
  onOpenDocument?: (uri: string) => void
}) {
```

- replace `<WorkstreamSummary workstream={selected} />` with `<WorkstreamHeader workstream={selected} onOpenDocument={onOpenDocument} />`.

- [ ] **Step 5: Run the worklog tests and typecheck**

Run (from `frontend/`): `timeout 300 npx vitest run src/features/worklog && timeout 300 npm run typecheck`
Expected: PASS (the Task 4 tests still find the `h3` title); typecheck reports no error.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/features/worklog
git commit -m "feat(worklog): close, reopen and purge a workstream"
```

### Task 6: Work log search

**Files:**
- Create: `frontend/src/features/worklog/components/worklog-search.tsx`
- Modify: `frontend/src/features/worklog/components/work-log-panel.tsx`
- Modify: `frontend/src/features/worklog/components/entry-timeline.tsx` (`initialEntryId`)
- Test: `frontend/src/features/worklog/__tests__/worklog-search.test.tsx`

**Interfaces:**
- Consumes: `useWorklogSearch`, `WorklogSearchHit` (Contracts, Task 3); `WorkLogPanel`, `EntryTimeline`, `firstLine` (Task 4).
- Produces: `WorklogSearch({ project, onOpen }: { project: string; onOpen: (workstreamKey: string, entryId: string) => void })`; `EntryTimeline` gains `initialEntryId?: string`.

**Items:** 1

**Implementer:** dr-superpowers:impl-sonnet-high
**Evaluation:** files 1 - spec 1 - coupling 1 - risk 0 = 3

- [ ] **Step 1: Write the failing test**

Create `frontend/src/features/worklog/__tests__/worklog-search.test.tsx`:

```tsx
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { render, screen, within } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import type { ReactNode } from "react"
import { beforeEach, describe, expect, it, vi } from "vitest"

vi.mock("@/lib/demo-flag", () => ({ DEMO: false }))
vi.mock("@/lib/api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/api")>()),
  apiFetch: vi.fn(),
}))

import { apiFetch } from "@/lib/api"
import type { WorklogEntry, Workstream } from "@/hooks/api"
import { WorkLogPanel } from "../components/work-log-panel"
import { WorklogSearch } from "../components/worklog-search"

const OPEN: Workstream = {
  id: "w-open",
  project: "darkmem",
  key: "plan-a",
  title: "Plan A",
  client: null,
  state: "open",
  closed_at: null,
  retain: false,
  properties: {},
  last_entry_at: "2026-09-28T10:00:00Z",
  created_at: "2026-09-28T08:00:00Z",
  updated_at: "2026-09-28T10:00:00Z",
}
const OTHER: Workstream = { ...OPEN, id: "w-other", key: "plan-b", title: "Plan B" }
const FAR: Workstream = { ...OPEN, id: "w-far", key: "plan-z", title: "Far plan" }
const HIT: WorklogEntry = {
  id: "e9",
  workstream_id: "w-other",
  seq: 9,
  run_key: "claude-code:r2",
  kind: "note",
  body: "Retention runs at 05:15 UTC",
  properties: {},
  created_at: "2026-09-28T09:30:00Z",
}

const FAR_HIT: WorklogEntry = {
  ...HIT,
  id: "e20",
  workstream_id: "w-far",
  seq: 20,
  body: "Retention on the far plan",
}

function wrapper({ children }: { children: ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>
}

beforeEach(() => {
  vi.mocked(apiFetch).mockReset()
  vi.mocked(apiFetch).mockImplementation((path: string) => {
    if (path === "/worklog/search") {
      return Promise.resolve({
        items: [
          { entry: HIT, workstream: "plan-b", rrf_score: 0.02, arms: ["keyword"] },
          { entry: FAR_HIT, workstream: "plan-z", rrf_score: 0.01, arms: ["keyword"] },
        ],
        semantic_ran: false,
      })
    }
    if (path === "/worklog/resume?project=darkmem&workstream=plan-z") {
      return Promise.resolve({ workstream: FAR, checkpoint: null, notes: [], notes_truncated: false, ledger: [] })
    }
    if (path.startsWith("/worklog/workstreams/w-far/entries")) {
      return Promise.resolve({ items: [FAR_HIT], next_after: null })
    }
    if (path.startsWith("/worklog/workstreams?")) {
      const open = path.includes("state=open")
      return Promise.resolve({ items: open ? [OPEN, OTHER] : [], next_before: null })
    }
    if (path.startsWith("/worklog/workstreams/w-other/entries")) {
      return Promise.resolve({ items: [HIT], next_after: null })
    }
    if (path.includes("/entries")) return Promise.resolve({ items: [], next_after: null })
    return Promise.reject(new Error(`unrouted ${path}`))
  })
})

describe("WorklogSearch", () => {
  it("searches the project and says when only the keyword arm ran", async () => {
    const onOpen = vi.fn()
    const user = userEvent.setup()
    render(<WorklogSearch project="darkmem" onOpen={onOpen} />, { wrapper })

    await user.type(screen.getByRole("searchbox", { name: "Search the work log" }), "retention{Enter}")
    expect(vi.mocked(apiFetch)).toHaveBeenCalledWith("/worklog/search", {
      method: "POST",
      body: JSON.stringify({ project: "darkmem", query: "retention" }),
    })
    expect(await screen.findByText(/keyword matches only/i)).toBeInTheDocument()
    await user.click(screen.getByRole("button", { name: /Retention runs at 05:15 UTC/ }))
    expect(onOpen).toHaveBeenCalledWith("plan-b", "e9")
  })

  it("opens a hit's workstream and entry in the panel", async () => {
    const user = userEvent.setup()
    render(<WorkLogPanel project="darkmem" />, { wrapper })

    await user.type(
      await screen.findByRole("searchbox", { name: "Search the work log" }),
      "retention{Enter}",
    )
    await user.click(await screen.findByRole("button", { name: /Retention runs at 05:15 UTC/ }))
    expect(await screen.findByRole("region", { name: "workstream plan-b" })).toBeInTheDocument()
    const detail = await screen.findByRole("article", { name: "entry" })
    expect(within(detail).getByText("Retention runs at 05:15 UTC")).toBeInTheDocument()
  })

  it("opens a hit whose workstream is not in the loaded list", async () => {
    const user = userEvent.setup()
    render(<WorkLogPanel project="darkmem" />, { wrapper })

    await user.type(
      await screen.findByRole("searchbox", { name: "Search the work log" }),
      "retention{Enter}",
    )
    await user.click(await screen.findByRole("button", { name: /Retention on the far plan/ }))
    expect(await screen.findByRole("region", { name: "workstream plan-z" })).toBeInTheDocument()
    const detail = await screen.findByRole("article", { name: "entry" })
    expect(within(detail).getByText("Retention on the far plan")).toBeInTheDocument()
  })
})
```

- [ ] **Step 2: Run it to verify it fails**

Run (from `frontend/`): `timeout 300 npx vitest run src/features/worklog/__tests__/worklog-search.test.tsx`
Expected: FAIL (cannot resolve `../components/worklog-search`).

- [ ] **Step 3: Create the search**

Create `frontend/src/features/worklog/components/worklog-search.tsx`:

```tsx
import { useState } from "react"
import { Badge } from "darkraise-ui/components/badge"
import { Input } from "darkraise-ui/components/input"
import { EmptyState, listItemClass } from "@/components/darkmem"
import { useWorklogSearch } from "@/hooks/api"
import { firstLine } from "./entry-timeline"

/** `worklog_search` over one project's workstreams (spec §8). A hit opens its
 *  workstream with the entry selected. */
export function WorklogSearch({
  project,
  onOpen,
}: {
  project: string
  onOpen: (workstreamKey: string, entryId: string) => void
}) {
  const [query, setQuery] = useState("")
  const search = useWorklogSearch()
  const hits = search.data?.items ?? []

  return (
    <div className="space-y-2">
      <form
        role="search"
        onSubmit={(event) => {
          event.preventDefault()
          const trimmed = query.trim()
          if (trimmed) search.mutate({ project, query: trimmed })
        }}
      >
        <Input
          type="search"
          aria-label="Search the work log"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder="Search this project's work log by words or meaning…"
        />
      </form>
      {search.isError ? (
        <EmptyState kind="failed" title="The search failed" description={search.error.message} />
      ) : search.isSuccess && hits.length === 0 ? (
        <EmptyState kind="filtered" title="No entry matches" />
      ) : null}
      {search.isSuccess && !search.data.semantic_ran ? (
        <p className="text-muted-foreground text-xs">
          Keyword matches only: the semantic arm did not run.
        </p>
      ) : null}
      {hits.length > 0 ? (
        <ul className="space-y-1.5">
          {hits.map((hit) => (
            <li key={hit.entry.id}>
              <button
                type="button"
                onClick={() => onOpen(hit.workstream, hit.entry.id)}
                className={listItemClass({
                  interactive: true,
                  className: "bg-card flex w-full items-center gap-2 p-2 text-left text-sm",
                })}
              >
                <Badge variant="outline">{hit.entry.kind}</Badge>
                <span className="text-muted-foreground shrink-0 font-mono text-xs">
                  {hit.workstream}
                </span>
                <span className="min-w-0 flex-1 truncate">{firstLine(hit.entry.body)}</span>
              </button>
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  )
}
```

- [ ] **Step 4: Let the timeline start on an entry**

In `frontend/src/features/worklog/components/entry-timeline.tsx`, change the component's signature and its selection state to:

```tsx
export function EntryTimeline({
  workstream,
  initialEntryId,
}: {
  workstream: Workstream
  initialEntryId?: string
}) {
  const [kind, setKind] = useState<KindFilter>("all")
  const [selectedId, setSelectedId] = useState<string | null>(initialEntryId ?? null)
```

- [ ] **Step 5: Wire it into the panel**

In `frontend/src/features/worklog/components/work-log-panel.tsx`, add `import { WorklogSearch } from "./worklog-search"`, add `const [focusEntryId, setFocusEntryId] = useState<string | undefined>(undefined)` after the `showClosed` state, and replace the final `return (…)` of `WorkLogPanel` (the one after the "No work log yet" early return) with:

```tsx
  const selectFromList = (key: string) => {
    setSelectedKey(key)
    setFocusEntryId(undefined)
  }

  return (
    <div className="space-y-4">
      <WorklogSearch
        project={project}
        onOpen={(key, entryId) => {
          setSelectedKey(key)
          setFocusEntryId(entryId)
        }}
      />
      <div className="grid gap-4 md:grid-cols-[16rem_minmax(0,1fr)]">
        <nav aria-label="workstreams" className="space-y-3">
          <WorkstreamList
            items={openItems}
            selectedKey={selected?.key ?? null}
            onSelect={selectFromList}
          />
          <MoreButton query={open} label="More open workstreams" />
          {closedItems.length > 0 ? (
            <div className="space-y-1.5">
              <Button
                variant="ghost"
                size="sm"
                aria-expanded={closedVisible}
                onClick={() => setShowClosed((shown) => !shown)}
              >
                {closedVisible
                  ? "Hide closed"
                  : `Closed (${closedItems.length}${closed.hasNextPage ? "+" : ""})`}
              </Button>
              {closedVisible ? (
                <>
                  <WorkstreamList
                    items={closedItems}
                    selectedKey={selected?.key ?? null}
                    onSelect={selectFromList}
                  />
                  <MoreButton query={closed} label="More closed workstreams" />
                </>
              ) : null}
            </div>
          ) : null}
        </nav>
        {resolving ? (
          <Skeleton className="h-64 w-full" />
        ) : selected ? (
          <section aria-label={`workstream ${selected.key}`} className="min-w-0 space-y-3">
            <WorkstreamHeader workstream={selected} onOpenDocument={onOpenDocument} />
            <EntryTimeline
              key={`${selected.id}:${focusEntryId ?? ""}`}
              workstream={selected}
              initialEntryId={focusEntryId}
            />
          </section>
        ) : (
          <EmptyState
            kind="empty"
            icon={ScrollText}
            title="No open workstream"
            description="Every workstream in this project is closed; open one from the closed list to read it."
          />
        )}
      </div>
    </div>
  )
```

- [ ] **Step 6: Run the worklog tests and typecheck**

Run (from `frontend/`): `timeout 300 npx vitest run src/features/worklog && timeout 300 npm run typecheck`
Expected: PASS; typecheck reports no error.

- [ ] **Step 7: Commit**

```bash
git add frontend/src/features/worklog
git commit -m "feat(worklog): search a project's work log"
```

### Task 7: Mount the Work log in the project workspace

**Files:**
- Modify: `frontend/src/features/documents/components/project-workspace.tsx`
- Modify: `frontend/src/routes/_authenticated/projects_.$project.tsx`
- Test: `frontend/src/features/documents/__tests__/project-workspace.test.tsx`, `frontend/src/features/documents/__tests__/project-workspace-render.test.tsx`

**Interfaces:**
- Consumes: `WorkLogPanel({ project, initialWorkstream, onOpenDocument })` (Contracts, Tasks 4-5).
- Produces: `ProjectWorkspace`'s `workstream?: string` prop and the route's `workstream` search param (Contracts).

**Items:** 1

**Implementer:** dr-superpowers:impl-opus-low
**Evaluation:** files 1 - spec 1 - coupling 1 - risk 1 = 4

- [ ] **Step 1: Write the failing tests**

In `frontend/src/features/documents/__tests__/project-workspace.test.tsx`:

- replace the `vi.mock("@/features/activity/components/checkpoints-tab", …)` block with:

```tsx
vi.mock("@/features/worklog/components/work-log-panel", () => ({
  WorkLogPanel: ({
    initialWorkstream,
    onOpenDocument,
  }: {
    initialWorkstream?: string
    onOpenDocument?: (uri: string) => void
  }) => (
    <div>
      work-log-panel:{initialWorkstream ?? "none"}
      <button type="button" onClick={() => onOpenDocument?.("notes/design.md")}>
        open design
      </button>
      <button type="button" onClick={() => onOpenDocument?.("notes/missing.md")}>
        open missing
      </button>
    </div>
  ),
}))
```

- replace the body of the test `renders the progress panel` with:

```tsx
    mockDocuments({ items: [DOC] })
    renderWorkspace({ tab: "progress", workstream: "plan-a" })

    expect(await screen.findByText("work-log-panel:plan-a")).toBeInTheDocument()
    // The ledger path convention no longer appears in the board's empty state.
    expect(screen.queryByText(/planning\/progress\.md/)).toBeNull()
```

- add, in the same `describe`, after that test:

```tsx
  it("opens a document a workstream links to in the Artifacts tab", async () => {
    mockDocuments({ items: [DOC] })
    const onTabChange = vi.fn()
    renderWorkspace({ tab: "progress", onTabChange })
    await screen.findByText("work-log-panel:none")

    // The document list loads asynchronously; a click before it lands is the
    // not-filed branch, so retry the click until the list is there.
    await waitFor(() => {
      fireEvent.click(screen.getByRole("button", { name: "open design" }))
      expect(onTabChange).toHaveBeenCalledWith("artifacts")
    })
  })

  it("names a linked document that is not filed instead of switching tabs", async () => {
    mockDocuments({ items: [DOC] })
    const onTabChange = vi.fn()
    vi.mocked(toast.error).mockClear()
    renderWorkspace({ tab: "progress", onTabChange })
    await screen.findByText("work-log-panel:none")

    fireEvent.click(screen.getByRole("button", { name: "open missing" }))
    expect(onTabChange).not.toHaveBeenCalled()
    expect(vi.mocked(toast.error)).toHaveBeenCalledWith(
      "notes/missing.md is not filed in this project",
    )
  })
```

  and add `import { toast } from "darkraise-ui/components/sonner"` beside the file's other imports (after the `vi.mock` blocks).

In `frontend/src/features/documents/__tests__/project-workspace-render.test.tsx`, replace the `vi.mock("@/features/activity/components/checkpoints-tab", …)` block with:

```tsx
vi.mock("@/features/worklog/components/work-log-panel", () => ({
  WorkLogPanel: () => null,
}))
```

- [ ] **Step 2: Run them to verify they fail**

Run (from `frontend/`): `timeout 300 npx vitest run src/features/documents/__tests__/project-workspace.test.tsx`
Expected: FAIL (`work-log-panel:plan-a` absent; the Progress tab still renders `CheckpointsTab`).

- [ ] **Step 3: Implement**

In `frontend/src/features/documents/components/project-workspace.tsx`:

- replace `import { CheckpointsTab } from "@/features/activity/components/checkpoints-tab"` with `import { WorkLogPanel } from "@/features/worklog/components/work-log-panel"`, and add `import { toast } from "darkraise-ui/components/sonner"`;
- delete the `LEDGER_SUFFIX` constant and its doc comment;
- extend the props: `{ project: string; workstream?: string } & (…)`, destructured as `export function ProjectWorkspace({ project, workstream, ...tabs }`;
- after `openCitation`, add:

```tsx
  const switchTab = tabs.onTabChange
  // A workstream names its plan, spec and handoff by uri; the workspace owns
  // the selection, so opening one is a selection plus a tab switch.
  const openDocumentByUri = useCallback(
    (uri: string) => {
      const doc = items.find((d) => d.uri === uri)
      if (!doc) {
        toast.error(`${uri} is not filed in this project`)
        return
      }
      setSelectedId(doc.id)
      setFocusBlockId(null)
      setMode("read")
      switchTab?.("artifacts")
    },
    [items, switchTab],
  )
```

- in the Progress `TabsContent`, change the board's `EmptyState` description to `"This project's corpus holds no progress ledger, so the board has nothing to project. Coding clients record their progress in the work log below."`, and replace `<CheckpointsTab project={project} />` with:

```tsx
        <div>
          <RegionLabel>work log</RegionLabel>
          <WorkLogPanel
            // Keyed on the requested workstream: the panel seeds its selection
            // from it once, so a link to another workstream must remount it.
            key={workstream ?? ""}
            project={project}
            initialWorkstream={workstream}
            onOpenDocument={openDocumentByUri}
          />
        </div>
```

In `frontend/src/routes/_authenticated/projects_.$project.tsx`, give `validateSearch` an explicit optional return type and read the new param:

```tsx
  validateSearch: (
    search: Record<string, unknown>,
  ): { tab?: WorkspaceTab; workstream?: string } => ({
    tab: TAB_VALUES.includes(search.tab as WorkspaceTab)
      ? (search.tab as WorkspaceTab)
      : undefined,
    workstream:
      typeof search.workstream === "string" && search.workstream
        ? search.workstream
        : undefined,
  }),
```

then read `const { tab, workstream } = Route.useSearch()` and pass `workstream={workstream}` to `ProjectWorkspace`.

- [ ] **Step 4: Run the tests and typecheck**

Run (from `frontend/`): `timeout 300 npx vitest run src/features/documents src/routes && timeout 300 npm run typecheck`
Expected: PASS; typecheck reports no error.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/features/documents frontend/src/routes/_authenticated/projects_.\$project.tsx
git commit -m "feat(worklog): show the Work log under the board"
```

### Task 8: Activity Work log tab

**Files:**
- Create: `frontend/src/features/worklog/components/open-workstreams.tsx`
- Modify: `frontend/src/routes/_authenticated/activity.tsx`
- Modify: `frontend/src/demo/projects.ts` (the `darkmem` row), `frontend/src/components/darkmem/detail-level-toggle.tsx` (doc comment)
- Test: `frontend/src/features/worklog/__tests__/open-workstreams.test.tsx`

**Interfaces:**
- Consumes: `useProjects` and the frontend `ProjectSummary` fields (Contracts, Task 2); `useWorkstreams`, `useWorklogResume` (Task 3); `firstLine` (Task 4); the route's `workstream` search param (Task 7).
- Produces: `OpenWorkstreams` and the Activity tab value `worklog` (Contracts).

**Items:** 1

**Implementer:** dr-superpowers:impl-opus-low
**Evaluation:** files 1 - spec 1 - coupling 1 - risk 1 = 4

- [ ] **Step 1: Write the failing test**

Create `frontend/src/features/worklog/__tests__/open-workstreams.test.tsx`:

```tsx
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { render, screen } from "@testing-library/react"
import type { ReactNode } from "react"
import { beforeEach, describe, expect, it, vi } from "vitest"

vi.mock("@/lib/demo-flag", () => ({ DEMO: false }))
vi.mock("@/lib/api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/api")>()),
  apiFetch: vi.fn(),
}))
vi.mock("@tanstack/react-router", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@tanstack/react-router")>()),
  Link: ({
    children,
    params,
    search,
  }: {
    children: ReactNode
    params: { project: string }
    search: { tab: string; workstream: string }
  }) => (
    <a href={`/projects/${params.project}?tab=${search.tab}&workstream=${search.workstream}`}>
      {children}
    </a>
  ),
}))

import { apiFetch } from "@/lib/api"
import { OpenWorkstreams } from "../components/open-workstreams"

function project(name: string, open: number, kind: "project" | "personal" = "project") {
  return {
    name,
    kind,
    memory_count: 0,
    document_count: 0,
    checkpoint_count: 0,
    page_count: 0,
    last_checkpoint_at: null,
    workstream_count: open,
    open_workstream_count: open,
    last_worklog_at: null,
    last_event_day: null,
  }
}

const OPEN = {
  id: "w1",
  project: "darkmem",
  key: "plan-a",
  title: "Plan A",
  client: null,
  state: "open",
  closed_at: null,
  retain: false,
  properties: {},
  last_entry_at: "2026-09-28T10:00:00Z",
  created_at: "2026-09-28T08:00:00Z",
  updated_at: "2026-09-28T10:00:00Z",
}

function entry(seq: number, kind: string, body: string) {
  return {
    id: `e${seq}`,
    workstream_id: "w1",
    seq,
    run_key: "r",
    kind,
    body,
    properties: {},
    created_at: "2026-09-28T10:00:00Z",
  }
}

function wrapper({ children }: { children: ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>
}

beforeEach(() => {
  vi.mocked(apiFetch).mockReset()
})

describe("OpenWorkstreams", () => {
  it("lists every project's open workstreams with their latest entry", async () => {
    vi.mocked(apiFetch).mockImplementation((path: string) => {
      if (path === "/projects") {
        return Promise.resolve([
          project("darkmem", 1),
          project("quiet", 0),
          project("notes", 1, "personal"),
        ])
      }
      if (path === "/worklog/workstreams?project=darkmem&state=open&limit=50") {
        return Promise.resolve({ items: [OPEN], next_before: null })
      }
      if (path === "/worklog/resume?project=darkmem&workstream=plan-a") {
        return Promise.resolve({
          workstream: OPEN,
          checkpoint: entry(4, "checkpoint", "## Halfway\n\nmore"),
          notes: [entry(2, "note", "a note")],
          notes_truncated: false,
          ledger: [entry(5, "ledger", "Task 3: done\n")],
        })
      }
      return Promise.reject(new Error(`unrouted ${path}`))
    })
    render(<OpenWorkstreams />, { wrapper })

    const link = await screen.findByRole("link", { name: /Plan A/ })
    expect(link).toHaveAttribute("href", "/projects/darkmem?tab=progress&workstream=plan-a")
    expect(await screen.findByText("ledger: Task 3: done")).toBeInTheDocument()
    const asked = vi.mocked(apiFetch).mock.calls.map(([path]) => String(path))
    expect(asked.some((path) => path.includes("project=quiet"))).toBe(false)
    expect(asked.some((path) => path.includes("project=notes"))).toBe(false)
  })

  it("says so when no project has an open workstream", async () => {
    vi.mocked(apiFetch).mockResolvedValue([project("quiet", 0)])
    render(<OpenWorkstreams />, { wrapper })
    expect(await screen.findByText("No open workstreams")).toBeInTheDocument()
  })
})
```

- [ ] **Step 2: Run it to verify it fails**

Run (from `frontend/`): `timeout 300 npx vitest run src/features/worklog/__tests__/open-workstreams.test.tsx`
Expected: FAIL (cannot resolve `../components/open-workstreams`).

- [ ] **Step 3: Create the list**

Create `frontend/src/features/worklog/components/open-workstreams.tsx`:

```tsx
import { useMemo } from "react"
import { Link } from "@tanstack/react-router"
import { ScrollText } from "lucide-react"
import { Button } from "darkraise-ui/components/button"
import { Skeleton } from "darkraise-ui/components/skeleton"
import { EmptyState, listItemClass } from "@/components/darkmem"
import { ModuleSurface } from "@/features/activity/components/module-surface"
import {
  useProjects,
  useWorklogResume,
  useWorkstreams,
  type WorklogEntry,
  type Workstream,
} from "@/hooks/api"
import { formatWhen } from "@/lib/format"
import { firstLine } from "./entry-timeline"

/** The newest of what resume carries: the checkpoint, the notes and the
 *  ledger tail are each bounded, and the newest entry is among them. */
function latestEntry(resume: {
  checkpoint: WorklogEntry | null
  notes: WorklogEntry[]
  ledger: WorklogEntry[]
}): WorklogEntry | null {
  const candidates = [resume.checkpoint, ...resume.notes, ...resume.ledger].filter(
    (e): e is WorklogEntry => e !== null,
  )
  return candidates.reduce<WorklogEntry | null>(
    (newest, e) => (newest === null || e.seq > newest.seq ? e : newest),
    null,
  )
}

function OpenWorkstreamRow({ workstream }: { workstream: Workstream }) {
  const resume = useWorklogResume(workstream.project, workstream.key)
  const latest = resume.data ? latestEntry(resume.data) : null
  let summary = "no entry yet"
  if (latest) summary = `${latest.kind}: ${firstLine(latest.body)}`
  else if (resume.isPending) summary = "…"
  else if (resume.isError) summary = "could not read the latest entry"

  return (
    <Link
      to="/projects/$project"
      params={{ project: workstream.project }}
      search={{ tab: "progress", workstream: workstream.key }}
      className={listItemClass({
        interactive: true,
        className: "bg-card flex flex-wrap items-center gap-2.5 p-3",
      })}
    >
      <ScrollText aria-hidden className="text-primary-text h-4 w-4 shrink-0" />
      <span className="flex min-w-0 flex-1 basis-56 flex-col gap-0.5">
        <span className="text-sm font-semibold">{workstream.title ?? workstream.key}</span>
        <span className="text-muted-foreground font-mono text-xs">
          {workstream.project} · {workstream.key}
        </span>
      </span>
      <span className="text-muted-foreground min-w-0 flex-1 basis-56 truncate text-sm">
        {summary}
      </span>
      <span className="text-muted-foreground font-mono text-sm whitespace-nowrap">
        {formatWhen(workstream.last_entry_at)}
      </span>
    </Link>
  )
}

function ProjectOpenWorkstreams({ project }: { project: string }) {
  const open = useWorkstreams(project, "open")
  const items = useMemo(
    () => open.data?.pages.flatMap((page) => page.items) ?? [],
    [open.data],
  )
  if (open.isError) {
    return (
      <p className="text-destructive text-sm">
        Could not read {project}'s work log: {open.error.message}
      </p>
    )
  }
  return (
    <>
      {items.map((w) => (
        <OpenWorkstreamRow key={w.id} workstream={w} />
      ))}
      {open.hasNextPage ? (
        <Button
          variant="ghost"
          size="sm"
          disabled={open.isFetchingNextPage}
          onClick={() => void open.fetchNextPage()}
        >
          More open workstreams in {project}
        </Button>
      ) : null}
    </>
  )
}

/** Every project's open workstreams (spec §8). There is no cross-project list
 *  route, so the project catalogue names the projects worth asking. */
export function OpenWorkstreams() {
  const projects = useProjects()
  const withOpen = (projects.data ?? []).filter(
    (p) => p.kind !== "personal" && p.open_workstream_count > 0,
  )

  if (projects.isError) {
    return (
      <EmptyState
        kind="failed"
        title="Could not read the project catalogue"
        description={projects.error.message}
      />
    )
  }
  if (projects.isPending) return <Skeleton className="h-32 w-full" />
  if (withOpen.length === 0) {
    return (
      <EmptyState
        kind="empty"
        icon={ScrollText}
        title="No open workstreams"
        description="A workstream opens when a coding client first appends to it with worklog_append, and stays listed here until it is closed."
      />
    )
  }
  return (
    <ModuleSurface
      title="Open workstreams"
      state="populated"
      meta={`${withOpen.length} ${withOpen.length === 1 ? "project" : "projects"}`}
    >
      {withOpen.map((p) => (
        <ProjectOpenWorkstreams key={p.name} project={p.name} />
      ))}
    </ModuleSurface>
  )
}
```

- [ ] **Step 4: Use it on the Activity route**

In `frontend/src/routes/_authenticated/activity.tsx`:

- replace `import { CheckpointsTab } from "@/features/activity/components/checkpoints-tab"` with `import { OpenWorkstreams } from "@/features/worklog/components/open-workstreams"`;
- in the `lucide-react` import, replace `Bookmark` with `ScrollText`;
- in `TAB_VALUES`, replace `"checkpoints"` with `"worklog"`;
- replace the checkpoints trigger and content with:

```tsx
            <TabsTrigger className="flex-1 gap-2" value="worklog">
              <ScrollText aria-hidden className="size-[var(--icon-size)]" />
              Work log
            </TabsTrigger>
```

```tsx
        <TabsContent value="worklog" className="pt-4">
          <OpenWorkstreams />
        </TabsContent>
```

In `frontend/src/demo/projects.ts`, give the `darkmem` row the shape of the demo work log Task 18 adds (one open and one closed workstream): `workstream_count: 2`, `open_workstream_count: 1`, `last_worklog_at: "2026-07-24T14:10:00Z"`.

In `frontend/src/components/darkmem/detail-level-toggle.tsx`, change `day tab (raw id lists), checkpoints, dream digest` in its doc comment to `day tab (raw id lists), dream digest`: the Work log tab has no detail-level variant.

- [ ] **Step 5: Run the tests and typecheck**

Run (from `frontend/`): `timeout 300 npx vitest run src/features/worklog src/features/activity src/demo && timeout 300 npm run typecheck`
Expected: PASS; typecheck reports no error.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/features/worklog frontend/src/routes/_authenticated/activity.tsx frontend/src/demo/projects.ts frontend/src/components/darkmem/detail-level-toggle.tsx
git commit -m "feat(worklog): list open workstreams on Activity"
```

### Task 9: Remove the checkpoint UI

**Files:**
- Delete: `frontend/src/features/activity/components/checkpoints-tab.tsx`, `frontend/src/features/activity/use-checkpoint-runs.ts`, `frontend/src/hooks/api/use-checkpoints-api.ts`, `frontend/src/features/activity/__tests__/checkpoints.test.tsx`
- Modify: `frontend/src/hooks/api/index.ts`, `frontend/src/features/activity/__tests__/activity-components.test.tsx`
- Modify: `frontend/src/demo/types.ts`, `frontend/src/demo/data/activity-curated.ts`, `frontend/src/demo/store.ts`, `frontend/src/demo/hooks.ts`, `frontend/src/demo/__tests__/activity.test.ts`
- Modify: `frontend/tests/demo-makes-no-api-calls.spec.ts` (`DEMO_ROUTES`)

**Interfaces:**
- Consumes: the Activity route and the workspace no longer import `CheckpointsTab` (Tasks 7, 8).
- Produces: nothing.

**Items:** 1

**Implementer:** dr-superpowers:impl-sonnet-high
**Evaluation:** files 1 - spec 0 - coupling 1 - risk 1 = 3

- [ ] **Step 1: Confirm nothing outside the checkpoint slice imports it**

Run (from `frontend/`): `rg -n "checkpoints-tab|use-checkpoint-runs|use-checkpoints-api|useLatestCheckpoint|useDemoSessionRuns|CURATED_SESSION_RUNS" src --glob '!src/features/activity/components/checkpoints-tab.tsx' --glob '!src/features/activity/use-checkpoint-runs.ts' --glob '!src/hooks/api/use-checkpoints-api.ts' --glob '!src/features/activity/__tests__/checkpoints.test.tsx'`
Expected: hits only in `hooks/api/index.ts`, `activity-components.test.tsx`, `demo/store.ts`, `demo/hooks.ts`, `demo/data/activity-curated.ts` and `demo/__tests__/activity.test.ts`. Any other hit means Task 7 or 8 is incomplete: stop and report it.

- [ ] **Step 2: Delete the slice**

```bash
git rm frontend/src/features/activity/components/checkpoints-tab.tsx frontend/src/features/activity/use-checkpoint-runs.ts frontend/src/hooks/api/use-checkpoints-api.ts frontend/src/features/activity/__tests__/checkpoints.test.tsx
```

Then:

- `frontend/src/hooks/api/index.ts`: delete `export * from "./use-checkpoints-api"`.
- `frontend/src/features/activity/__tests__/activity-components.test.tsx`: delete `import { CheckpointsTab } from "../components/checkpoints-tab"` and the whole `describe("CheckpointsTab is operational — no verification badge", …)` block.
- `frontend/src/demo/types.ts`: delete the `DemoCheckpointEvent` and `DemoSessionRun` interfaces, and the `sessionRuns: DemoSessionRun[]` member of the store state interface.
- `frontend/src/demo/data/activity-curated.ts`: delete `DemoSessionRun` from the type import, and delete everything from the `// S33 — session checkpoints.` banner comment through the end of the `CURATED_SESSION_RUNS` array (the `RESUME_BLOCK` constant included).
- `frontend/src/demo/store.ts`: delete `CURATED_SESSION_RUNS,` from the import and the `sessionRuns: CURATED_SESSION_RUNS,` line.
- `frontend/src/demo/hooks.ts`: delete the `useDemoSessionRuns` line.
- `frontend/src/demo/__tests__/activity.test.ts`: delete `CURATED_SESSION_RUNS,` from the import and the whole `describe("session checkpoints are operational, not knowledge", …)` block.

In `frontend/tests/demo-makes-no-api-calls.spec.ts`, add two entries to `DEMO_ROUTES` after `"/activity?tab=triage"`:

```ts
  "/activity?tab=worklog",
  "/projects/darkmem?tab=progress",
```

- [ ] **Step 3: Verify nothing names the slice**

Run (from `frontend/`): `rg -n "CheckpointsTab|use-checkpoint|useCheckpoint|useLatestCheckpoint|sessionRuns|SessionRun|DemoCheckpointEvent|RESUME_BLOCK" src tests`
Expected: no output.

- [ ] **Step 4: Run the frontend suite, typecheck and build**

Run (from `frontend/`): `timeout 900 npm test && timeout 300 npm run typecheck && timeout 600 npm run build`
Expected: every vitest file passes; typecheck and build succeed. If a run exits 143, it was the host's OOM killer (CLAUDE.md), not a failure: check `free -h` and rerun.

- [ ] **Step 5: Commit**

```bash
git add -A frontend/src frontend/tests/demo-makes-no-api-calls.spec.ts
git commit -m "refactor(activity): remove the checkpoint views"
```

### Task 10: Line diff renderer

**Files:**
- Modify: `frontend/package.json`, `frontend/package-lock.json` (add `diff`)
- Create: `frontend/src/features/documents/components/line-diff.tsx`
- Test: `frontend/src/features/documents/__tests__/line-diff.test.tsx`

**Interfaces:**
- Consumes: nothing from other tasks.
- Produces: `LineDiff({ before, after })` (Contracts).

**Items:** 1

**Implementer:** dr-superpowers:impl-sonnet-medium
**Evaluation:** files 1 - spec 0 - coupling 1 - risk 0 = 2

- [ ] **Step 1: Add the dependency**

Run (from `frontend/`): `timeout 300 npm install diff@^9.0.0`
Expected: `package.json` lists `"diff": "^9.0.0"` under `dependencies`; the package ships its own types (`libesm/index.d.ts`), so no `@types/diff`.

- [ ] **Step 2: Write the failing test**

Create `frontend/src/features/documents/__tests__/line-diff.test.tsx`:

```tsx
import { render, screen } from "@testing-library/react"
import { describe, expect, it } from "vitest"
import { LineDiff } from "../components/line-diff"

function lines(container: HTMLElement, change: string): string[] {
  return [...container.querySelectorAll(`[data-change="${change}"]`)].map(
    (row) => row.querySelector("[data-line]")?.textContent ?? "",
  )
}

describe("LineDiff", () => {
  it("marks removed, added and unchanged lines", () => {
    const { container } = render(<LineDiff before={"a\nb\nc\n"} after={"a\nB\nc\nd\n"} />)
    expect(lines(container, "removed")).toEqual(["b"])
    expect(lines(container, "added")).toEqual(["B", "d"])
    expect(lines(container, "same")).toEqual(["a", "c"])
  })

  it("keeps a blank line as a line", () => {
    const { container } = render(<LineDiff before={"a\n\nb\n"} after={"a\nb\n"} />)
    expect(lines(container, "removed")).toEqual([""])
  })

  it("says so when the two sides are identical", () => {
    render(<LineDiff before={"same\n"} after={"same\n"} />)
    expect(screen.getByText("The two revisions are identical.")).toBeInTheDocument()
  })
})
```

- [ ] **Step 3: Run it to verify it fails**

Run (from `frontend/`): `timeout 300 npx vitest run src/features/documents/__tests__/line-diff.test.tsx`
Expected: FAIL (cannot resolve `../components/line-diff`).

- [ ] **Step 4: Implement**

Create `frontend/src/features/documents/components/line-diff.tsx`:

```tsx
import { useMemo } from "react"
import { diffLines } from "diff"
import { cn } from "darkraise-ui/lib"

// darkraise-ui ships no diff component (checked 2026-09-28 against its
// dist/components). This renderer exists only for that gap; a library diff
// view retires it.

function splitLines(value: string): string[] {
  const lines = value.split("\n")
  if (lines.at(-1) === "") lines.pop()
  return lines
}

export function LineDiff({ before, after }: { before: string; after: string }) {
  const parts = useMemo(() => diffLines(before, after), [before, after])

  if (!parts.some((part) => part.added || part.removed)) {
    return (
      <p className="text-muted-foreground text-sm">The two revisions are identical.</p>
    )
  }

  return (
    <div
      role="group"
      aria-label="line diff"
      className="border-border overflow-x-auto rounded-md border py-1 font-mono text-xs leading-relaxed"
    >
      {parts.flatMap((part, partIndex) => {
        const change = part.added ? "added" : part.removed ? "removed" : "same"
        const mark = part.added ? "+" : part.removed ? "-" : " "
        return splitLines(part.value).map((line, lineIndex) => (
          <div
            key={`${partIndex}:${lineIndex}`}
            data-change={change}
            className={cn(
              "flex px-2 whitespace-pre-wrap",
              part.added && "bg-success/15 text-success-text",
              part.removed && "bg-destructive/15 text-destructive",
            )}
          >
            <span aria-hidden className="text-muted-foreground w-4 shrink-0 select-none">
              {mark}
            </span>
            <span data-line className="min-w-0 flex-1">
              {line}
            </span>
          </div>
        ))
      })}
    </div>
  )
}
```

- [ ] **Step 5: Run the test and typecheck**

Run (from `frontend/`): `timeout 300 npx vitest run src/features/documents/__tests__/line-diff.test.tsx && timeout 300 npm run typecheck`
Expected: PASS; typecheck reports no error.

- [ ] **Step 6: Commit**

```bash
git add frontend/package.json frontend/package-lock.json frontend/src/features/documents/components/line-diff.tsx frontend/src/features/documents/__tests__/line-diff.test.tsx
git commit -m "feat(documents): add a line diff renderer"
```

### Task 11: Document revision hooks

**Files:**
- Create: `frontend/src/hooks/api/use-document-revisions-api.ts`
- Modify: `frontend/src/hooks/api/index.ts`, `frontend/src/lib/query-keys.ts`
- Test: `frontend/src/hooks/api/__tests__/use-document-revisions-api.test.tsx`

**Interfaces:**
- Consumes: nothing from other tasks.
- Produces: the revision hooks and types (Contracts).

**Items:** 1

**Implementer:** dr-superpowers:impl-sonnet-high
**Evaluation:** files 1 - spec 0 - coupling 2 - risk 0 = 3

- [ ] **Step 1: Write the failing test**

Create `frontend/src/hooks/api/__tests__/use-document-revisions-api.test.tsx`:

```tsx
import { beforeEach, describe, expect, it, vi } from "vitest"
import { renderHook, waitFor } from "@testing-library/react"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import type { ReactNode } from "react"

vi.mock("@/lib/demo-flag", () => ({ DEMO: false }))
vi.mock("@/lib/api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/api")>()),
  apiFetch: vi.fn(),
}))

import { apiFetch } from "@/lib/api"
import { useDocumentRevision, useDocumentRevisions } from "../use-document-revisions-api"

function wrapper({ children }: { children: ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>
}

beforeEach(() => {
  vi.mocked(apiFetch).mockReset()
})

describe("document revision reads", () => {
  it("lists newest first and pages back on next_before", async () => {
    vi.mocked(apiFetch)
      .mockResolvedValueOnce({ document_id: "d1", items: [{ id: "r2" }], next_before: "r2" })
      .mockResolvedValueOnce({ document_id: "d1", items: [{ id: "r1" }], next_before: null })
    const { result } = renderHook(() => useDocumentRevisions("d1", true), { wrapper })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(vi.mocked(apiFetch).mock.calls[0]![0]).toBe("/documents/d1/revisions?")
    await result.current.fetchNextPage()
    await waitFor(() => expect(result.current.data?.pages).toHaveLength(2))
    expect(vi.mocked(apiFetch).mock.calls[1]![0]).toBe("/documents/d1/revisions?before=r2")
  })

  it("stays idle while the sheet is closed", () => {
    const { result } = renderHook(() => useDocumentRevisions("d1", false), { wrapper })
    expect(result.current.fetchStatus).toBe("idle")
    expect(vi.mocked(apiFetch)).not.toHaveBeenCalled()
  })

  it("reads one revision with its content, and nothing without an id", async () => {
    vi.mocked(apiFetch).mockResolvedValueOnce({ id: "r1", content: "a\n" })
    const none = renderHook(() => useDocumentRevision("d1", null), { wrapper })
    expect(none.result.current.fetchStatus).toBe("idle")
    const one = renderHook(() => useDocumentRevision("d1", "r1"), { wrapper })
    await waitFor(() => expect(one.result.current.isSuccess).toBe(true))
    expect(vi.mocked(apiFetch)).toHaveBeenCalledWith("/documents/d1/revisions/r1")
    expect(one.result.current.data?.content).toBe("a\n")
  })
})
```

- [ ] **Step 2: Run it to verify it fails**

Run (from `frontend/`): `timeout 300 npx vitest run src/hooks/api/__tests__/use-document-revisions-api.test.tsx`
Expected: FAIL (cannot resolve `../use-document-revisions-api`).

- [ ] **Step 3: Implement**

Create `frontend/src/hooks/api/use-document-revisions-api.ts`:

```ts
import { useInfiniteQuery, useQuery } from "@tanstack/react-query"
import { apiFetch } from "@/lib/api"
import { DEMO } from "@/lib/demo-flag"

export interface DocumentRevisionItem {
  id: string
  content_hash: string
  actor: string | null
  api_key_id: string | null
  created_at: string
}

export interface DocumentRevisionPage {
  document_id: string
  items: DocumentRevisionItem[]
  next_before: string | null
}

export interface DocumentRevision extends DocumentRevisionItem {
  document_id: string
  content: string
}

/** A document's revisions newest first, without content, paged back on the
 *  server's `before` cursor. `enabled` is the sheet's open state. */
export function useDocumentRevisions(documentId: string, enabled: boolean) {
  return useInfiniteQuery({
    queryKey: ["documentRevisions", documentId],
    initialPageParam: null as string | null,
    queryFn: ({ pageParam }) => {
      const qs = new URLSearchParams()
      if (pageParam) qs.set("before", pageParam)
      return apiFetch<DocumentRevisionPage>(`/documents/${documentId}/revisions?${qs}`)
    },
    getNextPageParam: (last: DocumentRevisionPage) => last.next_before,
    enabled: enabled && !DEMO,
  })
}

/** One revision with the content it filed. A revision never changes, so it is
 *  never refetched once read. */
export function useDocumentRevision(documentId: string, revisionId: string | null) {
  return useQuery<DocumentRevision>({
    queryKey: ["documentRevision", documentId, revisionId],
    queryFn: () => apiFetch<DocumentRevision>(`/documents/${documentId}/revisions/${revisionId}`),
    enabled: !DEMO && revisionId !== null,
    staleTime: Infinity,
  })
}
```

In `frontend/src/hooks/api/index.ts`, add `export * from "./use-document-revisions-api"`.

In `frontend/src/lib/query-keys.ts`, add to `QUERY_KEY_SCOPE` next to `documentBlocks`:

```ts
  documentRevisions: {
    kind: "global",
    reason:
      "Addressed by document id and carrying no project param, the same shape as documentBlocks",
  },
  documentRevision: {
    kind: "global",
    reason:
      "Addressed by document id and revision id; the same shape as documentRevisions",
  },
```

- [ ] **Step 4: Run the tests and typecheck**

Run (from `frontend/`): `timeout 300 npx vitest run src/hooks/api/__tests__/use-document-revisions-api.test.tsx src/lib/__tests__/query-keys.test.ts && timeout 300 npm run typecheck`
Expected: PASS; typecheck reports no error.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/hooks/api/use-document-revisions-api.ts frontend/src/hooks/api/index.ts frontend/src/lib/query-keys.ts frontend/src/hooks/api/__tests__/use-document-revisions-api.test.tsx
git commit -m "feat(documents): add the revision read hooks"
```

### Task 12: Revisions sheet on the document view

**Files:**
- Create: `frontend/src/features/documents/components/revisions-sheet.tsx`
- Modify: `frontend/src/features/documents/components/document-actions.tsx` (`DocumentActions`)
- Test: `frontend/src/features/documents/__tests__/revisions-sheet.test.tsx`

**Interfaces:**
- Consumes: `LineDiff` (Task 10); `useDocumentRevisions`, `useDocumentRevision` (Task 11).
- Produces: `RevisionsSheet({ documentId, open, onOpenChange })` (Contracts).

**Items:** 1

**Implementer:** dr-superpowers:impl-opus-low
**Evaluation:** files 1 - spec 1 - coupling 1 - risk 1 = 4

- [ ] **Step 1: Write the failing test**

Create `frontend/src/features/documents/__tests__/revisions-sheet.test.tsx`:

```tsx
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { render, screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import type { ReactNode } from "react"
import { beforeEach, describe, expect, it, vi } from "vitest"

vi.mock("@/lib/demo-flag", () => ({ DEMO: false }))
vi.mock("@/lib/api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/api")>()),
  apiFetch: vi.fn(),
}))
vi.mock("darkraise-ui/components/sonner", () => ({
  toast: { error: vi.fn(), success: vi.fn() },
  Toaster: () => null,
}))

import { apiFetch } from "@/lib/api"
import { DocumentActions } from "../components/document-actions"
import { RevisionsSheet } from "../components/revisions-sheet"

function item(id: string, hash: string, created_at: string) {
  return { id, content_hash: hash, actor: "claude-code", api_key_id: null, created_at }
}

const CONTENT: Record<string, string> = {
  r3: "a\nB\nc\n",
  r2: "a\nb\nc\n",
  r1: "a\nc\n",
}

function routeApi() {
  vi.mocked(apiFetch).mockImplementation((path: string) => {
    if (path.startsWith("/documents/d1/revisions?")) {
      return Promise.resolve({
        document_id: "d1",
        items: [
          item("r3", "3333333333", "2026-09-28T10:00:00Z"),
          item("r2", "2222222222", "2026-09-27T10:00:00Z"),
          item("r1", "1111111111", "2026-09-26T10:00:00Z"),
        ],
        next_before: null,
      })
    }
    const one = path.match(/^\/documents\/d1\/revisions\/(r\d)$/)
    if (one) return Promise.resolve({ id: one[1], document_id: "d1", content: CONTENT[one[1]!] })
    return Promise.reject(new Error(`unrouted ${path}`))
  })
}

function wrapper({ children }: { children: ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>
}

function changed(change: string): string[] {
  return [...document.querySelectorAll(`[data-change="${change}"] [data-line]`)].map(
    (line) => line.textContent ?? "",
  )
}

beforeEach(() => {
  vi.mocked(apiFetch).mockReset()
  routeApi()
})

describe("RevisionsSheet", () => {
  it("compares the two newest revisions by default", async () => {
    render(<RevisionsSheet documentId="d1" open onOpenChange={vi.fn()} />, { wrapper })
    await screen.findByRole("group", { name: "line diff" })
    expect(changed("removed")).toEqual(["b"])
    expect(changed("added")).toEqual(["B"])
  })

  it("compares any two the reader picks", async () => {
    const user = userEvent.setup()
    render(<RevisionsSheet documentId="d1" open onOpenChange={vi.fn()} />, { wrapper })
    await screen.findByRole("group", { name: "line diff" })

    await user.click(screen.getByRole("button", { name: "Compare from 11111111" }))
    await waitFor(() => expect(changed("added")).toEqual(["B"]))
    expect(changed("removed")).toEqual([])
    expect(screen.getByRole("button", { name: "Compare from 11111111" })).toHaveAttribute(
      "aria-pressed",
      "true",
    )
  })

  it("reads nothing while closed", () => {
    render(<RevisionsSheet documentId="d1" open={false} onOpenChange={vi.fn()} />, { wrapper })
    expect(vi.mocked(apiFetch)).not.toHaveBeenCalled()
  })
})

describe("DocumentActions", () => {
  it("opens the revisions sheet", async () => {
    const user = userEvent.setup()
    render(
      <DocumentActions
        document={{
          id: "d1",
          title: "Design",
          uri: "notes/design.md",
          source_type: "md",
          project: "darkmem",
          block_count: 3,
        } as never}
        mode="read"
        onModeChange={vi.fn()}
        onDeleted={vi.fn()}
      />,
      { wrapper },
    )
    await user.click(screen.getByRole("button", { name: "Revisions" }))
    expect(await screen.findByRole("group", { name: "line diff" })).toBeInTheDocument()
  })
})
```

- [ ] **Step 2: Run it to verify it fails**

Run (from `frontend/`): `timeout 300 npx vitest run src/features/documents/__tests__/revisions-sheet.test.tsx`
Expected: FAIL (cannot resolve `../components/revisions-sheet`).

- [ ] **Step 3: Create the sheet**

Create `frontend/src/features/documents/components/revisions-sheet.tsx`:

```tsx
import { useMemo, useState } from "react"
import { Button } from "darkraise-ui/components/button"
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from "darkraise-ui/components/sheet"
import { Skeleton } from "darkraise-ui/components/skeleton"
import { EmptyState } from "@/components/darkmem"
import { useDocumentRevision, useDocumentRevisions } from "@/hooks/api"
import { DEMO } from "@/lib/demo-flag"
import { formatWhen } from "@/lib/format"
import { LineDiff } from "./line-diff"

/** A document's revisions (spec §8) and a line diff between any two of them.
 *  Defaults to the two newest, so opening the sheet answers "what changed
 *  last". The server serves contents, not patches; the diff is computed here. */
export function RevisionsSheet({
  documentId,
  open,
  onOpenChange,
}: {
  documentId: string
  open: boolean
  onOpenChange: (open: boolean) => void
}) {
  const revisions = useDocumentRevisions(documentId, open)
  const items = useMemo(
    () => revisions.data?.pages.flatMap((page) => page.items) ?? [],
    [revisions.data],
  )
  const [picked, setPicked] = useState<{ from: string | null; to: string | null }>({
    from: null,
    to: null,
  })
  const to = picked.to ?? items[0]?.id ?? null
  const from = picked.from ?? items[1]?.id ?? null
  const after = useDocumentRevision(documentId, open ? to : null)
  const before = useDocumentRevision(documentId, open ? from : null)

  let comparison
  if (DEMO) {
    // The revision reads are disabled in demo mode and would stay pending.
    comparison = (
      <EmptyState
        kind="empty"
        title="No revisions in the demo"
        description="The demo files no documents, so it has no revisions to compare."
      />
    )
  } else if (revisions.isError) {
    comparison = (
      <EmptyState
        kind="failed"
        title="Could not read the revisions"
        description={revisions.error.message}
      />
    )
  } else if (revisions.isPending) {
    comparison = <Skeleton className="h-32 w-full" />
  } else if (items.length === 0) {
    comparison = (
      <EmptyState
        kind="empty"
        title="No revisions"
        description="A revision is written when a filing changes this document's content; block edits and byte sources write none."
      />
    )
  } else if (items.length === 1) {
    comparison = (
      <p className="text-muted-foreground text-sm">
        Only one revision exists, so there is nothing to compare yet.
      </p>
    )
  } else if (before.isError || after.isError) {
    comparison = (
      <EmptyState
        kind="failed"
        title="Could not read a revision"
        description={(before.error ?? after.error)?.message}
      />
    )
  } else if (before.data && after.data) {
    comparison = <LineDiff before={before.data.content} after={after.data.content} />
  } else {
    comparison = <Skeleton className="h-32 w-full" />
  }

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent side="right" className="w-full overflow-y-auto sm:max-w-2xl">
        <SheetHeader>
          <SheetTitle>Revisions</SheetTitle>
          <SheetDescription>
            Each filing that changed this document's content, newest first. Pick
            the two to compare.
          </SheetDescription>
        </SheetHeader>
        <div className="space-y-4 p-4">
          {items.length > 0 ? (
            <ul className="space-y-1">
              {items.map((revision) => {
                const short = revision.content_hash.slice(0, 8)
                return (
                  <li key={revision.id} className="flex flex-wrap items-center gap-2 text-sm">
                    <span className="min-w-0 flex-1">
                      {formatWhen(revision.created_at)}
                      <span className="text-muted-foreground font-mono text-xs">
                        {" "}
                        · {revision.actor ?? "unknown"} · {short}
                      </span>
                    </span>
                    <Button
                      size="sm"
                      variant={revision.id === from ? "default" : "outline"}
                      aria-pressed={revision.id === from}
                      aria-label={`Compare from ${short}`}
                      onClick={() => setPicked({ from: revision.id, to })}
                    >
                      From
                    </Button>
                    <Button
                      size="sm"
                      variant={revision.id === to ? "default" : "outline"}
                      aria-pressed={revision.id === to}
                      aria-label={`Compare to ${short}`}
                      onClick={() => setPicked({ from, to: revision.id })}
                    >
                      To
                    </Button>
                  </li>
                )
              })}
            </ul>
          ) : null}
          {revisions.hasNextPage ? (
            <Button
              variant="outline"
              size="sm"
              disabled={revisions.isFetchingNextPage}
              onClick={() => void revisions.fetchNextPage()}
            >
              Older revisions
            </Button>
          ) : null}
          {comparison}
        </div>
      </SheetContent>
    </Sheet>
  )
}
```

- [ ] **Step 4: Add the toolbar button**

In `frontend/src/features/documents/components/document-actions.tsx`:

- add `History` to the `lucide-react` import and `import { RevisionsSheet } from "./revisions-sheet"`;
- in `DocumentActions`, add `const [revisionsOpen, setRevisionsOpen] = useState(false)` after `confirmOpen`;
- add, between the Summarize and Delete buttons:

```tsx
      <IconButton
        icon={History}
        label="Revisions"
        variant="ghost"
        onClick={() => setRevisionsOpen(true)}
      />
```

- add, after the closing `</AlertDialog>`:

```tsx
      <RevisionsSheet
        documentId={document.id}
        open={revisionsOpen}
        onOpenChange={setRevisionsOpen}
      />
```

- update the component's doc comment's first line to "The document-level controls: edit, summarize, revisions, delete."

- [ ] **Step 5: Run the document tests and typecheck**

Run (from `frontend/`): `timeout 300 npx vitest run src/features/documents && timeout 300 npm run typecheck`
Expected: PASS; typecheck reports no error.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/features/documents
git commit -m "feat(documents): compare revisions in a sheet"
```

### Task 13: Move run-key resolution into the work log

**Files:**
- Modify: `backend/app/services/worklog.py` (imports, `__all__`, new `UndeclaredRun` and `resolve_run_key`)
- Modify: `backend/app/api/routes/worklog.py` (`append_entries`), `backend/app/api/mcp/server.py` (`worklog_append`)
- Test: `backend/tests/test_worklog_service.py`

**Interfaces:**
- Consumes: nothing from other tasks.
- Produces: `worklog.resolve_run_key` and `worklog.UndeclaredRun` (Contracts). The two work-log doors stop importing `app.services.checkpoints`; the checkpoint doors keep their own copy until Task 14 deletes them.

**Items:** 1

**Implementer:** dr-superpowers:impl-opus-medium
**Evaluation:** files 1 - spec 0 - coupling 2 - risk 2 = 5

- [ ] **Step 1: Write the failing tests**

Append to `backend/tests/test_worklog_service.py` (the file already imports `pytest` and `worklog`):

```python
@pytest.mark.parametrize("declared", [None, "", "   ", ":::", "::", "\u200b", " : "])
def test_an_undeclared_or_unsanitisable_run_is_refused(declared):
    """Two runs sharing one key would each resume the other's work, so a run
    that declares nothing, or nothing that survives sanitising, is refused
    rather than merged into capture's `unknown:` bucket."""
    with pytest.raises(worklog.UndeclaredRun):
        worklog.resolve_run_key(declared, source="codex", project="p")


def test_a_declared_run_resolves_through_the_capture_derivation():
    # "boot:1" sanitises to "boot1": the refusal keys on the sanitised result
    # being empty, not on the raw string losing a character.
    assert worklog.resolve_run_key("boot:1", source="codex", project="p") == "codex:boot1"


def test_the_refusal_names_what_to_send():
    with pytest.raises(worklog.UndeclaredRun, match="`run_key`"):
        worklog.resolve_run_key(None, source="codex", project="p")
```

- [ ] **Step 2: Run them to verify they fail**

Run (from `backend/`): `TEST_DATABASE_URL=postgresql+asyncpg://darkmem:darkmem@localhost:5433/darkmem_test_2 timeout 600 .venv/bin/python -m pytest -q tests/test_worklog_service.py -k "undeclared or declared_run or refusal_names"`
Expected: FAIL with `AttributeError: module 'app.services.worklog' has no attribute 'UndeclaredRun'`.

- [ ] **Step 3: Implement**

In `backend/app/services/worklog.py`:

- add `from app.api.mcp.client_identity import UNKNOWN_ORIGIN_PREFIX, resolve_origin_key` to the `app.*` imports (its import closure is the module alone, so the work-log wall's closures do not grow);
- add `"UndeclaredRun",` before `"WorklogJournalWriteFailed",` and `"resolve_run_key",` after `"purge_workstream",` in `__all__`;
- add, after the module constants (after `MAX_QUERY_CHARS = 2_000`):

```python
class UndeclaredRun(ValueError):
    """An append arrived with no declared agent-run identity."""


def resolve_run_key(declared, *, source: str, project: str) -> str:
    """The run's key by doc 05 §2.1's derivation, or a refusal.

    The derivation is capture's own `resolve_origin_key`, so the sanitising,
    the length bound and the prefix have one owner. Its fallback is not
    inherited: capture merges an undeclared origin into one
    `unknown:<source>:<project>` bucket, which is safe for a key that counts
    corroboration and wrong for one that looks work up, because two runs
    sharing it would each resume the other's work as their own.
    """
    if not isinstance(declared, str) or not declared.strip():
        raise UndeclaredRun(
            "a work-log entry needs a declared agent-run identity: send "
            "`run_key`, or the X-Darkmem-Origin header the client mints at "
            "process boot. Undeclared runs are refused rather than merged into "
            "one bucket the way undeclared captures are: two runs sharing a key "
            "would each resume the other's work as their own."
        )
    resolved = resolve_origin_key(declared, None, source=source, project=project)
    # Unreachable while `declared` is non-empty, but asserted rather than
    # assumed: the failure it guards is silent.
    if resolved.startswith(f"{UNKNOWN_ORIGIN_PREFIX}:"):
        raise UndeclaredRun(
            f"origin resolution produced the merge-to-one bucket {resolved!r}; "
            "refusing to file work under a key every unattributed run shares"
        )
    # `_sanitize_origin` drops separators and unprintables, so ":::" or a lone
    # zero-width space reduces to the bare "<source>:", one key every such run
    # would share.
    if resolved == f"{source}:":
        raise UndeclaredRun(
            f"the declared agent-run identity {declared!r} contains nothing that "
            f"survives sanitisation, so it resolves to the bare {resolved!r}. "
            "Send an identity with at least one printable, non-separator character."
        )
    return resolved
```

In `backend/app/api/routes/worklog.py`, delete `from app.services.checkpoints import resolve_checkpoint_origin` and change the call in `append_entries` to `run_key = worklog.resolve_run_key(` (arguments unchanged; the `except ValueError` still maps the refusal to 422).

In `backend/app/api/mcp/server.py`'s `worklog_append`, delete `from app.services.checkpoints import resolve_checkpoint_origin` and change `resolved = resolve_checkpoint_origin(` to `resolved = worklog.resolve_run_key(`.

- [ ] **Step 4: Run the work-log suites**

Run (from `backend/`): `TEST_DATABASE_URL=postgresql+asyncpg://darkmem:darkmem@localhost:5433/darkmem_test_2 timeout 900 .venv/bin/python -m pytest -q tests/test_worklog_service.py tests/test_worklog_rest.py tests/test_worklog_mcp.py tests/test_worklog_wall.py tests/test_checkpoints.py`
Expected: all PASS (`test_an_undeclared_run_is_refused` on both doors still holds; the checkpoint suite is untouched).

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/worklog.py backend/app/api/routes/worklog.py backend/app/api/mcp/server.py backend/tests/test_worklog_service.py
git commit -m "refactor(worklog): own the run-key resolution"
```

### Task 14: Remove the checkpoint doors

**Files:**
- Delete: `backend/app/api/routes/checkpoints.py`, `backend/tests/test_checkpoints.py`
- Modify: `backend/app/main.py`, `backend/app/api/mcp/server.py`, `backend/app/api/mcp/scopes.py`, `backend/app/services/content_surfaces.py`, `backend/app/services/prompt.py`
- Modify (guards): `backend/tests/test_door_parity.py`, `backend/tests/test_api/test_rest_conformance.py`, `backend/tests/test_mcp.py`
- Modify (docs): `docs/two-door-parity.md`, `CLAUDE.md`, `docs/runbook-exposed-deployment.md`, `docs/wiki/usage-guide.md`

**Interfaces:**
- Consumes: the work-log doors no longer import `app.services.checkpoints` (Task 13); no SPA code calls the checkpoint routes (Task 9).
- Produces: MCP tools 48 → 46 (capture 14, read 29, admin 3); the two `checkpoint.*` parity rows are gone.

**Items:** 1

**Implementer:** dr-superpowers:impl-opus-medium
**Evaluation:** files 1 - spec 0 - coupling 2 - risk 2 = 5

- [ ] **Step 1: Confirm the doors have no caller left**

Run (repo root): `rg -n -w "checkpoint_routes|checkpoint_save|checkpoint_latest" backend/app frontend/src sdks extension --glob '!**/node_modules/**'` and `rg -n "/checkpoints" frontend/src sdks extension --glob '!**/node_modules/**'`
Expected: the first lists hits only under `backend/app` (`main.py`, `api/routes/checkpoints.py`, `api/mcp/server.py`, `api/mcp/scopes.py`, `services/content_surfaces.py`, `services/prompt.py`); the second prints nothing. `-w` matters: `checkpoint_saved` is an event type that stays until Task 17 and is not a caller. A hit in `frontend/src`, `sdks` or `extension` means a caller survives: stop and report it.

- [ ] **Step 2: Remove the doors**

```bash
git rm backend/app/api/routes/checkpoints.py backend/tests/test_checkpoints.py
```

- `backend/app/main.py`: delete `checkpoints as checkpoint_routes, ` from the `from app.api.routes import …` line and the line `app.include_router(checkpoint_routes.router)`.
- `backend/app/api/mcp/server.py`: delete everything from the banner comment `# Session checkpoints (T3.16) — the second door onto app.services.checkpoints` (with the dashed rule above it) through the end of `checkpoint_latest`, stopping at the dashed rule that opens `# Work-log tools (spec 2026-09-23 §2)`. In the document-tools banner, change "for the reason the checkpoint banner above states: two transports over one module, never two implementations" to "for invariant 17's reason: two transports over one module, never two implementations".
- `backend/app/api/mcp/scopes.py`: delete the `"checkpoint_save",` and `"checkpoint_latest",` entries.
- `backend/app/services/content_surfaces.py`: delete the comment beginning `# Session checkpoints (T3.16). No memory content crosses` (five lines) and the entries `"POST /api/v1/checkpoints",` and `"GET /api/v1/checkpoints/latest",` from `ROUTES_WITHOUT_MEMORY_CONTENT`; in `MCP_TOOLS_WITHOUT_MEMORY_CONTENT`, delete the comment `# T3.16, for the reason its REST twins carry above: an agent's note about its own run is not memory content.` (two lines) with `"mcp:checkpoint_save",` and `"mcp:checkpoint_latest",`, and change the next comment to `# The work-log tools: a client's note about its own work is not memory content.`
- `backend/app/services/prompt.py`: delete the two lines

```python
        "- **checkpoint_save** / **checkpoint_latest** — the older single-run "
        "checkpoint pair, still served; prefer the work log.\n"
```

- `backend/tests/test_door_parity.py`: delete the `Surface(name="checkpoint.save", …)` and `Surface(name="checkpoint.latest", …)` entries.
- `backend/tests/test_api/test_rest_conformance.py`: delete the comment beginning `# T3.16. 201 rather than the capture doors' 202` (three lines) and the two `/api/v1/checkpoints` entries.
- `backend/tests/test_mcp.py`: delete `"checkpoint_latest",` and `"checkpoint_save",` from `EXPECTED_TOOLS`.

- [ ] **Step 3: Regenerate the parity table and fix the prose counts**

Run (from `backend/`):

```bash
.venv/bin/python - <<'PY'
import pathlib
from tests.test_door_parity import render_markdown
doc = pathlib.Path("../docs/two-door-parity.md")
text = doc.read_text(encoding="utf-8")
begin, end = "<!-- BEGIN GENERATED PARITY TABLE -->", "<!-- END GENERATED PARITY TABLE -->"
head, rest = text.split(begin, 1)
_, tail = rest.split(end, 1)
doc.write_text(f"{head}{begin}\n{render_markdown()}\n{end}{tail}", encoding="utf-8")
PY
```

Then edit by hand:

- `docs/two-door-parity.md` headline: `**91 surfaces: 33 two-door, 58 single-door with a stated reason (51 REST-only, 7 MCP-only), 0 divergent.**` becomes `**89 surfaces: 31 two-door, 58 single-door with a stated reason (51 REST-only, 7 MCP-only), 0 divergent.**` Recount from the regenerated table before writing it (`rg -c "\| two-door \|"`, `rg -c "REST single-door"`, `rg -c "MCP single-door"`); if the counts differ from these, write the counted ones.
- `CLAUDE.md`, MCP endpoint section: `48 tools` → `46 tools`; `` `capture` (15): `` → `` `capture` (14): `` with `` `checkpoint_save`, `` removed from its list; `` `read` (30). `` → `` `read` (29). ``
- `docs/runbook-exposed-deployment.md`, the paragraph beginning "**`/mcp` is scoped far more widely**" (its sentences wrap across lines): change the counts "48 tools", "15 require `capture`", "30 require `read`", "all 15 MCP writer tools" and "the 30 readers" to 46, 14, 29, 14 and 29, remove `` `checkpoint_save`, `` from the writer list, and rewrap the paragraph.
- `docs/wiki/usage-guide.md`: replace the table row `| Session | \`checkpoint_save\`, \`checkpoint_latest\` |` with `| Work log | \`worklog_append\`, \`worklog_resume\`, \`worklog_workstreams\`, \`worklog_entries\`, \`worklog_search\`, \`worklog_update\`, \`worklog_purge\` |`, and replace the paragraph beginning `**Checkpoint long sessions.**` with: `**Keep working data in the work log.** \`worklog_append\` files a checkpoint, ledger text or a note under a workstream; \`worklog_resume\` picks the work back up in the next session.`

- [ ] **Step 4: Run the guards leg**

Run (from `backend/`):

```bash
TEST_DATABASE_URL=postgresql+asyncpg://darkmem:darkmem@localhost:5433/darkmem_test_2 timeout 900 \
  .venv/bin/python -m pytest -q tests/test_content_surface_scoping.py tests/test_door_parity.py \
    tests/test_prompt_agent_instructions.py tests/test_api/test_rest_conformance.py \
    tests/test_sdk_generator.py tests/test_spa_edge.py tests/test_events.py \
    tests/test_mcp_auth.py tests/test_inert_objects.py tests/test_api/test_tags.py \
    tests/test_block_pipeline.py tests/test_block_retrieval.py tests/test_auto_research.py \
    tests/test_event_taxonomy_map.py tests/test_mcp.py tests/test_mcp_reindex.py \
    tests/test_worklog_mcp.py tests/test_worklog_rest.py
```

Expected: all PASS. Then run `rg -n -w "checkpoint_save|checkpoint_latest" backend/app backend/tests CLAUDE.md docs/two-door-parity.md docs/runbook-exposed-deployment.md docs/wiki` and `rg -n "/api/v1/checkpoints" backend/app backend/tests CLAUDE.md docs/two-door-parity.md docs/runbook-exposed-deployment.md docs/wiki` from the repo root; expected: no output from either.

- [ ] **Step 5: Commit**

```bash
git add -A backend/app backend/tests CLAUDE.md docs/two-door-parity.md docs/runbook-exposed-deployment.md docs/wiki/usage-guide.md
git commit -m "refactor(mcp): remove the checkpoint tools and routes

checkpoint_save, checkpoint_latest, POST /api/v1/checkpoints and GET
/api/v1/checkpoints/latest are gone; the work log (worklog_append,
worklog_resume) replaces them."
```

### Task 15: Projects endpoint drops its checkpoint fields

**Files:**
- Modify: `backend/app/api/routes/projects.py`
- Test: `backend/tests/test_projects_endpoint.py`, `backend/tests/test_projects_route.py` (docstring)
- Modify: `frontend/src/hooks/api/use-projects-api.ts`, `frontend/src/demo/projects.ts`
- Test (fixtures): every frontend fixture carrying `checkpoint_count` or `last_checkpoint_at`

**Interfaces:**
- Consumes: the frontend reads the work-log fields instead (Tasks 2, 8).
- Produces: `ProjectSummary` without `checkpoint_count` and `last_checkpoint_at` on both sides; the endpoint no longer reads `session_checkpoints`, which Task 16 drops.

**Items:** 1

**Implementer:** dr-superpowers:impl-opus-low
**Evaluation:** files 1 - spec 0 - coupling 2 - risk 1 = 4

- [ ] **Step 1: Update the tests to the new shape**

In `backend/tests/test_projects_endpoint.py`:

- delete `from app.models.checkpoint import SessionCheckpoint` and the whole test `test_a_checkpoint_only_project_is_visible`;
- in `test_counts_every_status_not_only_active`'s dict, delete the `"checkpoint_count": 0,` and `"last_checkpoint_at": None,` lines;
- in the module docstring, change "union documents and checkpoints" to "union documents, workstreams and pages", and "a checkpoint or a document -- `test_checkpoints.py` commits rows that outlive it" to "a workstream or a document -- suites that commit rows outlive their own test".

In `backend/tests/test_projects_route.py`'s docstring, change "memories, documents and checkpoints" to "memories, documents, workstreams and pages".

- [ ] **Step 2: Run them to verify they fail**

Run (from `backend/`): `TEST_DATABASE_URL=postgresql+asyncpg://darkmem:darkmem@localhost:5433/darkmem_test_2 timeout 600 .venv/bin/python -m pytest -q tests/test_projects_endpoint.py`
Expected: FAIL in `test_counts_every_status_not_only_active` (the row still carries the two checkpoint keys).

- [ ] **Step 3: Implement the backend**

In `backend/app/api/routes/projects.py`:

- delete `checkpoint_count: int` and `last_checkpoint_at: datetime | None` from `ProjectSummary`;
- in `_UNION_SQL`, delete the `UNION SELECT project FROM session_checkpoints` arm, the `c AS (…)` CTE, the `COALESCE(c.n, 0) AS checkpoint_count,` and `c.latest AS last_checkpoint_at,` select lines, the `LEFT JOIN c …` line, and the `+ COALESCE(c.n, 0)` term of the `ORDER BY`;
- in both docstrings, remove "a checkpoint, " / "checkpoints, " from the lists Task 1 wrote.

Run the Step 2 command again. Expected: PASS.

- [ ] **Step 4: Implement the frontend**

In `frontend/src/hooks/api/use-projects-api.ts`, delete `checkpoint_count: number` and `last_checkpoint_at: string | null` from `ProjectSummary`. Then find every remaining fixture:

Run (from `frontend/`): `rg -ln "checkpoint_count|last_checkpoint_at" src`

and delete the `checkpoint_count` and `last_checkpoint_at` properties from every object in every file it lists (`src/demo/projects.ts` and the test fixtures Tasks 2 and 8 touched). Where a fixture writes several properties on one line, delete only those two.

Run (from `frontend/`): `rg -n "checkpoint_count|last_checkpoint_at" src`
Expected: no output.

- [ ] **Step 5: Run the tests and typecheck**

Run (from `frontend/`): `timeout 600 npm test && timeout 300 npm run typecheck`
Expected: PASS; typecheck reports no error.

- [ ] **Step 6: Commit**

```bash
git add backend/app/api/routes/projects.py backend/tests/test_projects_endpoint.py backend/tests/test_projects_route.py frontend/src
git commit -m "refactor(projects): drop the checkpoint counts"
```

### Task 16: Drop the checkpoint store

**Files:**
- Delete: `backend/app/models/checkpoint.py`, `backend/app/schemas/checkpoint.py`, `backend/app/services/checkpoints.py`, `backend/app/services/resume_inject.py`, `backend/tests/test_resume_inject.py`, `backend/tests/test_checkpoint_isolation.py`
- Modify: `backend/app/models/__init__.py`, `backend/migrations/versions/0001_baseline.py`
- Modify (guards): `backend/tests/test_read_only_role.py`

**Interfaces:**
- Consumes: nothing reads `session_checkpoints` or imports the checkpoint modules outside this slice (Tasks 13–15).
- Produces: a baseline without `session_checkpoints`.

**Items:** 1

**Implementer:** dr-superpowers:impl-opus-high
**Evaluation:** files 1 - spec 0 - coupling 2 - risk 3 = 6

- [ ] **Step 1: Confirm nothing outside the slice reaches it**

Run (repo root): `rg -n "session_checkpoints|SessionCheckpoint|app\.services\.checkpoints|services import checkpoints|resume_inject|schemas\.checkpoint|models\.checkpoint|from \.checkpoint" backend/app backend/tests backend/scripts --glob '!backend/scripts/benchlib/promotion/**'`
Expected: hits only in the six files to delete, `backend/app/models/__init__.py` and `backend/tests/test_read_only_role.py` (the baseline is checked in Step 3). Any other hit is a reader this plan missed: stop and report it.

- [ ] **Step 2: Delete the slice**

```bash
git rm backend/app/models/checkpoint.py backend/app/schemas/checkpoint.py backend/app/services/checkpoints.py backend/app/services/resume_inject.py backend/tests/test_resume_inject.py backend/tests/test_checkpoint_isolation.py
```

- `backend/app/models/__init__.py`: delete `from .checkpoint import SessionCheckpoint` and `"SessionCheckpoint",` from `__all__`.
- `backend/tests/test_read_only_role.py`: delete `"session_checkpoints",` from `READABLE` and `"services/checkpoints.py",` from `PURE_READ_MODULES`.

- [ ] **Step 3: Regenerate the baseline without the table**

In `backend/migrations/versions/0001_baseline.py`:

- delete the block from the comment `# session_checkpoints — operational, NOT vault knowledge (spec` through the `op.execute(` that creates `ix_session_checkpoints_latest` (the comment, the `CREATE TABLE session_checkpoints` statement, the index comment and the index statement), leaving the blank line before the `# workstreams + worklog_entries — the work-log lane` banner;
- delete `"session_checkpoints",` from the table list in `downgrade()`.

Run (repo root): `rg -n "session_checkpoints|checkpoint" backend/migrations/versions/0001_baseline.py`
Expected: only the `worklog_entries` kind CHECK (`kind IN ('checkpoint', 'ledger', 'note')`).

- [ ] **Step 4: Prove the schema and the suites**

The backend conftest drops the test database's schema and runs `alembic upgrade head`, so any run proves the regenerated baseline applies. Run (from `backend/`):

```bash
TEST_DATABASE_URL=postgresql+asyncpg://darkmem:darkmem@localhost:5433/darkmem_test_2 timeout 1800 \
  .venv/bin/python -m pytest -q tests/test_read_only_role.py tests/test_inert_objects.py \
    tests/test_worklog_wall.py tests/test_worklog_service.py tests/test_projects_endpoint.py \
    tests/test_inject_fill.py tests/test_inject_watch.py tests/test_block_retrieval.py \
    tests/test_events.py tests/test_event_taxonomy_map.py tests/test_mcp.py
```

Expected: all PASS. Then confirm the table is gone from a fresh migrate:

```bash
docker exec darkmem-postgres-1 psql -U darkmem -d darkmem_test_2 -Atc "SELECT to_regclass('public.session_checkpoints') IS NULL"
```

Expected: `t`.

- [ ] **Step 5: Commit**

```bash
git add -A backend/app backend/tests backend/migrations/versions/0001_baseline.py
git commit -m "refactor(schema): drop session_checkpoints

The table, its model, service and resume path are gone. A deployed
database needs the table dropped and its schema_baseline_sha row
deleted before the new image boots."
```

### Task 17: Retire the checkpoint vocabulary and prose

**Files:**
- Modify: `backend/app/services/events.py` (`EVENT_TYPES`, `OBJECT_TYPES`), `frontend/src/features/activity/event-taxonomy.ts` (`EVENT_TYPES_WITHOUT_TAB`)
- Modify: `backend/app/services/inject_fill.py` (`fill`, `_pass`)
- Modify (prose): `CLAUDE.md`, `docs/agent-conventions.md`, `backend/app/api/mcp/client_identity.py` (`declared_origin` docstring), `backend/tests/test_document_routes.py` (`_ctx` docstring)

**Interfaces:**
- Consumes: no emitter of `checkpoint_saved` or `resumed` remains (Task 16).
- Produces: nothing.

**Items:** 1

**Implementer:** dr-superpowers:impl-opus-low
**Evaluation:** files 1 - spec 1 - coupling 1 - risk 1 = 4

- [ ] **Step 1: Retire the vocabulary**

- `backend/app/services/events.py`: in `EVENT_TYPES`, delete `"checkpoint_saved",` and the comment beginning `# T3.17, landed 2026-08-11 with its emitter.` together with `"resumed",`; in `OBJECT_TYPES`, delete `"checkpoint",`. Leave the older comment that cites "the rule T3.16 settled for `resumed`": it states a rule that still holds.
- `frontend/src/features/activity/event-taxonomy.ts`: in `EVENT_TYPES_WITHOUT_TAB`, delete the comment beginning `// A session checkpoint is operational, not vault knowledge (T3.16)` with `"checkpoint_saved",`, and the comment beginning `// T3.17's resume.` with `"resumed",`; in the work-log comment that follows (it wraps across two lines), change "Operational state like the checkpoint pair above: a client's own work" to "Operational state: a client's own work" and rewrap it. Keep the `const EVENT_TYPES_WITHOUT_TAB = new Set<string>([` line byte-identical; `backend/tests/test_event_taxonomy_map.py` parses it.

- [ ] **Step 2: Drop `fill`'s dead `lead` parameter**

In `backend/app/services/inject_fill.py`:

- change `fill`'s signature to `def fill(result: ComposedResult, *, token_budget: int) -> FillResult:`, delete the docstring paragraph that begins "``lead`` is T3.17's resume digest", and drop `, lead=lead` from both `_pass(...)` calls;
- change `_pass`'s signature to `rows: list[ComposedRow], budget: int, *, verified_only: bool` and delete the whole `if lead is not None:` block (its comment included).

Run (repo root): `rg -n "lead" backend/app/services/inject_fill.py`
Expected: no output.

- [ ] **Step 3: Correct the prose**

- `CLAUDE.md`, Domain model, the `origin_key` bullet: replace "It **is** served by `GET /api/v1/knowledge/facts/{id}` (`FactSourceGroup.origin_key`), `GET /events` (`checkpoint_saved` payloads), and `CheckpointResponse` on both verbs of both doors, where `session_checkpoints.origin_key` is a lookup key rather than a corroboration key." with "It **is** served by `GET /api/v1/knowledge/facts/{id}` (`FactSourceGroup.origin_key`)."
- `CLAUDE.md`, Work log: replace "The run key resolves as checkpoints resolve it; an undeclared run is refused." with "The run key resolves through `worklog.resolve_run_key` (capture's derivation, doc 05 §2.1); an undeclared run is refused, never merged into an `unknown:` bucket."
- `backend/app/api/mcp/client_identity.py`, `declared_origin`'s docstring: change "but the checkpoint doors resolve a declared identity" to "but the work-log doors resolve a declared identity".
- `backend/tests/test_document_routes.py`, `_ctx`'s docstring: change "Copied from `tests/test_checkpoints.py`: an in-process call" to "An in-process call".
- `docs/agent-conventions.md`: in the opening paragraph change "checkpoint its progress" to "record its progress in the work log"; in §1 change "documents and checkpoints" to "documents and the work log"; replace all of §3 (from `## 3. Checkpoint discipline` up to, not including, `## 4. Ledger shape`) with:

```markdown
## 3. Work-log discipline

Working data — checkpoints, ledger text, notes to the next session — goes to
the work log, never to `memory_add` (`backend/app/services/worklog.py`, module
docstring). One workstream per piece of work, keyed by a name the client
chooses; dr-superpowers uses the plan or design slug.

**Mint one run identity per process at boot, and declare it on every
`worklog_append`**, as `run_key` or the `X-Darkmem-Origin` header. An
undeclared run is *refused*, never merged into a shared bucket: two runs
sharing one key would each resume the other's work as their own
(`worklog.resolve_run_key`).

Bounds, enforced at the door and again by CHECK constraints (the constants at
the top of `worklog.py`):

| Bound | Value |
|---|---|
| entry `body` | 1–65,536 characters, stored verbatim |
| entries per append | 1–100, in one transaction |
| `properties` | ≤ 12,288 bytes of encoded JSON at the door |

**Resume at session start, checkpoint at every stop.** `worklog_resume`
answers the latest checkpoint, the newest 50 notes and the last 20 ledger
entries. Every entry stays readable through `worklog_entries` and
`worklog_search` until the workstream is purged or, closed and not retained,
ages past the `worklog_cleanup` window (90 days by default).

After a checkpoint, file the durable facts the run established with
`memory_add`, one per memory: the work log keeps how the work went, memories
keep what is now true.

```

- [ ] **Step 4: Run the affected suites**

Run (from `backend/`):

```bash
TEST_DATABASE_URL=postgresql+asyncpg://darkmem:darkmem@localhost:5433/darkmem_test_2 timeout 900 \
  .venv/bin/python -m pytest -q tests/test_events.py tests/test_event_taxonomy_map.py \
    tests/test_inject_fill.py tests/test_inject_watch.py tests/test_document_routes.py
```

and (from `frontend/`): `timeout 300 npx vitest run src/features/activity && timeout 300 npm run typecheck`
Expected: all PASS.

Run (repo root): `rg -n -i "checkpoint_saved|\"resumed\"|session_checkpoints|resume_inject|CheckpointResponse" backend/app frontend/src CLAUDE.md docs/agent-conventions.md docs/two-door-parity.md`
Expected: no output.

- [ ] **Step 5: Commit**

```bash
git add backend/app backend/tests/test_document_routes.py frontend/src/features/activity/event-taxonomy.ts CLAUDE.md docs/agent-conventions.md
git commit -m "refactor(events): retire the checkpoint vocabulary"
```

### Task 18: Work-log demo fixtures

**Files:**
- Create: `frontend/src/demo/worklog.ts`
- Modify: `frontend/src/hooks/api/use-worklog-api.ts`
- Test: `frontend/src/hooks/api/__tests__/use-worklog-api.demo.test.tsx`

**Interfaces:**
- Consumes: `use-worklog-api.ts` (Contracts, Task 3).
- Produces: `frontend/src/demo/worklog.ts` (Contracts); the work-log hooks serve it in demo mode and their writes refuse there.

**Items:** 1

**Implementer:** dr-superpowers:impl-sonnet-medium
**Evaluation:** files 1 - spec 0 - coupling 1 - risk 0 = 2

- [ ] **Step 1: Write the failing test**

Create `frontend/src/hooks/api/__tests__/use-worklog-api.demo.test.tsx`:

```tsx
import { describe, expect, it, vi } from "vitest"
import { renderHook } from "@testing-library/react"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import type { ReactNode } from "react"

vi.mock("@/lib/demo-flag", () => ({ DEMO: true }))
vi.mock("@/lib/api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/api")>()),
  apiFetch: vi.fn(),
}))

import { apiFetch } from "@/lib/api"
import { DEMO_WORKSTREAMS } from "@/demo/worklog"
import {
  useWorklogEntries,
  useWorklogResume,
  useWorklogSearch,
  useWorkstreamUpdate,
  useWorkstreams,
} from "../use-worklog-api"

function wrapper({ children }: { children: ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>
}

describe("the work log in demo mode", () => {
  it("serves fixtures and makes no request", async () => {
    const open = renderHook(() => useWorkstreams("darkmem", "open"), { wrapper })
    const openItems = open.result.current.data?.pages[0]?.items ?? []
    expect(openItems.length).toBeGreaterThan(0)
    expect(openItems.every((w) => w.state === "open")).toBe(true)

    const id = openItems[0]!.id
    const entries = renderHook(() => useWorklogEntries(id, null, true), { wrapper })
    expect(entries.result.current.data?.pages[0]?.items.length).toBeGreaterThan(0)

    const resume = renderHook(() => useWorklogResume("darkmem", openItems[0]!.key), { wrapper })
    expect(resume.result.current.data?.checkpoint?.kind).toBe("checkpoint")

    const search = renderHook(() => useWorklogSearch(), { wrapper })
    const answer = await search.result.current.mutateAsync({ project: "darkmem", query: "retention" })
    expect(answer.semantic_ran).toBe(false)
    expect(answer.items.length).toBeGreaterThan(0)

    expect(open.result.current.fetchStatus).toBe("idle")
    expect(entries.result.current.fetchStatus).toBe("idle")
    expect(vi.mocked(apiFetch)).not.toHaveBeenCalled()
  })

  it("refuses a write without calling the API", async () => {
    const update = renderHook(() => useWorkstreamUpdate(), { wrapper })
    await expect(
      update.result.current.mutateAsync({ id: DEMO_WORKSTREAMS[0]!.id, state: "closed" }),
    ).rejects.toThrow(/read-only/)
    expect(vi.mocked(apiFetch)).not.toHaveBeenCalled()
  })
})
```

- [ ] **Step 2: Run it to verify it fails**

Run (from `frontend/`): `timeout 300 npx vitest run src/hooks/api/__tests__/use-worklog-api.demo.test.tsx`
Expected: FAIL (cannot resolve `@/demo/worklog`).

- [ ] **Step 3: Create the fixtures**

Create `frontend/src/demo/worklog.ts`:

```ts
import type { WorklogEntry, Workstream } from "@/hooks/api"

const OPEN_ID = "0f0e1d2c-0000-4000-8000-000000000001"
const CLOSED_ID = "0f0e1d2c-0000-4000-8000-000000000002"

/** Two workstreams in the demo's `darkmem` project: one open plan with a
 *  checkpoint, ledger chunks and a note, and one closed plan. */
export const DEMO_WORKSTREAMS: Workstream[] = [
  {
    id: OPEN_ID,
    project: "darkmem",
    key: "work-log-increment-6",
    title: "Work-log increment 6: UI and checkpoint removal",
    client: "dr-superpowers",
    state: "open",
    closed_at: null,
    retain: false,
    properties: {
      plan_uri: "superpowers/plans/2026-09-28-work-log-increment-6.md",
      spec_uri: "superpowers/specs/2026-09-23-work-log-lane-design.md",
    },
    last_entry_at: "2026-07-24T14:10:00Z",
    created_at: "2026-07-24T09:00:00Z",
    updated_at: "2026-07-24T14:10:00Z",
  },
  {
    id: CLOSED_ID,
    project: "darkmem",
    key: "work-log-increment-5-retention",
    title: "Work-log increment 5: retention",
    client: "dr-superpowers",
    state: "closed",
    closed_at: "2026-07-23T18:00:00Z",
    retain: false,
    properties: {},
    last_entry_at: "2026-07-23T17:40:00Z",
    created_at: "2026-07-23T08:30:00Z",
    updated_at: "2026-07-23T18:00:00Z",
  },
]

function entry(
  workstream_id: string,
  seq: number,
  kind: WorklogEntry["kind"],
  body: string,
  created_at: string,
): WorklogEntry {
  return {
    // Unique across both workstreams: their ids differ only in the last digit.
    id: `${workstream_id.slice(0, 24)}${workstream_id.slice(-1)}${String(seq).padStart(11, "0")}`,
    workstream_id,
    seq,
    run_key: "claude-code:demo-run",
    kind,
    body,
    properties: {},
    created_at,
  }
}

export const DEMO_WORKLOG_ENTRIES: Record<string, WorklogEntry[]> = {
  [OPEN_ID]: [
    entry(OPEN_ID, 1, "ledger", "Task 1: projects endpoint reports work-log activity — done\n", "2026-07-24T10:05:00Z"),
    entry(OPEN_ID, 2, "note", "The Progress tab keeps its project board; the Work log replaces the checkpoint runs.", "2026-07-24T10:20:00Z"),
    entry(OPEN_ID, 3, "ledger", "Task 2: frontend project summaries — done\nTask 3: work-log hooks — done\n", "2026-07-24T12:45:00Z"),
    entry(
      OPEN_ID,
      4,
      "checkpoint",
      "## State\n\nTasks 1-3 are merged. Task 4 (the Work log panel) is next.\n\n## Next\n\n- Mount the panel under the project board\n- Keep retention and search untouched",
      "2026-07-24T14:10:00Z",
    ),
  ],
  [CLOSED_ID]: [
    entry(CLOSED_ID, 1, "ledger", "Task 1: retention sweep — done\n", "2026-07-23T11:00:00Z"),
    entry(
      CLOSED_ID,
      2,
      "checkpoint",
      "## State\n\nRetention is merged and deployed; the plan is complete.",
      "2026-07-23T17:40:00Z",
    ),
  ],
}
```

- [ ] **Step 4: Serve them from the hooks**

In `frontend/src/hooks/api/use-worklog-api.ts`:

- add `type InfiniteData,` to the `@tanstack/react-query` import and `import { DEMO_WORKLOG_ENTRIES, DEMO_WORKSTREAMS } from "@/demo/worklog"`;
- after `const ENTRY_PAGE = 200`, add:

```ts
const DEMO_REFUSAL = "The demo is read-only: its work log cannot be changed."

function demoWorkstreams(project: string, state: WorkstreamState): WorkstreamPage {
  return {
    items: DEMO_WORKSTREAMS.filter((w) => w.project === project && w.state === state),
    next_before: null,
  }
}

function demoEntries(workstreamId: string | null, kind: WorklogKind | null): WorklogEntryPage {
  const all = workstreamId ? (DEMO_WORKLOG_ENTRIES[workstreamId] ?? []) : []
  return { items: kind ? all.filter((e) => e.kind === kind) : all, next_after: null }
}

function demoResume(project: string, key: string): WorklogResume | null {
  const workstream = DEMO_WORKSTREAMS.find((w) => w.project === project && w.key === key)
  if (!workstream) return null
  const entries = DEMO_WORKLOG_ENTRIES[workstream.id] ?? []
  const checkpoints = entries.filter((e) => e.kind === "checkpoint")
  return {
    workstream,
    checkpoint: checkpoints.at(-1) ?? null,
    notes: entries.filter((e) => e.kind === "note"),
    notes_truncated: false,
    ledger: entries.filter((e) => e.kind === "ledger").slice(-20),
  }
}

function demoSearch(params: WorklogSearchParams): WorklogSearchResponse {
  const needle = params.query.toLowerCase()
  const byId = new Map(DEMO_WORKSTREAMS.map((w) => [w.id, w]))
  const hits = Object.values(DEMO_WORKLOG_ENTRIES)
    .flat()
    .filter((e) => {
      const w = byId.get(e.workstream_id)
      return (
        w?.project === params.project &&
        (!params.workstream || w.key === params.workstream) &&
        (!params.kind || e.kind === params.kind) &&
        e.body.toLowerCase().includes(needle)
      )
    })
  return {
    items: hits.map((e, rank) => ({
      entry: e,
      workstream: byId.get(e.workstream_id)!.key,
      rrf_score: 1 / (60 + rank + 1),
      arms: ["keyword"],
    })),
    semantic_ran: false,
  }
}
```

- in `useWorkstreams`, after `enabled: !DEMO,` add:

```ts
    initialData: DEMO
      ? ({
          pages: [demoWorkstreams(project, state)],
          pageParams: [null],
        } as InfiniteData<WorkstreamPage, string | null>)
      : undefined,
```

- in `useWorklogEntries`, after the `refetchInterval` line add:

```ts
    initialData: DEMO
      ? ({
          pages: [demoEntries(workstreamId, kind)],
          pageParams: [null],
        } as InfiniteData<WorklogEntryPage, number | null>)
      : undefined,
```

- in `useWorklogResume`, after `enabled: !DEMO && enabled,` add `initialData: DEMO ? demoResume(project, key) : undefined,`;
- make the three mutations answer in demo mode without the API: `useWorklogSearch`'s `mutationFn` becomes `(params) => DEMO ? Promise.resolve(demoSearch(params)) : apiFetch<WorklogSearchResponse>("/worklog/search", { method: "POST", body: JSON.stringify(params) })`, and `useWorkstreamUpdate`'s and `useWorkstreamPurge`'s become `DEMO ? Promise.reject(new Error(DEMO_REFUSAL)) : <their current apiFetch call>`.

- [ ] **Step 5: Run the work-log tests and typecheck**

Run (from `frontend/`): `timeout 300 npx vitest run src/hooks/api/__tests__ src/features/worklog && timeout 300 npm run typecheck`
Expected: PASS; typecheck reports no error.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/demo/worklog.ts frontend/src/hooks/api/use-worklog-api.ts frontend/src/hooks/api/__tests__/use-worklog-api.demo.test.tsx
git commit -m "feat(demo): add work-log fixtures"
```
