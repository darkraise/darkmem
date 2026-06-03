import { useState } from "react"
import { Button } from "darkraise-ui/components/button"
import { Checkbox } from "darkraise-ui/components/checkbox"
import { Label } from "darkraise-ui/components/label"
import { ScrollArea } from "darkraise-ui/components/scroll-area"
import type { CodeSymbolDetail, BlastRadiusResult } from "@/hooks/api"

interface CodeAnalysisPanelProps {
  selectedNode: {
    id: string
    label: string
    kind?: string
    file_path?: string
  } | null
  symbolDetail: CodeSymbolDetail | null | undefined
  blastRadiusIds: Set<string> | undefined
  blastRadiusData: BlastRadiusResult | null
  onBlastRadius: () => void
  onClearBlastRadius: () => void
  isBlastRadiusLoading: boolean
  nodeCount: number
  edgeCount: number
  visibleNodeTypes: Set<string>
  visibleEdgeTypes: Set<string>
  onToggleNodeType: (type: string) => void
  onToggleEdgeType: (type: string) => void
  nodeColors: Record<string, string>
  edgeColors: Record<string, string>
  allNodeTypes: string[]
  allEdgeTypes: string[]
}

function SectionHeader({ label }: { label: string }) {
  return (
    <div className="mb-3 flex items-center gap-2">
      <div className="h-1 w-1 rounded-full bg-primary" />
      <span className="font-mono text-sm font-semibold tracking-[0.2em] text-muted-foreground uppercase">
        {label}
      </span>
    </div>
  )
}

function CollapsibleSection({
  label,
  defaultOpen = true,
  children,
}: {
  label: string
  defaultOpen?: boolean
  children: React.ReactNode
}) {
  const [open, setOpen] = useState(defaultOpen)
  return (
    <div className="border-b border-border">
      <Button
        variant="ghost"
        className="flex w-full items-center gap-2 px-4 py-3 transition-colors hover:bg-accent"
        onClick={() => setOpen(!open)}
      >
        <div className="h-1 w-1 shrink-0 rounded-full bg-primary" />
        <span className="flex-1 text-left font-mono text-sm font-semibold tracking-[0.2em] text-muted-foreground uppercase">
          {label}
        </span>
        <span className="font-mono text-sm text-muted-foreground">
          {open ? "▾" : "▸"}
        </span>
      </Button>
      {open && <div className="px-4 pb-3">{children}</div>}
    </div>
  )
}

