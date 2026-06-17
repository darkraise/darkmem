import { Button } from "darkraise-ui/components/button"
import { Checkbox } from "darkraise-ui/components/checkbox"
import { Label } from "darkraise-ui/components/label"
import { Badge } from "darkraise-ui/components/badge"
import { ScrollArea } from "darkraise-ui/components/scroll-area"
import {
  Collapsible,
  CollapsibleTrigger,
  CollapsibleContent,
} from "darkraise-ui/components/collapsible"
import { Stat, StatLabel, StatValue } from "darkraise-ui/components/stat"
import { Spinner } from "darkraise-ui/components/spinner"
import { EmptyState } from "darkraise-ui/components/empty-state"
import { Boxes, ChevronDown, Crosshair } from "lucide-react"
import type { CodeSymbolDetail, BlastRadiusResult } from "@/hooks/api"
import { ProcessPanel } from "./process-panel"
import type { CodeProcess } from "../lib/code-processes"

export interface CommunityNavigatorItem {
  id: string
  label: string
  size: number
  nodeIds: string[]
  color: string
}

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
  processes: CodeProcess[]
  selectedProcessId: string | null
  onProcessSelect: (process: CodeProcess) => void
  communities: CommunityNavigatorItem[]
  selectedCommunityId: string | null
  onCommunitySelect: (community: CommunityNavigatorItem) => void
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
  return (
    <Collapsible defaultOpen={defaultOpen} className="border-b border-border">
      <CollapsibleTrigger className="group flex w-full cursor-pointer items-center gap-2 px-4 py-3 transition-colors hover:bg-accent">
        <div className="h-1 w-1 shrink-0 rounded-full bg-primary" />
        <span className="flex-1 text-left font-mono text-sm font-semibold tracking-[0.2em] text-muted-foreground uppercase">
          {label}
        </span>
        <ChevronDown
          className="h-4 w-4 shrink-0 text-muted-foreground transition-transform group-data-[state=closed]:-rotate-90"
          aria-hidden
        />
      </CollapsibleTrigger>
      <CollapsibleContent className="px-4 pb-3">{children}</CollapsibleContent>
    </Collapsible>
  )
}

// The backend emits risk as a free-form string (low/medium/high/critical in
// any casing); normalize to a small set so the badge color and label are
// stable regardless of vendor casing.
type RiskLevel = "low" | "medium" | "high" | "critical"

function normalizeRisk(raw: string): RiskLevel {
  const r = raw.trim().toLowerCase()
  if (r === "critical") return "critical"
  if (r === "high") return "high"
  if (r === "medium") return "medium"
  return "low"
}

const RISK_TEXT_CLASS: Record<RiskLevel, string> = {
  low: "text-muted-foreground",
  medium: "text-foreground",
  high: "text-destructive",
  critical: "text-destructive",
}

