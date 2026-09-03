import { useCallback, useMemo } from "react"

import {
  useBackupDestinations,
  useBackupInventory,
  useSaveBackupDestinations,
  type BackupDestination,
  type DestinationInventory,
} from "@/hooks/api/use-backups-api"
import { useEvents } from "@/hooks/api/use-events-api"
import { useTriggerJob } from "@/hooks/api/use-jobs-api"
import { DEMO } from "@/lib/demo-flag"

export const BACKUP_SHIP_JOB_KEY = "backup_ship"

/** The newest ship outcome for one destination. */
export interface BackupOutcome {
  destination: string
  event_type: "backup_shipped" | "backup_verify_failed"
  at: string
  file: string | null
  sha256: string | null
  error: string | null
}

export interface RunNowResult {
  ok: boolean
  /** Set when the run was refused; `busy` is the 409 a run already in flight
   *  produces, which is a state to report rather than an error to throw. */
  reason: "busy" | "failed" | null
  message: string | null
}

/** Everything the Backups tab reads and writes.
 *
 *  Outcomes come from `GET /events` rather than from a dedicated route: the
 *  ship journals one row per destination per run, and the newest row per
 *  destination is exactly the "last outcome" line the tab renders. A page of
 *  the two event types is enough — nothing here paginates, because the
 *  question is "what happened last", not "what happened ever".
 */
export function useBackupsTabBinding() {
  const destinationsQuery = useBackupDestinations()
  const inventoryQuery = useBackupInventory()
  const saveMutation = useSaveBackupDestinations()
  const triggerJob = useTriggerJob()

  // One query per type: `GET /events` takes a single `event_type`, and two
  // small queries beat a client-side filter over the whole unfiltered feed.
  const shipped = useEvents(
    { event_type: "backup_shipped", limit: 50 },
    { enabled: !DEMO },
  )
  const failed = useEvents(
    { event_type: "backup_verify_failed", limit: 50 },
    { enabled: !DEMO },
  )

  const destinations = useMemo(
    () => destinationsQuery.data?.destinations ?? [],
    [destinationsQuery.data],
  )

  const recentOutcomes = useMemo(() => {
    const rows = [...(shipped.data?.items ?? []), ...(failed.data?.items ?? [])]
    const newest = new Map<string, BackupOutcome>()
    for (const row of rows) {
      const payload = row.payload as Record<string, unknown>
      const destination = String(payload.destination ?? "")
      if (!destination) continue
      const previous = newest.get(destination)
      if (previous && previous.at >= row.created_at) continue
      newest.set(destination, {
        destination,
        event_type: row.event_type as BackupOutcome["event_type"],
        at: row.created_at,
        file: (payload.file as string) ?? null,
        sha256: (payload.sha256 as string) ?? null,
        error:
          (payload.error as string) ??
          (payload.got
            ? `read-back mismatch: expected ${payload.expected}, got ${payload.got}`
            : null),
      })
    }
    return newest
  }, [shipped.data, failed.data])

  const save = useCallback(
    async (next: BackupDestination[]) => saveMutation.mutateAsync(next),
    [saveMutation],
  )

  const runNow = useCallback(async (): Promise<RunNowResult> => {
    try {
      await triggerJob.mutateAsync(BACKUP_SHIP_JOB_KEY)
      return { ok: true, reason: null, message: null }
    } catch (error) {
      // A 409 means a run already holds the job's lock. That is a state the
      // operator should see, not an exception the tab should throw on — the
      // ship they asked for is already happening.
      const message = error instanceof Error ? error.message : String(error)
      const busy = /409/.test(message) || /busy/i.test(message)
      return {
        ok: false,
        reason: busy ? "busy" : "failed",
        message: busy ? "A backup run is already in progress." : message,
      }
    }
  }, [triggerJob])

  return {
    destinations,
    inventory: (inventoryQuery.data?.destinations ?? []) as DestinationInventory[],
    inventoryLoading: DEMO ? false : inventoryQuery.isLoading,
    recentOutcomes,
    save,
    runNow,
    isLoading: DEMO ? false : destinationsQuery.isLoading,
    isError: DEMO ? false : destinationsQuery.isError,
    isSaving: saveMutation.isPending,
    isRunning: triggerJob.isPending,
    saveError: saveMutation.error,
  }
}
