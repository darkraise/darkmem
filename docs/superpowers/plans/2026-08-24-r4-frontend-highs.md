# R4 — Frontend Correctness Singletons

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Settings saves the backend refuses become visible instead of silent, demo mode stops 401-redirecting off its own Settings tabs, a failed article read renders as a failure rather than an empty library, the edit-repository dialog shows the repository the operator actually picked, chat stream errors reach the screen, and the graph detail panel stays usable in a narrow window.

**Architecture:** Seven independent frontend fixes. Three of them (Tasks 1–3) are ordered by a real dependency; the remaining four are parallel. The unifying defect is the same in five of the seven: **a state the UI has not established is rendered as a state it observed** — a failed read as an empty result, an unresolved write as a success, a clamped preference as a chosen one.

**Tech Stack:** React 19, TanStack Query, TanStack Form, TanStack Router, vitest + Testing Library, Playwright, sigma.js, darkraise-ui.

**Spec:** `docs/superpowers/specs/2026-08-24-review-remediation.md`

## Why the first three are ordered

- **Task 1 (F19) goes first.** It tightens the pending-timer sweep to track `setInterval`, and that can newly fail existing suites that leak one — the frontend suite has never been held to this. Budget the collateral fixes inside this plan rather than treating them as scope creep. Every later frontend task should be written against the strict sweep, not have it dropped on top afterwards.
- **Task 2 (F17) before Task 3 (F18).** F18's `panel-resize-handle.tsx` consumes the clamp/float logic F17 changes in `panel-resize.ts`.
- **Tasks 4–7 are parallel** and share no files with each other.

Two of these tasks are also the pattern that a much larger later package generalises:
Task 5 (F12) establishes how a failed read should render, which a 27-site package
extends across the tree; Task 4 (F11+F15) establishes the demo guard that a 9-site
package hoists into one authority. Landing the pattern here first is deliberate.

## Global Constraints

- **Backend tests:** from `backend/`, `.venv/bin/python -m pytest -q <path>`. Needs the dev Postgres on `127.0.0.1:5433` and database `darkmem_test`. Baseline on master today is **6179 passed, 22 skipped** — a change in that count is a signal, not noise.
- **Parallel lanes need their own database.** `darkmem_test_2` … `darkmem_test_5` exist for this. Keep `darkmem_test` for whoever runs the controller gate. conftest pins `DATABASE_URL` to `TEST_DATABASE_URL` and then runs `DROP SCHEMA public CASCADE` — never point a lane at a real database.
- **Frontend tests:** from `frontend/`, `npx vitest run <path>`. Typecheck is `npx tsc -b` (plain `tsc` misses the project refs). Baseline is **1233 passing**.
- **Merge gate:** `./scripts/gate.sh` from the repo root. `--full` adds the retrieval eval, the API e2e suite, Playwright and a port-hygiene diff. Each task below says which it needs and why.
- **Commits:** `<type>(<scope>): <subject>`, type one of `feat|fix|docs|style|refactor|test|chore|perf`, subject imperative, ≤ 50 characters, no trailing period. Atomic — never combine two concerns.
- **Comments:** default to none. Add one only where the WHY is non-obvious — a hidden constraint, a subtle invariant, a workaround for a specific bug. Never explain WHAT the code does; never reference this plan, this task, or a ticket.
- **Never** hardcode a value or special-case an input to make a test pass, and never use `--no-verify`. If a fix turns out to be infeasible or a finding turns out to be wrong, say so and stop — do not work around it.
- **This plan ships in the image as the built SPA, so it needs a redeploy** — and the confirmation step is that the *new bundle* is being served, not the previous one. `docker exec darkmem-prod-darkmem-1 ls web/assets` and check the hashed filenames moved.
- **This stage needs `--full`.** jsdom cannot assert a pointer drag, a dialog remount, or a stream error surface; Playwright is the only arm that drives a real browser. `frontend/tests/` is Playwright and is excluded from `npm test` — run it via `npm run test:e2e`, and never via a bare `npx playwright test`, which points `/api` at the production instance on :8000.
- **Merge after R2's deploy is confirmed,** so browser verification happens against an image that already carries the ops change. Development can start in parallel with R1 and R3 — frontend and backend share no files here.
- **Before building any UI, check whether `darkraise-ui` already ships the component** (`ls frontend/node_modules/darkraise-ui/dist/components/`). A local component written against a library gap must record which gap.
- **Prerequisite:** the working tree must be committed first. `panel-resize.ts`, `panel-resize-handle.tsx` and `pending-timers.ts` are **untracked** today — Tasks 1–3 edit files that do not exist on master.

---

### Task 1: Track setInterval in the frontend pending-timer sweep

**Effort:** ~30 minutes.

**Files:**
- Modify: `frontend/src/test/pending-timers.ts:19-25`
- Modify: `frontend/src/test/pending-timers.ts:27-87`
- Test: `frontend/src/test/__tests__/pending-timers.test.ts`

**Interfaces:**
- Consumes: nothing from another task in this plan.
- Produces: no new exported symbol — this task changes behaviour inside an existing function.

- [ ] **Step 1: Write the failing test**

INSERT the four cases below into the existing describe block in
frontend/src/test/__tests__/pending-timers.test.ts, immediately BEFORE the
existing `it("cancels everything still armed", () => {` case (i.e. after the
existing `it("still runs the callback it wrapped, with its arguments", ...)`
case and its closing `})`). The placement matters: the existing final case
calls clearPendingTimers(), so a case appended after it would start from an
already-swept set. No imports change — pendingTimerCount, clearPendingTimers
and vi are already imported at the top of the file.

  it("counts an interval that is still armed", () => {
    const before = pendingTimerCount()
    const id = setInterval(() => {}, 60_000)
    const armed = pendingTimerCount()
    clearInterval(id)
    expect(armed).toBe(before + 1)
  })

  // The one place an interval must not behave like a timeout: firing does not
  // disarm it, so forgetting it on the first tick would drop it from the sweep.
  it("keeps an interval tracked after it has fired", async () => {
    const before = pendingTimerCount()
    const id = setInterval(() => {}, 1)
    await new Promise<void>((resolve) => setTimeout(resolve, 20))
    const armed = pendingTimerCount()
    clearInterval(id)
    expect(armed).toBe(before + 1)
  })

  it("forgets an interval that was cleared", () => {
    const before = pendingTimerCount()
    const id = setInterval(() => {}, 60_000)
    clearInterval(id)
    expect(pendingTimerCount()).toBe(before)
  })

  it("cancels an interval still armed", async () => {
    const ran = vi.fn()
    const id = setInterval(ran, 1)
    try {
      clearPendingTimers()
      await new Promise<void>((resolve) => setTimeout(resolve, 20))
      expect(ran).not.toHaveBeenCalled()
    } finally {
      clearInterval(id)
    }
  })

Notes on why each case is shaped this way:
- Every case cancels its own interval before the assertion (or in a finally),
  so a run against the unfixed harness cannot leave a 1ms interval firing for
  the rest of the worker's life.
- "forgets an interval that was cleared" passes today vacuously (an untracked
  id cannot be forgotten). It is included because it is the guard that stops a
  future edit from tracking intervals without untracking them on clear.
- "cancels an interval still armed" is the case that reproduces the reported
  hazard directly: an interval armed before the sweep must not fire after it.

- [ ] **Step 2: Run it and confirm it fails for the right reason**

Run:

```bash
cd /root/repositories/darkmem/frontend && npx vitest run src/test/__tests__/pending-timers.test.ts
```

Expected — this is what the run actually printed on master:

Observed on the unfixed harness (real run, 2026-08-24):

 ❯ src/test/__tests__/pending-timers.test.ts (11 tests | 3 failed) 59ms
 AssertionError: expected 1 to be 2 // Object.is equality
  ❯ src/test/__tests__/pending-timers.test.ts:40:19      ("counts an interval that is still armed")
 AssertionError: expected 1 to be 2 // Object.is equality
  ❯ src/test/__tests__/pending-timers.test.ts:51:19      ("keeps an interval tracked after it has fired")
 AssertionError: expected "vi.fn()" to not be called at all, but actually been called 17 times
  ❯ src/test/__tests__/pending-timers.test.ts:67:23      ("cancels an interval still armed")

 Tests  3 failed | 8 passed (11)
 Test Files  1 failed (1)

("expected 1 to be 2" rather than "0 to be 1" because the file's first case
deliberately leaves one 60s timeout armed, so `before` is 1. The 17 calls in
the third failure is a 20ms wait against a 1ms interval, so the exact count
drifts run to run — 17 and 18 were both observed; only "not 0" is the point.)

- [ ] **Step 3: Apply the fix**

One file changes: frontend/src/test/pending-timers.ts. Two edits.

--- EDIT 1: extend the module doc block. ---

CURRENT (lines 19-22 of the file, inside the leading /** ... */ block):

 * and *every* notification leaves that 100ms timer armed. Whether one lands in
 * the gap is a question of machine load, which is why this turned the merge gate
 * red once and passed four full runs in a row afterwards.
 *
 * Clearing what is still armed when a file ends is safe by construction: every

REPLACE WITH:

 * and *every* notification leaves that 100ms timer armed. Whether one lands in
 * the gap is a question of machine load, which is why this turned the merge gate
 * red once and passed four full runs in a row afterwards.
 *
 * Intervals are tracked for the same reason and are the worse case: a timeout
 * lands in the gap at most once, an interval keeps firing into it. TanStack
 * Query arms one per observer with a `refetchInterval` (`use-jobs-api`,
 * `use-pipeline-api`, `use-feed`) through the plain global.
 *
 * Clearing what is still armed when a file ends is safe by construction: every

--- EDIT 2: replace everything from `type TimeoutId` (line 27) to the end of
the file (line 87). ---

CURRENT (verbatim, the whole remainder of the file):

type TimeoutId = ReturnType<typeof setTimeout>

const pending = new Set<TimeoutId>()

/** Captured before anything can swap the globals, so the sweep still works
 *  under `vi.useFakeTimers()`. */
let nativeClearTimeout: typeof globalThis.clearTimeout | null = null

/** For the harness's own test; not part of the fixture surface. */
export function pendingTimerCount(): number {
  return pending.size
}

/**
 * Wrap `setTimeout`/`clearTimeout` so what is still armed can be cancelled.
 *
 * Called at module scope in the setup file, which runs once per test file after
 * the environment is installed. `vi.useFakeTimers()` swaps these out for its
 * own while it is active and restores them after, so a test using fake timers
 * simply bypasses the tracking.
 */
export function trackTimers(): void {
  const nativeSetTimeout = globalThis.setTimeout
  nativeClearTimeout = globalThis.clearTimeout

  globalThis.setTimeout = ((
    handler: TimerHandler,
    timeout?: number,
    ...args: unknown[]
  ) => {
    // A string handler is `eval` in disguise and nothing here uses it; hand it
    // straight to the platform rather than reimplementing that path.
    if (typeof handler !== "function") {
      return nativeSetTimeout(handler, timeout, ...args)
    }
    // The wrapper closes over `id` before `nativeSetTimeout` returns it. Even a
    // zero-delay timer cannot fire before this frame yields, so the binding is
    // always assigned by the time the callback reads it.
    const id: TimeoutId = nativeSetTimeout(
      (...callbackArgs: unknown[]) => {
        pending.delete(id)
        handler(...callbackArgs)
      },
      timeout,
      ...args,
    )
    pending.add(id)
    return id
  }) as typeof globalThis.setTimeout

  globalThis.clearTimeout = ((id: TimeoutId) => {
    pending.delete(id)
    nativeClearTimeout?.(id)
  }) as typeof globalThis.clearTimeout
}

/** Cancel everything still armed. Run from `afterAll`. */
export function clearPendingTimers(): void {
  for (const id of pending) nativeClearTimeout?.(id)
  pending.clear()
}

REPLACE WITH (verbatim):

type TimerId = ReturnType<typeof setTimeout>

const pendingTimeouts = new Set<TimerId>()
const pendingIntervals = new Set<TimerId>()

/** Captured before anything can swap the globals, so the sweep still works
 *  under `vi.useFakeTimers()`. */
let nativeClearTimeout: typeof globalThis.clearTimeout | null = null
let nativeClearInterval: typeof globalThis.clearInterval | null = null

/** For the harness's own test; not part of the fixture surface. */
export function pendingTimerCount(): number {
  return pendingTimeouts.size + pendingIntervals.size
}

/** Either clear function cancels either kind of timer (HTML Living Standard,
 *  and Node follows it), so no wrapper may assume which set holds the id. */
function forget(id: TimerId): void {
  pendingTimeouts.delete(id)
  pendingIntervals.delete(id)
}

/**
 * Wrap `setTimeout`/`setInterval` and their clears so what is still armed can
 * be cancelled.
 *
 * Called at module scope in the setup file, which runs once per test file after
 * the environment is installed. `vi.useFakeTimers()` swaps these out for its
 * own while it is active and restores them after, so a test using fake timers
 * simply bypasses the tracking.
 */
export function trackTimers(): void {
  const nativeSetTimeout = globalThis.setTimeout
  const nativeSetInterval = globalThis.setInterval
  nativeClearTimeout = globalThis.clearTimeout
  nativeClearInterval = globalThis.clearInterval

  globalThis.setTimeout = ((
    handler: TimerHandler,
    timeout?: number,
    ...args: unknown[]
  ) => {
    // A string handler is `eval` in disguise and nothing here uses it; hand it
    // straight to the platform rather than reimplementing that path.
    if (typeof handler !== "function") {
      return nativeSetTimeout(handler, timeout, ...args)
    }
    // The wrapper closes over `id` before `nativeSetTimeout` returns it. Even a
    // zero-delay timer cannot fire before this frame yields, so the binding is
    // always assigned by the time the callback reads it.
    const id: TimerId = nativeSetTimeout(
      (...callbackArgs: unknown[]) => {
        pendingTimeouts.delete(id)
        handler(...callbackArgs)
      },
      timeout,
      ...args,
    )
    pendingTimeouts.add(id)
    return id
  }) as typeof globalThis.setTimeout

  globalThis.setInterval = ((
    handler: TimerHandler,
    timeout?: number,
    ...args: unknown[]
  ) => {
    if (typeof handler !== "function") {
      return nativeSetInterval(handler, timeout, ...args)
    }
    // Unlike the timeout wrapper, the callback does not forget the id: firing
    // does not disarm an interval, so only a clear or the sweep may drop it.
    const id: TimerId = nativeSetInterval(
      (...callbackArgs: unknown[]) => {
        handler(...callbackArgs)
      },
      timeout,
      ...args,
    )
    pendingIntervals.add(id)
    return id
  }) as typeof globalThis.setInterval

  globalThis.clearTimeout = ((id: TimerId) => {
    forget(id)
    nativeClearTimeout?.(id)
  }) as typeof globalThis.clearTimeout

  globalThis.clearInterval = ((id: TimerId) => {
    forget(id)
    nativeClearInterval?.(id)
  }) as typeof globalThis.clearInterval
}

/** Cancel everything still armed. Run from `afterAll`. */
export function clearPendingTimers(): void {
  for (const id of pendingTimeouts) nativeClearTimeout?.(id)
  for (const id of pendingIntervals) nativeClearInterval?.(id)
  pendingTimeouts.clear()
  pendingIntervals.clear()
}

Nothing in frontend/src/test/setup.ts changes: it already calls trackTimers()
at module scope and clearPendingTimers() from afterAll, and both keep their
signatures.

Two things in the replacement that look like they could be simplified and
cannot:

