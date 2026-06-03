import { useState, useMemo, useEffect, type ReactNode } from "react"
import { Button } from "darkraise-ui/components/button"
import { Input } from "darkraise-ui/components/input"
import { ScrollArea } from "darkraise-ui/components/scroll-area"
import {
  Select,
  SelectTrigger,
  SelectValue,
  SelectContent,
  SelectItem,
} from "darkraise-ui/components/select"
import { useCodeSymbols } from "@/hooks/api"
import type { CodeSymbolDetail, CodeSearchResult } from "@/hooks/api"

interface CodeInspectorPanelProps {
  symbolDetail: CodeSymbolDetail | null | undefined
  searchResults: CodeSearchResult[]
  fileList: string[]
  onFileSelect: (id: string) => void
  onSearchResultClick: (result: CodeSearchResult) => void
  repoId: string | null
  nodeColors: Record<string, string>
  symbolKinds: string[]
  onSymbolSelect: (name: string, filePath: string) => void
}

type InspectorTab = "source" | "files" | "results" | "symbols"

const SYMBOLS_PAGE_SIZE = 25
const ALL_KINDS = "__all__"

function FileTree({
  files,
  onSelect,
}: {
  files: string[]
  onSelect: (id: string) => void
}) {
  const tree = useMemo(() => {
    const root: Record<string, Record<string, unknown>> = {}
    for (const fp of files) {
      const parts = fp.replace(/\\/g, "/").split("/")
      let current: Record<string, unknown> = root
      for (const part of parts) {
        if (!current[part]) current[part] = {}
        current = current[part] as Record<string, unknown>
      }
    }
    return root
  }, [files])

  const renderTree = (
    node: Record<string, unknown>,
    path = "",
    depth = 0,
  ): ReactNode[] =>
    Object.keys(node)
      .sort()
      .map((key) => {
        const fullPath = path ? `${path}/${key}` : key
        const children = node[key] as Record<string, unknown>
        const isLeaf = Object.keys(children).length === 0
        return (
          <div key={fullPath}>
            <div
              className={`flex cursor-pointer items-center gap-1.5 rounded px-2 py-1 font-mono text-sm transition-colors ${
                isLeaf
                  ? "text-foreground hover:bg-accent hover:text-foreground"
                  : "font-medium text-muted-foreground"
              }`}
              style={{ paddingLeft: `${depth * 14 + 8}px` }}
              onClick={() => (isLeaf ? onSelect(fullPath) : undefined)}
            >
              <span
                className={`text-sm ${isLeaf ? "text-primary" : "text-muted-foreground"}`}
              >
                {isLeaf ? "◈" : "▸"}
              </span>
              <span className="truncate">{key}</span>
            </div>
            {!isLeaf &&
              renderTree(
                children as Record<string, unknown>,
                fullPath,
                depth + 1,
              )}
          </div>
        )
      })

  return <div>{renderTree(tree)}</div>
}

