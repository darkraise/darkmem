/**
 * The frontend's single source for the closed memory-type vocabulary.
 *
 * Mirrors `MEMORY_TYPES` in `backend/app/taxonomy.py`; the backend's
 * `test_taxonomy.py` parses this file and fails if the two lists drift. Every
 * filter, select, and legend renders from here rather than keeping its own
 * copy, because a component that missed a widening silently hides every row of
 * the new type instead of failing.
 */

export const MEMORY_TYPES = [
  "fact",
  "decision",
  "preference",
  "problem",
  "reference",
  "architecture",
  "milestone",
  "episodic",
  "procedural",
] as const

export type MemoryType = (typeof MEMORY_TYPES)[number]

const MEMORY_TYPE_LABELS: Record<MemoryType, string> = {
  fact: "Fact",
  decision: "Decision",
  preference: "Preference",
  problem: "Problem",
  reference: "Reference",
  architecture: "Architecture",
  milestone: "Milestone",
  episodic: "Episodic",
  procedural: "Procedural",
}

export function memoryTypeLabel(value: string): string {
  return MEMORY_TYPE_LABELS[value as MemoryType] ?? value
}

export const MEMORY_TYPE_OPTIONS: { value: MemoryType; label: string }[] =
  MEMORY_TYPES.map((value) => ({ value, label: MEMORY_TYPE_LABELS[value] }))
