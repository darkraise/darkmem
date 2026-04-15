"""One-off emitter for classification top-up batch-021 — contrastive_decision_architecture mode, frontend UI slice.

Writes 100 rows (50 pairs) to data/v2/classification/batch_021.tmp.jsonl with ids class-02001..02100.
"""
from __future__ import annotations
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "classification" / "batch_021.tmp.jsonl"
ID_OFFSET = 2000
PAIR_OFFSET = 750

# (decision_text, decision_domain, architecture_text, architecture_domain)
PAIRS: list[tuple[str, str, str, str]] = [
    # 1. framework choice — Next.js App Router -> Astro
    (
        "Switched from Next.js App Router to Astro for the marketing site after hydration costs pushed Largest Contentful Paint past 3.4 seconds on mid-tier Android devices.",
        "ai_coding",
        "Marketing pages ship as static Astro 4 islands with React islands hydrated only for the quote calculator and the search dialog, sharing a single shadcn/ui theme token bundle.",
        "ai_coding",
    ),
    # 2. framework choice — CRA -> Vite
    (
        "Migrated the admin dashboard from Create React App to Vite 5 after webpack cold starts crossed 70 seconds on the design team's MacBook Airs.",
        "ai_coding",
        "The admin dashboard builds with Vite 5 using SWC for transforms, esbuild for prebundling, and a vendor manualChunks split that keeps the recharts bundle outside the first-load JS.",
        "ai_coding",
    ),
    # 3. rendering strategy — SSR -> ISR
    (
        "Moved product detail pages from on-demand SSR to Incremental Static Regeneration with a 60-second revalidate after origin CPU pegged during price update storms.",
        "ai_coding",
        "Product pages render via Next.js ISR with revalidate=60, on-demand revalidation triggered by a Kafka consumer on pricing events, and a stale-while-revalidate CDN policy in front.",
        "ai_coding",
    ),
    # 4. rendering — SSG for docs
    (
        "Chose full SSG over SSR for the developer documentation portal because the content is Git-sourced MDX and there is no per-user state to render.",
        "ai_coding",
        "Docs are pre-rendered by Astro at build time from MDX sources in the monorepo, deployed as immutable static files to Cloudflare Pages with a search index generated at build.",
        "ai_coding",
    ),
    # 5. state management — Redux -> Zustand
    (
        "Replaced Redux Toolkit with Zustand in the trading console after boilerplate for every new slice slowed feature delivery and discouraged typed selectors.",
        "ai_coding",
        "Trading console state is split into five Zustand stores (orders, portfolio, market data, UI, session) each with its own persist middleware and immer middleware for nested updates.",
        "ai_coding",
    ),
    # 6. state management — context -> Jotai
    (
        "Adopted Jotai over a tree of React Contexts for the form-heavy onboarding flow after nested providers forced full-tree rerenders on every keystroke.",
        "ai_coding",
        "Onboarding form state lives in Jotai atoms, grouped by step, with atomFamily used for per-field validation and a selectAtom derived atom feeding the progress indicator.",
        "ai_coding",
    ),
    # 7. server state — SWR -> TanStack Query
    (
        "Switched from SWR to TanStack Query v5 because the app needed mutation lifecycle hooks and query invalidation graphs that SWR could not express declaratively.",
        "ai_coding",
        "Server state is managed by TanStack Query v5 with a global QueryClient configured for 30s stale time, exponential retry backoff, and an Axios wrapper that normalizes error shapes.",
        "ai_coding",
    ),
    # 8. routing — React Router -> TanStack Router
    (
        "Moved the darkraise-ui package from React Router v6 to TanStack Router to get end-to-end typed routes and file-based route generation.",
        "ai_coding",
        "The UI uses TanStack Router with file-based route generation, each route exposing loader, search params schema, and error boundary colocated, and a root route owning the auth guard.",
        "ai_coding",
    ),
    # 9. routing — hash -> history
    (
        "Dropped hash-based routing on the embedded analytics widget after customers complained deep links broke when pasted into Slack unfurls.",
        "ai_coding",
        "The embedded widget uses the History API with a configurable basename so host apps can mount it under /analytics while retaining shareable deep links with standard URLs.",
        "ai_coding",
    ),
    # 10. component library — MUI -> shadcn/ui
    (
        "Replaced MUI v5 with shadcn/ui after designers could not override the deeply nested Emotion styles without escape-hatch sx props everywhere.",
        "ai_coding",
        "The component system is a copy-in shadcn/ui library on top of Radix primitives, styled with Tailwind and CVA variants, published internally as @darkraise/ui with tree-shakable exports.",
        "ai_coding",
    ),
    # 11. component library — Chakra -> Mantine
    (
        "Chose Mantine v7 over Chakra v2 for the internal tools after needing polished data grid, date range picker, and rich text editor primitives out of the box.",
        "ai_coding",
        "Internal tools use Mantine v7 with the Mantine DataTable, Mantine Dates, and Tiptap integration, themed by a single createTheme call driven from a design-token JSON file.",
        "ai_coding",
    ),
    # 12. design tokens — ad hoc -> Style Dictionary
    (
        "Adopted Style Dictionary for design tokens after hex values drifted between Figma, iOS, and the web app and caused three brand-inconsistency bug reports in a month.",
        "ai_coding",
        "Design tokens are authored in a single tokens.json, transformed by Style Dictionary into CSS variables, Tailwind theme extensions, Swift enums, and Kotlin objects consumed across platforms.",
        "ai_coding",
    ),
    # 13. CSS architecture — Sass modules -> Tailwind
    (
        "Moved the marketing codebase from Sass modules to Tailwind v3 after dead-style audits showed 38% of shipped CSS was unused on mobile.",
        "ai_coding",
        "Styling uses Tailwind v3 with a design-token preset, tailwind-merge for class reconciliation, and PurgeCSS running against MDX and TSX sources for a final 18 KB CSS bundle.",
        "ai_coding",
    ),
    # 14. CSS architecture — styled-components -> vanilla-extract
    (
        "Switched from styled-components to vanilla-extract because runtime CSS-in-JS added 40 ms to hydration on the checkout route.",
        "ai_coding",
        "Styles compile at build time via vanilla-extract with static theme contracts, generating atomic CSS through Sprinkles and ship zero runtime JS for styling in the checkout bundle.",
        "ai_coding",
    ),
    # 15. forms — formik -> react-hook-form
    (
        "Replaced Formik with react-hook-form in the signup funnel after re-render storms on large field arrays caused dropped keystrokes on low-end Chromebooks.",
        "ai_coding",
        "Signup forms use react-hook-form with uncontrolled inputs, Zod resolvers for validation, and a FormProvider at each step so field-array rows rerender in isolation.",
        "ai_coding",
    ),
    # 16. forms — custom validators -> Zod
    (
        "Adopted Zod schemas shared across client and server after duplicate yup and Joi validators drifted and rejected valid submissions on the edge.",
        "ai_coding",
        "Form schemas are defined once in a shared @darkraise/schemas package using Zod, consumed by react-hook-form resolvers on the client and by Fastify route validation on the server.",
        "ai_coding",
    ),
    # 17. frontend auth — localStorage JWT -> httpOnly cookies
    (
        "Replaced localStorage JWT storage with httpOnly SameSite=Strict cookies after a dependency with a postinstall script exfiltrated tokens in a preview build.",
        "ai_coding",
        "The SPA authenticates against a same-origin /auth proxy that sets httpOnly Secure SameSite=Strict session cookies, with CSRF tokens issued per form and verified by the API gateway.",
        "ai_coding",
    ),
    # 18. frontend auth — custom -> Auth.js
    (
        "Adopted Auth.js (NextAuth v5) over a hand-rolled OIDC client because refresh-token rotation and multi-provider linking kept regressing under test.",
        "ai_coding",
        "Authentication in the Next.js app is managed by Auth.js v5 with the Prisma adapter, Keycloak and GitHub providers, and middleware gating every /app route on a valid session cookie.",
        "ai_coding",
    ),
    # 19. bundler — webpack -> Rspack
    (
        "Switched the legacy webpack 5 pipeline to Rspack after production builds consistently exceeded the nine-minute CI budget on large branches.",
        "ai_coding",
        "The build pipeline runs Rspack 1.0 with the webpack-compatible config, SWC loaders, persistent filesystem cache on the CI runner, and a module-federation remote for the plugin surface.",
        "ai_coding",
    ),
    # 20. bundler — Rollup for library
    (
        "Chose Rollup over Vite library mode for the published UI package because we needed multi-format output plus bundled .d.ts files with precise export maps.",
        "ai_coding",
        "The @darkraise/ui package is built by Rollup 4 emitting ESM and CJS bundles, dts-rollup-generated type bundles, and a package.json with fine-grained exports per component entry.",
        "ai_coding",
    ),
    # 21. test runner — Jest -> Vitest
    (
        "Replaced Jest with Vitest after ESM-only dependencies broke the transform pipeline and ts-jest startup took 11 seconds on a two-test file.",
        "ai_coding",
        "Unit tests run under Vitest 1.6 in happy-dom mode, parallelized with eight workers, sharing the Vite dev config so module resolution matches the production bundle exactly.",
        "ai_coding",
    ),
    # 22. E2E — Cypress -> Playwright
    (
        "Migrated E2E tests from Cypress to Playwright after flake on cross-origin iframes and a missing multi-tab model made auth-flow tests unreliable.",
        "ai_coding",
        "E2E suites run in Playwright with three projects (chromium, firefox, webkit), sharded across four CI runners, using a storageState fixture to skip login for non-auth scenarios.",
        "ai_coding",
    ),
    # 23. visual regression — manual -> Chromatic
    (
        "Adopted Chromatic for visual regression after three UI bugs shipped to production that a diff would have caught before review.",
        "ai_coding",
        "Storybook 8 stories are published to Chromatic on every PR, with baseline snapshots keyed on the main branch, TurboSnap enabled to skip unchanged components, and a required GitHub check.",
        "ai_coding",
    ),
    # 24. visual regression — Playwright screenshots
    (
        "Chose Playwright's toHaveScreenshot over a SaaS visual tool because we already ran Playwright in CI and did not want another vendor managing screenshot baselines.",
        "ai_coding",
        "Visual regression runs as a dedicated Playwright project with deterministic fonts, masked timestamps, and PNG baselines stored in Git LFS under tests/visual/__screenshots__.",
        "ai_coding",
    ),
    # 25. accessibility — ad hoc -> axe-core
    (
        "Adopted axe-core in CI after a customer audit flagged 14 WCAG 2.2 AA violations that had slipped through manual review for a year.",
        "ai_coding",
        "Accessibility checks run as a Playwright project invoking axe-core on every key page, failing CI on serious or critical impact rules and producing a HTML report published as a job artifact.",
        "ai_coding",
    ),
    # 26. accessibility — Storybook a11y addon
    (
        "Chose the Storybook addon-a11y to shift accessibility left after most issues originated at the component level rather than the page composition.",
        "ai_coding",
        "Every Storybook story runs the addon-a11y checks in the Storybook test-runner under axe, with a shared axe config that disables color-contrast on tokens-sourced swatches.",
        "ai_coding",
    ),
    # 27. i18n — i18next -> FormatJS
    (
        "Switched from i18next to FormatJS after translators complained about missing ICU plural and select support on the billing invoices page.",
        "ai_coding",
        "Localization uses FormatJS with ICU MessageFormat strings, messages extracted to JSON by formatjs extract, and language bundles loaded on demand with dynamic import() per locale.",
        "ai_coding",
    ),
    # 28. i18n — client-only -> server-rendered locale
    (
        "Moved locale resolution from the client to the edge after users hitting the German site briefly saw English content while the bundle loaded.",
        "ai_coding",
        "Locale is detected at a Cloudflare Worker by Accept-Language and a user cookie, injected into the HTML as a __LOCALE__ global, and consumed by React Intl providers during SSR hydration.",
        "ai_coding",
    ),
    # 29. feature flags — env vars -> LaunchDarkly
    (
        "Adopted LaunchDarkly over env-variable gates after the pricing experiment needed percentage rollouts and per-account targeting within a single deploy.",
        "ai_coding",
        "The SPA bootstraps LaunchDarkly on mount with user identity keyed on account_id, streams flag updates via SSE, and wraps gated UI in a FeatureFlag component that short-circuits render.",
        "ai_coding",
    ),
    # 30. feature flags — OpenFeature + flagd
    (
        "Chose OpenFeature with flagd for internal tool flags because data residency rules blocked sending user identifiers to a SaaS flag provider.",
        "ai_coding",
        "Internal web apps evaluate flags through the OpenFeature React SDK against a flagd sidecar at localhost:8013, with rule definitions synced from a Git repository and reloaded on change.",
        "ai_coding",
    ),
    # 31. analytics — GA4 -> PostHog
    (
        "Replaced Google Analytics 4 with self-hosted PostHog after EU privacy review required first-party telemetry and session replay without third-party cookies.",
        "ai_coding",
        "Client analytics call a self-hosted PostHog instance via a reverse-proxied /ingest path, with autocapture enabled, session replay sampled at 10%, and identify fired after login.",
        "ai_coding",
    ),
    # 32. analytics — Segment client-side
    (
        "Adopted Segment with server-side destinations after ad blockers dropped about 22% of client-side events on the marketing funnel.",
        "ai_coding",
        "Events are sent client-side to a same-origin /collect edge endpoint that forwards to Segment server-side, which fans out to Mixpanel, Braze, and a BigQuery destination.",
        "ai_coding",
    ),
    # 33. error boundary — global handler -> Sentry + React ErrorBoundary
    (
        "Adopted nested React Error Boundaries tied to Sentry after a single uncaught render error in the sidebar blanked the entire dashboard for five minutes.",
        "ai_coding",
        "The app wraps each top-level route and each async island in an ErrorBoundary that reports to Sentry with a scoped tag and renders a localized fallback UI with a retry button.",
        "ai_coding",
    ),
    # 34. crash reporting — Sentry replay
    (
        "Enabled Sentry Session Replay on error-only sampling after support could not reproduce intermittent drag-and-drop bugs reported by enterprise users.",
        "ai_coding",
        "The SPA configures Sentry browser SDK with replaysSessionSampleRate=0 and replaysOnErrorSampleRate=1, masking all text inputs and blocking screenshots on the compliance-flagged routes.",
        "ai_coding",
    ),
    # 35. suspense/streaming — SSR streaming
    (
        "Adopted React 19 streaming SSR with Suspense boundaries after the product page's server render blocked on a slow reviews call, delaying Time To First Byte by 900 ms.",
        "ai_coding",
        "Product pages stream through React 19 renderToPipeableStream with Suspense boundaries around reviews, recommendations, and inventory, each resolved independently from the backing service.",
        "ai_coding",
    ),
    # 36. suspense — route-level code split
    (
        "Chose route-level lazy() boundaries over component-level after bundle analysis showed admin-only views were loaded for every signed-in customer.",
        "ai_coding",
        "Every TanStack Router route component is imported via lazy() with a shared Suspense boundary showing a skeleton, and router-level preload runs on link hover for primary navigation.",
        "ai_coding",
    ),
    # 37. data fetching — REST -> GraphQL
    (
        "Moved the dashboard from REST to GraphQL with a single endpoint because the widgets page made 14 sequential calls that could not be parallelized cleanly.",
        "ai_coding",
        "The dashboard queries a federated GraphQL gateway through urql with Graphcache, persisted operation IDs, and a single websocket subscription channel for live widget updates.",
        "ai_coding",
    ),
    # 38. data fetching — tRPC
    (
        "Chose tRPC over a hand-written REST client for the internal admin app because the teams own both ends of the wire in the same TypeScript monorepo.",
        "ai_coding",
        "The admin app calls a tRPC v11 router over HTTP batch links, types shared from the backend package, and uses superjson transformers so Date and Decimal values round-trip unchanged.",
        "ai_coding",
    ),
    # 39. data fetching — React Server Components
    (
        "Adopted React Server Components in the Next.js app for the reporting surface after client-only data fetching left large hydration payloads on routes nobody interacted with.",
        "ai_coding",
        "Reporting pages render as Server Components that fetch from Postgres directly through a server-only data layer, with Client Components pushed to leaves like filters and chart legends.",
        "ai_coding",
    ),
    # 40. offline support — service worker
    (
        "Adopted Workbox-generated service workers after field technicians in low-connectivity warehouses lost form progress when the Wi-Fi dropped mid-shift.",
        "ai_coding",
        "The field-ops PWA uses a Workbox service worker with a StaleWhileRevalidate strategy for APIs, a CacheFirst strategy for shell assets, and a background sync queue for pending form POSTs.",
        "ai_coding",
    ),
    # 41. offline — IndexedDB
    (
        "Chose IndexedDB via Dexie over localStorage for the draft editor because quotas and write latency on localStorage broke autosave for documents over 1 MB.",
        "ai_coding",
        "Drafts are persisted to IndexedDB through Dexie 4 with a versioned schema, an autosave hook debounced at 400 ms, and a background reconciliation worker that diffs local drafts against the server.",
        "ai_coding",
    ),
    # 42. monorepo tooling — Nx
    (
        "Picked Nx for the frontend monorepo over Turborepo because the team needed generators, module-boundary lint rules, and a dependency graph visualizer on day one.",
        "ai_coding",
        "The frontend monorepo is organized with Nx 19, enforcing tag-based import boundaries between feature, ui, and data-access libs, with Nx Cloud remote cache shared across developers and CI.",
        "ai_coding",
    ),
    # 43. icons — icon font -> SVGR
    (
        "Replaced a 240 KB icon font with tree-shakable SVG React components via SVGR after the font blocked First Contentful Paint on slow 3G.",
        "ai_coding",
        "Icons are authored as SVG files, compiled by SVGR into typed React components with aria-hidden defaults, and imported per-icon so only referenced glyphs land in the route bundle.",
        "ai_coding",
    ),
    # 44. charts — D3 -> Recharts -> visx
    (
        "Chose visx over Recharts for the finance dashboard because dense time-series plots needed bespoke axes and Canvas fallback for 40k-point series.",
        "ai_coding",
        "Finance charts are composed from visx primitives on top of a shared scale provider, SVG for <5k points and a Canvas renderer above that threshold, with a d3-time axis shared between both paths.",
        "ai_coding",
    ),
    # 45. animations — Framer Motion
    (
        "Adopted Framer Motion over CSS keyframes for route transitions after designers needed shared-layout animations between the list and detail views.",
        "ai_coding",
        "Route transitions use Framer Motion's layout animations, with a LayoutGroup at the router outlet and AnimatePresence wrapping the route tree so exit animations run before unmount.",
        "ai_coding",
    ),
    # 46. drag and drop — react-dnd -> dnd-kit
    (
        "Replaced react-dnd with dnd-kit on the kanban board after keyboard-only users could not reorder cards and the HTML5 backend dropped on touch devices.",
        "ai_coding",
        "The kanban board uses dnd-kit with the sortable preset, keyboard and pointer sensors configured, a DragOverlay rendered outside the scrollable column, and accessible announcements on drop.",
        "ai_coding",
    ),
    # 47. virtualization — react-window -> TanStack Virtual
    (
        "Switched from react-window to TanStack Virtual on the audit log page because variable row heights and a sticky group header caused visible jumps on scroll.",
        "ai_coding",
        "The audit log uses TanStack Virtual's useVirtualizer with dynamic row measurement, overscan of 8, and a sticky group header rendered outside the virtualized range to avoid measurement drift.",
        "ai_coding",
    ),
    # 48. type checking — PropTypes -> TypeScript strict
    (
        "Turned on TypeScript strict mode across the SPA after three production incidents traced back to undefined prop access that PropTypes warnings did not catch in production builds.",
        "ai_coding",
        "The SPA compiles with tsconfig strict, noUncheckedIndexedAccess, exactOptionalPropertyTypes, and verbatimModuleSyntax, with a project-references graph splitting app, ui, and data-access layers.",
        "ai_coding",
    ),
    # 49. package manager — npm -> pnpm
    (
        "Switched from npm to pnpm for the frontend workspace after node_modules size on a fresh clone exceeded 2.1 GB and installs took over four minutes.",
        "ai_coding",
        "The workspace uses pnpm 9 with a content-addressable store, a locked packageManager field in root package.json, and a .npmrc enforcing public-hoist-pattern=[] to catch phantom deps.",
        "ai_coding",
    ),
    # 50. linting — ESLint flat config
    (
        "Adopted ESLint flat config with typescript-eslint v8 after the legacy .eslintrc chain across packages drifted and produced inconsistent rules per workspace.",
        "ai_coding",
        "Linting runs from a single eslint.config.mjs at the monorepo root with scoped overrides per package, typescript-eslint v8 type-aware rules, and a Prettier disabled-rules block to avoid conflicts.",
        "ai_coding",
    ),
]


def emit() -> int:
    assert len(PAIRS) == 50, f"expected 50 pairs, got {len(PAIRS)}"
    OUT.parent.mkdir(parents=True, exist_ok=True)
    written = 0
    with OUT.open("w", encoding="utf-8") as f:
        for i, (dec_text, dec_domain, arch_text, arch_domain) in enumerate(PAIRS, start=1):
            pair_id = f"cls-pair-{PAIR_OFFSET + i:05d}"
            dec_id = f"class-{ID_OFFSET + (2 * i - 1):05d}"
            arch_id = f"class-{ID_OFFSET + (2 * i):05d}"
            f.write(json.dumps({"id": dec_id, "domain": dec_domain, "text": dec_text, "memory_type": "decision", "pair_id": pair_id}, ensure_ascii=False) + "\n")
            f.write(json.dumps({"id": arch_id, "domain": arch_domain, "text": arch_text, "memory_type": "architecture", "pair_id": pair_id}, ensure_ascii=False) + "\n")
            written += 2
    return written


if __name__ == "__main__":
    n = emit()
    print(f"wrote {n} rows to {OUT}")
