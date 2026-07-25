import { useState, type ReactNode } from "react"
import {
  Archive,
  Check,
  Clock,
  Copy,
  GitBranch,
  MoveDown,
  Repeat2,
  Trash2,
} from "lucide-react"
import { Badge } from "darkraise-ui/components/badge"
import { Button } from "darkraise-ui/components/button"
import { Checkbox } from "darkraise-ui/components/checkbox"
import { EmptyState } from "darkraise-ui/components/empty-state"
import { cn } from "darkraise-ui/lib"
import { LayerChip } from "@/components/darkmem"
import { useDemoHygiene } from "@/demo/hooks"
import { useDemoStore } from "@/demo/store"
import type { HygieneCategory, HygieneRow } from "@/demo/types"
import { LifecycleBadge } from "@/features/memories/components/lifecycle-badge"

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

function CategoryShell({
  icon,
  title,
  count,
  toolbar,
  clearLine,
  isEmpty,
  children,
}: {
  icon: ReactNode
  title: string
  count: string
  toolbar: ReactNode
  clearLine: string
  isEmpty: boolean
  children: ReactNode
}) {
  return (
    <div className="border-border bg-card overflow-hidden rounded-lg border">
      <div className="border-border bg-muted/30 flex flex-wrap items-center gap-2.5 border-b px-4 py-2.5">
        <span className="text-muted-foreground [&>svg]:h-4 [&>svg]:w-4">
          {icon}
        </span>
        <span className="text-sm font-semibold">{title}</span>
        <span className="text-muted-foreground font-mono text-sm">{count}</span>
        <div className="ml-auto flex flex-wrap items-center gap-2">{toolbar}</div>
      </div>
      <div className="flex flex-col gap-2.5 p-4">
        {isEmpty ? (
          <p className="text-muted-foreground flex items-center gap-2 text-sm">
            <Check aria-hidden className="text-success h-3.5 w-3.5 shrink-0" />
            {clearLine}
          </p>
        ) : (
          children
        )}
      </div>
    </div>
  )
}

function SelectionCount({ n, unit }: { n: number; unit: string }) {
  return (
    <span className="text-muted-foreground font-mono text-sm">
      {n} {unit}
      {n === 1 ? "" : "s"} selected
    </span>
  )
}

function MemoryRowLine({
  row,
  lead,
}: {
  row: HygieneRow
  lead?: ReactNode
}) {
  return (
    <div className="border-border flex flex-wrap items-start gap-2.5 rounded-md border p-2">
      {lead}
      <LayerChip layer={0} className="mt-0.5 shrink-0" />
      <span className="min-w-52 flex-1 space-y-0.5">
        <span className="block text-sm">{row.text}</span>
        {row.why && (
          <span className="text-muted-foreground block text-sm italic">
            {row.why}
          </span>
        )}
      </span>
      <span className="text-muted-foreground ml-auto shrink-0 font-mono text-sm">
        {row.meta}
      </span>
    </div>
  )
}

function Notice({ text }: { text: string | null }) {
  if (!text) return null
  return (
    <p className="text-success flex items-center gap-2 text-sm">
      <Check aria-hidden className="h-3.5 w-3.5 shrink-0" />
      {text}
    </p>
  )
}

