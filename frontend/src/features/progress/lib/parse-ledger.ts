import { TASK_ID, isLedgerStatus, type LedgerRow } from "../types"

const HEADER_PREFIX = "| Task | Title"

function cells(line: string): string[] {
  return line
    .trim()
    .replace(/^\|/, "")
    .replace(/\|$/, "")
    .split("|")
    .map((c) => c.trim())
}

/**
 * `progress.md`'s task tables → rows.
 *
 * The file carries one table per epic plus a per-epic summary table and a
 * status-legend table, so tables are located by their header text rather than
 * by position, and columns are mapped by header name so a column added to
 * `scripts/gen_progress.py` does not shift the parse.
 *
 * Two shapes in the real file that a naive split gets wrong:
 *
 * - Rows whose Task cell is not a task id (the summary and legend tables) are
 *   skipped rather than parsed into junk rows.
 * - Six rows carry an unescaped `|` inside their Review or Note prose, so they
 *   split into 12-14 cells against an 11-column header. Zipping would drop the
 *   tail of the Note, which is the one cell a `blocked` card renders in full —
 *   so the overflow is rejoined into the last column instead.
 */
export function parseLedger(markdown: string): LedgerRow[] {
  const rows: LedgerRow[] = []
  let headers: string[] | null = null

  for (const line of markdown.split("\n")) {
    if (line.startsWith(HEADER_PREFIX)) {
      headers = cells(line)
      continue
    }
    if (!headers || !line.startsWith("|")) continue

    const parts = cells(line)
    const id = parts[0]
    if (!id || !TASK_ID.test(id)) continue

    // Overflow is trailing prose, never a shifted column: every wide row in the
    // corpus keeps its first eight cells aligned and spills inside the free
    // text at the end.
    const values =
      parts.length > headers.length
        ? [
            ...parts.slice(0, headers.length - 1),
            parts.slice(headers.length - 1).join(" | "),
          ]
        : parts

    const at = (name: string) => {
      const i = headers!.indexOf(name)
      return i === -1 ? "" : (values[i] ?? "")
    }

    const rawStatus = at("Status")
    rows.push({
      id,
      title: at("Title"),
      size: at("Size"),
      model: at("Model"),
      effort: at("Effort"),
      version: at("Version"),
      owner: at("Owner"),
      status: isLedgerStatus(rawStatus) ? rawStatus : null,
      rawStatus,
      commit: at("Commit"),
      review: at("Review"),
      note: at("Note"),
    })
  }

  return rows
}
