"""One-off emitter for shared-base batch-238 — technical domain (Rust ecosystem: cargo, rustup, rust-analyzer, clippy, rustfmt, tokio, async-std, smol, hyper, axum, actix-web, warp, rocket, leptos, yew, dioxus, tauri, bevy, serde, bincode, rkyv, rmp-serde, thiserror, anyhow, tracing, log, env_logger, criterion, proptest, quickcheck, miri, cargo-fuzz, cargo-nextest, cargo-watch, cargo-udeps, sqlx, diesel, sea-orm, bindgen, cbindgen, PyO3, maturin, rayon, crossbeam, parking_lot, dashmap, once_cell, lazy_static, traits/generics/lifetimes, async-trait).

Writes 50 rows to data/v2/shared/batch_238.tmp.jsonl with ids shared-11851..11900.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "shared" / "batch_238.tmp.jsonl"
ID_OFFSET = 11850

# (text, memory_type, domain, noise, entities, relationships, qq, qk)
ENTRIES: list[tuple] = [
    # --- 1 ---
    ("The web service migrated from actix-web to axum because the tower middleware ecosystem composed cleanly with our existing tonic gRPC stack and shared a single tokio runtime.", "decision", "technical", False,
     [("actix-web", "framework"), ("axum", "framework"), ("tower", "library"), ("tonic", "library"), ("tokio", "library")],
     [("axum", "actix-web", "REPLACES"), ("axum", "tokio", "USES")],
     "which Rust web framework replaced actix-web and what middleware ecosystem drove the switch",
     "axum actix web tower tonic tokio middleware runtime swap"),
    # --- 2 ---
    ("Pinned the workspace to a 1.82 toolchain via rust-toolchain.toml so CI and local builds agree; rustup picks it up automatically and developers no longer need to remember cargo +stable invocations.", "decision", "technical", False,
     [("rust-toolchain.toml", "file"), ("rustup", "tool"), ("cargo", "tool"), ("1.82", "date")],
     [("rust-toolchain.toml", "rustup", "CONFIGURES")],
     "how did we pin the compiler version so CI and developer machines agree without manual toolchain flags",
     "rustup toolchain pin rust-toolchain toml cargo ci stable version"),
    # --- 3 ---
    ("clippy is wired into the pre-commit hook with -D warnings; the lint gate caught about forty implicit-into-iter copies in the first week and the PR noise settled after.", "milestone", "technical", False,
     [("clippy", "tool"), ("pre-commit", "tool")],
     [("clippy", "pre-commit", "CONFIGURES")],
     "which linter did we gate in pre-commit and what class of bug did it surface in the first week",
     "clippy pre commit lint warning deny iter copy pr noise gate"),
    # --- 4 ---
    ("rustfmt config is checked in as rustfmt.toml with max_width=100 and group_imports=StdExternalCrate; disagreements about import ordering stopped being a review topic after the config landed.", "preference", "technical", False,
     [("rustfmt", "tool"), ("rustfmt.toml", "file"), ("max_width", "config"), ("group_imports", "config")],
     [("rustfmt.toml", "rustfmt", "CONFIGURES")],
     "which formatter settings ended the import-ordering review bikeshed in the Rust workspace",
     "rustfmt toml max width group imports std external crate order"),
    # --- 5 ---
    ("rust-analyzer stalled on the monorepo until we enabled rust-analyzer.cargo.buildScripts.enable=true and bumped the check-on-save workers; cold-start index time dropped from ninety seconds to twenty.", "problem", "technical", False,
     [("rust-analyzer", "tool"), ("buildScripts.enable", "config"), ("check-on-save", "config")],
     [],
     "which rust-analyzer settings fixed the monorepo cold-start stall and how much did index time drop",
     "rust analyzer build scripts check save worker cold start index"),
    # --- 6 ---
    ("Adopted tokio as the single async runtime across the workspace; smol and async-std experiments got retired to avoid two executors fighting for the same worker threads in our services.", "preference", "technical", False,
     [("tokio", "library"), ("smol", "library"), ("async-std", "library")],
     [("tokio", "smol", "REPLACES"), ("tokio", "async-std", "REPLACES")],
     "which async runtime won out across the workspace and which two alternatives were retired",
     "tokio smol async std runtime single executor worker thread retire"),
    # --- 7 ---
    ("hyper powers the low-level HTTP client and server plumbing under axum; the direct hyper API is exposed only where we need custom h2 frame handling that the framework layer wraps away.", "architecture", "technical", False,
     [("hyper", "library"), ("axum", "framework"), ("h2", "protocol")],
     [("axum", "hyper", "DEPENDS_ON")],
     "which low-level HTTP library sits under axum and when do we drop to its direct API",
     "hyper axum http2 h2 frame client server low level framework wrap"),
    # --- 8 ---
    ("serde with derive is the default for every DTO in the public API crate; custom Deserialize impls only appear where we need tagged-enum handling that the derive can't express cleanly.", "architecture", "technical", False,
     [("serde", "library"), ("derive", "pattern"), ("Deserialize", "pattern")],
     [("serde", "derive", "USES")],
     "which serialisation library handles public DTOs and when do we write custom Deserialize impls",
     "serde derive dto public api deserialize tagged enum custom impl"),
    # --- 9 ---
    ("Switched the on-disk cache format from bincode to rkyv; zero-copy deserialisation knocked the warm cache hit path from 180 microseconds to under 5 for a typical record.", "milestone", "technical", False,
     [("bincode", "library"), ("rkyv", "library")],
     [("rkyv", "bincode", "REPLACES")],
     "which binary format replaced bincode for the on-disk cache and what latency win did it deliver",
     "rkyv bincode zero copy cache deserialise hit path microsecond record"),
    # --- 10. noise ---
    ("The office succulents on the third-floor windowsill all tilted toward the same east-facing window and someone rotated them each Monday.", "fact", "noise", True, [], [], None, None),
    # --- 11 ---
    ("Message-bus payloads use rmp-serde for MessagePack encoding; the compact wire format shaved roughly thirty percent off broker storage compared with the JSON payload it replaced.", "fact", "technical", False,
     [("rmp-serde", "library"), ("MessagePack", "protocol"), ("JSON", "technology")],
     [("rmp-serde", "JSON", "REPLACES")],
     "which MessagePack crate replaced JSON on the message bus and what broker-storage saving showed up",
     "rmp serde message pack json wire format broker storage thirty"),
    # --- 12 ---
    ("Errors in library crates use thiserror with a dedicated enum per module; the binary crates use anyhow for top-level propagation so we don't have to thread a massive error enum to main.", "fact", "technical", False,
     [("thiserror", "library"), ("anyhow", "library")],
     [],
     "how does the Rust workspace split error handling between library crates and binary crates",
     "thiserror anyhow library binary error enum propagate top level"),
    # --- 13 ---
    ("Standardised on tracing for structured logs with a tracing-subscriber fmt layer; the older log plus env_logger stack survives only in two legacy CLI tools that nobody has touched in a year.", "decision", "technical", False,
     [("tracing", "library"), ("tracing-subscriber", "library"), ("log", "library"), ("env_logger", "library")],
     [("tracing", "log", "REPLACES"), ("tracing", "env_logger", "REPLACES")],
     "which structured logging stack replaced log and env_logger across the workspace",
     "tracing subscriber fmt log env logger structured legacy cli replace"),
    # --- 14 ---
    ("criterion benchmarks run nightly against main; a regression gate at five percent rejects the PR and uploads the HTML report to the CI artifact bucket for the reviewer.", "architecture", "technical", False,
     [("criterion", "library"), ("main", "pattern"), ("CI", "infrastructure")],
     [("criterion", "CI", "DEPLOYED_ON")],
     "how do the nightly criterion benchmarks gate regressions against the main branch",
     "criterion benchmark nightly main regression gate html ci artifact"),
    # --- 15 ---
    ("proptest caught a nasty edge case in the range-merge code: shrinking produced a three-element input where adjacent ranges touched but didn't overlap, which the hand-written tests never tried.", "problem", "technical", False,
     [("proptest", "library"), ("range-merge", "pattern")],
     [],
     "which property testing tool found the adjacent-but-non-overlapping range-merge bug the unit tests missed",
     "proptest range merge shrink adjacent touch overlap edge case"),
    # --- 16 ---
    ("Picked proptest over quickcheck for the generator DSL and richer shrinking; quickcheck's Arbitrary stays only in the FFI boundary crate where the impl was already written.", "decision", "technical", False,
     [("proptest", "library"), ("quickcheck", "library"), ("Arbitrary", "pattern"), ("FFI", "pattern")],
     [("proptest", "quickcheck", "PREFERS")],
     "which property-testing crate won the workspace default and where does quickcheck still live",
     "proptest quickcheck arbitrary ffi shrink dsl generator default"),
    # --- 17 ---
    ("miri caught a stacked-borrows violation in the custom vector arena; a raw-pointer reborrow was aliasing an &mut that was still live, which the test suite never flagged on a normal build.", "problem", "technical", False,
     [("miri", "tool"), ("stacked-borrows", "pattern"), ("vector arena", "pattern")],
     [],
     "which Rust interpreter surfaced the stacked-borrows alias bug in the arena that normal tests missed",
     "miri stacked borrow raw pointer reborrow alias mut arena vector"),
    # --- 18 ---
    ("The cargo-fuzz onboarding guide in docs/fuzzing.md walks new contributors through libFuzzer corpus layout, the seed-input conventions, and how to reproduce a crash locally from a CI artifact.", "reference", "technical", False,
     [("cargo-fuzz", "tool"), ("docs/fuzzing.md", "file"), ("libFuzzer", "tool")],
     [("cargo-fuzz", "libFuzzer", "USES")],
     "which onboarding doc covers the cargo-fuzz setup and corpus layout for new contributors",
     "cargo fuzz docs fuzzing libfuzzer corpus seed input ci reproduce"),
    # --- 19 ---
    ("Replaced cargo test with cargo-nextest across the monorepo; parallel test execution cut the backend suite wall-clock from fourteen minutes to just under four on the CI runners.", "decision", "technical", False,
     [("cargo test", "command"), ("cargo-nextest", "tool"), ("monorepo", "project")],
     [("cargo-nextest", "cargo test", "REPLACES")],
     "which test runner replaced cargo test in the monorepo and how much wall-clock did it shave off CI",
     "cargo nextest test parallel monorepo ci minute wall clock replace"),
    # --- 20 ---
    ("cargo-watch drives the inner dev loop: save a file, cargo check runs automatically, and the terminal shows compile errors before the editor has even saved the linter run.", "preference", "technical", False,
     [("cargo-watch", "tool"), ("cargo check", "command")],
     [("cargo-watch", "cargo check", "USES")],
     "which Rust tool powers the save-and-compile dev loop and what command does it chain",
     "cargo watch check save dev loop compile error terminal linter"),
    # --- 21 ---
    ("cargo-udeps flagged seventeen unused dependencies across the workspace on the first run; trimming them shaved about forty seconds off a cold cargo build and cleaned the dependency graph.", "milestone", "technical", False,
     [("cargo-udeps", "tool"), ("cargo build", "command")],
     [],
     "which audit tool found unused workspace dependencies and what build-time win followed",
     "cargo udeps unused dependency workspace cold build trim graph"),
    # --- 22 ---
    ("Database access moved from diesel to sqlx so async queries stop blocking runtime workers; the compile-time query checking via sqlx::query! retained the type-safety we liked in diesel.", "decision", "technical", False,
     [("diesel", "library"), ("sqlx", "library"), ("query!", "api")],
     [("sqlx", "diesel", "REPLACES")],
     "which ORM replaced diesel for async workloads and which macro kept compile-time query checking",
     "sqlx diesel async query macro compile time type safe runtime"),
    # --- 23 ---
    ("sea-orm powers the admin-panel crate because the active-record style matched the dynamic query-builder patterns the UI needed; the hot-path services still use sqlx for raw query performance.", "architecture", "technical", False,
     [("sea-orm", "library"), ("sqlx", "library"), ("admin-panel", "project")],
     [("admin-panel", "sea-orm", "USES")],
     "which crate handles admin-panel queries versus hot-path services and why the split",
     "sea orm sqlx admin panel active record dynamic query builder"),
    # --- 24 ---
    ("Generated the C header from the Rust public API with cbindgen; the reverse-direction bindgen pass on the vendor SDK lets us call into their C library without hand-writing any extern blocks.", "architecture", "technical", False,
     [("cbindgen", "tool"), ("bindgen", "tool"), ("vendor SDK", "library")],
     [("cbindgen", "bindgen", "IS_A")],
     "which two code-generation tools bridge the Rust and C boundary in the vendor SDK integration",
     "cbindgen bindgen c header extern block vendor sdk rust boundary"),
    # --- 25 ---
    ("Python bindings ship through PyO3 and are built with maturin; the CI matrix produces wheels for cp39 through cp312 on linux-x86_64, macOS universal2, and Windows amd64.", "fact", "technical", False,
     [("PyO3", "library"), ("maturin", "tool"), ("linux-x86_64", "platform"), ("macOS", "platform"), ("Windows", "platform")],
     [("maturin", "PyO3", "USES")],
     "which stack builds the Python bindings and what wheel matrix does CI produce",
     "pyo3 maturin wheel cpython linux macos windows matrix build bind"),
    # --- 26 ---
    ("rayon's par_iter replaced the hand-rolled thread pool in the image-processing crate; the scheduler steals work across cores and we dropped about two hundred lines of thread coordination code.", "milestone", "technical", False,
     [("rayon", "library"), ("par_iter", "api"), ("thread pool", "pattern")],
     [("rayon", "thread pool", "REPLACES")],
     "which data-parallelism library replaced the hand-rolled thread pool in the image crate",
     "rayon par iter thread pool data parallel work steal image crate"),
    # --- 27 ---
    ("crossbeam channels replaced std::sync::mpsc for the cross-thread queues; the select! macro and bounded backpressure were the deciders after the mpsc bounded limit bit us twice.", "decision", "technical", False,
     [("crossbeam", "library"), ("std::sync::mpsc", "library"), ("select!", "api")],
     [("crossbeam", "std::sync::mpsc", "REPLACES")],
     "which channel library replaced std mpsc for cross-thread queues and which feature sealed the choice",
     "crossbeam mpsc channel select bounded backpressure cross thread"),
    # --- 28 ---
    ("parking_lot's Mutex is the default lock across the workspace; the smaller footprint and the unpoisoned-by-default behaviour matched our error-handling story better than std::sync::Mutex.", "preference", "technical", False,
     [("parking_lot", "library"), ("Mutex", "pattern"), ("std::sync::Mutex", "library")],
     [("parking_lot", "std::sync::Mutex", "PREFERS")],
     "which Mutex crate is the workspace default and what two traits sealed it over std",
     "parking lot mutex std sync unpoisoned footprint default workspace"),
    # --- 29 ---
    ("dashmap powers the per-session cache shared across worker threads; the sharded design dropped the lock contention we were seeing with a single Mutex<HashMap> under a hundred concurrent sessions.", "decision", "technical", False,
     [("dashmap", "library"), ("Mutex<HashMap>", "pattern"), ("per-session cache", "pattern")],
     [("dashmap", "Mutex<HashMap>", "REPLACES")],
     "which concurrent map replaced Mutex around HashMap for the per-session cache and why",
     "dashmap mutex hashmap session cache shard contention concurrent"),
    # --- 30 ---
    ("Static lookup tables now use once_cell::sync::Lazy; lazy_static was removed from the workspace because once_cell lands in std as OnceLock and the migration path is already on the radar.", "decision", "technical", False,
     [("once_cell", "library"), ("lazy_static", "library"), ("OnceLock", "api")],
     [("once_cell", "lazy_static", "REPLACES")],
     "which lazy-init crate replaced lazy_static and which std type is the eventual successor",
     "once cell lazy static oncelock std lazy init lookup table migrate"),
    # --- 31 ---
    ("async-trait papers over the missing async-fn-in-trait support for our public API traits; we plan to drop it once the 1.75-era AFIT feature covers dyn-compatible trait objects cleanly.", "decision", "technical", False,
     [("async-trait", "library"), ("AFIT", "concept"), ("1.75", "date")],
     [],
     "which crate fills the async-fn-in-trait gap for public traits and when do we plan to drop it",
     "async trait afit async fn trait object dyn compatible future drop"),
    # --- 32 ---
    ("Traits, generics, and lifetimes compose the public extension API: a Storage trait is generic over a Backend associated type, and the lifetime bound ties borrowed keys to the snapshot.", "architecture", "technical", False,
     [("Storage", "pattern"), ("Backend", "pattern"), ("generics", "concept"), ("lifetimes", "concept")],
     [],
     "how do traits generics and lifetimes combine to shape the public Storage extension API",
     "trait generic lifetime storage backend associated type snapshot key"),
    # --- 33 ---
    ("leptos powers the dashboard SPA with signal-based reactivity; we picked it over yew because the server-function ergonomics matched our axum backend and SSR hydration was cleaner out of the box.", "decision", "technical", False,
     [("leptos", "framework"), ("yew", "framework"), ("axum", "framework"), ("SSR", "pattern")],
     [("leptos", "yew", "PREFERS"), ("leptos", "axum", "COMMUNICATES_WITH")],
     "which Rust frontend framework won the dashboard SPA and what feature tipped the decision over yew",
     "leptos yew signal reactive server function axum ssr hydration"),
    # --- 34 ---
    ("dioxus builds the mobile companion app; the shared component tree renders to web, desktop, and mobile targets so we keep one codebase across three platforms instead of forking the UI three ways.", "architecture", "technical", False,
     [("dioxus", "framework"), ("mobile companion", "project")],
     [("mobile companion", "dioxus", "USES")],
     "which cross-platform Rust UI framework powers the mobile companion app and what does it unify",
     "dioxus mobile companion cross platform web desktop shared component"),
    # --- 35 ---
    ("tauri replaced Electron for the desktop build; the system webview plus a Rust backend cut the installer size from 95 MB to under 12 MB and memory idle dropped by roughly 300 MB.", "milestone", "technical", False,
     [("tauri", "framework"), ("Electron", "framework"), ("webview", "technology")],
     [("tauri", "Electron", "REPLACES")],
     "which desktop shell replaced Electron and what installer-size and memory improvements showed up",
     "tauri electron webview desktop installer memory idle mb shell"),
    # --- 36 ---
    ("The game prototype runs on bevy with the ECS default plugins; the archetype layout plays well with the rayon-backed schedule so the simulation scales across cores without manual thread management.", "architecture", "technical", False,
     [("bevy", "framework"), ("ECS", "pattern"), ("rayon", "library")],
     [("bevy", "rayon", "USES")],
     "which Rust game engine powers the prototype and how does its scheduler scale across CPU cores",
     "bevy ecs default plugin rayon schedule archetype scale core game"),
    # --- 37 ---
    ("rocket was evaluated for the internal tools service but lost to axum; the async story and the larger middleware ecosystem around tower carried the decision despite rocket's nicer macro syntax.", "decision", "technical", False,
     [("rocket", "framework"), ("axum", "framework"), ("tower", "library")],
     [("axum", "rocket", "PREFERS")],
     "which framework lost out to axum for the internal tools service and what two factors decided it",
     "rocket axum tower middleware async macro internal tool service"),
    # --- 38 ---
    ("warp is still embedded in the legacy metrics-export binary; the filter combinator style is terse for a single-endpoint service, and there's no business case to port it to axum right now.", "fact", "technical", False,
     [("warp", "framework"), ("axum", "framework"), ("metrics-export", "project")],
     [("metrics-export", "warp", "USES")],
     "which small legacy binary still runs on warp and why we haven't ported it to axum",
     "warp axum metrics export legacy filter combinator single endpoint"),
    # --- 39 ---
    ("actix-web remains in the ingest-proxy crate because the actor model matched the per-connection state we already had; the planned axum port is on the backlog behind three higher-priority services.", "fact", "technical", False,
     [("actix-web", "framework"), ("ingest-proxy", "project"), ("axum", "framework")],
     [("ingest-proxy", "actix-web", "USES")],
     "which legacy service still runs on actix-web and where does the port to axum sit on the roadmap",
     "actix web ingest proxy actor model axum port backlog priority"),
    # --- 40 ---
    ("cargo workspace inheritance trimmed per-crate Cargo.toml files by about forty percent; common dependencies and edition and rust-version now live once in the workspace root.", "milestone", "technical", False,
     [("cargo", "tool"), ("workspace", "pattern"), ("Cargo.toml", "file")],
     [],
     "how did cargo workspace inheritance shrink per-crate manifests and what fields moved to the root",
     "cargo workspace inherit cargo toml edition rust version manifest"),
    # --- 41 ---
    ("hyper 1.0's service trait rework forced the tower adapter rewrite; the adapter crate now bridges hyper::service and tower::Service so axum middleware keeps composing without per-service shims.", "problem", "technical", False,
     [("hyper", "library"), ("tower", "library"), ("axum", "framework"), ("Service", "pattern")],
     [("tower", "hyper", "DEPENDS_ON")],
     "which hyper 1.0 breaking change forced the tower adapter rewrite and what did the bridge preserve",
     "hyper 1.0 service trait tower adapter axum middleware shim bridge"),
    # --- 42 ---
    ("The serde_json dependency was swapped for simd-json on the ingest hot path; parser throughput jumped by about 2.3x on the benchmarks and the public DTO crates still use serde derive unchanged.", "milestone", "technical", False,
     [("serde_json", "library"), ("simd-json", "library"), ("ingest", "project")],
     [("simd-json", "serde_json", "REPLACES")],
     "which JSON parser replaced serde_json on the ingest hot path and what throughput multiple did it hit",
     "simd json serde json ingest parser throughput hot path dto swap"),
    # --- 43. noise ---
    ("The building's second-floor coffee machine started dispensing espresso ninety degrees to the left and nobody filed a ticket for three weeks.", "fact", "noise", True, [], [], None, None),
    # --- 44 ---
    ("tracing spans are propagated across tokio task boundaries via Instrument and in_current_span; forgetting the wrapper used to drop the request-id from the log line once an await crossed a spawn.", "problem", "technical", False,
     [("tracing", "library"), ("tokio", "library"), ("Instrument", "api"), ("in_current_span", "api")],
     [("tracing", "tokio", "USES")],
     "which tracing wrapper keeps spans alive across tokio spawn boundaries and what bug did forgetting it cause",
     "tracing span tokio instrument in current span spawn await request id"),
    # --- 45 ---
    ("axum extractors encode auth at the type level: a RequireAuth<User> parameter fails compilation if a handler forgets the check, so the middleware and the handler can't drift out of sync at review time.", "architecture", "technical", False,
     [("axum", "framework"), ("RequireAuth", "pattern"), ("extractor", "pattern")],
     [],
     "how do axum extractors guarantee at compile time that a handler enforced auth before running",
     "axum extractor require auth type level compile handler middleware drift"),
    # --- 46 ---
    ("Benchmarking harness switched to criterion-compare against a baseline commit; the HTML report highlights regressions over five percent in red and the CI job posts the diff summary to the PR comment.", "reference", "technical", False,
     [("criterion-compare", "tool"), ("PR", "pattern")],
     [],
     "how does the criterion benchmark harness flag regressions and surface them on a pull request",
     "criterion compare baseline commit html report regression ci pr comment"),
    # --- 47 ---
    ("The reference guide on the workspace's async-trait usage points to the tokio book chapter on pinning, plus the RFC thread on async-fn-in-trait dyn safety, for anyone new to the pattern.", "reference", "technical", False,
     [("async-trait", "library"), ("tokio", "library"), ("RFC", "publication")],
     [("async-trait", "RFC", "RELATED_TO")],
     "which two resources does the reference guide point newcomers to for async-trait pinning background",
     "async trait tokio book pin rfc dyn safe fn reference guide chapter"),
    # --- 48 ---
    ("Reference implementation for the custom allocator trait lives in the workspace README under the allocators section; it walks through the Layout math and the GlobalAlloc impl line by line.", "reference", "technical", False,
     [("allocator", "pattern"), ("README", "file"), ("Layout", "api"), ("GlobalAlloc", "api")],
     [],
     "where does the custom allocator walkthrough live and what two APIs does it dissect in detail",
     "allocator readme layout global alloc section walkthrough custom math"),
    # --- 49 ---
    ("The serde-derive reference example in the docs crate shows tagged-enum, flatten, and rename_all working together; most new contributors copy from it when wiring a new external API DTO.", "reference", "technical", False,
     [("serde", "library"), ("derive", "pattern"), ("rename_all", "api"), ("flatten", "api")],
     [("serde", "derive", "USES")],
     "which serde features does the docs-crate reference example combine for new external DTO contributors",
     "serde derive tagged enum flatten rename all dto docs crate example"),
    # --- 50 ---
    ("tokio's LocalSet reference pattern in the docs chapter on !Send futures solved our GUI-bridge headache; the single-threaded executor for the Lua-binding handles runs beside the main multi-threaded runtime.", "reference", "technical", False,
     [("tokio", "library"), ("LocalSet", "api"), ("Lua-binding", "pattern")],
     [("LocalSet", "tokio", "HAS_PART")],
     "which tokio reference pattern handled the non-Send GUI-bridge futures alongside the main runtime",
     "tokio local set send future gui bridge lua binding single thread"),
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
