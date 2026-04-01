import { X } from "lucide-react";
import { Button } from "@/components/ui/button";
import type { Node3D, GraphData3D } from "@/lib/graph-utils";
import { clusterColor } from "@/lib/graph-utils";

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
  for (const node of graphData.nodes) {
    if (node.cluster >= 0) {
      clusterCounts.set(node.cluster, (clusterCounts.get(node.cluster) ?? 0) + 1);
    }
  }

  return (
    <div className="flex flex-col gap-4 p-4">
      <h3 className="text-sm font-semibold text-foreground">Graph Summary</h3>
      <div className="grid grid-cols-2 gap-3 text-xs">
        <div className="rounded-md bg-accent p-2">
          <span className="text-muted-foreground">Nodes</span>
          <p className="text-lg font-bold text-foreground">{graphData.nodes.length}</p>
        </div>
        <div className="rounded-md bg-accent p-2">
          <span className="text-muted-foreground">Edges</span>
          <p className="text-lg font-bold text-foreground">{graphData.links.length}</p>
        </div>
        <div className="rounded-md bg-accent p-2">
          <span className="text-muted-foreground">Clusters</span>
          <p className="text-lg font-bold text-foreground">{clusterCounts.size}</p>
        </div>
      </div>

      {clusterCounts.size > 0 && (
        <div className="flex flex-col gap-1.5">
          <span className="text-xs text-muted-foreground">Clusters</span>
          {[...clusterCounts.entries()]
            .sort((a, b) => b[1] - a[1])
            .map(([id, count]) => {
              const node = graphData.nodes.find((n) => n.cluster === id);
              return (
                <div key={id} className="flex items-center gap-2 text-xs">
                  <span
                    className="inline-block h-2.5 w-2.5 rounded-full"
                    style={{ backgroundColor: clusterColor(id) }}
                  />
                  <span className="text-foreground">
                    {node?.clusterName || `Cluster ${id}`}
                  </span>
                  <span className="text-muted-foreground ml-auto">{count}</span>
                </div>
              );
            })}
        </div>
      )}
    </div>
  );
}
