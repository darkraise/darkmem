import type { DemoMemory } from "@/demo/types"

export interface MemoryTimelineEntry {
  id: string
  excerpt: string
  time: string
  status: DemoMemory["status"]
}

export interface MemoryTimelineGroup {
  /** Local calendar day, YYYY-MM-DD — stable React key. */
  key: string
  /** "Today" / "Yesterday" / a formatted date. */
  label: string
  entries: MemoryTimelineEntry[]
}

const EXCERPT_LEN = 64

function dayKey(d: Date): string {
  const m = String(d.getMonth() + 1).padStart(2, "0")
  const day = String(d.getDate()).padStart(2, "0")
  return `${d.getFullYear()}-${m}-${day}`
}

function dayLabel(d: Date, now: Date): string {
  const today = dayKey(now)
  const yesterday = dayKey(new Date(now.getTime() - 86_400_000))
  const key = dayKey(d)
  if (key === today) return "Today"
  if (key === yesterday) return "Yesterday"
  return d.toLocaleDateString(undefined, {
    day: "numeric",
    month: "short",
    year: d.getFullYear() === now.getFullYear() ? undefined : "numeric",
  })
}

/**
 * Group memories into per-day timeline buckets, most-recent first — the
 * left-rail navigation model for the Memories browse/search surface. Input
 * order does not matter; the result is always chronological (desc).
 */
export function groupMemoriesByDay(
  memories: DemoMemory[],
  now: Date = new Date(),
): MemoryTimelineGroup[] {
  const sorted = [...memories].sort((a, b) =>
    b.created_at.localeCompare(a.created_at),
  )
  const groups: MemoryTimelineGroup[] = []
  for (const memory of sorted) {
    const at = new Date(memory.created_at)
    const key = dayKey(at)
    const entry: MemoryTimelineEntry = {
      id: memory.id,
      excerpt:
        memory.content.length > EXCERPT_LEN
          ? `${memory.content.slice(0, EXCERPT_LEN).trimEnd()}…`
          : memory.content,
      time: at.toLocaleTimeString(undefined, {
        hour: "2-digit",
        minute: "2-digit",
      }),
      status: memory.status,
    }
    const last = groups[groups.length - 1]
    if (last && last.key === key) {
      last.entries.push(entry)
    } else {
      groups.push({ key, label: dayLabel(at, now), entries: [entry] })
    }
  }
  return groups
}
