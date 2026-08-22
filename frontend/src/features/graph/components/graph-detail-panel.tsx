import { X } from "lucide-react"
import { Button } from "darkraise-ui/components/button"
import { cn } from "darkraise-ui/lib"
import type { UnifiedMemory, GraphEntity, EntityRelation } from "@/hooks/api"
import { resolveNodeColor, entityTypeColor, clusterColor } from "@/features/graph/lib/graph-colors"
import { EntityTypeSwatch } from "./entity-type-swatch"
import type { ColorMode } from "@/features/graph/lib/graph-colors"
import { useMemoryGraphTheme } from "@/features/graph/lib/memory-graph-theme"

interface GraphDetailPanelProps {
  selectedMemory: UnifiedMemory | null
  clusterName: string
  memories: UnifiedMemory[]
  clusterNames: Record<string, string>
  visibleEdgeCount: number
  onClose: () => void
  children?: React.ReactNode
  selectedEntity?: GraphEntity | null
  entityRelations?: EntityRelation[]
  allEntities?: GraphEntity[]
  onNavigateToMemory?: (memoryId: string) => void
  colorMode: ColorMode
}

export function GraphDetailPanel({
  selectedMemory,
  clusterName,
  memories,
  clusterNames,
  visibleEdgeCount,
  onClose,
  children,
  selectedEntity,
  entityRelations,
  allEntities,
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
          >
            {children}
          </MemoryDetail>
        ) : (
          <GraphSummary
            memories={memories}
            clusterNames={clusterNames}
            visibleEdgeCount={visibleEdgeCount}
            colorMode={colorMode}
            entities={allEntities}
            entityRelations={entityRelations}
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

interface MemoryDetailProps {
  memory: UnifiedMemory
  clusterName: string
  children?: React.ReactNode
  colorMode: ColorMode
}


/** The lifecycle rung, in words.
 *
 *  Deliberately not drawn on the canvas: a graph that fades and dashes half
 *  its nodes stops being a picture of structure. Here there is room to say
 *  what `superseded` actually means, which a dashed ring never could.
 */
const STATUS_STYLES: Record<string, string> = {
  active: "border-success/50 bg-success/10 text-success",
  superseded: "border-warning/60 border-dashed bg-warning/5 text-warning",
  deprecated: "border-border border-dashed bg-muted/40 text-muted-foreground",
}

function MemoryStatus({ status }: { status: string }) {
  return (
    <div className="flex items-center gap-2">
      <span className="text-muted-foreground text-sm">Status:</span>
      <span
        data-testid="memory-status"
        className={cn(
          "inline-flex items-center rounded-full border px-2 py-0.5 font-mono text-[10px] tracking-wide uppercase",
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
              className="bg-accent text-primary rounded px-1.5 py-0.5 text-sm"
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

      {children && (
        <div className="border-border border-t pt-2">
          <p className="text-muted-foreground mb-2 text-sm font-medium tracking-wide uppercase">
            Entity Context
          </p>
          {children}
          <p className="text-muted-foreground mt-1 text-sm">
            Click a neighbor node to navigate.
          </p>
        </div>
      )}
    </div>
  )
}

interface GraphSummaryProps {
  memories: UnifiedMemory[]
  clusterNames: Record<string, string>
  visibleEdgeCount: number
  colorMode: ColorMode
  entities?: GraphEntity[]
  entityRelations?: EntityRelation[]
}

function GraphSummary({
  memories,
  clusterNames,
  visibleEdgeCount,
  colorMode,
  entities,
  entityRelations,
}: GraphSummaryProps) {
  const { palette } = useMemoryGraphTheme()
  const clusterCounts = new Map<number, number>()
  const typeCounts = new Map<string, number>()
  const sourceCounts = new Map<string, number>()
  const tagCategoryCounts = new Map<string, number>()

  for (const m of memories) {
    if (m.cluster >= 0) {
      clusterCounts.set(m.cluster, (clusterCounts.get(m.cluster) ?? 0) + 1)
    }
    const t = m.memory_type || "(none)"
    typeCounts.set(t, (typeCounts.get(t) ?? 0) + 1)
    sourceCounts.set(m.source, (sourceCounts.get(m.source) ?? 0) + 1)
    for (const tag of m.tags) {
      const prefix = tag.includes("/") ? (tag.split("/")[0] ?? tag) : tag
      tagCategoryCounts.set(prefix, (tagCategoryCounts.get(prefix) ?? 0) + 1)
    }
  }

  const entityTypeCounts = new Map<string, number>()
  for (const e of entities ?? []) {
    entityTypeCounts.set(
      e.entity_type,
      (entityTypeCounts.get(e.entity_type) ?? 0) + 1,
    )
  }

  const sortedClusters = [...clusterCounts.entries()].sort(
    (a, b) => b[1] - a[1],
  )
  const sortedTypes = [...typeCounts.entries()].sort((a, b) => b[1] - a[1])
  const sortedSources = [...sourceCounts.entries()].sort((a, b) => b[1] - a[1])
  const sortedTagCategories = [...tagCategoryCounts.entries()].sort(
    (a, b) => b[1] - a[1],
  )
  const sortedEntityTypes = [...entityTypeCounts.entries()].sort(
    (a, b) => b[1] - a[1],
  )

  return (
    <div className="space-y-4 p-4">
      <div className="grid grid-cols-2 gap-3">
        <div className="bg-background rounded-lg p-3">
          <p className="text-2xl font-bold">{memories.length}</p>
          <p className="text-muted-foreground text-sm">Memories</p>
        </div>
        <div className="bg-background rounded-lg p-3">
          <p className="text-2xl font-bold">{clusterCounts.size}</p>
          <p className="text-muted-foreground text-sm">Clusters</p>
        </div>
        <div className="bg-background rounded-lg p-3">
          <p className="text-2xl font-bold">{visibleEdgeCount}</p>
          <p className="text-muted-foreground text-sm">Edges</p>
        </div>
        <div className="bg-background rounded-lg p-3">
          <p className="text-2xl font-bold">{typeCounts.size}</p>
          <p className="text-muted-foreground text-sm">Types</p>
        </div>
        {(entities?.length ?? 0) > 0 && (
          <div className="bg-background rounded-lg p-3">
            <p className="text-2xl font-bold">{entities!.length}</p>
            <p className="text-muted-foreground text-sm">Entities</p>
          </div>
        )}
        {(entityRelations?.length ?? 0) > 0 && (
          <div className="bg-background rounded-lg p-3">
            <p className="text-2xl font-bold">{entityRelations!.length}</p>
            <p className="text-muted-foreground text-sm">Relations</p>
          </div>
        )}
      </div>

      {sortedClusters.length > 0 && (
        <div>
          <p className="text-muted-foreground mb-2 text-sm font-medium tracking-wide uppercase">
            Clusters
          </p>
          <div className="space-y-1.5">
            {sortedClusters.map(([cid, count]) => (
              <div key={cid} className="flex items-center gap-2 text-sm">
                <span
                  className="h-2.5 w-2.5 shrink-0 rounded-full"
                  style={{
                    backgroundColor:
                      colorMode === "cluster"
                        ? clusterColor(palette, cid)
                        : palette.unclustered,
                  }}
                />
                <span className="text-foreground flex-1 truncate">
                  {clusterNames[String(cid)] || `Cluster ${cid}`}
                </span>
                <span className="text-muted-foreground text-sm">{count}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {sortedTagCategories.length > 0 && (
        <div>
          <p className="text-muted-foreground mb-2 text-sm font-medium tracking-wide uppercase">
            Tag Categories
          </p>
          <div className="space-y-1.5">
            {sortedTagCategories.map(([category, count]) => (
              <div key={category} className="flex items-center gap-2 text-sm">
                <span
                  className="h-2.5 w-2.5 shrink-0 rounded-full"
                  style={{
                    backgroundColor:
                      colorMode === "tag"
                        ? resolveNodeColor(
                            {
                              cluster: -1,
                              memory_type: null,
                              tags: [category + "/x"],
                            },
                            "tag",
                            palette,
                          )
                        : palette.unclustered,
                  }}
                />
                <span className="text-foreground flex-1 capitalize">
                  {category}
                </span>
                <span className="text-muted-foreground text-sm">{count}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {sortedTypes.length > 0 && (
        <div>
          <p className="text-muted-foreground mb-2 text-sm font-medium tracking-wide uppercase">
            Types
          </p>
          <div className="space-y-1.5">
            {sortedTypes.map(([type, count]) => (
              <div key={type} className="flex items-center gap-2 text-sm">
                <span
                  className="h-2.5 w-2.5 shrink-0 rounded-full"
                  style={{
                    backgroundColor:
                      colorMode === "type"
                        ? resolveNodeColor(
                            {
                              cluster: -1,
                              memory_type: type === "(none)" ? null : type,
                              tags: [],
                            },
                            "type",
                            palette,
                          )
                        : palette.unclustered,
                  }}
                />
                <span className="text-foreground flex-1">{type}</span>
                <span className="text-muted-foreground text-sm">{count}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {sortedSources.length > 0 && (
        <div>
          <p className="text-muted-foreground mb-2 text-sm font-medium tracking-wide uppercase">
            Sources
          </p>
          <div className="space-y-1.5">
            {sortedSources.map(([src, count]) => (
              <div key={src} className="flex items-center gap-2 text-sm">
                <span className="text-foreground flex-1">{src}</span>
                <span className="text-muted-foreground text-sm">{count}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {sortedEntityTypes.length > 0 && (
        <div>
          <p className="text-muted-foreground mb-2 text-sm font-medium tracking-wide uppercase">
            Entity Types
          </p>
          <div className="space-y-1.5">
            {sortedEntityTypes.map(([etype, count]) => (
              <div key={etype} className="flex items-center gap-2 text-sm">
                <EntityTypeSwatch entityType={etype} palette={palette} />
                <span className="text-foreground flex-1 capitalize">
                  {etype}
                </span>
                <span className="text-muted-foreground text-sm">{count}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
