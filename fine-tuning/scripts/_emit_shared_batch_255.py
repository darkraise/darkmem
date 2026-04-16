"""One-off emitter for shared-base batch-255 — technical domain (React ecosystem: React 18/19 concurrent features, Next.js 14/15, TanStack, state libraries, Radix, shadcn, Tailwind 4, testing stacks).

Writes 50 rows to data/v2/shared/batch_255.tmp.jsonl with ids shared-12701..12750.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "shared" / "batch_255.tmp.jsonl"
ID_OFFSET = 12700

# (text, memory_type, domain, noise, entities, relationships, qq, qk)
ENTRIES: list[tuple] = [
    # --- 1 ---
    ("Wrapped the filter-panel setState call in startTransition after React 18 profiler showed input lag; the urgent keystroke now paints first and the filtered list rebuilds in the background.", "decision", "technical", False,
     [("startTransition", "api"), ("React 18", "framework"), ("filter-panel", "project")],
     [("startTransition", "React 18", "DEPENDS_ON")],
     "which concurrent API did we adopt to stop the filter panel from blocking keystrokes in React 18",
     "start transition react 18 filter panel input lag urgent paint"),
    # --- 2 ---
    ("useTransition replaced a home-rolled debounce hook for the search box; the isPending flag drives the spinner and stale results no longer flash when the user types fast.", "decision", "technical", False,
     [("useTransition", "api"), ("isPending", "api"), ("debounce hook", "pattern")],
     [("useTransition", "debounce hook", "REPLACES")],
     "which React hook retired the custom debounce in the search box and what state does the spinner bind to",
     "use transition pending flag debounce search spinner stale result"),
    # --- 3 ---
    ("useDeferredValue wraps the chart data prop so the input slider stays responsive while the expensive d3 layout recomputes on a lower-priority pass.", "fact", "technical", False,
     [("useDeferredValue", "api"), ("d3", "library"), ("slider", "pattern")],
     [("useDeferredValue", "d3", "APPLIES_TO")],
     "how does the chart keep slider input snappy while d3 recomputes the layout in React",
     "use deferred value d3 chart slider responsive lower priority"),
    # --- 4 ---
    ("Suspense boundaries now wrap every route-level data fetch; a shared skeleton renders until the server stream resolves, and nested fallbacks prevent a single slow card from stalling the whole page.", "fact", "technical", False,
     [("Suspense", "api"), ("skeleton", "pattern"), ("route-level", "pattern")],
     [("Suspense", "skeleton", "USES")],
     "how did route-level data loading adopt Suspense to avoid one slow card stalling the page",
     "suspense boundary route skeleton nested fallback stream server"),
    # --- 5 ---
    ("Replaced the legacy context-based window-size listener with useSyncExternalStore; tearing during concurrent renders disappeared and SSR hydration no longer logs mismatched values.", "problem", "technical", False,
     [("useSyncExternalStore", "api"), ("context-based", "pattern"), ("SSR hydration", "pattern")],
     [("useSyncExternalStore", "context-based", "REPLACES")],
     "which React hook fixed the tearing and hydration mismatch from the old window-size listener",
     "sync external store context window size tear hydration ssr"),
    # --- 6 ---
    ("Migrated the dashboard to React Server Components on Next.js 15; database calls moved out of the client bundle and the initial payload dropped below 80 KB of JavaScript.", "milestone", "technical", False,
     [("React Server Components", "framework"), ("Next.js 15", "framework"), ("dashboard", "project")],
     [("React Server Components", "Next.js 15", "DEPLOYED_ON")],
     "which server-first architecture cut the dashboard client bundle and where is it hosted",
     "react server component next 15 dashboard bundle size client payload"),
    # --- 7 ---
    ("Server Actions handle every form submit now; the old /api/* POST routes were deleted along with the fetch wrapper, and progressive enhancement works without client JavaScript enabled.", "decision", "technical", False,
     [("Server Actions", "framework"), ("fetch wrapper", "pattern"), ("progressive enhancement", "concept")],
     [("Server Actions", "fetch wrapper", "REPLACES")],
     "which Next.js feature replaced the custom fetch wrapper for form submits and what did it unlock",
     "server action form submit api route progressive enhancement fetch"),
    # --- 8 ---
    ("The use() hook landed in React 19 and unlocked conditional promise reads inside components; a gnarly wrapper around useEffect plus useState for one-shot fetches got deleted outright.", "milestone", "technical", False,
     [("use()", "api"), ("React 19", "framework"), ("useEffect", "api"), ("useState", "api")],
     [("use()", "React 19", "DEPENDS_ON")],
     "which React 19 hook replaced the effect-plus-state wrapper for one-shot promise reads",
     "use hook react 19 promise effect state one shot fetch conditional"),
    # --- 9 ---
    ("React 19 shipped ref as prop; forwardRef wrappers around every leaf button and input were removed, and the typings collapsed to a plain ref?: Ref<HTMLInputElement>.", "fact", "technical", False,
     [("React 19", "framework"), ("forwardRef", "api"), ("ref as prop", "pattern")],
     [("ref as prop", "forwardRef", "REPLACES")],
     "which React 19 change let us drop forwardRef from every leaf component",
     "react 19 ref prop forward ref leaf button input typings"),
    # --- 10. noise ---
    ("The basil on the kitchen windowsill is leggy again and someone keeps topping up the pot with espresso grounds that the cat then rolls in.", "fact", "noise", True, [], [], None, None),
    # --- 11 ---
    ("Enabled the React Compiler on the marketing site; manual useMemo and useCallback calls got stripped and the Lighthouse interaction score climbed seven points without a code rewrite.", "milestone", "technical", False,
     [("React Compiler", "tool"), ("useMemo", "api"), ("useCallback", "api"), ("Lighthouse", "tool")],
     [("React Compiler", "useMemo", "REPLACES")],
     "which React team compiler retired manual memoisation and what score moved on Lighthouse",
     "react compiler use memo callback lighthouse marketing interaction"),
    # --- 12 ---
    ("Next.js 14 App Router replaced the pages/ directory; layouts now colocate with routes and loading.tsx files provide per-segment Suspense boundaries without one-off wrappers.", "architecture", "technical", False,
     [("Next.js 14", "framework"), ("App Router", "pattern"), ("pages/", "pattern"), ("loading.tsx", "file")],
     [("App Router", "pages/", "REPLACES")],
     "which Next.js routing model replaced pages/ and how do per-segment loading states work",
     "next 14 app router pages directory loading tsx segment suspense"),
    # --- 13 ---
    ("Parallel routes render the analytics panel alongside the main feed through the @analytics slot; the two panels stream independently so a slow query in one cannot stall the other.", "reference", "technical", False,
     [("Parallel routes", "pattern"), ("@analytics", "pattern"), ("feed", "project")],
     [("Parallel routes", "feed", "APPLIES_TO")],
     "which App Router feature lets the analytics panel stream separately from the main feed",
     "parallel route analytics slot feed stream independent next app"),
    # --- 14 ---
    ("Intercepting routes drive the photo modal; the /photos/[id] route still exists for direct links, but navigating from the grid opens the same view inline without a full page transition.", "reference", "technical", False,
     [("Intercepting routes", "pattern"), ("photo modal", "project"), ("/photos/[id]", "pattern")],
     [("Intercepting routes", "photo modal", "APPLIES_TO")],
     "which App Router pattern drives the inline photo modal while keeping deep links intact",
     "intercept route photo modal grid inline deep link next"),
    # --- 15 ---
    ("Turbopack became the default dev server in Next.js 15; cold starts on the monorepo dropped from eleven seconds to under two, and HMR for server components is finally instant.", "milestone", "technical", False,
     [("Turbopack", "tool"), ("Next.js 15", "framework"), ("HMR", "pattern")],
     [("Turbopack", "Next.js 15", "APPLIES_TO")],
     "which bundler became the default Next.js 15 dev server and what cold-start win did it bring",
     "turbopack next 15 default dev cold start hmr server component"),
    # --- 16 ---
    ("next/image handles all user avatars through the remotePatterns allowlist; the CDN auto-generates AVIF and WebP variants and the layout-shift score dropped to zero on the profile page.", "architecture", "technical", False,
     [("next/image", "library"), ("remotePatterns", "config"), ("AVIF", "technology"), ("WebP", "technology")],
     [("next/image", "AVIF", "PRODUCES")],
     "which Next.js image component handles avatars and what formats does its CDN emit",
     "next image remote pattern avif webp avatar layout shift cdn"),
    # --- 17 ---
    ("Metadata API replaced next-seo across the site; per-route generateMetadata functions read live data and OpenGraph tags now reflect the actual article title instead of a template.", "reference", "technical", False,
     [("Metadata API", "api"), ("next-seo", "library"), ("generateMetadata", "api"), ("OpenGraph", "protocol")],
     [("Metadata API", "next-seo", "REPLACES")],
     "which Next.js API retired next-seo for per-route OpenGraph tags",
     "metadata api next seo generate open graph article per route"),
    # --- 18 ---
    ("Remix folded back into React Router v7; the same app runs as an SPA or with a loader-driven server, and we kept the Remix-style loader and action exports verbatim through the migration.", "reference", "technical", False,
     [("Remix", "framework"), ("React Router v7", "framework"), ("loader", "pattern"), ("action", "pattern")],
     [("React Router v7", "Remix", "REPLACES")],
     "which merge unified Remix with React Router v7 and which export shape survived the move",
     "remix react router v7 loader action spa server merge"),
    # --- 19 ---
    ("TanStack Start replaced our ad-hoc Vite plus React Router setup for the new admin app; streaming SSR, server functions, and type-safe routing came out of the box.", "decision", "technical", False,
     [("TanStack Start", "framework"), ("Vite", "tool"), ("React Router", "framework"), ("admin app", "project")],
     [("TanStack Start", "Vite", "REPLACES")],
     "which full-stack React framework replaced the Vite-plus-React-Router scaffold on the admin app",
     "tanstack start vite react router admin streaming ssr server function"),
    # --- 20 ---
    ("Every GET call in the app goes through TanStack Query now; cache keys are arrays of literals, staleTime defaults to 30 seconds, and the React Query Devtools ship only in dev builds.", "fact", "technical", False,
     [("TanStack Query", "library"), ("staleTime", "config"), ("React Query Devtools", "tool")],
     [("TanStack Query", "React Query Devtools", "USES")],
     "which data library owns all GET calls and what default staleTime did we settle on",
     "tanstack query stale time devtools cache key array get"),
    # --- 21 ---
    ("TanStack Router replaced React Router on the type-heavy dashboard; route params and search params are now typed end-to-end and a wrong link() call fails at compile time.", "decision", "technical", False,
     [("TanStack Router", "library"), ("React Router", "framework"), ("dashboard", "project"), ("link()", "api")],
     [("TanStack Router", "React Router", "REPLACES")],
     "which router gave the dashboard end-to-end typed params and compile-time link checks",
     "tanstack router react router typed param search dashboard link"),
    # --- 22 ---
    ("TanStack Table powers the ledger grid with 40k rows; column filters, virtualised rows via @tanstack/react-virtual, and a headless API let us style everything with Tailwind.", "fact", "technical", False,
     [("TanStack Table", "library"), ("@tanstack/react-virtual", "library"), ("Tailwind", "framework"), ("ledger grid", "project")],
     [("TanStack Table", "@tanstack/react-virtual", "USES")],
     "which headless table and virtualiser stack renders the 40k-row ledger grid and what styles it",
     "tanstack table react virtual tailwind ledger grid headless column"),
    # --- 23 ---
    ("TanStack Form is handling the multi-step onboarding; field-level validation with Zod and async validation against the profile endpoint replaced a pile of useState guards.", "reference", "technical", False,
     [("TanStack Form", "library"), ("Zod", "library"), ("profile endpoint", "service"), ("useState", "api")],
     [("TanStack Form", "useState", "REPLACES")],
     "which form library plus schema validator took over the multi-step onboarding flow",
     "tanstack form zod profile endpoint onboarding async field validation"),
    # --- 24 ---
    ("Redux Toolkit is still the store of record for the trading terminal; createSlice plus RTK Query handle both local state and server cache, and the new listener middleware replaced redux-saga outright.", "architecture", "technical", False,
     [("Redux Toolkit", "library"), ("createSlice", "api"), ("RTK Query", "library"), ("redux-saga", "library"), ("listener middleware", "pattern")],
     [("listener middleware", "redux-saga", "REPLACES")],
     "which Redux Toolkit primitives run the trading terminal and what did the listener middleware retire",
     "redux toolkit create slice rtk query saga listener terminal"),
    # --- 25 ---
    ("Picked Zustand over Redux Toolkit for the whiteboard side-panel; the store is fifteen lines, no provider is required, and the devtools middleware still gives us time-travel when debugging.", "decision", "technical", False,
     [("Zustand", "library"), ("Redux Toolkit", "library"), ("devtools middleware", "pattern"), ("whiteboard", "project")],
     [("Zustand", "Redux Toolkit", "PREFERS")],
     "which lightweight store won over Redux Toolkit for the whiteboard side-panel and why",
     "zustand redux toolkit whiteboard devtools time travel provider less"),
    # --- 26 ---
    ("Jotai drives the form editor because atom composition maps one-to-one onto nested field state; derived atoms with atomFamily gave per-row validation without selector gymnastics.", "decision", "technical", False,
     [("Jotai", "library"), ("atomFamily", "api"), ("form editor", "project")],
     [("Jotai", "form editor", "APPLIES_TO")],
     "which atomic state library fits the nested form editor and which API handles per-row validation",
     "jotai atom family form editor derived nested field state"),
    # --- 27 ---
    ("Valtio handles the collaborative cursor layer; proxy-based mutation feels like plain assignment, and snapshot-per-render avoids the tearing we used to see with Zustand in concurrent mode.", "decision", "technical", False,
     [("Valtio", "library"), ("Zustand", "library"), ("collaborative cursor", "project"), ("concurrent mode", "pattern")],
     [("Valtio", "Zustand", "PREFERS")],
     "which proxy store runs the collaborative cursor layer and which tearing issue did it avoid",
     "valtio zustand collaborative cursor proxy snapshot concurrent tearing"),
    # --- 28 ---
    ("Recoil is deprecated as of its final release; the remaining Recoil atoms in the canvas package are on a migration ticket to Jotai and no new features will be written against it.", "reference", "technical", False,
     [("Recoil", "library"), ("Jotai", "library"), ("canvas package", "project")],
     [("Jotai", "Recoil", "REPLACES")],
     "what is the migration target for the deprecated Recoil atoms remaining in the canvas package",
     "recoil deprecated jotai canvas migration atom final release"),
    # --- 29 ---
    ("XState runs the checkout flow's state chart; invoked actors handle the payment webhook race, and visualising the machine caught a missing guard that was letting double-submits through.", "architecture", "technical", False,
     [("XState", "library"), ("checkout flow", "project"), ("invoked actor", "pattern"), ("payment webhook", "service")],
     [("XState", "payment webhook", "APPLIES_TO")],
     "which state-chart library runs checkout and what bug did visualising the machine catch",
     "xstate checkout invoked actor payment webhook guard double submit"),
    # --- 30 ---
    ("React Hook Form paired with Zod is the default form stack; resolver wires the schema into the form, and the same Zod schema validates the Server Action body on submit.", "preference", "technical", False,
     [("React Hook Form", "library"), ("Zod", "library"), ("Server Action", "framework"), ("resolver", "api")],
     [("React Hook Form", "Zod", "USES")],
     "which form library and schema validator form our default pair across client and server actions",
     "react hook form zod resolver server action schema body submit"),
    # --- 31 ---
    ("Radix UI Primitives underpin every interactive component; accessibility, focus management, and keyboard semantics come for free, and we layer Tailwind classes on top rather than shipping the base styles.", "architecture", "technical", False,
     [("Radix UI", "library"), ("Tailwind", "framework"), ("focus management", "concept")],
     [("Radix UI", "Tailwind", "USES")],
     "which headless primitives give us accessibility for free and what do we layer styling with",
     "radix ui primitive tailwind accessibility focus keyboard semantics"),
    # --- 32 ---
    ("shadcn/ui components were copied into components/ui rather than installed as a package; the CLI scaffolds each primitive with its own Tailwind classes so design-system tweaks stay in-repo.", "decision", "technical", False,
     [("shadcn/ui", "library"), ("components/ui", "file"), ("Tailwind", "framework")],
     [("shadcn/ui", "Tailwind", "USES")],
     "why did we copy shadcn/ui components in-repo instead of installing them as a package",
     "shadcn ui components tailwind cli scaffold design system in repo"),
    # --- 33 ---
    ("Mantine powers the internal admin CMS because the date picker, rich text, and notifications modules gave us 80 percent of the surface area without pulling twelve separate libraries.", "decision", "technical", False,
     [("Mantine", "library"), ("admin CMS", "project")],
     [("Mantine", "admin CMS", "APPLIES_TO")],
     "which component kit covers the internal admin CMS and which modules justified the pick",
     "mantine admin cms date picker rich text notification module"),
    # --- 34 ---
    ("Chakra UI v3 migration is in progress on the partner portal; the biggest break was the switch to Panda CSS styling and the move away from the runtime emotion pipeline.", "milestone", "technical", False,
     [("Chakra UI", "library"), ("Panda CSS", "library"), ("emotion", "library"), ("partner portal", "project")],
     [("Panda CSS", "emotion", "REPLACES")],
     "which Chakra UI version bump flipped the styling engine to Panda CSS on the partner portal",
     "chakra ui v3 panda css emotion partner portal migration styling"),
    # --- 35 ---
    ("Material UI still owns the finance console because the MUI X data grid and date range picker have no drop-in equivalents; we pin the theme to a narrow palette to hide the Google-ish defaults.", "preference", "technical", False,
     [("Material UI", "library"), ("MUI X", "library"), ("finance console", "project")],
     [("MUI X", "finance console", "APPLIES_TO")],
     "which component library stays on the finance console and which paid component locks us in",
     "material ui mui x finance console data grid date range picker"),
    # --- 36 ---
    ("Ant Design drives the logistics back office because of its dense table layout and Chinese-locale-first form validation; we cherry-pick components rather than ship the whole theme.", "decision", "technical", False,
     [("Ant Design", "library"), ("logistics back office", "project")],
     [("Ant Design", "logistics back office", "APPLIES_TO")],
     "which component library runs the logistics back office and what does it do well there",
     "ant design logistics back office dense table chinese locale form"),
    # --- 37 ---
    ("Tailwind CSS 4 ships with a Rust-based Oxide engine; build times on the monorepo dropped by half and the JIT configuration collapsed into a single @theme block inside the global stylesheet.", "milestone", "technical", False,
     [("Tailwind CSS 4", "framework"), ("Oxide", "tool"), ("@theme", "api")],
     [("Tailwind CSS 4", "Oxide", "USES")],
     "which Tailwind CSS 4 engine rewrite cut build times and where does the config live now",
     "tailwind 4 oxide rust theme block global stylesheet build time"),
    # --- 38 ---
    ("Styled Components is on the freeze list; no new code should import it and the marketing site migration to Tailwind retired the last runtime style sheet in a production bundle.", "preference", "technical", False,
     [("Styled Components", "library"), ("Tailwind", "framework"), ("marketing site", "project")],
     [("Tailwind", "Styled Components", "REPLACES")],
     "why is Styled Components on the freeze list and what replaced it on the marketing site",
     "styled components freeze tailwind marketing site runtime style"),
    # --- 39 ---
    ("Emotion remains in the legacy design system behind a compatibility shim; css prop usage still compiles, but new components use Vanilla Extract tokens to share types with the server.", "architecture", "technical", False,
     [("Emotion", "library"), ("Vanilla Extract", "library"), ("design system", "project"), ("css prop", "api")],
     [("Vanilla Extract", "Emotion", "REPLACES")],
     "which styling library replaces Emotion in new components and why",
     "emotion vanilla extract design system css prop shim token"),
    # --- 40 ---
    ("Vanilla Extract tokens are the source of truth for colour, spacing, and typography; TypeScript types flow into both React components and server-rendered emails without duplication.", "architecture", "technical", False,
     [("Vanilla Extract", "library"), ("TypeScript", "language"), ("server-rendered emails", "project")],
     [("Vanilla Extract", "TypeScript", "USES")],
     "which styling library supplies typed design tokens for both React and server-rendered emails",
     "vanilla extract typescript token colour spacing typography email"),
    # --- 41 ---
    ("CSS Modules still power the pre-existing docs site because the Eleventy build picked them up for free; no need to drag Tailwind into a 20-page content site that ships no React at all.", "preference", "technical", False,
     [("CSS Modules", "technology"), ("Eleventy", "framework"), ("docs site", "project"), ("Tailwind", "framework")],
     [("CSS Modules", "Tailwind", "PREFERS")],
     "why do we keep CSS Modules on the Eleventy docs site instead of reaching for Tailwind",
     "css modules eleventy docs site tailwind content pre existing"),
    # --- 42 ---
    ("React Testing Library plus Vitest replaced Jest on the core packages; jsdom starts faster under Vite and the same configuration runs tests in the browser via @vitest/browser when needed.", "milestone", "technical", False,
     [("React Testing Library", "library"), ("Vitest", "library"), ("Jest", "library"), ("@vitest/browser", "library")],
     [("Vitest", "Jest", "REPLACES")],
     "which testing stack replaced Jest on the core packages and what browser option comes with it",
     "react testing library vitest jest jsdom browser vite core package"),
    # --- 43. noise ---
    ("The neighbours' dog found the squeaky pineapple we hid in the azaleas and now there is a small hole where the azalea used to be.", "fact", "noise", True, [], [], None, None),
    # --- 44 ---
    ("Playwright runs the end-to-end suite across Chromium, Firefox, and WebKit; the trace viewer is the first thing on-call opens when a nightly run fails because the DOM snapshot plus network log is enough to triage.", "fact", "technical", False,
     [("Playwright", "tool"), ("trace viewer", "tool"), ("Chromium", "platform"), ("WebKit", "platform")],
     [("Playwright", "trace viewer", "PRODUCES")],
     "which E2E runner drives the cross-browser suite and what artefact does on-call open on failure",
     "playwright chromium firefox webkit trace viewer e2e on call"),
    # --- 45 ---
    ("Jest lingers only in the legacy mobile packages because React Native's Metro plus jest-expo preset still expect it; the migration to Vitest is blocked until the RN side supports Vite.", "problem", "technical", False,
     [("Jest", "library"), ("Metro", "tool"), ("jest-expo", "library"), ("Vitest", "library")],
     [("Vitest", "Jest", "REPLACES")],
     "why is the mobile Jest-to-Vitest migration blocked and which tooling holds it back",
     "jest metro expo vitest react native mobile migration blocked"),
    # --- 46 ---
    ("Snapshot tests in React Testing Library are banned by lint rule; every assertion must describe an accessible role or label so rewrites do not spuriously churn generated strings.", "problem", "technical", False,
     [("React Testing Library", "library"), ("Snapshot tests", "pattern"), ("lint rule", "pattern")],
     [("React Testing Library", "Snapshot tests", "CONTRADICTS")],
     "which testing anti-pattern is blocked by lint and what assertion style replaces it",
     "react testing library snapshot lint role label accessible"),
    # --- 47 ---
    ("Playwright component testing picked up the Radix UI primitives directly; visual regressions against the design system no longer require a full Next.js harness to render a single popover.", "decision", "technical", False,
     [("Playwright", "tool"), ("component testing", "pattern"), ("Radix UI", "library"), ("Next.js", "framework")],
     [("Playwright", "Next.js", "REPLACES")],
     "which Playwright mode lets us visual-test Radix primitives without booting a full Next.js app",
     "playwright component testing radix ui next js visual regression"),
    # --- 48 ---
    ("Adopted msw for the browser and node test fakes; request handlers live alongside the components and both Playwright and Vitest import the same handler definitions.", "architecture", "technical", False,
     [("msw", "library"), ("Playwright", "tool"), ("Vitest", "library")],
     [("Playwright", "msw", "USES"), ("Vitest", "msw", "USES")],
     "which mocking library feeds both Playwright browser tests and Vitest node tests from the same handlers",
     "msw playwright vitest browser node handler mock shared definition"),
    # --- 49 ---
    ("Turbopack's persistent build cache in Next.js 15.1 survives across branch switches; CI cold builds still rebuild from scratch but local checkouts jumping between feature branches get near-instant rebuilds.", "fact", "technical", False,
     [("Turbopack", "tool"), ("Next.js 15.1", "framework"), ("persistent build cache", "pattern")],
     [("Turbopack", "persistent build cache", "USES")],
     "which Turbopack improvement in Next.js 15.1 speeds up local branch switches",
     "turbopack next 15 1 persistent build cache branch switch rebuild"),
    # --- 50 ---
    ("Streaming Server Actions return a ReadableStream so long-running exports push progress back to the client without a polling loop; the old POST-then-poll endpoint was deleted with its cron cleanup job.", "architecture", "technical", False,
     [("Server Actions", "framework"), ("ReadableStream", "api"), ("POST-then-poll", "pattern")],
     [("Server Actions", "POST-then-poll", "REPLACES")],
     "which streaming primitive let long-running exports push progress without a polling endpoint",
     "server action readable stream post poll progress export cron"),
]


def _find_span(text: str, needle: str, used: list[tuple[int, int]]) -> tuple[int, int]:
    start = 0
    while True:
        idx = text.find(needle, start)
        if idx < 0:
            raise ValueError(f"entity name {needle!r} not found in text {text!r}")
        end = idx + len(needle)
        overlap = any(not (end <= s or idx >= e) for s, e in used)
        if not overlap:
            return idx, end
        start = idx + 1


def emit() -> int:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    written = 0
    with OUT.open("w", encoding="utf-8") as f:
        for i, entry in enumerate(ENTRIES, start=1):
            text, mt, domain, noise, ents, rels, qq, qk = entry
            used: list[tuple[int, int]] = []
            entities = []
            for name, typ in ents:
                s, e = _find_span(text, name, used)
                used.append((s, e))
                entities.append({"name": name, "type": typ, "start": s, "end": e})
            row: dict = {
                "id": f"shared-{ID_OFFSET + i:05d}",
                "domain": domain,
                "text": text,
                "memory_type": mt,
                "noise": noise,
                "entities": entities,
                "relationships": [{"source": s, "target": t, "type": r} for s, t, r in rels],
            }
            if qq is not None and qk is not None:
                row["queries"] = [
                    {"form": "question", "text": qq},
                    {"form": "keyword", "text": qk},
                ]
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
            written += 1
    return written


if __name__ == "__main__":
    n = emit()
    print(f"wrote {n} rows to {OUT}")
