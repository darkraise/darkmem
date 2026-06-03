import { useState, useMemo, type ReactNode } from "react"
import { Button } from "darkraise-ui/components/button"
import { ScrollArea } from "darkraise-ui/components/scroll-area"
import type { CodeSymbolDetail, CodeSearchResult } from "@/hooks/api"

interface CodeInspectorPanelProps {
  symbolDetail: CodeSymbolDetail | null | undefined
  searchResults: CodeSearchResult[]
  fileList: string[]
  onFileSelect: (id: string) => void
  onSearchResultClick: (result: CodeSearchResult) => void
}

type InspectorTab = "source" | "files" | "results"

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

export function CodeInspectorPanel({
  symbolDetail,
  searchResults,
  fileList,
  onFileSelect,
  onSearchResultClick,
}: CodeInspectorPanelProps) {
  const [activeTab, setActiveTab] = useState<InspectorTab>("source")

  const tabs: { id: InspectorTab; label: string; count?: number }[] = [
    { id: "source", label: "Source" },
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
    </div>
  )
}
