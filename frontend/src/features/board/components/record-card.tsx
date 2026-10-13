import { useDraggable } from "@dnd-kit/core"
import { Lock } from "lucide-react"
import { Badge } from "darkraise-ui/components/badge"
import { cn } from "darkraise-ui/lib"
import { formatWhen } from "@/lib/format"
import {
  formatProgress,
  NOTE_REQUIRED,
  shortName,
  UNTRACKED_LABEL,
  type BoardRecord,
} from "../lib/records"

export const LEDGER_LOCK = "state comes from the plan's ledger"

/** One register row or plan task (§3 Cards). Only a register card in the
 *  register lane of a State grouping is draggable. */
export function RecordCard({
  record,
  draggable,
  pending,
  onOpen,
}: {
  record: BoardRecord
  draggable: boolean
  pending: boolean
  onOpen: (record: BoardRecord) => void
}) {
  const { setNodeRef, listeners, attributes, transform, isDragging } =
    useDraggable({
      id: record.id,
      disabled: !draggable || pending,
    })
  const style = transform
    ? { transform: `translate3d(${transform.x}px, ${transform.y}px, 0)` }
    : undefined
  const isRow = record.type === "register_row"
  const progress = formatProgress(record.planProgress)
  return (
    <article
      ref={setNodeRef}
      style={style}
      {...(draggable ? listeners : {})}
      {...(draggable ? attributes : {})}
      aria-label={`${record.label} ${record.title}`}
      aria-busy={pending || undefined}
      onClick={() => onOpen(record)}
      className={cn(
        "bg-card border-border space-y-1.5 rounded-md border p-2.5 text-sm",
        draggable && "cursor-grab",
        isDragging && "z-10 shadow-lg",
        pending && "opacity-60",
      )}
    >
      <div className="flex items-center gap-1.5">
        <Badge variant={isRow ? "secondary" : "outline"}>
          {isRow ? "row" : "task"}
        </Badge>
        <span className="text-muted-foreground truncate font-mono text-xs">
          {isRow ? record.label : `Task ${record.number}`} ·{" "}
          {shortName(record.source)}
        </span>
        {!isRow ? (
          <Lock
            className="text-muted-foreground ml-auto size-3.5 shrink-0"
            aria-label={LEDGER_LOCK}
          >
            <title>{LEDGER_LOCK}</title>
          </Lock>
        ) : null}
      </div>
      <p className="font-medium">{record.title}</p>
      {pending ? (
        <p className="text-muted-foreground text-xs">saving…</p>
      ) : null}
      {isRow && record.assigned && record.assigned !== "-" ? (
        <p className="text-muted-foreground truncate text-xs">
          {record.assigned}
        </p>
      ) : null}
      {isRow && progress ? <p className="text-xs">{progress}</p> : null}
      {isRow && NOTE_REQUIRED.has(record.state) && !record.noteBlank ? (
        <p className="text-muted-foreground text-xs">{record.note}</p>
      ) : null}
      {isRow && record.blockFirst ? (
        <p className="text-destructive text-xs">
          block-first: delete and re-file this register to edit it here
        </p>
      ) : null}
      {!isRow && record.commit ? (
        <p className="font-mono text-xs">{record.commit.slice(0, 7)}</p>
      ) : null}
      {!isRow && record.lastActivity ? (
        <p className="text-muted-foreground text-xs">
          {formatWhen(record.lastActivity)}
        </p>
      ) : null}
      {!isRow && record.state === "blocked" && record.note ? (
        <p className="text-xs whitespace-pre-wrap">{record.note}</p>
      ) : null}
      {record.untracked ? (
        <p className="text-muted-foreground text-xs">
          {UNTRACKED_LABEL[record.untracked]}
        </p>
      ) : null}
      {record.sharedNumber ? (
        <p className="text-xs">
          shares task number {record.number}; the ledger cannot tell them apart
        </p>
      ) : null}
    </article>
  )
}
