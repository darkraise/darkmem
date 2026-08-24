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
 * The width a pure split-pane clamp would give the panel.
 *
 * Both floors are honoured where the container can hold them both; below
 * that, the canvas's floor wins outright and the panel is squeezed toward
 * zero. That degenerate branch is what `panelLayout` exists to avoid — see
 * its doc comment — so this is no longer what lays the panel out on the
 * page. It survives for `widthFromPointer`, which only runs during an active
 * drag, itself only possible while the split is wide enough that dragging is
 * offered at all.
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

/**
 * The width the panel actually renders at, and whether it must float.
 *
 * Below `GRAPH_MIN_WIDTH + DETAIL_PANEL_MIN_WIDTH` no split satisfies both
 * floors, and `clampPanelWidth`'s answer to that — hand the canvas
 * everything, including squeezing the panel to 0 — makes the panel's own
 * close button disappear with it, with no way back short of a reload. (The
 * toolbar's reopen button is gated on the panel being closed at all, not on
 * its width, so it is absent whenever the panel is open regardless of size;
 * it was never the width's doing.)
 * Below the threshold the panel stops splitting the row with the canvas and
 * floats as an overlay on top of it instead, sized off the container rather
 * than off what the canvas leaves, so it is always visible and never eats
 * the graph.
 */
export function panelLayout(
  requested: number,
  containerWidth: number,
): { width: number; floating: boolean } {
  const safeRequested = Number.isFinite(requested)
    ? requested
    : DEFAULT_DETAIL_PANEL_WIDTH
  const floating = containerWidth - GRAPH_MIN_WIDTH < DETAIL_PANEL_MIN_WIDTH
  if (floating) {
    return {
      width: Math.min(
        containerWidth * 0.85,
        Math.max(DETAIL_PANEL_MIN_WIDTH, safeRequested),
      ),
      floating: true,
    }
  }
  const ceiling = containerWidth - GRAPH_MIN_WIDTH
  return {
    width: Math.max(DETAIL_PANEL_MIN_WIDTH, Math.min(ceiling, safeRequested)),
    floating: false,
  }
}

/** Panel width for a pointer at `clientX`, given the container's right edge. */
export function widthFromPointer(
  clientX: number,
  containerRight: number,
  containerWidth: number,
): number {
  return clampPanelWidth(containerRight - clientX, containerWidth)
}
