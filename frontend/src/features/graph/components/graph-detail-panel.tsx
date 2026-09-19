import { X } from "lucide-react"
import { Button } from "darkraise-ui/components/button"
import { cn } from "darkraise-ui/lib"
import type {
  UnifiedMemory,
  GraphEntity,
  EntityRelation,
  SimilarityEdge,
} from "@/hooks/api"
import { resolveNodeColor, entityTypeColor, clusterColor } from "@/features/graph/lib/graph-colors"
import { GraphSummary } from "./graph-summary"
import type { ColorMode } from "@/features/graph/lib/graph-colors"
import { useMemoryGraphTheme } from "@/features/graph/lib/memory-graph-theme"

interface GraphDetailPanelProps {
  selectedMemory: UnifiedMemory | null
  clusterName: string
  memories: UnifiedMemory[]
  clusterNames: Record<string, string>
  /** Edges between visible memories. The summary derives degree and isolation
   *  from the endpoints, which a bare count cannot carry. */
  visibleEdges: SimilarityEdge[]
  onClose: () => void
  children?: React.ReactNode
  selectedEntity?: GraphEntity | null
  entityRelations?: EntityRelation[]
  /** Every entity in the payload — the lookup table `EntityDetail` resolves
   *  relation endpoints against, which the visible set cannot serve. */
  allEntities?: GraphEntity[]
  /** The entities actually on the canvas; what the summary counts. */
  visibleEntities?: GraphEntity[]
  onNavigateToMemory?: (memoryId: string) => void
  colorMode: ColorMode
}

export function GraphDetailPanel({
  selectedMemory,
  clusterName,
  memories,
  clusterNames,
  visibleEdges,
  onClose,
  children,
  selectedEntity,
  entityRelations,
  allEntities,
  visibleEntities,
  onNavigateToMemory,
  colorMode,
}: GraphDetailPanelProps) {
  const panelTitle = selectedEntity
    ? "Entity Detail"
    : selectedMemory
      ? "Memory Detail"
      : "Graph Summary"

  return (
    <>
      <div className="border-border flex shrink-0 items-center justify-between border-b px-4 pt-3 pb-2">
        <span className="text-sm font-medium">{panelTitle}</span>
        <Button
          variant="ghost"
          size="icon"
          className="text-muted-foreground hover:text-foreground rounded-sm p-1"
          onClick={onClose}
        >
          <X className="h-4 w-4" />
        </Button>
      </div>

      <div className="min-h-0 flex-1 overflow-auto">
        {selectedEntity ? (
          <EntityDetail
            entity={selectedEntity}
            memories={memories}
            entityRelations={entityRelations}
            allEntities={allEntities}
            onNavigateToMemory={onNavigateToMemory}
          />
        ) : selectedMemory ? (
          <MemoryDetail
            memory={selectedMemory}
            clusterName={clusterName}
            colorMode={colorMode}
            similarNeighbors={similarNeighbors(
              selectedMemory.id,
              visibleEdges,
              memories,
            )}
            onNavigateToMemory={onNavigateToMemory}
          >
            {children}
          </MemoryDetail>
        ) : (
          <GraphSummary
            memories={memories}
            edges={visibleEdges}
            entities={visibleEntities ?? []}
            entityRelations={entityRelations ?? []}
            clusterNames={clusterNames}
            colorMode={colorMode}
          />
        )}
      </div>
    </>
  )
}

interface EntityDetailProps {
  entity: GraphEntity
  memories: UnifiedMemory[]
  entityRelations?: EntityRelation[]
  allEntities?: GraphEntity[]
  onNavigateToMemory?: (memoryId: string) => void
}

