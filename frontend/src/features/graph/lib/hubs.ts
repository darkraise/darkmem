export function topHubs(
  degrees: ReadonlyMap<string, number>,
  share = 0.02,
  minDegree = 5,
): Set<string> {
  const qualified = [...degrees].filter(([, d]) => d >= minDegree)
  if (qualified.length === 0) return new Set()
  qualified.sort((a, b) => b[1] - a[1] || (a[0] < b[0] ? -1 : a[0] > b[0] ? 1 : 0))
  const count = Math.max(1, Math.floor(share * degrees.size))
  return new Set(qualified.slice(0, count).map(([id]) => id))
}
