# UI review remediation — design

Date: 2026-09-18. Status: approved by the owner in chat, same day.

Source: the 2026-09-18 UI/UX review (31 findings), re-verified against a
real-mode disposable stack. Findings that reproduced only in demo mode are
marked *(demo)*. Owner decisions taken before this spec:

1. The header `ProjectSwitcher` is the only project scope (doc 13 §3 stands).
2. Plain-language rewrite; implementation notes move behind the existing
   Simple/Advanced switch; `advanced` stays the default (feature-epics F9).
3. The login page follows the app theme.
4. Fix the real UI first and the demo defects too.

## Constraints that bind every workstream

- **Invariant 14** (`tests/honesty/labels-always-render.spec.ts`): verification
  badges, layer labels (`L0 · memory`, `L2 · fact`, …), superseded/stale labels
  and exclusion counts render in both detail modes. Nothing here hides them.
- **Rulings 3 and 4** (`components/app-chrome/context-chip.tsx`): the context
  chip stays visually distinct (dashed, italic when undeclared) and reads
  literally "not declared".
- **darkraise-ui first** (CLAUDE.md): restyle library components, never
  re-implement them.
- **Accent is user-configurable** (Appearance tab): no fix may pin `--primary`
  to a fixed colour.
- **Demo makes no API calls** (`tests/demo-makes-no-api-calls.spec.ts`).

## A. Demo integrity

- Guard with `enabled: !DEMO` (or the hook's existing `LIVE` constant): 
  `useClassificationAreas` (`hooks/api/use-config-api.ts`), the api-keys read
  (Security tab), the jobs read the Maintenance tab issues, and both
  auto-research reads (Research tab). Each currently 401s and the global
  handler redirects the whole demo to `/login`.
- Extend `DEMO_ROUTES` in `tests/demo-makes-no-api-calls.spec.ts` with every
  Settings tab (`/settings?tab=<value>` for each `TAB_VALUES` entry) plus
  `/usage`, `/projects`, `/jobs`, `/chat`, `/knowledge/review`,
  `/knowledge/topics`, `/code/wiki`, `/memory-graph`.
- *(demo)* Demo fixtures: a project catalogue (so Projects, Documents and the
  switcher are populated), a usage overview (Usage currently renders its
  failed-read state because every query is disabled), and the Jobs list
  brought to the 24 registered jobs.

## B. One project scope

- `stores/project-store.ts`: the default scope becomes `ALL_PROJECTS`. A
  persisted scope naming a project absent from `GET /projects` resolves to
  `ALL_PROJECTS`, and the switcher says "Saved project not found — showing all".
- `ProjectSwitcher` offers "All projects" first.
- Remove page-level project controls; each page reads the store:
  Memories (free-text "project (blank = all)"), Facts (select), Review
  (free-text), Articles (select), Memory Graph (select), Documents (the select
  added in 88a961c6), and the Chat thread header's second project chip.
  The results headers keep naming the scope ("Results — project: darkmem").
- `/documents` under `ALL_PROJECTS` renders a chooser: "Documents open one
  project at a time", one button per project holding documents; a click sets
  the store. The `?project=` search param added in 88a961c6 is removed; the
  store is the source of truth.
- Code pages (Repositories, Code Graph, Code Wiki) render the switcher
  disabled with the tooltip "Code is scoped by repository, not by project",
  and drop the four inline disclaimers ("NOT APPLIED HERE" chip, "SCOPE:
  REPOSITORY, NOT PROJECT", "gated by repository, not project" in two page
  descriptions, "repo-scoped — not the project switcher").
- The context chip gains a help tooltip explaining what a session context
  does. Wording and dashed style unchanged.

## C. Header and responsive layout

- `app-page-header.tsx`: below `md`, render icon + title (truncated), and move
  ProjectSwitcher, ContextChip, DetailLevelToggle, theme switcher and
  notifications into one overflow `Popover` (darkraise-ui). Page `actions`
  render icon-only below `md` (each keeps an `aria-label`).
- Desktop: page descriptions are shortened to fit one line at 1440px; the
  header shows the full description in a tooltip when truncated.
- Tab bars with more tabs than fit (Settings: 10, Activity: 8): horizontal
  scroll with edge fade and the active tab scrolled into view; no clipped
  first/last tab. Use darkraise-ui `tabs`; restyle, do not replace.
- Activity → Pipeline row: below `md` the quoted content stacks above the
  stepper and the stepper renders vertically. No overlap with the timestamp.
- Code Graph below `lg`: explorer, canvas and inspector stack; the Blast
  Radius control lives in the inspector, never over the canvas.
- Chat: the conversation list panel gets a minimum width at which its header
  button and search placeholder are not clipped.

## D. Accessibility

- **Contrast.** In light mode define `--primary-text` and `--success-text` as
  `color-mix(in oklch, var(--primary) 70%, black)` (same for success), with
  dark mode aliasing them to the base tokens. Expose Tailwind utilities
  `text-primary-text` / `text-success-text` and use them wherever the primary
  or success colour is used as *text* in darkmem code (badges, "populated",
  mono counts, links). Buttons keep the library's own foreground pairing.
  Acceptance: axe `color-contrast` reports 0 in both themes on every route.
- **Minimum text size 12px.** Replace every `text-[10px]` (147) and
  `text-[11px]` (18) in `frontend/src` with `text-xs`; fix any layout that
  breaks. A vitest source scan fails the build on `text-[8-11px]`.
- **Notes editor (BlockNote).** Editor gets `aria-label="Page content"`;
  checklist inputs get an `aria-label` ("Mark as done" / "Mark as not done");
  the toggle button gets "Expand" / "Collapse". Applied through BlockNote's
  `domAttributes` and a post-render effect, recorded as a library gap.
- **Graph canvases.** Remove the nested-interactive pattern on the Memory Graph
  SVG and the Code Graph container (the container is not focusable when it
  holds focusable nodes).
- **Login.** Visible "Password" label with ≥ 4.5:1 contrast; button text
  contrast ≥ 4.5:1.

## E. Visual consistency

- **Login** (`features/auth/components/login-card.tsx`, `login-form.tsx`):
  theme tokens only (no hex), app `BrandMark`, follows light/dark, particle
  background tinted from `--primary`.
- **Sidebar:** active item = `bg-primary/10` + `text-primary-text`, no border;
  sidebar search box without the permanent accent border; the dark-mode default
  surface colour in `theme.config.ts` becomes neutral so sidebar and content
  share a hue.
- **Articles** nav and page icon: `Newspaper` (Documents keeps `FileText`).
- **Graph pages:** Code Graph panel headings match Memory Graph's (sentence
  case, sans); toolbar captions ≥ 12px; the counter reads "18 nodes · 18 edges"
  and never clips. Memory Graph labels: a label that would overlap an
  already-placed label is hidden and shown on hover/focus of its node.
