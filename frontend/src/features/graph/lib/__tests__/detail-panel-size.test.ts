import { describe, it, expect, beforeEach } from "vitest"
import { useGraphPrefs } from "../graph-prefs"
import {
  clampPanelWidth,
  widthFromPointer,
  DETAIL_PANEL_MIN_WIDTH,
  GRAPH_MIN_WIDTH,
  DEFAULT_DETAIL_PANEL_WIDTH,
} from "../panel-resize"

const WIDE = 1400

beforeEach(() => {
  useGraphPrefs.setState({ detailPanelWidth: DEFAULT_DETAIL_PANEL_WIDTH })
})

describe("clampPanelWidth", () => {
  it("honours a width both floors allow", () => {
    expect(clampPanelWidth(420, WIDE)).toBe(420)
  })

  it("opens at a width both floors allow", () => {
    expect(clampPanelWidth(DEFAULT_DETAIL_PANEL_WIDTH, WIDE)).toBe(
      DEFAULT_DETAIL_PANEL_WIDTH,
    )
  })

  // The whole point: dragging the edge across the canvas must stop at the
  // canvas's floor rather than squeezing it to nothing.
  it("stops the panel at the canvas floor", () => {
    expect(clampPanelWidth(1300, WIDE)).toBe(WIDE - GRAPH_MIN_WIDTH)
  })

  it("leaves the canvas its floor at every container width it fits in", () => {
    for (const container of [800, 1000, 1400, 2200, 3400]) {
      const panel = clampPanelWidth(Number.MAX_SAFE_INTEGER, container)
      expect(container - panel).toBeGreaterThanOrEqual(GRAPH_MIN_WIDTH)
    }
  })

  it("keeps the panel readable when it is dragged shut", () => {
    expect(clampPanelWidth(0, WIDE)).toBe(DETAIL_PANEL_MIN_WIDTH)
  })

  describe("a container too narrow for both floors", () => {
    // The canvas wins: a panel that has eaten the graph is useless, while a
    // panel under its own minimum is merely cramped.
    it("never lets the panel exceed what the canvas leaves", () => {
      const container = GRAPH_MIN_WIDTH + 100
      expect(clampPanelWidth(400, container)).toBe(100)
    })

    it("collapses rather than going negative", () => {
      expect(clampPanelWidth(400, GRAPH_MIN_WIDTH - 50)).toBe(0)
    })
  })

  // The panel renders before the container is measured; clamping against a
  // zero width there would collapse it on every mount.
  it("falls back to the requested width with no container measured", () => {
    expect(clampPanelWidth(360, Number.POSITIVE_INFINITY)).toBe(360)
  })

  it("returns the default for a width that is not a number", () => {
    expect(clampPanelWidth(Number.NaN, WIDE)).toBe(DEFAULT_DETAIL_PANEL_WIDTH)
  })
})

describe("widthFromPointer", () => {
  it("measures the panel from the pointer to the container's right edge", () => {
    expect(widthFromPointer(1000, 1500, WIDE)).toBe(500)
  })

  it("applies both floors to the dragged width", () => {
    expect(widthFromPointer(1490, 1500, WIDE)).toBe(DETAIL_PANEL_MIN_WIDTH)
    expect(widthFromPointer(100, 1500, WIDE)).toBe(WIDE - GRAPH_MIN_WIDTH)
  })
})

describe("the stored width", () => {
  it("keeps a width the panel can use", () => {
    useGraphPrefs.getState().setDetailPanelWidth(430)
    expect(useGraphPrefs.getState().detailPanelWidth).toBe(430)
  })

  it("refuses a width below the panel's own floor", () => {
    useGraphPrefs.getState().setDetailPanelWidth(40)
    expect(useGraphPrefs.getState().detailPanelWidth).toBe(
      DETAIL_PANEL_MIN_WIDTH,
    )
  })

  // Deliberately not clamped against the canvas here: a width chosen on a wide
  // monitor should come back in full on that monitor, not be rewritten by an
  // afternoon spent in a narrow window.
  it("keeps a width wider than a small window would allow", () => {
    useGraphPrefs.getState().setDetailPanelWidth(1200)
    expect(useGraphPrefs.getState().detailPanelWidth).toBe(1200)
    expect(clampPanelWidth(1200, 900)).toBe(900 - GRAPH_MIN_WIDTH)
  })

  it("ignores a width that is not a number", () => {
    useGraphPrefs.getState().setDetailPanelWidth(360)
    useGraphPrefs.getState().setDetailPanelWidth(Number.NaN)
    expect(useGraphPrefs.getState().detailPanelWidth).toBe(360)
  })

  it("persists alongside the other graph preferences", () => {
    useGraphPrefs.getState().setDetailPanelWidth(384)
    const stored = JSON.parse(
      localStorage.getItem("darkmem-graph-prefs") ?? "{}",
    )
    expect(stored.state.detailPanelWidth).toBe(384)
  })
})
