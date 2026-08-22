import { CircleDashed, TriangleAlert } from "lucide-react"
import { cn } from "darkraise-ui/lib"
import {
  ExclusionStrip,
  LayerChip,
  VerificationBadge,
  WhyRetrievedTrace,
} from "@/components/darkmem"
import type { DemoTurnContext } from "@/demo/types"

// The same composed, labelled rows the Memories why-retrieved trace renders
// (invariant 17) — no chat-only re-derivation of the honesty vocabulary.
export function DemoContextPanel({
  context,
}: {
  context: DemoTurnContext | undefined
}) {
  return (
    <div className="border-border bg-card min-h-0 space-y-2.5 overflow-y-auto rounded-md border p-3">
      <div className="flex items-center gap-2">
        <span className="text-sm font-semibold">
          Context used for this turn
        </span>
        <span
          className={cn(
            "ml-auto font-mono text-sm",
            context
              ? context.degraded
                ? "text-warning"
                : "text-success"
              : "text-muted-foreground",
          )}
        >
          {context ? (context.degraded ? "degraded" : "populated") : "empty"}
        </span>
      </div>

      {!context ? (
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
          {context.degraded && (
            <div className="border-warning/55 bg-warning/12 flex items-center gap-2 rounded-md border px-2.5 py-1.5 text-sm">
              <TriangleAlert
                aria-hidden
                className="text-warning h-3.5 w-3.5 shrink-0"
              />
              <b className="font-semibold">{context.degraded}</b>
            </div>
          )}
          <p className="text-muted-foreground text-sm">
            Same composed, labelled rows the Memories why-retrieved trace
            renders — no chat-only re-derivation.
          </p>
          {context.rows.map((row) => (
            <div
              key={row.id}
              className="border-border bg-background space-y-1.5 rounded-md border p-2.5"
            >
              <div className="flex flex-wrap items-center gap-1.5">
                <LayerChip layer={row.layer} />
                {row.verification && (
                  <VerificationBadge
                    status={row.verification}
                    detail={row.badge_line}
                  />
                )}
                {row.channel && (
                  <span className="text-muted-foreground ml-auto font-mono text-[10px]">
                    channel: {row.channel}
                  </span>
                )}
              </div>
              <p className="text-sm">{row.subject_text}</p>
              <p className="text-muted-foreground font-mono text-sm">
                {row.verification ? "badge — " : ""}
                <b className="text-foreground font-semibold">
                  {row.badge_line}
                </b>
              </p>
              {row.trace && (
                <WhyRetrievedTrace
                  channels={row.trace.channels}
                  rrfScore={row.trace.rrf_score}
                  summary={row.trace.summary}
                />
              )}
            </div>
          ))}
          <ExclusionStrip items={context.exclusions} />
        </>
      )}
    </div>
  )
}
