# Watchable Progress Implementation Plan (Increment 1, with Increment 0 as prerequisite)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

> **Implementer assignments:** each task names its implementer agent in an
> `**Implementer:**` line. When executing with
> superpowers:subagent-driven-development, REQUIRED SUB-SKILL:
> dcc-superpower-companions:dispatching-tiered-implementers. Under
> superpowers:executing-plans these lines are inert; ignore them.

> **Status: LANDED 2026-09-02.** Task 1 and Task 2 executed and deployed on
> this host (`0af60430` feat, `fcf08190` changelog). Gate green: 6,468 backend,
> 1,324 frontend, both SDK suites, 1,055 benchlib, F1 bench. Two corrections
> made against the plan as written, both recorded in the commit: the test
> sketch's `LATEST` fixture does not exist (the file has `CHECKPOINT` and a
> `route()` helper — review finding m-7), and the filter option cannot be
> selected with `findByText` because each run card also renders its project
> name, so the tests use `findByRole("option")`. Task 2 Step 4's verification
> grep is also wrong twice over: the SPA lives at `/app/web/assets`, not
> `/app/static/assets`, and `LIVE_POLL_MS` is minified away — grep the m2 copy
> string instead, which survives minification.

**Goal:** The owner opens the Activity → Checkpoints tab in a browser and watches a running agent session's notes update live, scoped to one project. This is the spec's increment 1 ("smallest visible win"), plus the increment-0 reachability procedure it is moot without.

**Architecture:** No backend change. The Checkpoints tab already groups runs from the `checkpoint_saved`/`resumed` events journal and fetches the latest digest per run; this plan adds a project filter (the `/events` read already takes a `project` SQL predicate) and a poll interval (TanStack Query `refetchInterval`, which the events hook already plumbs and the checkpoint hook gains). The "checkpoint per step" agent convention is doc-only and is carried by the conventions doc in `docs/superpowers/plans/2026-08-31-docs-corpus-import.md` (increment 5), not here.

**Spec:** `docs/superpowers/specs/2026-08-31-project-artifact-store-design.md` §3, §6 (increments 0 and 1).
**Review:** the 2026-08-31 adversarial review cleared increment 1 *conditional on stating the m2 limit* (below). Where review and spec disagree, the review wins.

## The m2 limit — what this increment delivers, stated first

**Checkpoint step content has no history read, and this plan does not pretend otherwise.**

- Checkpoint rows are append-only (`backend/app/services/checkpoints.py:176-203`), but the only reads anywhere are `POST /api/v1/checkpoints` and `GET /api/v1/checkpoints/latest` (`backend/app/api/routes/checkpoints.py:31,69`; MCP twins `checkpoint_save`/`checkpoint_latest`, `backend/app/api/mcp/server.py:503,560`). No verb serves a run's past summaries.
- The `checkpoint_saved` event payload **deliberately excludes the summary** — write-time minimization, stated at the writer (`backend/app/services/checkpoints.py:217-222`; payload is `{"origin_key", "next_steps"}` only). The journal outlives deletion by ruling (T2.59), so free-form step prose must not ride it.

So what increment 1 delivers is: the **latest** summary and next-steps, polling live, plus a timestamped **timeline of when saves and resumes happened** — with no step content on the timeline entries. A viewer who joins late sees when the run checkpointed, and only the newest note's text. Reading a run's past summaries would be a new read verb (`GET /api/v1/checkpoints?origin_key=&project=` list, plus an MCP twin under the two-door rule) — **explicit backend work this plan deliberately does not scope**, because the spec's increment 1 is "no backend change" and the durable record is the ledger document, not the checkpoint stream. If the owner asks to read past step notes from the browser, that is a spec amendment, not a stretch of this plan.

Task 1 states this limit in the tab's own descriptive copy, so the surface says what it is.

## Prerequisite — Increment 0: reachability (owner procedure, not a code task)