function BlastDepthHistogram({ byDepth }: { byDepth: BlastRadiusResult["by_depth"] }) {
  const buckets: Array<{ label: string; count: number }> = [
    { label: "d1", count: byDepth["1"]?.length ?? 0 },
    { label: "d2", count: byDepth["2"]?.length ?? 0 },
    { label: "d3+", count: byDepth["3+"]?.length ?? 0 },
  ]
  const max = Math.max(1, ...buckets.map((b) => b.count))

  return (
    <div className="space-y-1">
      <div className="font-mono text-sm tracking-[0.2em] text-muted-foreground uppercase">
        By Depth
      </div>
      <div className="space-y-1">
        {buckets.map((b) => (
          <div key={b.label} className="flex items-center gap-2">
            <span className="w-7 shrink-0 font-mono text-sm text-destructive/70">
              {b.label}
            </span>
            <div className="h-2 flex-1 overflow-hidden rounded-sm bg-muted">
              <div
                className="h-full rounded-sm bg-destructive/70"
                style={{ width: `${(b.count / max) * 100}%` }}
              />
            </div>
            <span className="w-8 shrink-0 text-right font-mono text-sm text-foreground tabular-nums">
              {b.count}
            </span>
          </div>
        ))}
      </div>
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
  processes,
  selectedProcessId,
  onProcessSelect,
  communities,
  selectedCommunityId,
  onCommunitySelect,
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
          <span className="ml-auto min-w-0 flex-1 truncate text-right font-mono text-sm text-muted-foreground">
            {selectedNode.label}
          </span>
        )}
      </div>

      <ScrollArea className="min-h-0 flex-1">
        {selectedNode ? (
          <>
            {/* Symbol Header */}
            <div className="border-b border-border p-4">
              <h3 className="truncate font-mono text-sm font-semibold text-foreground">
                {selectedNode.label}
              </h3>
              <div className="mt-2.5 flex flex-wrap gap-1.5">
                {selectedNode.kind && (
                  <Badge variant="default" size="sm" className="font-mono tracking-wider uppercase">
                    {selectedNode.kind}
                  </Badge>
                )}
                {symbolDetail?.visibility && (
                  <Badge variant="secondary" size="sm" className="font-mono tracking-wider uppercase">
                    {symbolDetail.visibility}
                  </Badge>
                )}
                {symbolDetail?.enrichment_status && (
                  <Badge
                    variant={
                      symbolDetail.enrichment_status === "completed"
                        ? "default"
                        : "secondary"
                    }
                    size="sm"
                    className="font-mono tracking-wider uppercase"
                  >
                    {symbolDetail.enrichment_status}
                  </Badge>
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
                    variant="destructive"
                    size="sm"
                    className="flex-1 font-mono uppercase tracking-wider"
                    onClick={onBlastRadius}
                    disabled={isBlastRadiusLoading}
                  >
                    {isBlastRadiusLoading ? (
                      <>
                        <Spinner size="sm" />
                        Analyzing…
                      </>
                    ) : (
                      "Run Blast Radius"
                    )}
                  </Button>
                  {blastRadiusIds && (
                    <Button
                      variant="outline"
                      size="sm"
                      className="font-mono uppercase tracking-wider"
                      onClick={onClearBlastRadius}
                    >
                      Clear
                    </Button>
                  )}
                </div>

                {blastRadiusData && (
                  <div className="mt-3 space-y-3">
                    <div className="flex items-center gap-3">
                      <Stat>
                        <StatLabel className="font-mono tracking-[0.2em] uppercase">
                          Affected
                        </StatLabel>
                        <StatValue className="font-mono text-destructive">
                          {blastRadiusData.total}
                        </StatValue>
                      </Stat>
                      {(() => {
                        const risk = normalizeRisk(blastRadiusData.risk)
                        return (
                          <Stat>
                            <StatLabel className="font-mono tracking-[0.2em] uppercase">
                              Risk
                            </StatLabel>
                            <StatValue
                              className={`font-mono uppercase ${RISK_TEXT_CLASS[risk]}`}
                            >
                              {risk}
                            </StatValue>
                          </Stat>
                        )
                      })()}
                    </div>

                    {blastRadiusData.by_depth && (
                      <BlastDepthHistogram byDepth={blastRadiusData.by_depth} />
                    )}

                    {blastRadiusData.affected.length > 0 && (
                      <ScrollArea className="mt-2 max-h-40">
                        <div className="space-y-0.5">
                          {blastRadiusData.affected.slice(0, 20).map((a, i) => (
                            <div
                              key={i}
                              className="flex items-center gap-2 rounded-sm px-2 py-1 font-mono text-sm"
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
          <EmptyState
            className="border-b border-border"
            icon={<Crosshair className="h-6 w-6" />}
            title="Select a node for analysis"
          />
        )}

        {/* Graph Statistics */}
        <div className="border-b border-border p-4">
          <SectionHeader label="Graph Statistics" />
          <div className="grid grid-cols-2 gap-2">
            <Stat>
              <StatLabel className="font-mono tracking-[0.2em] uppercase">
                Nodes
              </StatLabel>
              <StatValue className="font-mono">
                {nodeCount.toLocaleString()}
              </StatValue>
            </Stat>
            <Stat>
              <StatLabel className="font-mono tracking-[0.2em] uppercase">
                Edges
              </StatLabel>
              <StatValue className="font-mono">
                {edgeCount.toLocaleString()}
              </StatValue>
            </Stat>
          </div>
        </div>

        {/* Execution Flows */}
        <CollapsibleSection
          label="Execution Flows"
          defaultOpen={processes.length > 0}
        >
          <ProcessPanel
            processes={processes}
            selectedProcessId={selectedProcessId}
            onSelect={onProcessSelect}
          />
        </CollapsibleSection>

        {/* Communities (cluster navigator) — only when Leiden found clusters */}
        {communities.length > 0 && (
          <CollapsibleSection label="Communities" defaultOpen={false}>
            <div className="space-y-1">
              {communities.map((c) => {
                const active = c.id === selectedCommunityId
                return (
                  <Button
                    key={c.id}
                    variant="ghost"
                    onClick={() => onCommunitySelect(c)}
                    className={`flex h-auto w-full items-center gap-2 rounded-sm px-2 py-1.5 text-left transition-colors ${
                      active
                        ? "bg-primary/15 text-primary"
                        : "text-foreground hover:bg-accent"
                    }`}
                  >
                    <Boxes
                      className={`h-3.5 w-3.5 shrink-0 ${active ? "text-primary" : "text-muted-foreground"}`}
                    />
                    <span
                      className="h-2 w-2 shrink-0 rounded-full"
                      style={{ backgroundColor: c.color }}
                    />
                    <span className="min-w-0 flex-1 truncate font-mono text-sm font-medium">
                      {c.label}
                    </span>
                    <Badge variant="secondary" size="sm" className="shrink-0">
                      {c.size}
                    </Badge>
                  </Button>
                )
              })}
            </div>
          </CollapsibleSection>
        )}

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
