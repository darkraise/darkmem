/** Local calendar day key, YYYY-MM-DD — the click-to-date contract unit. */
export function localDayKey(d: Date): string {
  const m = String(d.getMonth() + 1).padStart(2, "0")
  const day = String(d.getDate()).padStart(2, "0")
  return `${d.getFullYear()}-${m}-${day}`
}

/** Local midday of a YYYY-MM-DD key — DST-safe anchor for that day. */
export function dayKeyToMs(key: string): number {
  const [y, m, d] = key.split("-").map(Number)
  return new Date(y ?? 1970, (m ?? 1) - 1, d ?? 1, 12).getTime()
}

export function formatDayKey(key: string): string {
  return new Date(dayKeyToMs(key)).toLocaleDateString(undefined, {
    weekday: "short",
    day: "numeric",
    month: "short",
    year: "numeric",
  })
}

export function relativeTime(iso: string): string {
  if (!iso) return ""
  const diff = Date.now() - new Date(iso).getTime()
  const mins = Math.floor(diff / 60000)
  if (mins < 1) return "just now"
  if (mins < 60) return `${mins}m ago`
  const hours = Math.floor(mins / 60)
  if (hours < 24) return `${hours}h ago`
  const days = Math.floor(hours / 24)
  return `${days}d ago`
}

/** "code and memory", "code, human and memory" — a list as a sentence
 *  rather than `[code, memory]`. */
export function formatList(items: readonly string[]): string {
  if (items.length <= 1) return items[0] ?? ""
  return `${items.slice(0, -1).join(", ")} and ${items[items.length - 1]}`
}

/** `relativeTime` for a value that must stay a plain string (a `meta` prop);
 *  a value that is not a date passes through as written. */
export function formatWhen(iso: string): string {
  return Number.isNaN(new Date(iso).getTime()) ? iso : relativeTime(iso)
}

export function formatDateTime(iso: string): string {
  return new Date(iso).toLocaleString(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  })
}

/** Milliseconds below a second, tenths below ten, then whole seconds. Each
 *  unit is rounded before it is split, so 59.6 s reads "1m 0s", never "60s". */
export function formatDuration(seconds: number): string {
  const ms = Math.round(seconds * 1000)
  if (ms < 1000) return `${ms}ms`
  const tenths = Math.round(seconds * 10) / 10
  if (tenths < 10) return `${tenths.toFixed(1)}s`
  const total = Math.round(seconds)
  if (total < 60) return `${total}s`
  return `${Math.floor(total / 60)}m ${total % 60}s`
}
