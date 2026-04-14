"""One-off emitter for shared-base batch-026 — ai_coding domain (debugging / profiling / perf).

Writes 50 rows to data/v2/shared/batch_026.tmp.jsonl with ids shared-01251..01300.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "shared" / "batch_026.tmp.jsonl"
ID_OFFSET = 1250

ENTRIES: list[tuple] = [
    # --- 1 ---
    ("py-spy sampling into a folded stack file gave us a flame graph that pinned a hot regex inside the request middleware.", "problem", "ai_coding", False,
     [("py-spy", "tool"), ("flame graph", "pattern"), ("middleware", "concept")],
     [],
     "which sampling profiler exposed the regex hot spot in the request path",
     "python sampling profiler folded stack regex middleware"),
    # --- 2 ---
    ("memray allocation tracing caught a per-request pandas frame copy that the RSS graph had smoothed into a slow climb.", "problem", "ai_coding", False,
     [("memray", "tool"), ("pandas", "library"), ("RSS", "concept")],
     [],
     "which allocator tracer revealed the frame copy hidden behind a gentle memory rise",
     "python allocation tracer dataframe copy leak resident set"),
    # --- 3 ---
    ("Node.js clinic.js doctor run pointed at event loop starvation from a sync bcrypt call; swapping to the async variant unblocked p99.", "problem", "ai_coding", False,
     [("clinic.js", "tool"), ("bcrypt", "library"), ("event loop", "concept")],
     [],
     "which Node diagnostic tool flagged the synchronous hash call blocking the loop",
     "Node event loop starvation sync hash async swap latency"),
    # --- 4 ---
    ("Chrome DevTools Performance panel recorded a main-thread long task we traced to a JSON.parse on a 14 MB payload during hydration.", "problem", "ai_coding", False,
     [("Chrome DevTools", "tool"), ("JSON.parse", "api"), ("hydration", "concept")],
     [],
     "which browser profiler pinned the hydration stall to a giant parse call",
     "browser performance panel long task parse payload hydrate"),
    # --- 5 ---
    ("perf record with dwarf call graphs finally resolved inlined frames in our Rust service; the flame graph stopped being a wall of question marks.", "milestone", "ai_coding", False,
     [("perf", "tool"), ("dwarf", "pattern"), ("Rust", "language"), ("flame graph", "pattern")],
     [],
     "which unwinding option fixed the missing symbols in Linux profiler output",
     "perf record dwarf unwind inline symbol resolution Rust"),
    # --- 6 ---
    ("dtrace on the Illumos host showed a block-device queue depth blowup under a compaction storm the application logs never mentioned.", "fact", "ai_coding", False,
     [("dtrace", "tool"), ("Illumos", "platform"), ("compaction", "concept")],
     [],
     "which dynamic tracer spotted the disk queue spike the app never logged",
     "illumos dynamic trace disk queue depth compaction storm"),
    # --- 7 ---
    ("USDT probes baked into the postgres binary let us correlate query stalls with lock-manager waits without patching the server.", "fact", "ai_coding", False,
     [("USDT", "technology"), ("postgres", "database"), ("lock-manager", "concept")],
     [],
     "which static tracepoints tied slow queries to lock waits without a recompile",
     "USDT static tracepoint postgres lock manager correlate"),
    # --- 8 ---
    ("bpftrace one-liner on syscall entry surfaced a read amplification we had blamed on the storage vendor for two sprints.", "problem", "ai_coding", False,
     [("bpftrace", "tool"), ("syscall", "concept")],
     [],
     "which eBPF one-liner caught the read amplification we had misattributed",
     "bpftrace syscall read amplification storage misdiagnosis"),
    # --- 9 ---
    ("Pixie auto-instrumentation on the staging cluster let the SRE team read HTTP spans without touching a single service image.", "decision", "ai_coding", False,
     [("Pixie", "tool"), ("staging cluster", "infrastructure"), ("HTTP", "protocol")],
     [],
     "which eBPF observability tool surfaced HTTP traces without rebuilding images",
     "eBPF auto instrument HTTP span cluster zero code change"),
    # --- 10. noise ---
    ("The microwave buzz in the next room kept breaking my concentration during the bug hunt.", "fact", "noise", True, [], [], None, None),
    # --- 11 ---
    ("Parca continuous profiling caught a slow memory leak in the API gateway that never tripped the Kubernetes OOMKill threshold.", "fact", "ai_coding", False,
     [("Parca", "tool"), ("API gateway", "service"), ("Kubernetes", "platform")],
     [],
     "which continuous profiler found the gateway leak that stayed under the kill limit",
     "continuous profile leak under threshold gateway cluster"),
    # --- 12 ---
    ("Grafana Pyroscope replaced our homegrown pprof scrape loop; differential flame graphs over deploys now take one click.", "decision", "ai_coding", False,
     [("Grafana Pyroscope", "tool"), ("pprof", "tool"), ("flame graph", "pattern")],
     [("Grafana Pyroscope", "pprof", "REPLACES")],
     "which continuous profiler took over from the hand-rolled pprof collection job",
     "pyroscope adoption diff flame graph deploy compare swap"),
    # --- 13 ---
    ("Attached gdb to a running pid with set scheduler-locking on; the stuck worker's backtrace showed a futex loop against a misused condvar.", "problem", "ai_coding", False,
     [("gdb", "tool"), ("futex", "concept"), ("condvar", "concept")],
     [],
     "how did we catch the stuck worker's kernel-level wait without killing the process",
     "gdb attach live pid backtrace futex condition variable"),
    # --- 14 ---
    ("rr record-and-replay on a flaky crypto test gave us reverse continue; stepping backwards from the abort found the uninitialised byte.", "problem", "ai_coding", False,
     [("rr", "tool"), ("reverse continue", "command")],
     [],
     "which time-travel debugger feature let us walk backwards from the crash",
     "record replay reverse step uninit memory abort trace"),
    # --- 15 ---
    ("Switched Rust benchmarks to a dedicated release profile with debug symbols; perf samples now map to function names instead of addresses.", "decision", "ai_coding", False,
     [("Rust", "language"), ("release profile", "config"), ("perf", "tool")],
     [],
     "which Rust build tweak made profiler samples resolve back to function names",
     "rust release debug symbol perf sample resolve profile"),
    # --- 16 ---
    ("Allocation sampling in Go's pprof showed a single json.Marshal call owning thirty percent of the heap churn during peak load.", "problem", "ai_coding", False,
     [("Go", "language"), ("pprof", "tool"), ("json.Marshal", "api")],
     [],
     "which profiler view pinned the dominant allocator during peak traffic",
     "go pprof alloc sample marshal heap churn peak"),
    # --- 17 ---
    ("Python 3.11 async stack traces finally print the awaiter chain end-to-end; chasing a stuck coroutine takes minutes, not an afternoon.", "milestone", "ai_coding", False,
     [("Python 3.11", "language"), ("coroutine", "concept")],
     [],
     "which interpreter upgrade made asynchronous tracebacks readable again",
     "python async traceback awaiter chain coroutine debug speedup"),
    # --- 18 ---
    ("Node heap snapshot diffs across two load tests found a Map that grew without bounds when the circuit breaker tripped in a specific order.", "problem", "ai_coding", False,
     [("Node", "platform"), ("heap snapshot", "pattern"), ("circuit breaker", "pattern")],
     [],
     "how did snapshot comparison expose the map leak tied to breaker ordering",
     "heap diff snapshot unbounded map breaker trip ordering"),
    # --- 19 ---
    ("Tuned GOGC to 200 and set GOMEMLIMIT just under the pod cap; GC pauses fell and OOMKills went to zero over the following week.", "decision", "ai_coding", False,
     [("GOGC", "config"), ("GOMEMLIMIT", "config"), ("GC", "concept")],
     [],
     "which Go runtime settings reduced both collector pauses and pod kills",
     "go gc tune soft memory limit pause oom kill drop"),
    # --- 20 ---
    ("Async task analytics via the asyncio task factory hook surfaced an unawaited coroutine leaking across every tenant.", "problem", "ai_coding", False,
     [("asyncio", "library"), ("task factory", "api"), ("coroutine", "concept")],
     [],
     "which asyncio introspection point caught the unawaited coroutine leak",
     "asyncio task factory hook unawaited leak tenant wide"),
    # --- 21 ---
    ("Traced a slow SQL query end-to-end through OpenTelemetry; the span tree showed the planner spending more time than execution itself.", "fact", "ai_coding", False,
     [("OpenTelemetry", "framework"), ("SQL", "language"), ("planner", "concept")],
     [],
     "which tracing system revealed the planner cost dominating a slow query",
     "otel span tree sql planner time execution breakdown"),
    # --- 22 ---
    ("Valgrind DHAT's block lifetime histogram pointed to a short-lived buffer we should have stack-allocated; hot path RSS dropped measurably.", "problem", "ai_coding", False,
     [("Valgrind", "tool"), ("DHAT", "tool"), ("RSS", "concept")],
     [],
     "which DHAT report pushed us to stack-allocate the short-lived buffer",
     "dhat block lifetime histogram stack allocation hot path"),
    # --- 23 ---
    ("Looking at off-CPU flame graphs made the real culprit obvious: workers spent most of their time parked on a semaphore, not burning cycles.", "fact", "ai_coding", False,
     [("off-CPU", "concept"), ("flame graph", "pattern"), ("semaphore", "concept")],
     [],
     "which alternative flame graph style exposed blocking time instead of CPU use",
     "off cpu flame graph semaphore wait blocking diagnosis"),
    # --- 24 ---
    ("Prefer off-CPU flame graphs over on-CPU ones for diagnosing latency issues; wall-clock waits usually dominate the user-visible budget.", "preference", "ai_coding", False,
     [("off-CPU", "concept"), ("on-CPU", "concept"), ("flame graph", "pattern")],
     [],
     "which flame graph flavour wins for chasing user-visible latency",
     "off cpu vs on cpu flame graph latency pick wall clock"),
    # --- 25 ---
    ("Java Flight Recorder captured a continuous low-overhead profile in production; the allocation-by-class view found a hidden boxing cascade.", "fact", "ai_coding", False,
     [("Java Flight Recorder", "tool"), ("allocation-by-class", "pattern"), ("boxing", "concept")],
     [],
     "which JVM profiler found the boxing cascade while staying cheap in prod",
     "jfr production low overhead allocation class boxing chain"),
    # --- 26 ---
    ("Perfetto traces from the Android client lined up frame misses with a binder call into a system service that occasionally stalled.", "problem", "ai_coding", False,
     [("Perfetto", "tool"), ("Android", "platform"), ("binder", "protocol")],
     [],
     "which tracing tool correlated dropped frames with a cross-process call",
     "perfetto android frame miss binder system service stall"),
    # --- 27 ---
    ("Xdebug profiler traces tipped off a PHP template helper that called a database lookup inside a loop over menu items.", "problem", "ai_coding", False,
     [("Xdebug", "tool"), ("PHP", "language"), ("database", "concept")],
     [],
     "which PHP profiler surfaced the database call buried inside a render loop",
     "xdebug php template helper db call inside loop menu"),
    # --- 28 ---
    ("Ruby stackprof sampled the Sidekiq workers and the top frame was Marshal.load on cached jobs — a swap to MessagePack shaved forty percent.", "milestone", "ai_coding", False,
     [("stackprof", "tool"), ("Sidekiq", "library"), ("Marshal.load", "api"), ("MessagePack", "library")],
     [("MessagePack", "Marshal.load", "REPLACES")],
     "which Ruby sampling profiler prompted the serialisation swap in background workers",
     "stackprof sidekiq marshal swap messagepack speedup"),
    # --- 29 ---
    ("PHP spx produced a call-graph that made one Laravel middleware's regex dominance embarrassingly visible; the offending rule was simplified.", "problem", "ai_coding", False,
     [("PHP spx", "tool"), ("Laravel", "framework")],
     [],
     "which PHP profiler exposed the middleware regex dominance",
     "php spx laravel middleware regex call graph cleanup"),
    # --- 30 ---
    (".NET PerfView exposed GC heap retention rooted at a static event handler that never detached; the memory curve flattened after the fix.", "problem", "ai_coding", False,
     [(".NET", "platform"), ("PerfView", "tool"), ("event handler", "concept")],
     [],
     "which .NET profiler pinned the static event leak retaining objects forever",
     "perfview static event leak root retain dotnet heap"),
    # --- 31 ---
    ("dotTrace's timeline view lined up a UI stutter with a background thread's lock contention on a logging queue during bursts.", "problem", "ai_coding", False,
     [("dotTrace", "tool"), ("UI", "concept"), ("logging queue", "concept")],
     [],
     "which .NET profiler matched UI stutter with background lock contention",
     "dotTrace timeline stutter background lock log queue"),
    # --- 32 ---
    ("JetBrains profiler integrated into Rider made attach-and-sample a menu item; adoption inside the team went from rare to default.", "fact", "ai_coding", False,
     [("JetBrains profiler", "tool"), ("Rider", "tool")],
     [],
     "which IDE change made attaching a profiler frictionless for the .NET folks",
     "jetbrains profiler rider attach sample menu adoption"),
    # --- 33 ---
    ("Xcode Instruments' Time Profiler template caught a main-thread layout storm triggered by an offscreen table view's auto-sizing pass.", "problem", "ai_coding", False,
     [("Xcode", "tool"), ("Instruments", "tool"), ("Time Profiler", "pattern")],
     [],
     "which Apple profiler exposed the offscreen layout storm on the UI thread",
     "xcode instruments time profiler layout storm table"),
    # --- 34 ---
    ("BPF CO-RE let us ship a single eBPF binary across kernel versions without recompile; operator pain during rollouts dropped to near zero.", "milestone", "ai_coding", False,
     [("BPF CO-RE", "technology"), ("eBPF", "technology")],
     [],
     "which eBPF portability feature killed the per-kernel recompile headache",
     "bpf core portability eBPF kernel version ship single binary"),
    # --- 35 ---
    ("Programmed the PMU to count LLC-misses per function; the hottest loop turned out to be chasing pointers across a fragmented arena.", "problem", "ai_coding", False,
     [("PMU", "technology"), ("LLC", "concept")],
     [],
     "which hardware counter configuration revealed the cache-miss hot loop",
     "pmu counter last level cache miss pointer chase arena"),
    # --- 36 ---
    ("Datadog continuous profiling correlated request traces with CPU flame graphs; stepping from a slow span to its sampled frames took one click.", "fact", "ai_coding", False,
     [("Datadog", "service"), ("flame graph", "pattern")],
     [],
     "which vendor tool tied request traces to sampled CPU frames directly",
     "datadog continuous profile trace flame graph jump"),
    # --- 37 ---
    ("Grafana Pyroscope's diff mode between two deploy tags caught a regression in a templating helper before the synthetic monitor fired.", "milestone", "ai_coding", False,
     [("Grafana Pyroscope", "tool"), ("synthetic monitor", "concept"), ("templating helper", "concept")],
     [],
     "which profiler diff feature caught the regression ahead of the synthetic check",
     "pyroscope diff deploy tag regression template helper"),
    # --- 38 ---
    ("Turned on Linux perf's LBR sampling for a short window; branch-misprediction hot spots in the JIT stood out like headlights.", "fact", "ai_coding", False,
     [("perf", "tool"), ("LBR", "technology"), ("JIT", "concept")],
     [],
     "which perf mode made branch-misprediction issues in the JIT obvious",
     "perf lbr branch miss sample jit hotspot short window"),
    # --- 39 ---
    ("Prefer bpftrace one-liners for quick production diagnosis over writing a long C BPF program; the turnaround wins outweigh the ceiling.", "preference", "ai_coding", False,
     [("bpftrace", "tool"), ("BPF", "technology"), ("C", "language")],
     [("bpftrace", "C", "PREFERS")],
     "which eBPF style wins for fast production investigations",
     "bpftrace one liner vs c bpf program turnaround pick"),
    # --- 40 ---
    ("The debug builds of the Rust service hid a scaling cliff by making a quadratic helper fast enough; release builds exposed it immediately.", "problem", "ai_coding", False,
     [("Rust", "language"), ("debug builds", "config"), ("release builds", "config")],
     [],
     "why did the scaling cliff only show up when we switched build flavours",
     "debug vs release rust quadratic helper cliff surface"),
    # --- 41 ---
    ("Recorded a flight recorder dump on the prod JVM during a stall; the thread dump in the same bundle showed a blocked class loader lock.", "problem", "ai_coding", False,
     [("flight recorder", "tool"), ("JVM", "platform"), ("class loader lock", "concept")],
     [],
     "which JVM capture combined timing and thread state to find the loader stall",
     "jfr thread dump class loader lock stall diagnosis"),
    # --- 42 ---
    ("Wrapped our Tokio runtime with the console subscriber; awaiting tasks got listed by time-blocked, which flushed out a poorly bounded channel.", "problem", "ai_coding", False,
     [("Tokio", "library"), ("console subscriber", "tool"), ("channel", "concept")],
     [],
     "which Tokio diagnostic listed async tasks by blocked time and found the channel",
     "tokio console subscriber task block time channel bound"),
    # --- 43 ---
    ("Set up an async-profiler agent on the Kotlin service with the alloc event; the allocation profile clipped several boxing hot spots.", "fact", "ai_coding", False,
     [("async-profiler", "tool"), ("Kotlin", "language"), ("alloc event", "pattern")],
     [],
     "which JVM sampling profiler surfaced the boxing allocator hot spots",
     "async profiler kotlin alloc event boxing hotspot"),
    # --- 44 ---
    ("Hooked eBPF tcpretrans into the observability stack; a low-grade packet-loss pattern between two AZs finally had a smoking-gun graph.", "problem", "ai_coding", False,
     [("eBPF", "technology"), ("tcpretrans", "tool"), ("AZ", "infrastructure")],
     [],
     "which kernel tracing tool finally proved the cross-zone packet loss",
     "ebpf tcp retrans pattern loss zone pair graph evidence"),
    # --- 45 ---
    ("Switched CPython builds used in perf runs to the no-gil preview; single-process scaling improved but GC tuning had to come back to the table.", "fact", "ai_coding", False,
     [("CPython", "language"), ("no-gil", "config"), ("GC", "concept")],
     [],
     "which interpreter variant reopened the collector tuning discussion",
     "cpython no gil preview single process scaling gc tune"),
    # --- 46 ---
    ("Captured a core dump with coredumpctl and loaded it in gdb back in the office; post-mortem beat trying to catch the crash live under load.", "decision", "ai_coding", False,
     [("coredumpctl", "tool"), ("gdb", "tool"), ("core dump", "pattern")],
     [],
     "which approach beat live reproduction for a hard-to-reproduce production crash",
     "coredumpctl core dump gdb post mortem vs live repro"),
    # --- 47 ---
    ("Rewired the V8 heap snapshot pipeline into a nightly CI job; leak regressions now fail the build the day they land, not two weeks later.", "milestone", "ai_coding", False,
     [("V8", "platform"), ("heap snapshot", "pattern"), ("CI", "infrastructure")],
     [],
     "which automation flipped Node leaks from late surprise to same-day failure",
     "v8 heap snapshot ci nightly leak regression fast feedback"),
    # --- 48 ---
    ("Enabled sampling allocation profiling in Go continuously with a low rate; the cost stayed under one percent and we kept a year of history.", "decision", "ai_coding", False,
     [("Go", "language"), ("allocation profiling", "pattern")],
     [],
     "which always-on profiling choice stayed cheap while giving long-term history",
     "go alloc sample continuous low rate overhead history"),
    # --- 49 ---
    ("PerfView's GC heap snapshot diff tied a slow leak to a collection cached in a DI container; scoping the dependency as transient cleared it.", "problem", "ai_coding", False,
     [("PerfView", "tool"), ("DI container", "pattern"), ("transient", "config")],
     [],
     "which .NET heap diff pointed at a mis-scoped DI registration",
     "perfview heap diff di container scope transient leak"),
    # --- 50 ---
    ("Adopted Parca Agent cluster-wide on 2026-03-18; symbolised profiles for every language runtime now live in one place for on-call.", "milestone", "ai_coding", False,
     [("Parca Agent", "tool"), ("2026-03-18", "date")],
     [],
     "when did cluster-wide continuous profiling become available for the on-call team",
     "parca agent cluster rollout symbolise runtime unified date"),
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
