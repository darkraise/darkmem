import { useEffect, useMemo, useRef, useState } from "react"
import { useVirtualizer } from "@tanstack/react-virtual"
import { ChevronRight, FileCode2, FolderClosed, FolderOpen } from "lucide-react"
import { cn } from "darkraise-ui/lib"
import type { CodeNodeKind, DemoCodeGraph, DemoCodeNode } from "@/features/code/types"
import {
  ancestorDirs,
  createFileTree,
  flattenTree,
  type TreeRow,
} from "../lib/file-tree"
import { chartVar } from "./code-canvas"

const KIND_CHART: Record<CodeNodeKind, number> = {
  file: 1,
  module: 1,
  class: 2,
  struct: 2,
  interface: 2,
  trait: 2,
  enum: 2,
  namespace: 2,
  impl: 2,
  type: 2,
  property: 2,
  method: 3,
  function: 3,
  route: 3,
  tool: 3,
}

const ROW_HEIGHT = 24
const INDENT = 12

export function CodeExplorer({
  files,
  graph,
  query,
  activePath,
  selectedNodeId,
  onOpenFile,
  onSelectSymbol,
}: {
  files: string[]
  graph: DemoCodeGraph | undefined
  query: string
  /** File currently focused in the inspector — its branch stays open. */
  activePath: string | null
  selectedNodeId: string | null
  onOpenFile: (path: string) => void
  onSelectSymbol: (nodeId: string) => void
}) {
  const [expanded, setExpanded] = useState<ReadonlySet<string>>(new Set())
  const scrollRef = useRef<HTMLDivElement | null>(null)

  const symbolsByFile = useMemo(() => {
    const map = new Map<string, DemoCodeNode[]>()
    for (const node of graph?.nodes ?? []) {
      if (node.kind === "file" || node.kind === "module") continue
      map.set(node.file, [...(map.get(node.file) ?? []), node])
    }
    return map
  }, [graph])

  const trimmed = query.trim().toLowerCase()

  // Searching narrows the path set rather than the rendered rows, so a
  // match deep in the tree still arrives with its folders around it.
  const visiblePaths = useMemo(() => {
    if (trimmed === "") return files
    return files.filter(
      (path) =>
        path.toLowerCase().includes(trimmed) ||
        (symbolsByFile.get(path) ?? []).some((s) =>
          s.name.toLowerCase().includes(trimmed),
        ),
    )
  }, [files, trimmed, symbolsByFile])

  const tree = useMemo(() => createFileTree(visiblePaths), [visiblePaths])

  const effectiveExpanded = useMemo(() => {
    if (trimmed === "") return expanded
    const all = new Set<string>()
    for (const path of visiblePaths) {
      for (const dir of ancestorDirs(path)) all.add(dir)
      if ((symbolsByFile.get(path) ?? []).some((s) =>
        s.name.toLowerCase().includes(trimmed),
      )) {
        all.add(path)
      }
    }
    return all
  }, [trimmed, visiblePaths, expanded, symbolsByFile])

  const rows = useMemo(
    () =>
      flattenTree(tree, effectiveExpanded, (path) => symbolsByFile.get(path) ?? []),
    [tree, effectiveExpanded, symbolsByFile],
  )

  // Opening a file from the graph reveals it in the tree instead of leaving
  // the explorer pointing somewhere else.
  useEffect(() => {
    if (!activePath) return
    setExpanded((prev) => {
      const next = new Set(prev)
      let changed = false
      for (const dir of [...ancestorDirs(activePath), activePath]) {
        if (!next.has(dir)) {
          next.add(dir)
          changed = true
        }
      }
      return changed ? next : prev
    })
  }, [activePath])

  const virtualizer = useVirtualizer({
    count: rows.length,
    getScrollElement: () => scrollRef.current,
    estimateSize: () => ROW_HEIGHT,
    overscan: 12,
    getItemKey: (index) => rows[index]?.key ?? index,
  })

  const toggle = (path: string) => {
    setExpanded((prev) => {
      const next = new Set(prev)
      if (next.has(path)) next.delete(path)
      else next.add(path)
      return next
    })
  }

  if (files.length === 0) {
    return (
      <p className="text-muted-foreground p-2.5 text-sm">
        No file listing yet — the tree is written by an index run, so a repo
        that has never been indexed has nothing to browse.
      </p>
    )
  }

  return (
    <div ref={scrollRef} className="min-h-0 flex-1 overflow-auto p-1">
      {rows.length === 0 ? (
        <p className="text-muted-foreground p-2 text-sm">
          No file or symbol matches "{query}" — the graph itself is unchanged.
        </p>
      ) : (
        <div
          className="relative w-full"
          style={{ height: virtualizer.getTotalSize() }}
        >
          {virtualizer.getVirtualItems().map((item) => {
            const row = rows[item.index]
            if (!row) return null
            return (
              <div
                key={item.key}
                className="absolute top-0 left-0 w-full"
                style={{
                  height: ROW_HEIGHT,
                  transform: `translateY(${item.start}px)`,
                }}
              >
                <ExplorerRow
                  row={row}
                  open={row.kind !== "symbol" && effectiveExpanded.has(row.path)}
                  active={
                    row.kind === "symbol"
                      ? row.nodeId === selectedNodeId
                      : row.kind === "file" && row.path === activePath
                  }
                  onActivate={() => {
                    if (row.kind === "dir") toggle(row.path)
                    else if (row.kind === "file") {
                      toggle(row.path)
                      onOpenFile(row.path)
                    } else onSelectSymbol(row.nodeId)
                  }}
                />
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}

function ExplorerRow({
  row,
  open,
  active,
  onActivate,
}: {
  row: TreeRow
  open: boolean
  active: boolean
  onActivate: () => void
}) {
  return (
    <button
      type="button"
      onClick={onActivate}
      aria-expanded={row.kind === "symbol" ? undefined : open}
      title={row.kind === "symbol" ? row.name : row.path}
      className={cn(
        "flex h-full w-full items-center gap-1 rounded-sm pr-1.5 text-left text-sm",
        active ? "bg-primary/12" : "hover:bg-muted/50",
      )}
      style={{ paddingLeft: 4 + row.depth * INDENT }}
    >
      {row.kind === "dir" ? (
        <>
          <ChevronRight
            aria-hidden
            className={cn(
              "h-3 w-3 shrink-0 transition-transform",
              open && "rotate-90",
            )}
          />
          {open ? (
            <FolderOpen aria-hidden className="text-primary/70 h-3.5 w-3.5 shrink-0" />
          ) : (
            <FolderClosed
              aria-hidden
              className="text-muted-foreground h-3.5 w-3.5 shrink-0"
            />
          )}
          <span className="min-w-0 flex-1 truncate">{row.name}</span>
        </>
      ) : row.kind === "file" ? (
        <>
          <ChevronRight
            aria-hidden
            className={cn(
              "h-3 w-3 shrink-0 transition-transform",
              open && "rotate-90",
              row.symbolCount === 0 && "invisible",
            )}
          />
          <FileCode2
            aria-hidden
            className="text-muted-foreground h-3.5 w-3.5 shrink-0"
          />
          <span className="min-w-0 flex-1 truncate font-mono">{row.name}</span>
          {row.symbolCount > 0 && (
            <span className="text-muted-foreground shrink-0 font-mono text-[10px]">
              {row.symbolCount}
            </span>
          )}
        </>
      ) : (
        <>
          <span className="w-3 shrink-0" />
          <span
            aria-hidden
            className="h-2 w-2 shrink-0 rounded-[2px]"
            style={{ background: chartVar(KIND_CHART[row.symbolKind]) }}
          />
          <span className="min-w-0 flex-1 truncate font-mono">{row.name}</span>
          <span className="text-muted-foreground shrink-0 font-mono text-[10px] uppercase">
            {row.symbolKind}
          </span>
        </>
      )}
    </button>
  )
}
