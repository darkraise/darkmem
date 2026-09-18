# UI Review Remediation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: the skill the **Execution:** line names — dr-superpowers:subagent-driven-development for `subagent`, dr-superpowers:executing-plans for `inline`. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix the 2026-09-18 UI/UX review's findings in the darkmem SPA — demo integrity, one project scope, a responsive header, accessibility, visual consistency and plain-language copy — without touching the backend.

**Architecture:** Every change is frontend-only. The header `ProjectSwitcher` becomes the single project scope (the store gains an all-projects default and a stale-scope fallback), pages read that store instead of owning a project control, and the header's controls collapse into one overflow popover below `md`. Accessibility and consistency fixes are token- and scan-driven: two contrast-safe text tokens with a source scan that forbids the old utilities, a source scan that forbids sub-12px text, and small component edits for the notes editor, graph canvases and login. Copy moves implementation detail behind the existing Simple/Advanced switch without hiding any invariant-14 honesty label.

**Tech Stack:** React 19, TypeScript, TanStack Router + Query v5, zustand 5, darkraise-ui ^6.6.0, Tailwind v4, BlockNote 0.54.2, vitest 4 + @testing-library/react, Playwright.

**Spec:** `docs/superpowers/specs/2026-09-18-ui-review-remediation-design.md`

**Execution:** inline — `claude --model sonnet --effort high` — 2 of 25 tasks are heavy (4, 13), not a majority, so they are delegated; the 6 four-band tasks (2, 5, 6, 7, 8, 9) are at most a third of the plan (3 x 6 <= 25), so they are delegated too; the highest self-implemented total is 3

**Plan review:** 2026-09-19 — dr-superpowers:judge-opus — executability 14 / coherence 13 / coverage 14 / assumptions 15 (round 1)

## Global Constraints

