import type React from "react"
import {
  NumberInput,
  NumberInputControl,
  NumberInputDecrementTrigger,
  NumberInputField,
  NumberInputIncrementTrigger,
  NumberInputTriggerGroup,
} from "darkraise-ui/components/number-input"

/**
 * The library's compound `NumberInput` assembled once, so the five numeric
 * fields in this app share one shape instead of five `<input type="number">`
 * spellings.
 *
 * `onValueChange` reports `valueAsNumber`, which is `NaN` for text the field
 * cannot parse. That distinction is the reason to use this at all: a raw
 * number input reports `""` for a typo, and `Number("")` is `0`, which is
 * finite — so a typo silently committed a zero. Callers get `NaN` and can
 * refuse it.
 */
export function NumberField({
  value,
  onValueChange,
  min,
  max,
  step,
  disabled,
  onBlur,
  onKeyDown,
  "aria-label": ariaLabel,
  className,
}: {
  value: number
  onValueChange: (next: number) => void
  min?: number
  max?: number
  step?: number
  disabled?: boolean
  /** Commit-on-blur callers need the field's own blur, not the wrapper's. */
  onBlur?: () => void
  /** For commit-on-Enter. The field handles arrows and page keys itself. */
  onKeyDown?: (event: React.KeyboardEvent<HTMLInputElement>) => void
  "aria-label": string
  className?: string
}) {
  return (
    <NumberInput
      value={value}
      onValueChange={(details) => onValueChange(details.valueAsNumber)}
      min={min}
      max={max}
      step={step}
      disabled={disabled}
      className={className}
    >
      <NumberInputControl>
        <NumberInputField
          aria-label={ariaLabel}
          onBlur={onBlur}
          onKeyDown={onKeyDown}
          className="font-mono"
        />
        <NumberInputTriggerGroup>
          <NumberInputIncrementTrigger />
          <NumberInputDecrementTrigger />
        </NumberInputTriggerGroup>
      </NumberInputControl>
    </NumberInput>
  )
}
