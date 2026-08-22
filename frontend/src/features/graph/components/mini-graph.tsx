import { Button } from "darkraise-ui/components/button"
import { useMemoryContext } from "@/hooks/api"
import { entityTypeColor } from "@/features/graph/lib/graph-colors"
import { useMemoryGraphTheme } from "@/features/graph/lib/memory-graph-theme"

export interface MiniGraphProps {
  memoryId: string
  onNavigate: (id: string) => void
  onEntitySelect?: (entityId: string) => void
}

export function MiniGraph({
  memoryId,
  onNavigate,
  onEntitySelect,
}: MiniGraphProps) {
  const { data, isLoading } = useMemoryContext(memoryId)
  const { palette } = useMemoryGraphTheme()

  if (isLoading)
    return (
      <p className="text-muted-foreground p-2 text-sm">Loading context…</p>
    )
  if (!data || (data.entities.length === 0 && data.neighbors.length === 0)) {
    return (
      <p className="text-muted-foreground p-2 text-sm">
        No entities extracted yet. Run the pipeline with entity extraction
        enabled to populate this graph.
      </p>
    )
  }

  return (
    <div
      className="border-border space-y-2 rounded border bg-background p-2"
      style={{ minHeight: 80 }}
    >
      {data.entities.length > 0 && (
        <div>
          <p className="text-muted-foreground mb-1 text-sm">Entities</p>
          <div className="flex flex-wrap gap-1">
            {data.entities.map((e) => (
              <Button
                variant="ghost"
                key={e.id}
                className="rounded px-1.5 py-0.5"
                style={{
                  backgroundColor: palette.entityFill,
                  border: `1px solid ${entityTypeColor(e.entity_type, palette)}`,
                  color: entityTypeColor(e.entity_type, palette),
                }}
                onClick={() => onEntitySelect?.(e.id)}
              >
                {e.name}
              </Button>
            ))}
          </div>
        </div>
      )}
      {data.neighbors.length > 0 && (
        <div>
          <p className="text-muted-foreground mb-1 text-sm">Neighbors</p>
          <div className="space-y-0.5">
            {data.neighbors.slice(0, 5).map((n) => (
              <Button
                variant="ghost"
                key={n.id}
                className="text-muted-foreground hover:text-foreground block w-full truncate py-0.5 text-left"
                onClick={() => onNavigate(n.id)}
                title={n.content}
              >
                {n.content.slice(0, 60)}
              </Button>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
