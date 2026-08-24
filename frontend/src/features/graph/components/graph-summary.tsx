import { ChevronDown } from "lucide-react"
import {
  Collapsible,
  CollapsibleTrigger,
  CollapsibleContent,
} from "darkraise-ui/components/collapsible"
import type {
  UnifiedMemory,
  GraphEntity,
  EntityRelation,
  SimilarityEdge,
} from "@/hooks/api"
import {
  resolveNodeColor,
  clusterColor,
  entityTypeColor,
  type ColorMode,
  type MemoryPalette,
} from "@/features/graph/lib/graph-colors"
import { useMemoryGraphTheme } from "@/features/graph/lib/memory-graph-theme"
import { deriveGraphSummary } from "@/features/graph/lib/graph-summary-stats"
import { EntityTypeSwatch } from "./entity-type-swatch"

const HUB_LIMIT = 5
const RELATION_TYPE_LIMIT = 4

/** Lifecycle colours are semantic, not palette: the rungs mean healthy,
 *  retired and dead, and reading them off the cluster hues would tie the
 *  meaning to whichever cluster ids happened to be on screen. */
const STATUS_BAR_CLASS: Record<string, string> = {
  active: "bg-success",
  superseded: "bg-warning",
  deprecated: "bg-muted-foreground",
}
const STATUS_FALLBACK_CLASS = "bg-border"

interface GraphSummaryProps {
  memories: UnifiedMemory[]
  edges: SimilarityEdge[]
  entities: GraphEntity[]
  entityRelations: EntityRelation[]
  clusterNames: Record<string, string>
  colorMode: ColorMode
}

export function GraphSummary({
  memories,
  edges,
  entities,
  entityRelations,
  clusterNames,
  colorMode,
}: GraphSummaryProps) {
  const { palette } = useMemoryGraphTheme()
  const stats = deriveGraphSummary(memories, edges, entities, entityRelations)

  const clusterLabel = (id: number) =>
    clusterNames[String(id)] || `Cluster ${id}`

  return (
    <div className="flex flex-col gap-5 p-4">
      <Headline
        memoryCount={stats.memoryCount}
        edgeCount={stats.edgeCount}
        averageDegree={stats.averageDegree}
        clusterCount={stats.clusters.length}
        entityCount={stats.entityCount}
        relationCount={stats.relationCount}
      />

      {stats.lifecycle && <Lifecycle rows={stats.lifecycle} />}

      <section>
        <SectionLabel>Shape</SectionLabel>
        <div className="flex flex-col gap-1.5">
          {stats.largestCluster && (
            <Measure
              label="Largest cluster"
              value={formatPercent(stats.largestCluster.share)}
              note={clusterLabel(stats.largestCluster.id)}
            />
          )}
          <Measure
            label="Unclustered"
            value={String(stats.unclusteredCount)}
            note={
              stats.memoryCount > 0
                ? formatPercent(stats.unclusteredCount / stats.memoryCount)
                : undefined
            }
          />
          <Measure
            label="Isolated nodes"
            value={String(stats.isolatedCount)}
            note="no visible edge"
          />
          {stats.meanImportance !== null && (
            <Measure
              label="Mean importance"
              value={stats.meanImportance.toFixed(2)}
            />
          )}
        </div>
      </section>

      {stats.hubs.length > 0 && (
        <section>
          <SectionLabel shown={Math.min(HUB_LIMIT, stats.hubs.length)} total={stats.hubs.length}>
            Top entities
          </SectionLabel>
          <div className="flex flex-col gap-2.5">
            {stats.hubs.slice(0, HUB_LIMIT).map((hub) => (
              <div key={hub.id}>
                <div className="flex items-center gap-2 text-sm">
                  <EntityTypeSwatch
                    entityType={hub.entityType}
                    palette={palette}
                  />
                  <span className="text-foreground flex-1 truncate">
                    {hub.name}
                  </span>
                  <span className="text-muted-foreground tabular-nums">
                    {hub.count}
                  </span>
                </div>
                <Bar
                  fraction={hub.count / stats.hubs[0]!.count}
                  color={entityTypeColor(hub.entityType, palette)}
                />
              </div>
            ))}
          </div>
        </section>
      )}

      {stats.relationTypes.length > 0 && (
        <section>
          <SectionLabel
            shown={Math.min(RELATION_TYPE_LIMIT, stats.relationTypes.length)}
            total={stats.relationTypes.length}
          >
            Top relations
          </SectionLabel>
          <div className="flex flex-col gap-1.5">
            {stats.relationTypes
              .slice(0, RELATION_TYPE_LIMIT)
              .map((row) => (
                <div key={row.key} className="flex items-center gap-2 text-sm">
                  <span className="text-foreground flex-1 truncate font-mono text-xs">
                    {row.label}
                  </span>
                  <span className="text-muted-foreground tabular-nums">
                    {row.count}
                  </span>
                </div>
              ))}
          </div>
        </section>
      )}

      <section>
        <SectionLabel>Breakdowns</SectionLabel>
        <div>
          <Drawer label="Clusters" count={stats.clusters.length}>
            {stats.clusters.map(({ id, count }) => (
              <FacetLine
                key={id}
                label={clusterLabel(id)}
                count={count}
                swatch={
                  <Dot
                    color={
                      colorMode === "cluster"
                        ? clusterColor(palette, id)
                        : palette.unclustered
                    }
                  />
                }
              />
            ))}
          </Drawer>

          <Drawer label="Types" count={stats.types.length}>
            {stats.types.map((row) => (
              <FacetLine
                key={row.key}
                label={row.label}
                count={row.count}
                swatch={
                  <Dot
                    color={nodeColor(
                      colorMode,
                      "type",
                      {
                        cluster: -1,
                        memory_type: row.key === "(none)" ? null : row.key,
                        tags: [],
                      },
                      palette,
                    )}
                  />
                }
              />
            ))}
          </Drawer>

          <Drawer label="Tag categories" count={stats.tagCategories.length}>
            {stats.tagCategories.map((row) => (
              <FacetLine
                key={row.key}
                label={row.label}
                count={row.count}
                capitalize
                swatch={
                  <Dot
                    color={nodeColor(
                      colorMode,
                      "tag",
                      {
                        cluster: -1,
                        memory_type: null,
                        // resolveNodeColor keys on the segment before the
                        // slash, so the category needs one to hash as itself.
                        tags: [`${row.key}/x`],
                      },
                      palette,
                    )}
                  />
                }
              />
            ))}
          </Drawer>

          <Drawer label="Sources" count={stats.sources.length}>
            {stats.sources.map((row) => (
              <FacetLine key={row.key} label={row.label} count={row.count} />
            ))}
          </Drawer>

          <Drawer label="Entity types" count={stats.entityTypes.length}>
            {stats.entityTypes.map((row) => (
              <FacetLine
                key={row.key}
                label={row.label}
                count={row.count}
                capitalize
                swatch={
                  <EntityTypeSwatch entityType={row.key} palette={palette} />
                }
              />
            ))}
          </Drawer>
        </div>
      </section>
    </div>
  )
}

