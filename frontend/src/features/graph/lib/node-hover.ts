import type { Settings } from "sigma/settings"
import type { NodeDisplayData, PartialButFor } from "sigma/types"
import type { GraphThemeTokens } from "./code-graph-theme"

export interface HoverChrome {
  fill: string
  shadow: string
}

/**
 * The hover/selection label plate, in the app's own theme.
 *
 * Sigma's built-in `drawDiscNodeHover` hardcodes a `#FFF` plate and a `#000`
 * shadow while drawing the label in `settings.labelColor` — which every
 * renderer here sets to `--foreground`. Under a dark theme that is
 * near-white text on a white plate: the label of the node you just selected
 * is the one thing you cannot read. So the plate takes `--popover`, the
 * surface `--foreground` is the contrast partner for.
 */
export function hoverChrome(tokens: GraphThemeTokens): HoverChrome {
  return {
    fill: tokens.popover,
    shadow: tokens.isDark ? "#000" : tokens.border,
  }
}

/** Sigma's `drawDiscNodeLabel`, with the plate's own foreground rather than
 *  `settings.labelColor` — the two are the same token today, but the plate is
 *  what the text has to read against. */
function drawLabel(
  context: CanvasRenderingContext2D,
  data: PartialButFor<NodeDisplayData, "x" | "y" | "size" | "label" | "color">,
  settings: Settings,
  color: string,
): void {
  if (!data.label) return
  context.fillStyle = color
  context.font = `${settings.labelWeight} ${settings.labelSize}px ${settings.labelFont}`
  context.fillText(data.label, data.x + data.size + 3, data.y + settings.labelSize / 3)
}

/** Themed replacement for sigma's `drawDiscNodeHover`, geometry unchanged. */
export function drawThemedDiscNodeHover(
  context: CanvasRenderingContext2D,
  data: PartialButFor<NodeDisplayData, "x" | "y" | "size" | "label" | "color">,
  settings: Settings,
  tokens: GraphThemeTokens,
): void {
  const size = settings.labelSize
  const { fill, shadow } = hoverChrome(tokens)
  context.font = `${settings.labelWeight} ${size}px ${settings.labelFont}`

  context.fillStyle = fill
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
  drawLabel(context, data, settings, tokens.popoverForeground)
}
