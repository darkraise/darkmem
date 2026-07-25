import { Lightbulb } from "lucide-react"
import { cn } from "darkraise-ui/lib"
import { useDetailLevel } from "./use-detail-level"

export interface TraceChannel {
  /** Channel name, e.g. "semantic", "keyword", "ppr", "rerank". */
  name: string
  /** Bar width as a 0–1 fraction. `null` renders the channel as off. */
  fraction: number | null
  /** Rendered value, e.g. "0.82" or "7.4". Defaults to the fraction. */
  display?: string
}

export interface WhyRetrievedTraceProps {
  channels: TraceChannel[]
  /** Fused ordering signal — always shown in Advanced mode. */
  rrfScore: number
  /** Plain-language "why it ranked" line shown in Simple mode. */
  summary: string
  className?: string
}

const CHANNEL_COLORS = [
  "var(--chart-1)",
  "var(--chart-2)",
  "var(--chart-5)",
  "var(--chart-4)",
  "var(--chart-3)",
]

// Simple mode collapses the score breakdown to one plain line; honesty
// labels (verification badge, layer chip) live on the parent row and stay
// visible in both modes (invariant 14).
export function WhyRetrievedTrace({
  channels,
  rrfScore,
  summary,
  className,
}: WhyRetrievedTraceProps) {
  const level = useDetailLevel((s) => s.level)

  if (level === "simple") {
    return (
      <div
        className={cn(
          "bg-muted/40 text-muted-foreground flex items-center gap-2 rounded-sm px-2.5 py-1.5 text-sm",
          className,
        )}
      >
        <Lightbulb aria-hidden className="text-primary h-4 w-4 shrink-0" />
        <span>
          <b className="text-foreground font-semibold">Why it ranked:</b>{" "}
          {summary}
        </span>
      </div>
    )
  }

  return (
    <div className={cn("flex flex-col gap-1.5", className)}>
      {channels.map((channel, i) => {
        const off = channel.fraction == null
        return (
          <div
            key={channel.name}
            className="grid grid-cols-[5.5rem_1fr_4rem] items-center gap-2 text-sm"
          >
            <span className={cn("font-mono", off && "opacity-60")}>
              {channel.name}
            </span>
            <span className="bg-muted h-2 overflow-hidden rounded-full">
              <span
                className="block h-full rounded-full"
                style={{
                  width: `${Math.round((channel.fraction ?? 0) * 100)}%`,
                  background: CHANNEL_COLORS[i % CHANNEL_COLORS.length],
                }}
              />
            </span>
            <span
              className={cn(
                "text-muted-foreground text-right font-mono",
                off && "opacity-60",
              )}
            >
              {off ? "off" : (channel.display ?? channel.fraction?.toFixed(2))}
            </span>
          </div>
        )
      })}
      <div className="bg-primary/10 border-primary/35 mt-0.5 flex items-center gap-2.5 rounded-md border px-2.5 py-1.5">
        <span className="text-primary font-mono text-sm tracking-wide uppercase">
          rrf_score
        </span>
        <span className="font-mono text-sm font-semibold">
          {rrfScore.toFixed(4)}
        </span>
        <span className="text-muted-foreground text-sm">
          the ordering signal
        </span>
      </div>
    </div>
  )
}
