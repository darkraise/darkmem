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
  if (tier === "ground") return false
  if (isHovered) return true
  if (tier === "focus" || tier === "adjacent") return true
  return isHub || zoomedIn
}
