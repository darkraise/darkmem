import { describe, expect, it } from "vitest"
import {
  ISLAND_LABEL_FOCUS_ALPHA,
  ISLAND_LABEL_MAX_CHARS,
  ISLAND_LABEL_MIN_RADIUS_PX,
  islandLabelAlpha,
  islandLabelInputs,
  islandLabelText,
  placeIslandLabels,
  type IslandLabelInput,
} from "../island-labels"

const viewport = { width: 1000, height: 800 }
/** A fixed-advance stand-in for canvas text metrics. */
const measure = (text: string, fontPx: number) => text.length * fontPx * 0.6

const island = (over: Partial<IslandLabelInput>): IslandLabelInput => ({
  key: "cluster:0",
  text: "Auth and sessions",
  count: 50,
  x: 500,
  y: 400,
  radiusPx: 80,
  ...over,
})

function overlaps(
  a: { x: number; y: number; width: number; height: number },
  b: { x: number; y: number; width: number; height: number },
) {
  return (
    Math.abs(a.x - b.x) * 2 < a.width + b.width && Math.abs(a.y - b.y) * 2 < a.height + b.height
  )
}

describe("island labels", () => {
  it("names each island at its centre", () => {
    const placed = placeIslandLabels(
      [island({}), island({ key: "cluster:1", text: "Backups", x: 200, y: 200 })],
      measure,
      viewport,
    )
    expect(placed.map((p) => [p.key, p.x, p.y])).toEqual([
      ["cluster:0", 500, 400],
      ["cluster:1", 200, 200],
    ])
  })

  it("never lets two labels overlap: the larger island keeps its centre, the smaller moves a line", () => {
    const placed = placeIslandLabels(
      [
        island({ key: "small", count: 10, x: 510, y: 405 }),
        island({ key: "big", count: 90 }),
        island({ key: "far", count: 5, x: 100, y: 100 }),
      ],
      measure,
      viewport,
    )
    expect(placed.map((p) => p.key)).toEqual(["big", "small", "far"])
    const big = placed.find((p) => p.key === "big")!
    const small = placed.find((p) => p.key === "small")!
    expect([big.x, big.y]).toEqual([500, 400])
    expect(small.y).toBeLessThan(405)
    for (const a of placed) for (const b of placed) if (a !== b) expect(overlaps(a, b)).toBe(false)
  })

  it("tries above, then below, and drops a name with no free position", () => {
    const crowd = [
      island({ key: "a", count: 90 }),
      island({ key: "b", count: 80, x: 505 }),
      island({ key: "c", count: 70, x: 495 }),
      island({ key: "d", count: 60, x: 500 }),
    ]
    const placed = placeIslandLabels(crowd, measure, viewport)
    expect(placed.map((p) => p.key)).toEqual(["a", "b", "c"])
    const ys = Object.fromEntries(placed.map((p) => [p.key, p.y]))
    expect(ys.b!).toBeLessThan(400)
    expect(ys.c!).toBeGreaterThan(400)
    for (const a of placed) for (const b of placed) if (a !== b) expect(overlaps(a, b)).toBe(false)
  })

  it("draws a larger island's name in a larger font, within 11 to 15 px", () => {
    const placed = placeIslandLabels(
      [island({ key: "big", count: 400 }), island({ key: "small", count: 4, x: 100, y: 100 })],
      measure,
      viewport,
    )
    const font = Object.fromEntries(placed.map((p) => [p.key, p.fontPx]))
    expect(font.big).toBe(15)
    expect(font.small).toBeGreaterThanOrEqual(11)
    expect(font.small).toBeLessThan(font.big!)
  })

  it("leaves an island too small on screen unnamed, until zooming in grows it", () => {
    const tiny = island({ radiusPx: ISLAND_LABEL_MIN_RADIUS_PX - 1 })
    expect(placeIslandLabels([tiny], measure, viewport)).toEqual([])
    expect(
      placeIslandLabels([{ ...tiny, radiusPx: ISLAND_LABEL_MIN_RADIUS_PX }], measure, viewport),
    ).toHaveLength(1)
  })

  it("pulls a name that would cross the canvas edge inside it, over its own island", () => {
    const [p] = placeIslandLabels([island({ x: 960, radiusPx: 80 })], measure, viewport)
    expect(p).toBeDefined()
    expect(p!.x + p!.width / 2).toBeLessThanOrEqual(viewport.width)
    expect(960 - p!.x).toBeLessThanOrEqual(80)
  })

  it("keeps a name out of the toolbar band at the top of the canvas", () => {
    const [p] = placeIslandLabels([island({ y: 30 })], measure, { ...viewport, top: 48 })
    expect(p).toBeDefined()
    expect(p!.y - p!.height / 2).toBeGreaterThanOrEqual(48)
    expect(placeIslandLabels([island({ y: 30, radiusPx: 24 })], measure, { ...viewport, top: 48 })).toEqual([])
  })

  it("skips an island whose label would sit off screen", () => {
    expect(placeIslandLabels([island({ x: -200 })], measure, viewport)).toEqual([])
    expect(placeIslandLabels([island({ y: 900 })], measure, viewport)).toEqual([])
  })

  it("cuts a long name with an ellipsis and keeps a short one whole", () => {
    expect(islandLabelText("Backups")).toBe("Backups")
    const long = "Graph renderer island packing, thin edges, selection chrome and labels"
    const cut = islandLabelText(long)
    expect(cut.length).toBe(ISLAND_LABEL_MAX_CHARS)
    expect(cut.endsWith("…")).toBe(true)
    expect(islandLabelText("  spaced   out  ")).toBe("spaced out")
  })

  it("keeps names at full strength unless something is selected", () => {
    expect(islandLabelAlpha(false)).toBe(1)
    expect(islandLabelAlpha(true)).toBe(ISLAND_LABEL_FOCUS_ALPHA)
  })

  it("builds one input per clustered island: derived name, else Cluster <id>; the loose island unnamed", () => {
    const groups = [
      { key: "cluster:3", loose: false, radius: 10, members: ["a", "b", "c"] },
      { key: "cluster:7", loose: false, radius: 5, members: ["d"] },
      { key: "loose", loose: true, radius: 40, members: ["e", "f"] },
    ]
    const centres = new Map([
      ["cluster:3", { x: 0, y: 0 }],
      ["cluster:7", { x: 20, y: 0 }],
      ["loose", { x: 0, y: 50 }],
    ])
    const toViewport = (p: { x: number; y: number }) => ({ x: 100 + 3 * p.x, y: 100 - 3 * p.y })
    const inputs = islandLabelInputs(groups, centres, { "3": "Auth and sessions" }, toViewport)
    expect(inputs).toEqual([
      { key: "cluster:3", text: "Auth and sessions", count: 3, x: 100, y: 100, radiusPx: 30 },
      { key: "cluster:7", text: "Cluster 7", count: 1, x: 160, y: 100, radiusPx: 15 },
    ])
  })

  it("names nothing for an empty graph", () => {
    expect(islandLabelInputs([], new Map(), {}, (p) => p)).toEqual([])
    expect(placeIslandLabels([], measure, viewport)).toEqual([])
  })
})
