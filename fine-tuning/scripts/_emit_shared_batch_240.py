"""One-off emitter for shared-base batch-240 — technical domain (TypeScript/JavaScript runtimes: Node, Bun, Deno, package managers, TS 5.x, validators, frameworks).

Writes 50 rows to data/v2/shared/batch_240.tmp.jsonl with ids shared-11951..12000.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "shared" / "batch_240.tmp.jsonl"
ID_OFFSET = 11950

# (text, memory_type, domain, noise, entities, relationships, qq, qk)
ENTRIES: list[tuple] = [
    # --- 1 ---
    ("Flipped the service over to ESM by setting type:module in package.json; the CommonJS require path is gone and top-level await now works inside the bootstrap file without an IIFE wrapper.", "decision", "technical", False,
     [("ESM", "technology"), ("CommonJS", "technology"), ("package.json", "file"), ("top-level await", "pattern")],
     [("ESM", "CommonJS", "REPLACES")],
     "which module system swap enabled top-level await in the service bootstrap without an IIFE",
     "esm commonjs package json top level await module type bootstrap"),
    # --- 2 ---
    ("package.json exports field now maps a public subpath like ./client separately from ./server; consumers that deep-imported internal files get a clean error instead of a working but unsupported path.", "architecture", "technical", False,
     [("package.json", "file"), ("exports field", "pattern"), ("./client", "api"), ("./server", "api")],
     [],
     "how does the package seal internal files while publishing distinct client and server entrypoints",
     "package json exports field subpath client server deep import"),
    # --- 3 ---
    ("Adopted Node 20's permission model via --permission with --allow-fs-read=./data and --allow-net; the worker refuses to touch home directory paths even if a dependency tries via fs.readFile.", "decision", "technical", False,
     [("Node 20", "technology"), ("permission model", "pattern"), ("--allow-fs-read", "config"), ("--allow-net", "config"), ("fs.readFile", "api")],
     [],
     "which Node 20 runtime feature sandboxes filesystem and network access for the worker process",
     "node 20 permission model allow fs read net sandbox worker"),
    # --- 4 ---
    ("Request-scoped context now threads through AsyncLocalStorage instead of a thread-local shim; the old continuation-local-storage package was dropped because its monkey patches drifted with every Node minor.", "decision", "technical", False,
     [("AsyncLocalStorage", "api"), ("continuation-local-storage", "library"), ("Node", "technology")],
     [("AsyncLocalStorage", "continuation-local-storage", "REPLACES")],
     "which Node primitive replaced continuation-local-storage for request-scoped context propagation",
     "async local storage continuation cls node request scope context"),
    # --- 5 ---
    ("Heavy CSV parsing moved off the main event loop onto worker_threads with a SharedArrayBuffer transfer; p99 API latency on the ingest route dropped from 420 ms to 38 ms.", "milestone", "technical", False,
     [("worker_threads", "api"), ("SharedArrayBuffer", "api"), ("CSV", "technology"), ("event loop", "concept")],
     [],
     "which Node concurrency primitive moved CSV parsing off the event loop and what latency win followed",
     "worker threads shared array buffer csv event loop latency p99"),
    # --- 6 ---
    ("Migrated the HTTP layer from Express+Node to Bun.serve; cold start on the Fly.io machine halved and the built-in router drops the need for a separate middleware stack.", "decision", "technical", False,
     [("Bun.serve", "api"), ("Express", "framework"), ("Node", "technology"), ("Fly.io", "service")],
     [("Bun.serve", "Express", "REPLACES")],
     "which Bun API replaced the Express-on-Node HTTP stack and what cold-start win did it deliver on Fly",
     "bun serve express node fly io cold start router middleware"),
    # --- 7 ---
    ("Bun's built-in SQLite client replaced better-sqlite3 for the local cache; the native binding no longer needs prebuilds per platform and the import path shortened to bun:sqlite.", "reference", "technical", False,
     [("bun:sqlite", "api"), ("better-sqlite3", "library"), ("SQLite", "database")],
     [("bun:sqlite", "better-sqlite3", "REPLACES")],
     "which Bun built-in module replaced better-sqlite3 and what prebuild headache did it remove",
     "bun sqlite better sqlite3 native binding prebuild platform import"),
    # --- 8 ---
    ("Shelling out to ffmpeg now goes through Bun.spawn with stdout streamed as a ReadableStream; child_process.spawn had awkward backpressure behaviour on long transcodes.", "reference", "technical", False,
     [("Bun.spawn", "api"), ("child_process.spawn", "api"), ("ffmpeg", "tool"), ("ReadableStream", "api")],
     [("Bun.spawn", "child_process.spawn", "REPLACES")],
     "which Bun subprocess API replaced child_process.spawn for streaming ffmpeg output with backpressure",
     "bun spawn child process ffmpeg readable stream backpressure transcode"),
    # --- 9 ---
    ("Unit tests run under bun test; the old jest + ts-jest transformer path got deleted and snapshot files survived the migration unchanged because Bun honours the .snap format.", "milestone", "technical", False,
     [("bun test", "tool"), ("jest", "framework"), ("ts-jest", "library"), (".snap", "file")],
     [("bun test", "jest", "REPLACES")],
     "which test runner replaced jest and ts-jest while keeping existing snapshot files valid",
     "bun test jest ts jest transformer snapshot snap migration runner"),
    # --- 10. noise ---
    ("Someone wheeled an espresso machine into the quiet phone room and nobody has owned up to it for two weeks now.", "fact", "noise", True, [], [], None, None),
    # --- 11 ---
    ("Deno scripts run with explicit --allow-read=./config and --allow-net=api.example.com; the blanket --allow-all flag is banned in CI because a supply-chain compromise would otherwise touch anything.", "preference", "technical", False,
     [("Deno", "technology"), ("--allow-read", "config"), ("--allow-net", "config"), ("--allow-all", "config")],
     [],
     "why does the CI pipeline forbid Deno's --allow-all and which scoped permissions replace it",
     "deno allow read net all permission ci supply chain scope"),
    # --- 12 ---
    ("deno.json defines a tasks block so contributors run deno task dev rather than memorising the flag soup; the block also pins importMap entries to avoid version drift across developer machines.", "architecture", "technical", False,
     [("deno.json", "file"), ("deno task", "tool"), ("importMap", "pattern")],
     [],
     "how does deno.json standardise developer workflow and prevent dependency version drift across machines",
     "deno json task import map flag pin version drift contributor"),
    # --- 13 ---
    ("Publishing the shared validator library to JSR instead of npm dropped the dual-build dance; JSR serves the TypeScript source directly and Deno, Bun, and Node all consume it.", "decision", "technical", False,
     [("JSR", "service"), ("npm", "tool"), ("TypeScript", "language"), ("Deno", "technology"), ("Bun", "technology"), ("Node", "technology")],
     [("JSR", "npm", "PREFERS")],
     "which registry replaced npm for the shared validator library and what build step did it retire",
     "jsr npm typescript deno bun node registry dual build publish"),
    # --- 14 ---
    ("Switched the monorepo to pnpm workspaces; the content-addressed store cut node_modules disk footprint from 2.4 GB to 380 MB and phantom-dependency bugs surfaced immediately.", "fact", "technical", False,
     [("pnpm", "tool"), ("monorepo", "pattern"), ("node_modules", "concept"), ("phantom-dependency", "pattern")],
     [("pnpm", "phantom-dependency", "FIXES")],
     "which package manager adoption surfaced phantom dependencies and how much disk did the store save",
     "pnpm workspace monorepo node modules phantom dependency store disk"),
    # --- 15 ---
    ("Yarn classic got retired in favour of yarn berry with the node-modules linker; PnP mode was evaluated and rejected because the editor tooling support lagged for TypeScript project references.", "decision", "technical", False,
     [("yarn berry", "tool"), ("Yarn classic", "tool"), ("PnP", "pattern"), ("node-modules linker", "config"), ("TypeScript", "language")],
     [("yarn berry", "Yarn classic", "REPLACES")],
     "which yarn version won the upgrade and why was PnP mode rejected for the TypeScript monorepo",
     "yarn berry classic pnp node modules linker typescript editor"),
    # --- 16 ---
    ("Corepack pins the package manager version at repo root so a contributor running npm by accident in a pnpm repo fails loudly rather than producing a second lockfile.", "architecture", "technical", False,
     [("Corepack", "tool"), ("pnpm", "tool"), ("npm", "tool"), ("lockfile", "concept")],
     [],
     "how does Corepack prevent accidental package-manager mixups and duplicated lockfiles in the repo",
     "corepack pnpm npm lockfile pin package manager contributor mix"),
    # --- 17 ---
    ("Upgraded to TypeScript 5.4 to pick up const type parameters; the shared factory function now infers the exact tuple literal instead of widening to string[] for the event-name list.", "milestone", "technical", False,
     [("TypeScript 5.4", "technology"), ("const type parameters", "pattern"), ("tuple literal", "concept")],
     [],
     "which TypeScript 5.4 feature fixed the event-name list widening from tuple to string array",
     "typescript 5 4 const type parameter tuple literal widen factory"),
    # --- 18 ---
    ("Stage-3 decorators replaced the legacy experimentalDecorators flag; the tsconfig still enables emitDecoratorMetadata but the decorator shape is now the standard @dec(target, context) signature.", "reference", "technical", False,
     [("Stage-3 decorators", "pattern"), ("experimentalDecorators", "config"), ("tsconfig", "file"), ("emitDecoratorMetadata", "config")],
     [("Stage-3 decorators", "experimentalDecorators", "REPLACES")],
     "which decorator proposal replaced experimentalDecorators and what signature does the new shape use",
     "stage 3 decorators experimental metadata tsconfig standard signature"),
    # --- 19 ---
    ("Config loaders now use the TypeScript satisfies operator so an inline object gets narrow literal types while still being validated against a broader ConfigShape interface.", "fact", "technical", False,
     [("satisfies operator", "pattern"), ("ConfigShape", "concept"), ("TypeScript", "language")],
     [],
     "how does the loader keep narrow literal types on an inline object yet still enforce a broader interface",
     "satisfies operator config shape narrow literal interface validate"),
    # --- 20 ---
    ("Resource cleanup now leans on using declarations and Symbol.dispose; the try/finally ladder around database handles collapsed to a single block and matched the pattern docs in the TS 5.2 notes.", "architecture", "technical", False,
     [("using", "pattern"), ("Symbol.dispose", "api"), ("try/finally", "pattern"), ("TS 5.2", "technology")],
     [("using", "try/finally", "REPLACES")],
     "which TS 5.2 feature replaced try/finally ladders for database handle cleanup in the service",
     "using symbol dispose try finally resource cleanup database ts 5 2"),
    # --- 21 ---
    ("Enabled noUncheckedIndexedAccess in tsconfig and the runtime payload-handling code caught three latent undefined bugs on first compile; the array-index assumption was wrong in each spot.", "problem", "technical", False,
     [("noUncheckedIndexedAccess", "config"), ("tsconfig", "file")],
     [("noUncheckedIndexedAccess", "tsconfig", "APPLIES_TO")],
     "which tsconfig flag surfaced three latent undefined bugs on the first compile after enabling",
     "no unchecked indexed access tsconfig undefined array bug latent"),
    # --- 22 ---
    ("isolatedDeclarations turned on for the public library package; contributors must annotate exported return types explicitly but the .d.ts generation is now parallel and no longer gates the build.", "decision", "technical", False,
     [("isolatedDeclarations", "config"), (".d.ts", "file"), ("library package", "pattern")],
     [],
     "which TypeScript flag parallelised declaration generation at the cost of explicit return annotations",
     "isolated declarations d ts parallel build return annotation library"),
    # --- 23 ---
    ("tsconfig extends a shared base via @company/tsconfig-base; individual packages override module and moduleResolution but inherit strict, target, and lib from the base without copy-paste drift.", "fact", "technical", False,
     [("tsconfig", "file"), ("@company/tsconfig-base", "library"), ("moduleResolution", "config"), ("strict", "config")],
     [],
     "how does the monorepo share tsconfig settings across packages while letting modules override independently",
     "tsconfig extends shared base module resolution strict target monorepo"),
    # --- 24 ---
    ("Import statements for types-only symbols must use the type-only syntax; the verbatimModuleSyntax flag catches any mixed import/export so tree-shaking doesn't accidentally drag runtime code in.", "preference", "technical", False,
     [("type-only", "pattern"), ("verbatimModuleSyntax", "config"), ("tree-shaking", "pattern")],
     [],
     "which flag enforces type-only imports and what bundling risk does it defuse",
     "verbatim module syntax type only import tree shake runtime code"),
    # --- 25 ---
    ("Runtime input validation standardised on Zod schemas; the ad-hoc if-ladders per endpoint got deleted and the schema.parse boundary doubles as the OpenAPI source via zod-to-openapi.", "decision", "technical", False,
     [("Zod", "library"), ("schema.parse", "method"), ("OpenAPI", "technology"), ("zod-to-openapi", "library")],
     [("Zod", "schema.parse", "USES")],
     "which runtime validator replaced ad-hoc if-ladders and how does the schema feed OpenAPI documentation",
     "zod schema parse openapi zod to openapi runtime validate endpoint"),
    # --- 26 ---
    ("Benchmarked Valibot against Zod for the edge workers; Valibot's tree-shakeable functional API cut the Cloudflare bundle by 34 kB and the validation surface stayed compatible with the existing schemas.", "decision", "technical", False,
     [("Valibot", "library"), ("Zod", "library"), ("Cloudflare", "service"), ("edge workers", "platform")],
     [("Valibot", "Zod", "REPLACES")],
     "which validator replaced Zod on the Cloudflare edge and how much did the bundle shrink",
     "valibot zod cloudflare edge worker bundle tree shake functional"),
    # --- 27 ---
    ("ArkType replaced a homegrown parser for stringly-typed schemas; the TypeScript inference driven by the schema literal eliminated a whole class of schema-vs-type drift bugs.", "fact", "technical", False,
     [("ArkType", "library"), ("TypeScript", "language"), ("schema literal", "pattern")],
     [("ArkType", "TypeScript", "USES")],
     "which validation library ties schema and type together via literal inference to kill drift bugs",
     "arktype typescript schema literal inference drift validation parse"),
    # --- 28 ---
    ("Effect-ts now owns the service-layer composition; the old Promise chain swallowed typed errors and Effect's typed failure channel plus Layer-based DI surface made the error paths explicit.", "architecture", "technical", False,
     [("Effect-ts", "library"), ("Promise", "api"), ("Layer", "pattern"), ("failure channel", "pattern")],
     [("Effect-ts", "Promise", "REPLACES")],
     "which library replaced bare Promises in the service layer to make typed errors and DI explicit",
     "effect ts promise layer failure channel di service typed error"),
    # --- 29 ---
    ("Result<T, E> types replaced thrown errors at module boundaries; callers must handle the Err variant and the pattern removed four try/catch wrappers in the HTTP adapter alone.", "decision", "technical", False,
     [("Result", "pattern"), ("Err", "pattern"), ("try/catch", "pattern"), ("HTTP adapter", "concept")],
     [("Result", "try/catch", "REPLACES")],
     "which type pattern replaced thrown errors at module boundaries in the HTTP adapter",
     "result type err thrown error module boundary try catch http"),
    # --- 30 ---
    ("ts-pattern drives the discriminated-union handling in the payment state machine; the prior switch+never-exhaustiveness-helper combo was verbose and missed two states during the last refund flow rewrite.", "decision", "technical", False,
     [("ts-pattern", "library"), ("discriminated-union", "pattern"), ("switch", "pattern"), ("payment state machine", "pattern")],
     [("ts-pattern", "switch", "REPLACES")],
     "which library replaced switch statements for discriminated unions in the payment state machine",
     "ts pattern discriminated union switch exhaust payment state machine"),
    # --- 31 ---
    ("Biome replaced ESLint plus Prettier for the web app; lint and format run as one Rust-backed binary so the pre-commit hook finishes in 180 ms instead of 4.2 seconds.", "decision", "technical", False,
     [("Biome", "tool"), ("ESLint", "tool"), ("Prettier", "tool"), ("pre-commit", "pattern")],
     [("Biome", "ESLint", "REPLACES"), ("Biome", "Prettier", "REPLACES")],
     "which single tool replaced ESLint and Prettier and what pre-commit speed win did it produce",
     "biome eslint prettier rust pre commit hook lint format speed"),
    # --- 32 ---
    ("Oxlint sits in front of ESLint on the backend repo as a cheap first pass; 80 percent of rule hits never reach the JavaScript linter and contributors get feedback an order of magnitude faster.", "fact", "technical", False,
     [("Oxlint", "tool"), ("ESLint", "tool"), ("JavaScript", "language")],
     [],
     "how does Oxlint layer with ESLint to give contributors faster lint feedback on the backend repo",
     "oxlint eslint javascript backend linter rust fast feedback layer"),
    # --- 33 ---
    ("ESLint 9 flat config replaced the legacy .eslintrc tree; a single eslint.config.mjs at the root composes rule sets per package path, and the old extends-based inheritance got deleted.", "milestone", "technical", False,
     [("ESLint 9", "tool"), ("flat config", "pattern"), (".eslintrc", "file"), ("eslint.config.mjs", "file")],
     [("flat config", ".eslintrc", "REPLACES")],
     "which ESLint 9 config style replaced .eslintrc and how does it compose rule sets by path",
     "eslint 9 flat config eslintrc mjs inheritance rule set path"),
    # --- 34 ---
    ("Prettier is pinned through the .prettierrc in the repo root with a trailingComma:all override; the version lives in package.json so editor integrations don't pick up a drifted global install.", "preference", "technical", False,
     [("Prettier", "tool"), (".prettierrc", "file"), ("package.json", "file"), ("trailingComma", "config")],
     [],
     "how does the repo pin Prettier version and format rules against editor-local global installs",
     "prettier rc package json trailing comma version pin editor global"),
    # --- 35 ---
    ("Dev scripts run under tsx for speed; ts-node's TypeScript compiler pass was too slow on the hot-reload loop and swc-node was the other finalist before tsx won on out-of-the-box ESM support.", "fact", "technical", False,
     [("tsx", "tool"), ("ts-node", "tool"), ("swc-node", "tool"), ("ESM", "technology")],
     [("tsx", "ts-node", "REPLACES")],
     "which dev runner replaced ts-node for the hot-reload loop and which finalist lost on ESM support",
     "tsx ts node swc node esm dev hot reload compile script"),
    # --- 36 ---
    ("NestJS owns the public API gateway; module boundaries and decorator-driven DI keep the controller layer tidy, but heavy request paths bypass the interceptor chain for latency reasons.", "architecture", "technical", False,
     [("NestJS", "framework"), ("API gateway", "pattern"), ("interceptor", "pattern"), ("decorator-driven DI", "pattern")],
     [],
     "which framework owns the API gateway and why do hot request paths skip the interceptor chain",
     "nest js api gateway module interceptor decorator di latency hot"),
    # --- 37 ---
    ("Fastify replaced Express on the internal services; schema-driven validation plus native JSON serialisation lifted throughput from 9k to 34k rps on the /orders endpoint during the soak test.", "milestone", "technical", False,
     [("Fastify", "framework"), ("Express", "framework"), ("/orders", "api"), ("JSON", "technology")],
     [("Fastify", "Express", "REPLACES")],
     "which web framework replaced Express internally and what throughput gain did /orders show in soak",
     "fastify express schema json serialise orders throughput soak"),
    # --- 38 ---
    ("The edge-facing API runs on Hono atop Cloudflare Workers; the tiny bundle footprint keeps the startup under 15 ms and the middleware shape matches the Fastify conventions the backend team already knows.", "reference", "technical", False,
     [("Hono", "framework"), ("Cloudflare Workers", "service"), ("Fastify", "framework")],
     [],
     "which framework powers the Cloudflare Workers API and how does its middleware feel familiar to Fastify users",
     "hono cloudflare worker edge bundle middleware fastify convention"),
    # --- 39 ---
    ("Hattip is the abstraction layer that lets the SSR handler run on Node, Bun, Deno, and Cloudflare without rewriting the request pipeline; adapters plug into the same handler signature.", "architecture", "technical", False,
     [("Hattip", "framework"), ("SSR", "pattern"), ("Node", "technology"), ("Bun", "technology"), ("Deno", "technology"), ("Cloudflare", "service")],
     [],
     "how does Hattip let one SSR handler run across Node, Bun, Deno, and Cloudflare without rewrites",
     "hattip ssr node bun deno cloudflare adapter handler portable"),
    # --- 40 ---
    ("Import attributes for JSON modules landed; we replaced assert { type: 'json' } with the new with { type: 'json' } once the Node LTS caught up, which unblocked the deprecation warning on boot.", "milestone", "technical", False,
     [("Import attributes", "pattern"), ("assert", "pattern"), ("with", "pattern"), ("Node LTS", "technology")],
     [("with", "assert", "REPLACES")],
     "which JSON-module import syntax replaced the older assert form once Node LTS caught up",
     "import attribute assert with json module node lts deprecation"),
    # --- 41 ---
    ("Node's built-in test runner (node:test) replaced mocha on CI jobs; parallelism via --test-concurrency halved the suite wall clock and the assertion API stayed close to the node:assert surface devs already used.", "fact", "technical", False,
     [("node:test", "api"), ("mocha", "framework"), ("--test-concurrency", "config"), ("node:assert", "api")],
     [("node:test", "mocha", "REPLACES")],
     "which built-in Node runner replaced mocha on CI and which flag cut the wall-clock in half",
     "node test mocha concurrency assert ci wall clock parallel builtin"),
    # --- 42 ---
    ("Bun's FFI via bun:ffi calls directly into libsodium without a C shim; the previous napi addon added a build step per platform and is gone from the repo now.", "reference", "technical", False,
     [("bun:ffi", "api"), ("libsodium", "library"), ("napi", "api"), ("C shim", "pattern")],
     [("bun:ffi", "napi", "REPLACES")],
     "which Bun interop API replaced the napi addon for libsodium bindings and what build step vanished",
     "bun ffi libsodium napi addon c shim binding platform build"),
    # --- 43. noise ---
    ("There's a running bet in the kitchenette over how long the departing intern's desk plant lasts before someone overwaters it.", "fact", "noise", True, [], [], None, None),
    # --- 44 ---
    ("Use pnpm dlx instead of npx for one-shot CLI invocations; pnpm's per-run isolation avoids polluting the shared store with transient tool versions the repo doesn't actually depend on.", "preference", "technical", False,
     [("pnpm dlx", "tool"), ("npx", "tool"), ("shared store", "concept")],
     [("pnpm dlx", "npx", "PREFERS")],
     "which dlx command is preferred over npx for one-shot CLIs and what store pollution does it avoid",
     "pnpm dlx npx one shot cli isolation shared store transient tool"),
    # --- 45 ---
    ("Deno's built-in deno lint and deno fmt cover the Deno-only services; adding a third-party ESLint ruleset was considered and rejected because the out-of-the-box rules matched the codestyle guide already.", "reference", "technical", False,
     [("deno lint", "tool"), ("deno fmt", "tool"), ("ESLint", "tool"), ("Deno", "technology")],
     [("deno lint", "ESLint", "PREFERS")],
     "which built-in Deno tools cover the lint-and-format slot and why was ESLint rejected for those services",
     "deno lint fmt eslint built in rule codestyle format service"),
    # --- 46 ---
    ("Shared TypeScript types for the API live in a @company/contracts package on JSR; both the Node backend and the Deno edge worker import the same tagged-union response types with no codegen step.", "architecture", "technical", False,
     [("@company/contracts", "library"), ("JSR", "service"), ("Node", "technology"), ("Deno", "technology"), ("tagged-union", "pattern")],
     [],
     "how do the Node backend and Deno edge share API response types without a codegen step",
     "contracts jsr node deno tagged union shared type import codegen"),
    # --- 47 ---
    ("AsyncLocalStorage context leaked across requests when mixed with raw Promise.all; the fix was to propagate the store via .run inside each branch rather than relying on inherited async context.", "problem", "technical", False,
     [("AsyncLocalStorage", "api"), ("Promise.all", "api"), (".run", "method")],
     [(".run", "AsyncLocalStorage", "APPLIES_TO")],
     "which AsyncLocalStorage misuse caused cross-request context leaks under Promise.all and what fix landed",
     "async local storage promise all run context leak propagate request"),
    # --- 48 ---
    ("Bun + Hono now serves the OG image endpoint; response streaming via a ReadableStream plus JIT-compiled satori renders the first byte in under 45 ms and the cold cache hit under 120 ms.", "milestone", "technical", False,
     [("Bun", "technology"), ("Hono", "framework"), ("satori", "library"), ("ReadableStream", "api"), ("OG image", "concept")],
     [],
     "which Bun and Hono combination drives the OG image endpoint and what render latency did it hit",
     "bun hono satori og image readable stream render latency cold"),
    # --- 49 ---
    ("Fastify schema validation is delegated to TypeBox compiled with ajv; the type-driven request typing saves a manual Zod schema and the plugin hook collapses validation and documentation into one source.", "architecture", "technical", False,
     [("Fastify", "framework"), ("TypeBox", "library"), ("ajv", "library"), ("Zod", "library")],
     [("TypeBox", "Zod", "REPLACES")],
     "which validator backs Fastify schema handling and how does it fold typing, validation, and docs together",
     "fastify typebox ajv zod schema validate doc plugin type driven"),
    # --- 50 ---
    ("NestJS v10 broke the custom interceptor order after the RxJS 7 bump; pinning the RxJS peer dep and re-implementing the interceptor as a middleware resolved the regression without downgrading Nest.", "problem", "technical", False,
     [("NestJS v10", "framework"), ("RxJS 7", "library"), ("interceptor", "pattern"), ("middleware", "pattern")],
     [("middleware", "interceptor", "REPLACES")],
     "which NestJS v10 and RxJS 7 regression broke interceptor order and how was it resolved without downgrading",
     "nest js v10 rxjs 7 interceptor middleware order regression peer"),
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
