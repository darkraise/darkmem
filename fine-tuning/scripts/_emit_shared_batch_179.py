"""One-off emitter for shared-base batch-179 — technical domain (garbage collection: generational, mark-sweep, G1GC, ZGC, Shenandoah, Go GC, .NET, V8, OCaml, Erlang).

Writes 50 rows to data/v2/shared/batch_179.tmp.jsonl with ids shared-08901..08950.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "shared" / "batch_179.tmp.jsonl"
ID_OFFSET = 8900

# (text, memory_type, domain, noise, entities, relationships, qq, qk)
ENTRIES: list[tuple] = [
    # --- 1 ---
    ("Switched the payments service JVM from Parallel GC to G1GC after p99 pause times spiked past 800 ms on the 24 GB heap; MaxGCPauseMillis=200 holds with HeapRegion at 16m.", "decision", "technical", False,
     [("Parallel GC", "algorithm"), ("G1GC", "algorithm"), ("MaxGCPauseMillis", "config"), ("HeapRegion", "config"), ("JVM", "platform")],
     [("G1GC", "Parallel GC", "REPLACES"), ("G1GC", "MaxGCPauseMillis", "CONFIGURES")],
     "which collector replaced Parallel GC on the payments JVM and which flag holds the pause budget",
     "g1gc parallel gc jvm pause maxgcpausemillis heapregion payments"),
    # --- 2 ---
    ("ZGC became the default on the trading gateway once Java 21 shipped; sub-millisecond pause targets held under a 64 GB heap where G1GC's mixed cycles used to stall.", "milestone", "technical", False,
     [("ZGC", "algorithm"), ("G1GC", "algorithm"), ("Java 21", "platform"), ("trading gateway", "service")],
     [("ZGC", "G1GC", "REPLACES"), ("ZGC", "trading gateway", "DEPLOYED_ON")],
     "which low-pause collector took over from G1GC on the trading gateway after Java 21 landed",
     "zgc g1gc java 21 trading gateway sub millisecond pause heap"),
    # --- 3 ---
    ("The generational hypothesis still holds in the claims processor: most objects die young, so the bulk of allocations never escape the young generation and a minor GC clears them in microseconds.", "fact", "technical", False,
     [("generational hypothesis", "theory"), ("young generation", "concept"), ("minor GC", "method"), ("claims processor", "service")],
     [("young generation", "generational hypothesis", "IMPLEMENTS")],
     "which GC theory does the claims processor rely on and what does a minor cycle clear in microseconds",
     "generational hypothesis young generation minor gc claims die young"),
    # --- 4 ---
    ("The Semispace copying GC lives at the bottom of the toy VM; from-space is scanned once, live objects copy to to-space, and the pointer bump allocator resets to the start of from-space after flip.", "architecture", "technical", False,
     [("Semispace", "algorithm"), ("copying GC", "method"), ("bump allocator", "pattern"), ("toy VM", "project")],
     [("Semispace", "toy VM", "APPLIES_TO"), ("bump allocator", "Semispace", "USES")],
     "how does the toy VM's semispace GC use from-space and to-space with a bump allocator",
     "semispace copying gc bump allocator from space to space toy vm"),
    # --- 5 ---
    ("Mark-sweep on the embedded Scheme interpreter leaves heap fragmentation after long runs; switched to mark-compact so the free list could be replaced with a single bump pointer.", "decision", "technical", False,
     [("Mark-sweep", "algorithm"), ("mark-compact", "algorithm"), ("Scheme", "language"), ("free list", "pattern")],
     [("mark-compact", "Mark-sweep", "REPLACES"), ("mark-compact", "free list", "REPLACES")],
     "which compacting collector took over from mark-sweep on the Scheme interpreter and why",
     "mark sweep compact scheme interpreter fragmentation free list bump"),
    # --- 6 ---
    ("CMS was removed in Java 17 and our legacy batch jobs finally had to migrate; picked Shenandoah because the concurrent compaction matched CMS's operational feel without the promotion failures.", "milestone", "technical", False,
     [("CMS", "algorithm"), ("Shenandoah", "algorithm"), ("Java 17", "platform"), ("batch jobs", "service")],
     [("Shenandoah", "CMS", "REPLACES"), ("Shenandoah", "batch jobs", "DEPLOYED_ON")],
     "which concurrent collector replaced CMS on the legacy batch jobs after Java 17",
     "cms shenandoah java 17 batch jobs concurrent compaction promotion"),
    # --- 7 ---
    ("Epsilon GC runs in the short-lived benchmark harness: no collection at all, the heap just grows until the process exits; it isolates allocator cost from collector noise in microbenchmarks.", "fact", "technical", False,
     [("Epsilon", "algorithm"), ("benchmark harness", "project"), ("allocator", "concept")],
     [("Epsilon", "benchmark harness", "DEPLOYED_ON")],
     "which no-op collector does the benchmark harness use to isolate allocator cost from GC noise",
     "epsilon gc benchmark harness no op allocator cost microbenchmark"),
    # --- 8 ---
    ("Azul C4 is the collector of record on the market-data ingestion box; its loaded-value barrier gives concurrent compaction with no stop-the-world pause even at 512 GB heap sizes.", "architecture", "technical", False,
     [("Azul C4", "algorithm"), ("loaded-value barrier", "method"), ("market-data ingestion", "service")],
     [("Azul C4", "market-data ingestion", "DEPLOYED_ON"), ("Azul C4", "loaded-value barrier", "USES")],
     "which collector handles the 512 GB market-data box and which barrier keeps compaction concurrent",
     "azul c4 loaded value barrier market data ingestion 512 gb heap"),
    # --- 9 ---
    ("G1NewSizePercent tuned from default 5 to 20 on the write-heavy ingest JVM running G1GC; short-lived allocations now stay in Eden long enough to die there instead of being promoted early.", "decision", "technical", False,
     [("G1NewSizePercent", "config"), ("Eden", "concept"), ("G1GC", "algorithm"), ("ingest JVM", "service")],
     [("G1NewSizePercent", "Eden", "CONFIGURES")],
     "which G1GC flag tuned up Eden size on the ingest JVM and what promotion problem did it fix",
     "g1newsizepercent eden g1gc ingest jvm promotion short lived"),
    # --- 10. noise ---
    ("The office espresso machine developed a whistling beep every time someone forgot to lift the lever and nobody has admitted to owning the manual.", "fact", "noise", True, [], [], None, None),
    # --- 11 ---
    ("OpenJ9 gencon became our default on the IBM stack; the local optimiser nursery and tenured space split maps cleanly onto our Request-Response lifecycle with very few tenured survivors.", "decision", "technical", False,
     [("OpenJ9", "platform"), ("gencon", "algorithm"), ("nursery", "concept"), ("tenured space", "concept")],
     [("OpenJ9", "gencon", "USES")],
     "which OpenJ9 collector policy suits the request-response lifecycle and how does it split nursery from tenured",
     "openj9 gencon nursery tenured request response ibm default policy"),
    # --- 12 ---
    ("OpenJ9 balanced replaced gencon on the large in-memory cache because region-based collection kept fragmentation bounded on the 256 GB heap; gencon was hitting compaction stalls.", "decision", "technical", False,
     [("OpenJ9", "platform"), ("balanced", "algorithm"), ("gencon", "algorithm"), ("in-memory cache", "service")],
     [("balanced", "gencon", "REPLACES"), ("balanced", "in-memory cache", "DEPLOYED_ON")],
     "which OpenJ9 policy took over from gencon on the 256 GB cache and why did gencon stall",
     "openj9 balanced gencon region cache compaction stall 256 gb"),
    # --- 13 ---
    (".NET server GC (SRV) is enabled on the order book replica because concurrent workstation GC (WKS) single-threaded the collection on a 32-core machine that had plenty of parallel slack.", "decision", "technical", False,
     [("server GC", "algorithm"), ("workstation GC", "algorithm"), (".NET", "platform"), ("order book replica", "service")],
     [("server GC", "workstation GC", "REPLACES"), ("server GC", "order book replica", "DEPLOYED_ON")],
     "which .NET GC flavour replaced workstation mode on the 32-core order book replica and why",
     "dotnet server gc workstation srv wks order book 32 core replica"),
    # --- 14 ---
    ("Large Object Heap pinning caused a .NET fragmentation spike in the export service; pooled ArrayPool<byte> buffers kept allocations off the LOH and RSS stopped creeping across restarts.", "problem", "technical", False,
     [("Large Object Heap", "concept"), ("ArrayPool<byte>", "api"), ("export service", "service"), (".NET", "platform")],
     [("ArrayPool<byte>", "Large Object Heap", "FIXES")],
     "which pooled buffer type took pressure off the Large Object Heap in the export service",
     "large object heap loh arraypool export service fragmentation rss"),
    # --- 15 ---
    ("Go 1.19 soft memory limit via GOMEMLIMIT dropped OOM kills on the Kubernetes ingress pods; the pacer now throttles mutator allocation before cgroup memory.max is breached.", "milestone", "technical", False,
     [("Go", "language"), ("GOMEMLIMIT", "config"), ("Kubernetes", "platform"), ("pacer", "concept")],
     [("GOMEMLIMIT", "Kubernetes", "APPLIES_TO"), ("pacer", "GOMEMLIMIT", "USES")],
     "which Go 1.19 knob stopped the ingress OOM kills and how does the pacer cooperate with it",
     "go gomemlimit soft memory limit kubernetes pacer ingress oom"),
    # --- 16 ---
    ("GOGC at 100 was the default but the analytics shard churned the heap; bumping the Go GOGC knob to 300 cut CPU overhead from 12 percent to 4 percent at the cost of a 2x resident set.", "decision", "technical", False,
     [("GOGC", "config"), ("Go", "language"), ("analytics shard", "service")],
     [("GOGC", "analytics shard", "CONFIGURES")],
     "how did tuning GOGC trade CPU for resident set on the analytics shard and what numbers landed",
     "gogc go analytics shard cpu overhead resident set trade heap"),
    # --- 17 ---
    ("Go's concurrent tri-color mark-sweep collector runs alongside the mutator with a write barrier; stop-the-world windows are only the mark start and mark termination ticks, each under a millisecond.", "fact", "technical", False,
     [("tri-color mark-sweep", "algorithm"), ("Go", "language"), ("write barrier", "method")],
     [("Go", "tri-color mark-sweep", "USES")],
     "which collector does Go use and where do its stop-the-world ticks land in the mark cycle",
     "go tri color mark sweep write barrier stop world mark termination"),
    # --- 18 ---
    ("Python's reference counting handles most objects deterministically at zero-refs; the generational cycle collector in gc module only runs to break reference cycles that pure refcount cannot reclaim.", "architecture", "technical", False,
     [("reference counting", "method"), ("generational cycle collector", "algorithm"), ("Python", "language"), ("gc", "library")],
     [("Python", "reference counting", "USES"), ("generational cycle collector", "reference counting", "EXTENDS")],
     "how does Python layer reference counting with the generational cycle collector to reclaim cycles",
     "python reference count generational cycle collector gc module refcount"),
    # --- 19 ---
    ("V8 Orinoco redesigned the browser's GC into a set of tasks that run concurrent or parallel to the main thread; mark-sweep-compact became mostly off-thread and the Scavenger got a parallel newspace pass.", "milestone", "technical", False,
     [("V8", "platform"), ("Orinoco", "project"), ("Scavenger", "algorithm"), ("mark-sweep-compact", "algorithm")],
     [("Orinoco", "V8", "APPLIES_TO"), ("Scavenger", "Orinoco", "HAS_PART")],
     "which V8 GC redesign moved mark-sweep-compact off the main thread and parallelised the Scavenger",
     "v8 orinoco scavenger mark sweep compact parallel concurrent main"),
    # --- 20 ---
    ("OCaml's minor GC is a copying collector over a small fixed-size region; the major GC is an incremental mark-sweep with an optional compaction pass that runs when fragmentation exceeds a ratio threshold.", "architecture", "technical", False,
     [("OCaml", "language"), ("minor GC", "method"), ("major GC", "method"), ("compaction pass", "method")],
     [("OCaml", "minor GC", "USES"), ("OCaml", "major GC", "USES")],
     "how does OCaml split minor copying GC from the major incremental mark-sweep with compaction",
     "ocaml minor major gc copying incremental mark sweep compaction"),
    # --- 21 ---
    ("Erlang uses a per-process heap model so GC is cheap and fully isolated; a process that dies frees its heap atomically and the scheduler never pauses the VM for a global stop-the-world.", "architecture", "technical", False,
     [("Erlang", "language"), ("per-process heap", "pattern"), ("scheduler", "concept")],
     [("Erlang", "per-process heap", "USES")],
     "why does Erlang avoid a global stop-the-world and what does per-process heap allocation buy it",
     "erlang per process heap isolated scheduler stop world atomic"),
    # --- 22 ---
    ("Replaced a long-lived cache of byte[] arrays with a chunked ring buffer because the Large Object Heap 85 KB threshold kept triggering Gen2 collections on the .NET export worker.", "decision", "technical", False,
     [("byte[]", "api"), ("ring buffer", "pattern"), ("Large Object Heap", "concept"), ("Gen2", "concept"), (".NET", "platform")],
     [("ring buffer", "byte[]", "REPLACES"), ("Large Object Heap", "Gen2", "CAUSES")],
     "which data structure replaced the byte array cache after LOH triggered Gen2 collections",
     "ring buffer byte array loh gen2 dotnet export worker 85kb"),
    # --- 23 ---
    ("ZGC's colored pointers encode GC metadata in the high bits of a 64-bit reference; load barriers mask off the color on dereference so the mutator sees a plain pointer.", "fact", "technical", False,
     [("ZGC", "algorithm"), ("colored pointers", "method"), ("load barrier", "method")],
     [("ZGC", "colored pointers", "USES"), ("load barrier", "colored pointers", "USES")],
     "which pointer-tagging technique does ZGC use for metadata and how does the load barrier mask it",
     "zgc colored pointer load barrier 64 bit tag high bits mask"),
    # --- 24 ---
    ("Shenandoah uses Brooks forwarding pointers so every object carries an indirection word; reads follow it concurrently while a relocation pass is running, dodging the stop-the-world copy.", "fact", "technical", False,
     [("Shenandoah", "algorithm"), ("Brooks forwarding pointers", "method"), ("relocation", "method")],
     [("Shenandoah", "Brooks forwarding pointers", "USES")],
     "which indirection technique lets Shenandoah relocate objects concurrently with mutator reads",
     "shenandoah brooks forwarding pointer relocation concurrent indirect"),
    # --- 25 ---
    ("The Hotspot Jira for bug JDK-8238358 explained why concurrent refinement threads in G1GC over-consumed CPU on small heaps; tuning G1ConcRefinementThreads cleaned it up.", "reference", "technical", False,
     [("JDK-8238358", "publication"), ("G1GC", "algorithm"), ("G1ConcRefinementThreads", "config"), ("Hotspot", "platform")],
     [("G1ConcRefinementThreads", "G1GC", "CONFIGURES")],
     "which Hotspot issue explained G1GC refinement-thread CPU overhead on small heaps",
     "jdk 8238358 g1gc refinement thread hotspot cpu small heap"),
    # --- 26 ---
    ("Jones and Hosking's The Garbage Collection Handbook is the team's shared reference for GC terminology; the copying, mark-sweep, and generational chapters settle most design arguments in code review.", "reference", "technical", False,
     [("The Garbage Collection Handbook", "publication"), ("copying", "method"), ("mark-sweep", "algorithm"), ("generational", "concept")],
     [("The Garbage Collection Handbook", "generational", "APPLIES_TO")],
     "which reference book anchors the team's shared GC terminology for design arguments",
     "garbage collection handbook jones hosking reference copying mark"),
    # --- 27 ---
    ("Ungar's 1984 paper introduced the generational hypothesis with a tenuring threshold that the modern HotSpot Young Gen still echoes in MaxTenuringThreshold; the foundations did not age.", "reference", "technical", False,
     [("Ungar", "person"), ("generational hypothesis", "theory"), ("MaxTenuringThreshold", "config"), ("HotSpot", "platform")],
     [("MaxTenuringThreshold", "generational hypothesis", "IMPLEMENTS")],
     "which 1984 paper seeded the generational hypothesis that HotSpot MaxTenuringThreshold still echoes",
     "ungar 1984 generational hypothesis hotspot maxtenuringthreshold paper"),
    # --- 28 ---
    ("Shipped the Observability board for GC metrics: jvm_gc_pause_seconds histograms per collector, Prometheus scrape on port 9100, Grafana panel broken down by cause and region.", "milestone", "technical", False,
     [("Prometheus", "tool"), ("Grafana", "tool"), ("jvm_gc_pause_seconds", "api"), ("Observability board", "project")],
     [("Observability board", "Prometheus", "USES"), ("Observability board", "Grafana", "USES")],
     "which observability stack ships GC pause histograms for the JVM fleet and how is it exposed",
     "observability gc metric jvm pause prometheus grafana scrape 9100"),
    # --- 29 ---
    ("For the pricing engine the team prefers Shenandoah over ZGC because older kernels in the production fleet lack the huge-page support ZGC relies on for its multi-mapping trick.", "preference", "technical", False,
     [("Shenandoah", "algorithm"), ("ZGC", "algorithm"), ("pricing engine", "service"), ("huge-page", "concept")],
     [("Shenandoah", "ZGC", "PREFERS"), ("ZGC", "huge-page", "DEPENDS_ON")],
     "why does the pricing engine team prefer Shenandoah over ZGC on the current fleet",
     "shenandoah zgc pricing engine huge pages kernel multi mapping"),
    # --- 30 ---
    ("Team prefers Go over Java for the new metrics aggregator because the GC pacer's soft limit handling matches Kubernetes memory quotas better than MaxRAMPercentage tuning on the JVM.", "preference", "technical", False,
     [("Go", "language"), ("Java", "language"), ("Kubernetes", "platform"), ("metrics aggregator", "service"), ("MaxRAMPercentage", "config")],
     [("Go", "Java", "PREFERS"), ("metrics aggregator", "Kubernetes", "DEPLOYED_ON")],
     "which language did the team pick for the metrics aggregator and which GC quirk drove the choice",
     "go java metrics aggregator kubernetes pacer maxrampercentage quota"),
    # --- 31 ---
    ("Old Scheme toy still uses Cheney's algorithm for its copying collector because the iterative BFS over to-space is simpler to reason about than a recursive mark pass for the teaching notes.", "preference", "technical", False,
     [("Cheney's algorithm", "algorithm"), ("Scheme", "language"), ("to-space", "concept"), ("BFS", "method")],
     [("Cheney's algorithm", "BFS", "USES")],
     "why does the Scheme toy prefer Cheney's algorithm over a recursive mark for teaching",
     "cheney algorithm scheme copying to space bfs iterative teaching"),
    # --- 32 ---
    ("Prefer mark-compact over mark-sweep in the bytecode VM because long-lived server processes need defragmented heaps; the added compaction cost is paid off by faster bump allocation in the hot path.", "architecture", "technical", False,
     [("mark-compact", "algorithm"), ("mark-sweep", "algorithm"), ("bytecode VM", "project"), ("bump allocation", "pattern")],
     [("mark-compact", "mark-sweep", "PREFERS")],
     "why does the bytecode VM prefer mark-compact over mark-sweep for long-lived server processes",
     "mark compact sweep bytecode vm bump allocation defragment server"),
    # --- 33 ---
    ("Promotion failure in G1GC on the order matcher caused 4 second pauses during the 11:00 open; raised InitiatingHeapOccupancyPercent from 45 to 35 and grew the heap by 20 percent to buy headroom.", "problem", "technical", False,
     [("Promotion failure", "concept"), ("G1GC", "algorithm"), ("InitiatingHeapOccupancyPercent", "config"), ("order matcher", "service")],
     [("InitiatingHeapOccupancyPercent", "Promotion failure", "FIXES")],
     "which G1GC flag and heap change cured the 11:00 open promotion failure on the order matcher",
     "promotion failure g1gc iho initiatingheapoccupancypercent order matcher"),
    # --- 34 ---
    ("V8's Scavenger runs as a parallel semispace copying collector over new-space while the main thread is paused for a few hundred microseconds; surviving objects promote into old-space.", "fact", "technical", False,
     [("V8", "platform"), ("Scavenger", "algorithm"), ("new-space", "concept"), ("old-space", "concept")],
     [("Scavenger", "new-space", "APPLIES_TO")],
     "which V8 collector handles new-space and where do its survivors promote to",
     "v8 scavenger semispace new space old space parallel promote"),
    # --- 35 ---
    ("Python's gc.set_threshold was bumped from (700, 10, 10) to (2000, 15, 15) on the ingestion worker because the gen0 sweep was firing 400 times a second under heavy dict churn.", "decision", "technical", False,
     [("gc.set_threshold", "api"), ("Python", "language"), ("ingestion worker", "service"), ("gen0", "concept")],
     [("gc.set_threshold", "ingestion worker", "CONFIGURES")],
     "which Python GC threshold change cut the gen0 sweep rate on the ingestion worker",
     "python gc set threshold gen0 ingestion worker dict churn 2000"),
    # --- 36 ---
    ("The Go runtime's GC pacer targets a heap-growth ratio tied to GOGC; when allocation outpaces mark, the pacer slows the mutator via an assist credit that each goroutine repays during allocation.", "architecture", "technical", False,
     [("Go", "language"), ("pacer", "concept"), ("GOGC", "config"), ("assist credit", "method")],
     [("pacer", "GOGC", "USES"), ("pacer", "assist credit", "USES")],
     "how does the Go GC pacer use GOGC and assist credit to keep mark ahead of allocation",
     "go pacer gogc assist credit mutator allocation ratio heap"),
    # --- 37 ---
    ("Runtime.getRuntime().gc() is banned in the code review rules; explicit GC hints interact poorly with G1GC and ZGC heuristics and reviewers mark them as a DisallowedApi finding on sight.", "preference", "technical", False,
     [("Runtime.getRuntime().gc()", "api"), ("G1GC", "algorithm"), ("ZGC", "algorithm"), ("DisallowedApi", "tool")],
     [("DisallowedApi", "Runtime.getRuntime().gc()", "CONTRADICTS")],
     "which JVM API does the team ban in code review and why does it hurt modern collector heuristics",
     "runtime gc ban code review g1gc zgc disallowedapi explicit hint"),
    # --- 38 ---
    ("Read Hertz and Berger's Quantifying the Performance of Garbage Collection vs. Explicit Memory Management when sizing the JVM fleet; the 5x heap rule shaped the container memory budget.", "reference", "technical", False,
     [("Quantifying the Performance of Garbage Collection vs. Explicit Memory Management", "publication"), ("JVM", "platform"), ("5x heap rule", "concept")],
     [("5x heap rule", "Quantifying the Performance of Garbage Collection vs. Explicit Memory Management", "BUILDS_ON")],
     "which paper produced the 5x heap rule that informs the JVM fleet's memory budget",
     "hertz berger quantifying gc explicit memory 5x heap rule paper"),
    # --- 39 ---
    ("The GC Handbook chapter on concurrent collectors is where the team cross-references ZGC, Shenandoah, and C4 design trade-offs before picking a collector for a new service.", "reference", "technical", False,
     [("GC Handbook", "publication"), ("ZGC", "algorithm"), ("Shenandoah", "algorithm"), ("C4", "algorithm")],
     [("GC Handbook", "ZGC", "APPLIES_TO"), ("GC Handbook", "Shenandoah", "APPLIES_TO")],
     "which reference does the team consult when comparing ZGC, Shenandoah, and C4 for a new service",
     "gc handbook concurrent collector zgc shenandoah c4 compare pick"),
    # --- 40 ---
    ("Wilson's Uniprocessor Garbage Collection Techniques survey sits pinned in the platform channel; new hires read it before touching anything in the allocator or collector path.", "reference", "technical", False,
     [("Uniprocessor Garbage Collection Techniques", "publication"), ("Wilson", "person"), ("platform channel", "project")],
     [("Uniprocessor Garbage Collection Techniques", "Wilson", "AUTHORED_BY")],
     "which GC survey is the onboarding read before new hires touch the allocator or collector path",
     "wilson uniprocessor garbage collection survey pinned onboarding"),
    # --- 41 ---
    ("ZGC generational mode landed in Java 21 as experimental and Java 22 as production; the old single-generation ZGC is staying around only for compatibility tests on the legacy risk engine.", "milestone", "technical", False,
     [("ZGC", "algorithm"), ("Java 21", "platform"), ("Java 22", "platform"), ("risk engine", "service")],
     [("Java 22", "ZGC", "PRODUCES"), ("ZGC", "risk engine", "DEPLOYED_ON")],
     "when did generational ZGC ship as production and what is the legacy single-generation mode kept for",
     "zgc generational java 21 22 experimental production risk engine"),
    # --- 42 ---
    ("Rewrote the Erlang supervision tree so worker processes are short-lived; the per-process heap dies with them, so we never trigger a major GC in the hot trading loop.", "architecture", "technical", False,
     [("Erlang", "language"), ("supervision tree", "pattern"), ("worker process", "concept"), ("trading loop", "service")],
     [("worker process", "Erlang", "USES"), ("supervision tree", "trading loop", "APPLIES_TO")],
     "how did the Erlang supervision-tree redesign avoid major GC in the trading loop",
     "erlang supervision tree worker process per heap trading loop major"),
    # --- 43. noise ---
    ("The Friday potluck crossed some new border when the intern brought a durian and the meeting room needed its windows open for most of the afternoon.", "fact", "noise", True, [], [], None, None),
    # --- 44 ---
    ("Epsilon was the right default in the stress-test harness because it lets the allocator run flat-out; any GC activity now signals a memory leak rather than a tuning issue.", "decision", "technical", False,
     [("Epsilon", "algorithm"), ("stress-test harness", "project"), ("allocator", "concept")],
     [("Epsilon", "stress-test harness", "DEPLOYED_ON")],
     "why does the stress-test harness run on Epsilon and what does any collection activity signal",
     "epsilon stress test harness allocator memory leak default signal"),
    # --- 45 ---
    ("Mark-compact's sliding compaction keeps object ordering which is friendly to caches; the Lisp-2 layout needs two extra words per object, so the bytecode VM uses the threaded variant to save space.", "fact", "technical", False,
     [("Mark-compact", "algorithm"), ("sliding compaction", "method"), ("Lisp-2", "method"), ("bytecode VM", "project")],
     [("bytecode VM", "Mark-compact", "USES")],
     "which mark-compact variant does the bytecode VM pick to avoid the Lisp-2 two-word overhead",
     "mark compact sliding lisp 2 threaded bytecode vm cache order"),
    # --- 46 ---
    ("Migrated the financial reporting batch to OpenJ9 balanced in 2026-04-10 after gencon's Class Unloading pauses blocked the nightly SLA twice in one week.", "milestone", "technical", False,
     [("OpenJ9", "platform"), ("balanced", "algorithm"), ("gencon", "algorithm"), ("2026-04-10", "date"), ("financial reporting", "service")],
     [("balanced", "gencon", "REPLACES"), ("balanced", "financial reporting", "DEPLOYED_ON")],
     "which OpenJ9 policy change landed on 2026-04-10 for the financial reporting batch and what pause did it cure",
     "openj9 balanced gencon class unloading sla reporting 2026 04 10"),
    # --- 47 ---
    ("Disabled the JVM DisableExplicitGC flag on the legacy SOAP gateway because a vendor library calls System.gc() during shutdown and suppressing it left native handles un-closed and fds leaking.", "decision", "technical", False,
     [("DisableExplicitGC", "config"), ("System.gc()", "api"), ("SOAP gateway", "service"), ("JVM", "platform")],
     [("System.gc()", "DisableExplicitGC", "CONTRADICTS")],
     "why was DisableExplicitGC turned off on the legacy SOAP gateway and which resource leaked without it",
     "disable explicit gc system soap gateway fd leak vendor shutdown"),
    # --- 48 ---
    ("Cross-generational references are tracked via a card table in HotSpot so a minor GC can scan only dirty cards in old gen; write barriers mark the card on pointer stores into old gen.", "architecture", "technical", False,
     [("card table", "method"), ("HotSpot", "platform"), ("write barrier", "method"), ("minor GC", "method"), ("old gen", "concept")],
     [("HotSpot", "card table", "USES"), ("write barrier", "card table", "CONFIGURES")],
     "how does HotSpot use card tables and write barriers to scope a minor GC over old-gen references",
     "card table hotspot write barrier minor gc old gen dirty cross"),
    # --- 49 ---
    ("Promotion-rate graphs on the G1GC order router were driven by Survivor-space overflow; bumping SurvivorRatio from 8 to 6 gave enough space for aging and tenured growth fell by half.", "decision", "technical", False,
     [("SurvivorRatio", "config"), ("Survivor-space", "concept"), ("order router", "service"), ("G1GC", "algorithm")],
     [("SurvivorRatio", "Survivor-space", "CONFIGURES")],
     "which survivor-space config change cut tenured growth in half on the order router",
     "survivor ratio survivor space order router tenured promotion age"),
    # --- 50 ---
    ("Allocation profiling with async-profiler flame graphs pinned the top-of-list allocation hotspot to a BigDecimal multiply loop; swapping to long cents cut GC pause frequency in half on the pricing feed.", "problem", "technical", False,
     [("async-profiler", "tool"), ("BigDecimal", "api"), ("long", "api"), ("pricing feed", "service")],
     [("long", "BigDecimal", "REPLACES"), ("async-profiler", "pricing feed", "APPLIES_TO")],
     "which allocation hotspot did async-profiler expose on the pricing feed and what replaced BigDecimal",
     "async profiler flame graph bigdecimal long cents pricing feed gc"),
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
