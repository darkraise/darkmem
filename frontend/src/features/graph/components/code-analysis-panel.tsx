import { useState } from "react";
import { Checkbox } from "darkraise-ui/components/checkbox";
import { Label } from "darkraise-ui/components/label";
import type { CodeSymbolDetail, BlastRadiusResult } from "@/hooks/api";

interface CodeAnalysisPanelProps {
  selectedNode: {
    id: string;
    label: string;
    kind?: string;
    file_path?: string;
  } | null;
  symbolDetail: CodeSymbolDetail | null | undefined;
  blastRadiusIds: Set<string> | undefined;
  blastRadiusData: BlastRadiusResult | null;
  onBlastRadius: () => void;
  onClearBlastRadius: () => void;
  isBlastRadiusLoading: boolean;
  nodeCount: number;
  edgeCount: number;
  visibleNodeTypes: Set<string>;
  visibleEdgeTypes: Set<string>;
  onToggleNodeType: (type: string) => void;
  onToggleEdgeType: (type: string) => void;
  nodeColors: Record<string, string>;
  edgeColors: Record<string, string>;
  allNodeTypes: string[];
  allEdgeTypes: string[];
}

function SectionHeader({
  color,
  label,
}: {
  color: string;
  label: string;
}) {
  return (
    <div className="flex items-center gap-2 mb-3">
      <div
        className="w-1 h-1 rounded-full"
        style={{
          backgroundColor: color,
          boxShadow: `0 0 4px ${color}80`,
        }}
      />
      <span className="text-[9px] uppercase tracking-[0.2em] text-zinc-500 font-mono font-semibold">
        {label}
      </span>
    </div>
  );
}

