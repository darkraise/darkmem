import { Code2 } from "lucide-react"
import { useCodeSymbolDetail } from "@/hooks/api"
import type { DemoCodeNode } from "@/features/code/types"

// Deliberately narrower than the demo's per-file pseudo-source view: one
// symbol's real, stored source_code (CodeSymbol.source_code, a genuine
// column — code_query.py) rather than a synthesized whole file. The demo's
// buildFileSource fabricates declaration lines and call-derived body
// statements from graph structure; promoting that here would put invented
// code in front of a user labelled as real (T1.59 plan §4, Finding 4).
export function RealCodeInspector({
  selectedNode,
}: {
  selectedNode: DemoCodeNode | null
}) {
  const isSymbol = !!selectedNode && selectedNode.kind !== "file"
  const { data: symbol, isLoading, isError } = useCodeSymbolDetail(
    isSymbol ? selectedNode.id : null,
  )

  if (!selectedNode) {
    return (
      <div className="border-border bg-muted/20 flex w-full min-w-0 flex-col border-b lg:w-[24rem] lg:shrink-0 lg:border-r lg:border-b-0 p-3">
        <p className="text-muted-foreground text-sm">
          Select a symbol in the graph or explorer to read its source here.
        </p>
      </div>
    )
  }

  if (!isSymbol) {
    return (
      <div className="border-border bg-muted/20 flex w-full min-w-0 flex-col border-b lg:w-[24rem] lg:shrink-0 lg:border-r lg:border-b-0 p-3">
        <p className="text-muted-foreground text-sm">
          {selectedNode.name} is a file, not a symbol — select a symbol
          within it to view its real source. This inspector shows one
          symbol's stored source at a time, not a synthesized whole-file
          view.
        </p>
      </div>
    )
  }

  return (
    <div className="border-border bg-muted/20 flex w-full min-w-0 flex-col border-b lg:w-[24rem] lg:shrink-0 lg:border-r lg:border-b-0">
      <div className="border-border bg-card flex items-center gap-1.5 border-b px-2 py-1.5">
        <Code2 aria-hidden className="text-primary-text h-3.5 w-3.5 shrink-0" />
        <span className="min-w-0 flex-1 truncate font-mono text-sm">
          {selectedNode.name}
        </span>
        <span className="text-muted-foreground shrink-0 font-mono text-[10px] uppercase">
          {selectedNode.kind}
        </span>
      </div>
      {isLoading && (
        <p className="text-muted-foreground p-3 text-sm">Loading source…</p>
      )}
      {isError && (
        <p className="text-destructive p-3 text-sm">
          Failed to load this symbol's source.
        </p>
      )}
      {symbol && (
        <div className="min-h-0 flex-1 overflow-auto">
          {symbol.signature && (
            <p className="text-muted-foreground border-border border-b px-3 py-1.5 font-mono text-sm">
              {symbol.signature}
            </p>
          )}
          {symbol.summary && (
            <p className="text-muted-foreground border-border border-b px-3 py-1.5 text-sm">
              {symbol.summary}
            </p>
          )}
          <pre className="bg-background overflow-x-auto p-3 font-mono text-[12px] leading-[1.55] whitespace-pre">
            {symbol.source_code}
          </pre>
        </div>
      )}
    </div>
  )
}
