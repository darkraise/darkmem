import { Badge } from "darkraise-ui/components/badge"
import { GitCommitHorizontal, Lock } from "lucide-react"
import type { BoardTask } from "../use-progress-corpus"
import type { StartableVerdict } from "../lib/startable"
import { plainText } from "../lib/plain-text"

/**
 * One task, as a card.
 *
 * A `blocked` card renders its Note in full rather than behind a click: the
 * ledger keeps that reason in a free-text column at the far right of an
 * eleven-column table, which is the one thing the table genuinely hides.
 */
export function TaskCard({
  entry,
  verdict,
  onOpen,
}: {
  entry: BoardTask
  verdict: StartableVerdict
  onOpen: () => void
}) {
  const { task, row, epic } = entry
  const blocked = row?.rawStatus === "blocked"

  return (
    <button
      type="button"
      onClick={onOpen}
      className="border-border bg-card hover:border-primary/50 focus-visible:ring-ring w-full rounded-md border p-2.5 text-left transition-colors focus-visible:ring-2 focus-visible:outline-none"
    >
      <div className="flex items-baseline gap-1.5">
        <span className="text-primary font-mono text-[11px] font-semibold">
          {task.id}
        </span>
        {verdict.startable && (
          <Badge variant="outline" className="h-4 px-1 text-[10px]">
            startable
          </Badge>
        )}
      </div>

      <p className="mt-0.5 text-[13px] leading-snug font-medium">
        {plainText(task.title)}
      </p>

      <div className="text-muted-foreground mt-1.5 flex flex-wrap items-center gap-x-2 gap-y-1 text-[11px]">
        <span>{epic.key}</span>
        {task.lane && <span className="truncate">{task.lane}</span>}
        {task.meta.Size && <span>{task.meta.Size}</span>}
        {task.meta.Model && <span>{task.meta.Model}</span>}
      </div>

      {row?.owner && (
        <p className="text-muted-foreground mt-1 truncate font-mono text-[10px]">
          {row.owner}
        </p>
      )}

      {row?.commit && (
        <p className="text-muted-foreground mt-1 flex items-center gap-1 truncate font-mono text-[10px]">
          <GitCommitHorizontal aria-hidden className="size-3 shrink-0" />
          <span className="truncate">{row.commit}</span>
        </p>
      )}

      {blocked && row?.note && (
        <p className="border-warning/50 bg-warning/5 mt-2 rounded border-l-2 px-2 py-1 text-[11px] leading-snug">
          {plainText(row.note)}
        </p>
      )}

      {!verdict.startable && row?.rawStatus === "todo" && verdict.reason && (
        <p className="text-muted-foreground mt-2 flex items-start gap-1 text-[11px] leading-snug">
          <Lock aria-hidden className="mt-0.5 size-3 shrink-0" />
          <span>{verdict.reason}</span>
        </p>
      )}
    </button>
  )
}