function nodeColor(
  colorMode: ColorMode,
  mode: ColorMode,
  node: { cluster: number; memory_type: string | null; tags: string[] },
  palette: MemoryPalette,
): string {
  return colorMode === mode
    ? resolveNodeColor(node, mode, palette)
    : palette.unclustered
}

function formatPercent(fraction: number): string {
  return `${Math.round(fraction * 100)}%`
}

/** `shown`/`total` say what a "Top N" list left out. A truncated list that
 *  names no total reads as the whole population. */
function SectionLabel({
  children,
  shown,
  total,
}: {
  children: React.ReactNode
  shown?: number
  total?: number
}) {
  const truncated = shown !== undefined && total !== undefined && total > shown
  return (
    <p className="text-muted-foreground mb-2 flex items-baseline gap-1.5 font-mono text-xs font-medium tracking-[0.14em] uppercase">
      <span>{children}</span>
      {truncated && (
        <span className="tracking-normal normal-case opacity-70">
          {shown} of {total}
        </span>
      )}
    </p>
  )
}

function Dot({ color }: { color: string }) {
  return (
    <span
      className="h-2.5 w-2.5 shrink-0 rounded-full"
      style={{ backgroundColor: color }}
    />
  )
}

function Bar({ fraction, color }: { fraction: number; color: string }) {
  return (
    <div className="bg-muted/60 mt-1 ml-4.5 h-0.5 overflow-hidden rounded-full">
      <div
        className="h-full rounded-full opacity-70"
        style={{
          width: `${Math.max(2, Math.round(fraction * 100))}%`,
          backgroundColor: color,
        }}
      />
    </div>
  )
}

interface HeadlineProps {
  memoryCount: number
  edgeCount: number
  averageDegree: number | null
  clusterCount: number
  entityCount: number
  relationCount: number
}

