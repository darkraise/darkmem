import type Sigma from "sigma"
import { hexToRgba } from "./graph-colors"

/** The Regions switch: off, or one region per cluster. */
export type HullMode = "none" | "cluster"

/** No regions by default: a hull per cluster over a dense graph hides the
 *  edges the canvas exists to show. */
export const DEFAULT_HULL_MODE: HullMode = "none"

export function convexHull(
  pts: { x: number; y: number }[],
): { x: number; y: number }[] {
  if (pts.length < 3) return pts
  const sorted = [...pts].sort((a, b) => a.x - b.x || a.y - b.y)
  const cross = (
    o: { x: number; y: number },
    a: { x: number; y: number },
    b: { x: number; y: number },
  ) => (a.x - o.x) * (b.y - o.y) - (a.y - o.y) * (b.x - o.x)
  const lower: { x: number; y: number }[] = []
  for (const p of sorted) {
    while (
      lower.length >= 2 &&
      // length >= 2 guarantees both indices are defined
      cross(lower[lower.length - 2]!, lower[lower.length - 1]!, p) <= 0
    )
      lower.pop()
    lower.push(p)
  }
  const upper: { x: number; y: number }[] = []
  for (const p of [...sorted].reverse()) {
    while (
      upper.length >= 2 &&
      // length >= 2 guarantees both indices are defined
      cross(upper[upper.length - 2]!, upper[upper.length - 1]!, p) <= 0
    )
      upper.pop()
    upper.push(p)
  }
  upper.pop()
  lower.pop()
  return lower.concat(upper)
}

export interface Point {
  x: number
  y: number
}

/**
 * Where a region's name chip hangs.
 *
 * The topmost point of the territory — smallest y, since the viewport counts
 * downward — with ties broken leftward so the chip does not jitter between
 * two equally-high nodes as the layout settles.
 */
export function hullTopAnchor(points: Point[]): Point | null {
  let best: Point | null = null
  for (const p of points) {
    if (!best || p.y < best.y || (p.y === best.y && p.x < best.x)) best = p
  }
  return best
}

/** A region's name and its size. The name may be a derived cluster label or a
 *  bare group key; passing the key through is more honest than inventing a
 *  name for it. */
export function regionChipLabel(name: string, count: number): string {
  return `${name} \u00b7 ${count}`
}

/**
 * A group's convex hull in sigma's framed-graph space.
 *
 * The camera maps framed-graph space to the viewport by an affine transform,
 * which carries a hull's vertices onto the hull of the mapped points. So the
 * hull is recomputed only when the layout moves, and each frame maps just its
 * few vertices.
 */
export function framedHullVertices(sigma: Sigma, memberIds: string[]): Point[] {
  const points: Point[] = []
  for (const id of memberIds) {
    const data = sigma.getNodeDisplayData(id)
    if (data) points.push({ x: data.x, y: data.y })
  }
  return points.length < 3 ? points : convexHull(points)
}

/** Screen pixels a region outline keeps clear of its outermost members. */
export const REGION_PAD_PX = 22

export interface HullCorner {
  x: number
  y: number
  /** Canvas angles (y down), swept clockwise on screen from `from` to `to`. */
  from: number
  to: number
}

/**
 * The corners of a convex hull grown by a padding: the shape every point
 * within that distance of the hull covers. Its outline is the hull's edges pushed out along
 * their normals, joined by a circular arc round each vertex, so it is smooth
 * and convex at any vertex spacing. Two points give a capsule, one a circle.
 */
export function roundedHullCorners(points: readonly Point[]): HullCorner[] {
  const pts: Point[] = []
  for (const p of points) {
    const last = pts[pts.length - 1]
    if (!last || Math.hypot(p.x - last.x, p.y - last.y) > 1e-6) pts.push(p)
  }
  if (pts.length > 1) {
    const first = pts[0]!
    const last = pts[pts.length - 1]!
    if (Math.hypot(first.x - last.x, first.y - last.y) <= 1e-6) pts.pop()
  }
  if (pts.length === 0) return []
  if (pts.length === 1) return [{ ...pts[0]!, from: 0, to: 2 * Math.PI }]
  let area2 = 0
  for (let i = 0; i < pts.length; i++) {
    const a = pts[i]!
    const b = pts[(i + 1) % pts.length]!
    area2 += a.x * b.y - b.x * a.y
  }
  // Walk the hull clockwise on screen, so each edge's outward normal is (dy, -dx).
  if (area2 < 0) pts.reverse()
  const n = pts.length
  const normal = (a: Point, b: Point) => Math.atan2(-(b.x - a.x), b.y - a.y)
  const corners: HullCorner[] = []
  for (let i = 0; i < n; i++) {
    const prev = pts[(i - 1 + n) % n]!
    const cur = pts[i]!
    const next = pts[(i + 1) % n]!
    const from = normal(prev, cur)
    let to = normal(cur, next)
    while (to < from) to += 2 * Math.PI
    corners.push({ x: cur.x, y: cur.y, from, to })
  }
  return corners
}

export function drawFramedHull(
  ctx: CanvasRenderingContext2D,
  sigma: Sigma,
  framed: Point[],
  color: string,
  fillAlpha: number,
  strokeAlpha: number,
): Point[] {
  const positions = framed.map((p) => sigma.framedGraphToViewport(p))
  if (positions.length < 2) return positions
  ctx.save()
  ctx.beginPath()
  for (const c of roundedHullCorners(positions)) {
    ctx.arc(c.x, c.y, REGION_PAD_PX, c.from, c.to, false)
  }
  ctx.closePath()
  ctx.fillStyle = hexToRgba(color, fillAlpha)
  ctx.fill()
  ctx.strokeStyle = hexToRgba(color, strokeAlpha)
  ctx.lineWidth = 1
  ctx.stroke()
  ctx.restore()
  return positions
}

