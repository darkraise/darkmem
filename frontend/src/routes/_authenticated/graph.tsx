import { createFileRoute } from "@tanstack/react-router";
import { useFullGraph } from "@/hooks/api";
import { KnowledgeGraphRenderer, type KGSelection } from "@/features/graph/components/knowledge-graph-renderer";
import { ENTITY_TYPE_COLORS } from "@/features/graph/lib/graph-colors";
import { useState, useMemo } from "react";

export const Route = createFileRoute("/_authenticated/graph")({
  component: KnowledgeGraphPage,
});

function KnowledgeGraphPage() {
  const { data: graph, isLoading } = useFullGraph();
  const [selected, setSelected] = useState<KGSelection | null>(null);

  const entities = useMemo(() => (graph?.entities || []) as Array<{ id?: string; name: string; entity_type: string }>, [graph]);
  const relations = useMemo(() => (graph?.relations || []) as Array<{ source: string; target: string; type?: string; weight?: number }>, [graph]);

  const nodeCount = entities.length;
  const edgeCount = relations.length;

  return (
    <div className="p-6">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-xl font-semibold">Knowledge Graph</h2>
        {nodeCount > 0 && (
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
        <div className="relative bg-card border border-border rounded-lg overflow-hidden" style={{ height: "70vh" }}>
          <KnowledgeGraphRenderer
            entities={entities}
            relations={relations}
            selectedId={selected?.kind === "node" ? selected.id : null}
            onSelect={setSelected}
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
          {Object.entries(ENTITY_TYPE_COLORS).map(([type, color]) => (
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
