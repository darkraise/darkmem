#!/usr/bin/env bash
# darkmem grammar-pack build: ALL grammars linked into ONE native library per RID.
#
# Each grammar compiles as its own translation unit against its OWN vendored
# tree_sitter/parser.h (-I per grammar — a single combined compile would resolve every
# #include against the first vendored header found, silently mixing ABI versions).
# The objects then link into a single shared library exporting every
# tree_sitter_<lang>() entry point. Grammars reference no libtree-sitter symbols
# (parser.h is types/macros only), so the pack needs NO core linkage — the stock
# TreeSitter.DotNet core loads it via `new Language(packPath, "tree_sitter_<lang>")`.
#
# Usage: ./build-grammar-pack.sh <grammar-src-dir>... [-o <out-root>] [-r <rid>[,...]] [-n <name>]
set -euo pipefail

ZIG="${ZIG:-zig}"
OUT="out"
RIDS="win-x64,linux-x64,linux-arm64,osx-x64,osx-arm64"
NAME="darkmem-grammars"
SRCS=()
while [[ $# -gt 0 ]]; do case "$1" in
  -o) OUT="$2"; shift 2 ;;
  -r) RIDS="$2"; shift 2 ;;
  -n) NAME="$2"; shift 2 ;;
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

pack_of() { case "$1" in
  win-*)   echo "${NAME}.dll" ;;
  linux-*) echo "lib${NAME}.so" ;;
  osx-*)   echo "lib${NAME}.dylib" ;;
esac; }

for rid in ${RIDS//,/ }; do
  tgt="$(target_of "$rid")"
  objdir="$OUT/$rid/obj"; mkdir -p "$objdir"
  objs=()
  for src in "${SRCS[@]}"; do
    lang="$(basename "$src")"; lang="${lang#tree-sitter-}"
    for unit in parser scanner; do
      c="$src/src/$unit.c"; [[ -f "$c" ]] || continue
      o="$objdir/${lang}-${unit}.o"
      "$ZIG" cc -target "$tgt" -c -O2 -fno-sanitize=undefined -I"$src/src" "$c" -o "$o"
      objs+=("$o")
    done
  done
  pack="$OUT/$rid/$(pack_of "$rid")"
  "$ZIG" cc -target "$tgt" -shared "${objs[@]}" -o "$pack"
  echo "packed $pack (${#objs[@]} objects)"
done
