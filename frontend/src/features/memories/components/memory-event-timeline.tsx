import { Badge } from "darkraise-ui/components/badge"
import { Skeleton } from "darkraise-ui/components/skeleton"

import { useApiKeys, useEvents, type ApiKeySummary } from "@/hooks/api"

function formatDateTime(iso: string): string {
  return new Date(iso).toLocaleString()
}

/** What a row says about who made the call.
 *
 * Four states, never two: keyed, session, *keyed by a key this box can no
 * longer name*, and *keyed but the key list could not be read*. The third
 * exists because `events.api_key_id` carries no foreign key — a row deleted
 * straight from the database leaves history pointing at nothing — and
 * collapsing it into "session" would attribute a programmatic call to the
 * human. Ordinary revocation is not this case: revoking keeps the row, so a
 * revoked key still names itself here.
 *
 * The fourth was the collapse this docstring already forbade and the code
 * still performed (E4 epic review, M1): on a *failed* key-list read `keys`
 * stays undefined forever, which is indistinguishable from the still-loading
 * case unless the error is threaded in — so a keyed row rendered with no key
 * indication at all, exactly the attribution to the human that the third state
 * exists to prevent.
 */
export interface ActorAttribution {
  actor: string | null
  keyLabel: string | null
  keyRevoked: boolean
  keyUnresolved: boolean
  keyListUnreadable: boolean
}

export function attributeEvent(
  event: { actor: string | null; api_key_id: string | null },
  keys: ApiKeySummary[] | undefined,
  keyListFailed = false,
): ActorAttribution {
  if (!event.api_key_id) {
    return {
      actor: event.actor,
      keyLabel: null,
      keyRevoked: false,
      keyUnresolved: false,
      keyListUnreadable: false,
    }
  }
  const key = keys?.find((candidate) => candidate.id === event.api_key_id)
  if (!key) {
    return {
      actor: event.actor,
      keyLabel: null,
      keyRevoked: false,
      // Undecided while the list is still loading — an unresolved marker shown
      // then would flicker onto every keyed row and read as data loss. A read
      // that *failed* is decided, and says so.
      keyUnresolved: keys !== undefined,
      keyListUnreadable: keys === undefined && keyListFailed,
    }
  }
  return {
    actor: event.actor,
    keyLabel: key.name,
    keyRevoked: key.revoked_at !== null,
    keyUnresolved: false,
    keyListUnreadable: false,
  }
}

function AttributionCell({ attribution }: { attribution: ActorAttribution }) {
  const { actor, keyLabel, keyRevoked, keyUnresolved, keyListUnreadable } =
    attribution
  return (
    <span className="flex flex-wrap items-center gap-1.5">
      {keyLabel !== null ? (
        <>
          <Badge variant="outline" size="sm" className="font-mono">
            key: {keyLabel}
          </Badge>
          {keyRevoked && (
            <span className="text-muted-foreground text-sm">(revoked)</span>
          )}
        </>
      ) : keyUnresolved ? (
        <Badge variant="outline" size="sm" className="font-mono">
          key: no longer listed
        </Badge>
      ) : keyListUnreadable ? (
        <Badge variant="outline" size="sm" className="font-mono">
          key: unknown
        </Badge>
      ) : null}
      {actor ? (
        <span className="text-muted-foreground font-mono text-sm">{actor}</span>
      ) : (
        <span className="text-muted-foreground text-sm italic">
          no actor recorded
        </span>
      )}
    </span>
  )
}

/**
 * One memory's history off the durable `events` substrate (doc 13 §6.4),
 * carrying the key and actor every keyed call stamps (doc 18 §5, T4.02).
 *
 * Reads `GET /events` by object rather than deriving anything from the memory
 * row: the journal is what makes the timeline trustworthy, and a timeline
 * reconstructed from the current row could not show a transition that has
 * since been superseded.
 */
export function MemoryEventTimeline({ memoryId }: { memoryId: string }) {
  const {
    data: events,
    isLoading,
    isError,
  } = useEvents({ object_type: "memory", object_id: memoryId, limit: 50 })
  // Revoked keys included — see `useApiKeys`. Its failure is not this card's
  // failure: an unlabelled key is worse than no card, but a missing card for
  // rows that exist is worse still, so the timeline renders either way.
  const { data: keys, isError: keyListFailed } = useApiKeys()

  if (isLoading) return <Skeleton className="h-24 w-full rounded-md" />

  if (isError) {
    return (
      <p className="text-muted-foreground text-sm">
        The history could not be loaded.
      </p>
    )
  }

  const rows = events?.items ?? []
  if (rows.length === 0) {
    return (
      <p className="text-muted-foreground text-sm italic">
        No events for this memory.
      </p>
    )
  }

  return (
    <div>
      {rows.map((event) => (
        <div
          key={event.id}
          className="border-border flex flex-wrap items-start gap-2.5 border-t border-dashed py-2.5 first:border-t-0 first:pt-0"
        >
          <span className="text-muted-foreground w-44 shrink-0 pt-0.5 font-mono text-sm whitespace-nowrap">
            {formatDateTime(event.created_at)}
          </span>
          <Badge variant="outline" size="sm" className="shrink-0 font-mono">
            {event.event_type}
          </Badge>
          <AttributionCell
            attribution={attributeEvent(event, keys, keyListFailed)}
          />
        </div>
      ))}
      {events && events.total > rows.length && (
        <p className="text-muted-foreground border-border border-t border-dashed pt-2.5 text-sm">
          showing {rows.length} of {events.total}
        </p>
      )}
    </div>
  )
}