1. The interval handler is forwarded through an arrow that only calls it. That
   arrow is not decoration — passing `handler` (typed `TimerHandler`) straight
   to nativeSetInterval selects the DOM overload, which returns `number`, and
   `number` does not assign to `TimerId` (which resolves to NodeJS.Timeout in
   this project's type setup). `npx tsc -b` fails with
   "src/test/pending-timers.ts(104,11): error TS2322: Type 'number' is not
   assignable to type 'Timeout'." if someone removes it. Passing an arrow with
   a typed rest parameter selects the Node overload, exactly as the existing
   setTimeout wrapper already does.
2. `forget` deletes from both sets. clearTimeout(intervalId) and
   clearInterval(timeoutId) are both legal and both work (HTML Living Standard;
   Node's own clearInterval source carries that comment), so a wrapper that
   deleted from only "its" set would leave a genuinely cancelled id counted as
   pending until the end-of-file sweep.

- [ ] **Step 4: Run the same command and confirm it passes**

Harness suite, after the fix (real run):

 Test Files  1 passed (1)
      Tests  11 passed (11)

Whole frontend suite, after the fix (cd /root/repositories/darkmem/frontend && npx vitest run):

 Test Files  160 passed (160)
      Tests  1239 passed (1239)

Typecheck, after the fix (cd /root/repositories/darkmem/frontend && npx tsc -b):
no output, exit 0.

- [ ] **Step 5: Run the surrounding suite for regressions**

Blast radius is every frontend test file at once — vitest.config.ts lists
src/test/setup.ts as the single setupFile, so all 160 files import this module.
A mistake here does not fail one suite, it fails the run. Mitigation is that
the whole suite was run green with this exact patch applied (160 files / 1239
tests, 54s), alongside `npx tsc -b` clean.

The intended behaviour change: an interval armed during a test file is now
cancelled when that file ends. A test that deliberately relied on an interval
outliving its own file would break — none does (nothing under frontend/src
outside the harness calls setInterval at all; the callers are libraries,
principally @tanstack/query-core's queryObserver arming one per observer with a
refetchInterval, which darkmem sets in src/hooks/api/use-jobs-api.ts:51,
src/hooks/api/use-pipeline-api.ts:71,322 and src/features/activity/use-feed.ts:83).

Three narrower risks, each checked:
- `this` binding. The interval callback now runs through an arrow, so a
  non-arrow handler sees `this === undefined` rather than Node's Timeout
  object. This is exactly the pre-existing behaviour of the setTimeout wrapper,
  so it introduces no new class of difference, and no code in the tree reads
  `this` in a timer callback.
- Timer identity. The native id is returned unchanged, so `.unref()`, identity
  comparisons and a library's own clearInterval(id) all keep working — verified
  by the "forgets an interval that was cleared" case and by the full suite.
- Fake timers. `vi.useFakeTimers()` installs its own globals over these
  wrappers and restores them afterwards, so tracking is simply out of the path
  while they are active — unchanged by this patch, and covered by the two
  existing cases in the "under fake timers" describe block.

Existing tests covering the surrounding behaviour: the seven original cases in
frontend/src/test/__tests__/pending-timers.test.ts (counts an armed timer,
forgets a fired one, forgets a cleared one, still runs the callback with its
arguments, cancels everything still armed, and the two fake-timer cases) — all
still pass. Beyond that, the harness has no isolated coverage; the real
regression signal is the full `npx vitest run`.

Two facts an engineer picking this up needs:
- Both files this task edits are currently UNTRACKED in the working tree
  (`?? frontend/src/test/pending-timers.ts`, `?? frontend/src/test/__tests__/`)
  — they are in-flight work from another lane that has not committed yet. This
  task edits them in place, so it must land with or after that lane. Its
  collision surface is those two files and nothing else.
- This is not a running-artifact change and needs no redeploy. Nothing outside
  frontend/src/test imports pending-timers.ts (verified with rg), so it is
  never in the SPA bundle; the CLAUDE.md redeploy rule is scoped to changes
  that alter the running artifact.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/test/__tests__/pending-timers.test.ts frontend/src/test/pending-timers.ts
git commit -m "test(harness): track intervals in the timer sweep"
```

### Task 2: Float the graph detail panel when the split is too narrow

**Effort:** ~45 minutes.

**Files:**
- Modify: `frontend/src/features/graph/lib/panel-resize.ts:21-46`
- Modify: `frontend/src/features/memory-graph/components/real-memory-graph-page.tsx:7-7`
- Modify: `frontend/src/features/memory-graph/components/real-memory-graph-page.tsx:32-37`
- Modify: `frontend/src/features/memory-graph/components/real-memory-graph-page.tsx:94-99`
- Modify: `frontend/src/features/memory-graph/components/real-memory-graph-page.tsx:220-226`
- Modify: `frontend/src/features/memory-graph/components/real-memory-graph-page.tsx:448-462`
- Modify: `frontend/src/features/graph/lib/__tests__/detail-panel-size.test.ts:1-56`
- Create: `frontend/src/features/memory-graph/components/__tests__/detail-panel-narrow-container.test.tsx`
- Test: `frontend/src/features/memory-graph/components/__tests__/detail-panel-narrow-container.test.tsx`

**Interfaces:**
- Consumes: nothing from another task in this plan.
- Produces: no new exported symbol — this task changes behaviour inside an existing function.

**Owner decision this task carries** (answer before starting, not during):

None blocking. One adjacent defect worth the owner's attention, deliberately left out of this task: the detail panel's close button (`frontend/src/features/graph/components/graph-detail-panel.tsx:60-68`) is an icon-only `<Button>` wrapping a bare lucide `<X />` with no `aria-label` and no text, so it has no accessible name at all — a screen reader announces it as an unlabelled button, and the test above has to reach it positionally (`within(panel).getAllByRole("button")[0]`) rather than by name. Adding `aria-label="Close details panel"` is a one-line fix but is a different defect from F17 and belongs in its own change.

- [ ] **Step 1: Write the failing test**

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest"
import { render, screen, within } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import type { ReactNode } from "react"
import type { UnifiedGraphData } from "@/hooks/api"
import {
  DEFAULT_DETAIL_PANEL_WIDTH,
  DETAIL_PANEL_MIN_WIDTH,
  GRAPH_MIN_WIDTH,
} from "@/features/graph/lib/panel-resize"

vi.mock("@/features/chat/components/chat-overlay", () => ({
  ChatOverlay: () => null,
}))
vi.mock("@/features/graph/components/graph-2d-renderer", () => ({
  Graph2DRenderer: () => null,
}))
vi.mock("@/features/graph/components/graph-3d-renderer", () => ({
  Graph3DRenderer: () => null,
}))
vi.mock("@/features/graph/components/mini-graph", () => ({
  MiniGraph: () => null,
}))

const mockUseUnifiedGraph = vi.fn()
vi.mock("@/hooks/api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/hooks/api")>()),
  useUnifiedGraph: () => mockUseUnifiedGraph(),
}))

import { RealMemoryGraphPage } from "../real-memory-graph-page"

/** A phone in portrait: too narrow to seat the canvas and the panel at once. */
const NARROW = 400

const ONE_MEMORY: UnifiedGraphData = {
  memories: [
    {
      id: "m1",
      content: "hello",
      source: "api",
      tags: [],
      memory_type: null,
      importance: 0.5,
      cluster: 0,
    },
  ],
  clusters: {},
  cluster_names: {},
  similarity_edges: [],
}

function wrapper({ children }: { children: ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>
}

const realResizeObserver = window.ResizeObserver

// The suite-wide stub never reports a size, so the page would keep its
// unmeasured-container fallback and never reach the narrow branch at all.
function observeAt(width: number) {
  window.ResizeObserver = class {
    constructor(private cb: ResizeObserverCallback) {}
    observe() {
      this.cb(
        [
          { contentRect: { width, height: 768 } },
        ] as unknown as ResizeObserverEntry[],
        this as unknown as ResizeObserver,
      )
    }
    unobserve() {}
    disconnect() {}
  } as unknown as typeof ResizeObserver
}

describe("the detail panel in a container too narrow to split", () => {
  beforeEach(() => {
    mockUseUnifiedGraph.mockReset()
    mockUseUnifiedGraph.mockReturnValue({ data: ONE_MEMORY, isLoading: false })
    observeAt(NARROW)
  })

  afterEach(() => {
    window.ResizeObserver = realResizeObserver
  })

  it("still gives the panel a usable width", async () => {
    expect(NARROW - GRAPH_MIN_WIDTH).toBeLessThan(DETAIL_PANEL_MIN_WIDTH)
    const user = userEvent.setup()
    render(<RealMemoryGraphPage />, { wrapper })

    await user.click(
      screen.getByRole("button", { name: /show details panel/i }),
    )

    const panel = screen.getByTestId("graph-detail-panel")
    expect(parseFloat(panel.style.width)).toBeGreaterThanOrEqual(
      DETAIL_PANEL_MIN_WIDTH,
    )
  })

  // Opening the panel is one click and the toolbar's reopen button is gated on
  // the panel being shut, so a panel whose own close control cannot be reached
  // is a dead end until the page is reloaded.
  it("leaves the close control reachable", async () => {
    const user = userEvent.setup()
    render(<RealMemoryGraphPage />, { wrapper })

    await user.click(
      screen.getByRole("button", { name: /show details panel/i }),
    )
    const panel = screen.getByTestId("graph-detail-panel")
    expect(parseFloat(panel.style.width)).toBeGreaterThan(0)

    await user.click(within(panel).getAllByRole("button")[0]!)
    expect(screen.queryByTestId("graph-detail-panel")).not.toBeInTheDocument()
  })

  it("floats the panel over the canvas rather than splitting it", async () => {
    const user = userEvent.setup()
    render(<RealMemoryGraphPage />, { wrapper })

    await user.click(
      screen.getByRole("button", { name: /show details panel/i }),
    )

    expect(screen.getByTestId("graph-detail-panel")).toHaveAttribute(
      "data-layout",
      "overlay",
    )
    expect(
      screen.queryByRole("separator", { name: /resize the detail panel/i }),
    ).not.toBeInTheDocument()
  })
})

describe("the detail panel in a container that can seat both floors", () => {
  beforeEach(() => {
    mockUseUnifiedGraph.mockReset()
    mockUseUnifiedGraph.mockReturnValue({ data: ONE_MEMORY, isLoading: false })
    observeAt(1400)
  })

  afterEach(() => {
    window.ResizeObserver = realResizeObserver
  })

  it("keeps the split pane and its drag edge", async () => {
    const user = userEvent.setup()
    render(<RealMemoryGraphPage />, { wrapper })

    await user.click(
      screen.getByRole("button", { name: /show details panel/i }),
    )

    const panel = screen.getByTestId("graph-detail-panel")
    expect(panel).toHaveAttribute("data-layout", "split")
    expect(parseFloat(panel.style.width)).toBe(DEFAULT_DETAIL_PANEL_WIDTH)
    expect(
      screen.getByRole("separator", { name: /resize the detail panel/i }),
    ).toBeInTheDocument()
  })
})

- [ ] **Step 2: Run it and confirm it fails for the right reason**

Run:

```bash
cd /root/repositories/darkmem/frontend && npx vitest run src/features/memory-graph/components/__tests__/detail-panel-narrow-container.test.tsx
```

Expected — this is what the run actually printed on master:

All 4 tests fail. Measured on the tree as it stands today:

```
 ❯ src/features/memory-graph/components/__tests__/detail-panel-narrow-container.test.tsx (4 tests | 4 failed)
     × still gives the panel a usable width
     × leaves the close control reachable
     × floats the panel over the canvas rather than splitting it
     × keeps the split pane and its drag edge

 FAIL  ... > still gives the panel a usable width
AssertionError: expected 0 to be greater than or equal to 260
 ❯ ...detail-panel-narrow-container.test.tsx:99:43

 FAIL  ... > leaves the close control reachable
AssertionError: expected 0 to be greater than 0
 ❯ ...detail-panel-narrow-container.test.tsx:115:43

 FAIL  ... > floats the panel over the canvas rather than splitting it
Error: expect(element).toHaveAttribute("data-layout", "overlay")
Expected the element to have attribute: data-layout="overlay"
Received: null

 FAIL  ... > keeps the split pane and its drag edge
Error: expect(element).toHaveAttribute("data-layout", "split")
Expected the element to have attribute: data-layout="split"
Received: null

 Test Files  1 failed (1)
      Tests  4 failed (4)
```

The first two are the finding itself: at a 400px container `clampPanelWidth` takes the `ceiling <= DETAIL_PANEL_MIN_WIDTH` branch and returns 0, so the panel div renders `style="width: 0px"` with `overflow-hidden` and its close button has no box. The last two fail on the missing `data-layout` attribute, which is the layout mode the fix introduces (see the note in `implementation` about why that attribute exists).

- [ ] **Step 3: Apply the fix**

The finding is confirmed. `clampPanelWidth(320, 400)` computes `ceiling = 400 - 420 = -20`, takes the `ceiling <= DETAIL_PANEL_MIN_WIDTH` branch and returns `Math.max(0, Math.min(260, -20))` = **0**. The page renders the panel as `<div style={{width: 0}} class="... overflow-hidden">`, so the panel's own X close button has no box. The toolbar's "Show details panel" reopen button is rendered only when `!selection.showPanel`, so it is gone the moment the panel opens. The `PanelResizeHandle` is still in the DOM but inert, because `widthAt` -> `widthFromPointer` -> `clampPanelWidth` maps every pointer position back through the same branch to 0, and its arrow-key `nudge` clamps to `min=260` which `clampPanelWidth` then flattens to 0 again. Nothing on the page recovers; only a reload does. Before the split-pane change this panel was `w-[320px] max-w-[85vw]` and always rendered something (confirmed in `git diff` of the page).

The fix restores that overlay behaviour as an explicit second layout mode.

---

### 1. `frontend/src/features/graph/lib/panel-resize.ts`

CURRENT (lines 21-46, leave the file's leading block comment and `widthFromPointer` untouched):

```ts
/** Narrower than this and the summary's own rows start truncating. */
export const DETAIL_PANEL_MIN_WIDTH = 260

/** What the canvas keeps no matter how far the handle is dragged. */
export const GRAPH_MIN_WIDTH = 420

export const DEFAULT_DETAIL_PANEL_WIDTH = 320

/**
 * The width the panel may actually take right now.
 *
 * Both floors are honoured, and the canvas wins when the container is too
 * narrow to satisfy both: a panel that has eaten the graph is useless, while a
 * panel below its own minimum is merely cramped.
 */
export function clampPanelWidth(
  requested: number,
  containerWidth: number,
): number {
  if (!Number.isFinite(requested)) return DEFAULT_DETAIL_PANEL_WIDTH
  const ceiling = containerWidth - GRAPH_MIN_WIDTH
  if (ceiling <= DETAIL_PANEL_MIN_WIDTH) {
    return Math.max(0, Math.min(DETAIL_PANEL_MIN_WIDTH, ceiling))
  }
  return Math.max(DETAIL_PANEL_MIN_WIDTH, Math.min(ceiling, requested))
}
```

REPLACEMENT:

```ts
/** Narrower than this and the summary's own rows start truncating. */
export const DETAIL_PANEL_MIN_WIDTH = 260

/** What the canvas keeps no matter how far the handle is dragged. */
export const GRAPH_MIN_WIDTH = 420

export const DEFAULT_DETAIL_PANEL_WIDTH = 320

/** How much of a container too narrow to split the floating panel may cover. */
export const OVERLAY_MAX_FRACTION = 0.85

/**
 * Whether the container can seat both floors side by side.
 *
 * It cannot on a phone, a narrow window or a tablet in portrait, and there the
 * panel floats over the canvas rather than taking width from it. A split
 * honouring both floors would have to hand the panel zero, and a zero-width
 * panel takes its own close control off screen while the toolbar's reopen
 * button is hidden for as long as the panel is open — a dead end no gesture
 * escapes.
 */
export function isOverlayLayout(containerWidth: number): boolean {
  return containerWidth - GRAPH_MIN_WIDTH < DETAIL_PANEL_MIN_WIDTH
}

/**
 * The width the panel may actually take right now.
 *
 * Split: both floors are honoured, the canvas capping how far the handle goes.
 * Overlay: the panel keeps its own floor and is bounded by a share of the
 * container, so the canvas stays visible beside it.
 */
export function clampPanelWidth(
  requested: number,
  containerWidth: number,
): number {
  const want = Number.isFinite(requested)
    ? requested
    : DEFAULT_DETAIL_PANEL_WIDTH
  if (isOverlayLayout(containerWidth)) {
    return Math.min(
      Math.max(DETAIL_PANEL_MIN_WIDTH, want),
      containerWidth * OVERLAY_MAX_FRACTION,
    )
  }
  return Math.max(
    DETAIL_PANEL_MIN_WIDTH,
    Math.min(containerWidth - GRAPH_MIN_WIDTH, want),
  )
}
```

The boundary moves from `<=` to `<` deliberately: at a container of exactly `GRAPH_MIN_WIDTH + DETAIL_PANEL_MIN_WIDTH` (680px) both floors fit exactly, so that is a split, not an overlay. `isOverlayLayout(Number.POSITIVE_INFINITY)` is `false`, so the unmeasured-container path the page relies on still resolves to a split at the stored width.

---

### 2. `frontend/src/features/memory-graph/components/real-memory-graph-page.tsx`

Four edits.

**2a. Add the `cn` import** (after the `useSetPageChrome` import, line 7).

CURRENT:
```tsx
import { useSetPageChrome } from "@/components/app-chrome"
```
REPLACEMENT:
```tsx
import { useSetPageChrome } from "@/components/app-chrome"
import { cn } from "darkraise-ui/lib"
```

**2b. Import the new predicate** (lines 32-37).

CURRENT:
```tsx
import {
  clampPanelWidth,
  widthFromPointer,
  DETAIL_PANEL_MIN_WIDTH,
  GRAPH_MIN_WIDTH,
} from "@/features/graph/lib/panel-resize"
```
REPLACEMENT:
```tsx
import {
  clampPanelWidth,
  isOverlayLayout,
  widthFromPointer,
  DETAIL_PANEL_MIN_WIDTH,
  GRAPH_MIN_WIDTH,
} from "@/features/graph/lib/panel-resize"
```

**2c. Resolve the layout mode once** (lines 94-99).

CURRENT:
```tsx
  const panelWidth = clampPanelWidth(
    draggedPanelWidth ?? storedPanelWidth,
    // Before the split is measured, honour the stored width rather than
    // clamping against a zero container and collapsing the panel.
    splitWidth || Number.POSITIVE_INFINITY,
  )
```
REPLACEMENT:
```tsx
  // Before the split is measured, honour the stored width rather than clamping
  // against a zero container and collapsing the panel.
  const measuredWidth = splitWidth || Number.POSITIVE_INFINITY
  const overlayPanel = isOverlayLayout(measuredWidth)
  const panelWidth = clampPanelWidth(
    draggedPanelWidth ?? storedPanelWidth,
    measuredWidth,
  )
```

**2d. Make the split root a positioning context** (line 221-226).

CURRENT:
```tsx
    <div
      ref={splitRef}
      className="flex h-full overflow-hidden"
      style={{ minHeight: 0 }}
      data-testid="graph-split"
    >
```
REPLACEMENT:
```tsx
    <div
      ref={splitRef}
      className="relative flex h-full overflow-hidden"
      style={{ minHeight: 0 }}
      data-testid="graph-split"
    >
```

**2e. Render the panel as an overlay when there is no room to split** (lines 448-462; only the handle and the opening `<div>` change — everything from `<GraphDetailPanel` down is untouched).

CURRENT:
```tsx
      {selection.showPanel && memoryCount > 0 && (
        <>
          <PanelResizeHandle
            width={panelWidth}
            onResize={setDraggedPanelWidth}
            onCommit={commitPanelWidth}
            widthAt={widthAt}
            min={DETAIL_PANEL_MIN_WIDTH}
            max={Math.max(DETAIL_PANEL_MIN_WIDTH, splitWidth - GRAPH_MIN_WIDTH)}
          />
          <div
            data-testid="graph-detail-panel"
            className="bg-card flex shrink-0 flex-col overflow-hidden"
            style={{ width: panelWidth }}
          >
```
REPLACEMENT:
```tsx
      {selection.showPanel && memoryCount > 0 && (
        <>
          {!overlayPanel && (
            <PanelResizeHandle
              width={panelWidth}
              onResize={setDraggedPanelWidth}
              onCommit={commitPanelWidth}
              widthAt={widthAt}
              min={DETAIL_PANEL_MIN_WIDTH}
              max={Math.max(
                DETAIL_PANEL_MIN_WIDTH,
                splitWidth - GRAPH_MIN_WIDTH,
              )}
            />
          )}
          <div
            data-testid="graph-detail-panel"
            data-layout={overlayPanel ? "overlay" : "split"}
            className={cn(
              "bg-card flex flex-col overflow-hidden",
              overlayPanel
                ? "border-border absolute inset-y-0 right-0 z-40 border-l shadow-xl"
                : "shrink-0",
            )}
            style={{ width: panelWidth }}
          >
```

Why `data-layout` exists at all: jsdom loads no Tailwind stylesheet and performs no layout, so `getComputedStyle` cannot tell an overlay from a split pane and there is nothing else on the element that names the mode. This is the same reason the sibling `data-testid="graph-detail-panel"` is there. It costs one attribute and makes the mode assertable.

The handle is not rendered in overlay mode because there is no split to drag: it was already inert there (every pointer position and every arrow-key nudge clamped back through the same branch), so this removes a control that never did anything rather than removing a capability.

---

### 3. `frontend/src/features/graph/lib/__tests__/detail-panel-size.test.ts`

Two existing assertions pin the behaviour being replaced and must be rewritten — this is the behaviour change, not a workaround. Add `isOverlayLayout` and `OVERLAY_MAX_FRACTION` to the import list at the top of the file, then:

CURRENT (lines 45-56):
```ts
  describe("a container too narrow for both floors", () => {
    // The canvas wins: a panel that has eaten the graph is useless, while a
    // panel under its own minimum is merely cramped.
    it("never lets the panel exceed what the canvas leaves", () => {
      const container = GRAPH_MIN_WIDTH + 100
      expect(clampPanelWidth(400, container)).toBe(100)
    })

    it("collapses rather than going negative", () => {
      expect(clampPanelWidth(400, GRAPH_MIN_WIDTH - 50)).toBe(0)
    })
  })
```
REPLACEMENT:
```ts
  describe("a container too narrow for both floors", () => {
    // Neither floor is squeezed here: the panel floats over the canvas instead
    // of taking width from it, because a panel narrowed to nothing takes its
    // own close control with it and the toolbar's reopen button is hidden for
    // as long as the panel is open.
    it("keeps the panel usable rather than collapsing it", () => {
      const container = GRAPH_MIN_WIDTH + 100
      expect(isOverlayLayout(container)).toBe(true)
      expect(clampPanelWidth(400, container)).toBe(400)
    })

    it("never hands the panel a width of zero", () => {
      for (const container of [320, 420, GRAPH_MIN_WIDTH - 50, 600, 679]) {
        expect(clampPanelWidth(400, container)).toBeGreaterThan(0)
      }
    })

    it("leaves the canvas visible beside the floating panel", () => {
      const container = GRAPH_MIN_WIDTH - 50
      expect(clampPanelWidth(400, container)).toBe(
        container * OVERLAY_MAX_FRACTION,
      )
    })
  })

  it("splits as soon as the container can seat both floors", () => {
    const exact = GRAPH_MIN_WIDTH + DETAIL_PANEL_MIN_WIDTH
    expect(isOverlayLayout(exact)).toBe(false)
    expect(isOverlayLayout(exact - 1)).toBe(true)
    expect(clampPanelWidth(400, exact)).toBe(DETAIL_PANEL_MIN_WIDTH)
  })
```

The other nine assertions in that file are unaffected and were verified to still pass.

---

Scope note: this task does not address F18 (a click without a drag committing the clamped width). The two interact only in that the handle is no longer rendered below 680px, so F18's misfire is now impossible in the narrow regime; it remains live in the split regime (stored 800 on a 900px window still clamps to 480 and a bare click still commits it).

This is a `frontend/` change, so it alters the running artifact: after it lands, redeploy this host per CLAUDE.md (`./scripts/gate.sh` -> `DARKMEM_PUSH=0 ./scripts/build-push.sh` -> `docker compose up -d` -> confirm the change is in the running image). No backend, schema or migration surface is touched.

- [ ] **Step 4: Run the same command and confirm it passes**

```
 ✓ src/features/memory-graph/components/__tests__/detail-panel-narrow-container.test.tsx (4 tests)

 Test Files  1 passed (1)
      Tests  4 passed (4)
```

Verified end to end: with the fix applied all 4 pass; with the fix reverted all 4 fail as quoted above. Also measured with the fix applied:

- `cd /root/repositories/darkmem/frontend && npx vitest run src/features/graph src/features/memory-graph` -> `Test Files 26 passed (26) / Tests 253 passed (253)`
- `cd /root/repositories/darkmem/frontend && npx tsc -b` -> exit 0, no output
- `cd /root/repositories/darkmem/frontend && npx vitest run src/routes/_authenticated/__tests__/memory-graph-route.real.test.tsx src/routes/_authenticated/__tests__/memory-graph-route.demo.test.tsx` -> `Test Files 2 passed (2)`

- [ ] **Step 5: Run the surrounding suite for regressions**

Four real risks, each checked:

1. **`relative` on the split root creates a new containing block.** Every absolutely positioned element on the canvas side (the filter button, the toolbar, the truncation banner, the filter drawer, the chat overlay, the refetch spinner) lives inside `<div ref={containerRef} className="relative min-h-0 flex-1">`, which is already a containing block, so none of them re-anchor. The only other absolutely positioned descendant of the root is the `sr-only` `<h1>`, which Tailwind clips to a 1x1 box — no visual effect. Verified: `src/features/memory-graph/components/__tests__/real-memory-graph-page.test.tsx` and `graph-loading-affordance.test.tsx` both still pass.

2. **Stacking order.** `position: relative` without a `z-index` does not open a stacking context, so the canvas column's `z-20`/`z-25`/`z-30` children compete with the overlay panel in the root's context. The panel is `z-40`, so it paints above the toolbar and the filter drawer — which is what an overlay must do. Not covered by a test (jsdom does not paint); confirm by eye during the post-landing redeploy at a narrow browser window.

3. **The overlay covers part of the canvas below 680px.** Deliberate, and it is what this page did before the split-pane change (`w-[320px] max-w-[85vw]`). `OVERLAY_MAX_FRACTION = 0.85` reproduces that 85% bound, so a strip of graph always shows to the left of the panel.

4. **The resize handle disappears below 680px, taking the keyboard resize path with it.** Correct rather than a loss: in that regime `widthAt` and `nudge` both routed through the branch that returned 0, so neither the pointer nor the arrow keys could move the edge. The new page test `keeps the split pane and its drag edge` pins that the handle is still there at 1400px.

Tests covering the surrounding behaviour, all measured green with the fix applied:

| File | What it covers |
|---|---|
| `frontend/src/features/graph/lib/__tests__/detail-panel-size.test.ts` | the clamp itself (two assertions rewritten by this task, nine untouched) |
| `frontend/src/features/memory-graph/components/__tests__/real-memory-graph-page.test.tsx` | page renders, entity layer, truncation banner |
| `frontend/src/features/memory-graph/components/__tests__/graph-loading-affordance.test.tsx` | skeleton / refetch affordances on the same page |
| `frontend/src/routes/_authenticated/__tests__/memory-graph-route.{real,demo}.test.tsx` | the route that mounts this page |
| `frontend/src/features/graph/components/__tests__/*.tsx` (8 files) | the panel's own contents, summary and neighbours |

No Playwright e2e touches `graph-detail-panel` or `graph-split` (grepped `frontend/tests/`), so the e2e lane is unaffected. Nothing backend, nothing in `backend/migrations/versions/0001_baseline.py`.

One caveat about the full frontend suite: `npx vitest run` over the whole tree currently reports unrelated failures in `src/features/settings/__tests__/settings-flags*.test.tsx`, `src/features/code/__tests__/real-repositories-view.test.tsx` and a missing `src/test/__tests__/probe.test.ts`. Those come from other lanes' uncommitted work in the same working tree (findings F11/F13/F15/F19), not from this change — the failure set varied between two consecutive runs while this change sat untouched.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/features/graph/lib/__tests__/detail-panel-size.test.ts frontend/src/features/graph/lib/panel-resize.ts frontend/src/features/memory-graph/components/__tests__/detail-panel-narrow-container.test.tsx frontend/src/features/memory-graph/components/real-memory-graph-page.tsx
git commit -m "fix(graph): float the detail panel when too narrow"
```

### Task 3: Commit the detail-panel width only after an actual drag

**Effort:** ~25 minutes.

**Files:**
- Modify: `frontend/src/features/graph/components/panel-resize-handle.tsx:39-71`
- Create: `frontend/src/features/graph/components/__tests__/panel-resize-handle.test.tsx`
- Test: `frontend/src/features/graph/components/__tests__/panel-resize-handle.test.tsx`

**Interfaces:**
- Consumes: nothing from another task in this plan.
- Produces: no new exported symbol — this task changes behaviour inside an existing function.

**Owner decision this task carries** (answer before starting, not during):

Should a press that drifts a pixel or two horizontally also be treated as a click? The fix as written closes the reported bug (zero horizontal movement) exactly, but a 1px accidental drag still overwrites a stored 800px preference with ~481px, because by the component's definition that is a resize. Closing it means a slop threshold — ignore the drag until the pointer has moved, say, 3px from where it went down — which is standard practice but does make sub-threshold fine adjustments impossible with the mouse (the arrow keys already move in 24px steps, so there is no fine keyboard path either). That is a feel decision for the repo owner, not something to slip in under a correctness fix, so it is not in the implementation above.

- [ ] **Step 1: Write the failing test**

import { describe, it, expect, beforeAll, beforeEach, vi } from "vitest"
import { render, screen, fireEvent } from "@testing-library/react"
import { useState } from "react"
import { PanelResizeHandle } from "../panel-resize-handle"
import { useGraphPrefs } from "@/features/graph/lib/graph-prefs"
import {
  clampPanelWidth,
  widthFromPointer,
  DETAIL_PANEL_MIN_WIDTH,
  GRAPH_MIN_WIDTH,
} from "@/features/graph/lib/panel-resize"

// The window the user is on now; the stored preference was chosen on a much
// wider monitor, so it renders clamped.
const CONTAINER = 900
const STORED = 800

beforeAll(() => {
  // jsdom ships neither half of the pointer-capture API; the handle takes the
  // capture so a drag survives the pointer crossing the canvas.
  Element.prototype.setPointerCapture =
    vi.fn() as unknown as Element["setPointerCapture"]
  Element.prototype.releasePointerCapture =
    vi.fn() as unknown as Element["releasePointerCapture"]
})

/**
 * The page's own wiring: the rendered width is the stored one clamped against
 * today's container, a live drag overrides it, and a commit writes the store.
 */
function Split() {
  const stored = useGraphPrefs((s) => s.detailPanelWidth)
  const [dragged, setDragged] = useState<number | null>(null)
  const width = clampPanelWidth(dragged ?? stored, CONTAINER)
  return (
    <PanelResizeHandle
      width={width}
      onResize={setDragged}
      onCommit={(px) => {
        setDragged(null)
        useGraphPrefs.getState().setDetailPanelWidth(px)
      }}
      widthAt={(clientX) => widthFromPointer(clientX, CONTAINER, CONTAINER)}
      min={DETAIL_PANEL_MIN_WIDTH}
      max={CONTAINER - GRAPH_MIN_WIDTH}
    />
  )
}

const grip = () =>
  screen.getByRole("separator", { name: /resize the detail panel/i })

/** Where the edge sits for the width currently on screen. */
const edgeAt = (width: number) => CONTAINER - width

describe("PanelResizeHandle", () => {
  beforeEach(() => {
    localStorage.clear()
    useGraphPrefs.setState({ detailPanelWidth: STORED })
  })

  // A width wider than today's window is clamped on render, never rewritten:
  // it has to come back in full on the monitor it was chosen on.
  it("leaves the stored width alone when the pointer never moves", () => {
    render(<Split />)
    const clamped = clampPanelWidth(STORED, CONTAINER)
    const x = edgeAt(clamped)

    fireEvent.pointerDown(grip(), { pointerId: 1, clientX: x })
    fireEvent.pointerUp(grip(), { pointerId: 1, clientX: x })

    expect(useGraphPrefs.getState().detailPanelWidth).toBe(STORED)
  })

  it("leaves the stored width alone when a press is cancelled unmoved", () => {
    render(<Split />)
    const x = edgeAt(clampPanelWidth(STORED, CONTAINER))

    fireEvent.pointerDown(grip(), { pointerId: 1, clientX: x })
    fireEvent.pointerCancel(grip(), { pointerId: 1, clientX: x })

    expect(useGraphPrefs.getState().detailPanelWidth).toBe(STORED)
  })

  it("stores the width a real drag ends at", () => {
    render(<Split />)
    const start = edgeAt(clampPanelWidth(STORED, CONTAINER))

    fireEvent.pointerDown(grip(), { pointerId: 1, clientX: start })
    fireEvent.pointerMove(grip(), { pointerId: 1, clientX: 500 })
    fireEvent.pointerUp(grip(), { pointerId: 1, clientX: 500 })

    expect(useGraphPrefs.getState().detailPanelWidth).toBe(
      widthFromPointer(500, CONTAINER, CONTAINER),
    )
  })

  it("stores a width chosen with the arrow keys", () => {
    render(<Split />)

    fireEvent.keyDown(grip(), { key: "ArrowRight" })

    const clamped = clampPanelWidth(STORED, CONTAINER)
    expect(useGraphPrefs.getState().detailPanelWidth).toBeLessThan(clamped)
  })
})

- [ ] **Step 2: Run it and confirm it fails for the right reason**

Run:

```bash
cd /root/repositories/darkmem/frontend && npx vitest run src/features/graph/components/__tests__/panel-resize-handle.test.tsx
```

Expected — this is what the run actually printed on master:

Two of the four tests fail before the fix, both with the clamped width written over the stored one:

 FAIL  src/features/graph/components/__tests__/panel-resize-handle.test.tsx > PanelResizeHandle > leaves the stored width alone when the pointer never moves
 AssertionError: expected 480 to be 800 // Object.is equality
 - Expected
 + Received
 - 800
 + 480
   72|     expect(useGraphPrefs.getState().detailPanelWidth).toBe(STORED)

 FAIL  src/features/graph/components/__tests__/panel-resize-handle.test.tsx > PanelResizeHandle > leaves the stored width alone when a press is cancelled unmoved
 AssertionError: expected 480 to be 800 // Object.is equality

 Test Files  1 failed (1)
      Tests  2 failed | 2 passed (4)

480 is clampPanelWidth(800, 900) — the container's 900px minus the canvas floor of 420. The other two tests (a real drag, and the arrow keys) pass before and after, so they pin that the fix does not simply stop committing.

- [ ] **Step 3: Apply the fix**

One file: `frontend/src/features/graph/components/panel-resize-handle.tsx`. Four small edits inside `PanelResizeHandle`, all in the block from the refs down to `endDrag`. Nothing else in the file, and no other file, changes.

--- Edit 1: the ref block (currently lines 39-41) ---

CURRENT:
```tsx
  const draggingRef = useRef(false)
  const latestRef = useRef(width)
  latestRef.current = width
```

REPLACE WITH:
```tsx
  const draggingRef = useRef(false)
  const movedRef = useRef(false)
  const downXRef = useRef(0)
  const latestRef = useRef(width)
  latestRef.current = width
```

--- Edit 2: inside `handlePointerDown` (currently lines 44-46) ---

CURRENT:
```tsx
      event.preventDefault()
      draggingRef.current = true
      event.currentTarget.setPointerCapture(event.pointerId)
```

REPLACE WITH:
```tsx
      event.preventDefault()
      draggingRef.current = true
      movedRef.current = false
      downXRef.current = event.clientX
      event.currentTarget.setPointerCapture(event.pointerId)
```

--- Edit 3: the body of `handlePointerMove` (currently lines 58-59) ---

CURRENT:
```tsx
      if (!draggingRef.current) return
      onResize(widthAt(event.clientX))
```

REPLACE WITH:
```tsx
      if (!draggingRef.current) return
      // Vertical-only movement maps to the width already on screen, so it is
      // not a resize either.
      if (event.clientX === downXRef.current) return
      movedRef.current = true
      onResize(widthAt(event.clientX))
```

--- Edit 4: the tail of `endDrag` (currently lines 69-71) ---

CURRENT:
```tsx
      document.body.style.cursor = ""
      document.body.style.userSelect = ""
      onCommit(latestRef.current)
```

REPLACE WITH:
```tsx
      document.body.style.cursor = ""
      document.body.style.userSelect = ""
      // A press that never moved the edge chose no width. Committing the one
      // on screen would write back a stored preference that today's container
      // is only clamping, losing the width the user picked on a wider screen.
      if (!movedRef.current) return
      onCommit(latestRef.current)
```

Note what the early return in Edit 4 sits *after*: `draggingRef.current = false`, `releasePointerCapture` and both `document.body` style resets all still run on a bare click, so the cursor and text-selection state are cleaned up exactly as before. Only the commit is skipped.

Why the guard in Edit 3 compares `clientX` rather than just setting a flag on any move: a press that jitters vertically fires `pointermove` with an unchanged `clientX`, and `widthAt` maps that back to the width already on screen — committing it would rewrite the stored preference with the clamp, which is the same defect. Skipping `onResize` there also keeps the page's transient `draggedPanelWidth` at `null` for a gesture that will not commit, so the invariant is exact: `onCommit` fires from a pointer gesture if and only if `onResize` fired during it, and a gesture that never called `onResize` leaves no local override stranded.

`nudge` (the arrow keys) is untouched and keeps calling `onResize` then `onCommit`: a key press is a deliberate width choice, not an accidental click.

- [ ] **Step 4: Run the same command and confirm it passes**

cd /root/repositories/darkmem/frontend && npx vitest run src/features/graph/components/__tests__/panel-resize-handle.test.tsx

 Test Files  1 passed (1)
      Tests  4 passed (4)

Measured with the fix applied. The wider suite around it also stays green: `npx vitest run src/features/graph` gives "Test Files 23 passed (23) / Tests 243 passed (243)", `npx vitest run src/features/memory-graph` gives "Test Files 3 passed (3) / Tests 8 passed (8)", and `npx tsc -b` exits 0 with no output.

- [ ] **Step 5: Run the surrounding suite for regressions**

The behaviour that changes is narrow: a pointer gesture that never moves the pointer horizontally no longer writes the panel width to `localStorage`. Nothing else about the drag changes — the live `onResize` during a drag, the commit at the end of a real drag, the arrow-key commit, the pointer capture and the body cursor/user-select cleanup are all unchanged, including on the skipped path.

Honest risks:

1. A pointing device or browser that delivers `pointerup` at a different `clientX` without ever delivering a `pointermove` would now be treated as a click and would not commit. In practice pointer capture guarantees the intermediate moves are delivered to the captured element, and the panel width would simply stay where the last rendered width put it (no visual jump, no stuck state), so the failure mode is "the resize is ignored", not corruption. I could not construct this case in jsdom or reason it into a real browser.

2. The residual the fix does *not* close: a hair-trigger click that drifts one pixel horizontally is a real drag by this definition and still commits ~481px over a stored 800px. Closing that needs a slop threshold (a few px before a press counts as a drag), which changes drag feel for deliberate fine adjustments. See `needs_decision`.

3. Two other lanes are editing this area concurrently — `frontend/src/features/graph/lib/panel-resize.ts` and `frontend/src/features/memory-graph/components/real-memory-graph-page.tsx` (the F17 overlay-layout fix). This task touches neither, and the new test is written so it passes against both the pre-F17 `clampPanelWidth` and the overlay version: at a 900px container both return 480 for a stored 800, and the container is deliberately wide enough that `isOverlayLayout` is false either way.

Existing tests covering the surrounding behaviour, all of which pass with the fix applied:
- `frontend/src/features/graph/lib/__tests__/detail-panel-size.test.ts` — `clampPanelWidth`, `widthFromPointer`, and the store rule this finding relies on ("keeps a width wider than a small window would allow").
- `frontend/src/features/graph/lib/__tests__/graph-prefs.test.ts` — the persisted preference store.
- `frontend/src/features/memory-graph/components/__tests__/real-memory-graph-page.test.tsx` and `graph-loading-affordance.test.tsx` — the page that wires the handle.
- The whole `src/features/graph` directory (23 files, 243 tests).

This changes `frontend/`, so it alters the running artifact: after it lands, the host needs `./scripts/gate.sh` → `DARKMEM_PUSH=0 ./scripts/build-push.sh` → `docker compose up -d`, then confirm the change is in the running image rather than only in the tree. No backend, no schema, no migration — `backend/migrations/versions/0001_baseline.py` is untouched.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/features/graph/components/__tests__/panel-resize-handle.test.tsx frontend/src/features/graph/components/panel-resize-handle.tsx
git commit -m "fix(graph): commit panel width only after a drag"
```

### Task 4: Surface refused Flags-tab saves and gate Settings reads in demo

**Effort:** ~90 minutes.

**Files:**
- Modify: `frontend/src/features/settings/use-flags-tab-binding.ts:168-209`
- Modify: `frontend/src/features/settings/use-flags-tab-binding.ts:253-338`
- Modify: `frontend/src/features/settings/use-flags-tab-binding.ts:483-502`
- Modify: `frontend/src/features/settings/components/flags-tab.tsx:84-137`
- Modify: `frontend/src/features/settings/components/flags-tab.tsx:620-632`
- Modify: `frontend/src/features/settings/components/flags-tab.tsx:765-780`
- Modify: `frontend/src/features/settings/components/flags-tab.tsx:1033-1050`
- Modify: `frontend/src/features/settings/components/flags-tab.tsx:1160-1175`
- Modify: `frontend/src/features/settings/components/flags-tab.tsx:1225-1240`
- Modify: `frontend/src/hooks/api/use-config-api.ts:275-283`
- Modify: `frontend/src/hooks/api/use-auto-research-api.ts:21-26`
- Modify: `frontend/src/hooks/api/use-auto-research-api.ts:75-80`
- Modify: `frontend/src/hooks/api/use-llm-providers-api.ts:60-65`
- Modify: `frontend/src/features/settings/components/research-tab.tsx:1-45`
- Modify: `frontend/src/features/settings/components/providers-panel.tsx:1-20`
- Modify: `frontend/src/features/settings/__tests__/settings-flags.real.test.tsx:443-483`
- Modify: `frontend/src/features/settings/__tests__/settings-flags.test.tsx:1-4`
- Modify: `frontend/src/features/settings/__tests__/settings-flags.test.tsx:405-413`
- Create: `frontend/src/features/settings/__tests__/settings-flags.demo.test.tsx`
- Create: `frontend/src/features/settings/__tests__/settings-flags-save-error.real.test.tsx`
- Test: `frontend/src/features/settings/__tests__/settings-flags.demo.test.tsx`

**Interfaces:**
- Consumes: nothing from another task in this plan.
- Produces: no new exported symbol — this task changes behaviour inside an existing function.

**Owner decision this task carries** (answer before starting, not during):

Two, both for the repo owner.

(a) Demo mode's Research tab. Gating `useAutoResearch` leaves the tab reading
"reading…" forever, because that copy is deliberately keyed on "the row has not
answered yet" rather than on a default. The alternatives are a demo fixture for
`auto_research` (matching what `useDemoFlags` does for the Flags tab) or a third
state meaning "no backend to ask". I took neither, because inventing a demo
posture for the research loop is a content decision, not a bug fix. The same
question applies in miniature to ProvidersPanel, which now renders its empty
state — "no providers configured" is a claim, and in demo mode nothing was asked.

(b) An adjacent hazard I found and deliberately did NOT fix:
`frontend/src/features/settings/components/purpose-dialog.tsx` also calls
`useLlmProviders()` ungated (line 101), and worse, its effect at line ~109 fires
`probe.mutate({ name: providerName })` — a POST to /config/llm-providers/{name}/probe
— every time the dialog opens. An `enabled` flag cannot gate a mutation, so this
one needs its own guard and its own task. In demo mode, opening any purpose editor
on the LLM tab still 401-redirects to /login today.

- [ ] **Step 1: Write the failing test**

Two NEW test files. They cannot be one file: the demo half must run with
`DEMO: true` and the error half with `DEMO: false`, and that mock is module-level.

================================================================================
FILE 1 (new): frontend/src/features/settings/__tests__/settings-flags.demo.test.tsx
covers F15 (the demo 401-redirect)
================================================================================

import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { act, render, renderHook } from "@testing-library/react"
import type { ReactNode } from "react"
import { beforeEach, describe, expect, it, vi } from "vitest"

vi.mock("@/lib/demo-flag", () => ({ DEMO: true }))
vi.mock("@/lib/api", () => ({ apiFetch: vi.fn() }))

import { apiFetch } from "@/lib/api"
import { ProvidersPanel } from "../components/providers-panel"
import { ResearchTab } from "../components/research-tab"
import { useFlagsTabBinding } from "../use-flags-tab-binding"

function wrapper({ children }: { children: ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>
}

describe("useFlagsTabBinding (DEMO on — standalone fixture)", () => {
  beforeEach(() => vi.clearAllMocks())

  it("serves the fixture without ever calling the network", async () => {
    const { result } = renderHook(() => useFlagsTabBinding(), { wrapper })
    await act(async () => {
      await Promise.resolve()
    })

    expect(result.current.isLoading).toBe(false)
    expect(result.current.availableAreas.length).toBeGreaterThan(0)
    // A 401 on a demo build reaches `handleUnauthorized`, which sends the
    // browser to /login — a sign-in form on a build that has no accounts.
    expect(apiFetch).not.toHaveBeenCalled()
  })
})

describe("the other Settings surfaces a demo reader can open", () => {
  beforeEach(() => vi.clearAllMocks())

  it("renders the Research tab without calling the network", async () => {
    render(<ResearchTab />, { wrapper })
    await act(async () => {
      await Promise.resolve()
    })
    expect(apiFetch).not.toHaveBeenCalled()
  })

  it("renders the Providers panel without calling the network", async () => {
    render(<ProvidersPanel />, { wrapper })
    await act(async () => {
      await Promise.resolve()
    })
    expect(apiFetch).not.toHaveBeenCalled()
  })
})

================================================================================
FILE 2 (new): frontend/src/features/settings/__tests__/settings-flags-save-error.real.test.tsx
covers F11 (the swallowed write failure)
================================================================================

import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import {
  fireEvent,
  render,
  screen,
  waitFor,
  within,
} from "@testing-library/react"
import type { ReactNode } from "react"
import { afterEach, describe, expect, it, vi } from "vitest"

vi.mock("@/lib/demo-flag", () => ({ DEMO: false }))
vi.mock("@/lib/api", () => ({ apiFetch: vi.fn() }))

import { apiFetch } from "@/lib/api"
import { FlagsTab } from "../components/flags-tab"

function wrapper({ children }: { children: ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>
}

const FEATURE_FLAGS_FIXTURE = {
  hybrid_search_enabled: true,
  reranker_enabled: false,
  pipeline_concurrency: 5,
  classification_areas: ["general"],
  classification_mode: "simple",
  embedding_batch_size: 20,
  embedding_concurrency: 1,
  entity_cache_ttl_minutes: 60,
  relation_rescue: true,
  confidence_rank_gamma: 0.4,
  w_importance: 0,
  w_heat: 0,
  w_recency: 0,
  w_context_boost: 0.25,
  ppr_enabled: false,
  w_ppr: 0,
  dual_level_enabled: true,
  w_dual: 0.15,
  community_injection_enabled: false,
  classification_labels: [{ name: "fact", description: "a fact", area: null }],
  classification_areas_apply: false,
  graph_channels: [],
  rank_arms: [],
  measurable_flags: [],
  measured_flags: [],
}

const LADDER_FIXTURE = {
  params: [],
  measured: [],
  row_present: false,
  measurement_task: "T2.40",
}

/** The API's own 422 for `w_heat: Field(ge=0, le=5)` — the case an operator
 *  reaches by typing a number the control happily accepts. */
const REFUSAL = "w_heat: Input should be less than or equal to 5"

function mockApiFetch() {
  vi.mocked(apiFetch).mockImplementation(
    (path: string, init?: RequestInit) => {
      if (init?.method === "PUT") return Promise.reject(new Error(REFUSAL))
      if (path === "/config/feature-flags") {
        return Promise.resolve(FEATURE_FLAGS_FIXTURE)
      }
      if (path === "/config/repo-allowlist") {
        return Promise.resolve({ patterns: [] })
      }
      if (path === "/config/verification-ladder") {
        return Promise.resolve(LADDER_FIXTURE)
      }
      if (path === "/config/classification-areas") return Promise.resolve([])
      return Promise.reject(new Error(`unexpected apiFetch(${path})`))
    },
  )
}

describe("FlagsTab — a refused write reaches the operator", () => {
  afterEach(() => vi.clearAllMocks())

  it("renders the API's refusal and keeps the edits in an open dialog", async () => {
    mockApiFetch()
    render(<FlagsTab />, { wrapper })
    await screen.findByText("w_heat")

    fireEvent.click(
      screen.getByRole("button", { name: "Edit rank_fusion_factor arms" }),
    )
    const dialog = screen.getByRole("dialog")
    const input = within(dialog).getByLabelText("w_heat")
    fireEvent.change(input, { target: { value: "0.5" } })
    fireEvent.keyDown(input, { key: "Enter" })
    fireEvent.click(within(dialog).getByRole("button", { name: "Save" }))

    // Without this the save is silent: the dialog closes, the spinner stops,
    // the refetch repaints the old number, and the control reads as broken.
    await waitFor(() =>
      expect(screen.getByText(new RegExp(REFUSAL))).toBeInTheDocument(),
    )
    // The edits are the operator's only copy — closing over a refusal throws
    // away every other arm that one request carried.
    expect(screen.getByRole("dialog")).toBeInTheDocument()
    expect(
      within(screen.getByRole("dialog")).getByLabelText("w_heat"),
    ).toHaveValue("0.5")
  })
})

- [ ] **Step 2: Run it and confirm it fails for the right reason**

Run:

```bash
cd /root/repositories/darkmem/frontend && npx vitest run src/features/settings/__tests__/settings-flags.demo.test.tsx src/features/settings/__tests__/settings-flags-save-error.real.test.tsx
```

Expected — this is what the run actually printed on master:

Both files fail, 4 tests failing and 0 passing:

 FAIL  src/features/settings/__tests__/settings-flags.demo.test.tsx > useFlagsTabBinding (DEMO on — standalone fixture) > serves the fixture without ever calling the network
 AssertionError: expected "vi.fn()" to not be called at all, but actually been called 1 times
 Received:
   1st vi.fn() call:
     Array [ "/config/classification-areas" ]

 (the ResearchTab and ProvidersPanel cases fail the same way, on
  "/config/auto-research" + "/config/auto-research/runs" and
  "/config/llm-providers" respectively)

 FAIL  src/features/settings/__tests__/settings-flags-save-error.real.test.tsx > FlagsTab — a refused write reaches the operator > renders the API's refusal and keeps the edits in an open dialog
 TestingLibraryElementError: Unable to find an element with the text: /w_heat: Input should be less than or equal to 5/. This could be because the text is broken up by multiple elements.

 Test Files  2 failed (2)
      Tests  4 failed (4)

- [ ] **Step 3: Apply the fix**

SEVEN source edits plus TWO edits to existing tests. Every "current" block below is
verbatim from master; replace it with the "replacement" block.

--------------------------------------------------------------------------------
EDIT 1 — frontend/src/hooks/api/use-config-api.ts (around line 275)
Give the hook the `enabled` option `useSystemPrompts`/`useNotifications` already have.
--------------------------------------------------------------------------------
current:

export function useClassificationAreas() {
  return useQuery<ClassificationAreaInfo[]>({
    queryKey: ["classificationAreas"],
    queryFn: () =>
      apiFetch<ClassificationAreaInfo[]>("/config/classification-areas"),
    staleTime: 300_000,
  })
}

replacement:

export function useClassificationAreas(options?: { enabled?: boolean }) {
  return useQuery<ClassificationAreaInfo[]>({
    queryKey: ["classificationAreas"],
    queryFn: () =>
      apiFetch<ClassificationAreaInfo[]>("/config/classification-areas"),
    staleTime: 300_000,
    enabled: options?.enabled ?? true,
  })
}

--------------------------------------------------------------------------------
EDIT 2 — frontend/src/hooks/api/use-auto-research-api.ts (lines 21 and 75)
--------------------------------------------------------------------------------
current:

export function useAutoResearch() {
  return useQuery<AutoResearchConfig>({
    queryKey: ["autoResearch"],
    queryFn: () => apiFetch<AutoResearchConfig>("/config/auto-research"),
  })
}

replacement:

export function useAutoResearch(options?: { enabled?: boolean }) {
  return useQuery<AutoResearchConfig>({
    queryKey: ["autoResearch"],
    queryFn: () => apiFetch<AutoResearchConfig>("/config/auto-research"),
    enabled: options?.enabled ?? true,
  })
}

current:

export function useResearchRuns() {
  return useQuery<ResearchRunList>({
    queryKey: ["autoResearch", "runs"],
    queryFn: () => apiFetch<ResearchRunList>("/config/auto-research/runs"),
  })
}

replacement:

export function useResearchRuns(options?: { enabled?: boolean }) {
  return useQuery<ResearchRunList>({
    queryKey: ["autoResearch", "runs"],
    queryFn: () => apiFetch<ResearchRunList>("/config/auto-research/runs"),
    enabled: options?.enabled ?? true,
  })
}

--------------------------------------------------------------------------------
EDIT 3 — frontend/src/hooks/api/use-llm-providers-api.ts (line 60)
--------------------------------------------------------------------------------
current:

export function useLlmProviders() {
  return useQuery<LlmProvidersResponse>({
    queryKey: ["llmProviders"],
    queryFn: () => apiFetch<LlmProvidersResponse>("/config/llm-providers"),
  })
}

replacement:

export function useLlmProviders(options?: { enabled?: boolean }) {
  return useQuery<LlmProvidersResponse>({
    queryKey: ["llmProviders"],
    queryFn: () => apiFetch<LlmProvidersResponse>("/config/llm-providers"),
    enabled: options?.enabled ?? true,
  })
}

--------------------------------------------------------------------------------
EDIT 4 — frontend/src/features/settings/components/research-tab.tsx
--------------------------------------------------------------------------------
current (import block, line 8):

import { HelpTip } from "@/components/darkmem"

replacement:

import { HelpTip } from "@/components/darkmem"
import { DEMO } from "@/lib/demo-flag"

current (inside ResearchTab, lines 41-43):

  const config = useAutoResearch()
  const update = useUpdateAutoResearch()
  const runs = useResearchRuns()

replacement:

  const config = useAutoResearch({ enabled: !DEMO })
  const update = useUpdateAutoResearch()
  const runs = useResearchRuns({ enabled: !DEMO })

--------------------------------------------------------------------------------
EDIT 5 — frontend/src/features/settings/components/providers-panel.tsx
--------------------------------------------------------------------------------
current (import block, line 6):

import { EmptyState, IconSegmented } from "@/components/darkmem"

replacement:

import { EmptyState, IconSegmented } from "@/components/darkmem"
import { DEMO } from "@/lib/demo-flag"

current (line 19):

  const { data, isLoading } = useLlmProviders()

replacement:

  const { data, isLoading } = useLlmProviders({ enabled: !DEMO })

--------------------------------------------------------------------------------
EDIT 6 — frontend/src/features/settings/use-flags-tab-binding.ts
Four separate hunks.
--------------------------------------------------------------------------------
6a) the FlagsTabBinding interface (lines 196-208).

current:

  isSaving: (key: string) => boolean
  allowlistPatterns: string[]
  overridesWritten: number
  isLoading: boolean
  /** One `feature_flags` write for a whole section's edits. Every control on
   *  this tab that lives in that row goes through here, so a card with six
   *  changed fields costs one request rather than six. */
  saveFlags: (section: SectionKey, patch: Record<string, unknown>) => void
  /** One `verification_ladder` write. `null` clears a threshold back to its
   *  floor. The response is the resolver's report, so a clamped save reports
   *  the clamp rather than echoing the number back. */
  saveLadder: (patch: Record<string, number | null>) => void
  saveAllowlist: (patterns: string[]) => void

replacement:

  isSaving: (key: string) => boolean
  /** The message the API refused a section's last save with, keyed the way
   *  `isSaving` is. Undefined once that section is saved again. */
  saveError: (key: string) => string | undefined
  allowlistPatterns: string[]
  overridesWritten: number
  isLoading: boolean
  /** One `feature_flags` write for a whole section's edits. Every control on
   *  this tab that lives in that row goes through here, so a card with six
   *  changed fields costs one request rather than six. Resolves false on a
   *  refused write, so the editor can keep the edits rather than discard
   *  them. */
  saveFlags: (
    section: SectionKey,
    patch: Record<string, unknown>,
  ) => Promise<boolean>
  /** One `verification_ladder` write. `null` clears a threshold back to its
   *  floor. The response is the resolver's report, so a clamped save reports
   *  the clamp rather than echoing the number back. */
  saveLadder: (patch: Record<string, number | null>) => Promise<boolean>
  saveAllowlist: (patterns: string[]) => Promise<boolean>

6b) `track` (lines 260-285). THIS IS THE F11 FIX.

current:

  const track = useCallback(
    (key: string, run: () => Promise<unknown>) => {
      setInFlight((keys) => [...keys, key])
      // The catch is required, not defensive: `mutateAsync` rejects on a failed
      // write and an unhandled rejection would take the page down over a
      // settings save. The error surface is the mutation's own; this only has
      // to stop the spinner.
      void run()
        .catch(() => {})
        .finally(() =>
          setInFlight((keys) => {
            const at = keys.indexOf(key)
            return at < 0 ? keys : [...keys.slice(0, at), ...keys.slice(at + 1)]
          }),
        )
    },
    [],
  )

  const flagsQuery = useFeatureFlags(!DEMO)
  const updateFlags = useUpdateFeatureFlags()
  const allowlistQuery = useRepoAllowlist(!DEMO)
  const updateAllowlist = useUpdateRepoAllowlist()
  const ladderQuery = useVerificationLadder(!DEMO)
  const updateLadder = useUpdateVerificationLadder()
  const areasQuery = useClassificationAreas()

replacement:

  const [errors, setErrors] = useState<Readonly<Record<string, string>>>({})
  const saveError = useCallback((key: string) => errors[key], [errors])
  const track = useCallback(
    (key: string, run: () => Promise<unknown>): Promise<boolean> => {
      setInFlight((keys) => [...keys, key])
      setErrors((current) => {
        if (!(key in current)) return current
        const { [key]: _cleared, ...rest } = current
        return rest
      })
      // Resolved rather than rethrown: `mutateAsync` rejects on a failed write
      // and an unhandled rejection would take the page down over a settings
      // save. The caller reads the boolean and the message off `saveError`.
      return run()
        .then(() => true)
        .catch((error: unknown) => {
          setErrors((current) => ({
            ...current,
            [key]: error instanceof Error ? error.message : String(error),
          }))
          return false
        })
        .finally(() =>
          setInFlight((keys) => {
            const at = keys.indexOf(key)
            return at < 0 ? keys : [...keys.slice(0, at), ...keys.slice(at + 1)]
          }),
        )
    },
    [],
  )

  const flagsQuery = useFeatureFlags(!DEMO)
  const updateFlags = useUpdateFeatureFlags()
  const allowlistQuery = useRepoAllowlist(!DEMO)
  const updateAllowlist = useUpdateRepoAllowlist()
  const ladderQuery = useVerificationLadder(!DEMO)
  const updateLadder = useUpdateVerificationLadder()
  const areasQuery = useClassificationAreas({ enabled: !DEMO })

(the last line is the F15 fix.)

6c) the DEMO early-return branch. Two hunks inside it.

current (line 305):

      isSaving: () => false,
      allowlistPatterns: demoFlags.repo_allowlist.patterns,

replacement:

      isSaving: () => false,
      saveError: () => undefined,
      allowlistPatterns: demoFlags.repo_allowlist.patterns,

current (lines 324-336, the tail of the demo save functions):

            } else {
              saveDemoArm(key, value)
            }
          }
        }
      },
      saveLadder: (patch) => {
        for (const [name, committed] of Object.entries(patch)) {
          saveDemoCorroboration(name, committed)
        }
      },
      saveAllowlist: saveDemoAllowlist,

replacement:

            } else {
              saveDemoArm(key, value)
            }
          }
        }
        return Promise.resolve(true)
      },
      saveLadder: (patch) => {
        for (const [name, committed] of Object.entries(patch)) {
          saveDemoCorroboration(name, committed)
        }
        return Promise.resolve(true)
      },
      saveAllowlist: (patterns) => {
        saveDemoAllowlist(patterns)
        return Promise.resolve(true)
      },

6d) the real-mode return object (lines 483-501).

current:

    isSaving,
    allowlistPatterns: allowlistQuery.data?.patterns ?? [],

replacement:

    isSaving,
    saveError,
    allowlistPatterns: allowlistQuery.data?.patterns ?? [],

current:

      track(section, () =>
        updateFlags.mutateAsync(patch as Partial<FeatureFlags>),
      )
    },
    saveLadder: (patch) => {
      track(SECTIONS.ladder, () => updateLadder.mutateAsync(patch))
    },
    saveAllowlist: (patterns) => {
      track(SECTIONS.allowlist, () => updateAllowlist.mutateAsync(patterns))
    },

replacement:

      return track(section, () =>
        updateFlags.mutateAsync(patch as Partial<FeatureFlags>),
      )
    },
    saveLadder: (patch) =>
      track(SECTIONS.ladder, () => updateLadder.mutateAsync(patch)),
    saveAllowlist: (patterns) =>
      track(SECTIONS.allowlist, () => updateAllowlist.mutateAsync(patterns)),

--------------------------------------------------------------------------------
EDIT 7 — frontend/src/features/settings/components/flags-tab.tsx
Six hunks: the shared dialog shell, then the five dialogs that use it.
--------------------------------------------------------------------------------
7a) SectionDialog's signature (lines 84-103).

current:

function SectionDialog({
  title,
  description,
  dirty,
  saving,
  canSave = true,
  onOpenChange,
  onSave,
  children,
}: {
  title: string
  description: string
  /** Field names this save will write, in display order. */
  dirty: string[]
  saving: boolean
  canSave?: boolean
  onOpenChange: (open: boolean) => void
  onSave: () => void
  children: ReactNode
}) {

replacement:

function SectionDialog({
  title,
  description,
  dirty,
  saving,
  error,
  canSave = true,
  onOpenChange,
  onSave,
  children,
}: {
  title: string
  description: string
  /** Field names this save will write, in display order. */
  dirty: string[]
  saving: boolean
  /** What the API refused the last save with. */
  error?: string
  canSave?: boolean
  onOpenChange: (open: boolean) => void
  /** Resolves false when the write was refused, which is what keeps the
   *  dialog — and the operator's only copy of the edits — open. */
  onSave: () => Promise<boolean>
  children: ReactNode
}) {

7b) SectionDialog's body — render the message.

current:

        <div className="flex flex-col gap-2">{children}</div>
        <div className="border-border flex flex-wrap items-center gap-2 border-t pt-3">

replacement:

        <div className="flex flex-col gap-2">{children}</div>
        {error && (
          <p role="alert" className="text-destructive text-sm">
            Not saved — {error}
          </p>
        )}
        <div className="border-border flex flex-wrap items-center gap-2 border-t pt-3">

7c) SectionDialog's Save button — close only on success.

current:

            disabled={dirty.length === 0 || !canSave || saving}
            onClick={onSave}
          >

replacement:

            disabled={dirty.length === 0 || !canSave || saving}
            onClick={() => {
              void onSave().then((saved) => {
                if (saved) onOpenChange(false)
              })
            }}
          >

7d) AllowlistDialog (around line 622).

current:

      dirty={dirty}
      saving={saving}
      onOpenChange={onOpenChange}
      onSave={() => {
        binding.saveAllowlist(patterns)
        onOpenChange(false)
      }}
    >

replacement:

      dirty={dirty}
      saving={saving}
      error={binding.saveError(SECTIONS.allowlist)}
      onOpenChange={onOpenChange}
      onSave={() => binding.saveAllowlist(patterns)}
    >

7e) LadderDialog (around line 768).

current:

      dirty={dirty}
      saving={saving}
      onOpenChange={onOpenChange}
      onSave={() => {
        binding.saveLadder(
          Object.fromEntries(dirty.map((name) => [name, draft[name] ?? null])),
        )
        onOpenChange(false)
      }}
    >

replacement:

      dirty={dirty}
      saving={saving}
      error={binding.saveError(SECTIONS.ladder)}
      onOpenChange={onOpenChange}
      onSave={() =>
        binding.saveLadder(
          Object.fromEntries(dirty.map((name) => [name, draft[name] ?? null])),
        )
      }
    >

7f) ClassificationDialog (around line 1035).

current:

      dirty={dirty}
      saving={saving}
      onOpenChange={onOpenChange}
      onSave={() => {
        const patch: Record<string, unknown> = {}
        if (dirty.includes("classification_mode")) {
          patch.classification_mode = mode
        }
        if (dirty.includes("classification_areas")) {
          patch.classification_areas = areas
        }
        binding.saveFlags(SECTIONS.classification, patch)
        onOpenChange(false)
      }}
    >

replacement:

      dirty={dirty}
      saving={saving}
      error={binding.saveError(SECTIONS.classification)}
      onOpenChange={onOpenChange}
      onSave={() => {
        const patch: Record<string, unknown> = {}
        if (dirty.includes("classification_mode")) {
          patch.classification_mode = mode
        }
        if (dirty.includes("classification_areas")) {
          patch.classification_areas = areas
        }
        return binding.saveFlags(SECTIONS.classification, patch)
      }}
    >

7g) FlagsSectionDialog (around line 1163).

current:

      dirty={dirty}
      saving={binding.isSaving(section)}
      onOpenChange={onOpenChange}
      onSave={() => {
        binding.saveFlags(
          section,
          Object.fromEntries(dirty.map((k) => [k, draft[k]])),
        )
        onOpenChange(false)
      }}
    >

replacement:

      dirty={dirty}
      saving={binding.isSaving(section)}
      error={binding.saveError(section)}
      onOpenChange={onOpenChange}
      onSave={() =>
        binding.saveFlags(
          section,
          Object.fromEntries(dirty.map((k) => [k, draft[k]])),
        )
      }
    >

7h) GraphDialog (around line 1228).

current:

      dirty={dirty}
      saving={binding.isSaving(SECTIONS.graph)}
      onOpenChange={onOpenChange}
      onSave={() => {
        binding.saveFlags(
          SECTIONS.graph,
          Object.fromEntries(dirty.map((k) => [k, draft[k]])),
        )
        onOpenChange(false)
      }}
    >

replacement:

      dirty={dirty}
      saving={binding.isSaving(SECTIONS.graph)}
      error={binding.saveError(SECTIONS.graph)}
      onOpenChange={onOpenChange}
      onSave={() =>
        binding.saveFlags(
          SECTIONS.graph,
          Object.fromEntries(dirty.map((k) => [k, draft[k]])),
        )
      }
    >

--------------------------------------------------------------------------------
EDIT 8 — frontend/src/features/settings/__tests__/settings-flags.real.test.tsx
MANDATORY, and the failure mode if you skip it is baffling. `act(cb)` inspects
what `cb` returns: now that `saveFlags` resolves a boolean, an expression-bodied
arrow hands `act` a thenable, which silently switches it to async mode. Nothing
warns; instead the NEXT FOUR tests in the file die with
`TypeError: Cannot read properties of null (reading 'isLoading')` and an empty
DOM, because React's act queue is left open.
--------------------------------------------------------------------------------
current (line 446):

    act(() => result.current.saveFlags("arms", { w_heat: 0.5 }))

replacement:

    // Braces, not an expression body: `saveFlags` resolves to whether the
    // write landed, and returning that thenable puts `act` into async mode.
    act(() => {
      result.current.saveFlags("arms", { w_heat: 0.5 })
    })

current (lines 476-480):

    act(() =>
      result.current.saveFlags("classification", {
        classification_mode: "expanded",
      }),
    )

replacement:

    act(() => {
      result.current.saveFlags("classification", {
        classification_mode: "expanded",
      })
    })

--------------------------------------------------------------------------------
EDIT 9 — frontend/src/features/settings/__tests__/settings-flags.test.tsx
One demo test asserted on the read-only card immediately after Save. The dialog
now closes on a settled save (one microtask later in demo mode), so for that tick
its own area checkboxes carry the same "Technical" label and `getByText` finds two.
--------------------------------------------------------------------------------
current (line 2):

import { fireEvent, render, screen, within } from "@testing-library/react"

replacement:

import {
  fireEvent,
  render,
  screen,
  waitFor,
  within,
} from "@testing-library/react"

current (around line 405):

  it("brings the areas back in expanded mode", () => {
    renderTab()
    openEditor("classification")
    switchToExpanded()
    saveEditor()
    // The read-only card now lists the enabled areas and what each contributes.
    expect(screen.getByText("Technical")).toBeInTheDocument()
  })

replacement:

  it("brings the areas back in expanded mode", async () => {
    renderTab()
    openEditor("classification")
    switchToExpanded()
    saveEditor()
    // The dialog closes on a *settled* save, so it is still up for a tick —
    // and while it is, its own area checkboxes carry these names too.
    await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull())
    // The read-only card now lists the enabled areas and what each contributes.
    expect(screen.getByText("Technical")).toBeInTheDocument()
  })

- [ ] **Step 4: Run the same command and confirm it passes**

cd /root/repositories/darkmem/frontend && npx vitest run src/features/settings/__tests__/settings-flags.demo.test.tsx src/features/settings/__tests__/settings-flags-save-error.real.test.tsx

 Test Files  2 passed (2)
      Tests  4 passed (4)

I ran the full change end to end on this checkout. `npx vitest run` over the whole
frontend gives `Test Files 160 passed (160) / Tests 1237 passed (1237)` and
`npx tsc -b` exits 0.

- [ ] **Step 5: Run the surrounding suite for regressions**

Three real risks, all measured on this checkout rather than guessed.

1. The `act()` trap (highest risk, and it bites silently). Changing `saveFlags` /
   `saveLadder` / `saveAllowlist` from `void` to `Promise<boolean>` means any
   existing `act(() => binding.saveX(...))` written with an expression body now
   returns a thenable to `act`, which switches it into async mode. React does not
   warn. What you see instead is the NEXT tests in that file failing with
   `TypeError: Cannot read properties of null (reading 'isLoading')` against an
   empty `<div />`. I hit exactly this: two call sites in
   `settings-flags.real.test.tsx` broke four later tests in the same file. Edit 8
   is the fix. If any new caller of these three functions appears while this task
   is in flight, check it for the same shape.

2. Dialogs now close on a settled save instead of synchronously. Any test that
   asserts on the read-only card immediately after clicking Save may now match
   both the card and the still-open dialog. One existing test did
   (`settings-flags.test.tsx` → "brings the areas back in expanded mode"); Edit 9
   fixes it. In the browser the difference is one animation frame on success and
   is not perceptible.

3. Demo-mode rendering of the two sibling surfaces changes, deliberately.
   `ResearchTab` now shows its meta as "reading…" forever in demo mode, because
   `config.data` stays undefined with the query disabled; `ProvidersPanel` renders
   its empty state. Both are strictly better than today's behaviour (a 401 that
   navigates the whole demo to /login), but they are visible and a demo reviewer
   may report them. See `needs_decision`.

Existing tests that cover the surrounding behaviour and must stay green:
  frontend/src/features/settings/__tests__/settings-flags.real.test.tsx (20 tests —
    the in-flight/spinner contract, the one-request-per-section PUT bodies, the
    ladder committed/effective split)
  frontend/src/features/settings/__tests__/settings-flags.test.tsx (the whole demo
    rendering of the tab, including every Save-writes-to-the-store case)
  frontend/src/features/settings/__tests__/settings-research.real.test.tsx
  frontend/src/features/settings/__tests__/settings-providers.real.test.tsx
  frontend/src/features/settings/__tests__/settings-llm.real.test.tsx,
    settings-llm.test.tsx, settings-llm-load.real.test.tsx (they render the LLM tab,
    which owns ProvidersPanel)
Run the whole settings directory at minimum:
  cd frontend && npx vitest run src/features/settings/__tests__/
and then `npx tsc -b` — the binding's exported interface changed, so a stale
consumer is a compile error rather than a silent break.

Backend: untouched, no schema contact, no `0001_baseline.py` contact.

DEPLOY: this changes `frontend/`, so it alters the running artifact. Per CLAUDE.md
the host must be redeployed after it lands: ./scripts/gate.sh →
DARKMEM_PUSH=0 ./scripts/build-push.sh → docker compose up -d → wait for healthy →
confirm the new bits are in the image, not only in the tree.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/features/settings/__tests__/settings-flags-save-error.real.test.tsx frontend/src/features/settings/__tests__/settings-flags.demo.test.tsx frontend/src/features/settings/__tests__/settings-flags.real.test.tsx frontend/src/features/settings/__tests__/settings-flags.test.tsx frontend/src/features/settings/components/flags-tab.tsx frontend/src/features/settings/components/providers-panel.tsx frontend/src/features/settings/components/research-tab.tsx frontend/src/features/settings/use-flags-tab-binding.ts frontend/src/hooks/api/use-auto-research-api.ts frontend/src/hooks/api/use-config-api.ts frontend/src/hooks/api/use-llm-providers-api.ts
git commit -m "fix(settings): show save errors, gate demo reads

The Flags tab swallowed every failed write: `track` caught the rejection
with an empty handler on the grounds that "the error surface is the
mutation's own", and no such surface existed — the three mutations declare
no `onError`, the QueryClient sets no global handler, and every section
dialog closed itself unconditionally on Save. A 422 from a value the
control accepts (w_heat is bounded ge=0/le=5) closed the dialog, stopped
the spinner, discarded every other field that one request carried, and
repainted the old values on the next refetch.

`track` now resolves to whether the write landed and records the refusal
per section; `SectionDialog` renders it and closes only on success, so the
edits survive a refusal.

Separately, `useClassificationAreas` was called unconditionally one line
above the `if (DEMO)` return and accepted no `enabled` option, so opening
Settings on a demo build — Flags is the default tab — issued a request that
401s, and `handleUnauthorized` navigated the whole page to /login. The same
omission sat on `useAutoResearch`, `useResearchRuns` and `useLlmProviders`.
All four now take the `enabled` option `useSystemPrompts` and
`useNotifications` already had, and their Settings call sites pass `!DEMO`.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_018XiqGjAhaYmvPyZ88AhUnR"
```

### Task 5: Render a failed article read as a failure, not an empty library

**Effort:** ~30 minutes.

**Files:**
- Modify: `frontend/src/features/knowledge/components/articles-tab.tsx:3-3`
- Modify: `frontend/src/features/knowledge/components/articles-tab.tsx:215-215`
- Modify: `frontend/src/features/knowledge/components/articles-tab.tsx:241-245`
- Modify: `frontend/src/features/knowledge/components/articles-tab.tsx:262-267`
- Modify: `frontend/src/features/knowledge/__tests__/articles-tab.real.test.tsx:170-192`
- Test: `frontend/src/features/knowledge/__tests__/articles-tab.real.test.tsx`

**Interfaces:**
- Consumes: nothing from another task in this plan.
- Produces: no new exported symbol — this task changes behaviour inside an existing function.

- [ ] **Step 1: Write the failing test**

Paste both cases at the end of the existing `describe("ArticlesTab on live data", ...)` block in
frontend/src/features/knowledge/__tests__/articles-tab.real.test.tsx — i.e. immediately after the
existing `it("never reaches the demo fixture", ...)` case and before that describe's closing `})`.

No new imports are needed: the file already imports `describe, it, expect, vi, beforeEach` from
vitest, `render, screen, waitFor` from @testing-library/react, `apiFetch` from "@/lib/api", and
already defines `wrapper` and the `beforeEach` that calls `vi.mocked(apiFetch).mockReset()`.

```tsx
  it("renders a failed read as a failure, never as an empty library", async () => {
    // Invariant 14: "no articles" and "we could not tell you" are different
    // sentences, and collapsing them is how a broken surface looks healthy.
    vi.mocked(apiFetch).mockRejectedValue(new Error("boom"))

    render(<ArticlesTab />, { wrapper })

    await screen.findByText("Could not load articles")
    expect(screen.queryByText("No articles yet")).not.toBeInTheDocument()
    expect(
      screen.queryByText(/nothing is being withheld from you here/i),
    ).not.toBeInTheDocument()
    expect(screen.getByText("count unavailable")).toBeInTheDocument()
  })

  it("does not claim the library is empty while the read is in flight", async () => {
    let release: (value: unknown) => void = () => {}
    vi.mocked(apiFetch).mockReturnValue(
      new Promise((resolve) => {
        release = resolve
      }) as never,
    )

    render(<ArticlesTab />, { wrapper })

    expect(screen.queryByText("No articles yet")).not.toBeInTheDocument()
    expect(
      screen.getByRole("status", { name: "Loading articles" }),
    ).toBeInTheDocument()

    release({ items: [], total: 0, limit: 50, offset: 0 })
    expect(await screen.findByText("No articles yet")).toBeInTheDocument()
  })
```

- [ ] **Step 2: Run it and confirm it fails for the right reason**

Run:

```bash
cd /root/repositories/darkmem/frontend && npx vitest run src/features/knowledge/__tests__/articles-tab.real.test.tsx
```

Expected — this is what the run actually printed on master:

Both new cases fail; the ten pre-existing cases in the file still pass. Verified by running them
against the unmodified component:

```
 FAIL  src/features/knowledge/__tests__/articles-tab.real.test.tsx > ArticlesTab on live data > renders a failed read as a failure, never as an empty library
TestingLibraryElementError: Unable to find an element with the text: Could not load articles.
  ... the printed DOM contains  <h3 class="dr-empty-state-title">No articles yet</h3>
  and  <p class="dr-empty-state-description">No articles have been synthesised for this
  project yet. ... nothing is being withheld from you here.</p>
 ❯ src/features/knowledge/__tests__/articles-tab.real.test.tsx (the `await screen.findByText` line)

 FAIL  src/features/knowledge/__tests__/articles-tab.real.test.tsx > ArticlesTab on live data > does not claim the library is empty while the read is in flight
Error: expect(element).not.toBeInTheDocument()
expected document not to contain element, found <h3 class="dr-empty-state-title">
  No articles yet
</h3> instead

 Test Files  1 failed (1)
      Tests  2 failed | 10 passed (12)
```

The first fails on a 1000ms `findByText` timeout because no failure branch exists at all; the
second fails synchronously on the very first render, because the cold-start EmptyState is what the
component paints while the request is still pending.

- [ ] **Step 3: Apply the fix**

Single file: `frontend/src/features/knowledge/components/articles-tab.tsx`. Four edits. All four
were applied and verified locally (`npx vitest run` green on the file, `npx tsc -b` exit 0), then
reverted so this plan is the thing that lands.

--- EDIT 1 of 4 — add the Skeleton import (top of file, after line 3) ---

CURRENT (lines 1-4):
```tsx
import { useMemo, useState } from "react"
import { Link } from "@tanstack/react-router"
import { GitBranch, FileText } from "lucide-react"
import {
```

REPLACEMENT:
```tsx
import { useMemo, useState } from "react"
import { Link } from "@tanstack/react-router"
import { GitBranch, FileText } from "lucide-react"
import { Skeleton } from "darkraise-ui/components/skeleton"
import {
```

(That is the same import path `facts-tab.tsx:4` already uses; no new dependency.)

--- EDIT 2 of 4 — derive the two read states (inside `ArticlesTab`, at line 215) ---

CURRENT (line 215, the line just above the `return (`):
```tsx
  const projectLabel = project === "all" ? "all projects" : project
```

REPLACEMENT:
```tsx
  const projectLabel = project === "all" ? "all projects" : project
  const loading = !DEMO && live.isLoading
  const failed = !DEMO && live.isError
```

(The `!DEMO` guards are belt-and-braces: `useArticles` is passed `{ enabled: !DEMO }`, so in demo
mode the query is disabled and both flags are already false. Keeping them explicit means the demo
branch cannot start rendering a skeleton if the enable condition is ever loosened.)

--- EDIT 3 of 4 — stop the header asserting a count it does not have (lines 241-245) ---

CURRENT:
```tsx
      <ListSurface
        title={`Articles — project: ${projectLabel}`}
        populated={shown.length > 0}
        meta={`${shown.length} ${shown.length === 1 ? "subject" : "subjects"}`}
      >
```

REPLACEMENT:
```tsx
      <ListSurface
        title={`Articles — project: ${projectLabel}`}
        populated={shown.length > 0}
        meta={
          failed
            ? "count unavailable"
            : loading
              ? "reading…"
              : `${shown.length} ${shown.length === 1 ? "subject" : "subjects"}`
        }
      >
```

(Verbatim the two strings `facts-tab.tsx:247-249` already uses for the same two states. The
ellipsis in "reading…" is U+2026, matching facts-tab.)

--- EDIT 4 of 4 — branch before the empty state (lines 262-267) ---

CURRENT:
```tsx
        {shown.length > 0 ? (
          shown.map((article) => (
            <ArticleRow key={article.id} article={article} />
          ))
        ) : (
          <EmptyState
            kind="empty"
```

REPLACEMENT:
```tsx
        {shown.length > 0 ? (
          shown.map((article) => (
            <ArticleRow key={article.id} article={article} />
          ))
        ) : loading ? (
          // A pending read is not an absence. Skeleton rows in the shape of
          // the list that is coming, so the surface never claims the library
          // is bare while it is still being read.
          <div
            className="flex flex-col gap-2 py-2"
            role="status"
            aria-label="Loading articles"
          >
            {Array.from({ length: 3 }, (_, i) => (
              <Skeleton key={i} className="h-16 w-full rounded-md" />
            ))}
          </div>
        ) : failed ? (
          // Invariant 14: a failed read is never rendered as an empty library.
          // "No articles" and "we could not tell you" are different sentences,
          // and collapsing them is how a broken surface looks healthy.
          <EmptyState
            kind="failed"
            title="Could not load articles"
            description="The library did not answer. This is a failed read, not an empty library — nothing here says how many articles exist."
          />
        ) : (
          <EmptyState
            kind="empty"
```

Everything below (`icon={FileText}`, `title="No articles yet"`, the three-way `description`, the
closing `/>` and `)}`) stays exactly as it is. The ordering — rows, then loading, then failed,
then empty — mirrors `facts-tab.tsx:371-443`.

Two notes on the choices, so they are not second-guessed later:

* `kind="failed"` (not `kind="filtered"`). `components/darkmem/empty-state.tsx:21` defines `failed`
  as "the request errored — never render this as an absence", and it is what
  `settings/components/notifications-tab.tsx:60`, `usage/components/outliers-panel.tsx:272` and
  `usage/components/usage-page.tsx:47` all use. FactsTab's own error branch uses `filtered`, which
  is a separate, pre-existing inconsistency — see regression_risk.
* Three skeleton rows rather than FactsTab's five: this list is not virtualized and its rows are
  shorter, so three fills the card without pushing the fold.


- [ ] **Step 4: Run the same command and confirm it passes**

```
 RUN  v4.1.7 /root/repositories/darkmem/frontend

 Test Files  1 passed (1)
      Tests  12 passed (12)
```

And `cd /root/repositories/darkmem/frontend && npx tsc -b` exits 0 with no output. Both were
confirmed against the applied patch before it was reverted.

- [ ] **Step 5: Run the surrounding suite for regressions**

Contained: one presentational component, two added render branches, no data flow or API change.

What could break, and why it does not:

* **Demo mode.** `ArticlesTab` is the demo Articles surface too. Both new branches are gated on
  `!DEMO`, and `useArticles` is already passed `{ enabled: !DEMO }`, so in demo mode `isLoading`
  and `isError` are both false regardless. No new network call is introduced, so the
  "demo mode must make no API calls" rule is untouched.
* **Project switching.** `useArticles` sets `placeholderData: keepPreviousData`, so switching the
  project scope keeps the previous rows on screen and `isLoading` stays false — the new skeleton
  branch does not flash between scopes. It only renders on the very first read of a query key.
* **The `populated` chip in the card header still reads `shown.length > 0`,** so on a failed read
  the header shows "empty" beside "count unavailable". That is exactly what FactsTab does today
  (`facts-tab.tsx:368`); changing it is a separate decision about `ListSurface`'s vocabulary and is
  deliberately out of scope here.

Existing tests that cover the surrounding behaviour, all of which must stay green:

* `frontend/src/features/knowledge/__tests__/articles-tab.real.test.tsx` — the ten existing cases,
  in particular "says the corpus is empty rather than claiming the feature is unshipped" (the
  genuine cold start must still reach the `kind="empty"` state) and "does not say nothing is
  withheld while counting withheld articles" (the all-in-review copy must still win over the
  cold-start copy). Both were re-run against the patched component and pass.
* `frontend/src/features/knowledge/__tests__/facts-tab.render.test.tsx` — the same
  rows/loading/error/empty ordering on the Facts tab; unmodified by this change, but it is the
  reference implementation being mirrored.
* `frontend/src/components/darkmem/__tests__/empty-state.test.tsx` — pins that `kind="failed"`
  refuses an `icon` prop (a type error), which is why the new state passes no icon.
* `npx tsc -b` from `frontend/` — catches the `EmptyStateProps` union violation if someone later
  adds an icon to the failed state.

Adjacent finding, surfaced rather than fixed: `facts-tab.tsx:434-439` renders its own failed read
with `kind="filtered"` (the blue SearchX "a query excluded everything" mark) where the house
convention for an errored request is `kind="failed"` (the destructive-toned CircleAlert), as used
by notifications-tab, outliers-panel, usage-page, real-wiki-view and system-prompt-dialog. The copy
there is honest; only the mark and colour are wrong, so it reads as a filter result rather than an
error. It is a one-word change but it touches a file this task does not otherwise open, and
`facts-tab.render.test.tsx` asserts the title text rather than the kind, so nothing would catch a
mistake there — left for its own commit.

Deployment: this changes `frontend/`, so it alters the running artifact. Per CLAUDE.md the host
must be redeployed after it lands — `./scripts/gate.sh` → `DARKMEM_PUSH=0 ./scripts/build-push.sh`
→ `docker compose up -d` → wait for `healthy`, then confirm the new string is in the built bundle
(e.g. `docker exec darkmem-prod-darkmem-1 grep -rl "Could not load articles" /app/static/assets`),
because compose reuses an image whose tag did not move.

No backend, no migration, no schema baseline contact.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/features/knowledge/__tests__/articles-tab.real.test.tsx frontend/src/features/knowledge/components/articles-tab.tsx
git commit -m "fix(knowledge): surface failed article reads"
```

### Task 6: Mount the edit-repository dialog fresh per repository

**Effort:** ~25 minutes.

**Files:**
- Modify: `frontend/src/features/code/components/real-repositories-view.tsx:197-215`
- Modify: `frontend/src/features/code/components/real-repositories-view.tsx:239-242`
- Modify: `frontend/src/features/code/components/real-repositories-view.tsx:459-463`
- Test: `frontend/src/features/code/__tests__/real-repositories-view.test.tsx`

**Interfaces:**
- Consumes: nothing from another task in this plan.
- Produces: no new exported symbol — this task changes behaviour inside an existing function.

**Owner decision this task carries** (answer before starting, not during):

Adjacent bug found while reading the same function, deliberately NOT fixed here because it needs an owner call on what the field is for.

The edit form collects a required `path` field that is never sent. `editRepoSchema` (frontend/src/features/code/schemas.ts:5-10) declares `path: z.string().min(1, "Path required")`, but `RepoUpdateParams` (frontend/src/hooks/api/use-code-api.ts:60-64) has no `path` member and `EditRepoDialog`'s onSubmit never puts one in the request body. Meanwhile the field is seeded from `repo.local_path`, which is `string | null` on the wire (backend/app/schemas/code.py:37) and is NULL for every URL-cloned repo — `RepoManager.create` only sets it when the caller passed an explicit `local_path` (backend/app/services/repo_manager.py:133-148).

Consequence: for a URL-backed repository the Path box renders empty, `safeParse` fails, and onSubmit hits `if (!parsed.success) return` — Save does nothing at all, with no error, no toast and no PUT. The operator sees a dialog that simply will not save. (This is also why the test above gives both fixture repos a non-null `local_path`; without it the Save assertion would pass for the wrong reason.)

The owner needs to decide which of these it is: (a) drop the Path field from the edit dialog entirely, since the update endpoint cannot accept it; (b) keep it but make it optional in `editRepoSchema` and render it read-only; or (c) add `local_path` to the repo update contract on both the backend and `RepoUpdateParams`, which is a REST-contract change and out of scope for a UI fix.

- [ ] **Step 1: Write the failing test**

// Append this `it(...)` block as the LAST test inside the existing
// `describe("RealRepositoriesView", () => { ... })` in
// frontend/src/features/code/__tests__/real-repositories-view.test.tsx
// (i.e. paste it immediately before the file's final `})` on line 266).
// It reuses the file's existing imports, `wrapper` and `BASE_REPO`; no new
// imports are needed.

  it("opens the edit form on the repo just clicked, never a previous repo's values", async () => {
    const repos = [
      {
        ...BASE_REPO,
        id: "r1",
        name: "darkmem-backend",
        local_path: "/srv/darkmem-backend",
        default_branch: "main",
        status: "ready",
        status_message: null,
        last_indexed_commit: "aaa1111",
        last_indexed_at: "2026-07-27T09:00:00Z",
        index_debt: {
          queued: 0,
          deferred_total: 0,
          drained_total: 0,
          last_defer: null,
          last_drain: null,
        },
      },
      {
        ...BASE_REPO,
        id: "r2",
        name: "darkmem-frontend",
        local_path: "/srv/darkmem-frontend",
        default_branch: "release",
        status: "ready",
        status_message: null,
        last_indexed_commit: "bbb2222",
        last_indexed_at: "2026-07-27T09:00:00Z",
        index_debt: {
          queued: 0,
          deferred_total: 0,
          drained_total: 0,
          last_defer: null,
          last_drain: null,
        },
      },
    ]
    vi.mocked(apiFetch).mockImplementation((path: string) => {
      if (path === "/repos") return Promise.resolve(repos)
      return Promise.resolve({})
    })

    const user = userEvent.setup()
    render(<RealRepositoriesView />, { wrapper })

    await screen.findByText("darkmem-backend")
    await user.click(screen.getAllByRole("button", { name: "Edit" })[0]!)

    const first = await screen.findByRole("dialog")
    await user.type(within(first).getByLabelText("Name"), "-renamed")
    await user.click(within(first).getByRole("button", { name: "Cancel" }))
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument()

    await user.click(screen.getAllByRole("button", { name: "Edit" })[1]!)
    const second = await screen.findByRole("dialog")

    expect(within(second).getByLabelText("Name")).toHaveValue("darkmem-frontend")
    expect(within(second).getByLabelText("Branch")).toHaveValue("release")

    await user.click(within(second).getByRole("button", { name: "Save" }))

    const putCall = vi
      .mocked(apiFetch)
      .mock.calls.find(([, init]) => init?.method === "PUT")
    expect(putCall).toBeUndefined()
  })

- [ ] **Step 2: Run it and confirm it fails for the right reason**

Run:

```bash
cd /root/repositories/darkmem/frontend && npx vitest run src/features/code/__tests__/real-repositories-view.test.tsx
```

Expected — this is what the run actually printed on master:

Runs 9 tests, 8 pass, the new one fails (observed on 2026-08-24 against master's file):

 FAIL  src/features/code/__tests__/real-repositories-view.test.tsx > RealRepositoriesView > opens the edit form on the repo just clicked, never a previous repo's values
Error: expect(element).toHaveValue(darkmem-frontend)

Expected the element to have value:
  darkmem-frontend
Received:
  darkmem-backend-renamed

 Test Files  1 failed (1)
      Tests  1 failed | 8 passed (9)

The failure is the finding itself: the dialog was opened on repo "darkmem-frontend" but still renders the name typed while editing repo "darkmem-backend". (The two assertions after it — the wrong Branch, and the PUT that a "no changes" save must not issue — are never reached because the first one aborts the test.)

- [ ] **Step 3: Apply the fix**

Single file: frontend/src/features/code/components/real-repositories-view.tsx. Three edits, no new imports, no new comments.

WHY this is the fix (do not shortcut it): `useForm` from @tanstack/react-form 1.32 calls `formApi.update(opts)` in a layout effect on every render, and form-core's `update` re-applies `defaultValues` only while `!this.state.isTouched` (node_modules/@tanstack/form-core/dist/esm/FormApi.js:92). The first keystroke sets `isTouched`, so from then on the single long-lived `EditRepoDialog` instance ignores every later repo's defaults. Making the component's existence depend on a repo — and keying it by repo id — gives each edit its own FormApi, which is the only thing that reliably reseeds the fields.

--- Edit 1 of 3: line 197-215, the component signature, the form defaults and the now-impossible null check in onSubmit.

CURRENT CODE (starts at line 197):

function EditRepoDialog({
  repo,
  open,
  onOpenChange,
}: {
  repo: Repo | null
  open: boolean
  onOpenChange: (open: boolean) => void
}) {
  const updateRepo = useUpdateRepo()
  const form = useForm({
    defaultValues: {
      name: repo?.name ?? "",
      path: repo?.local_path ?? "",
      branch: repo?.default_branch ?? "main",
      auto_sync: repo?.auto_sync ?? true,
    },
    onSubmit: async ({ value }) => {
      if (!repo) return
      const parsed = editRepoSchema.safeParse(value)

REPLACEMENT:

function EditRepoDialog({
  repo,
  onOpenChange,
}: {
  repo: Repo
  onOpenChange: (open: boolean) => void
}) {
  const updateRepo = useUpdateRepo()
  const form = useForm({
    defaultValues: {
      name: repo.name,
      path: repo.local_path ?? "",
      branch: repo.default_branch,
      auto_sync: repo.auto_sync,
    },
    onSubmit: async ({ value }) => {
      const parsed = editRepoSchema.safeParse(value)

(`local_path` stays `?? ""` because `Repo.local_path` is genuinely `string | null`; `name`, `default_branch` and `auto_sync` are non-nullable on `Repo`, so their fallbacks were already dead.)

Leave the rest of the `onSubmit` body exactly as it is — the diff-computation against `repo.name` / `repo.default_branch` / `repo.auto_sync` and the `updateRepo.mutateAsync` call are unchanged.

--- Edit 2 of 3: line 239-242, drop the guard and stop threading `open`.

CURRENT CODE:

  if (!repo) return null

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>

REPLACEMENT:

  return (
    <Dialog open onOpenChange={onOpenChange}>

--- Edit 3 of 3: line 459-463, the call site inside `RealRepositoriesView`.

CURRENT CODE:

      <EditRepoDialog
        repo={editingRepo}
        open={!!editingRepo}
        onOpenChange={(o) => !o && setEditingRepo(null)}
      />

REPLACEMENT:

      {editingRepo && (
        <EditRepoDialog
          key={editingRepo.id}
          repo={editingRepo}
          onOpenChange={(o) => !o && setEditingRepo(null)}
        />
      )}

The conditional mount is what fixes the reachable bug (close then reopen). The `key` additionally guarantees a fresh form if `editingRepo` is ever swapped from one repo straight to another without passing through null.

--- Verified locally on 2026-08-24: with the three edits applied, `npx vitest run src/features/code/__tests__/real-repositories-view.test.tsx` is 9/9 green, `npx vitest run src/features/code/` is 52/52 green, and `npx tsc -b` exits 0. The working tree was then restored to master's content, so these edits still need to be applied.

NOT chosen, and why: the sibling `RealReindexDialog` resets on close (`useEffect(() => { if (!open) form.reset() }, [open, form])`, real-reindex-dialog.tsx:47-49). Copying that here works only because `form.reset()` reads `this.options.defaultValues`, which `update` refreshes on every render even when it declines to apply it — a coupling to library internals that is not obvious from the call site. Unmounting is the property, not a side effect of one.

- [ ] **Step 4: Run the same command and confirm it passes**

cd /root/repositories/darkmem/frontend && npx vitest run src/features/code/__tests__/real-repositories-view.test.tsx

 Test Files  1 passed (1)
      Tests  9 passed (9)

And the whole feature directory: `npx vitest run src/features/code/` gives

 Test Files  7 passed (7)
      Tests  52 passed (52)

Typecheck: `cd /root/repositories/darkmem/frontend && npx tsc -b` prints nothing and exits 0.

- [ ] **Step 5: Run the surrounding suite for regressions**

Low, and bounded to one dialog. `EditRepoDialog` is module-private — `rg "EditRepoDialog" frontend/src` returns only its definition and the single call site — so no other caller sees the changed prop shape, and `npx tsc -b` catches it if one is added.

Three specific things to know:

1. No visual change. Today `EditRepoDialog` already returns null before rendering `<Dialog>` whenever `repo` is null, so the Radix dialog was never mounted in the closed state and never had an exit animation. Conditional mounting reproduces exactly that lifecycle.

2. After a successful save, `onOpenChange(false)` now unmounts the component while `form.handleSubmit()` is still unwinding. The remaining work in form-core's `_handleSubmit` is store `setState` plus event emits on a detached store (checked in node_modules/@tanstack/form-core/dist/esm/FormApi.js:454-560) — no React state update on an unmounted component, no throw. The save path is exercised by the new test and by the existing "submits the reindex options the dialog collected" test's sibling flow.

3. Existing coverage for the surrounding behaviour, all in frontend/src/features/code/__tests__/real-repositories-view.test.tsx and all still green: the stale banner, the three index-debt cases, the live phase label, the auto-provision label, "submits the reindex options the dialog collected, in POST /repos/{id}/reindex's own shape" (the sibling dialog, untouched), and "issues a POST /repos with the create form's fields on Add repository" (AddRepoDialog, untouched). Nothing else in the tree renders this component.

Full-suite note so nobody blames this change: `npx vitest run` on the current working tree is already red before any of these edits — I measured 5 failures across 3 files on master's content, and a second run failed a *different* set of files (settings-flags*.test.tsx, memory-graph/detail-panel-narrow-container.test.tsx, src/test/__tests__/probe.test.ts). Each of those files passes when run alone. They are pre-existing order-dependent flakes in other lanes' in-flight work, unrelated to F13.

Deployment: this touches frontend/, so it alters the running artifact. Per CLAUDE.md this host must be redeployed after it lands — ./scripts/gate.sh, then DARKMEM_PUSH=0 ./scripts/build-push.sh, then docker compose up -d, then confirm the new bits are actually in the running image (compose reuses an image whose tag did not move). No backend, schema, migration, Dockerfile or compose change; the baseline revision is untouched.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/features/code/__tests__/real-repositories-view.test.tsx frontend/src/features/code/components/real-repositories-view.tsx
git commit -m "fix(code): mount edit-repo dialog fresh per repository

EditRepoDialog was mounted once for the lifetime of the Repositories
view, so its single TanStack FormApi kept whichever repo's values were
last typed: form-core re-applies defaultValues only while the form is
untouched, and the first keystroke clears that. Opening Edit on a second
repo then rendered the first repo's name and branch, and saving issued a
PUT that renamed the second repo and repointed its default branch.

Mount the dialog only when a repo is selected, keyed by its id, so each
edit gets its own form seeded from the repo actually being edited.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_018XiqGjAhaYmvPyZ88AhUnR"
```

### Task 7: Render chat stream errors and refetch the failed thread

**Effort:** ~30 minutes.

**Files:**
- Modify: `frontend/src/features/chat/hooks/use-chat-stream.ts:65-71`
- Modify: `frontend/src/features/chat/components/chat-input.tsx:7-25`
- Modify: `frontend/src/features/chat/components/chat-input.tsx:53-55`
- Modify: `frontend/src/features/chat/components/real-chat-page.tsx:124-128`
- Modify: `frontend/src/features/chat/components/chat-overlay.tsx:110-117`
- Create: `frontend/src/features/chat/__tests__/chat-stream-error-surface.test.tsx`
- Test: `frontend/src/features/chat/__tests__/chat-stream-error-surface.test.tsx`

**Interfaces:**
- Consumes: nothing from another task in this plan.
- Produces: no new exported symbol — this task changes behaviour inside an existing function.

**Owner decision this task carries** (answer before starting, not during):

Whether the backend's two error yields in backend/app/services/chat.py (lines 148 and 192) should also carry `conversation_id`. Without it, a turn that fails on the very first message of a brand-new thread leaves the frontend unable to name the conversation the backend just created and committed — this task's unconditional sidebar-list invalidation surfaces the thread but cannot open it. Adding the field is a two-line change but widens the chat SSE contract, so it is left for the repo owner rather than folded in here.

- [ ] **Step 1: Write the failing test**

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest"
import { render, screen, renderHook, act } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import type { ReactNode } from "react"

const mockUseConversations = vi.fn()
const mockUseConversation = vi.fn()
const mockUseCreateConversation = vi.fn()
const mockUseDeleteConversation = vi.fn()

vi.mock("@/hooks/api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/hooks/api")>()),
  useConversations: () => mockUseConversations(),
  useConversation: (id: string | null) => mockUseConversation(id),
  useCreateConversation: () => mockUseCreateConversation(),
  useDeleteConversation: () => mockUseDeleteConversation(),
}))

