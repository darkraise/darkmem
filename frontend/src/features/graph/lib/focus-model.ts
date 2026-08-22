/**
 * The three-tier focus model the graph renderers share.
 *
 * Selecting a node sorts the canvas into the node itself, its neighbourhood,
 * and everything else. The last of those recedes but is never repainted: it
 * keeps its hue and its position, so the surrounding map stays readable as
 * context rather than collapsing into flat grey.
 */
export type FocusTier = "none" | "focus" | "adjacent" | "ground"

export function focusTier(
  nodeId: string,
  focusId: string | null,
  isNeighbour: boolean,
): FocusTier {
  if (!focusId) return "none"
  if (nodeId === focusId) return "focus"
  return isNeighbour ? "adjacent" : "ground"
}

/** Opacity of a grounded node — the dim preference, as a fraction. */
export function groundNodeAlpha(dimPercent: number): number {
  return dimPercent / 100
}

/**
 * Strength of the ground while hovering with nothing selected.
 *
 * Hovering sorts the canvas the same way a selection does, but it is a
 * transient gesture rather than a committed one, so it recedes half as far --
 * twice the configured strength left standing.
 */
export function hoverGroundAlpha(dimPercent: number): number {
  return Math.min(1, groundNodeAlpha(dimPercent) * 2)
}

/**
 * Opacity of a grounded edge.
 *
 * Derived from the same number rather than carried separately: two knobs for
 * one idea eventually disagree about how far back "back" is. The factor keeps
 * edges under the nodes they join at every setting, which is what stops a
 * dimmed region reading as a mesh.
 */
const GROUND_EDGE_FACTOR = 0.35

export function groundEdgeAlpha(dimPercent: number): number {
  return groundNodeAlpha(dimPercent) * GROUND_EDGE_FACTOR
}

/**
 * Push a colour back toward the ground it sits on.
 *
 * Not alpha. Sigma blends premultiplied — `gl.ONE, gl.ONE_MINUS_SRC_ALPHA` —
 * so a colour carrying a low alpha still contributes at full intensity:
 * `result = src + dst * (1 - a)`. Against a dark page `dst` is ~0, so the node
 * renders as bright as an undimmed one and nothing recedes at all. Against a
 * light page it washes toward white and merely looks like it worked.
 *
 * Blending toward the background instead is independent of the blend mode,
 * keeps the hue that is carrying cluster or type, and is correct in both
 * themes by construction rather than by a per-theme number.
 */
export function recede(color: string, background: string, strength: number): string {
  const src = parseChannels(color)
  const bg = parseChannels(background)
  if (!src || !bg) return background

  // Composite the source over the ground using its own alpha first, then push
  // it back by `strength`. Relation and membership edges carry rgba() rather
  // than hex, so ignoring alpha here would make a faint edge recede as if it
  // were solid.
  const keep = src.a * strength
  const mix = (c: keyof Channels) =>
    Math.round(Number(src[c]) * keep + Number(bg[c]) * (1 - keep))

  return `#${[mix("r"), mix("g"), mix("b")]
    .map((v) => Math.max(0, Math.min(255, v)).toString(16).padStart(2, "0"))
    .join("")}`
}

interface Channels {
  r: number
  g: number
  b: number
  a: number
}

/** Hex or rgb()/rgba(). Anything else returns null, and the caller falls back
 *  to the ground rather than emitting a colour built from NaN. */
function parseChannels(color: string): Channels | null {
  const value = color.trim()

  if (value.startsWith("#")) {
    const hex =
      value.length === 4
        ? value
            .slice(1)
            .split("")
            .map((c) => c + c)
            .join("")
        : value.slice(1)
    if (hex.length < 6) return null
    const r = parseInt(hex.slice(0, 2), 16)
    const g = parseInt(hex.slice(2, 4), 16)
    const b = parseInt(hex.slice(4, 6), 16)
    const a = hex.length >= 8 ? parseInt(hex.slice(6, 8), 16) / 255 : 1
    if ([r, g, b].some(Number.isNaN)) return null
    return { r, g, b, a }
  }

  const m = value.match(
    /^rgba?\(\s*([\d.]+)[\s,]+([\d.]+)[\s,]+([\d.]+)(?:[\s,/]+([\d.]+))?\s*\)$/i,
  )
  if (!m) return null
  const [r, g, b] = [Number(m[1]), Number(m[2]), Number(m[3])]
  if ([r, g, b].some(Number.isNaN)) return null
  return { r, g, b, a: m[4] === undefined ? 1 : Number(m[4]) }
}

export interface LabelContext {
  tier: FocusTier
  isHub: boolean
  zoomedIn: boolean
  isHovered: boolean
}

/**
 * Labels arrive in tiers rather than all at once.
 *
 * Hubs stay legible at every scale; ordinary nodes wait until you are close
 * enough to read them. Focusing overrides zoom for the neighbourhood, because
 * focusing *is* the request to read it.
 */
export function labelVisible({
  tier,
  isHub,
  zoomedIn,
  isHovered,
}: LabelContext): boolean {
  // Hover first: pointing at a node is a direct request to know what it is,
  // and it must outrank the ground rule that would otherwise swallow it while
  // something else is selected.
  if (isHovered) return true
  if (tier === "ground") return false
  if (tier === "focus" || tier === "adjacent") return true
  return isHub || zoomedIn
}
