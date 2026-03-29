import { useMemoryGraph } from "@/hooks/useApi";
// eslint-disable-next-line @typescript-eslint/no-var-requires, @typescript-eslint/no-explicit-any
import CytoscapeComp from "react-cytoscapejs";
const CytoscapeComponent = CytoscapeComp as any;
import { useRef, useMemo, useCallback, useReducer, useState } from "react";

const SOURCE_COLORS: Record<string, string> = {
  "claude-code": "#58a6ff",
  "mcp-test": "#3fb950",
  api: "#d2a8ff",
  "rest-test": "#ffa657",
  dashboard: "#f778ba",
};

const TAG_COLORS = [
  "#a855f7", "#c084fc", "#d8b4fe", "#9333ea",
  "#7c3aed", "#8b5cf6", "#a78bfa", "#c4b5fd",
];

function getNodeColor(tags: string[], source: string): string {
  if (tags.length > 0) {
    const primary = tags[0];
    let hash = 0;
    for (let i = 0; i < primary.length; i++) hash = ((hash << 5) - hash + primary.charCodeAt(i)) | 0;
    return TAG_COLORS[Math.abs(hash) % TAG_COLORS.length];
  }
  return SOURCE_COLORS[source] || "#8b949e";
}

export default function KnowledgeGraph() {
  const [threshold, setThreshold] = useState(0.3);
  const { data: graph, isLoading } = useMemoryGraph(threshold);
  const cyRef = useRef<any>(null);
  const listenersAttached = useRef(false);
  const [, forceUpdate] = useReducer((x: number) => x + 1, 0);
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const selectedRef = useRef<any>(null);

  const elements = useMemo(() => {
    if (!graph) return [];

    const edgeCounts: Record<string, number> = {};
    for (const e of graph.edges) {
      edgeCounts[e.source] = (edgeCounts[e.source] || 0) + 1;
      edgeCounts[e.target] = (edgeCounts[e.target] || 0) + 1;
    }

    const nodes = graph.nodes.map((n) => {
      const connections = edgeCounts[n.id] || 0;
      const size = Math.max(20, Math.min(50, 20 + Math.log2(connections + 1) * 10));
      return {
        data: {
          id: n.id,
          label: n.content.length > 40 ? n.content.slice(0, 40) + "..." : n.content,
          fullContent: n.content,
          source: n.source,
          tags: n.tags,
          memory_type: n.memory_type,
          color: getNodeColor(n.tags, n.source),
          size,
        },
      };
    });

    const edges = graph.edges.map((e, i) => ({
      data: {
        id: `e-${i}`,
        source: e.source,
        target: e.target,
        score: e.score,
        width: Math.max(0.5, (e.score - threshold) / (1 - threshold) * 3),
        opacity: Math.max(0.2, e.score),
      },
    }));

    return [...nodes, ...edges];
  }, [graph, threshold]);

  const handleCy = useCallback((cy: any) => {
    cyRef.current = cy;
    if (listenersAttached.current) return;
    listenersAttached.current = true;

    cy.on("tap", "node", (evt: any) => {
      const data = evt.target.data();
      selectedRef.current = { ...data, kind: "node" };
      forceUpdate();
    });
    cy.on("tap", "edge", (evt: any) => {
      const data = evt.target.data();
      const sourceNode = cy.getElementById(data.source).data();
      const targetNode = cy.getElementById(data.target).data();
      selectedRef.current = {
        ...data,
        kind: "edge",
        sourceContent: sourceNode?.fullContent,
        targetContent: targetNode?.fullContent,
      };
      forceUpdate();
    });
    cy.on("tap", (evt: any) => {
      if (evt.target === cy) {
        selectedRef.current = null;
        forceUpdate();
      }
    });
  }, []);

  const stylesheet = useMemo(() => [
    {
      selector: "node",
      style: {
        label: "data(label)",
        "background-color": "data(color)",
        color: "#c9d1d9",
        "text-valign": "bottom" as const,
        "text-halign": "center" as const,
        "text-margin-y": 6,
        "font-size": 8,
        width: "data(size)",
        height: "data(size)",
        "border-width": 1,
        "border-color": "#30363d",
        "text-max-width": 100,
        "text-wrap": "ellipsis" as const,
      },
    },
    {
      selector: "edge",
      style: {
        width: "data(width)",
        "line-color": "#30363d",
        "line-opacity": "data(opacity)",
        "curve-style": "bezier" as const,
      },
    },
    {
      selector: "node:selected",
      style: {
        "border-color": "#58a6ff",
        "border-width": 3,
      },
    },
  ], []);

  const layout = useMemo(() => ({
    name: "cose",
    animate: true,
    animationDuration: 1000,
    nodeRepulsion: () => 12000,
    idealEdgeLength: () => 120,
    gravity: 0.3,
    numIter: 500,
  }), []);

  const nodeCount = graph?.nodes.length || 0;
  const edgeCount = graph?.edges.length || 0;
  const selected = selectedRef.current;

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-xl font-semibold">Knowledge Graph</h2>
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <label>Similarity</label>
            <input
              type="range" min="0.1" max="0.9" step="0.05"
              value={threshold}
              onChange={(e) => { setThreshold(parseFloat(e.target.value)); listenersAttached.current = false; }}
              className="w-24"
            />
            <span className="font-mono text-xs w-8">{threshold}</span>
          </div>
          {nodeCount > 0 && (
            <span className="text-sm text-muted-foreground">
              {nodeCount} memories, {edgeCount} connections
            </span>
          )}
        </div>
      </div>
      {isLoading && <p className="text-muted-foreground">Loading graph...</p>}
      {!isLoading && nodeCount === 0 && (
        <p className="text-muted-foreground">
          No vectors yet. Create memories with the pipeline running to generate embeddings.
        </p>
      )}
      {nodeCount > 0 && (
        <div className="bg-card border border-border rounded-lg overflow-hidden" style={{ height: "70vh" }}>
          <CytoscapeComponent
            elements={elements}
            stylesheet={stylesheet}
            layout={layout}
            style={{ width: "100%", height: "100%" }}
            cy={handleCy}
          />
        </div>
      )}
      {selected && (
        <div className="mt-4 bg-card border border-border rounded-lg p-4">
          {selected.kind === "node" ? (
            <>
              <p className="text-sm text-foreground">{selected.fullContent}</p>
              <div className="flex gap-1 mt-2 flex-wrap">
                {selected.tags?.map((t: string) => (
                  <span key={t} className="text-xs px-1.5 py-0.5 rounded bg-accent text-primary">{t}</span>
                ))}
              </div>
              <p className="text-xs text-muted-foreground mt-2">
                {selected.source} {selected.memory_type && `| ${selected.memory_type}`}
              </p>
            </>
          ) : (
            <div>
              <p className="text-xs text-muted-foreground mb-2">Similarity: {(selected.score * 100).toFixed(0)}%</p>
              <div className="grid grid-cols-2 gap-4">
                <div className="text-sm text-foreground bg-background rounded p-2">{selected.sourceContent}</div>
                <div className="text-sm text-foreground bg-background rounded p-2">{selected.targetContent}</div>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
