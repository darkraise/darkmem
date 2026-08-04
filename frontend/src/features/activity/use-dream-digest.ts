import { useState } from "react"

import { ApiError } from "@/lib/api"
import {
  useDreamCycleDigest,
  useDreamCycles,
  useUndoDreamAction,
  useUndoDreamCycle,
  type DreamAction,
  type DreamCycleDigest,
  type DreamCycleSummary,
  type DreamObjectGroup,
  type UndoneAction,
} from "@/hooks/api"

export type { DreamAction, DreamCycleDigest, DreamCycleSummary, DreamObjectGroup, UndoneAction }

export interface BlockedReason {
  event_id: number
  action: string
  reason: string
}

/** The three outcomes a dream-digest undo can settle to, carried through
 *  unflattened (app/services/dream_undo.py; doc 08 §7's Events journal
 *  section, "Undo is all-or-nothing"). `refused` is the ONLY one that
 *  guarantees nothing was written — collapsing it with `error` would tell a
 *  user "state unknown" about a request that in fact changed nothing. */
export type UndoOutcome =
  | { kind: "ok"; undoBatchId: string; undone: UndoneAction[] }
  | { kind: "refused"; reasons: BlockedReason[] }
  | { kind: "error"; message: string }

async function settle(
  run: () => Promise<{ undo_batch_id: string; undone: UndoneAction[] }>,
): Promise<UndoOutcome> {
  try {
    const result = await run()
    return { kind: "ok", undoBatchId: result.undo_batch_id, undone: result.undone }
  } catch (err) {
    if (err instanceof ApiError && err.status === 409) {
      return {
        kind: "refused",
        reasons: (err.details ?? []) as BlockedReason[],
      }
    }
    return {
      kind: "error",
      message: err instanceof Error ? err.message : "undo failed",
    }
  }
}

const CYCLE_PAGE = 20

export interface DreamDigestState {
  cycles: DreamCycleSummary[]
  cyclesLoading: boolean
  cyclesError: boolean
  selectedCycleId: string | null
  selectCycle: (cycleId: string) => void
  digest: DreamCycleDigest | null
  digestLoading: boolean
  digestError: boolean
  /** The one action, through the batch-of-one door — no other code path
   *  exists for a single undo. */
  undoAction: (eventId: number) => Promise<UndoOutcome>
  /** A named subset — e.g. every currently-undoable action in one object's
   *  group. Goes through whole: the primitive decides, never a client-side
   *  prefilter that would silently shrink a set the caller named. */
  undoNamed: (eventIds: number[]) => Promise<UndoOutcome>
  /** Body-less: whatever is left of the cycle. */
  undoCycle: () => Promise<UndoOutcome>
}

/**
 * Live-only: there is no demo producer feeding this hook. The demo dream
 * digest (DemoDreamDigest in dream-tab.tsx) renders its own canned narrative
 * — grouped by action *kind*, with richer action types (promote_demote,
 * ratify, invalidate, resynthesize) than the three the real journal ships,
 * and no per-action timestamp or object id to key a real grouping on. Forcing
 * it through this hook's shape would mean either fabricating fields the
 * fixture does not have (a timestamp, an object id) or discarding demo
 * narrative the fixture was written to show — both worse than two render
 * paths. See the T2.38 report for the full reasoning; this is a considered
 * divergence from use-facts.ts's "one row type, two producers" idiom, not an
 * oversight.
 */
export function useDreamDigest(): DreamDigestState {
  const [selected, setSelected] = useState<string | null>(null)
  const cyclesQuery = useDreamCycles({ limit: CYCLE_PAGE })
  const cycles = cyclesQuery.data?.items ?? []
  // Defaults to the most recent cycle once the list loads; a user pick
  // overrides it until cleared.
  const activeCycleId = selected ?? cycles[0]?.cycle_id ?? null

  const digestQuery = useDreamCycleDigest(activeCycleId)
  const actionMutation = useUndoDreamAction()
  const cycleMutation = useUndoDreamCycle()

  const undoCycleRequest = (body?: { event_ids?: number[] }) =>
    activeCycleId
      ? settle(() =>
          cycleMutation.mutateAsync({ cycleId: activeCycleId, body }),
        )
      : Promise.resolve<UndoOutcome>({
          kind: "error",
          message: "no cycle selected",
        })

  return {
    cycles,
    cyclesLoading: cyclesQuery.isLoading,
    cyclesError: cyclesQuery.isError,
    selectedCycleId: activeCycleId,
    selectCycle: setSelected,
    digest: digestQuery.data ?? null,
    digestLoading: digestQuery.isLoading,
    digestError: digestQuery.isError,
    undoAction: (eventId) => settle(() => actionMutation.mutateAsync(eventId)),
    undoNamed: (eventIds) => undoCycleRequest({ event_ids: eventIds }),
    undoCycle: () => undoCycleRequest(undefined),
  }
}
