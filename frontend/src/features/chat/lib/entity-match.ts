export interface EntityMatch {
  start: number
  end: number
  name: string
}

function isWordChar(ch: string | undefined): boolean {
  return ch !== undefined && /[a-z0-9]/i.test(ch)
}

/**
 * Index of the first occurrence of `needle` in `haystack` bordered by
 * non-alphanumeric characters on both sides (a word-boundary match), or -1.
 *
 * Substring matching badged entity names mid-word — `api` inside "capital",
 * `cat` inside "category" — corrupting the rendered answer. The boundary check
 * looks at the characters OUTSIDE the needle, so the name itself may contain
 * separators (`darkraise-ui`, `github actions`).
 */
function findWordBoundaryIndex(haystack: string, needle: string): number {
  if (!needle) return -1
  let from = 0
  for (;;) {
    const idx = haystack.indexOf(needle, from)
    if (idx === -1) return -1
    const before = idx > 0 ? haystack[idx - 1] : undefined
    const afterPos = idx + needle.length
    const after = afterPos < haystack.length ? haystack[afterPos] : undefined
    if (!isWordChar(before) && !isWordChar(after)) return idx
    from = idx + 1
  }
}

/**
 * Find word-boundary positions of each entity name in `text`, deduped by name
 * and sorted by start position. Names are matched case-insensitively; the
 * returned offsets index into the original `text`.
 */
export function findEntityMatches(
  text: string,
  entityNames: { name: string; id?: string }[],
): EntityMatch[] {
  const lowerText = text.toLowerCase()
  const matches: EntityMatch[] = []
  const seen = new Set<string>()

  for (const entity of entityNames) {
    const lowerName = entity.name.toLowerCase()
    if (seen.has(lowerName)) continue
    const idx = findWordBoundaryIndex(lowerText, lowerName)
    if (idx === -1) continue
    seen.add(lowerName)
    matches.push({ start: idx, end: idx + entity.name.length, name: entity.name })
  }

  matches.sort((a, b) => a.start - b.start)
  return matches
}
