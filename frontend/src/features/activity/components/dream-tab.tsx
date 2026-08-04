import { useState } from "react"
import {
  ArrowRight,
  ChevronDown,
  CircleAlert,
  CircleX,
  Link2,
  Lock,
  Pencil,
  RefreshCcw,
  Scale,
  Undo2,
  UserCheck,
  type LucideIcon,
} from "lucide-react"
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "darkraise-ui/components/alert-dialog"
import { Badge } from "darkraise-ui/components/badge"
import { Button } from "darkraise-ui/components/button"
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "darkraise-ui/components/collapsible"
import { EmptyState } from "darkraise-ui/components/empty-state"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "darkraise-ui/components/select"
import { toast } from "darkraise-ui/components/sonner"
import { cn } from "darkraise-ui/lib"
import { LayerChip, useDetailLevel, VerificationBadge } from "@/components/darkmem"
import { dreamActionsOfType, eligibleForUndo } from "@/demo/activity"
import {
  useDemoDreamActions,
  useDemoDreamCycle,
  useDemoDreamPastActions,
} from "@/demo/hooks"
import { useDemoStore } from "@/demo/store"
import type {
  DemoDreamAction,
  DemoDreamGroup,
  DreamActionType,
} from "@/demo/types"
import { DEMO } from "@/lib/demo-flag"
import { relativeTime } from "@/lib/format"
import {
  undoActionLabel as actionLabel,
  undoReasonLabel as reasonLabel,
  useDreamDigest,
  type DreamAction,
  type DreamObjectGroup,
  type UndoOutcome,
} from "../use-dream-digest"
import { SurfaceStateChip } from "./module-surface"

const GROUP_ICONS: Record<DreamActionType, LucideIcon> = {
  supersede: ArrowRight,
  refine: Pencil,
  edge_derive: Link2,
  promote_demote: ArrowRight,
  ratify: UserCheck,
  invalidate: CircleX,
  resynthesize: RefreshCcw,
}

function Transition({ action }: { action: DemoDreamAction }) {
  const t = action.transition
  if (!t) return null
  const pill = (text: string) => (
    <span className="border-border text-muted-foreground rounded-full border border-dashed px-2 py-0.5 font-mono text-sm">
      {text}
    </span>
  )
  return (
    <span className="inline-flex flex-wrap items-center gap-1.5">
      {t.from ? <VerificationBadge status={t.from} /> : pill(t.from_plain ?? "")}
      <ArrowRight aria-hidden className="text-muted-foreground h-3 w-3" />
      {t.to ? (
        <VerificationBadge status={t.to} label={t.to_label} />
      ) : (
        pill(t.to_plain ?? "")
      )}
    </span>
  )
}

function UndoControl({ action }: { action: DemoDreamAction }) {
  const undo = useDemoStore((s) => s.undoDreamAction)
  // Honesty: an action past its undo window renders undo DISABLED with the
  // reason printed inline — never hidden, never a broken button.
  if (action.undo_blocked) {
    return (
      <span className="border-border bg-muted/35 text-muted-foreground ml-auto flex max-w-xs items-start gap-1.5 rounded-md border border-dashed px-2.5 py-1.5 text-[10px] leading-snug">
        <Lock aria-hidden className="mt-0.5 h-3 w-3 shrink-0" />
        <span>
          Undo unavailable —{" "}
          <b className="text-foreground font-semibold">
            {action.undo_blocked.reason}
          </b>
        </span>
      </span>
    )
  }
  if (action.undone) {
    return (
      <span className="text-muted-foreground ml-auto text-sm italic">
        {action.undone_note ?? "undone — journaled"}
      </span>
    )
  }
  // A single action's undo is a low-consequence journaled restore — the
  // outline button commits directly; only the batch confirms via dialog.
  return (
    <Button
      size="sm"
      variant="outline"
      className="ml-auto"
      onClick={() => undo(action.id)}
    >
      <Undo2 className="mr-1.5 size-3.5" />
      {action.undo_label ?? "Undo"}
    </Button>
  )
}

