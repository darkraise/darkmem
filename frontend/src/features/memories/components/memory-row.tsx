import { ChevronDown } from "lucide-react"
import { Badge } from "darkraise-ui/components/badge"
import { Button } from "darkraise-ui/components/button"
import { cn } from "darkraise-ui/lib"
import { relativeTime } from "@/lib/format"
import {
  LayerChip,
  VerificationBadge,
  WhyRetrievedTrace,
  listItemClass,
  type KnowledgeLayer,
  type VerificationStatus,
} from "@/components/darkmem"
import type { MemoryStatus } from "@/hooks/api"
import type { MemoryTraceView } from "../use-memory-search"
import { Link } from "@tanstack/react-router"
import { LifecycleBadge } from "./lifecycle-badge"

// The minimal shape a result row needs to render, shared between the demo
// store's DemoMemory and the real backend's Memory — the fields honesty
// invariant 14 requires (layer, lifecycle, verification) always render,
// whichever source populated them.
export interface MemoryRowData {
  id: string
  content: string
  tags: string[]
  flags?: string[] | null
  source: string
  created_at: string
  layer: KnowledgeLayer
  status?: MemoryStatus
  verification_status?: VerificationStatus | null
  verification_detail?: string
}

export function MemoryRow({
  memory,
  trace,
  expanded,
  focused,
  onToggleTrace,
}: {
  memory: MemoryRowData
  trace?: MemoryTraceView
  expanded?: boolean
  focused?: boolean
  onToggleTrace?: () => void
}) {
  return (
    <div
      id={`memory-row-${memory.id}`}
      className={listItemClass({
        interactive: true,
        className: cn("p-2.5", focused && "ring-primary/60 ring-1"),
      })}
    >
      <div className="flex items-start gap-2.5">
        <div className="flex shrink-0 flex-wrap items-center gap-1.5 pt-0.5">
          <LayerChip layer={memory.layer} />
          <LifecycleBadge status={memory.status} />
          {memory.verification_status && (
            <VerificationBadge
              status={memory.verification_status}
              detail={memory.verification_detail}
            />
          )}
        </div>
        <Link
          to="/memories/$memoryId"
          params={{ memoryId: memory.id }}
          className="hover:text-primary min-w-0 flex-1 text-sm break-words transition-colors"
        >
          <span className="line-clamp-2">{memory.content}</span>
          <span className="text-muted-foreground mt-1 flex flex-wrap items-center gap-1.5">
            {memory.flags?.map((flag) => (
              <Badge
                key={flag}
                variant="outline"
                size="sm"
                className="border-warning/40 text-warning"
              >
                {flag}
              </Badge>
            ))}
            {memory.tags.map((tag) => (
              <Badge key={tag} variant="secondary" size="sm">
                {tag}
              </Badge>
            ))}
          </span>
        </Link>
        <span className="text-muted-foreground shrink-0 pt-0.5 text-right font-mono text-sm">
          {relativeTime(memory.created_at)}
          <span className="block">{memory.source}</span>
        </span>
        {trace && onToggleTrace && (
          <Button
            variant="ghost"
            aria-expanded={expanded}
            aria-label={expanded ? "Hide why retrieved" : "Show why retrieved"}
            className="text-muted-foreground shrink-0"
            onClick={onToggleTrace}
          >
            why?
            <ChevronDown
              aria-hidden
              className={cn(
                "ml-1 h-3.5 w-3.5 transition-transform",
                expanded && "rotate-180",
              )}
            />
          </Button>
        )}
      </div>
      {trace && expanded && (
        <WhyRetrievedTrace
          channels={trace.channels}
          rrfScore={trace.rrfScore}
          summary={trace.summary}
          className="border-border mt-2.5 border-t pt-2.5"
        />
      )}
    </div>
  )
}
