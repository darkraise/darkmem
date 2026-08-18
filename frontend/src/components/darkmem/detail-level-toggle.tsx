import { AlignLeft, Circle } from "lucide-react"
import { IconSegmented, type IconSegmentedOption } from "./icon-segmented"
import { useDetailLevel, type DetailLevel } from "./use-detail-level"

const OPTIONS: ReadonlyArray<IconSegmentedOption<DetailLevel>> = [
  { value: "simple", label: "Simple", icon: Circle },
  { value: "advanced", label: "Advanced", icon: AlignLeft },
]

export function DetailLevelToggle() {
  const level = useDetailLevel((s) => s.level)
  const setLevel = useDetailLevel((s) => s.setLevel)

  return (
    <IconSegmented
      value={level}
      options={OPTIONS}
      onChange={setLevel}
      label="Detail level"
    />
  )
}
