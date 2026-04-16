"""One-off emitter for shared-base batch-180 — technical domain (compiler design and toolchains: LLVM, Clang, MLIR, GCC, linkers, JITs, sanitizers, PGO, LTO, BOLT, vectorisation, register allocation, SSA).

Writes 50 rows to data/v2/shared/batch_180.tmp.jsonl with ids shared-08951..09000.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "shared" / "batch_180.tmp.jsonl"
ID_OFFSET = 8950

# (text, memory_type, domain, noise, entities, relationships, qq, qk)
ENTRIES: list[tuple] = [
    # --- 1 decision ---
    ("Switched the C++ toolchain from GCC to Clang for the release build; the LLVM diagnostic output and better ThinLTO throughput on our 32-core box tipped the decision.", "decision", "technical", False,
     [("GCC", "tool"), ("Clang", "tool"), ("LLVM", "framework"), ("ThinLTO", "method")],
     [("Clang", "GCC", "REPLACES"), ("Clang", "LLVM", "USES")],
     "which C++ compiler replaced GCC for the release build and what LLVM feature sealed it",
     "clang gcc llvm thinlto release toolchain diagnostic throughput"),
    # --- 2 decision ---
    ("Replaced ld.gold with mold in the link step; a cold full link of the server binary dropped from 42 seconds to under 6, and mold handles our DWARF-heavy debug output without choking.", "decision", "technical", False,
     [("ld.gold", "tool"), ("mold", "tool"), ("DWARF", "protocol")],
     [("mold", "ld.gold", "REPLACES")],
     "which linker replaced ld.gold for the server link and what speedup did the cold link see",
     "mold gold linker cold link dwarf debug server binary speed"),
    # --- 3 architecture ---
    ("The custom DSL lowers through MLIR dialects: a high-level tensor dialect canonicalises, converts into linalg, then into LLVM IR, which Clang drives for codegen on the same backend.", "architecture", "technical", False,
     [("MLIR", "framework"), ("linalg", "library"), ("LLVM IR", "language"), ("Clang", "tool")],
     [("MLIR", "LLVM IR", "PRODUCES"), ("Clang", "LLVM IR", "USES")],
     "how does the DSL pipeline lower through MLIR dialects before hitting LLVM codegen",
     "mlir dialect linalg llvm ir clang lower tensor dsl pipeline"),
    # --- 4 reference ---
    ("Larsen and Amarasinghe's superword-level parallelism paper is the origin of LLVM's SLPVectorize pass; we cite it whenever reviewers ask why SLP chose a greedy packing strategy over an ILP solver.", "reference", "technical", False,
     [("Larsen", "person"), ("Amarasinghe", "person"), ("SLPVectorize", "method"), ("LLVM", "framework")],
     [("SLPVectorize", "LLVM", "USES")],
     "which superword-level parallelism paper originates LLVM's SLPVectorize and its greedy packing",
     "larsen amarasinghe slp superword vectorize llvm greedy packing"),
    # --- 5 decision ---
    ("Enabled full LTO on the hot path of the database kernel and ThinLTO on the rest of the tree; full LTO won another four percent on TPC-H but blew link RAM past 90 GB on the whole repo.", "decision", "technical", False,
     [("full LTO", "method"), ("ThinLTO", "method"), ("TPC-H", "concept")],
     [("full LTO", "ThinLTO", "IMPROVES_ON")],
     "how is LTO split between hot path and rest of tree and what memory cost forced the mix",
     "full lto thinlto database kernel tpc h link memory split"),
    # --- 6 milestone ---
    ("BOLT post-link optimisation landed for the query engine binary: instruction-cache misses dropped 31 percent on the production trace and tail latency at p99 improved by nine percent.", "milestone", "technical", False,
     [("BOLT", "tool"), ("query engine", "service")],
     [("BOLT", "query engine", "APPLIES_TO")],
     "which post-link tool landed on the query engine and what cache miss improvement did it produce",
     "bolt post link query engine icache miss tail latency p99"),
    # --- 7 reference ---
    ("The classic linear-scan register allocation paper by Poletto and Sarkar is still the baseline we cite when explaining why the JIT picked linear scan over graph colouring for compile-time reasons.", "reference", "technical", False,
     [("linear-scan", "algorithm"), ("graph colouring", "algorithm"), ("Poletto", "person"), ("Sarkar", "person")],
     [("linear-scan", "graph colouring", "IMPROVES_ON")],
     "which register allocation paper anchors the JIT's choice of linear scan over graph colouring",
     "linear scan graph colouring register allocation poletto sarkar jit"),
    # --- 8 problem ---
    ("AddressSanitizer caught a heap-use-after-free in the plan cache that only reproduced on the release build once LTO inlined the destructor across translation units and the shadow map lit up.", "problem", "technical", False,
     [("AddressSanitizer", "tool"), ("LTO", "method"), ("plan cache", "service")],
     [("AddressSanitizer", "plan cache", "APPLIES_TO")],
     "which sanitiser caught the heap-use-after-free in the plan cache and which optimisation unmasked it",
     "address sanitizer asan lto inline plan cache use after free"),
    # --- 9 architecture ---
    ("V8 pipelines new JavaScript through Sparkplug for cheap baseline code, Maglev for a mid-tier SSA optimiser, and Turboshaft for the top tier; the old Crankshaft path is long gone from the tree.", "architecture", "technical", False,
     [("V8", "framework"), ("Sparkplug", "tool"), ("Maglev", "tool"), ("Turboshaft", "tool"), ("Crankshaft", "tool")],
     [("Turboshaft", "Crankshaft", "REPLACES"), ("V8", "Sparkplug", "USES"), ("V8", "Maglev", "USES")],
     "how does V8 tier its JavaScript compilation through Sparkplug, Maglev, and Turboshaft",
     "v8 sparkplug maglev turboshaft crankshaft tier javascript jit"),
    # --- 10 noise ---
    ("The office espresso machine has started reporting its water level in metric tons for reasons no one in facilities has been able to explain.", "fact", "noise", True, [], [], None, None),
    # --- 11 decision ---
    ("Picked Cranelift over LLVM for the Wasm runtime's baseline tier; compile time is an order of magnitude faster and we tolerate the 15 percent codegen gap for cold functions.", "decision", "technical", False,
     [("Cranelift", "framework"), ("LLVM", "framework"), ("Wasm", "technology")],
     [("Cranelift", "LLVM", "PREFERS")],
     "which backend did the Wasm runtime pick for the baseline tier and what trade-off justified it",
     "cranelift llvm wasm baseline tier compile time codegen gap"),
    # --- 12 fact ---
    ("HotSpot's C1 emits straightforward code quickly while C2 runs the expensive SSA-based optimiser after the method passes the invocation threshold; tiered compilation plumbs both together.", "fact", "technical", False,
     [("HotSpot", "framework"), ("C1", "tool"), ("C2", "tool"), ("tiered compilation", "concept")],
     [("HotSpot", "C1", "USES"), ("HotSpot", "C2", "USES")],
     "how does HotSpot combine C1 and C2 through tiered compilation after the invocation threshold",
     "hotspot c1 c2 tiered compilation jvm ssa invocation threshold"),
    # --- 13 reference ---
    ("Futamura's partial-evaluation projections are the theoretical basis GraalVM's Truffle cites when specialising guest-language ASTs into Graal IR; the first projection matches Truffle's compile step exactly.", "reference", "technical", False,
     [("Futamura", "person"), ("GraalVM", "framework"), ("Truffle", "library"), ("Graal IR", "language"), ("partial-evaluation", "method")],
     [("Truffle", "partial-evaluation", "USES"), ("GraalVM", "Truffle", "USES")],
     "which Futamura result underpins the way Truffle specialises guest-language ASTs into Graal IR",
     "futamura partial evaluation projection graalvm truffle graal ir"),
    # --- 14 decision ---
    ("The .NET side standardised on RyuJIT with tiered compilation and ReadyToRun AOT images for the startup path; quickjit warm-up latency on cold services was the deciding factor.", "decision", "technical", False,
     [("RyuJIT", "tool"), ("ReadyToRun", "method"), (".NET", "framework"), ("tiered compilation", "concept")],
     [(".NET", "RyuJIT", "USES"), (".NET", "ReadyToRun", "USES")],
     "how did .NET split its codegen between RyuJIT tiered compilation and ReadyToRun AOT images",
     "ryujit readytorun dotnet tiered compilation aot startup quickjit"),
    # --- 15 problem ---
    ("ThreadSanitizer flagged a data race in the lock-free ring buffer where a relaxed load on the head pointer raced with the release store on the tail; memory_order_acquire on the load fixed it.", "problem", "technical", False,
     [("ThreadSanitizer", "tool"), ("memory_order_acquire", "api"), ("ring buffer", "pattern")],
     [("memory_order_acquire", "ThreadSanitizer", "FIXES")],
     "which sanitiser caught the ring-buffer data race and which memory order silenced the report",
     "thread sanitizer tsan ring buffer memory order acquire race"),
    # --- 16 milestone ---
    ("Two-pass PGO rolled out on the analytics binary: instrumented canary collected profdata for seven days, optimised build landed on 2026-01-18, and branch-probability reshaping cut cold-path CPU by 14 percent.", "milestone", "technical", False,
     [("PGO", "method"), ("profdata", "file"), ("analytics binary", "service"), ("2026-01-18", "date")],
     [("PGO", "profdata", "PRODUCES"), ("PGO", "analytics binary", "APPLIES_TO")],
     "when did two-pass PGO land on the analytics binary and what cold-path CPU win did it record",
     "pgo profdata analytics canary seven day cold path cpu 14"),
    # --- 17 milestone ---
    ("Propeller shipped alongside BOLT for the search-indexer binary; function-section reordering driven by a perf profile cut icache misses another 8 percent on top of the BOLT baseline.", "milestone", "technical", False,
     [("Propeller", "tool"), ("BOLT", "tool"), ("search-indexer", "service")],
     [("Propeller", "BOLT", "EXTENDS"), ("Propeller", "search-indexer", "APPLIES_TO")],
     "which layout tool landed on top of BOLT for the search indexer and what icache win did it add",
     "propeller bolt search indexer function section icache reorder"),
    # --- 18 decision ---
    ("Dropped the ICC build target; the Intel oneAPI DPC++ toolchain took over for the SYCL offload path and GCC covers the plain x86_64 host build, which simplified the CI matrix considerably.", "decision", "technical", False,
     [("ICC", "tool"), ("Intel oneAPI DPC++", "tool"), ("GCC", "tool"), ("SYCL", "framework")],
     [("Intel oneAPI DPC++", "ICC", "REPLACES"), ("Intel oneAPI DPC++", "SYCL", "USES")],
     "which Intel compiler replaced ICC and how is the SYCL offload path now compiled",
     "icc intel oneapi dpcpp sycl offload gcc x86 ci matrix"),
    # --- 19 fact ---
    ("zig cc bundles a cross-compiling Clang with libc headers for every common target; a single invocation produces a musl-linked Linux binary from a macOS dev box with no separate sysroot.", "fact", "technical", False,
     [("zig cc", "tool"), ("Clang", "tool"), ("musl", "library"), ("macOS", "platform")],
     [("zig cc", "Clang", "USES"), ("zig cc", "musl", "SUPPORTS")],
     "how does zig cc cross-compile to a musl Linux target from macOS without a separate sysroot",
     "zig cc clang musl macos cross compile sysroot libc header"),
    # --- 20 preference ---
    ("I prefer ld.lld over gold when the toolchain is already Clang; it keeps the pipeline single-vendor, emits straighter diagnostics, and supports our ThinLTO cache directory out of the box.", "preference", "technical", False,
     [("ld.lld", "tool"), ("gold", "tool"), ("Clang", "tool"), ("ThinLTO", "method")],
     [("ld.lld", "gold", "PREFERS"), ("ld.lld", "ThinLTO", "SUPPORTS")],
     "which linker is preferred when the toolchain is already Clang and which feature seals it",
     "lld gold clang thinlto cache linker single vendor diagnostic"),
    # --- 21 architecture ---
    ("The JIT's register allocator runs a linear-scan pass over the SSA form with live-range splitting at loop boundaries; spills go to a dedicated stack slot pool and coalesce on the way out.", "architecture", "technical", False,
     [("linear-scan", "algorithm"), ("SSA", "concept"), ("live-range splitting", "method"), ("spill", "pattern")],
     [("linear-scan", "SSA", "APPLIES_TO")],
     "how does the JIT's register allocator handle SSA live ranges across loops with spill coalescing",
     "linear scan ssa live range split loop spill coalesce jit"),
    # --- 22 reference ---
    ("Cytron et al's dominator-frontier algorithm underpins the SSA construction pass; every phi placement in the IR goes back to that 1991 paper even though we rewrote the implementation three times.", "reference", "technical", False,
     [("Cytron", "person"), ("dominator-frontier", "algorithm"), ("SSA", "concept"), ("phi", "concept")],
     [("SSA", "dominator-frontier", "USES")],
     "which algorithm from Cytron and colleagues anchors phi placement during SSA construction",
     "cytron dominator frontier ssa phi placement 1991 paper ir"),
    # --- 23 fact ---
    ("Tail-call elimination in Clang only fires when the call is in tail position, the ABIs match, and the callee does not need the caller's stack frame; the 'musttail' attribute forces the pass.", "fact", "technical", False,
     [("Tail-call elimination", "method"), ("Clang", "tool"), ("musttail", "api"), ("ABI", "concept")],
     [("Clang", "Tail-call elimination", "USES")],
     "which three conditions must hold for Clang to do tail-call elimination automatically",
     "tail call elimination clang musttail abi stack frame position"),
    # --- 24 fact ---
    ("Loop unrolling in LLVM is driven by the LoopUnrollPass with a cost model that factors trip-count knowledge, register pressure, and icache budget; the default unroll threshold is tuned per target.", "fact", "technical", False,
     [("LoopUnrollPass", "method"), ("LLVM", "framework"), ("cost model", "concept")],
     [("LLVM", "LoopUnrollPass", "USES")],
     "which inputs drive LLVM's loop-unrolling cost model beyond a simple trip count",
     "loop unroll pass llvm cost model trip count register icache"),
    # --- 25 decision ---
    ("Inline heuristics got retuned for the interpreter dispatch loop: setting inlinehint on each opcode handler and bumping the inline-threshold flag cut dispatch overhead by 22 percent.", "decision", "technical", False,
     [("inlinehint", "api"), ("inline-threshold", "config"), ("interpreter dispatch", "pattern")],
     [("inlinehint", "interpreter dispatch", "APPLIES_TO")],
     "which inline heuristics were retuned for the interpreter dispatch loop and what speedup landed",
     "inline hint threshold interpreter dispatch loop heuristic llvm"),
    # --- 26 milestone ---
    ("UBSan rollout on the row-id hash wrapped up on 2026-02-03: widened the accumulator to int64_t, cleared the last signed-overflow diagnostic, and flipped the CI gate to fail on new UBSan reports.", "milestone", "technical", False,
     [("UBSan", "tool"), ("int64_t", "concept"), ("row-id hash", "algorithm"), ("2026-02-03", "date")],
     [("UBSan", "row-id hash", "APPLIES_TO")],
     "when did UBSan rollout finish on the row-id hash and what CI gate flipped alongside the fix",
     "ubsan row id hash int64 overflow ci gate fail rollout date"),
    # --- 27 fact ---
    ("The GC barrier codegen path in the JIT threads a write barrier through every heap store that crosses a generation boundary; the fast path is two instructions and the slow path calls into the runtime.", "fact", "technical", False,
     [("write barrier", "pattern"), ("GC", "concept"), ("generation boundary", "concept")],
     [("write barrier", "GC", "IMPLEMENTS")],
     "how does the JIT codegen thread GC write barriers through heap stores across a generation boundary",
     "gc write barrier generation heap store jit fast slow path"),
    # --- 28 fact ---
    ("C++ name mangling under the Itanium ABI encodes template arguments, namespaces, and CV-qualifiers into a compact symbol; demangling at link failures is the fastest route to the offending overload.", "fact", "technical", False,
     [("name mangling", "concept"), ("Itanium ABI", "protocol"), ("template", "concept")],
     [("name mangling", "Itanium ABI", "IMPLEMENTS")],
     "what does Itanium-ABI C++ name mangling encode and why is demangling useful at link failures",
     "cpp name mangling itanium abi template namespace cv demangle"),
    # --- 29 decision ---
    ("Chose graph-colouring register allocation for the AOT compiler path where compile time is budget-tolerant; linear-scan stays in the JIT where allocator latency dominates the total compile cost.", "decision", "technical", False,
     [("graph-colouring", "algorithm"), ("linear-scan", "algorithm"), ("AOT", "method"), ("JIT", "method")],
     [("graph-colouring", "AOT", "APPLIES_TO"), ("linear-scan", "JIT", "APPLIES_TO")],
     "how are graph-colouring and linear-scan register allocators split between AOT and JIT paths",
     "graph colouring linear scan aot jit register allocation compile"),
    # --- 30 architecture ---
    ("SpiderMonkey tiers through the Baseline interpreter, the Baseline JIT, and IonMonkey; Warp took over as the frontend that feeds Ion with typed IR instead of the old type-inference path.", "architecture", "technical", False,
     [("SpiderMonkey", "framework"), ("IonMonkey", "tool"), ("Warp", "tool"), ("Baseline JIT", "tool")],
     [("SpiderMonkey", "IonMonkey", "USES"), ("Warp", "IonMonkey", "USES")],
     "how does SpiderMonkey tier its pipeline and where does Warp fit relative to IonMonkey",
     "spidermonkey ionmonkey warp baseline jit tier typed ir"),
    # --- 31 reference ---
    ("Lattner's LLVM thesis from 2002 is still the clearest description of why a reusable middle-end IR beats per-language optimisers; we hand it to new compiler hires on day one.", "reference", "technical", False,
     [("Lattner", "person"), ("LLVM", "framework"), ("IR", "concept")],
     [("LLVM", "IR", "USES")],
     "which foundational LLVM writeup by Lattner explains the reusable middle-end IR design",
     "lattner llvm thesis 2002 middle end ir reusable optimiser"),
    # --- 32 problem ---
    ("Auto-SIMD through LoopVectorize silently bailed on the inner dot-product because the reduction variable had a non-associative float order; a #pragma clang loop vectorize(enable) with -ffast-math restored it.", "problem", "technical", False,
     [("LoopVectorize", "method"), ("dot-product", "algorithm"), ("-ffast-math", "config"), ("#pragma clang loop", "api")],
     [("-ffast-math", "LoopVectorize", "CONFIGURES")],
     "why did LoopVectorize bail on the dot-product reduction and which flag restored vectorisation",
     "auto simd loop vectorize dot product reduction fast math pragma"),
    # --- 33 architecture ---
    ("The compiler driver runs Clang's preprocessor, parser, and Sema in-process and hands off to the LLVM backend as an in-memory Module; no intermediate .bc file hits the disk in the normal build.", "architecture", "technical", False,
     [("Clang", "tool"), ("Sema", "method"), ("LLVM", "framework"), ("Module", "concept")],
     [("Clang", "LLVM", "COMMUNICATES_WITH")],
     "how does the compiler driver hand Clang's frontend output to the LLVM backend without touching disk",
     "clang sema llvm module driver preprocessor parser in memory"),
    # --- 34 decision ---
    ("Turned on -fno-semantic-interposition on the shared libraries; the resulting intra-DSO calls skip the PLT and the inliner sees across boundaries, which paid for itself on the hot path benchmarks.", "decision", "technical", False,
     [("-fno-semantic-interposition", "config"), ("PLT", "concept"), ("DSO", "concept")],
     [("-fno-semantic-interposition", "PLT", "REPLACES")],
     "which flag removed PLT indirection on intra-DSO calls and what did the inliner gain",
     "fno semantic interposition plt dso inline shared library hot"),
    # --- 35 architecture ---
    ("MLIR's pass pipeline is declarative: each pass registers a dialect it operates on, the driver schedules them by dependency, and nested pass managers run per-region without a separate pipeline file.", "architecture", "technical", False,
     [("MLIR", "framework"), ("pass pipeline", "pattern"), ("dialect", "concept")],
     [("MLIR", "dialect", "USES")],
     "how does MLIR schedule passes across dialects without an external pipeline configuration file",
     "mlir pass pipeline dialect nested pass manager schedule region"),
    # --- 36 milestone ---
    ("The monorepo flipped to Clang 18 as the default host compiler on 2026-03-11; ThinLTO cache hit rate stabilised at 87 percent and the hermetic sysroot landed in the same cut.", "milestone", "technical", False,
     [("Clang 18", "tool"), ("ThinLTO", "method"), ("2026-03-11", "date")],
     [("Clang 18", "ThinLTO", "USES")],
     "when did the monorepo flip to Clang 18 as default and what ThinLTO cache hit rate did it hit",
     "clang 18 thinlto hermetic sysroot default monorepo host flip"),
    # --- 37 fact ---
    ("LLVM's dominator tree is maintained incrementally during transforms through the DominatorTreeWrapperPass; passes that move blocks must notify the updater or later analyses read stale idoms.", "fact", "technical", False,
     [("dominator tree", "concept"), ("LLVM", "framework"), ("DominatorTreeWrapperPass", "api")],
     [("LLVM", "dominator tree", "USES")],
     "how does LLVM keep the dominator tree fresh across transforms and what breaks it",
     "dominator tree llvm wrapper pass idom incremental update stale"),
    # --- 38 architecture ---
    ("The Clang Static Analyzer runs on every preflight CI job; it catches null-dereference and use-after-move bugs before they reach review and the results feed the same diagnostics channel as the compiler.", "architecture", "technical", False,
     [("Clang Static Analyzer", "tool"), ("CI", "service"), ("use-after-move", "pattern")],
     [("Clang Static Analyzer", "CI", "DEPLOYED_ON")],
     "where does the Clang Static Analyzer run in the pipeline and which bug classes does it cover",
     "clang static analyzer ci preflight null deref use after move"),
    # --- 39 decision ---
    ("Stopped shipping -O3 by default and settled on -O2 -fno-plt -fstack-protector-strong; the last three percent of wins from -O3 cost us reproducibility headaches that weren't worth the ticket queue.", "decision", "technical", False,
     [("-O2", "config"), ("-O3", "config"), ("-fno-plt", "config"), ("-fstack-protector-strong", "config")],
     [("-O2", "-O3", "REPLACES")],
     "why did the default optimisation level move from -O3 to -O2 with added hardening flags",
     "o2 o3 fno plt stack protector strong default opt reproducibility"),
    # --- 40 milestone ---
    ("GlobalISel became the default instruction selector on aarch64 in our LLVM fork on 2026-03-04; codegen quality matched SelectionDAG on the internal benchmark suite and compile time dropped 18 percent.", "milestone", "technical", False,
     [("SelectionDAG", "method"), ("GlobalISel", "method"), ("LLVM", "framework"), ("aarch64", "platform"), ("2026-03-04", "date")],
     [("GlobalISel", "SelectionDAG", "REPLACES"), ("GlobalISel", "aarch64", "APPLIES_TO")],
     "when did GlobalISel become default on aarch64 in the LLVM fork and what compile-time win came with it",
     "global isel selection dag aarch64 llvm default compile time 18"),
    # --- 41 preference ---
    ("I prefer running ASan with -fsanitize=address,undefined in local dev and keeping TSan on a separate nightly job; mixing TSan with the allocator interceptors makes debugging the first failure painful.", "preference", "technical", False,
     [("ASan", "tool"), ("TSan", "tool"), ("-fsanitize=address,undefined", "config")],
     [("ASan", "TSan", "PREFERS")],
     "which sanitiser split is preferred between local dev and nightly jobs and why",
     "asan ubsan tsan nightly local dev sanitize address undefined"),
    # --- 42 architecture ---
    ("The JVM runtime uses card-marking write barriers compiled inline by C2; a store into an oop field stamps a card in the card table, and the young GC scans only dirty cards during a minor collection.", "architecture", "technical", False,
     [("card-marking", "method"), ("C2", "tool"), ("card table", "concept"), ("JVM", "framework")],
     [("C2", "card-marking", "USES")],
     "how does C2 inline the card-marking write barrier so the young GC can scan only dirty cards",
     "card marking write barrier c2 jvm oop dirty card young gc"),
    # --- 43 noise ---
    ("Someone left a laminated do-not-adjust note on the third-floor thermostat and it now runs a full degree colder than the rest of the office.", "fact", "noise", True, [], [], None, None),
    # --- 44 preference ---
    ("For new services I prefer starting with Clang plus ld.lld plus ThinLTO and only reaching for full LTO or BOLT once a baseline profile says the last percent matters.", "preference", "technical", False,
     [("Clang", "tool"), ("ld.lld", "tool"), ("ThinLTO", "method"), ("BOLT", "tool")],
     [("Clang", "ld.lld", "USES"), ("Clang", "ThinLTO", "USES")],
     "which toolchain stack is preferred for new services before reaching for heavier optimisation",
     "clang lld thinlto bolt baseline service toolchain profile start"),
    # --- 45 milestone ---
    ("PGO rollout finished for the gateway binary on 2026-02-21; a week of canary profile collection at 1 percent traffic produced a profdata that cut request CPU by 11 percent at steady state.", "milestone", "technical", False,
     [("PGO", "method"), ("gateway", "service"), ("profdata", "file"), ("2026-02-21", "date")],
     [("PGO", "gateway", "APPLIES_TO"), ("PGO", "profdata", "PRODUCES")],
     "when did PGO finish rolling out on the gateway and what steady-state CPU win did it deliver",
     "pgo gateway profdata canary 1 percent traffic cpu 11 steady"),
    # --- 46 reference ---
    ("Chaitin's graph-colouring register allocation paper from 1982 is the reference every backend maintainer reaches for when justifying spill heuristics and interference-graph coalescing rules.", "reference", "technical", False,
     [("Chaitin", "person"), ("graph-colouring", "algorithm"), ("interference-graph", "concept")],
     [("graph-colouring", "interference-graph", "USES")],
     "which Chaitin paper anchors backend maintainers' choices on spill heuristics and coalescing",
     "chaitin graph colouring 1982 register allocation spill coalesce"),
    # --- 47 decision ---
    ("Gated Maglev inlining behind a higher invocation count and promoted hot code straight to Turboshaft on the JSON parse path; the speculative deopt loop that kept reoptimising stopped firing after the policy change.", "decision", "technical", False,
     [("Maglev", "tool"), ("Turboshaft", "tool"), ("deopt loop", "pattern"), ("JSON", "technology")],
     [("Turboshaft", "Maglev", "REPLACES")],
     "which tier policy change stopped the Maglev deopt loop on the JSON parse path",
     "maglev turboshaft deopt loop json parse invocation count gate"),
    # --- 48 architecture ---
    ("The build system ships a deterministic Clang toolchain as a hermetic package; every compiler invocation runs under a remote executor with cached action outputs keyed by command line plus input hash.", "architecture", "technical", False,
     [("Clang", "tool"), ("hermetic package", "pattern"), ("remote executor", "service")],
     [("Clang", "remote executor", "DEPLOYED_ON")],
     "how does the build system make Clang invocations hermetic and cacheable on a remote executor",
     "clang hermetic remote executor cache action command input hash"),
    # --- 49 decision ---
    ("Disabled automatic vectorisation on the cryptographic code with -fno-vectorize and -fno-slp-vectorize; timing-variable SIMD paths were the bigger risk than any throughput the vectoriser recovered.", "decision", "technical", False,
     [("-fno-vectorize", "config"), ("-fno-slp-vectorize", "config"), ("cryptographic code", "concept"), ("SIMD", "concept")],
     [("-fno-vectorize", "SIMD", "REPLACES")],
     "why did the cryptographic code disable auto-vectorisation and which two flags enforced it",
     "fno vectorize slp vectorize crypto simd timing variable"),
    # --- 50 preference ---
    ("For hardened binaries I prefer turning on Clang's -fsanitize=cfi-icall alongside LTO; the control-flow integrity checks catch crafted indirect pointers and the LTO-visible type metadata is already in the pipeline.", "preference", "technical", False,
     [("-fsanitize=cfi-icall", "config"), ("LTO", "method"), ("Clang", "tool"), ("control-flow integrity", "concept")],
     [("Clang", "control-flow integrity", "IMPLEMENTS"), ("control-flow integrity", "LTO", "DEPENDS_ON")],
     "which Clang CFI flag is preferred for hardened binaries and why does LTO make it cheap to adopt",
     "clang cfi icall lto hardened indirect call prefer type metadata"),
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
