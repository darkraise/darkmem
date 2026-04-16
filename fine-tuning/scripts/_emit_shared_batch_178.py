"""One-off emitter for shared-base batch-178 — technical domain (memory allocators and heap management: ptmalloc2, tcmalloc, jemalloc, mimalloc, snmalloc, rpmalloc, Hoard, libumem, arena patterns, slab, buddy, TLAB, sanitizers, profilers, OOM killer).

Writes 50 rows to data/v2/shared/batch_178.tmp.jsonl with ids shared-08851..08900.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "shared" / "batch_178.tmp.jsonl"
ID_OFFSET = 8850

# (text, memory_type, domain, noise, entities, relationships, qq, qk)
ENTRIES: list[tuple] = [
    # --- 1 ---
    ("Swapped ptmalloc2 for jemalloc on the ingest service; the glibc default's per-arena contention showed up as a two-hundred-millisecond tail at p99 under the 64-thread load mix.", "decision", "technical", False,
     [("ptmalloc2", "library"), ("jemalloc", "library"), ("glibc", "library")],
     [("jemalloc", "ptmalloc2", "REPLACES")],
     "which allocator swap cleared the ingest service tail latency under heavy thread contention",
     "jemalloc ptmalloc2 glibc arena contention tail latency ingest thread"),
    # --- 2 ---
    ("tcmalloc's per-thread cache returns small allocations without touching a central heap lock; the central free list only gets involved when the thread cache overflows its size-class bin.", "reference", "technical", False,
     [("tcmalloc", "library"), ("per-thread cache", "pattern"), ("size-class bin", "pattern"), ("central free list", "pattern")],
     [("tcmalloc", "per-thread cache", "USES")],
     "how does tcmalloc service small allocations without grabbing a central heap lock in the common path",
     "tcmalloc thread cache size class central free list small alloc"),
    # --- 3 ---
    ("mimalloc shipped as the default for the Rust game server build; the page-reclaim-on-free design kept RSS flat under a churning actor graph where snmalloc drifted upward over twelve hours.", "decision", "technical", False,
     [("mimalloc", "library"), ("snmalloc", "library"), ("Rust", "language"), ("RSS", "concept")],
     [("mimalloc", "snmalloc", "PREFERS")],
     "which allocator did the Rust game server pick for flat RSS under a churning actor graph",
     "mimalloc snmalloc rust game server rss churn actor twelve hour"),
    # --- 4 ---
    ("rpmalloc's lock-free thread caches won the benchmark for the audio engine hot path; the spin-free acquire on cache hit let the real-time thread stay within its 256-sample budget.", "fact", "technical", False,
     [("rpmalloc", "library"), ("thread cache", "pattern"), ("real-time thread", "pattern"), ("audio engine", "project")],
     [("rpmalloc", "thread cache", "USES")],
     "which allocator kept the audio engine hot path within its real-time sample budget and why",
     "rpmalloc lock free thread cache audio engine real time 256 sample"),
    # --- 5 ---
    ("Hoard's blowup-bound hash mapping between threads and superblocks kept the heap from ballooning in the producer-consumer benchmark where ptmalloc2 fragmented past two times working set.", "milestone", "technical", False,
     [("Hoard", "library"), ("ptmalloc2", "library"), ("superblock", "pattern"), ("producer-consumer", "pattern")],
     [("Hoard", "ptmalloc2", "IMPROVES_ON")],
     "which allocator design bounded the heap blowup that ptmalloc2 suffered on producer-consumer workloads",
     "hoard superblock producer consumer blowup ptmalloc fragmentation bound"),
    # --- 6 ---
    ("libumem's magazine-and-depot caching pattern on Solaris inspired the two-level thread-local cache in the internal allocator; per-CPU magazines reduce cross-socket traffic on NUMA boxes.", "reference", "technical", False,
     [("libumem", "library"), ("magazine", "pattern"), ("depot", "pattern"), ("Solaris", "platform"), ("NUMA", "concept")],
     [("magazine", "libumem", "BUILDS_ON")],
     "which Solaris allocator's caching pattern inspired the internal two-level thread-local cache design",
     "libumem magazine depot solaris numa per cpu cache inspiration two level"),
    # --- 7 ---
    ("Rust's default allocator chain routes through System which delegates to the platform malloc; opting into mimalloc on the binary crate is a three-line change in main.rs via a global attribute.", "fact", "technical", False,
     [("Rust", "language"), ("System", "api"), ("mimalloc", "library"), ("main.rs", "file")],
     [("System", "mimalloc", "REPLACES")],
     "how do Rust binaries swap the default System allocator for mimalloc with minimal code change",
     "rust system allocator mimalloc global attribute main rs delegate platform"),
    # --- 8 ---
    ("Arena allocator for the request lifetime replaced scattered per-field malloc calls in the parser; bump a pointer, free the whole arena at request end, zero leaks possible by construction.", "architecture", "technical", False,
     [("Arena allocator", "pattern"), ("malloc", "command"), ("bump", "pattern"), ("parser", "project")],
     [("Arena allocator", "malloc", "REPLACES")],
     "which lifetime-scoped allocator pattern replaced scattered malloc calls in the parser and eliminated leak risk",
     "arena bump allocator parser request lifetime free whole zero leak"),
    # --- 9 ---
    ("Thread-local caches in jemalloc are tcaches sized per size-class; the tcache fill and flush move a magazine of slots at a time so cross-thread synchronisation stays amortised.", "architecture", "technical", False,
     [("jemalloc", "library"), ("tcache", "pattern"), ("size-class", "pattern"), ("magazine", "pattern")],
     [("jemalloc", "tcache", "HAS_PART")],
     "how does jemalloc amortise cross-thread synchronisation through its thread-local tcache refill strategy",
     "jemalloc tcache magazine fill flush size class cross thread amortise"),
    # --- 10. noise ---
    ("The office kitchen's coffee grinder has been making a dying-whale noise all week and no one admits to being the one to break it.", "fact", "noise", True, [], [], None, None),
    # --- 11 ---
    ("Size-class bins segregate allocations into power-of-two-ish buckets: a 40-byte request rounds to the 48-byte class in jemalloc, trading a little internal fragmentation for zero external fragmentation.", "decision", "technical", False,
     [("Size-class", "pattern"), ("jemalloc", "library"), ("internal fragmentation", "concept"), ("external fragmentation", "concept")],
     [("Size-class", "external fragmentation", "FIXES")],
     "how do size-class bins trade internal against external fragmentation in a modern general-purpose allocator",
     "size class bin jemalloc internal external fragmentation bucket round 48"),
    # --- 12 ---
    ("The buddy allocator in the Linux page allocator splits free blocks in halves and coalesces neighbours on release; the order-3 bucket serves most per-CPU page allocations in our workload.", "fact", "technical", False,
     [("buddy allocator", "algorithm"), ("Linux", "platform"), ("page allocator", "pattern"), ("order-3", "concept")],
     [("Linux", "buddy allocator", "USES")],
     "how does the Linux buddy allocator manage page-level splits and coalescing across free orders",
     "buddy allocator linux page order split coalesce neighbour release three"),
    # --- 13 ---
    ("SLUB replaced SLAB as the Linux kernel's default object cache in 2.6.23; reduced metadata overhead and per-cpu partial lists closed the contention gap on many-core boxes.", "milestone", "technical", False,
     [("SLUB", "algorithm"), ("SLAB", "algorithm"), ("Linux", "platform"), ("partial list", "pattern")],
     [("SLUB", "SLAB", "REPLACES")],
     "which kernel object cache replaced SLAB as Linux default and what overhead did it shed",
     "slub slab linux 2 6 23 kernel cache metadata per cpu partial"),
    # --- 14 ---
    ("SLOB is the tiny-memory fallback for embedded Linux builds; the first-fit free list trades throughput for a footprint a SLUB cache could not match on 16 MB target boards.", "fact", "technical", False,
     [("SLOB", "algorithm"), ("SLUB", "algorithm"), ("first-fit", "algorithm"), ("embedded Linux", "platform")],
     [("SLOB", "SLUB", "IMPROVES_ON")],
     "which Linux object allocator fits tiny embedded memory budgets and what trade-off does it accept",
     "slob slub embedded linux first fit 16mb footprint throughput tiny"),
    # --- 15 ---
    ("Bump allocator for the per-frame scratch arena: the renderer allocates transient vertices by incrementing a pointer and resets the arena at end-of-frame with zero deallocation cost.", "decision", "technical", False,
     [("Bump allocator", "pattern"), ("scratch arena", "pattern"), ("renderer", "project"), ("end-of-frame", "pattern")],
     [("renderer", "Bump allocator", "USES")],
     "how does the renderer service per-frame transient vertex allocations with zero deallocation overhead",
     "bump allocator scratch arena renderer transient vertex frame reset zero"),
    # --- 16 ---
    ("GC'd heap vs manual heap trade-off surfaced in the ETL service: the Go pipeline stalls 12 ms at p99 during a concurrent sweep while the Rust sibling never crosses 2 ms on the same input.", "problem", "technical", False,
     [("Go", "language"), ("Rust", "language"), ("concurrent sweep", "algorithm"), ("ETL", "project")],
     [],
     "what p99 stall did the Go pipeline show versus its Rust sibling and which heap strategy caused it",
     "go rust concurrent sweep etl pipeline stall 12 ms gc manual heap"),
    # --- 17 ---
    ("mmap gets used for allocations above MMAP_THRESHOLD in glibc so munmap releases pages back to the kernel immediately; below that threshold, brk grows the heap and release is lazy.", "fact", "technical", False,
     [("mmap", "command"), ("brk", "command"), ("MMAP_THRESHOLD", "config"), ("glibc", "library"), ("munmap", "command")],
     [("glibc", "mmap", "USES")],
     "which syscall does glibc switch to above MMAP_THRESHOLD and why does it change release semantics",
     "mmap brk mmap threshold glibc munmap heap page release lazy"),
    # --- 18 ---
    ("madvise(MADV_FREE) tells the kernel a page range can be reclaimed lazily on memory pressure; MADV_DONTNEED releases immediately and zero-fills on next touch, costing a page fault.", "reference", "technical", False,
     [("madvise", "command"), ("MADV_FREE", "config"), ("MADV_DONTNEED", "config"), ("page fault", "concept")],
     [],
     "which two madvise flags differ in lazy versus immediate page release and what cost does the eager flag carry",
     "madvise madv free madv dontneed page fault release lazy zero fill"),
    # --- 19 ---
    ("jemalloc defaults to MADV_FREE on Linux 4.5+ for decommit; the shift from MADV_DONTNEED cut decommit syscall cost dramatically but complicated RSS interpretation in monitoring dashboards.", "decision", "technical", False,
     [("jemalloc", "library"), ("MADV_FREE", "config"), ("MADV_DONTNEED", "config"), ("Linux 4.5", "platform"), ("RSS", "concept")],
     [("MADV_FREE", "MADV_DONTNEED", "REPLACES")],
     "which madvise flag did jemalloc adopt for decommit and what monitoring surprise did it introduce",
     "jemalloc madv free madv dontneed linux 4 5 decommit rss monitoring"),
    # --- 20 ---
    ("Transparent huge pages flipped to madvise from always after THP compaction stalls bit the OLTP box; khugepaged background scans kept the benefit on the hot anonymous regions we flagged.", "decision", "technical", False,
     [("Transparent huge pages", "concept"), ("THP", "concept"), ("khugepaged", "service"), ("OLTP", "project"), ("madvise", "command")],
     [("THP", "OLTP", "CAUSES")],
     "which THP mode change stopped compaction stalls on the OLTP box while retaining huge-page benefit",
     "transparent huge page thp madvise always khugepaged oltp compaction stall"),
    # --- 21 ---
    ("NUMA-aware allocation pins per-thread arenas to the socket owning the thread; mbind and set_mempolicy drive the placement decisions so cross-socket traffic stays under five percent.", "architecture", "technical", False,
     [("NUMA", "concept"), ("mbind", "command"), ("set_mempolicy", "command"), ("arena", "pattern")],
     [],
     "how do NUMA-aware allocators pin per-thread arenas to the local socket and which syscalls drive it",
     "numa mbind set mempolicy arena socket thread pin cross traffic"),
    # --- 22 ---
    ("Fragmentation in the long-running cache process crept past 1.8x working set after a week; restart-on-threshold lived as a crutch until jemalloc's purge tuning pulled it back to 1.1x.", "preference", "technical", False,
     [("Fragmentation", "concept"), ("jemalloc", "library"), ("working set", "concept"), ("purge", "pattern")],
     [("jemalloc", "Fragmentation", "FIXES")],
     "which allocator tuning replaced the weekly restart crutch for the fragmenting cache process",
     "fragmentation jemalloc purge working set cache restart crutch 1 8x"),
    # --- 23 ---
    ("The JVM's TLAB gives each Java thread a small bump region inside Eden so allocation is a pointer-increment plus a bound check; refilling the TLAB is the only path that touches shared Eden.", "architecture", "technical", False,
     [("TLAB", "pattern"), ("JVM", "platform"), ("Eden", "concept"), ("Java", "language")],
     [("JVM", "TLAB", "USES")],
     "how does the JVM keep per-thread allocation to a pointer-increment in Eden with TLABs",
     "tlab jvm eden java thread bump pointer increment refill shared"),
    # --- 24 ---
    ("Valgrind's memcheck caught the uninitialised-read bug in the audio decoder that had evaded our fuzzers for months; the slowdown is twenty times so it only runs on the nightly CI lane.", "milestone", "technical", False,
     [("Valgrind", "tool"), ("memcheck", "tool"), ("audio decoder", "project"), ("CI", "infrastructure")],
     [("Valgrind", "audio decoder", "APPLIES_TO")],
     "which tool caught the long-standing uninitialised-read bug in the audio decoder and why is it nightly-only",
     "valgrind memcheck audio decoder uninitialised read nightly ci slowdown"),
    # --- 25 ---
    ("AddressSanitizer instrumentation on the gateway CI lane catches heap-buffer-overflow and use-after-free at about 2x cost; the shadow-memory scheme maps eight app bytes to one shadow byte.", "reference", "technical", False,
     [("AddressSanitizer", "tool"), ("heap-buffer-overflow", "error"), ("use-after-free", "error"), ("shadow-memory", "concept"), ("gateway", "project")],
     [("AddressSanitizer", "use-after-free", "FIXES")],
     "which memory-safety instrumentation runs on the gateway CI at 2x cost and what shadow-memory ratio does it use",
     "address sanitizer asan heap overflow use after free shadow memory 8 to 1"),
    # --- 26 ---
    ("MemorySanitizer flagged a whole cluster of read-of-uninitialised-memory bugs in the protobuf glue; unlike ASan it tracks bit-level origin, so the report points back to the exact uninit store.", "problem", "technical", False,
     [("MemorySanitizer", "tool"), ("ASan", "tool"), ("protobuf", "library"), ("bit-level origin", "pattern")],
     [("MemorySanitizer", "ASan", "IMPROVES_ON")],
     "which sanitizer surfaced read-of-uninitialised bugs in the protobuf glue and what does it track that ASan does not",
     "memory sanitizer msan protobuf uninitialised origin bit level asan compare"),
    # --- 27 ---
    ("heaptrack on the search backend pointed at a vector<string> growth hot spot eating 40% of peak RSS; reserve() plus a pool of interned strings cut that slice in half inside a week.", "preference", "technical", False,
     [("heaptrack", "tool"), ("search backend", "project"), ("vector<string>", "pattern"), ("interned strings", "pattern")],
     [("heaptrack", "search backend", "APPLIES_TO")],
     "which profiler flagged the vector growth RSS hog in the search backend and what fix followed",
     "heaptrack search backend vector string reserve intern pool 40 peak rss"),
    # --- 28 ---
    ("Valgrind Massif's snapshot tree produced the stack-by-stack breakdown of peak allocations that finally explained why the packet-replay tool's RSS doubled between v1.2 and v1.3.", "milestone", "technical", False,
     [("Massif", "tool"), ("Valgrind", "tool"), ("packet-replay", "project"), ("v1.3", "date")],
     [("Massif", "Valgrind", "IS_A")],
     "which profiler snapshot finally explained the RSS doubling between packet-replay v1.2 and v1.3",
     "massif valgrind packet replay snapshot peak alloc stack v1 3 rss"),
    # --- 29 ---
    ("Linux OOM killer kicked the metrics sidecar at 3 a.m. every Saturday; oom_score_adj went to -900 on the database container and the sidecar picked up cgroup memory limits instead.", "problem", "technical", False,
     [("Linux OOM killer", "service"), ("oom_score_adj", "config"), ("metrics sidecar", "service"), ("cgroup", "concept")],
     [("Linux OOM killer", "metrics sidecar", "CAUSES")],
     "how did we stop the Linux OOM killer from targeting the database instead of the metrics sidecar",
     "linux oom killer oom score adj metrics sidecar cgroup database saturday"),
    # --- 30 ---
    ("Slab allocator in the kernel groups same-sized objects on page-aligned slabs so construct and destruct amortise; the inode cache is the canonical consumer on workloads with heavy stat traffic.", "architecture", "technical", False,
     [("Slab allocator", "algorithm"), ("inode cache", "pattern"), ("page-aligned", "concept"), ("kernel", "platform")],
     [("Slab allocator", "inode cache", "APPLIES_TO")],
     "how does the kernel's slab allocator amortise construct and destruct costs and which cache is the canonical consumer",
     "slab allocator inode cache page aligned kernel construct destruct stat"),
    # --- 31 ---
    ("snmalloc's snmalloc-style message-passing deallocation made freeing across threads cheaper than jemalloc on the pub-sub benchmark; producers never take the consumer's allocator locks.", "fact", "technical", False,
     [("snmalloc", "library"), ("jemalloc", "library"), ("pub-sub", "pattern"), ("message-passing", "pattern")],
     [("snmalloc", "jemalloc", "IMPROVES_ON")],
     "which allocator design beats jemalloc on cross-thread free throughput in the pub-sub benchmark",
     "snmalloc jemalloc message pass cross thread free pub sub producer"),
    # --- 32 ---
    ("Chose Hoard over tbbmalloc for the HPC node after a week of A/B on the solver workload; tbb's scalable_allocator was close on small blocks but trailed on the mixed large-small mix.", "decision", "technical", False,
     [("Hoard", "library"), ("tbbmalloc", "library"), ("scalable_allocator", "api"), ("HPC", "platform")],
     [("Hoard", "tbbmalloc", "PREFERS")],
     "which allocator won the HPC solver A/B against tbbmalloc and what workload shape tilted it",
     "hoard tbbmalloc scalable allocator hpc solver ab mix large small"),
    # --- 33 ---
    ("Allocation-arena pattern underpins the per-request memory for the router; request start reserves 2 MB, request end resets the cursor, and no per-field malloc pressure reaches the global heap.", "architecture", "technical", False,
     [("arena", "pattern"), ("router", "project"), ("cursor", "pattern"), ("global heap", "concept")],
     [("router", "arena", "USES")],
     "how does the router's per-request arena pattern shield the global heap from per-field malloc pressure",
     "arena router request cursor reset global heap 2mb reserve no malloc"),
    # --- 34 ---
    ("MALLOC_ARENA_MAX=2 cured the RSS bloat we saw after forking a 32-thread process; ptmalloc2 defaults to one arena per CPU, multiplying pages held but never returned in our memory profile.", "preference", "technical", False,
     [("MALLOC_ARENA_MAX", "config"), ("ptmalloc2", "library"), ("fork", "command"), ("RSS", "concept")],
     [("MALLOC_ARENA_MAX", "RSS", "FIXES")],
     "which glibc knob cured the post-fork RSS bloat caused by ptmalloc2's default per-CPU arena count",
     "malloc arena max ptmalloc2 fork rss bloat per cpu arena default 32"),
    # --- 35 ---
    ("Thread-local caches in mimalloc use free-list sharding plus deferred free to keep the fast path branchless; the fast path is around six instructions on x86-64 for small allocations.", "architecture", "technical", False,
     [("mimalloc", "library"), ("free-list sharding", "pattern"), ("deferred free", "pattern"), ("x86-64", "platform")],
     [("mimalloc", "free-list sharding", "USES")],
     "how does mimalloc keep the small-allocation fast path to roughly six x86-64 instructions",
     "mimalloc free list sharding deferred free six instruction x86 64 fast"),
    # --- 36 ---
    ("rpmalloc was chosen for the Windows build after mimalloc exhibited a page-table-lock contention spike under the 128-thread stress test; both beat the default HeapAlloc by an order of magnitude.", "decision", "technical", False,
     [("rpmalloc", "library"), ("mimalloc", "library"), ("HeapAlloc", "api"), ("Windows", "platform")],
     [("rpmalloc", "mimalloc", "PREFERS")],
     "which allocator won the Windows 128-thread stress test against mimalloc and what lock surfaced the gap",
     "rpmalloc mimalloc heap alloc windows 128 thread page table lock"),
    # --- 37 ---
    ("Moved from a single global arena to per-thread arenas in the custom allocator; the lock profile flattened and the top contended lock in perf dropped out of the top ten entirely.", "milestone", "technical", False,
     [("per-thread arena", "pattern"), ("global arena", "pattern"), ("perf", "tool"), ("custom allocator", "project")],
     [("per-thread arena", "global arena", "REPLACES")],
     "which allocator refactor dropped the top contended lock out of the perf top ten",
     "per thread arena global allocator lock perf contend top ten custom"),
    # --- 38 ---
    ("The slab allocator's constructor and destructor hooks let the filesystem cache keep inodes half-initialised between uses; cold-cache latency fell once the locks cache warmed with the workload.", "fact", "technical", False,
     [("slab allocator", "algorithm"), ("constructor", "method"), ("destructor", "method"), ("inode", "pattern")],
     [("slab allocator", "inode", "APPLIES_TO")],
     "which slab allocator feature keeps inodes half-initialised across uses and what latency did it cut",
     "slab allocator constructor destructor inode half init cold cache warm"),
    # --- 39 ---
    ("jemalloc's background thread purge keeps decommit off the application critical path; background_thread:true in the malloc conf moved the munmap cost out of the request hot path.", "decision", "technical", False,
     [("jemalloc", "library"), ("background_thread", "config"), ("munmap", "command"), ("decommit", "pattern")],
     [("background_thread", "munmap", "CONFIGURES")],
     "which jemalloc setting moved decommit and munmap cost off the request hot path",
     "jemalloc background thread purge munmap decommit hot path malloc conf"),
    # --- 40 ---
    ("Transparent huge pages defrag=defer+madvise replaced defrag=always after the compaction stalls we saw with khugepaged; the deferred scan path kept the huge-page hit rate over 80 percent.", "decision", "technical", False,
     [("defrag=defer+madvise", "config"), ("defrag=always", "config"), ("khugepaged", "service"), ("Transparent huge pages", "concept")],
     [("defrag=defer+madvise", "defrag=always", "REPLACES")],
     "which THP defrag mode replaced always and what huge-page hit rate did the deferred scan preserve",
     "thp defrag defer madvise always khugepaged compaction stall 80 hit"),
    # --- 41 ---
    ("OOM killer tuning for the Kubernetes node: memory.high on the workload cgroup trips kswapd earlier, and the kubelet's eviction thresholds get the pod killed cleanly before the global killer fires.", "architecture", "technical", False,
     [("OOM killer", "service"), ("memory.high", "config"), ("kswapd", "service"), ("kubelet", "service"), ("Kubernetes", "platform")],
     [("memory.high", "OOM killer", "REPLACES")],
     "which cgroup and kubelet knobs preempt the global OOM killer with clean pod eviction on nodes",
     "oom killer memory high kswapd kubelet kubernetes eviction cgroup clean"),
    # --- 42 ---
    ("Rust's GlobalAlloc trait is the plug-point for swapping allocators; the binary picks one via #[global_allocator] and libraries stay allocator-agnostic by going through the trait.", "reference", "technical", False,
     [("GlobalAlloc", "api"), ("Rust", "language"), ("#[global_allocator]", "pattern")],
     [("Rust", "GlobalAlloc", "USES")],
     "which Rust trait is the plug-point for allocator swaps and how do libraries stay allocator-agnostic",
     "rust global alloc trait global allocator attribute library agnostic plug"),
    # --- 43. noise ---
    ("A neighbourhood cat has decided the recycling bin outside the office is a suitable afternoon nap spot and now it's all over the company slack.", "fact", "noise", True, [], [], None, None),
    # --- 44 ---
    ("TLAB sizing in HotSpot auto-tunes via ResizeTLAB; manual -XX:TLABSize=256k stabilised allocation-rate variance on the streaming analytics job where the adaptive sizing oscillated under bursty input.", "decision", "technical", False,
     [("TLAB", "pattern"), ("HotSpot", "platform"), ("ResizeTLAB", "config"), ("TLABSize", "config")],
     [("TLABSize", "ResizeTLAB", "REPLACES")],
     "how did pinning TLAB size to 256k fix the allocation-rate jitter on the streaming analytics job",
     "tlab hotspot resize size 256k analytics pin jitter bursty alloc"),
    # --- 45 ---
    ("Heaptrack's flame graph pointed the finger at std::regex construction inside a tight loop; hoisting the compiled regex out cut the tool's peak allocations per request from 41k down to 120.", "milestone", "technical", False,
     [("Heaptrack", "tool"), ("std::regex", "library"), ("flame graph", "pattern")],
     [("Heaptrack", "std::regex", "APPLIES_TO")],
     "which heaptrack finding led to hoisting a compiled regex and by how much did per-request allocations drop",
     "heaptrack flame graph std regex compile hoist allocation 41k 120"),
    # --- 46 ---
    ("Chose a bump arena over tcmalloc for the compiler's frontend pass; the AST lives exactly as long as the pass and bulk-freeing with arena_reset is about a hundred times faster than tcmalloc free.", "decision", "technical", False,
     [("bump arena", "pattern"), ("tcmalloc", "library"), ("arena_reset", "method"), ("AST", "concept")],
     [("bump arena", "tcmalloc", "PREFERS")],
     "which allocator pattern beat tcmalloc for the compiler frontend AST lifetime and by what factor on bulk free",
     "bump arena tcmalloc compiler frontend ast reset bulk free 100x pass"),
    # --- 47 ---
    ("Per-CPU slab caches in the newer SLUB variant avoid the per-cpu partial-list hop on the fast path; allocation cost on contended benchmarks dropped by about thirty percent in the 5.15 kernel.", "reference", "technical", False,
     [("SLUB", "algorithm"), ("per-cpu partial-list", "pattern"), ("5.15 kernel", "date")],
     [("SLUB", "per-cpu partial-list", "IMPROVES_ON")],
     "which SLUB change skipped the per-cpu partial hop and what allocation win landed in the 5.15 kernel",
     "slub per cpu slab partial list kernel 5 15 contend bench 30 percent"),
    # --- 48 ---
    ("AddressSanitizer plus UBSan on every PR catches memory-safety and undefined-behaviour regressions before merge; the buildbot rejects the patch if either instrumentation trips.", "architecture", "technical", False,
     [("AddressSanitizer", "tool"), ("UBSan", "tool"), ("buildbot", "infrastructure"), ("PR", "concept")],
     [("AddressSanitizer", "PR", "APPLIES_TO")],
     "which two sanitizers gate every PR and what does the buildbot do on a failure",
     "address sanitizer asan ubsan pr buildbot reject merge instrumentation"),
    # --- 49 ---
    ("Migrated the custom slab pool to tcmalloc's size-class layout; the legacy homegrown bins had 27 sizes and four percent internal waste, while tcmalloc's 88 classes trim that to under one percent.", "milestone", "technical", False,
     [("tcmalloc", "library"), ("slab pool", "pattern"), ("size-class", "pattern"), ("internal waste", "concept")],
     [("tcmalloc", "slab pool", "REPLACES")],
     "which migration cut internal waste from four percent to under one percent and how many size classes helped",
     "tcmalloc size class slab pool 88 27 internal waste one percent four"),
    # --- 50 ---
    ("Preferred jemalloc over tcmalloc for the column store; jemalloc's arena-per-thread placement and background purge matched the long-lived mixed-size allocation shape better in our p99 latency runs.", "preference", "technical", False,
     [("jemalloc", "library"), ("tcmalloc", "library"), ("column store", "project"), ("arena-per-thread", "pattern")],
     [("jemalloc", "tcmalloc", "PREFERS")],
     "which allocator did the column store prefer over tcmalloc and which jemalloc features drove the choice",
     "jemalloc tcmalloc column store arena thread background purge p99 mixed"),
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
