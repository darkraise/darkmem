/** Money is stored as integer micro-USD end to end; only the display divides. */
export function formatUsd(micros: number): string {
  const dollars = micros / 1_000_000
  // Sub-cent spend is real spend. Rendering it as "$0.00" would tell an
  // operator a call was free when it was merely cheap, so small amounts keep
  // enough places to stay distinguishable from zero.
  if (dollars !== 0 && Math.abs(dollars) < 0.01) {
    return `$${dollars.toFixed(4)}`
  }
  return `$${dollars.toFixed(2)}`
}

export function formatTokens(count: number): string {
  if (count < 1_000) return String(count)
  if (count < 1_000_000) return `${(count / 1_000).toFixed(1)}k`
  return `${(count / 1_000_000).toFixed(2)}M`
}

export function formatRate(microsPerMtok: number): string {
  return `$${(microsPerMtok / 1_000_000).toFixed(2)}/Mtok`
}

/** What a breakdown row's cost cell should say.
 *
 * `SUM(cost_micros)` is 0 when every call in the group priced to NULL, so a
 * model with no rate renders as free -- the exact confusion the unpriced
 * count exists to prevent. A group that is *entirely* unmeasured or unpriced
 * says so instead of showing a total it does not have; a mixed group keeps its
 * number, which is a real floor, and carries the row's warning mark.
 */
export function costCell(row: {
  cost_micros: number
  calls: number
  unmeasured_calls: number
  unpriced_calls: number
}): string {
  if (row.calls > 0 && row.unmeasured_calls === row.calls) return "not measured"
  if (row.calls > 0 && row.unpriced_calls === row.calls) return "not priced"
  return formatUsd(row.cost_micros)
}