vi.mock("@tanstack/react-router", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@tanstack/react-router")>()),
  useNavigate: () => vi.fn(),
}))

import { RealChatPage } from "../components/real-chat-page"
import { ChatOverlay } from "../components/chat-overlay"
import { useChatStream } from "../hooks/use-chat-stream"

const STREAM_ERROR = "Stream interrupted: All connection attempts failed"

function sseStreamFromEvents(events: object[]): ReadableStream<Uint8Array> {
  const encoder = new TextEncoder()
  const body = events.map((e) => `data: ${JSON.stringify(e)}\n\n`).join("")
  return new ReadableStream({
    start(controller) {
      controller.enqueue(encoder.encode(body))
      controller.close()
    },
  })
}

function stubFailingStream() {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue({
      ok: true,
      body: sseStreamFromEvents([
        { type: "sources", memories: [], facts: [], entities: [] },
        { type: "error", message: STREAM_ERROR },
      ]),
    }),
  )
}

function wrapper({ children }: { children: ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>
}

beforeEach(() => {
  mockUseConversations.mockReset()
  mockUseConversation.mockReset()
  mockUseCreateConversation.mockReset()
  mockUseDeleteConversation.mockReset()
  mockUseConversations.mockReturnValue({
    data: { conversations: [] },
    isLoading: false,
    isError: false,
    refetch: vi.fn(),
  })
  mockUseConversation.mockReturnValue({ data: undefined })
  mockUseCreateConversation.mockReturnValue({ mutateAsync: vi.fn() })
  mockUseDeleteConversation.mockReturnValue({ mutate: vi.fn() })
})

afterEach(() => {
  vi.unstubAllGlobals()
})

// A turn that dies mid-stream clears the pending bubble and the spinner, so
// without a rendered error the user's question simply disappears from the
// pane while it is still persisted server-side.
describe("a failed chat turn says so on screen", () => {
  it("RealChatPage renders the stream's error message", async () => {
    const user = userEvent.setup()
    stubFailingStream()

    render(<RealChatPage />, { wrapper })

    await user.type(
      screen.getByPlaceholderText(/Ask about your memories/),
      "which pooler",
    )
    await user.click(screen.getByRole("button", { name: "Send message" }))

    expect(await screen.findByRole("alert")).toHaveTextContent(STREAM_ERROR)
  })

  it("ChatOverlay renders the stream's error message", async () => {
    const user = userEvent.setup()
    stubFailingStream()

    render(<ChatOverlay />, { wrapper })
    await user.click(screen.getByRole("button", { name: "Open chat panel" }))

    await user.type(
      screen.getByPlaceholderText(/Ask about selection/),
      "which pooler",
    )
    await user.click(screen.getByRole("button", { name: "Send message" }))

    expect(await screen.findByRole("alert")).toHaveTextContent(STREAM_ERROR)
  })
})

// The error event carries no conversation_id, so the id the caller passed in
// is the only handle on the thread whose user message the backend committed.
describe("a failed turn still refetches the thread it was sent to", () => {
  it("invalidates the incoming conversation id when no done event arrived", async () => {
    stubFailingStream()
    const qc = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    })
    const invalidate = vi.spyOn(qc, "invalidateQueries")

    const { result } = renderHook(() => useChatStream(), {
      wrapper: ({ children }: { children: ReactNode }) => (
        <QueryClientProvider client={qc}>{children}</QueryClientProvider>
      ),
    })

    await act(async () => {
      await result.current.sendMessage("c1", "which pooler")
    })

    expect(invalidate).toHaveBeenCalledWith({
      queryKey: ["conversation", "c1"],
    })
  })
})


