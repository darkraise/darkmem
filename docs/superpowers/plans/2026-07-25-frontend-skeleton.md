# darkmem Frontend Skeleton — build roadmap

**Status:** roadmap, dated 2026-07-25. Branch `feat/frontend-skeleton`.
Companion to the design-system artifact (`docs/design/mockups/design-system.html`)
and the reshaped design corpus (docs 13/14 + docs/design/mockups fragments S01–S33).

## Goal

Turn `frontend/` into a **comprehensive, fully-interactive skeleton** of the
reshaped darkmem UI — every screen present, navigable, and interactive over
**mock data** (runs standalone, no backend) — that becomes the frontend the
implementation phase fills in with real data/logic. Faithful to darkraise-ui and
the design system.

## Approach — reuse the toolchain, rebuild the app surface

A literal from-scratch scaffold would re-derive working boilerplate (Vite 8 +
Tailwind v4 + TanStack Router/Query/Form + darkraise-ui@3.1.2 + the exact
`theme.config.ts` + `theme-persistence` + `router-adapter` + providers) and
discard the existing `src/demo/` mock store and mature feature patterns. Instead:

- **Keep** the build toolchain and the provider stack (`app-providers.tsx`,
  `__root.tsx`, `theme.config.ts`, `globals.css`, `vite.config.ts`, tsconfig,
  eslint, vitest, Storybook) — this *is* the correct darkraise-ui setup.
- **Rebuild the app surface**: routes, features, and shell reshaped to docs 13/14,
  everything wired to a **mock-data layer** (an extension of `src/demo/`) so the
  app runs with no backend.
- **Standalone mock mode**: a build-time flag (e.g. `VITE_DEMO=1`, default on for
  this skeleton) makes auth a no-op and points the `hooks/api/*` surface at the
  demo store instead of `fetch`. The real API paths stay in the tree for the
  implementation phase to switch back on.

Net end-state is the same as "a brand-new app swapped in" — a fresh, comprehensive
skeleton — without throwing away the parts that already work. (If a literal
from-scratch scaffold is still preferred, this roadmap's IA / screen inventory /
waves carry over unchanged.)

## Reshaped information architecture (doc 13 §3)

Three nav groups, eight destinations, plus the two auth screens; a switchable
shell (Sidebar / TopNav / Stacked) and the chrome controls (project switcher,
context chip, theme switcher, **detail-level toggle**, command palette).

| Group | Destination | Route | Sub-surfaces |
|---|---|---|---|
| Workspace | Dashboard | `/` | contribution calendar, stat tiles, live feed |
| Workspace | Memories | `/memories` | search + list, why-retrieved trace, create/edit, detail |
| Workspace | Knowledge | `/knowledge` | Facts, Articles, Topics, Review (+ Hygiene) tabs |
| Workspace | Chat | `/chat` | thread list, messages, retrieval-context panel |
| Explore | Code | `/code` | Repositories, Code Graph, Wiki tabs |
| Explore | Memory Graph | `/memory-graph` | force/tree/circles graph |
| Operate | Activity | `/activity` | pipeline stepper, feed, triage, jobs, staged monitors, dream digest, day drill, **session checkpoints** |
| Operate | Settings | `/settings` | Flags, LLM, Jobs, Security, Maintenance, Distribution tabs |
| (guest) | Login / Setup | `/login`, `/setup` | login card, setup wizard |

## Screen inventory (maps to mockups S01–S33)

- **Dashboard** — S01
- **Memories** — search/list S02, why-retrieved trace S03, create/edit S04, detail S05
- **Knowledge** — Facts S06, Fact detail S07, Articles S08, Article detail S09, Topics S10, Review S11, Hygiene S12
- **Chat** — S13
- **Code** — Repositories S14, Code Graph S15, Wiki S16
- **Memory Graph** — S17
- **Activity** — stepper S18, feed S19, triage S20, jobs S21, staged monitors S22, dream digest S23, day drill S24, session checkpoints S33
- **Settings** — Flags S25, LLM S26, Jobs S27, Security S28, Maintenance S29, Distribution S30
- **Auth** — Login S31, Setup wizard S32
- **Cross-cutting** — the detail-level toggle (Simple/Advanced) honored on every advanced surface; theme + layout switchers in chrome

## Mock-data layer

Extend `src/demo/` from four entities to the full domain: memories, entities/relations,
facts (`knowledge_triples`) + `fact_sources` + verification ladder, articles +
citations, topics/communities, memory-relations, events (for calendar/timeline),
repos + code graph + wiki, jobs + config/flags, pipeline runs + failures,
review/hygiene queues, dream cycles + digest, distribution/inject records,
session checkpoints. Typed in `demo/types.ts`; deterministic generators in
`demo/generate.ts`; served through demo-aware `hooks/api/*` (or `useVault`/`useReview`/
`useEvents`/`useActivity`/`useDistribution` additions) behind the demo flag.

## Build waves

Each wave ends green: `npm run typecheck` (= `tsc -b`; bare `tsc` is a no-op here)
+ `npm run build` + a dev-run smoke check.

- **Wave 0 — foundation.** Demo/standalone mode + mock auth; extend mock-data types
  + fixtures; reshaped nav/IA + shell; chrome (detail toggle, switchers, palette);
  shared darkmem UI as components (verification badge, layer chip, why-retrieved
  trace, exclusion strip, honesty states). Prove with the Dashboard.
- **Wave 1 — Workspace.** Memories (search/trace/create/detail).
- **Wave 2 — Knowledge vault.** Facts, Fact detail, Articles, Article detail, Topics,
  Review, Hygiene.
- **Wave 3 — Explore.** Code (Repos/Graph/Wiki), Memory Graph, Chat.
- **Wave 4 — Activity.** Stepper, feed, triage, jobs, staged monitors, dream digest,
  day drill, session checkpoints.
- **Wave 5 — Settings + Auth.** Flags, LLM, Jobs, Security, Maintenance, Distribution;
  Login, Setup wizard.

## Verification & guardrails

- Type gate is `tsc -b` / `npm run build` — the bare `tsc --noEmit` is a no-op
  under this repo's project-reference tsconfig.
- Keep the real API layer intact behind the demo flag so the implementation phase
  can wire real data without re-architecting.
- Faithful to the design system: real `dr-*` components + tokens; darkmem patterns
  from `design-system.html`; honesty invariants (invariant 14) never hidden.

## Non-goals (this skeleton)

Real backend calls, real auth, real pipeline/LLM execution, persistence beyond the
in-memory demo store. Those are the implementation phase.
