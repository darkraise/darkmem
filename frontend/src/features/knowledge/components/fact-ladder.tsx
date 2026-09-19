import { ScrollText } from "lucide-react"
import { Badge } from "darkraise-ui/components/badge"
import { useDetailLevel, EmptyState, Timestamp } from "@/components/darkmem"
import type { FactLadderEvent } from "@/hooks/api"
import { RungTransition } from "./fact-parts"

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value)
}

/** The one key `before`/`after` both carry, whichever it is — every writer
 *  of this journal shape (`knowledge_triples.py`) records exactly one field
 *  per transition, never a bundle, so "the first key" is the whole payload's
 *  transition, not an arbitrary pick. `sources_changed` and `human_verdict`
 *  carry no `before`/`after` at all and fall through to `null` here — this
 *  reads the shape the payload actually has, it does not assume one. */
function payloadTransition(
  payload: Record<string, unknown>,
): { field: string; from: unknown; to: unknown } | null {
  const before = payload.before
  const after = payload.after
  if (!isRecord(before) || !isRecord(after)) return null
  const field = Object.keys(after)[0]
  if (!field) return null
  return { field, from: before[field] ?? null, to: after[field] }
}

function asDisplayString(value: unknown): string | null {
  if (value === null || value === undefined) return null
  return typeof value === "string" ? value : JSON.stringify(value)
}

function FactLadderRow({ event }: { event: FactLadderEvent }) {
  const advanced = useDetailLevel((s) => s.level) === "advanced"
  const transition = payloadTransition(event.payload)
  const isRungTransition =
    transition?.field === "verification_status" &&
    (transition.to === null || typeof transition.to === "string")

  return (
    <div className="border-border flex flex-wrap items-start gap-2.5 border-t border-dashed py-2.5 first:border-t-0 first:pt-0">
      <span className="text-muted-foreground w-40 shrink-0 pt-0.5 font-mono text-sm">
        <Timestamp iso={event.created_at} />
      </span>
      <div className="min-w-52 flex-1 space-y-1">
        <div className="flex flex-wrap items-center gap-2">
          <Badge variant="outline" size="sm" className="rounded-sm font-mono">
            {event.event_type}
          </Badge>
          {event.actor && (
            <span className="text-muted-foreground text-sm">by {event.actor}</span>
          )}
        </div>
        {isRungTransition && (
          <RungTransition
            from={asDisplayString(transition.from)}
            to={asDisplayString(transition.to) ?? "candidate"}
          />
        )}
        {transition && !isRungTransition && (
          <p className="text-muted-foreground text-sm">
            {transition.field}: {asDisplayString(transition.from) ?? "—"} →{" "}
            {asDisplayString(transition.to) ?? "—"}
          </p>
        )}
        {advanced && (
          <p className="text-muted-foreground font-mono text-xs break-all">
            {JSON.stringify(event.payload)}
          </p>
        )}
      </div>
    </div>
  )
}

/** Every `object_type='fact'` journal row for this id, oldest-to-newest
 *  (`GET /knowledge/facts/{id}`'s `ladder`, T2.86) — the ladder history the
 *  demo store used to fake with prose. Raw event rows, not a narrative: each
 *  row shows what actually changed (`before` → `after` on the one field the
 *  writer recorded), not a description invented to read smoothly. */
export function FactLadderHistory({ events }: { events: FactLadderEvent[] }) {
  if (events.length === 0) {
    return (
      <EmptyState
        kind="empty"
        icon={ScrollText}
        title="No journalled transitions"
        description="Every rung this fact climbs is journalled. It has not moved yet."
      />
    )
  }
  return (
    <div>
      {events.map((event) => (
        <FactLadderRow key={event.id} event={event} />
      ))}
    </div>
  )
}