function Headline({
  memoryCount,
  edgeCount,
  averageDegree,
  clusterCount,
  entityCount,
  relationCount,
}: HeadlineProps) {
  return (
    <div>
      <div className="flex items-baseline gap-2">
        <span
          data-testid="graph-summary-memory-count"
          className="text-2xl leading-none font-bold tabular-nums"
        >
          {memoryCount}
        </span>
        <span className="text-muted-foreground text-sm">memories</span>
        <span className="ml-auto text-lg leading-none font-semibold tabular-nums">
          {edgeCount}
        </span>
        <span className="text-muted-foreground text-sm">edges</span>
      </div>
      <div className="text-muted-foreground mt-2 flex flex-wrap gap-x-3 gap-y-1 font-mono text-xs">
        {averageDegree !== null && (
          <span>
            <span className="text-foreground">{averageDegree.toFixed(1)}</span>{" "}
            avg degree
          </span>
        )}
        <span>
          <span className="text-foreground">{clusterCount}</span> clusters
        </span>
        {entityCount > 0 && (
          <span>
            <span className="text-foreground">{entityCount}</span> entities
          </span>
        )}
        {relationCount > 0 && (
          <span>
            <span className="text-foreground">{relationCount}</span> relations
          </span>
        )}
      </div>
    </div>
  )
}

function Lifecycle({ rows }: { rows: { status: string; count: number }[] }) {
  const total = rows.reduce((sum, r) => sum + r.count, 0)
  return (
    <section data-testid="graph-summary-lifecycle">
      <SectionLabel>Lifecycle</SectionLabel>
      <div className="bg-muted flex h-2 overflow-hidden rounded-full">
        {rows.map((row) => (
          <div
            key={row.status}
            className={STATUS_BAR_CLASS[row.status] ?? STATUS_FALLBACK_CLASS}
            style={{ width: `${(row.count / total) * 100}%` }}
          />
        ))}
      </div>
      <div className="text-muted-foreground mt-2 flex flex-wrap gap-x-3.5 gap-y-1 text-sm">
        {rows.map((row) => (
          <span key={row.status} className="inline-flex items-center gap-1.5">
            <span
              className={`h-2.5 w-2.5 shrink-0 rounded-full ${
                STATUS_BAR_CLASS[row.status] ?? STATUS_FALLBACK_CLASS
              }`}
            />
            {row.status}{" "}
            <span className="text-foreground font-medium tabular-nums">
              {row.count}
            </span>
          </span>
        ))}
      </div>
    </section>
  )
}

function Measure({
  label,
  value,
  note,
}: {
  label: string
  value: string
  note?: string
}) {
  return (
    <div className="flex items-baseline justify-between gap-3 text-sm">
      <span className="text-muted-foreground">{label}</span>
      <span className="text-foreground font-medium tabular-nums">
        {value}
        {note && (
          <span className="text-muted-foreground ml-1 text-xs font-normal">
            · {note}
          </span>
        )}
      </span>
    </div>
  )
}

function Drawer({
  label,
  count,
  children,
}: {
  label: string
  count: number
  children: React.ReactNode
}) {
  if (count === 0) return null
  return (
    <Collapsible className="border-border border-b last:border-b-0">
      <CollapsibleTrigger className="group hover:text-foreground text-muted-foreground flex w-full cursor-pointer items-center gap-2 py-2 text-left text-sm">
        <ChevronDown
          className="h-3.5 w-3.5 shrink-0 transition-transform group-data-[state=closed]:-rotate-90"
          aria-hidden
        />
        <span className="text-foreground flex-1">{label}</span>
        <span className="tabular-nums">{count}</span>
      </CollapsibleTrigger>
      <CollapsibleContent>
        <div className="flex flex-col gap-1.5 pt-0.5 pb-3 pl-6">
          {children}
        </div>
      </CollapsibleContent>
    </Collapsible>
  )
}

function FacetLine({
  label,
  count,
  swatch,
  capitalize,
}: {
  label: string
  count: number
  swatch?: React.ReactNode
  capitalize?: boolean
}) {
  return (
    <div className="flex items-center gap-2 text-sm">
      {swatch ?? <span className="h-2.5 w-2.5 shrink-0" aria-hidden />}
      <span
        className={`text-foreground flex-1 truncate ${capitalize ? "capitalize" : ""}`}
      >
        {label}
      </span>
      <span className="text-muted-foreground tabular-nums">{count}</span>
    </div>
  )
}
