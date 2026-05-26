import { useState } from "react"
import { Checkbox } from "darkraise-ui/components/checkbox"
import { Label } from "darkraise-ui/components/label"
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

function SectionHeader({ color, label }: { color: string; label: string }) {
  return (
    <div className="mb-3 flex items-center gap-2">
      <div
        className="h-1 w-1 rounded-full"
        style={{
          backgroundColor: color,
          boxShadow: `0 0 4px ${color}80`,
        }}
      />
      <span className="font-mono text-[9px] font-semibold tracking-[0.2em] text-zinc-500 uppercase">
        {label}
      </span>
    </div>
  )
}

function CollapsibleSection({
  color,
  label,
  defaultOpen = true,
  children,
}: {
  color: string
  label: string
  defaultOpen?: boolean
  children: React.ReactNode
}) {
  const [open, setOpen] = useState(defaultOpen)
  return (
    <div className="border-b border-cyan-900/10">
      <button
        className="flex w-full items-center gap-2 px-4 py-3 transition-colors hover:bg-white/[0.01]"
        onClick={() => setOpen(!open)}
      >
        <div
          className="h-1 w-1 shrink-0 rounded-full"
          style={{
            backgroundColor: color,
            boxShadow: `0 0 4px ${color}80`,
          }}
        />
        <span className="flex-1 text-left font-mono text-[9px] font-semibold tracking-[0.2em] text-zinc-500 uppercase">
          {label}
        </span>
        <span className="font-mono text-[9px] text-zinc-700">
          {open ? "▾" : "▸"}
        </span>
      </button>
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
    <div className="code-analysis-panel flex h-full flex-col border-l border-cyan-900/15">
      <div className="flex shrink-0 items-center gap-2 border-b border-cyan-900/15 px-4 py-2.5">
        <div className="h-1.5 w-1.5 rounded-full bg-violet-400 shadow-[0_0_6px_rgba(139,92,246,0.5)]" />
        <span className="font-mono text-[10px] font-semibold tracking-[0.2em] text-violet-300/70 uppercase">
          Analysis
        </span>
        {selectedNode && (
          <span className="ml-auto max-w-[120px] truncate font-mono text-[9px] text-zinc-600">
            {selectedNode.label}
          </span>
        )}
      </div>

      <div className="min-h-0 flex-1 scrollbar-thin overflow-y-auto">
        {selectedNode ? (
          <>
            {/* Symbol Header */}
            <div className="border-b border-cyan-900/10 p-4">
              <h3 className="truncate font-mono text-sm font-semibold text-cyan-100/90">
                {selectedNode.label}
              </h3>
              <div className="mt-2.5 flex flex-wrap gap-1.5">
                {selectedNode.kind && (
                  <span className="rounded-sm border border-cyan-500/15 bg-cyan-500/5 px-2 py-0.5 font-mono text-[9px] tracking-wider text-cyan-400/70 uppercase">
                    {selectedNode.kind}
                  </span>
                )}
                {symbolDetail?.visibility && (
                  <span className="rounded-sm border border-violet-500/15 bg-violet-500/5 px-2 py-0.5 font-mono text-[9px] tracking-wider text-violet-400/70 uppercase">
                    {symbolDetail.visibility}
                  </span>
                )}
                {symbolDetail?.enrichment_status && (
                  <span
                    className={`rounded-sm border px-2 py-0.5 font-mono text-[9px] tracking-wider uppercase ${
                      symbolDetail.enrichment_status === "completed"
                        ? "border-emerald-500/15 bg-emerald-500/5 text-emerald-400/70"
                        : "border-amber-500/15 bg-amber-500/5 text-amber-400/70"
                    }`}
                  >
                    {symbolDetail.enrichment_status}
                  </span>
                )}
              </div>

              {symbolDetail?.file_path && (
                <div className="mt-3 flex items-center gap-2">
                  <span className="shrink-0 font-mono text-[8px] tracking-[0.2em] text-zinc-600 uppercase">
                    Path
                  </span>
                  <span className="truncate font-mono text-[10px] text-zinc-400/80">
                    {symbolDetail.file_path}
                    {symbolDetail.line_start > 0 &&
                      `:${symbolDetail.line_start}–${symbolDetail.line_end}`}
                  </span>
                </div>
              )}
            </div>

            {/* AI Summary */}
            {symbolDetail?.summary && (
              <div className="border-b border-cyan-900/10 p-4">
                <SectionHeader color="#22d3ee" label="AI Summary" />
                <p className="font-mono text-[11px] leading-[1.7] text-zinc-300/70">
                  {symbolDetail.summary}
                </p>
              </div>
            )}

            {/* Blast Radius */}
            {isAnalyzableSymbol && (
              <div className="border-b border-cyan-900/10 p-4">
                <SectionHeader color="#f43f5e" label="Impact Analysis" />
                <div className="flex gap-2">
                  <button
                    className="flex-1 rounded-sm border border-rose-500/15 bg-rose-500/[0.03] px-3 py-1.5 font-mono text-[10px] tracking-wider text-rose-400/70 uppercase transition-colors hover:border-rose-500/25 hover:bg-rose-500/8 disabled:cursor-not-allowed disabled:opacity-30"
                    onClick={onBlastRadius}
                    disabled={isBlastRadiusLoading}
                  >
                    {isBlastRadiusLoading ? "Analyzing…" : "Run Blast Radius"}
                  </button>
                  {blastRadiusIds && (
                    <button
                      className="rounded-sm border border-zinc-700/50 px-3 py-1.5 font-mono text-[10px] tracking-wider text-zinc-500 uppercase transition-colors hover:bg-zinc-800/50"
                      onClick={onClearBlastRadius}
                    >
                      Clear
                    </button>
                  )}
                </div>

                {blastRadiusData && (
                  <div className="mt-3 space-y-2">
                    <div className="flex items-center gap-3">
                      <div className="rounded-sm border border-rose-500/10 bg-rose-500/5 px-2.5 py-1.5">
                        <div className="font-mono text-base font-bold text-rose-300/80">
                          {blastRadiusData.total}
                        </div>
                        <div className="font-mono text-[8px] tracking-[0.2em] text-rose-500/40 uppercase">
                          Affected
                        </div>
                      </div>
                      <div
                        className={`rounded-sm border px-2.5 py-1.5 ${
                          blastRadiusData.risk === "high"
                            ? "border-rose-500/10 bg-rose-500/5"
                            : blastRadiusData.risk === "medium"
                              ? "border-amber-500/10 bg-amber-500/5"
                              : "border-emerald-500/10 bg-emerald-500/5"
                        }`}
                      >
                        <div
                          className={`font-mono text-base font-bold ${
                            blastRadiusData.risk === "high"
                              ? "text-rose-300/80"
                              : blastRadiusData.risk === "medium"
                                ? "text-amber-300/80"
                                : "text-emerald-300/80"
                          }`}
                        >
                          {blastRadiusData.risk}
                        </div>
                        <div className="font-mono text-[8px] tracking-[0.2em] text-zinc-500 uppercase">
                          Risk
                        </div>
                      </div>
                    </div>

                    {blastRadiusData.affected.length > 0 && (
                      <div className="mt-2 max-h-40 scrollbar-thin space-y-0.5 overflow-y-auto">
                        {blastRadiusData.affected.slice(0, 20).map((a, i) => (
                          <div
                            key={i}
                            className="flex items-center gap-2 rounded-sm px-2 py-1 font-mono text-[10px] transition-colors hover:bg-rose-500/[0.03]"
                          >
                            <span className="shrink-0 text-rose-500/30">
                              d{a.distance}
                            </span>
                            <span className="w-14 shrink-0 truncate text-zinc-500">
                              {a.kind}
                            </span>
                            <span className="truncate text-zinc-400/70">
                              {a.name}
                            </span>
                          </div>
                        ))}
                        {blastRadiusData.affected.length > 20 && (
                          <div className="px-2 py-1 font-mono text-[9px] text-zinc-600">
                            +{blastRadiusData.affected.length - 20} more
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                )}
              </div>
            )}
          </>
        ) : (
          <div className="border-b border-cyan-900/10 p-4">
            <div className="flex h-32 flex-col items-center justify-center text-center">
              <div className="mb-3 flex h-10 w-10 items-center justify-center rounded-lg border border-violet-500/8 bg-violet-500/[0.03]">
                <span className="font-mono text-lg text-violet-500/25">◆</span>
              </div>
              <p className="font-mono text-[11px] text-zinc-600">
                Select a node for analysis
              </p>
            </div>
          </div>
        )}

        {/* Graph Statistics */}
        <div className="border-b border-cyan-900/10 p-4">
          <SectionHeader color="#22d3ee" label="Graph Statistics" />
          <div className="grid grid-cols-2 gap-2">
            <div className="rounded-sm border border-cyan-500/8 bg-cyan-500/[0.03] px-3 py-2">
              <div className="font-mono text-lg font-bold text-cyan-300/80 tabular-nums">
                {nodeCount.toLocaleString()}
              </div>
              <div className="font-mono text-[8px] tracking-[0.2em] text-cyan-500/35 uppercase">
                Nodes
              </div>
            </div>
            <div className="rounded-sm border border-cyan-500/8 bg-cyan-500/[0.03] px-3 py-2">
              <div className="font-mono text-lg font-bold text-cyan-300/80 tabular-nums">
                {edgeCount.toLocaleString()}
              </div>
              <div className="font-mono text-[8px] tracking-[0.2em] text-cyan-500/35 uppercase">
                Edges
              </div>
            </div>
          </div>
        </div>

        {/* Node Type Filters */}
        <CollapsibleSection
          color="#22d3ee"
          label="Node Types"
          defaultOpen={false}
        >
          <div className="space-y-0.5">
            {allNodeTypes.map((type) => (
              <Label
                key={type}
                className="group flex cursor-pointer items-center gap-2 py-0.5 font-mono text-[10px]"
              >
                <Checkbox
                  checked={visibleNodeTypes.has(type)}
                  onCheckedChange={() => onToggleNodeType(type)}
                  className="h-3 w-3 border-zinc-700"
                />
                <span
                  className="h-1.5 w-1.5 shrink-0 rounded-full"
                  style={{
                    backgroundColor: nodeColors[type],
                    boxShadow: `0 0 3px ${nodeColors[type]}50`,
                  }}
                />
                <span
                  className={`capitalize ${visibleNodeTypes.has(type) ? "text-zinc-300/80" : "text-zinc-600"}`}
                >
                  {type}
                </span>
              </Label>
            ))}
          </div>
        </CollapsibleSection>

        {/* Edge Type Filters */}
        <CollapsibleSection
          color="#8b5cf6"
          label="Edge Types"
          defaultOpen={false}
        >
          <div className="space-y-0.5">
            {allEdgeTypes.map((type) => (
              <Label
                key={type}
                className="group flex cursor-pointer items-center gap-2 py-0.5 font-mono text-[10px]"
              >
                <Checkbox
                  checked={visibleEdgeTypes.has(type)}
                  onCheckedChange={() => onToggleEdgeType(type)}
                  className="h-3 w-3 border-zinc-700"
                />
                <span
                  className="h-1.5 w-1.5 shrink-0 rounded-full"
                  style={{
                    backgroundColor: edgeColors[type],
                    boxShadow: `0 0 3px ${edgeColors[type]}50`,
                  }}
                />
                <span
                  className={`capitalize ${visibleEdgeTypes.has(type) ? "text-zinc-300/80" : "text-zinc-600"}`}
                >
                  {type}
                </span>
              </Label>
            ))}
          </div>
        </CollapsibleSection>
      </div>
    </div>
  )
}