- **Articles list:** fixed-width badge column so titles align.
- **Dashboard:** the contribution calendar fills the card width (cell size
  derived from width); stat cards compact.
- **Notes:** title and editor share one left edge; editor inherits the app
  font; checkbox `accent-color: var(--primary)`; toggle triangle, code block
  and callout use `--muted-foreground`, `--muted` and `--info` tokens.
- **Jobs:** description expands on click; Run is an outline button; a failed
  last run shows the word "failed" beside its icon.
- **Review:** Review/Hygiene switch is a darkraise-ui `SegmentGroup`; the stray
  `/knowledge · review` label is removed.

## F. Copy

Advanced-only (rendered when `useDetailLevel() === "advanced"`): task ids
("activated by T2.30"), raw config keys and snake_case identifiers
(`by_review_state`, `review_state=open`, `w_conf`), algorithm names
("Leiden"), the per-row "ratify/reject are REST/UI … never exposed over MCP"
note (shown once in the page's help tooltip in both modes instead), and the
"populated" data-state badge ("empty" and "failed" render in both modes).

Both modes:
- Timestamps render through `lib/format.ts` (relative, absolute on hover),
  never raw ISO strings.
- Kind lists read as prose ("code and memory"), not `[code, memory]`.
- Long explanatory paragraphs (Activity → Pipeline, Settings → Flags/LLM) move
  into the page or section help tooltip.
- Stale copy corrected: `features/settings/components/llm-tab.tsx` ("Seven
  purposes … seeded-inert synthesis" → eight live purposes), the Review page's
  "article_synthesis is still a placeholder job" (it shipped).

## G. Dead code

Delete `src/lib/settings-tab.ts` and `src/lib/__tests__/settings-tab.test.ts`;
update `settings-distribution.real.test.tsx`, its only other importer.

## H. Demo-only visuals

Demo Memory Graph page gets its `PageChrome`; the demo chat thread list stops
clipping "+ New"; demo memory rows match the real row layout.

## Verification

- Unit tests for every behaviour change (scope resolution and fallback, demo
  guards, Advanced-only rendering, the text-size scan, the tab-bar scroll).
- `tests/honesty/labels-always-render.spec.ts` and the extended demo spec
  green.
- Final pass on a real-mode disposable stack and on demo: axe in both themes
  (0 `color-contrast`, 0 critical), screenshots at 390px and 1440px with no
  clipped header, tab bar or panel.
- `./scripts/gate.sh`, then redeploy per CLAUDE.md.

## Out of scope

Backend changes; the parser/serialiser document issues; changing which labels
invariant 14 protects; a redesign of page information architecture beyond the
scope model.
