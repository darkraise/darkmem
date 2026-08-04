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

/** `error.details` on a dream-digest 409 is asserted structurally
 *  (`app/schemas/dream_digest.py::BlockedAction`) but carries no generated
 *  type on either side of the wire — a blind cast would render
 *  `#undefined undefined: undefined` in the refusal toast the moment the
 *  backend shape drifts. Malformed entries are dropped rather than trusted;
 *  `reportOutcome`'s own fallback ("the door refused before writing
 *  anything") is what a caller sees if every entry fails this check, which
 *  is honest even though it is not the withheld reason. */
function isBlockedReason(value: unknown): value is BlockedReason {
  if (typeof value !== "object" || value === null) return false
  const v = value as Record<string, unknown>
  return (
    typeof v.event_id === "number" &&
    typeof v.action === "string" &&
    typeof v.reason === "string"
  )
}

function parseBlockedReasons(details: unknown[] | undefined): BlockedReason[] {
  return (details ?? []).filter(isBlockedReason)
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
        reasons: parseBlockedReasons(err.details),
      }
    }
    return {
      kind: "error",
      message: err instanceof Error ? err.message : "undo failed",
    }
  }
}

export interface DreamDigestState {
  cycles: DreamCycleSummary[]
  cyclesLoading: boolean
  cyclesError: boolean
  /** How many cycles the server actually holds behind the (unset) project
   *  filter — the denominator `cycles.length` must be read against so the
   *  picker cannot imply completeness past its own page. 0 before the first
   *  page resolves. */
  cyclesTotal: number
  /** True while more cycles than `cycles.length` remain unfetched. */
  cyclesHasMore: boolean
  cyclesFetchingMore: boolean
  fetchMoreCycles: () => void
  selectedCycleId: string | null
  selectCycle: (cycleId: string) => void
  digest: DreamCycleDigest | null
  digestLoading: boolean
  digestError: boolean
  /** The one action, through the batch-of-one door — no other code path
   *  exists for a single undo. */
  undoAction: (eventId: number) => Promise<UndoOutcome>
  /** A named subset — e.g. every currently-undoable action in one object's
   *  group, or every currently-undoable action left in the cycle. Goes
   *  through whole: the primitive decides, never a client-side prefilter
   *  that would silently shrink a set the caller named.
   *
   *  This is also how a whole-cycle undo is requested (T2.38 fix round 1,
   *  F1): the body-less form of `POST /cycles/{id}/undo` selects **every**
   *  not-yet-undone action, including ones blocked by `state_changed` or a
   *  missing object, and one blocked action refuses the entire batch
   *  (`dream_undo.py`). A confirm dialog that counts only the currently
   *  undoable ones and then fires the body-less form promises a set the
   *  door does not select — naming exactly that set instead makes the
   *  dialog's promise the request, and a blocked action simply is not part
   *  of what was asked for rather than a reason the whole undo refuses. */
  undoNamed: (eventIds: number[]) => Promise<UndoOutcome>
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
  const cyclesQuery = useDreamCycles()
  const cyclePages = cyclesQuery.data?.pages ?? []
  const cycles = cyclePages.flatMap((page) => page.items)
  // Every page's `total` is the same server count behind the same filter;
  // the last page is the freshest read of it.
  const cyclesTotal = cyclePages[cyclePages.length - 1]?.total ?? 0
  // Defaults to the most recent cycle once the list loads; a user pick
  // overrides it until cleared.
  const activeCycleId = selected ?? cycles[0]?.cycle_id ?? null

  const digestQuery = useDreamCycleDigest(activeCycleId)
  const actionMutation = useUndoDreamAction()
  const cycleMutation = useUndoDreamCycle()

  const undoNamed = (eventIds: number[]) =>
    activeCycleId
      ? settle(() =>
          cycleMutation.mutateAsync({
            cycleId: activeCycleId,
            body: { event_ids: eventIds },
          }),
        )
      : Promise.resolve<UndoOutcome>({
          kind: "error",
          message: "no cycle selected",
        })

  return {
    cycles,
    cyclesLoading: cyclesQuery.isLoading,
    cyclesError: cyclesQuery.isError,
    cyclesTotal,
    cyclesHasMore: cyclesQuery.hasNextPage ?? false,
    cyclesFetchingMore: cyclesQuery.isFetchingNextPage,
    fetchMoreCycles: () => {
      if (cyclesQuery.hasNextPage && !cyclesQuery.isFetchingNextPage) {
        void cyclesQuery.fetchNextPage()
      }
    },
    selectedCycleId: activeCycleId,
    selectCycle: setSelected,
    digest: digestQuery.data ?? null,
    digestLoading: digestQuery.isLoading,
    digestError: digestQuery.isError,
    undoAction: (eventId) => settle(() => actionMutation.mutateAsync(eventId)),
    undoNamed,
  }
}
