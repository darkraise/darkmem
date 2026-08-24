import { describe, it, expect, beforeEach } from "vitest"
import { useGraphPrefs } from "../graph-prefs"
import {
  clampPanelWidth,
  widthFromPointer,
  panelLayout,
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
    // This is `clampPanelWidth`'s own retired policy, still exercised here
    // because `widthFromPointer` still calls it during a drag: the canvas
    // wins outright and the panel is squeezed toward zero. `panelLayout`
    // (below) is what actually lays the panel out on the page now, and
    // floats it instead once the container is this narrow -- see its own
    // doc comment.
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

describe("panelLayout", () => {
  const REQUESTED = DEFAULT_DETAIL_PANEL_WIDTH // 320

  it("splits normally in a comfortably wide container", () => {
    expect(panelLayout(REQUESTED, 900)).toEqual({
      width: REQUESTED,
      floating: false,
    })
  })

  // The exact threshold: both floors just barely coexist, so the panel is
  // pinned at its own minimum and the split still holds.
  it("still splits, pinned to its own floor, at the exact threshold", () => {
    expect(panelLayout(REQUESTED, GRAPH_MIN_WIDTH + DETAIL_PANEL_MIN_WIDTH)).toEqual({
      width: DETAIL_PANEL_MIN_WIDTH,
      floating: false,
    })
  })

  // One pixel narrower and no split can hold both floors at once.
  it("floats one pixel below the threshold", () => {
    const result = panelLayout(
      REQUESTED,
      GRAPH_MIN_WIDTH + DETAIL_PANEL_MIN_WIDTH - 1,
    )
    expect(result.floating).toBe(true)
    expect(result.width).toBeGreaterThanOrEqual(DETAIL_PANEL_MIN_WIDTH)
  })

  // This is the width the unfixed clampPanelWidth collapsed to 0 at.
  it("floats and never collapses to 0 at the old canvas floor", () => {
    const result = panelLayout(REQUESTED, GRAPH_MIN_WIDTH)
    expect(result.floating).toBe(true)
    expect(result.width).toBeGreaterThanOrEqual(DETAIL_PANEL_MIN_WIDTH)
    expect(result.width).toBeLessThanOrEqual(GRAPH_MIN_WIDTH * 0.85)
  })

  // 300 * 0.85 = 255, under the panel's own 260px floor: the floor wins, so
  // the panel is wider than the naive 85% cap here rather than unreadable.
  it("floors at its own minimum when 85% of the container is smaller still", () => {
    const result = panelLayout(REQUESTED, 300)
    expect(result.floating).toBe(true)
    expect(result.width).toBe(DETAIL_PANEL_MIN_WIDTH)
  })

  it("holds that floor regardless of how large the request is", () => {
    const result = panelLayout(2000, 300)
    expect(result.floating).toBe(true)
    expect(result.width).toBe(DETAIL_PANEL_MIN_WIDTH)
  })

  // The exact regression this fixes: a container that has not been measured
  // yet reports 0, and the unfixed floating branch returned
  // `Math.min(0, ...)` -- 0 -- for it. That is precisely the failure the
  // floating branch exists to remove, so it must never reproduce it.
  it("never returns 0 at a zero-width container", () => {
    const result = panelLayout(REQUESTED, 0)
    expect(result.floating).toBe(true)
    expect(result.width).toBe(DETAIL_PANEL_MIN_WIDTH)
  })

  // Once the container is wide enough that 85% of it clears the floor, the
  // cap is what actually governs -- distinct from the floor winning above.
  it("caps at 85% of the container once that exceeds the floor", () => {
    const result = panelLayout(2000, 600)
    expect(result.floating).toBe(true)
    expect(result.width).toBe(600 * 0.85)
  })

  // The unmeasured-container case the page actually passes on first render
  // (`splitWidth || Number.POSITIVE_INFINITY`). `clampPanelWidth(360,
  // Infinity)` above pins this for the retired function; this is the
  // function the page calls today.
  it("falls back to the requested width with no container measured", () => {
    expect(panelLayout(360, Number.POSITIVE_INFINITY)).toEqual({
      width: 360,
      floating: false,
    })
  })

  it("falls back to the default width for a non-numeric request", () => {
    expect(panelLayout(Number.NaN, 900)).toEqual({
      width: DEFAULT_DETAIL_PANEL_WIDTH,
      floating: false,
    })
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
