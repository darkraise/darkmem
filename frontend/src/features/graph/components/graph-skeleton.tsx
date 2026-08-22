import { Skeleton } from "darkraise-ui/components/skeleton"

/**
 * Placeholder for the graph canvas.
 *
 * Built from the same `Skeleton` primitive every other surface loads with, so
 * it derives its colour from the theme rather than carrying its own. The
 * previous version hardcoded five RGB triples that matched neither the theme
 * tokens nor `buildMemoryPalette`, which is why it read as a different
 * product while it was on screen.
 *
 * The two node shapes are the honest signal: the graph draws memories as
 * discs and entities as diamonds, so the placeholder does too. Positions are
 * fixed rather than random — a placeholder that reshuffles on every render
 * reads as content arriving and then changing its mind.
 */

type Kind = "disc" | "diamond"

const NODES: { top: string; left: string; size: number; kind: Kind; delay: number }[] = [
  { top: "30%", left: "20%", size: 34, kind: "disc", delay: 0 },
  { top: "22%", left: "28%", size: 24, kind: "disc", delay: 0.3 },
  { top: "42%", left: "27%", size: 20, kind: "diamond", delay: 0.6 },
  { top: "38%", left: "14%", size: 18, kind: "diamond", delay: 0.15 },
  { top: "18%", left: "44%", size: 28, kind: "disc", delay: 0.45 },
  { top: "26%", left: "54%", size: 20, kind: "diamond", delay: 0.75 },
  { top: "37%", left: "62%", size: 32, kind: "disc", delay: 0.2 },
  { top: "28%", left: "72%", size: 22, kind: "disc", delay: 0.5 },
  { top: "48%", left: "69%", size: 18, kind: "diamond", delay: 0.8 },
  { top: "44%", left: "48%", size: 26, kind: "disc", delay: 0.35 },
  { top: "62%", left: "38%", size: 30, kind: "disc", delay: 0.25 },
  { top: "68%", left: "50%", size: 20, kind: "diamond", delay: 0.55 },
  { top: "58%", left: "58%", size: 22, kind: "disc", delay: 0.7 },
  { top: "66%", left: "26%", size: 18, kind: "diamond", delay: 0.4 },
  { top: "20%", left: "82%", size: 24, kind: "disc", delay: 0.6 },
]

const EDGES: { top: string; left: string; width: string; rotate: string }[] = [
  { top: "32%", left: "22%", width: "9%", rotate: "-14deg" },
  { top: "36%", left: "17%", width: "7%", rotate: "26deg" },
  { top: "24%", left: "30%", width: "13%", rotate: "-6deg" },
  { top: "40%", left: "30%", width: "17%", rotate: "6deg" },
  { top: "20%", left: "47%", width: "8%", rotate: "18deg" },
  { top: "39%", left: "50%", width: "12%", rotate: "-4deg" },
  { top: "30%", left: "65%", width: "8%", rotate: "-22deg" },
  { top: "40%", left: "64%", width: "6%", rotate: "34deg" },
  { top: "47%", left: "42%", width: "10%", rotate: "36deg" },
  { top: "64%", left: "40%", width: "10%", rotate: "12deg" },
  { top: "61%", left: "29%", width: "9%", rotate: "-8deg" },
  { top: "60%", left: "52%", width: "7%", rotate: "-24deg" },
]

/** Faint groupings under the nodes, matching the hull layer the graph draws. */
const HULLS = [
  { cx: "22%", cy: "34%", rx: "13%", ry: "16%" },
  { cx: "58%", cy: "34%", rx: "15%", ry: "14%" },
  { cx: "40%", cy: "64%", rx: "14%", ry: "12%" },
]

export function GraphSkeleton({
  label = "Loading graph",
}: {
  label?: string
}) {
  return (
    <div className="relative h-full min-h-0 flex-1">
      <div className="bg-background absolute inset-0 overflow-hidden">
        {HULLS.map((h, i) => (
          <div
            key={`h-${i}`}
            className="border-border/50 bg-muted/30 absolute rounded-[50%] border"
            style={{
              left: h.cx,
              top: h.cy,
              width: `calc(${h.rx} * 2)`,
              height: `calc(${h.ry} * 2)`,
              transform: "translate(-50%, -50%)",
            }}
          />
        ))}

        {EDGES.map((e, i) => (
          <div
            key={`e-${i}`}
            className="bg-border absolute h-px"
            style={{
              top: e.top,
              left: e.left,
              width: e.width,
              transform: `rotate(${e.rotate})`,
              transformOrigin: "0 0",
            }}
          />
        ))}

        {NODES.map((n, i) => (
          <Skeleton
            key={`n-${i}`}
            className={`absolute ${n.kind === "disc" ? "rounded-full" : "rounded-[2px]"}`}
            style={{
              top: n.top,
              left: n.left,
              width: n.size,
              height: n.size,
              // The graph's entity nodes are squares turned 45 degrees; so are
              // these, rather than an approximation with a different outline.
              transform: n.kind === "diamond" ? "rotate(45deg)" : undefined,
              animationDelay: `${n.delay}s`,
            }}
          />
        ))}

        {/* Placed where the real controls are — top-left filter, top-right
            settings cluster — so the chrome does not appear to move when the
            graph replaces this. */}
        <Skeleton className="absolute top-3 left-3 h-9 w-9" />
        <div className="absolute top-3 right-3 flex gap-1.5">
          <Skeleton className="h-9 w-9" />
          <Skeleton className="h-9 w-9" />
          <Skeleton className="h-9 w-9" />
        </div>

        <p
          className="text-muted-foreground absolute bottom-5 left-1/2 -translate-x-1/2 text-sm"
          role="status"
        >
          {label}
        </p>
      </div>
    </div>
  )
}
