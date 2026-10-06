import { useState } from "react"
import { ChevronDown, ChevronUp, FileText, Diamond } from "lucide-react"
import { Badge } from "darkraise-ui/components/badge"
import { Button } from "darkraise-ui/components/button"
import {
  Collapsible,
  CollapsibleTrigger,
  CollapsibleContent,
} from "darkraise-ui/components/collapsible"
import { LayerChip } from "@/components/darkmem"
import { LifecycleBadge } from "@/features/memories/components/lifecycle-badge"
import type { MemoryStatus } from "@/hooks/api"
import { shortId } from "@/lib/short-id"

interface SourceBadgesProps {
  memories: {
    index?: number
    content?: string
    source?: string
    tags?: string[]
    score?: number
    id?: string
    created_at?: string
    project?: string
    status?: MemoryStatus
    selected?: boolean
  }[]
  entities: { id?: string; name?: string; entity_type?: string }[]
}

function formatMemoryDate(dateStr?: string): string {
  if (!dateStr) return ""
  const d = new Date(dateStr)
  if (isNaN(d.getTime())) return ""
  return d.toLocaleDateString([], {
    month: "short",
    day: "numeric",
    year: "numeric",
  })
}

export function SourceBadges({ memories, entities }: SourceBadgesProps) {
  const [open, setOpen] = useState(false)

  if (memories.length === 0 && entities.length === 0) return null

  const entityCount = entities.filter((e) => e.name).length

  return (
    <div className="mt-2.5">
      <Collapsible open={open} onOpenChange={setOpen}>
        <CollapsibleTrigger asChild>
          <Button
            variant="ghost"
            className="text-muted-foreground/70 hover:text-muted-foreground flex items-center gap-2"
          >
            {memories.length > 0 && (
              <Badge variant="secondary" className="gap-1">
                <FileText className="h-3 w-3" />
                {memories.length}{" "}
                {memories.length === 1 ? "memory" : "memories"}
              </Badge>
            )}
            {entityCount > 0 && (
              <Badge variant="outline" className="gap-1">
                <Diamond className="h-3 w-3" />
                {entityCount} {entityCount === 1 ? "entity" : "entities"}
              </Badge>
            )}
            {open ? (
              <ChevronUp className="h-3 w-3" />
            ) : (
              <ChevronDown className="h-3 w-3" />
            )}
          </Button>
        </CollapsibleTrigger>

        <CollapsibleContent>
          <div className="animate-in slide-in-from-top-1 mt-2 space-y-1.5 text-sm duration-150">
            {memories.map((m, i) => {
              const dateLabel = formatMemoryDate(m.created_at)
              return (
                <div
                  key={m.id ?? i}
                  className="border-border bg-card rounded-lg border p-2.5"
                >
                  <div className="mb-1 flex flex-wrap items-center gap-1.5">
                    <LayerChip layer={0} />
                    <LifecycleBadge status={m.status} />
                    {m.selected && (
                      <Badge variant="outline">your selection</Badge>
                    )}
                  </div>
                  <div className="text-foreground/90 line-clamp-2 leading-relaxed">
                    {m.content || `Memory ${shortId(m.id)}`}
                  </div>
                  <div className="text-muted-foreground/50 mt-1.5 flex flex-wrap gap-x-3 gap-y-1 text-sm">
                    {m.source && (
                      <span className="inline-flex items-center gap-1">
                        <FileText className="h-3 w-3" />
                        {m.source}
                      </span>
                    )}
                    {/* The fused ranking score, not a similarity: ~0.01-0.03
                        for the best hit, so as a percentage every source read
                        "1-2% match". It orders sources; it is not a grade. */}
                    {m.score != null && (
                      <span title="Fused ranking score (RRF): higher ranks first; not a percentage">
                        score {m.score.toFixed(3)}
                      </span>
                    )}
                    {dateLabel && <span>{dateLabel}</span>}
                    {m.tags && m.tags.length > 0 && (
                      <span className="truncate">
                        {m.tags.slice(0, 2).join(", ")}
                      </span>
                    )}
                  </div>
                </div>
              )
            })}
            {entities
              .filter((e) => e.name)
              .map((e, i) => (
                <div
                  key={e.id ?? i}
                  className="border-border bg-card flex items-center gap-2.5 rounded-lg border p-2.5"
                >
                  <Diamond className="text-muted-foreground h-3 w-3 shrink-0" />
                  <span className="text-foreground/90 font-medium">
                    {e.name}
                  </span>
                  {e.entity_type && (
                    <Badge variant="secondary" className="capitalize">
                      {e.entity_type}
                    </Badge>
                  )}
                </div>
              ))}
          </div>
        </CollapsibleContent>
      </Collapsible>
    </div>
  )
}
