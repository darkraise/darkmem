import type { Settings } from "sigma/settings"
import type { NodeDisplayData, PartialButFor } from "sigma/types"
import type { GraphThemeTokens } from "./code-graph-theme"
import { recede } from "./focus-model"
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

/** Ring geometry per chrome kind. Hoisted out of `hoverChrome` because
 *  LABEL_CLEARANCE below is derived from it: a ring widened in one place and a
 *  label offset left in another is how the text ended up under the ring. */
const RING = {
  hover: { width: 1, gap: 2 },
  focus: { width: 2, gap: 2.5 },
} as const

/** Clear space between the focus ring's outer edge and the label plate. */
const PLATE_GAP = 3
/** Inner padding of the label plate. */
const PLATE_PAD_X = 6
const PLATE_PAD_Y = 3
const PLATE_CORNER = 4
/** Share of the ring colour tinting a selected node's label plate. */
const FOCUS_TINT = 0.24

/**
 * Clear space between a node's edge and the left edge of its label.
 *
 * Sized to clear the *focus* ring, the wider of the two, and used for the
 * unhovered label as well — one offset in the resting state and another under
 * the chrome would make the label jump sideways the moment you point at a
 * node. Sigma's own `drawDiscNodeLabel` hardcodes 3, which put the text
 * inside both rings, so the renderers pass `drawNodeLabel` below instead.
 */
export const LABEL_CLEARANCE =
  RING.focus.gap + RING.focus.width + PLATE_GAP + PLATE_PAD_X

/** Left edge of the label plate: just clear of the focus ring. */
export const PLATE_INSET = RING.focus.gap + RING.focus.width + PLATE_GAP

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
 * keeps its own fill and the ring reads as an addition to it. The plate holds
 * only the label; a plate filled round the node as well reads as a solid disc
 * of the ring colour with the node lost inside it.
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
      ringWidth: RING.hover.width,
      ringGap: RING.hover.gap,
      glow: false,
      shadow,
    }
  }

  // A tint of the ring over the page, outlined in the ring: it reads as the
  // selection's own tag without a slab of full accent beside the node.
  const fill = recede(ring, tokens.background, FOCUS_TINT)
  return {
    fill,
    text: readableOn(fill, tokens),
    plateStroke: ring,
    ring,
    ringWidth: RING.focus.width,
    ringGap: RING.focus.gap,
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
    data.x + data.size + LABEL_CLEARANCE,
    data.y + settings.labelSize / 3,
  )
}

/**
 * The resting label, at the same offset the plated one uses.
 *
 * Replaces sigma's `drawDiscNodeLabel`, which is identical but for the
 * hardcoded 3px offset. Colour resolution matches it exactly: the per-node
 * `labelColor` attribute when the setting names one, so a grounded label still
 * recedes with its node.
 */
export function drawNodeLabel(
  context: CanvasRenderingContext2D,
  data: PartialButFor<NodeDisplayData, "x" | "y" | "size" | "label" | "color">,
  settings: Settings,
): void {
  if (!data.label) return
  const { labelSize, labelFont, labelWeight, labelColor } = settings
  context.fillStyle = labelColor.attribute
    ? (data as unknown as Record<string, string>)[labelColor.attribute] ||
      labelColor.color ||
      "#000"
    : (labelColor.color ?? "#000")
  context.font = `${labelWeight} ${labelSize}px ${labelFont}`
  context.fillText(
    data.label,
    data.x + data.size + LABEL_CLEARANCE,
    data.y + labelSize / 3,
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

/**
 * The label plate: a rounded tag to the right of the ring, holding the label
 * in the chrome's text colour. Nothing is painted over or around the node.
 */
export function drawLabelPlate(
  context: CanvasRenderingContext2D,
  data: PartialButFor<NodeDisplayData, "x" | "y" | "size" | "label" | "color">,
  settings: Settings,
  chrome: HoverChrome,
): void {
  if (!data.label) return
  const size = settings.labelSize
  context.font = `${settings.labelWeight} ${size}px ${settings.labelFont}`
  const textWidth = context.measureText(data.label).width
  const x0 = data.x + data.size + PLATE_INSET
  const x1 = x0 + PLATE_PAD_X + textWidth + PLATE_PAD_X
  const y0 = data.y - size / 2 - PLATE_PAD_Y
  const y1 = data.y + size / 2 + PLATE_PAD_Y
  const r = Math.min(PLATE_CORNER, (y1 - y0) / 2)

  context.save()
  context.beginPath()
  context.moveTo(x0 + r, y0)
  context.lineTo(x1 - r, y0)
  context.arc(x1 - r, y0 + r, r, -Math.PI / 2, 0)
  context.lineTo(x1, y1 - r)
  context.arc(x1 - r, y1 - r, r, 0, Math.PI / 2)
  context.lineTo(x0 + r, y1)
  context.arc(x0 + r, y1 - r, r, Math.PI / 2, Math.PI)
  context.lineTo(x0, y0 + r)
  context.arc(x0 + r, y0 + r, r, Math.PI, (3 * Math.PI) / 2)
  context.closePath()
  context.fillStyle = chrome.fill
  context.shadowOffsetX = 0
  context.shadowOffsetY = 0
  context.shadowBlur = 6
  context.shadowColor = chrome.shadow
  context.fill()
  context.shadowBlur = 0
  if (chrome.plateStroke) {
    context.strokeStyle = chrome.plateStroke
    context.lineWidth = 1
    context.stroke()
  }
  context.restore()
  drawPlatedLabel(context, data, settings, chrome.text)
}

/** Themed replacement for sigma's `drawDiscNodeHover`: a ring round the node
 *  and the label on its own plate. */
export function drawThemedDiscNodeHover(
  context: CanvasRenderingContext2D,
  data: PartialButFor<NodeDisplayData, "x" | "y" | "size" | "label" | "color">,
  settings: Settings,
  tokens: GraphThemeTokens,
  color: SelectionColor,
  kind: ChromeKind,
): void {
  const chrome = hoverChrome(tokens, color, kind, data.color)
  drawLabelPlate(context, data, settings, chrome)
  drawFocusRing(context, data.x, data.y, data.size, chrome, "circle")
}
