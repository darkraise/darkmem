/** One stored argument as text. The server already minimised it, so a
 *  `{chars}`/`{items}` object reads as a size, never as the value. */
export function formatArgument(value: unknown): string {
  if (value === null || value === undefined) return "null"
  if (typeof value === "string") return value
  if (typeof value === "number" || typeof value === "boolean")
    return String(value)
  if (Array.isArray(value)) return `[${value.map(formatArgument).join(", ")}]`
  if (typeof value === "object") {
    const o = value as Record<string, unknown>
    if (typeof o.chars === "number") return `‹${o.chars} chars›`
    if (typeof o.items === "number") return `‹${o.items} items›`
    if (typeof o.more === "number") return `+${o.more}`
    if (typeof o.present === "boolean") return o.present ? "‹set›" : "null"
  }
  return JSON.stringify(value)
}

export function formatArguments(args: Record<string, unknown>): string {
  return Object.entries(args)
    .map(([k, v]) => `${k}=${formatArgument(v)}`)
    .join("  ")
}
