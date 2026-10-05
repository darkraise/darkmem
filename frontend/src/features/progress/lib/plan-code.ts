/**
 * A plan's code: the short, stable prefix that makes "Task 6" of a plan a
 * reference unique across the project (`CRF-6`).
 *
 * Derived from the filename alone, never from the plan's content or from
 * which other documents happen to be loaded, so a reference written into a
 * commit message or a ledger line still names the same task next month.
 *
 *     2026-10-03-comprehensive-review-fixes.md    → CRF
 *     2026-09-23-work-log-increment-1-store-and-verbs.md → WLI1SV
 *     2026-07-31-t2.26-groundedness-judge.md       → T226GJ
 *
 * The leading date is dropped and connective words contribute nothing. A
 * word contributes its first letter plus every digit it carries (`b3` → `B3`,
 * `t2.26` → `T226`, `phase5` → `P5`): an increment number or a task id is what
 * tells two otherwise alike plans apart. A word that starts with a digit
 * contributes itself (`3d` → `3D`, `1a` → `1A`).
 */

const DATE_PREFIX = /^\d{4}-\d{2}-\d{2}-/
const SKIPPED = new Set(["a", "an", "and", "the", "of", "to", "for", "in", "on", "with", "from", "by", "plan"])

export function planStem(filename: string): string {
  return filename.replace(/\.md$/i, "").replace(DATE_PREFIX, "")
}

export function derivePlanCode(filename: string): string {
  const words = planStem(filename)
    .split(/[-_\s]+/)
    .filter((w) => w && !SKIPPED.has(w.toLowerCase()))

  const code = words
    .map((w) => (/^\d/.test(w) ? w : w.charAt(0) + w.replace(/\D/g, "")))
    .join("")
    .toUpperCase()
    .replace(/[^A-Z0-9]/g, "")

  return code || "PLAN"
}

/**
 * Codes for a project's plans, unique among them.
 *
 * Two plans whose names abbreviate alike are told apart by a numeric suffix
 * in filename order. Filenames lead with their date, so a newly written plan
 * sorts last and takes the next suffix without moving anyone else's code. A
 * suffix does depend on the set of filed plans, though: unfiling, renaming or
 * back-dating one of `XY`, `XY2`, `XY3` renumbers the later ones. No two of
 * this repository's plans abbreviate alike today, so no suffix is in play.
 */
export function assignPlanCodes(filenames: string[]): Map<string, string> {
  const codes = new Map<string, string>()
  const taken = new Set<string>()

  for (const filename of [...filenames].sort()) {
    const base = derivePlanCode(filename)
    let code = base
    for (let n = 2; taken.has(code); n++) code = `${base}${n}`
    taken.add(code)
    codes.set(filename, code)
  }
  return codes
}
