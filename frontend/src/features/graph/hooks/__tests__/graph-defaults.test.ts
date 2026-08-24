import { describe, it, expect } from "vitest"
import { renderHook } from "@testing-library/react"
import { useGraphLayout } from "../use-graph-layout"
import { DEFAULT_COLOR_MODE } from "@/features/graph/lib/graph-colors"
import { DEFAULT_SIZE_MODE } from "@/features/graph/lib/graph-utils"
import { DEFAULT_HULL_MODE } from "@/features/graph/lib/graph-geometry"

// The graph opens on one encoding of each kind, and which one is a decision
// rather than whatever the segment lists first. Pinned so a reordered options
// array cannot quietly move it.
describe("graph encoding defaults", () => {
  it("colours by cluster", () => {
    expect(DEFAULT_COLOR_MODE).toBe("cluster")
  })

  it("draws no regions", () => {
    expect(DEFAULT_HULL_MODE).toBe("none")
  })

  it("sizes by weight", () => {
    expect(DEFAULT_SIZE_MODE).toBe("importance")
  })

  it("is what the layout hook actually starts on", () => {
    const { result } = renderHook(() => useGraphLayout())
    expect(result.current.sizeMode).toBe(DEFAULT_SIZE_MODE)
    expect(result.current.hullMode).toBe(DEFAULT_HULL_MODE)
  })
})
