export type MemoryEdgeKind = "memory" | "relation" | "membership"

/** Emphasis is a flat width, not a per-kind multiple. Scaling each kind by
 *  the same factor made connected relation edges visibly heavier than
 *  connected similarity ones, which reads as "some of these matter more"
 *  rather than as one highlight. Hovering stays lighter than selecting so the
 *  two remain distinguishable while a selection is held. */
export const HOVER_EDGE_SIZE = 2.4
export const SELECTED_EDGE_SIZE = 3.2

/** Memory-to-memory similarity is what this page is about, so it carries the
 *  heaviest line; the entity overlay's own edges sit under it. The knowledge
 *  graph keeps the opposite order on purpose -- there entities ARE the
 *  subject -- so its copy of this rule is not the same rule. */
export function restEdgeSize(kind: unknown): number {
  if (kind === "relation") return 1.2
  if (kind === "membership") return 0.8
  return 1.6
}

/** The width the memory canvas draws an edge at: selection beats hover,
 *  hover never thins an edge, and an unlit edge keeps its kind's rest width. */
export function memoryEdgeSize(
  kind: unknown,
  touches: { selected: boolean; hovered: boolean },
): number {
  let size = restEdgeSize(kind)
  if (touches.selected) size = SELECTED_EDGE_SIZE
  if (touches.hovered) size = Math.max(size, HOVER_EDGE_SIZE)
  return size
}