- **No backend change.** A task that finds it needs one stops and reports (spec "Out of scope").
- **Invariant 14** (`frontend/tests/honesty/labels-always-render.spec.ts`): verification badges, layer labels (`L0 · memory`, `L2 · fact`, …), superseded/stale labels and exclusion counts render in **both** detail modes. Nothing in this plan hides them. The exclusion *tag* (`by_context_conflict`, `by_review_state`, …) is part of that set: the honesty spec asserts it visible in both modes (`labels-always-render.spec.ts:52`), so it stays in both even where the spec lists `by_review_state` as advanced-only.
- **Rulings 3 and 4** (`components/app-chrome/context-chip.tsx`): the context chip stays visually distinct (dashed, italic when undeclared) and reads literally "not declared".
- **darkraise-ui first** (CLAUDE.md): restyle library components, never re-implement them. A local component written against a library gap records which gap in a comment.
- **Accent is user-configurable** (Appearance tab): no fix may pin `--primary` to a fixed colour. Derived tokens are computed *from* `--primary`.
- **Demo makes no API calls** (`frontend/tests/demo-makes-no-api-calls.spec.ts`). Every new query carries `enabled: !DEMO` (import `DEMO` from `@/lib/demo-flag`); demo data is served through `initialData`, never through a live `queryFn`.
- **Default detail level stays `advanced`** (`components/darkmem/use-detail-level.ts`). Advanced-only content renders when `useDetailLevel((s) => s.level) === "advanced"`.
- **Minimum text size is 12px:** no `text-[8px]` … `text-[11px]` class anywhere in `frontend/src` (Task 14 adds the scan). `text-xs` is 13px in this app (`frontend/src/styles/globals.css:27`).
- **Primary/success/warning/info colour used as text** goes through `text-primary-text` / `text-success-text` / `text-warning-text` / `text-info-text` (Task 13 adds the tokens and the scan). Buttons keep the library's own foreground pairing (`text-primary-foreground` is untouched).
- **Copy rule:** the literal phrases the spec fixes are used verbatim: "Saved project not found — showing all", "Documents open one project at a time", "Code is scoped by repository, not by project", "Page content", "Mark as done", "Mark as not done", "Expand", "Collapse", "failed".
- **Comments:** default to none; only where the WHY is non-obvious. Never reference a task, the review or a finding number.
- **English only** in code, comments, docs, commits and tests.
- **Commits:** `<type>(<scope>): <subject>`, type = feat|fix|docs|style|refactor|test|chore|perf, subject <= 50 chars, imperative, no period. Every commit message ends with `Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>` (the commit steps pass it as a second `-m`).
- **Every `git` command runs from the worktree root** `/root/repositories/darkmem/.worktrees/ui-review`, with repo-relative paths (`frontend/src/...`).
- **Frontend commands run from `frontend/`:** `npm run typecheck` (= `tsc -b`), `npx vitest run <path>`, `npm test` (= `vitest run`), `npm run build`. `npm run lint` is advisory; a task leaves no *new* lint error. **Never run prettier** on files a task does not edit (the frontend is not prettier-clean repo-wide).
- **Playwright never reaches `:8000`.** A bare `npx playwright test` proxies `/api` to the live instance. Task-level demo specs run only as `E2E_API_TARGET=http://127.0.0.1:9 timeout 900 npx playwright test --project=demo-fixture <spec>` (the dead target means no request can reach a real backend; demo specs issue none). The full e2e leg runs only through `backend/scripts/e2e/run_playwright_e2e.py` (Task 25).
- **Host hazard:** an `earlyoom` daemon kills memory-heavy runs at ~80% swap. **Exit 143 is a SIGTERM, not a failure** — check `free -h` and re-run the leg alone before believing a red.
- **Process hygiene:** every server a task starts (vite, a disposable stack, Playwright's web servers) is stopped before the task ends; Playwright stops its own `webServer` entries.
- **Deploy is not a task here.** After merge, CLAUDE.md's redeploy sequence applies (gate, `DARKMEM_PUSH=0 ./scripts/build-push.sh`, image sha equal to HEAD, `docker compose up -d`, confirm the change in `/app/web`).

## Contracts

Paths are under `frontend/src/` unless stated.

**`demo/projects.ts` (Task 2)** — `DEMO_PROJECTS: ProjectSummary[]` (from `@/hooks/api`): `darkmem` (10 memories, 12 documents, 3 checkpoints), `default` (5000 memories), `acme-storefront` (4 documents), `notes` (`kind: "personal"`, 3 pages).

**`demo/usage.ts` (Task 2)** — `DEMO_USAGE_OVERVIEW: UsageOverview`, `DEMO_USAGE_SERIES: UsageSeries`.

**`stores/project-store.ts` (Task 4)**
- `ALL_PROJECTS = null` (unchanged), `DEFAULT_PROJECT = "default"` (kept as the backend's capture default; no longer the store default), `projectLabel(scope)` (unchanged).
- State: `activeProject: ProjectScope` (initial `ALL_PROJECTS`), `missingProject: string | null` (initial `null`, not persisted), `setProject(scope)` (also clears `missingProject`), `reconcile(known: readonly string[])` — a scope absent from `known` becomes `ALL_PROJECTS` and its name moves to `missingProject`.
- `STALE_SCOPE_NOTICE = "Saved project not found — showing all"`.

**`components/app-chrome/project-switcher.tsx` (Tasks 4, 5)**
- `ProjectScopeReconciler(): null` — mounted once in the authenticated layout; calls `reconcile` with the non-personal project names once `useProjects` succeeds.
- `CODE_SCOPE_REASON = "Code is scoped by repository, not by project"`.
- `ProjectSwitcher({ disabledReason }: { disabledReason?: string })` — disabled trigger plus a tooltip when `disabledReason` is set.
- `projectScopeDisabledReason(pathname: string): string | undefined` — `CODE_SCOPE_REASON` for `/code` and `/code/*`.

**`components/app-chrome/project-chooser.tsx` (Task 8)** — `ProjectChooser({ icon, heading, description, projects, noun, emptyTitle, emptyDescription, onChoose })` with `projects: ChooserProject[]` (`{ name: string; count: number }`), `noun: { one: string; many: string }`, `onChoose: (project: string) => void`; exported from `@/components/app-chrome`. Used by `/documents` ("Documents open one project at a time") and Topics ("Topics open one project at a time").

**`components/app-chrome/header-controls.tsx` (Task 9)** — `HEADER_WIDE_QUERY = "(min-width: 768px)"`; `HeaderControls({ projectDisabledReason }: { projectDisabledReason?: string })`.

**`components/darkmem/scroll-tabs-list.tsx` (Task 10)** — `ScrollTabsList({ activeValue, className, children }: { activeValue: string; className?: string; children: ReactNode })`, exported from `@/components/darkmem`.

**`styles/globals.css` (Task 13)** — CSS custom properties `--primary-text`, `--success-text`, `--warning-text`, `--info-text`; Tailwind colours of the same names (utilities `text-primary-text`, `text-success-text`, `text-warning-text`, `text-info-text`, with opacity modifiers).

**`components/darkmem/timestamp.tsx` (Task 22)** — `Timestamp({ iso, className }: { iso: string | null | undefined; className?: string })`, exported from `@/components/darkmem`.

**`lib/format.ts` (Task 22)** — `formatList(items: readonly string[]): string` ("code and memory"); `formatWhen(iso: string): string` (relative time, or the input unchanged when it is not a date).

**`features/memories/components/memory-results-header.tsx` (Task 24)** — `MemoryResultsHeader({ scopeLabel, shown, total }: { scopeLabel: string; shown: number; total: number })`.

## Assumptions (evidence)

- **The code blocks in this plan were written against the tree at `88a961c6` and were not executed while planning.** Each task's run steps are the verification; a step whose result differs from its **Expected** line stops the task and is reported, never adapted around.
- **Unguarded demo reads** (2026-09-18, source read): `useClassificationAreas` `hooks/api/use-config-api.ts:275-282` (no `enabled`); `useApiKeys` `use-api-keys-api.ts:33-39` (`enabled: options?.enabled ?? true`); `useJobs` `use-jobs-api.ts:47-55` called with no argument by `features/settings/components/job-history-retention.tsx:22` (Maintenance tab); `useAutoResearch` / `useResearchRuns` `use-auto-research-api.ts:21-26, 75-80`. The `/jobs` page itself calls `useJobs(!DEMO)` through `features/activity/use-job-board.ts:70`, so it is already clean.
- **`DEMO_ROUTES`** is `tests/demo-makes-no-api-calls.spec.ts:19-33` and has no `/settings` entry.
- **The Settings Backups tab is unreachable** — adjacent bug: `routes/_authenticated/settings.tsx:36-46` `TAB_VALUES` lacks `"backups"` while `:133-136` renders its trigger and `:169-171` its content, so `onValueChange` drops the click and `validateSearch` drops `?tab=backups`. Task 3 fixes it; the spec counts "Settings: 10" tabs, which is the list with backups.
- **`lib/settings-tab.ts` is dead**: imported only by `lib/__tests__/settings-tab.test.ts` and `features/settings/__tests__/settings-distribution.real.test.tsx:273` (`rg -n "settings-tab" frontend/src`, 2026-09-18).
- **Demo memory projects** measured 2026-09-18 by a throwaway vitest over `useDemoStore.getState().memories`: `{"darkmem":10,"default":5000}`. Curated knowledge fixtures also name `acme-storefront` (`rg -o 'project: "[a-z0-9-]+"' src/demo`).
- **The registered jobs** are 18 in `backend/app/main.py:298-580` plus 6 in `backend/app/services/dream_jobs.py:631-760` = 24 (AST read of every `Job(...)` call, 2026-09-18); the demo fixture `demo/data/jobs.json` holds 7.
- **Page-level project controls** (2026-09-18): Memories real `features/memories/components/real-memories-view.tsx:30,132-141`; Memories demo `routes/_authenticated/memories.tsx:63,265-280`; Facts `features/knowledge/components/facts-tab.tsx:127,303-317`; Review `features/knowledge/components/review-tab.tsx:21,42-49`; Articles `features/knowledge/components/articles-tab.tsx:179,220-233`; Documents `routes/_authenticated/documents.tsx:16-23,57-80`. **Two facts in the brief differ:** the Memory Graph select is in the *demo* explorer `features/memory-graph/components/memory-graph-explorer.tsx:57,171-184` (the real page already reads the store through `hooks/api/use-graph-api.ts:93`), and the Chat second project chip is in the *demo* pane `features/chat/components/demo-message-pane.tsx:43-46` (`real-chat-page.tsx` has none).
- **Code-scope disclaimers** (2026-09-18): `features/code/components/repositories-tab.tsx:205-218` (demo: "not applied here" + "gated by repository, not project"), `code-graph-tab.tsx:287-290` and `real-code-graph-view.tsx:211-214` ("scope: repository, not project"), `wiki-tab.tsx:210-212` and `real-wiki-view.tsx:117-119` ("repo-scoped — not the project switcher"), and the two route descriptions `routes/_authenticated/code_.graph.tsx:32`, `code_.repositories.tsx:20`. `real-repositories-view.tsx` carries none. `features/code/__tests__/code-tabs.test.tsx:24-28,70-72,139-141` assert them.
- **Colour tokens are HSL triples** set as inline styles on `document.documentElement` by the theme provider (`node_modules/darkraise-ui/dist/chunk-FVOKEH2M.js:1498-1505`) and consumed as `hsl(var(--primary))` (`dist/styles.css:10826-10845`, `@theme inline`), and the mode is `<html data-mode>` (`styles/globals.css:40-41`). So the derived token is `color-mix(in oklch, hsl(var(--primary)) 70%, black)` on `:root` — the brief's `var(--primary)` without `hsl()` would be an invalid colour.
- **Text sizes** (2026-09-18): `rg -o "text-\[(8|9|10|11)(\.5)?px\]" frontend/src` → 147 `text-[10px]` + 18 `text-[11px]` across **63** files (the brief said 56), none in a test file.
- **`text-primary` / `text-success` as text**: 111 + 27 class occurrences in 78 non-test files (`rg -o "\btext-(primary|success)(/[0-9]+)?\b"`, which also counts inside `text-primary-foreground`; the sweep's lookahead excludes those).
- **No notifications control exists in the header** (`routes/_authenticated.tsx:235-243`, the `headerSlot`, renders AppPageHeader, ProjectSwitcher, ContextChip, DetailLevelToggle, MinimalThemeSwitcher; the library's `NotificationBell` is not used), so the overflow popover carries the four controls that exist.
- **darkraise-ui has no `activeBar="none"`** (`dist/layout/index.d.ts`: `type SidebarActiveBar = "bar" | "ring" | "both"`), so the borderless active item is an unlayered CSS override of `.dr-sidebar-nav-item.active` / `[data-status="active"]`; `@layer components` rules lose to it regardless of specificity.
- **Nested popovers:** darkraise-ui's `PopoverContent` honours `event.preventDefault()` in `onInteractOutside` (`dist/chunk-WPXGP5KR.js:225-240`) and renders with class `dr-popover-content` (`:259`), which is how the header overflow keeps itself open while an inner popover (the switcher, the context chip) is used.
- **`ResizablePanel` sizes are percentages only** and it sets `flexShrink: 0; width: <size>%` (`dist/chunk-ZU5NS2PO.js:202-240`), so a CSS `min-width` on the chat thread pane would overflow the group; Task 11 raises the percentage floor and makes the header wrap instead.
- **BlockNote 0.54.2** accepts `domAttributes.editor` (`node_modules/@blocknote/core/types/src/editor/BlockNoteEditor.d.ts:58`, `BlockNoteDOMAttributes` keyed `"editor" | "block" | "blockGroup" | "blockContent" | "inlineContent"`), marks a toggle's open state as `data-show-children="true"|"false"` on the toggle wrapper, renders the toggle button as `.bn-toggle-button`, sets its font on `.bn-default-styles` (Inter stack, 16px) and paints code blocks `#161616` (`dist/style.css`).
- **No `BrandMark` component exists**: the app's mark is the CSS mask `.dr-brand-logo::before` over `/logo.svg` painted with `--primary` (`styles/globals.css:486-518`); Task 17 reuses that mask as `.dm-brand-mark`.
- **The Memory Graph SVG with nested buttons is the demo explorer** (`memory-graph-explorer.tsx:206-324`, `role="img"` holding `role="button" tabIndex={0}` nodes); the real Memory Graph renders through Sigma on a canvas (`features/graph/components/graph-2d-renderer.tsx`), whose label density is Sigma's own. The Code Graph canvas has the same pattern in `features/code/components/code-canvas.tsx:111-184`, and its label reads "Demo code graph" in real mode too (adjacent bug, fixed in Task 16).
- **Backend-produced claim sentences keep their bracket lists**: the verification claim "asserted by N distinct origins of kinds [memory, code]" is minted server-side and `features/knowledge/__tests__/no-second-claim-producer.test.ts` forbids a frontend producer, so Task 22 changes only kind lists the frontend itself formats.
- **Flags row keys stay visible in Simple mode**: every Flags row is labelled by its config key (`flags-tab.tsx:327-328,440-441,476-477`) with no plain-language label to substitute; Task 23 hides the secondary keys (arm aliases, activation task ids) only.
- **`axe-core` 4.11.4 is installed** as a transitive dependency (`frontend/node_modules/axe-core/package.json`), which Task 25's scratch audit injects; no dependency is added.
- **The sidebar search box's standing accent border is not visible in source**: the trigger is the library's `.dr-search-command-trigger` (`dist/styles.css`, no primary border rule found), so the border most likely comes from an accent-intensity axis at runtime. unverified — Task 25 verifies it (Step 6 screenshots); Task 18's override pins the rest state to `--border` either way.
- **The theme mode persists under the localStorage key `mode`** (`src/lib/theme-hidden-axes.ts:36`); its value format is not visible in the library bundle. unverified — Task 25 verifies it (Step 4 checks `data-mode` per page load and says what to do on a mismatch).
- **`DEFAULT_PROJECT` stays exported** as the backend's capture default: eight test files use it as a fixture value (`rg -l DEFAULT_PROJECT frontend/src`), and it remains true as a statement about where an unscoped capture lands.
- **Topics ignored the scope** (`topics-tab.tsx:190` defaults `project = "default"`; `routes/_authenticated/knowledge_.topics.tsx:18` passes nothing). Task 8 fixes it with the Documents chooser pattern.
- **Spec conflict, resolved toward invariant 14**: §F lists `by_review_state` as advanced-only, but it is an exclusion tag and the honesty spec asserts exclusion tags in both modes (`tests/honesty/labels-always-render.spec.ts:52`), which the spec's own constraints forbid hiding. Task 23 rewrites only the reason sentence around it.
- **Targeted Playwright runs** use `--project=demo-fixture` with `E2E_API_TARGET=http://127.0.0.1:9`: the rule against bare Playwright exists because `/api` proxies to the live `:8000` (`frontend/vite.config.ts:26`); a dead target removes that path, and demo specs make no API request by construction. The full e2e leg still goes through `run_playwright_e2e.py` (Task 25).
- **Raw timestamp sites are complete** (2026-09-19): `rg -n --pcre2 '\{[a-zA-Z_.?]*\.(?:[a-z_]*_at|at|since)\}' frontend/src -g '*.tsx' -g '!*.test.*' -g '!*.stories.*'` lists 23 lines; Task 22 converts every live one (`$articleId.tsx:335,361`, `review-queue.tsx:179,185,266,313,315`, `belief-window.tsx:55-57` via `DateField`, `fact-sources.tsx:52`, `hygiene-queue.tsx:353,354,381,385`, `fact-detail.tsx:50`, `fact-ladder.tsx:43`, `reindex-dialog.tsx:81`). Three are left on purpose: `wiki-tab.tsx:217` and `repositories-tab.tsx:30,105` render demo-only fixture labels such as "2026-07-20 04:12", which `code-tabs.test.tsx:137` asserts verbatim and which are not API timestamps.
- **Library-owned and warning/info text contrast** (2026-09-19): darkraise-ui's own stylesheet paints `--primary` / `--success` / `--warning` / `--info` as text in 50 rules (a scan of `node_modules/darkraise-ui/dist/styles.css` for `color: hsl(var(--primary|success|warning|info))` and `@apply text-…`), e.g. `.dr-btn[data-variant="link"]`, `.dr-stat-change[data-direction="up"]`, `.dr-tabs-trigger[data-variant="underline"]`, `.dr-segment-group-item[data-variant="outline"][data-state="checked"]`. darkmem itself uses `text-warning` / `text-info` in 43 files (`rg -l --pcre2 '(?<![-\w])text-(warning|info)(?![-\w])' frontend/src -g '!*.test.*'`). Task 13 therefore derives all four text tokens and sweeps all four utilities in darkmem source; library rules stay outside darkmem's control, so Task 25 counts a `color-contrast` node inside a `.dr-*` library element with no darkmem text utility as a named library exception, reported with its selector rather than failing the gate.
- **Plan review round 1:** coherence 13 (borderline) — accepted after fixing the three literal-edit ranges (T9, T17, T23) that drove it.
- **The demo graph fixture has at least one overlapping label under the all-projects scope**: unverified — Task 16 verifies it (its focus test asserts a hidden label exists before focusing it; if none does, the test names the fixture as the cause and the task reports rather than weakening the assertion).
- **plan-lint warns "no **Plan review:** line yet"** until the review round runs; that warning is expected at this stage.
- **Task count is 25, above the brief's 10–16 estimate**, because Rule S (files + spec + coupling < 4) splits the spec's eight sections into reviewer-sized units.

## Task index

1. Demo reads stay offline
2. Demo fixtures for projects, usage and jobs
3. Settings tab registry and dead code
4. Project scope defaults to all projects
5. Code pages opt out of project scope
6. Memories and Documents read the global scope
7. Knowledge, graph and chat pages read the global scope
8. Topics follows the global scope
9. Responsive app header
10. Scrollable tab bars
11. Activity pipeline rows and chat thread pane
12. Code Graph layout and panel chrome
13. Contrast-safe text tokens
14. Minimum 12px text
15. Notes editor accessibility
16. Graph canvas semantics and label overlap
17. Login follows the app theme
18. Sidebar and theme surface
19. Articles and Dashboard polish
20. Notes editor styling
21. Jobs and Review controls
22. Timestamps and kind lists in prose
23. Advanced-only detail and corrected copy
24. Demo-only visuals
25. Final verification

---

### Task 1: Demo reads stay offline

Spec §A, first two bullets. Five authenticated reads mount in demo mode with no guard; each 401s and the global handler hard-navigates the demo to `/login`. The guard goes on the hook, so every caller (including `memory-event-timeline.tsx`, which also calls `useApiKeys`) is covered at once.

**Files:**
- Modify: `frontend/src/hooks/api/use-config-api.ts:1-2,275-282`
- Modify: `frontend/src/hooks/api/use-api-keys-api.ts:1-3,33-39`
- Modify: `frontend/src/hooks/api/use-jobs-api.ts:1-2,47-55`
- Modify: `frontend/src/hooks/api/use-auto-research-api.ts:1-3,21-26,75-80`
- Modify: `frontend/tests/demo-makes-no-api-calls.spec.ts:19-33`
- Create: `frontend/src/hooks/api/__tests__/demo-reads.demo.test.tsx`

**Interfaces:**
- Consumes: nothing.
- Produces: nothing other tasks name.

**Implementer:** dr-superpowers:impl-sonnet-medium
**Evaluation:** files 1 - spec 0 - coupling 0 - risk 1 = 2

- [ ] **Step 1: Write the failing test**

Create `frontend/src/hooks/api/__tests__/demo-reads.demo.test.tsx`:

```tsx
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { act, renderHook } from "@testing-library/react"
import type { ReactNode } from "react"
import { afterEach, describe, expect, it, vi } from "vitest"

vi.mock("@/lib/demo-flag", () => ({ DEMO: true }))
vi.mock("@/lib/api", () => ({ apiFetch: vi.fn() }))

import { apiFetch } from "@/lib/api"
import {
  useApiKeys,
  useAutoResearch,
  useClassificationAreas,
  useJobs,
  useResearchRuns,
} from "@/hooks/api"

function wrapper({ children }: { children: ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>
}

afterEach(() => vi.clearAllMocks())

// A demo read that reaches apiFetch 401s, and the 401 handler navigates the
// whole demo to /login — so "no request" is the only acceptable outcome.
describe("demo mode issues none of the Settings reads", () => {
  const hooks: Array<[string, () => unknown]> = [
    ["useClassificationAreas", () => useClassificationAreas()],
    ["useApiKeys", () => useApiKeys()],
    ["useJobs", () => useJobs()],
    ["useAutoResearch", () => useAutoResearch()],
    ["useResearchRuns", () => useResearchRuns()],
  ]

  for (const [name, hook] of hooks) {
    it(`${name} stays idle`, async () => {
      renderHook(hook, { wrapper })
      await act(async () => {})
      expect(apiFetch).not.toHaveBeenCalled()
    })
  }
})
```

- [ ] **Step 2: Run test to verify it fails**

Run (from `frontend/`): `npx vitest run src/hooks/api/__tests__/demo-reads.demo.test.tsx`
Expected: FAIL — five tests, each with `expected "spy" to not be called at all`.

- [ ] **Step 3: Guard the five hooks**

In `frontend/src/hooks/api/use-config-api.ts`, add the import after the `apiFetch` import (line 2):

```ts
import { DEMO } from "@/lib/demo-flag"
```

and replace `useClassificationAreas` (lines 275-282) with:

```ts
export function useClassificationAreas() {
  return useQuery<ClassificationAreaInfo[]>({
    queryKey: ["classificationAreas"],
    queryFn: () =>
      apiFetch<ClassificationAreaInfo[]>("/config/classification-areas"),
    staleTime: 300_000,
    enabled: !DEMO,
  })
}
```

In `frontend/src/hooks/api/use-api-keys-api.ts`, add after the `apiFetch` import:

```ts
import { DEMO } from "@/lib/demo-flag"
```

and change the `enabled` line of `useApiKeys` to:

```ts
    enabled: !DEMO && (options?.enabled ?? true),
```

In `frontend/src/hooks/api/use-jobs-api.ts`, add after the `apiFetch` import:

```ts
import { DEMO } from "@/lib/demo-flag"
```

and change the `enabled` line of `useJobs` to:

```ts
    enabled: !DEMO && enabled,
```

In `frontend/src/hooks/api/use-auto-research-api.ts`, add after the `apiFetch` import:

```ts
import { DEMO } from "@/lib/demo-flag"
```

and give both reads the guard:

```ts
export function useAutoResearch() {
  return useQuery<AutoResearchConfig>({
    queryKey: ["autoResearch"],
    queryFn: () => apiFetch<AutoResearchConfig>("/config/auto-research"),
    enabled: !DEMO,
  })
}
```

```ts
export function useResearchRuns() {
  return useQuery<ResearchRunList>({
    queryKey: ["autoResearch", "runs"],
    queryFn: () => apiFetch<ResearchRunList>("/config/auto-research/runs"),
    enabled: !DEMO,
  })
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `npx vitest run src/hooks/api/__tests__/demo-reads.demo.test.tsx src/features/settings`
Expected: PASS (5 new tests; every Settings test still green).

- [ ] **Step 5: Extend the demo route list**

In `frontend/tests/demo-makes-no-api-calls.spec.ts`, replace the `DEMO_ROUTES` array (lines 19-33) with:

```ts
const SETTINGS_TABS = [
  "flags",
  "llm",
  "security",
  "maintenance",
  "integration",
  "git-accounts",
  "notifications",
  "research",
  "backups",
  "appearance",
] as const

const DEMO_ROUTES = [
  "/",
  "/memories",
  "/memory-graph",
  "/activity?tab=feed",
  "/activity?tab=day",
  "/activity?tab=jobs",
  "/activity?tab=monitors",
  "/activity?tab=pipeline",
  "/activity?tab=triage",
  "/code/repositories",
  "/code/graph",
  "/code/wiki",
  "/knowledge/facts",
  "/knowledge/review",
  "/knowledge/topics",
  "/documents",
  "/notes",
  "/projects",
  "/chat",
  "/jobs",
  "/usage",
  ...SETTINGS_TABS.map((tab) => `/settings?tab=${tab}`),
]
```

- [ ] **Step 6: Run the demo spec and guard anything else it names**

Run (from `frontend/`): `E2E_API_TARGET=http://127.0.0.1:9 timeout 900 npx playwright test --project=demo-fixture tests/demo-makes-no-api-calls.spec.ts`
Expected: 31 passed.

If a route fails, its message names the URL it attempted (for example `GET /api/v1/distribution/...`). Find the hook that builds that path with `rg -n "<path>" src/hooks/api`, apply the same guard in the hook (`enabled: !DEMO`, or `enabled: !DEMO && (<existing condition>)` when it already has one, with the `DEMO` import from `@/lib/demo-flag`), add the hook to the `hooks` array in `demo-reads.demo.test.tsx`, and re-run Steps 4 and 6. Record each extra hook in the commit body.

- [ ] **Step 7: Typecheck**

Run: `npm run typecheck`
Expected: exit 0.

- [ ] **Step 8: Commit**

```bash
git add frontend/src/hooks/api frontend/tests/demo-makes-no-api-calls.spec.ts
git commit -m "fix(demo): keep every Settings read offline" -m "Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

### Task 2: Demo fixtures for projects, usage and jobs

Spec §A, third bullet. The project catalogue populates the header switcher, `/projects` and the Documents chooser; the usage fixture replaces Usage's failed-read state; the jobs fixture lists all 24 registered jobs. Demo data enters through `initialData` so the query stays disabled and issues nothing.

**Files:**
- Create: `frontend/src/demo/projects.ts`
- Create: `frontend/src/demo/usage.ts`
- Modify: `frontend/src/hooks/api/use-projects-api.ts:1-3,26-36`
- Modify: `frontend/src/hooks/api/use-usage-api.ts:1-5,146-165`
- Modify: `frontend/src/demo/data/jobs.json` (append 17 entries)
- Modify: `frontend/src/demo/__tests__/activity.test.ts:122-134`
- Create: `frontend/src/hooks/api/__tests__/demo-fixtures.demo.test.tsx`

**Interfaces:**
- Consumes: nothing.
- Produces: `DEMO_PROJECTS`, `DEMO_USAGE_OVERVIEW`, `DEMO_USAGE_SERIES` (Contracts). Tasks 4 and 6 rely on `useProjects()` returning `DEMO_PROJECTS` in demo mode.

**Implementer:** dr-superpowers:impl-opus-low
**Evaluation:** files 2 - spec 0 - coupling 1 - risk 1 = 4

- [ ] **Step 1: Write the failing tests**

Create `frontend/src/hooks/api/__tests__/demo-fixtures.demo.test.tsx`:

```tsx
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { renderHook } from "@testing-library/react"
import type { ReactNode } from "react"
import { afterEach, describe, expect, it, vi } from "vitest"

vi.mock("@/lib/demo-flag", () => ({ DEMO: true }))
vi.mock("@/lib/api", () => ({ apiFetch: vi.fn() }))

import { apiFetch } from "@/lib/api"
import { useProjects, useUsageOverview, useUsageSeries } from "@/hooks/api"

function wrapper({ children }: { children: ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>
}

afterEach(() => vi.clearAllMocks())

describe("demo fixtures reach the hooks without a request", () => {
  it("serves the project catalogue", () => {
    const { result } = renderHook(() => useProjects(), { wrapper })
    expect(result.current.isSuccess).toBe(true)
    expect(result.current.data?.map((p) => p.name)).toEqual([
      "default",
      "darkmem",
      "acme-storefront",
      "notes",
    ])
    expect(apiFetch).not.toHaveBeenCalled()
  })

  it("serves a usage overview and series for every window", () => {
    for (const window of ["24h", "7d", "30d", "all"] as const) {
      const overview = renderHook(() => useUsageOverview(window), { wrapper })
      const series = renderHook(() => useUsageSeries(window), { wrapper })
      expect(overview.result.current.data?.total_calls).toBeGreaterThan(0)
      expect(series.result.current.data?.buckets.length).toBeGreaterThan(0)
    }
    expect(apiFetch).not.toHaveBeenCalled()
  })
})
```

In `frontend/src/demo/__tests__/activity.test.ts`, replace the first `jobs` test (lines 123-134) with:

```ts
  it("ships every registered job — the list can never be empty", () => {
    const jobs = useDemoStore.getState().jobs
    expect(jobs.map((j) => j.key)).toEqual([
      "repo_sync",
      "code_enrichment",
      "token_blocklist_cleanup",
      "pipeline_failure_cleanup",
      "graph_orphan_cleanup",
      "tag_orphan_cleanup",
      "expired_memory_cleanup",
      "buffer_flush",
      "job_run_cleanup",
      "llm_usage_cleanup",
      "backup_ship",
      "code_deriver",
      "ppr_snapshot",
      "relation_embedding_refresh",
      "block_embedding_refresh",
      "repo_entity_anchoring",
      "repo_entity_merge",
      "citation_reverify",
      "fact_lift",
      "verification_recompute",
      "contradiction_scan",
      "memory_dream",
      "topic_detection",
      "article_synthesis",
    ])
  })
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `npx vitest run src/hooks/api/__tests__/demo-fixtures.demo.test.tsx src/demo/__tests__/activity.test.ts`
Expected: FAIL — `isSuccess` is `false` for projects, `total_calls` of `undefined`, and the jobs array has 7 entries.

- [ ] **Step 3: Add the project catalogue**

Create `frontend/src/demo/projects.ts`:

```ts
import type { ProjectSummary } from "@/hooks/api"

/** Busiest first, as `GET /projects` orders them. The counts mirror the demo
 *  store: 10 curated memories in `darkmem`, the 5000-row bulk fixture in
 *  `default`, and the curated knowledge fixtures in `acme-storefront`. */
export const DEMO_PROJECTS: ProjectSummary[] = [
  {
    name: "default",
    kind: "project",
    memory_count: 5000,
    document_count: 0,
    checkpoint_count: 0,
    page_count: 0,
    last_checkpoint_at: null,
    last_event_day: "2026-07-25",
  },
  {
    name: "darkmem",
    kind: "project",
    memory_count: 10,
    document_count: 12,
    checkpoint_count: 3,
    page_count: 0,
    last_checkpoint_at: "2026-07-24T14:10:00Z",
    last_event_day: "2026-07-25",
  },
  {
    name: "acme-storefront",
    kind: "project",
    memory_count: 0,
    document_count: 4,
    checkpoint_count: 0,
    page_count: 0,
    last_checkpoint_at: null,
    last_event_day: "2026-07-20",
  },
  {
    name: "notes",
    kind: "personal",
    memory_count: 0,
    document_count: 0,
    checkpoint_count: 0,
    page_count: 3,
    last_checkpoint_at: null,
    last_event_day: "2026-07-24",
  },
]
```

In `frontend/src/hooks/api/use-projects-api.ts`, add after the `DEMO` import:

```ts
import { DEMO_PROJECTS } from "@/demo/projects"
```

and add one line after `enabled: !DEMO,` inside `useProjects`:

```ts
    initialData: DEMO ? DEMO_PROJECTS : undefined,
```

- [ ] **Step 4: Add the usage fixture**

Create `frontend/src/demo/usage.ts`:

```ts
import type { UsageOverview, UsageSeries } from "@/hooks/api"

const row = (
  key: string,
  cost_micros: number,
  calls: number,
  prompt_tokens: number,
  completion_tokens: number,
) => ({
  key,
  cost_micros,
  calls,
  prompt_tokens,
  cached_tokens: Math.round(prompt_tokens * 0.3),
  completion_tokens,
  unmeasured_calls: 0,
  unpriced_calls: 0,
})

export const DEMO_USAGE_OVERVIEW: UsageOverview = {
  window_start: "2026-06-25T00:00:00Z",
  window_end: "2026-07-25T00:00:00Z",
  total_cost_micros: 4_182_000,
  total_calls: 1_864,
  prompt_tokens: 2_410_000,
  cached_tokens: 723_000,
  completion_tokens: 318_000,
  reasoning_tokens: 0,
  unmeasured_calls: 12,
  unpriced_calls: 0,
  unpriced_models: [],
  merged_classification_present: true,
  cache_hit_ratio: 0.3,
  failed_calls: 9,
  failed_cost_micros: 21_000,
  by_purpose: [
    row("extraction", 2_310_000, 820, 1_420_000, 190_000),
    row("reasoning", 1_080_000, 214, 540_000, 88_000),
    row("reranker", 512_000, 610, 360_000, 24_000),
    row("summarization", 280_000, 220, 90_000, 16_000),
  ],
  by_model: [
    row("deepseek-v4-flash", 3_390_000, 1_030, 1_960_000, 278_000),
    row("qwen3-embedding:0.6b", 0, 610, 360_000, 0),
    row("gpt-5.5", 792_000, 224, 90_000, 40_000),
  ],
  by_subject_type: [
    row("memory", 2_600_000, 1_100, 1_500_000, 200_000),
    row("chat", 1_080_000, 214, 540_000, 88_000),
    row("job", 502_000, 550, 370_000, 30_000),
  ],
}

const DAY_MS = 86_400_000
const SERIES_END = Date.UTC(2026, 6, 25)

export const DEMO_USAGE_SERIES: UsageSeries = {
  bucket: "day",
  buckets: Array.from({ length: 30 }, (_, i) => {
    const calls = 40 + ((i * 17) % 45)
    return {
      bucket_start: new Date(SERIES_END - (29 - i) * DAY_MS).toISOString(),
      cost_micros: calls * 2_200,
      calls,
      prompt_tokens: calls * 1_300,
      completion_tokens: calls * 170,
      unmeasured_calls: i % 9 === 0 ? 1 : 0,
    }
  }),
}
```

In `frontend/src/hooks/api/use-usage-api.ts`, add after the `DEMO` import (line 4):

```ts
import { DEMO_USAGE_OVERVIEW, DEMO_USAGE_SERIES } from "@/demo/usage"
```

and add `initialData` to the two reads the Overview tab renders (`useUsageOverview` and `useUsageSeries`), directly after their `enabled: LIVE,` lines:

```ts
    initialData: LIVE ? undefined : DEMO_USAGE_OVERVIEW,
```

```ts
    initialData: LIVE ? undefined : DEMO_USAGE_SERIES,
```

- [ ] **Step 5: Append the 17 missing jobs**

Run from the worktree root (a one-shot edit; the script is not kept):

```bash
node -e '
const fs = require("fs")
const path = "frontend/src/demo/data/jobs.json"
const jobs = JSON.parse(fs.readFileSync(path, "utf8"))
const add = (key, name, description, cron, cron_label, min_interval_seconds, last_run_label, last_summary) => ({
  key, name, description, enabled: true, cron, cron_label, min_interval_seconds,
  max_run_seconds: 300, running: false, lock_held_since: null, next_run_label: null,
  last_run_label, last_status: "ok", last_summary, config_schema: [],
})
jobs.push(
  add("buffer_flush", "Buffer Flush", "Claims accepted captures from the ingest buffer and runs them through the pipeline.", "*/5 * * * * *", "every 5s, six-field seconds-first", 1, "14:12 UTC", "ok, 4 captures processed"),
  add("job_run_cleanup", "Job History Cleanup", "Trims the job run history to its configured ceiling, newest kept.", "0 4 * * 0", "Sundays at 04:00", 3600, "Sun 04:00 UTC", "ok, 0 rows trimmed"),
  add("llm_usage_cleanup", "LLM Usage Retention", "Deletes LLM usage rows older than the retention window.", "0 4 * * *", "daily at 04:00", 3600, "04:00 UTC", "ok, 212 rows past the window deleted"),
  add("backup_ship", "Backup Ship", "Dumps, encrypts and ships the database to every enabled backup destination, then verifies each upload.", "30 4 * * *", "daily at 04:30", 3600, "04:30 UTC", "ok, 1 destination shipped and verified"),
  add("code_deriver", "Code Graph Deriver", "Derives each indexed repository's graph assertions from its import edges.", "50 * * * *", "hourly at :50", 300, "13:50 UTC", "ok, 3 repos derived"),
  add("ppr_snapshot", "PPR Graph Snapshot", "Rebuilds the cached entity-graph snapshot the PPR retrieval arm ranks against.", "30 * * * *", "hourly at :30", 300, "13:30 UTC", "ok, 2 projects refreshed"),
  add("relation_embedding_refresh", "Relation Embedding Refresh", "Embeds relations that have no vector under the active embedder.", "15 * * * *", "hourly at :15", 300, "14:15 UTC", "ok, 18 relations embedded"),
  add("block_embedding_refresh", "Block Embedding Refresh", "Embeds document and page blocks that have no vector under the active embedder.", "35 * * * *", "hourly at :35", 300, "13:35 UTC", "ok, 41 blocks embedded"),
  add("repo_entity_anchoring", "Repo Entity Anchoring", "Embeds entities a repository asserts but no memory does, so dedup can see them.", "45 * * * *", "hourly at :45", 300, "13:45 UTC", "ok, 6 entities anchored"),
  add("repo_entity_merge", "Repo Entity Merge", "Fuses a repository entity with the near-named entity a memory already created.", "50 * * * *", "hourly at :50", 300, "13:50 UTC", "ok, 1 pair merged"),
  add("citation_reverify", "Citation Re-verify", "Re-resolves every code citation against its repository's current HEAD and marks the stale ones.", "45 * * * *", "hourly at :45", 300, "13:45 UTC", "ok, 0 citations went stale"),
  add("fact_lift", "Fact Lift", "Derives candidate facts and their sources from the entity graph.", "*/15 * * * *", "every 15 minutes", 60, "14:00 UTC", "ok, 3 facts lifted"),
  add("verification_recompute", "Verification Recompute", "Recomputes each changed fact's place on the verification ladder.", "*/2 * * * *", "every 2 minutes", 30, "14:12 UTC", "ok, 5 facts recomputed"),
  add("contradiction_scan", "Contradiction Scan", "Checks overlapping facts for contradictions and flags suspected ones for review.", "0 */6 * * *", "every 6 hours", 300, "12:00 UTC", "ok, 0 contradictions suspected"),
  add("memory_dream", "Memory Dream", "Deduplicates and refines memories, and proposes near-duplicates for the hygiene queue. It never deletes.", "0 3 * * *", "daily at 03:00", 300, "03:00 UTC", "ok, 2 memories refined"),
  add("topic_detection", "Topic Detection", "Groups each active project's entities into topic communities.", "0 4 * * *", "daily at 04:00", 300, "04:00 UTC", "ok, 3 topics detected"),
  add("article_synthesis", "Article Synthesis", "Writes an article per eligible subject from its verified facts only.", "0 5 * * *", "daily at 05:00", 300, "05:00 UTC", "ok, 1 article synthesised"),
)
fs.writeFileSync(path, JSON.stringify(jobs, null, 2) + "\n")
'
```

- [ ] **Step 6: Run tests to verify they pass**

Run (from `frontend/`): `npx vitest run src/hooks/api/__tests__/demo-fixtures.demo.test.tsx src/demo src/features/usage src/features/jobs src/features/activity`
Expected: PASS. If a jobs or activity test asserted the old count of 7, update that assertion to 24 and name the file in the commit body.

- [ ] **Step 7: Typecheck and re-run the demo spec**

Run: `npm run typecheck`
Expected: exit 0.
Run: `E2E_API_TARGET=http://127.0.0.1:9 timeout 900 npx playwright test --project=demo-fixture tests/demo-makes-no-api-calls.spec.ts`
Expected: 31 passed.

- [ ] **Step 8: Commit**

```bash
git add frontend/src/demo frontend/src/hooks/api
git commit -m "feat(demo): add project, usage and job fixtures" -m "Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

### Task 3: Settings tab registry and dead code

Spec §G, plus the adjacent Backups bug recorded in Assumptions: `TAB_VALUES` is the list the route validates, and it lacks `"backups"`.

**Files:**
- Delete: `frontend/src/lib/settings-tab.ts`
- Delete: `frontend/src/lib/__tests__/settings-tab.test.ts`
- Modify: `frontend/src/features/settings/__tests__/settings-distribution.real.test.tsx:268-276`
- Modify: `frontend/src/routes/_authenticated/settings.tsx:36-46`
- Create: `frontend/src/routes/_authenticated/__tests__/settings-tabs.test.ts`

**Interfaces:**
- Consumes: nothing.
- Produces: `TAB_VALUES` exported from `routes/_authenticated/settings.tsx`.

**Implementer:** dr-superpowers:impl-sonnet-low
**Evaluation:** files 1 - spec 0 - coupling 0 - risk 0 = 1

- [ ] **Step 1: Write the failing test**

Create `frontend/src/routes/_authenticated/__tests__/settings-tabs.test.ts`:

```ts
import { readFileSync } from "node:fs"
import { join } from "node:path"
import { describe, expect, it } from "vitest"
import { TAB_VALUES } from "../settings"

describe("Settings tab registry", () => {
  // A trigger whose value is missing here renders, but the route drops both
  // the click and ?tab=<value>, so the tab can never be opened.
  it("registers every tab the page renders", () => {
    const source = readFileSync(
      join(process.cwd(), "src/routes/_authenticated/settings.tsx"),
      "utf8",
    )
    const rendered = [...source.matchAll(/<TabsTrigger[^>]*value="([^"]+)"/g)]
      .map((m) => m[1])
      .sort()
    expect([...TAB_VALUES].sort()).toEqual(rendered)
    expect(TAB_VALUES).toHaveLength(10)
  })
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npx vitest run src/routes/_authenticated/__tests__/settings-tabs.test.ts`
Expected: FAIL — `TAB_VALUES` is not exported (`undefined` is not iterable).

- [ ] **Step 3: Export the registry with backups**

In `frontend/src/routes/_authenticated/settings.tsx`, replace lines 36-46 with:

```ts
export const TAB_VALUES = [
  "flags",
  "llm",
  "security",
  "maintenance",
  "integration",
  "git-accounts",
  "research",
  "notifications",
  "backups",
  "appearance",
] as const
```

- [ ] **Step 4: Delete the dead module and its last importer's test block**

```bash
git rm frontend/src/lib/settings-tab.ts frontend/src/lib/__tests__/settings-tab.test.ts
```

In `frontend/src/features/settings/__tests__/settings-distribution.real.test.tsx`, delete the whole `describe("the Distribution tab is one a human can return to", …)` block (lines 268-276). Its claim is now covered by the registry test above: the tab is reachable because the route registers `integration`.

- [ ] **Step 5: Run tests and typecheck**

Run: `npx vitest run src/routes/_authenticated/__tests__/settings-tabs.test.ts src/features/settings && npm run typecheck`
Expected: PASS; typecheck exit 0. `rg -n "settings-tab\"" src` prints nothing.

- [ ] **Step 6: Commit**

```bash
git add -A frontend/src/lib frontend/src/features/settings/__tests__/settings-distribution.real.test.tsx frontend/src/routes/_authenticated/settings.tsx frontend/src/routes/_authenticated/__tests__/settings-tabs.test.ts
git commit -m "fix(settings): register the Backups tab" -m "Also deletes lib/settings-tab.ts, which nothing imported." -m "Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

### Task 4: Project scope defaults to all projects

Spec §B, first two bullets. A fresh session opens on every project, and a persisted scope the corpus no longer holds widens to every project with the switcher saying so. "All projects" is already the switcher's first row (`project-switcher.tsx:87-93`); a test pins it.

**Files:**
- Modify: `frontend/src/stores/project-store.ts` (whole file)
- Modify: `frontend/src/components/app-chrome/project-switcher.tsx:1-17,45-128`
- Modify: `frontend/src/components/app-chrome/index.ts:5`
- Modify: `frontend/src/routes/_authenticated.tsx:46-52,290`
- Modify: `frontend/src/stores/__tests__/project-store.test.ts`
- Modify: `frontend/src/components/app-chrome/__tests__/project-switcher.test.tsx`

**Interfaces:**
- Consumes: `useProjects()` serves `DEMO_PROJECTS` in demo mode (Task 2).
- Produces: the `stores/project-store.ts` and `ProjectScopeReconciler` entries in Contracts.

**Implementer:** dr-superpowers:impl-opus-medium
**Evaluation:** files 1 - spec 0 - coupling 2 - risk 2 = 5

- [ ] **Step 1: Write the failing store tests**

In `frontend/src/stores/__tests__/project-store.test.ts`, change the import to:

```ts
import {
  useProjectStore,
  ALL_PROJECTS,
  DEFAULT_PROJECT,
} from "../project-store"
```

replace the `beforeEach` body with:

```ts
    localStorage.clear()
    useProjectStore.setState({
      activeProject: DEFAULT_PROJECT,
      missingProject: null,
    })
```

replace the test `"defaults to the backend's own default project"` with:

```ts
  it("opens on every project", () => {
    expect(useProjectStore.getInitialState().activeProject).toBe(ALL_PROJECTS)
    expect(useProjectStore.getInitialState().missingProject).toBeNull()
  })
```

and append inside the `describe`:

```ts
  it("reconcile keeps a scope the corpus still holds", () => {
    useProjectStore.getState().setProject("acme")
    useProjectStore.getState().reconcile(["acme", "darkmem"])
    expect(useProjectStore.getState().activeProject).toBe("acme")
    expect(useProjectStore.getState().missingProject).toBeNull()
  })

  it("reconcile widens a scope the corpus no longer holds, naming it", () => {
    useProjectStore.getState().setProject("gone")
    useProjectStore.getState().reconcile(["acme"])
    expect(useProjectStore.getState().activeProject).toBe(ALL_PROJECTS)
    expect(useProjectStore.getState().missingProject).toBe("gone")
  })

  it("reconcile leaves the all-projects scope alone", () => {
    useProjectStore.getState().setProject(ALL_PROJECTS)
    useProjectStore.getState().reconcile([])
    expect(useProjectStore.getState().activeProject).toBe(ALL_PROJECTS)
    expect(useProjectStore.getState().missingProject).toBeNull()
  })

  it("picking a scope clears the missing-project notice", () => {
    useProjectStore.setState({ activeProject: ALL_PROJECTS, missingProject: "gone" })
    useProjectStore.getState().setProject("acme")
    expect(useProjectStore.getState().missingProject).toBeNull()
  })

  it("persists the scope but not the notice", () => {
    useProjectStore.setState({ activeProject: ALL_PROJECTS, missingProject: "gone" })
    useProjectStore.getState().setProject("acme")
    const stored = JSON.parse(localStorage.getItem("darkmem-project") ?? "{}")
    expect(stored.state).toEqual({ activeProject: "acme" })
  })
```

- [ ] **Step 2: Write the failing switcher tests**

In `frontend/src/components/app-chrome/__tests__/project-switcher.test.tsx`, change the switcher import line to:

```ts
import { ProjectScopeReconciler, ProjectSwitcher } from "../project-switcher"
```

change the store import to add `STALE_SCOPE_NOTICE`:

```ts
import {
  useProjectStore,
  DEFAULT_PROJECT,
  ALL_PROJECTS,
  STALE_SCOPE_NOTICE,
} from "@/stores/project-store"
```

set `missingProject: null` in the existing `beforeEach` `setState` call, and append inside the top-level `describe("ProjectSwitcher", …)`:

```ts
  it("offers All projects first", async () => {
    mockUseProjects.mockReturnValue({
      data: [{ name: "acme", kind: "project", memory_count: 3, document_count: 0, checkpoint_count: 0, page_count: 0 }],
      isLoading: false,
    })
    const user = userEvent.setup()
    renderSwitcher()
    await user.click(screen.getByRole("button", { name: /project scope/i }))
    const labels = screen
      .getAllByRole("button")
      .filter((b) => b.hasAttribute("aria-pressed"))
      .map((row) => row.textContent ?? "")
    expect(labels[0]).toMatch(/^All projects/)
    expect(labels.findIndex((l) => l.startsWith("All projects"))).toBeLessThan(
      labels.findIndex((l) => l.startsWith("acme")),
    )
  })

  it("says so when a saved project was not found", () => {
    useProjectStore.setState({ activeProject: ALL_PROJECTS, missingProject: "gone" })
    renderSwitcher()
    expect(screen.getByText(STALE_SCOPE_NOTICE)).toBeInTheDocument()
    expect(
      screen.getByRole("button", { name: /project scope/i }),
    ).toHaveTextContent("project: all projects")
  })
})

describe("ProjectScopeReconciler", () => {
  beforeEach(() => {
    useProjectStore.setState({ activeProject: "gone", missingProject: null })
  })

  it("widens a saved scope the server list does not hold", () => {
    mockUseProjects.mockReturnValue({
      data: [
        { name: "acme", kind: "project" },
        { name: "notes", kind: "personal" },
      ],
      isLoading: false,
      isSuccess: true,
    })
    render(<ProjectScopeReconciler />)
    expect(useProjectStore.getState().activeProject).toBe(ALL_PROJECTS)
    expect(useProjectStore.getState().missingProject).toBe("gone")
  })

  it("does nothing until the list has loaded", () => {
    mockUseProjects.mockReturnValue({ data: undefined, isLoading: true, isSuccess: false })
    render(<ProjectScopeReconciler />)
    expect(useProjectStore.getState().activeProject).toBe("gone")
  })

  it("treats the personal space as no project scope", () => {
    useProjectStore.setState({ activeProject: "notes", missingProject: null })
    mockUseProjects.mockReturnValue({
      data: [{ name: "notes", kind: "personal" }],
      isLoading: false,
      isSuccess: true,
    })
    render(<ProjectScopeReconciler />)
    expect(useProjectStore.getState().activeProject).toBe(ALL_PROJECTS)
  })
```

(The `ProjectSwitcher` describe's closing `})` moves to the end of the first appended block, as written above; the reconciler block ends with the file's final `})`.)

- [ ] **Step 3: Run tests to verify they fail**

Run: `npx vitest run src/stores/__tests__/project-store.test.ts src/components/app-chrome/__tests__/project-switcher.test.tsx`
Expected: FAIL — `activeProject` initial `"default"`, `reconcile is not a function`, `ProjectScopeReconciler` not exported, `STALE_SCOPE_NOTICE` undefined. One new test passes already and is expected to: "offers All projects first" pins existing behaviour (`project-switcher.tsx:87-93`).

- [ ] **Step 4: Rewrite the store**

Replace `frontend/src/stores/project-store.ts` with:

```ts
import { create } from "zustand"
import { persist } from "zustand/middleware"

/** The backend's own default (`memories.project` column default, doc 04 §3):
 *  where an unscoped capture lands. It is not the scope a session opens on —
 *  an install whose corpus never used it would open on an empty view. */
export const DEFAULT_PROJECT = "default"

/**
 * "Every project" — the absence of a scope, not a project named something.
 *
 * `null` rather than a reserved string because `memories.project` is free
 * text: any sentinel spelling could also be a real project name, and the two
 * would then be indistinguishable at the request boundary. A null scope is
 * simply not sent, and every consuming endpoint already reads an absent
 * `project` as wide (`MemorySearchRequest.project` and `/graph/unified`'s
 * query param are both `str | None`, and the graph service applies no memory
 * filter at all when it is None).
 */
export const ALL_PROJECTS = null

export type ProjectScope = string | typeof ALL_PROJECTS

export const STALE_SCOPE_NOTICE = "Saved project not found — showing all"

/** What the scope is called in the chrome. */
export function projectLabel(project: ProjectScope): string {
  return project ?? "all projects"
}

interface ProjectState {
  /**
   * The global isolation/scope boundary (doc 13 §3) — the project switcher
   * writes here, and it rides into every project-scoped query key via
   * `src/lib/query-keys.ts`. This is NOT the session `applies_when`
   * context declaration; see `context-store.ts` for that, and never let
   * the two read from or write into each other.
   *
   * `null` means every project; see `ALL_PROJECTS`.
   */
  activeProject: ProjectScope
  /** A persisted scope the corpus no longer holds. Kept only so the switcher
   *  can explain why the view widened; never persisted. */
  missingProject: string | null
  setProject: (project: ProjectScope) => void
  reconcile: (known: readonly string[]) => void
}

export const useProjectStore = create<ProjectState>()(
  persist(
    (set, get) => ({
      activeProject: ALL_PROJECTS,
      missingProject: null,

      setProject: (project: ProjectScope) => {
        if (project === ALL_PROJECTS) {
          set({ activeProject: ALL_PROJECTS, missingProject: null })
          return
        }
        const trimmed = project.trim()
        if (!trimmed) return
        set({ activeProject: trimmed, missingProject: null })
      },

      reconcile: (known: readonly string[]) => {
        const active = get().activeProject
        if (active === ALL_PROJECTS || known.includes(active)) return
        set({ activeProject: ALL_PROJECTS, missingProject: active })
      },
    }),
    {
      name: "darkmem-project",
      partialize: (state) => ({ activeProject: state.activeProject }),
    },
  ),
)
```

- [ ] **Step 5: Add the reconciler and the notice to the switcher**

In `frontend/src/components/app-chrome/project-switcher.tsx`, change the first import to:

```ts
import { useEffect, useState } from "react"
```

and the store import to:

```ts
import {
  ALL_PROJECTS,
  STALE_SCOPE_NOTICE,
  projectLabel,
  useProjectStore,
  type ProjectScope,
} from "@/stores/project-store"
```

Insert this component directly above `export function ProjectSwitcher()`:

```tsx
/** Widens a persisted scope the corpus no longer holds. Mounted once in the
 *  authenticated layout rather than inside the switcher, because below `md`
 *  the switcher lives in a popover that is not mounted until opened. */
export function ProjectScopeReconciler() {
  const { data, isSuccess } = useProjects()
  const reconcile = useProjectStore((s) => s.reconcile)

  useEffect(() => {
    if (!isSuccess || !data) return
    reconcile(data.filter((p) => p.kind !== "personal").map((p) => p.name))
  }, [data, isSuccess, reconcile])

  return null
}
```

Inside `ProjectSwitcher`, add after the `setProject` selector:

```ts
  const missingProject = useProjectStore((s) => s.missingProject)
```

and wrap the returned `<Popover>…</Popover>` so the notice renders beside the trigger:

```tsx
  return (
    <span className="inline-flex items-center gap-2">
      <Popover open={open} onOpenChange={setOpen}>
        {/* the existing PopoverTrigger and PopoverContent, unchanged */}
      </Popover>
      {missingProject && (
        <span
          role="status"
          className="text-muted-foreground text-xs whitespace-nowrap"
        >
          {STALE_SCOPE_NOTICE}
        </span>
      )}
    </span>
  )
```

(The comment line stands for the two existing children, moved verbatim; do not type it.)

- [ ] **Step 6: Export and mount the reconciler**

In `frontend/src/components/app-chrome/index.ts`, change line 5 to:

```ts
export { ProjectScopeReconciler, ProjectSwitcher } from "./project-switcher"
```

In `frontend/src/routes/_authenticated.tsx`, add `ProjectScopeReconciler` to the `@/components/app-chrome` import list, and add it on the line after `{!DEMO && <LiveUpdates />}`:

```tsx
        <ProjectScopeReconciler />
```

- [ ] **Step 7: Run tests to verify they pass**

Run: `npx vitest run src/stores src/components/app-chrome src/lib src/hooks/api`
Expected: PASS. Any test that relied on the old implicit `"default"` scope without setting it fails with a project mismatch; set the store explicitly in that test's `beforeEach` (`useProjectStore.setState({ activeProject: DEFAULT_PROJECT, missingProject: null })`) and name the file in the commit body.

- [ ] **Step 8: Typecheck and run the whole unit suite**

Run: `npm run typecheck && npm test`
Expected: exit 0; the whole suite green.

- [ ] **Step 9: Commit**

```bash
git add frontend/src/stores frontend/src/components/app-chrome frontend/src/routes/_authenticated.tsx
git commit -m "feat(scope): open every session on all projects" -m "A persisted scope the corpus no longer holds widens to all projects" -m "and the switcher says so." -m "Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

### Task 5: Code pages opt out of project scope

Spec §B, "Code pages" and "context chip" bullets. On `/code/*` the switcher renders disabled with the spec's tooltip, and the five inline disclaimers go. The context chip gains a help tooltip; its wording and dashed style do not change.

**Files:**
- Modify: `frontend/src/components/app-chrome/project-switcher.tsx`
- Modify: `frontend/src/components/app-chrome/context-chip.tsx:1-12,30-56`
- Modify: `frontend/src/routes/_authenticated.tsx:43-52,235-243`
- Modify: `frontend/src/features/code/components/repositories-tab.tsx:205-218`
- Modify: `frontend/src/features/code/components/code-graph-tab.tsx:287-290`
- Modify: `frontend/src/features/code/components/real-code-graph-view.tsx:211-214`
- Modify: `frontend/src/features/code/components/wiki-tab.tsx:178,210-212`
- Modify: `frontend/src/features/code/components/real-wiki-view.tsx:117-119`
- Modify: `frontend/src/routes/_authenticated/code_.graph.tsx:32`, `frontend/src/routes/_authenticated/code_.repositories.tsx:20`
- Modify: `frontend/src/features/code/__tests__/code-tabs.test.tsx:24-28,70-72,139-141`
- Test: `frontend/src/components/app-chrome/__tests__/project-switcher.test.tsx`, `frontend/src/components/app-chrome/__tests__/context-chip.test.tsx`

**Interfaces:**
- Consumes: `ProjectSwitcher` and the store from Task 4.
- Produces: `CODE_SCOPE_REASON`, `projectScopeDisabledReason`, `ProjectSwitcher({ disabledReason })` (Contracts). Task 9 passes `projectScopeDisabledReason(pathname)` through `HeaderControls`.

**Implementer:** dr-superpowers:impl-opus-low
**Evaluation:** files 2 - spec 0 - coupling 1 - risk 1 = 4

- [ ] **Step 1: Write the failing tests**

In `frontend/src/components/app-chrome/__tests__/project-switcher.test.tsx`, extend the switcher import:

```ts
import {
  CODE_SCOPE_REASON,
  ProjectScopeReconciler,
  ProjectSwitcher,
  projectScopeDisabledReason,
} from "../project-switcher"
```

and append:

```ts
describe("project scope on code pages", () => {
  it("names the code routes and nothing else", () => {
    expect(projectScopeDisabledReason("/code/graph")).toBe(CODE_SCOPE_REASON)
    expect(projectScopeDisabledReason("/code/repositories")).toBe(CODE_SCOPE_REASON)
    expect(projectScopeDisabledReason("/code")).toBe(CODE_SCOPE_REASON)
    expect(projectScopeDisabledReason("/codex")).toBeUndefined()
    expect(projectScopeDisabledReason("/memories")).toBeUndefined()
  })

  it("renders the switcher disabled, explaining why", async () => {
    mockUseProjects.mockReturnValue({ data: [], isLoading: false })
    const user = userEvent.setup()
    const qc = new QueryClient()
    render(
      <QueryClientProvider client={qc}>
        <ProjectSwitcher disabledReason={CODE_SCOPE_REASON} />
      </QueryClientProvider>,
    )
    expect(screen.getByRole("button", { name: /project scope/i })).toBeDisabled()
    await user.hover(screen.getByLabelText(`Project scope — ${CODE_SCOPE_REASON}`))
    expect(await screen.findAllByText(CODE_SCOPE_REASON)).not.toHaveLength(0)
  })
})
```

In `frontend/src/components/app-chrome/__tests__/context-chip.test.tsx`, append inside the `describe`:

```ts
  it("explains what a session context does, without changing the chip", () => {
    render(<ContextChip />)
    expect(
      screen.getByRole("button", { name: "About context hints" }),
    ).toBeInTheDocument()
    const chip = screen.getByRole("button", { name: "Session context" })
    expect(chip).toHaveTextContent("context: not declared")
    expect(chip.className).toMatch(/border-dashed/)
    expect(chip.className).toMatch(/italic/)
  })
```

In `frontend/src/features/code/__tests__/code-tabs.test.tsx`, replace the three disclaimer assertions:

- lines 24-28 with
  ```ts
      expect(screen.queryByText("gated by repository, not project")).toBeNull()
      expect(screen.queryByText("not applied here")).toBeNull()
  ```
- lines 70-72 with
  ```ts
      expect(screen.queryByText("scope: repository, not project")).toBeNull()
  ```
- lines 139-141 with
  ```ts
      expect(
        screen.queryByText("repo-scoped — not the project switcher"),
      ).toBeNull()
  ```

- [ ] **Step 2: Run tests to verify they fail**

Run: `npx vitest run src/components/app-chrome src/features/code/__tests__/code-tabs.test.tsx`
Expected: FAIL — `projectScopeDisabledReason` is not a function, no "About context hints" button, and the three disclaimers still render.

- [ ] **Step 3: Add the disabled state to the switcher**

In `frontend/src/components/app-chrome/project-switcher.tsx`, add the tooltip import after the popover import:

```ts
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "darkraise-ui/components/tooltip"
```

add below the imports:

```ts
export const CODE_SCOPE_REASON = "Code is scoped by repository, not by project"

/** Code routes browse one repository at a time; a project scope would read
 *  as a filter that silently does nothing there. */
export function projectScopeDisabledReason(pathname: string): string | undefined {
  return pathname === "/code" || pathname.startsWith("/code/")
    ? CODE_SCOPE_REASON
    : undefined
}

const TRIGGER_CLASS =
  "border-border bg-muted hover:bg-muted/70 inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-sm transition-colors"
```

change the signature to:

```tsx
export function ProjectSwitcher({
  disabledReason,
}: {
  disabledReason?: string
}) {
```

give the existing trigger button `className={TRIGGER_CLASS}` (replacing its inline string), and add this early return after the `isAll` line:

```tsx
  if (disabledReason) {
    return (
      <TooltipProvider delayDuration={150}>
        <Tooltip>
          <TooltipTrigger asChild>
            {/* A disabled button receives no pointer events, so the wrapper
                carries the hover and the focus that open the tooltip. */}
            <span
              tabIndex={0}
              aria-label={`Project scope — ${disabledReason}`}
              className="inline-flex rounded-full"
            >
              <button
                type="button"
                disabled
                aria-label="Project scope"
                className={cn(TRIGGER_CLASS, "pointer-events-none opacity-60")}
              >
                <Globe aria-hidden className="text-muted-foreground h-3.5 w-3.5" />
                project: {projectLabel(activeProject)}
              </button>
            </span>
          </TooltipTrigger>
          <TooltipContent>{disabledReason}</TooltipContent>
        </Tooltip>
      </TooltipProvider>
    )
  }
```

- [ ] **Step 4: Add the context chip's help tooltip**

In `frontend/src/components/app-chrome/context-chip.tsx`, add the import:

```ts
import { HelpTip } from "@/components/darkmem"
```

and wrap the returned `<Popover>…</Popover>` in a span that adds the tooltip after it:

```tsx
  return (
    <span className="inline-flex items-center gap-1">
      <Popover
        open={open}
        onOpenChange={(next) => {
          setOpen(next)
          if (next) setDraft(declared?.axes ?? {})
        }}
      >
        {/* the existing PopoverTrigger and PopoverContent, unchanged */}
      </Popover>
      <HelpTip label="About context hints" side="bottom">
        A session context is a retrieval hint, not a filter. Declaring an
        environment, situation or version ranks memories recorded under a
        matching context higher and sets aside ones that conflict with it. The
        project switcher is what limits the data you see.
      </HelpTip>
    </span>
  )
```

(The comment line stands for the two existing children, moved verbatim; do not type it.)

- [ ] **Step 5: Pass the reason from the layout**

In `frontend/src/routes/_authenticated.tsx`, import `projectScopeDisabledReason` from `@/components/app-chrome/project-switcher` and change the switcher in `headerSlot` to:

```tsx
            <ProjectSwitcher
              disabledReason={projectScopeDisabledReason(pathname)}
            />
```

- [ ] **Step 6: Remove the five disclaimers and the two description tails**

- `features/code/components/repositories-tab.tsx`: delete lines 205-218 — the JSX comment starting "The global project switcher is shown inert here" and the whole `<div className="border-border flex flex-wrap …">` holding the "not applied here" and "gated by repository, not project" pills. Remove `ChevronsLeftRight` from the `lucide-react` import (its only other use was that pill).
- `features/code/components/code-graph-tab.tsx`: delete the `<span …>` holding `scope: repository, not project` (lines 287-290) and remove `ChevronsLeftRight` from the `lucide-react` import.
- `features/code/components/real-code-graph-view.tsx`: delete the `<span …>` holding `scope: repository, not project` (lines 211-214) and remove `ChevronsLeftRight` from the `lucide-react` import.
- `features/code/components/wiki-tab.tsx`: delete the JSX comment `{/* repo picker — deliberately NOT the project switcher */}` (line 178) and the `<span …>repo-scoped — not the project switcher</span>` (lines 210-212).
- `features/code/components/real-wiki-view.tsx`: delete the `<span …>repo-scoped — not the project switcher</span>` (lines 117-119).
- `routes/_authenticated/code_.graph.tsx:32`: `description="The symbol graph of an indexed repository."`
- `routes/_authenticated/code_.repositories.tsx:20`: `description="Indexed repositories and their indexing pipelines."`

- [ ] **Step 7: Run tests to verify they pass**

Run: `npx vitest run src/components/app-chrome src/features/code && npm run typecheck`
Expected: PASS; typecheck exit 0. `rg -n "not applied here|scope: repository, not project|gated by repository|not the project switcher" src --glob '!*.test.*'` prints nothing.

- [ ] **Step 8: Commit**

```bash
git add frontend/src/components/app-chrome frontend/src/routes frontend/src/features/code
git commit -m "feat(scope): disable the switcher on code pages" -m "Replaces the five inline repository-scope disclaimers, and adds a" -m "help tooltip to the context chip." -m "Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

### Task 6: Memories and Documents read the global scope

Spec §B, "Remove page-level project controls" (Memories) and the `/documents` chooser bullet. Both Memories views drop their own project control and read the store; the results header keeps naming the scope. `/documents` under all projects renders a chooser whose buttons set the store, and the `?project=` search param is removed.

**Files:**
- Modify: `frontend/src/features/memories/components/real-memories-view.tsx:1,28-41,72,131-141,244-266`
- Modify: `frontend/src/routes/_authenticated/memories.tsx:63,239-280`
- Modify: `frontend/src/routes/_authenticated/documents.tsx` (whole file)
- Modify: `frontend/src/routes/_authenticated/__tests__/documents.test.tsx` (whole file)
- Modify: `frontend/src/features/memories/__tests__/real-memories-view.test.tsx`
- Modify: `frontend/tests/honesty/labels-always-render.spec.ts:1,35-40,64-66`
- Modify: `frontend/tests/honesty/exclusions-on-empty.spec.ts:1,35-43`

**Interfaces:**
- Consumes: `useProjectStore`, `ALL_PROJECTS`, `projectLabel` (Task 4); `useProjects()` serving `DEMO_PROJECTS` in demo (Task 2).
- Produces: the Documents chooser, which Task 8 moves into the shared `ProjectChooser`.

**Implementer:** dr-superpowers:impl-opus-low
**Evaluation:** files 2 - spec 0 - coupling 1 - risk 1 = 4

- [ ] **Step 1: Write the failing Memories test**

In `frontend/src/features/memories/__tests__/real-memories-view.test.tsx`, add the store import below the existing imports:

```ts
import { ALL_PROJECTS, useProjectStore } from "@/stores/project-store"
```

change the `beforeEach` to:

```ts
  beforeEach(() => {
    vi.clearAllMocks()
    useProjectStore.setState({ activeProject: ALL_PROJECTS, missingProject: null })
  })
```

and append inside the `describe`:

```ts
  it("scopes by the header switcher and offers no project field of its own", async () => {
    useProjectStore.setState({ activeProject: "acme", missingProject: null })
    vi.mocked(apiFetch).mockResolvedValue({
      items: [],
      total: 0,
      limit: 50,
      offset: 0,
      envelope: {
        query: "",
        channels: { semantic: { ran: false }, keyword: { ran: false } },
        reranked: false,
        weights: { semantic_weight: 0.7 },
        excluded: {},
      },
    })
    render(<RealMemoriesView />, { wrapper })

    expect(await screen.findByText("Results — project: acme")).toBeInTheDocument()
    expect(screen.queryByRole("textbox", { name: "Project scope" })).toBeNull()
    const bodies = vi
      .mocked(apiFetch)
      .mock.calls.map((call) => JSON.parse(String((call[1] as RequestInit | undefined)?.body ?? "{}")))
    expect(bodies.some((body) => body.project === "acme")).toBe(true)
  })
```

- [ ] **Step 2: Write the failing Documents tests**

Replace `frontend/src/routes/_authenticated/__tests__/documents.test.tsx` with:

```tsx
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import type { ComponentType, ReactNode } from "react"
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"

vi.mock("@/lib/demo-flag", () => ({ DEMO: false }))
vi.mock("@/lib/api", () => ({ apiFetch: vi.fn() }))
vi.mock("@tanstack/react-router", async () => {
  const actual = await vi.importActual<Record<string, unknown>>(
    "@tanstack/react-router",
  )
  return {
    ...actual,
    createFileRoute: () => (opts: Record<string, unknown>) => opts,
  }
})
vi.mock("@/features/documents/components/project-workspace", () => ({
  ProjectWorkspace: ({ project }: { project: string }) => (
    <div data-testid="workspace">{project}</div>
  ),
}))

import { apiFetch } from "@/lib/api"
import { usePageChrome } from "@/components/app-chrome"
import type { ProjectSummary } from "@/hooks/api"
import { ALL_PROJECTS, useProjectStore } from "@/stores/project-store"
import { Route } from "../documents"
import { FULL_HEIGHT_ROUTES, FULL_WIDTH_ROUTES } from "../../_authenticated"

function wrapper({ children }: { children: ReactNode }) {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  })
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>
}

function HeaderActions() {
  return <>{usePageChrome((s) => s.actions)}</>
}

function renderRoute() {
  const Component = (Route.options ?? Route).component as ComponentType
  render(
    <>
      <HeaderActions />
      <Component />
    </>,
    { wrapper },
  )
}

function mockProjects(
  rows: Array<Pick<ProjectSummary, "name" | "kind" | "document_count">>,
) {
  const full: ProjectSummary[] = rows.map((row) => ({
    memory_count: 0,
    checkpoint_count: 0,
    page_count: 0,
    last_checkpoint_at: null,
    last_event_day: null,
    ...row,
  }))
  vi.mocked(apiFetch).mockResolvedValue(full)
}

beforeEach(() => {
  useProjectStore.setState({ activeProject: ALL_PROJECTS, missingProject: null })
})
afterEach(() => vi.clearAllMocks())

describe("/documents route", () => {
  it("under all projects offers one button per project holding documents", async () => {
    mockProjects([
      { name: "empty", kind: "project", document_count: 0 },
      { name: "darkmem", kind: "project", document_count: 475 },
      { name: "other", kind: "project", document_count: 2 },
      { name: "notes", kind: "personal", document_count: 3 },
    ])
    renderRoute()
    expect(
      await screen.findByText("Documents open one project at a time"),
    ).toBeInTheDocument()
    expect(screen.getByRole("button", { name: /^darkmem/ })).toBeInTheDocument()
    expect(screen.getByRole("button", { name: /^other/ })).toBeInTheDocument()
    expect(screen.queryByRole("button", { name: /^empty/ })).toBeNull()
    expect(screen.queryByRole("button", { name: /^notes/ })).toBeNull()
    expect(screen.queryByTestId("workspace")).toBeNull()
  })

  it("a chooser click sets the global scope and opens that project", async () => {
    mockProjects([{ name: "darkmem", kind: "project", document_count: 475 }])
    renderRoute()
    await userEvent.click(await screen.findByRole("button", { name: /^darkmem/ }))
    expect(useProjectStore.getState().activeProject).toBe("darkmem")
    expect(await screen.findByTestId("workspace")).toHaveTextContent("darkmem")
  })

  it("opens the project the global scope names", async () => {
    useProjectStore.setState({ activeProject: "other", missingProject: null })
    mockProjects([
      { name: "darkmem", kind: "project", document_count: 475 },
      { name: "other", kind: "project", document_count: 2 },
    ])
    renderRoute()
    expect(await screen.findByTestId("workspace")).toHaveTextContent("other")
  })

  it("puts no project picker in the header", async () => {
    mockProjects([{ name: "darkmem", kind: "project", document_count: 475 }])
    renderRoute()
    await screen.findByText("Documents open one project at a time")
    expect(screen.queryByRole("combobox")).toBeNull()
  })

  it("says so when no project holds documents", async () => {
    mockProjects([{ name: "empty", kind: "project", document_count: 0 }])
    renderRoute()
    expect(
      await screen.findByText("No project holds documents yet"),
    ).toBeInTheDocument()
  })

  it("reports a failed project read instead of an empty corpus", async () => {
    vi.mocked(apiFetch).mockRejectedValue(new Error("boom"))
    renderRoute()
    expect(await screen.findByText(/could not be loaded/i)).toBeInTheDocument()
  })

  it("says so when the corpus holds no non-personal project", async () => {
    mockProjects([{ name: "notes", kind: "personal", document_count: 3 }])
    renderRoute()
    expect(await screen.findByText(/no project holds anything/i)).toBeInTheDocument()
  })

  it("claims the full height and width for its resizable split", () => {
    expect(FULL_HEIGHT_ROUTES).toContain("/documents")
    expect(FULL_WIDTH_ROUTES).toContain("/documents")
  })
})
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `npx vitest run src/features/memories/__tests__/real-memories-view.test.tsx src/routes/_authenticated/__tests__/documents.test.tsx`
Expected: FAIL — the Memories view reads "Results — project: all projects" and renders its own "Project scope" textbox; the Documents route renders no chooser.

- [ ] **Step 4: Make the real Memories view read the store**

In `frontend/src/features/memories/components/real-memories-view.tsx`:

Add the import:

```ts
import { ALL_PROJECTS, projectLabel, useProjectStore } from "@/stores/project-store"
```

Replace `const [project, setProject] = useState("")` (line 30) with:

```ts
  const activeProject = useProjectStore((s) => s.activeProject)
  const setScope = useProjectStore((s) => s.setProject)
```

In the `useMemorySearchPage` call, replace `project: project.trim() || "all",` with:

```ts
      project: activeProject ?? "all",
```

Add, directly after the second `useEffect` (the one resetting `loadingRef`):

```ts
  useEffect(() => {
    setLimit(PAGE)
  }, [activeProject])
```

Replace `const scopeLabel = project.trim() || "all projects"` with:

```ts
  const scopeLabel = projectLabel(activeProject)
```

Delete the second `<Input … aria-label="Project scope" />` (lines 132-141). In the "No matches" description replace

```ts
                project.trim() ? ` in project ${project.trim()}` : ""
```

with

```ts
                activeProject ? ` in project ${activeProject}` : ""
```

and replace the project-empty branch (`) : project.trim() ? (` through its `</Button>` action) with:

```tsx
          ) : activeProject ? (
            <EmptyState
              kind="empty"
              icon={Brain}
              scope="page"
              title={`No memories in project ${activeProject}`}
              description="This project has no memories yet — other projects might."
              action={
                <Button variant="outline" onClick={() => setScope(ALL_PROJECTS)}>
                  Show all projects
                </Button>
              }
            />
```

- [ ] **Step 5: Make the demo Memories page read the store**

In `frontend/src/routes/_authenticated/memories.tsx`, add the import:

```ts
import { ALL_PROJECTS, useProjectStore } from "@/stores/project-store"
```

replace `const [scope, setScope] = useState("all")` (line 63) with:

```ts
  const activeProject = useProjectStore((s) => s.activeProject)
  const setProject = useProjectStore((s) => s.setProject)
  const scope = activeProject ?? "all"
  const setScope = (next: string) =>
    setProject(next === "all" ? ALL_PROJECTS : next)
```

replace the comment above the search bar (lines 239-241) with:

```tsx
      {/* Search bar: the query and the session context. The project scope is
          the header switcher; the context declares the session applies_when —
          conflating them would silently exclude rows. */}
```

and delete the project `<Select value={scope} onValueChange={setScope}>…</Select>` block (lines 265-280). The `Select` imports stay: the context control still uses them.

- [ ] **Step 6: Rewrite the Documents route**

Replace `frontend/src/routes/_authenticated/documents.tsx` with:

```tsx
import { createFileRoute } from "@tanstack/react-router"
import { FileText } from "lucide-react"
import { Button } from "darkraise-ui/components/button"
import { Skeleton } from "darkraise-ui/components/skeleton"
import { PageChrome } from "@/components/app-chrome"
import { EmptyState } from "@/components/darkmem"
import { ProjectWorkspace } from "@/features/documents/components/project-workspace"
import { useProjects, type ProjectSummary } from "@/hooks/api"
import { ALL_PROJECTS, useProjectStore } from "@/stores/project-store"

export const Route = createFileRoute("/_authenticated/documents")({
  component: DocumentsPage,
})

function DocumentsPage() {
  const { data, isLoading, isError } = useProjects()
  const activeProject = useProjectStore((s) => s.activeProject)
  const setProject = useProjectStore((s) => s.setProject)
  // The notes space has its own route and its own workspace (`/notes`); this
  // is the corpus browser, so the personal project never appears here.
  const rows = (data ?? []).filter((p) => p.kind !== "personal")
  const project =
    activeProject !== ALL_PROJECTS && rows.some((p) => p.name === activeProject)
      ? activeProject
      : null

  return (
    <div className="flex flex-col gap-4 lg:h-full lg:min-h-0">
      <PageChrome
        icon={FileText}
        title="Documents"
        description="Browse, search and question the documents filed into each project."
      />
      {isError ? (
        <p className="text-destructive text-sm">
          Projects could not be loaded — a failed read, not an empty corpus.
        </p>
      ) : isLoading ? (
        <Skeleton className="h-64 w-full" />
      ) : rows.length === 0 ? (
        <EmptyState
          kind="empty"
          icon={FileText}
          title="No project holds anything yet"
          description="A project appears here once a memory, document or checkpoint carries its name."
        />
      ) : project ? (
        // Remounted per project: every piece of workspace state (selection,
        // expansion, search focus) is meaningful only within one project.
        <ProjectWorkspace key={project} project={project} />
      ) : (
        <DocumentsProjectChooser
          projects={rows.filter((p) => p.document_count > 0)}
          onChoose={setProject}
        />
      )}
    </div>
  )
}

/** The workspace is one project's tree, so "all projects" has nothing to
 *  render; picking here sets the same global scope the header switcher does. */
function DocumentsProjectChooser({
  projects,
  onChoose,
}: {
  projects: ProjectSummary[]
  onChoose: (project: string) => void
}) {
  if (projects.length === 0) {
    return (
      <EmptyState
        kind="empty"
        icon={FileText}
        title="No project holds documents yet"
        description="Documents appear here once an agent files one into a project."
      />
    )
  }
  return (
    <section
      aria-labelledby="documents-chooser-title"
      className="border-border bg-card mx-auto w-full max-w-xl space-y-3 rounded-lg border p-5"
    >
      <h2 id="documents-chooser-title" className="text-sm font-semibold">
        Documents open one project at a time
      </h2>
      <p className="text-muted-foreground text-sm">
        Pick a project to browse its documents. The project switcher in the
        header changes it later.
      </p>
      <div className="flex flex-wrap gap-2">
        {projects.map((p) => (
          <Button key={p.name} variant="outline" onClick={() => onChoose(p.name)}>
            {p.name}
            <span className="text-muted-foreground ml-2 text-xs">
              {p.document_count} {p.document_count === 1 ? "document" : "documents"}
            </span>
          </Button>
        ))}
      </div>
    </section>
  )
}
```

- [ ] **Step 7: Point the honesty specs at the header switcher**

In `frontend/tests/honesty/labels-always-render.spec.ts` and `frontend/tests/honesty/exclusions-on-empty.spec.ts`, add below the `@playwright/test` import (and add `type Page` to that import in `exclusions-on-empty.spec.ts`):

```ts
/** The header switcher is the one project scope; its rows are named
 *  "<project><N> items". */
async function selectProject(page: Page, name: string) {
  await page.getByRole("button", { name: "Project scope" }).click()
  await page
    .getByRole("button", { name: new RegExp(`^${name}\\s*\\d+ items?$`) })
    .click()
}
```

In `labels-always-render.spec.ts`, replace the four-line comment plus the `scopeTrigger` lines of the first test (lines 35-40) with `await selectProject(page, "darkmem")`, and the `scopeTrigger` lines of the second test (lines 64-66) with `await selectProject(page, "darkmem")`.

In `exclusions-on-empty.spec.ts`, delete the comment and the `scopeTrigger` declaration and visibility assertion (lines 35-39), and replace

```ts
    await scopeTrigger.click()
    await page.getByRole("option", { name: "default" }).click()
```

with

```ts
    await selectProject(page, "default")
```

- [ ] **Step 8: Run tests to verify they pass**

Run: `npx vitest run src/features/memories src/routes/_authenticated/__tests__/documents.test.tsx && npm run typecheck`
Expected: PASS; typecheck exit 0.
Run: `E2E_API_TARGET=http://127.0.0.1:9 timeout 900 npx playwright test --project=demo-fixture tests/honesty tests/demo-makes-no-api-calls.spec.ts`
Expected: every test passes.

- [ ] **Step 9: Commit**

```bash
git add frontend/src/features/memories frontend/src/routes/_authenticated/memories.tsx frontend/src/routes/_authenticated/documents.tsx frontend/src/routes/_authenticated/__tests__/documents.test.tsx frontend/tests/honesty
git commit -m "feat(scope): scope Memories and Documents globally" -m "Documents under all projects offers a chooser that sets the scope;" -m "the ?project= search param is gone." -m "Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

### Task 7: Knowledge, graph and chat pages read the global scope

Spec §B, "Remove page-level project controls" for Facts, Review, Articles, Memory Graph and the Chat thread header. The Memory Graph select and the Chat chip live in the demo explorer and demo pane (Assumptions); the real pages already read the store. Result headers keep naming the scope.

**Files:**
- Modify: `frontend/src/features/knowledge/components/facts-tab.tsx:26,123-152,168-171,258-317,452-459`
- Modify: `frontend/src/features/knowledge/components/review-tab.tsx` (whole file)
- Modify: `frontend/src/features/knowledge/components/articles-tab.tsx:172-233`
- Modify: `frontend/src/features/memory-graph/components/memory-graph-explorer.tsx:1-70,171-184,196-210`
- Modify: `frontend/src/features/chat/components/demo-message-pane.tsx:2,41-46`
- Modify: `frontend/src/features/knowledge/__tests__/facts-tab.render.test.tsx:104-123`
- Modify: `frontend/src/features/memory-graph/__tests__/memory-graph.test.tsx`
- Modify: `frontend/src/features/chat/__tests__/demo-chat.test.tsx:84`
- Create: `frontend/src/features/knowledge/components/__tests__/review-tab-scope.test.tsx`

**Interfaces:**
- Consumes: `useProjectStore`, `ALL_PROJECTS`, `projectLabel` (Task 4).
- Produces: nothing other tasks name. Task 21 edits `review-tab.tsx` again (the mode switch).

**Implementer:** dr-superpowers:impl-opus-low
**Evaluation:** files 2 - spec 0 - coupling 1 - risk 1 = 4

- [ ] **Step 1: Write the failing tests**

In `frontend/src/features/knowledge/__tests__/facts-tab.render.test.tsx`, add the import:

```ts
import { useProjectStore } from "@/stores/project-store"
```

set `useProjectStore.setState({ activeProject: null, missingProject: null })` in the `beforeEach` of `describe("FactsTab — the project scope reaches the route as the route defines it", …)`, and append inside that describe:

```ts
  it("scopes by the header switcher and offers no project select", async () => {
    useProjectStore.setState({ activeProject: "acme", missingProject: null })
    vi.mocked(apiFetch).mockResolvedValue(page([item()], 1))
    render(<FactsTab />, { wrapper })

    await screen.findByText("darkmem uses postgres")
    expect(urls()[0]).toContain("project=acme")
    expect(screen.getByText(/Facts — project: acme/)).toBeInTheDocument()
    expect(screen.queryByRole("combobox", { name: "Project scope" })).toBeNull()
  })
```

Create `frontend/src/features/knowledge/components/__tests__/review-tab-scope.test.tsx`:

```tsx
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { render, screen, waitFor } from "@testing-library/react"
import type { ReactNode } from "react"
import { beforeEach, describe, expect, it, vi } from "vitest"

vi.mock("@/lib/demo-flag", () => ({ DEMO: false }))
vi.mock("@/lib/api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/api")>()),
  apiFetch: vi.fn(),
}))
vi.mock("@tanstack/react-router", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@tanstack/react-router")>()),
  Link: ({ children }: { children?: ReactNode }) => <a>{children}</a>,
}))

import { apiFetch } from "@/lib/api"
import { useProjectStore } from "@/stores/project-store"
import { ReviewTab } from "../review-tab"

function wrapper({ children }: { children: ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>
}

describe("ReviewTab scope", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(apiFetch).mockRejectedValue(new Error("offline"))
  })

  it("sends the header switcher's project and offers no project field", async () => {
    useProjectStore.setState({ activeProject: "darkmem", missingProject: null })
    render(<ReviewTab />, { wrapper })
    await waitFor(() =>
      expect(
        vi.mocked(apiFetch).mock.calls.some((call) =>
          String(call[0]).includes("project=darkmem"),
        ),
      ).toBe(true),
    )
    expect(screen.queryByRole("textbox", { name: "Project filter" })).toBeNull()
  })
})
```

In `frontend/src/features/memory-graph/__tests__/memory-graph.test.tsx`, change the vitest import to `import { beforeEach, describe, it, expect } from "vitest"` and add:

```ts
import { useProjectStore } from "@/stores/project-store"
```

and inside the `describe`, before the first `it`:

```ts
  beforeEach(() => {
    useProjectStore.setState({ activeProject: "darkmem", missingProject: null })
  })
