/** An SVG viewBox in user units. */
export interface ViewBox {
  x: number
  y: number
  w: number
  h: number
}

/** Zoom limits relative to the fitted (whole-graph) view. */
export const MIN_ZOOM = 0.5
export const MAX_ZOOM = 6

/** The current magnification of `view` against the fitted `base`. */
export function zoomLevel(view: ViewBox, base: ViewBox): number {
  return base.w / view.w
}

/**
 * Scale the view by `factor` (< 1 zooms in, > 1 zooms out) about the point
 * (px, py) in user units, so that point stays under the cursor/fingers.
 * The result is clamped to [MIN_ZOOM, MAX_ZOOM] against `base`.
 */
export function zoomViewAt(
  view: ViewBox,
  base: ViewBox,
  factor: number,
  px: number,
  py: number,
): ViewBox {
  const nextLevel = Math.min(
    MAX_ZOOM,
    Math.max(MIN_ZOOM, base.w / (view.w * factor)),
  )
  const applied = base.w / nextLevel / view.w
  return {
    x: px - (px - view.x) * applied,
    y: py - (py - view.y) * applied,
    w: view.w * applied,
    h: view.h * applied,
  }
}

/** Zoom about the view's centre (the +/- buttons). */
export function zoomViewCentered(
  view: ViewBox,
  base: ViewBox,
  factor: number,
): ViewBox {
  return zoomViewAt(
    view,
    base,
    factor,
    view.x + view.w / 2,
    view.y + view.h / 2,
  )
}

/** Move the view by (dx, dy) user units (a drag moves content the other way). */
export function panView(view: ViewBox, dx: number, dy: number): ViewBox {
  return { ...view, x: view.x - dx, y: view.y - dy }
}

export function viewBoxAttr(view: ViewBox): string {
  return `${view.x} ${view.y} ${view.w} ${view.h}`
}
