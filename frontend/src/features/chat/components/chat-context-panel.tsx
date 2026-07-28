import { CircleDashed } from "lucide-react"
import { cn } from "darkraise-ui/lib"
import { LayerChip } from "@/components/darkmem"
import { LifecycleBadge } from "@/features/memories/components/lifecycle-badge"
import type { MemoryStatus } from "@/hooks/api"

export interface ChatContextRow {
  id?: string
  content?: string
  source?: string
  status?: MemoryStatus
  project?: string
}

interface ChatContextPanelProps {
  /**
   * `null` means no turn has produced a context yet. A non-null array
   * (including an empty one) means a turn ran and this is what it
   * retrieved — the honest "populated" state even when nothing came back.
   */
  rows: ChatContextRow[] | null
}

/**
 * The real counterpart of DemoContextPanel (T1.60, Step 8) — same
 * populated/empty header contract and per-row card shape, built over real
 * retrieval data instead of the demo fixture. No VerificationBadge, no
 * WhyRetrievedTrace: chat's retrieval carries no RetrievalEnvelope or
 * numeric verification ladder today (§1's exclusion) — the absence is
 * stated below, not silently omitted. `degraded` has no source today
 * (chat's retrieval swallows channel failures into empty lists with a
 * server-side log, not a surfaced flag) so this panel never fabricates one.
 */
export function ChatContextPanel({ rows }: ChatContextPanelProps) {
  const populated = rows !== null

  return (
    <div className="border-border bg-card space-y-2.5 rounded-md border p-3">
      <div className="flex items-center gap-2">
        <span className="text-sm font-semibold">
          Context used for this turn
        </span>
        <span
          className={cn(
            "ml-auto font-mono text-sm",
            populated ? "text-success" : "text-muted-foreground",
          )}
        >
          {populated ? "populated" : "empty"}
        </span>
      </div>

      {!populated ? (
        <div className="border-border bg-muted/12 flex flex-col items-center gap-1.5 rounded-md border border-dashed p-5 text-center">
          <CircleDashed
            aria-hidden
            className="text-muted-foreground h-4.5 w-4.5"
          />
          <p className="text-sm font-semibold">No context yet</p>
          <p className="text-muted-foreground text-sm">
            Nothing has been asked in this thread — send a message to see the
            labelled rows it retrieved.
          </p>
        </div>
      ) : (
        <>
          <p className="text-muted-foreground text-sm">
            L0 memories — no verification ladder applies yet.
          </p>
          {rows.length === 0 && (
            <p className="text-muted-foreground text-sm">
              No memories were retrieved for this turn.
            </p>
          )}
          {rows.map((row, i) => (
            <div
              key={row.id ?? i}
              className="border-border bg-background space-y-1.5 rounded-md border p-2.5"
            >
              <div className="flex flex-wrap items-center gap-1.5">
                <LayerChip layer={0} />
                <LifecycleBadge status={row.status} />
              </div>
              <p className="text-sm">{row.content}</p>
              {row.source && (
                <p className="text-muted-foreground font-mono text-sm">
                  {row.source}
                </p>
              )}
            </div>
          ))}
        </>
      )}
    </div>
  )
}
