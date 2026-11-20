export const ISLAND_LABEL_MIN_RADIUS_PX = 24
export const ISLAND_LABEL_MAX_CHARS = 40
const FONT_MIN_PX = 11
const FONT_MAX_PX = 15
const LINE_HEIGHT = 1.4
const PAD_X = 6
const MARGIN = 4

export interface IslandLabelInput {
  key: string
  text: string
  count: number
  /** Island centre in viewport pixels. */
  x: number
  y: number
  radiusPx: number
}

export interface PlacedIslandLabel {
  key: string
  text: string
  x: number
  y: number
  fontPx: number
  width: number
  height: number
}

export function islandLabelText(name: string): string {
  const clean = name.trim().replace(/\s+/g, " ")
  if (clean.length <= ISLAND_LABEL_MAX_CHARS) return clean
  return clean.slice(0, ISLAND_LABEL_MAX_CHARS - 1).trimEnd() + "…"
}

/** Island names give way to a selection rather than compete with it. */
export const ISLAND_LABEL_FOCUS_ALPHA = 0.35

/** Names stay at every zoom and with Regions on: a region chip hangs off its
 *  hull's top edge and is often off screen, so it cannot stand in for them. */
export function islandLabelAlpha(hasSelection: boolean): number {
  return hasSelection ? ISLAND_LABEL_FOCUS_ALPHA : 1
}

/** One label input per clustered island, the loose island excepted. Island
 *  keys are `cluster:<id>`; derived names are keyed by the bare id. */
export function islandLabelInputs(
  groups: readonly {
    key: string
    loose: boolean
    radius: number
    members: readonly string[]
  }[],
  centres: ReadonlyMap<string, { x: number; y: number }>,
  names: Readonly<Record<string, string>>,
  toViewport: (p: { x: number; y: number }) => { x: number; y: number },
): IslandLabelInput[] {
  const inputs: IslandLabelInput[] = []
  for (const g of groups) {
    if (g.loose) continue
    const centre = centres.get(g.key)
    if (!centre) continue
    const c = toViewport(centre)
    const rim = toViewport({ x: centre.x + g.radius, y: centre.y })
    const id = g.key.slice(g.key.indexOf(":") + 1)
    inputs.push({
      key: g.key,
      text: islandLabelText(names[id] ?? `Cluster ${id}`),
      count: g.members.length,
      x: c.x,
      y: c.y,
      radiusPx: Math.hypot(rim.x - c.x, rim.y - c.y),
    })
  }
  return inputs
}

/**
 * Where each island's name goes this frame: at the island's centre, larger
 * islands first and in a larger font. A name that would overlap one already
 * placed tries just above, then just below, the name it hit. A name that
 * would cross the canvas edge, or run under the toolbar band at its top, is
 * pulled inside. Every position stays over
 * the island (within its radius of the centre); a name with no such free
 * position, or on an island too small to read, is dropped, and returns at a
 * view where the islands sit further apart.
 */
export function placeIslandLabels(
  islands: readonly IslandLabelInput[],
  measure: (text: string, fontPx: number) => number,
  viewport: { width: number; height: number; top?: number },
): PlacedIslandLabel[] {
  const top = viewport.top ?? 0
  const largest = Math.max(1, ...islands.map((i) => i.count))
  const ordered = [...islands].sort(
    (a, b) => b.count - a.count || a.key.localeCompare(b.key),
  )
  const placed: PlacedIslandLabel[] = []
  for (const island of ordered) {
    if (island.radiusPx < ISLAND_LABEL_MIN_RADIUS_PX || !island.text) continue
    const fontPx = Math.round(
      FONT_MIN_PX +
        (FONT_MAX_PX - FONT_MIN_PX) * Math.sqrt(island.count / largest),
    )
    const width = measure(island.text, fontPx) + 2 * PAD_X
    const height = fontPx * LINE_HEIGHT
    const clamp = (v: number, half: number, max: number) =>
      max < 2 * half ? v : Math.min(Math.max(v, half), max - half)
    const x = clamp(island.x, width / 2, viewport.width)
    const at = (y: number) => ({
      x,
      y: top + clamp(y - top, height / 2, viewport.height - top),
      width,
      height,
    })
    const near = (b: { x: number; y: number }) =>
      Math.hypot(b.x - island.x, b.y - island.y) <= island.radiusPx
    const hits = (p: PlacedIslandLabel, b: { x: number; y: number }) =>
      Math.abs(p.x - b.x) * 2 < p.width + width + 2 * MARGIN &&
      Math.abs(p.y - b.y) * 2 < p.height + height + 2 * MARGIN
    const fits = (b: { x: number; y: number }) =>
      near(b) &&
      b.x - width / 2 >= 0 &&
      b.x + width / 2 <= viewport.width &&
      b.y - height / 2 >= top &&
      b.y + height / 2 <= viewport.height &&
      !placed.some((p) => hits(p, b))
    let box: ReturnType<typeof at> | undefined = at(island.y)
    if (!fits(box)) {
      const hit = placed.find((p) => hits(p, box!))
      const clear = hit ? (hit.height + height) / 2 + MARGIN + 0.5 : 0
      box = hit ? [hit.y - clear, hit.y + clear].map(at).find(fits) : undefined
    }
    if (!box) continue
    placed.push({ key: island.key, text: island.text, ...box, fontPx })
  }
  return placed
}