function SymbolsTab({
  repoId,
  nodeColors,
  symbolKinds,
  onSymbolSelect,
}: {
  repoId: string | null
  nodeColors: Record<string, string>
  symbolKinds: string[]
  onSymbolSelect: (name: string, filePath: string) => void
}) {
  const [rawQuery, setRawQuery] = useState("")
  const [debouncedQuery, setDebouncedQuery] = useState("")
  const [kind, setKind] = useState(ALL_KINDS)
  const [offset, setOffset] = useState(0)

  useEffect(() => {
    const t = setTimeout(() => setDebouncedQuery(rawQuery.trim()), 300)
    return () => clearTimeout(t)
  }, [rawQuery])

  // A new query or kind filter resets to the first page so the offset window
  // never points past a shrunken result set.
  useEffect(() => {
    setOffset(0)
  }, [debouncedQuery, kind])

  const { data, isFetching } = useCodeSymbols({
    repoId,
    q: debouncedQuery || undefined,
    kind: kind === ALL_KINDS ? undefined : kind,
    offset,
    limit: SYMBOLS_PAGE_SIZE,
  })

  const items = data?.items ?? []
  const total = data?.total ?? 0
  const rangeStart = total === 0 ? 0 : offset + 1
  const rangeEnd = Math.min(offset + items.length, total)
  const hasPrev = offset > 0
  const hasNext = offset + SYMBOLS_PAGE_SIZE < total

  if (!repoId) {
    return (
      <div className="flex h-32 flex-col items-center justify-center px-4 text-center">
        <p className="font-mono text-sm text-muted-foreground">
          Select a repository to browse symbols
        </p>
      </div>
    )
  }

  return (
    <div className="flex h-full flex-col">
      <div className="flex shrink-0 flex-col gap-2 border-b border-border p-3">
        <Input
          placeholder="Filter symbols…"
          className="h-8 border-border bg-transparent font-mono text-sm"
          value={rawQuery}
          onChange={(e) => setRawQuery(e.target.value)}
        />
        <Select value={kind} onValueChange={setKind}>
          <SelectTrigger className="h-8 border-border bg-transparent font-mono text-sm">
            <SelectValue placeholder="All kinds" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value={ALL_KINDS}>All</SelectItem>
            {symbolKinds.map((k) => (
              <SelectItem key={k} value={k}>
                {k}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      <ScrollArea className="min-h-0 flex-1">
        <div className="space-y-0.5 p-2">
          {items.length > 0 ? (
            items.map((sym) => (
              <Button
                variant="ghost"
                key={sym.id}
                className="group w-full rounded-md border border-transparent px-3 py-2 text-left transition-colors hover:border-border hover:bg-accent"
                onClick={() => onSymbolSelect(sym.name, sym.file_path)}
              >
                <div className="flex items-center gap-2">
                  <span
                    aria-hidden="true"
                    className="size-2 shrink-0 rounded-full"
                    style={{
                      backgroundColor:
                        nodeColors[sym.kind] ?? "hsl(var(--muted-foreground))",
                    }}
                  />
                  <span className="min-w-0 flex-1 truncate font-mono text-sm text-foreground">
                    {sym.name}
                  </span>
                  <span className="shrink-0 font-mono text-sm text-muted-foreground">
                    {sym.kind}
                  </span>
                </div>
                <div className="mt-1 truncate font-mono text-sm text-muted-foreground">
                  {sym.file_path}
                  {sym.line_start > 0 && (
                    <span> · L{sym.line_start}–{sym.line_end}</span>
                  )}
                </div>
              </Button>
            ))
          ) : (
            <div className="flex h-32 flex-col items-center justify-center px-4 text-center">
              <p className="font-mono text-sm text-muted-foreground">
                {isFetching ? "Loading symbols…" : "No symbols found"}
              </p>
            </div>
          )}
        </div>
      </ScrollArea>

      <div className="flex shrink-0 items-center justify-between gap-2 border-t border-border px-3 py-2">
        <span className="font-mono text-sm text-muted-foreground tabular-nums">
          {rangeStart}-{rangeEnd} of {total}
        </span>
        <div className="flex items-center gap-1">
          <Button
            variant="outline"
            className="h-7 px-2 font-mono text-sm"
            disabled={!hasPrev}
            onClick={() => setOffset((o) => Math.max(0, o - SYMBOLS_PAGE_SIZE))}
          >
            Prev
          </Button>
          <Button
            variant="outline"
            className="h-7 px-2 font-mono text-sm"
            disabled={!hasNext}
            onClick={() => setOffset((o) => o + SYMBOLS_PAGE_SIZE)}
          >
            Next
          </Button>
        </div>
      </div>
    </div>
  )
}

export function CodeInspectorPanel({
  symbolDetail,
  searchResults,
  fileList,
  onFileSelect,
  onSearchResultClick,
  repoId,
  nodeColors,
  symbolKinds,
  onSymbolSelect,
}: CodeInspectorPanelProps) {
  const [activeTab, setActiveTab] = useState<InspectorTab>("source")

  const tabs: { id: InspectorTab; label: string; count?: number }[] = [
    { id: "source", label: "Source" },
    { id: "symbols", label: "Symbols" },
    { id: "files", label: "Files", count: fileList.length || undefined },
    {
      id: "results",
      label: "Results",
      count: searchResults.length || undefined,
    },
  ]

  return (
    <div className="code-inspector-panel flex h-full flex-col border-r border-border">
      <div className="flex shrink-0 items-center gap-2 border-b border-border px-4 py-2.5">
        <div className="h-1.5 w-1.5 rounded-full bg-primary" />
        <span className="font-mono text-sm font-semibold tracking-[0.2em] text-foreground uppercase">
          Code Inspector
        </span>
      </div>

      <div className="flex shrink-0 border-b border-border">
        {tabs.map((tab) => (
          <Button
            variant="ghost"
            key={tab.id}
            className={`relative flex-1 px-3 py-2 font-mono text-sm tracking-widest uppercase transition-colors ${
              activeTab === tab.id
                ? "bg-primary/15 text-primary"
                : "text-muted-foreground hover:bg-accent hover:text-foreground"
            }`}
            onClick={() => setActiveTab(tab.id)}
          >
            {tab.label}
            {tab.count !== undefined && (
              <span className="ml-1 text-sm text-primary">{tab.count}</span>
            )}
            {activeTab === tab.id && (
              <div className="absolute right-2 bottom-0 left-2 h-px bg-gradient-to-r from-transparent via-primary to-transparent" />
            )}
          </Button>
        ))}
      </div>

      {activeTab === "symbols" && (
        <SymbolsTab
          repoId={repoId}
          nodeColors={nodeColors}
          symbolKinds={symbolKinds}
          onSymbolSelect={onSymbolSelect}
        />
      )}

      {activeTab !== "symbols" && (
      <ScrollArea className="min-h-0 flex-1">
        {activeTab === "source" && (
          <div className="p-3">
            {symbolDetail ? (
              <div className="space-y-3">
                <div className="flex items-center gap-2 rounded-md border border-border bg-card px-3 py-1.5">
                  <span className="font-mono text-sm text-primary">◈</span>
                  <span className="flex-1 truncate font-mono text-sm text-foreground">
                    {symbolDetail.file_path ?? symbolDetail.name}
                  </span>
                  {symbolDetail.line_start > 0 && (
                    <span className="shrink-0 font-mono text-sm text-muted-foreground">
                      L{symbolDetail.line_start}–{symbolDetail.line_end}
                    </span>
                  )}
                </div>

                {symbolDetail.signature && (
                  <div className="overflow-hidden rounded-md border border-border bg-card">
                    <div className="border-b border-border px-3 py-1">
                      <span className="font-mono text-sm tracking-[0.2em] text-muted-foreground uppercase">
                        Signature
                      </span>
                    </div>
                    <pre className="overflow-x-auto px-3 py-2 font-mono text-sm leading-relaxed whitespace-pre-wrap text-foreground">
                      {symbolDetail.signature}
                    </pre>
                  </div>
                )}

                {symbolDetail.source_code && (
                  <div className="overflow-hidden rounded-md border border-border bg-card">
                    <div className="flex items-center justify-between border-b border-border px-3 py-1">
                      <span className="font-mono text-sm tracking-[0.2em] text-muted-foreground uppercase">
                        Source
                      </span>
                      <span className="font-mono text-sm text-muted-foreground">
                        {symbolDetail.source_code.split("\n").length} lines
                      </span>
                    </div>
                    <pre className="max-h-[65vh] overflow-x-auto overflow-y-auto px-3 py-2 font-mono text-sm leading-[1.6] text-foreground">
                      {symbolDetail.source_code}
                    </pre>
                  </div>
                )}

                {symbolDetail.docstring && (
                  <div className="overflow-hidden rounded-md border border-border bg-card">
                    <div className="border-b border-border px-3 py-1">
                      <span className="font-mono text-sm tracking-[0.2em] text-muted-foreground uppercase">
                        Docstring
                      </span>
                    </div>
                    <p className="px-3 py-2 font-mono text-sm leading-relaxed whitespace-pre-wrap text-muted-foreground">
                      {symbolDetail.docstring}
                    </p>
                  </div>
                )}
              </div>
            ) : (
              <div className="flex h-48 flex-col items-center justify-center text-center">
                <div className="mb-3 flex h-10 w-10 items-center justify-center rounded-lg border border-border bg-card">
                  <span className="font-mono text-lg text-muted-foreground">◇</span>
                </div>
                <p className="font-mono text-sm text-muted-foreground">
                  Select a symbol to inspect
                </p>
                <p className="mt-1 font-mono text-sm text-muted-foreground">
                  Click a node in the graph
                </p>
              </div>
            )}
          </div>
        )}

        {activeTab === "files" && (
          <div className="py-2">
            {fileList.length > 0 ? (
              <FileTree files={fileList} onSelect={onFileSelect} />
            ) : (
              <div className="flex h-32 flex-col items-center justify-center px-4 text-center">
                <p className="font-mono text-sm text-muted-foreground">
                  No files loaded
                </p>
              </div>
            )}
          </div>
        )}

        {activeTab === "results" && (
          <div className="space-y-0.5 p-2">
            {searchResults.length > 0 ? (
              searchResults.map((r, i) => (
                <Button
                  variant="ghost"
                  key={`${r.file_path}:${r.symbol_name ?? ""}:${i}`}
                  className="group w-full rounded-md border border-transparent px-3 py-2.5 text-left transition-colors hover:border-border hover:bg-accent"
                  onClick={() => onSearchResultClick(r)}
                >
                  <div className="truncate font-mono text-sm text-foreground">
                    {r.file_path}
                  </div>
                  {r.symbol_name && (
                    <div className="mt-0.5 font-mono text-sm text-primary">
                      {r.symbol_name}
                    </div>
                  )}
                  <div className="mt-1 line-clamp-2 font-mono text-sm leading-relaxed text-muted-foreground">
                    {r.chunk_content.slice(0, 140)}
                  </div>
                  <div className="mt-1 font-mono text-sm text-muted-foreground">
                    score {r.score.toFixed(3)}
                  </div>
                </Button>
              ))
            ) : (
              <div className="flex h-32 flex-col items-center justify-center px-4 text-center">
                <p className="font-mono text-sm text-muted-foreground">
                  No search results
                </p>
                <p className="mt-1 font-mono text-sm text-muted-foreground">
                  Press Enter in the search bar
                </p>
              </div>
            )}
          </div>
        )}
      </ScrollArea>
      )}
    </div>
  )
}
