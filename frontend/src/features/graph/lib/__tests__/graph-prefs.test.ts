import { describe, it, expect, beforeEach } from "vitest"
import {
  useGraphPrefs,
  DIM_MIN,
  DIM_MAX,
  DEFAULT_TREATMENT,
  DEFAULT_DIM,
} from "../graph-prefs"

describe("graphPrefs", () => {
  beforeEach(() => {
    localStorage.clear()
    useGraphPrefs.setState({
      selectionTreatment: DEFAULT_TREATMENT,
      dimUnrelated: DEFAULT_DIM,
    })
  })

  it("defaults to the halo treatment at 15% dim", () => {
    expect(useGraphPrefs.getState().selectionTreatment).toBe("halo")
    expect(useGraphPrefs.getState().dimUnrelated).toBe(15)
  })

  it("setSelectionTreatment records the choice", () => {
    useGraphPrefs.getState().setSelectionTreatment("invert")
    expect(useGraphPrefs.getState().selectionTreatment).toBe("invert")
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
    useGraphPrefs.getState().setSelectionTreatment("keyline")
    useGraphPrefs.getState().setDimUnrelated(25)
    const stored = JSON.parse(localStorage.getItem("darkmem-graph-prefs") ?? "{}")
    expect(stored.state.selectionTreatment).toBe("keyline")
    expect(stored.state.dimUnrelated).toBe(25)
  })
})
