import { useGraphEntities } from "@/hooks/useApi";
// @ts-ignore
import CytoscapeComponent from "react-cytoscapejs";
import { useState, useMemo } from "react";

export default function KnowledgeGraph() {
  const { data: entities, isLoading } = useGraphEntities();
  const [selected, setSelected] = useState<{ label: string; type: string } | null>(null);

  const elements = useMemo(() => {
    if (!entities || !Array.isArray(entities)) return [];
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const nodes = (entities as any[]).map((e: any) => ({
      data: { id: e.id || e.name, label: e.name, type: e.entity_type },
    }));
    return nodes;
  }, [entities]);

  const stylesheet = [
    {
      selector: "node",
      style: {
        label: "data(label)",
        "background-color": "#21262d",
        color: "#c9d1d9",
        "text-valign": "bottom" as const,
        "text-margin-y": 5,
        "font-size": 10,
        width: 30,
        height: 30,
        "border-width": 2,
        "border-color": "#58a6ff",
      },
    },
    {
      selector: "edge",
      style: {
        width: 1,
        "line-color": "#30363d",
        "curve-style": "bezier" as const,
      },
    },
  ];

  return (
    <div>
      <h2 className="text-xl font-semibold mb-4">Knowledge Graph</h2>
      {isLoading && <p className="text-muted-foreground">Loading graph...</p>}
      {!isLoading && elements.length === 0 && (
        <p className="text-muted-foreground">No entities in the knowledge graph yet. Create memories with the pipeline running to populate it.</p>
      )}
      {elements.length > 0 && (
        <div className="bg-card border border-border rounded-lg overflow-hidden" style={{ height: "70vh" }}>
          <CytoscapeComponent
            elements={elements}
            stylesheet={stylesheet}
            layout={{ name: "cose", animate: true }}
            style={{ width: "100%", height: "100%" }}
            cy={(cy: any) => {
              cy.on("tap", "node", (evt: any) => {
                const data = evt.target.data();
                setSelected(data);
              });
            }}
          />
        </div>
      )}
      {selected && (
        <div className="mt-4 bg-card border border-border rounded-lg p-4">
          <h3 className="font-medium">{selected.label}</h3>
          <p className="text-sm text-muted-foreground">{selected.type}</p>
        </div>
      )}
    </div>
  );
}
