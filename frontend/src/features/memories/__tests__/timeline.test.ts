import { describe, expect, it } from "vitest"
import { groupMemoriesByDay } from "../timeline"
import type { DemoMemory } from "@/demo/types"

function mem(id: string, created_at: string, content = `content ${id}`) {
  return { id, created_at, content, status: "active" } as DemoMemory
}

const NOW = new Date("2026-07-25T12:00:00")

describe("groupMemoriesByDay", () => {
  it("groups by local day, most-recent first, regardless of input order", () => {
    const groups = groupMemoriesByDay(
      [
        mem("a", "2026-07-23T09:00:00"),
        mem("c", "2026-07-25T08:30:00"),
        mem("b", "2026-07-25T10:15:00"),
      ],
      NOW,
    )
    expect(groups.map((g) => g.key)).toEqual(["2026-07-25", "2026-07-23"])
    expect(groups[0]?.entries.map((e) => e.id)).toEqual(["b", "c"])
    expect(groups[1]?.entries.map((e) => e.id)).toEqual(["a"])
  })

  it("labels today and yesterday relative to now", () => {
    const groups = groupMemoriesByDay(
      [
        mem("t", "2026-07-25T01:00:00"),
        mem("y", "2026-07-24T23:00:00"),
        mem("o", "2026-07-01T12:00:00"),
      ],
      NOW,
    )
    expect(groups.map((g) => g.label).slice(0, 2)).toEqual([
      "Today",
      "Yesterday",
    ])
    expect(groups[2]?.label).not.toBe("Yesterday")
  })

  it("truncates long content into an excerpt with an ellipsis", () => {
    const long = "x".repeat(120)
    const groups = groupMemoriesByDay([mem("l", "2026-07-25T09:00:00", long)], NOW)
    const excerpt = groups[0]?.entries[0]?.excerpt ?? ""
    expect(excerpt.endsWith("…")).toBe(true)
    expect(excerpt.length).toBeLessThan(70)
  })
})
