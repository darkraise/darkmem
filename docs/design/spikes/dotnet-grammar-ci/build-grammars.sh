#!/usr/bin/env bash
# darkmem grammar-CI spike: compile tree-sitter grammars per .NET RID with `zig cc`.
# One compiler, every target — no MSVC, no CMake, no tree-sitter CLI (grammar repos
# ship the generated src/parser.c + vendored headers; -Isrc finds them).
#
# Usage: ./build-grammars.sh <grammar-src-dir>... [-o <out-root>] [-r <rid>[,<rid>...]]
#   grammar-src-dir = a cloned grammar repo (e.g. path/to/tree-sitter-yaml)
# Output: <out-root>/<rid>/<libprefix>tree-sitter-<lang>.<ext>  (NuGet runtimes/ layout)
set -euo pipefail

ZIG="${ZIG:-zig}"
OUT="out"
RIDS="win-x64,linux-x64,linux-arm64,osx-x64,osx-arm64"
SRCS=()
while [[ $# -gt 0 ]]; do case "$1" in
  -o) OUT="$2"; shift 2 ;;
  -r) RIDS="$2"; shift 2 ;;
  *) SRCS+=("$1"); shift ;;
esac; done

target_of() { case "$1" in
  win-x64)     echo "x86_64-windows-gnu" ;;
  win-arm64)   echo "aarch64-windows-gnu" ;;
  linux-x64)   echo "x86_64-linux-gnu" ;;
  linux-arm64) echo "aarch64-linux-gnu" ;;
  osx-x64)     echo "x86_64-macos" ;;
  osx-arm64)   echo "aarch64-macos" ;;
  *) echo "unknown RID: $1" >&2; exit 1 ;;
esac; }

artifact_of() { local rid="$1" lang="$2"; case "$rid" in
  win-*)   echo "tree-sitter-${lang}.dll" ;;
  linux-*) echo "libtree-sitter-${lang}.so" ;;
  osx-*)   echo "libtree-sitter-${lang}.dylib" ;;
esac; }

for src in "${SRCS[@]}"; do
  lang="$(basename "$src")"; lang="${lang#tree-sitter-}"
  units=("$src/src/parser.c")
  # External scanners are single compilation units; yaml's schema.*.c are #included by
  # scanner.c (selected via YAML_SCHEMA, default core), never compiled separately.
  [[ -f "$src/src/scanner.c" ]] && units+=("$src/src/scanner.c")
  for rid in ${RIDS//,/ }; do
    mkdir -p "$OUT/$rid"
    art="$OUT/$rid/$(artifact_of "$rid" "$lang")"
    "$ZIG" cc -target "$(target_of "$rid")" -shared -O2 -fno-sanitize=undefined \
      -I"$src/src" "${units[@]}" -o "$art"
    echo "built $art (${#units[@]} unit(s))"
  done
done
