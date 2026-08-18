import type { LucideIcon } from "lucide-react"
import {
  SegmentGroup,
  SegmentGroupIndicator,
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
      // Filled: the checked segment takes the primary pill and
      // `text-primary-foreground`. The outline variant marks it with a hollow
      // ring and a colour shift only, which is too quiet to carry selection
      // on a control whose segments are icons.
      variant="default"
      aria-label={label}
      className={className}
    >
      {/* The sliding pill IS the selected state. Without it the only mark on
          the checked segment is a text-colour shift, which on an icon-only
          control reads as nothing being selected at all. It measures the
          checked item, so it has to live inside the group. */}
      <SegmentGroupIndicator className="rounded-md" />
      {options.map((option) => (
        <Tooltip key={option.value}>
          {/* The trigger wraps the segment rather than becoming it. With
              `asChild` on the item itself, Tooltip's own `data-state`
              (open/closed) lands on the element and overwrites the segment's
              `data-state` (checked/unchecked) — so the library's
              `[data-state="checked"]` colour rule never matched and the
              checked icon stayed the same muted grey as the unchecked one.
              The indicator pill still moved, because it reads context rather
              than the attribute, which is what made this look like a
              half-working selection instead of a clobbered attribute. */}
          <TooltipTrigger asChild>
            <span className="inline-flex">
              {/* Square, not the base `px-3 py-1.5` rectangle: these segments
                  hold one icon and no text, so equal padding is what makes
                  the pill read as a rounded square rather than a wide slab.
                  The radius matches the indicator's override above. */}
              <SegmentGroupItem
                value={option.value}
                aria-label={option.label}
                className="size-8 rounded-md p-0"
              >
                <option.icon aria-hidden className="size-[var(--icon-size)]" />
              </SegmentGroupItem>
            </span>
          </TooltipTrigger>
          <TooltipContent>{option.label}</TooltipContent>
        </Tooltip>
      ))}
    </SegmentGroup>
  )
}
