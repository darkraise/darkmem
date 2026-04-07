import { X } from "lucide-react";
import type { UnifiedMemory, GraphEntity, EntityRelation } from "@/hooks/useApi";
import { UNIFIED_PALETTE, UNCLUSTERED_COLOR, entityTypeColor, resolveNodeColor } from "@/lib/graph-colors";
import type { ColorMode } from "@/lib/graph-colors";

interface GraphDetailPanelProps {
  selectedMemory: UnifiedMemory | null;
  clusterName: string;
  memories: UnifiedMemory[];
  clusterNames: Record<string, string>;
  visibleEdgeCount: number;
  onClose: () => void;
  children?: React.ReactNode;
  selectedEntity?: GraphEntity | null;
  entityRelations?: EntityRelation[];
  allEntities?: GraphEntity[];
  onNavigateToMemory?: (memoryId: string) => void;
  colorMode: ColorMode;
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
      : "Graph Summary";

  return (
    <>
      <div className="flex items-center justify-between px-4 pt-3 pb-2 border-b border-border shrink-0">
        <span className="text-sm font-medium">{panelTitle}</span>
        <button
          className="text-muted-foreground hover:text-foreground rounded-sm p-1"
          onClick={onClose}
        >
          <X className="w-4 h-4" />
        </button>
      </div>

      <div className="flex-1 overflow-auto min-h-0">
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
  );
}

interface EntityDetailProps {
  entity: GraphEntity;
  memories: UnifiedMemory[];
  entityRelations?: EntityRelation[];
  allEntities?: GraphEntity[];
  onNavigateToMemory?: (memoryId: string) => void;
}