function CollapsibleSection({
  color,
  label,
  defaultOpen = true,
  children,
}: {
  color: string;
  label: string;
  defaultOpen?: boolean;
  children: React.ReactNode;
}) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <div className="border-b border-cyan-900/10">
      <button
        className="w-full flex items-center gap-2 px-4 py-3 hover:bg-white/[0.01] transition-colors"
        onClick={() => setOpen(!open)}
      >
        <div
          className="w-1 h-1 rounded-full shrink-0"
          style={{
            backgroundColor: color,
            boxShadow: `0 0 4px ${color}80`,
          }}
        />
        <span className="text-[9px] uppercase tracking-[0.2em] text-zinc-500 font-mono font-semibold flex-1 text-left">
          {label}
        </span>
        <span className="text-[9px] text-zinc-700 font-mono">
          {open ? "▾" : "▸"}
        </span>
      </button>
      {open && <div className="px-4 pb-3">{children}</div>}
    </div>
  );
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
    selectedNode.kind !== "module";

  return (
    <div className="code-analysis-panel flex flex-col h-full border-l border-cyan-900/15">
      <div className="flex items-center gap-2 px-4 py-2.5 border-b border-cyan-900/15 shrink-0">
        <div className="w-1.5 h-1.5 rounded-full bg-violet-400 shadow-[0_0_6px_rgba(139,92,246,0.5)]" />
        <span className="text-[10px] font-semibold tracking-[0.2em] uppercase text-violet-300/70 font-mono">
          Analysis
        </span>
        {selectedNode && (
          <span className="ml-auto text-[9px] text-zinc-600 font-mono truncate max-w-[120px]">
            {selectedNode.label}
          </span>
        )}
      </div>

      <div className="flex-1 overflow-y-auto scrollbar-thin min-h-0">
        {selectedNode ? (
          <>
            {/* Symbol Header */}
            <div className="p-4 border-b border-cyan-900/10">
              <h3 className="text-sm font-semibold text-cyan-100/90 font-mono truncate">
                {selectedNode.label}
              </h3>
              <div className="flex gap-1.5 mt-2.5 flex-wrap">
                {selectedNode.kind && (
                  <span className="px-2 py-0.5 text-[9px] font-mono uppercase tracking-wider rounded-sm border border-cyan-500/15 text-cyan-400/70 bg-cyan-500/5">
                    {selectedNode.kind}
                  </span>
                )}
                {symbolDetail?.visibility && (
                  <span className="px-2 py-0.5 text-[9px] font-mono uppercase tracking-wider rounded-sm border border-violet-500/15 text-violet-400/70 bg-violet-500/5">
                    {symbolDetail.visibility}
                  </span>
                )}
                {symbolDetail?.enrichment_status && (
                  <span
                    className={`px-2 py-0.5 text-[9px] font-mono uppercase tracking-wider rounded-sm border ${
                      symbolDetail.enrichment_status === "completed"
                        ? "border-emerald-500/15 text-emerald-400/70 bg-emerald-500/5"
                        : "border-amber-500/15 text-amber-400/70 bg-amber-500/5"
                    }`}
                  >
                    {symbolDetail.enrichment_status}
                  </span>
                )}
              </div>

              {symbolDetail?.file_path && (
                <div className="mt-3 flex items-center gap-2">
                  <span className="text-[8px] uppercase tracking-[0.2em] text-zinc-600 font-mono shrink-0">
                    Path
                  </span>
                  <span className="text-[10px] text-zinc-400/80 font-mono truncate">
                    {symbolDetail.file_path}
                    {symbolDetail.line_start > 0 &&
                      `:${symbolDetail.line_start}–${symbolDetail.line_end}`}
                  </span>
                </div>
              )}
            </div>

            {/* AI Summary */}
            {symbolDetail?.summary && (
              <div className="p-4 border-b border-cyan-900/10">
                <SectionHeader color="#22d3ee" label="AI Summary" />
                <p className="text-[11px] text-zinc-300/70 leading-[1.7] font-mono">
                  {symbolDetail.summary}
                </p>
              </div>
            )}

            {/* Blast Radius */}
            {isAnalyzableSymbol && (
              <div className="p-4 border-b border-cyan-900/10">
                <SectionHeader color="#f43f5e" label="Impact Analysis" />
                <div className="flex gap-2">
                  <button
                    className="flex-1 px-3 py-1.5 text-[10px] font-mono uppercase tracking-wider rounded-sm border border-rose-500/15 text-rose-400/70 bg-rose-500/[0.03] hover:bg-rose-500/8 hover:border-rose-500/25 transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
                    onClick={onBlastRadius}
                    disabled={isBlastRadiusLoading}
                  >
                    {isBlastRadiusLoading
                      ? "Analyzing…"
                      : "Run Blast Radius"}
                  </button>
                  {blastRadiusIds && (
                    <button
                      className="px-3 py-1.5 text-[10px] font-mono uppercase tracking-wider rounded-sm border border-zinc-700/50 text-zinc-500 hover:bg-zinc-800/50 transition-colors"
                      onClick={onClearBlastRadius}
                    >
                      Clear
                    </button>
                  )}
                </div>

                {blastRadiusData && (
                  <div className="mt-3 space-y-2">
                    <div className="flex items-center gap-3">
                      <div className="px-2.5 py-1.5 rounded-sm bg-rose-500/5 border border-rose-500/10">
                        <div className="text-base font-bold text-rose-300/80 font-mono">
                          {blastRadiusData.total}
                        </div>
                        <div className="text-[8px] uppercase tracking-[0.2em] text-rose-500/40 font-mono">
                          Affected
                        </div>
                      </div>
                      <div
                        className={`px-2.5 py-1.5 rounded-sm border ${
                          blastRadiusData.risk === "high"
                            ? "bg-rose-500/5 border-rose-500/10"
                            : blastRadiusData.risk === "medium"
                              ? "bg-amber-500/5 border-amber-500/10"
                              : "bg-emerald-500/5 border-emerald-500/10"
                        }`}
                      >
                        <div
                          className={`text-base font-bold font-mono ${
                            blastRadiusData.risk === "high"
                              ? "text-rose-300/80"
                              : blastRadiusData.risk === "medium"
                                ? "text-amber-300/80"
                                : "text-emerald-300/80"
                          }`}
                        >
                          {blastRadiusData.risk}
                        </div>
                        <div className="text-[8px] uppercase tracking-[0.2em] text-zinc-500 font-mono">
                          Risk
                        </div>
                      </div>
                    </div>

                    {blastRadiusData.affected.length > 0 && (
                      <div className="mt-2 space-y-0.5 max-h-40 overflow-y-auto scrollbar-thin">
                        {blastRadiusData.affected.slice(0, 20).map((a, i) => (
                          <div
                            key={i}
                            className="flex items-center gap-2 px-2 py-1 rounded-sm text-[10px] font-mono hover:bg-rose-500/[0.03] transition-colors"
                          >
                            <span className="text-rose-500/30 shrink-0">
                              d{a.distance}
                            </span>
                            <span className="text-zinc-500 shrink-0 w-14 truncate">
                              {a.kind}
                            </span>
                            <span className="text-zinc-400/70 truncate">
                              {a.name}
                            </span>
                          </div>
                        ))}
                        {blastRadiusData.affected.length > 20 && (
                          <div className="text-[9px] text-zinc-600 font-mono px-2 py-1">
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
          <div className="p-4 border-b border-cyan-900/10">
            <div className="flex flex-col items-center justify-center h-32 text-center">
              <div className="w-10 h-10 rounded-lg border border-violet-500/8 bg-violet-500/[0.03] flex items-center justify-center mb-3">
                <span className="text-violet-500/25 text-lg font-mono">
                  ◆
                </span>
              </div>
              <p className="text-[11px] text-zinc-600 font-mono">
                Select a node for analysis
              </p>
            </div>
          </div>
        )}

        {/* Graph Statistics */}
        <div className="p-4 border-b border-cyan-900/10">
          <SectionHeader color="#22d3ee" label="Graph Statistics" />
          <div className="grid grid-cols-2 gap-2">
            <div className="px-3 py-2 rounded-sm bg-cyan-500/[0.03] border border-cyan-500/8">
              <div className="text-lg font-bold text-cyan-300/80 font-mono tabular-nums">
                {nodeCount.toLocaleString()}
              </div>
              <div className="text-[8px] uppercase tracking-[0.2em] text-cyan-500/35 font-mono">
                Nodes
              </div>
            </div>
            <div className="px-3 py-2 rounded-sm bg-cyan-500/[0.03] border border-cyan-500/8">
              <div className="text-lg font-bold text-cyan-300/80 font-mono tabular-nums">
                {edgeCount.toLocaleString()}
              </div>
              <div className="text-[8px] uppercase tracking-[0.2em] text-cyan-500/35 font-mono">
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
                className="flex items-center gap-2 text-[10px] cursor-pointer font-mono py-0.5 group"
              >
                <Checkbox
                  checked={visibleNodeTypes.has(type)}
                  onCheckedChange={() => onToggleNodeType(type)}
                  className="h-3 w-3 border-zinc-700"
                />
                <span
                  className="w-1.5 h-1.5 rounded-full shrink-0"
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
                className="flex items-center gap-2 text-[10px] cursor-pointer font-mono py-0.5 group"
              >
                <Checkbox
                  checked={visibleEdgeTypes.has(type)}
                  onCheckedChange={() => onToggleEdgeType(type)}
                  className="h-3 w-3 border-zinc-700"
                />
                <span
                  className="w-1.5 h-1.5 rounded-full shrink-0"
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
  );
}
