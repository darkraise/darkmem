import type { Settings } from "sigma/settings"
import type { NodeDisplayData, PartialButFor } from "sigma/types"
import type { GraphThemeTokens } from "./code-graph-theme"
import { hexToRgba } from "./graph-colors"

export interface HoverChrome {
  /** The label plate. */
  fill: string
  /** Label text, chosen for measured contrast against `fill`. */
  text: string
  /** Plate outline, so the plate still reads where a node shares its hue. */
  stroke: string
  shadow: string
}

function channel(hex: string, at: number): number {
  const c = parseInt(hex.slice(at, at + 2), 16) / 255
  return c <= 0.03928 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4)
}

/** WCAG relative luminance. */
function luminance(hex: string): number {
  return (
    0.2126 * channel(hex, 1) + 0.7152 * channel(hex, 3) + 0.0722 * channel(hex, 5)
  )
}

function contrastRatio(a: string, b: string): number {
  const la = luminance(a)
  const lb = luminance(b)
  const hi = Math.max(la, lb)
  const lo = Math.min(la, lb)
  return (hi + 0.05) / (lo + 0.05)
}

/**
 * The chrome for the plate behind a hovered or selected node's label.
 *
 * The plate is the **accent**, not a surface token. Both `--popover` and
 * `--card` sit within a few percent lightness of `--background` by design —
 * that is what makes them read as the same sheet of paper — so a plate
 * painted in one is invisible against the graph canvas in either theme, and
 * a selection that paints nothing visible is indistinguishable from one that
 * did not register. The accent is the one token guaranteed to differ from the
 * page in both themes, and it is already the app's selection colour.
 *
 * Text is picked by measured contrast rather than assumed: an accent may land
 * anywhere on the lightness scale (`accentIntensity` alone moves it), so
 * neither `--foreground` nor `--background` is safe to hardcode.
 */
export function hoverChrome(tokens: GraphThemeTokens): HoverChrome {
  const fill = tokens.primary
  const text =
    contrastRatio(fill, tokens.background) >= contrastRatio(fill, tokens.foreground)
      ? tokens.background
      : tokens.foreground
  return {
    fill,
    text,
    stroke: hexToRgba(text, 0.25),
    shadow: hexToRgba("#000000", 0.55),
  }
}

/** Sigma's `drawDiscNodeLabel`, in the plate's own text colour rather than
 *  `settings.labelColor` — the plate is what the text has to read against,
 *  and the unplated labels elsewhere on the canvas read against the page. */
export function drawPlatedLabel(
  context: CanvasRenderingContext2D,
  data: PartialButFor<NodeDisplayData, "x" | "y" | "size" | "label" | "color">,
  settings: Settings,
  color: string,
): void {
  if (!data.label) return
  context.fillStyle = color
  context.font = `${settings.labelWeight} ${settings.labelSize}px ${settings.labelFont}`
  context.fillText(
    data.label,
    data.x + data.size + 3,
    data.y + settings.labelSize / 3,
  )
}

/** Themed replacement for sigma's `drawDiscNodeHover`, geometry unchanged. */
export function drawThemedDiscNodeHover(
  context: CanvasRenderingContext2D,
  data: PartialButFor<NodeDisplayData, "x" | "y" | "size" | "label" | "color">,
  settings: Settings,
  tokens: GraphThemeTokens,
): void {
  const size = settings.labelSize
  const { fill, text, stroke, shadow } = hoverChrome(tokens)
  context.font = `${settings.labelWeight} ${size}px ${settings.labelFont}`

  context.fillStyle = fill
  context.strokeStyle = stroke
  context.lineWidth = 1
  context.shadowOffsetX = 0
  context.shadowOffsetY = 0
  context.shadowBlur = 8
  context.shadowColor = shadow

  const PADDING = 2
  if (typeof data.label === "string") {
    const textWidth = context.measureText(data.label).width
    const boxWidth = Math.round(textWidth + 5)
    const boxHeight = Math.round(size + 2 * PADDING)
    const radius = Math.max(data.size, size / 2) + PADDING
    const angleRadian = Math.asin(boxHeight / 2 / radius)
    const xDeltaCoord = Math.sqrt(
      Math.abs(Math.pow(radius, 2) - Math.pow(boxHeight / 2, 2)),
    )

    context.beginPath()
    context.moveTo(data.x + xDeltaCoord, data.y + boxHeight / 2)
    context.lineTo(data.x + radius + boxWidth, data.y + boxHeight / 2)
    context.lineTo(data.x + radius + boxWidth, data.y - boxHeight / 2)
    context.lineTo(data.x + xDeltaCoord, data.y - boxHeight / 2)
    context.arc(data.x, data.y, radius, angleRadian, -angleRadian)
    context.closePath()
    context.fill()
  } else {
    context.beginPath()
    context.arc(data.x, data.y, data.size + PADDING, 0, Math.PI * 2)
    context.closePath()
    context.fill()
  }

  context.shadowBlur = 0
  context.stroke()
  drawPlatedLabel(context, data, settings, text)
}
