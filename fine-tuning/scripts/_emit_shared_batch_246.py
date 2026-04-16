"""One-off emitter for shared-base batch-246 — technical domain (WebAssembly and WASI: core spec, proposals, component model, WIT, WASI previews, runtimes, tooling, edge platforms, plugin systems, source languages).

Writes 50 rows to data/v2/shared/batch_246.tmp.jsonl with ids shared-12251..12300.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "shared" / "batch_246.tmp.jsonl"
ID_OFFSET = 12250

# (text, memory_type, domain, noise, entities, relationships, qq, qk)
ENTRIES: list[tuple] = [
    # --- 1 ---
    ("The Wasm MVP froze the core instruction set at 1.0 in 2019 and anchors every downstream runtime; later proposals bolt onto this baseline without breaking module decoding.", "reference", "technical", False,
     [("Wasm MVP", "technology"), ("core instruction set", "concept")],
     [("Wasm MVP", "core instruction set", "HAS_PART")],
     "which WebAssembly milestone froze the baseline instruction set and what does it guarantee for later proposals",
     "wasm mvp 1.0 core instruction baseline module decode proposal"),
    # --- 2 ---
    ("Switched the host SDK from wasmer to wasmtime after benchmarking cold-start on a cached module; wasmtime's Cranelift tier hit first instruction in under three milliseconds against wasmer's LLVM backend at twelve.", "decision", "technical", False,
     [("wasmer", "framework"), ("wasmtime", "framework"), ("Cranelift", "tool"), ("LLVM", "tool")],
     [("wasmtime", "wasmer", "REPLACES"), ("wasmtime", "Cranelift", "USES")],
     "which Wasm runtime swap did the host SDK land on and what cold-start measurement drove the choice",
     "wasmtime wasmer cranelift llvm cold start benchmark host sdk"),
    # --- 3 ---
    ("The reference-types proposal landed in wasmtime 0.27 and unlocked externref as a first-class value; the plugin layer can now pass host handles around without a side-table of integer keys.", "milestone", "technical", False,
     [("reference-types", "concept"), ("wasmtime", "framework"), ("externref", "concept")],
     [("reference-types", "externref", "HAS_PART")],
     "which Wasm proposal introduced externref into wasmtime and what side-table did it retire for plugin handles",
     "reference types externref wasmtime plugin handle side table integer"),
    # --- 4 ---
    ("Multi-value returns replaced the old single-return ABI in the codegen path; a tuple of i32 and i64 rides back on the stack directly, so the wrapper shim that spilled the second value through a pointer is gone.", "architecture", "technical", False,
     [("Multi-value returns", "concept"), ("single-return ABI", "concept"), ("codegen", "concept")],
     [("Multi-value returns", "single-return ABI", "REPLACES")],
     "which ABI change let the codegen return tuples directly and what wrapper shim did it eliminate",
     "multi value return abi tuple stack wrapper shim pointer spill"),
    # --- 5 ---
    ("SIMD in Wasm maps to v128 and a fixed set of 128-bit operations; the engine lowers them to SSE4 on x86 and NEON on arm64 at compile time so the module binary stays portable.", "fact", "technical", False,
     [("SIMD", "concept"), ("v128", "concept"), ("SSE4", "technology"), ("NEON", "technology")],
     [("SIMD", "v128", "HAS_PART")],
     "how does Wasm SIMD stay portable while still hitting native vector instructions on x86 and arm64",
     "simd v128 sse4 neon lower compile portable wasm vector"),
    # --- 6 ---
    ("Enabled the threads proposal on the wasmtime embedder with shared-memory linear memories; the atomics operations let the Rust compile target use std::sync::Mutex without the single-threaded runtime fallback.", "milestone", "technical", False,
     [("threads proposal", "concept"), ("wasmtime", "framework"), ("shared-memory", "concept"), ("Rust", "language")],
     [("threads proposal", "shared-memory", "USES")],
     "which Wasm proposal unlocked shared-memory and atomics in wasmtime for the Rust compile target",
     "threads proposal shared memory atomic wasmtime rust mutex embedder"),
    # --- 7 ---
    ("The exceptions proposal brings try/catch primitives into Wasm itself; the old trampoline that marshalled longjmp through a host import got deleted once wasmtime and V8 both shipped native support.", "decision", "technical", False,
     [("exceptions proposal", "concept"), ("wasmtime", "framework"), ("V8", "framework"), ("longjmp", "method")],
     [("exceptions proposal", "longjmp", "REPLACES")],
     "which Wasm proposal retired the longjmp-via-host trampoline once wasmtime and V8 shipped native support",
     "exceptions proposal try catch wasmtime v8 longjmp trampoline host"),
    # --- 8 ---
    ("The GC proposal adds managed structs and arrays with reference types backed by the host collector; TypeScript-to-Wasm toolchains no longer need a bump allocator shipped inside every module.", "milestone", "technical", False,
     [("GC proposal", "concept"), ("managed structs", "concept"), ("TypeScript", "language"), ("bump allocator", "concept")],
     [("GC proposal", "bump allocator", "REPLACES")],
     "which Wasm proposal lets TypeScript toolchains stop shipping a bump allocator inside every module",
     "gc proposal managed struct array typescript bump allocator host"),
    # --- 9 ---
    ("The component model wraps core modules with typed imports and exports described by WIT files; cross-language linking no longer forces both sides onto the same C ABI.", "architecture", "technical", False,
     [("component model", "concept"), ("WIT", "language"), ("core modules", "concept"), ("C ABI", "protocol")],
     [("component model", "WIT", "USES"), ("component model", "C ABI", "REPLACES")],
     "how does the Wasm component model let two languages link without agreeing on the C ABI",
     "component model wit core module typed import export c abi"),
    # --- 10. noise ---
    ("The office coffee machine started grinding half a second later than usual and nobody on the operations channel admits to changing the bean setting.", "fact", "noise", True, [], [], None, None),
    # --- 11 ---
    ("WIT is the interface description language for the component model; a .wit file declares record, variant, and resource types that bindgen turns into per-language glue on both the host and guest sides.", "reference", "technical", False,
     [("WIT", "language"), ("component model", "concept"), ("bindgen", "tool")],
     [("WIT", "component model", "APPLIES_TO"), ("bindgen", "WIT", "USES")],
     "which interface description language backs the component model and what generates per-language glue from it",
     "wit interface definition component model bindgen record variant resource"),
    # --- 12 ---
    ("wasi_snapshot_preview1 froze the POSIX-ish syscall surface at 0.2 and remains the ABI every wasm32-wasi binary still links against; its module name wraps fd_read, fd_write, and clock_time_get among others.", "reference", "technical", False,
     [("wasi_snapshot_preview1", "protocol"), ("wasm32-wasi", "platform"), ("fd_read", "api"), ("fd_write", "api"), ("clock_time_get", "api")],
     [("wasm32-wasi", "wasi_snapshot_preview1", "DEPENDS_ON")],
     "which frozen WASI ABI does every wasm32-wasi binary still link against and which syscalls sit on that surface",
     "wasi snapshot preview1 posix wasm32 fd read write clock time"),
    # --- 13 ---
    ("wasi_preview2 reorganises the syscall surface as a set of component-model worlds; filesystem, sockets, and clocks become separate interfaces the host decides to offer or withhold per component.", "decision", "technical", False,
     [("wasi_preview2", "protocol"), ("component-model worlds", "concept"), ("filesystem", "api"), ("sockets", "api"), ("clocks", "api")],
     [("wasi_preview2", "component-model worlds", "USES")],
     "how does wasi_preview2 restructure the syscall surface compared to preview1 and what does the host now control per component",
     "wasi preview2 world filesystem socket clock component host offer"),
    # --- 14 ---
    ("Adopted wasm-tools from the Bytecode Alliance as the canonical CLI for component composition; it validates, prints, strips, and composes component binaries and replaced three in-house shell scripts.", "decision", "technical", False,
     [("wasm-tools", "tool"), ("Bytecode Alliance", "organization"), ("component", "concept")],
     [("wasm-tools", "Bytecode Alliance", "AUTHORED_BY")],
     "which upstream CLI replaced the in-house component composition scripts and which project maintains it",
     "wasm tools bytecode alliance component compose validate strip cli"),
    # --- 15 ---
    ("wasm-opt from Binaryen runs as a post-link optimiser pass; the -O3 --converge pipeline shrinks the shipped component by roughly twenty-two percent and removes duplicate funcrefs that the Rust toolchain emits.", "fact", "technical", False,
     [("wasm-opt", "tool"), ("Binaryen", "project"), ("Rust", "language"), ("funcrefs", "concept")],
     [("wasm-opt", "Binaryen", "HAS_PART")],
     "which Binaryen pass shrinks shipped Wasm components after linking and what artefact does it deduplicate",
     "wasm opt binaryen o3 converge shrink funcref duplicate rust"),
    # --- 16 ---
    ("wasm-pack packages a crate into an npm-installable artefact with the JS glue, the .wasm binary, and a TypeScript declarations file; it became the default browser-side delivery path for the analytics widget.", "decision", "technical", False,
     [("wasm-pack", "tool"), ("npm", "technology"), ("TypeScript", "language"), ("analytics widget", "project")],
     [("wasm-pack", "npm", "PRODUCES")],
     "which packager did the analytics widget pick for browser-side delivery and what artefacts does it bundle",
     "wasm pack npm typescript declaration browser glue analytics widget"),
    # --- 17 ---
    ("Benchmarked WasmEdge against wasmtime for the image-transform hot path; WasmEdge with AOT and its tensorflow plugin shaved forty milliseconds per inference request on the edge tier.", "milestone", "technical", False,
     [("WasmEdge", "framework"), ("wasmtime", "framework"), ("AOT", "concept"), ("tensorflow", "library")],
     [("WasmEdge", "wasmtime", "IMPROVES_ON"), ("WasmEdge", "tensorflow", "USES")],
     "which Wasm runtime pulled ahead of wasmtime on the image-transform hot path and which compiled mode and plugin drove it",
     "wasmedge wasmtime aot tensorflow plugin edge image transform benchmark"),
    # --- 18 ---
    ("WAMR is the embedded-target runtime in the firmware build; interpreter plus AOT modes coexist, and the flash footprint stays under eighty kilobytes on the Cortex-M4 variant.", "architecture", "technical", False,
     [("WAMR", "framework"), ("AOT", "concept"), ("Cortex-M4", "platform"), ("interpreter", "concept")],
     [("WAMR", "Cortex-M4", "DEPLOYED_ON")],
     "which embedded Wasm runtime ships in the firmware build and how does it fit on a Cortex-M4",
     "wamr embedded aot interpreter cortex m4 firmware flash footprint"),
    # --- 19 ---
    ("V8's Wasm embedder exposes the liftoff baseline compiler and TurboFan tiering tier; Chrome and Node both share this pipeline, so a module hot on the profile silently migrates from liftoff to TurboFan.", "reference", "technical", False,
     [("V8", "framework"), ("liftoff", "tool"), ("TurboFan", "tool"), ("Chrome", "platform"), ("Node", "platform")],
     [("V8", "liftoff", "HAS_PART"), ("V8", "TurboFan", "HAS_PART")],
     "which two V8 compilers handle Wasm tiering and which host runtimes share that pipeline",
     "v8 liftoff turbofan tier chrome node embedder baseline compiler"),
    # --- 20 ---
    ("Wazero is the zero-dependency Go runtime of choice because the whole embedder compiles into a single static binary; no cgo, no libc, no shell-outs to wasmtime during CI.", "decision", "technical", False,
     [("Wazero", "framework"), ("Go", "language"), ("cgo", "concept"), ("libc", "library")],
     [("Wazero", "Go", "USES")],
     "which Wasm runtime does the Go team prefer for pure-Go embedding and what dependencies does it deliberately avoid",
     "wazero zero dependency go cgo libc static binary embedder"),
    # --- 21 ---
    ("Spin from Fermyon drives the serverless-function layer; a spin.toml maps HTTP routes to component entry points and the runtime cold-starts each request in under a millisecond on the edge node.", "architecture", "technical", False,
     [("Spin", "framework"), ("Fermyon", "organization"), ("spin.toml", "file"), ("HTTP", "protocol")],
     [("Spin", "Fermyon", "AUTHORED_BY")],
     "which Fermyon runtime drives the serverless-function layer and how are HTTP routes wired into components",
     "spin fermyon serverless toml http route component cold start edge"),
    # --- 22 ---
    ("The Extism host is embedded in the desktop client to run untrusted plugins; a manifest declares allowed hosts and paths, and each plugin runs inside its own Wasm sandbox with no ambient authority.", "architecture", "technical", False,
     [("Extism", "framework"), ("desktop client", "project"), ("manifest", "concept"), ("sandbox", "concept")],
     [("Extism", "desktop client", "DEPLOYED_ON")],
     "which host framework runs untrusted plugins in the desktop client and how does it constrain plugin capabilities",
     "extism host plugin desktop manifest sandbox ambient authority wasm"),
    # --- 23 ---
    ("WasmCloud orchestrates actors across a lattice of NATS-connected hosts; capability providers like httpserver and keyvalue-redis are loaded at runtime without rebuilding the actor image.", "architecture", "technical", False,
     [("WasmCloud", "framework"), ("NATS", "technology"), ("actors", "concept"), ("httpserver", "service"), ("keyvalue-redis", "service")],
     [("WasmCloud", "NATS", "COMMUNICATES_WITH")],
     "which lattice-style orchestrator connects Wasm actors over NATS and how are capability providers loaded",
     "wasmcloud actor lattice nats capability provider httpserver keyvalue"),
    # --- 24 ---
    ("Wasmer Deploy hosts the report-generator service; wasmer.toml declares the entrypoint and static assets, and the platform scales the function to zero when no request is in flight.", "fact", "technical", False,
     [("Wasmer Deploy", "service"), ("report-generator", "project"), ("wasmer.toml", "file")],
     [("report-generator", "Wasmer Deploy", "DEPLOYED_ON")],
     "where does the report-generator service run and which manifest file declares its entrypoint",
     "wasmer deploy report generator toml entrypoint scale zero static"),
    # --- 25 ---
    ("Cloudflare Workers exposes a V8 isolate per request with a Wasm module bound as a binding; a module import in the wrangler.toml streams the .wasm binary into the isolate at cold start.", "reference", "technical", False,
     [("Cloudflare Workers", "platform"), ("V8 isolate", "concept"), ("wrangler.toml", "file")],
     [("Cloudflare Workers", "V8 isolate", "USES")],
     "how does Cloudflare Workers bind a Wasm module into a V8 isolate and which manifest file controls the import",
     "cloudflare workers v8 isolate wasm binding wrangler toml stream"),
    # --- 26 ---
    ("Vercel Edge Runtime executes the middleware bundle as a Wasm-adjacent V8 isolate too; the middleware.ts compile target emits a bundle that shares the same Edge runtime primitives as Cloudflare's Workers API.", "fact", "technical", False,
     [("Vercel Edge Runtime", "platform"), ("middleware.ts", "file"), ("Workers API", "api")],
     [("Vercel Edge Runtime", "Workers API", "IS_A")],
     "how does Vercel's Edge Runtime share primitives with the Cloudflare Workers API and which source file compiles into it",
     "vercel edge runtime middleware workers api isolate bundle share"),
    # --- 27 ---
    ("Fastly Compute runs the service on Lucet-derived tooling with full wasi_snapshot_preview1 support; the Rust crate compiles to wasm32-wasi and uploads as a .tar.gz via the fastly CLI.", "preference", "technical", False,
     [("Fastly Compute", "platform"), ("Lucet", "framework"), ("wasi_snapshot_preview1", "protocol"), ("fastly CLI", "tool")],
     [("Fastly Compute", "Lucet", "BUILDS_ON"), ("Fastly Compute", "wasi_snapshot_preview1", "SUPPORTS")],
     "which runtime powers Fastly Compute and what upload flow does the fastly CLI use for a wasm32-wasi crate",
     "fastly compute lucet wasi preview1 rust wasm32 cli tar upload"),
    # --- 28 ---
    ("Deno Deploy uses the V8 isolate model too but exposes Wasm through the standard WebAssembly.instantiateStreaming API; the same code runs in deno run locally and on the edge without a separate build target.", "fact", "technical", False,
     [("Deno Deploy", "platform"), ("V8 isolate", "concept"), ("WebAssembly.instantiateStreaming", "api")],
     [("Deno Deploy", "V8 isolate", "USES")],
     "how does Deno Deploy expose Wasm to user code and what portability does that give compared to Cloudflare's binding model",
     "deno deploy v8 isolate webassembly instantiate streaming edge local"),
    # --- 29 ---
    ("Envoy runs filters as Wasm plugins through proxy-wasm; the SDK binds callbacks like on_http_request_headers so traffic policy can be deployed as a signed .wasm artefact instead of an Envoy rebuild.", "decision", "technical", False,
     [("Envoy", "service"), ("proxy-wasm", "protocol"), ("on_http_request_headers", "api")],
     [("Envoy", "proxy-wasm", "USES")],
     "how does Envoy expose Wasm plugins to traffic filters and which SDK callback handles request headers",
     "envoy proxy wasm plugin filter on http request headers signed artefact"),
    # --- 30 ---
    ("Istio picked up the same proxy-wasm ABI via its Envoy sidecars; shipping a mesh-wide policy now means publishing a Wasm bundle to the control plane rather than rolling a new Envoy image per change.", "decision", "technical", False,
     [("Istio", "service"), ("proxy-wasm", "protocol"), ("Envoy", "service"), ("control plane", "concept")],
     [("Istio", "proxy-wasm", "USES"), ("Istio", "Envoy", "DEPENDS_ON")],
     "how does Istio ship mesh-wide policy changes without rebuilding Envoy and which ABI does it lean on",
     "istio proxy wasm envoy sidecar control plane policy mesh bundle"),
    # --- 31 ---
    ("Shopify Scripts migrated to Wasm via Shopify Functions; merchants upload a compiled module written in Rust or AssemblyScript and the runtime caps execution at five milliseconds per checkout stage.", "milestone", "technical", False,
     [("Shopify Scripts", "platform"), ("Shopify Functions", "platform"), ("Rust", "language"), ("AssemblyScript", "language")],
     [("Shopify Functions", "Shopify Scripts", "REPLACES")],
     "which Shopify platform replaced Scripts with Wasm and what source languages do merchants use",
     "shopify scripts functions wasm rust assemblyscript checkout millisecond"),
    # --- 32 ---
    ("Suborbital's Reactr runtime hosts the plugin tier as Wasm modules; the host binds a small set of capabilities like HTTP, cache, and database through the Runnable API and denies everything else by default.", "architecture", "technical", False,
     [("Suborbital", "organization"), ("Reactr", "framework"), ("Runnable API", "api"), ("HTTP", "protocol")],
     [("Reactr", "Suborbital", "AUTHORED_BY"), ("Reactr", "Runnable API", "USES")],
     "which Suborbital runtime hosts Wasm plugins and which API surface does it expose to guests",
     "suborbital reactr runnable api wasm plugin host http cache capability"),
    # --- 33 ---
    ("AssemblyScript is preferred for the browser-side filters because the TypeScript-shaped syntax kept the frontend team productive; Rust was considered but the borrow-checker tax wasn't worth it for sub-kilobyte modules.", "preference", "technical", False,
     [("AssemblyScript", "language"), ("TypeScript", "language"), ("Rust", "language"), ("borrow-checker", "concept")],
     [("AssemblyScript", "Rust", "PREFERS"), ("AssemblyScript", "TypeScript", "IS_A")],
     "which Wasm source language did the frontend team pick for small browser-side filters and why not Rust",
     "assemblyscript typescript rust borrow checker browser filter prefer"),
    # --- 34 ---
    ("Emscripten remained the compile path for the C++ physics engine; its FS shim plus SDL2 port meant the existing desktop codebase ran in the browser without swapping out the audio subsystem.", "decision", "technical", False,
     [("Emscripten", "tool"), ("C++", "language"), ("FS shim", "concept"), ("SDL2", "library"), ("physics engine", "project")],
     [("physics engine", "Emscripten", "USES"), ("Emscripten", "SDL2", "SUPPORTS")],
     "which compile toolchain did the C++ physics engine stay on for the browser port and what shims kept it portable",
     "emscripten cpp physics fs shim sdl2 browser port audio"),
    # --- 35 ---
    ("TinyGo replaced the full Go compiler for the Wasm target; the binary dropped from eight megabytes to three hundred kilobytes and the GC pause profile flattened out on the edge cold-start trace.", "decision", "technical", False,
     [("TinyGo", "tool"), ("Go", "language"), ("GC pause", "concept")],
     [("TinyGo", "Go", "REPLACES")],
     "which Go compiler swap shrunk the Wasm binary and flattened GC pauses on edge cold start",
     "tinygo go wasm target binary size gc pause edge cold start"),
    # --- 36 ---
    ("Component-level cross-language interop shipped: a Rust producer exports a graph-search resource, a Python guest imports it through the same WIT world, and no FFI layer sits between them.", "milestone", "technical", False,
     [("Rust", "language"), ("Python", "language"), ("WIT", "language"), ("graph-search", "project"), ("FFI", "concept")],
     [("WIT", "FFI", "REPLACES")],
     "how did a Rust producer and a Python guest share a graph-search resource without an FFI layer between them",
     "component cross language rust python wit world resource ffi interop"),
    # --- 37 ---
    ("Pinned wasmtime to the 18.x line for the production runtime; the 19.x bump changed the linker shim signatures and broke the signed-plugin cache, so the upgrade is parked until the migration note lands.", "problem", "technical", False,
     [("wasmtime", "framework"), ("linker shim", "concept"), ("signed-plugin cache", "concept")],
     [],
     "which wasmtime major version is the production runtime pinned to and what broke on the 19.x bump",
     "wasmtime 18 19 pin linker shim signed plugin cache upgrade break"),
    # --- 38 ---
    ("Prefer wasm-tools component new over the older wit-component CLI for packaging; wasm-tools tracks WIT grammar changes more aggressively and already supports the resource-type rewrites.", "preference", "technical", False,
     [("wasm-tools", "tool"), ("wit-component", "tool"), ("WIT", "language"), ("resource-type", "concept")],
     [("wasm-tools", "wit-component", "PREFERS")],
     "which component packaging CLI does the team prefer and which WIT feature tipped the choice",
     "wasm tools component new wit component cli grammar resource prefer"),
    # --- 39 ---
    ("Memory64 is the next proposal the runtime team is watching; the 4 GiB linear-memory cap already bites the vector-search module, and moving to 64-bit pointers would remove the chunking layer entirely.", "fact", "technical", False,
     [("Memory64", "concept"), ("linear-memory", "concept"), ("vector-search", "project")],
     [("vector-search", "Memory64", "APPLIES_TO")],
     "which Wasm proposal would let the vector-search module drop its chunking layer and what limit motivates it",
     "memory64 linear memory 4 gib vector search chunk pointer cap"),
    # --- 40 ---
    ("Enable `--no-default-features` on the wasmtime crate in build scripts; the default pulls cache and profiling, which doubles the embedder size and tripped the plugin loader's size budget.", "preference", "technical", False,
     [("wasmtime", "framework"), ("cache", "concept"), ("profiling", "concept"), ("plugin loader", "project")],
     [],
     "which wasmtime crate flag does the build script set to keep the embedder small and which default features cause the bloat",
     "wasmtime no default features cache profiling embedder size plugin loader"),
    # --- 41 ---
    ("Built the signing layer for component artefacts on top of sigstore; a cosign signature over the component binary plus a WIT hash makes tampered plugins detectable at load time inside the host.", "architecture", "technical", False,
     [("sigstore", "service"), ("cosign", "tool"), ("WIT", "language"), ("component binary", "concept")],
     [("cosign", "sigstore", "USES")],
     "how does the plugin layer detect tampered component artefacts at load time and what identity layer does it build on",
     "sigstore cosign component wit hash signature tamper host load"),
    # --- 42 ---
    ("Debug builds of Wasm components ship a DWARF section; wasmtime --coredump plus addr2line resolves the frame back to the original Rust source even through the component-model adapter layer.", "fact", "technical", False,
     [("DWARF", "concept"), ("wasmtime", "framework"), ("addr2line", "tool"), ("Rust", "language")],
     [("wasmtime", "DWARF", "SUPPORTS")],
     "how does the debug build resolve a Wasm crash back to Rust source through the component adapter",
     "dwarf wasmtime coredump addr2line rust source component adapter debug"),
    # --- 43. noise ---
    ("A raccoon has apparently been raiding the shared compost bin and the kitchen slack thread now has a week of blurry motion-detection photos.", "fact", "noise", True, [], [], None, None),
    # --- 44 ---
    ("jco is the JavaScript component bindgen: it consumes a signed .wasm component plus its WIT world and emits an ESM module with type declarations that Node 20 and modern browsers both import directly.", "reference", "technical", False,
     [("jco", "tool"), ("WIT", "language"), ("ESM", "concept"), ("Node", "platform")],
     [("jco", "WIT", "USES")],
     "which tool converts a signed component plus its world definition into an ES module that Node 20 can import without glue",
     "jco javascript component bindgen wit esm node browser import"),
    # --- 45 ---
    ("Ran into a cold-start regression on Spin after the wasmtime 17 bump; the Cranelift cache disk layout changed, so the first request after deploy paid a full compile even on cached modules.", "problem", "technical", False,
     [("Spin", "framework"), ("wasmtime", "framework"), ("Cranelift", "tool"), ("cache", "concept")],
     [("Spin", "wasmtime", "DEPENDS_ON")],
     "which Spin cold-start regression followed the wasmtime 17 upgrade and which subsystem changed shape",
     "spin wasmtime 17 cranelift cache disk layout cold start regression"),
    # --- 46 ---
    ("Switched the Python plugin layer to componentize-py; the old PyOxidizer path produced a single fat binary while componentize-py emits a WIT-typed component that the Extism host can load directly.", "decision", "technical", False,
     [("componentize-py", "tool"), ("PyOxidizer", "tool"), ("Python", "language"), ("Extism", "framework"), ("WIT", "language")],
     [("componentize-py", "PyOxidizer", "REPLACES")],
     "which tool replaced PyOxidizer for the Python plugin layer and which Wasm host consumes the output",
     "componentize py pyoxidizer python extism wit component plugin"),
    # --- 47 ---
    ("The golden performance fixture runs SpecTest-style Wasm suites under wasmtime, WasmEdge, and Wazero; any runtime that regresses more than five percent on the canonicalize_f32 benchmark blocks the release.", "architecture", "technical", False,
     [("SpecTest", "tool"), ("wasmtime", "framework"), ("WasmEdge", "framework"), ("Wazero", "framework"), ("canonicalize_f32", "method")],
     [("SpecTest", "wasmtime", "APPLIES_TO"), ("SpecTest", "WasmEdge", "APPLIES_TO"), ("SpecTest", "Wazero", "APPLIES_TO")],
     "how does the release pipeline guard against runtime regressions and which benchmark is the release blocker",
     "spectest wasmtime wasmedge wazero canonicalize f32 regression release"),
    # --- 48 ---
    ("wasm-bindgen stays as the Rust-to-JavaScript glue for browser targets; it predates the component model and the existing webapp imports would all need rewriting against jco to migrate now.", "decision", "technical", False,
     [("wasm-bindgen", "tool"), ("Rust", "language"), ("JavaScript", "language"), ("jco", "tool"), ("component model", "concept")],
     [],
     "why does the browser target still use wasm-bindgen instead of migrating to the component-model path through jco",
     "wasm bindgen rust javascript jco component model browser migrate"),
    # --- 49 ---
    ("Adopted the wasip2 target for new services; cargo build --target wasm32-wasip2 produces a component directly, and the old wasm32-wasi path is frozen for legacy compatibility only.", "milestone", "technical", False,
     [("wasip2", "platform"), ("wasm32-wasip2", "platform"), ("wasm32-wasi", "platform"), ("cargo", "tool")],
     [("wasm32-wasip2", "wasm32-wasi", "REPLACES")],
     "which Rust target produces a component directly for new services and what is the fate of the older wasm32-wasi target",
     "wasip2 wasm32 wasi cargo target component rust legacy freeze"),
    # --- 50 ---
    ("Component imports that miss a host binding now surface as structured TrapError messages instead of panics; the host maps the WIT resource path to an HTTP 501 when the capability is intentionally withheld.", "problem", "technical", False,
     [("TrapError", "concept"), ("WIT", "language"), ("HTTP", "protocol"), ("host binding", "concept")],
     [],
     "how do missing host bindings now surface in the component runtime and what HTTP status does the host map to a withheld capability",
     "trap error wit resource http 501 host binding miss component panic"),
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
