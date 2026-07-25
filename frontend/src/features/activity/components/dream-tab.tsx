import { useState } from "react"
import {
  ArrowRight,
  ChevronDown,
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
import { cn } from "darkraise-ui/lib"
import { LayerChip, VerificationBadge } from "@/components/darkmem"
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
        {action.claim && (
          <span className="text-muted-foreground text-sm">{action.claim}</span>
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

export function DreamTab() {
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
          <p className="text-sm font-semibold">{cycle.disputed.claim}</p>
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
