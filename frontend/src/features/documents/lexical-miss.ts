/** Whether a section search came back on meaning alone.
 *
 * The search ranks by cosine and applies no similarity floor, so it always
 * answers with its nearest sections -- a nonsense query gets twenty hits, and
 * "No sections matched" is unreachable. Ranking is not this file's to change
 * (retrieval stays as it is); what the reader is owed is the fact that none of
 * the hits contains a word they typed, so the list is read as "closest by
 * meaning" rather than as matches.
 *
 * Deliberately crude, because a wrong answer here costs one sentence of
 * notice copy, not a result: a hit mentions a word when its text or heading
 * path contains the word's stem as a substring, case-insensitively. Words
 * under three characters and a handful of English stopwords are ignored,
 * since nearly every section contains "the" and that says nothing about the
 * query. A query with no word left to test is never called a miss.
 */

export interface LexicalHit {
  text: string
  heading_path: string[]
}

// prettier-ignore
const STOPWORDS = new Set([
  "the", "and", "for", "with", "are", "was", "were", "this", "that", "from",
  "into", "what", "which", "who", "how", "why", "when", "where", "does", "not",
  "but", "has", "have", "had", "its", "our", "your", "their", "there", "about",
  "can", "will", "should", "would", "could", "you", "all", "any",
])

/** Plural and third-person endings off, so "jobs" finds "job" and
 *  "searches" finds "search". `-es` comes off only after a sibilant
 *  ("notes" is "note", not "not"), and a double `s` is never a plural. */
function stem(word: string): string {
  if (/(ch|sh|ss|x|z)es$/.test(word)) return word.slice(0, -2)
  if (word.endsWith("s") && !word.endsWith("ss") && word.length > 3) {
    return word.slice(0, -1)
  }
  return word
}

export function queryWords(query: string): string[] {
  const words = query.toLowerCase().match(/[\p{L}\p{N}_]+/gu) ?? []
  return [
    ...new Set(
      words.filter((w) => w.length >= 3 && !STOPWORDS.has(w)).map(stem),
    ),
  ]
}

/** True when there are hits, the query has words worth testing, and no hit
 *  mentions any of them. */
export function noHitMentionsQuery(query: string, hits: LexicalHit[]): boolean {
  if (hits.length === 0) return false
  const words = queryWords(query)
  if (words.length === 0) return false
  return !hits.some((hit) => {
    const haystack = `${hit.heading_path.join(" ")} ${hit.text}`.toLowerCase()
    return words.some((word) => haystack.includes(word))
  })
}
