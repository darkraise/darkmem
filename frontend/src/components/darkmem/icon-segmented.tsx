import type { LucideIcon } from "lucide-react"
import {
  SegmentGroup,
  SegmentGroupItem,
} from "darkraise-ui/components/segment-group"
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "darkraise-ui/components/tooltip"

export interface IconSegmentedOption<T extends string> {
  value: T
  /** The tooltip text, and the control's accessible name for this segment.
   *  Icon-only segments have no visible text, so this is the only name a
   *  screen reader or a test can address them by. */
  label: string
  icon: LucideIcon
}

/**
 * Icon-only segmented control: `SegmentGroup` for the behaviour, `Tooltip`
 * for the label the icon replaces. Composition over darkraise-ui, not a
 * reimplementation — `SegmentGroup` is radio-based, so each segment keeps
 * `role="radio"` and arrow-key roving focus for free.
 *
 * Exists because three surfaces want the same shape (detail level, the
 * classifier kind, the jobs layout switch) and an icon with no accessible
 * name is the easy thing to get wrong three times.
 */
export function IconSegmented<T extends string>({
  value,
  options,
  onChange,
  label,
  className,
}: {
  value: T
  options: ReadonlyArray<IconSegmentedOption<T>>
  onChange: (value: T) => void
  /** Names the group itself, not any one segment. */
  label: string
  className?: string
}) {
  return (
    <SegmentGroup
      value={value}
      onValueChange={(next) => {
        // The group is single-select and always has a checked item, but a
        // deselect would arrive as "" and must not reach a typed setter.
        if (next) onChange(next as T)
      }}
      variant="outline"
      aria-label={label}
      className={className}
    >
      {options.map((option) => (
        <Tooltip key={option.value}>
          <TooltipTrigger asChild>
            <SegmentGroupItem value={option.value} aria-label={option.label}>
              <option.icon aria-hidden className="size-[var(--icon-size)]" />
            </SegmentGroupItem>
          </TooltipTrigger>
          <TooltipContent>{option.label}</TooltipContent>
        </Tooltip>
      ))}
    </SegmentGroup>
  )
}
