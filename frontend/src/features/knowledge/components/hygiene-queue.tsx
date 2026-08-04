import { useEffect, useState, type ReactNode } from "react"
import { Link } from "@tanstack/react-router"
import {
  Check,
  ChevronLeft,
  ChevronRight,
  Clock,
  Copy,
  GitBranch,
  Loader2,
  RotateCcw,
  SearchX,
  Trash2,
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
import { Checkbox } from "darkraise-ui/components/checkbox"
import { LayerChip, useDetailLevel } from "@/components/darkmem"
import { DEMO } from "@/lib/demo-flag"
import { useDemoStore } from "@/demo/store"
import {
  useBulkConfirmDedup,
  useBulkPrune,
  useUndoCycle,
  type HygieneBulkActionResponse,
} from "@/hooks/api"
import { LifecycleBadge } from "@/features/memories/components/lifecycle-badge"
import {
  useHygieneCountsRows,
  useHygieneDuplicateRows,
  useHygieneExpiringRows,
  useHygieneLowConfidenceRows,
  useHygieneSupersededRows,
  type HygieneDuplicateRowData,
  type HygieneMemoryRowData,
} from "../use-hygiene-queue"

const PAGE = 10

function useSelection() {
  const [selected, setSelected] = useState<ReadonlySet<string>>(new Set())
  const toggle = (id: string) =>
    setSelected((prev) => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  const clear = () => setSelected(new Set())
  return { selected, toggle, clear }
}

function SelectionCount({ n, unit }: { n: number; unit: string }) {
  return (
    <span className="text-muted-foreground font-mono text-sm">
      {n} {unit}
      {n === 1 ? "" : "s"} selected
    </span>
  )
}

function PageControls({
  offset,
  limit,
  total,
  onPrev,
  onNext,
}: {
  offset: number
  limit: number
  total: number
  onPrev: () => void
  onNext: () => void
}) {
  if (total <= limit) return null
  return (
    <div className="flex items-center justify-end gap-2 pt-1">
      <span className="text-muted-foreground font-mono text-sm">
        {Math.min(offset + 1, total)}–{Math.min(offset + limit, total)} of {total}
      </span>
      <Button size="sm" variant="outline" disabled={offset === 0} onClick={onPrev}>
        <ChevronLeft className="size-3.5" />
      </Button>
      <Button
        size="sm"
        variant="outline"
        disabled={offset + limit >= total}
        onClick={onNext}
      >
        <ChevronRight className="size-3.5" />
      </Button>
    </div>
  )
}

/** After a bulk action lands, this is the batch's real undo affordance —
 *  `POST /dream-digest/cycles/{cycle_id}/undo`, the same door the automated
 *  dreaming jobs use, not a new one invented for this surface. Not shown at
 *  all once the batch has been undone. */
function ActionNotice({
  result,
  onUndo,
  undoing,
  undone,
}: {
  result: HygieneBulkActionResponse
  onUndo: () => void
  undoing: boolean
  undone: boolean
}) {
  const applied = result.results.filter((r) => r.applied).length
  const refused = result.results.length - applied
  return (
    <div className="border-success/40 bg-success/5 flex flex-wrap items-center gap-2 rounded-md border border-dashed p-2 text-sm">
      <Check aria-hidden className="text-success h-3.5 w-3.5 shrink-0" />
      <span>
        {applied} applied{refused > 0 ? `, ${refused} refused` : ""} — cycle{" "}
        <span className="font-mono">{result.cycle_id}</span>
      </span>
      {undone ? (
        <span className="text-muted-foreground ml-auto font-mono">undone</span>
      ) : (
        <Button
          size="sm"
          variant="outline"
          className="ml-auto"
          disabled={undoing || applied === 0}
          onClick={onUndo}
        >
          <RotateCcw className="mr-1.5 size-3.5" />
          {undoing ? "Undoing…" : "Undo this batch"}
        </Button>
      )}
    </div>
  )
}

function CategoryShell({
  icon,
  title,
  meta,
  toolbar,
  isEmpty,
  isError,
  isLoading,
  emptyLine,
  errorLine,
  children,
}: {
  icon: ReactNode
  title: string
  meta: string
  toolbar?: ReactNode
  isEmpty: boolean
  isError: boolean
  isLoading: boolean
  emptyLine: string
  errorLine: string
  children: ReactNode
}) {
  return (
    <div className="border-border bg-card overflow-hidden rounded-lg border">
      <div className="border-border bg-muted/30 flex flex-wrap items-center gap-2.5 border-b px-4 py-2.5">
        <span className="text-muted-foreground [&>svg]:h-4 [&>svg]:w-4">{icon}</span>
        <span className="text-sm font-semibold">{title}</span>
        <span className="text-muted-foreground font-mono text-sm">{meta}</span>
        {toolbar && <div className="ml-auto flex flex-wrap items-center gap-2">{toolbar}</div>}
      </div>
      <div className="flex flex-col gap-2.5 p-4">
        {isError ? (
          <p className="text-destructive flex items-center gap-2 text-sm">
            <SearchX aria-hidden className="h-3.5 w-3.5 shrink-0" />
            {errorLine}
          </p>
        ) : isLoading ? (
          <p className="text-muted-foreground flex items-center gap-2 text-sm">
            <Loader2 aria-hidden className="h-3.5 w-3.5 shrink-0 animate-spin" />
            loading…
          </p>
        ) : isEmpty ? (
          <p className="text-muted-foreground flex items-center gap-2 text-sm">
            <Check aria-hidden className="text-success h-3.5 w-3.5 shrink-0" />
            {emptyLine}
          </p>
        ) : (
          children
        )}
      </div>
    </div>
  )
}

function shortId(id: string): string {
  return id.slice(0, 8)
}

function DuplicateRow({
  row,
  selected,
  onToggle,
}: {
  row: HygieneDuplicateRowData
  selected: boolean
  onToggle: () => void
}) {
  const level = useDetailLevel((s) => s.level)
  return (
    <div className="border-border space-y-1.5 rounded-md border border-dashed p-2.5">
      <div className="flex items-center gap-2.5">
        <Checkbox
          size="sm"
          checked={selected}
          onCheckedChange={onToggle}
          aria-label={`Select duplicate pair ${row.id}`}
        />
        {level === "advanced" && row.verdict && (
          <span className="text-muted-foreground font-mono text-sm">{row.verdict}</span>
        )}
        {level === "advanced" && row.score != null && (
          <Badge variant="outline" size="sm" className="font-mono">
            score {row.score.toFixed(2)}
          </Badge>
        )}
        {level === "advanced" && row.hygiene_state && (
          <Badge variant="outline" size="sm" className="font-mono">
            state: {row.hygiene_state}
          </Badge>
        )}
      </div>
      <div className="flex flex-wrap items-center gap-2 pl-6">
        <LayerChip layer={0} />
        <Link
          to="/memories/$memoryId"
          params={{ memoryId: row.source_memory_id }}
          className="hover:text-primary font-mono text-sm transition-colors"
        >
          {shortId(row.source_memory_id)}
        </Link>
        <span className="text-muted-foreground text-sm">↔</span>
        <Link
          to="/memories/$memoryId"
          params={{ memoryId: row.target_memory_id }}
          className="hover:text-primary font-mono text-sm transition-colors"
        >
          {shortId(row.target_memory_id)}
        </Link>
        <Badge variant="outline" size="sm" className="rounded-sm font-mono">
          {row.rel_type}
        </Badge>
      </div>
      {level === "advanced" && (
        <p className="text-muted-foreground pl-6 font-mono text-sm">
          project {row.project}
          {row.detected_at && ` · detected_at ${row.detected_at}`} · created_at{" "}
          {row.created_at}
        </p>
      )}
    </div>
  )
}

function MemoryRowLine({ row }: { row: HygieneMemoryRowData; lead?: ReactNode }) {
  const level = useDetailLevel((s) => s.level)
  return (
    <span className="min-w-52 flex-1 space-y-0.5">
      <span className="flex flex-wrap items-center gap-1.5">
        <span className="text-sm">{row.content_preview || "(no content preview)"}</span>
        <Badge variant="outline" size="sm" className="font-mono">
          {row.reason}
        </Badge>
      </span>
      {level === "advanced" && (
        <span className="text-muted-foreground block font-mono text-sm">
          project {row.project} · confidence {row.confidence ?? "—"}
          {row.expires_at && ` · expires_at ${row.expires_at}`}
          {row.superseded_by && ` · superseded_by ${shortId(row.superseded_by)}`}
          {" · created_at "}
          {row.created_at}
        </span>
      )}
    </span>
  )
}

function MemoryRow({
  row,
  lead,
}: {
  row: HygieneMemoryRowData
  lead?: ReactNode
}) {
  return (
    <div className="border-border flex flex-wrap items-start gap-2.5 rounded-md border p-2">
      {lead}
      {row.status === "superseded" ? (
        <LifecycleBadge status="superseded" className="mt-0.5 shrink-0" />
      ) : (
        <LayerChip layer={0} className="mt-0.5 shrink-0" />
      )}
      <MemoryRowLine row={row} />
      <Link
        to="/memories/$memoryId"
        params={{ memoryId: row.id }}
        className="text-muted-foreground hover:text-primary ml-auto shrink-0 font-mono text-sm transition-colors"
      >
        {shortId(row.id)}
      </Link>
    </div>
  )
}

type PendingAction =
  | { kind: "confirm-dedup"; ids: string[] }
  | { kind: "prune-low"; ids: string[] }
  | { kind: "prune-expiring"; ids: string[] }
  | null

// Housekeeping is consequence-ranked in ambition (doc 08 §6) but ships
// recency-ordered here — T2.23's own reported gap, see the report — and is
// served-labelled, never a gate: sitting in this queue changes nothing about
// how a row serves.
export function HygieneQueue({ project }: { project?: string }) {
  const [dupOffset, setDupOffset] = useState(0)
  const [lowOffset, setLowOffset] = useState(0)
  const [expOffset, setExpOffset] = useState(0)
  const [supOffset, setSupOffset] = useState(0)

  useEffect(() => {
    setDupOffset(0)
    setLowOffset(0)
    setExpOffset(0)
    setSupOffset(0)
  }, [project])

  const dupSel = useSelection()
  const lowSel = useSelection()
  const expSel = useSelection()

  const counts = useHygieneCountsRows({ project })
  const duplicates = useHygieneDuplicateRows({ project, limit: PAGE, offset: dupOffset })
  const lowConfidence = useHygieneLowConfidenceRows({ project, limit: PAGE, offset: lowOffset })
  const expiring = useHygieneExpiringRows({ project, limit: PAGE, offset: expOffset })
  const superseded = useHygieneSupersededRows({ project, limit: PAGE, offset: supOffset })

  const confirmDedup = useBulkConfirmDedup()
  const bulkPrune = useBulkPrune()
  const undoCycle = useUndoCycle()
  const demoResolve = useDemoStore((s) => s.resolveHygiene)

  const [pending, setPending] = useState<PendingAction>(null)
  const [notices, setNotices] = useState<
    Partial<Record<"duplicates" | "lowConfidence" | "expiring", HygieneBulkActionResponse>>
  >({})
  const [undone, setUndone] = useState<Partial<Record<"duplicates" | "lowConfidence" | "expiring", boolean>>>(
    {},
  )
  const [undoingArm, setUndoingArm] = useState<string | null>(null)

  const applyPending = () => {
    if (!pending) return
    if (DEMO) {
      const category =
        pending.kind === "confirm-dedup"
          ? "duplicates"
          : pending.kind === "prune-low"
            ? "lowConfidence"
            : "expiring"
      demoResolve(category, pending.ids)
      setPending(null)
      return
    }
    if (pending.kind === "confirm-dedup") {
      confirmDedup.mutate(pending.ids, {
        onSuccess: (result) => {
          setNotices((prev) => ({ ...prev, duplicates: result }))
          setUndone((prev) => ({ ...prev, duplicates: false }))
          dupSel.clear()
        },
      })
    } else if (pending.kind === "prune-low") {
      bulkPrune.mutate(pending.ids, {
        onSuccess: (result) => {
          setNotices((prev) => ({ ...prev, lowConfidence: result }))
          setUndone((prev) => ({ ...prev, lowConfidence: false }))
          lowSel.clear()
        },
      })
    } else {
      bulkPrune.mutate(pending.ids, {
        onSuccess: (result) => {
          setNotices((prev) => ({ ...prev, expiring: result }))
          setUndone((prev) => ({ ...prev, expiring: false }))
          expSel.clear()
        },
      })
    }
    setPending(null)
  }

  const runUndo = (arm: "duplicates" | "lowConfidence" | "expiring") => {
    const notice = notices[arm]
    if (!notice) return
    setUndoingArm(arm)
    undoCycle.mutate(notice.cycle_id, {
      onSuccess: () => {
        setUndone((prev) => ({ ...prev, [arm]: true }))
        setUndoingArm(null)
      },
      onError: () => setUndoingArm(null),
    })
  }

  const countsLine = counts.error
    ? "counts unavailable"
    : `${counts.duplicates} duplicate pair${counts.duplicates === 1 ? "" : "s"} · ${
        counts.low_confidence
      } low-confidence · ${counts.expiring_soon} expiring soon · ${counts.superseded} superseded`

  return (
    <div className="space-y-3">
      <div className="border-border bg-muted/15 text-muted-foreground rounded-md border border-dashed px-2.5 py-1.5 text-sm">
        Housekeeping over L0 memories — distinct from the Review queue's
        truth adjudication over facts and articles.{" "}
        <span className="font-mono">{countsLine}</span>
      </div>

      <CategoryShell
        icon={<Copy aria-hidden />}
        title="Candidate duplicates"
        meta="from dreaming"
        isEmpty={duplicates.rows.length === 0}
        isError={duplicates.error}
        isLoading={duplicates.loading && duplicates.rows.length === 0}
        emptyLine="Candidate duplicates — none flagged by the last dream cycle"
        errorLine="Could not load candidate duplicates — this is a failed read, not zero pairs"
        toolbar={
          <>
            <SelectionCount n={dupSel.selected.size} unit="pair" />
            <Button
              size="sm"
              disabled={dupSel.selected.size === 0}
              onClick={() => setPending({ kind: "confirm-dedup", ids: [...dupSel.selected] })}
            >
              <Copy className="mr-1.5 size-3.5" />
              Confirm dedup
            </Button>
          </>
        }
      >
        {notices.duplicates && (
          <ActionNotice
            result={notices.duplicates}
            onUndo={() => runUndo("duplicates")}
            undoing={undoingArm === "duplicates"}
            undone={Boolean(undone.duplicates)}
          />
        )}
        {duplicates.rows.map((row) => (
          <DuplicateRow
            key={row.id}
            row={row}
            selected={dupSel.selected.has(row.id)}
            onToggle={() => dupSel.toggle(row.id)}
          />
        ))}
        <PageControls
          offset={dupOffset}
          limit={PAGE}
          total={duplicates.total}
          onPrev={() => setDupOffset((o) => Math.max(0, o - PAGE))}
          onNext={() => setDupOffset((o) => o + PAGE)}
        />
      </CategoryShell>

      <CategoryShell
        icon={<Clock aria-hidden />}
        title="Low-confidence memories"
        meta=""
        isEmpty={lowConfidence.rows.length === 0}
        isError={lowConfidence.error}
        isLoading={lowConfidence.loading && lowConfidence.rows.length === 0}
        emptyLine="Low-confidence memories — none below the review threshold"
        errorLine="Could not load low-confidence memories — this is a failed read, not zero rows"
        toolbar={
          <>
            <SelectionCount n={lowSel.selected.size} unit="row" />
            <Button
              size="sm"
              variant="outline"
              className="border-destructive/55 text-destructive"
              disabled={lowSel.selected.size === 0}
              onClick={() => setPending({ kind: "prune-low", ids: [...lowSel.selected] })}
            >
              <Trash2 className="mr-1.5 size-3.5" />
              Prune
            </Button>
          </>
        }
      >
        {notices.lowConfidence && (
          <ActionNotice
            result={notices.lowConfidence}
            onUndo={() => runUndo("lowConfidence")}
            undoing={undoingArm === "lowConfidence"}
            undone={Boolean(undone.lowConfidence)}
          />
        )}
        {lowConfidence.rows.map((row) => (
          <MemoryRow
            key={row.id}
            row={row}
            lead={
              <Checkbox
                size="sm"
                checked={lowSel.selected.has(row.id)}
                onCheckedChange={() => lowSel.toggle(row.id)}
                aria-label={`Select ${row.content_preview.slice(0, 40)}`}
              />
            }
          />
        ))}
        <PageControls
          offset={lowOffset}
          limit={PAGE}
          total={lowConfidence.total}
          onPrev={() => setLowOffset((o) => Math.max(0, o - PAGE))}
          onNext={() => setLowOffset((o) => o + PAGE)}
        />
      </CategoryShell>

      <CategoryShell
        icon={<Clock aria-hidden />}
        title="Expiring soon"
        meta="expires_at approaching"
        isEmpty={expiring.rows.length === 0}
        isError={expiring.error}
        isLoading={expiring.loading && expiring.rows.length === 0}
        emptyLine="Expiring soon — no rows with expires_at inside the lookahead window"
        errorLine="Could not load expiring memories — this is a failed read, not zero rows"
        toolbar={
          <>
            <SelectionCount n={expSel.selected.size} unit="row" />
            <Button
              size="sm"
              variant="outline"
              className="border-destructive/55 text-destructive"
              disabled={expSel.selected.size === 0}
              onClick={() => setPending({ kind: "prune-expiring", ids: [...expSel.selected] })}
            >
              <Trash2 className="mr-1.5 size-3.5" />
              Prune now
            </Button>
          </>
        }
      >
        <p className="text-muted-foreground text-sm italic">
          No backend door extends or clears a TTL yet (`memory_dream`'s
          `refine` allowlist is `summary`-only) — pruning now is the one real
          action available here; see the report.
        </p>
        {notices.expiring && (
          <ActionNotice
            result={notices.expiring}
            onUndo={() => runUndo("expiring")}
            undoing={undoingArm === "expiring"}
            undone={Boolean(undone.expiring)}
          />
        )}
        {expiring.rows.map((row) => (
          <MemoryRow
            key={row.id}
            row={row}
            lead={
              <Checkbox
                size="sm"
                checked={expSel.selected.has(row.id)}
                onCheckedChange={() => expSel.toggle(row.id)}
                aria-label={`Select ${row.content_preview.slice(0, 40)}`}
              />
            }
          />
        ))}
        <PageControls
          offset={expOffset}
          limit={PAGE}
          total={expiring.total}
          onPrev={() => setExpOffset((o) => Math.max(0, o - PAGE))}
          onNext={() => setExpOffset((o) => o + PAGE)}
        />
      </CategoryShell>

      <CategoryShell
        icon={<GitBranch aria-hidden />}
        title="Superseded lineage"
        meta="read-only — see below"
        isEmpty={superseded.rows.length === 0}
        isError={superseded.error}
        isLoading={superseded.loading && superseded.rows.length === 0}
        emptyLine="Superseded lineage — nothing flagged for cleanup"
        errorLine="Could not load superseded lineage — this is a failed read, not zero chains"
      >
        <p className="text-muted-foreground text-sm italic">
          No bulk action here: `deprecate()` (the primitive `prune` reuses)
          only accepts an `active` memory, and every row below is already
          `superseded` — every prune attempt would refuse with
          `already_superseded`. Listed for visibility only.
        </p>
        {superseded.rows.map((row) => (
          <MemoryRow key={row.id} row={row} />
        ))}
        <PageControls
          offset={supOffset}
          limit={PAGE}
          total={superseded.total}
          onPrev={() => setSupOffset((o) => Math.max(0, o - PAGE))}
          onNext={() => setSupOffset((o) => o + PAGE)}
        />
      </CategoryShell>

      <AlertDialog
        open={pending != null}
        onOpenChange={(open) => {
          if (!open) setPending(null)
        }}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>
              {pending?.kind === "confirm-dedup"
                ? `Confirm ${pending.ids.length} duplicate pair${pending.ids.length === 1 ? "" : "s"}?`
                : `Prune ${pending?.ids.length ?? 0} row${pending?.ids.length === 1 ? "" : "s"}?`}
            </AlertDialogTitle>
            <AlertDialogDescription>
              {pending?.kind === "confirm-dedup"
                ? "Marks the near_duplicate pass-block as confirmed. This is undoable afterward through the batch's dream-digest cycle."
                : "Retires each memory with no successor (deprecate() — never a hard delete). This is undoable afterward through the batch's dream-digest cycle."}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction onClick={applyPending}>Apply</AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  )
}

