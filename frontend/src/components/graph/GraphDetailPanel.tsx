import { X } from "lucide-react";
import type { UnifiedMemory } from "@/hooks/useApi";
import { clusterColor, typeColor } from "@/lib/graph-colors";

interface GraphDetailPanelProps {
  selectedMemory: UnifiedMemory | null;
  clusterName: string;
  memories: UnifiedMemory[];
  clusterNames: Record<string, string>;
  visibleEdgeCount: number;
  onClose: () => void;
  children?: React.ReactNode;
}

export function GraphDetailPanel({
  selectedMemory,
  clusterName,
  memories,
  clusterNames,
  visibleEdgeCount,
  onClose,
  children,
}: GraphDetailPanelProps) {
  return (
    <>
      <div className="flex items-center justify-between px-4 pt-3 pb-2 border-b border-border">
        <span className="text-sm font-medium">
          {selectedMemory ? "Memory Detail" : "Graph Summary"}
        </span>
        <button
          className="text-muted-foreground hover:text-foreground rounded-sm p-1"
          onClick={onClose}
        >
          <X className="w-4 h-4" />
        </button>
      </div>

      {selectedMemory ? (
        <MemoryDetail
          memory={selectedMemory}
          clusterName={clusterName}
        >
          {children}
        </MemoryDetail>
      ) : (
        <GraphSummary
          memories={memories}
          clusterNames={clusterNames}
          visibleEdgeCount={visibleEdgeCount}
        />
      )}
    </>
  );
}

interface MemoryDetailProps {
  memory: UnifiedMemory;
  clusterName: string;
  children?: React.ReactNode;
}

function MemoryDetail({ memory, clusterName, children }: MemoryDetailProps) {
  return (
    <div className="p-4 space-y-3">
      <p className="text-sm text-foreground leading-relaxed">{memory.content}</p>

      {memory.tags.length > 0 && (
        <div className="flex gap-1 flex-wrap">
          {memory.tags.map((t) => (
            <span
              key={t}
              className="text-xs px-1.5 py-0.5 rounded bg-accent text-primary"
            >
              {t}
            </span>
          ))}
        </div>
      )}

      <div className="text-xs text-muted-foreground space-y-0.5">
        <div>
          Source: <span className="text-foreground">{memory.source}</span>
        </div>
        {memory.memory_type && (
          <div>
            Type: <span className="text-foreground">{memory.memory_type}</span>
          </div>
        )}
        <div>
          Importance:{" "}
          <span className="text-foreground">{memory.importance.toFixed(2)}</span>
        </div>
        {memory.cluster >= 0 && (
          <div className="flex items-center gap-1">
            Cluster:{" "}
            <span className="inline-flex items-center gap-1 text-foreground">
              <span
                className="inline-block w-2 h-2 rounded-full"
                style={{ backgroundColor: clusterColor(memory.cluster) }}
              />
              {clusterName || `Cluster ${memory.cluster}`}
            </span>
          </div>
        )}
      </div>

      {children && (
        <div className="pt-2 border-t border-border">
          <p className="text-xs font-medium text-muted-foreground mb-2 uppercase tracking-wide">
            Entity Context
          </p>
          {children}
          <p className="text-xs text-muted-foreground mt-1">
            Click a neighbor node to navigate.
          </p>
        </div>
      )}
    </div>
  );
}

interface GraphSummaryProps {
  memories: UnifiedMemory[];
  clusterNames: Record<string, string>;
  visibleEdgeCount: number;
}

function GraphSummary({ memories, clusterNames, visibleEdgeCount }: GraphSummaryProps) {
  const clusterCounts = new Map<number, number>();
  const typeCounts = new Map<string, number>();
  const sourceCounts = new Map<string, number>();

  for (const m of memories) {
    if (m.cluster >= 0) {
      clusterCounts.set(m.cluster, (clusterCounts.get(m.cluster) ?? 0) + 1);
    }
    const t = m.memory_type || "(none)";
    typeCounts.set(t, (typeCounts.get(t) ?? 0) + 1);
    sourceCounts.set(m.source, (sourceCounts.get(m.source) ?? 0) + 1);
  }

  const sortedClusters = [...clusterCounts.entries()].sort((a, b) => b[1] - a[1]);
  const sortedTypes = [...typeCounts.entries()].sort((a, b) => b[1] - a[1]);
  const sortedSources = [...sourceCounts.entries()].sort((a, b) => b[1] - a[1]);

  return (
    <div className="p-4 space-y-4">
      <div className="grid grid-cols-2 gap-3">
        <div className="bg-background rounded-lg p-3">
          <p className="text-2xl font-bold">{memories.length}</p>
          <p className="text-xs text-muted-foreground">Memories</p>
        </div>
        <div className="bg-background rounded-lg p-3">
          <p className="text-2xl font-bold">{clusterCounts.size}</p>
          <p className="text-xs text-muted-foreground">Clusters</p>
        </div>
        <div className="bg-background rounded-lg p-3">
          <p className="text-2xl font-bold">{visibleEdgeCount}</p>
          <p className="text-xs text-muted-foreground">Edges</p>
        </div>
        <div className="bg-background rounded-lg p-3">
          <p className="text-2xl font-bold">{typeCounts.size}</p>
          <p className="text-xs text-muted-foreground">Types</p>
        </div>
      </div>

      {sortedClusters.length > 0 && (
        <div>
          <p className="text-xs font-medium text-muted-foreground mb-2 uppercase tracking-wide">
            Clusters
          </p>
          <div className="space-y-1.5">
            {sortedClusters.map(([cid, count]) => (
              <div key={cid} className="flex items-center gap-2 text-sm">
                <span
                  className="w-2.5 h-2.5 rounded-full shrink-0"
                  style={{ backgroundColor: clusterColor(cid) }}
                />
                <span className="flex-1 truncate text-foreground">
                  {clusterNames[String(cid)] || `Cluster ${cid}`}
                </span>
                <span className="text-xs text-muted-foreground">{count}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {sortedTypes.length > 0 && (
        <div>
          <p className="text-xs font-medium text-muted-foreground mb-2 uppercase tracking-wide">
            Types
          </p>
          <div className="space-y-1.5">
            {sortedTypes.map(([type, count]) => (
              <div key={type} className="flex items-center gap-2 text-sm">
                <span
                  className="w-2.5 h-2.5 rounded-full shrink-0"
                  style={{ backgroundColor: typeColor(type === "(none)" ? null : type) }}
                />
                <span className="flex-1 text-foreground">{type}</span>
                <span className="text-xs text-muted-foreground">{count}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {sortedSources.length > 0 && (
        <div>
          <p className="text-xs font-medium text-muted-foreground mb-2 uppercase tracking-wide">
            Sources
          </p>
          <div className="space-y-1.5">
            {sortedSources.map(([src, count]) => (
              <div key={src} className="flex items-center gap-2 text-sm">
                <span className="flex-1 text-foreground">{src}</span>
                <span className="text-xs text-muted-foreground">{count}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
