"""One-off emitter for shared-base batch-038 — technical domain (programming languages / runtimes / compilers / VMs slice).

Writes 50 rows to data/v2/shared/batch_038.tmp.jsonl with ids shared-01851..01900.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "shared" / "batch_038.tmp.jsonl"
ID_OFFSET = 1850

ENTRIES: list[tuple] = [
    # --- 1 ---
    ("GraalVM native-image cut the Micronaut service cold start from 1.4 s to 38 ms; a tracing agent run produced the reflection config.", "milestone", "technical", False,
     [("GraalVM", "platform"), ("Micronaut", "framework")],
     [],
     "which ahead-of-time build collapsed the Micronaut service cold start",
     "native image cold start reflection tracing agent reduce"),
    # --- 2 ---
    ("GraalVM's reflection caveat hit the Jackson polymorphic deserialiser; we added reachability-metadata entries rather than fall back to JIT mode.", "problem", "technical", False,
     [("GraalVM", "platform"), ("Jackson", "library")],
     [],
     "which native-image pitfall did the polymorphic deserialiser trigger",
     "reflection metadata polymorphic deserialiser caveat fix"),
    # --- 3 ---
    ("OpenJDK ZGC replaced G1 on the low-latency trading gateway; tail pauses dropped under 1 ms once generational ZGC stabilised.", "decision", "technical", False,
     [("OpenJDK", "platform"), ("ZGC", "algorithm"), ("G1", "algorithm")],
     [("ZGC", "G1", "REPLACES")],
     "which collector took over from G1 on the latency-critical gateway",
     "generational concurrent collector tail pause sub millisecond"),
    # --- 4 ---
    ("Shenandoah was evaluated against ZGC for the analytics JVM; ZGC won on heap-size scaling past 200 GB, Shenandoah stayed on the smaller services.", "decision", "technical", False,
     [("Shenandoah", "algorithm"), ("ZGC", "algorithm"), ("JVM", "platform")],
     [],
     "which collector won the large-heap bake-off against Shenandoah",
     "large heap scaling concurrent collector bake off compare"),
    # --- 5 ---
    ("Project Loom virtual threads swept out the Netty thread-pool juggling in the request handler; blocking JDBC calls stopped starving the executor.", "decision", "technical", False,
     [("Project Loom", "technology"), ("Netty", "framework"), ("JDBC", "protocol")],
     [("Project Loom", "Netty", "REPLACES")],
     "which JVM feature retired the bespoke event-loop thread pools",
     "virtual thread blocking IO starvation executor remove"),
    # --- 6 ---
    ("Project Panama's foreign linker replaced JNI for the ICU4C bindings; startup cost per call dropped and the Java side stayed type-safe.", "decision", "technical", False,
     [("Project Panama", "technology"), ("JNI", "protocol"), ("ICU4C", "library")],
     [("Project Panama", "JNI", "REPLACES")],
     "which native interop layer took over from JNI for the ICU bindings",
     "foreign linker native interop type safe per call cost"),
    # --- 7 ---
    ("Project Valhalla value types landed for the coordinate class; heap footprint on the map tiles pipeline shrank by roughly a third.", "milestone", "technical", False,
     [("Project Valhalla", "technology")],
     [],
     "which JVM preview feature shrank the coordinate class heap footprint",
     "value type flattened layout coordinate heap reduction"),
    # --- 8 ---
    ("Truffle interpreters on GraalVM let us reuse the PEG parser across the policy DSL and the scripting dialect; partial evaluation covered the speed gap.", "architecture", "technical", False,
     [("Truffle", "framework"), ("GraalVM", "platform")],
     [],
     "which framework let one interpreter skeleton drive two DSL dialects",
     "partial evaluation DSL reuse parser interpreter skeleton"),
    # --- 9 ---
    ("V8 hidden classes penalised our event object when a late-added field changed the shape; pre-declaring all fields in the constructor restored inline caches.", "problem", "technical", False,
     [("V8", "platform")],
     [],
     "which V8 optimisation did the late field assignment break",
     "hidden class inline cache shape transition pre declare"),
    # --- 10. noise ---
    ("One sec, I need to find that benchmark log.", "fact", "noise", True, [], [], None, None),
    # --- 11 ---
    ("Node 22's permission model scoped the build tool to an allowlist of paths; the postinstall exfiltration class of attack stopped applying.", "decision", "technical", False,
     [("Node 22", "platform")],
     [],
     "which Node feature sandboxed the build tool's filesystem reach",
     "permission allowlist postinstall sandbox runtime scope"),
    # --- 12 ---
    ("Deno KV backed the session store for the edge worker; strong consistency on single-region reads kept the auth middleware simple.", "architecture", "technical", False,
     [("Deno KV", "database")],
     [],
     "which built-in Deno store holds the edge worker's session data",
     "edge session single region consistent KV built in"),
    # --- 13 ---
    ("Bun runtime's fetch internals reuse a single HTTP client per origin; our webhook fan-out saw connection churn drop sharply after the port.", "fact", "technical", False,
     [("Bun", "platform")],
     [],
     "which Bun runtime detail cut connection churn on the webhook fan-out",
     "per origin client reuse connection churn fetch internals"),
    # --- 14 ---
    ("CPython's adaptive interpreter from PEP 659 specialised the hot attribute-access bytecode; numeric loops sped up without touching C extensions.", "fact", "technical", False,
     [("CPython", "language"), ("PEP 659", "publication")],
     [],
     "which CPython change sped up numeric loops without C extensions",
     "adaptive specialising bytecode attribute access speedup"),
    # --- 15 ---
    ("PyPy JIT warmup was still the sticking point for short CLI runs; we kept CPython on the short-lived admin scripts and pushed PyPy to the long workers.", "decision", "technical", False,
     [("PyPy", "platform"), ("CPython", "language")],
     [],
     "why did the admin CLI scripts stay on CPython rather than PyPy",
     "warmup cost short lived process workload split"),
    # --- 16 ---
    ("Ruby YJIT delivered roughly 1.4x on the Rails dashboard endpoints; the memory uplift was tolerable after raising the exec-mem cap.", "milestone", "technical", False,
     [("Ruby", "language"), ("YJIT", "algorithm"), ("Rails", "framework")],
     [],
     "which Ruby JIT produced the Rails dashboard speed-up",
     "Rails endpoint speedup exec mem cap JIT lazy basic block"),
    # --- 17 ---
    ("Erlang/BEAM hot code reload shipped the pricing logic fix with zero dropped sessions; the two-version module load ran the old callers to completion.", "milestone", "technical", False,
     [("Erlang", "language"), ("BEAM", "platform")],
     [],
     "which BEAM feature let the pricing fix land without dropping sessions",
     "hot code reload two version module callers drain"),
    # --- 18 ---
    ("Elixir LiveView drove the dashboard with server-rendered diffs; the JS bundle shrank to the LiveView client and a small morphdom patch.", "architecture", "technical", False,
     [("Elixir", "language"), ("LiveView", "framework"), ("morphdom", "library")],
     [],
     "which server-driven UI framework replaced the old SPA dashboard build",
     "server rendered diff small client bundle dashboard morphdom"),
    # --- 19 ---
    ("Crystal's type inference carried the CLI rewrite with almost no annotations; compile times stayed sharp because incremental codegen reuses ll.bc cache.", "fact", "technical", False,
     [("Crystal", "language")],
     [],
     "which Crystal compiler trait kept the CLI rewrite annotation-light",
     "type inference incremental bitcode cache CLI rewrite"),
    # --- 20 ---
    ("Nim's ORC memory model replaced the older ARC variant for the backend daemon; cycle collection stopped the Monday memory growth.", "decision", "technical", False,
     [("Nim", "language"), ("ORC", "algorithm"), ("ARC", "algorithm")],
     [("ORC", "ARC", "REPLACES")],
     "which Nim memory strategy ended the daemon's weekly memory creep",
     "cycle collector reference counting daemon memory drift"),
    # --- 21 ---
    ("Zig comptime generated the protocol parser at build time from the schema constant; the runtime dispatch table vanished from the hot path.", "architecture", "technical", False,
     [("Zig", "language")],
     [],
     "which Zig feature removed the runtime dispatch table from the parser",
     "compile time metaprogramming schema parser dispatch elide"),
    # --- 22 ---
    ("Rust GATs let the async Stream adapter stay zero-cost; we dropped the boxed-future shim the library had carried since 2021.", "milestone", "technical", False,
     [("Rust", "language"), ("GATs", "technology")],
     [],
     "which Rust language feature retired the boxed-future shim",
     "generic associated type zero cost async stream shim"),
    # --- 23 ---
    ("Async traits in stable Rust closed out the last dyn-compat workaround for the plugin interface; the `#[async_trait]` crate came out of the dependency tree.", "decision", "technical", False,
     [("Rust", "language"), ("Async traits", "technology"), ("async_trait", "library")],
     [("Async traits", "async_trait", "REPLACES")],
     "which stabilised Rust feature dropped the async_trait crate dependency",
     "native async trait dyn compat plugin interface stable"),
    # --- 24 ---
    ("Go generics adoption stalled on the older data pipeline; constraint-heavy interfaces felt uglier than the interface{} it replaced, so we held the refactor.", "problem", "technical", False,
     [("Go", "language")],
     [],
     "why did the data pipeline refactor to Go generics get parked",
     "type parameter constraint interface empty readability regression"),
    # --- 25 ---
    ("Kotlin Multiplatform shared the domain models and the networking layer across Android and iOS; the view layer stayed native on each side.", "architecture", "technical", False,
     [("Kotlin Multiplatform", "framework"), ("Android", "platform"), ("iOS", "platform")],
     [],
     "which code layers ended up shared across mobile targets",
     "shared domain network native view cross platform split"),
    # --- 26 ---
    ("Scala 3 inline metaprogramming replaced the old macro-paradise plugins for the schema derivation library; compile errors finally pointed at user code.", "decision", "technical", False,
     [("Scala 3", "language"), ("macro-paradise", "library")],
     [("Scala 3", "macro-paradise", "REPLACES")],
     "which Scala 3 facility unseated the macro-paradise plugin stack",
     "inline macro quoted expression derivation error site"),
    # --- 27 ---
    ("Swift macros generated the Codable conformances for the networking DTOs; the build skipped the previous SwiftSyntax-based code-gen step entirely.", "milestone", "technical", False,
     [("Swift macros", "technology"), ("Codable", "api"), ("SwiftSyntax", "library")],
     [("Swift macros", "SwiftSyntax", "REPLACES")],
     "which Swift feature replaced the standalone SwiftSyntax codegen pass",
     "compile time macro codegen conformance generate skip"),
    # --- 28 ---
    ("OCaml multicore's domains unblocked the SAT encoder; CPU utilisation on the 16-core runner finally climbed past the old one-core ceiling.", "milestone", "technical", False,
     [("OCaml", "language")],
     [],
     "which OCaml evolution let the SAT encoder use more than one core",
     "multicore domain parallelism utilisation runner ceiling"),
    # --- 29 ---
    ("Roc's lambda sets closed the closure-allocation question for the platform; every callback site compiled to a flat tag union with no boxing.", "fact", "technical", False,
     [("Roc", "language")],
     [],
     "which Roc mechanism eliminates callback allocations on the platform",
     "lambda set tag union closure allocation compile"),
    # --- 30 ---
    ("Gleam's OTP wrappers let the BEAM team adopt the language without rewriting their supervision trees; interop stayed symmetric with Erlang modules.", "fact", "technical", False,
     [("Gleam", "language"), ("OTP", "framework"), ("Erlang", "language")],
     [],
     "which Gleam library tied the new service into the existing OTP supervisors",
     "typed wrapper supervisor tree Erlang interop adoption"),
    # --- 31 ---
    ("F# computation expressions modelled the retry/timeout DSL for the payments client; each effect stayed inspectable rather than hiding behind Task.", "architecture", "technical", False,
     [("F#", "language")],
     [],
     "which F# feature hosts the payments client's retry DSL",
     "computation expression builder effect inspect retry timeout"),
    # --- 32 ---
    ("WebAssembly component model let the image-processing plugin ship as a single .wasm file; the host imports were described by a WIT world at build time.", "architecture", "technical", False,
     [("WebAssembly", "technology"), ("WIT", "protocol")],
     [],
     "which WebAssembly standard packaged the plugin with its host imports",
     "component WIT world single artifact plugin host import"),
    # --- 33 ---
    ("WASI 0.2 landed the preview2 filesystem and sockets API; our CLI dropped the custom polyfill for standard input handling.", "milestone", "technical", False,
     [("WASI 0.2", "technology")],
     [],
     "which WASI release retired the custom stdin polyfill in the CLI",
     "preview2 filesystem sockets standard stdin polyfill drop"),
    # --- 34. noise ---
    ("Hold on, pulling up the flame graph now.", "fact", "noise", True, [], [], None, None),
    # --- 35 ---
    ("Cranelift backend in wasmtime compiled the cold functions about 6x faster than the old LLVM path; steady-state performance sits within 10 percent.", "fact", "technical", False,
     [("Cranelift", "technology"), ("wasmtime", "platform"), ("LLVM", "framework")],
     [("Cranelift", "LLVM", "REPLACES")],
     "which wasmtime backend traded steady-state speed for faster compiles",
     "cold compile time backend codegen tradeoff steady state"),
    # --- 36 ---
    ("Dafny verification caught the off-by-one in the ring-buffer enqueue before merge; the Hoare proof required a decreases clause we had missed.", "milestone", "technical", False,
     [("Dafny", "language")],
     [],
     "which verifier caught the ring-buffer off-by-one pre-merge",
     "formal proof decreases clause ring buffer invariant"),
    # --- 37 ---
    ("Idris elaborator reflection generated the JSON codec at type-check time; the library shipped without a separate derivation macro.", "architecture", "technical", False,
     [("Idris", "language")],
     [],
     "which Idris feature derived the JSON codec without a separate macro",
     "elaborator reflection compile time derivation typecheck"),
    # --- 38 ---
    ("MLIR dialects carried the tensor IR from the frontend down to the vendor backend; the old monolithic IR was split into three dialects for clarity.", "architecture", "technical", False,
     [("MLIR", "framework")],
     [],
     "which compiler infrastructure split the tensor IR into layered dialects",
     "multi level IR dialect lowering tensor vendor backend"),
    # --- 39 ---
    ("LLVM 19's updated ThinLTO cache invalidation avoided the full re-link on small header edits; CI link time dropped another 18 percent.", "milestone", "technical", False,
     [("LLVM 19", "framework")],
     [],
     "which LLVM update shortened incremental CI link times after header edits",
     "ThinLTO cache invalidation incremental header edit relink"),
    # --- 40 ---
    ("CRaC checkpoint/restore cut the Spring Boot startup to under 100 ms for the canary fleet; warm caches persisted across the restore.", "decision", "technical", False,
     [("CRaC", "technology"), ("Spring Boot", "framework")],
     [],
     "which JDK feature gave the Spring Boot canaries sub-100 ms start",
     "checkpoint restore warm cache startup canary fleet"),
    # --- 41 ---
    ("OpenJ9 stayed on the long-running batch JVMs; class data sharing and shared caches kept footprint lower than HotSpot for our workload.", "preference", "technical", False,
     [("OpenJ9", "platform"), ("HotSpot", "platform")],
     [("OpenJ9", "HotSpot", "PREFERS")],
     "which JVM holds the batch workers over HotSpot and why",
     "class data sharing shared cache footprint batch preference"),
    # --- 42 ---
    ("Julia's package precompilation finally cached native code on 1.9; the first-plot latency complaint stopped landing in the issue tracker.", "milestone", "technical", False,
     [("Julia", "language")],
     [],
     "which Julia release ended the first-plot latency complaints",
     "precompile native cache first use latency plot"),
    # --- 43 ---
    ("Mojo's MLIR-based compile pipeline lets Python-like code lower to vendor kernels without a C extension; the fast path stays readable.", "fact", "technical", False,
     [("Mojo", "language"), ("MLIR", "framework"), ("Python", "language")],
     [],
     "which Mojo design choice keeps the accelerator fast path readable",
     "Python syntax MLIR lower vendor kernel readable fast path"),
    # --- 44 ---
    ("GCC 14's -fhardened umbrella flag switched on the whole mitigation set for the firmware build; we dropped the bespoke flag list we had maintained since 2021.", "decision", "technical", False,
     [("GCC 14", "framework")],
     [],
     "which GCC flag collapsed the firmware hardening flag list",
     "hardened umbrella flag mitigation firmware bespoke retire"),
    # --- 45 ---
    ("Haskell GHC 9.10's delimited continuations primitive let the effect library drop its CPS-transform workaround; type errors improved markedly.", "milestone", "technical", False,
     [("Haskell", "language"), ("GHC 9.10", "framework")],
     [],
     "which GHC primitive retired the effect library's CPS-transform shim",
     "delimited continuation primitive effect CPS shim drop"),
    # --- 46 ---
    ("D's BetterC subset powered the embedded bootloader; runtime-free code kept the binary under 32 KB while keeping the source readable.", "architecture", "technical", False,
     [("D", "language"), ("BetterC", "technology")],
     [],
     "which D subset underlies the 32 KB bootloader build",
     "runtime free subset embedded bootloader binary size"),
    # --- 47 ---
    ("Chicken Scheme's blocking-mode GC made the interactive pricing tool's latency predictable; the generational mode had been hitting a 20 ms tail spike.", "decision", "technical", False,
     [("Chicken Scheme", "language")],
     [],
     "which Chicken Scheme GC mode fixed the pricing tool's tail spikes",
     "blocking mode collector tail latency spike predictable"),
    # --- 48 ---
    ("Erlang JIT (BeamAsm) on OTP 26 gave the routing service ~30 percent throughput; no source changes were required, just the runtime upgrade.", "milestone", "technical", False,
     [("Erlang", "language"), ("BeamAsm", "algorithm"), ("OTP 26", "platform")],
     [],
     "which BEAM JIT release produced the routing service speed-up",
     "BeamAsm OTP runtime upgrade throughput no source change"),
    # --- 49 ---
    ("LuaJIT's trace compiler still beat every port candidate on the rules engine; the fallback list stayed short because NYI blacklists caught escapes fast.", "preference", "technical", False,
     [("LuaJIT", "platform")],
     [],
     "why did the rules engine stay on LuaJIT after the port evaluations",
     "trace compiler NYI blacklist rules engine port decision"),
    # --- 50 ---
    ("TypeScript 5.5 inferred the types on our regex capture groups; the hand-written d.ts overrides for the URL parser came out of the tree.", "milestone", "technical", False,
     [("TypeScript 5.5", "language")],
     [],
     "which TypeScript release let us delete the regex capture d.ts overrides",
     "regex capture group type inference d ts override drop"),
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