export function CodeAnalysisPanel({
  selectedNode,
  symbolDetail,
  blastRadiusIds,
  blastRadiusData,
  onBlastRadius,
  onClearBlastRadius,
  isBlastRadiusLoading,
  nodeCount,
  edgeCount,
  visibleNodeTypes,
  visibleEdgeTypes,
  onToggleNodeType,
  onToggleEdgeType,
  nodeColors,
  edgeColors,
  allNodeTypes,
  allEdgeTypes,
}: CodeAnalysisPanelProps) {
  const isAnalyzableSymbol =
    selectedNode &&
    selectedNode.kind !== "file" &&
    selectedNode.kind !== "module"

  return (
    <div className="code-analysis-panel flex h-full flex-col border-l border-border">
      <div className="flex shrink-0 items-center gap-2 border-b border-border px-4 py-2.5">
        <div className="h-1.5 w-1.5 rounded-full bg-primary" />
        <span className="font-mono text-sm font-semibold tracking-[0.2em] text-foreground uppercase">
          Analysis
        </span>
        {selectedNode && (
          <span className="ml-auto max-w-[120px] truncate font-mono text-sm text-muted-foreground">
            {selectedNode.label}
          </span>
        )}
      </div>

      <ScrollArea className="min-h-0 flex-1">
        {selectedNode ? (
          <>
            {/* Symbol Header */}
            <div className="border-b border-border p-4">
              <h3 className="truncate font-mono text-base font-semibold text-foreground">
                {selectedNode.label}
              </h3>
              <div className="mt-2.5 flex flex-wrap gap-1.5">
                {selectedNode.kind && (
                  <span className="rounded-sm border border-primary/30 bg-primary/15 px-2 py-0.5 font-mono text-sm tracking-wider text-primary uppercase">
                    {selectedNode.kind}
                  </span>
                )}
                {symbolDetail?.visibility && (
                  <span className="rounded-sm border border-border bg-muted px-2 py-0.5 font-mono text-sm tracking-wider text-muted-foreground uppercase">
                    {symbolDetail.visibility}
                  </span>
                )}
                {symbolDetail?.enrichment_status && (
                  <span
                    className={`rounded-sm border px-2 py-0.5 font-mono text-sm tracking-wider uppercase ${
                      symbolDetail.enrichment_status === "completed"
                        ? "border-primary/30 bg-primary/15 text-primary"
                        : "border-border bg-muted text-muted-foreground"
                    }`}
                  >
                    {symbolDetail.enrichment_status}
                  </span>
                )}
              </div>

              {symbolDetail?.file_path && (
                <div className="mt-3 flex items-center gap-2">
                  <span className="shrink-0 font-mono text-sm tracking-[0.2em] text-muted-foreground uppercase">
                    Path
                  </span>
                  <span className="truncate font-mono text-sm text-foreground">
                    {symbolDetail.file_path}
                    {symbolDetail.line_start > 0 &&
                      `:${symbolDetail.line_start}–${symbolDetail.line_end}`}
                  </span>
                </div>
              )}
            </div>

            {/* AI Summary */}
            {symbolDetail?.summary && (
              <div className="border-b border-border p-4">
                <SectionHeader label="AI Summary" />
                <p className="font-mono text-sm leading-[1.7] text-foreground">
                  {symbolDetail.summary}
                </p>
              </div>
            )}

            {/* Blast Radius */}
            {isAnalyzableSymbol && (
              <div className="border-b border-border p-4">
                <SectionHeader label="Impact Analysis" />
                <div className="flex gap-2">
                  <Button
                    variant="ghost"
                    className="flex-1 rounded-sm border border-destructive/30 bg-destructive/10 px-3 py-1.5 font-mono text-sm tracking-wider text-destructive uppercase transition-colors hover:border-destructive/50 hover:bg-destructive/20 disabled:cursor-not-allowed disabled:opacity-30"
                    onClick={onBlastRadius}
                    disabled={isBlastRadiusLoading}
                  >
                    {isBlastRadiusLoading ? "Analyzing…" : "Run Blast Radius"}
                  </Button>
                  {blastRadiusIds && (
                    <Button
                      variant="outline"
                      className="rounded-sm border border-border px-3 py-1.5 font-mono text-sm tracking-wider text-muted-foreground uppercase transition-colors hover:bg-accent"
                      onClick={onClearBlastRadius}
                    >
                      Clear
                    </Button>
                  )}
                </div>

                {blastRadiusData && (
                  <div className="mt-3 space-y-2">
                    <div className="flex items-center gap-3">
                      <div className="rounded-sm border border-destructive/20 bg-destructive/10 px-2.5 py-1.5">
                        <div className="font-mono text-base font-bold text-destructive">
                          {blastRadiusData.total}
                        </div>
                        <div className="font-mono text-sm tracking-[0.2em] text-destructive/70 uppercase">
                          Affected
                        </div>
                      </div>
                      <div
                        className={`rounded-sm border px-2.5 py-1.5 ${
                          blastRadiusData.risk === "high"
                            ? "border-destructive/20 bg-destructive/10"
                            : blastRadiusData.risk === "medium"
                              ? "border-primary/20 bg-primary/10"
                              : "border-border bg-muted"
                        }`}
                      >
                        <div
                          className={`font-mono text-base font-bold ${
                            blastRadiusData.risk === "high"
                              ? "text-destructive"
                              : blastRadiusData.risk === "medium"
                                ? "text-primary"
                                : "text-muted-foreground"
                          }`}
                        >
                          {blastRadiusData.risk}
                        </div>
                        <div className="font-mono text-sm tracking-[0.2em] text-muted-foreground uppercase">
                          Risk
                        </div>
                      </div>
                    </div>

                    {blastRadiusData.affected.length > 0 && (
                      <ScrollArea className="mt-2 max-h-40">
                        <div className="space-y-0.5">
                          {blastRadiusData.affected.slice(0, 20).map((a, i) => (
                            <div
                              key={i}
                              className="flex items-center gap-2 rounded-sm px-2 py-1 font-mono text-sm transition-colors hover:bg-accent"
                            >
                              <span className="shrink-0 text-destructive/70">
                                d{a.distance}
                              </span>
                              <span className="w-14 shrink-0 truncate text-muted-foreground">
                                {a.kind}
                              </span>
                              <span className="truncate text-foreground">
                                {a.name}
                              </span>
                            </div>
                          ))}
                          {blastRadiusData.affected.length > 20 && (
                            <div className="px-2 py-1 font-mono text-sm text-muted-foreground">
                              +{blastRadiusData.affected.length - 20} more
                            </div>
                          )}
                        </div>
                      </ScrollArea>
                    )}
                  </div>
                )}
              </div>
            )}
          </>
        ) : (
          <div className="border-b border-border p-4">
            <div className="flex h-32 flex-col items-center justify-center text-center">
              <div className="mb-3 flex h-10 w-10 items-center justify-center rounded-lg border border-border bg-card">
                <span className="font-mono text-lg text-muted-foreground">◆</span>
              </div>
              <p className="font-mono text-sm text-muted-foreground">
                Select a node for analysis
              </p>
            </div>
          </div>
        )}

        {/* Graph Statistics */}
        <div className="border-b border-border p-4">
          <SectionHeader label="Graph Statistics" />
          <div className="grid grid-cols-2 gap-2">
            <div className="rounded-sm border border-border bg-card px-3 py-2">
              <div className="font-mono text-lg font-bold text-foreground tabular-nums">
                {nodeCount.toLocaleString()}
              </div>
              <div className="font-mono text-sm tracking-[0.2em] text-muted-foreground uppercase">
                Nodes
              </div>
            </div>
            <div className="rounded-sm border border-border bg-card px-3 py-2">
              <div className="font-mono text-lg font-bold text-foreground tabular-nums">
                {edgeCount.toLocaleString()}
              </div>
              <div className="font-mono text-sm tracking-[0.2em] text-muted-foreground uppercase">
                Edges
              </div>
            </div>
          </div>
        </div>

        {/* Node Type Filters */}
        <CollapsibleSection label="Node Types" defaultOpen={false}>
          <div className="space-y-0.5">
            {allNodeTypes.map((type) => (
              <Label
                key={type}
                className="group flex cursor-pointer items-center gap-2 py-0.5 font-mono text-sm"
              >
                <Checkbox
                  checked={visibleNodeTypes.has(type)}
                  onCheckedChange={() => onToggleNodeType(type)}
                  className="h-3 w-3 border-border"
                />
                <span
                  className="h-1.5 w-1.5 shrink-0 rounded-full"
                  style={{ backgroundColor: nodeColors[type] }}
                />
                <span
                  className={`capitalize ${visibleNodeTypes.has(type) ? "text-foreground" : "text-muted-foreground"}`}
                >
                  {type}
                </span>
              </Label>
            ))}
          </div>
        </CollapsibleSection>

        {/* Edge Type Filters */}
        <CollapsibleSection label="Edge Types" defaultOpen={false}>
          <div className="space-y-0.5">
            {allEdgeTypes.map((type) => (
              <Label
                key={type}
                className="group flex cursor-pointer items-center gap-2 py-0.5 font-mono text-sm"
              >
                <Checkbox
                  checked={visibleEdgeTypes.has(type)}
                  onCheckedChange={() => onToggleEdgeType(type)}
                  className="h-3 w-3 border-border"
                />
                <span
                  className="h-1.5 w-1.5 shrink-0 rounded-full"
                  style={{ backgroundColor: edgeColors[type] }}
                />
                <span
                  className={`capitalize ${visibleEdgeTypes.has(type) ? "text-foreground" : "text-muted-foreground"}`}
                >
                  {type}
                </span>
              </Label>
            ))}
          </div>
        </CollapsibleSection>
      </ScrollArea>
    </div>
  )
}
