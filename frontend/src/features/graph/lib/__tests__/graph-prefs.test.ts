import { describe, it, expect, beforeEach } from "vitest"
import {
  useGraphPrefs,
  DIM_MIN,
  DIM_MAX,
  DEFAULT_SELECTION_COLOR,
  DEFAULT_DIM,
  NODE_LIMIT_DEFAULT,
} from "../graph-prefs"

describe("graphPrefs", () => {
  beforeEach(() => {
    localStorage.clear()
    useGraphPrefs.setState({
      selectionColor: DEFAULT_SELECTION_COLOR,
      dimUnrelated: DEFAULT_DIM,
    })
  })

  it("defaults to an accent halo at 15% dim", () => {
    expect(useGraphPrefs.getState().selectionColor).toBe("accent")
    expect(useGraphPrefs.getState().dimUnrelated).toBe(15)
  })

  it("setSelectionColor records the choice", () => {
    useGraphPrefs.getState().setSelectionColor("inverted")
    expect(useGraphPrefs.getState().selectionColor).toBe("inverted")
  })

  // Below the floor the ground is gone rather than dimmed, and above the
  // ceiling focus stops reading — so the store refuses both rather than
  // trusting every caller to bound it.
  it("clamps the dim level into the legible range", () => {
    useGraphPrefs.getState().setDimUnrelated(0)
    expect(useGraphPrefs.getState().dimUnrelated).toBe(DIM_MIN)

    useGraphPrefs.getState().setDimUnrelated(90)
    expect(useGraphPrefs.getState().dimUnrelated).toBe(DIM_MAX)
  })

  it("ignores a dim level that is not a number", () => {
    useGraphPrefs.getState().setDimUnrelated(30)
    useGraphPrefs.getState().setDimUnrelated(Number.NaN)
    expect(useGraphPrefs.getState().dimUnrelated).toBe(30)
  })

  it("persists under the darkmem-graph-prefs key", () => {
    useGraphPrefs.getState().setSelectionColor("inverted")
    useGraphPrefs.getState().setDimUnrelated(25)
    const stored = JSON.parse(localStorage.getItem("darkmem-graph-prefs") ?? "{}")
    expect(stored.state.selectionColor).toBe("inverted")
    expect(stored.state.dimUnrelated).toBe(25)
  })

  it("A11: defaults to 1,000 memories", () => {
    expect(NODE_LIMIT_DEFAULT).toBe(1000)
  })

  it("A11: a stored 200 from before version 1 loads as 1,000, and any other stored value is kept", async () => {
    for (const [stored, expected] of [[200, 1000], [500, 500], [50000, 50000]] as const) {
      localStorage.setItem("darkmem-graph-prefs", JSON.stringify({ state: { nodeLimit: stored }, version: 0 }))
      await useGraphPrefs.persist.rehydrate()
      expect(useGraphPrefs.getState().nodeLimit).toBe(expected)
    }
  })
})