- [ ] **Step 2: Run it and confirm it fails for the right reason**

Run:

```bash
cd /root/repositories/darkmem/frontend && npx vitest run src/features/chat/__tests__/chat-stream-error-surface.test.tsx
```

Expected — this is what the run actually printed on master:

All three tests fail. Verified by actually running it against unmodified master.

Summary line:
      Tests  3 failed (3)
 Test Files  1 failed (1)

The two render tests fail with:
  TestingLibraryElementError: Unable to find role="alert"
(the printed DOM shows the composer with only the textarea, the send button and the "Enter to send · Shift+Enter for new line" hint — no error row anywhere)

The third fails with:
  AssertionError: expected "invalidateQueries" to be called with arguments: [ { queryKey: [ …(2) ] } ]
  Number of calls: 0
(`refreshAfterStream` early-returns on `!resultConversationId`, so neither the detail key nor the list key is invalidated on a failed turn)

- [ ] **Step 3: Apply the fix**

Four edits, all in frontend/src/features/chat. No backend change, no schema change.

--- EDIT 1 of 4: frontend/src/features/chat/hooks/use-chat-stream.ts (lines 65-71) ---

CURRENT CODE (leave the four-line comment above it untouched):

      const refreshAfterStream = () => {
        if (!resultConversationId) return
        qc.invalidateQueries({ queryKey: ["conversation", resultConversationId] })
        // The sidebar list also shows each conversation's updated_at/message_count,
        // which change on every message — refresh it too, not only for new threads.
        qc.invalidateQueries({ queryKey: ["conversations"] })
      }

