import { CircleDashed, TriangleAlert } from "lucide-react"
import { EmptyState } from "@/components/darkmem"
import { cn } from "darkraise-ui/lib"
import {
  ExclusionStrip,
  LayerChip,
  VerificationBadge,
  WhyRetrievedTrace,
} from "@/components/darkmem"
import { LifecycleBadge } from "@/features/memories/components/lifecycle-badge"
import { SuppressedBadge } from "@/features/knowledge/components/fact-parts"
import {
  CHAT_EXCLUSION_CAVEAT,
  channelStates,
  exclusionItems,
  factNumbers,
  layerNumber,
  rowTrace,
  type ChatContextFact,
  type ChatContextRow,
  type ChatRetrievalEnvelope,
} from "../lib/retrieval"

export type { ChatContextRow } from "../lib/retrieval"

interface ChatContextPanelProps {
  /**
   * `null` means no turn has produced a context yet. A non-null array
   * (including an empty one) means a turn ran and this is what it
   * retrieved — the honest "populated" state even when nothing came back.
   */
  rows: ChatContextRow[] | null
  /** L2 rows the composition served this turn, with their badges. */
  facts?: ChatContextFact[]
  /** Doc 07 §8's request envelope, once a turn has produced one. */
  envelope?: ChatRetrievalEnvelope | null
}

const STATE_STYLE: Record<string, string> = {
  ok: "text-success",
  failed: "text-warning",
  "not asked": "text-muted-foreground",
}

/**
 * The real counterpart of DemoContextPanel, over the rows a converged chat
 * turn now actually receives (T2.58).
 *
 * Everything here is read off the payload: the channel states, the exclusion
 * counts and the per-row breakdown all come from the retrieval envelope the
 * composition built, and the trace is rendered through the same adapter the
 * Memories surface uses. The panel recomputes no score and writes no second
 * explanation of one ranking — before the convergence there was nothing to
 * read, and the absence was stated here rather than filled in.
 */
export function ChatContextPanel({
  rows,
  facts,
  envelope,
}: ChatContextPanelProps) {
  const populated = rows !== null
  const degraded = populated && envelope?.partial === true
  const channels = channelStates(envelope)
  const exclusions = exclusionItems(envelope)
  const factNumber = factNumbers(facts)

  return (
    // `overflow-y-auto` + `min-h-0`: as a full-height grid column this pane
    // has a bounded height, and a turn that retrieved a dozen rows must scroll
    // inside it rather than stretch the page it no longer owns the height of.
    <div className="border-border bg-card min-h-0 space-y-2.5 overflow-y-auto rounded-md border p-3">
      <div className="flex items-center gap-2">
        <span className="text-sm font-semibold">
          Context used for this turn
        </span>
        <span
          className={cn(
            "ml-auto font-mono text-sm",
            !populated
              ? "text-muted-foreground"
              : degraded
                ? "text-warning"
                : "text-success",
          )}
        >
          {!populated ? "empty" : degraded ? "degraded" : "populated"}
        </span>
      </div>

      {!populated ? (
        <EmptyState
          kind="empty"
          icon={CircleDashed}
          title="No context yet"
          description="Nothing has been asked in this thread — send a message to see the labelled rows it retrieved."
        />
      ) : (
        <>
          {degraded && (
            <div className="border-warning/55 bg-warning/12 flex items-center gap-2 rounded-md border px-2.5 py-1.5 text-sm">
              <TriangleAlert
                aria-hidden
                className="text-warning h-3.5 w-3.5 shrink-0"
              />
              <b className="font-semibold">
                A retrieval channel failed — this answer was built on what
                survived, not on the whole corpus.
              </b>
            </div>
          )}

          {channels.length > 0 && (
            <div className="border-border bg-muted/12 space-y-1 rounded-md border p-2">
              <p className="text-muted-foreground text-sm">
                Channels this turn asked
                {envelope?.reranked ? ", reranked" : ""}
              </p>
              <div className="flex flex-wrap gap-x-3 gap-y-1">
                {channels.map((channel) => (
                  <span key={channel.name} className="font-mono text-sm">
                    {channel.name}{" "}
                    <span className={STATE_STYLE[channel.state]}>
                      {channel.state}
                    </span>
                  </span>
                ))}
              </div>
            </div>
          )}

          {(facts ?? []).map((fact) => (
            <div
              key={fact.id}
              className="border-border bg-background space-y-1.5 rounded-md border p-2.5"
            >
              <div className="flex flex-wrap items-center gap-1.5">
                <LayerChip layer={layerNumber(fact.layer ?? "L2")} />
                {fact.verification_status && (
                  <VerificationBadge
                    status={fact.verification_status}
                    detail={fact.badge?.claim}
                  />
                )}
                {fact.label_suppressed && (
                  <SuppressedBadge reason={fact.label_suppressed} />
                )}
              </div>
              <p className="text-sm">{fact.text}</p>
              {fact.badge && (
                <p className="text-muted-foreground font-mono text-sm">
                  badge —{" "}
                  <b className="text-foreground font-semibold">
                    {fact.badge.claim}
                  </b>
                </p>
              )}
              {(() => {
                const trace = rowTrace(fact)
                return trace ? (
                  <WhyRetrievedTrace
                    channels={trace.channels}
                    rrfScore={trace.rrfScore}
                    summary={trace.summary}
                  />
                ) : null
              })()}
            </div>
          ))}

          {rows.length === 0 && (facts ?? []).length === 0 && (
            <EmptyState
              kind="filtered"
              title="No memories retrieved"
              description="Retrieval ran for this turn and matched nothing. This is an empty result, not a failed search."
            />
          )}

          {rows.map((row, i) => {
            const trace = rowTrace(row)
            return (
              <div
                key={row.id ?? i}
                className="border-border bg-background space-y-1.5 rounded-md border p-2.5"
              >
                <div className="flex flex-wrap items-center gap-1.5">
                  <LayerChip layer={layerNumber(row.layer)} />
                  <LifecycleBadge status={row.status} />
                  {row.grouped_under && (
                    <span className="text-muted-foreground font-mono text-sm">
                      {factNumber.has(row.grouped_under)
                        ? `supports fact F${factNumber.get(row.grouped_under)}`
                        : "supports a fact"}
                    </span>
                  )}
                </div>
                <p className="text-sm">{row.content}</p>
                {row.source && (
                  <p className="text-muted-foreground font-mono text-sm">
                    {row.source}
                  </p>
                )}
                {trace && (
                  <WhyRetrievedTrace
                    channels={trace.channels}
                    rrfScore={trace.rrfScore}
                    summary={trace.summary}
                  />
                )}
              </div>
            )
          })}

          {envelope && (
            <>
              <ExclusionStrip items={exclusions} />
              <p className="text-muted-foreground text-sm">
                {CHAT_EXCLUSION_CAVEAT}
              </p>
            </>
          )}
        </>
      )}
    </div>
  )
}