function DreamEntry({ action }: { action: DemoDreamAction }) {
  return (
    <div className="border-border flex flex-wrap items-center gap-2.5 rounded-md border px-2.5 py-2">
      <LayerChip layer={action.layer} />
      <div className="flex min-w-0 flex-1 basis-60 flex-col gap-1">
        <span className="text-sm">{action.title}</span>
        {(action.note ?? action.badge_claim) && (
          <span className="text-muted-foreground text-sm">
            {action.note ?? action.badge_claim}
          </span>
        )}
        <span className="text-muted-foreground font-mono text-sm">
          {action.meta}
        </span>
      </div>
      <Transition action={action} />
      {action.caution_tag && (
        <Badge
          variant="outline"
          size="sm"
          className="border-warning/55 bg-warning/10 text-warning"
        >
          {action.caution_tag}
        </Badge>
      )}
      <UndoControl action={action} />
    </div>
  )
}

function DreamGroup({ group }: { group: DemoDreamGroup }) {
  const actions = useDemoDreamActions()
  const cycle = useDemoDreamCycle()
  const undoBatch = useDemoStore((s) => s.undoDreamBatch)
  const [confirmOpen, setConfirmOpen] = useState(false)

  const entries = dreamActionsOfType(actions, group.type)
  const eligible = eligibleForUndo(entries)
  const excluded = entries.length - eligible.length
  const Icon = GROUP_ICONS[group.type]

  return (
    <div className="border-border bg-card overflow-hidden rounded-lg border">
      <div className="border-border bg-muted/30 flex flex-wrap items-center gap-2.5 border-b px-3.5 py-2.5">
        <span className="border-border bg-muted inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-sm font-semibold">
          <Icon aria-hidden className="h-3.5 w-3.5" />
          {group.label}
        </span>
        <span className="text-muted-foreground font-mono text-sm">
          {group.count_label}
        </span>
        <span className="text-muted-foreground ml-auto text-sm whitespace-nowrap">
          {cycle.undoable_until_label} · {cycle.retention_label}
        </span>
        {group.batchable && (
          <Button
            size="sm"
            variant="outline"
            disabled={eligible.length === 0}
            onClick={() => setConfirmOpen(true)}
          >
            <Undo2 className="mr-1.5 size-3.5" />
            Undo batch ({entries.length})
          </Button>
        )}
      </div>
      <div className="flex flex-col gap-2 p-3.5">
        {group.annotation && (
          <p className="text-muted-foreground text-sm">{group.annotation}</p>
        )}
        {entries.map((action) => (
          <DreamEntry key={action.id} action={action} />
        ))}
        {group.more_note && (
          <span className="text-muted-foreground text-sm italic">
            {group.more_note}
          </span>
        )}
      </div>

      {/* Per-batch undo spans many objects — it gets the AlertDialog; undo
          stays a standard treatment, not destructive-red: every inverse is a
          journaled restore, never a deletion. */}
      <AlertDialog open={confirmOpen} onOpenChange={setConfirmOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Undo this batch?</AlertDialogTitle>
            <AlertDialogDescription>
              This restores {eligible.length} object
              {eligible.length === 1 ? "" : "s"} from cycle #{cycle.id}'s{" "}
              {group.label} group.
              {excluded > 0 &&
                ` ${excluded} entr${excluded === 1 ? "y" : "ies"} in this group ${excluded === 1 ? "is" : "are"} excluded — undo is disabled for ${excluded === 1 ? "it" : "them"} (already undone, or blocked with the reason shown inline).`}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <ul className="text-muted-foreground list-disc pl-5 text-sm">
            {eligible.slice(0, 3).map((a) => (
              <li key={a.id}>{a.title}</li>
            ))}
            {eligible.length > 3 && (
              <li>+{eligible.length - 3} more in this batch</li>
            )}
          </ul>
          <p className="text-muted-foreground border-border border-t border-dashed pt-2 font-mono text-sm">
            journals {eligible.length} undone event
            {eligible.length === 1 ? "" : "s"}, one per restored object ·
            authenticated curation action
          </p>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={() => {
                undoBatch(group.type)
                setConfirmOpen(false)
              }}
            >
              <Undo2 className="mr-1.5 size-3.5" />
              Undo {eligible.length} of {entries.length}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  )
}

/** The canned narrative surface, unchanged from before this task. It has its
 *  own action taxonomy (7 kinds, grouped by kind) and its own optimistic
 *  client-side undo through the demo store — genuinely a different shape
 *  from the real journal (doc 08 §7), not just a different data source. See
 *  `../use-dream-digest.ts`'s module docstring for why this file does not
 *  force the two through one adapter. */
function DemoDreamDigest() {
  const cycle = useDemoDreamCycle()
  const pastActions = useDemoDreamPastActions()
  const [pastOpen, setPastOpen] = useState(false)

  const stats: {
    label: string
    value: number
    split?: string
    caution?: boolean
  }[] = [
    { label: "superseded", value: cycle.summary.superseded },
    { label: "refined", value: cycle.summary.refined },
    {
      label: "promoted / demoted",
      value: cycle.summary.promoted_demoted,
      split: cycle.summary.promoted_split,
    },
    { label: "disputed", value: cycle.summary.disputed, caution: true },
    { label: "edges derived", value: cycle.summary.edges_derived },
  ]

  return (
    <div className="space-y-4">
      <p className="text-muted-foreground max-w-4xl text-sm">
        One consolidation cycle's journaled changes, grouped by object and
        action, with per-action and per-batch undo — tractable because
        consolidation is invalidate-not-delete plus append-only events, so
        every inverse is a status, pointer, or timestamp restore, never a
        resurrection.
      </p>

      <div className="border-border flex flex-wrap items-center gap-2.5 border-b border-dashed pb-3">
        <span className="font-mono text-sm font-semibold">
          cycle #{cycle.id}
        </span>
        <SurfaceStateChip state="populated" />
        <span className="text-muted-foreground font-mono text-sm">
          {cycle.window_label}
        </span>
        <span className="text-muted-foreground ml-auto text-sm">
          {cycle.trigger_label}
        </span>
      </div>

      <div className="grid grid-cols-2 gap-2.5 md:grid-cols-5">
        {stats.map((stat) => (
          <div
            key={stat.label}
            className={cn(
              "border-border flex flex-col gap-0.5 rounded-md border p-2.5",
              stat.caution && "border-warning/50 bg-warning/5",
            )}
          >
            <span
              className={cn(
                "font-mono text-xl font-semibold",
                stat.caution && "text-warning",
              )}
            >
              {stat.value}
            </span>
            <span className="text-muted-foreground text-sm">{stat.label}</span>
            {stat.split && (
              <span className="text-muted-foreground font-mono text-[10px]">
                {stat.split}
              </span>
            )}
          </div>
        ))}
      </div>

      <div className="space-y-3">
        {cycle.groups.map((group) => (
          <DreamGroup key={group.type} group={group} />
        ))}
      </div>

      {cycle.disputed && (
        <div className="border-destructive/45 bg-destructive/5 space-y-2.5 rounded-md border border-dashed p-3">
          <div className="flex flex-wrap items-center gap-2">
            <span className="border-warning/55 bg-warning/10 text-warning inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-sm font-semibold">
              <Scale aria-hidden className="h-3.5 w-3.5" />
              Disputed (surfaced this cycle)
            </span>
            <LayerChip layer={2} />
          </div>
          <p className="text-sm font-semibold">{cycle.disputed.legend}</p>
          <div className="grid grid-cols-1 gap-2 md:grid-cols-[1fr_auto_1fr]">
            <div className="border-border space-y-1.5 rounded-md border p-2.5">
              <VerificationBadge status="disputed" />
              <p className="text-sm">{cycle.disputed.sides[0].assertion}</p>
              <p className="text-muted-foreground text-sm">
                {cycle.disputed.sides[0].origins}
              </p>
            </div>
            <div className="text-muted-foreground flex items-center justify-center font-mono text-sm uppercase">
              vs
            </div>
            <div className="border-border space-y-1.5 rounded-md border p-2.5">
              <VerificationBadge status="disputed" />
              <p className="text-sm">{cycle.disputed.sides[1].assertion}</p>
              <p className="text-muted-foreground text-sm">
                {cycle.disputed.sides[1].origins}
              </p>
            </div>
          </div>
          <p className="text-muted-foreground text-sm">{cycle.disputed.note}</p>
        </div>
      )}

      <Collapsible open={pastOpen} onOpenChange={setPastOpen}>
        <div className="border-border rounded-md border border-dashed">
          <CollapsibleTrigger className="flex w-full items-center gap-2 px-3 py-2.5 text-sm">
            <Lock aria-hidden className="text-muted-foreground h-4 w-4" />
            Earlier cycles — {pastActions.length} actions past their undo
            window (not part of cycle #{cycle.id}'s summary above)
            <ChevronDown
              aria-hidden
              className={cn(
                "text-muted-foreground ml-auto h-4 w-4 transition-transform",
                pastOpen && "rotate-180",
              )}
            />
          </CollapsibleTrigger>
          <CollapsibleContent>
            <div className="border-border space-y-2 border-t border-dashed p-3">
              {pastActions.map((action) => (
                <DreamEntry key={action.id} action={action} />
              ))}
            </div>
          </CollapsibleContent>
        </div>
      </Collapsible>
    </div>
  )
}

// ─────────────────────────────── live surface ───────────────────────────────
// `actionLabel` / `reasonLabel` are `undoActionLabel` / `undoReasonLabel`
// from `use-dream-digest.ts`, aliased on import — hygiene-queue.tsx's undo
// path (the same backend door) shares that single copy (F9).

/** Up to 3 action identities, plus a "+N more" tail — the live surface's
 *  answer to F6: a confirm dialog for a state-mutating batch should name
 *  what it acts on, not just count it, the way the demo predecessor's
 *  `AlertDialog` listed up to 3 titles. `DreamAction` has no title, so this
 *  lists the action kind and the object it touches instead — both real
 *  fields, nothing composed. */
function ActionPreviewList({ actions }: { actions: DreamAction[] }) {
  if (actions.length === 0) return null
  return (
    <ul className="text-muted-foreground list-disc pl-5 text-sm">
      {actions.slice(0, 3).map((a) => (
        <li key={a.event_id} className="font-mono">
          #{a.event_id} {actionLabel(a.action)} · object{" "}
          {a.object_id.slice(0, 8)}
        </li>
      ))}
      {actions.length > 3 && <li>+{actions.length - 3} more</li>}
    </ul>
  )
}

function formatValue(value: unknown): string {
  if (value === undefined) return "—"
  if (value === null) return "null"
  if (typeof value === "string") return value || "—"
  return JSON.stringify(value)
}

/** Every field either side wrote, where the two sides disagree — the literal
 *  "what changed" a dream-digest action must show (Done-when). Pure and
 *  exported so its own behavior — union over both objects' keys, not just
 *  `after`'s — is directly testable without mounting the component. */
export function diffFields(
  before: Record<string, unknown>,
  after: Record<string, unknown>,
): { field: string; from: string; to: string }[] {
  const keys = new Set([...Object.keys(before), ...Object.keys(after)])
  const rows: { field: string; from: string; to: string }[] = []
  for (const key of [...keys].sort()) {
    const a = before[key]
    const b = after[key]
    if (JSON.stringify(a) === JSON.stringify(b)) continue
    rows.push({ field: key, from: formatValue(a), to: formatValue(b) })
  }
  return rows
}

/**
 * Renders exactly the fields the backend returned — no invented summary
 * sentence. Doc 08 §7's `restored` / `not_restored` are already the
 * backend's own account of what changed; this only lays them out, it does
 * not re-word them the way T2.36's `meta` line re-worded `badge.claim` (that
 * review's finding 1 — a second, drifting producer of the same honesty
 * sentence). `refused` and `error` are two different sentences because they
 * are two different guarantees, never collapsed into one.
 */
function reportOutcome(scope: string, outcome: UndoOutcome) {
  if (outcome.kind === "ok") {
    toast.success(`${scope} — undo committed`, {
      description: outcome.undone
        .map(
          (u) =>
            `#${u.event_id} restored: ${u.restored.join(", ") || "—"}` +
            (u.not_restored.length
              ? `; not restored: ${u.not_restored.join(", ")}`
              : ""),
        )
        .join(" · "),
    })
    return
  }
  if (outcome.kind === "refused") {
    // The one outcome that guarantees nothing was written — said plainly,
    // never folded into the generic failure message below.
    toast.error(`${scope} — undo refused, nothing happened`, {
      description:
        outcome.reasons
          .map((r) => `#${r.event_id} ${actionLabel(r.action)}: ${reasonLabel(r.reason)}`)
          .join("; ") || "the door refused before writing anything",
    })
    return
  }
  // Anything other than a 409 may have left restores in the session for the
  // door's own request-scoped session to roll back — this UI cannot promise
  // "nothing happened" here, so it does not.
  toast.error(`${scope} — undo failed, state unknown`, {
    description: `${outcome.message}. The digest was re-read from the server — check it before retrying.`,
  })
}

function LiveActionRow({
  action,
  detailLevel,
  onUndo,
}: {
  action: DreamAction
  detailLevel: "simple" | "advanced"
  onUndo: (eventId: number) => void
}) {
  const changes = diffFields(action.before, action.after)
  return (
    <div className="border-border flex flex-col gap-2 rounded-md border px-2.5 py-2">
      <div className="flex flex-wrap items-center gap-2">
        <Badge variant="outline" size="sm" className="font-mono">
          {actionLabel(action.action)}
        </Badge>
        {action.origin ? (
          <span className="text-muted-foreground font-mono text-sm">
            {action.origin}
            {action.actor ? ` · ${action.actor}` : ""}
          </span>
        ) : action.detector ? (
          <span className="text-muted-foreground font-mono text-sm">
            detector: {action.detector}
          </span>
        ) : null}
        <span className="text-muted-foreground ml-auto font-mono text-sm">
          {relativeTime(action.created_at)}
        </span>
      </div>

      <div className="text-sm">
        {changes.length === 0 ? (
          <span className="text-muted-foreground italic">
            no field-level change captured for this action
          </span>
        ) : (
          <ul className="flex flex-col gap-0.5">
            {changes.map((change) => (
              <li key={change.field} className="font-mono text-sm">
                <span className="text-muted-foreground">{change.field}:</span>{" "}
                {change.from}
                <ArrowRight aria-hidden className="mx-1 inline h-3 w-3" />
                {change.to}
              </li>
            ))}
          </ul>
        )}
      </div>

      {detailLevel === "advanced" && Object.keys(action.detail).length > 0 && (
        <p className="text-muted-foreground font-mono text-[10px]">
          event #{action.event_id} · {JSON.stringify(action.detail)}
        </p>
      )}

      <div className="flex items-center">
        {action.undone ? (
          <span className="text-muted-foreground text-sm italic">
            undone — journaled
            {action.undone_by ? ` by ${action.undone_by}` : ""}
            {action.undone_at ? ` at ${relativeTime(action.undone_at)}` : ""}
            {detailLevel === "advanced" && action.undo_batch_id
              ? ` (batch ${action.undo_batch_id.slice(0, 8)})`
              : ""}
          </span>
        ) : action.undoable ? (
          <Button
            size="sm"
            variant="outline"
            className="ml-auto"
            onClick={() => onUndo(action.event_id)}
          >
            <Undo2 className="mr-1.5 size-3.5" />
            Undo
          </Button>
        ) : (
          <span className="border-border bg-muted/35 text-muted-foreground ml-auto flex max-w-xs items-start gap-1.5 rounded-md border border-dashed px-2.5 py-1.5 text-[10px] leading-snug">
            <Lock aria-hidden className="mt-0.5 h-3 w-3 shrink-0" />
            <span>
              Undo unavailable —{" "}
              <b className="text-foreground font-semibold">
                {reasonLabel(action.undo_blocked_reason)}
              </b>
            </span>
          </span>
        )}
      </div>
    </div>
  )
}

function LiveObjectGroupPanel({
  group,
  detailLevel,
  onUndoAction,
  onUndoGroup,
}: {
  group: DreamObjectGroup
  detailLevel: "simple" | "advanced"
  onUndoAction: (eventId: number) => void
  onUndoGroup: (group: DreamObjectGroup, eligibleActions: DreamAction[]) => void
}) {
  const eligible = group.actions.filter((a) => a.undoable && !a.undone)
  return (
    <div className="border-border bg-card overflow-hidden rounded-lg border">
      <div className="border-border bg-muted/30 flex flex-wrap items-center gap-2.5 border-b px-3.5 py-2.5">
        <span className="border-border bg-muted inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 font-mono text-sm font-semibold">
          object {group.object_id.slice(0, 8)}
        </span>
        {group.project && (
          <span className="text-muted-foreground font-mono text-sm">
            project: {group.project}
          </span>
        )}
        <span className="text-muted-foreground font-mono text-sm">
          {group.actions.length} action{group.actions.length === 1 ? "" : "s"}
        </span>
        <Button
          size="sm"
          variant="outline"
          className="ml-auto"
          disabled={eligible.length === 0}
          onClick={() => onUndoGroup(group, eligible)}
        >
          <Undo2 className="mr-1.5 size-3.5" />
          Undo group ({eligible.length})
        </Button>
      </div>
      <div className="flex flex-col gap-2 p-3.5">
        {group.actions.map((action) => (
          <LiveActionRow
            key={action.event_id}
            action={action}
            detailLevel={detailLevel}
            onUndo={onUndoAction}
          />
        ))}
      </div>
    </div>
  )
}

export function LiveDreamDigest() {
  const level = useDetailLevel((s) => s.level)
  const {
    cycles,
    cyclesLoading,
    cyclesError,
    cyclesTotal,
    cyclesHasMore,
    cyclesFetchingMore,
    fetchMoreCycles,
    selectedCycleId,
    selectCycle,
    digest,
    digestLoading,
    digestError,
    undoAction,
    undoNamed,
  } = useDreamDigest()

  const [confirmGroup, setConfirmGroup] = useState<{
    group: DreamObjectGroup
    actions: DreamAction[]
  } | null>(null)
  const [confirmCycle, setConfirmCycle] = useState(false)

  if (cyclesError) {
    // Invariant 14: a failed read is never rendered as an empty cycle list.
    return (
      <EmptyState
        icon={<CircleAlert aria-hidden className="h-6 w-6" />}
        title="Could not load dream cycles"
        description="The /dream-digest/cycles request failed. This is a failed read, not an empty history — nothing here says whether a cycle ran."
      />
    )
  }
  if (!cyclesLoading && cycles.length === 0) {
    return (
      <EmptyState
        icon={<CircleAlert aria-hidden className="h-6 w-6" />}
        title="No consolidation cycles yet"
        description="No dreaming pass or curation batch has journalled a cycle in this window."
      />
    )
  }

  const activeCycle = cycles.find((c) => c.cycle_id === selectedCycleId)
  const cycleEligible = digest
    ? digest.objects.flatMap((g) => g.actions).filter((a) => a.undoable && !a.undone)
    : []

  return (
    <div className="space-y-4">
      <p className="text-muted-foreground max-w-4xl text-sm">
        One consolidation cycle's journaled changes, grouped by object — the
        journal's own grouping, in the order the actions actually happened —
        with per-action and per-object undo. Undo is a compare-and-swap
        against live state: a request refused with 409 changed nothing, and
        the digest re-reads from the server after every attempt.
      </p>

      <div className="border-border flex flex-wrap items-center gap-2.5 border-b border-dashed pb-3">
        <Select value={selectedCycleId ?? undefined} onValueChange={selectCycle}>
          <SelectTrigger className="w-auto min-w-52 rounded-full" aria-label="Cycle">
            <SelectValue>
              {activeCycle
                ? `cycle #${activeCycle.cycle_id} — ${activeCycle.total} actions`
                : cyclesLoading
                  ? "loading cycles…"
                  : "select a cycle"}
            </SelectValue>
          </SelectTrigger>
          <SelectContent>
            {cycles.map((c) => (
              <SelectItem key={c.cycle_id} value={c.cycle_id}>
                cycle #{c.cycle_id} — {c.total} actions
                {c.origin ? ` · ${c.origin}` : " · automated"}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        {digestError ? (
          // SurfaceState has no error value (module-surface.tsx) — adding one
          // is a cross-surface change (pipeline-tab, jobs-tab already
          // conflate loading with empty the same way) outside this fix's
          // scope, so this chip stays local to the dream tab rather than
          // widening the shared type.
          <span className="border-destructive/50 text-destructive inline-flex items-center gap-1 rounded-full border px-2 py-0.5 font-mono text-[10px] uppercase tracking-wide">
            <CircleAlert aria-hidden className="h-3 w-3" />
            error
          </span>
        ) : (
          <SurfaceStateChip state={digest ? "populated" : "empty"} />
        )}
        {activeCycle && (
          <span className="text-muted-foreground font-mono text-sm">
            {relativeTime(activeCycle.started_at)} –{" "}
            {relativeTime(activeCycle.ended_at)}
          </span>
        )}
        <span className="text-muted-foreground ml-auto font-mono text-sm">
          {cycles.length} of {cyclesTotal} cycles loaded
        </span>
        {cyclesHasMore && (
          <Button
            size="sm"
            variant="outline"
            disabled={cyclesFetchingMore}
            onClick={fetchMoreCycles}
          >
            {cyclesFetchingMore ? "loading…" : "load more cycles"}
          </Button>
        )}
      </div>

      {digestError ? (
        <EmptyState
          icon={<CircleAlert aria-hidden className="h-6 w-6" />}
          title="Could not load this cycle"
          description="The cycle read failed — this is a failed read, not an empty cycle."
        />
      ) : digestLoading || !digest ? (
        <EmptyState
          icon={<CircleAlert aria-hidden className="h-6 w-6 animate-pulse" />}
          title="Loading cycle"
          description="Reading the journal."
        />
      ) : (
        <>
          <div className="grid grid-cols-2 gap-2.5 md:grid-cols-4">
            {Object.entries(digest.counts).map(([action, count]) => (
              <div
                key={action}
                className="border-border flex flex-col gap-0.5 rounded-md border p-2.5"
              >
                <span className="font-mono text-xl font-semibold">{count}</span>
                <span className="text-muted-foreground text-sm">
                  {actionLabel(action)}
                </span>
              </div>
            ))}
            <div className="border-border flex flex-col gap-0.5 rounded-md border p-2.5">
              <span className="font-mono text-xl font-semibold">
                {digest.undone_count}
              </span>
              <span className="text-muted-foreground text-sm">undone</span>
            </div>
          </div>

          <div className="flex justify-end">
            <Button
              size="sm"
              variant="outline"
              disabled={cycleEligible.length === 0}
              onClick={() => setConfirmCycle(true)}
            >
              <Undo2 className="mr-1.5 size-3.5" />
              Undo remaining in cycle ({cycleEligible.length})
            </Button>
          </div>

          <div className="space-y-3">
            {digest.objects.map((group) => (
              <LiveObjectGroupPanel
                key={group.object_id}
                group={group}
                detailLevel={level}
                onUndoAction={async (eventId) =>
                  reportOutcome(`action #${eventId}`, await undoAction(eventId))
                }
                onUndoGroup={(g, actions) => setConfirmGroup({ group: g, actions })}
              />
            ))}
          </div>
        </>
      )}

      <AlertDialog
        open={confirmGroup !== null}
        onOpenChange={(open) => !open && setConfirmGroup(null)}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Undo this object's actions?</AlertDialogTitle>
            <AlertDialogDescription>
              {confirmGroup &&
                `Restores ${confirmGroup.actions.length} action${confirmGroup.actions.length === 1 ? "" : "s"} on object ${confirmGroup.group.object_id.slice(0, 8)}.`}
            </AlertDialogDescription>
          </AlertDialogHeader>
          {confirmGroup && <ActionPreviewList actions={confirmGroup.actions} />}
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={async () => {
                if (!confirmGroup) return
                const { group, actions } = confirmGroup
                setConfirmGroup(null)
                reportOutcome(
                  `object ${group.object_id.slice(0, 8)}`,
                  await undoNamed(actions.map((a) => a.event_id)),
                )
              }}
            >
              <Undo2 className="mr-1.5 size-3.5" />
              Undo
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      <AlertDialog open={confirmCycle} onOpenChange={setConfirmCycle}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Undo the rest of this cycle?</AlertDialogTitle>
            <AlertDialogDescription>
              Restores the {cycleEligible.length} action
              {cycleEligible.length === 1 ? "" : "s"} in cycle #
              {activeCycle?.cycle_id} that {cycleEligible.length === 1 ? "is" : "are"}{" "}
              currently undoable. Actions already undone, or blocked (object
              changed since, or past the undo window), are left untouched
              rather than sent and refused.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <ActionPreviewList actions={cycleEligible} />
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={async () => {
                setConfirmCycle(false)
                reportOutcome(
                  `cycle #${activeCycle?.cycle_id}`,
                  await undoNamed(cycleEligible.map((a) => a.event_id)),
                )
              }}
            >
              <Undo2 className="mr-1.5 size-3.5" />
              Undo {cycleEligible.length}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  )
}

export function DreamTab() {
  return DEMO ? <DemoDreamDigest /> : <LiveDreamDigest />
}
