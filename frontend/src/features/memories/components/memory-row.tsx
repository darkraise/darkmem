import { ChevronDown } from "lucide-react"
import { Badge } from "darkraise-ui/components/badge"
import { Button } from "darkraise-ui/components/button"
import { cn } from "darkraise-ui/lib"
import { relativeTime } from "@/lib/format"
import {
  VerificationBadge,
  WhyRetrievedTrace,
  listItemClass,
  type VerificationStatus,
} from "@/components/darkmem"
import type { MemoryStatus } from "@/hooks/api"
import type { MemoryTraceView } from "../use-memory-search"
import { Link } from "@tanstack/react-router"
import { LifecycleBadge } from "./lifecycle-badge"

// The minimal shape a result row needs to render, shared between the demo
// store's DemoMemory and the real backend's Memory — lifecycle and
// verification always render, whichever source populated them.
export interface MemoryRowData {
  id: string
  content: string
  tags: string[]
  flags?: string[] | null
  source: string
  created_at: string
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
      {/* Below sm the row stacks: badges + content on the first line, the
          time/source/why? metadata on a second line (a single shrink-0 row
          squeezed a badged result's content to one glyph per line at
          390px). From sm up the metadata joins the first line through
          `sm:contents`. */}
      <div className="grid grid-cols-[auto_minmax(0,1fr)] items-start gap-y-1.5 sm:grid-cols-[auto_minmax(0,1fr)_auto_auto] sm:gap-x-2.5">
        <div className="mr-2.5 flex max-w-[7.5rem] flex-col items-start gap-1 pt-0.5 empty:mr-0 sm:mr-0 sm:max-w-none sm:flex-row sm:flex-wrap sm:items-center sm:gap-1.5">
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
          className="hover:text-primary-text focus-visible:ring-ring focus-visible:ring-offset-background min-w-0 rounded-sm text-sm break-words transition-colors focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:outline-none"
        >
          <span className="line-clamp-2">{memory.content}</span>
          <span className="text-muted-foreground mt-1 flex flex-wrap items-center gap-1.5">
            {memory.flags?.map((flag) => (
              <Badge
                key={flag}
                variant="outline"
                size="sm"
                className="border-warning/40 text-warning-text"
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
        <div
          data-testid="memory-row-meta"
          className="col-span-2 flex items-center justify-between gap-2 sm:contents"
        >
          <span className="text-muted-foreground pt-0.5 font-mono text-sm whitespace-nowrap sm:text-right">
            {relativeTime(memory.created_at)}
            <span aria-hidden className="sm:hidden">
              {" · "}
            </span>
            <span className="sm:block">{memory.source}</span>
          </span>
          {trace && onToggleTrace && (
            <Button
              variant="ghost"
              aria-expanded={expanded}
              aria-label={
                expanded ? "Hide why retrieved" : "Show why retrieved"
              }
              className="text-muted-foreground"
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