```

and append:

```ts
  it("reads the header scope and offers no project select", () => {
    render(<MemoryGraphExplorer />)
    expect(screen.queryByRole("combobox", { name: "Project scope" })).toBeNull()
  })
```

In `frontend/src/features/chat/__tests__/demo-chat.test.tsx`, append to the second `DemoMessagePane` test (after line 83):

```ts
    expect(screen.queryByText("project: darkmem")).toBeNull()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `npx vitest run src/features/knowledge src/features/memory-graph src/features/chat`
Expected: FAIL — Facts sends no `project=acme` and renders its own select; ReviewTab sends no project and renders the "Project filter" field; the explorer renders its select; the pane renders "project: darkmem".

- [ ] **Step 3: Facts**

In `frontend/src/features/knowledge/components/facts-tab.tsx`:

Add the import:

```ts
import { useProjectStore } from "@/stores/project-store"
```

Replace `const [project, setProject] = useState(ALL_PROJECTS)` (line 127) with:

```ts
  const activeProject = useProjectStore((s) => s.activeProject)
  const setScope = useProjectStore((s) => s.setProject)
  const project = activeProject ?? ALL_PROJECTS
```

Remove `projects,` from the `useFactRows` destructuring (line 149). Replace the controls comment (lines 259-261) with:

```tsx
      {/* Distinct controls, never one ambiguous "filters" blob: subject
          free-texts, relation and status constrain their columns. The project
          scope is the header switcher (the isolation boundary). */}
```

Delete the project `<Select value={project} onValueChange={setProject}>…</Select>` block (lines 303-317). In the "Clear filters" action replace `setProject(ALL_PROJECTS)` with `setScope(null)`.

- [ ] **Step 4: Review**

Replace `frontend/src/features/knowledge/components/review-tab.tsx` with:

