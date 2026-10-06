import { Link } from "@tanstack/react-router"
import { Badge } from "darkraise-ui/components/badge"
import { cn } from "darkraise-ui/lib"
import { Timestamp, useDetailLevel } from "@/components/darkmem"
import type { FactSource, OriginKind } from "@/demo/types"
import { groupSourcesByOrigin } from "@/demo/knowledge"
import type { FactSourceGroup } from "@/hooks/api"
import { StaleBadge } from "./fact-parts"

const UNKNOWN_ORIGIN_KEY = "unknown"

function detailText(detail: Record<string, unknown> | null): string {
  if (!detail || Object.keys(detail).length === 0) return "—"
  return JSON.stringify(detail)
}

/** The live door's already-grouped `fact_sources` rows (T2.36a's
 *  `sources_by_origin`), flattened back into `FactSourcesGroups`' input
 *  shape so this one component — with its existing Simple/Advanced
 *  behaviour — serves both producers. Re-grouping the flattened rows by
 *  `origin_key` reproduces exactly the partition the backend already
 *  computed, since both group on the same key; this is not a second
 *  grouping *decision*, only the same one taken twice. `detail` has no
 *  demo-shaped free-text field on the wire — the backend's is a structured
 *  `dict`, rendered here rather than dropped. */
export function sourceGroupsToFlatSources(groups: FactSourceGroup[]): FactSource[] {
  return groups.flatMap((group) =>
    group.sources.map((source) => ({
      origin_key: group.origin_key ?? UNKNOWN_ORIGIN_KEY,
      kind: source.source_kind as OriginKind,
      ref: source.source_ref,
      detail: detailText(source.detail),
      at: source.created_at,
      // Broadcast the group's own `stale` (doc 10 §6) onto every row it
      // contains, so re-grouping by origin_key downstream (`groupSourcesByOrigin`)
      // recovers the same flag rather than losing it in the flatten.
      stale: group.stale,
    })),
  )
}

const UUID_RE =
  /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i
const REF_LINK = "underline-offset-2 hover:underline text-primary-text"

/** A source's ref, linked to the page that holds it where one exists: a
 *  memory source's ref is the memory id, and a code source whose ref is a
 *  bare repository id opens that repository's graph. A human or block ref,
 *  or a code ref in another shape, has no single page and stays text. */
function SourceRef({ source }: { source: FactSource }) {
  if (source.kind === "memory" && UUID_RE.test(source.ref)) {
    return (
      <Link
        to="/memories/$memoryId"
        params={{ memoryId: source.ref }}
        className={REF_LINK}
      >
        {source.ref}
      </Link>
    )
  }
  if (source.kind === "code" && UUID_RE.test(source.ref)) {
    return (
      <Link to="/code/graph" search={{ repo: source.ref }} className={REF_LINK}>
        {source.ref}
      </Link>
    )
  }
  return <>{source.ref}</>
}

export function SourceRow({ source }: { source: FactSource }) {
  return (
    <div className="border-border flex flex-wrap items-baseline gap-x-2.5 gap-y-0.5 border-t border-dashed py-1.5 first:border-t-0 first:pt-0">
      <span className="min-w-40 shrink-0 font-mono text-sm font-semibold">
        <SourceRef source={source} />
      </span>
      <span className="min-w-52 flex-1 text-sm">{source.detail}</span>
      <span className="text-muted-foreground ml-auto shrink-0 font-mono text-sm">
        <Timestamp iso={source.at} />
      </span>
    </div>
  )
}

// fact_sources grouped by origin_key so the badge's K — COUNT(DISTINCT
// origin_key), never the raw row count — is auditable, not asserted.
export function FactSourcesGroups({
  sources,
  className,
}: {
  sources: FactSource[]
  className?: string
}) {
  const level = useDetailLevel((s) => s.level)
  const groups = groupSourcesByOrigin(sources)

  return (
    <div className={cn("space-y-2.5", className)}>
      {groups.map((group) => (
        <div
          key={group.origin_key}
          className="border-border space-y-1.5 rounded-md border p-2.5"
        >
          <div className="flex flex-wrap items-center gap-2">
            <Badge variant="outline" size="sm" className="rounded-sm font-mono">
              {group.kind}
            </Badge>
            {group.stale && <StaleBadge />}
            <span className="font-mono text-sm">{group.origin_key}</span>
            {group.rows.length > 1 && (
              <span className="text-muted-foreground ml-auto text-sm whitespace-nowrap">
                {group.rows.length} entries, counted once
              </span>
            )}
          </div>
          {level === "advanced" && (
            <div>
              {group.rows.map((row, i) => (
                <SourceRow key={i} source={row} />
              ))}
            </div>
          )}
          {group.stale && (
            // A demotion of corroboration, never a contradiction — this
            // origin's citation no longer resolves, so it stopped
            // corroborating; it is not evidence *against* the fact.
            <p className="text-muted-foreground text-sm italic">
              The citation no longer resolves, so this origin is not counted.
            </p>
          )}
        </div>
      ))}
    </div>
  )
}