function EntityDetail({
  entity,
  memories,
  entityRelations,
  allEntities,
  onNavigateToMemory,
}: EntityDetailProps) {
  const { palette } = useMemoryGraphTheme()
  const color = entityTypeColor(entity.entity_type, palette)
  const related =
    entityRelations?.filter(
      (r) => r.source === entity.id || r.target === entity.id,
    ) ?? []

  return (
    <div className="space-y-4 p-4">
      <div>
        <h3 className="text-foreground text-sm font-semibold">
          {entity.name}
        </h3>
        <span
          className="mt-1 inline-block rounded-full px-2 py-0.5 text-sm capitalize"
          style={{ backgroundColor: color + "20", color }}
        >
          {entity.entity_type}
        </span>
      </div>

      {Object.keys(entity.properties).length > 0 && (
        <div>
          <p className="text-muted-foreground mb-1 text-sm font-semibold tracking-wider uppercase">
            Properties
          </p>
          <div className="space-y-1">
            {Object.entries(entity.properties).map(([key, value]) => (
              <div key={key} className="flex gap-2 text-sm">
                <span className="text-muted-foreground">{key}:</span>
                <span className="text-foreground">{String(value)}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      <div>
        <p className="text-muted-foreground mb-1 text-sm font-semibold tracking-wider uppercase">
          Linked Memories ({entity.memory_ids.length})
        </p>
        <div className="space-y-1">
          {entity.memory_ids.slice(0, 20).map((mid) => {
            const mem = memories.find((m) => m.id === mid)
            return (
              <Button
                key={mid}
                variant="ghost"
                className="text-muted-foreground hover:text-foreground block w-full truncate py-0.5 text-left"
                onClick={() => onNavigateToMemory?.(mid)}
                title={mem?.content}
              >
                {mem ? mem.content.slice(0, 80) : mid.slice(0, 8) + "…"}
              </Button>
            )
          })}
        </div>
      </div>

      {related.length > 0 && (
        <div>
          <p className="text-muted-foreground mb-1 text-sm font-semibold tracking-wider uppercase">
            Related Entities ({related.length})
          </p>
          <div className="space-y-1">
            {related.map((r, i) => {
              const otherId = r.source === entity.id ? r.target : r.source
              const otherEntity = allEntities?.find((e) => e.id === otherId)
              const isSource = r.source === entity.id
              return (
                <div key={i} className="flex items-center gap-1.5 text-sm">
                  <span className="text-muted-foreground">
                    {isSource ? "→" : "←"}
                  </span>
                  <span className="text-foreground">{r.type}</span>
                  <span className="text-muted-foreground">→</span>
                  <span className="text-foreground truncate">
                    {otherEntity?.name ?? otherId.slice(0, 8)}
                  </span>
                </div>
              )
            })}
          </div>
        </div>
      )}
    </div>
  )
}

export interface SimilarNeighbor {
  memory: UnifiedMemory
  score: number
}

/**
 * The memories joined to this one by an edge the canvas drew — cosine
 * similarity over the content embeddings, above the threshold slider.
 *
 * Derived from the same edge list the renderer consumes, so the count here
 * and the spokes on screen can never disagree. This is a different relation
 * from Entity Context's neighbours, which are memories asserting a shared
 * entity and are scoped to one project; the two legitimately differ, and
 * before both were labelled the panel read as though one were wrong.
 */
function similarNeighbors(
  memoryId: string,
  edges: SimilarityEdge[],
  memories: UnifiedMemory[],
): SimilarNeighbor[] {
  const byId = new Map(memories.map((m) => [m.id, m]))
  const best = new Map<string, number>()
  for (const e of edges) {
    const other =
      e.source === memoryId ? e.target : e.target === memoryId ? e.source : null
    if (other === null) continue
    best.set(other, Math.max(best.get(other) ?? 0, e.score))
  }
  const out: SimilarNeighbor[] = []
  for (const [id, score] of best) {
    const memory = byId.get(id)
    if (memory) out.push({ memory, score })
  }
  return out.sort(
    (a, b) => b.score - a.score || a.memory.id.localeCompare(b.memory.id),
  )
}

interface MemoryDetailProps {
  memory: UnifiedMemory
  clusterName: string
  children?: React.ReactNode
  colorMode: ColorMode
  similarNeighbors: SimilarNeighbor[]
  onNavigateToMemory?: (memoryId: string) => void
}


/** The lifecycle rung, in words.
 *
 *  Deliberately not drawn on the canvas: a graph that fades and dashes half
 *  its nodes stops being a picture of structure. Here there is room to say
 *  what `superseded` actually means, which a dashed ring never could.
 */
const STATUS_STYLES: Record<string, string> = {
  active: "border-success/50 bg-success/10 text-success-text",
  superseded: "border-warning/60 border-dashed bg-warning/5 text-warning-text",
  deprecated: "border-border border-dashed bg-muted/40 text-muted-foreground",
}

function MemoryStatus({ status }: { status: string }) {
  return (
    <div className="flex items-center gap-2">
      <span className="text-muted-foreground text-sm">Status:</span>
      <span
        data-testid="memory-status"
        className={cn(
          "inline-flex items-center rounded-full border px-2 py-0.5 font-mono text-xs tracking-wide uppercase",
          STATUS_STYLES[status] ??
            "border-border bg-muted/40 text-muted-foreground",
        )}
      >
        {status}
      </span>
    </div>
  )
}

function MemoryDetail({
  memory,
  clusterName,
  children,
  colorMode,
  similarNeighbors,
  onNavigateToMemory,
}: MemoryDetailProps) {
  const { palette } = useMemoryGraphTheme()
  return (
    <div className="space-y-3 p-4">
      <p className="text-foreground text-sm leading-relaxed">
        {memory.content}
      </p>

      {memory.tags.length > 0 && (
        <div className="flex flex-wrap gap-1">
          {memory.tags.map((t) => (
            <span
              key={t}
              className="bg-accent text-primary-text rounded px-1.5 py-0.5 text-sm"
            >
              {t}
            </span>
          ))}
        </div>
      )}

      {memory.status && <MemoryStatus status={memory.status} />}

      <div className="text-muted-foreground space-y-0.5 text-sm">
        <div className="flex items-center gap-1">
          Source:{" "}
          <span className="text-foreground inline-flex items-center gap-1">
            <span
              className="inline-block h-2 w-2 rounded-full"
              style={{
                backgroundColor:
                  colorMode === "tag"
                    ? resolveNodeColor(
                        {
                          cluster: -1,
                          memory_type: null,
                          tags: memory.tags.slice(0, 1),
                        },
                        "tag",
                        palette,
                      )
                    : palette.unclustered,
              }}
            />
            {memory.source}
          </span>
        </div>
        {memory.memory_type && (
          <div className="flex items-center gap-1">
            Type:{" "}
            <span className="text-foreground inline-flex items-center gap-1">
              <span
                className="inline-block h-2 w-2 rounded-full"
                style={{
                  backgroundColor:
                    colorMode === "type"
                      ? resolveNodeColor(
                          {
                            cluster: -1,
                            memory_type: memory.memory_type,
                            tags: [],
                          },
                          "type",
                          palette,
                        )
                      : palette.unclustered,
                }}
              />
              {memory.memory_type}
            </span>
          </div>
        )}
        <div>
          Importance:{" "}
          <span className="text-foreground">
            {memory.importance.toFixed(2)}
          </span>
        </div>
        {memory.cluster >= 0 && (
          <div className="flex items-center gap-1">
            Cluster:{" "}
            <span className="text-foreground inline-flex items-center gap-1">
              <span
                className="inline-block h-2 w-2 rounded-full"
                style={{
                  backgroundColor:
                    colorMode === "cluster"
                      ? clusterColor(palette, memory.cluster)
                      : palette.unclustered,
                }}
              />
              {clusterName || `Cluster ${memory.cluster}`}
            </span>
          </div>
        )}
      </div>

      <div className="border-border border-t pt-3">
        <NeighborHeading
          label="Similar memories"
          count={similarNeighbors.length}
          hint="Joined by an edge on the canvas — cosine similarity above the threshold."
        />
        {similarNeighbors.length === 0 ? (
          <p className="text-muted-foreground text-sm">
            No edge above the current similarity threshold.
          </p>
        ) : (
          <div className="space-y-0.5">
            {similarNeighbors.map(({ memory: n, score }) => (
              <Button
                key={n.id}
                variant="ghost"
                className="text-muted-foreground hover:text-foreground flex w-full items-baseline gap-2 py-0.5 text-left"
                onClick={() => onNavigateToMemory?.(n.id)}
                title={n.content}
              >
                <span className="flex-1 truncate">{n.content}</span>
                <span className="text-foreground shrink-0 font-mono text-xs tabular-nums">
                  {score.toFixed(2)}
                </span>
              </Button>
            ))}
          </div>
        )}
      </div>

      {children && (
        <div className="border-border border-t pt-3">
          <NeighborHeading
            label="Entity Context"
            hint="Memories asserting a shared entity, within this project — a different relation from the edges above."
          />
          {children}
          <p className="text-muted-foreground mt-1 text-sm">
            Click a neighbor node to navigate.
          </p>
        </div>
      )}
    </div>
  )
}

function NeighborHeading({
  label,
  count,
  hint,
}: {
  label: string
  count?: number
  hint: string
}) {
  return (
    <div className="mb-2">
      <p className="text-muted-foreground text-sm font-medium tracking-wide uppercase">
        {label}
        {count !== undefined && (
          <span className="ml-1.5 tabular-nums">({count})</span>
        )}
      </p>
      <p className="text-muted-foreground/80 mt-0.5 text-xs leading-snug">
        {hint}
      </p>
    </div>
  )
}