// Housekeeping is consequence-ranked and served-labelled, never a gate:
// sitting in this queue changes nothing about how a row serves.
export function HygieneQueue() {
  const hygiene = useDemoHygiene()
  const resolve = useDemoStore((s) => s.resolveHygiene)

  const dupSel = useSelection()
  const lowSel = useSelection()
  const expSel = useSelection()
  const chainSel = useSelection()

  const [notices, setNotices] = useState<
    Partial<Record<HygieneCategory, string>>
  >({})

  const act = (
    category: HygieneCategory,
    selection: ReturnType<typeof useSelection>,
    notice: (n: number) => string,
  ) => {
    const ids = [...selection.selected]
    if (ids.length === 0) return
    resolve(category, ids)
    selection.clear()
    setNotices((prev) => ({ ...prev, [category]: notice(ids.length) }))
  }

  const allEmpty =
    hygiene.duplicates.length === 0 &&
    hygiene.lowConfidence.length === 0 &&
    hygiene.expiring.length === 0 &&
    hygiene.lineage.length === 0

  return (
    <div className="space-y-3">
      {allEmpty && (
        <EmptyState
          icon={<Archive aria-hidden className="h-6 w-6" />}
          title="Nothing to tidy"
          description="All four hygiene categories are clear for project darkmem — nothing needs a bulk action right now. New candidates surface here automatically as dreaming, confidence, and TTL sweeps run."
        />
      )}

      <CategoryShell
        icon={<Copy aria-hidden />}
        title="Candidate duplicates"
        count={`${hygiene.duplicates.length} pair${hygiene.duplicates.length === 1 ? "" : "s"} · from dreaming`}
        isEmpty={hygiene.duplicates.length === 0}
        clearLine="Candidate duplicates — 0, none flagged by the last dream cycle"
        toolbar={
          <>
            <SelectionCount n={dupSel.selected.size} unit="pair" />
            <Button
              size="sm"
              disabled={dupSel.selected.size === 0}
              onClick={() =>
                act(
                  "duplicates",
                  dupSel,
                  (n) =>
                    `${n} pair${n === 1 ? "" : "s"} confirmed as duplicates — the older row of each pair was superseded, not deleted.`,
                )
              }
            >
              <Copy className="mr-1.5 size-3.5" />
              Confirm dedup
            </Button>
            <Button
              size="sm"
              variant="outline"
              disabled={dupSel.selected.size === 0}
              onClick={() =>
                act(
                  "duplicates",
                  dupSel,
                  (n) =>
                    `${n} pair${n === 1 ? "" : "s"} superseded instead — the correcting memory now points superseded_by at the corrected one.`,
                )
              }
            >
              <Repeat2 className="mr-1.5 size-3.5" />
              Supersede instead
            </Button>
          </>
        }
      >
        <Notice text={notices.duplicates ?? null} />
        {hygiene.duplicates.map((pair) => (
          <div
            key={pair.id}
            className="border-border space-y-1.5 rounded-md border border-dashed p-2.5"
          >
            <div className="flex items-center gap-2.5">
              {/* One shared checkbox per pair — the bulk action acts on the
                  pair, not the rows independently. */}
              <Checkbox
                size="sm"
                checked={dupSel.selected.has(pair.id)}
                onCheckedChange={() => dupSel.toggle(pair.id)}
                aria-label={`Select duplicate pair ${pair.id}`}
              />
              <span className="text-muted-foreground font-mono text-sm">
                {pair.connector}
              </span>
            </div>
            <div className="space-y-1.5 pl-6">
              <MemoryRowLine row={pair.rows[0]} />
              <MemoryRowLine row={pair.rows[1]} />
            </div>
          </div>
        ))}
      </CategoryShell>

      <CategoryShell
        icon={<Clock aria-hidden />}
        title="Low-confidence memories"
        count={`${hygiene.lowConfidence.length}`}
        isEmpty={hygiene.lowConfidence.length === 0}
        clearLine="Low-confidence memories — 0 below the review threshold"
        toolbar={
          <>
            <SelectionCount n={lowSel.selected.size} unit="row" />
            <Button
              size="sm"
              variant="outline"
              disabled={lowSel.selected.size === 0}
              onClick={() =>
                act(
                  "lowConfidence",
                  lowSel,
                  (n) =>
                    `TTL set on ${n} row${n === 1 ? "" : "s"} — they leave this queue and will surface under Expiring soon as their window approaches.`,
                )
              }
            >
              <Clock className="mr-1.5 size-3.5" />
              Set TTL
            </Button>
            <Button
              size="sm"
              variant="outline"
              className="border-destructive/55 text-destructive"
              disabled={lowSel.selected.size === 0}
              onClick={() =>
                act(
                  "lowConfidence",
                  lowSel,
                  (n) => `${n} row${n === 1 ? "" : "s"} pruned.`,
                )
              }
            >
              <Trash2 className="mr-1.5 size-3.5" />
              Prune
            </Button>
          </>
        }
      >
        <Notice text={notices.lowConfidence ?? null} />
        {hygiene.lowConfidence.map((row) => (
          <MemoryRowLine
            key={row.id}
            row={row}
            lead={
              <Checkbox
                size="sm"
                checked={lowSel.selected.has(row.id)}
                onCheckedChange={() => lowSel.toggle(row.id)}
                aria-label={`Select ${row.text.slice(0, 40)}`}
              />
            }
          />
        ))}
      </CategoryShell>

      <CategoryShell
        icon={<Clock aria-hidden />}
        title="Expiring soon"
        count={`${hygiene.expiring.length} · expires_at approaching`}
        isEmpty={hygiene.expiring.length === 0}
        clearLine="Expiring soon — 0 rows with expires_at inside the lookahead window"
        toolbar={
          <>
            <SelectionCount n={expSel.selected.size} unit="row" />
            <Button
              size="sm"
              disabled={expSel.selected.size === 0}
              onClick={() =>
                act(
                  "expiring",
                  expSel,
                  (n) =>
                    `TTL extended by 30 days on ${n} row${n === 1 ? "" : "s"} — now outside the lookahead window.`,
                )
              }
            >
              <Clock className="mr-1.5 size-3.5" />
              Extend TTL
            </Button>
            <Button
              size="sm"
              variant="outline"
              disabled={expSel.selected.size === 0}
              onClick={() =>
                act(
                  "expiring",
                  expSel,
                  (n) =>
                    `${n} row${n === 1 ? "" : "s"} left to expire — the expired_memory_cleanup job deletes them past expires_at.`,
                )
              }
            >
              <MoveDown className="mr-1.5 size-3.5" />
              Let expire
            </Button>
          </>
        }
      >
        <Notice text={notices.expiring ?? null} />
        {hygiene.expiring.map((row) => (
          <MemoryRowLine
            key={row.id}
            row={row}
            lead={
              <Checkbox
                size="sm"
                checked={expSel.selected.has(row.id)}
                onCheckedChange={() => expSel.toggle(row.id)}
                aria-label={`Select ${row.text.slice(0, 40)}`}
              />
            }
          />
        ))}
      </CategoryShell>

      <CategoryShell
        icon={<GitBranch aria-hidden />}
        title="Superseded lineage"
        count={`${hygiene.lineage.length} chain${hygiene.lineage.length === 1 ? "" : "s"}`}
        isEmpty={hygiene.lineage.length === 0}
        clearLine="Superseded lineage — 0 chains flagged for cleanup"
        toolbar={
          <>
            <SelectionCount n={chainSel.selected.size} unit="chain" />
            <Button
              size="sm"
              variant="outline"
              className="border-destructive/55 text-destructive"
              disabled={chainSel.selected.size === 0}
              onClick={() =>
                act(
                  "lineage",
                  chainSel,
                  (n) =>
                    `${n} chain${n === 1 ? "" : "s"} pruned — dependents still pointing superseded_by at a pruned row were demoted to deprecated with the pointer cleared, so chk_superseded_has_pointer held throughout the batch.`,
                )
              }
            >
              <Trash2 className="mr-1.5 size-3.5" />
              Prune
            </Button>
          </>
        }
      >
        <Notice text={notices.lineage ?? null} />
        {hygiene.lineage.map((chain) => (
          <div key={chain.id} className="space-y-1.5">
            <div className="flex items-center gap-2.5">
              <Checkbox
                size="sm"
                checked={chainSel.selected.has(chain.id)}
                onCheckedChange={() => chainSel.toggle(chain.id)}
                aria-label={`Select lineage chain ${chain.id}`}
              />
              <span className="text-muted-foreground font-mono text-sm">
                {chain.connector}
              </span>
            </div>
            <div className="space-y-0.5 pl-6">
              {chain.links.map((link, i) => (
                <div key={i} className="space-y-0.5">
                  {i > 0 && (
                    <span className="text-muted-foreground flex items-center gap-1.5 pl-2.5 font-mono text-[10px]">
                      <MoveDown aria-hidden className="h-3 w-3" />
                      superseded_by
                    </span>
                  )}
                  <div
                    className={cn(
                      "border-border flex flex-wrap items-start gap-2.5 rounded-md border p-2",
                    )}
                  >
                    {link.status === "superseded" ? (
                      <LifecycleBadge status="superseded" className="mt-0.5 shrink-0" />
                    ) : (
                      <LayerChip layer={0} className="mt-0.5 shrink-0" />
                    )}
                    <span className="min-w-52 flex-1 space-y-0.5">
                      <span className="block text-sm">{link.text}</span>
                      {link.why && (
                        <span className="text-muted-foreground block text-sm italic">
                          {link.why}
                        </span>
                      )}
                    </span>
                    <Badge
                      variant="outline"
                      size="sm"
                      className="text-muted-foreground ml-auto shrink-0 font-mono"
                    >
                      {link.meta}
                    </Badge>
                  </div>
                </div>
              ))}
            </div>
          </div>
        ))}
      </CategoryShell>
    </div>
  )
}
