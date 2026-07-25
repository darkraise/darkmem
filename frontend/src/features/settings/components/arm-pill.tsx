import { CircleDashed, Zap } from "lucide-react"
import { cn } from "darkraise-ui/lib"
import { armStatus } from "@/demo/settings"

// Invariant 23, per-row: an arm at 0 renders INACTIVE (built-but-unspent,
// dashed neutral) — never omitted, never implied "off entirely". A non-zero
// arm renders ACTIVE (a live, spent signal).
export function ArmPill({ value }: { value: number }) {
  const status = armStatus(value)
  const active = status === "active"
  const Icon = active ? Zap : CircleDashed
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-full border px-2.5 py-0.5 font-mono text-[10px] tracking-wide uppercase whitespace-nowrap",
        active
          ? "border-primary/55 bg-primary/10 text-primary"
          : "border-border text-muted-foreground bg-muted/40 border-dashed",
      )}
    >
      <Icon aria-hidden className="h-3 w-3" />
      {status}
    </span>
  )
}
