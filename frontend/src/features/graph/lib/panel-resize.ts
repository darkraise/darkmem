/**
 * The canvas/detail split, in pixels.
 *
 * ## Why this is not `darkraise-ui/components/resizable`
 *
 * The library's group allocates in percentages and renormalises whenever the
 * set of panels changes: a panel joining a group whose remaining panel already
 * holds 100% is scaled to `size / (100 + size)`, so a 45% panel reopens at 31%
 * and — once that value is persisted — narrows again on every open. There is no
 * prop that makes room for a joining panel instead, and the detail panel
 * genuinely mounts and unmounts with the selection.
 *
 * Pixels are also the unit the requirement is stated in: the canvas must keep a
 * readable width, which is a pixel fact about the graph, not a share of a
 * window that might be 900px or 3400px wide.
 *
 * Retire this the moment the library grows a panel that can join a group
 * without rescaling its siblings.
 */

/** Narrower than this and the summary's own rows start truncating. */
export const DETAIL_PANEL_MIN_WIDTH = 260

/** What the canvas keeps no matter how far the handle is dragged. */
export const GRAPH_MIN_WIDTH = 420

export const DEFAULT_DETAIL_PANEL_WIDTH = 320

/**
 * The width the panel may actually take right now.
 *
 * Both floors are honoured, and the canvas wins when the container is too
 * narrow to satisfy both: a panel that has eaten the graph is useless, while a
 * panel below its own minimum is merely cramped.
 */
export function clampPanelWidth(
  requested: number,
  containerWidth: number,
): number {
  if (!Number.isFinite(requested)) return DEFAULT_DETAIL_PANEL_WIDTH
  const ceiling = containerWidth - GRAPH_MIN_WIDTH
  if (ceiling <= DETAIL_PANEL_MIN_WIDTH) {
    return Math.max(0, Math.min(DETAIL_PANEL_MIN_WIDTH, ceiling))
  }
  return Math.max(DETAIL_PANEL_MIN_WIDTH, Math.min(ceiling, requested))
}

/** Panel width for a pointer at `clientX`, given the container's right edge. */
export function widthFromPointer(
  clientX: number,
  containerRight: number,
  containerWidth: number,
): number {
  return clampPanelWidth(containerRight - clientX, containerWidth)
}
