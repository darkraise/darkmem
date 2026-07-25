import { Badge } from "darkraise-ui/components/badge"
import { cn } from "darkraise-ui/lib"
import type { BeliefWindow } from "@/demo/types"

function DateField({ label, value }: { label: string; value: string | null }) {
  return (
    <span className="flex flex-col font-mono text-sm">
      <span className="text-muted-foreground">{label}</span>
      <span>{value ?? "—"}</span>
    </span>
  )
}

// valid_at / invalid_at / expired_at as a timeline — "what did we believe
// as of X." Closed windows are retained as history, never a live claim.
export function BeliefWindowRow({
  window,
  className,
}: {
  window: BeliefWindow
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
            ? "border-primary/50 bg-primary/10 text-primary"
            : "text-muted-foreground border-dashed",
        )}
      >
        {open ? "open" : "window-closed"}
      </Badge>
      <span className="flex shrink-0 flex-wrap gap-4">
        <DateField label="valid_at" value={window.valid_at} />
        <DateField label="invalid_at" value={window.invalid_at} />
        <DateField label="expired_at" value={window.expired_at} />
      </span>
      {window.note && (
        <span className="text-muted-foreground min-w-52 flex-1 text-sm">
          {window.note}
        </span>
      )}
    </div>
  )
}
