import { useState, useMemo, type ReactNode } from "react";
import type { CodeSymbolDetail, CodeSearchResult } from "@/hooks/api";

interface CodeInspectorPanelProps {
  symbolDetail: CodeSymbolDetail | null | undefined;
  searchResults: CodeSearchResult[];
  fileList: string[];
  onFileSelect: (id: string) => void;
  onSearchResultClick: (result: CodeSearchResult) => void;
}

type InspectorTab = "source" | "files" | "results";

function FileTree({
  files,
  onSelect,
}: {
  files: string[];
  onSelect: (id: string) => void;
}) {
  const tree = useMemo(() => {
    const root: Record<string, Record<string, unknown>> = {};
    for (const fp of files) {
      const parts = fp.replace(/\\/g, "/").split("/");
      let current: Record<string, unknown> = root;
      for (const part of parts) {
        if (!current[part]) current[part] = {};
        current = current[part] as Record<string, unknown>;
      }
    }
    return root;
  }, [files]);

  const renderTree = (
    node: Record<string, unknown>,
    path = "",
    depth = 0,
  ): ReactNode[] =>
    Object.keys(node)
      .sort()
      .map((key) => {
        const fullPath = path ? `${path}/${key}` : key;
        const children = node[key] as Record<string, unknown>;
        const isLeaf = Object.keys(children).length === 0;
        return (
          <div key={fullPath}>
            <div
              className={`flex items-center gap-1.5 py-1 px-2 text-[11px] cursor-pointer rounded transition-colors font-mono ${
                isLeaf
                  ? "text-cyan-300/70 hover:text-cyan-200 hover:bg-cyan-500/8"
                  : "text-zinc-500 font-medium"
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
        );
      });

  return <div>{renderTree(tree)}</div>;
}

export function CodeInspectorPanel({
  symbolDetail,
  searchResults,
  fileList,
  onFileSelect,
  onSearchResultClick,
}: CodeInspectorPanelProps) {
  const [activeTab, setActiveTab] = useState<InspectorTab>("source");

  const tabs: { id: InspectorTab; label: string; count?: number }[] = [
    { id: "source", label: "Source" },
    { id: "files", label: "Files", count: fileList.length || undefined },
    {
      id: "results",
      label: "Results",
      count: searchResults.length || undefined,
    },
  ];

  return (
    <div className="code-inspector-panel flex flex-col h-full border-r border-cyan-900/15">
      <div className="flex items-center gap-2 px-4 py-2.5 border-b border-cyan-900/15 shrink-0">
        <div className="w-1.5 h-1.5 rounded-full bg-cyan-400 shadow-[0_0_6px_rgba(34,211,238,0.5)]" />
        <span className="text-[10px] font-semibold tracking-[0.2em] uppercase text-cyan-300/70 font-mono">
          Code Inspector
        </span>
      </div>

      <div className="flex border-b border-cyan-900/15 shrink-0">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            className={`flex-1 px-3 py-2 text-[10px] font-mono uppercase tracking-widest transition-colors relative ${
              activeTab === tab.id
                ? "text-cyan-300 bg-cyan-500/5"
                : "text-zinc-600 hover:text-zinc-400 hover:bg-white/[0.02]"
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
              <div className="absolute bottom-0 left-2 right-2 h-px bg-gradient-to-r from-transparent via-cyan-400/50 to-transparent" />
            )}
          </button>
        ))}
      </div>

      <div className="flex-1 overflow-y-auto scrollbar-thin min-h-0">
        {activeTab === "source" && (
          <div className="p-3">
            {symbolDetail ? (
              <div className="space-y-3">
                <div className="flex items-center gap-2 px-3 py-1.5 rounded-md bg-cyan-500/5 border border-cyan-500/8">
                  <span className="text-[9px] text-cyan-500/50 font-mono">
                    ◈
                  </span>
                  <span className="text-[11px] text-cyan-300/60 font-mono truncate flex-1">
                    {symbolDetail.file_path ?? symbolDetail.name}
                  </span>
                  {symbolDetail.line_start > 0 && (
                    <span className="text-[9px] text-cyan-500/30 font-mono shrink-0">
                      L{symbolDetail.line_start}–{symbolDetail.line_end}
                    </span>
                  )}
                </div>

                {symbolDetail.signature && (
                  <div className="rounded-md border border-cyan-500/8 bg-[#0a0a14] overflow-hidden">
                    <div className="px-3 py-1 border-b border-cyan-500/5">
                      <span className="text-[8px] uppercase tracking-[0.2em] text-cyan-500/35 font-mono">
                        Signature
                      </span>
                    </div>
                    <pre className="px-3 py-2 text-[11px] font-mono text-cyan-100/80 overflow-x-auto whitespace-pre-wrap leading-relaxed">
                      {symbolDetail.signature}
                    </pre>
                  </div>
                )}

                {symbolDetail.source_code && (
                  <div className="rounded-md border border-cyan-500/8 bg-[#0a0a14] overflow-hidden">
                    <div className="flex items-center justify-between px-3 py-1 border-b border-cyan-500/5">
                      <span className="text-[8px] uppercase tracking-[0.2em] text-cyan-500/35 font-mono">
                        Source
                      </span>
                      <span className="text-[8px] text-zinc-700 font-mono">
                        {symbolDetail.source_code.split("\n").length} lines
                      </span>
                    </div>
                    <pre className="px-3 py-2 text-[11px] leading-[1.6] font-mono text-zinc-300/80 overflow-x-auto max-h-[65vh] overflow-y-auto scrollbar-thin">
                      {symbolDetail.source_code}
                    </pre>
                  </div>
                )}

                {symbolDetail.docstring && (
                  <div className="rounded-md border border-violet-500/8 bg-violet-500/[0.02] overflow-hidden">
                    <div className="px-3 py-1 border-b border-violet-500/5">
                      <span className="text-[8px] uppercase tracking-[0.2em] text-violet-500/35 font-mono">
                        Docstring
                      </span>
                    </div>
                    <p className="px-3 py-2 text-[11px] font-mono text-violet-200/60 leading-relaxed whitespace-pre-wrap">
                      {symbolDetail.docstring}
                    </p>
                  </div>
                )}
              </div>
            ) : (
              <div className="flex flex-col items-center justify-center h-48 text-center">
                <div className="w-10 h-10 rounded-lg border border-cyan-500/8 bg-cyan-500/[0.03] flex items-center justify-center mb-3">
                  <span className="text-cyan-500/25 text-lg font-mono">
                    ◇
                  </span>
                </div>
                <p className="text-[11px] text-zinc-600 font-mono">
                  Select a symbol to inspect
                </p>
                <p className="text-[10px] text-zinc-700 font-mono mt-1">
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
              <div className="flex flex-col items-center justify-center h-32 text-center px-4">
                <p className="text-[11px] text-zinc-600 font-mono">
                  No files loaded
                </p>
              </div>
            )}
          </div>
        )}

        {activeTab === "results" && (
          <div className="p-2 space-y-0.5">
            {searchResults.length > 0 ? (
              searchResults.map((r, i) => (
                <button
                  key={`${r.file_path}:${r.symbol_name ?? ""}:${i}`}
                  className="w-full text-left px-3 py-2.5 rounded-md border border-transparent hover:border-cyan-500/8 hover:bg-cyan-500/[0.03] transition-colors group"
                  onClick={() => onSearchResultClick(r)}
                >
                  <div className="text-[11px] text-cyan-300/60 font-mono truncate group-hover:text-cyan-200/80">
                    {r.file_path}
                  </div>
                  {r.symbol_name && (
                    <div className="text-[10px] text-cyan-500/40 font-mono mt-0.5">
                      {r.symbol_name}
                    </div>
                  )}
                  <div className="text-[10px] text-zinc-600 font-mono mt-1 line-clamp-2 leading-relaxed">
                    {r.chunk_content.slice(0, 140)}
                  </div>
                  <div className="text-[8px] text-zinc-700 font-mono mt-1">
                    score {r.score.toFixed(3)}
                  </div>
                </button>
              ))
            ) : (
              <div className="flex flex-col items-center justify-center h-32 text-center px-4">
                <p className="text-[11px] text-zinc-600 font-mono">
                  No search results
                </p>
                <p className="text-[10px] text-zinc-700 font-mono mt-1">
                  Press Enter in the search bar
                </p>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
