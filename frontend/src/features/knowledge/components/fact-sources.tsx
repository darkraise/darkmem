import { Badge } from "darkraise-ui/components/badge"
import { cn } from "darkraise-ui/lib"
import { useDetailLevel } from "@/components/darkmem"
import type { FactSource } from "@/demo/types"
import {
  distinctOriginCount,
  groupSourcesByOrigin,
} from "@/demo/knowledge"

export function SourceRow({ source }: { source: FactSource }) {
  return (
    <div className="border-border flex flex-wrap items-baseline gap-x-2.5 gap-y-0.5 border-t border-dashed py-1.5 first:border-t-0 first:pt-0">
      <span className="min-w-40 shrink-0 font-mono text-sm font-semibold">
        {source.ref}
      </span>
      <span className="min-w-52 flex-1 text-sm">{source.detail}</span>
      <span className="text-muted-foreground ml-auto shrink-0 font-mono text-sm">
        {source.at}
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
  const distinct = distinctOriginCount(sources)

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
            <span className="font-mono text-sm">
              origin_key: {group.origin_key}
            </span>
            <span className="text-muted-foreground ml-auto text-sm whitespace-nowrap">
              1 distinct origin · {group.rows.length}{" "}
              {group.rows.length === 1 ? "row" : "rows"}
            </span>
          </div>
          {level === "advanced" && (
            <div>
              {group.rows.map((row, i) => (
                <SourceRow key={i} source={row} />
              ))}
            </div>
          )}
          {group.rows.length > 1 && (
            <p className="text-muted-foreground text-sm italic">
              same origin_key — same capturing session — {group.rows.length}{" "}
              memories, one origin, counted once.
            </p>
          )}
        </div>
      ))}
      <p className="text-muted-foreground text-sm">
        COUNT(DISTINCT origin_key) over the {sources.length} raw fact_sources{" "}
        {sources.length === 1 ? "row" : "rows"} above ={" "}
        <b className="text-foreground">{distinct}</b> — the badge's K.
        {sources.length !== distinct &&
          ` A UI that read "${sources.length} sources" here would silently overclaim.`}
      </p>
    </div>
  )
}
