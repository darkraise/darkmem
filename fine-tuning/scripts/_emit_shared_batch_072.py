"""One-off emitter for shared-base batch-072 — ai_coding domain (concurrency and parallelism patterns in application code).

Writes 50 rows to data/v2/shared/batch_072.tmp.jsonl with ids shared-03551..03600.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "shared" / "batch_072.tmp.jsonl"
ID_OFFSET = 3550

# (text, memory_type, domain, noise, entities, relationships, qq, qk)
ENTRIES: list[tuple] = [
    # --- 1 ---
    ("Migrated the ingestion pipeline from raw asyncio.gather calls to anyio task groups; cancellation now propagates correctly when one child raises instead of leaving siblings dangling.", "decision", "ai_coding", False,
     [("asyncio.gather", "method"), ("anyio", "library"), ("task groups", "pattern")],
     [("anyio", "asyncio.gather", "REPLACES")],
     "which Python concurrency primitive replaced gather in the ingestion pipeline and what did it fix",
     "anyio task group replace asyncio gather cancel propagate sibling"),
    # --- 2 ---
    ("Adopted structured concurrency for the crawler workers; every spawned coroutine lives inside a nursery scope so a fail-fast crash tears the whole subtree down deterministically.", "architecture", "ai_coding", False,
     [("structured concurrency", "pattern"), ("nursery", "pattern"), ("crawler", "service")],
     [("structured concurrency", "nursery", "USES")],
     "how does the crawler ensure spawned coroutines die together when one fails",
     "structured concurrency nursery scope tear down fail fast crawler"),
    # --- 3 ---
    ("Switched the order-matching engine off platform threads and onto Java virtual threads; thread-per-request blocking JDBC calls finally stopped exhausting the pool under burst load.", "milestone", "ai_coding", False,
     [("virtual threads", "pattern"), ("Java", "language"), ("JDBC", "library"), ("order-matching engine", "service")],
     [("virtual threads", "Java", "APPLIES_TO")],
     "which JVM threading model replaced platform threads on the matching engine and why",
     "virtual thread loom platform replace blocking jdbc pool exhaust"),
    # --- 4 ---
    ("Goroutines in the dispatcher fan out work to a worker pool sized to GOMAXPROCS; an unbounded go func per request was eating heap and trashing the scheduler.", "problem", "ai_coding", False,
     [("Goroutines", "pattern"), ("worker pool", "pattern"), ("GOMAXPROCS", "config"), ("dispatcher", "service")],
     [("worker pool", "Goroutines", "REPLACES")],
     "which Go concurrency change capped goroutine growth in the dispatcher service",
     "goroutine worker pool gomaxprocs unbounded heap scheduler thrash"),
    # --- 5 ---
    ("Tokio runtime is configured as a multi-threaded scheduler with 8 workers; the websocket gateway pins the network task to a LocalSet so the !Send handle stays on one thread.", "architecture", "ai_coding", False,
     [("Tokio", "library"), ("LocalSet", "pattern"), ("websocket gateway", "service")],
     [("websocket gateway", "Tokio", "USES")],
     "how is the Tokio runtime configured for the websocket gateway and where do non-Send tasks live",
     "tokio runtime multi thread worker localset non send websocket"),
    # --- 6 ---
    ("Replaced shared-state Mutex<HashMap> in the rate limiter with a sharded DashMap; lock contention on the hot path dropped from 40 percent CPU to under 5.", "decision", "ai_coding", False,
     [("Mutex", "pattern"), ("DashMap", "library"), ("rate limiter", "service"), ("HashMap", "pattern")],
     [("DashMap", "Mutex", "REPLACES")],
     "which Rust map type replaced the mutex-guarded hashmap in the rate limiter and what changed",
     "dashmap shard mutex hashmap contention rate limiter rust hot path"),
    # --- 7 ---
    ("The pricing actor uses Akka's typed behaviours over the classic untyped API; compiler-checked message protocols caught three protocol drifts before the first deploy.", "decision", "ai_coding", False,
     [("Akka", "framework"), ("typed behaviours", "pattern"), ("pricing actor", "service")],
     [("typed behaviours", "Akka", "USES")],
     "which Akka API flavour does the pricing actor use and what bugs did it catch",
     "akka typed behaviour untyped message protocol compile check actor"),
    # --- 8 ---
    ("Ported the chat presence service from Node EventEmitter to an Elixir GenServer; supervised restarts replaced the bespoke try/catch reconnect loop and uptime jumped past three nines.", "milestone", "ai_coding", False,
     [("Elixir", "language"), ("GenServer", "pattern"), ("EventEmitter", "library"), ("chat presence service", "service")],
     [("GenServer", "EventEmitter", "REPLACES")],
     "how did the chat presence service get supervised restarts after the rewrite",
     "elixir genserver supervisor restart eventemitter port presence"),
    # --- 9 ---
    ("Erlang's let-it-crash philosophy drives the billing worker tree; each child is restarted with a one-for-one strategy and a max-restart-intensity guard against crash storms.", "architecture", "ai_coding", False,
     [("Erlang", "language"), ("let-it-crash", "pattern"), ("one-for-one", "pattern"), ("billing worker", "service")],
     [("billing worker", "Erlang", "USES")],
     "which Erlang supervision strategy backs the billing worker tree and how are crash storms bounded",
     "erlang let it crash one for one supervisor max restart intensity"),
    # --- 10. noise ---
    ("Someone left a half-empty bag of jelly beans on the ops desk and now nobody admits to bringing them.", "fact", "noise", True, [], [], None, None),
    # --- 11 ---
    ("The image resizer chose channels over a shared mutex queue; passing a *Job through a buffered chan keeps producer and consumer cleanly decoupled and easy to test.", "decision", "ai_coding", False,
     [("channels", "pattern"), ("mutex", "pattern"), ("image resizer", "service")],
     [("channels", "mutex", "PREFERS")],
     "which Go synchronisation flavour did the image resizer pick over a shared mutex queue",
     "go channel buffered mutex queue producer consumer decouple test"),
    # --- 12 ---
    ("Tokio's work-stealing scheduler keeps tail latency flat when one worker hits a slow task; before the move, the round-robin executor stalled the whole batch on a single straggler.", "fact", "ai_coding", False,
     [("Tokio", "library"), ("work-stealing", "algorithm"), ("round-robin", "algorithm")],
     [("work-stealing", "round-robin", "IMPROVES_ON")],
     "why did Tokio's scheduler beat the previous round-robin executor on tail latency",
     "work stealing scheduler round robin tail latency straggler tokio"),
    # --- 13 ---
    ("ThreadPoolExecutor with a fixed cap of 32 backs the report renderer; bumping max_workers higher only shifted the bottleneck onto the database connection pool.", "fact", "ai_coding", False,
     [("ThreadPoolExecutor", "library"), ("max_workers", "config"), ("report renderer", "service")],
     [],
     "which Python thread-pool sizing did the report renderer settle on and why not larger",
     "thread pool executor max workers cap database connection bottleneck"),
    # --- 14 ---
    ("Backpressure on the event ingestion path comes from a bounded asyncio.Queue with maxsize=1024; producers await put when full instead of buffering unbounded in memory.", "architecture", "ai_coding", False,
     [("asyncio.Queue", "library"), ("Backpressure", "pattern"), ("maxsize", "config"), ("event ingestion", "service")],
     [],
     "how does the event ingestion path apply backpressure to upstream producers",
     "backpressure bounded asyncio queue maxsize await put producer"),
    # --- 15 ---
    ("Project Reactor's Flux.onBackpressureBuffer with a drop-oldest strategy fronts the metrics fan-in; we accept losing the tail of a burst over OOM-killing the JVM.", "decision", "ai_coding", False,
     [("Reactor", "framework"), ("Flux", "api"), ("onBackpressureBuffer", "method"), ("metrics fan-in", "service")],
     [],
     "which Reactor backpressure strategy fronts the metrics fan-in and what trade-off does it accept",
     "reactor flux backpressure buffer drop oldest oom metrics fan in"),
    # --- 16 ---
    ("RxJava migration moved every subscribeOn(Schedulers.io()) to Schedulers.from(boundedExecutor); the cached io scheduler had been quietly spawning hundreds of threads under load.", "problem", "ai_coding", False,
     [("RxJava", "library"), ("Schedulers.io", "method"), ("boundedExecutor", "config")],
     [("boundedExecutor", "Schedulers.io", "REPLACES")],
     "which RxJava scheduler swap stopped a thread explosion under sustained load",
     "rxjava scheduler io bounded executor cached thread explosion"),
    # --- 17 ---
    ("Go's race detector caught a data race on the cached config map during integration tests; the fix wrapped reads in a sync.RWMutex and kept the hot read path lock-free with atomic.Pointer.", "problem", "ai_coding", False,
     [("race detector", "tool"), ("sync.RWMutex", "library"), ("atomic.Pointer", "library"), ("cached config map", "pattern")],
     [],
     "which Go tool flagged the config-map data race and what synchronisation pattern fixed it",
     "go race detector data race config map rwmutex atomic pointer"),
    # --- 18 ---
    ("Rust's compile-time Send and Sync checks rejected a naive Rc<RefCell> on the worker queue; switched to Arc<Mutex> and the borrow-checker audit took ten minutes instead of a week.", "fact", "ai_coding", False,
     [("Send", "concept"), ("Sync", "concept"), ("Rc", "library"), ("RefCell", "library"), ("Arc", "library"), ("Mutex", "library")],
     [("Arc", "Rc", "REPLACES")],
     "which Rust trait checks rejected the Rc/RefCell worker queue and what replaced it",
     "rust send sync rc refcell arc mutex worker queue borrow checker"),
    # --- 19 ---
    ("Compiled the analytics aggregator with ThreadSanitizer in CI; a long-tail flaky test turned out to be a missed memory_order_release on a counter store.", "problem", "ai_coding", False,
     [("ThreadSanitizer", "tool"), ("memory_order_release", "method"), ("analytics aggregator", "service")],
     [],
     "which sanitizer caught the analytics aggregator's flaky test and what was the actual race",
     "thread sanitizer tsan ci flaky test memory order release counter"),
    # --- 20 ---
    ("Java's ForkJoinPool.commonPool() is fine for short CPU tasks but we now create a dedicated ForkJoinPool per tenant; common-pool sharing across tenants caused noisy-neighbour latency spikes.", "decision", "ai_coding", False,
     [("ForkJoinPool", "library"), ("commonPool", "method"), ("tenant", "concept")],
     [],
     "why did the service stop sharing ForkJoinPool.commonPool across tenants",
     "forkjoinpool common pool tenant noisy neighbour latency dedicate"),
    # --- 21 ---
    ("Switched the search indexer's parallel stream to an explicit ForkJoinPool.submit so the work stays off the common pool; the change made p99 indexing time drop by 35 percent.", "milestone", "ai_coding", False,
     [("parallel stream", "pattern"), ("ForkJoinPool", "library"), ("search indexer", "service")],
     [("ForkJoinPool", "parallel stream", "REPLACES")],
     "how did moving parallel streams off the common pool affect search indexer latency",
     "parallel stream fork join pool submit common p99 indexer latency"),
    # --- 22 ---
    ("Cats Effect 3 fibers replaced the bespoke Future composition in the Scala pricing service; cancellation propagation and resource brackets removed two recurring leak classes.", "decision", "ai_coding", False,
     [("Cats Effect 3", "library"), ("fibers", "pattern"), ("Future", "api"), ("Scala", "language")],
     [("fibers", "Future", "REPLACES")],
     "which Scala effect system replaced raw Future composition in the pricing service",
     "cats effect fiber future scala cancel propagation resource bracket"),
    # --- 23 ---
    ("Kotlin coroutines now use supervisorScope around the upstream calls so one failed child doesn't cancel the siblings; coroutineScope is reserved for fail-fast pipelines.", "preference", "ai_coding", False,
     [("Kotlin", "language"), ("supervisorScope", "method"), ("coroutineScope", "method")],
     [],
     "when does the codebase pick supervisorScope over coroutineScope in Kotlin",
     "kotlin supervisor scope coroutine fail fast sibling cancel choice"),
    # --- 24 ---
    ("Trio's nursery API ships nicer cancel scopes than asyncio; the test harness uses trio.move_on_after to bound flaky integration steps without a global timeout decorator.", "fact", "ai_coding", False,
     [("Trio", "library"), ("nursery", "pattern"), ("move_on_after", "method"), ("asyncio", "library")],
     [("Trio", "asyncio", "IMPROVES_ON")],
     "which Trio API does the test harness use to bound flaky integration steps",
     "trio nursery cancel scope move on after timeout integration test"),
    # --- 25 ---
    ("Replaced ad-hoc futures.wait with concurrent.futures.as_completed in the batch translator; partial results stream out as workers finish instead of blocking on the slowest one.", "decision", "ai_coding", False,
     [("concurrent.futures", "library"), ("as_completed", "method"), ("batch translator", "service")],
     [("as_completed", "concurrent.futures", "USES")],
     "which futures iteration pattern lets the batch translator stream partial results",
     "as completed futures wait stream partial result slowest worker"),
    # --- 26 ---
    ("CompletableFuture chains in the Java order pipeline now run on a named ExecutorService; the default ForkJoinPool was hiding what was actually saturating CPU during a P1 incident.", "problem", "ai_coding", False,
     [("CompletableFuture", "library"), ("ExecutorService", "library"), ("ForkJoinPool", "library")],
     [("ExecutorService", "ForkJoinPool", "REPLACES")],
     "why did the Java pipeline move CompletableFuture chains off the default ForkJoinPool",
     "completable future executor service named fork join default p1 hide"),
    # --- 27 ---
    ("Async Rust select! with biased ordering keeps the cancellation branch first; without bias, the io branch starved cancel signals and shutdown took 30 seconds longer than budgeted.", "fact", "ai_coding", False,
     [("select!", "method"), ("biased", "config"), ("Rust", "language")],
     [],
     "which Rust select! tweak fixed slow cancellation in the async event loop",
     "rust select biased cancellation branch starvation shutdown budget"),
    # --- 28 ---
    ("Erlang processes for the chat fan-out cap mailbox depth using selective receive plus a high-water mark; senders get a {error, overload} reply and back off when the mailbox approaches the limit.", "architecture", "ai_coding", False,
     [("Erlang", "language"), ("selective receive", "pattern"), ("mailbox", "pattern"), ("chat fan-out", "service")],
     [],
     "how does the Erlang chat fan-out apply backpressure when actor mailboxes grow",
     "erlang process mailbox selective receive high water overload back"),
    # --- 29 ---
    ("Switched from std::thread spawning to rayon's par_iter on the embedding batcher; the work-stealing pool kept all cores busy without us hand-rolling a chunking strategy.", "decision", "ai_coding", False,
     [("std::thread", "library"), ("rayon", "library"), ("par_iter", "method"), ("embedding batcher", "service")],
     [("rayon", "std::thread", "REPLACES")],
     "which Rust parallel-iteration library replaced manual std::thread on the embedding batcher",
     "rayon par iter std thread work steal embedding batch chunk core"),
    # --- 30 ---
    ("OpenMP parallel for replaced a hand-written pthread fan-out in the simulation kernel; the schedule(dynamic, 64) clause smoothed out the imbalance on irregular workloads.", "milestone", "ai_coding", False,
     [("OpenMP", "framework"), ("pthread", "library"), ("schedule", "config"), ("simulation kernel", "service")],
     [("OpenMP", "pthread", "REPLACES")],
     "which OpenMP feature smoothed out imbalance after replacing pthread fan-out in the simulation kernel",
     "openmp parallel for pthread schedule dynamic chunk imbalance"),
    # --- 31 ---
    ("Disruptor's ring buffer replaced the LinkedBlockingQueue between the FIX gateway and the matcher; the lock-free SPSC path cut median latency from 220 microseconds to 14.", "milestone", "ai_coding", False,
     [("Disruptor", "library"), ("LinkedBlockingQueue", "library"), ("FIX gateway", "service"), ("matcher", "service")],
     [("Disruptor", "LinkedBlockingQueue", "REPLACES")],
     "which lock-free queue replaced LinkedBlockingQueue between the FIX gateway and matcher",
     "disruptor ring buffer linked blocking queue spsc latency matcher"),
    # --- 32 ---
    ("std::atomic<bool> with memory_order_acquire/release replaced a mutex-guarded shutdown flag in the C++ ingestion daemon; the hot read on every loop iteration stopped showing in perf top.", "decision", "ai_coding", False,
     [("std::atomic", "library"), ("memory_order_acquire", "method"), ("mutex", "pattern"), ("ingestion daemon", "service")],
     [("std::atomic", "mutex", "REPLACES")],
     "which C++ atomic pattern replaced the mutex-guarded shutdown flag and what did profiling show",
     "atomic acquire release mutex shutdown flag perf top hot read"),
    # --- 33 ---
    ("Reader-writer lock on the routing table flipped to a left-right concurrent data structure; readers no longer block during the once-a-minute config swap.", "architecture", "ai_coding", False,
     [("Reader-writer lock", "pattern"), ("left-right", "algorithm"), ("routing table", "pattern")],
     [("left-right", "Reader-writer lock", "REPLACES")],
     "which concurrent data structure replaced the routing-table reader-writer lock",
     "left right reader writer lock routing table swap reader block"),
    # --- 34 ---
    ("Switched the pub/sub topic map to a copy-on-write snapshot held behind an Arc; subscribers iterate a stable view while writers swap a fresh map atomically.", "decision", "ai_coding", False,
     [("copy-on-write", "pattern"), ("Arc", "library"), ("pub/sub", "pattern")],
     [("copy-on-write", "pub/sub", "APPLIES_TO")],
     "which copy-on-write pattern fronts the pub/sub topic map for lock-free reads",
     "copy on write arc snapshot pub sub topic map atomic swap reader"),
    # --- 35 ---
    ("Loom model checking caught a missed memory ordering in the lock-free queue's dequeue path; without exhaustive interleaving, the bug would have hit production once every billion ops.", "problem", "ai_coding", False,
     [("Loom", "tool"), ("lock-free queue", "pattern"), ("memory ordering", "concept")],
     [("Loom", "lock-free queue", "APPLIES_TO")],
     "which Rust model checker exposed the lock-free queue's missed memory ordering",
     "loom model check lock free queue dequeue memory order interleave"),
    # --- 36 ---
    ("Adopted the actor model in Pony for the pricing kernel; reference capabilities make data-race-free message passing a compile-time guarantee instead of a code-review hope.", "decision", "ai_coding", False,
     [("Pony", "language"), ("actor model", "pattern"), ("reference capabilities", "concept")],
     [("Pony", "actor model", "USES")],
     "which language brings compile-time data-race freedom to the pricing kernel actor model",
     "pony actor reference capability data race compile time pricing"),
    # --- 37 ---
    ("Python's GIL drove the ML inference workers to multiprocessing.Pool instead of threads; per-worker model warmup happens once at fork so steady-state requests skip the load cost.", "architecture", "ai_coding", False,
     [("GIL", "concept"), ("multiprocessing.Pool", "library"), ("inference workers", "service")],
     [("multiprocessing.Pool", "GIL", "RELATED_TO")],
     "why did the inference workers pick multiprocessing over threads and how is warmup amortised",
     "python gil multiprocessing pool fork warmup model inference worker"),
    # --- 38 ---
    ("Replaced thread-per-connection in the TCP echo server with epoll-driven non-blocking io via tokio::net::TcpListener; the C10K barrier on a single box stopped being a barrier.", "milestone", "ai_coding", False,
     [("epoll", "api"), ("tokio::net::TcpListener", "library"), ("thread-per-connection", "pattern"), ("TCP echo server", "service")],
     [("tokio::net::TcpListener", "thread-per-connection", "REPLACES")],
     "which io model replaced thread-per-connection on the TCP echo server",
     "epoll non blocking io tokio tcp listener thread per connection c10k"),
    # --- 39 ---
    ("Coroutine context switching in the python-asyncio event loop is roughly 200 ns; that's the budget we benchmark against when deciding whether a callback should be inlined or scheduled.", "reference", "ai_coding", False,
     [("python-asyncio", "library"), ("event loop", "pattern")],
     [],
     "what coroutine switch cost frames the inline-versus-schedule decision in the asyncio event loop",
     "python asyncio event loop coroutine switch cost budget inline"),
    # --- 40 ---
    ("Goroutine leak hunting uses pprof's /debug/pprof/goroutine endpoint plus a goleak.VerifyNone in every test teardown; a leaked ticker goroutine had been holding 30 MB of pinned closures.", "problem", "ai_coding", False,
     [("pprof", "tool"), ("goleak", "library"), ("ticker", "pattern")],
     [],
     "which Go tooling caught the leaked ticker goroutine and how do tests guard against regressions",
     "goroutine leak pprof goleak verify none ticker closure pin memory"),
    # --- 41 ---
    ("Channel select with a default branch is the non-blocking probe pattern in the Go scheduler shim; the default arm avoids the deadlock when no peer is ready and the loop has other work.", "fact", "ai_coding", False,
     [("Channel select", "pattern"), ("default branch", "pattern"), ("scheduler shim", "service")],
     [],
     "which Go select pattern gives a non-blocking probe in the scheduler shim",
     "go select default non blocking probe deadlock peer ready loop"),
    # --- 42 ---
    ("Async Rust hot loops avoid spawn_blocking for tiny CPU work; the task hand-off and channel cost dwarf the actual computation under a few microseconds, so we inline instead.", "preference", "ai_coding", False,
     [("spawn_blocking", "method"), ("Async Rust", "language")],
     [],
     "when do we skip spawn_blocking in async Rust hot loops and inline instead",
     "spawn blocking async rust hot loop hand off channel cost inline"),
    # --- 43 ---
    ("Quasar fibers were the JVM concurrency bet before Loom; the codebase migrated off Quasar to Project Loom virtual threads once Java 21 LTS shipped them stably.", "milestone", "ai_coding", False,
     [("Quasar", "library"), ("Loom", "project"), ("virtual threads", "pattern"), ("Java 21", "language")],
     [("Loom", "Quasar", "REPLACES")],
     "which JVM fiber library got replaced by Project Loom virtual threads in the codebase",
     "quasar fiber project loom virtual thread java 21 lts migrate jvm"),
    # --- 44 ---
    ("Ractor in Ruby 3 powers the parallel test runner; isolating mutable state per ractor lets specs share helpers without hitting the GVL bottleneck on multi-core boxes.", "architecture", "ai_coding", False,
     [("Ractor", "library"), ("Ruby 3", "language"), ("GVL", "concept"), ("parallel test runner", "service")],
     [("Ractor", "GVL", "REPLACES")],
     "which Ruby 3 primitive frees the parallel test runner from the GVL bottleneck",
     "ruby ractor gvl parallel test runner isolate state core multi"),
    # --- 45 ---
    ("Web worker pool in the document editor sizes itself to navigator.hardwareConcurrency minus one; leaving a core for the main thread kept input latency under a single frame budget.", "decision", "ai_coding", False,
     [("Web worker", "pattern"), ("navigator.hardwareConcurrency", "api"), ("document editor", "project")],
     [],
     "how does the document editor size its web worker pool and why subtract one",
     "web worker hardware concurrency main thread frame budget input"),
    # --- 46 ---
    ("SharedArrayBuffer with Atomics.wait/notify backs the cross-worker queue in the editor; postMessage round-trips were burning more CPU on JSON than the actual diff computation.", "decision", "ai_coding", False,
     [("SharedArrayBuffer", "api"), ("Atomics.wait", "method"), ("postMessage", "method")],
     [("SharedArrayBuffer", "postMessage", "REPLACES")],
     "which browser primitive replaced postMessage on the cross-worker queue in the editor",
     "shared array buffer atomics wait notify post message worker queue"),
    # --- 47 ---
    ("Adopted CSP-style channels via core.async on the Clojure data ingestion service; bounded chans make backpressure obvious and removed three custom state-machine files.", "decision", "ai_coding", False,
     [("core.async", "library"), ("CSP", "concept"), ("Clojure", "language"), ("data ingestion service", "service")],
     [("core.async", "CSP", "IMPLEMENTS")],
     "which Clojure library brought CSP channels and explicit backpressure to the ingestion service",
     "clojure core async csp channel bounded backpressure ingestion"),
    # --- 48 ---
    ("Fork/join of map-reduce tasks runs through Java's RecursiveTask with a sequential threshold of 1024; below the threshold the task computes inline instead of forking another subtask.", "fact", "ai_coding", False,
     [("RecursiveTask", "library"), ("Fork/join", "pattern"), ("map-reduce", "pattern")],
     [],
     "which Java fork-join class drives map-reduce tasks and how is the cutoff chosen",
     "recursive task fork join sequential threshold map reduce inline"),
    # --- 49. noise ---
    ("The downstairs cafe started selling a matcha cookie that nobody on the team can describe without giggling.", "fact", "noise", True, [], [], None, None),
    # --- 50 ---
    ("Reactor's parallel() with runOn(Schedulers.parallel()) replaced a hand-written CountDownLatch barrier in the report aggregator; cancellation now flows through the operator chain for free.", "milestone", "ai_coding", False,
     [("Reactor", "framework"), ("CountDownLatch", "library"), ("Schedulers.parallel", "method"), ("report aggregator", "service")],
     [("Reactor", "CountDownLatch", "REPLACES")],
     "which Reactor operator pair replaced the hand-written CountDownLatch in the report aggregator",
     "reactor parallel run on schedulers count down latch barrier report"),
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
