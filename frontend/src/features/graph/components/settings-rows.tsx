import {
  SegmentGroup,
  SegmentGroupIndicator,
  SegmentGroupItem,
} from "darkraise-ui/components/segment-group"
import { Slider } from "darkraise-ui/components/slider"
import { Label } from "darkraise-ui/components/label"
import { cn } from "darkraise-ui/lib"
import type React from "react"

/**
 * The row shapes the graph's settings surfaces share.
 *
 * They used to be copied between the toolbar popover and SelectionSettings,
 * whose own comment claimed "one row shape shared with the layout controls
 * beside it" while being a second copy of it. One definition, so the claim is
 * true and a spacing change lands on both.
 */

/** The mono-uppercase section header the settings cards use, so the popover
 *  reads as the same product rather than as a stray widget. */
export function SectionLabel({
  children,
  className,
}: {
  children: React.ReactNode
  className?: string
}) {
  return (
    <div
      className={cn(
        "text-muted-foreground mb-2 font-mono text-xs font-semibold tracking-[0.14em] uppercase",
        className,
      )}
    >
      {children}
    </div>
  )
}

export type RowSize = "sm" | "default"

/** Width of the label column. Every row shares it, which is what makes a
 *  column of unrelated controls read as one grid. */
const LABEL_COL = "w-16 shrink-0 text-right font-normal"

// darkraise-ui's segment group ships no size: `.dr-segment-group-item` pins
// px-3/py-1.5/text-sm, and the base radio-group's data-size is overridden to
// auto. These utilities are what "small" means here. They win on layer order
// rather than specificity -- Tailwind v4 puts utilities after the library's
// @layer components -- so a single class beats the library's two-class rule.
const SEGMENT_SM_GROUP = "p-0.5"
const SEGMENT_SM_ITEM = "px-2 py-1 text-xs"

export function SegmentRow({
  label,
  value,
  onChange,
  options,
  size = "default",
  ariaLabel,
}: {
  label: string
  value: string
  onChange: (v: string) => void
  options: { value: string; label: string }[]
  size?: RowSize
  ariaLabel?: string
}) {
  return (
    <div className="text-muted-foreground flex items-center gap-2 text-sm">
      <Label className={LABEL_COL}>{label}</Label>
      <SegmentGroup
        color="accent"
        value={value}
        onValueChange={(v) => {
          if (v) onChange(v)
        }}
        aria-label={ariaLabel ?? label}
        className={cn("min-w-0 flex-1", size === "sm" && SEGMENT_SM_GROUP)}
      >
        <SegmentGroupIndicator />
        {options.map((o) => (
          <SegmentGroupItem
            key={o.value}
            value={o.value}
            className={cn("flex-1", size === "sm" && SEGMENT_SM_ITEM)}
          >
            {o.label}
          </SegmentGroupItem>
        ))}
      </SegmentGroup>
    </div>
  )
}

export function SliderRow({
  label,
  min,
  max,
  step,
  value,
  onChange,
  float = false,
  suffix = "",
  ariaLabel,
}: {
  label: string
  min: number
  max: number
  step: number
  value: number
  onChange: (v: number) => void
  float?: boolean
  suffix?: string
  ariaLabel?: string
}) {
  return (
    <div className="text-muted-foreground flex items-center gap-2 text-sm">
      <Label className={LABEL_COL}>{label}</Label>
      <Slider
        value={[value]}
        onValueChange={([v]) => {
          const next = v ?? value
          onChange(float ? next : Math.round(next))
        }}
        min={min}
        max={max}
        step={step}
        aria-label={ariaLabel ?? label}
        className="flex-1"
      />
      <span className="text-foreground w-10 shrink-0 text-right font-mono text-xs tabular-nums">
        {value}
        {suffix}
      </span>
    </div>
  )
}

/** A labelled switch on the same grid as the rows above it. */
export function SwitchRow({
  label,
  children,
  hint,
}: {
  label: string
  children: React.ReactNode
  hint?: React.ReactNode
}) {
  return (
    <div className="text-muted-foreground flex items-center gap-2 text-sm">
      <Label className={LABEL_COL}>{label}</Label>
      {children}
      {hint}
    </div>
  )
}
