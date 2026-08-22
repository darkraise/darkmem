import type { Settings } from "sigma/settings"
import type { NodeDisplayData, PartialButFor } from "sigma/types"
import type { GraphThemeTokens } from "./code-graph-theme"
import type { SelectionColor } from "./graph-prefs"

/** Focus is what you clicked; hover is what the pointer is over. They must
 *  never look alike — reading one as the other is the defect this model
 *  replaces. */
export type ChromeKind = "focus" | "hover"

export interface HoverChrome {
  /** Label plate fill. */
  fill: string
  /** Label text, chosen for measured contrast against `fill`. */
  text: string
  /** Plate outline, for the treatments whose plate shares the page's colour. */
  plateStroke: string | null
  /** The halo drawn around the node itself. */
  ring: string
  ringWidth: number
  /** Clear space between the node's edge and the halo. Without it the halo
   *  reads as a thick border and the node looks recoloured rather than
   *  ringed. */
  ringGap: number
  glow: boolean
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
  return (Math.max(la, lb) + 0.05) / (Math.min(la, lb) + 0.05)
}

/** Whichever of the theme's two poles reads better on `plate`. An accent may
 *  land anywhere on the lightness scale — `accentIntensity` alone moves it —
 *  so neither pole is safe to hardcode. */
function readableOn(plate: string, tokens: GraphThemeTokens): string {
  return contrastRatio(plate, tokens.background) >= contrastRatio(plate, tokens.foreground)
    ? tokens.background
    : tokens.foreground
}

/**
 * The chrome for the plate and ring around a hovered or selected node.
 *
 * The plate is never a surface token. `--popover` and `--card` sit within a
 * few percent lightness of `--background` by design — that is what makes them
 * read as the same sheet of paper — so a plate painted in one is invisible
 * against the graph canvas in either theme, and a selection that paints
 * nothing visible cannot be told from one that did not register.
 *
 * Every treatment rings the node rather than repainting it: sigma redraws
 * highlighted nodes on the `hoverNodes` layer above this one, so the node
 * keeps its own fill and the ring reads as an addition to it.
 */
export function hoverChrome(
  tokens: GraphThemeTokens,
  color: SelectionColor,
  kind: ChromeKind,
  _nodeColor: string,
): HoverChrome {
  const shadow = tokens.isDark ? "#000000" : tokens.border
  const inverted = color === "inverted"
  const ring = inverted ? tokens.foreground : tokens.primary

  // Hover is deliberately uniform: it is not a selection, and giving it a
  // personality per colour would be another chance to mistake it for one.
  if (kind === "hover") {
    return {
      fill: tokens.background,
      text: tokens.foreground,
      plateStroke: tokens.primary,
      ring: tokens.primary,
      ringWidth: 1.5,
      ringGap: 2.5,
      glow: false,
      shadow,
    }
  }

  return {
    fill: ring,
    text: readableOn(ring, tokens),
    plateStroke: null,
    ring,
    ringWidth: 3,
    ringGap: 4,
    glow: !inverted,
    shadow,
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

/** The node shapes a halo has to be able to trace. */
export type HaloShape = "circle" | "diamond"

/** The halo around the node.
 *
 *  It follows the node's own shape: a circle drawn round a diamond reads as a
 *  bubble the node happens to sit in rather than as that node being picked
 *  out. Drawn after the plate so the plate's shadow cannot smear it. */
export function drawFocusRing(
  context: CanvasRenderingContext2D,
  x: number,
  y: number,
  radius: number,
  chrome: HoverChrome,
  shape: HaloShape = "circle",
): void {
  const r = radius + chrome.ringGap + chrome.ringWidth / 2
  context.save()
  context.beginPath()
  if (shape === "diamond") {
    context.moveTo(x, y - r)
    context.lineTo(x + r, y)
    context.lineTo(x, y + r)
    context.lineTo(x - r, y)
    context.closePath()
  } else {
    context.arc(x, y, r, 0, Math.PI * 2)
  }
  context.strokeStyle = chrome.ring
  context.lineWidth = chrome.ringWidth
  context.lineJoin = "round"
  if (chrome.glow) {
    context.shadowBlur = 10
    context.shadowColor = chrome.ring
  }
  context.stroke()
  context.restore()
}

/** Themed replacement for sigma's `drawDiscNodeHover`, geometry unchanged. */
export function drawThemedDiscNodeHover(
  context: CanvasRenderingContext2D,
  data: PartialButFor<NodeDisplayData, "x" | "y" | "size" | "label" | "color">,
  settings: Settings,
  tokens: GraphThemeTokens,
  color: SelectionColor,
  kind: ChromeKind,
): void {
  const size = settings.labelSize
  const chrome = hoverChrome(tokens, color, kind, data.color)
  context.font = `${settings.labelWeight} ${size}px ${settings.labelFont}`

  context.fillStyle = chrome.fill
  context.shadowOffsetX = 0
  context.shadowOffsetY = 0
  context.shadowBlur = 8
  context.shadowColor = chrome.shadow

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
  if (chrome.plateStroke) {
    context.strokeStyle = chrome.plateStroke
    context.lineWidth = 1
    context.stroke()
  }

  drawFocusRing(context, data.x, data.y, data.size, chrome, "circle")
  drawPlatedLabel(context, data, settings, chrome.text)
}
