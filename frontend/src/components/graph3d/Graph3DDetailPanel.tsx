import { X } from "lucide-react";
import { Button } from "@/components/ui/button";
import type { Node3D, GraphData3D } from "@/lib/graph-utils";
import { clusterColor, typeColor } from "@/lib/graph-utils";

interface Graph3DDetailPanelProps {
  selectedNode: Node3D | null;
  graphData: GraphData3D;
  onClose: () => void;
}

export function Graph3DDetailPanel({
  selectedNode,
  graphData,
  onClose,
}: Graph3DDetailPanelProps) {
  if (!selectedNode) {
    return <GraphSummary graphData={graphData} />;
  }

  return (
    <div className="flex flex-col gap-4 p-4">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-foreground">Memory Detail</h3>
        <Button variant="ghost" size="icon" onClick={onClose} className="h-6 w-6">
          <X className="h-4 w-4" />
        </Button>
      </div>

      <p className="text-sm text-muted-foreground leading-relaxed">
        {selectedNode.content}
      </p>

      {selectedNode.tags.length > 0 && (
        <div className="flex flex-wrap gap-1.5">
          {selectedNode.tags.map((tag) => (
            <span
              key={tag}
              className="rounded-md bg-accent px-2 py-0.5 text-xs text-foreground"
            >
              {tag}
            </span>
          ))}
        </div>
      )}

      <div className="grid grid-cols-2 gap-3 text-xs">
        <div>
          <span className="text-muted-foreground">Source</span>
          <p className="text-foreground font-medium">{selectedNode.source}</p>
        </div>
        {selectedNode.memoryType && (
          <div>
            <span className="text-muted-foreground">Type</span>
            <p className="text-foreground font-medium">{selectedNode.memoryType}</p>
          </div>
        )}
        <div>
          <span className="text-muted-foreground">Importance</span>
          <p className="text-foreground font-medium">
            {selectedNode.importance.toFixed(2)}
          </p>
        </div>
        {selectedNode.cluster >= 0 && (
          <div>
            <span className="text-muted-foreground">Cluster</span>
            <div className="flex items-center gap-1.5">
              <span
                className="inline-block h-2.5 w-2.5 rounded-full"
                style={{ backgroundColor: selectedNode.color }}
              />
              <span className="text-foreground font-medium">
                {selectedNode.clusterName || `#${selectedNode.cluster}`}
              </span>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function GraphSummary({ graphData }: { graphData: GraphData3D }) {
  const clusterCounts = new Map<number, number>();
  const typeCounts = new Map<string, number>();
  const sourceCounts = new Map<string, number>();
  const visibleEdges = graphData.links.filter((l) => !l.hidden);

  for (const node of graphData.nodes) {
    if (node.cluster >= 0) {
      clusterCounts.set(node.cluster, (clusterCounts.get(node.cluster) ?? 0) + 1);
    }
    const t = node.memoryType || "(none)";
    typeCounts.set(t, (typeCounts.get(t) ?? 0) + 1);
    sourceCounts.set(node.source, (sourceCounts.get(node.source) ?? 0) + 1);
  }

  const sortedClusters = [...clusterCounts.entries()].sort((a, b) => b[1] - a[1]);
  const sortedTypes = [...typeCounts.entries()].sort((a, b) => b[1] - a[1]);
  const sortedSources = [...sourceCounts.entries()].sort((a, b) => b[1] - a[1]);

  return (
    <div className="flex flex-col gap-4 p-4">
      <h3 className="text-sm font-semibold text-foreground">Graph Summary</h3>

      <div className="grid grid-cols-2 gap-3">
        <div className="rounded-lg bg-background p-3">
          <p className="text-2xl font-bold text-foreground">{graphData.nodes.length}</p>
          <p className="text-xs text-muted-foreground">Memories</p>
        </div>
        <div className="rounded-lg bg-background p-3">
          <p className="text-2xl font-bold text-foreground">{clusterCounts.size}</p>
          <p className="text-xs text-muted-foreground">Clusters</p>
        </div>
        <div className="rounded-lg bg-background p-3">
          <p className="text-2xl font-bold text-foreground">{visibleEdges.length}</p>
          <p className="text-xs text-muted-foreground">Edges</p>
        </div>
        <div className="rounded-lg bg-background p-3">
          <p className="text-2xl font-bold text-foreground">{typeCounts.size}</p>
          <p className="text-xs text-muted-foreground">Types</p>
        </div>
      </div>

      {sortedClusters.length > 0 && (
        <div>
          <p className="text-xs font-medium text-muted-foreground mb-2 uppercase tracking-wide">
            Clusters
          </p>
          <div className="space-y-1.5">
            {sortedClusters.map(([id, count]) => {
              const node = graphData.nodes.find((n) => n.cluster === id);
              return (
                <div key={id} className="flex items-center gap-2 text-sm">
                  <span
                    className="w-2.5 h-2.5 rounded-full shrink-0"
                    style={{ backgroundColor: clusterColor(id) }}
                  />
                  <span className="flex-1 truncate text-foreground">
                    {node?.clusterName || `Cluster ${id}`}
                  </span>
                  <span className="text-xs text-muted-foreground">{count}</span>
                </div>
              );
            })}
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
