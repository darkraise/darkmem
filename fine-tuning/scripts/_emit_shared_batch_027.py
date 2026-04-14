"""One-off emitter for shared-base batch-027 — ai_coding domain (frontend tooling / bundlers / language-level dev tooling).

Writes 50 rows to data/v2/shared/batch_027.tmp.jsonl with ids shared-01301..01350.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "shared" / "batch_027.tmp.jsonl"
ID_OFFSET = 1300

# (text, memory_type, domain, noise, entities, relationships, qq, qk)
ENTRIES: list[tuple] = [
    # --- 1 ---
    ("ESLint's ecosystem of custom rules still outpaces Biome, so our legacy React apps stayed on ESLint while new services picked Biome.", "decision", "ai_coding", False,
     [("ESLint", "tool"), ("Biome", "tool"), ("React", "framework")],
     [],
     "why did older frontend codebases keep the classic linter while new ones moved on",
     "linter split legacy plugin ecosystem greenfield choice"),
    # --- 2 ---
    ("Oxlint finished a full repo scan in 800 ms versus ESLint's 42 s; the gap makes it a viable fast pre-commit gate.", "fact", "ai_coding", False,
     [("Oxlint", "tool"), ("ESLint", "tool")],
     [],
     "how much faster did the Rust-based linter run than the Node-based one on a full scan",
     "native linter speed order magnitude pre-commit gate viable"),
    # --- 3 ---
    ("Prefer Biome over Oxlint for now; Biome's fix autosuggestions are more conservative and fewer codemods fight the formatter.", "preference", "ai_coding", False,
     [("Biome", "tool"), ("Oxlint", "tool")],
     [("Biome", "Oxlint", "PREFERS")],
     "which new-generation linter won out when both were trialled side by side",
     "lint formatter autofix conservatism pick codemod friction"),
    # --- 4 ---
    ("prettier-plugin-tailwindcss automatically sorts class names into the canonical Tailwind order, ending the class-order review nits.", "fact", "ai_coding", False,
     [("prettier-plugin-tailwindcss", "library"), ("Tailwind", "framework")],
     [],
     "which plugin removed the class-order argument from every pull request review",
     "formatter plugin utility class ordering review nit end"),
    # --- 5 ---
    ("Rome's deprecation in favor of Biome caught us mid-migration; the fork kept the config compatible so the diff stayed small.", "problem", "ai_coding", False,
     [("Rome", "tool"), ("Biome", "tool")],
     [("Biome", "Rome", "REPLACES")],
     "how did the Rome-to-Biome rename play out for an in-flight adoption",
     "tool fork rename config compatibility mid-migration catch"),
    # --- 6 ---
    ("TypeScript project references finally paid off on the 14-package monorepo; tsc --build only recompiles the dirty subgraph.", "fact", "ai_coding", False,
     [("TypeScript", "language"), ("project references", "pattern"), ("tsc", "tool")],
     [],
     "which TypeScript feature cut incremental compile work in the multi-package repo",
     "typed graph build partial recompile dirty subgraph gain"),
    # --- 7 ---
    ("SWC transformed our CI test compile step from 38 s to 6 s once we replaced the Babel preset pipeline.", "milestone", "ai_coding", False,
     [("SWC", "tool"), ("Babel", "tool"), ("CI", "infrastructure")],
     [("SWC", "Babel", "REPLACES")],
     "when did the transpile step in CI stop being the long pole for tests",
     "Rust transpile replace Babel pipeline compile time drop"),
    # --- 8 ---
    ("esbuild's plugin API is minimal by design, which made writing our SVG-to-component loader about 80 lines of code.", "fact", "ai_coding", False,
     [("esbuild", "tool"), ("SVG", "technology")],
     [],
     "how did the narrow plugin surface help the custom asset loader stay small",
     "bundler plugin minimalism custom loader line count simplicity"),
    # --- 9 ---
    ("Rollup tree-shaking kept the unused lodash helpers because the package lacked sideEffects:false; adding that field dropped 42 KB.", "problem", "ai_coding", False,
     [("Rollup", "tool"), ("lodash", "library"), ("sideEffects", "config")],
     [],
     "why did dead-code elimination fail to strip the utility library before the manifest fix",
     "tree shake miss side effect flag package manifest size drop"),
    # --- 10. noise ---
    ("Might need a second monitor to handle all these config files at once.", "fact", "noise", True, [], [], None, None),
    # --- 11 ---
    ("Vite's plugin ecosystem carried us through SSR, PWA and MDX needs without writing anything custom; the surface matches Rollup's API.", "fact", "ai_coding", False,
     [("Vite", "tool"), ("Rollup", "tool"), ("SSR", "concept"), ("MDX", "technology")],
     [("Vite", "Rollup", "BUILDS_ON")],
     "which dev server's plugin catalog covered all three feature needs out of the box",
     "dev server plugin coverage server render PWA MDX reuse"),
    # --- 12 ---
    ("PostCSS 8 plugin order matters; putting autoprefixer before cssnano ran the vendor expansion on already-minified output.", "problem", "ai_coding", False,
     [("PostCSS 8", "tool"), ("autoprefixer", "library"), ("cssnano", "library")],
     [],
     "what plugin ordering mistake blew up the CSS build output size",
     "CSS pipeline order prefix minify wrong sequence bloat"),
    # --- 13 ---
    ("Tailwind JIT made the uncached dev rebuild instant; the content-path globs still need tight scoping or startup crawls slow down.", "fact", "ai_coding", False,
     [("Tailwind JIT", "tool")],
     [],
     "where does the on-demand CSS compiler still need careful configuration",
     "just in time compile instant rebuild content glob scope tune"),
    # --- 14 ---
    ("CSS Modules beat styled-components on the critical-render path; zero runtime cost mattered more than the ergonomic win.", "decision", "ai_coding", False,
     [("CSS Modules", "pattern"), ("styled-components", "library")],
     [("CSS Modules", "styled-components", "PREFERS")],
     "which styling strategy won when first-paint latency was the top metric",
     "scoped CSS runtime cost first paint critical path win"),
    # --- 15 ---
    ("tsconfig paths worked in the IDE but broke at runtime in Node; tsc-alias rewrote the emitted JS to real relative specifiers.", "problem", "ai_coding", False,
     [("tsconfig", "config"), ("Node", "platform"), ("tsc-alias", "tool")],
     [],
     "why did the import-alias mapping compile fine but fail when the service started",
     "path alias runtime resolve gap rewrite emitted specifier"),
    # --- 16 ---
    ("npx is no longer the recommended runner; pnpm dlx and bunx both cache more aggressively and respect engines fields.", "fact", "ai_coding", False,
     [("npx", "command"), ("pnpm dlx", "command"), ("bunx", "command")],
     [],
     "which one-shot package runners took over from the original npm wrapper",
     "package runner alternative cache behaviour engines field"),
    # --- 17 ---
    ("Corepack now enforces the lockfile's packageManager field; CI rejects mismatched Yarn versions instead of silently upgrading.", "architecture", "ai_coding", False,
     [("Corepack", "tool"), ("Yarn", "tool"), ("CI", "infrastructure")],
     [],
     "how does the toolchain now stop accidental package-manager version drift in pipelines",
     "lockfile enforcement package manager pin reject mismatch"),
    # --- 18 ---
    ("Rush's phased builds handle our 80-package monorepo better than Turborepo did; the policies and change files keep releases honest.", "decision", "ai_coding", False,
     [("Rush", "tool"), ("Turborepo", "tool")],
     [("Rush", "Turborepo", "PREFERS")],
     "why did the very large JS monorepo settle on the older Microsoft-style tool",
     "phased build policy change file scale monorepo pick reason"),
    # --- 19 ---
    ("pnpm patch let us fix a broken type in a third-party SDK and commit the diff; upstreaming the PR came afterwards without blocking work.", "fact", "ai_coding", False,
     [("pnpm patch", "command"), ("SDK", "concept")],
     [],
     "which package-manager command lets a repo ship a local fix without forking a dependency",
     "patch command vendor fix commit diff upstream later workflow"),
    # --- 20 ---
    ("Yarn PnP migration stalled on the same Jest and Webpack resolver gaps that killed our 2023 attempt; rolled back to node-modules linker.", "problem", "ai_coding", False,
     [("Yarn PnP", "tool"), ("Jest", "library"), ("Webpack", "tool"), ("node-modules linker", "pattern")],
     [],
     "why did the plug-and-play install layout stall for the second time in a row",
     "zero install resolver gap tool compat rollback second attempt"),
    # --- 21 ---
    ("Deno's npm compat handles most packages but bails on anything using native addons; we keep argon2 and better-sqlite3 out of Deno scripts.", "fact", "ai_coding", False,
     [("Deno", "platform"), ("argon2", "library"), ("better-sqlite3", "library")],
     [],
     "where does the Deno runtime's npm interop still leave specific packages unsupported",
     "runtime compat native addon carve out package exclusion list"),
    # --- 22 ---
    ("Bun install's binary lockfile was fast but unreadable in code review; we switched to the text lockfile mode once it stabilised.", "decision", "ai_coding", False,
     [("Bun", "tool")],
     [],
     "which Bun option did we flip once the reviewable lockfile shape became available",
     "package manager lockfile format binary text review readability"),
    # --- 23 ---
    ("Cargo workspaces finally let us share the proc-macro crate without circular dep warnings once we pulled it into its own sub-workspace.", "problem", "ai_coding", False,
     [("Cargo", "tool"), ("proc-macro", "pattern")],
     [],
     "how did the Rust workspace untangle the macro-crate dependency cycle",
     "workspace layout macro crate cycle sub workspace extraction"),
    # --- 24 ---
    ("cargo tree --duplicates surfaced four minor-version drifts of serde that a release audit would have otherwise missed.", "fact", "ai_coding", False,
     [("cargo tree", "command"), ("serde", "library")],
     [],
     "which command exposed the duplicated dependency versions before the release cut",
     "dep graph duplicate scan library version drift pre-release"),
    # --- 25 ---
    ("Replaced all Go // +build comments with //go:build directives on 2026-01-18; gofmt no longer fights the legacy syntax.", "milestone", "ai_coding", False,
     [("Go", "language"), ("// +build", "pattern"), ("//go:build", "pattern"), ("gofmt", "tool"), ("2026-01-18", "date")],
     [("//go:build", "// +build", "REPLACES")],
     "when did we finish migrating build constraints to the new Go directive syntax",
     "build tag migration new directive formatter conflict date"),
    # --- 26 ---
    ("Python packaging finally settled on pyproject.toml with Hatchling backend; setup.py lingered only in two legacy C-extension packages.", "decision", "ai_coding", False,
     [("pyproject.toml", "config"), ("Hatchling", "tool"), ("setup.py", "file")],
     [("pyproject.toml", "setup.py", "REPLACES")],
     "which Python packaging files did we standardise on and what exceptions remain",
     "packaging config unify backend legacy extension exception"),
    # --- 27 ---
    ("Java module path still trips people who assume classpath semantics; the split-package errors always come back to a missing module-info.java.", "problem", "ai_coding", False,
     [("Java", "language"), ("module-info.java", "file")],
     [],
     "why does the Java module system keep producing the same split-package complaint",
     "JPMS module path classpath confusion split package descriptor"),
    # --- 28 ---
    ("Moved the build scripts from Groovy DSL to Kotlin DSL; type-aware autocomplete in IntelliJ makes tasks far less guesswork.", "decision", "ai_coding", False,
     [("Groovy DSL", "language"), ("Kotlin DSL", "language"), ("IntelliJ", "tool")],
     [("Kotlin DSL", "Groovy DSL", "REPLACES")],
     "why did the Gradle build scripts get rewritten into the typed DSL",
     "build script DSL swap typed autocomplete IDE guesswork reduce"),
    # --- 29 ---
    ("Maven BOMs solved the transitive version drift inside the platform artifacts; consumers no longer pin 30 versions per pom.", "architecture", "ai_coding", False,
     [("Maven", "tool"), ("BOM", "pattern")],
     [],
     "what pattern removed the per-pom dependency version pinning burden",
     "bill of materials transitive unify consumer simplify pom"),
    # --- 30 ---
    ("Rolldown is still experimental for us; stable on ESM libraries but chokes on CommonJS with dynamic require, so parked until the matrix matures.", "fact", "ai_coding", False,
     [("Rolldown", "tool"), ("ESM", "concept"), ("CommonJS", "concept")],
     [],
     "where does the new Rust-based bundler still fall short of a drop-in adoption",
     "experimental bundler module format compat dynamic require gap"),
    # --- 31 ---
    ("Lerna to Nx migration wrapped on 2026-02-24; task graph caching alone cut our CI main-branch build from 18 min to 7 min.", "milestone", "ai_coding", False,
     [("Lerna", "tool"), ("Nx", "tool"), ("CI", "infrastructure"), ("2026-02-24", "date")],
     [("Nx", "Lerna", "REPLACES")],
     "when did the monorepo orchestrator swap land and what was the build time win",
     "monorepo tool migration task graph cache CI speedup date"),
    # --- 32 ---
    ("source-map-explorer on the production bundle revealed moment.js dragging in every locale; swapping to date-fns saved 180 KB gzipped.", "problem", "ai_coding", False,
     [("source-map-explorer", "tool"), ("moment.js", "library"), ("date-fns", "library")],
     [("date-fns", "moment.js", "REPLACES")],
     "which bundle analyzer finding led to the date library swap",
     "analyzer locale bloat library replacement bundle size save"),
    # --- 33 ---
    ("We switched source map strategy from inline to hidden-source-map with an uploader to Sentry; production bundles stopped leaking full source.", "decision", "ai_coding", False,
     [("hidden-source-map", "pattern"), ("Sentry", "service")],
     [],
     "which source map approach stopped shipping full source to end-users in production",
     "source map strategy hidden upload error tracker leak prevent"),
    # --- 34 ---
    ("CDN bundling via esm.sh for prototypes let demos run with zero install, though CSP rules had to allow the host explicitly.", "fact", "ai_coding", False,
     [("esm.sh", "service"), ("CSP", "protocol")],
     [],
     "which prototyping workflow skips the install step and what security rule it requires",
     "CDN import prototype no install content security policy allow"),
    # --- 35 ---
    ("Snowpack's influence shows up in modern dev servers: native-ESM-first, per-file caching, no bundling in dev.", "fact", "ai_coding", False,
     [("Snowpack", "tool")],
     [],
     "which retired dev server shaped the default of serving native modules unbundled",
     "dev server history native module per file cache influence"),
    # --- 36 ---
    ("Our Vite plugin for env-per-feature branches rewrites import.meta.env at build time so preview deploys target the right API without rebuilds.", "architecture", "ai_coding", False,
     [("Vite", "tool"), ("import.meta.env", "api")],
     [],
     "how do preview deployments point at the right backend without rebuilding the bundle",
     "env injection build time per branch preview deploy backend"),
    # --- 37 ---
    ("The rollup-plugin-visualizer treemap made the 2 MB vendor chunk's owners obvious in five minutes; no more guessing about code-splitting candidates.", "fact", "ai_coding", False,
     [("rollup-plugin-visualizer", "library")],
     [],
     "which visualization tool pointed out the split candidates in the vendor chunk",
     "bundle analyzer treemap vendor chunk ownership split candidate"),
    # --- 38 ---
    ("Chose Parcel over Vite for a quick internal dashboard; zero-config handled the TSX plus PostCSS plus asset hash pipeline in one file.", "decision", "ai_coding", False,
     [("Parcel", "tool"), ("Vite", "tool"), ("PostCSS", "tool")],
     [("Parcel", "Vite", "PREFERS")],
     "which bundler won the quick-dashboard project and what drove the choice",
     "zero config bundler internal tool asset pipeline one file pick"),
    # --- 39 ---
    ("rspack replaced Webpack on the legacy admin app; config compat meant we changed three lines and kept every existing loader.", "decision", "ai_coding", False,
     [("rspack", "tool"), ("Webpack", "tool")],
     [("rspack", "Webpack", "REPLACES")],
     "which drop-in replacement bundler let the old admin UI keep its loaders",
     "native bundler drop in replace config compat loader retain"),
    # --- 40 ---
    ("Stylelint still beats Biome for CSS-specific rules; we run it as a second lint pass until Biome's CSS coverage catches up.", "fact", "ai_coding", False,
     [("Stylelint", "tool"), ("Biome", "tool")],
     [],
     "which CSS-focused linter keeps running alongside the newer all-in-one tool",
     "CSS lint specialised rule coverage second pass parallel tool"),
    # --- 41 ---
    ("Turbopack dev-server HMR on a 200k-LOC Next app stayed under 50 ms per edit; the lazy-compile model actually held up.", "fact", "ai_coding", False,
     [("Turbopack", "tool"), ("Next", "framework"), ("HMR", "concept")],
     [],
     "how fast did the new Rust bundler handle hot module replacement on a large app",
     "HMR latency large app lazy compile measurement bundler"),
    # --- 42 ---
    ("Publishing dual-format ESM and CJS builds with tsup took one config block; the exports map handled the resolver routing cleanly.", "fact", "ai_coding", False,
     [("tsup", "tool"), ("ESM", "concept"), ("CJS", "concept"), ("exports map", "pattern")],
     [],
     "which tool produced the dual-module library build with minimal configuration",
     "dual publish tool config exports field resolver routing"),
    # --- 43 ---
    ("Our GitHub Actions cache hit rate on pnpm-store jumped from 40% to 92% once the cache key used the lockfile hash plus Node version.", "milestone", "ai_coding", False,
     [("GitHub Actions", "service"), ("pnpm-store", "pattern"), ("Node", "platform")],
     [],
     "which cache-key fix drove the install-cache hit rate above 90 percent",
     "CI cache key lockfile hash runtime version hit rate jump"),
    # --- 44 ---
    ("Stopped pinning exact versions in package.json; caret ranges plus a committed lockfile gives us update proposals without churn.", "preference", "ai_coding", False,
     [("package.json", "file")],
     [],
     "which dependency-range policy balances lockfile determinism with upgrade proposals",
     "semver range lockfile caret exact pin update workflow"),
    # --- 45 ---
    ("GraalVM native-image on the Kotlin CLI cut startup from 600 ms to 15 ms; reflection configs needed a tracing agent run to assemble.", "decision", "ai_coding", False,
     [("GraalVM", "tool"), ("Kotlin", "language")],
     [],
     "which JVM tool delivered the sub-20ms CLI startup and what setup did it need",
     "native image startup JIT free reflection config tracing agent"),
    # --- 46 ---
    ("Python wheels with ABI3 tags let us ship one binary per platform across Python 3.9 through 3.13; the CI matrix shrank by four rows.", "decision", "ai_coding", False,
     [("ABI3", "pattern"), ("Python", "language"), ("CI", "infrastructure")],
     [],
     "which wheel tagging choice lets one binary span several Python versions",
     "stable ABI wheel tag binary multi version CI matrix reduce"),
    # --- 47 ---
    ("cargo-nextest ran our Rust test suite in 32 s versus cargo test's 110 s; the per-test process model kept flaky network mocks isolated.", "milestone", "ai_coding", False,
     [("cargo-nextest", "tool"), ("cargo test", "command"), ("Rust", "language")],
     [("cargo-nextest", "cargo test", "IMPROVES_ON")],
     "which test runner cut the Rust suite to a third of its original wall time",
     "test runner parallel process isolation flaky mock speed gain"),
    # --- 48 ---
    ("Dropped husky in favor of lefthook a year ago, and now dropped lefthook for lazygit's built-in hook config on the smallest repos.", "decision", "ai_coding", False,
     [("lefthook", "tool"), ("lazygit", "tool")],
     [],
     "which tool replaced the dedicated git hook runner on the tiny repositories",
     "git hook tooling evolution small repo built in config pick"),
    # --- 49 ---
    ("The TypeScript 5.5 isolatedDeclarations flag forced us to annotate public API return types explicitly; declaration emit time dropped by half.", "fact", "ai_coding", False,
     [("TypeScript 5.5", "language"), ("isolatedDeclarations", "config")],
     [],
     "which TS 5.5 switch traded explicit annotations for faster declaration builds",
     "compiler flag explicit type annotation dts emit speed trade"),
    # --- 50 ---
    ("Babel still pays rent for one thing: targeting ancient Android WebViews where SWC's output trips undefined-symbol errors.", "fact", "ai_coding", False,
     [("Babel", "tool"), ("SWC", "tool"), ("Android WebView", "platform")],
     [],
     "which last-stand use case keeps the older transpiler in the toolchain",
     "legacy transpiler target old runtime symbol gap keep rationale"),
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