/**
 * Hull groups and their framed-space shapes, recomputed only when they can
 * have changed.
 *
 * Groups depend on the memories and the mode, so they are rebuilt only when
 * either identity moves. Shapes depend on node positions, which move only
 * while the layout runs: they refresh at most every `refreshMs` then, and
 * once more after `invalidate`.
 */
export function createHullShapeCache<M>(
  computeGroups: (memories: M[], mode: HullMode) => Map<string, string[]>,
  refreshMs: number,
) {
  let groupsFor: { memories: M[]; mode: HullMode } | null = null
  let groups = new Map<string, string[]>()
  const shapes = new Map<string, Point[]>()
  let shapesAt = -Infinity
  let stale = true
  return {
    update(
      memories: M[],
      mode: HullMode,
      sigma: Sigma,
      layoutRunning: boolean,
      now: number,
    ): Map<string, string[]> {
      if (
        !groupsFor ||
        groupsFor.memories !== memories ||
        groupsFor.mode !== mode
      ) {
        groups = computeGroups(memories, mode)
        groupsFor = { memories, mode }
        stale = true
      }
      if (stale || (layoutRunning && now - shapesAt >= refreshMs)) {
        shapes.clear()
        for (const [groupKey, members] of groups) {
          shapes.set(groupKey, framedHullVertices(sigma, members))
        }
        shapesAt = now
        stale = false
      }
      return groups
    },
    shape(groupKey: string): Point[] {
      return shapes.get(groupKey) ?? []
    },
    invalidate(): void {
      stale = true
    },
  }
}

export const REGION_CHIP_HEIGHT = 17
export const REGION_CHIP_FONT_PX = 10
const CHIP_GAP = 6
const CHIP_MARGIN = 4

export interface RegionChipInput {
  key: string
  text: string
  count: number
  /** Chip width in pixels, text measured plus padding. */
  width: number
  /** The region outline's top point and extents, in viewport pixels. */
  top: Point
  left: number
  right: number
  bottom: number
}

export interface PlacedRegionChip {
  key: string
  text: string
  x: number
  y: number
  width: number
  height: number
}

/**
 * Where each region's chip goes this frame: just inside the outline's top,
 * above its topmost members, larger regions first. Inside, not hung above:
 * packed regions touch, and a chip in the gap reads as its neighbour's. A chip is pulled inside the canvas edges and below
 * the toolbar band; one that hits a placed chip moves below it. A chip that
 * no longer overlaps its own region's extent (the region is off screen), that
 * would fall below the canvas, or that still collides, is dropped.
 */
export function placeRegionChips(
  chips: readonly RegionChipInput[],
  viewport: { width: number; height: number; top?: number },
): PlacedRegionChip[] {
  const top = viewport.top ?? 0
  const h = REGION_CHIP_HEIGHT
  const ordered = [...chips].sort((a, b) => b.count - a.count || a.key.localeCompare(b.key))
  const placed: PlacedRegionChip[] = []
  const hit = (x: number, y: number, w: number) =>
    placed.find(
      (p) =>
        x < p.x + p.width + CHIP_MARGIN &&
        p.x < x + w + CHIP_MARGIN &&
        y < p.y + p.height + CHIP_MARGIN &&
        p.y < y + h + CHIP_MARGIN,
    )
  for (const chip of ordered) {
    const w = chip.width
    if (w + 2 * CHIP_MARGIN > viewport.width) continue
    const x = Math.min(Math.max(chip.top.x - w / 2, CHIP_MARGIN), viewport.width - w - CHIP_MARGIN)
    let y = Math.max(chip.top.y + CHIP_GAP, top + CHIP_MARGIN)
    const other = hit(x, y, w)
    if (other) y = other.y + other.height + CHIP_MARGIN
    const offRegion = y + h > chip.bottom || x + w < chip.left || x > chip.right
    if (offRegion || y + h > viewport.height - CHIP_MARGIN || hit(x, y, w)) continue
    placed.push({ key: chip.key, text: chip.text, x, y, width: w, height: h })
  }
  return placed
}

export function drawRegionChip(
  ctx: CanvasRenderingContext2D,
  chip: PlacedRegionChip,
  opts: { fill: string; stroke: string; text: string; font: string },
): void {
  ctx.save()
  ctx.font = `500 ${REGION_CHIP_FONT_PX}px ${opts.font}`
  ctx.beginPath()
  ctx.roundRect(chip.x, chip.y, chip.width, chip.height, chip.height / 2)
  ctx.fillStyle = opts.fill
  ctx.fill()
  ctx.strokeStyle = opts.stroke
  ctx.lineWidth = 1
  ctx.stroke()
  ctx.fillStyle = opts.text
  ctx.textAlign = "center"
  ctx.textBaseline = "middle"
  ctx.fillText(chip.text, chip.x + chip.width / 2, chip.y + chip.height / 2 + 0.5)
  ctx.restore()
}

export function computeHullGroups(
  memories: { id: string; cluster: number }[],
  hullMode: HullMode,
): Map<string, string[]> {
  const groups = new Map<string, string[]>()
  if (hullMode === "none") return groups
  for (const m of memories) {
    if (m.cluster < 0) continue
    const key = String(m.cluster)
    const arr = groups.get(key)
    if (arr) arr.push(m.id)
    else groups.set(key, [m.id])
  }
  return groups
}
