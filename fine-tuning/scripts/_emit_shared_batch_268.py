"""One-off emitter for shared-base batch-268 — technical domain (browser engines and rendering internals: V8/SpiderMonkey/JSC tiers, Blink/WebKit/Gecko/Servo/Ladybird, parsing, style, layout, compositor, scheduler, modern web APIs).

Writes 50 rows to data/v2/shared/batch_268.tmp.jsonl with ids shared-13351..13400.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "shared" / "batch_268.tmp.jsonl"
ID_OFFSET = 13350

# (text, memory_type, domain, noise, entities, relationships, qq, qk)
ENTRIES: list[tuple] = [
    # --- 1 ---
    ("V8 added Maglev between Sparkplug and TurboFan so warm functions get a mid-tier optimising compiler without paying the full TurboFan compile cost up front.", "decision", "technical", False,
     [("V8", "technology"), ("Maglev", "tool"), ("Sparkplug", "tool"), ("TurboFan", "tool")],
     [("Maglev", "V8", "EXTENDS"), ("Maglev", "TurboFan", "IMPROVES_ON")],
     "where does Maglev slot in the V8 tier pipeline and what does it buy over jumping straight to TurboFan",
     "v8 maglev sparkplug turbofan tier compiler warm function cost"),
    # --- 2 ---
    ("TurboFan is being replaced internally by Turboshaft; the new IR makes optimisation passes easier to write and dropped the sea-of-nodes graph in favour of a block-based representation.", "decision", "technical", False,
     [("TurboFan", "tool"), ("Turboshaft", "tool"), ("sea-of-nodes", "pattern"), ("block-based", "pattern")],
     [("Turboshaft", "TurboFan", "REPLACES"), ("Turboshaft", "block-based", "USES")],
     "which V8 compiler IR is succeeding TurboFan and what graph representation did it move to",
     "turboshaft turbofan v8 ir sea of nodes block based replace"),
    # --- 3 ---
    ("Sparkplug is a baseline non-optimising compiler that emits machine code directly from the Ignition bytecode stream in a single linear pass without an IR.", "fact", "technical", False,
     [("Sparkplug", "tool"), ("Ignition", "tool"), ("bytecode", "concept")],
     [("Sparkplug", "Ignition", "DEPENDS_ON")],
     "how does Sparkplug generate code from V8 bytecode and why does it skip an intermediate representation",
     "sparkplug ignition bytecode baseline compiler single pass no ir"),
    # --- 4 ---
    ("Liftoff is V8's baseline Wasm compiler; it emits code in a single pass while TurboFan tier-ups in the background for hot functions identified by the execution counter.", "architecture", "technical", False,
     [("Liftoff", "tool"), ("V8", "technology"), ("Wasm", "technology"), ("TurboFan", "tool")],
     [("Liftoff", "Wasm", "APPLIES_TO"), ("TurboFan", "Liftoff", "IMPROVES_ON")],
     "which Wasm tiering pair does V8 use for startup versus sustained performance",
     "liftoff wasm v8 turbofan tier up baseline single pass hot function"),
    # --- 5 ---
    ("SpiderMonkey's Warp frontend replaced IonBuilder; it consumes CacheIR from the baseline inline caches to build the MIR graph for Ion, dropping a layer of type inference.", "decision", "technical", False,
     [("SpiderMonkey", "technology"), ("Warp", "tool"), ("IonBuilder", "tool"), ("CacheIR", "concept"), ("Ion", "tool")],
     [("Warp", "IonBuilder", "REPLACES"), ("Warp", "CacheIR", "USES")],
     "which SpiderMonkey component retired IonBuilder and where does it source its type information now",
     "warp ionbuilder spidermonkey cacheir ion mir type inference replace"),
    # --- 6 ---
    ("JavaScriptCore runs four tiers: LLInt interprets, Baseline JITs, DFG optimises on profiles, and FTL uses B3 to reach TurboFan-class output for the hottest functions.", "reference", "technical", False,
     [("JavaScriptCore", "technology"), ("LLInt", "tool"), ("Baseline", "tool"), ("DFG", "tool"), ("FTL", "tool"), ("B3", "tool")],
     [("FTL", "B3", "USES"), ("DFG", "Baseline", "IMPROVES_ON")],
     "which four execution tiers does JavaScriptCore chain and which backend does FTL rely on",
     "javascriptcore llint baseline dfg ftl b3 tier jit interpreter"),
    # --- 7 ---
    ("JSC added an OMG tier for Wasm so long-running Wasm functions get a second optimising pass beyond BBQ; startup stays fast because BBQ still handles the initial compile.", "architecture", "technical", False,
     [("JSC", "technology"), ("OMG", "tool"), ("BBQ", "tool"), ("Wasm", "technology")],
     [("OMG", "BBQ", "IMPROVES_ON"), ("OMG", "Wasm", "APPLIES_TO")],
     "which JSC Wasm tier runs after BBQ and what does BBQ give up in exchange for fast startup",
     "jsc omg bbq wasm tier optimise startup long running function"),
    # --- 8 ---
    ("Blink's HTMLTokenizer is a state-machine implementation of the WHATWG tokenisation spec; each state corresponds to a labelled case and character reference resolution happens lazily at consume time.", "reference", "technical", False,
     [("Blink", "technology"), ("HTMLTokenizer", "concept"), ("WHATWG", "organization")],
     [("HTMLTokenizer", "WHATWG", "IMPLEMENTS")],
     "how does Blink structure its HTML tokeniser and when does it resolve named character references",
     "blink html tokenizer whatwg state machine character reference lazy"),
    # --- 9 ---
    ("html5ever is Servo's HTML parser written in Rust; it is driven by a token sink trait so that consumers like Kuchiki or script::dom can reuse the same tokenisation core.", "fact", "technical", False,
     [("html5ever", "library"), ("Servo", "project"), ("Rust", "language"), ("Kuchiki", "library")],
     [("html5ever", "Servo", "DEPLOYED_ON"), ("Kuchiki", "html5ever", "USES")],
     "which Rust HTML parser does Servo use and what extension point lets other consumers reuse its tokeniser",
     "html5ever servo rust parser token sink kuchiki dom reuse"),
    # --- 10. noise ---
    ("The office kettle only boils if you press the button twice and someone taped a handwritten note about it to the wall.", "fact", "noise", True, [], [], None, None),
    # --- 11 ---
    ("CSS selector matching in Blink uses a RuleSet bucketed by rightmost simple selector plus a Bloom filter of ancestor ids and classes to reject non-matching chains cheaply.", "architecture", "technical", False,
     [("Blink", "technology"), ("RuleSet", "concept"), ("Bloom filter", "algorithm")],
     [("RuleSet", "Bloom filter", "USES")],
     "how does Blink narrow CSS selector matching before walking the full selector chain",
     "css selector ruleset bloom filter blink ancestor match reject"),
    # --- 12 ---
    ("Style invalidation in Blink moved from recalc-the-subtree to a targeted InvalidationSet keyed by class, id, and attribute; only the affected descendants get their computed style rebuilt.", "milestone", "technical", False,
     [("Style invalidation", "concept"), ("Blink", "technology"), ("InvalidationSet", "concept")],
     [("InvalidationSet", "Style invalidation", "IMPROVES_ON")],
     "which invalidation mechanism replaced full subtree recalc for CSS style updates in Blink",
     "style invalidation invalidationset blink subtree recalc class id"),
    # --- 13 ---
    ("LayoutNG replaced the legacy LayoutObject block-flow path in Blink; the new algorithm is fragment-based so multicol, tables, and flex share a single constraint-space API.", "milestone", "technical", False,
     [("LayoutNG", "tool"), ("LayoutObject", "concept"), ("Blink", "technology"), ("constraint-space", "api")],
     [("LayoutNG", "LayoutObject", "REPLACES"), ("LayoutNG", "constraint-space", "USES")],
     "which Blink layout rewrite retired the legacy LayoutObject flow and what unified API does it expose",
     "layoutng layoutobject blink fragment constraint space multicol table"),
    # --- 14 ---
    ("Blink runs a compositor thread separate from main so scrolling, transforms, and opacity animations can proceed even when JavaScript stalls the main thread for tens of milliseconds.", "architecture", "technical", False,
     [("Blink", "technology"), ("compositor thread", "concept"), ("main thread", "concept")],
     [("compositor thread", "main thread", "RELATED_TO")],
     "which Blink thread keeps scroll and transform animations smooth when the main thread is blocked",
     "compositor thread blink main thread scroll transform opacity stall"),
    # --- 15 ---
    ("Chromium's GPU process isolates driver crashes and GPU memory from the browser and renderer processes; a crash merely flips to software rasterisation while tabs stay alive.", "architecture", "technical", False,
     [("Chromium", "project"), ("GPU process", "concept"), ("renderer process", "concept"), ("software rasterisation", "concept")],
     [("GPU process", "renderer process", "COMMUNICATES_WITH")],
     "why does Chromium run GPU work in its own process and what happens when the driver crashes",
     "chromium gpu process renderer isolate driver crash software raster"),
    # --- 16 ---
    ("The TaskQueue scheduler in Blink prioritises input and compositor work over timer callbacks; a frozen or background tab drops to a per-minute budget so inactive pages cannot hog CPU.", "architecture", "technical", False,
     [("TaskQueue", "concept"), ("Blink", "technology"), ("compositor", "concept"), ("timer", "concept")],
     [("TaskQueue", "compositor", "PREFERS")],
     "how does Blink's task scheduler keep input responsive and what does it do with background tabs",
     "task queue scheduler blink compositor input priority background"),
    # --- 17 ---
    ("IntersectionObserver replaced scroll-event-plus-getBoundingClientRect for viewport visibility checks; the observer fires asynchronously and avoids forcing a synchronous layout per scroll.", "decision", "technical", False,
     [("IntersectionObserver", "api"), ("getBoundingClientRect", "api"), ("scroll-event", "concept")],
     [("IntersectionObserver", "getBoundingClientRect", "REPLACES")],
     "which browser API retired the scroll-plus-getBoundingClientRect pattern for visibility detection",
     "intersection observer scroll boundingclientrect viewport async layout"),
    # --- 18 ---
    ("ResizeObserver delivers content-box or border-box size changes without a polling loop; it batches on a dedicated queue between layout and paint so observer callbacks see post-layout sizes.", "fact", "technical", False,
     [("ResizeObserver", "api"), ("content-box", "concept"), ("border-box", "concept"), ("layout", "concept"), ("paint", "concept")],
     [("ResizeObserver", "layout", "DEPENDS_ON")],
     "when in the frame lifecycle does ResizeObserver fire and which box sizes does it expose",
     "resize observer content box border layout paint batch queue"),
    # --- 19 ---
    ("MutationObserver replaced the deprecated DOM Mutation Events; callbacks fire as a microtask batch at the end of the current task instead of interrupting DOM mutation synchronously.", "decision", "technical", False,
     [("MutationObserver", "api"), ("DOM Mutation Events", "api"), ("microtask", "concept")],
     [("MutationObserver", "DOM Mutation Events", "REPLACES"), ("MutationObserver", "microtask", "USES")],
     "which DOM observation API retired Mutation Events and when do its callbacks actually run",
     "mutation observer dom mutation events microtask batch deprecated"),
    # --- 20 ---
    ("Priority Hints exposes fetchpriority on img, link, and script so developers can bias the browser's network queue without relying on resource preload hacks or document order tricks.", "decision", "technical", False,
     [("Priority Hints", "api"), ("fetchpriority", "api"), ("preload", "api")],
     [("Priority Hints", "preload", "REPLACES")],
     "which attribute does Priority Hints add and which older preload tricks does it make unnecessary",
     "priority hints fetchpriority preload img link script network queue"),
    # --- 21 ---
    ("View Transitions API captures the pre-change DOM as a snapshot and animates to the post-change state via generated pseudo-elements, no manual FLIP measurement code required.", "fact", "technical", False,
     [("View Transitions API", "api"), ("FLIP", "pattern"), ("pseudo-elements", "concept")],
     [("View Transitions API", "FLIP", "REPLACES")],
     "which browser API removes the need for hand-written FLIP animations between DOM states",
     "view transitions api flip pseudo element snapshot dom animate"),
    # --- 22 ---
    ("Back/forward cache keeps frozen page state in memory across a navigation so a history traversal restores instantly; eligibility is blocked by Cache-Control: no-store, unload handlers, and open IndexedDB transactions.", "architecture", "technical", False,
     [("Back/forward cache", "concept"), ("IndexedDB", "technology"), ("unload handler", "api")],
     [("Back/forward cache", "unload handler", "RELATED_TO")],
     "what does back/forward cache preserve across navigations and which page features disqualify it",
     "bfcache back forward cache no store unload indexeddb frozen navigate"),
    # --- 23 ---
    ("Prerender2 replaced the earlier NoStatePrefetch path in Chromium; the prerendered page runs scripts in a hidden state and activates atomically on navigation instead of throwing the prerender away.", "milestone", "technical", False,
     [("Prerender2", "concept"), ("NoStatePrefetch", "concept"), ("Chromium", "project")],
     [("Prerender2", "NoStatePrefetch", "REPLACES")],
     "which Chromium prerender mechanism succeeded NoStatePrefetch and how does it activate on navigation",
     "prerender2 nostateprefetch chromium hidden activate atomic navigate"),
    # --- 24 ---
    ("Speculation Rules lets a page declare JSON rules for prefetch or prerender of same-origin URLs; the browser treats the rules as hints and may ignore them on slow networks or save-data.", "decision", "technical", False,
     [("Speculation Rules", "api"), ("prefetch", "concept"), ("prerender", "concept"), ("JSON", "technology")],
     [("Speculation Rules", "prerender", "CONFIGURES")],
     "how do Speculation Rules declare prefetch and prerender intents and under what conditions are they ignored",
     "speculation rules json prefetch prerender hint save data slow"),
    # --- 25 ---
    ("Service Worker cache is a named storage of Request and Response pairs addressed by URL plus Vary headers; matching is content-aware so the same URL with different Accept can store multiple entries.", "reference", "technical", False,
     [("Service Worker", "technology"), ("Request", "api"), ("Response", "api"), ("Vary", "api")],
     [("Service Worker", "Vary", "USES")],
     "how does the Service Worker cache key entries and why can one URL hold multiple responses",
     "service worker cache request response vary accept key match"),
    # --- 26 ---
    ("Origin Private File System is a sandboxed per-origin filesystem exposed via the File System Access API; writes go to a private directory unreachable by user file pickers.", "fact", "technical", False,
     [("Origin Private File System", "api"), ("File System Access API", "api")],
     [("Origin Private File System", "File System Access API", "EXTENDS")],
     "which web storage surface gives each origin a private filesystem hidden from user file pickers",
     "opfs origin private file system sandbox per origin picker hidden"),
    # --- 27 ---
    ("WebCodecs exposes VideoEncoder, VideoDecoder, AudioEncoder and AudioDecoder backed by the same hardware codecs the media element uses; applications get raw frame access without ffmpeg.wasm.", "architecture", "technical", False,
     [("WebCodecs", "api"), ("VideoEncoder", "api"), ("VideoDecoder", "api"), ("ffmpeg.wasm", "library")],
     [("WebCodecs", "ffmpeg.wasm", "REPLACES")],
     "which web API gives hardware codec access in JavaScript and what userland library does it obsolete",
     "webcodecs video encoder decoder hardware ffmpeg wasm codec frame"),
    # --- 28 ---
    ("WebGPU shipped as the successor to WebGL; the API surface is modelled on modern low-level GPU APIs so pipelines, bind groups, and command encoders map almost directly to Vulkan and Metal.", "milestone", "technical", False,
     [("WebGPU", "api"), ("WebGL", "api"), ("Vulkan", "api"), ("Metal", "api")],
     [("WebGPU", "WebGL", "REPLACES"), ("WebGPU", "Vulkan", "RELATED_TO")],
     "which web graphics API replaced WebGL and which native APIs does its abstraction mirror",
     "webgpu webgl vulkan metal pipeline bind group command encoder"),
    # --- 29 ---
    ("WebNN gives the browser a portable neural network API that delegates to platform accelerators like CoreML, DirectML, or XNNPACK; models run on-device without shipping a custom runtime per site.", "milestone", "technical", False,
     [("WebNN", "api"), ("CoreML", "framework"), ("DirectML", "framework"), ("XNNPACK", "library")],
     [("WebNN", "CoreML", "USES"), ("WebNN", "DirectML", "USES")],
     "which browser API abstracts on-device neural inference and which platform backends does it sit on top of",
     "webnn coreml directml xnnpack accelerator on device neural"),
    # --- 30 ---
    ("Servo's layout engine is being rewritten around Fragment trees in Rust, matching the LayoutNG fragment model in Blink so that multi-column and flex flows share a common abstraction.", "decision", "technical", False,
     [("Servo", "project"), ("Fragment trees", "concept"), ("Rust", "language"), ("LayoutNG", "tool"), ("Blink", "technology")],
     [("Servo", "Fragment trees", "USES"), ("Servo", "LayoutNG", "BUILDS_ON")],
     "which Blink abstraction is Servo's layout rewrite mirroring and what unit organises the new flow",
     "servo fragment tree rust layoutng blink multicol flex abstraction"),
    # --- 31 ---
    ("Ladybird is an independent browser engine spun out of SerenityOS; the team is rewriting the networking stack and JavaScript engine in pursuit of a third independent implementation of the web.", "milestone", "technical", False,
     [("Ladybird", "project"), ("SerenityOS", "project")],
     [("Ladybird", "SerenityOS", "BUILDS_ON")],
     "which independent browser engine came out of SerenityOS and what is its strategic rationale",
     "ladybird serenityos independent browser engine third implementation"),
    # --- 32 ---
    ("Gecko's Stylo engine replaced the old C++ style system with a Rust crate sharing code with Servo; parallel style recalc on multi-core became viable because the Rust code is data-race free.", "milestone", "technical", False,
     [("Gecko", "technology"), ("Stylo", "tool"), ("Rust", "language"), ("Servo", "project")],
     [("Stylo", "Gecko", "EXTENDS"), ("Stylo", "Servo", "BUILDS_ON")],
     "which Gecko component was replaced by a Rust crate shared with Servo and what parallelism did it unlock",
     "stylo gecko rust servo parallel style recalc data race"),
    # --- 33 ---
    ("WebKit keeps an LayerTree representation separate from the RenderTree; compositing decisions happen after layout and hand the result to CoreAnimation on macOS or the TextureMapper on Linux.", "reference", "technical", False,
     [("WebKit", "technology"), ("LayerTree", "concept"), ("RenderTree", "concept"), ("CoreAnimation", "framework"), ("TextureMapper", "tool")],
     [("WebKit", "CoreAnimation", "USES")],
     "how does WebKit split layout from compositing and which platform backends consume the layer tree",
     "webkit layer tree render tree coreanimation texturemapper composite"),
    # --- 34 ---
    ("Chromium's renderer-to-browser IPC moved from legacy Chromium IPC to Mojo; Mojo's message pipes and structured data let process boundaries use typed interfaces instead of serialised tag dispatch.", "decision", "technical", False,
     [("Chromium", "project"), ("Mojo", "framework"), ("IPC", "concept")],
     [("Mojo", "IPC", "REPLACES"), ("Chromium", "Mojo", "USES")],
     "which IPC framework replaced legacy Chromium IPC and what typing benefit did Mojo bring",
     "mojo chromium ipc message pipe typed interface legacy replace"),
    # --- 35 ---
    ("Same-origin checks consider scheme, host, and port as a triple; a script on https cannot read a document on http even for the same host because the scheme mismatch breaks the triple.", "reference", "technical", False,
     [("Same-origin", "concept"), ("scheme", "concept"), ("host", "concept"), ("port", "concept"), ("https", "protocol"), ("http", "protocol")],
     [("Same-origin", "scheme", "HAS_PART")],
     "which three pieces make up a web origin and why does an https page see http as a different origin",
     "same origin scheme host port triple https http cross boundary"),
    # --- 36 ---
    ("CORS preflight fires an OPTIONS request when the browser sees a non-simple header, a non-standard method, or credentials with a wildcard Access-Control-Allow-Origin policy.", "fact", "technical", False,
     [("CORS", "protocol"), ("OPTIONS", "method"), ("Access-Control-Allow-Origin", "api")],
     [("CORS", "OPTIONS", "USES")],
     "under what conditions does the browser emit a CORS preflight OPTIONS before the real request",
     "cors preflight options non simple header method credentials wildcard"),
    # --- 37 ---
    ("Blink invalidates the HTML parser's speculative-prefetch work when a streaming script inserts characters mid-parse; this is why injecting markup with document-writing APIs from third-party scripts wrecks load performance.", "problem", "technical", False,
     [("Blink", "technology"), ("HTML parser", "concept"), ("speculative-prefetch", "concept")],
     [("Blink", "speculative-prefetch", "USES")],
     "why does third-party script-driven markup injection wreck Blink's preload scanner and load speed",
     "blink html parser streaming script speculative prefetch preload third"),
    # --- 38 ---
    ("JavaScript module loading in browsers uses a worklet-like graph fetcher: each import URL is fetched once per realm, and cycles resolve to the partially-initialised module record rather than deadlocking.", "reference", "technical", False,
     [("JavaScript", "language"), ("module record", "concept"), ("realm", "concept")],
     [],
     "how does the browser's ES module loader handle import cycles without deadlocking or re-fetching",
     "javascript module loader import realm cycle partially initialised"),
    # --- 39 ---
    ("Chromium's Site Isolation process-per-site-instance model assigns each cross-site iframe its own renderer process so Spectre-class attacks cannot read cross-origin memory in the same address space.", "architecture", "technical", False,
     [("Chromium", "project"), ("Site Isolation", "concept"), ("renderer process", "concept"), ("Spectre", "concept")],
     [("Site Isolation", "Spectre", "FIXES")],
     "which Chromium process model isolates cross-site iframes and which attack class motivated it",
     "site isolation chromium spectre iframe renderer process cross site"),
    # --- 40 ---
    ("Chrome profiled style recalc on e-commerce pages and found the majority of time in descendant invalidation from class changes on body; class-level InvalidationSet shrank this to a small subtree.", "problem", "technical", False,
     [("Chrome", "technology"), ("style recalc", "concept"), ("InvalidationSet", "concept"), ("body", "concept")],
     [("InvalidationSet", "style recalc", "IMPROVES_ON")],
     "which profiling finding about body-class changes drove adoption of class-level InvalidationSet in Chrome",
     "chrome style recalc body class invalidationset descendant subtree"),
    # --- 41 ---
    ("requestAnimationFrame callbacks run between style and layout in the Blink frame pipeline; reading layout-dependent properties inside rAF forces a synchronous style-and-layout flush before the paint.", "fact", "technical", False,
     [("requestAnimationFrame", "api"), ("Blink", "technology"), ("style", "concept"), ("layout", "concept")],
     [("requestAnimationFrame", "layout", "RELATED_TO")],
     "where does requestAnimationFrame sit in Blink's frame pipeline and what does layout-reading inside it force",
     "requestanimationframe raf blink style layout paint frame pipeline"),
    # --- 42 ---
    ("The Chromium team prefers origin trials over flag-gated rollouts for new web APIs; origin trials give per-origin opt-in with automatic expiry so deprecation does not rely on dev console warnings alone.", "preference", "technical", False,
     [("Chromium", "project"), ("origin trials", "concept"), ("flag-gated", "pattern")],
     [("origin trials", "flag-gated", "PREFERS")],
     "why does the Chromium team prefer origin trials over flag-gated rollouts for new web APIs",
     "origin trials chromium flag rollout api opt in expiry deprecation"),
    # --- 43. noise ---
    ("The hallway clock between the fourth and fifth floor is always exactly seven minutes fast and nobody will own the fix.", "fact", "noise", True, [], [], None, None),
    # --- 44 ---
    ("Safari prefers a single-process-per-tab model that defers site isolation decisions until a navigation commits, which keeps memory use lower than Chromium at the cost of coarser cross-origin separation.", "preference", "technical", False,
     [("Safari", "technology"), ("Chromium", "project"), ("site isolation", "concept")],
     [("Safari", "Chromium", "CONTRADICTS")],
     "how does Safari's process model differ from Chromium's site isolation and what is the trade-off",
     "safari chromium single process tab site isolation memory trade"),
    # --- 45 ---
    ("The Firefox team ported the style system first to Rust through Stylo before attempting the layout port, because style recalc had the clearest data-parallel shape and the smallest API surface into the DOM.", "decision", "technical", False,
     [("Firefox", "technology"), ("Stylo", "tool"), ("Rust", "language"), ("DOM", "concept")],
     [("Stylo", "DOM", "DEPENDS_ON")],
     "why did Firefox port style to Rust before tackling layout and what property made style a good first target",
     "firefox stylo rust layout style recalc data parallel dom port"),
    # --- 46 ---
    ("Blink teams prefer shipping features behind a RuntimeEnabledFeatures flag with a staged rollout through Finch rather than compile-time gates, so rollback is a server-side config flip.", "preference", "technical", False,
     [("Blink", "technology"), ("RuntimeEnabledFeatures", "config"), ("Finch", "tool")],
     [("Blink", "RuntimeEnabledFeatures", "USES"), ("Blink", "Finch", "USES")],
     "which rollout mechanism do Blink teams prefer for feature flags so rollback stays server-side",
     "blink runtime enabled features finch rollout flag config rollback"),
    # --- 47 ---
    ("Memory pressure on mobile browsers triggered a preference for byte-addressable bytecode caches over source caches; Chrome stores the V8 bytecode next to the source in the HTTP cache for repeat visits.", "preference", "technical", False,
     [("Chrome", "technology"), ("V8", "technology"), ("bytecode cache", "concept"), ("HTTP cache", "concept")],
     [("Chrome", "bytecode cache", "PREFERS")],
     "which caching strategy does Chrome prefer for V8 bytecode on repeat visits and what drove the choice",
     "chrome v8 bytecode cache http mobile memory repeat visit source"),
    # --- 48 ---
    ("A long-standing problem in WebKit was that nested CSS containment breaks when a container query target is inside a composited layer; a layer-boundary invalidation pass had to be added to keep queries consistent.", "problem", "technical", False,
     [("WebKit", "technology"), ("CSS containment", "concept"), ("container query", "api"), ("composited layer", "concept")],
     [("WebKit", "container query", "FIXES")],
     "which WebKit interaction between container queries and composited layers forced a dedicated invalidation pass",
     "webkit css containment container query composited layer invalidation"),
    # --- 49 ---
    ("SpiderMonkey's Baseline Wasm tier mirrors Liftoff in V8: single-pass machine code generation with no IR so startup is fast, then Ion tiers up the hot functions after profiling.", "decision", "technical", False,
     [("SpiderMonkey", "technology"), ("Baseline", "tool"), ("Wasm", "technology"), ("Liftoff", "tool"), ("V8", "technology"), ("Ion", "tool")],
     [("Baseline", "Liftoff", "IS_A"), ("Ion", "Baseline", "IMPROVES_ON")],
     "how does SpiderMonkey's Wasm Baseline tier mirror Liftoff and where does Ion fit in tiering",
     "spidermonkey baseline wasm liftoff v8 ion tier startup profile"),
    # --- 50 ---
    ("Chromium moved the renderer's main thread scheduler to a priority-based TaskQueue with explicit categories; input and compositor tasks preempt microtask drains so scroll-driven animations stay jank-free under JS load.", "decision", "technical", False,
     [("Chromium", "project"), ("TaskQueue", "concept"), ("microtask", "concept"), ("compositor", "concept")],
     [("TaskQueue", "microtask", "PREFERS")],
     "which scheduler change in Chromium keeps scroll animations jank-free when JavaScript floods the microtask queue",
     "chromium task queue scheduler microtask compositor input priority jank"),
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
