import { Label } from "darkraise-ui/components/label"
import {
  RadioGroup,
  RadioGroupItem,
} from "darkraise-ui/components/radio-group"
import { Slider } from "darkraise-ui/components/slider"
import { cn } from "darkraise-ui/lib"
import {
  DIM_MAX,
  DIM_MIN,
  DIM_STEP,
  useGraphPrefs,
  type SelectionTreatment,
} from "@/features/graph/lib/graph-prefs"

const TREATMENTS: {
  value: SelectionTreatment
  label: string
  hint: string
}[] = [
  {
    value: "halo",
    label: "Halo",
    hint: "An accent ring and glow. Reads at a distance.",
  },
  {
    value: "keyline",
    label: "Keyline",
    hint: "A dashed ring in the node's own colour. Leaves the accent to mean 'relation'.",
  },
  {
    value: "invert",
    label: "Inverted",
    hint: "A heavy contrast ring and a reversed label. Most legible on a crowded canvas.",
  },
]

/**
 * The graph's view preferences — how selection is announced, and how far the
 * rest of the map recedes behind it.
 *
 * Rendered by both Settings → Appearance and the graph toolbar's own popover.
 * One component over one store, so the two surfaces cannot drift: setting it
 * in either place is the same write.
 */
export function SelectionSettings({
  compact = false,
  className,
}: {
  /** The popover is narrow — drop the per-option hints there. */
  compact?: boolean
  className?: string
}) {
  const treatment = useGraphPrefs((s) => s.selectionTreatment)
  const setTreatment = useGraphPrefs((s) => s.setSelectionTreatment)
  const dim = useGraphPrefs((s) => s.dimUnrelated)
  const setDim = useGraphPrefs((s) => s.setDimUnrelated)

  return (
    <div className={cn("flex flex-col gap-3.5", className)}>
      <div className="flex flex-col gap-2">
        <Label className="text-sm font-medium">Selection</Label>
        {!compact && (
          <p className="text-muted-foreground text-sm">
            How the graph marks the node you clicked. It never repaints the
            node — that colour is already carrying cluster or type.
          </p>
        )}
        <RadioGroup
          value={treatment}
          onValueChange={(v) => setTreatment(v as SelectionTreatment)}
          className="flex flex-col gap-1.5"
        >
          {TREATMENTS.map((t) => (
            <label
              key={t.value}
              className="hover:bg-muted/40 flex cursor-pointer items-start gap-2.5 rounded-md px-1.5 py-1 transition-colors"
            >
              <RadioGroupItem value={t.value} className="mt-0.5 shrink-0" />
              <span className="min-w-0">
                <span className="text-foreground block text-sm">{t.label}</span>
                {!compact && (
                  <span className="text-muted-foreground block text-sm">
                    {t.hint}
                  </span>
                )}
              </span>
            </label>
          ))}
        </RadioGroup>
      </div>

      <div className="flex flex-col gap-2">
        <div className="flex items-baseline gap-2">
          <Label className="text-sm font-medium">Dim unrelated</Label>
          <span className="text-foreground ml-auto font-mono text-sm tabular-nums">
            {dim}%
          </span>
        </div>
        {!compact && (
          <p className="text-muted-foreground text-sm">
            How far the rest of the map recedes when something is focused. It
            keeps its colours and its shape — edges recede with it.
          </p>
        )}
        <div className="flex items-center gap-2.5">
          <span className="text-muted-foreground font-mono text-xs tabular-nums">
            {DIM_MIN}
          </span>
          <Slider
            value={[dim]}
            onValueChange={([v]) => setDim(v ?? dim)}
            min={DIM_MIN}
            max={DIM_MAX}
            step={DIM_STEP}
            aria-label="Dim unrelated nodes, percent"
            className="flex-1"
          />
          <span className="text-muted-foreground font-mono text-xs tabular-nums">
            {DIM_MAX}
          </span>
        </div>
      </div>
    </div>
  )
}