```tsx
import { useState } from "react"
import {
  ToggleGroup,
  ToggleGroupItem,
} from "darkraise-ui/components/toggle-group"
import { useProjectStore } from "@/stores/project-store"
import { ReviewQueue } from "./review-queue"
import { HygieneQueue } from "./hygiene-queue"

type TriageMode = "review" | "hygiene"

// One shared triage shell, two visibly distinct modes: Review adjudicates
// truth over facts/articles, Hygiene curates housekeeping over L0 memories —
// disjoint tables by construction (app/services/hygiene_queue.py), so the
// two queues can never share a row. Switching the tab swaps the query, not
// the URL; both queues take the header switcher's project scope and apply it
// to their own backend routes.
export function ReviewTab() {
  const [mode, setMode] = useState<TriageMode>("review")
  const project = useProjectStore((s) => s.activeProject) ?? undefined

  return (
    <div className="space-y-4">
      <div className="border-border flex flex-wrap items-center gap-2.5 border-b border-dashed pb-3">
        <ToggleGroup
          type="single"
          size="sm"
          value={mode}
          onValueChange={(value) => {
            if (value === "review" || value === "hygiene") setMode(value)
          }}
          aria-label="Triage mode"
        >
          <ToggleGroupItem value="review">Review — truth</ToggleGroupItem>
          <ToggleGroupItem value="hygiene">Hygiene — housekeeping</ToggleGroupItem>
        </ToggleGroup>
        <span className="text-muted-foreground font-mono text-sm">
          /knowledge · {mode}
        </span>
      </div>
      {mode === "review" ? (
        <ReviewQueue project={project} />
      ) : (
        <HygieneQueue project={project} />
      )}
    </div>
  )
}
```