function EntityDetail({ entity, memories, entityRelations, allEntities, onNavigateToMemory }: EntityDetailProps) {
  const color = entityTypeColor(entity.entity_type);
  const related = entityRelations?.filter(
    (r) => r.source === entity.id || r.target === entity.id,
  ) ?? [];

  return (
    <div className="p-4 space-y-4">
      <div>
        <h3 className="text-base font-semibold text-foreground">{entity.name}</h3>
        <span
          className="inline-block mt-1 px-2 py-0.5 text-xs rounded-full capitalize"
          style={{ backgroundColor: color + "20", color }}
        >
          {entity.entity_type}
        </span>
      </div>

      {Object.keys(entity.properties).length > 0 && (
        <div>
          <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-1">Properties</p>
          <div className="space-y-1">
            {Object.entries(entity.properties).map(([key, value]) => (
              <div key={key} className="flex gap-2 text-xs">
                <span className="text-muted-foreground">{key}:</span>
                <span className="text-foreground">{String(value)}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      <div>
        <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-1">
          Linked Memories ({entity.memory_ids.length})
        </p>
        <div className="space-y-1">
          {entity.memory_ids.slice(0, 20).map((mid) => {
            const mem = memories.find((m) => m.id === mid);
            return (
              <button
                key={mid}
                className="w-full text-left text-xs text-muted-foreground hover:text-foreground truncate block py-0.5"
                onClick={() => onNavigateToMemory?.(mid)}
                title={mem?.content}
              >
                {mem ? mem.content.slice(0, 80) : mid.slice(0, 8) + "…"}
              </button>
            );
          })}
        </div>
      </div>

      {related.length > 0 && (
        <div>
          <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-1">
            Related Entities ({related.length})
          </p>
          <div className="space-y-1">
            {related.map((r, i) => {
              const otherId = r.source === entity.id ? r.target : r.source;
              const otherEntity = allEntities?.find((e) => e.id === otherId);
              const isSource = r.source === entity.id;
              return (
                <div key={i} className="flex items-center gap-1.5 text-xs">
                  <span className="text-muted-foreground">{isSource ? "→" : "←"}</span>
                  <span className="text-foreground">{r.type}</span>
                  <span className="text-muted-foreground">→</span>
                  <span className="text-foreground truncate">{otherEntity?.name ?? otherId.slice(0, 8)}</span>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}

interface MemoryDetailProps {
  memory: UnifiedMemory;
  clusterName: string;
  children?: React.ReactNode;
  colorMode: ColorMode;
}

function MemoryDetail({ memory, clusterName, children, colorMode }: MemoryDetailProps) {
  return (
    <div className="p-4 space-y-3">
      <p className="text-sm text-foreground leading-relaxed">{memory.content}</p>

      {memory.tags.length > 0 && (
        <div className="flex gap-1 flex-wrap">
          {memory.tags.map((t) => (
            <span
              key={t}
              className="text-xs px-1.5 py-0.5 rounded bg-accent text-primary"
            >
              {t}
            </span>
          ))}
        </div>
      )}

      <div className="text-xs text-muted-foreground space-y-0.5">
        <div className="flex items-center gap-1">
          Source:{" "}
          <span className="inline-flex items-center gap-1 text-foreground">
            <span
              className="inline-block w-2 h-2 rounded-full"
              style={{ backgroundColor: colorMode === "tag" ? resolveNodeColor({ cluster: -1, memory_type: null, tags: memory.tags.length > 0 ? [memory.tags[0]] : [] }, "tag") : "#8b949e" }}
            />
            {memory.source}
          </span>
        </div>
        {memory.memory_type && (
          <div className="flex items-center gap-1">
            Type:{" "}
            <span className="inline-flex items-center gap-1 text-foreground">
              <span
                className="inline-block w-2 h-2 rounded-full"
                style={{ backgroundColor: colorMode === "type" ? resolveNodeColor({ cluster: -1, memory_type: memory.memory_type, tags: [] }, "type") : "#8b949e" }}
              />
              {memory.memory_type}
            </span>
          </div>
        )}
        <div>
          Importance:{" "}
          <span className="text-foreground">{memory.importance.toFixed(2)}</span>
        </div>
        {memory.cluster >= 0 && (
          <div className="flex items-center gap-1">
            Cluster:{" "}
            <span className="inline-flex items-center gap-1 text-foreground">
              <span
                className="inline-block w-2 h-2 rounded-full"
                style={{ backgroundColor: colorMode === "cluster" ? UNIFIED_PALETTE[memory.cluster % UNIFIED_PALETTE.length] : "#8b949e" }}
              />
              {clusterName || `Cluster ${memory.cluster}`}
            </span>
          </div>
        )}
      </div>

      {children && (
        <div className="pt-2 border-t border-border">
          <p className="text-xs font-medium text-muted-foreground mb-2 uppercase tracking-wide">
            Entity Context
          </p>
          {children}
          <p className="text-xs text-muted-foreground mt-1">
            Click a neighbor node to navigate.
          </p>
        </div>
      )}
    </div>
  );
}

interface GraphSummaryProps {
  memories: UnifiedMemory[];
  clusterNames: Record<string, string>;
  visibleEdgeCount: number;
  colorMode: ColorMode;
  entities?: GraphEntity[];
  entityRelations?: EntityRelation[];
}

function GraphSummary({ memories, clusterNames, visibleEdgeCount, colorMode, entities, entityRelations }: GraphSummaryProps) {
  const clusterCounts = new Map<number, number>();
  const typeCounts = new Map<string, number>();
  const sourceCounts = new Map<string, number>();
  const tagCategoryCounts = new Map<string, number>();

  for (const m of memories) {
    if (m.cluster >= 0) {
      clusterCounts.set(m.cluster, (clusterCounts.get(m.cluster) ?? 0) + 1);
    }
    const t = m.memory_type || "(none)";
    typeCounts.set(t, (typeCounts.get(t) ?? 0) + 1);
    sourceCounts.set(m.source, (sourceCounts.get(m.source) ?? 0) + 1);
    for (const tag of m.tags) {
      const prefix = tag.includes("/") ? tag.split("/")[0] : tag;
      tagCategoryCounts.set(prefix, (tagCategoryCounts.get(prefix) ?? 0) + 1);
    }
  }

  const entityTypeCounts = new Map<string, number>();
  for (const e of entities ?? []) {
    entityTypeCounts.set(e.entity_type, (entityTypeCounts.get(e.entity_type) ?? 0) + 1);
  }

  const sortedClusters = [...clusterCounts.entries()].sort((a, b) => b[1] - a[1]);
  const sortedTypes = [...typeCounts.entries()].sort((a, b) => b[1] - a[1]);
  const sortedSources = [...sourceCounts.entries()].sort((a, b) => b[1] - a[1]);
  const sortedTagCategories = [...tagCategoryCounts.entries()].sort((a, b) => b[1] - a[1]);
  const sortedEntityTypes = [...entityTypeCounts.entries()].sort((a, b) => b[1] - a[1]);

  return (
    <div className="p-4 space-y-4">
      <div className="grid grid-cols-2 gap-3">
        <div className="bg-background rounded-lg p-3">
          <p className="text-2xl font-bold">{memories.length}</p>
          <p className="text-xs text-muted-foreground">Memories</p>
        </div>
        <div className="bg-background rounded-lg p-3">
          <p className="text-2xl font-bold">{clusterCounts.size}</p>
          <p className="text-xs text-muted-foreground">Clusters</p>
        </div>
        <div className="bg-background rounded-lg p-3">
          <p className="text-2xl font-bold">{visibleEdgeCount}</p>
          <p className="text-xs text-muted-foreground">Edges</p>
        </div>
        <div className="bg-background rounded-lg p-3">
          <p className="text-2xl font-bold">{typeCounts.size}</p>
          <p className="text-xs text-muted-foreground">Types</p>
        </div>
        {(entities?.length ?? 0) > 0 && (
          <div className="bg-background rounded-lg p-3">
            <p className="text-2xl font-bold">{entities!.length}</p>
            <p className="text-xs text-muted-foreground">Entities</p>
          </div>
        )}
        {(entityRelations?.length ?? 0) > 0 && (
          <div className="bg-background rounded-lg p-3">
            <p className="text-2xl font-bold">{entityRelations!.length}</p>
            <p className="text-xs text-muted-foreground">Relations</p>
          </div>
        )}
      </div>

      {sortedClusters.length > 0 && (
        <div>
          <p className="text-xs font-medium text-muted-foreground mb-2 uppercase tracking-wide">
            Clusters
          </p>
          <div className="space-y-1.5">
            {sortedClusters.map(([cid, count]) => (
              <div key={cid} className="flex items-center gap-2 text-sm">
                <span
                  className="w-2.5 h-2.5 rounded-full shrink-0"
                  style={{ backgroundColor: colorMode === "cluster" ? UNIFIED_PALETTE[cid % UNIFIED_PALETTE.length] : "#8b949e" }}
                />
                <span className="flex-1 truncate text-foreground">
                  {clusterNames[String(cid)] || `Cluster ${cid}`}
                </span>
                <span className="text-xs text-muted-foreground">{count}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {sortedTagCategories.length > 0 && (
        <div>
          <p className="text-xs font-medium text-muted-foreground mb-2 uppercase tracking-wide">
            Tag Categories
          </p>
          <div className="space-y-1.5">
            {sortedTagCategories.map(([category, count]) => (
              <div key={category} className="flex items-center gap-2 text-sm">
                <span
                  className="w-2.5 h-2.5 rounded-full shrink-0"
                  style={{ backgroundColor: colorMode === "tag" ? resolveNodeColor({ cluster: -1, memory_type: null, tags: [category + "/x"] }, "tag") : "#8b949e" }}
                />
                <span className="flex-1 text-foreground capitalize">{category}</span>
                <span className="text-xs text-muted-foreground">{count}</span>
              </div>
            ))}
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
                  style={{ backgroundColor: colorMode === "type" ? resolveNodeColor({ cluster: -1, memory_type: type === "(none)" ? null : type, tags: [] }, "type") : "#8b949e" }}
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

      {sortedEntityTypes.length > 0 && (
        <div>
          <p className="text-xs font-medium text-muted-foreground mb-2 uppercase tracking-wide">
            Entity Types
          </p>
          <div className="space-y-1.5">
            {sortedEntityTypes.map(([etype, count]) => (
              <div key={etype} className="flex items-center gap-2 text-sm">
                <span
                  className="w-2.5 h-2.5 shrink-0"
                  style={{ backgroundColor: entityTypeColor(etype), clipPath: "polygon(50% 0%, 100% 50%, 50% 100%, 0% 50%)" }}
                />
                <span className="flex-1 text-foreground capitalize">{etype}</span>
                <span className="text-xs text-muted-foreground">{count}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
