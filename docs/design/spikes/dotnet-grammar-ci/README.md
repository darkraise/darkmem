# Spike: tree-sitter grammar build pipeline (the #14 residual)

**Date:** 2026-07-24 · **Context:** feeds `docs/design/03a-backend-stack-dotnet-viability.md` §5.1.1 (matrix row #14, the last 🔴-derived residual).

## Why

After the 2026-07-23 spikes, #14 was the one item still gating "all green": 12 of
darkmem's 33 grammars are not bundled by TreeSitter.DotNet and were assumed to need
"a C toolchain + per-RID CI pipeline" — bounded, but unproven, and this dev box has
no C compiler. This spike proves the whole residual on the dev box itself.

## What it proves (all observed, exit 0)

1. **`zig cc` is the whole toolchain.** One ~80 MB winget install (`zig.zig`, 0.16.0)
   compiles every grammar *and cross-compiles every RID from one box* — no MSVC, no
   CMake, no tree-sitter CLI, no per-OS runners:
   `-target x86_64-windows-gnu | x86_64-linux-gnu | aarch64-linux-gnu | x86_64-macos | aarch64-macos`
   → verified PE32+ `.dll`, ELF `.so`, and Mach-O arm64 `.dylib` from this Windows box.
2. **All 12 missing grammars compile** (14 artifacts — xml → xml+dtd, markdown →
   block+inline): kotlin, lua, yaml, sql, zig, elixir, cmake, make, objc, xml, regex,
   markdown. That includes **all 8 hand-written external scanners** (the hard case a
   pure-managed port could never absorb). Grammar repos ship generated `src/parser.c`
   + vendored headers, so `-Isrc` + compile `parser.c [scanner.c]` is the entire build.
3. **No binding fork is needed for grammar delivery.** TreeSitter.DotNet's
   `new Language(libraryPath, "tree_sitter_<lang>")` constructor loads external
   grammar libraries first-class. Self-compiled DLLs parse and run S-expression
   queries end to end: regex `(alternation)` capture, yaml `block_mapping_pair` keys
   through the 52 KB external scanner, and 12/12 breadth parses with `hasError=false`.
   Grammars can ship as darkmem's **own artifact pack** (NuGet `runtimes/<rid>/native/`
   layout or a data directory); the binding stays a stock NuGet dependency.

```
[1] regex parse: root='pattern', hasError=False        query (alternation): [b|c]
[2] yaml  parse: root='stream',  hasError=False        keys: [server, host, ports]
[3] breadth: kotlin, lua, sql, zig, elixir, cmake, make, objc, xml, dtd,
    markdown, markdown-inline — 12/12 OK (all roots error-free)
[verdict] ... WORKS (12/12 breadth)
```

## Findings / gotchas

- **`tree-sitter-sql` does not commit `parser.c` on its default branch** — clone the
  `gh-pages` branch (generated sources published there). Every other repo ships it.
- **`zig cc` enables UBSan trap-on-UB by default** — build with
  `-fno-sanitize=undefined` (in `build-grammars.sh`) or hand-written scanners with
  benign UB can die with "illegal instruction" at parse time.
- Both spiked grammar sets are ABI/`LANGUAGE_VERSION` 15; the binding's bundled
  libtree-sitter accepts them. Pin grammar checkouts and re-verify node-type names
  against the Python-side versions (03a §5.1's caveat stands — e.g. these fresh
  checkouts may differ from the pinned PyPI wheel versions darkmem uses today).
- winget's zig is a portable install: binary at
  `%LOCALAPPDATA%\Microsoft\WinGet\Packages\zig.zig_*\zig-x86_64-windows-*\zig.exe`
  (new shells get it on PATH).

## Stage 2 (2026-07-24): single-DLL grammar pack — 6/6 from one file

`build-grammar-pack.sh` links ALL grammars into **one** native library per RID:
each grammar compiles as its own translation unit against its own vendored
`tree_sitter/parser.h` (a combined compile would resolve every `#include` against
the first vendored header found, silently mixing ABI versions), then all objects
link into a single shared library. 16 grammars (the 12 missing **plus python and
c-sharp**, proving bundled + unbundled sources mix) = 28 objects → one ~32 MB
`darkmem-grammars.dll` / `libdarkmem-grammars.so`, **zero symbol collisions**
(grammars export only namespaced `tree_sitter_<lang>*`). The spike loaded six
languages from that single file — kotlin, yaml, sql, markdown, python, c_sharp —
all parsed error-free (6/6). Grammars reference no libtree-sitter symbols, so the
pack needs no core linkage; the stock binding's bundled core loads it.

## The production shape this implies

A **standalone grammar-pack project** (own repo or `tools/` folder): pinned grammar
checkouts (submodules or SHA manifest) + `build-grammar-pack.sh` + a thin managed
facade, published as one NuGet with `runtimes/<rid>/native/` — the app adds ONE
PackageReference and calls `new Language(packPath, "tree_sitter_<lang>")`. Built by
one single-runner CI job (any OS): checkout → install zig → pack all RIDs. No OS
matrix, no MSVC/Xcode, no tree-sitter CLI. Optionally cover all 33 languages so
even the 21 bundled grammars stop depending on binding releases.

## Reproduce

```
winget install -e --id zig.zig            # the only toolchain needed
git clone --depth 1 <the grammar repos; sql: -b gh-pages>
./build-grammars.sh <grammar-dirs...> -o out            # per-grammar libs, all 5 RIDs
./build-grammar-pack.sh <grammar-dirs...> -o pack       # OR one pack lib per RID
dotnet run -c Release -- out/win-x64 pack/win-x64/darkmem-grammars.dll
```

Exit code 0 = all checks pass. Multi-grammar repos pass their subdirs
(`tree-sitter-xml/xml`, `tree-sitter-xml/dtd`, `tree-sitter-markdown/tree-sitter-markdown`,
`tree-sitter-markdown/tree-sitter-markdown-inline`).
