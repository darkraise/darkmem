import { useState, useMemo, type ReactNode } from "react"
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
              className={`flex cursor-pointer items-center gap-1.5 rounded px-2 py-1 font-mono text-[11px] transition-colors ${
                isLeaf
                  ? "text-cyan-300/70 hover:bg-cyan-500/8 hover:text-cyan-200"
                  : "font-medium text-zinc-500"
              }`}
              style={{ paddingLeft: `${depth * 14 + 8}px` }}
              onClick={() => (isLeaf ? onSelect(fullPath) : undefined)}
            >
              <span
                className={`text-[9px] ${isLeaf ? "text-cyan-500/50" : "text-zinc-600"}`}
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
    <div className="code-inspector-panel flex h-full flex-col border-r border-cyan-900/15">
      <div className="flex shrink-0 items-center gap-2 border-b border-cyan-900/15 px-4 py-2.5">
        <div className="h-1.5 w-1.5 rounded-full bg-cyan-400 shadow-[0_0_6px_rgba(34,211,238,0.5)]" />
        <span className="font-mono text-[10px] font-semibold tracking-[0.2em] text-cyan-300/70 uppercase">
          Code Inspector
        </span>
      </div>

      <div className="flex shrink-0 border-b border-cyan-900/15">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            className={`relative flex-1 px-3 py-2 font-mono text-[10px] tracking-widest uppercase transition-colors ${
              activeTab === tab.id
                ? "bg-cyan-500/5 text-cyan-300"
                : "text-zinc-600 hover:bg-white/[0.02] hover:text-zinc-400"
            }`}
            onClick={() => setActiveTab(tab.id)}
          >
            {tab.label}
            {tab.count !== undefined && (
              <span className="ml-1 text-[8px] text-cyan-500/50">
                {tab.count}
              </span>
            )}
            {activeTab === tab.id && (
              <div className="absolute right-2 bottom-0 left-2 h-px bg-gradient-to-r from-transparent via-cyan-400/50 to-transparent" />
            )}
          </button>
        ))}
      </div>

      <div className="min-h-0 flex-1 scrollbar-thin overflow-y-auto">
        {activeTab === "source" && (
          <div className="p-3">
            {symbolDetail ? (
              <div className="space-y-3">
                <div className="flex items-center gap-2 rounded-md border border-cyan-500/8 bg-cyan-500/5 px-3 py-1.5">
                  <span className="font-mono text-[9px] text-cyan-500/50">
                    ◈
                  </span>
                  <span className="flex-1 truncate font-mono text-[11px] text-cyan-300/60">
                    {symbolDetail.file_path ?? symbolDetail.name}
                  </span>
                  {symbolDetail.line_start > 0 && (
                    <span className="shrink-0 font-mono text-[9px] text-cyan-500/30">
                      L{symbolDetail.line_start}–{symbolDetail.line_end}
                    </span>
                  )}
                </div>

                {symbolDetail.signature && (
                  <div className="overflow-hidden rounded-md border border-cyan-500/8 bg-[#0a0a14]">
                    <div className="border-b border-cyan-500/5 px-3 py-1">
                      <span className="font-mono text-[8px] tracking-[0.2em] text-cyan-500/35 uppercase">
                        Signature
                      </span>
                    </div>
                    <pre className="overflow-x-auto px-3 py-2 font-mono text-[11px] leading-relaxed whitespace-pre-wrap text-cyan-100/80">
                      {symbolDetail.signature}
                    </pre>
                  </div>
                )}

                {symbolDetail.source_code && (
                  <div className="overflow-hidden rounded-md border border-cyan-500/8 bg-[#0a0a14]">
                    <div className="flex items-center justify-between border-b border-cyan-500/5 px-3 py-1">
                      <span className="font-mono text-[8px] tracking-[0.2em] text-cyan-500/35 uppercase">
                        Source
                      </span>
                      <span className="font-mono text-[8px] text-zinc-700">
                        {symbolDetail.source_code.split("\n").length} lines
                      </span>
                    </div>
                    <pre className="max-h-[65vh] scrollbar-thin overflow-x-auto overflow-y-auto px-3 py-2 font-mono text-[11px] leading-[1.6] text-zinc-300/80">
                      {symbolDetail.source_code}
                    </pre>
                  </div>
                )}

                {symbolDetail.docstring && (
                  <div className="overflow-hidden rounded-md border border-violet-500/8 bg-violet-500/[0.02]">
                    <div className="border-b border-violet-500/5 px-3 py-1">
                      <span className="font-mono text-[8px] tracking-[0.2em] text-violet-500/35 uppercase">
                        Docstring
                      </span>
                    </div>
                    <p className="px-3 py-2 font-mono text-[11px] leading-relaxed whitespace-pre-wrap text-violet-200/60">
                      {symbolDetail.docstring}
                    </p>
                  </div>
                )}
              </div>
            ) : (
              <div className="flex h-48 flex-col items-center justify-center text-center">
                <div className="mb-3 flex h-10 w-10 items-center justify-center rounded-lg border border-cyan-500/8 bg-cyan-500/[0.03]">
                  <span className="font-mono text-lg text-cyan-500/25">◇</span>
                </div>
                <p className="font-mono text-[11px] text-zinc-600">
                  Select a symbol to inspect
                </p>
                <p className="mt-1 font-mono text-[10px] text-zinc-700">
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
                <p className="font-mono text-[11px] text-zinc-600">
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
                <button
                  key={`${r.file_path}:${r.symbol_name ?? ""}:${i}`}
                  className="group w-full rounded-md border border-transparent px-3 py-2.5 text-left transition-colors hover:border-cyan-500/8 hover:bg-cyan-500/[0.03]"
                  onClick={() => onSearchResultClick(r)}
                >
                  <div className="truncate font-mono text-[11px] text-cyan-300/60 group-hover:text-cyan-200/80">
                    {r.file_path}
                  </div>
                  {r.symbol_name && (
                    <div className="mt-0.5 font-mono text-[10px] text-cyan-500/40">
                      {r.symbol_name}
                    </div>
                  )}
                  <div className="mt-1 line-clamp-2 font-mono text-[10px] leading-relaxed text-zinc-600">
                    {r.chunk_content.slice(0, 140)}
                  </div>
                  <div className="mt-1 font-mono text-[8px] text-zinc-700">
                    score {r.score.toFixed(3)}
                  </div>
                </button>
              ))
            ) : (
              <div className="flex h-32 flex-col items-center justify-center px-4 text-center">
                <p className="font-mono text-[11px] text-zinc-600">
                  No search results
                </p>
                <p className="mt-1 font-mono text-[10px] text-zinc-700">
                  Press Enter in the search bar
                </p>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
