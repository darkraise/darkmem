"""One-off emitter for shared-base batch-117 — ai_coding domain (application state management in code / state libraries and store patterns on the frontend).

Writes 50 rows to data/v2/shared/batch_117.tmp.jsonl with ids shared-05801..05850.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "shared" / "batch_117.tmp.jsonl"
ID_OFFSET = 5800

# (text, memory_type, domain, noise, entities, relationships, qq, qk)
ENTRIES: list[tuple] = [
    # --- 1 ---
    ("Swapped the global Redux store for Zustand on the dashboard shell; the boilerplate dropped to a single create() call and the bundle shed 18 kB gzipped.", "decision", "ai_coding", False,
     [("Redux", "library"), ("Zustand", "library"), ("dashboard shell", "project")],
     [("Zustand", "Redux", "REPLACES")],
     "which state library replaced Redux on the dashboard shell and what was the bundle impact",
     "zustand replace redux dashboard shell bundle size boilerplate drop"),
    # --- 2 ---
    ("Redux Toolkit's createSlice became mandatory for any new reducer in the app; raw switch-case reducers and hand-rolled action constants are rejected at code review.", "preference", "ai_coding", False,
     [("Redux Toolkit", "library"), ("createSlice", "method"), ("reducer", "pattern")],
     [("Redux Toolkit", "reducer", "IMPROVES_ON")],
     "which Redux authoring style is now mandatory for new slices and which old style gets rejected",
     "redux toolkit createslice mandatory reducer switch case reject"),
    # --- 3 ---
    ("Atom graph on the editor canvas uses Jotai; each tool setting is a tiny atom and derived atoms compute the merged toolbox without re-rendering unrelated panels.", "architecture", "ai_coding", False,
     [("Jotai", "library"), ("editor canvas", "project"), ("atom", "concept")],
     [],
     "which atom-based state library drives the editor canvas and why did fine-grained atoms win",
     "jotai atom editor canvas derived render isolation tool setting"),
    # --- 4 ---
    ("Recoil got evicted from the collaboration workspace after its maintenance status stalled; the selectors were ported to Jotai with a small adapter layer.", "problem", "ai_coding", False,
     [("Recoil", "library"), ("Jotai", "library"), ("collaboration workspace", "project")],
     [("Jotai", "Recoil", "REPLACES")],
     "why did we migrate away from Recoil on the collaboration workspace and where did the atoms land",
     "recoil deprecate migrate jotai selector port adapter workspace"),
    # --- 5 ---
    ("Valtio's proxy wraps the ephemeral drag-and-drop state; mutating position.x directly inside the handler reads naturally and subscribers only fire for touched keys.", "fact", "ai_coding", False,
     [("Valtio", "library"), ("drag-and-drop", "pattern"), ("proxy", "pattern")],
     [],
     "which proxy-based library holds the drag-and-drop position and how does mutation flow",
     "valtio proxy drag drop mutate position subscribe touched key"),
    # --- 6 ---
    ("MobX observables still drive the legacy reporting module; we froze the migration because the decorator syntax reads cleanly and the team ships faster than a rewrite would.", "decision", "ai_coding", False,
     [("MobX", "library"), ("observables", "pattern"), ("reporting module", "project")],
     [],
     "why did we stop the MobX migration on the legacy reporting module rather than finish the rewrite",
     "mobx observable legacy reporting freeze migration decorator cost"),
    # --- 7 ---
    ("Replaced nested if-else in the checkout flow with an XState machine; invalid transitions like pay-then-edit-cart simply cannot fire and the visualiser became our spec.", "decision", "ai_coding", False,
     [("XState", "library"), ("checkout", "pattern"), ("nested if-else", "pattern")],
     [("XState", "nested if-else", "REPLACES")],
     "which library replaced the nested-if checkout flow and how did the state machine encode invalid transitions",
     "xstate checkout machine invalid transition visualiser spec if"),
    # --- 8 ---
    ("Effect-TS runtimes now host the background sync workflow; the retry, timeout, and cancellation policies compose declaratively instead of sprawling try-catch ladders.", "architecture", "ai_coding", False,
     [("Effect-TS", "library"), ("background sync", "pattern"), ("runtime", "concept")],
     [],
     "which effect system replaced try-catch ladders in the background sync flow",
     "effect ts runtime retry timeout cancel compose sync workflow"),
    # --- 9 ---
    ("The React Context was split into three providers after profiling: auth, theme, and feature flags; a single combined context had been re-rendering the entire tree on flag fetch.", "problem", "ai_coding", False,
     [("React Context", "library"), ("auth", "pattern"), ("feature flags", "pattern")],
     [],
     "which Context split fixed the full-tree re-render the dashboard used to suffer on flag fetch",
     "react context split auth theme flag rerender profile dashboard"),
    # --- 10. noise ---
    ("The office plant near the printer grew a crooked shoot that points at the coffee machine.", "fact", "noise", True, [], [], None, None),
    # --- 11 ---
    ("Signals from @preact/signals-react replaced a wide Redux slice for the timeline cursor; downstream components subscribe via computed and re-render only when their slice changes.", "decision", "ai_coding", False,
     [("@preact/signals-react", "library"), ("Redux", "library"), ("timeline cursor", "pattern")],
     [("@preact/signals-react", "Redux", "REPLACES")],
     "which signals library took over the timeline cursor from Redux and what render property did we gain",
     "preact signals react replace redux timeline cursor computed render"),
    # --- 12 ---
    ("Solid's createStore drives the admin panel's row selection; fine-grained reactivity means ticking a checkbox never re-renders the 2000 sibling rows.", "architecture", "ai_coding", False,
     [("Solid", "framework"), ("createStore", "method"), ("admin panel", "project")],
     [],
     "which Solid primitive powers row selection in the admin panel and what render cost did it remove",
     "solid createstore admin row selection fine grained reactive render"),
    # --- 13 ---
    ("Vue 3's ref and reactive carry the live form state; we picked the Composition API over the Options API because colocated refs beat the old data-options sprawl on deeply nested forms.", "preference", "ai_coding", False,
     [("Vue 3", "framework"), ("Composition API", "pattern"), ("Options API", "pattern")],
     [("Composition API", "Options API", "PREFERS")],
     "which Vue 3 API style carries form state and why did we stop writing the Options API",
     "vue composition api options ref reactive form compose nested"),
    # --- 14 ---
    ("Pinia replaced Vuex across every Vue 3 app; the TypeScript inference on getters and actions is dramatically better and modules disappeared in favour of plain stores.", "decision", "ai_coding", False,
     [("Pinia", "library"), ("Vuex", "library"), ("Vue 3", "framework")],
     [("Pinia", "Vuex", "REPLACES")],
     "which store library swapped in for Vuex across Vue 3 apps and what did typing feel like after",
     "pinia replace vuex vue 3 typescript getter action module flatten"),
    # --- 15 ---
    ("NgRx powers the enterprise Angular console; actions, reducers, and effects stay clearly split, and the store devtools replay made a gnarly rounding bug trivial to pin.", "architecture", "ai_coding", False,
     [("NgRx", "library"), ("Angular", "framework"), ("effects", "pattern")],
     [],
     "which Angular state library drives the enterprise console and how did devtools replay help debug",
     "ngrx angular console action reducer effect devtools replay debug"),
    # --- 16 ---
    ("Adopted the TanStack Query plus Redux combo: server cache lives in Query, view-only UI state stays in Redux Toolkit, and no slice tries to mirror fetched data any more.", "architecture", "ai_coding", False,
     [("TanStack Query", "library"), ("Redux Toolkit", "library"), ("server cache", "concept")],
     [],
     "how is server cache split from UI state now that TanStack Query sits next to Redux Toolkit",
     "tanstack query redux toolkit server cache ui state split mirror"),
    # --- 17 ---
    ("Stopped storing fetched lists inside Redux slices; the normalised data now lives in TanStack Query's cache and slices only hold selection, filters, and draft edits.", "problem", "ai_coding", False,
     [("Redux", "library"), ("TanStack Query", "library"), ("normalised", "pattern")],
     [("TanStack Query", "Redux", "REPLACES")],
     "which state layer now owns fetched lists and what does Redux still hold",
     "tanstack query cache fetch list redux slice selection filter"),
    # --- 18 ---
    ("The notifications slice is normalised by id with an ids array and a byId map; the old nested array had been forcing O(n) updates whenever one toast flipped its read flag.", "architecture", "ai_coding", False,
     [("notifications", "pattern"), ("byId", "pattern"), ("ids", "pattern")],
     [],
     "which store shape did the notifications slice adopt and what update cost did it fix",
     "normalised store byid ids array notification update complexity"),
    # --- 19 ---
    ("Optimistic UI on the like button mutates the Redux slice first, then rolls back inside the thunk's rejected handler if the server 4xx's; latency perception dropped sharply in field tests.", "architecture", "ai_coding", False,
     [("like button", "pattern"), ("thunk", "pattern"), ("Redux", "library")],
     [],
     "which optimistic-UI flow drives the like button and how does the rollback fire on server rejection",
     "optimistic ui like redux thunk rollback reject latency perception"),
    # --- 20 ---
    ("TanStack Query's onMutate handles the optimistic write on the comment composer; the rollback path uses the snapshot returned from setQueryData for a clean revert.", "fact", "ai_coding", False,
     [("TanStack Query", "library"), ("onMutate", "method"), ("setQueryData", "method")],
     [],
     "how does the comment composer do optimistic writes and clean rollbacks with TanStack Query",
     "tanstack query onmutate optimistic rollback setquerydata snapshot"),
    # --- 21 ---
    ("Undo/redo on the editor uses a command pattern stack: each mutation pushes a do/undo pair and the store exposes undo() and redo() as plain actions; time travel just walks the stack.", "architecture", "ai_coding", False,
     [("command pattern", "pattern"), ("undo", "method"), ("redo", "method"), ("editor", "project")],
     [],
     "how does the editor implement undo and redo without pulling in a whole history library",
     "undo redo command pattern stack mutation action editor time travel"),
    # --- 22 ---
    ("Replaced redux-undo with a hand-rolled command pattern stack; the library was re-computing diffs on every action and the per-key overhead was dominating the frame budget.", "problem", "ai_coding", False,
     [("redux-undo", "library"), ("command pattern", "pattern")],
     [("command pattern", "redux-undo", "REPLACES")],
     "why did we drop redux-undo and what did we swap in for history on the editor",
     "redux undo remove command stack diff overhead frame budget"),
    # --- 23 ---
    ("SSR state hydration now serialises the Redux store into a single script tag, then calls hydrateStore on the client before React mounts; mismatched trees stopped flickering.", "milestone", "ai_coding", False,
     [("SSR", "pattern"), ("Redux", "library"), ("hydrateStore", "method")],
     [],
     "which SSR hydration step stopped the mismatched-tree flicker and where does the initial state come from",
     "ssr hydrate redux store script tag hydrateStore mismatch flicker"),
    # --- 24 ---
    ("Next.js app-router pages rehydrate Zustand via a small <StoreProvider> client boundary; the server populates initial state on the props and the client create() seeds from it.", "architecture", "ai_coding", False,
     [("Next.js", "framework"), ("Zustand", "library"), ("StoreProvider", "pattern")],
     [],
     "how does the Next.js app-router page hand Zustand its initial server state",
     "next.js app router zustand hydrate storeprovider server initial"),
    # --- 25 ---
    ("zustand/persist now syncs the theme and sidebar slice to localStorage under a versioned key; a migrate() callback bumps v1 shapes forward instead of nuking preferences on deploy.", "architecture", "ai_coding", False,
     [("zustand/persist", "library"), ("localStorage", "api"), ("migrate", "method")],
     [],
     "which persistence layer syncs theme and sidebar to localStorage and how do shape changes survive a deploy",
     "zustand persist localStorage version migrate theme sidebar slice"),
    # --- 26 ---
    ("Replaced a raw localStorage JSON blob with idb-keyval for anything over a few kilobytes; quota errors on Safari private mode went away and writes no longer block the main thread.", "problem", "ai_coding", False,
     [("localStorage", "api"), ("idb-keyval", "library"), ("Safari", "platform")],
     [("idb-keyval", "localStorage", "REPLACES")],
     "why did bigger persisted state move from localStorage to idb-keyval and what browser bug went away",
     "idb keyval replace localstorage safari private quota async"),
    # --- 27 ---
    ("Dexie backs the offline queue store; pending mutations live in an IndexedDB table keyed by id and the reconciler drains them on reconnect using Dexie's transaction helpers.", "architecture", "ai_coding", False,
     [("Dexie", "library"), ("IndexedDB", "api"), ("offline queue", "pattern")],
     [("Dexie", "IndexedDB", "USES")],
     "which library wraps IndexedDB for the offline-queue store and how are drains ordered",
     "dexie indexeddb offline queue transaction drain reconcile mutation"),
    # --- 28 ---
    ("An event-sourcing flavour came to the form wizard: every field edit appends a typed event and the current view is a fold; undo is just dropping the last event, nothing clever.", "architecture", "ai_coding", False,
     [("event-sourcing", "pattern"), ("form wizard", "project"), ("fold", "pattern")],
     [],
     "how did the form wizard end up with an event-sourced state model and how cheap did undo become",
     "event sourcing form wizard fold append undo drop event frontend"),
    # --- 29 ---
    ("Redux's middleware chain is pinned to redux-thunk only; redux-saga was ripped out after one recursive generator ate the event loop and nobody could step through it in the debugger.", "decision", "ai_coding", False,
     [("redux-thunk", "library"), ("redux-saga", "library"), ("generator", "pattern")],
     [("redux-thunk", "redux-saga", "PREFERS")],
     "which Redux middleware did we keep and which one did a debugger incident get us to drop",
     "redux thunk saga remove generator recursive debugger debug drop"),
    # --- 30 ---
    ("createAsyncThunk wraps every API call in the auth slice; pending, fulfilled, and rejected cases update a uniform status enum that the UI reads for spinners and error banners.", "architecture", "ai_coding", False,
     [("createAsyncThunk", "method"), ("auth slice", "pattern"), ("status", "pattern")],
     [],
     "which Redux Toolkit helper wraps auth calls and how do the UI states derive from its lifecycle",
     "createasyncthunk auth slice pending fulfilled rejected status ui"),
    # --- 31 ---
    ("Reselect memoised selectors feed the heavy dashboard table; recomputing the grouped rows on every keystroke used to drop 12 fps but the memoised selector holds the output stable.", "problem", "ai_coding", False,
     [("Reselect", "library"), ("dashboard table", "project"), ("memoised selector", "pattern")],
     [],
     "which selector library stopped the dashboard table from recomputing grouped rows on every keystroke",
     "reselect memoise selector dashboard table keystroke recompute fps"),
    # --- 32 ---
    ("RTK Query replaced a bespoke fetch-plus-thunk layer in the billing module; caching, invalidation tags, and polling now come from the toolkit instead of hand-rolled reducers.", "decision", "ai_coding", False,
     [("RTK Query", "library"), ("billing module", "project"), ("thunk", "pattern")],
     [("RTK Query", "thunk", "REPLACES")],
     "which data-fetch layer took over from the thunk+fetch duo in the billing module",
     "rtk query replace thunk fetch billing cache invalidate poll tag"),
    # --- 33 ---
    ("Context selectors through use-context-selector cut render counts on the nav tree by half; plain useContext was forcing every consumer to rerender on unrelated changes.", "fact", "ai_coding", False,
     [("use-context-selector", "library"), ("useContext", "method"), ("nav tree", "project")],
     [("use-context-selector", "useContext", "IMPROVES_ON")],
     "which context hook library halved re-renders on the nav tree compared with useContext",
     "use context selector rerender nav tree useContext reduce consumer"),
    # --- 34 ---
    ("Chose a single Zustand slice with selectors over splitting into stores after profiling; shallow comparisons on selector outputs made the one-store approach cheaper than we expected.", "decision", "ai_coding", False,
     [("Zustand", "library"), ("selector", "pattern"), ("shallow", "method")],
     [],
     "why did we consolidate on one Zustand store and how do selectors keep renders tight",
     "zustand single store selector shallow compare render consolidate"),
    # --- 35 ---
    ("State hydration mismatch between server and client traced to Date objects round-tripping through JSON as strings; the fix was a serialise/deserialise pair with reviver on hydrate.", "problem", "ai_coding", False,
     [("Date", "concept"), ("JSON", "protocol"), ("reviver", "method")],
     [],
     "which serialisation mismatch caused the hydration warning and how did we land a safe round-trip",
     "hydrate mismatch date json reviver serialise deserialise round"),
    # --- 36 ---
    ("Preact signals carry the realtime tick counter; the rendering shell reads a .value inside a component and the dependency tracking wires up without any useEffect.", "fact", "ai_coding", False,
     [("Preact signals", "library"), ("tick counter", "pattern"), ("useEffect", "method")],
     [],
     "which signal primitive drives the realtime tick counter and how does it skip useEffect entirely",
     "preact signals value render tick counter useeffect dependency"),
    # --- 37 ---
    ("Documented the store-shape rules in docs/state.md: flat by id, dates as epoch ms, money as cents string; referenced on every PR that touches a reducer or selector.", "reference", "ai_coding", False,
     [("docs/state.md", "file"), ("reducer", "pattern"), ("selector", "pattern")],
     [],
     "which internal document pins the store-shape rules that PRs touching reducers have to cite",
     "state shape doc store flat id date epoch money cents reference"),
    # --- 38 ---
    ("Added devtools integration to every Zustand store with the devtools middleware; time-travel in Redux DevTools now works for non-Redux stores and dev onboarding sped up.", "milestone", "ai_coding", False,
     [("Zustand", "library"), ("Redux DevTools", "tool"), ("devtools", "pattern")],
     [("Zustand", "Redux DevTools", "USES")],
     "which middleware wires Zustand into Redux DevTools and what onboarding win did it unlock",
     "zustand devtools middleware redux devtools time travel onboard"),
    # --- 39 ---
    ("Immer drives immutable updates inside Redux Toolkit reducers; direct state.x = y in a slice reads like mutation but commits produce a new tree via the proxy.", "architecture", "ai_coding", False,
     [("Immer", "library"), ("Redux Toolkit", "library"), ("proxy", "pattern")],
     [],
     "which library lets Redux Toolkit reducers look mutable while producing immutable state",
     "immer redux toolkit reducer mutate proxy immutable draft commit"),
    # --- 40 ---
    ("Dropped Reselect for a native structuralSharing output in RTK Query 2; one less dependency and the cached result equality was already good enough for the table view.", "decision", "ai_coding", False,
     [("Reselect", "library"), ("RTK Query 2", "library"), ("structuralSharing", "method")],
     [("RTK Query 2", "Reselect", "REPLACES")],
     "which RTK Query feature let us drop reselect from the table view",
     "rtk query 2 structural sharing drop reselect table equality"),
    # --- 41 ---
    ("Ported the nested-boolean toast state to an XState machine with idle, visible, and dismissing states; the transient dismissing state holds focus for the CSS exit animation.", "architecture", "ai_coding", False,
     [("XState", "library"), ("toast", "pattern"), ("nested-boolean", "pattern"), ("dismissing", "pattern")],
     [("XState", "nested-boolean", "REPLACES")],
     "how did the toast component's booleans turn into an XState machine with an exit-animation hold",
     "xstate toast machine idle visible dismissing animation focus"),
    # --- 42 ---
    ("Recommended pattern: keep each Zustand slice a pure function of state and actions, and expose a selector file beside the store so components never import the hook with a shape argument.", "preference", "ai_coding", False,
     [("Zustand", "library"), ("selector", "pattern"), ("slice", "pattern")],
     [],
     "what is the codebase's preferred Zustand authoring split between store definition and selectors",
     "zustand slice selector file colocate hook shape argument import"),
    # --- 43 ---
    ("Cross-tab sync for the user preferences store uses the BroadcastChannel API; any setting change rebroadcasts and peer tabs merge via a last-write-wins timestamp.", "architecture", "ai_coding", False,
     [("BroadcastChannel", "api"), ("user preferences", "pattern"), ("last-write-wins", "pattern")],
     [],
     "which browser API propagates preferences across tabs and how are conflicts resolved",
     "broadcast channel cross tab preferences last write wins merge"),
    # --- 44 ---
    ("The optimistic toggle on the follow button was causing UI flicker until we added a short debounced confirm window; the confirm either commits the server-returned state or rolls back.", "problem", "ai_coding", False,
     [("follow button", "pattern"), ("debounce", "pattern"), ("optimistic", "pattern")],
     [],
     "which debounce change smoothed out the follow-button optimistic toggle from flickering",
     "optimistic toggle follow button debounce confirm flicker rollback"),
    # --- 45 ---
    ("Picked Jotai over Zustand for the drawing tool because atom families scaled cleaner to ten thousand shape atoms; Zustand's selector equality was fine but the split-state ergonomics won.", "decision", "ai_coding", False,
     [("Jotai", "library"), ("Zustand", "library"), ("drawing tool", "project"), ("atom families", "pattern")],
     [("Jotai", "Zustand", "PREFERS")],
     "why did the drawing tool choose Jotai over Zustand for ten-thousand-shape state",
     "jotai zustand drawing tool atom family scale split state compare"),
    # --- 46 ---
    ("Valtio's derive helper feeds the computed layout; mutating the source proxy triggers derived recomputation and subscribers run without us wiring any effects.", "fact", "ai_coding", False,
     [("Valtio", "library"), ("derive", "method"), ("layout", "pattern")],
     [],
     "which Valtio helper drives computed layout values and what effect wiring does it replace",
     "valtio derive proxy computed layout subscribe effect wire"),
    # --- 47 ---
    ("Effect-TS Ref cells replaced a bag of let-bound mutable variables inside the worker; concurrent updates now go through a single modify and races disappeared.", "problem", "ai_coding", False,
     [("Effect-TS", "library"), ("Ref", "concept"), ("worker", "service")],
     [("Effect-TS", "worker", "APPLIES_TO")],
     "which Effect-TS primitive replaced ad-hoc let-bound variables and killed races in the worker",
     "effect ts ref worker concurrent modify let bound race condition"),
    # --- 48 ---
    ("The global UI store rule: nothing that a URL param can encode lives in Redux; filters, sort, page, and drawer state live in the router instead so deep-linking and back-button behave.", "preference", "ai_coding", False,
     [("Redux", "library"), ("URL param", "concept"), ("router", "library")],
     [],
     "which global rule governs what stays out of Redux because the URL can carry it",
     "redux url param router filter sort page drawer deep link back"),
    # --- 49. noise ---
    ("The kettle on the third floor makes a different sound depending on how full it is that morning.", "fact", "noise", True, [], [], None, None),
    # --- 50 ---
    ("Migrated the legacy Flux dispatcher to Redux Toolkit; the imperative stores got rewritten as slices and the registered-callback soup collapsed into a single reducer graph.", "milestone", "ai_coding", False,
     [("Flux", "library"), ("Redux Toolkit", "library"), ("dispatcher", "pattern")],
     [("Redux Toolkit", "Flux", "REPLACES")],
     "which legacy dispatcher did the app retire in favour of Redux Toolkit slices",
     "flux dispatcher redux toolkit slice migration callback reducer"),
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
