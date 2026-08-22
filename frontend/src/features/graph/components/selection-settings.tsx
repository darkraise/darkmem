import { Label } from "darkraise-ui/components/label"
import {
  SegmentGroup,
  SegmentGroupIndicator,
  SegmentGroupItem,
} from "darkraise-ui/components/segment-group"
import { Slider } from "darkraise-ui/components/slider"
import { cn } from "darkraise-ui/lib"
import {
  DIM_MAX,
  DIM_MIN,
  DIM_STEP,
  useGraphPrefs,
  type SelectionColor,
} from "@/features/graph/lib/graph-prefs"

const COLORS: { value: SelectionColor; label: string }[] = [
  { value: "accent", label: "Accent" },
  { value: "inverted", label: "Inverted" },
]

/**
 * The graph's view preferences — what colour a selection's halo is painted in,
 * and how far the rest of the map recedes behind it.
 *
 * Rendered by both Settings → Appearance and the graph toolbar's own popover.
 * One component over one store, so the two surfaces cannot drift: setting it
 * in either place is the same write.
 */
export function SelectionSettings({
  compact = false,
  className,
}: {
  /** The popover is narrow — drop the prose there. */
  compact?: boolean
  className?: string
}) {
  const color = useGraphPrefs((s) => s.selectionColor)
  const setColor = useGraphPrefs((s) => s.setSelectionColor)
  const dim = useGraphPrefs((s) => s.dimUnrelated)
  const setDim = useGraphPrefs((s) => s.setDimUnrelated)

  return (
    <div className={cn("flex flex-col gap-3", className)}>
      {!compact && (
        <p className="text-muted-foreground text-sm">
          A selected node keeps its own colour and gains a halo. This is what
          that halo is painted in — the accent, or a high-contrast inversion
          for a crowded canvas where the accent competes with relation edges.
        </p>
      )}

      {/* One row shape shared with the layout controls beside it, so the panel
          reads as a single grid. */}
      <div className="text-muted-foreground flex items-center gap-2 text-sm">
        <Label className="w-16 shrink-0 text-right font-normal">Halo</Label>
        <SegmentGroup
          color="accent"
          value={color}
          onValueChange={(v) => setColor(v as SelectionColor)}
          className="min-w-0 flex-1"
        >
          <SegmentGroupIndicator />
          {COLORS.map((c) => (
            <SegmentGroupItem key={c.value} value={c.value}>
              {c.label}
            </SegmentGroupItem>
          ))}
        </SegmentGroup>
      </div>

      <div className="text-muted-foreground flex items-center gap-2 text-sm">
        <Label className="w-16 shrink-0 text-right font-normal">Dim</Label>
        <Slider
          value={[dim]}
          onValueChange={([v]) => setDim(v ?? dim)}
          min={DIM_MIN}
          max={DIM_MAX}
          step={DIM_STEP}
          aria-label="Dim unrelated nodes, percent"
          className="flex-1"
        />
        <span className="text-foreground w-10 shrink-0 text-right font-mono tabular-nums">
          {dim}%
        </span>
      </div>
      {!compact && (
        <p className="text-muted-foreground -mt-1 text-sm">
          How far the rest of the map recedes when something is focused. It
          keeps its colours and its shape — edges recede with it.
        </p>
      )}
    </div>
  )
}
