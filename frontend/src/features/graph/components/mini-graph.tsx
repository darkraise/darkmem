import { useMemoryContext } from "@/hooks/api";
import { entityTypeColor } from "@/features/graph/lib/graph-colors";

export interface MiniGraphProps {
  memoryId: string;
  onNavigate: (id: string) => void;
  onEntitySelect?: (entityId: string) => void;
}

export function MiniGraph({ memoryId, onNavigate, onEntitySelect }: MiniGraphProps) {
  const { data, isLoading } = useMemoryContext(memoryId);

  if (isLoading)
    return (
      <p className="text-xs text-muted-foreground p-2">Loading context…</p>
    );
  if (!data || (data.entities.length === 0 && data.neighbors.length === 0)) {
    return (
      <p className="text-xs text-muted-foreground p-2">
        No entities extracted yet. Run the pipeline with entity extraction enabled to populate this graph.
      </p>
    );
  }

  return (
    <div className="bg-[#0d1117] border border-border rounded p-2 space-y-2" style={{ minHeight: 80 }}>
      {data.entities.length > 0 && (
        <div>
          <p className="text-xs text-muted-foreground mb-1">Entities</p>
          <div className="flex flex-wrap gap-1">
            {data.entities.map((e) => (
              <button
                key={e.id}
                className="text-xs px-1.5 py-0.5 rounded"
                style={{ backgroundColor: entityTypeColor(e.entity_type) + "30", color: entityTypeColor(e.entity_type) }}
                onClick={() => onEntitySelect?.(e.id)}
              >
                {e.name}
              </button>
            ))}
          </div>
        </div>
      )}
      {data.neighbors.length > 0 && (
        <div>
          <p className="text-xs text-muted-foreground mb-1">Neighbors</p>
          <div className="space-y-0.5">
            {data.neighbors.slice(0, 5).map((n) => (
              <button
                key={n.id}
                className="w-full text-left text-xs text-muted-foreground hover:text-foreground truncate block py-0.5"
                onClick={() => onNavigate(n.id)}
                title={n.content}
              >
                {n.content.slice(0, 60)}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
