type Positioned = {
  forEachNode(callback: (id: string, attrs: Record<string, unknown>) => void): void
  hasNode(id: string): boolean
}

/** Keeps where every node of `graph` sits, so a rebuild can start from it. */
export function rememberPositions(
  settled: Map<string, { x: number; y: number }>,
  graph: Positioned,
): void {
  graph.forEachNode((id, attrs) => {
    const x = attrs.x as number
    const y = attrs.y as number
    if (Number.isFinite(x) && Number.isFinite(y)) settled.set(id, { x, y })
  })
}

/** Drops what no longer appears in `graph`, so filtering a large graph down
 *  does not keep every position it ever drew. */
export function forgetUndrawn(
  settled: Map<string, { x: number; y: number }>,
  graph: Positioned,
): void {
  for (const id of settled.keys()) {
    if (!graph.hasNode(id)) settled.delete(id)
  }
}