> **Owner ruling, 2026-09-02: the agent-side client config is NOT repointed, and step 2 below is withdrawn.** The Claude Code MCP configuration is not to be pointed at this development instance. Where a task needs to exercise an MCP verb, it calls the endpoint **directly with a script** against `http://127.0.0.1:8000/mcp/` — no client-config edit, and nothing about any other instance's configuration is touched. The rest of this section stands: a key still has to exist for a scripted call to authenticate, because the bearer requirement has no bypass.
>
> This changes what "reachability" means for the increments below. Nothing in increments 1-8 is blocked by the client config; what they need is that the endpoint answers an authenticated call, which a script establishes just as well.

**Endpoint shape, measured on the running instance 2026-09-02 — the trailing slash is load-bearing:**

| Request | Answer |
|---|---|
| `POST /mcp` (no trailing slash) | `405` |
| `POST /mcp/` unkeyed | `401` |
| `POST /mcp/` with an invalid key | `401` |

A caller that drops the slash gets `405 Method Not Allowed` and will read it as a broken endpoint rather than a missing character. Write `/mcp/` in every script. (CLAUDE.md's "mounted at `/mcp`" describes the mount point, not the path a client posts to.)

Current state (verified 2026-09-02): the auth guard is live and behaves as doc 18 §5 describes — unkeyed and mis-keyed calls both answer `401`, so no MCP verb is exercisable until a key exists.

1. **Mint an API key** on the local instance (SPA: Settings → API keys; or REST):
   ```bash
   # POST /api/v1/api-keys with a logged-in session; scopes are per-tool groups.
   # capture = the 8 writers incl. checkpoint_save and document_put; read = the 25 readers.
   curl -s -X POST http://127.0.0.1:8000/api/v1/api-keys \
     -H "Content-Type: application/json" -b "$COOKIE_JAR" \
     -d '{"name": "agent-mcp", "scopes": ["capture", "read"]}'
   ```
   The `token` field of the response (`ApiKeyCreated`, `backend/app/schemas/api_keys.py:38-41`) is the only copy that will ever exist — record it in `.claude/local-credentials.md` (gitignored), never in a tracked file. Do not grant `admin` unless the agent should be able to trigger reindexes (`admin` reaches exactly one tool, `code_reindex`).
2. ~~**Repoint the client config**~~ — **withdrawn by the owner's 2026-09-02 ruling above.** Do not edit `/root/.claude.json`, and do not add, remove or repoint an `mcpServers` entry for this or any other instance. If a future task needs an agent session to reach these tools, that is a decision for the owner to take at that time, not a step an implementer performs.
3. **Verify with a direct scripted call**, not from an agent session:
   ```bash
   KEY=$(sed -n 's/^darkmem_api_key: *//p' .claude/local-credentials.md)
   curl -s -X POST http://127.0.0.1:8000/mcp/ \
     -H "Authorization: Bearer $KEY" -H 'Content-Type: application/json' \
     -H 'Accept: application/json, text/event-stream' \
     -d '{"jsonrpc":"2.0","id":1,"method":"tools/list"}'
   ```
   Expect the tool catalogue. `401` means the key is wrong or absent; `405` means the trailing slash was dropped. `MCP_ALLOWED_HOSTS` is empty on this instance, which is localhost-only and therefore correct for a `127.0.0.1` caller — a scripted local call never meets the Host guard, so no allowlist change is needed or wanted.
4. **No migration, by ruling.** Repointing carries nothing across from wherever the config pointed before. Per `CLAUDE.md`'s "Greenfield until the freeze", no data migration is owed and none is in scope here — this procedure moves a client config and mints a credential, nothing else.

## Global Constraints

- **No backend change in this plan.** The `/events` route already takes `project` (`backend/app/api/routes/events.py:35`), `useEvents` already accepts `refetchInterval` (`frontend/src/hooks/api/use-events-api.ts:50-61`). If a step appears to need a backend edit, stop — the plan is wrong, not the constraint.
- **Frontend:** from `frontend/`: `npm run typecheck` (= `tsc -b`; plain `tsc` misses project refs), `npm test` (vitest), `npm run build`. `npm run lint` is advisory.
- **Merge gate:** `./scripts/gate.sh` from the repo root before the final commit. Do not run `--full` casually — an earlyoom daemon on this host kills Chromium; a red Playwright leg that passes standalone on a rested machine is a kill, not a regression. Never invoke Playwright bare; go through `backend/scripts/e2e/run_playwright_e2e.py`.
- **UI components come from darkraise-ui first.** `select` exists (`frontend/node_modules/darkraise-ui/dist/components/select.*`). Do not hand-roll a dropdown.
- **Do not use `GET /api/v1/projects` as the filter source.** The route derives from `memories` only (`backend/app/api/routes/projects.py:28-49`, docstring: "derived, never a registry"); a project holding only checkpoints or documents is invisible to it (review finding M2). A checkpoint-only project would be invisible in its own filter — the exact surface this plan builds.
- **Demo mode must make no API calls** (session memory): every new query rides `enabled: !DEMO`, which the existing hooks already do — keep it that way.
- **Commits:** `<type>(<scope>): <subject>`, ≤50 chars, imperative. A `feat` on master cuts a release, so the final task writes the CHANGELOG section.
- **Comments:** only where the WHY is non-obvious.

## File Structure

```
frontend/src/hooks/api/use-checkpoints-api.ts        # modify: refetchInterval option
frontend/src/features/activity/use-checkpoint-runs.ts # modify: project param + poll
frontend/src/features/activity/components/checkpoints-tab.tsx # modify: filter UI + copy
frontend/src/features/activity/__tests__/checkpoints.test.tsx # extend
CHANGELOG.md                                          # Task 2
```

---

### Task 1: Project filter and live polling on the Checkpoints tab

**Files:**
- Modify: `frontend/src/hooks/api/use-checkpoints-api.ts:31-38` (`useLatestCheckpoint` options)
- Modify: `frontend/src/features/activity/use-checkpoint-runs.ts` (project param, poll constant)
- Modify: `frontend/src/features/activity/components/checkpoints-tab.tsx` (filter UI, m2 copy)
- Modify: `frontend/src/features/activity/__tests__/checkpoints.test.tsx`

**Interfaces:**
- Consumes: `GET /events?object_type=checkpoint&project=…` (server-side project predicate, `backend/app/services/events.py` `list_events`); `GET /checkpoints/latest`.
- Produces: `useCheckpointRuns(project: string | null)` — the only signature change; `CheckpointsTab` stays prop-less.

**Implementer:** dcc-superpower-companions:impl-opus-low
**Evaluation:** files 2 - spec 1 - coupling 0 - risk 1 = 4
**Approach:** inline - skip 3: the review's M2 finding rules out `/api/v1/projects` as the filter source; options derive from the loaded runs instead.

- [x] **Step 1: Write the failing tests**

Extend `frontend/src/features/activity/__tests__/checkpoints.test.tsx` (the existing mock journal already carries two projects once you change one fixture's `project` — set the `cc-run-other` event's `project` to `"other-proj"`):

```tsx
it("filters runs to one project through the server-side events predicate", async () => {
  // First (unfiltered) load shows both runs and both projects as options.
  vi.mocked(apiFetch).mockImplementation(async (path: string) => {
    if (path.startsWith("/events")) {
      const filtered = path.includes("project=darkmem")
        ? { items: JOURNAL.items.filter((e) => e.project === "darkmem"), total: 2 }
        : JOURNAL
      return filtered
    }
    return LATEST
  })
  render(<CheckpointsTab />, { wrapper })
  await screen.findByText("cc-run-8f3a2c")
  expect(screen.getByText("cc-run-other")).toBeInTheDocument()

  // Select "darkmem" in the project filter; the other project's run disappears
  // and the refetch carried the project param (server-side, not client slicing).
  await userEvent.click(screen.getByLabelText(/project/i))
  await userEvent.click(await screen.findByRole("option", { name: "darkmem" }))
  await waitFor(() =>
    expect(vi.mocked(apiFetch)).toHaveBeenCalledWith(
      expect.stringContaining("project=darkmem"),
    ),
  )
  await waitFor(() =>
    expect(screen.queryByText("cc-run-other")).not.toBeInTheDocument(),
  )
})

it("polls the journal and the latest digest on the live interval", async () => {
  // The tab is a watch surface: both queries carry refetchInterval. Assert the
  // journal query refetches after the interval elapses under fake timers.
  vi.useFakeTimers()
  try {
    render(<CheckpointsTab />, { wrapper })
    await vi.waitFor(() => expect(vi.mocked(apiFetch)).toHaveBeenCalled())
    const callsBefore = vi.mocked(apiFetch).mock.calls.length
    await vi.advanceTimersByTimeAsync(LIVE_POLL_MS + 100)
    expect(vi.mocked(apiFetch).mock.calls.length).toBeGreaterThan(callsBefore)
  } finally {
    vi.useRealTimers()
  }
})

it("states that history rows carry no step content", () => {
  render(<CheckpointsTab />, { wrapper })
  expect(
    screen.getByText(/only the latest note's text is readable/i),
  ).toBeInTheDocument()
})
```

Adjust selector details to the actual `select` component's rendered roles (read `frontend/node_modules/darkraise-ui/dist/components/select.d.ts` — the props carry their own doc comments). If fake timers fight TanStack Query's scheduling in this vitest setup, an acceptable fallback for the poll test is asserting the hook wiring instead: render a probe component that calls `useCheckpointRuns(null)` and assert `useEvents` received `refetchInterval: LIVE_POLL_MS` via a spy on the hooks module. Do not delete the poll assertion entirely — the interval is the increment.

- [x] **Step 2: Run tests to verify they fail**

`cd frontend && npm test -- checkpoints` — expected: FAIL (no filter control, no `LIVE_POLL_MS` export, no limit copy).

- [x] **Step 3: `useLatestCheckpoint` gains `refetchInterval`**

In `frontend/src/hooks/api/use-checkpoints-api.ts:31-38`, widen the options parameter and pass it through:

```ts
export function useLatestCheckpoint(
  params: { originKey: string | null; project: string },
  options?: { enabled?: boolean; refetchInterval?: number },
) {
  const { originKey, project } = params
  return useQuery<CheckpointResponse | null>({
    queryKey: ["checkpoint-latest", originKey, project],
    enabled: (options?.enabled ?? true) && Boolean(originKey),
    refetchInterval: options?.refetchInterval,
    ...
```

(`useEvents` already has the same option at `use-events-api.ts:50-61`; this makes the pair symmetric.)

- [x] **Step 4: `use-checkpoint-runs.ts` — project param and poll**

```ts
/** The tab is a live watch: both queries refetch on this interval. TanStack's
 *  default `refetchIntervalInBackground: false` pauses it while the window is
 *  unfocused, which is wanted — an idle tab must not poll forever. */
export const LIVE_POLL_MS = 15_000

export function useCheckpointRuns(project: string | null): { ... } {
  const demoRuns = useDemoSessionRuns()
  const query = useEvents(
    {
      object_type: CHECKPOINT_OBJECT_TYPE,
      limit: EVENT_LIMIT,
      ...(project ? { project } : {}),
    },
    { enabled: !DEMO, refetchInterval: LIVE_POLL_MS },
  )
  ...
}
```

and in `useCheckpointDigest`, pass `{ enabled: !DEMO, refetchInterval: LIVE_POLL_MS }` to `useLatestCheckpoint`. The `queryKey: ["events", params]` already includes `project`, so filtered and unfiltered pages never share a cache entry.

- [x] **Step 5: The filter UI and the m2 copy in `checkpoints-tab.tsx`**

- State: `const [projectFilter, setProjectFilter] = useState<string | null>(null)`; pass it to `useCheckpointRuns(projectFilter)`.
- Options: accumulate every project ever seen this mount, so selecting one does not collapse the option list to itself (the filtered page only contains the filtered project):

```tsx
const seenProjects = useRef(new Set<string>())
for (const run of runs) seenProjects.current.add(run.project)
const projectOptions = [...seenProjects.current].sort()
```

- Render a darkraise-ui `select` in the `ModuleSurface` header area (or directly above the run list), labelled "project", with an "all projects" default item mapping to `null`. Do **not** fetch `/api/v1/projects` — see Global Constraints (review M2).
- The existing `selected = runs.find((r) => r.id === selectedId) ?? runs[0] ?? null` already re-anchors selection when the filter drops the selected run; leave it.
- Extend the tab's descriptive paragraph (the `<p className="text-muted-foreground max-w-4xl text-sm">` block) with one sentence stating the limit: *"The history below shows when each save and resume happened; only the latest note's text is readable — event payloads deliberately carry no step content, and no endpoint serves a run's past summaries."* This is invariant 14's honest-reporting posture applied to the surface itself, and it is the review's m2 condition made visible where the owner will read it.

- [x] **Step 6: Run the tests, typecheck, build**

```bash
cd frontend && npm test -- checkpoints && npm run typecheck && npm run build
```

All green. Also run the full `npm test` — the tab is rendered by `activity-components.test.tsx` and `activity-real-modules.test.tsx`, which must not break on the new control.

---

### Task 2: Gate, changelog, deploy

**Files:**
- Modify: `CHANGELOG.md`

**Interfaces:**
- Consumes: Task 1's landed diff.
- Produces: the running instance the owner reviews.

**Implementer:** dcc-superpower-companions:impl-sonnet-medium
**Evaluation:** files 0 - spec 0 - coupling 0 - risk 2 = 2

- [x] **Step 1: Merge gate**

`./scripts/gate.sh` from the repo root. Green before commit. (Plain `--full` is unreliable on this host — see Global Constraints.)

- [x] **Step 2: Changelog**

A `feat` push to master cuts a release, and a push whose derived version has no `## vN.N.N` section in `CHANGELOG.md` fails before the suite runs. Add the section for the next derived version (v1.5.0 if this is the first `feat` since v1.4.0). **Coordinate with the parser-fixes plan** (`2026-08-31-document-parser-fixes.md`): if both land in one push, one section covers both; two pushes need two sections.

- [x] **Step 3: Commit**

`feat(activity): project filter and live poll on checkpoints` (Task 1) — plus the CHANGELOG in the same or a `docs(changelog):` commit per the atomic-commit rule.

- [x] **Step 4: Redeploy this machine** (owner ruling 2026-08-21 — the change alters the running artifact)

```bash
DARKMEM_PUSH=0 ./scripts/build-push.sh   # DARKMEM_PUSH=0 is not optional
docker compose up -d
# wait for healthy, then confirm the change is in the running image, not only the tree:
docker exec darkmem-prod-darkmem-1 grep -rl "LIVE_POLL_MS" /app/static/assets/ | head -1
```

A skipped or failed build redeploys the old bits and still reports `Started` — the grep is the honest check. Never push an image from this machine; `release.yml` is the only path to a registry.

- [x] **Step 5: Watch it work**

With increment 0 done and an agent session checkpointing (declare one `origin_key` per run to every save — the correlation is client discipline, `checkpoints.py` module docstring, final paragraph), open Activity → Checkpoints, select the project, and confirm the latest digest and the history timeline update within ~15 s of a save.

## Rollback

Task 1 is additive UI: `git revert` the commit and redeploy. No data, no schema, no backend surface moved. The increment-0 config edit is reverted by restoring the old `mcpServers.darkmem` block (and the minted key can be revoked at Settings → API keys).

## Notes on scope

- **The m2 limit is the deliverable's edge, restated:** live watch = latest summary + save/resume timeline. Past step content is not readable from any surface, by design of the event payload. A history read verb is out of scope and would be a spec amendment.
- The events page is capped at `EVENT_LIMIT` 200 (`use-checkpoint-runs.ts`); the `total` is shown beside the list so a truncated page never reads as the whole history — unchanged by this plan. Server-side project filtering means a busy multi-project journal no longer starves a quiet project's runs out of the page, which is the second (unstated) benefit of filtering in SQL rather than client-side.
- Pushing checkpoint events over `/ws` is the spec's own "polish item, to-verify, not assumed" — not scoped here.
- Increments 3, 4, 6, 7, 8 and D1 are deliberately unplanned: the 2026-08-31 review requires spec amendments (3, 4, 6, D1) or a redesign (7, 8) first.
