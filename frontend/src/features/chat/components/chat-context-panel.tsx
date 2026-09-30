import { CircleDashed, TriangleAlert } from "lucide-react"
import { EmptyState } from "@/components/darkmem"
import {
  ExclusionStrip,
  LayerChip,
  VerificationBadge,
  WhyRetrievedTrace,
} from "@/components/darkmem"
import { LifecycleBadge } from "@/features/memories/components/lifecycle-badge"
import { SuppressedBadge } from "@/features/knowledge/components/fact-parts"
import {
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
  const failedChannels = channelStates(envelope)
    .filter((channel) => channel.state === "failed")
    .map((channel) => channel.name.replace(/[._]/g, " "))
  const exclusions = exclusionItems(envelope)
  const factNumber = factNumbers(facts)

  return (
    // `overflow-y-auto` + `min-h-0`: as a full-height grid column this pane
    // has a bounded height, and a turn that retrieved a dozen rows must scroll
    // inside it rather than stretch the page it no longer owns the height of.
    <div className="border-border bg-card min-h-0 space-y-2.5 overflow-y-auto rounded-md border p-3 lg:rounded-none lg:border-0 lg:bg-transparent">
      <div className="flex items-center gap-2">
        <span className="text-sm font-semibold">
          Context used for this turn
        </span>
        {degraded && (
          <span className="text-warning-text ml-auto font-mono text-sm">
            degraded
          </span>
        )}
      </div>

      {!populated ? (
        <EmptyState
          kind="empty"
          icon={CircleDashed}
          title="No context yet"
          description="Send a message to see what it retrieves."
        />
      ) : (
        <>
          {degraded && (
            <div className="border-warning/55 bg-warning/12 flex items-center gap-2 rounded-md border px-2.5 py-1.5 text-sm">
              <TriangleAlert
                aria-hidden
                className="text-warning-text h-3.5 w-3.5 shrink-0"
              />
              <b className="font-semibold">
                {failedChannels.length > 0
                  ? `${failedChannels.join(", ")} search failed, so this answer may be incomplete.`
                  : "A retrieval channel failed, so this answer may be incomplete."}
              </b>
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
              {fact.badge && fact.verification_status === "disputed" && (
                <p className="text-muted-foreground font-mono text-sm">
                  {fact.badge.claim}
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
              description="Nothing matched this message."
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

          {envelope && <ExclusionStrip items={exclusions} />}
        </>
      )}
    </div>
  )
}
