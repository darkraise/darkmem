import { Badge } from "darkraise-ui/components/badge"
import { cn } from "darkraise-ui/lib"
import { Timestamp } from "@/components/darkmem"

function DateField({ label, value }: { label: string; value: string | null }) {
  return (
    <span className="flex flex-col font-mono text-sm">
      <span className="text-muted-foreground">{label}</span>
      <Timestamp iso={value} />
    </span>
  )
}

/** Structural, not `@/demo/types`' `BeliefWindow`: the live door's
 *  `valid_at` is nullable (a candidate fact predates verification) where the
 *  demo fixture's is always a string, and the live door carries no `note`.
 *  A demo `BeliefWindow` still satisfies this shape at every existing call
 *  site — the widening only ever loosens, never narrows. */
export interface BeliefWindowLike {
  valid_at: string | null
  invalid_at: string | null
  expired_at: string | null
  note?: string
}

// valid_at / invalid_at / expired_at as a timeline — "what did we believe
// as of X." Closed windows are retained as history, never a live claim.
export function BeliefWindowRow({
  window,
  className,
}: {
  window: BeliefWindowLike
  className?: string
}) {
  const open = window.invalid_at == null && window.expired_at == null
  return (
    <div
      className={cn(
        "border-border flex flex-wrap items-start gap-x-4 gap-y-1.5 rounded-md border p-2.5",
        className,
      )}
    >
      <Badge
        variant="outline"
        size="sm"
        className={cn(
          "shrink-0 font-mono tracking-wide uppercase",
          open
            ? "border-primary/50 bg-primary/10 text-primary-text"
            : "text-muted-foreground border-dashed",
        )}
      >
        {open ? "open" : "closed"}
      </Badge>
      <span className="flex shrink-0 flex-wrap gap-4">
        <DateField label="Valid from" value={window.valid_at} />
        <DateField label="Invalid from" value={window.invalid_at} />
        <DateField label="Expired" value={window.expired_at} />
      </span>
      {window.note && (
        <span className="text-muted-foreground min-w-52 flex-1 text-sm">
          {window.note}
        </span>
      )}
    </div>
  )
}
