import { cn } from "darkraise-ui/lib"
import { SegmentRow, SliderRow } from "./settings-rows"
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
  /** The popover is narrow — use small segments there. */
  compact?: boolean
  className?: string
}) {
  const color = useGraphPrefs((s) => s.selectionColor)
  const setColor = useGraphPrefs((s) => s.setSelectionColor)
  const dim = useGraphPrefs((s) => s.dimUnrelated)
  const setDim = useGraphPrefs((s) => s.setDimUnrelated)

  return (
    <div className={cn("flex flex-col", compact ? "gap-2" : "gap-3", className)}>
      {/* The same row primitives the toolbar popover uses, so the panel reads
          as a single grid -- and so a spacing change lands on both rather than
          on whichever copy someone remembered. The popover asks for the small
          segments; Settings > Appearance has the room for full-size ones. */}
      <SegmentRow
        label="Halo"
        value={color}
        onChange={(v) => setColor(v as SelectionColor)}
        size={compact ? "sm" : "default"}
        ariaLabel="Selection halo colour"
        options={COLORS}
      />

      <SliderRow
        label="Dim"
        min={DIM_MIN}
        max={DIM_MAX}
        step={DIM_STEP}
        value={dim}
        onChange={setDim}
        suffix="%"
        ariaLabel="Dim unrelated nodes, percent"
      />
    </div>
  )
}