(The mode switch and the `/knowledge · {mode}` label are Task 21's.)

- [ ] **Step 5: Articles**

In `frontend/src/features/knowledge/components/articles-tab.tsx`, add the import:

```ts
import { useProjectStore } from "@/stores/project-store"
```

In `ArticlesTab`, delete the five-line comment starting `"darkmem" is the *demo* fixture's project` and replace `const [project, setProject] = useState(DEMO ? "darkmem" : "all")` with:

```ts
  const project = useProjectStore((s) => s.activeProject) ?? "all"
```

Delete the `projects` `useMemo` (the block computing distinct project names) and the whole `<Select value={project} onValueChange={setProject}>…</Select>`. Remove the `Select*` names from the `darkraise-ui/components/select` import (delete the import if nothing else uses it) and `useState` from the React import if it is now unused.

- [ ] **Step 6: Demo Memory Graph explorer**

In `frontend/src/features/memory-graph/components/memory-graph-explorer.tsx`:

Add the import:

```ts
import { ALL_PROJECTS, projectLabel, useProjectStore } from "@/stores/project-store"
```

Remove `distinctGraphProjects,` from the `@/demo/explore` import and the whole `darkraise-ui/components/select` import. Replace the two lines

```ts
  const projects = useMemo(() => distinctGraphProjects(graph), [graph])
  const [project, setProject] = useState(projects[0] ?? "darkmem")
```

with

```ts
  const project = useProjectStore((s) => s.activeProject)
```

and the `scoped` memo with:

```ts
  const scoped = useMemo(
    () => (project === ALL_PROJECTS ? graph : scopeMemoryGraph(graph, project)),
    [graph, project],
  )
```

Delete the `<Select value={project} onValueChange={setProject}>…</Select>` block in the toolbar. In the empty state replace `` `Project ${project} has no memories yet, …` `` with `` `${project === ALL_PROJECTS ? "No project" : `Project ${project}`} has no memories yet, …` `` (keep the rest of the sentence), and change the SVG's `aria-label` to begin `` `Entity graph for ${project === ALL_PROJECTS ? projectLabel(project) : `project ${project}`}: `` (keep the rest).

- [ ] **Step 7: Demo chat pane**

In `frontend/src/features/chat/components/demo-message-pane.tsx`, delete the JSX comment "Two distinct chips, never conflated…" and the `<span …>` holding `project: darkmem` (lines 41-46), and remove `Globe` from the `lucide-react` import.

- [ ] **Step 8: Run tests to verify they pass**

Run: `npx vitest run src/features/knowledge src/features/memory-graph src/features/chat && npm run typecheck`
Expected: PASS; typecheck exit 0.
Run: `E2E_API_TARGET=http://127.0.0.1:9 timeout 900 npx playwright test --project=demo-fixture tests/demo-makes-no-api-calls.spec.ts tests/honesty`
Expected: every test passes.

- [ ] **Step 9: Commit**

```bash
git add frontend/src/features/knowledge frontend/src/features/memory-graph frontend/src/features/chat
git commit -m "feat(scope): remove page-level project controls" -m "Facts, Review, Articles, the demo graph and the demo chat pane now" -m "read the header switcher's scope." -m "Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

### Task 8: Topics follows the global scope

Owner-approved addition to spec §B (one project scope). Topics hardcoded `project = "default"` (`topics-tab.tsx:190`), so it ignored the switcher. It now reads the store; under all projects it renders the same "open one project at a time" chooser Documents uses, because topic detection runs per project. The chooser moves out of `documents.tsx` into one shared component that both pages use.

**Files:**
- Create: `frontend/src/components/app-chrome/project-chooser.tsx`
- Modify: `frontend/src/components/app-chrome/index.ts`
- Modify: `frontend/src/routes/_authenticated/documents.tsx` (the `DocumentsProjectChooser` Task 6 added)
- Modify: `frontend/src/features/knowledge/components/topics-tab.tsx` (imports at lines 1-35; `export function TopicsTab` at line 190)
- Modify: `frontend/src/features/knowledge/__tests__/topics-tab.render.test.tsx:16,65`
- Create: `frontend/src/features/knowledge/__tests__/topics-scope.test.tsx`

**Interfaces:**
- Consumes: `useProjectStore`, `ALL_PROJECTS` (Task 4); `useProjects()` serving `DEMO_PROJECTS` in demo (Task 2); the Documents chooser copy (Task 6).
- Produces: `ProjectChooser` (Contracts); `TopicsForProject({ project })` exported from `topics-tab.tsx`.

**Implementer:** dr-superpowers:impl-opus-low
**Evaluation:** files 2 - spec 0 - coupling 1 - risk 1 = 4

- [ ] **Step 1: Write the failing test**

Create `frontend/src/features/knowledge/__tests__/topics-scope.test.tsx`:

```tsx
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import type { ReactNode } from "react"
import { beforeEach, describe, expect, it, vi } from "vitest"

vi.mock("@/lib/demo-flag", () => ({ DEMO: false }))
vi.mock("@/lib/api", () => ({ apiFetch: vi.fn() }))

import { apiFetch } from "@/lib/api"
import { ALL_PROJECTS, useProjectStore } from "@/stores/project-store"
import { TopicsTab } from "../components/topics-tab"

function wrapper({ children }: { children: ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>
}

const PROJECTS = [
  { name: "darkmem", kind: "project", memory_count: 10, document_count: 0, checkpoint_count: 0, page_count: 0, last_checkpoint_at: null, last_event_day: null },
  { name: "docs-only", kind: "project", memory_count: 0, document_count: 4, checkpoint_count: 0, page_count: 0, last_checkpoint_at: null, last_event_day: null },
  { name: "notes", kind: "personal", memory_count: 0, document_count: 0, checkpoint_count: 0, page_count: 3, last_checkpoint_at: null, last_event_day: null },
]

beforeEach(() => {
  vi.clearAllMocks()
  vi.mocked(apiFetch).mockImplementation(async (url: string) => {
    if (url === "/projects") return PROJECTS
    throw new Error(`unscoped topics read: ${url}`)
  })
})

describe("TopicsTab scope", () => {
  it("under all projects offers the projects that hold memories, and reads no topics", async () => {
    useProjectStore.setState({ activeProject: ALL_PROJECTS, missingProject: null })
    render(<TopicsTab />, { wrapper })
    expect(await screen.findByText("Topics open one project at a time")).toBeInTheDocument()
    expect(screen.getByRole("button", { name: /^darkmem/ })).toBeInTheDocument()
    expect(screen.queryByRole("button", { name: /^docs-only/ })).toBeNull()
    expect(screen.queryByRole("button", { name: /^notes/ })).toBeNull()
    expect(
      vi.mocked(apiFetch).mock.calls.every((call) => call[0] === "/projects"),
    ).toBe(true)
  })

  it("a chooser click sets the global scope", async () => {
    useProjectStore.setState({ activeProject: ALL_PROJECTS, missingProject: null })
    render(<TopicsTab />, { wrapper })
    await userEvent.click(await screen.findByRole("button", { name: /^darkmem/ }))
    expect(useProjectStore.getState().activeProject).toBe("darkmem")
  })

  it("reads the scoped project's topics, never the hardcoded default", async () => {
    useProjectStore.setState({ activeProject: "darkmem", missingProject: null })
    render(<TopicsTab />, { wrapper })
    await vi.waitFor(() =>
      expect(
        vi.mocked(apiFetch).mock.calls.some((call) => String(call[0]).includes("darkmem")),
      ).toBe(true),
    )
    expect(
      vi.mocked(apiFetch).mock.calls.some((call) => String(call[0]).includes("default")),
    ).toBe(false)
  })
})
```

In `frontend/src/features/knowledge/__tests__/topics-tab.render.test.tsx`, change the import (line 16) to `import { TopicsForProject } from "../components/topics-tab"` and line 65 to `return render(<TopicsForProject project="darkmem" />, { wrapper: Wrapper })`.

- [ ] **Step 2: Run tests to verify they fail**

Run: `npx vitest run src/features/knowledge/__tests__/topics-scope.test.tsx src/features/knowledge/__tests__/topics-tab.render.test.tsx`
Expected: FAIL — no chooser text; topics are read for `default`; `TopicsForProject` is not exported.

- [ ] **Step 3: The shared chooser**

Create `frontend/src/components/app-chrome/project-chooser.tsx`:

```tsx
import type { LucideIcon } from "lucide-react"
import { Button } from "darkraise-ui/components/button"
import { EmptyState } from "@/components/darkmem"

export interface ChooserProject {
  name: string
  /** How much of this page's subject the project holds. */
  count: number
}

/** For pages that show one project at a time: under the all-projects scope
 *  they have nothing to render, so they offer the projects instead. A pick
 *  sets the same global scope the header switcher does. */
export function ProjectChooser({
  icon,
  heading,
  description,
  projects,
  noun,
  emptyTitle,
  emptyDescription,
  onChoose,
}: {
  icon: LucideIcon
  heading: string
  description: string
  projects: ChooserProject[]
  noun: { one: string; many: string }
  emptyTitle: string
  emptyDescription: string
  onChoose: (project: string) => void
}) {
  if (projects.length === 0) {
    return (
      <EmptyState
        kind="empty"
        icon={icon}
        title={emptyTitle}
        description={emptyDescription}
      />
    )
  }
  return (
    <section
      aria-labelledby="project-chooser-title"
      className="border-border bg-card mx-auto w-full max-w-xl space-y-3 rounded-lg border p-5"
    >
      <h2 id="project-chooser-title" className="text-sm font-semibold">
        {heading}
      </h2>
      <p className="text-muted-foreground text-sm">{description}</p>
      <div className="flex flex-wrap gap-2">
        {projects.map((p) => (
          <Button key={p.name} variant="outline" onClick={() => onChoose(p.name)}>
            {p.name}
            <span className="text-muted-foreground ml-2 text-xs">
              {p.count} {p.count === 1 ? noun.one : noun.many}
            </span>
          </Button>
        ))}
      </div>
    </section>
  )
}
```

In `frontend/src/components/app-chrome/index.ts`, add:

```ts
export { ProjectChooser } from "./project-chooser"
export type { ChooserProject } from "./project-chooser"
```

In `frontend/src/routes/_authenticated/documents.tsx`, delete the `DocumentsProjectChooser` function (and the `Button` and `type ProjectSummary` imports it alone used), add `ProjectChooser` to the `@/components/app-chrome` import, and replace `<DocumentsProjectChooser … />` with:

```tsx
        <ProjectChooser
          icon={FileText}
          heading="Documents open one project at a time"
          description="Pick a project to browse its documents. The project switcher in the header changes it later."
          projects={rows
            .filter((p) => p.document_count > 0)
            .map((p) => ({ name: p.name, count: p.document_count }))}
          noun={{ one: "document", many: "documents" }}
          emptyTitle="No project holds documents yet"
          emptyDescription="Documents appear here once an agent files one into a project."
          onChoose={setProject}
        />
```

- [ ] **Step 4: Topics reads the store**

In `frontend/src/features/knowledge/components/topics-tab.tsx`, add the imports:

```ts
import { Tags } from "lucide-react"
import { ProjectChooser } from "@/components/app-chrome"
import { useProjects } from "@/hooks/api"
import { ALL_PROJECTS, useProjectStore } from "@/stores/project-store"
```

(merge `Tags` into the existing `lucide-react` import if there is one). Rename the existing `export function TopicsTab({ project = "default" }: { project?: string }) {` to

```tsx
export function TopicsForProject({ project }: { project: string }) {
```

leaving its body unchanged, and add above it:

```tsx
/** Topic detection runs per project, so the all-projects scope has no topic
 *  set to show; it offers the projects instead. */
export function TopicsTab() {
  const project = useProjectStore((s) => s.activeProject)
  return project === ALL_PROJECTS ? (
    <TopicsProjectChooser />
  ) : (
    <TopicsForProject key={project} project={project} />
  )
}

function TopicsProjectChooser() {
  const setProject = useProjectStore((s) => s.setProject)
  const { data, isLoading, isError } = useProjects()
  if (isError) {
    return (
      <p className="text-destructive text-sm">
        Projects could not be loaded — a failed read, not an empty corpus.
      </p>
    )
  }
  if (isLoading) return null
  return (
    <ProjectChooser
      icon={Tags}
      heading="Topics open one project at a time"
      description="Topics are detected per project. Pick one to see its communities; the project switcher in the header changes it later."
      projects={(data ?? [])
        .filter((p) => p.kind !== "personal" && p.memory_count > 0)
        .map((p) => ({ name: p.name, count: p.memory_count }))}
      noun={{ one: "memory", many: "memories" }}
      emptyTitle="No project holds memories yet"
      emptyDescription="Topics are detected from memories; capture some and a project appears here."
      onChoose={setProject}
    />
  )
}
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `npx vitest run src/features/knowledge src/routes/_authenticated/__tests__/documents.test.tsx src/components/app-chrome && npm run typecheck`
Expected: PASS; typecheck exit 0.
Run: `E2E_API_TARGET=http://127.0.0.1:9 timeout 900 npx playwright test --project=demo-fixture tests/demo-makes-no-api-calls.spec.ts`
Expected: 31 passed.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/components/app-chrome frontend/src/routes/_authenticated/documents.tsx frontend/src/features/knowledge
git commit -m "feat(scope): make Topics follow the project switcher" -m "Under all projects it offers the same one-project chooser as Documents," -m "now a shared component." -m "Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

### Task 9: Responsive app header

Spec §C, first two bullets. Below `md` the header shows icon plus truncated title, the four header controls move into one overflow `Popover`, and page actions render icon-only. On desktop the long page descriptions are shortened, and a description that still truncates shows in full in a tooltip.

**Files:**
- Create: `frontend/src/components/app-chrome/header-controls.tsx`
- Modify: `frontend/src/components/app-chrome/app-page-header.tsx` (whole file)
- Modify: `frontend/src/components/app-chrome/index.ts`
- Modify: `frontend/src/routes/_authenticated.tsx:43-52,235-243`
- Modify: `frontend/src/styles/globals.css` (after line 439)
- Modify (description strings): `frontend/src/routes/_authenticated/settings.tsx:67`, `chat.tsx:60`, `knowledge_.articles_.$articleId.tsx:146-147`, `code_.wiki.tsx:24`, `projects_.$project.tsx:34`, `knowledge_.facts.tsx:16`, `knowledge_.articles.tsx:16`; `frontend/src/features/chat/components/real-chat-page.tsx:88`; `frontend/src/features/memory-graph/components/real-memory-graph-page.tsx:54-55`
- Create: `frontend/src/components/app-chrome/__tests__/header-controls.test.tsx`
- Modify: `frontend/src/components/app-chrome/__tests__/app-chrome.test.tsx`

**Interfaces:**
- Consumes: `ProjectSwitcher({ disabledReason })`, `projectScopeDisabledReason` (Task 5); `ContextChip`, `MinimalThemeSwitcher`, `DetailLevelToggle` (existing).
- Produces: `HeaderControls`, `HEADER_WIDE_QUERY` (Contracts).

**Implementer:** dr-superpowers:impl-opus-low
**Evaluation:** files 2 - spec 0 - coupling 1 - risk 1 = 4

- [ ] **Step 1: Write the failing header-controls test**

Create `frontend/src/components/app-chrome/__tests__/header-controls.test.tsx`:

```tsx
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import type { ReactNode } from "react"
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"

vi.mock("@/hooks/api", () => ({
  useProjects: () => ({ data: [], isLoading: false, isSuccess: true }),
}))
vi.mock("../minimal-theme-switcher", () => ({
  MinimalThemeSwitcher: () => <button type="button">Theme</button>,
}))
vi.mock("@/components/darkmem", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/components/darkmem")>()),
  DetailLevelToggle: () => <div>detail-level</div>,
}))

import { HeaderControls } from "../header-controls"
import { useProjectStore } from "@/stores/project-store"

const realMatchMedia = window.matchMedia

function setWide(wide: boolean) {
  window.matchMedia = vi.fn().mockImplementation((query: string) => ({
    matches: wide,
    media: query,
    onchange: null,
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    addListener: vi.fn(),
    removeListener: vi.fn(),
    dispatchEvent: vi.fn(),
  }))
}

function wrapper({ children }: { children: ReactNode }) {
  return (
    <QueryClientProvider client={new QueryClient()}>{children}</QueryClientProvider>
  )
}

beforeEach(() => {
  useProjectStore.setState({ activeProject: null, missingProject: null })
})
afterEach(() => {
  window.matchMedia = realMatchMedia
})

describe("HeaderControls", () => {
  it("renders every control inline from md up", () => {
    setWide(true)
    render(<HeaderControls />, { wrapper })
    expect(screen.getByRole("button", { name: "Project scope" })).toBeInTheDocument()
    expect(screen.getByRole("button", { name: "Session context" })).toBeInTheDocument()
    expect(screen.getByText("detail-level")).toBeInTheDocument()
    expect(screen.getByRole("button", { name: "Theme" })).toBeInTheDocument()
    expect(screen.queryByRole("button", { name: "View options" })).toBeNull()
  })

  it("collapses the controls into one overflow popover below md", async () => {
    setWide(false)
    const user = userEvent.setup()
    render(<HeaderControls />, { wrapper })
    expect(screen.queryByRole("button", { name: "Project scope" })).toBeNull()

    await user.click(screen.getByRole("button", { name: "View options" }))
    expect(await screen.findByRole("button", { name: "Project scope" })).toBeInTheDocument()
    expect(screen.getByRole("button", { name: "Session context" })).toBeInTheDocument()
    expect(screen.getByText("detail-level")).toBeInTheDocument()
  })

  it("keeps the overflow open while a control's own popover is used", async () => {
    setWide(false)
    const user = userEvent.setup()
    render(<HeaderControls />, { wrapper })
    await user.click(screen.getByRole("button", { name: "View options" }))
    await user.click(await screen.findByRole("button", { name: "Project scope" }))
    await user.click(await screen.findByRole("button", { name: /^All projects/ }))
    expect(screen.getByRole("button", { name: "Session context" })).toBeInTheDocument()
  })

  it("passes the code-page reason to the switcher", () => {
    setWide(true)
    render(<HeaderControls projectDisabledReason="Code is scoped by repository, not by project" />, { wrapper })
    expect(screen.getByRole("button", { name: "Project scope" })).toBeDisabled()
  })
})
```

- [ ] **Step 2: Write the failing header tests**

Append inside `describe("PageChrome / AppPageHeader", …)` in `frontend/src/components/app-chrome/__tests__/app-chrome.test.tsx`:

```tsx
  it("marks page actions so they render icon-only below md", () => {
    render(
      <>
        <PageChrome
          title="Memories"
          actions={<button type="button">Create memory</button>}
        />
        <AppPageHeader />
      </>,
    )
    const action = screen.getByRole("button", { name: "Create memory" })
    expect(action.parentElement).toHaveClass("dm-header-actions")
  })

  it("shows a truncated description in full on hover", async () => {
    const width = Object.getOwnPropertyDescriptor(HTMLElement.prototype, "scrollWidth")
    const client = Object.getOwnPropertyDescriptor(HTMLElement.prototype, "clientWidth")
    Object.defineProperty(HTMLElement.prototype, "scrollWidth", { configurable: true, get: () => 800 })
    Object.defineProperty(HTMLElement.prototype, "clientWidth", { configurable: true, get: () => 200 })
    try {
      const description = "A description far too long for the header bar at this width"
      render(
        <>
          <PageChrome title="Settings" description={description} />
          <AppPageHeader />
        </>,
      )
      fireEvent.pointerEnter(screen.getByText(description))
      fireEvent.focus(screen.getByText(description))
      expect((await screen.findAllByText(description)).length).toBeGreaterThan(1)
    } finally {
      if (width) Object.defineProperty(HTMLElement.prototype, "scrollWidth", width)
      if (client) Object.defineProperty(HTMLElement.prototype, "clientWidth", client)
    }
  })
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `npx vitest run src/components/app-chrome`
Expected: FAIL — `../header-controls` does not exist; the actions wrapper has no `dm-header-actions` class; the description renders once.

- [ ] **Step 4: Create the header controls**

Create `frontend/src/components/app-chrome/header-controls.tsx`:

```tsx
import { useState } from "react"
import { SlidersHorizontal } from "lucide-react"
import { Button } from "darkraise-ui/components/button"
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "darkraise-ui/components/popover"
import { DetailLevelToggle } from "@/components/darkmem"
import { useMediaQuery } from "@/hooks/use-media-query"
import { ContextChip } from "./context-chip"
import { MinimalThemeSwitcher } from "./minimal-theme-switcher"
import { ProjectSwitcher } from "./project-switcher"

export const HEADER_WIDE_QUERY = "(min-width: 768px)"

/**
 * The header's view controls. From `md` up they sit inline beside the page
 * title; below it they share one overflow popover so the title keeps the bar.
 * A JS media query rather than `md:` classes, because the narrow branch swaps
 * the container rather than restyling it.
 */
export function HeaderControls({
  projectDisabledReason,
}: {
  projectDisabledReason?: string
}) {
  const wide = useMediaQuery(HEADER_WIDE_QUERY)
  const [open, setOpen] = useState(false)

  const controls = (
    <>
      <ProjectSwitcher disabledReason={projectDisabledReason} />
      <ContextChip />
      <DetailLevelToggle />
      <MinimalThemeSwitcher />
    </>
  )

  if (wide) {
    return <div className="flex shrink-0 items-center gap-2">{controls}</div>
  }

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <Button variant="ghost" size="icon" aria-label="View options">
          <SlidersHorizontal aria-hidden className="size-4" />
        </Button>
      </PopoverTrigger>
      <PopoverContent
        side="bottom"
        align="end"
        className="flex w-72 flex-col items-start gap-3 p-3"
        // The switcher and the context chip open popovers of their own, which
        // portal outside this one; a click inside them must not close it.
        onInteractOutside={(event) => {
          const target = event.target
          if (target instanceof Element && target.closest(".dr-popover-content")) {
            event.preventDefault()
          }
        }}
      >
        {controls}
      </PopoverContent>
    </Popover>
  )
}
```

In `frontend/src/components/app-chrome/index.ts`, add:

```ts
export { HeaderControls, HEADER_WIDE_QUERY } from "./header-controls"
```

- [ ] **Step 5: Rewrite the page header**

Replace `frontend/src/components/app-chrome/app-page-header.tsx` with:

```tsx
import { useEffect, useRef, useState } from "react"
import { Link } from "@tanstack/react-router"
import { ArrowLeft } from "lucide-react"
import { Button } from "darkraise-ui/components/button"
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "darkraise-ui/components/tooltip"
import { splitNavHref } from "@/providers/router-adapter"
import { usePageChrome } from "./page-chrome"

/**
 * Page identity block for the app header bar (rendered via the layout's
 * `headerSlot`): an optional back button, then icon + title + description +
 * actions. darkraise-ui's PageHeader has no icon slot and renders
 * in-content, so this is a custom component fed by the page-chrome store.
 *
 * The back button is icon-only and names its destination in a tooltip. It
 * used to render the label as text beside the arrow, which the top-nav
 * layout then hid in CSS -- so that layout already showed a bare arrow with
 * nothing anywhere saying where it went. One treatment everywhere, and the
 * destination is always reachable.
 */
export function AppPageHeader() {
  const { icon: Icon, title, description, parent, actions } = usePageChrome()

  if (!title) return null

  const back = parent ? splitNavHref(parent.href) : null

  return (
    <div className="flex min-w-0 flex-1 items-center gap-2.5 text-left">
      {parent && back && (
        <TooltipProvider delayDuration={150}>
          <Tooltip>
            <TooltipTrigger asChild>
              <Button
                variant="ghost"
                size="icon"
                asChild
                className="text-muted-foreground hover:text-foreground -ml-1 shrink-0"
              >
                <Link
                  to={back.to}
                  search={back.search}
                  aria-label={`Back to ${parent.label}`}
                >
                  <ArrowLeft aria-hidden className="size-4" />
                </Link>
              </Button>
            </TooltipTrigger>
            <TooltipContent>Back to {parent.label}</TooltipContent>
          </Tooltip>
        </TooltipProvider>
      )}
      {Icon && (
        <span className="bg-primary/10 text-primary flex h-7 w-7 shrink-0 items-center justify-center rounded-md">
          <Icon aria-hidden className="h-4 w-4" />
        </span>
      )}
      <h1 className="min-w-0 truncate text-sm font-semibold md:shrink-0">
        {title}
      </h1>
      {description && <HeaderDescription text={description} />}
      {actions && (
        <div className="dm-header-actions ml-auto flex shrink-0 items-center gap-2 pl-2">
          {actions}
        </div>
      )}
    </div>
  )
}

/** One line, truncated; when it does not fit, the full text is a tooltip
 *  away. Measured on the box rather than assumed from the string length,
 *  because what fits depends on the header's other contents. */
function HeaderDescription({ text }: { text: string }) {
  const boxRef = useRef<HTMLDivElement>(null)
  const [truncated, setTruncated] = useState(false)
  const [hovered, setHovered] = useState(false)

  useEffect(() => {
    const line = boxRef.current?.querySelector("p")
    if (!line) return
    const measure = () => setTruncated(line.scrollWidth > line.clientWidth)
    measure()
    const observer = new ResizeObserver(measure)
    observer.observe(line)
    return () => observer.disconnect()
  }, [text])

  return (
    <div
      ref={boxRef}
      className="dm-chrome-desc border-border hidden min-w-0 border-l pl-2.5 lg:block"
    >
      <TooltipProvider delayDuration={300}>
        <Tooltip open={truncated && hovered} onOpenChange={setHovered}>
          <TooltipTrigger asChild>
            <p
              tabIndex={truncated ? 0 : undefined}
              className="text-muted-foreground truncate text-sm"
            >
              {text}
            </p>
          </TooltipTrigger>
          <TooltipContent className="max-w-md">{text}</TooltipContent>
        </Tooltip>
      </TooltipProvider>
    </div>
  )
}
```

(The `text-primary` on the icon badge is swept by Task 13.)

- [ ] **Step 6: Icon-only actions below md**

In `frontend/src/styles/globals.css`, add after the `.dr-top-nav-layout .dm-chrome-desc` rule (line 439):

```css
/* Page actions go icon-only below md. The label stays in the DOM, so it is
   still the button's accessible name; only its glyphs collapse. A button with
   no icon keeps its text, because it would otherwise render empty. */
@media (width < 48rem) {
  .dm-header-actions :is(button, a):has(> svg) {
    font-size: 0;
    gap: 0;
    padding-inline: 0.5rem;
  }
  .dm-header-actions :is(button, a):has(> svg) > svg {
    margin: 0;
  }
}
```

- [ ] **Step 7: Use the controls in the layout**

In `frontend/src/routes/_authenticated.tsx`, delete the line `import { DetailLevelToggle } from "@/components/darkmem"` and replace the multi-line `import { … } from "@/components/app-chrome"` statement (the one naming `AppPageHeader`, `BackToTop`, `ContextChip`, `MinimalThemeSwitcher`, `ProjectScopeReconciler`, `ProjectSwitcher`) with:

```ts
import {
  AppPageHeader,
  BackToTop,
  HeaderControls,
  ProjectScopeReconciler,
} from "@/components/app-chrome"
```

Leave the separate `import { projectScopeDisabledReason } from "@/components/app-chrome/project-switcher"` line Task 5 added exactly as it is — do not add a second one. Then replace the `headerSlot={ … }` value with:

```tsx
        headerSlot={
          <>
            <AppPageHeader />
            <HeaderControls
              projectDisabledReason={projectScopeDisabledReason(pathname)}
            />
          </>
        }
```

- [ ] **Step 8: Shorten the long page descriptions**

Replace each `description` string (header descriptions only):

| File | New description |
|---|---|
| `routes/_authenticated/settings.tsx:67` | `Tunables, LLM purposes, security, maintenance and appearance.` |
| `routes/_authenticated/chat.tsx:60` | `Chat over your memory, with each answer's sources beside it.` |
| `features/chat/components/real-chat-page.tsx:88` | `Chat over your memory, with each answer's sources beside it.` |
| `routes/_authenticated/knowledge_.articles_.$articleId.tsx:146-147` | `One synthesised article, every claim linked to its fact.` |
| `routes/_authenticated/code_.wiki.tsx:24` | `A repository's generated wiki; generate it from a reindex.` |
| `routes/_authenticated/projects_.$project.tsx:34` | `Everything this project holds, and its recorded progress.` |
| `routes/_authenticated/knowledge_.facts.tsx:16` | `Verified facts with their sources, rungs and belief windows.` |
| `routes/_authenticated/knowledge_.articles.tsx:16` | `Synthesised articles whose every claim links to a fact.` |
| `features/memory-graph/components/real-memory-graph-page.tsx:54-55` | `Entities and topics from your memories, for browsing only.` |

- [ ] **Step 9: Run tests to verify they pass**

Run: `npx vitest run src/components/app-chrome src/routes src/features/chat src/features/memory-graph && npm run typecheck`
Expected: PASS; typecheck exit 0. If a test asserts an old description string, update it to the new one and name the file in the commit body.

- [ ] **Step 10: Commit**

```bash
git add frontend/src/components/app-chrome frontend/src/routes frontend/src/styles/globals.css frontend/src/features/chat/components/real-chat-page.tsx frontend/src/features/memory-graph/components/real-memory-graph-page.tsx
git commit -m "feat(chrome): collapse header controls below md" -m "Page actions go icon-only on narrow screens, long descriptions are" -m "shortened, and a truncated one shows in full in a tooltip." -m "Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

### Task 10: Scrollable tab bars

Spec §C, tab-bar bullet. Settings (10 tabs) and Activity (8 tabs) scroll horizontally with an edge fade, scroll the active tab into view, and never clip the first or last tab. The library's `TabsList` is kept and wrapped; the wrapper records the gap.

**Files:**
- Create: `frontend/src/components/darkmem/scroll-tabs-list.tsx`
- Modify: `frontend/src/components/darkmem/index.ts`
- Modify: `frontend/src/styles/globals.css` (append)
- Modify: `frontend/src/routes/_authenticated/settings.tsx:1-7,100-145`
- Modify: `frontend/src/routes/_authenticated/activity.tsx:1-10,88-124`
- Create: `frontend/src/components/darkmem/__tests__/scroll-tabs-list.test.tsx`

**Interfaces:**
- Consumes: nothing.
- Produces: `ScrollTabsList` (Contracts).

**Implementer:** dr-superpowers:impl-sonnet-medium
**Evaluation:** files 2 - spec 0 - coupling 0 - risk 0 = 2

- [ ] **Step 1: Write the failing test**

Create `frontend/src/components/darkmem/__tests__/scroll-tabs-list.test.tsx`:

```tsx
import { render, screen } from "@testing-library/react"
import { afterEach, describe, expect, it, vi } from "vitest"
import { Tabs, TabsTrigger } from "darkraise-ui/components/tabs"
import { ScrollTabsList } from "../scroll-tabs-list"

function renderTabs(active: string) {
  return render(
    <Tabs value={active}>
      <ScrollTabsList activeValue={active}>
        {["one", "two", "three"].map((v) => (
          <TabsTrigger key={v} value={v}>
            {v}
          </TabsTrigger>
        ))}
      </ScrollTabsList>
    </Tabs>,
  )
}

afterEach(() => {
  vi.mocked(Element.prototype.scrollIntoView).mockClear()
})

describe("ScrollTabsList", () => {
  it("scrolls the active tab into view", () => {
    renderTabs("three")
    const calls = vi.mocked(Element.prototype.scrollIntoView).mock
    expect(calls.contexts).toContain(screen.getByRole("tab", { name: "three" }))
  })

  it("sizes the strip to its tabs so none is clipped", () => {
    renderTabs("one")
    expect(screen.getByRole("tablist")).toHaveClass("w-max", "min-w-full")
  })

  it("marks the edge that has more tabs past it", () => {
    const scroll = Object.getOwnPropertyDescriptor(HTMLElement.prototype, "scrollWidth")
    const client = Object.getOwnPropertyDescriptor(HTMLElement.prototype, "clientWidth")
    Object.defineProperty(HTMLElement.prototype, "scrollWidth", { configurable: true, get: () => 900 })
    Object.defineProperty(HTMLElement.prototype, "clientWidth", { configurable: true, get: () => 300 })
    try {
      renderTabs("one")
      const strip = screen.getByRole("tablist").parentElement!
      expect(strip).toHaveAttribute("data-fade-end")
      expect(strip).not.toHaveAttribute("data-fade-start")
    } finally {
      if (scroll) Object.defineProperty(HTMLElement.prototype, "scrollWidth", scroll)
      if (client) Object.defineProperty(HTMLElement.prototype, "clientWidth", client)
    }
  })
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npx vitest run src/components/darkmem/__tests__/scroll-tabs-list.test.tsx`
Expected: FAIL — cannot resolve `../scroll-tabs-list`.

- [ ] **Step 3: Create the wrapper**

Create `frontend/src/components/darkmem/scroll-tabs-list.tsx`:

```tsx
import {
  useCallback,
  useEffect,
  useRef,
  useState,
  type ReactNode,
} from "react"
import { TabsList } from "darkraise-ui/components/tabs"
import { cn } from "darkraise-ui/lib"

/**
 * darkraise-ui gap: `TabsList` has no overflow behaviour — a strip with more
 * tabs than fit clips its first and last tab. This keeps the library list and
 * only adds a horizontal scroller around it: the list sizes to its tabs, the
 * edge with more tabs past it fades, and the active tab scrolls into view.
 */
export function ScrollTabsList({
  activeValue,
  className,
  children,
}: {
  activeValue: string
  className?: string
  children: ReactNode
}) {
  const scrollRef = useRef<HTMLDivElement>(null)
  const [edges, setEdges] = useState({ start: false, end: false })

  const measure = useCallback(() => {
    const el = scrollRef.current
    if (!el) return
    setEdges({
      start: el.scrollLeft > 1,
      end: el.scrollLeft + el.clientWidth < el.scrollWidth - 1,
    })
  }, [])

  useEffect(() => {
    const el = scrollRef.current
    if (!el) return
    measure()
    const observer = new ResizeObserver(measure)
    observer.observe(el)
    el.addEventListener("scroll", measure, { passive: true })
    return () => {
      observer.disconnect()
      el.removeEventListener("scroll", measure)
    }
  }, [measure])

  useEffect(() => {
    scrollRef.current
      ?.querySelector<HTMLElement>('[role="tab"][data-state="active"]')
      ?.scrollIntoView({ block: "nearest", inline: "nearest" })
  }, [activeValue])

  return (
    <div
      ref={scrollRef}
      className="dm-tab-scroll"
      data-fade-start={edges.start || undefined}
      data-fade-end={edges.end || undefined}
    >
      <TabsList className={cn("w-max min-w-full", className)}>{children}</TabsList>
    </div>
  )
}
```

In `frontend/src/components/darkmem/index.ts`, add:

```ts
export { ScrollTabsList } from "./scroll-tabs-list"
```

Append to `frontend/src/styles/globals.css`:

```css
/* Horizontally scrolling tab strip (ScrollTabsList). The fade marks the edge
   that still has tabs past it. */
.dm-tab-scroll {
  overflow-x: auto;
  scrollbar-width: thin;
}
.dm-tab-scroll[data-fade-start] {
  mask-image: linear-gradient(to right, transparent, black 2rem);
}
.dm-tab-scroll[data-fade-end] {
  mask-image: linear-gradient(to right, black calc(100% - 2rem), transparent);
}
.dm-tab-scroll[data-fade-start][data-fade-end] {
  mask-image: linear-gradient(
    to right,
    transparent,
    black 2rem,
    black calc(100% - 2rem),
    transparent
  );
}
```

- [ ] **Step 4: Use it on Settings and Activity**

In `frontend/src/routes/_authenticated/settings.tsx`, change the tabs import to `import { Tabs, TabsContent, TabsTrigger } from "darkraise-ui/components/tabs"`, add `import { ScrollTabsList } from "@/components/darkmem"`, and replace

```tsx
          <div className="overflow-x-auto">
            <TabsList className="w-full">
```

with

```tsx
          <ScrollTabsList activeValue={tab ?? "flags"}>
```

and the matching closing `</TabsList>` + `</div>` with `</ScrollTabsList>`. In the comment above the sticky wrapper, change "`overflow-x-auto` on the one inside" to "the scroller (`ScrollTabsList`) inside it".

In `frontend/src/routes/_authenticated/activity.tsx`, make the same three edits with `activeValue={tab ?? "pipeline"}`.

- [ ] **Step 5: Run tests to verify they pass**

Run: `npx vitest run src/components/darkmem src/routes src/features/settings src/features/activity && npm run typecheck`
Expected: PASS; typecheck exit 0.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/components/darkmem frontend/src/styles/globals.css frontend/src/routes/_authenticated/settings.tsx frontend/src/routes/_authenticated/activity.tsx
git commit -m "feat(ui): scroll long tab bars instead of clipping" -m "Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

### Task 11: Activity pipeline rows and chat thread pane

Spec §C, the Activity → Pipeline and Chat bullets, and spec §H's demo thread list ("the demo chat thread list stops clipping + New"), which shares the fix. Below `md` a pipeline row stacks its quoted content above a vertical stepper. The chat thread pane opens wider, cannot be dragged narrower than its header needs, and its header wraps instead of clipping.

**Files:**
- Modify: `frontend/src/features/activity/components/pipeline-tab.tsx:64-72`
- Modify: `frontend/src/features/activity/components/pipeline-stepper.tsx:116-165`
- Modify: `frontend/src/features/chat/components/chat-panels.tsx:24-45,102-110`
- Modify: `frontend/src/features/chat/components/chat-sidebar.tsx:52-59`
- Modify: `frontend/src/features/chat/components/demo-thread-list.tsx:28-35`
- Create: `frontend/src/features/activity/__tests__/pipeline-stepper.test.tsx`
- Create: `frontend/src/features/chat/__tests__/chat-panels.test.tsx`

**Interfaces:**
- Consumes: nothing.
- Produces: `THREADS_MIN_SIZE` exported from `chat-panels.tsx` (used only by its own test).

**Implementer:** dr-superpowers:impl-sonnet-high
**Evaluation:** files 2 - spec 0 - coupling 0 - risk 1 = 3

- [ ] **Step 1: Write the failing tests**

Create `frontend/src/features/activity/__tests__/pipeline-stepper.test.tsx`:

```tsx
import { render, screen } from "@testing-library/react"
import { describe, expect, it } from "vitest"
import { useDemoStore } from "@/demo/store"
import { PipelineStepper } from "../components/pipeline-stepper"

describe("PipelineStepper", () => {
  it("is an ordered list that runs vertically below md and horizontally from md", () => {
    const run = useDemoStore.getState().pipelineRuns[0]!
    render(<PipelineStepper run={run} />)
    const list = screen.getByRole("list", { name: "Pipeline steps" })
    expect(list).toHaveClass("flex-col", "md:flex-row")
    expect(screen.getAllByRole("listitem")).toHaveLength(run.steps.length)
  })
})
```

Create `frontend/src/features/chat/__tests__/chat-panels.test.tsx`:

```tsx
import { render } from "@testing-library/react"
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"
import { ChatPanels, THREADS_MIN_SIZE } from "../components/chat-panels"

const realMatchMedia = window.matchMedia

beforeEach(() => {
  window.localStorage.clear()
  window.matchMedia = vi.fn().mockImplementation((query: string) => ({
    matches: true,
    media: query,
    onchange: null,
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    addListener: vi.fn(),
    removeListener: vi.fn(),
    dispatchEvent: vi.fn(),
  }))
})
afterEach(() => {
  window.matchMedia = realMatchMedia
})

function threadsWidth(container: HTMLElement): number {
  const pane = container.querySelector<HTMLElement>('[data-panel-id="chat-threads"]')!
  return Number.parseFloat(pane.style.width)
}

describe("ChatPanels", () => {
  it("opens the thread pane at least as wide as its floor", () => {
    const { container } = render(
      <ChatPanels threads={<div />} conversation={<div />} context={<div />} />,
    )
    expect(threadsWidth(container)).toBeGreaterThanOrEqual(THREADS_MIN_SIZE)
  })

  it("ignores a stored layout that squeezed the thread pane below its floor", () => {
    window.localStorage.setItem("darkmem.chat.panel-sizes", JSON.stringify([10, 66, 24]))
    const { container } = render(
      <ChatPanels threads={<div />} conversation={<div />} context={<div />} />,
    )
    expect(threadsWidth(container)).toBeGreaterThanOrEqual(THREADS_MIN_SIZE)
  })
})
```

In `frontend/src/features/chat/__tests__/demo-chat.test.tsx`, append inside `describe("DemoThreadList", …)`:

```ts
  it("lets its header wrap rather than clip the New button", () => {
    render(
      <DemoThreadList
        threads={CURATED_CHAT_THREADS}
        activeId="thread-ranking"
        onSelect={vi.fn()}
        onNew={vi.fn()}
      />,
    )
    expect(screen.getByRole("button", { name: /new/i }).parentElement).toHaveClass("flex-wrap")
  })
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `npx vitest run src/features/activity/__tests__/pipeline-stepper.test.tsx src/features/chat`
Expected: FAIL — no list named "Pipeline steps"; `THREADS_MIN_SIZE` undefined; the stored 10% layout is honoured; the header does not wrap.

- [ ] **Step 3: Stack the pipeline row**

In `frontend/src/features/activity/components/pipeline-tab.tsx`, replace the row's first block (lines 64-72) with:

```tsx
      <div className="flex flex-col gap-1 md:flex-row md:flex-wrap md:items-baseline md:gap-2.5">
        <span className="text-muted-foreground font-mono text-sm">
          {run.id}
        </span>
        <span className="min-w-0 text-sm md:flex-1">{run.content}</span>
        <span className="text-muted-foreground font-mono text-sm whitespace-nowrap md:ml-auto">
          {run.time_label}
        </span>
      </div>
```

In `frontend/src/features/activity/components/pipeline-stepper.tsx`, replace `PipelineStepper` (lines 116-end of the function) with:

```tsx
export function PipelineStepper({ run }: { run: DemoPipelineRun }) {
  return (
    <ol
      aria-label="Pipeline steps"
      className="flex flex-col md:flex-row md:items-start md:overflow-x-auto md:pb-1"
    >
      {run.steps.map((state, i) => (
        <li
          key={PHASE_LABELS[i]}
          className="flex flex-col md:flex-1 md:flex-row md:items-start"
        >
          {i > 0 && (
            <>
              <span
                aria-hidden
                className={cn("ml-[13px] h-3 w-0.5 md:hidden", connectorClass(state))}
              />
              <span
                aria-hidden
                className={cn(
                  "mt-3.5 hidden h-0.5 min-w-3 flex-1 md:block",
                  connectorClass(state),
                )}
              />
            </>
          )}
          <div className="flex items-center gap-2 md:w-24 md:flex-none md:flex-col md:gap-1">
            {i === 4 ? (
              <WriteDot state={state} substeps={run.substeps} />
            ) : (
              <span
                className={cn(
                  "bg-card flex h-7 w-7 flex-none items-center justify-center rounded-full border-2",
                  DOT_STYLES[state],
                )}
              >
                <StepIcon state={state} />
              </span>
            )}
            <span className="text-muted-foreground font-mono text-xs">
              {i + 1}
            </span>
            <span
              className={cn(
                "text-sm leading-tight md:text-center",
                LABEL_STYLES[state],
              )}
            >
              {PHASE_LABELS[i]}
            </span>
            {i === 4 && run.substeps && (
              <span className="flex gap-1">
                <SubstepPill label="vector" state={run.substeps.vector} />
                <SubstepPill label="graph" state={run.substeps.graph} />
              </span>
            )}
          </div>
        </li>
      ))}
    </ol>
  )
}
```

- [ ] **Step 4: Floor the chat thread pane**

In `frontend/src/features/chat/components/chat-panels.tsx`, replace `const DEFAULT_SIZES = [16, 60, 24]` with:

```ts
/** The thread pane's floor, in percent (the group takes no pixel sizes). At
 *  the narrowest wide layout it still fits the pane's header and search box. */
export const THREADS_MIN_SIZE = 18
const DEFAULT_SIZES = [20, 56, 24]
```

in `readStoredSizes`, extend the accepted-layout condition with one more clause, so the `if` reads:

```ts
    if (
      Array.isArray(parsed) &&
      parsed.length === DEFAULT_SIZES.length &&
      parsed.every((n) => typeof n === "number" && Number.isFinite(n) && n > 0) &&
      (parsed[0] as number) >= THREADS_MIN_SIZE
    ) {
```

and change the thread panel's `minSize={10}` to `minSize={THREADS_MIN_SIZE}`.

In `frontend/src/features/chat/components/chat-sidebar.tsx`, replace the header row

```tsx
        <div className="flex items-center justify-between">
          <span className="text-sm font-semibold">Conversations</span>
```

with

```tsx
        <div className="flex flex-wrap items-center justify-between gap-2">
          <span className="min-w-0 truncate text-sm font-semibold">Conversations</span>
```

In `frontend/src/features/chat/components/demo-thread-list.tsx`, replace

```tsx
      <div className="border-border flex items-center justify-between gap-2 border-b px-3 py-2">
        <span className="text-sm font-semibold">Conversations</span>
```

with

```tsx
      <div className="border-border flex flex-wrap items-center justify-between gap-2 border-b px-3 py-2">
        <span className="min-w-0 truncate text-sm font-semibold">Conversations</span>
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `npx vitest run src/features/activity src/features/chat && npm run typecheck`
Expected: PASS; typecheck exit 0.
Run: `E2E_API_TARGET=http://127.0.0.1:9 timeout 900 npx playwright test --project=demo-fixture tests/activity-pipeline.spec.ts tests/activity.spec.ts`
Expected: every test passes. A failure that asserts the old layout or copy this task changed is updated to the new one and named in the commit body; any other failure stops the task.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/features/activity frontend/src/features/chat
git commit -m "fix(ui): stack pipeline rows and widen chat threads" -m "Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

### Task 12: Code Graph layout and panel chrome

Spec §C, Code Graph bullet, and the Code Graph half of spec §E's graph-page bullet. Below `lg` the explorer, inspector, canvas and analysis panel stack; from `lg` they sit in a row. The Blast Radius control stays in the analysis inspector (it never sits over the canvas). Panel headings become sentence case sans like Memory Graph's, toolbar captions reach 12px, and the counter reads "N nodes · N edges".

**Files:**
- Modify: `frontend/src/features/code/components/real-code-graph-view.tsx:57-70,273-324,326-334,403,465,521,527,569`
- Modify: `frontend/src/features/code/components/real-code-inspector.tsx:23,33,45`
- Modify: `frontend/src/features/code/__tests__/real-code-graph-view.test.tsx`

**Interfaces:**
- Consumes: nothing (Task 5 already removed this file's scope pill).
- Produces: nothing.

**Implementer:** dr-superpowers:impl-sonnet-medium
**Evaluation:** files 1 - spec 0 - coupling 0 - risk 1 = 2

- [ ] **Step 1: Write the failing test**

Append inside `describe("RealCodeGraphView", …)` in `frontend/src/features/code/__tests__/real-code-graph-view.test.tsx`:

```ts
  it("spells out the counter and stacks its panes below lg", async () => {
    mockApi()
    const { container } = render(
      <RealCodeGraphView
        repoId="r1"
        onRepoChange={vi.fn()}
        onOpenRepositories={vi.fn()}
      />,
      { wrapper },
    )
    await screen.findByText("ingestion")
    expect(screen.getByText(/^\d+ nodes · \d+ edges$/)).toBeInTheDocument()
    expect(screen.getByText("Layout")).toBeInTheDocument()
    expect(screen.getByText("Colour by")).toBeInTheDocument()
    const heading = screen.getByText("Selected symbol")
    expect(heading.closest("span")).not.toHaveClass("uppercase")
    expect(container.querySelector(".lg\\:flex-row")).not.toBeNull()
    expect(container.querySelector(".md\\:flex-row")).toBeNull()
  })
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npx vitest run src/features/code/__tests__/real-code-graph-view.test.tsx`
Expected: FAIL — the counter reads "3 n 5 e"-style abbreviations, the captions are lowercase "layout" / "colour by", and the pane row switches at `md`.

- [ ] **Step 3: Section titles and captions**

In `frontend/src/features/code/components/real-code-graph-view.tsx`, replace `SectionTitle`'s span class (line 66) with:

```tsx
    <span className="text-foreground flex items-center gap-1.5 text-sm font-semibold">
```

replace the two toolbar captions

```tsx
          <span className="text-muted-foreground font-mono text-[10px] uppercase">
            layout
          </span>
```

```tsx
          <span className="text-muted-foreground font-mono text-[10px] uppercase">
            colour by
          </span>
```

with

```tsx
          <span className="text-muted-foreground text-xs">Layout</span>
```

```tsx
          <span className="text-muted-foreground text-xs">Colour by</span>
```

and the counter — the `<span …>` that currently reads

```tsx
        <span className="text-muted-foreground ml-auto font-mono text-sm whitespace-nowrap">
          <b className="text-primary font-semibold">{graph.nodes.length}</b> n{" "}
          <b className="text-primary font-semibold">{graph.edges.length}</b> e
        </span>
```

(located by that content; after Task 5 removed the scope pill above it, it sits about four lines earlier than the original `:321-324`) — with:

```tsx
        <span className="text-muted-foreground ml-auto shrink-0 text-sm whitespace-nowrap">
          {graph.nodes.length} {graph.nodes.length === 1 ? "node" : "nodes"} ·{" "}
          {graph.edges.length} {graph.edges.length === 1 ? "edge" : "edges"}
        </span>
```

Replace the remaining `text-[10px]` in this file (the blast bucket pills, the process step counts and their `mermaid` button) with `text-xs`.

- [ ] **Step 4: Stack the panes below lg**

In the same file:

- the pane row `className="flex min-h-0 flex-1 flex-col md:flex-row"` → `className="flex min-h-0 flex-1 flex-col lg:flex-row"`;
- the left `Tabs` className: every `md:` prefix → `lg:` (`lg:w-56 lg:shrink-0 lg:border-r lg:border-b-0`);
- the right analysis column className: every `md:` prefix → `lg:` (`lg:w-60 lg:shrink-0 lg:border-t-0 lg:border-l`).

In `frontend/src/features/code/components/real-code-inspector.tsx`, replace `w-[24rem] min-w-0 shrink-0 flex-col border-r` in all three container classNames (lines 23, 33, 45) with:

```
w-full min-w-0 flex-col border-b lg:w-[24rem] lg:shrink-0 lg:border-r lg:border-b-0
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `npx vitest run src/features/code && npm run typecheck`
Expected: PASS; typecheck exit 0.
Run: `E2E_API_TARGET=http://127.0.0.1:9 timeout 900 npx playwright test --project=demo-fixture tests/code-index-debt.spec.ts`
Expected: every test passes. A failure that asserts the old layout or copy this task changed is updated to the new one and named in the commit body; any other failure stops the task.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/features/code
git commit -m "fix(code): stack the Code Graph panes below lg" -m "Also sentence-cases its panel headings, lifts its captions to 12px" -m "and spells out the node and edge counter." -m "Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

### Task 13: Contrast-safe text tokens

Spec §D, Contrast. Light-mode green text measured ~3:1. Derived tokens darken the accent and success colours — and, because Task 25's acceptance is 0 `color-contrast` findings, the warning and info colours darkmem also uses as text (Assumptions) — for text in light mode and alias them in dark mode; every darkmem use of those four *as text* moves to them, and a source scan keeps it that way. The accent stays user-configurable because the token is computed from `--primary`.

**Files:**
- Modify: `frontend/src/styles/globals.css:26-35` (tokens) and every `@apply text-primary` (lines 58, 61, 101, 104)
- Modify (mechanical sweep): every file under `frontend/src` containing `text-primary` / `text-success` / `text-warning` / `text-info` as a whole class (about 110 source files plus test files; see Step 4)
- Create: `frontend/src/__tests__/text-color-tokens.test.ts`

**Interfaces:**
- Consumes: nothing.
- Produces: `--primary-text`, `--success-text`, `--warning-text`, `--info-text` and their `text-*-text` utilities (Contracts). Tasks 18, 20, 21, 23 and 24 use them.

**Implementer:** dr-superpowers:impl-opus-medium
**Evaluation:** files 1 - spec 0 - coupling 2 - risk 2 = 5

- [ ] **Step 1: Write the failing scan**

Create `frontend/src/__tests__/text-color-tokens.test.ts`:

```ts
import { readFileSync, readdirSync, statSync } from "node:fs"
import { join, relative } from "node:path"
import { describe, expect, it } from "vitest"

const SRC = join(process.cwd(), "src")
const SELF = join(SRC, "__tests__", "text-color-tokens.test.ts")
// A whole `text-primary` / `text-success` class, with or without a variant
// prefix or an opacity suffix — never `text-primary-foreground` or the
// `-text` tokens themselves.
const RAW = /(?<![-\w])text-(?:primary|success|warning|info)(?![-\w])/

function walk(dir: string, out: string[] = []): string[] {
  for (const entry of readdirSync(dir)) {
    const p = join(dir, entry)
    if (statSync(p).isDirectory()) walk(p, out)
    else if (/\.(tsx?|css)$/.test(entry)) out.push(p)
  }
  return out
}

describe("semantic text colours use the contrast-safe tokens", () => {
  it("no source uses text-primary/-success/-warning/-info as a text colour", () => {
    const offenders = walk(SRC)
      .filter((f) => f !== SELF)
      .flatMap((f) =>
        readFileSync(f, "utf8")
          .split("\n")
          .map((line, i) => (RAW.test(line) ? `${relative(SRC, f)}:${i + 1}` : null))
          .filter((hit): hit is string => hit !== null),
      )
    expect(
      offenders,
      "use the matching text-*-text token (light-mode contrast)",
    ).toEqual([])
  })

  it("defines the four tokens and aliases them in dark mode", () => {
    const css = readFileSync(join(SRC, "styles", "globals.css"), "utf8")
    for (const token of ["primary", "success", "warning", "info"]) {
      expect(css).toContain(`--color-${token}-text: var(--${token}-text)`)
    }
    expect(css).toContain(
      "--primary-text: color-mix(in oklch, hsl(var(--primary)) 70%, black)",
    )
    expect(css).toMatch(/\[data-mode="dark"\]\s*\{[^}]*--primary-text: hsl\(var\(--primary\)\)/)
  })
})
```

- [ ] **Step 2: Run the scan to verify it fails**

Run: `npx vitest run src/__tests__/text-color-tokens.test.ts`
Expected: FAIL — both tests; the first lists every current use.

- [ ] **Step 3: Define the tokens**

In `frontend/src/styles/globals.css`, add directly after the closing `}` of the `@theme { … }` block (line 35):

```css
/* Accent and success used as TEXT. In light mode the raw hues measure ~3:1
   against the page, so text takes them darkened; dark mode keeps the hue.
   Derived from --primary rather than pinned, so the Appearance accent picker
   still drives it. Fills, borders and buttons keep the raw tokens. */
@theme inline {
  --color-primary-text: var(--primary-text);
  --color-success-text: var(--success-text);
  --color-warning-text: var(--warning-text);
  --color-info-text: var(--info-text);
}
:root {
  --primary-text: color-mix(in oklch, hsl(var(--primary)) 70%, black);
  --success-text: color-mix(in oklch, hsl(var(--success)) 70%, black);
  --warning-text: color-mix(in oklch, hsl(var(--warning)) 60%, black);
  --info-text: color-mix(in oklch, hsl(var(--info)) 70%, black);
}
[data-mode="dark"] {
  --primary-text: hsl(var(--primary));
  --success-text: hsl(var(--success));
  --warning-text: hsl(var(--warning));
  --info-text: hsl(var(--info));
}
```

- [ ] **Step 4: Sweep the utilities**

Run from `frontend/` (one mechanical pass over sources, tests and the stylesheet):

```bash
rg -l --pcre2 '(?<![-\w])text-(primary|success|warning|info)(?![-\w])' src \
  | grep -v 'src/__tests__/text-color-tokens.test.ts' \
  | xargs perl -pi -e 's/(?<![-\w])text-(primary|success|warning|info)(?![-\w])/text-$1-text/g'
```

This rewrites `text-primary` → `text-primary-text`, `hover:text-primary` → `hover:text-primary-text`, `text-primary/70` → `text-primary-text/70` (and the same for success, warning and info), every test assertion on those classes (including `empty-state.test.tsx:26` and `project-workspace.test.tsx:625`) and the four `@apply text-primary` lines in `globals.css`. `text-primary-foreground` is untouched by the lookahead.

- [ ] **Step 5: Run the scan and the suite**

Run: `npx vitest run src/__tests__/text-color-tokens.test.ts && npm test && npm run typecheck && npm run build`
Expected: scan PASS; whole suite green; typecheck exit 0; build green (Tailwind resolves `text-primary-text` from the `@theme inline` colour).

- [ ] **Step 6: Commit**

```bash
git add -A frontend/src
git commit -m "fix(a11y): route semantic text colours via tokens" -m "Light mode darkens the accent, success, warning and info hues for text" -m "so they clear 4.5:1; dark mode keeps them. A scan forbids the raw classes." -m "Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

### Task 14: Minimum 12px text

Spec §D, minimum text size. Every `text-[10px]` (147) and `text-[11px]` (18) in `frontend/src` becomes `text-xs` (13px here), and a source scan fails the build on `text-[8px]` … `text-[11px]`. Tasks 11 and 12 already converted the stepper and Code Graph occurrences.

**Files:**
- Modify (mechanical sweep): every file under `frontend/src` listed by `rg -l "text-\[(10|11)px\]" src` (63 files before Tasks 11-12)
- Create: `frontend/src/__tests__/min-text-size.test.ts`

**Interfaces:**
- Consumes: nothing.
- Produces: nothing.

**Implementer:** dr-superpowers:impl-sonnet-medium
**Evaluation:** files 1 - spec 0 - coupling 0 - risk 1 = 2

- [ ] **Step 1: Write the failing scan**

Create `frontend/src/__tests__/min-text-size.test.ts`:

```ts
import { readFileSync, readdirSync, statSync } from "node:fs"
import { join, relative } from "node:path"
import { describe, expect, it } from "vitest"

const SRC = join(process.cwd(), "src")
const SELF = join(SRC, "__tests__", "min-text-size.test.ts")
const TOO_SMALL = /text-\[(?:[0-9]|1[01])(?:\.\d+)?px\]/

function walk(dir: string, out: string[] = []): string[] {
  for (const entry of readdirSync(dir)) {
    const p = join(dir, entry)
    if (statSync(p).isDirectory()) walk(p, out)
    else if (/\.(tsx?|css)$/.test(entry)) out.push(p)
  }
  return out
}

describe("text is never smaller than 12px", () => {
  it("no source sets an arbitrary text size below 12px", () => {
    const offenders = walk(SRC)
      .filter((f) => f !== SELF)
      .flatMap((f) =>
        readFileSync(f, "utf8")
          .split("\n")
          .map((line, i) => (TOO_SMALL.test(line) ? `${relative(SRC, f)}:${i + 1}` : null))
          .filter((hit): hit is string => hit !== null),
      )
    expect(offenders, "use text-xs (13px in this app) or larger").toEqual([])
  })
})
```

- [ ] **Step 2: Run the scan to verify it fails**

Run: `npx vitest run src/__tests__/min-text-size.test.ts`
Expected: FAIL, listing the remaining `text-[10px]` / `text-[11px]` lines.

- [ ] **Step 3: Sweep**

Run from `frontend/`:

```bash
rg -l 'text-\[(10|11)px\]' src | xargs perl -pi -e 's/text-\[1[01]px\]/text-xs/g'
```

Then list any class string that now carries `text-xs` twice and drop the duplicate by hand:

```bash
rg -n 'text-xs[^"`]*\btext-xs\b' src
```

- [ ] **Step 4: Run the scan, the suite and the build**

Run: `npx vitest run src/__tests__/min-text-size.test.ts && npm test && npm run typecheck && npm run build`
Expected: scan PASS; suite green; typecheck exit 0; build green. Layouts that break at the larger size are caught by Task 25's screenshots; a break seen while running the app here is fixed in this task by widening the offending container (for example a `w-24` label column to `w-28`), never by going back below 12px.

- [ ] **Step 5: Commit**

```bash
git add -A frontend/src
git commit -m "fix(a11y): raise every sub-12px text to text-xs" -m "Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

### Task 15: Notes editor accessibility

Spec §D, Notes editor. The BlockNote editor gets `aria-label="Page content"` through `domAttributes`; checklist inputs and toggle buttons get their labels from a post-render pass that re-runs when the editor's DOM changes. BlockNote renders neither label itself, so the pass records that library gap.

**Files:**
- Create: `frontend/src/features/notes/lib/editor-a11y.ts`
- Modify: `frontend/src/features/notes/use-page-editor.ts:57-62`
- Modify: `frontend/src/features/notes/page-editor.tsx:1-15,31-66`
- Create: `frontend/src/features/notes/__tests__/editor-a11y.test.ts`
- Modify: `frontend/src/features/notes/__tests__/page-editor.test.tsx`

**Interfaces:**
- Consumes: nothing.
- Produces: `labelEditorControls(root: ParentNode): void`, `useEditorControlLabels(ref: RefObject<HTMLElement | null>): void` (used only inside `page-editor.tsx`).

**Implementer:** dr-superpowers:impl-sonnet-high
**Evaluation:** files 2 - spec 0 - coupling 0 - risk 1 = 3

- [ ] **Step 1: Write the failing tests**

Create `frontend/src/features/notes/__tests__/editor-a11y.test.ts`:

```ts
import { describe, expect, it } from "vitest"
import { labelEditorControls } from "../lib/editor-a11y"

function dom(html: string): HTMLElement {
  const root = document.createElement("div")
  root.innerHTML = html
  return root
}

describe("labelEditorControls", () => {
  it("names a checklist box by the action it performs", () => {
    const root = dom(`
      <div data-content-type="checkListItem"><input type="checkbox" /></div>
      <div data-content-type="checkListItem"><input type="checkbox" checked /></div>
    `)
    labelEditorControls(root)
    const [open, done] = root.querySelectorAll("input")
    expect(open!.getAttribute("aria-label")).toBe("Mark as done")
    expect(done!.getAttribute("aria-label")).toBe("Mark as not done")
  })

  it("names a toggle button by the state it will produce", () => {
    const root = dom(`
      <div class="bn-toggle-wrapper" data-show-children="false"><button class="bn-toggle-button"></button></div>
      <div class="bn-toggle-wrapper" data-show-children="true"><button class="bn-toggle-button"></button></div>
    `)
    labelEditorControls(root)
    const [closed, open] = root.querySelectorAll("button")
    expect(closed!.getAttribute("aria-label")).toBe("Expand")
    expect(closed!.getAttribute("aria-expanded")).toBe("false")
    expect(open!.getAttribute("aria-label")).toBe("Collapse")
    expect(open!.getAttribute("aria-expanded")).toBe("true")
  })
})
```

In `frontend/src/features/notes/__tests__/page-editor.test.tsx`, append inside `describe("PageEditor", …)`:

```tsx
  it("labels the editor, its checklist boxes and its toggles", async () => {
    const blocks = toEditorBlocks([
      b("t1", "todo", "buy milk", { checked: false }),
      b("g1", "toggle", "more"),
    ]).blocks
    const { container } = render(<PageEditor initialBlocks={blocks} editable />)
    await act(async () => {})
    expect(container.querySelector('[aria-label="Page content"]')).not.toBeNull()
    expect(screen.getByRole("checkbox", { name: "Mark as done" })).toBeInTheDocument()
    expect(screen.getByRole("button", { name: "Expand" })).toBeInTheDocument()
  })
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `npx vitest run src/features/notes/__tests__/editor-a11y.test.ts src/features/notes/__tests__/page-editor.test.tsx`
Expected: FAIL — `../lib/editor-a11y` does not exist; no `[aria-label="Page content"]`.

- [ ] **Step 3: Create the labelling pass**

Create `frontend/src/features/notes/lib/editor-a11y.ts`:

```ts
import { useEffect, type RefObject } from "react"

/**
 * BlockNote gap (0.54.2): a checklist item's checkbox and a toggle's
 * disclosure button render with no accessible name, and neither accepts one
 * through `domAttributes`. This names them from the DOM BlockNote produced,
 * and is re-run whenever that DOM changes.
 */
export function labelEditorControls(root: ParentNode): void {
  root
    .querySelectorAll<HTMLInputElement>(
      '[data-content-type="checkListItem"] input[type="checkbox"]',
    )
    .forEach((input) => {
      const label = input.checked ? "Mark as not done" : "Mark as done"
      if (input.getAttribute("aria-label") !== label) {
        input.setAttribute("aria-label", label)
      }
    })

  root.querySelectorAll<HTMLElement>(".bn-toggle-button").forEach((button) => {
    const open =
      button.closest("[data-show-children]")?.getAttribute("data-show-children") ===
      "true"
    const label = open ? "Collapse" : "Expand"
    if (button.getAttribute("aria-label") !== label) {
      button.setAttribute("aria-label", label)
    }
    if (button.getAttribute("aria-expanded") !== String(open)) {
      button.setAttribute("aria-expanded", String(open))
    }
  })
}

export function useEditorControlLabels(ref: RefObject<HTMLElement | null>): void {
  useEffect(() => {
    const root = ref.current
    if (!root) return
    const relabel = () => labelEditorControls(root)
    relabel()
    // aria-* is not in the filter, so the pass's own writes never re-trigger it.
    const observer = new MutationObserver(relabel)
    observer.observe(root, {
      subtree: true,
      childList: true,
      attributes: true,
      attributeFilter: ["data-show-children", "checked"],
    })
    // Ticking a box changes the `checked` property, which no mutation reports.
    root.addEventListener("change", relabel)
    return () => {
      observer.disconnect()
      root.removeEventListener("change", relabel)
    }
  }, [ref])
}
```

- [ ] **Step 4: Wire it into the editor**

In `frontend/src/features/notes/use-page-editor.ts`, add one option to the `useCreateBlockNote({ … })` call, after `trailingBlock: false,`:

```ts
    domAttributes: { editor: { "aria-label": "Page content" } },
```

In `frontend/src/features/notes/page-editor.tsx`, add the imports:

```ts
import { useRef } from "react"
import { useEditorControlLabels } from "./lib/editor-a11y"
```

inside `PageEditor`, after `const editor = usePageEditor(initialBlocks)`:

```ts
  const editorRoot = useRef<HTMLDivElement>(null)
  useEditorControlLabels(editorRoot)
```

and attach the ref to the editor's container: change `<div className="mx-auto max-w-3xl">` to `<div ref={editorRoot} className="mx-auto max-w-3xl">`.

- [ ] **Step 5: Run tests to verify they pass**

Run: `npx vitest run src/features/notes && npm run typecheck`
Expected: PASS; typecheck exit 0.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/features/notes
git commit -m "fix(a11y): label the notes editor and its controls" -m "Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

### Task 16: Graph canvas semantics and label overlap

Spec §D, graph canvases, and the Memory Graph label half of spec §E's graph bullet, plus an owner-approved addition: a visible keyboard focus indicator on graph nodes (both carried `outline-none` with nothing in its place). Both SVG canvases wrap focusable node buttons, so the SVG itself must not be an image (whose children are presentational) — it becomes a named group, and neither container is focusable. On the Memory Graph a label that would overlap one already placed is hidden and shows while its node is hovered, focused or selected. Both SVG canvases are the demo explorer and the Code Graph canvas (Assumptions); the real Memory Graph's Sigma canvas already thins labels.

**Files:**
- Create: `frontend/src/features/memory-graph/lib/label-placement.ts`
- Modify: `frontend/src/features/memory-graph/components/memory-graph-explorer.tsx:52-70,206-312`
- Modify: `frontend/src/features/code/components/code-canvas.tsx:111-115`
- Create: `frontend/src/features/memory-graph/__tests__/label-placement.test.ts`
- Modify: `frontend/src/features/memory-graph/__tests__/memory-graph.test.tsx`
- Create: `frontend/src/features/code/__tests__/code-canvas.test.tsx`

**Interfaces:**
- Consumes: the explorer's store-driven scope (Task 7).
- Produces: `visibleLabelIds(labels: readonly LabelBox[]): Set<string>`, `interface LabelBox { id: string; x: number; y: number; text: string }` (used only by the explorer).

**Implementer:** dr-superpowers:impl-sonnet-high
**Evaluation:** files 2 - spec 0 - coupling 0 - risk 1 = 3

- [ ] **Step 1: Write the failing tests**

Create `frontend/src/features/memory-graph/__tests__/label-placement.test.ts`:

```ts
import { describe, expect, it } from "vitest"
import { visibleLabelIds } from "../lib/label-placement"

describe("visibleLabelIds", () => {
  it("keeps labels that do not collide", () => {
    const ids = visibleLabelIds([
      { id: "a", x: 0, y: 0, text: "postgres" },
      { id: "b", x: 0, y: 40, text: "redis" },
    ])
    expect([...ids]).toEqual(["a", "b"])
  })

  it("hides a label that would overlap one already placed", () => {
    const ids = visibleLabelIds([
      { id: "a", x: 0, y: 0, text: "postgres" },
      { id: "b", x: 20, y: 4, text: "pgvector" },
      { id: "c", x: 200, y: 0, text: "redis" },
    ])
    expect([...ids]).toEqual(["a", "c"])
  })
})
```

Create `frontend/src/features/code/__tests__/code-canvas.test.tsx`:

```tsx
import { render, screen } from "@testing-library/react"
import { describe, expect, it, vi } from "vitest"
import { CodeCanvas } from "../components/code-canvas"

const GRAPH = {
  repo_id: "r1",
  nodes: [
    { id: "a", name: "main.py", kind: "file" as const, file: "main.py", community: "c1" },
    { id: "b", name: "run", kind: "function" as const, file: "main.py", community: "c1" },
  ],
  edges: [{ source: "a", target: "b", type: "CONTAINS" }],
  communities: [{ id: "c1", label: "core", chart: 1 as const }],
  processes: [],
}

describe("CodeCanvas", () => {
  it("is a named group of node buttons, not an image, and not itself focusable", () => {
    render(
      <CodeCanvas
        graph={GRAPH}
        layout="force"
        colorBy="kind"
        selectedId={null}
        onSelect={vi.fn()}
        visibleIds={null}
        blastIds={null}
        highlightCommunity={null}
        processIds={null}
        playing={false}
        zoom={1}
        center={null}
      />,
    )
    const canvas = screen.getByRole("group", { name: /^Code graph — 2 nodes, 1 edges/ })
    expect(canvas).not.toHaveAttribute("tabindex")
    expect(screen.queryByRole("img")).toBeNull()
    expect(screen.getByRole("button", { name: "run (function)" })).toBeInTheDocument()
  })

  it("shows a theme-coloured ring on the node that has keyboard focus", () => {
    render(
      <CodeCanvas
        graph={GRAPH}
        layout="force"
        colorBy="kind"
        selectedId={null}
        onSelect={vi.fn()}
        visibleIds={null}
        blastIds={null}
        highlightCommunity={null}
        processIds={null}
        playing={false}
        zoom={1}
        center={null}
      />,
    )
    const node = screen.getByRole("button", { name: "run (function)" })
    expect(node.getAttribute("class")).not.toMatch(/(^|\s)outline-none(\s|$)/)
    const ring = node.querySelector('[data-focus-ring]')!
    expect(ring.getAttribute("class")).toMatch(/stroke-ring/)
    expect(ring.getAttribute("class")).toMatch(/group-focus-visible:opacity-100/)
  })
})
```

In `frontend/src/features/memory-graph/__tests__/memory-graph.test.tsx`, change the first assertion's `getByRole("img", …)` to `getByRole("group", …)` and append:

```ts
  it("shows a hidden label while its node has focus", () => {
    // Every project at once: the densest layout the fixture offers.
    useProjectStore.setState({ activeProject: null, missingProject: null })
    render(<MemoryGraphExplorer />)
    const nodes = screen.getAllByRole("button").filter((b) => b.tagName.toLowerCase() === "g")
    const hidden = nodes.find((n) => n.querySelector("text") === null)
    expect(hidden, "the fixture places at least one overlapping label").toBeDefined()
    fireEvent.focus(hidden!)
    expect(hidden!.querySelector("text")).not.toBeNull()
    fireEvent.blur(hidden!)
    expect(hidden!.querySelector("text")).toBeNull()
  })

  it("is not an image around its node buttons", () => {
    render(<MemoryGraphExplorer />)
    expect(screen.queryByRole("img")).toBeNull()
  })

  it("shows a theme-coloured ring on the node that has keyboard focus", () => {
    render(<MemoryGraphExplorer />)
    const node = screen.getByRole("button", { name: "postgres (database)" })
    expect(node.getAttribute("class")).not.toMatch(/(^|\s)outline-none(\s|$)/)
    const ring = node.querySelector('[data-focus-ring]')!
    expect(ring.getAttribute("class")).toMatch(/stroke-ring/)
    expect(ring.getAttribute("class")).toMatch(/group-focus-visible:opacity-100/)
  })
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `npx vitest run src/features/memory-graph src/features/code/__tests__/code-canvas.test.tsx`
Expected: FAIL — `../lib/label-placement` missing; both canvases have `role="img"`; the code canvas label begins "Demo code graph"; neither node has a focus ring.

- [ ] **Step 3: Create the label placement**

Create `frontend/src/features/memory-graph/lib/label-placement.ts`:

```ts
export interface LabelBox {
  id: string
  /** The node centre; the label starts to its right. */
  x: number
  y: number
  text: string
}

// The explorer's label: 10.5px monospace at x+12, baseline y+4, in viewBox
// units. A monospace glyph is ~0.6em wide.
const LABEL_OFFSET_X = 12
const CHAR_WIDTH = 6.3
const ASCENT = 8
const DESCENT = 4

/** Greedy, in input order: a label is placed unless its box overlaps a box
 *  already placed. The caller shows a hidden label while its node is
 *  hovered, focused or selected. */
export function visibleLabelIds(labels: readonly LabelBox[]): Set<string> {
  const placed: Array<{ x1: number; x2: number; y1: number; y2: number }> = []
  const visible = new Set<string>()
  for (const label of labels) {
    const box = {
      x1: label.x + LABEL_OFFSET_X,
      x2: label.x + LABEL_OFFSET_X + label.text.length * CHAR_WIDTH,
      y1: label.y - ASCENT,
      y2: label.y + DESCENT,
    }
    const collides = placed.some(
      (p) => box.x1 < p.x2 && p.x1 < box.x2 && box.y1 < p.y2 && p.y1 < box.y2,
    )
    if (collides) continue
    placed.push(box)
    visible.add(label.id)
  }
  return visible
}
```

- [ ] **Step 4: Use it in the explorer and fix both roles**

In `frontend/src/features/memory-graph/components/memory-graph-explorer.tsx`:

Add the import:

```ts
import { visibleLabelIds } from "../lib/label-placement"
```

Add, after `const [focusTopic, setFocusTopic] = useState<string | null>(null)`:

```ts
  const [revealedId, setRevealedId] = useState<string | null>(null)
```

Add, after the `positions` memo:

```ts
  const labelled = useMemo(
    () =>
      visibleLabelIds(
        scoped.entities.flatMap((e) => {
          const pos = positions[e.id]
          return pos ? [{ id: e.id, x: pos.x, y: pos.y, text: e.name }] : []
        }),
      ),
    [scoped, positions],
  )
```

On the `<svg>`, change `role="img"` to `role="group"`. On each entity `<g role="button" …>`, change `className="cursor-pointer outline-none"` to `className="group cursor-pointer focus-visible:outline-none"`, add as its first child after `<title>`:

```tsx
                      <circle
                        data-focus-ring
                        r={16}
                        strokeWidth={2}
                        className="stroke-ring fill-none opacity-0 group-focus-visible:opacity-100"
                      />
```

and add these handlers:

```tsx
                      onMouseEnter={() => setRevealedId(entity.id)}
                      onMouseLeave={() => setRevealedId(null)}
                      onFocus={() => setRevealedId(entity.id)}
                      onBlur={() => setRevealedId(null)}
```

and render the label conditionally, replacing the `<text …>{entity.name}</text>` element with:

```tsx
                      {(labelled.has(entity.id) ||
                        revealedId === entity.id ||
                        isSelected) && (
                        <text
                          x={12}
                          y={4}
                          fontSize={10.5}
                          className="font-mono"
                          fill="hsl(var(--foreground))"
                        >
                          {entity.name}
                        </text>
                      )}
```

In `frontend/src/features/code/components/code-canvas.tsx`, on each node `<g role="button" …>` change `"cursor-pointer outline-none"` inside its `cn(…)` to `"group cursor-pointer focus-visible:outline-none"` and add after its `<title>`:

```tsx
            <circle
              data-focus-ring
              r={15}
              strokeWidth={2}
              className="stroke-ring fill-none opacity-0 group-focus-visible:opacity-100"
            />
```

(The browser's own outline does not follow an SVG group's shape, so the ring is drawn in the theme's `--ring` colour and shown only on keyboard focus.) Then change the `<svg>`'s `role="img"` to `role="group"` and its `aria-label` to:

```tsx
      aria-label={`Code graph — ${graph.nodes.length} nodes, ${graph.edges.length} edges, ${layout} layout`}
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `npx vitest run src/features/memory-graph src/features/code && npm run typecheck`
Expected: PASS; typecheck exit 0.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/features/memory-graph frontend/src/features/code
git commit -m "fix(a11y): graph canvas roles, focus rings, labels" -m "Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

### Task 17: Login follows the app theme

Spec §D, Login, and spec §E, Login. The login card uses theme tokens only (no hex), the app's brand mark, the library button's own colours and a visible "Password" label; it follows light and dark mode; and the particle background takes its tint from `--primary`. The mesh gradient (fixed dark hex) is switched off.

**Files:**
- Modify: `frontend/src/features/auth/components/login-card.tsx` (whole file)
- Modify: `frontend/src/features/auth/components/login-form.tsx:61-90`
- Create: `frontend/src/lib/primary-palette.ts`
- Modify: `frontend/src/routes/_guest.tsx:1-5,22-28`
- Modify: `frontend/src/styles/globals.css:504-512`
- Create: `frontend/src/lib/__tests__/primary-palette.test.ts`
- Modify: `frontend/src/features/auth/components/__tests__/login-card.test.tsx`

**Interfaces:**
- Consumes: nothing.
- Produces: `hslTripleToRgb(triple: string): [number, number, number] | null`, `readPrimaryParticleColors(root?: HTMLElement): ParticleBackgroundProps["colors"]`; CSS class `.dm-brand-mark`.

**Implementer:** dr-superpowers:impl-sonnet-high
**Evaluation:** files 2 - spec 0 - coupling 0 - risk 1 = 3

- [ ] **Step 1: Write the failing tests**

Create `frontend/src/lib/__tests__/primary-palette.test.ts`:

```ts
import { describe, expect, it } from "vitest"
import { hslTripleToRgb, readPrimaryParticleColors } from "../primary-palette"

describe("hslTripleToRgb", () => {
  it("converts the theme's space-separated HSL triple", () => {
    expect(hslTripleToRgb("0 100% 50%")).toEqual([255, 0, 0])
    expect(hslTripleToRgb(" 120 100% 25% ")).toEqual([0, 128, 0])
    expect(hslTripleToRgb("221 83% 53%")).toEqual([36, 99, 235])
  })

  it("rejects anything that is not a triple", () => {
    expect(hslTripleToRgb("")).toBeNull()
    expect(hslTripleToRgb("#22c55e")).toBeNull()
  })
})

describe("readPrimaryParticleColors", () => {
  it("tints every particle colour from --primary", () => {
    const root = document.createElement("div")
    root.style.setProperty("--primary", "0 100% 50%")
    document.body.appendChild(root)
    try {
      expect(readPrimaryParticleColors(root)).toEqual({
        nodes: ["rgb(255, 0, 0)", "rgba(255, 0, 0, 0.7)"],
        accents: ["rgb(255, 0, 0)"],
        link: "255,0,0",
        mouseLink: "255,0,0",
      })
    } finally {
      root.remove()
    }
  })
})
```

Replace the body of `frontend/src/features/auth/components/__tests__/login-card.test.tsx` below `wrap` with:

```tsx
describe("LoginCard", () => {
  it("renders the brand wordmark, a visible password label, and submit", () => {
    wrap(<LoginCard onSuccess={() => {}} />)
    expect(screen.getByText("darkmem")).toBeInTheDocument()
    expect(screen.getByLabelText("Password")).toBeInTheDocument()
    expect(screen.getByText("Password")).not.toHaveClass("sr-only")
    expect(screen.getByRole("button", { name: /sign in/i })).toBeInTheDocument()
  })

  it("uses the app's brand mark and the library button colours", () => {
    const { container } = wrap(<LoginCard onSuccess={() => {}} />)
    expect(container.querySelector(".dm-brand-mark")).not.toBeNull()
    const submit = screen.getByRole("button", { name: /sign in/i })
    expect(submit.className).not.toMatch(/gradient|slate|#/)
  })

  it("carries no hard-coded colour in its source", () => {
    const dir = join(process.cwd(), "src/features/auth/components")
    for (const file of ["login-card.tsx", "login-form.tsx"]) {
      const source = readFileSync(join(dir, file), "utf8")
      expect(source, file).not.toMatch(/#[0-9a-fA-F]{3,8}\b|\b(slate|cyan|indigo|white|black)[-/]/)
    }
  })
})
```

and add at the top of that file:

```ts
import { readFileSync } from "node:fs"
import { join } from "node:path"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `npx vitest run src/lib/__tests__/primary-palette.test.ts src/features/auth`
Expected: FAIL — `../primary-palette` missing; no `.dm-brand-mark`; the button carries gradient classes; the sources carry hex.

- [ ] **Step 3: Create the palette helper**

Create `frontend/src/lib/primary-palette.ts`:

```ts
import type { ParticleBackgroundProps } from "@/components/particle-background"

/** The theme stores colours as bare HSL triples ("221 83% 53%"). */
export function hslTripleToRgb(triple: string): [number, number, number] | null {
  const m = triple.trim().match(/^(-?[\d.]+)(?:deg)?\s+([\d.]+)%\s+([\d.]+)%$/)
  if (!m) return null
  const h = ((Number(m[1]) % 360) + 360) % 360
  const s = Number(m[2]) / 100
  const l = Number(m[3]) / 100
  const a = s * Math.min(l, 1 - l)
  const channel = (n: number) => {
    const k = (n + h / 30) % 12
    return Math.round((l - a * Math.max(-1, Math.min(k - 3, 9 - k, 1))) * 255)
  }
  return [channel(0), channel(8), channel(4)]
}

/** Particle colours from the live accent, so the guest backdrop follows the
 *  Appearance picker instead of a fixed palette. */
export function readPrimaryParticleColors(
  root: HTMLElement = document.documentElement,
): ParticleBackgroundProps["colors"] {
  // The theme provider writes the live accent as an inline style on <html>;
  // the stylesheet default is the fallback before it has run.
  const triple =
    root.style.getPropertyValue("--primary") ||
    getComputedStyle(root).getPropertyValue("--primary")
  const rgb = hslTripleToRgb(triple)
  if (!rgb) return undefined
  const [r, g, b] = rgb
  const solid = `rgb(${r}, ${g}, ${b})`
  return {
    nodes: [solid, `rgba(${r}, ${g}, ${b}, 0.7)`],
    accents: [solid],
    link: `${r},${g},${b}`,
    mouseLink: `${r},${g},${b}`,
  }
}
```

- [ ] **Step 4: Rebuild the card and the form on tokens**

Replace `frontend/src/features/auth/components/login-card.tsx` with:

```tsx
import { Card, CardContent } from "darkraise-ui/components/card"
import { LoginForm } from "./login-form"

export function LoginCard({ onSuccess }: { onSuccess: () => void }) {
  return (
    <Card className="w-full max-w-sm">
      <CardContent className="p-8">
        <div className="mb-1 flex items-center justify-center gap-2.5">
          <span aria-hidden className="dm-brand-mark size-7" />
          <span className="text-foreground text-3xl font-extrabold tracking-tight">
            darkmem
          </span>
        </div>
        <p className="text-muted-foreground mb-6 text-center text-sm">
          Sign in to continue
        </p>
        <LoginForm onSuccess={onSuccess} />
      </CardContent>
    </Card>
  )
}
```

In `frontend/src/features/auth/components/login-form.tsx`, replace everything from the line `<PasswordInput>` (line 61) through the submit button's closing `</Button>` (line 90) — that is the password control, the closing of the `FieldWrapper` render prop and `form.Field`, and the gradient submit button — with:

```tsx
              <PasswordInput>
                <PasswordInputControl>
                  <PasswordInputField
                    id={field.name}
                    autoComplete="current-password"
                    autoFocus
                    value={field.state.value}
                    aria-invalid={isInvalid}
                    aria-describedby={ariaDescribedBy}
                    onChange={(e) => field.handleChange(e.target.value)}
                    onBlur={field.handleBlur}
                  />
                  <PasswordInputVisibilityTrigger>
                    <PasswordInputIndicator />
                  </PasswordInputVisibilityTrigger>
                </PasswordInputControl>
              </PasswordInput>
            )}
          </FieldWrapper>
        )}
      </form.Field>

      <Button type="submit" disabled={login.isPending} className="w-full">
        {login.isPending ? "Signing in…" : "Sign in"}
      </Button>
```

- [ ] **Step 5: Tint the backdrop and share the brand mask**

In `frontend/src/routes/_guest.tsx`, add `import { readPrimaryParticleColors } from "@/lib/primary-palette"` and change the backdrop to:

```tsx
      <ParticleBackground gradient={false} colors={readPrimaryParticleColors()} />
```

In `frontend/src/styles/globals.css`, replace the `.dr-brand-logo::before { … }` rule (lines 504-512) with:

```css
.dr-brand-logo::before,
.dm-brand-mark {
  background-color: hsl(var(--primary));
  -webkit-mask: url("/logo.svg") center / contain no-repeat;
  mask: url("/logo.svg") center / contain no-repeat;
}
.dr-brand-logo::before {
  content: "";
  flex: none;
  height: 2rem;
  width: 2rem;
}
.dm-brand-mark {
  display: inline-block;
  flex: none;
}
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `npx vitest run src/lib src/features/auth src/features/setup && npm run typecheck`
Expected: PASS (including `brand-assets.test.ts`); typecheck exit 0. The label's and the button's ≥ 4.5:1 contrast cannot be measured in jsdom; Task 25's axe run on `/login` in both modes is that check.

- [ ] **Step 7: Commit**

```bash
git add frontend/src/features/auth frontend/src/lib frontend/src/routes/_guest.tsx frontend/src/styles/globals.css
git commit -m "fix(auth): build the login card on theme tokens" -m "It follows light and dark mode, uses the app's brand mark and the" -m "library button, and tints the particle backdrop from --primary." -m "Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

### Task 18: Sidebar and theme surface

Spec §E, Sidebar. The active item becomes a tint plus the contrast-safe accent text with no rail or ring; the sidebar search box loses its standing accent border; and the default surface colour becomes neutral so sidebar and content share a hue. darkraise-ui offers no borderless `activeBar` value, so the active item is an unlayered CSS override that records the gap.

**Files:**
- Modify: `frontend/src/styles/globals.css` (after the sidebar header rules, line ~439)
- Modify: `frontend/src/theme.config.ts:17`
- Modify: `frontend/src/__tests__/theme-config.test.ts:56`
- Create: `frontend/src/__tests__/sidebar-style.test.ts`

**Interfaces:**
- Consumes: `--primary-text` (Task 13).
- Produces: nothing.

**Implementer:** dr-superpowers:impl-sonnet-high
**Evaluation:** files 1 - spec 0 - coupling 1 - risk 1 = 3

- [ ] **Step 1: Write the failing tests**

In `frontend/src/__tests__/theme-config.test.ts`, change `surfaceColor: "indigo",` (line 56) to `surfaceColor: "neutral",`.

Create `frontend/src/__tests__/sidebar-style.test.ts`:

```ts
import { readFileSync } from "node:fs"
import { join } from "node:path"
import { describe, expect, it } from "vitest"

const css = readFileSync(join(process.cwd(), "src/styles/globals.css"), "utf8")

function rule(selectorStart: string): string {
  const at = css.indexOf(selectorStart)
  expect(at, `no rule starting ${selectorStart}`).toBeGreaterThan(-1)
  return css.slice(at, css.indexOf("}", at))
}

describe("sidebar styling", () => {
  it("marks the active item with a tint and accent text, no rail or ring", () => {
    const active = rule(".dr-sidebar-nav .dr-sidebar-nav-item:is(.active")
    expect(active).toContain("box-shadow: none")
    expect(active).toContain("background-color: hsl(var(--primary) / 0.1)")
    expect(active).toContain("color: var(--primary-text)")
  })

  it("gives the search box the ordinary border until it has focus", () => {
    const search = rule(".dr-sidebar-layout-search .dr-search-command-trigger:not(:focus-visible)")
    expect(search).toContain("border-color: hsl(var(--border))")
  })
})
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `npx vitest run src/__tests__/theme-config.test.ts src/__tests__/sidebar-style.test.ts`
Expected: FAIL — the surface default is `indigo`; neither rule exists.

- [ ] **Step 3: Neutral surface**

In `frontend/src/theme.config.ts`, change `surfaceColor: "indigo",` to:

```ts
    surfaceColor: "neutral",
```

- [ ] **Step 4: Sidebar rules**

In `frontend/src/styles/globals.css`, add after the `.dr-top-nav-layout .dm-chrome-desc` rule and the header-actions block Task 9 added:

```css
/* Active sidebar item: a tint and the accent text colour, nothing on the
   edges. darkraise-ui's `activeBar` only offers a rail, a ring or both, so the
   borderless state is this override; it is unlayered and so beats the
   library's @layer components rules at any specificity. */
.dr-sidebar-nav .dr-sidebar-nav-item:is(.active, [data-status="active"]) {
  background-color: hsl(var(--primary) / 0.1);
  box-shadow: none;
  color: var(--primary-text);
}
.dr-sidebar-nav
  .dr-sidebar-nav-item:is(.active, [data-status="active"])
  .dr-sidebar-nav-icon-svg {
  color: var(--primary-text);
}

/* The sidebar search box carried the accent border at rest; it keeps the
   ordinary border until it is focused. */
.dr-sidebar-layout-search .dr-search-command-trigger:not(:focus-visible) {
  border-color: hsl(var(--border));
}
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `npx vitest run src/__tests__ src/lib/__tests__/theme-persistence.test.ts && npm run build`
Expected: PASS; build green.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/styles/globals.css frontend/src/theme.config.ts frontend/src/__tests__
git commit -m "style(chrome): calm the sidebar and neutral surface" -m "Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

### Task 19: Articles and Dashboard polish

Spec §E, the Articles icon, Articles list and Dashboard bullets. Articles gets the `Newspaper` icon in the nav and the page header (Documents keeps `FileText`); the article list's badge column gets a fixed width so titles align; the contribution calendar fills its card, with cell size derived from the width; stat cards get tighter padding.

**Files:**
- Modify: `frontend/src/routes/_authenticated.tsx:8-26,77-80`
- Modify: `frontend/src/routes/_authenticated/knowledge_.articles.tsx:2,14`
- Modify: `frontend/src/features/knowledge/components/articles-tab.tsx:118-133`
- Modify: `frontend/src/features/dashboard/year-heatmap.tsx:1-20,63-160`
- Modify: `frontend/src/routes/_authenticated/index.tsx:55-66,126`
- Create: `frontend/src/features/dashboard/__tests__/year-heatmap.test.tsx`
- Create: `frontend/src/features/knowledge/__tests__/articles-row.test.tsx`

**Interfaces:**
- Consumes: nothing.
- Produces: nothing.

**Implementer:** dr-superpowers:impl-sonnet-high
**Evaluation:** files 2 - spec 0 - coupling 0 - risk 1 = 3

- [ ] **Step 1: Write the failing tests**

Create `frontend/src/features/dashboard/__tests__/year-heatmap.test.tsx`:

```tsx
import { render, screen } from "@testing-library/react"
import { describe, expect, it, vi } from "vitest"

vi.mock("@tanstack/react-router", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@tanstack/react-router")>()),
  useNavigate: () => vi.fn(),
}))

import { YearHeatmap } from "../year-heatmap"

describe("YearHeatmap", () => {
  it("lays the weeks out as fluid grid columns that fill the card", () => {
    render(
      <YearHeatmap
        days={[{ date: "2026-07-24", count: 3, types: [], verified: 0, injects: 0 }]}
      />,
    )
    const grid = screen.getByTestId("heatmap-grid")
    expect(grid.style.gridTemplateColumns).toMatch(/^auto repeat\(\d+, minmax\(10px, 1fr\)\)$/)
    const cell = screen.getByRole("button", { name: /3 memories/ })
    expect(cell).toHaveClass("aspect-square", "w-full")
  })
})
```

Create `frontend/src/features/knowledge/__tests__/articles-row.test.tsx`:

```tsx
import { render, screen } from "@testing-library/react"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import type { ReactNode } from "react"
import { describe, expect, it, vi } from "vitest"

vi.mock("@/lib/demo-flag", () => ({ DEMO: true }))
vi.mock("@tanstack/react-router", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@tanstack/react-router")>()),
  Link: ({ children, className }: { children?: ReactNode; className?: string }) => (
    <a className={className}>{children}</a>
  ),
}))

import { ArticlesTab } from "../components/articles-tab"
import { useProjectStore } from "@/stores/project-store"

describe("Articles list", () => {
  it("gives every row the same badge-column width so titles align", () => {
    useProjectStore.setState({ activeProject: null, missingProject: null })
    render(
      <QueryClientProvider client={new QueryClient()}>
        <ArticlesTab />
      </QueryClientProvider>,
    )
    const columns = screen.getAllByTestId("article-badges")
    expect(columns.length).toBeGreaterThan(0)
    for (const column of columns) expect(column).toHaveClass("w-40", "shrink-0")
  })
})
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `npx vitest run src/features/dashboard/__tests__/year-heatmap.test.tsx src/features/knowledge/__tests__/articles-row.test.tsx`
Expected: FAIL — no `heatmap-grid` test id; no `article-badges` test id.

- [ ] **Step 3: Articles icon and badge column**

In `frontend/src/routes/_authenticated.tsx`, add `Newspaper` to the `lucide-react` import and change the Articles nav entry to `{ label: "Articles", href: "/knowledge/articles", icon: Newspaper }`.

In `frontend/src/routes/_authenticated/knowledge_.articles.tsx`, change the icon import to `import { Newspaper } from "lucide-react"` and `icon={FileText}` to `icon={Newspaper}`.

In `frontend/src/features/knowledge/components/articles-tab.tsx`, replace the badge column opening tag in `ArticleRow`

```tsx
      <div className="flex shrink-0 flex-col items-start gap-1.5">
```

with

```tsx
      <div
        data-testid="article-badges"
        className="flex w-40 shrink-0 flex-col items-start gap-1.5"
      >
```

- [ ] **Step 4: Fluid calendar grid**

In `frontend/src/features/dashboard/year-heatmap.tsx`, change the React import to `import { Fragment, useMemo } from "react"` and replace the whole returned JSX of `YearHeatmap` with:

```tsx
  return (
    <div className="space-y-2">
      <div className="overflow-x-auto pb-1">
        {/* One grid: a label column, then one fluid column per week, so the
            cells take the card's width instead of a fixed 12px. */}
        <div
          data-testid="heatmap-grid"
          className="grid min-w-max gap-1 sm:min-w-0"
          style={{
            gridTemplateColumns: `auto repeat(${weeks.length}, minmax(10px, 1fr))`,
          }}
        >
          <span aria-hidden />
          {weeks.map((week, i) => (
            <span
              key={`month-${i}`}
              aria-hidden
              className="text-muted-foreground relative h-4 text-xs whitespace-nowrap"
            >
              {week.monthLabel && (
                <span className="absolute left-0">{week.monthLabel}</span>
              )}
            </span>
          ))}
          {WEEKDAY_LABELS.map((label, di) => (
            <Fragment key={`row-${di}`}>
              <span
                aria-hidden
                className="text-muted-foreground flex items-center pr-1 text-xs"
              >
                {label}
              </span>
              {weeks.map((week, wi) => {
                const day = week.days[di]
                if (!day) {
                  return (
                    <span
                      key={`empty-${wi}`}
                      aria-hidden
                      className="aspect-square w-full"
                    />
                  )
                }
                return (
                  <HoverCard key={day.date} openDelay={120} closeDelay={40}>
                    <HoverCardTrigger asChild>
                      <button
                        type="button"
                        // The inject count rides the label rather than a
                        // colour alone: a coloured dot nobody can read out
                        // is not a surface a human can check push against.
                        aria-label={`${formatDayKey(day.date)} — ${day.count} memor${day.count === 1 ? "y" : "ies"}${day.injects > 0 ? `, ${day.injects} inject${day.injects === 1 ? "" : "s"}` : ""}`}
                        onClick={() =>
                          navigate({
                            to: "/memories",
                            search: { date: day.date },
                          })
                        }
                        className={cn(
                          "aspect-square w-full rounded-sm",
                          intensityClass(day.count, thresholds),
                          "hover:ring-ring focus-visible:ring-ring outline-none hover:ring-1 focus-visible:ring-1",
                          day.date === todayKey && "ring-primary/60 ring-1",
                          day.injects > 0 && "ring-info/70 ring-1 ring-offset-0",
                        )}
                      />
                    </HoverCardTrigger>
                    <HoverCardContent
                      side="top"
                      className="w-60 p-3"
                      collisionPadding={12}
                    >
                      <CellPopover day={day} />
                    </HoverCardContent>
                  </HoverCard>
                )
              })}
            </Fragment>
          ))}
        </div>
      </div>
      <div className="text-muted-foreground flex items-center gap-1.5 text-sm">
        <span>Less</span>
        {[
          "bg-muted",
          "bg-primary/25",
          "bg-primary/50",
          "bg-primary/75",
          "bg-primary",
        ].map((cls) => (
          <span key={cls} className={cn(CELL, cls)} />
        ))}
        <span>More</span>
      </div>
    </div>
  )
```

`CELL` stays (the legend uses it).

- [ ] **Step 5: Compact stat cards**

In `frontend/src/routes/_authenticated/index.tsx`, change `StatTile`'s `<CardContent className="pt-5">` to `<CardContent className="px-4 py-3">`, and the stat grid `className="grid grid-cols-2 gap-4 lg:grid-cols-4"` to `className="grid grid-cols-2 gap-3 lg:grid-cols-4"`.

- [ ] **Step 6: Run tests to verify they pass**

Run: `npx vitest run src/features/dashboard src/features/knowledge src/routes && npm run typecheck`
Expected: PASS; typecheck exit 0.
Run: `E2E_API_TARGET=http://127.0.0.1:9 timeout 900 npx playwright test --project=demo-fixture tests/dashboard.spec.ts tests/knowledge.spec.ts`
Expected: every test passes. A failure that asserts the old layout or copy this task changed is updated to the new one and named in the commit body; any other failure stops the task.

- [ ] **Step 7: Commit**

```bash
git add frontend/src/routes frontend/src/features/knowledge frontend/src/features/dashboard
git commit -m "style(ui): polish Articles and the Dashboard" -m "Articles gets its own icon and an aligned badge column; the contribution" -m "calendar fills its card and the stat cards are tighter." -m "Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

### Task 20: Notes editor styling

Spec §E, Notes. Title and editor share one left edge; the editor inherits the app font; the toggle triangle, code block and callout use the theme's `--muted-foreground`, `--muted` and semantic tokens. The checkbox `accent-color` rule already exists (`page-editor.css:25-27`) and stays.

**Files:**
- Modify: `frontend/src/features/notes/page-editor.css` (append)
- Modify: `frontend/src/features/notes/lib/editor-schema.tsx:14-19`
- Modify: `frontend/src/features/notes/page-editor.tsx` (the editor container class)
- Modify: `frontend/src/features/notes/page-pane.tsx:64,96`
- Modify: `frontend/src/features/notes/__tests__/page-editor.test.tsx`

**Interfaces:**
- Consumes: `text-success-text` (Task 13); the `editorRoot` container from Task 15.
- Produces: nothing.

**Implementer:** dr-superpowers:impl-sonnet-low
**Evaluation:** files 1 - spec 0 - coupling 0 - risk 0 = 1

- [ ] **Step 1: Write the failing test**

Append inside `describe("PageEditor", …)` in `frontend/src/features/notes/__tests__/page-editor.test.tsx`:

```tsx
  it("paints callouts with theme tokens and shares the title's left edge", async () => {
    const blocks = toEditorBlocks([b("c1", "callout", "heads up", { variant: "info" })]).blocks
    const { container } = render(<PageEditor initialBlocks={blocks} editable />)
    await act(async () => {})
    const callout = container.querySelector('[data-variant="info"]')!
    expect(callout.className).toMatch(/bg-info\/10/)
    expect(callout.className).not.toMatch(/sky-/)
    expect(container.querySelector(".max-w-3xl")).not.toHaveClass("mx-auto")
  })
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npx vitest run src/features/notes/__tests__/page-editor.test.tsx`
Expected: FAIL — the callout carries `bg-sky-500/15`; the container is `mx-auto`.

- [ ] **Step 3: Tokens for callouts**

In `frontend/src/features/notes/lib/editor-schema.tsx`, replace `CALLOUT_TONE` (lines 14-19) with:

```ts
const CALLOUT_TONE: Record<CalloutVariant, string> = {
  info: "border-info/40 bg-info/10 [&>svg]:text-info-text",
  warning: "border-warning/40 bg-warning/10 [&>svg]:text-warning-text",
  error: "border-destructive/40 bg-destructive/10 [&>svg]:text-destructive",
  success: "border-success/40 bg-success/10 [&>svg]:text-success-text",
}
```

- [ ] **Step 4: Font, edges, toggle and code block**

Append to `frontend/src/features/notes/page-editor.css`:

```css
/* The editor writes in the app's font at the app's size, not BlockNote's
   Inter at 16px. */
.bn-container.bn-shadcn .bn-default-styles {
  font-family: inherit;
  font-size: inherit;
}

/* BlockNote insets the document 54px for its side menu; the pane supplies
   that gutter instead, so the title and the first block share one edge. */
.bn-container.bn-shadcn .bn-editor {
  padding-inline: 0;
}

.bn-container.bn-shadcn .bn-toggle-button {
  color: hsl(var(--muted-foreground));
}

.bn-container.bn-shadcn [data-content-type="codeBlock"] {
  background-color: hsl(var(--muted));
  color: hsl(var(--foreground));
}
.bn-container.bn-shadcn [data-content-type="codeBlock"] > div > select {
  color: hsl(var(--muted-foreground));
}
```

In `frontend/src/features/notes/page-editor.tsx`, change the editor container `className="mx-auto max-w-3xl"` to `className="max-w-3xl"`.

In `frontend/src/features/notes/page-pane.tsx`, give the title row and the scroll area the same left gutter: change `<div className="flex items-center gap-3">` (line 64) to `<div className="flex items-center gap-3 pl-12">` and `<ScrollArea className="min-h-0 flex-1 pr-3">` (line 96) to `<ScrollArea className="min-h-0 flex-1 pr-3 pl-12">`.

- [ ] **Step 5: Run tests to verify they pass**

Run: `npx vitest run src/features/notes && npm run typecheck`
Expected: PASS; typecheck exit 0.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/features/notes
git commit -m "style(notes): put the page editor on theme tokens" -m "Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

### Task 21: Jobs and Review controls

Spec §E, Jobs and Review. A job card's description expands on click; the trigger ("Run") is an outline button; a failed last run shows the word "failed" beside its icon. Review's mode switch becomes a darkraise-ui `SegmentGroup`, and the stray `/knowledge · review` label goes.

**Files:**
- Modify: `frontend/src/features/jobs/components/job-grid-card.tsx:1-5,36-38`
- Modify: `frontend/src/features/jobs/components/job-actions.tsx:73-81`
- Modify: `frontend/src/features/jobs/components/job-schedule-state.tsx:62-73`
- Modify: `frontend/src/features/knowledge/components/review-tab.tsx`
- Create: `frontend/src/features/jobs/__tests__/job-card.test.tsx`
- Modify: `frontend/src/features/knowledge/components/__tests__/review-tab-scope.test.tsx`

**Interfaces:**
- Consumes: `review-tab.tsx` as Task 7 left it.
- Produces: nothing.

**Implementer:** dr-superpowers:impl-sonnet-medium
**Evaluation:** files 2 - spec 0 - coupling 0 - risk 0 = 2

- [ ] **Step 1: Write the failing tests**

Create `frontend/src/features/jobs/__tests__/job-card.test.tsx`:

```tsx
import { render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { describe, expect, it, vi } from "vitest"
import { useDemoStore } from "@/demo/store"
import { JobGridCard } from "../components/job-grid-card"

function renderCard(key: string) {
  const job = useDemoStore.getState().jobs.find((j) => j.key === key)!
  render(
    <JobGridCard
      job={job}
      onTrigger={vi.fn()}
      onConfigure={vi.fn()}
      onHistory={vi.fn()}
      onToggleEnabled={vi.fn()}
    />,
  )
  return job
}

describe("JobGridCard", () => {
  it("expands its description on click", async () => {
    const job = renderCard("pipeline_failure_cleanup")
    const description = screen.getByRole("button", { name: job.description })
    expect(description).toHaveAttribute("aria-expanded", "false")
    expect(description).toHaveClass("line-clamp-2")
    await userEvent.click(description)
    expect(description).toHaveAttribute("aria-expanded", "true")
    expect(description).not.toHaveClass("line-clamp-2")
  })

  it("offers Run as an outline button", () => {
    renderCard("token_blocklist_cleanup")
    expect(screen.getByRole("button", { name: "Trigger now" })).toHaveAttribute(
      "data-variant",
      "outline",
    )
  })

  it("says failed in words beside a failed run's icon", () => {
    renderCard("expired_memory_cleanup")
    expect(screen.getByText("failed")).toBeInTheDocument()
  })
})
```

In `frontend/src/features/knowledge/components/__tests__/review-tab-scope.test.tsx`, append inside the `describe`:

```tsx
  it("switches modes with a segmented control and drops the path label", () => {
    useProjectStore.setState({ activeProject: null, missingProject: null })
    render(<ReviewTab />, { wrapper })
    expect(screen.getByRole("radiogroup", { name: "Triage mode" })).toBeInTheDocument()
    expect(screen.queryByText(/\/knowledge ·/)).toBeNull()
  })
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `npx vitest run src/features/jobs/__tests__/job-card.test.tsx src/features/knowledge/components/__tests__/review-tab-scope.test.tsx`
Expected: FAIL — the description is a paragraph, the trigger is `default`, no "failed" word, the mode switch is a toggle group and the path label renders.

- [ ] **Step 3: Job card**

In `frontend/src/features/jobs/components/job-grid-card.tsx`, add `import { useState } from "react"` and `import { cn } from "darkraise-ui/lib"`, add `const [expanded, setExpanded] = useState(false)` as the first line of `JobGridCard`, and replace the description paragraph with:

```tsx
        <button
          type="button"
          aria-expanded={expanded}
          onClick={() => setExpanded((open) => !open)}
          className={cn(
            "text-muted-foreground text-left text-sm",
            !expanded && "line-clamp-2",
          )}
        >
          {job.description}
        </button>
```

In `frontend/src/features/jobs/components/job-actions.tsx`, change the trigger `Action`'s `variant="default"` to `variant="outline"`, and in the doc comment above `JobActions` (lines 14-23) replace the two bullets for **Trigger now** and **Configure** with:

```ts
 * - `outline` for **Trigger now** and **Configure** — Trigger acts on the
 *   system the moment it is pressed (and is disabled while a run holds the
 *   lock); Configure changes what the job will do through a dialog with its
 *   own save. The label tooltip says which is which.
```

(the `ghost` bullet for **Run history** stays).

In `frontend/src/features/jobs/components/job-schedule-state.tsx`, replace the final return of `JobLastRun` (lines 62-73) with:

```tsx
  const ok = job.last_status === "ok"
  const Icon = ok ? CircleCheck : CircleAlert
  return (
    <span
      className={`inline-flex w-fit items-center gap-1.5 text-sm ${
        ok ? "text-success-text" : "text-destructive"
      }`}
    >
      <Icon aria-hidden className="size-[var(--icon-size-sm)] shrink-0" />
      {!ok && <span className="font-medium">failed</span>}
      <span className="text-muted-foreground truncate">{when ?? job.last_status}</span>
    </span>
  )
```

- [ ] **Step 4: Review mode switch**

In `frontend/src/features/knowledge/components/review-tab.tsx`, replace the `toggle-group` import with:

```ts
import {
  SegmentGroup,
  SegmentGroupIndicator,
  SegmentGroupItem,
} from "darkraise-ui/components/segment-group"
```

and replace the `<ToggleGroup …>…</ToggleGroup>` plus the `<span …>/knowledge · {mode}</span>` with:

```tsx
        <SegmentGroup
          aria-label="Triage mode"
          value={mode}
          onValueChange={(value) => {
            if (value === "review" || value === "hygiene") setMode(value)
          }}
        >
          <SegmentGroupIndicator />
          <SegmentGroupItem value="review">Review — truth</SegmentGroupItem>
          <SegmentGroupItem value="hygiene">Hygiene — housekeeping</SegmentGroupItem>
        </SegmentGroup>
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `npx vitest run src/features/jobs src/features/knowledge && npm run typecheck`
Expected: PASS, including the existing `review-tab.test.tsx`, which switches modes by clicking the "Hygiene — housekeeping" text; typecheck exit 0.
Run: `E2E_API_TARGET=http://127.0.0.1:9 timeout 900 npx playwright test --project=demo-fixture tests/activity.spec.ts tests/knowledge.spec.ts`
Expected: every test passes. A failure that asserts the old layout or copy this task changed is updated to the new one and named in the commit body; any other failure stops the task.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/features/jobs frontend/src/features/knowledge
git commit -m "feat(ui): clearer job cards and review mode switch" -m "Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

### Task 22: Timestamps and kind lists in prose

Spec §F, "Both modes": timestamps render through `lib/format.ts` (relative, absolute on hover) and kind lists read as prose. It also moves the per-row "ratify/reject are REST/UI … never exposed over MCP" note into a single help tooltip on the Review page, shown in both modes, because the row note holding it is the one this task rewrites. Class strings below are as Tasks 13 and 14 left them (`text-[10px]` is already `text-xs`).

**Files:**
- Create: `frontend/src/components/darkmem/timestamp.tsx`
- Modify: `frontend/src/components/darkmem/index.ts`
- Modify: `frontend/src/lib/format.ts` (append)
- Modify: `frontend/src/features/knowledge/components/review-queue.tsx:27-33,264-267,311-315`
- Modify: `frontend/src/features/knowledge/components/review-tab.tsx`
- Modify: `frontend/src/features/knowledge/components/dispute-panel.tsx:1,15-21`
- Modify: `frontend/src/features/knowledge/components/facts-tab.tsx:89-91`
- Modify: `frontend/src/features/knowledge/components/fact-ladder.tsx:3,42-44`
- Modify: `frontend/src/features/knowledge/components/fact-detail.tsx:6,451-455`
- Modify: `frontend/src/routes/_authenticated/knowledge_.articles_.$articleId.tsx:6,335,361`
- Modify: `frontend/src/features/knowledge/components/review-queue.tsx:179,185` (suspicion block)
- Modify: `frontend/src/features/knowledge/components/hygiene-queue.tsx:29,353-354,381-385`
- Modify: `frontend/src/features/knowledge/components/fact-sources.tsx:3,52`
- Modify: `frontend/src/features/knowledge/components/fact-detail.tsx:6,50`
- Modify: `frontend/src/features/knowledge/components/belief-window.tsx:4-11`
- Modify: `frontend/src/features/code/components/reindex-dialog.tsx:79-81`
- Create: `frontend/src/components/darkmem/__tests__/timestamp.test.tsx`
- Modify: `frontend/src/lib/__tests__/format.test.ts`
- Modify: `frontend/src/features/knowledge/components/__tests__/review-tab.test.tsx`

**Interfaces:**
- Consumes: nothing.
- Produces: `Timestamp`, `formatList`, `formatWhen(iso: string): string` (Contracts; `formatWhen` is used where the value must be a plain string, such as a `meta` prop).

**Implementer:** dr-superpowers:impl-sonnet-medium
**Evaluation:** files 2 - spec 0 - coupling 0 - risk 0 = 2

- [ ] **Step 1: Write the failing tests**

Create `frontend/src/components/darkmem/__tests__/timestamp.test.tsx`:

```tsx
import { render, screen } from "@testing-library/react"
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"
import { Timestamp } from "../timestamp"

beforeEach(() => {
  vi.useFakeTimers()
  vi.setSystemTime(new Date("2026-09-18T12:00:00Z"))
})
afterEach(() => vi.useRealTimers())

describe("Timestamp", () => {
  it("reads relative and carries the absolute time on hover", () => {
    const { container } = render(<Timestamp iso="2026-09-18T09:00:00Z" />)
    const time = container.querySelector("time")!
    expect(time).toHaveTextContent("3h ago")
    expect(time).toHaveAttribute("datetime", "2026-09-18T09:00:00Z")
    expect(time.getAttribute("title")).toBe(new Date("2026-09-18T09:00:00Z").toLocaleString())
  })

  it("shows a value that is not a date as written, and a missing one as a dash", () => {
    const { rerender } = render(<Timestamp iso="14:10 UTC" />)
    expect(screen.getByText("14:10 UTC")).toBeInTheDocument()
    rerender(<Timestamp iso={null} />)
    expect(screen.getByText("—")).toBeInTheDocument()
  })
})
```

Append to `frontend/src/lib/__tests__/format.test.ts` (add `formatList` and `formatWhen` to its `../format` import):

```ts
describe("formatList", () => {
  it("reads as prose", () => {
    expect(formatList([])).toBe("")
    expect(formatList(["memory"])).toBe("memory")
    expect(formatList(["code", "memory"])).toBe("code and memory")
    expect(formatList(["code", "human", "memory"])).toBe("code, human and memory")
  })
})

describe("formatWhen", () => {
  it("passes a value that is not a date through unchanged", () => {
    expect(formatWhen("14:10 UTC")).toBe("14:10 UTC")
  })
})
```

Append to `frontend/src/features/knowledge/components/__tests__/review-tab.test.tsx`:

```tsx
describe("ReviewTab: plain-language row chrome", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    useDetailLevel.setState({ level: "advanced" })
  })

  it("renders the queued time through the shared timestamp, and the MCP note once", async () => {
    mockApi()
    const { container } = render(withQuery(<ReviewTab />))
    await screen.findByText(/why ranked here:/)
    expect(container.querySelector('time[datetime="2026-08-01T00:00:00Z"]')).not.toBeNull()
    expect(screen.queryByText(/2026-08-01T00:00:00Z/)).toBeNull()
    expect(screen.queryByText(/never exposed over MCP/)).toBeNull()
    expect(screen.getByRole("button", { name: "About review actions" })).toBeInTheDocument()
  })
})
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `npx vitest run src/components/darkmem/__tests__/timestamp.test.tsx src/lib/__tests__/format.test.ts src/features/knowledge/components/__tests__/review-tab.test.tsx`
Expected: FAIL — `../timestamp` missing, `formatList` not exported, the raw ISO string and the MCP note render.

- [ ] **Step 3: The primitives**

Append to `frontend/src/lib/format.ts`:

```ts
/** "code and memory", "code, human and memory" — a list as a sentence
 *  rather than `[code, memory]`. */
export function formatList(items: readonly string[]): string {
  if (items.length <= 1) return items[0] ?? ""
  return `${items.slice(0, -1).join(", ")} and ${items[items.length - 1]}`
}

/** `relativeTime` for a value that must stay a plain string (a `meta` prop);
 *  a value that is not a date passes through as written. */
export function formatWhen(iso: string): string {
  return Number.isNaN(new Date(iso).getTime()) ? iso : relativeTime(iso)
}
```

Create `frontend/src/components/darkmem/timestamp.tsx`:

```tsx
import { relativeTime } from "@/lib/format"

/** Every timestamp a reader sees: relative in the text, absolute on hover. A
 *  value that is not a date (a demo label such as "14:10 UTC") is shown as
 *  written rather than as "NaN". */
export function Timestamp({
  iso,
  className,
}: {
  iso: string | null | undefined
  className?: string
}) {
  if (!iso) return <span className={className}>—</span>
  const date = new Date(iso)
  if (Number.isNaN(date.getTime())) return <span className={className}>{iso}</span>
  return (
    <time dateTime={iso} title={date.toLocaleString()} className={className}>
      {relativeTime(iso)}
    </time>
  )
}
```

In `frontend/src/components/darkmem/index.ts`, add:

```ts
export { Timestamp } from "./timestamp"
```

- [ ] **Step 4: Review queue and Review page**

In `frontend/src/features/knowledge/components/review-queue.tsx`, add `Timestamp,` to the `@/components/darkmem` import (lines 27-33). Replace the fact row's note span (the `<span …>` holding `queued since {fact.created_at} · ratify/reject are REST/UI, authenticated — never exposed over MCP`) with:

```tsx
        <span className="text-muted-foreground ml-auto text-xs">
          queued <Timestamp iso={fact.created_at} />
        </span>
```

and replace the article row's meta paragraph (the `<p …>` holding `synthesized ${article.synthesized_at}` … `created {article.created_at}`) with:

```tsx
      <p className="text-muted-foreground text-sm">
        {article.synthesized_at ? (
          <>
            synthesised <Timestamp iso={article.synthesized_at} />
          </>
        ) : (
          "not synthesised yet"
        )}
        {" · created "}
        <Timestamp iso={article.created_at} />
      </p>
```

In `frontend/src/features/knowledge/components/review-tab.tsx`, add `import { HelpTip } from "@/components/darkmem"` and put the tooltip after the `</SegmentGroup>` (Task 21) inside the toolbar `div`:

```tsx
        <HelpTip label="About review actions">
          Ratify and reject are available only here, in the signed-in app; no
          MCP tool can reach them, whatever scopes a key holds.
        </HelpTip>
```

- [ ] **Step 5: Kind lists and the remaining timestamps**

- `features/knowledge/components/dispute-panel.tsx`: add `import { formatList } from "@/lib/format"`, and replace the kinds paragraph's content with
  ```tsx
          {side.origin_count} {side.origin_count === 1 ? "origin" : "origins"},
          of kind {formatList(side.origin_kinds)}
  ```
- `features/knowledge/components/facts-tab.tsx`: add `import { formatList } from "@/lib/format"` and change `` ` · ${fact.origin_kinds.join(", ")}` `` to `` ` · ${formatList(fact.origin_kinds)}` ``.
- `features/knowledge/components/fact-ladder.tsx`: add `Timestamp` to the `@/components/darkmem` import and change `{event.created_at}` to `<Timestamp iso={event.created_at} />`.
- `features/knowledge/components/fact-detail.tsx`: add `Timestamp` to the `@/components/darkmem` import and change `under-sourced since {fact.demotion_pending_since}` to `under-sourced since <Timestamp iso={fact.demotion_pending_since} />`.
- `routes/_authenticated/knowledge_.articles_.$articleId.tsx`: add `Timestamp` to the `@/components/darkmem` import and `import { formatWhen } from "@/lib/format"`; change ``meta={`stale since ${article.stale.since}`}`` to ``meta={`stale since ${formatWhen(article.stale.since)}`}`` and `<MetaRow label="synthesised">{article.synthesized_at}</MetaRow>` to `<MetaRow label="synthesised"><Timestamp iso={article.synthesized_at} /></MetaRow>`.

- `features/knowledge/components/review-queue.tsx` (suspicion block): `· since {s.suspected_at}` → `· since <Timestamp iso={s.suspected_at} />`, and `counterpart withdrawn {s.counterpart_expired_at} —` → `counterpart withdrawn <Timestamp iso={s.counterpart_expired_at} /> —`.
- `features/knowledge/components/hygiene-queue.tsx`: add `Timestamp` to the `@/components/darkmem` import (line 29) and `import { formatWhen } from "@/lib/format"`; in both Advanced-only detail lines change the trailing `{row.created_at}` (lines 354 and 385) to `<Timestamp iso={row.created_at} />`, `` ` · detected_at ${row.detected_at}` `` (line 353) to `` ` · detected_at ${formatWhen(row.detected_at)}` `` and `` ` · expires_at ${row.expires_at}` `` (line 381) to `` ` · expires_at ${formatWhen(row.expires_at)}` ``.
- `features/knowledge/components/fact-sources.tsx`: add `Timestamp` to the `@/components/darkmem` import (line 3) and change `{source.at}` (line 52) to `<Timestamp iso={source.at} />`.
- `features/knowledge/components/fact-detail.tsx`: change the demo ladder row's `{event.at}` (line 50) to `<Timestamp iso={event.at} />` (a demo label that is not a date renders as written).
- `features/knowledge/components/belief-window.tsx`: add `import { Timestamp } from "@/components/darkmem"` and in `DateField` change `<span>{value ?? "—"}</span>` to `<Timestamp iso={value} />` (it renders "—" for null itself).
- `features/code/components/reindex-dialog.tsx`: add `import { formatWhen } from "@/lib/format"` and change `` ` · last indexed ${repo.last_indexed_at}` `` to `` ` · last indexed ${formatWhen(repo.last_indexed_at)}` ``.

The backend's own claim sentence ("asserted by N distinct origins of kinds [memory, code]") is not a frontend format and is left as served (Assumptions).

- [ ] **Step 6: Run tests to verify they pass**

Run: `npx vitest run src/components/darkmem src/lib src/features/knowledge src/routes && npm run typecheck`
Expected: PASS; typecheck exit 0. A test asserting an old raw ISO string or bracket list in these components is updated to the new text and named in the commit body.

- [ ] **Step 7: Commit**

```bash
git add frontend/src/components/darkmem frontend/src/lib frontend/src/features/knowledge frontend/src/routes
git commit -m "feat(copy): relative timestamps and prose kind lists" -m "Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

### Task 23: Advanced-only detail and corrected copy

Spec §F, the Advanced-only list, the "long explanatory paragraphs" bullet and the stale-copy bullet. Advanced-only: task ids ("activated by T2.30"), raw config keys and snake_case identifiers (arm aliases, dispute-evidence fields), algorithm names ("Leiden"), and the "populated" data-state word ("empty", "degraded" and failed states stay in both modes). The Activity → Pipeline, Settings → Flags and Settings → LLM intros shrink to one line with the rest in their help tooltip. Two stale claims are corrected. Exclusion tags stay in both modes (Global Constraints, invariant 14).

**Files:**
- Modify: `frontend/src/features/knowledge/components/list-surface.tsx`
- Modify: `frontend/src/features/activity/components/module-surface.tsx:1-10,36-56`
- Modify: `frontend/src/features/chat/components/chat-context-panel.tsx:75-86`, `demo-context-panel.tsx:24-35`
- Modify: `frontend/src/features/memories/components/real-memories-view.tsx:148-156`, `frontend/src/routes/_authenticated/memories.tsx` (the results-header "populated" span)
- Modify: `frontend/src/features/settings/components/flags-tab.tsx:257-264,311-335,1310-1316`
- Modify: `frontend/src/features/settings/components/llm-tab.tsx:32-47`
- Modify: `frontend/src/features/settings/use-llm-tab-binding.ts:50-55`
- Modify: `frontend/src/features/activity/components/pipeline-tab.tsx:3,127-136`
- Modify: `frontend/src/features/knowledge/components/review-queue.tsx:120-160,573`
- Modify: `frontend/src/features/knowledge/components/topics-tab.tsx` (the `Leiden communities` heading inside `TopicsForProject`, which Task 8 split out of `TopicsTab`)
- Modify: `frontend/src/features/knowledge/components/articles-tab.tsx` (the `ExclusionStrip` reason)
- Modify: `frontend/src/features/code/components/real-code-graph-view.tsx:545`
- Modify: `frontend/src/features/activity/components/monitors-tab.tsx:163` (the staged buffer card's `reason`)
- Modify: `frontend/src/features/knowledge/components/dispute-panel.tsx:12,21`
- Create: `frontend/src/components/darkmem/__tests__/advanced-only-copy.test.tsx`

**Interfaces:**
- Consumes: `useDetailLevel` (existing); the class names Task 13 introduced (`text-success-text`).
- Produces: nothing.

**Implementer:** dr-superpowers:impl-sonnet-high
**Evaluation:** files 2 - spec 0 - coupling 0 - risk 1 = 3

- [ ] **Step 1: Write the failing test**

Create `frontend/src/components/darkmem/__tests__/advanced-only-copy.test.tsx`:

```tsx
import { render, screen } from "@testing-library/react"
import { beforeEach, describe, expect, it } from "vitest"
import { useDetailLevel } from "@/components/darkmem"
import { ListSurface } from "@/features/knowledge/components/list-surface"
import { SurfaceStateChip } from "@/features/activity/components/module-surface"

describe("the populated state word is advanced-only", () => {
  beforeEach(() => useDetailLevel.setState({ level: "simple" }))

  it("ListSurface hides 'populated' in Simple and keeps 'empty'", () => {
    const { rerender } = render(
      <ListSurface title="Facts" populated>
        <div />
      </ListSurface>,
    )
    expect(screen.queryByText("populated")).toBeNull()
    rerender(
      <ListSurface title="Facts" populated={false}>
        <div />
      </ListSurface>,
    )
    expect(screen.getByText("empty")).toBeInTheDocument()
  })

  it("SurfaceStateChip hides 'populated' in Simple and keeps the others", () => {
    const { rerender } = render(<SurfaceStateChip state="populated" />)
    expect(screen.queryByText("populated")).toBeNull()
    rerender(<SurfaceStateChip state="error" />)
    expect(screen.getByText("error")).toBeInTheDocument()
    rerender(<SurfaceStateChip state="empty" />)
    expect(screen.getByText("empty")).toBeInTheDocument()
  })

  it("both show 'populated' in Advanced", () => {
    useDetailLevel.setState({ level: "advanced" })
    render(
      <>
        <ListSurface title="Facts" populated>
          <div />
        </ListSurface>
        <SurfaceStateChip state="populated" />
      </>,
    )
    expect(screen.getAllByText("populated")).toHaveLength(2)
  })
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npx vitest run src/components/darkmem/__tests__/advanced-only-copy.test.tsx`
Expected: FAIL — "populated" renders in Simple mode.

- [ ] **Step 3: The populated word**

In `frontend/src/features/knowledge/components/list-surface.tsx`, add `import { useDetailLevel } from "@/components/darkmem"`, add `const advanced = useDetailLevel((s) => s.level) === "advanced"` as the component's first line, and wrap the state span:

```tsx
        {(!populated || advanced) && (
          <span
            className={cn(
              "font-mono text-sm",
              populated ? "text-success-text" : "text-muted-foreground",
            )}
          >
            {populated ? "populated" : "empty"}
          </span>
        )}
```

In `frontend/src/features/activity/components/module-surface.tsx`, add `import { useDetailLevel } from "@/components/darkmem"` and make `SurfaceStateChip` start with:

```tsx
  const advanced = useDetailLevel((s) => s.level) === "advanced"
  if (state === "populated" && !advanced) return null
```

(before its `STATE_STYLES[state]` destructuring).

In `frontend/src/features/chat/components/chat-context-panel.tsx`, add `useDetailLevel` to the `@/components/darkmem` import (or add that import), read `const advanced = useDetailLevel((s) => s.level) === "advanced"` in the component, and render the state span only when `!populated || degraded || advanced`. In `demo-context-panel.tsx` do the same with the condition `!context || context.degraded || advanced`.

In `frontend/src/features/memories/components/real-memories-view.tsx` and the demo `routes/_authenticated/memories.tsx`, read `const advanced = useDetailLevel((s) => s.level) === "advanced"` (import `useDetailLevel` from `@/components/darkmem`) and render the results header's populated/empty span only when the list is empty or `advanced` (`rows.length === 0 || advanced` in the real view, `shownCount === 0 || advanced` in the demo page).

- [ ] **Step 4: Settings copy**

In `frontend/src/features/settings/components/flags-tab.tsx`:

- add `useDetailLevel` to the `@/components/darkmem` import;
- `ActivationNote` becomes
  ```tsx
  function ActivationNote({ taskId }: { taskId?: string }) {
    const advanced = useDetailLevel((s) => s.level) === "advanced"
    if (!taskId || !advanced) return null
    return (
      <span className="text-muted-foreground font-mono text-sm whitespace-nowrap">
        activated by <span className="font-semibold">{taskId}</span>
      </span>
    )
  }
  ```
- in `ArmRow`, add `const advanced = useDetailLevel((s) => s.level) === "advanced"` as its first line and change `{arm.alias && (` to `{arm.alias && advanced && (`;
- replace the intro `<span>` (lines 1311-1316) with `<span>Retrieval weights, feature flags and pipeline tunables.</span>` and prepend to the existing "About the Flags tab" tooltip text: `Ranking-arm weights, behavioral feature flags, graph augmentation, the pipeline and embedding tunables, classification, the corroboration promotion gate and the repo auto-provision allowlist.` (a new first sentence, followed by the existing text).

In `frontend/src/features/settings/components/llm-tab.tsx`, replace the intro block (the `<span>` starting "Seven purposes" and its `HelpTip`) with:

```tsx
        <span>Eight purposes, all live — each picks a provider and a model.</span>
        <HelpTip label="About the LLM tab">
          Each purpose picks a provider from the Providers sub-tab plus the
          model and params that vary per purpose. `verification` is read-only
          here: it judges the verification ladder, and its qualification is a
          gate&apos;s evidence. A save live-reloads the orchestrator — no
          redeploy, no LLM_* env vars. Each purpose is one row naming a shared
          provider row, so a credential rotation on the Providers sub-tab
          reaches every purpose that uses it with nothing to re-apply here.
          Every vendor auth, reasoning-control and structured-output quirk that
          api_kind selects is resolved by the backend orchestrator, never
          re-implemented here.
        </HelpTip>
```

In `frontend/src/features/settings/use-llm-tab-binding.ts`, change the `synthesis` role to `"Layer-3 article write-ups and auto-research write-ups"` and delete the comment above it that says nothing reads the row.

- [ ] **Step 5: Activity intro**

In `frontend/src/features/activity/components/pipeline-tab.tsx`, add `HelpTip` to the `@/components/darkmem` import and replace the intro `<p>` (lines 128-136) with:

```tsx
      <div className="text-muted-foreground flex max-w-4xl items-center gap-1.5 text-sm">
        <span>Each captured memory&apos;s progress through the pipeline.</span>
        <HelpTip label="About the pipeline">
          A memory moves through content embed, extract and classify, entity
          embed, dedup and write, and ends in one terminal state — completed,
          partial or failed. A partial memory always names the step that
          broke. There is no per-phase progress event, so a running row shows
          the steps its one eventual terminal broadcast resolves into.
        </HelpTip>
      </div>
```

- [ ] **Step 6: Knowledge and code copy**

In `frontend/src/features/knowledge/components/review-queue.tsx`, in `EvidenceBlock` add `const advanced = useDetailLevel((s) => s.level) === "advanced"` after the early returns' `payload` lookup, and replace its final `return (…)` with:

```tsx
  return (
    <div className="border-border bg-muted/10 space-y-1 rounded-md border border-dashed p-2 text-sm">
      {advanced && (
        <p className="font-mono">
          outcome {payload.outcome ?? "—"} · origin_count{" "}
          {payload.origin_count ?? "—"} · required_n {payload.required_n ?? "—"} ·
          gate_fired {payload.gate_fired ?? "—"}
        </p>
      )}
      {advanced && payload.source_kinds && payload.source_kinds.length > 0 && (
        <p className="font-mono">source_kinds [{payload.source_kinds.join(", ")}]</p>
      )}
      {c ? (
        <p>
          Contradicted by: {c.counterpart_subject} {c.counterpart_rel_type}{" "}
          {c.counterpart_object}
          {advanced && (
            <span className="font-mono">
              {" "}
              · rule {c.rule} · witness_origin {c.witness_origin}
            </span>
          )}
        </p>
      ) : (
        !advanced && (
          <p className="text-muted-foreground">
            The dispute&apos;s evidence is recorded; Advanced shows the ladder&apos;s raw decision.
          </p>
        )
      )}
    </div>
  )
```

and change the empty-articles `EmptyState` description (line 573) to `"The article half of the review queue is caught up. Articles are queued here when synthesis cannot ground one."`.

In `frontend/src/features/knowledge/components/topics-tab.tsx`, inside `TopicsForProject` (Task 8 renamed the old `TopicsTab` body; `useDetailLevel` is already imported at line 12) add `const advanced = useDetailLevel((s) => s.level) === "advanced"` as its first line and change the heading `<span className="text-sm font-semibold">Leiden communities</span>` to:

```tsx
        <span className="text-sm font-semibold">
          Topic communities
          {advanced && <span className="text-muted-foreground font-normal"> (Leiden)</span>}
        </span>
```

In `frontend/src/features/knowledge/components/articles-tab.tsx`, change the `ExclusionStrip` item's `reason` to `"Awaiting review — withheld from this view and routed to Knowledge → Review; nothing was deleted."` (its `tag: "by_review_state"` stays).

In `frontend/src/features/code/components/real-code-graph-view.tsx`, change `"Leiden clustering found no group above the size threshold in this repository."` to `"Community detection found no group above the size threshold in this repository."`.

In `frontend/src/features/activity/components/monitors-tab.tsx`, in the component rendering the staged buffer card (the `StagedCard` whose `reason` begins "T1.61 could not add"), add `const advanced = useDetailLevel((s) => s.level) === "advanced"` (import `useDetailLevel` from `@/components/darkmem` if the file does not already) and change its `reason` to:

```tsx
          reason={`No API route reads or acts on the capture buffer yet, so this panel has nothing live to bind — an honest gap, not a broken panel.${advanced ? " (T1.61 recorded it in the epic amendment log.)" : ""}`}
```

In `frontend/src/features/knowledge/components/dispute-panel.tsx`, add `import { useDetailLevel } from "@/components/darkmem"` (merge into its existing `@/components/darkmem` import), add `const advanced = useDetailLevel((s) => s.level) === "advanced"` as the first line of `DisputeSideCard`, change the `object_name: {side.object_name}` paragraph's content (line 12) to `{advanced ? "object_name: " : "Object: "}{side.object_name}`, and change the section label `sources — grouped by origin_key` (line 21) to `{advanced ? "sources — grouped by origin_key" : "Sources, grouped by origin"}`.

- [ ] **Step 7: Run tests to verify they pass**

Run: `npx vitest run src/components/darkmem src/features && npm run typecheck`
Expected: PASS; typecheck exit 0. A test that asserted "populated", an arm alias, "activated by …", "Leiden communities" or a replaced sentence **while in Simple mode** is updated to the new behaviour and named in the commit body; the same assertion in Advanced mode must still pass unchanged.

- [ ] **Step 8: Run the honesty specs**

Run: `E2E_API_TARGET=http://127.0.0.1:9 timeout 900 npx playwright test --project=demo-fixture tests/honesty`
Expected: every test passes (labels, lifecycle badges, exclusion counts and tags still render in both modes).

- [ ] **Step 9: Commit**

```bash
git add frontend/src/components/darkmem frontend/src/features frontend/src/routes/_authenticated/memories.tsx
git commit -m "feat(copy): keep implementation detail in Advanced" -m "Task ids, raw keys, algorithm names and the populated state word render" -m "only in Advanced; long intros move to help tooltips; stale LLM and" -m "article-synthesis copy is corrected." -m "Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

### Task 24: Demo-only visuals

Spec §H. The demo Memory Graph publishes its `PageChrome` like the real page; demo memory rows sit in the same results card as the real view's, through one shared header and the same body spacing. The third §H item, the demo thread list clipping "+ New", shipped with Task 11's shared header fix.

**Files:**
- Create: `frontend/src/features/memories/components/memory-results-header.tsx`
- Modify: `frontend/src/features/memories/components/real-memories-view.tsx` (results header)
- Modify: `frontend/src/routes/_authenticated/memories.tsx` (results header and body)
- Modify: `frontend/src/features/memory-graph/components/memory-graph-explorer.tsx:1-60`
- Create: `frontend/src/features/memories/__tests__/memory-results-header.test.tsx`
- Modify: `frontend/src/features/memory-graph/__tests__/memory-graph.test.tsx`

**Interfaces:**
- Consumes: the advanced-only populated rule (Task 23) and `text-success-text` (Task 13).
- Produces: `MemoryResultsHeader` (Contracts).

**Implementer:** dr-superpowers:impl-sonnet-high
**Evaluation:** files 2 - spec 0 - coupling 0 - risk 1 = 3

- [ ] **Step 1: Write the failing tests**

Create `frontend/src/features/memories/__tests__/memory-results-header.test.tsx`:

```tsx
import { render, screen } from "@testing-library/react"
import { describe, expect, it } from "vitest"
import { useDetailLevel } from "@/components/darkmem"
import { MemoryResultsHeader } from "../components/memory-results-header"

describe("MemoryResultsHeader", () => {
  it("names the scope and the count in both modes", () => {
    useDetailLevel.setState({ level: "simple" })
    render(<MemoryResultsHeader scopeLabel="darkmem" shown={3} total={10} />)
    expect(screen.getByText("Results — project: darkmem")).toBeInTheDocument()
    expect(screen.getByText("3 of 10 shown")).toBeInTheDocument()
    expect(screen.queryByText("populated")).toBeNull()
  })

  it("says populated in Advanced and empty in both", () => {
    useDetailLevel.setState({ level: "advanced" })
    const { rerender } = render(
      <MemoryResultsHeader scopeLabel="all projects" shown={3} total={10} />,
    )
    expect(screen.getByText("populated")).toBeInTheDocument()
    useDetailLevel.setState({ level: "simple" })
    rerender(<MemoryResultsHeader scopeLabel="all projects" shown={0} total={0} />)
    expect(screen.getByText("empty")).toBeInTheDocument()
  })
})
```

In `frontend/src/features/memory-graph/__tests__/memory-graph.test.tsx`, add `import { AppPageHeader } from "@/components/app-chrome"` and append:

```tsx
  it("publishes the page chrome the real page does", () => {
    render(
      <>
        <MemoryGraphExplorer />
        <AppPageHeader />
      </>,
    )
    expect(screen.getByRole("heading", { name: "Memory Graph" })).toBeInTheDocument()
  })
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `npx vitest run src/features/memories/__tests__/memory-results-header.test.tsx src/features/memory-graph`
Expected: FAIL — `../components/memory-results-header` missing; no "Memory Graph" heading.

- [ ] **Step 3: The shared results header**

Create `frontend/src/features/memories/components/memory-results-header.tsx`:

```tsx
import { cn } from "darkraise-ui/lib"
import { useDetailLevel } from "@/components/darkmem"

/** The results card's header, shared by the real Memories view and the demo
 *  page so the two cannot drift apart. "populated" is Advanced-only; "empty"
 *  is shown in both modes. */
export function MemoryResultsHeader({
  scopeLabel,
  shown,
  total,
}: {
  scopeLabel: string
  shown: number
  total: number
}) {
  const advanced = useDetailLevel((s) => s.level) === "advanced"
  return (
    <div
      data-testid="memory-results-header"
      className="border-border bg-muted/30 flex flex-wrap items-center gap-2.5 border-b px-4 py-2.5"
    >
      <span className="text-sm font-semibold">Results — project: {scopeLabel}</span>
      {(shown === 0 || advanced) && (
        <span
          className={cn(
            "font-mono text-sm",
            shown > 0 ? "text-success-text" : "text-muted-foreground",
          )}
        >
          {shown > 0 ? "populated" : "empty"}
        </span>
      )}
      <span className="text-muted-foreground ml-auto font-mono text-sm">
        {shown} of {total} shown
      </span>
    </div>
  )
}
```

In `frontend/src/features/memories/components/real-memories-view.tsx`, import it and replace the whole header `<div className="border-border bg-muted/30 …">…</div>` inside the results card with:

```tsx
        <MemoryResultsHeader scopeLabel={scopeLabel} shown={rows.length} total={total} />
```

In `frontend/src/routes/_authenticated/memories.tsx`, import it, replace the demo page's header `<div className="border-border bg-muted/30 …">…</div>` with:

```tsx
          <MemoryResultsHeader
            scopeLabel={scopeLabel}
            shown={shownCount}
            total={matchCount}
          />
```

and change the card body `<div className="p-4">` to `<div className="space-y-3 p-4">`, the real view's body spacing. Remove the `advanced` variable Task 23 added to either file if nothing else reads it.

- [ ] **Step 4: Demo Memory Graph chrome**

In `frontend/src/features/memory-graph/components/memory-graph-explorer.tsx`, add `import { useSetPageChrome } from "@/components/app-chrome"` and, as the first lines of `MemoryGraphExplorer`:

```tsx
  useSetPageChrome({
    icon: Waypoints,
    title: "Memory Graph",
    description: "Entities and topics from your memories, for browsing only.",
  })
```

(`Waypoints` is already imported.)

- [ ] **Step 5: Run tests to verify they pass**

Run: `npx vitest run src/features/memories src/features/memory-graph && npm run typecheck`
Expected: PASS; typecheck exit 0.
Run: `E2E_API_TARGET=http://127.0.0.1:9 timeout 900 npx playwright test --project=demo-fixture tests/honesty tests/demo-makes-no-api-calls.spec.ts`
Expected: every test passes.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/features/memories frontend/src/features/memory-graph frontend/src/routes/_authenticated/memories.tsx
git commit -m "fix(demo): align demo memory rows and graph chrome" -m "Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

### Task 25: Final verification

Spec "Verification". Runs every check the spec names on the finished branch: the unit suite, typecheck and build; the honesty and demo specs; axe in both themes with 0 critical findings and 0 `color-contrast` findings on darkmem-owned elements on every audited route (library-owned darkraise-ui colouring is listed as a named exception — Assumptions), in real mode on a disposable stack and in demo; screenshots at 390px and 1440px with no clipped header, tab bar or panel; then the gate. This task fixes nothing: a failure is recorded against the task that owns it and handed back as fix work.

**Files:**
- Create (scratch, not committed): `<scratchpad>/axe-audit.cjs`, `<scratchpad>/audit/` (screenshots and JSON results)

**Interfaces:**
- Consumes: every earlier task.
- Produces: nothing committed.

**Implementer:** dr-superpowers:impl-sonnet-high
**Evaluation:** files 1 - spec 1 - coupling 1 - risk 0 = 3

- [ ] **Step 1: Unit suite, typecheck, build**

Run (from `frontend/`): `npm test && npm run typecheck && npm run build`
Expected: all green. `rg -n 'text-\[(8|9|10|11)px\]' src` and `rg -n --pcre2 '(?<![-\w])text-(primary|success|warning|info)(?![-\w])' src --glob '!src/__tests__/text-color-tokens.test.ts'` print nothing.

- [ ] **Step 2: Demo and honesty specs**

Run: `E2E_API_TARGET=http://127.0.0.1:9 timeout 900 npx playwright test --project=demo-fixture tests/demo-makes-no-api-calls.spec.ts tests/honesty`
Expected: every test passes (31 demo routes, three honesty specs).

- [ ] **Step 3: Write the audit script**

Write `<scratchpad>/axe-audit.cjs` (`<scratchpad>` is the session's scratchpad directory; nothing here is committed):

```js
// Usage (from frontend/): AUDIT_OUT=<dir> node <scratchpad>/axe-audit.cjs <baseURL> <label> [password]
const { join } = require("node:path")
const { mkdirSync, writeFileSync } = require("node:fs")

const fromFrontend = (m) => require.resolve(m, { paths: [process.cwd()] })
const { chromium } = require(fromFrontend("@playwright/test"))
const AXE = fromFrontend("axe-core/axe.min.js")

const [base, label, password] = process.argv.slice(2)
const OUT = process.env.AUDIT_OUT
mkdirSync(OUT, { recursive: true })

const ROUTES = [
  "/login",
  "/",
  "/memories",
  "/memory-graph",
  "/projects",
  "/documents",
  "/notes",
  "/knowledge/facts",
  "/knowledge/articles",
  "/knowledge/topics",
  "/knowledge/review",
  "/code/repositories",
  "/code/graph",
  "/code/wiki",
  "/chat",
  "/jobs",
  "/usage",
  "/activity?tab=pipeline",
  "/activity?tab=checkpoints",
  "/settings?tab=flags",
  "/settings?tab=llm",
  "/settings?tab=appearance",
]

async function audit(page, results, { mode, width, route }) {
  await page.goto(base + route)
  await page.waitForTimeout(1500)
  const applied = await page.evaluate(() => document.documentElement.dataset.mode)
  const name = `${label}-${mode}-${width}${route.replace(/[/?=&]/g, "_")}.png`
  await page.screenshot({ path: join(OUT, name) })
  await page.addScriptTag({ path: AXE })
  // A contrast node inside a darkraise-ui element that carries no darkmem
  // text utility is the library's own colouring (Assumptions): reported by
  // selector as an exception, not counted against darkmem.
  const violations = await page.evaluate(async () => {
    const isLibrary = (html) =>
      /class="[^"]*\bdr-/.test(html) && !/\btext-[a-z]+-text\b/.test(html)
    return (await window.axe.run(document, { resultTypes: ["violations"] })).violations.map((v) => {
      const library = v.id === "color-contrast" ? v.nodes.filter((n) => isLibrary(n.html)) : []
      return {
        id: v.id,
        impact: v.impact,
        nodes: v.nodes.length - library.length,
        library: library.map((n) => n.target.join(" ")),
        sample: v.nodes.slice(0, 3).map((n) => n.target.join(" ")),
      }
    })
  })
  const overflow = await page.evaluate(
    () => document.documentElement.scrollWidth > window.innerWidth,
  )
  results.push({ label, mode, applied, width, route, screenshot: name, overflow, violations })
}

;(async () => {
  const browser = await chromium.launch()
  const results = []
  for (const mode of ["light", "dark"]) {
    for (const width of [390, 1440]) {
      const context = await browser.newContext({ viewport: { width, height: 900 } })
      await context.addInitScript((m) => {
        try {
          window.localStorage.setItem("mode", m)
        } catch {}
      }, mode)
      const page = await context.newPage()
      for (const route of ROUTES) {
        await audit(page, results, { mode, width, route })
        if (route === "/login" && password) {
          await page.getByLabel("Password").fill(password)
          await page.getByRole("button", { name: /sign in/i }).click()
          await page.waitForURL((url) => !url.pathname.startsWith("/login"))
        }
      }
      await context.close()
    }
  }
  await browser.close()
  writeFileSync(join(OUT, `${label}.json`), JSON.stringify(results, null, 2))
  const failing = results.filter(
    (r) =>
      r.applied !== r.mode ||
      r.overflow ||
      r.violations.some(
        (v) => (v.id === "color-contrast" && v.nodes > 0) || v.impact === "critical",
      ),
  )
  const libraryExceptions = [
    ...new Set(results.flatMap((r) => r.violations.flatMap((v) => v.library))),
  ]
  console.log(`${label}: library-owned contrast exceptions: ${libraryExceptions.length}`)
  for (const selector of libraryExceptions) console.log(`  library: ${selector}`)
  console.log(`${label}: ${results.length} page loads, ${failing.length} failing`)
  for (const r of failing) console.log(JSON.stringify(r))
  process.exit(failing.length ? 1 : 0)
})()
```

- [ ] **Step 4: Audit demo mode**

Start a demo dev server as a tracked background process and record its PID:
`cd frontend && VITE_DEMO=1 npx vite --port 3641 --strictPort` (background).
Run: `cd frontend && AUDIT_OUT=<scratchpad>/audit timeout 1200 node <scratchpad>/axe-audit.cjs http://localhost:3641 demo`
Expected: `demo: 88 page loads, 0 failing`. Stop the vite process (`pkill -P <pid>; kill <pid>`).

A line with `"applied"` different from `"mode"` means the stored mode did not reach the theme; switch the mode once through the header's theme switcher in a headed check and record the storage key it writes, then re-run.

- [ ] **Step 5: Audit real mode on a disposable stack**

Never on `:8000`. Start, as tracked background processes with their PIDs recorded:
- `cd backend && python -m scripts.e2e.stack --keep-running --port 8323 --password "$AUDIT_PW" --seed-facts` (with `AUDIT_PW` a fresh random string);
- `cd frontend && E2E_API_TARGET=http://127.0.0.1:8323 npx vite --port 3640 --strictPort`.

Run: `cd frontend && AUDIT_OUT=<scratchpad>/audit timeout 1200 node <scratchpad>/axe-audit.cjs http://localhost:3640 real "$AUDIT_PW"`
Expected: `real: 88 page loads, 0 failing`. Stop vite, then the stack (Ctrl-C equivalent: `kill -INT <stack pid>`, which runs its teardown), and confirm with `ss -ltnp | rg ':(8323|3640|3641)\b'` that nothing still listens.

- [ ] **Step 6: Read the screenshots**

Open every `real-*-390_*.png` and `demo-*-390_*.png`, and the 1440px shots of `/settings`, `/activity`, `/code/graph`, `/chat` and `/memory-graph`, in both modes. For each, confirm: the header shows icon and title without overlap and (below md) one "View options" button; the Settings and Activity tab strips show their first and last tab reachable with an edge fade rather than a clipped tab; no panel runs off the right edge (the Code Graph panes stack at 390px; the chat thread header shows "Conversations" and "New"); the Activity pipeline stepper runs vertically at 390px; the login card follows the mode. Record each failing screenshot with the task that owns the surface.

- [ ] **Step 7: The gate**

Run (from the worktree root): `timeout 3600 ./scripts/gate.sh`
Expected: exit 0. Exit 143 is a SIGTERM from the host's OOM guard, not a failure: check `free -h` and re-run the red leg alone. Then run the full Playwright leg alone: `cd backend && timeout 3600 python scripts/e2e/run_playwright_e2e.py`. Expected: exit 0.

- [ ] **Step 8: Report**

Report the four audit totals, the library-owned contrast exceptions by selector, the gate and Playwright exit codes, and every failure from Steps 4-7 with its screenshot or rule id and owning task. Confirm no process started here is still running. Do not commit anything from this task.

