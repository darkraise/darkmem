import { describe, expect, it } from "vitest"
import {
  MEMORY_SIZE_MAX,
  MEMORY_SIZE_MIN,
  UNIFORM_MEMORY_SIZE,
  memorySizes,
} from "../memory-size"

const none = new Map<string, number>()

/** The production corpus on 2026-11-20: importance 0.4 to 0.8, half at 0.6. */
function corpus() {
  const counts: [number, number][] = [
    [0.4, 3],
    [0.5, 19],
    [0.6, 51],
    [0.7, 25],
    [0.8, 2],
  ]
  return counts.flatMap(([importance, n]) =>
    Array.from({ length: n }, (_, i) => ({ id: `${importance}-${i}`, importance })),
  )
}

describe("memory sizes", () => {
  it("spreads a narrow band of importances across the whole size range", () => {
    const sizes = memorySizes("importance", corpus(), none)
    const at = (v: number) => sizes.get(`${v}-0`)!
    expect(at(0.8) / at(0.4)).toBeGreaterThanOrEqual(4)
    expect(at(0.4)).toBeLessThan(MEMORY_SIZE_MIN * 1.1)
    expect(at(0.8)).toBeGreaterThan(MEMORY_SIZE_MAX * 0.9)
  })

  it("grows each step of importance by 1.2x in area, and the steps round the median by 2x", () => {
    const sizes = memorySizes("importance", corpus(), none)
    const area = (lo: number, hi: number) =>
      (sizes.get(`${hi}-0`)! / sizes.get(`${lo}-0`)!) ** 2
    for (const [lo, hi] of [[0.4, 0.5], [0.5, 0.6], [0.6, 0.7], [0.7, 0.8]] as const) {
      expect(area(lo, hi)).toBeGreaterThanOrEqual(1.2)
    }
    expect(area(0.5, 0.6)).toBeGreaterThanOrEqual(2)
    expect(area(0.6, 0.7)).toBeGreaterThanOrEqual(2)
  })

  it("draws equal weights at one size and orders unequal ones", () => {
    const sizes = memorySizes("importance", corpus(), none)
    expect(sizes.get("0.6-0")).toBe(sizes.get("0.6-50"))
    const ordered = [0.4, 0.5, 0.6, 0.7, 0.8].map((v) => sizes.get(`${v}-0`)!)
    expect([...ordered].sort((a, b) => a - b)).toEqual(ordered)
  })

  it("draws a view where every weight is equal at the middle size", () => {
    const flat = [1, 2, 3].map((i) => ({ id: String(i), importance: 0.6 }))
    const sizes = memorySizes("importance", flat, none)
    const mid = sizes.get("1")!
    expect(mid).toBeGreaterThan(MEMORY_SIZE_MIN)
    expect(mid).toBeLessThan(MEMORY_SIZE_MAX)
    expect(memorySizes("importance", flat.slice(0, 1), none).get("1")).toBe(mid)
  })

  it("ranks by connection count in connections mode", () => {
    const mems = ["a", "b", "c", "d"].map((id) => ({ id, importance: 0.5 }))
    const conns = new Map([
      ["a", 0],
      ["b", 1],
      ["c", 3],
      ["d", 40],
    ])
    const sizes = memorySizes("connections", mems, conns)
    expect(sizes.get("a")!).toBeLessThan(sizes.get("b")!)
    expect(sizes.get("b")!).toBeLessThan(sizes.get("c")!)
    expect(sizes.get("c")!).toBeLessThan(sizes.get("d")!)
  })

  it("draws every memory alike in uniform mode", () => {
    const sizes = memorySizes("uniform", corpus(), none)
    expect(new Set(sizes.values())).toEqual(new Set([UNIFORM_MEMORY_SIZE]))
  })
})
