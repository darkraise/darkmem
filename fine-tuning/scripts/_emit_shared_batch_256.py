"""One-off emitter for shared-base batch-256 — technical domain (non-React modern JS frameworks: Svelte/SvelteKit, Solid/SolidStart, Qwik/QwikCity, Astro, Lit, Stencil, Preact, Alpine, htmx, Turbo, Stimulus, Marko, Hydrogen, Nuxt, Analog, Fresh, Redwood).

Writes 50 rows to data/v2/shared/batch_256.tmp.jsonl with ids shared-12751..12800.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "shared" / "batch_256.tmp.jsonl"
ID_OFFSET = 12750

# (text, memory_type, domain, noise, entities, relationships, qq, qk)
ENTRIES: list[tuple] = [
    # --- 1 ---
    ("Migrated the dashboard stores from Svelte writable to Svelte 5 runes; $state replaces the imported store helper and $derived collapses the old get/subscribe wrappers into plain expressions.", "architecture", "technical", False,
     [("Svelte 5", "framework"), ("writable", "method"), ("$state", "api"), ("$derived", "api")],
     [("$state", "writable", "REPLACES")],
     "which Svelte 5 rune took over from the writable store helper in the dashboard refactor",
     "svelte 5 runes state derived writable store replace dashboard"),
    # --- 2 ---
    ("Picked Svelte over Vue for the marketing site because the compile-to-vanilla-JS model drops the runtime bundle to near zero and the team prefers single-file components with scoped styles.", "decision", "technical", False,
     [("Svelte", "framework"), ("Vue", "framework"), ("compile-to-vanilla-JS", "pattern")],
     [("Svelte", "Vue", "PREFERS")],
     "why did the marketing site land on Svelte instead of Vue and what bundle property sealed the pick",
     "svelte vue marketing compile vanilla js bundle runtime pick"),
    # --- 3 ---
    ("SvelteKit load functions now run in +page.server.ts for the account pages so the session cookie stays server-side; the browser load ran into a mixed-auth state during prerender and got retired.", "decision", "technical", False,
     [("SvelteKit", "framework"), ("+page.server.ts", "file"), ("browser load", "pattern"), ("session cookie", "concept")],
     [("+page.server.ts", "browser load", "REPLACES")],
     "which SvelteKit load layer took over the account pages after prerender broke the browser version",
     "sveltekit load page server ts browser session cookie account"),
    # --- 4 ---
    ("Form actions in SvelteKit drive the checkout flow with progressive enhancement; the +page.svelte form posts to a named action and the fallback still works when JavaScript is disabled in the browser.", "architecture", "technical", False,
     [("Form actions", "pattern"), ("SvelteKit", "framework"), ("+page.svelte", "file"), ("progressive enhancement", "pattern")],
     [("Form actions", "SvelteKit", "APPLIES_TO")],
     "how does the checkout flow stay functional without JavaScript while still using SvelteKit form actions",
     "sveltekit form action progressive enhancement page svelte checkout"),
    # --- 5 ---
    ("The reactive derivation chain that was five $: labels deep got rewritten as $derived rune expressions; the compiler output shrinks and the read graph is now traceable without squinting at dollar-colons.", "milestone", "technical", False,
     [("$derived", "api"), ("$: labels", "pattern"), ("reactive derivation", "concept")],
     [("$derived", "$: labels", "REPLACES")],
     "which Svelte 5 rune collapsed the deep chain of dollar-colon reactive labels",
     "svelte derived rune dollar colon label reactive chain rewrite"),
    # --- 6 ---
    ("Bound the canvas width prop with $bindable so the parent component reads live resize values; the earlier custom event plumbing was fragile and missed mid-drag updates on Safari builds.", "problem", "technical", False,
     [("$bindable", "api"), ("canvas", "api"), ("Safari", "platform"), ("custom event", "pattern")],
     [("$bindable", "custom event", "REPLACES")],
     "which Svelte 5 rune replaced custom events for two-way canvas width binding on Safari",
     "svelte bindable canvas width custom event safari mid drag resize"),
    # --- 7 ---
    ("Switched effect registration from onMount/afterUpdate pairs to a single $effect block per concern; the rune tracks dependencies automatically and the cleanup function runs deterministically on disposal.", "decision", "technical", False,
     [("$effect", "api"), ("onMount", "method"), ("afterUpdate", "method")],
     [("$effect", "onMount", "REPLACES")],
     "which rune consolidated onMount and afterUpdate lifecycle pairs in the Svelte refactor",
     "svelte effect rune on mount after update lifecycle cleanup track"),
    # --- 8 ---
    ("Component prop typing moved to $props with a TypeScript generic; the export let dance with $$Props fallbacks was hurting editor jump-to-definition and got dropped across the design system.", "decision", "technical", False,
     [("$props", "api"), ("TypeScript", "language"), ("export let", "pattern"), ("design system", "project")],
     [("$props", "export let", "REPLACES")],
     "which Svelte 5 mechanism replaced export let for typed component props in the design system",
     "svelte props rune export let typescript generic design system"),
    # --- 9 ---
    ("Picked Solid.js for the trading terminal after benchmarks showed fine-grained reactivity beats virtual-DOM diffing on 5000-cell updates per second; the render loop stays flat instead of thrashing.", "decision", "technical", False,
     [("Solid.js", "framework"), ("fine-grained reactivity", "pattern"), ("virtual-DOM", "pattern"), ("trading terminal", "project")],
     [("Solid.js", "virtual-DOM", "PREFERS")],
     "why did the trading terminal pick Solid.js over a virtual-DOM framework at 5000 updates per second",
     "solid js fine grained reactivity virtual dom trading terminal cell"),
    # --- 10. noise ---
    ("The coffee machine in the kitchenette is leaking from the drip tray again and maintenance has taped a hand-drawn sign over the button.", "fact", "noise", True, [], [], None, None),
    # --- 11 ---
    ("The team prefers Solid primitives for real-time data views: createSignal for the live value, createMemo for derived aggregates, and createEffect for DOM side effects, because the reviewers find this split easier to read than a useReducer-style bundle on the price ticker.", "preference", "technical", False,
     [("createSignal", "api"), ("createMemo", "api"), ("createEffect", "api"), ("Solid", "framework")],
     [("createSignal", "Solid", "APPLIES_TO")],
     "which Solid primitive split does the team prefer for real-time data views and why",
     "solid signal memo effect prefer real time price ticker review"),
    # --- 12 ---
    ("SolidStart ships the landing page; the server islands render above-the-fold at request time while the interactive widgets hydrate on idle so first paint beats the Core Web Vitals budget.", "milestone", "technical", False,
     [("SolidStart", "framework"), ("server islands", "pattern"), ("Core Web Vitals", "concept")],
     [("SolidStart", "server islands", "USES")],
     "which SolidStart pattern keeps the landing page inside the Core Web Vitals budget on first paint",
     "solid start server island core web vital landing page idle hydrate"),
    # --- 13 ---
    ("Chose Qwik for the catalog because resumability skips the hydration step on load and the page picks up interactivity directly from the serialized state without re-executing component setup code.", "decision", "technical", False,
     [("Qwik", "framework"), ("resumability", "concept"), ("hydration", "concept"), ("catalog", "project")],
     [("resumability", "hydration", "REPLACES")],
     "which Qwik concept replaces hydration on the catalog page and what does the client skip at load",
     "qwik resumability hydration catalog load serialize state setup"),
    # --- 14 ---
    ("Qwik $ boundaries split the checkout handler into lazy-loaded chunks; onClick$ pulls the click handler over the wire only when the user actually clicks, not on initial render.", "fact", "technical", False,
     [("Qwik", "framework"), ("$ boundaries", "pattern"), ("onClick$", "api")],
     [("$ boundaries", "Qwik", "APPLIES_TO")],
     "how does Qwik defer the click handler bytes until the user actually clicks on checkout",
     "qwik dollar boundary onclick lazy chunk checkout wire user click"),
    # --- 15 ---
    ("Qwik City reference: file-based routes live under src/routes and export default handlers for GET, POST, and action endpoints, which lets the storefront collocate server endpoints without a separate API server per feature.", "reference", "technical", False,
     [("Qwik City", "framework"), ("storefront", "project"), ("src/routes", "file")],
     [("Qwik City", "storefront", "APPLIES_TO")],
     "how does Qwik City avoid standing up a separate API server for storefront endpoints",
     "qwik city routing src routes storefront endpoint file based api"),
    # --- 16 ---
    ("Astro 5 runs the docs site with islands architecture; most pages ship zero JavaScript and only the search box and theme toggle islands hydrate on the client when the user focuses them.", "architecture", "technical", False,
     [("Astro 5", "framework"), ("islands architecture", "pattern"), ("docs site", "project")],
     [("islands architecture", "Astro 5", "APPLIES_TO")],
     "which Astro architecture keeps most docs pages at zero client JavaScript while still enabling search",
     "astro 5 island architecture docs zero javascript search theme toggle"),
    # --- 17 ---
    ("Astro DB stores content collections for the changelog; typed queries from +page files stay server-side and the production build emits a prebuilt SQLite bundle for edge reads.", "fact", "technical", False,
     [("Astro DB", "database"), ("content collections", "pattern"), ("SQLite", "database"), ("changelog", "project")],
     [("Astro DB", "SQLite", "USES")],
     "how does Astro DB serve changelog queries at the edge after a production build",
     "astro db content collection changelog sqlite edge prebuilt query"),
    # --- 18 ---
    ("Astro Actions replaced the hand-rolled form POST endpoints; typed client calls go through a single actions handler and the framework validates input with Zod before the server function runs.", "decision", "technical", False,
     [("Astro Actions", "api"), ("Zod", "library"), ("form POST", "pattern")],
     [("Astro Actions", "form POST", "REPLACES")],
     "which Astro feature took over hand-rolled form POST endpoints and how is input validated",
     "astro action form post zod typed client validate server function"),
    # --- 19 ---
    ("View Transitions ship on the Astro blog; same-origin nav animates the article header into place without a full reload and the fallback keeps classic nav for browsers without the API.", "fact", "technical", False,
     [("View Transitions", "api"), ("Astro", "framework"), ("blog", "project")],
     [("View Transitions", "Astro", "APPLIES_TO")],
     "how does the Astro blog animate same-origin navigation while still degrading on older browsers",
     "view transition astro blog same origin animate article fallback nav"),
    # --- 20 ---
    ("Server islands in Astro 5 defer personalised blocks past first paint; the public shell streams immediately and the greeting island renders from the server once the session lookup resolves.", "architecture", "technical", False,
     [("Server islands", "pattern"), ("Astro 5", "framework"), ("first paint", "concept"), ("session lookup", "method")],
     [("Server islands", "Astro 5", "APPLIES_TO")],
     "which Astro 5 mechanism defers personalised greeting blocks without blocking first paint",
     "astro server island first paint personalise greeting session defer"),
    # --- 21 ---
    ("Chose Lit for the embedded admin panel because web components register their tag once and the panel works inside the host CMS iframe without framework conflicts with whatever the host page already ships.", "decision", "technical", False,
     [("Lit", "library"), ("web components", "pattern"), ("admin panel", "project"), ("CMS", "service")],
     [("Lit", "web components", "IMPLEMENTS")],
     "which library lets the admin panel run inside a host CMS iframe without framework conflicts",
     "lit web component admin panel cms iframe host tag element"),
    # --- 22 ---
    ("Stencil compiles the design-system components to framework-agnostic custom elements; the output loads cleanly in the Angular app, the Vue dashboard, and the plain HTML marketing pages.", "architecture", "technical", False,
     [("Stencil", "framework"), ("custom elements", "pattern"), ("Angular", "framework"), ("Vue", "framework")],
     [("Stencil", "custom elements", "PRODUCES")],
     "which compiler outputs the design-system components so Angular, Vue, and plain HTML all consume them",
     "stencil custom element angular vue html design system compile"),
    # --- 23 ---
    ("Swapped React for Preact on the embedded widget: the 3 KB runtime drops the bundle under the partner's size budget and the compat shim covers the existing hooks without a rewrite.", "decision", "technical", False,
     [("Preact", "framework"), ("React", "framework"), ("compat shim", "pattern"), ("embedded widget", "project")],
     [("Preact", "React", "REPLACES")],
     "which lightweight framework replaced React on the embedded widget to hit the partner size budget",
     "preact react embed widget size bundle compat shim hook partner"),
    # --- 24 ---
    ("Alpine.js sprinkles interactivity on the server-rendered admin: x-data, x-show, and x-on keep a settings panel reactive without a bundler step and without the React dependency the team didn't want.", "architecture", "technical", False,
     [("Alpine.js", "framework"), ("x-data", "api"), ("x-show", "api"), ("x-on", "api")],
     [("Alpine.js", "x-data", "USES")],
     "which three Alpine.js directives drive the settings panel without needing a bundler",
     "alpine js x data show on settings panel server render bundler"),
    # --- 25 ---
    ("htmx attribute reference: hx-get fetches a partial, hx-target picks the swap destination, hx-swap selects the swap strategy, and hx-trigger chooses the DOM event with optional debounce like keyup changed delay:300ms, which the inbox filters rely on end to end.", "reference", "technical", False,
     [("htmx", "library"), ("hx-get", "api"), ("hx-target", "api"), ("hx-trigger", "api"), ("hx-swap", "api"), ("inbox filters", "project")],
     [("htmx", "inbox filters", "APPLIES_TO")],
     "what are the four htmx attributes that fetch, target, swap, and trigger requests and how do the inbox filters use them",
     "htmx hx get target trigger swap attribute reference inbox keyup"),
    # --- 26 ---
    ("Adopted htmx over Alpine.js for the server-rendered marketplace; the team preferred plain hx attributes on the server markup and didn't need the reactive client store Alpine provided.", "decision", "technical", False,
     [("htmx", "library"), ("Alpine.js", "framework"), ("marketplace", "project")],
     [("htmx", "Alpine.js", "PREFERS")],
     "why did the marketplace move from Alpine.js to htmx and what feature of Alpine was surplus",
     "htmx alpine marketplace server render reactive store attribute pick"),
    # --- 27 ---
    ("Turbo drives the Rails admin as part of the Hotwire stack: turbo-frame swaps in a settings panel on link click and turbo-stream pushes live table updates over the WebSocket without a client-side router.", "architecture", "technical", False,
     [("Turbo", "framework"), ("Hotwire", "framework"), ("turbo-frame", "api"), ("turbo-stream", "api"), ("WebSocket", "protocol")],
     [("Turbo", "Hotwire", "IS_A")],
     "how do turbo-frame and turbo-stream split duties on the Rails admin panel",
     "turbo hotwire frame stream rails admin websocket client router"),
    # --- 28 ---
    ("Stimulus reference for the Hotwire stack: data-controller names the controller class and data-action binds DOM events to controller methods in the form event->controller#method, which is the whole extension surface for wiring behaviour to markup.", "reference", "technical", False,
     [("Stimulus", "framework"), ("Hotwire", "framework"), ("data-controller", "api"), ("data-action", "api")],
     [("Stimulus", "Hotwire", "IS_A")],
     "which two Stimulus attributes attach a controller class to markup and bind DOM events to methods",
     "stimulus hotwire data controller action method reference event bind"),
    # --- 29 ---
    ("Marko handles the eBay-scale product list; the streaming server-renderer flushes HTML as data resolves so the first row appears before the tail of the response even completes.", "fact", "technical", False,
     [("Marko", "framework"), ("eBay", "organization"), ("streaming server-renderer", "pattern")],
     [("Marko", "eBay", "APPLIES_TO")],
     "which Marko feature flushes the first product row before the response tail finishes",
     "marko ebay streaming server renderer product list flush html row"),
    # --- 30 ---
    ("Shipped the Shopify storefront on Hydrogen this sprint; @shopify/hydrogen-react primitives talk to the Storefront API and the Oxygen runtime hosts it at the edge with per-request caching rules now tuned in production.", "milestone", "technical", False,
     [("Hydrogen", "framework"), ("Shopify", "organization"), ("Storefront API", "api"), ("Oxygen", "infrastructure")],
     [("Hydrogen", "Shopify", "APPLIES_TO")],
     "which runtime hosts Hydrogen at the edge and which API drives the Shopify storefront",
     "hydrogen shopify storefront api oxygen edge cache primitive react"),
    # --- 31 ---
    ("Migrated the marketing app from Nuxt 2 to Nuxt 3 on Vue 3; the Composition API rewrite was mechanical per component but the plugins layer needed a real audit for server-versus-client boundaries.", "milestone", "technical", False,
     [("Nuxt 3", "framework"), ("Nuxt 2", "framework"), ("Vue 3", "framework"), ("Composition API", "api")],
     [("Nuxt 3", "Nuxt 2", "REPLACES")],
     "which Nuxt upgrade landed on Vue 3 and what non-mechanical part of the migration took real work",
     "nuxt 3 2 vue composition api migration plugin server client"),
    # --- 32 ---
    ("Nuxt 3 auto-imports blew up a circular dependency between composables; the fix declared imports explicitly in the three affected files so the build graph stopped flipping between module orders.", "problem", "technical", False,
     [("Nuxt 3", "framework"), ("auto-imports", "pattern"), ("composables", "pattern")],
     [],
     "which Nuxt 3 convenience hid a circular dependency and how did the fix unblock the build",
     "nuxt 3 auto import composable circular dependency build module order"),
    # --- 33 ---
    ("Analog provides the Angular meta-framework for the internal portal; file-based routing and server routes keep the shape familiar to the SvelteKit refugees on the team without dropping Angular.", "decision", "technical", False,
     [("Analog", "framework"), ("Angular", "framework"), ("SvelteKit", "framework"), ("internal portal", "project")],
     [("Analog", "Angular", "EXTENDS")],
     "which Angular meta-framework matched the SvelteKit-style file routing on the internal portal",
     "analog angular meta framework file route server sveltekit portal"),
    # --- 34 ---
    ("Fresh runs the edge API gateway on Deno; islands architecture plus TypeScript-first routing means the gateway ships zero npm dependencies and the supply-chain surface stays small by design.", "architecture", "technical", False,
     [("Fresh", "framework"), ("Deno", "platform"), ("edge API gateway", "project"), ("islands architecture", "pattern")],
     [("Fresh", "Deno", "DEPLOYED_ON")],
     "which Deno meta-framework runs the edge API gateway and what supply-chain property drove the pick",
     "fresh deno edge api gateway island typescript npm supply chain"),
    # --- 35 ---
    ("Redwood powers the nonprofit CMS; the GraphQL-first contract between web and api sides kept the page templates honest and the generator CLI boilerplates new models in one command.", "architecture", "technical", False,
     [("Redwood", "framework"), ("GraphQL", "protocol"), ("nonprofit CMS", "project"), ("generator CLI", "tool")],
     [("Redwood", "GraphQL", "USES")],
     "how does Redwood split web from api and which tool spins up a new model in one step",
     "redwood graphql nonprofit cms generator cli model web api side"),
    # --- 36 ---
    ("SvelteKit adapter reference: @sveltejs/adapter-cloudflare targets Cloudflare Pages and @sveltejs/adapter-node emits a standalone Node server, both selected through the SVELTE_ADAPTER environment variable the build reads at CI time.", "reference", "technical", False,
     [("SvelteKit", "framework"), ("Cloudflare Pages", "infrastructure"), ("Node", "platform"), ("SVELTE_ADAPTER", "config")],
     [("SvelteKit", "Cloudflare Pages", "DEPLOYED_ON")],
     "which two SvelteKit adapters cover Cloudflare Pages and Node, and which env var picks between them",
     "sveltekit adapter cloudflare pages node svelte adapter reference env"),
    # --- 37 ---
    ("Solid's createResource fetches account data with suspense support; the old manual effect-plus-signal pattern got dropped because pending states were racing with tab focus on the banking app.", "problem", "technical", False,
     [("createResource", "api"), ("Solid", "framework"), ("suspense", "concept"), ("banking app", "project")],
     [("createResource", "Solid", "APPLIES_TO")],
     "which Solid primitive replaced manual effect-plus-signal fetching after a pending-state race on tab focus",
     "solid create resource suspense effect signal tab focus banking race"),
    # --- 38 ---
    ("Qwik components use useSignal and useStore for state; useStore wraps an object reactively and useSignal keeps scalars, with both surviving the resume without re-running the component function.", "fact", "technical", False,
     [("Qwik", "framework"), ("useSignal", "api"), ("useStore", "api"), ("resume", "concept")],
     [("useSignal", "Qwik", "APPLIES_TO")],
     "how do Qwik useSignal and useStore divide state duties while preserving resume semantics",
     "qwik use signal store state resume scalar object reactive survive"),
    # --- 39 ---
    ("Astro content collections reference: collections live under src/content, each collection declares a Zod schema, and typed getEntry and getCollection calls return validated entries so frontmatter drift fails the build instead of surfacing at runtime.", "reference", "technical", False,
     [("Astro", "framework"), ("content collections", "pattern"), ("src/content", "file"), ("Zod", "library"), ("getEntry", "api"), ("getCollection", "api")],
     [("Astro", "Zod", "USES")],
     "where do Astro content collections live on disk, which library validates entries, and which two calls read them",
     "astro content collection src zod schema get entry reference frontmatter"),
    # --- 40 ---
    ("Lit reactive properties with @property decorators replaced the manual attributeChangedCallback plumbing; the decorator wires change detection and observed attributes in one declaration.", "decision", "technical", False,
     [("Lit", "library"), ("@property", "api"), ("attributeChangedCallback", "method")],
     [("@property", "attributeChangedCallback", "REPLACES")],
     "which Lit decorator retired manual attributeChangedCallback plumbing on the component library",
     "lit property decorator attribute changed callback reactive change"),
    # --- 41 ---
    ("Stencil output targets now emit ESM for modern browsers and a separate lazy bundle for older chromes; the dist-custom-elements target is the one the docs site imports directly.", "fact", "technical", False,
     [("Stencil", "framework"), ("ESM", "protocol"), ("dist-custom-elements", "config")],
     [],
     "which Stencil output target does the docs site import and what alternate bundle covers older chromes",
     "stencil output target esm dist custom element lazy bundle chrome"),
    # --- 42 ---
    ("Preact Signals API reference: signal(value) creates a reactive cell exposing .value, computed(fn) derives a read-only cell from other signals, and effect(fn) runs side effects on dependency changes, replacing the useState and useMemo hooks for fine-grained updates.", "reference", "technical", False,
     [("Preact", "framework"), ("Signals", "library"), ("signal", "api"), ("computed", "api"), ("useState", "api"), ("useMemo", "api")],
     [("Signals", "useState", "REPLACES")],
     "which three Preact Signals primitives cover reactive state, derivation, and side effects and what hooks do they replace",
     "preact signal computed effect use state memo reference reactive"),
    # --- 43. noise ---
    ("The stray cat that hangs around the side entrance got a name from the ops channel and someone set up a feeding rota on a spreadsheet.", "fact", "noise", True, [], [], None, None),
    # --- 44 ---
    ("htmx hx-boost upgraded full-page links to partial swaps; the upgrade dropped per-page JavaScript bundles from the docs archive and the browser history still behaved correctly on back navigation.", "milestone", "technical", False,
     [("htmx", "library"), ("hx-boost", "api"), ("docs archive", "project")],
     [("hx-boost", "htmx", "APPLIES_TO")],
     "which htmx attribute upgraded full-page links to partial swaps on the docs archive",
     "htmx hx boost link partial swap docs archive bundle back history"),
    # --- 45 ---
    ("The team prefers Turbo streams over ActionCable for live admin updates and keeps the polling endpoint only as a fallback; reviewers find the stream-based approach less noisy than hand-rolled fetch loops and the WebSocket upgrade is nearly always available in production.", "preference", "technical", False,
     [("Turbo", "framework"), ("ActionCable", "library"), ("polling", "pattern"), ("WebSocket", "protocol")],
     [("Turbo", "polling", "REPLACES")],
     "why does the team prefer Turbo streams over polling for live admin updates and what role does polling still play",
     "turbo action cable websocket poll prefer admin fallback review"),
    # --- 46 ---
    ("Stimulus controllers prefer data-action over inline onclick so the JavaScript stays out of the markup; the codebase now has a lint rule that flags any onclick surviving a Turbo refresh.", "preference", "technical", False,
     [("Stimulus", "framework"), ("data-action", "api"), ("onclick", "api"), ("lint rule", "tool")],
     [("data-action", "onclick", "PREFERS")],
     "which Stimulus convention replaced inline onclick and what tool enforces the rule across the codebase",
     "stimulus data action onclick inline lint rule enforce markup"),
    # --- 47 ---
    ("The team defaults to Svelte for internal tools and Astro for public content sites; Nuxt stays in play only on projects where a Vue 3 library is already in the customer stack.", "preference", "technical", False,
     [("Svelte", "framework"), ("Astro", "framework"), ("Nuxt", "framework"), ("Vue 3", "framework")],
     [("Svelte", "Nuxt", "PREFERS")],
     "what is the team default framework split between internal tools, content sites, and customer stacks",
     "svelte astro nuxt vue default internal content customer prefer"),
    # --- 48 ---
    ("Hydrogen caches Storefront API responses with stale-while-revalidate at Oxygen; the mean time-to-first-byte on the product page dropped below 80 ms during the holiday traffic benchmark.", "milestone", "technical", False,
     [("Hydrogen", "framework"), ("Storefront API", "api"), ("stale-while-revalidate", "pattern"), ("Oxygen", "infrastructure")],
     [("Hydrogen", "stale-while-revalidate", "USES")],
     "which caching pattern and runtime drove Hydrogen product-page TTFB below 80 ms during the holiday benchmark",
     "hydrogen storefront stale while revalidate oxygen ttfb holiday page"),
    # --- 49 ---
    ("Fresh route handlers in routes/api live as plain TypeScript files with a default export; the Deno Deploy target reads the same file tree at cold start without a bundler invocation in between.", "fact", "technical", False,
     [("Fresh", "framework"), ("routes/api", "file"), ("Deno Deploy", "infrastructure"), ("TypeScript", "language")],
     [("Fresh", "Deno Deploy", "DEPLOYED_ON")],
     "how do Fresh route handlers reach Deno Deploy without an intermediate bundler step",
     "fresh route api typescript deno deploy cold start bundler handler"),
    # --- 50 ---
    ("Redwood Cells standardise the loading/empty/failure/success states per data-bound component; the old mix of ad-hoc conditionals was tripping up code review and the Cell contract retired it.", "milestone", "technical", False,
     [("Redwood", "framework"), ("Cells", "pattern"), ("code review", "activity")],
     [("Cells", "Redwood", "APPLIES_TO")],
     "which Redwood pattern standardises loading, empty, failure, and success states across data-bound components",
     "redwood cell loading empty failure success data component review"),
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
