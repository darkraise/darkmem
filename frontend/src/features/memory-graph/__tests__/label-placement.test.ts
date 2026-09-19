import { describe, expect, it } from "vitest"
import { visibleLabelIds } from "../lib/label-placement"

describe("visibleLabelIds", () => {
  it("keeps labels that do not collide", () => {
    const ids = visibleLabelIds([
      { id: "a", x: 0, y: 0, text: "postgres" },
      { id: "b", x: 0, y: 40, text: "redis" },
    ])
    expect([...ids]).toEqual(["a", "b"])
  })

  it("hides a label that would overlap one already placed", () => {
    const ids = visibleLabelIds([
      { id: "a", x: 0, y: 0, text: "postgres" },
      { id: "b", x: 20, y: 4, text: "pgvector" },
      { id: "c", x: 200, y: 0, text: "redis" },
    ])
    expect([...ids]).toEqual(["a", "c"])
  })
})