REPLACEMENT:

      const refreshAfterStream = () => {
        // Only the terminal `done` event carries a conversation_id, so a turn
        // that died mid-stream has none — but the backend committed the user's
        // message before the stream began, so the thread the caller named is
        // still the one to refetch.
        const target = resultConversationId ?? conversationId
        if (target) {
          qc.invalidateQueries({ queryKey: ["conversation", target] })
        }
        // The sidebar list also shows each conversation's updated_at/message_count,
        // which change on every message — refresh it too, not only for new threads.
        qc.invalidateQueries({ queryKey: ["conversations"] })
      }

`conversationId` is the first parameter of the enclosing `sendMessage` callback, already in scope.
Note the list invalidation is now unconditional: on a failed first turn of a BRAND-NEW thread both
ids are null, and the sidebar list is the only thing that can surface the conversation the backend
just created and committed.


--- EDIT 2 of 4: frontend/src/features/chat/components/chat-input.tsx (lines 7-25) ---

CURRENT CODE:

interface ChatInputProps {
  onSend: (message: string) => void
  onStop?: () => void
  isStreaming?: boolean
  disabled?: boolean
  placeholder?: string
  contextLabel?: string | null
  onClearContext?: () => void
}

export function ChatInput({
  onSend,
  onStop,
  isStreaming = false,
  disabled = false,
  placeholder = "Ask about your memories... (@ to mention)",
  contextLabel,
  onClearContext,
}: ChatInputProps) {

REPLACEMENT:

interface ChatInputProps {
  onSend: (message: string) => void
  onStop?: () => void
  isStreaming?: boolean
  disabled?: boolean
  placeholder?: string
  contextLabel?: string | null
  onClearContext?: () => void
  error?: string | null
}

export function ChatInput({
  onSend,
  onStop,
  isStreaming = false,
  disabled = false,
  placeholder = "Ask about your memories... (@ to mention)",
  contextLabel,
  onClearContext,
  error,
}: ChatInputProps) {


--- EDIT 3 of 4: frontend/src/features/chat/components/chat-input.tsx (lines 53-55, same file) ---

CURRENT CODE:

  return (
    <div className="border-border space-y-2 border-t p-3">
      {contextLabel && (

REPLACEMENT:

  return (
    <div className="border-border space-y-2 border-t p-3">
      {error && (
        <p
          role="alert"
          className="bg-destructive/15 text-destructive rounded-md px-3 py-2 text-sm"
        >
          {error}
        </p>
      )}
      {contextLabel && (

(The `role="alert"` + `bg-destructive/15 text-destructive rounded-md px-3 py-2 text-sm` shape is the
one already used for the login failure banner in
frontend/src/features/auth/components/login-form.tsx:92-98. darkraise-ui ships an `Alert`
component, but nothing in this repo uses it and every existing inline error is this `<p role="alert">`
— matching the house pattern keeps one look across the app.)


--- EDIT 4a of 4: frontend/src/features/chat/components/real-chat-page.tsx (lines 124-128) ---

CURRENT CODE:

            <ChatInput
              onSend={handleSend}
              onStop={stream.abort}
              isStreaming={stream.isStreaming}
            />

REPLACEMENT:

            <ChatInput
              onSend={handleSend}
              onStop={stream.abort}
              isStreaming={stream.isStreaming}
              error={stream.error}
            />


--- EDIT 4b of 4: frontend/src/features/chat/components/chat-overlay.tsx (lines 110-117) ---

CURRENT CODE:

      <ChatInput
        onSend={handleSend}
        onStop={stream.abort}
        isStreaming={stream.isStreaming}
        contextLabel={contextLabel}
        onClearContext={() => setContextLabel(null)}
        placeholder="Ask about selection..."
      />

REPLACEMENT:

      <ChatInput
        onSend={handleSend}
        onStop={stream.abort}
        isStreaming={stream.isStreaming}
        contextLabel={contextLabel}
        onClearContext={() => setContextLabel(null)}
        placeholder="Ask about selection..."
        error={stream.error}
      />


WHY THE ALERT LIVES IN ChatInput RATHER THAN IN EACH PAGE
The finding proposes "an alert row above ChatInput" in both consumers. ChatInput already owns the
strip above the textarea (that is where `contextLabel` renders) and already owns turn state
(`isStreaming`, the stop button), and it has exactly two call sites — the same two that consume
`useChatStream`. Putting the row inside it gives one implementation instead of two copies, which is
what CLAUDE.md's reuse rule asks for. The rendered result is identical to the proposal.

WHAT THIS DOES NOT FIX (deliberate scope)
The backend's error event (backend/app/services/chat.py:148 and :192) carries no `conversation_id`,
so a turn that fails on the FIRST message of a brand-new thread still cannot tell the frontend which
conversation was created. The unconditional `["conversations"]` invalidation above makes that thread
appear in the sidebar, which is as far as a frontend-only fix reaches. Adding `conversation_id` to
those two yields would be a change to the chat SSE contract; it is not required to make this finding's
failure mode visible and is left out on purpose.

- [ ] **Step 4: Run the same command and confirm it passes**

Verified by actually applying the fix and running it:

 Test Files  1 passed (1)
      Tests  3 passed (3)

Also verified after the fix:
- cd /root/repositories/darkmem/frontend && npx vitest run src/features/chat
      Tests  37 passed (37) / Test Files  7 passed (7)
- cd /root/repositories/darkmem/frontend && npx tsc -b  → exit 0, no output

- [ ] **Step 5: Run the surrounding suite for regressions**

Low, and measured rather than assumed.

1. `ChatInput` gains one optional prop with no default behaviour change: when `error` is undefined or
   null nothing renders and the DOM is byte-identical to today. The only two call sites are the two
   files edited here.

2. `refreshAfterStream` now invalidates `["conversations"]` unconditionally instead of only when a
   conversation id is known. On the SUCCESS path this is not a change at all — the `done` event always
   carries `conversation_id`, so `resultConversationId` was always set there. The behaviour only
   differs on the two failure paths (`error` event, fetch exception), where today it does nothing. Cost
   is at most one extra sidebar refetch after a failed turn.

3. `refreshAfterStream` is NOT called on the `!res.ok` and `!reader` early returns, and this task does
   not add it there. That is correct: a non-ok HTTP response means the endpoint raised before returning
   the StreamingResponse, so `send_message` never ran and no user message was committed
   (backend/app/services/chat.py:155 commits the user turn only after the generator starts). Those two
   paths still set `error`, which now renders.

4. Abort is untouched: `abort()` clears `isStreaming` and `pendingUserMessage` and never sets `error`,
   and the catch block still swallows `AbortError`, so pressing Stop shows no error banner.

Existing tests covering the surrounding behaviour, all re-run green with the fix applied:
- frontend/src/features/chat/__tests__/real-chat-page.test.tsx — the page's three-column assembly,
  the empty-pane copy, and conversation switching.
- frontend/src/features/chat/hooks/__tests__/use-chat-stream-source-fields.test.tsx — the happy-path
  SSE parse (sources + done), which is what would break if the refreshAfterStream edit were wrong.
- frontend/src/features/chat/__tests__/chat-retrieval-envelope.test.tsx and
  chat-honesty-labels.test.tsx — the context panel and badge render sites.
- frontend/src/features/chat/__tests__/demo-chat.test.tsx — the demo pane, which uses neither
  ChatInput nor useChatStream and is unaffected.

Unrelated pre-existing failure to expect: `npx vitest run src/features/memory-graph` currently has one
red test in `src/features/memory-graph/components/__tests__/detail-panel-narrow-container.test.tsx`
("close button" query). That file is untracked work-in-progress from another lane, it mocks
`ChatOverlay` to `() => null`, and it fails identically without this change. Do not attribute it here.

This change alters the running artifact (frontend/), so per CLAUDE.md the host must be redeployed after
it lands: ./scripts/gate.sh → DARKMEM_PUSH=0 ./scripts/build-push.sh → docker compose up -d, then
confirm the new bits are in the running image.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/features/chat/__tests__/chat-stream-error-surface.test.tsx frontend/src/features/chat/components/chat-input.tsx frontend/src/features/chat/components/chat-overlay.tsx frontend/src/features/chat/components/real-chat-page.tsx frontend/src/features/chat/hooks/use-chat-stream.ts
git commit -m "fix(chat): render stream errors, refetch thread"
```

---

## Finishing this plan

- [ ] `cd frontend && npx tsc -b && npx vitest run` — expect the baseline 1233 plus this plan's additions, and expect Task 1 to have moved that number if any suite was leaking an interval.
- [ ] `./scripts/gate.sh --full` from the repo root, for the Playwright arm.
- [ ] Redeploy and confirm the new SPA bundle is serving.
- [ ] Answer the four owner decisions these tasks carry (recorded in the spec's decision register) before starting the tasks that hold them.
- [ ] File the one deferred adjacent finding that this plan surfaces and does not fix: `graph-detail-panel.tsx`'s close button is an icon-only `Button` with no accessible name. It belongs in the later accessibility package, and will be lost if nobody writes it down.
