import { blendHex } from "./graph-colors"

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
  return blendHex(color, background, 1 - strength)
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
