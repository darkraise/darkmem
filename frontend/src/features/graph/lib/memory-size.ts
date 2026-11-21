import type { SizeMode } from "./graph-utils"

export const MEMORY_SIZE_MIN = 10
export const MEMORY_SIZE_MAX = 46
export const UNIFORM_MEMORY_SIZE = 18
/** Above 1 most memories stay small and the heaviest few stand out. */
const SIZE_CURVE = 1.6

/** What a memory's size stands for in a weighted mode: its importance, or
 *  how many links it has. Both renderers size from it, each in its own
 *  units. */
export function sizeWeight(
  mode: Exclude<SizeMode, "uniform">,
  importance: number,
  connections: number,
): number {
  return mode === "importance" ? importance : connections
}

/**
 * Each memory's size from its rank among the memories the filters keep, not
 * from its raw weight. Importances cluster in a narrow band (0.5 to 0.7 for
 * nearly the whole corpus), and a linear map drew that band as one size;
 * ranking spreads it across the full range. Equal weights share a mid-rank,
 * so they share a size.
 */
export function memorySizes(
  mode: SizeMode,
  memories: readonly { id: string; importance: number }[],
  connections: ReadonlyMap<string, number>,
): Map<string, number> {
  const sizes = new Map<string, number>()
  if (mode === "uniform") {
    for (const m of memories) sizes.set(m.id, UNIFORM_MEMORY_SIZE)
    return sizes
  }
  const weight = (m: { id: string; importance: number }) =>
    sizeWeight(mode, m.importance, connections.get(m.id) ?? 0)
  const sorted = memories.map(weight).sort((a, b) => a - b)
  const n = sorted.length
  const percentile = new Map<number, number>()
  for (let i = 0; i < n; ) {
    let j = i
    while (j < n && sorted[j] === sorted[i]) j++
    percentile.set(sorted[i]!, (i + (j - i) / 2) / n)
    i = j
  }
  for (const m of memories) {
    const p = percentile.get(weight(m))!
    sizes.set(
      m.id,
      MEMORY_SIZE_MIN + (MEMORY_SIZE_MAX - MEMORY_SIZE_MIN) * p ** SIZE_CURVE,
    )
  }
  return sizes
}
