import type { CodeNodeKind, DemoCodeNode } from "@/features/code/types"

export interface DirEntry {
  kind: "dir"
  path: string
  name: string
}

export interface FileEntry {
  kind: "file"
  path: string
  name: string
}

export type TreeEntry = DirEntry | FileEntry

export type TreeRow =
  | { kind: "dir"; key: string; path: string; name: string; depth: number }
  | {
      kind: "file"
      key: string
      path: string
      name: string
      depth: number
      symbolCount: number
    }
  | {
      kind: "symbol"
      key: string
      nodeId: string
      name: string
      symbolKind: CodeNodeKind
      path: string
      depth: number
    }

export interface FileTree {
  /** Direct children of a directory; "" is the repo root. */
  childrenOf: (dir: string) => TreeEntry[]
}

/**
 * A directory index over a flat path list, materialised one level at a
 * time. `childrenOf` is only ever called for a directory the user has
 * expanded, and each answer is cached, so a collapsed subtree costs
 * nothing no matter how many files sit under it.
 */
export function createFileTree(paths: string[]): FileTree {
  const sorted = [...paths].sort()
  const cache = new Map<string, TreeEntry[]>()

  const childrenOf = (dir: string): TreeEntry[] => {
    const cached = cache.get(dir)
    if (cached) return cached
    const prefix = dir === "" ? "" : `${dir}/`
    const dirs = new Set<string>()
    const files: FileEntry[] = []
    for (const path of sorted) {
      if (!path.startsWith(prefix)) continue
      const rest = path.slice(prefix.length)
      if (rest === "") continue
      const slash = rest.indexOf("/")
      if (slash === -1) {
        files.push({ kind: "file", path, name: rest })
      } else {
        dirs.add(rest.slice(0, slash))
      }
    }
    // Directories first, then files — the shape every file explorer uses.
    const entries: TreeEntry[] = [
      ...[...dirs].sort().map<DirEntry>((name) => ({
        kind: "dir",
        path: `${prefix}${name}`,
        name,
      })),
      ...files,
    ]
    cache.set(dir, entries)
    return entries
  }

  return { childrenOf }
}

/**
 * Depth-first walk of the expanded subtrees only, flattened into the row
 * list a virtualizer can window. Symbols hang off their file and are
 * resolved through `symbolsOf`, which is not called for a collapsed file.
 */
export function flattenTree(
  tree: FileTree,
  expanded: ReadonlySet<string>,
  symbolsOf: (path: string) => DemoCodeNode[],
): TreeRow[] {
  const rows: TreeRow[] = []

  const walk = (dir: string, depth: number) => {
    for (const entry of tree.childrenOf(dir)) {
      if (entry.kind === "dir") {
        rows.push({
          kind: "dir",
          key: entry.path,
          path: entry.path,
          name: entry.name,
          depth,
        })
        if (expanded.has(entry.path)) walk(entry.path, depth + 1)
        continue
      }
      const symbols = symbolsOf(entry.path)
      rows.push({
        kind: "file",
        key: entry.path,
        path: entry.path,
        name: entry.name,
        depth,
        symbolCount: symbols.length,
      })
      if (!expanded.has(entry.path)) continue
      for (const symbol of symbols) {
        rows.push({
          kind: "symbol",
          key: `${entry.path}#${symbol.id}`,
          nodeId: symbol.id,
          name: symbol.name,
          symbolKind: symbol.kind,
          path: entry.path,
          depth: depth + 1,
        })
      }
    }
  }

  walk("", 0)
  return rows
}

/** Every ancestor directory of a path, root-first. */
export function ancestorDirs(path: string): string[] {
  const parts = path.split("/")
  parts.pop()
  const out: string[] = []
  let current = ""
  for (const part of parts) {
    current = current === "" ? part : `${current}/${part}`
    out.push(current)
  }
  return out
}
