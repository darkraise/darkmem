"""One-off emitter for shared-base batch-012 — ai_coding domain (round 3).

Same pattern as _emit_shared_batch_007.py; only ENTRIES changes.
Writes 50 rows to data/v2/shared/batch_012.tmp.jsonl with ids shared-00551..00600.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "shared" / "batch_012.tmp.jsonl"
ID_OFFSET = 550

# (text, memory_type, domain, noise, entities, relationships, qq, qk)
ENTRIES: list[tuple] = [
    # --- 1 ---
    ("VS Code remote-container dev loops finally felt snappy after mounting node_modules into a named volume instead of the workspace.", "problem", "ai_coding", False,
     [("VS Code", "tool"), ("node_modules", "file")],
     [],
     "why were edits inside a containerised editor so sluggish until a volume tweak",
     "remote editor dev loop latency dependency mount fix"),
    # --- 2 ---
    ("During pair reviews Copilot and Claude produced different refactor shapes; Claude stuck to the existing module boundaries more often.", "fact", "ai_coding", False,
     [("Copilot", "tool"), ("Claude", "tool"), ("refactor", "activity")],
     [],
     "how do the two assistant tools behave differently in structural cleanup tasks",
     "assistant comparison refactor boundary respect review"),
    # --- 3 ---
    ("Prefer pair programming with an AI during refactors; it keeps the ratchet moving and forces the why into a comment message.", "preference", "ai_coding", False,
     [("pair programming", "activity"), ("AI", "concept"), ("refactor", "activity")],
     [],
     "which collaborative style works best when reshaping existing code",
     "assistant collaboration refactor cadence rationale capture"),
    # --- 4 ---
    ("Tuning the LSP server's memory cap from 2 GB to 4 GB fixed the freezes the frontend folks kept hitting on huge monorepos.", "problem", "ai_coding", False,
     [("LSP", "protocol"), ("monorepo", "project")],
     [],
     "what setting change stopped the editor stalls on the big repo",
     "language server heap ceiling freeze big repo resolve"),
    # --- 5 ---
    ("IntelliJ inspections still flag real bugs Ruff misses, so the Java folks kept the IDE as the source of truth for their warnings.", "fact", "ai_coding", False,
     [("IntelliJ", "tool"), ("Ruff", "tool"), ("Java", "language")],
     [],
     "why does the Java team lean on the IDE checker over a standalone linter",
     "IDE warning fidelity rule coverage language bias"),
    # --- 6 ---
    ("Capped our static analysis noise budget at fifty open findings per repo; anything over that rotates back to the author.", "decision", "ai_coding", False,
     [("static analysis", "method")],
     [],
     "what rule limits the backlog of unresolved warnings per codebase",
     "analyzer finding cap rotation back ownership policy"),
    # --- 7 ---
    ("Turning on incremental TypeScript project references cut the full build from 90 s to 22 s on 2026-03-02.", "milestone", "ai_coding", False,
     [("TypeScript", "language"), ("project references", "pattern"), ("2026-03-02", "date")],
     [],
     "when did incremental TS builds start shaving most of a minute off the clock",
     "typed JS incremental graph build speedup achievement"),
    # --- 8 ---
    ("Turborepo remote cache now rides on an S3 bucket behind a signed URL gateway; the self-hosted vendor bill went to zero.", "architecture", "ai_coding", False,
     [("Turborepo", "tool"), ("S3", "service")],
     [],
     "where does the monorepo's shared build cache live now that hosting changed",
     "build cache object store signed access cost drop"),
    # --- 9 ---
    ("Kept esbuild over swc on the library side; friendlier plugin story for the codegen we already owned.", "decision", "ai_coding", False,
     [("esbuild", "tool"), ("swc", "tool")],
     [("esbuild", "swc", "PREFERS")],
     "why did the library packages stay on the older of the two bundlers",
     "bundler comparison plugin ecosystem in-house codegen"),
    # --- 10. noise ---
    ("Honestly I might just grab another cup of coffee first.", "fact", "noise", True, [], [], None, None),
    # --- 11 ---
    ("Vitest browser mode ran our component tests in real Chromium so snapshot pixel diffs actually matched what humans saw.", "decision", "ai_coding", False,
     [("Vitest", "library"), ("Chromium", "platform")],
     [],
     "what runner configuration lined up component snapshots with real rendering",
     "test runtime real browser snapshot fidelity pick"),
    # --- 12 ---
    ("Playwright component testing replaced our bespoke JSDOM harness; accessibility assertions got simpler immediately.", "decision", "ai_coding", False,
     [("Playwright", "library"), ("JSDOM", "library")],
     [("Playwright", "JSDOM", "REPLACES")],
     "which component test setup took over from the DOM-emulator harness",
     "UI unit runner swap a11y check simpler wiring"),
    # --- 13 ---
    ("Moving from Jest to Vitest surfaced a pile of ESM boundary surprises the old runner had been hiding with transforms.", "problem", "ai_coding", False,
     [("Jest", "library"), ("Vitest", "library"), ("ESM", "concept")],
     [],
     "what hidden module issues popped up after flipping the test runner",
     "runner migration ES module boundary transform reveal"),
    # --- 14 ---
    ("PyCharm debugger conditional breakpoints remain the fastest way to pause inside a noisy loop.", "preference", "ai_coding", False,
     [("PyCharm", "tool")],
     [],
     "which debugger feature wins for stopping on a rare inner-loop state",
     "IDE pause predicate hot loop iteration inspection"),
    # --- 15 ---
    ("Used rr record-and-replay to chase a non-deterministic segfault in the C++ sidecar; the run playback pinned the root cause in an hour.", "problem", "ai_coding", False,
     [("rr", "tool"), ("C++", "language"), ("segfault", "error")],
     [],
     "how did we catch the flaky crash in the native component",
     "time-travel debugger native crash reproduce playback"),
    # --- 16 ---
    ("Valgrind DHAT surfaced a retained allocation in the parser that jemalloc stats had been rounding away.", "fact", "ai_coding", False,
     [("Valgrind", "tool"), ("DHAT", "tool"), ("jemalloc", "library")],
     [],
     "which heap profiler pointed out the allocation the runtime stats were hiding",
     "allocation profile retained bytes allocator round hidden"),
    # --- 17 ---
    ("Added ASAN and TSAN builds to the nightly matrix; race reports caught a torn write the release build hid for months.", "milestone", "ai_coding", False,
     [("ASAN", "tool"), ("TSAN", "tool")],
     [],
     "when did the sanitiser builds start catching the silent race bug",
     "sanitiser nightly matrix race torn write catch"),
    # --- 18 ---
    ("Wired libFuzzer into the protocol parser; within a weekend it found two crashes the hand-written suite had never triggered.", "decision", "ai_coding", False,
     [("libFuzzer", "tool"), ("protocol parser", "concept")],
     [],
     "what fuzzing change exposed crashes the manual tests had missed",
     "coverage fuzz adoption parser crash discovery weekend"),
    # --- 19 ---
    ("Hypothesis property-based tests caught an off-by-one in the pagination helper that three hand-written cases had stepped over.", "problem", "ai_coding", False,
     [("Hypothesis", "library"), ("pagination", "concept")],
     [],
     "which property-based finding pinned the paging math error",
     "property test generator pagination off-by-one shrink"),
    # --- 20 ---
    ("Adopted mutation testing with mutmut; the score exposed two test files that were effectively asserting nothing.", "decision", "ai_coding", False,
     [("mutmut", "tool"), ("mutation testing", "method")],
     [],
     "what testing technique revealed assertion-free test files",
     "mutation score adoption dead test coverage expose"),
    # --- 21 ---
    ("Golden-file testing works well for snapshot-shaped outputs but rots fast on formatting tweaks; we gate updates behind a reviewer check.", "fact", "ai_coding", False,
     [("Golden-file testing", "pattern")],
     [],
     "when does fixture comparison style work and when does it hurt",
     "snapshot compare style drift reviewer gate update"),
    # --- 22 ---
    ("Pydantic v2 TypeAdapter lets us validate bare dataclasses without subclassing BaseModel; our config loader shrank by a third.", "fact", "ai_coding", False,
     [("Pydantic v2", "library"), ("TypeAdapter", "api"), ("BaseModel", "api"), ("dataclasses", "library")],
     [],
     "what Pydantic helper validates data objects without the usual base class",
     "validator adapter bare class subclass free size drop"),
    # --- 23 ---
    ("Structural pattern matching finally earned its keep when we switched the webhook dispatcher to match on event payload shape.", "fact", "ai_coding", False,
     [("Structural pattern matching", "pattern"), ("webhook dispatcher", "concept")],
     [],
     "which module showed off the value of Python match statements in practice",
     "pattern match real use event dispatch shape case"),
    # --- 24 ---
    ("For new libraries we stayed on poetry rather than PDM or Hatch; the lockfile tooling around CI is the most mature.", "preference", "ai_coding", False,
     [("poetry", "tool"), ("PDM", "tool"), ("Hatch", "tool")],
     [("poetry", "PDM", "PREFERS")],
     "which Python packaging tool wins for starting a new library",
     "packaging tool pick lockfile tooling maturity bias"),
    # --- 25 ---
    ("Rye took over interpreter management on the laptops; no more asking people which pyenv shim they activated.", "decision", "ai_coding", False,
     [("Rye", "tool"), ("pyenv", "tool")],
     [("Rye", "pyenv", "REPLACES")],
     "what tool replaced the old Python version manager on dev machines",
     "interpreter manager swap shim confusion laptop setup"),
    # --- 26 ---
    ("tox-uv shaved sixty percent off the test matrix wall time because environment creation stopped being the long pole.", "milestone", "ai_coding", False,
     [("tox-uv", "tool")],
     [],
     "which plugin made the Python test matrix wall time fall by more than half",
     "env creation speedup matrix long pole plugin adoption"),
    # --- 27 ---
    ("Swapped the make-style task runner for nox; Python-defined sessions read more like code and less like macros.", "decision", "ai_coding", False,
     [("nox", "tool")],
     [],
     "why did we move tasks into a Python-based runner instead of a Makefile-style one",
     "task runner swap readable session definition python"),
    # --- 28 ---
    ("Prefer just over make for new repos; arguments and docstrings come free, recipes read like CLI commands.", "preference", "ai_coding", False,
     [("just", "tool"), ("make", "tool")],
     [("just", "make", "PREFERS")],
     "which command runner wins for greenfield repositories",
     "task runner alternative argument docstring recipe style"),
    # --- 29 ---
    ("The terraform fmt diff kept churning because different editors inserted trailing whitespace; a pre-commit hook settled it.", "problem", "ai_coding", False,
     [("terraform fmt", "command")],
     [],
     "why did the infra formatter keep reporting noise across machines",
     "formatter churn whitespace editor config pre-commit"),
    # --- 30 ---
    ("Ran the Spin Kubernetes WASM runtime for a stateless webhook; cold start went from 800 ms to 40 ms.", "fact", "ai_coding", False,
     [("Spin", "framework"), ("Kubernetes", "platform"), ("WASM", "technology")],
     [],
     "what runtime change cut cold start latency for a small webhook service",
     "wasm runtime cluster cold start reduction stateless webhook"),
    # --- 31 ---
    ("Deno's npm compatibility mostly holds, but postinstall scripts still need a workaround; we keep those packages off the Deno side.", "fact", "ai_coding", False,
     [("Deno", "platform"), ("npm", "tool")],
     [],
     "where does the Deno compatibility story with npm still fall short",
     "cross-runtime compat postinstall script gap carve-out"),
    # --- 32 ---
    ("Bun install produced a lockfile that Yarn could not parse; we held the lockfile swap until it stabilised.", "problem", "ai_coding", False,
     [("Bun", "tool"), ("Yarn", "tool")],
     [],
     "why did the new package manager's lockfile block the migration",
     "lockfile format cross-manager parse block migration wait"),
    # --- 33 ---
    ("Yarn PnP migration hurt because not every editor could resolve modules without node_modules; we rolled back on 2026-02-07.", "problem", "ai_coding", False,
     [("Yarn PnP", "tool"), ("node_modules", "file"), ("2026-02-07", "date")],
     [],
     "when did the plug-and-play module resolution experiment get reverted",
     "zero-install rollback editor resolve incompat date"),
    # --- 34 ---
    ("Corepack adoption standardised the package manager pin in repos; no more people running the wrong one for two years.", "decision", "ai_coding", False,
     [("Corepack", "tool")],
     [],
     "what tool settled which package manager should be used in each repo",
     "manager pin repo uniformity adoption wrong tool drift"),
    # --- 35 ---
    ("npm workspaces still lacks a patch command; contributors pulled in pnpm patch for local fixes and pushed upstream from there.", "problem", "ai_coding", False,
     [("npm workspaces", "tool"), ("pnpm patch", "command")],
     [],
     "which package manager gap do we still work around when editing deps locally",
     "workspace patch missing workaround local dependency fix"),
    # --- 36 ---
    ("The renovate config bikeshed finally ended with a shared preset; new repos inherit the auto-merge rules on day one.", "milestone", "ai_coding", False,
     [("renovate", "tool"), ("auto-merge", "pattern")],
     [],
     "how did the arguments over dependency update rules get resolved",
     "shared preset inheritance update automation convergence"),
    # --- 37 ---
    ("lefthook's parallel group kept failing the whole hook run when a single slow step timed out; we moved that step to serial.", "problem", "ai_coding", False,
     [("lefthook", "tool")],
     [],
     "why did a single slow commit hook step poison the entire parallel run",
     "hook runner parallel group timeout serial workaround"),
    # --- 38 ---
    ("The Prettier plugin for imports sorts by group and produces cleaner diffs than hand-written eslint-plugin-import rules.", "preference", "ai_coding", False,
     [("Prettier", "tool"), ("eslint-plugin-import", "library")],
     [("Prettier", "eslint-plugin-import", "PREFERS")],
     "which import sorter gives tidier diffs across the monorepo",
     "import ordering plugin diff quality lint rule alternative"),
    # --- 39 ---
    ("BiomeJS is now the formatter plus linter for new TypeScript repos; the oxc stack still felt too unfinished for day jobs.", "decision", "ai_coding", False,
     [("BiomeJS", "tool"), ("oxc", "tool"), ("TypeScript", "language")],
     [("BiomeJS", "oxc", "PREFERS")],
     "which all-in-one JS tooling chain did new repos settle on and why",
     "combined format lint tool choice maturity day job reason"),
    # --- 40 ---
    ("Rolldown built on top of Oxc improved Vite 5 cold build times by roughly forty percent in a trial repo.", "fact", "ai_coding", False,
     [("Rolldown", "tool"), ("Oxc", "tool"), ("Vite 5", "tool")],
     [("Rolldown", "Oxc", "BUILDS_ON")],
     "what new Rust-based bundler shaved cold build time on the next bundler version",
     "native bundler derivative build speed trial measurement"),
    # --- 41 ---
    ("Our esbuild plugin for env variable stripping replaced the old babel-plugin-transform-define chain that kept breaking.", "decision", "ai_coding", False,
     [("esbuild", "tool"), ("babel-plugin-transform-define", "library")],
     [("esbuild", "babel-plugin-transform-define", "REPLACES")],
     "which bundler plugin took over runtime-flag stripping from the Babel chain",
     "env strip plugin swap flaky transform alternative adoption"),
    # --- 42 ---
    ("Docker buildx layer caching made the container build four times faster once we split the lock install from the source copy.", "milestone", "ai_coding", False,
     [("Docker", "tool"), ("buildx", "tool")],
     [],
     "which container build change delivered the four-times speed win",
     "image build cache layer split install speedup result"),
    # --- 43 ---
    ("devcontainer.json is checked in and shared across the team; onboarding to the backend service takes an afternoon instead of two days.", "architecture", "ai_coding", False,
     [("devcontainer.json", "file"), ("backend service", "service")],
     [],
     "how do new joiners get a working backend environment so quickly now",
     "dev container spec shared onboarding time reduction"),
    # --- 44 ---
    ("nix-shell gave us a reproducible Python tooling layer that uv alone could not pin; the hashes finally matched across machines.", "decision", "ai_coding", False,
     [("nix-shell", "tool"), ("uv", "tool"), ("Python", "language")],
     [],
     "what tool added reproducibility on top of the Python dependency pinner",
     "reproducible env layer hash match machine parity tool"),
    # --- 45 ---
    ("direnv combined with uv-python activates the right interpreter on cd; hand-running shims stopped mattering in 2026.", "fact", "ai_coding", False,
     [("direnv", "tool"), ("uv-python", "tool")],
     [],
     "which pair of tools auto-switches the Python runtime when you change directory",
     "directory hook interpreter activation shim retirement pair"),
    # --- 46 ---
    ("Switched from asdf to mise for polyglot version management; the Rust core and better resolver cache were the pitch.", "decision", "ai_coding", False,
     [("asdf", "tool"), ("mise", "tool"), ("Rust", "language")],
     [("mise", "asdf", "REPLACES")],
     "which cross-language version manager replaced the older one and why",
     "polyglot runtime manager swap native core resolver cache"),
    # --- 47 ---
    ("Cross-compiling to ARM Macs from Linux CI needed the right target triple; clang's arm64-apple-darwin saved the Rust builds.", "fact", "ai_coding", False,
     [("ARM Macs", "platform"), ("Linux CI", "infrastructure"), ("clang", "tool"), ("Rust", "language")],
     [],
     "which target triple fixed Apple Silicon cross-builds from the Linux pipeline",
     "cross-compile target triple Apple Silicon pipeline setup"),
    # --- 48 ---
    ("Go 1.22's HTTP routing pattern language let us drop gorilla-mux from the internal APIs; matching reads clearly in stdlib now.", "decision", "ai_coding", False,
     [("Go 1.22", "language"), ("gorilla-mux", "library")],
     [("Go 1.22", "gorilla-mux", "REPLACES")],
     "which standard library feature replaced the third-party Go router",
     "stdlib router pattern drop library internal API rewrite"),
    # --- 49 ---
    ("WASI component model for CLIs looks promising but the tooling around debug builds is still rough; we parked a spike until Q3.", "fact", "ai_coding", False,
     [("WASI", "technology"), ("component model", "concept"), ("CLI", "concept")],
     [],
     "why did the WebAssembly component CLI experiment get paused for now",
     "component spec CLI debug tool maturity spike park"),
    # --- 50 ---
    ("Migrated internal docs from Obsidian vaults into Logseq on 2026-03-22; graph queries on backlinks became first-class.", "milestone", "ai_coding", False,
     [("Obsidian", "tool"), ("Logseq", "tool"), ("2026-03-22", "date")],
     [("Logseq", "Obsidian", "REPLACES")],
     "when did the team move the internal knowledge base to the outliner tool",
     "notes platform swap backlink graph query date"),
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
