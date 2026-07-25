import { AlignLeft, Circle } from "lucide-react"
import {
  ToggleGroup,
  ToggleGroupItem,
} from "darkraise-ui/components/toggle-group"
import { useDetailLevel, type DetailLevel } from "./use-detail-level"

export function DetailLevelToggle() {
  const level = useDetailLevel((s) => s.level)
  const setLevel = useDetailLevel((s) => s.setLevel)

  return (
    <ToggleGroup
      type="single"
      size="sm"
      value={level}
      onValueChange={(value) => {
        if (value === "simple" || value === "advanced") {
          setLevel(value as DetailLevel)
        }
      }}
      aria-label="Detail level"
    >
      <ToggleGroupItem value="simple">
        <Circle aria-hidden className="h-3.5 w-3.5" />
        Simple
      </ToggleGroupItem>
      <ToggleGroupItem value="advanced">
        <AlignLeft aria-hidden className="h-3.5 w-3.5" />
        Advanced
      </ToggleGroupItem>
    </ToggleGroup>
  )
}
