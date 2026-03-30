import { useFullGraph } from "@/hooks/useApi";
// @ts-ignore
import CytoscapeComponent from "react-cytoscapejs";
import { useRef, useMemo, useCallback, useReducer } from "react";

const TYPE_COLORS: Record<string, string> = {
  person: "#58a6ff",
  service: "#3fb950",
  project: "#d2a8ff",
  technology: "#ffa657",
  concept: "#8b949e",
  organization: "#f778ba",
};

const stylesheet = [
  {
    selector: "node",
    style: {
      label: "data(label)",
      "background-color": "data(color)",
      color: "#c9d1d9",
      "text-valign": "bottom" as const,
      "text-margin-y": 6,
      "font-size": 10,
      width: 28,
      height: 28,
      "border-width": 2,
      "border-color": "#30363d",
    },
  },
  {
    selector: "edge",
    style: {
      width: 1.5,
      "line-color": "#30363d",
      "target-arrow-color": "#30363d",
      "target-arrow-shape": "triangle" as const,
      "curve-style": "bezier" as const,
      label: "data(label)",
      "font-size": 8,
      color: "#484f58",
      "text-rotation": "autorotate" as const,
      "text-margin-y": -8,
    },
  },
  {
    selector: "node:selected",
    style: {
      "border-color": "#58a6ff",
      "border-width": 3,
    },
  },
];

const layout = { name: "cose", animate: true, nodeRepulsion: () => 8000, idealEdgeLength: () => 100 };

// eslint-disable-next-line @typescript-eslint/no-explicit-any
type Selected = { kind: "node" | "edge"; [key: string]: any } | null;

export default function KnowledgeGraph() {
  const { data: graph, isLoading } = useFullGraph();
  const cyRef = useRef<any>(null);
  const listenersAttached = useRef(false);
  const [, forceUpdate] = useReducer((x: number) => x + 1, 0);
  const selectedRef = useRef<Selected>(null);

  const elements = useMemo(() => {
    if (!graph) return [];
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const entities = (graph.entities || []) as any[];
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const relations = (graph.relations || []) as any[];

    const nodes = entities.map((e) => ({
      data: {
        id: e.id || e.name,
        label: e.name,
        type: e.entity_type,
        color: TYPE_COLORS[e.entity_type] || "#8b949e",
      },
    }));

    const nodeIds = new Set(nodes.map((n) => n.data.id));
    const edges = relations
      .filter((r) => r.source && r.target && nodeIds.has(r.source) && nodeIds.has(r.target))
      .map((r, i) => ({
        data: {
          id: `edge-${i}`,
          source: r.source,
          target: r.target,
          label: r.type || "",
          weight: r.weight || 0.5,
        },
      }));

    return [...nodes, ...edges];
  }, [graph]);

  const handleCy = useCallback((cy: any) => {
    cyRef.current = cy;
    if (listenersAttached.current) return;
    listenersAttached.current = true;

    cy.on("tap", "node", (evt: any) => {
      selectedRef.current = { ...evt.target.data(), kind: "node" };
      forceUpdate();
    });
    cy.on("tap", "edge", (evt: any) => {
      selectedRef.current = { ...evt.target.data(), kind: "edge" };
      forceUpdate();
    });
    cy.on("tap", (evt: any) => {
      if (evt.target === cy) {
        selectedRef.current = null;
        forceUpdate();
      }
    });
  }, []);

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const nodeCount = elements.filter((e: any) => !e.data.source).length;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const edgeCount = elements.filter((e: any) => e.data.source).length;
  const selected = selectedRef.current;

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-xl font-semibold">Knowledge Graph</h2>
        {elements.length > 0 && (
          <span className="text-sm text-muted-foreground">
            {nodeCount} entities, {edgeCount} relationships
          </span>
        )}
      </div>
      {isLoading && <p className="text-muted-foreground">Loading graph...</p>}
      {!isLoading && nodeCount === 0 && (
        <p className="text-muted-foreground">
          No entities in the knowledge graph yet. Create memories with the pipeline running to populate it.
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
              <h3 className="font-medium">{selected.label}</h3>
              <p className="text-sm text-muted-foreground">Type: {selected.type}</p>
            </>
          ) : (
            <>
              <h3 className="font-medium">{selected.label || "relationship"}</h3>
              <p className="text-sm text-muted-foreground">
                {selected.source} → {selected.target}
                {selected.weight && <span className="ml-2">weight: {selected.weight}</span>}
              </p>
            </>
          )}
        </div>
      )}
      {nodeCount > 0 && (
        <div className="mt-4 flex gap-3 flex-wrap">
          {Object.entries(TYPE_COLORS).map(([type, color]) => (
            <div key={type} className="flex items-center gap-1.5 text-xs text-muted-foreground">
              <div className="w-3 h-3 rounded-full" style={{ backgroundColor: color }} />
              {type}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
